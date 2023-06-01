import json
import os
import shutil
import uuid
from operator import or_
from flask import Blueprint, request
from flask_jwt_extended import get_jwt_identity
from sqlalchemy import func, asc, and_, desc

from app.gateway import authorization_require
from app.models import db, TestRepository, Repository, TestCase
from app.utils import send_result, send_error, get_timestamp_now
from app.validator import TestCaseSchema, RepositorySchema, RepositoryProjectSchema

api = Blueprint('test_repository', __name__)


@api.route("/", methods=["POST"])
@authorization_require()
def create_repo():
    try:
        token = get_jwt_identity()
        cloud_id = token.get('cloudId')
        project_id = token.get('projectId')
        user_id = token.get('userId')
        body_request = request.get_json()
        name = body_request.get('name', '')
        parent_id = request.args.get('parent_id', '', type=str)
        if name == '':
            return send_error(message="Folder name must not be empty.", is_dynamic=True)
        coincided = check_coincided_name(name=name, cloud_id=cloud_id, project_id=project_id, parent_id=parent_id)
        if coincided:
            return send_error(message=f"Duplicate folder name, '{name}' already exists at this location",
                              is_dynamic=True)
        if parent_id == '' or parent_id == "-1":
            index = Repository.query.filter(Repository.cloud_id == cloud_id, Repository.project_id == project_id,
                                            Repository.parent_id == "-1").count()
            parent_id = "-1"
        else:
            test_repo = Repository.query.filter(Repository.id == parent_id).first()
            if test_repo is None:
                return send_error(message="Check your params")
            index = Repository.query.filter(Repository.cloud_id == cloud_id, Repository.project_id == project_id,
                                            Repository.parent_id == parent_id).count()
        repo = Repository(
            id=str(uuid.uuid4()),
            project_id=project_id,
            cloud_id=cloud_id,
            name=name,
            parent_id=parent_id,
            index=index + 1,
            created_date=get_timestamp_now()
        )
        db.session.add(repo)
        db.session.flush()
        db.session.commit()
        return send_result(message=f'Folder {name} created.', show=True)
    except Exception as ex:
        db.session.rollback()
        return send_error(message=str(ex))


@api.route("/", methods=["PUT"])
@authorization_require()
def rename_repo():
    try:
        token = get_jwt_identity()
        cloud_id = token.get('cloudId')
        project_id = token.get('projectId')
        user_id = token.get('userId')
        body_request = request.get_json()
        name = body_request.get('name', '')
        repository_id = body_request.get('repository_id', '')
        if repository_id == '' or repository_id == "-1":
            return send_error(message="Must not rename")
        if name == '':
            return send_error(message="Folder name must not be empty.", is_dynamic=True)
        repo = Repository.query.filter(Repository.id == repository_id).first()
        if repo is None:
            return send_error(message="Not found folder, refresh the page to view the changes.", is_dynamic=True)
        repo.name = name
        db.session.flush()
        db.session.commit()
        return send_result(message="Rename success", show=True)
    except Exception as ex:
        db.session.rollback()
        return send_error(message=str(ex))


@api.route("/", methods=["DELETE"])
@authorization_require()
def remove_repo():
    try:
        token = get_jwt_identity()
        cloud_id = token.get('cloudId')
        project_id = token.get('projectId')
        user_id = token.get('userId')
        body_request = request.get_json()
        repository_id = body_request.get('repository_id', '')
        if repository_id == '' or repository_id == "-1":
            return send_error(message="Must not delete")
        repo = Repository.query.filter(Repository.id == repository_id).first()
        if repo is None:
            return send_error(message="Not found folder, refresh the page to view the changes.", is_dynamic=True)
        # check repo là parent ID nào
        repo_ids = get_child_repo_id(cloud_id, project_id, repository_id, [repository_id])
        Repository.query.filter(Repository.id.in_(repo_ids)).delete()
        db.session.flush()
        db.session.commit()
        return send_result(message="Remove success")
    except Exception as ex:
        db.session.rollback()
        return send_error(message=str(ex))


