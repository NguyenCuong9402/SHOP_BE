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
from app.models import test_test_executions, TestExecutions, MapTestExec, Test
from app.utils import send_error, send_result
from app.validator import IssueIDSchema, IssueIDValidator, TestExecValidator
from sqlalchemy.sql import func

api = Blueprint('enrollments', __name__)

TEST_EXECUTION_NOT_EXIST = '119'
ADD_ISSUE_TO_EXECUTION = '18'
REMOVE_ISSUE_TO_EXECUTION = '16'
CREATE_TEST_EXECUTION = '19'
TEST_EXECUTION_EXIST = '20'
INVALID_PARAMETERS_ERROR = 'g1'


@api.route('', methods=['POST'])
def create_test_exec():
    """ This api get information of an enrollment_info.

        Returns:

        Examples::

    """
    # 1. Get keyword from json body
    try:
        body = request.get_json()
        params = TestExecValidator().load(body) if body else dict()
    except ValidationError as err:
        logger.error(json.dumps({
            "message": err.messages,
            "data": err.valid_data
        }))
        return send_error(message_id=INVALID_PARAMETERS_ERROR, data=err.messages)

    exec_id = params.get('id', '')
    name = params.get('name', '')
    key = params.get('key', '')

    # check test execution exist
    test_executions: TestExecutions = TestExecutions.query.filter(TestExecutions.id == exec_id).first()
    if test_executions:
        return send_error(message_id=TEST_EXECUTION_EXIST)

    new_test_executions = TestExecutions()
    new_test_executions.id = exec_id
    new_test_executions.name = name
    new_test_executions.key = key
    db.session.add(new_test_executions)
    db.session.commit()

    return send_result(message_id=CREATE_TEST_EXECUTION)


@api.route('/<test_execution_id>', methods=['GET'])
def get_issue_links(test_execution_id):
    """ This api get information of an enrollment_info.

        Returns:

        Examples::

    """

    map_test_executions: MapTestExec = MapTestExec.query. \
        filter(MapTestExec.exec_id == test_execution_id).all()
    if not map_test_executions:
        return send_error(message_id=TEST_EXECUTION_NOT_EXIST)
    data = IssueIDSchema(many=True).dump(map_test_executions)
    return send_result(data=data)


@api.route('/<test_execution_id>', methods=['POST'])
def add_issue_links(test_execution_id):
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

    # check test exist
    test_issue: Test = Test.query.filter(Test.id.in_(issue_ids)).all()
    if not test_issue:
        return send_error(message_id=TEST_EXECUTION_NOT_EXIST)

    # get index
    map_test_executions: MapTestExec = MapTestExec.query.\
        filter(MapTestExec.exec_id == test_execution_id).first()
    if not map_test_executions:
        index = 1
    else:
        test_executions_index = db.session.query(func.max(MapTestExec.index).label('index')). \
            filter(MapTestExec.exec_id == test_execution_id).first()
        index = test_executions_index.index + 1

    for item in test_issue:
        new_maps_test_executions = MapTestExec()
        new_maps_test_executions.id = str(uuid.uuid4())
        new_maps_test_executions.test_id = item.id
        new_maps_test_executions.exec_id = test_execution_id
        new_maps_test_executions.index = index
        db.session.add(new_maps_test_executions)
        index += 1
    db.session.commit()

    return send_result(message_id=ADD_ISSUE_TO_EXECUTION)


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
    map_test_executions: MapTestExec = MapTestExec.query.\
        filter(MapTestExec.exec_id == test_execution_id).delete()
    db.session.commit()

    return send_result(message_id=REMOVE_ISSUE_TO_EXECUTION)
