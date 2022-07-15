"""User site
Author: HungVD
Create Date: 11/07/2022
Target: Use for users view enrollment information
"""
import json

import uuid
from flask import Blueprint, request
from marshmallow import ValidationError
from app.extensions import logger, db
from app.models import test_test_executions, TestExecutions, MapTestExec, Test, TestRepo, MapRepo
from app.utils import send_error, send_result
from app.validator import RepoValidator, MoveRepoValidator, RepositoryAddIssueValidator, GetRepositoryValidator
from sqlalchemy import func
from datetime import datetime

api = Blueprint('enrollments', __name__)

TEST_REPO_NOT_EXIST = '119'
TEST_REP_NAME_EXIST = '119'
ADD_ISSUE_TO_REPO = '18'
REMOVE_ISSUE_TO_EXECUTION = '16'
INVALID_PARAMETERS_ERROR = 'g1'
ID_REPO_DEFAULT = '-1'
CREATE_REPO = '16'
RENAME_REPO = '16'
MOVE_REPO = '16'
TEST_NOT_EXIST = '16'
REORDER_ISSUE_TO_REPO = '16'
MOVER_ISSUE_TO_REPO = '16'


def reindex_issue(index, issue_ids, repo_id):
    """
    """
    index_temp = 0

    if index:   # if index not None : Re oder issue in repository
        len_index = len(issue_ids)
        index_renew = index

        map_repo: MapRepo = MapRepo.query.filter(MapRepo.test_repo_id == repo_id).order_by(MapRepo.index.asc()).all()

        for item in map_repo:

            if item.id in issue_ids:
                item.index = index_renew
                index_renew += 1
                continue

            # add item
            if index == index_temp:
                index_temp = index_temp + len_index
            item.index = index_temp
            index_temp += 1
        db.session.commit()
    else:   # if index None : Remove issue in repository
        map_repo: MapRepo = MapRepo.query.filter(MapRepo.test_repo_id == repo_id).order_by(MapRepo.index.asc()).all()
        for item in map_repo:
            if item.id in issue_ids:
                continue
            item.index = index_temp
            index_temp += 1
        db.session.commit()
    return True


@api.route('', methods=['POST'])
def create_test_repo():
    """ This api get information of an enrollment_info.

        Returns:

        Examples::

    """
    # 1. Get keyword from json body
    try:
        body = request.get_json()
        params = RepoValidator(exclude =("id",)).load(body) if body else dict()
    except ValidationError as err:
        logger.error(json.dumps({
            "message": err.messages,
            "data": err.valid_data
        }))
        return send_error(message_id=INVALID_PARAMETERS_ERROR, data=err.messages)

    project_id = params.get('project_id', '')
    parent_folder_id = params.get('parent_folder_id', ID_REPO_DEFAULT)
    name = params.get('project_id')

    # check repo exist
    test_repo_exist: TestRepo = TestRepo.query.filter(TestRepo.project_id == project_id,
                                                      TestRepo.parent_id == project_id).first()
    if not test_repo_exist:
        return send_error(message_id=TEST_REPO_NOT_EXIST)

    # check test exist
    test_repo_name_exist: TestRepo = TestRepo.query.filter(TestRepo.project_id == project_id,
                                                           TestRepo.parent_id == project_id,
                                                           TestRepo.name == name).first()
    if test_repo_name_exist:
        return send_error(message_id=TEST_REP_NAME_EXIST)

    new_test_repo = TestRepo()
    new_test_repo.id = str(uuid.uuid4())
    new_test_repo.parent_id = parent_folder_id
    new_test_repo.name = name
    new_test_repo.project_id = project_id
    new_test_repo.create_date = datetime.utcnow().timestamp()
    db.session.add(new_test_repo)
    db.session.commit()

    return send_result(message_id=CREATE_REPO)


@api.route('/rename', methods=['POST'])
def rename_test_repo():
    """ This api get information of an enrollment_info.

        Returns:

        Examples::

    """
    # 1. Get keyword from json body
    try:
        body = request.get_json()
        params = RepoValidator(only=("id", "name")).load(body) if body else dict()
    except ValidationError as err:
        logger.error(json.dumps({
            "message": err.messages,
            "data": err.valid_data
        }))
        return send_error(message_id=INVALID_PARAMETERS_ERROR, data=err.messages)

    repo_id = params.get('id', '')
    name = params.get('project_id')

    # check repo exist
    test_repo: TestRepo = TestRepo.query.filter(TestRepo.id == repo_id).first()
    if not test_repo:
        return send_error(message_id=TEST_REPO_NOT_EXIST)

    # check test exist
    test_repo_name_exist: TestRepo = TestRepo.query.filter(TestRepo.project_id == test_repo.project_id,
                                                           TestRepo.parent_id == test_repo.parent_id,
                                                           TestRepo.name == name, TestRepo.id != repo_id).first()
    if test_repo_name_exist:
        return send_error(message_id=TEST_REP_NAME_EXIST)

    test_repo.name = name
    db.session.commit()

    return send_result(message_id=RENAME_REPO)