def get_child_repo_id(cloud_id: str, project_id: str, repo_id: str, list_repo_id: list):
    stack = [repo_id]
    while True:
        if not stack:
            break
        current_repo_id = stack.pop()
        parents = Repository.query.filter(Repository.cloud_id == cloud_id, Repository.project_id == project_id,
                                          Repository.parent_id == current_repo_id).all()
        for parent in parents:
            list_repo_id.append(parent.id)
            stack.append(parent.id)
    return list_repo_id


@api.route("/move-test", methods=["POST"])
@authorization_require()
def move_test_to_repo():
    try:
        token = get_jwt_identity()
        cloud_id = token.get('cloudId')
        project_id = token.get('projectId')
        user_id = token.get('userId')
        body_request = request.get_json()
        test_id = body_request.get('test_id', '')
        repository_id_old = body_request.get('repository_id_old', '')
        repository_id_new = body_request.get('repository_id_new', '')
        if test_id == "":
            return send_error(message="Check validate request")
        check_test_case = TestCase.query.filter(TestCase.id == test_id, TestCase.project_id == project_id,
                                                TestCase.cloud_id == cloud_id).first()
        if check_test_case is None:
            return send_error(message="Not found test case")
        if repository_id_new == "" or repository_id_new == "-1":
            test_now = TestRepository.query.filter(TestRepository.test_id == test_id).first()
            if test_now.repository_id != "-1":
                db.session.delete(test_now)
                db.session.flush()
        else:
            repo = Repository.query.filter(Repository.id == repository_id_new).first()
            if repo is None:
                return send_error(message="Not found Folder, refresh the page to view the changes.", is_dynamic=True)

            test_now = TestRepository.query.filter(TestRepository.test_id == test_id).first()
            if test_now is None:
                index = TestRepository.query.filter(TestRepository.repository_id == repository_id_new).count()
                test_to_repo = TestRepository(
                    id=str(uuid.uuid4()),
                    test_id=test_id,
                    repository_id=repository_id_new,
                    create_date=get_timestamp_now(),
                    index=index + 1
                )
                db.session.add(test_to_repo)
                db.session.flush()
            else:
                check = False if test_now.repository_id == repository_id_old else True
                test_now.repository_id = repository_id_new
                test_now.create_date = get_timestamp_now()
                db.session.flush()
                TestRepository.query.filter(TestRepository.repository_id == test_now.repository_id)\
                    .filter(TestRepository.index > test_now.index) \
                    .update(dict(index=TestRepository.index - 1))
                db.session.commit()
                if check:
                    return send_result(message="Please refresh the page to view the changes.| Move success", show=True)
        db.session.commit()
        return send_result(message="Move success", show=True)
    except Exception as ex:
        db.session.rollback()
        return send_error(message=str(ex))


@api.route("/remove-test", methods=["DELETE"])
@authorization_require()
def remove_test_to_repo():
    try:
        token = get_jwt_identity()
        cloud_id = token.get('cloudId')
        project_id = token.get('projectId')
        user_id = token.get('userId')
        body_request = request.get_json()
        test_id = body_request.get('test_id', '')
        repository_id = body_request.get('repository_id', '')
        if test_id == "" or repository_id == "-1" or repository_id == "":
            return send_error(message="Check validate request")
        repo = Repository.query.filter(Repository.id == repository_id).first()
        test_repo = TestRepository.query.filter(TestRepository.test_id == test_id,
                                                TestRepository.repository_id == repository_id).first()
        if repo is None or test_repo is None:
            return send_error(message="Please refresh the page to view the changes.", is_dynamic=True)
        TestRepository.query.filter(TestRepository.repository_id == test_repo.repository_id) \
            .filter(TestRepository.index > test_repo.index) \
            .update(dict(index=TestRepository.index - 1))
        db.session.delete(test_repo)
        db.session.flush()
        db.session.commit()
        return send_result(message="Remove success")
    except Exception as ex:
        db.session.rollback()
        return send_error(message=str(ex))


