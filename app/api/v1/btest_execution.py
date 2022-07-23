"""User site
Author: HungVD
Create Date: 11/07/2022
Target: Use for users view enrollment information
"""
import json

import uuid
from flask import Blueprint, request
from marshmallow import ValidationError
from sqlalchemy import or_

from app.extensions import logger, db
from app.models import test_test_executions, TestExecutions, MapTestExec, Test, TestStatus, TestSets
from app.gateway import authorization_require
from app.parser import TestExecSchema
from app.utils import send_error, send_result
from app.validator import IssueIDSchema, IssueIDValidator, TestExecValidator, \
    GetExecutionValidator, TestRunSchema, TestExecutionSchema
from sqlalchemy.sql import func
from flask_jwt_extended import get_jwt_identity, jwt_required

api = Blueprint('testexec', __name__)

TEST_EXECUTION_NOT_EXIST = '119'
ADD_ISSUE_TO_EXECUTION = '18'
REMOVE_ISSUE_TO_EXECUTION = '16'
CREATE_TEST_EXECUTION = '19'
TEST_EXECUTION_EXIST = '20'
INVALID_PARAMETERS_ERROR = 'g1'

DEFAULT_STATUS = '1'


@api.route('', methods=['POST'])
@authorization_require()
def create_test_exec():
    """ This api get information of an enrollment_info.

        Returns:

        Examples::

    """
    # 1. Get keyword from json body
    try:
        body = request.get_json()
        params = TestExecValidator().load(body) if body else dict()
        token = get_jwt_identity()
        cloud_id = token.get('cloudId')
    except ValidationError as err:
        logger.error(json.dumps({
            "message": err.messages,
            "data": err.valid_data
        }))
        return send_error(message_id=INVALID_PARAMETERS_ERROR, data=err.messages)

    issue_id = params.get('issue_id', '')
    name = params.get('name', '')
    key = params.get('key', '')

    # check test execution exist
    test_executions: TestExecutions = TestExecutions.query.filter(TestExecutions.jira_id == issue_id).first()
    if test_executions:
        return send_error(message_id=TEST_EXECUTION_EXIST)

    new_test_executions = TestExecutions()
    new_test_executions.id = str(uuid.uuid4())
    new_test_executions.jira_id = issue_id
    new_test_executions.cloud_id = cloud_id
    new_test_executions.name = name
    new_test_executions.key = key
    db.session.add(new_test_executions)
    db.session.commit()
    test_exec_data = TestExecutionSchema().dump(new_test_executions)

    return send_result(data=test_exec_data, message_id=CREATE_TEST_EXECUTION)


@api.route('/<test_execution_id>/testruns', methods=['POST'])
@authorization_require()
def get_issue_links(test_execution_id):
    """ This api get information of an enrollment_info.

        Returns:

        Examples::

    """
    # 1. Get keyword from json body
    try:
        params = request.get_json()
        params = GetExecutionValidator().load(params) if params else dict()
        token = get_jwt_identity()
        cloud_id = token.get('cloudId')
    except ValidationError as err:
        logger.error(json.dumps({
            "message": err.messages,
            "data": err.valid_data
        }))
        return send_error(message_id=INVALID_PARAMETERS_ERROR, data=err.messages)

    existed_exec = TestExecutions.query.filter(or_(
        TestExecutions.id == test_execution_id,
        TestExecutions.jira_id == test_execution_id,
        TestExecutions.key == test_execution_id,
        TestExecutions.name == test_execution_id),
        TestExecutions.cloud_id == cloud_id
    ).first()

    if not existed_exec:
        return send_error(data=[], message_id=TEST_EXECUTION_NOT_EXIST)

    fields = params.get('fields_column', None)
    filters = params.get('filters', {})

    statuses = filters.get('statuses', None)
    test_sets = filters.get('test_sets', None)
    issue_ids = filters.get('test_issue_ids', None)

    query = MapTestExec.query

    # add fields
    if fields is not None:
        column_show = []
        fields = fields + ['test_id', 'id', 'tests']
        # for key in fields:
        #     column_show.append(getattr(MapTestExec, key))
        # query = query.with_entities(*column_show)

    # Add filters
    if statuses is not None:
        query = query.join(TestStatus, MapTestExec.status_id == TestStatus.id).filter(TestStatus.value.in_(statuses))

    if test_sets is not None:
        query = query.join(Test, MapTestExec.test_id == Test.id).filter(Test.test_sets.any(TestSets.id.in_(test_sets)))

    if issue_ids is not None:
        query = query.filter(MapTestExec.test_id.in_(issue_ids))

    test_run = query.filter(MapTestExec.exec_id == test_execution_id).all()

    if fields is not None:
        test_run_dump = TestRunSchema(many=True, only=fields).dump(test_run)
    else:
        test_run_dump = TestRunSchema(many=True).dump(test_run)
    return send_result(data=test_run_dump, message="OK")


