import json
import uuid
from operator import or_

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, create_access_token
from benedict import benedict

from app.api.v1.setting.setting_validator import UpdateMiscellaneousRequest
from app.api.v1.test_run.schema import TestRunSchema, CombineSchema
from app.gateway import authorization_require
from app.models import TestStep, TestCase, TestType, db, TestField, Setting, TestRun, TestExecution, \
    TestCasesTestExecutions, TestStatus
from app.utils import send_result, send_error, data_preprocessing, get_timestamp_now
from app.validator import CreateTestValidator, SettingSchema
from app.parser import TestFieldSchema, TestStepSchema

api = Blueprint('test_run', __name__)


@api.route("/search", methods=["POST"])
@authorization_require()
def search_test_run():
    try:
        token = get_jwt_identity()
        cloud_id = token.get('cloudId')
        project_id = token.get('projectId')

        body_request = request.get_json()

        test_case_issue_id = body_request.get('test_case_issue_id', None)
        test_execution_issue_id = body_request.get('test_execution_issue_id', None)
        test_status_ids = body_request.get('test_status_id', None)

        query = db.session.query(TestRun). \
            join(TestCase, TestCase.id == TestRun.test_case_id). \
            join(TestExecution, TestExecution.id == TestRun.test_execution_id). \
            join(TestStatus, TestStatus.id == TestRun.test_status_id)

        if test_case_issue_id:
            query = query.filter(TestCase.issue_id == test_case_issue_id, TestCase.cloud_id == cloud_id,
                                 TestCase.project_id == project_id)

        if test_execution_issue_id:
            query = query.filter(TestExecution.issue_id == test_execution_issue_id)

        if test_status_ids:
            query = query.filter(TestRun.test_status_id.in_(test_status_ids))

        test_runs = query.all()

        return send_result(data=CombineSchema(many=True).dump(test_runs), message="OK")

    except Exception as ex:
        return send_result(data='', message="OK")


@api.route("/<issue_id>/test_run", methods=["GET"])
@authorization_require()
def get_test_run(issue_id):
    try:
        token = get_jwt_identity()
        cloud_id = token.get('cloudId')
        project_id = token.get('projectId')

        # Get test case
        test_case = TestCase.query.filter(TestCase.cloud_id == cloud_id, TestCase.issue_id == issue_id,
                                          TestCase.project_id == project_id).first()

        # test_executions = test_case.test_execution.all()
        # test_execution_ids = [item.id for item in test_executions]

        test_runs = db.session.query(TestRun) \
            .join(TestExecution, TestExecution.id == TestRun.test_execution_id). \
            join(TestCase, TestExecution.test_cases). \
            filter(TestCase.issue_id == test_case.issue_id).all()

        return send_result(data='Done', message="OK")

    except Exception as ex:
        print(ex)


@api.route("/<test_issue_id>/test_execution/<test_execution_issue_id>", methods=["POST"])
@authorization_require()
def add_test_execution(test_issue_id, test_execution_issue_id):
    try:
        token = get_jwt_identity()
        cloud_id = token.get('cloudId')
        project_id = token.get('projectId')

        """
            Get test case, create new if not exist
        """
        test_case = TestCase.query.filter(TestCase.issue_id == test_issue_id,
                                          TestCase.cloud_id == cloud_id,
                                          TestExecution.project_id == project_id).first()
        if test_case is None:
            test_case = TestCase(
                id=str(uuid.uuid4()),
                issue_id=test_issue_id,
                project_id=project_id,
                cloud_id=cloud_id,
                created_date=get_timestamp_now()
            )
            db.session.add(test_case)
            db.session.flush()

        """
           Get test execution, create new if not exist
        """
        test_execution = TestExecution.query.filter(TestExecution.issue_id == test_execution_issue_id,
                                                    TestExecution.cloud_id == cloud_id,
                                                    TestExecution.project_id == project_id).first()
        if test_execution is None:
            test_execution = TestExecution(
                id=str(uuid.uuid4()),
                issue_id=test_execution_issue_id,
                project_id=project_id,
                cloud_id=cloud_id,
                created_date=get_timestamp_now()
            )
            db.session.add(test_execution)
            db.session.flush()

        """
        Generate test run
        """
        test_run = TestRun.query.filter(TestRun.test_execution_id == test_execution.id,
                                        TestRun.test_case_id == test_case.id,
                                        ).first()
        if test_run is None:
            default_status = TestStatus.query.filter(TestStatus.name == 'TODO').first()

            test_run = TestRun(
                id=str(uuid.uuid4()),
                project_id=project_id, cloud_id=cloud_id, test_case_id=test_case.id,
                test_execution_id=test_execution.id, activities='{}', test_steps='{}', findings='{}',
                meta_data='{}',
                issue_id=test_case.issue_id,
                created_date=get_timestamp_now(),
                test_status_id=default_status.id
            )
            db.session.add(test_run)
            db.session.flush()

        db.session.commit()
        return send_result(data='', message='Add test execution to test case successfully', show=True)
    except Exception as ex:
        db.session.rollback()


@api.route("/<test_case_id>/test_run_id", methods=["GET"])
@authorization_require()
def get_test_run_by_id(test_case_id):
    try:
        token = get_jwt_identity()

        cloud_id = token.get('cloudId')
        issue_id = 100002
        project_id = 10003
        test_run = TestRun.query.first()
        status = test_run.status
        return send_result(data='Done', message="OK")

    except Exception as ex:
        print(ex)
