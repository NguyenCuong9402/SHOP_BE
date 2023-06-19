import json
import os
import shutil
import uuid
from operator import or_
from flask import Blueprint, request
from flask_jwt_extended import get_jwt_identity
from sqlalchemy import func, asc, and_, desc

from app.api.v1.history_test import save_history_test_case
from app.api.v1.test_type.test_type import get_test_type_default
from app.gateway import authorization_require
from app.models import db, TestRepository, Repository, TestCase, TestCasesTestSets
from app.utils import send_result, send_error, get_timestamp_now
from app.validator import TestCaseSchema, RepositorySchema, RepositoryProjectSchema

api = Blueprint('test_repository', __name__)


@api.route('', methods=["POST"])
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
            return send_error(message=f"{name} already exists at this location",
                              is_dynamic=True)
        if parent_id == '' or parent_id == project_id:
            repo_all = Repository.query.filter(Repository.cloud_id == cloud_id, Repository.project_id == project_id,
                                               or_(Repository.id == str(project_id), Repository.type == 1)).first()
            if repo_all is None:
                repo_all = Repository(
                    id=str(project_id),
                    project_id=project_id,
                    cloud_id=cloud_id,
                    name=DEFAULT_DATA['name'],
                    type=DEFAULT_DATA["type"],
                    created_date=get_timestamp_now()
                )
                db.session.add(repo_all)
                db.session.flush()
            parent_id = str(project_id)
        else:
            test_repo = Repository.query.filter(Repository.id == parent_id, Repository.cloud_id == cloud_id,
                                                Repository.project_id == project_id, Repository.type == 0).first()
            if test_repo is None:
                return send_error(message="Check your params")
        index = Repository.query.filter(Repository.cloud_id == cloud_id, Repository.project_id == project_id,
                                        Repository.parent_id == parent_id, Repository.type == 0).count()
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


@api.route('', methods=["PUT"])
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
        repo_all = Repository.query.filter(Repository.cloud_id == cloud_id, Repository.project_id == project_id,
                                           Repository.id == repository_id).first()
        if repository_id in [str(project_id), ""] or repo_all.type == 1:
            return send_error(message="Must not rename")
        if name == '':
            return send_error(message="Folder name must not be empty.", is_dynamic=True)
        repo = Repository.query.filter(Repository.id == repository_id, Repository.cloud_id == cloud_id,
                                       Repository.cloud_id == cloud_id, Repository.type != 1).first()
        old_name = repo.name
        if repo is None:
            return send_error(message="Test Repository has been changed \n "
                                      "Please refresh the page to view the changes.", is_dynamic=True)
        repo.name = name
        db.session.flush()
        db.session.commit()
        return send_result(message=f"Folder {old_name} renamed to {name}", show=True)
    except Exception as ex:
        db.session.rollback()
        return send_error(message=str(ex))


