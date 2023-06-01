import json
import os
import shutil
import uuid
from operator import or_
from flask import Blueprint, request
from flask_jwt_extended import get_jwt_identity
from sqlalchemy import func, asc, and_

from app.gateway import authorization_require
from app.models import db, TestRepository, Repository, TestCase
from app.utils import send_result, send_error, get_timestamp_now

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
        if parent_id == '':
            index = Repository.query.filter(Repository.cloud_id == cloud_id, Repository.project_id == project_id,
                                            or_(Repository.parent_id.is_(None),
                                                Repository.parent_id == parent_id)).count()
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
        if test_id == "" or repository_id_new == "":
            return send_error(message="Check validate request")
        check_test_case = TestCase.query.filter(TestCase.id == test_id, TestCase.project_id == project_id,
                                                TestCase.cloud_id == cloud_id).first()
        if check_test_case is None:
            return send_error(message="Not found test case")
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
            db.session.commit()
        else:
            check = False if test_now.repository_id == repository_id_old else True
            test_now.repository_id = repository_id_new
            test_now.create_date = get_timestamp_now()
            db.session.flush()
            db.session.commit()
            if check:
                return send_result(message="Please refresh the page to view the changes.| Move success", show=True)
        return send_result(message="Move success", show=True)
    except Exception as ex:
        db.session.rollback()
        return send_error(message=str(ex))


def check_coincided_name(name='', self_id=None, project_id='', cloud_id='', parent_id=''):
    if parent_id == '':
        existed_test_step = Repository.query.filter(
            and_(func.lower(Repository.name) == func.lower(name), Repository.id != self_id,
                 Repository.cloud_id == cloud_id, Repository.project_id == project_id,
                 or_(Repository.parent_id.is_(None), Repository.parent_id == parent_id))).first()
    else:
        existed_test_step = Repository.query.filter(
            and_(func.lower(Repository.name) == func.lower(name), Repository.id != self_id,
                 Repository.cloud_id == cloud_id, Repository.project_id == project_id,
                 Repository.parent_id == parent_id)).first()
    if existed_test_step is None:
        return False
    return True
