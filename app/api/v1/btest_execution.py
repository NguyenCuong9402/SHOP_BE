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
from app.models import test_test_executions, TestExecutions, MapTestExecutions, Test
from app.utils import send_error, send_result
from app.validator import IssueIDSchema, IssueIDValidator
from sqlalchemy import func

api = Blueprint('enrollments', __name__)

TEST_EXECUTION_NOT_EXIST = '119'
ADD_ISSUE_TO_EXECUTION = '18'
REMOVE_ISSUE_TO_EXECUTION = '16'
INVALID_PARAMETERS_ERROR = 'g1'


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
    map_test_executions: MapTestExecutions = MapTestExecutions.query.\
        filter(MapTestExecutions.exec_id == test_execution_id, func.max(MapTestExecutions.index)).first()
    if not map_test_executions:
        index = 1
    else:
        index = map_test_executions.index + 1

    for item in test_issue:
        new_maps_test_executions = MapTestExecutions()
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
    map_test_executions: MapTestExecutions = MapTestExecutions.query.\
        filter(MapTestExecutions.exec_id == test_execution_id, func.max(MapTestExecutions.index)).delete()
    db.session.commit()

    return send_result(message_id=REMOVE_ISSUE_TO_EXECUTION)