@api.route("/get-test", methods=["GET"])
@authorization_require()
def get_test_in_repo():
    try:
        token = get_jwt_identity()
        cloud_id = token.get('cloudId')
        project_id = token.get('projectId')
        repository_id = request.args.get('repository_id', '', type=str)
        if repository_id == '' or repository_id == "-1":
            count_repo = Repository.query.filter(Repository.cloud_id == cloud_id, Repository.project_id).count()
            if count_repo == 0:
                repo_0 = Repository(
                    id=DEFAULT_DATA['id'],
                    name=DEFAULT_DATA['name'],
                    cloud_id=cloud_id,
                    project_id=project_id
                )
                db.session.add(repo_0)
                db.session.flush()
                db.session.commit()
            repos = Repository.query.filter(Repository.cloud_id == cloud_id, Repository.project_id == project_id,
                                            Repository.id != DEFAULT_DATA['id']).all()
            repo_id = [repo.id for repo in repos]
            test_repos = TestRepository.query.filter(TestRepository.repository_id.in_(repo_id)).all()
            test_ids = [test_repo.test_id for test_repo in test_repos]
            test_cases_not_in_repo = TestCase.query.filter(TestCase.id.notin_(test_ids)).order_by(
                desc(TestCase.issue_key)).all()
            tests = TestCaseSchema(many=True).dump(test_cases_not_in_repo)
            return send_result(data={"test_cases": tests, "repository_id": "-1"})
        else:
            repo = Repository.query.filter(Repository.cloud_id == cloud_id, Repository.project_id == project_id,
                                           Repository.id == repository_id).first()
            test_repos = TestRepository.query.filter(TestRepository.repository_id == repo.id).all()
            test_ids = [test_repo.test_id for test_repo in test_repos]
            test_cases_in_repo = TestCase.query.filter(TestCase.id.in_(test_ids))\
                .order_by(desc(TestCase.issue_id)).all()
            tests = TestCaseSchema(many=True).dump(test_cases_in_repo)
            return send_result(data={"test_cases": tests, "repository_id": repository_id})
    except Exception as ex:
        db.session.rollback()
        return send_error(message=str(ex))


@api.route("/get-repository", methods=["GET"])
@authorization_require()
def get_repo():
    try:
        token = get_jwt_identity()
        cloud_id = token.get('cloudId')
        project_id = token.get('projectId')
        count_repo = Repository.query.filter(Repository.cloud_id == cloud_id, Repository.project_id).count()
        if count_repo == 0:
            repo_0 = Repository(
                id=DEFAULT_DATA['id'],
                name=DEFAULT_DATA['name'],
                cloud_id=cloud_id,
                project_id=project_id
            )
            db.session.add(repo_0)
            db.session.flush()
            db.session.commit()
        repos = Repository.query.filter(Repository.cloud_id == cloud_id, Repository.project_id == project_id,
                                        Repository.id != DEFAULT_DATA['id']).all()
        repository = RepositorySchema(many=True).dump(repos)
        # set data -> repo_0
        repo_0 = Repository.query.filter(Repository.cloud_id == cloud_id, Repository.project_id == project_id,
                                         Repository.id == DEFAULT_DATA['id']).first()
        repository_0 = RepositoryProjectSchema().dump(repo_0)
        repo_id = [repo.id for repo in repos]
        test_repos = TestRepository.query.filter(TestRepository.repository_id.in_(repo_id)).all()
        test_ids = [test_repo.test_id for test_repo in test_repos]
        count_test_repo_0 = TestCase.query.filter(TestCase.id.notin_(test_ids)).count()
        repository_0['count_test'] = count_test_repo_0
        return send_result(data=[repository_0]+repository)
    except Exception as ex:
        db.session.rollback()
        return send_error(message=str(ex))


def check_coincided_name(name='', self_id=None, project_id='', cloud_id='', parent_id=''):
    if parent_id == '':
        existed_test_step = Repository.query.filter(
            and_(func.lower(Repository.name) == func.lower(name), Repository.id != self_id,
                 Repository.cloud_id == cloud_id, Repository.project_id == project_id,
                 Repository.parent_id == '-1')).first()
    else:
        existed_test_step = Repository.query.filter(
            and_(func.lower(Repository.name) == func.lower(name), Repository.id != self_id,
                 Repository.cloud_id == cloud_id, Repository.project_id == project_id,
                 Repository.parent_id == parent_id)).first()
    if existed_test_step is None:
        return False
    return True


DEFAULT_DATA = {
        "name": "all",
        "id": "-1"
    }