@api.route('', methods=["DELETE"])
@authorization_require()
def remove_repo():
    try:
        token = get_jwt_identity()
        cloud_id = token.get('cloudId')
        project_id = token.get('projectId')
        user_id = token.get('userId')
        body_request = request.get_json()
        repository_id = body_request.get('repository_id', '')
        repo = Repository.query.filter(Repository.cloud_id == cloud_id, Repository.project_id == project_id,
                                       Repository.id == repository_id).first()
        if repository_id in [str(project_id), ""] or repo.type == 1:
            return send_error(message="Must not delete")
        if repo is None:
            return send_error(message="Test Repository has been changed \n "
                                      "Please refresh the page to view the changes.", is_dynamic=True)
        name = repo.name
        # find repo child by repo to remove
        repo_ids = get_child_repo_id(cloud_id, project_id, repository_id, [repository_id])
        Repository.query.filter(Repository.id.in_(repo_ids), Repository.cloud_id == cloud_id,
                                Repository.project_id == project_id).delete()
        db.session.flush()
        db.session.commit()
        return send_result(message=f"Folder {name} removed")
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
        test_case = body_request.get('test_case')
        repository_id_old = body_request.get('repository_id_old', '')
        repository_id_new = body_request.get('repository_id_new', '')
        index_drop = body_request.get('index_drop')
        if not isinstance(index_drop, int):
            index_drop = 0
        if len(test_case) == 0:
            return send_error(message="Check validate request")
        test_case = TestCase.query.filter(TestCase.issue_id == test_case['issue_id'], TestCase.cloud_id == cloud_id,
                                          TestCase.project_id == project_id).first()
        test_type_id = get_test_type_default(cloud_id, project_id)
        if test_case is None:
            test_case = TestCase(
                id=str(uuid.uuid4()),
                issue_id=test_case['issue_id'],
                issue_key=test_case['issue_key'],
                project_id=project_id,
                cloud_id=cloud_id,
                created_date=get_timestamp_now(),
                test_type_id=test_type_id
            )
            db.session.add(test_case)
            db.session.flush()
        # move test to root
        repo = Repository.query.filter(Repository.id == repository_id_new, Repository.cloud_id == cloud_id,
                                       Repository.project_id == project_id).first()
        if repository_id_new in [str(project_id), ""] or repo.type == 1:
            test_now = db.session.query(TestRepository.repository_id, Repository.name, Repository.parent_id)\
                .join(Repository, Repository.id == TestRepository.repository_id)\
                .filter(TestRepository.test_id == test_case.id).first()
            if test_now.repository_id != project_id:
                old = get_link_repo_parent(cloud_id, project_id, test_now.parent_id, test_now.name)
                db.session.delete(test_now)
                db.session.flush()
                save_history_test_case(test_case.id, user_id, 6, 2, [], [old, ""])
                message = "Test(s) moved to Test Repository Root."
            else:
                message = "No change"
        else:
            if repo is None:
                return send_error(message="Test Repository has been changed"
                                          " \nrefresh the page to view the changes.", is_dynamic=True)
            test_now = TestRepository.query.filter(TestRepository.test_id == test_case.id).first()
            # move test from root to not root
            if test_now is None:
                index = TestRepository.query.filter(TestRepository.repository_id == repository_id_new).count()
                test_to_repo = TestRepository(
                    id=str(uuid.uuid4()),
                    test_id=test_case.id,
                    repository_id=repository_id_new,
                    create_date=get_timestamp_now(),
                    index=index + 1
                )
                db.session.add(test_to_repo)
                db.session.flush()
                message = f"Test(s) moved to folder {repo.name}"
                new = get_link_repo_parent(cloud_id, project_id, repo.parent_id, repo.name)
                save_history_test_case(test_case.id, user_id, 6, 2, [], ["", new])
            else:
                # move test in repo A to repo B
                if repository_id_new != repository_id_old:
                    test_repo = TestRepository.query.filter(TestRepository.repository_id == repository_id_new).first()
                    if test_repo is None:
                        return send_error(message="Test Repository has been changed"
                                                  " \nrefresh the page to view the changes.", is_dynamic=True)
                    repository = Repository.query.filter(Repository.id == test_repo.repository_id,
                                                         Repository.cloud_id == cloud_id, Repository.
                                                         project_id == project_id).first()
                    if repository is None:
                        return send_error(message="Test Repository has been changed"
                                                  " \nrefresh the page to view the changes.", is_dynamic=True)
                    check = False if test_now.repository_id == repository_id_old else True
                    count = TestRepository.query.filter(TestRepository.repository_id == repository_id_new).count()
                    # update index test old repo
                    TestRepository.query.filter(TestRepository.repository_id == test_now.repository_id) \
                        .filter(TestRepository.index > test_now.index) \
                        .update(dict(index=TestRepository.index - 1))
                    # set index test to new repo
                    test_now.repository_id = repository_id_new
                    test_now.index = count + 1
                    test_now.create_date = get_timestamp_now()
                    db.session.flush()
                    db.session.commit()
                    if check:
                        return send_result(message="Please refresh the page to view the changes.| Move success", show=True)
                    message = f"Test(s) moved to folder {repo.name}"
                # change index in repo A
                else:
                    index_max = TestRepository.query.filter(TestRepository.repository_id == repository_id_new).count()
                    if index_drop == 0:
                        return send_result(message="No change")
                    test_repository = TestRepository.query.filter(TestRepository.repository_id == repository_id_new,
                                                                  TestRepository.test_id == test_case.id).first()
                    if test_repository:
                        return send_error(message="Tests in not in Test Repository")
                    if test_repository.index < index_drop:
                        if index_drop < 1:
                            return send_error(message=f'Must be a value between 1 and {index_max}')
                        TestRepository.query.filter(TestRepository.repository_id == repository_id_new) \
                            .filter(TestRepository.index < index_drop + 1)\
                            .filter(TestRepository.index > test_repository.index) \
                            .update(dict(index=TestRepository.index - 1))
                        test_repository.index = index_drop
                        db.session.flush()
                    else:
                        if index_drop > index_max:
                            return send_error(message=f'Must be a value between 1 and {index_max}')
                        TestRepository.query.filter(TestRepository.repository_id == repository_id_new) \
                            .filter(TestRepository.index < test_repository.index) \
                            .filter(TestRepository.index > index_drop - 1) \
                            .update(dict(index=TestRepository.index - 1))
                        test_repository.index = index_drop
                        db.session.flush()
                    message = "Update successfully"
        db.session.commit()
        return send_result(message=message, show=True)
    except Exception as ex:
        db.session.rollback()
        return send_error(message=str(ex))