@api.route('move', methods=['POST'])
def move_test_repo():
    """ This api get information of an enrollment_info.

        Returns:

        Examples::

    """
    # 1. Get keyword from json body
    try:
        body = request.get_json()
        params = MoveRepoValidator().load(body) if body else dict()
    except ValidationError as err:
        logger.error(json.dumps({
            "message": err.messages,
            "data": err.valid_data
        }))
        return send_error(message_id=INVALID_PARAMETERS_ERROR, data=err.messages)

    repo_id = params.get('id', '')
    index = params.get('index', None)
    project_id = params.get('project_id', '')
    parent_folder_id = params.get('parent_folder_id', ID_REPO_DEFAULT)

    # check repo exist
    test_repo: TestRepo = TestRepo.query.filter(TestRepo.id == repo_id).first()
    if not test_repo:
        return send_error(message_id=TEST_REPO_NOT_EXIST)

    # check test name exist
    test_repo_name_exist: TestRepo = TestRepo.query.filter(TestRepo.project_id == project_id,
                                                           TestRepo.parent_id == parent_folder_id,
                                                           TestRepo.name == test_repo.name,
                                                           TestRepo.id != test_repo.id).first()
    if test_repo_name_exist:
        return send_error(message_id=TEST_REP_NAME_EXIST)

    # update index
    if index:
        if index < test_repo.index:
            db.session.query(TestRepo). \
                filter(TestRepo.index > index, TestRepo.index < test_repo.index - 1). \
                update(dict(index=TestRepo.index + 1))
        elif index > test_repo.index:
            db.session.query(TestRepo). \
                filter(TestRepo.index > test_repo.index + 1, TestRepo.index < index). \
                update(dict(index=TestRepo.index - 1))
    else:
        test_repo_max_index = db.session.query(func.max(TestRepo.index).label('index')).\
            filter(TestRepo.project_id == project_id, TestRepo.parent_id == parent_folder_id).first()
        index = test_repo_max_index.index + 1

    test_repo.project_id = project_id
    test_repo.parent_id = parent_folder_id
    test_repo.index = index
    db.session.commit()

    return send_result(message_id=MOVE_REPO)


@api.route('/issue/add', methods=['POST'])
def add_issue_links():
    """ This api get information of an enrollment_info.

        Returns:

        Examples::

    """
    # 1. Get keyword from json body
    try:
        body = request.get_json()
        params = RepositoryAddIssueValidator().load(body) if body else dict()
    except ValidationError as err:
        logger.error(json.dumps({
            "message": err.messages,
            "data": err.valid_data
        }))
        return send_error(message_id=INVALID_PARAMETERS_ERROR, data=err.messages)

    issue_ids = params.get('issue_id', [])
    folder_id = params.get('folder_id', '')
    project_id = params.get('project_id', '')

    # check repo exist
    test_repo_exist: TestRepo = TestRepo.query.filter(TestRepo.id == folder_id).first()
    if not test_repo_exist:
        return send_error(message_id=TEST_REPO_NOT_EXIST)

    # check test exist
    test_repo_issue: MapRepo = MapRepo.query.filter(MapRepo.test_id.in_(issue_ids)).all()
    list_issue_add = list(set(issue_ids)-set([test_repo_issue.test_id]))

    test_repo_max_index = db.session.query(func.max(MapRepo.index).label('index')). \
        filter(MapRepo.test_repo_id == folder_id).first()
    index = test_repo_max_index.index

    for issue_id in list_issue_add:
        new_maps_repo = MapRepo()
        new_maps_repo.id = str(uuid.uuid4())
        new_maps_repo.test_id = issue_id
        new_maps_repo.test_repo_id = folder_id
        new_maps_repo.index = index
        new_maps_repo.create_date = datetime.utcnow().timestamp()
        db.session.add(new_maps_repo)
        index += 1
    db.session.commit()
    return send_result(message_id=MOVER_ISSUE_TO_REPO)


