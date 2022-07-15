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
from app.models import test_test_executions, TestExecutions, MapTestExec, Test, TestRepo
from app.utils import send_error, send_result
from app.validator import RepoValidator, IssueIDValidator
from sqlalchemy import func
from datetime import datetime

api = Blueprint('enrollments', __name__)

TEST_REPO_NOT_EXIST = '119'
TEST_REP_NAME_EXIST = '119'
ADD_ISSUE_TO_EXECUTION = '18'
REMOVE_ISSUE_TO_EXECUTION = '16'
INVALID_PARAMETERS_ERROR = 'g1'
ID_REPO_DEFAULT = '-1'
CREATE_REPO = '16'
RENAME_REPO = '16'


@api.route('/<test_execution_id>', methods=['GET'])
def get_issue_links(test_execution_id):
    """ This api get information of an enrollment_info.

        Returns:

        Examples::

    """

    map_test_executions: TestExecutions = TestExecutions.query.filter(TestExecutions.id == test_execution_id).first()
    if not map_test_executions:
        return send_error(message_id=TEST_EXECUTION_NOT_EXIST)
    data = IssueIDSchema(many=True).dump(map_test_executions.tests)
    return send_result(data=data)


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
                                                      TestRepo.parent_folder_id == project_id).first()
    if not test_repo_exist:
        return send_error(message_id=TEST_REPO_NOT_EXIST)

    # check test exist
    test_repo_name_exist: TestRepo = TestRepo.query.filter(TestRepo.project_id == project_id,
                                                           TestRepo.parent_folder_id == project_id,
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


@api.route('', methods=['POST'])
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
                                                           TestRepo.parent_folder_id == test_repo.parent_id,
                                                           TestRepo.name == name, TestRepo.id != repo_id).first()
    if test_repo_name_exist:
        return send_error(message_id=TEST_REP_NAME_EXIST)

    test_repo.name = name
    db.session.commit()

    return send_result(message_id=RENAME_REPO)


@api.route('/<test_execution_id>', methods=['DELETE'])
def remove_issue_links(test_execution_id):
    """ This api get information of an enrollment_info.

        Returns:

        Examples::

    """
    # 1. Get keyword from json body
    try:
        body = request.get_json()
        params = IssueIDValidator().load(body) if body else dict()
    except ValidationError as err:
        logger.error(json.dumps({
            "message": err.messages,
            "data": err.valid_data
        }))
        return send_error(message_id=INVALID_PARAMETERS_ERROR, data=err.messages)

    issue_ids = params.get('issue_id', [])

    # check test execution exist
    test_executions: TestExecutions = TestExecutions.query.filter(TestExecutions.id == test_execution_id).first()
    if not test_executions:
        return send_error(message_id=TEST_EXECUTION_NOT_EXIST)

    # # check test exist
    # test_issue: Test = Test.query.filter(Test.id.in_(issue_ids)).all()
    # if not test_issue:
    #     return send_error(message_id=TEST_EXECUTION_NOT_EXIST)

    # get index
    map_test_executions: MapTestExec = MapTestExec.query. \
        filter(MapTestExec.exec_id == test_execution_id, func.max(MapTestExec.index)).delete()
    db.session.commit()

    return send_result(message_id=REMOVE_ISSUE_TO_EXECUTION)