def get_link_repo_parent(cloud_id: str, project_id: str, parent_id: str, link: str):
    stack = [(parent_id, link)]
    while stack:
        curr_id, current_link = stack.pop()
        test_parent = Repository.query.filter(Repository.cloud_id == cloud_id, Repository.project_id == project_id,
                                              Repository.id == parent_id).first()
        if test_parent is not None:
            if test_parent.type == 1:
                break
            link = test_parent.name + "/" + current_link
            stack.append([test_parent.parent_id, link])
    return link


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
        repo = Repository.query.filter(Repository.id == repository_id).first()
        if (repository_id in [str(project_id), ""]) or test_id == "" or repo.type == 1:
            return send_error(message="Check validate request")
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


@api.route("/get-test", methods=["POST"])
@authorization_require()
def get_test_in_repo():
    try:
        token = get_jwt_identity()
        cloud_id = token.get('cloudId')
        project_id = token.get('projectId')
        repository_id = request.args.get('repository_id', '', type=str)
        body_request = request.get_json()
        test_types = body_request.get("test_types", [])
        test_sets = body_request.get("test_sets", [])
        count_repo = Repository.query.filter(Repository.cloud_id == cloud_id, Repository.project_id).count()
        if count_repo == 0:
            repo_0 = Repository(
                id=str(project_id),
                name=DEFAULT_DATA['name'],
                cloud_id=cloud_id,
                project_id=project_id,
                type=DEFAULT_DATA['type']
            )
            db.session.add(repo_0)
            db.session.flush()
            db.session.commit()
        if repository_id in [str(project_id), ""]:
            repository = Repository.query.filter(Repository.cloud_id == cloud_id, Repository.project_id == project_id,
                                                 or_(Repository.type != DEFAULT_DATA['type'],
                                                     Repository.id != project_id)).all()
            repo_id = [item.id for item in repository]
            test_repository = TestRepository.query.filter(TestRepository.repository_id.in_(repo_id)).all()
            repository_id = str(project_id)
        else:
            repo = Repository.query.filter(Repository.cloud_id == cloud_id, Repository.project_id == project_id,
                                           Repository.id == repository_id).first()
            test_repository = TestRepository.query.filter(TestRepository.repository_id == repo.id).all()
        test_ids = [test_repo.test_id for test_repo in test_repository]
        test_cases_in_repo = TestCase.query.filter(TestCase.id.in_(test_ids))\
            .order_by(desc(TestCase.issue_id))
        if len(test_types) > 0:
            test_cases_in_repo = test_cases_in_repo.filter(TestCase.test_type_id.in_(test_types))
        if len(test_sets) > 0:
            test_cases_in_repo = test_cases_in_repo.join(TestCasesTestSets,
                                                         test_cases_in_repo.id == TestCasesTestSets.test_case_id)\
                .filter(TestCasesTestSets.test_set_id.in_(test_sets))
        tests = [test.id for test in test_cases_in_repo]
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
            repo_all = Repository(
                id=str(project_id),
                project_id=project_id,
                cloud_id=cloud_id,
                name=DEFAULT_DATA['name'],
                type=DEFAULT_DATA["type"],
                created_date=get_timestamp_now()
            )
            db.session.add(repo_all)
            db.session.flush()
        repos = Repository.query.filter(Repository.cloud_id == cloud_id, Repository.project_id == project_id,
                                        Repository.type != 1).all()
        # set data -> repo_0
        repo_0 = Repository.query.filter(Repository.cloud_id == cloud_id, Repository.project_id == project_id,
                                         Repository.type == 1, Repository.id == str(project_id)).first()
        repository_0 = RepositoryProjectSchema().dump(repo_0)
        repo_id = [repo.id for repo in repos]
        test_repo_count = TestRepository.query.filter(TestRepository.repository_id.in_(repo_id)).count()
        repository_0['count_test'] = test_repo_count
        return send_result(data=[repository_0])
    except Exception as ex:
        db.session.rollback()
        return send_error(message=str(ex))