@api.route('/<test_execution_id>', methods=['POST'])
@authorization_require()
def add_issue_links(test_execution_id):
    """ This api get information of an enrollment_info.

        Returns:

        Examples::

    """
    # 1. Get keyword from json body
    try:
        body = request.get_json()
        params = IssueIDValidator().load(body) if body else dict()
        token = get_jwt_identity()
        cloud_id = token.get('cloudId')
    except ValidationError as err:
        logger.error(json.dumps({
            "message": err.messages,
            "data": err.valid_data
        }))
        return send_error(message_id=INVALID_PARAMETERS_ERROR, data=err.messages)

    issue_ids = params.get('issue_id', [])

    # check test execution exist
    test_executions: TestExecutions = TestExecutions.query.filter(or_(
        TestExecutions.id == test_execution_id,
        TestExecutions.jira_id == test_execution_id,
        TestExecutions.key == test_execution_id,
        TestExecutions.name == test_execution_id),
        TestExecutions.cloud_id == cloud_id).first()
    if not test_executions:
        return send_error(message_id=TEST_EXECUTION_NOT_EXIST)

    # check test exist
    test_issue: Test = Test.query.filter(Test.id.in_(issue_ids)).all()
    if not test_issue:
        return send_error(message_id=TEST_EXECUTION_NOT_EXIST)

    # get index
    map_test_executions: MapTestExec = MapTestExec.query.\
        filter(MapTestExec.exec_id == test_executions.id).first()
    if not map_test_executions:
        index = 1
    else:
        test_executions_index = db.session.query(func.max(MapTestExec.index).label('index')). \
            filter(MapTestExec.exec_id == test_executions.id).first()
        index = test_executions_index.index + 1

    for item in test_issue:
        new_maps_test_executions = MapTestExec()
        new_maps_test_executions.id = str(uuid.uuid4())
        new_maps_test_executions.test_id = item.id
        new_maps_test_executions.exec_id = test_executions.id
        new_maps_test_executions.index = index
        new_maps_test_executions.status_id = DEFAULT_STATUS
        db.session.add(new_maps_test_executions)
        index += 1
    db.session.commit()

    return send_result(message_id=ADD_ISSUE_TO_EXECUTION)


@api.route('/<test_execution_id>', methods=['DELETE'])
@authorization_require()
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
    test_executions: TestExecutions = TestExecutions.query.filter(or_(TestExecutions.id == test_execution_id,
                                                                      TestExecutions.key == test_execution_id)).first()
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


@api.route('/<test_execution_id>', methods=['GET'])
@jwt_required()
def get_issue_by_exec_id(test_execution_id):
    """ This api get information of an enrollment_info.

        Returns:

        Examples::

    """
    token = get_jwt_identity()
    cloud_id = token.get('cloudId')
    params = request.args
    issues_key = params.get("issueKey")
    issues_name = params.get("issueName")

    existed_exec = TestExecutions.query.filter(TestExecutions.jira_id == test_execution_id,
                                               TestExecutions.cloud_id == cloud_id).first()
    if not existed_exec:
        return send_error(data=[], message_id=TEST_EXECUTION_NOT_EXIST)

    test_execution_id = existed_exec.id

    map_test_executions = MapTestExec.query.filter(MapTestExec.exec_id == test_execution_id).all()
    data = TestExecSchema(many=True).dump(map_test_executions)
    return send_result(data=data)