@api.route('/issue/reorder', methods=['POST'])
def re_oder_issue_links():
    """ This api get information of an enrollment_info.

        Returns:

        Examples::

    """
    # 1. Get keyword from json body
    try:
        body = request.get_json()
        params = RepositoryAddIssueValidator().load(body) if body else dict()
    except ValidationError as err:
        logger.error(json.dumps({
            "message": err.messages,
            "data": err.valid_data
        }))
        return send_error(message_id=INVALID_PARAMETERS_ERROR, data=err.messages)

    issue_ids = params.get('issue_id', [])
    index = params.get('index', None)
    folder_id = params.get('folder_id', '-1')
    project_id = params.get('project_id', '')

    # check repo exist
    test_repo_exist: TestRepo = TestRepo.query.filter(TestRepo.id == folder_id).first()
    if not test_repo_exist:
        return send_error(message_id=TEST_REPO_NOT_EXIST)

    # check test exist
    test_issue: Test = Test.query.filter(Test.id.in_(issue_ids)).all()
    if not test_issue:
        return send_error(message_id=TEST_NOT_EXIST)

    # re index issue
    status = reindex_issue(index=index, issue_ids=issue_ids, repo_id=test_repo_exist.id)

    return send_result(message_id=REORDER_ISSUE_TO_REPO)


@api.route('/issue/move', methods=['POST'])
def move_issue_links():
    """ This api get information of an enrollment_info.

        Returns:

        Examples::

    """
    # 1. Get keyword from json body
    try:
        body = request.get_json()
        params = RepositoryAddIssueValidator().load(body) if body else dict()
    except ValidationError as err:
        logger.error(json.dumps({
            "message": err.messages,
            "data": err.valid_data
        }))
        return send_error(message_id=INVALID_PARAMETERS_ERROR, data=err.messages)

    issue_ids = params.get('issue_id', [])
    folder_id = params.get('folder_id', '')
    project_id = params.get('project_id', '')

    # check repo exist
    test_repo_exist: TestRepo = TestRepo.query.filter(TestRepo.id == folder_id).first()
    if not test_repo_exist:
        return send_error(message_id=TEST_REPO_NOT_EXIST)

    # check test exist
    test_repo_issue: MapRepo = MapRepo.query.filter(MapRepo.test_id.in_(issue_ids)).all()
    for item in test_repo_issue:
        # re index issue
        status = reindex_issue(index=None, issue_ids=[item.test_id], repo_id=test_repo_issue.test_repo_id)
        db.session.delete(item)

    test_repo_max_index = db.session.query(func.max(MapRepo.index).label('index')). \
        filter(MapRepo.test_repo_id == folder_id).first()
    index = test_repo_max_index.index

    for issue_id in issue_ids:
        new_maps_repo = MapRepo()
        new_maps_repo.id = str(uuid.uuid4())
        new_maps_repo.test_id = issue_id
        new_maps_repo.test_repo_id = folder_id
        new_maps_repo.index = index
        new_maps_repo.create_date = datetime.utcnow().timestamp()
        db.session.add(new_maps_repo)
        index += 1
    db.session.commit()
    return send_result(message_id=MOVER_ISSUE_TO_REPO)


@api.route('', methods=['GET'])
def get_repository():
    """ This api get information of an enrollment_info.

        Returns:

        Examples::

    """
    # 1. Get keyword from json body
    try:
        params = request.args
        params = GetRepositoryValidator().load(params) if params else dict()
    except ValidationError as err:
        logger.error(json.dumps({
            "message": err.messages,
            "data": err.valid_data
        }))
        return send_error(message_id=INVALID_PARAMETERS_ERROR, data=err.messages)

    issue_ids = params.get('issue_id', [])
    folder_id = params.get('folder_id', '')
    project_id = params.get('project_id', '')

    # check repo exist
    test_repo_exist: TestRepo = TestRepo.query.filter(TestRepo.id == folder_id).first()
    if not test_repo_exist:
        return send_error(message_id=TEST_REPO_NOT_EXIST)

    # check test exist
    test_repo_issue: MapRepo = MapRepo.query.filter(MapRepo.test_id.in_(issue_ids)).all()
    for item in test_repo_issue:
        # re index issue
        status = reindex_issue(index=None, issue_ids=[item.test_id], repo_id=test_repo_issue.test_repo_id)
        db.session.delete(item)

    test_repo_max_index = db.session.query(func.max(MapRepo.index).label('index')). \
        filter(MapRepo.test_repo_id == folder_id).first()
    index = test_repo_max_index.index

    for issue_id in issue_ids:
        new_maps_repo = MapRepo()
        new_maps_repo.id = str(uuid.uuid4())
        new_maps_repo.test_id = issue_id
        new_maps_repo.test_repo_id = folder_id
        new_maps_repo.index = index
        new_maps_repo.create_date = datetime.utcnow().timestamp()
        db.session.add(new_maps_repo)
        index += 1
    db.session.commit()
    return send_result(message_id=MOVER_ISSUE_TO_REPO)



