import json
import uuid
from operator import or_

from flask import Blueprint, request
from flask_jwt_extended import jwt_required, get_jwt_identity, create_access_token
from benedict import benedict
from sqlalchemy.orm import joinedload
from app.api.v1.history_test import save_history_test_execution
from app.api.v1.test_run.schema import TestRunSchema
from app.gateway import authorization_require
from app.models import TestStep, TestCase, TestType, db, TestField, Setting, TestRun, TestExecution, \
    TestCasesTestExecutions, TestStatus, TestStepDetail, TestExecutionsTestEnvironments
from app.utils import send_result, send_error, data_preprocessing, get_timestamp_now
from app.validator import TestExecutionSchema

api = Blueprint('test_execution', __name__)


@api.route("/<test_case_id>", methods=["GET"])
@authorization_require()
def get_test_case(test_case_id):
    token = get_jwt_identity()
    cloud_id = token.get('cloudId')
    test_case = TestCase.get_by_id(test_case_id)
    return send_result(data=json.dumps(test_case), message="OK")


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

        return send_result(data=TestRunSchema(many=True).dump(test_runs), message="OK")

    except Exception as ex:
        print(ex)


@api.route("/<test_execution_issue_id>", methods=["POST"])
@authorization_require()
def add_test_to_test_execution(test_execution_issue_id):
    try:
        body_request = request.get_json()
        token = get_jwt_identity()
        user_id = token.get('userId')
        cloud_id = token.get('cloudId')
        project_id = token.get('projectId')

        test_cases = body_request.get('test_cases')
        test_execution_issue_key = body_request.get('test_execution_issue_key')

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
                issue_key=test_execution_issue_key,
                project_id=project_id,
                cloud_id=cloud_id,
                created_date=get_timestamp_now()
            )
            db.session.add(test_execution)
            db.session.flush()
        test_case_ids = []
        for test_case_issue_id, test_case_issue_key in test_cases.items():
            """
               Get test execution, create new if not exist
            """
            test_case = TestCase.query.filter(TestCase.issue_id == test_case_issue_id,
                                              TestCase.cloud_id == cloud_id,
                                              TestCase.project_id == project_id).first()
            if test_case is None:
                test_case = TestCase(
                    id=str(uuid.uuid4()),
                    issue_id=test_case_issue_id,
                    issue_key=test_case_issue_key,
                    project_id=project_id,
                    cloud_id=cloud_id,
                    created_date=get_timestamp_now()
                )
                db.session.add(test_case)
                db.session.flush()
            exist_test_case = TestCasesTestExecutions\
                .query.filter(TestCasesTestExecutions.test_case_id == test_case.id,
                              TestCasesTestExecutions.test_execution_id == test_execution.id).first()
            if exist_test_case is None:
                """
                  Add this test case to test execution
                """
                test_case_test_execution = TestCasesTestExecutions(
                    test_case_id=test_case.id,
                    test_execution_id=test_execution.id,
                )
                db.session.add(test_case_test_execution)
                db.session.flush()
                test_case_ids.append(test_case.id)

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
            else:
                return send_error(message='Test Executions were already associated with the Test',
                                  status=200, show=False)
        db.session.commit()
        save_history_test_execution(test_execution.id, user_id, 1, 3, test_case_ids)
        return send_result(message=f'Add {len(test_case_ids)} test case to execution case successfully')
    except Exception as ex:
        db.session.rollback()
        return send_error(message=str(ex))


@api.route("/<test_execution_id>", methods=["DELETE"])
@authorization_require()
def remove_test_to_test_execution(test_execution_id):
    try:
        token = get_jwt_identity()
        user_id = token.get('userId')
        body_request = request.get_json()
        cloud_id = token.get('cloudId')
        project_id = token.get('projectId')
        test_case_ids = body_request.get('test_case_ids')
        # xóa test run
        TestRun.query.filter(TestRun.test_execution_id == test_execution_id)\
            .filter(TestRun.test_case_id.in_(test_case_ids))\
            .delete()
        db.session.flush()
        # xóa test_cases_test_executions
        TestCasesTestExecutions.query.filter(
            TestCasesTestExecutions.test_execution_id == test_execution_id) \
            .filter(TestCasesTestExecutions.test_case_id.in_(test_case_ids)).delete()
        db.session.flush()
        db.session.commit()
        save_history_test_execution(test_execution_id, user_id, 2, 3, test_case_ids)
        return send_result(message=f'Remove {len(test_case_ids)} test to test case execution successfully')
    except Exception as ex:
        db.session.rollback()
        return send_error(message=str(ex))


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


@api.route("/test", methods=["GET"])
@authorization_require()
def test():
    try:
        test = TestCase.query.options(
            joinedload(TestCase.test_steps, innerjoin=True).joinedload(TestStep.test_details, innerjoin=True)).filter(
            TestStepDetail.id == '1').all()
        return send_result(data='Done', message="OK")

    except Exception as ex:
        print(ex)


@api.route("/", methods=["POST"])
@authorization_require()
def create_test_case():
    try:
        token = get_jwt_identity()

        cloud_id = token.get('cloudId')
        issue_id = token.get('issueId')
        project_id = token.get('projectId')

        test_execution = TestExecution(
            id=str(uuid.uuid4()),
            issue_id=issue_id,
            project_id=project_id,
            cloud_id=cloud_id,
            created_date=get_timestamp_now()
        )
        db.session.add(test_execution)
        db.session.flush()

        return send_result(data=TestExecutionSchema().dump(test_execution))

    except Exception as ex:
        print(ex)