@api.route("/change-repository", methods=["PUT"])
@authorization_require()
def change_repo():
    try:
        token = get_jwt_identity()
        cloud_id = token.get('cloudId')
        project_id = token.get('projectId')
        body_request = request.get_json()
        parent_id = body_request.get('parent_id', '')
        index_drop = body_request.get('index_drop')
        repository_id = body_request.get('repository_id', '')
        if not isinstance(index_drop, int):
            index_drop = 0
        repo_now = Repository.query.filter(Repository.cloud_id == cloud_id, Repository.project_id == project_id,
                                           Repository.id == repository_id).first()
        if repository_id == "" or repository_id == project_id or repo_now.type == 1:
            return send_error(message="Must not change")
        # change repo child index in repo parent
        if repo_now.parent_id == parent_id:
            if index_drop == 0:
                return send_result(message="No change")
            if repo_now.index < index_drop:
                Repository.query.filter(Repository.cloud_id == cloud_id, Repository.project_id == project_id,
                                        Repository.parent_id == parent_id) \
                    .filter(Repository.index < index_drop + 1).filter(Repository.index > repo_now.index)\
                    .update(dict(index=Repository.index - 1))
                repo_now.index = index_drop
                db.session.flush()
            else:
                Repository.query.filter(Repository.cloud_id == cloud_id, Repository.project_id == project_id,
                                        Repository.parent_id == parent_id) \
                    .filter(Repository.index < repo_now.index).filter(Repository.index > index_drop - 1) \
                    .update(dict(index=Repository.index + 1))
                repo_now.index = index_drop
                db.session.flush()
        else:
            Repository.query.filter(Repository.cloud_id == cloud_id, Repository.project_id == project_id,
                                    Repository.parent_id == repo_now.parent_id) \
                .filter(Repository.index > repo_now.index)\
                .update(dict(index=Repository.index - 1))
            repo_parent_count = Repository.query.filter(Repository.parent_id == parent_id, Repository.cloud_id == cloud_id,
                                                        Repository.project_id).count()
            if index_drop < 1 or index_drop > repo_parent_count + 1:
                return send_error(message=f'Must be a value between 1 and {repo_parent_count}')
            Repository.query.filter(Repository.cloud_id == cloud_id, Repository.project_id == project_id,
                                    Repository.parent_id == parent_id) \
                .filter(Repository.index > index_drop - 1) \
                .update(dict(index=Repository.index + 1))
            repo_now.index = index_drop
            repo_now.parent_id = parent_id
            db.session.flush()
        db.session.commit()
        return send_result(message="change oke")
    except Exception as ex:
        db.session.commit()
        return send_error(message=str(ex))


def check_coincided_name(name='', self_id=None, project_id='', cloud_id='', parent_id=''):
    if parent_id == '':
        existed_test_step = Repository.query.filter(
            and_(func.lower(Repository.name) == func.lower(name), Repository.id != self_id,
                 Repository.cloud_id == cloud_id, Repository.project_id == project_id,
                 Repository.parent_id == str(project_id))).first()
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
        "type": 1
    }
