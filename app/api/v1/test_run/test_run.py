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


@api.route("/<test_run_id>/<new_name_status>", methods=["PUT"])
@authorization_require()
def change_status_test_run(test_run_id, new_name_status):
    try:
        token = get_jwt_identity()
        project_id = token.get("projectId")
        cloud_id = token.get("cloudId")
        user_id = token.get("userId")
        query = TestRun.query.filter(TestRun.id == test_run_id).first()
        if not query:
            return send_error(message="Test run is not exists")
        status = TestStatus.query.filter(TestStatus.cloud_id == cloud_id, TestStatus.project_id == project_id,
                                         TestStatus.name == new_name_status).first()
        if not status:
            return send_error(message="status is not exists")
        query.test_status_id = status.id
        db.session.flush()
        db.session.commit()
        return send_result(message="success")
    except Exception as ex:
        db.session.rollback()
        return send_error(message=str(ex))


# call change status mới call set time
@api.route("/<test_run_id>/set_time", methods=["PUT"])
@authorization_require()
def set_time_test_run(test_run_id):
    try:
        token = get_jwt_identity()
        project_id = token.get("projectId")
        cloud_id = token.get("cloudId")
        user_id = token.get("userId")
        edited = request.args.get('edited', False, type=bool)
        reg = request.get_json()
        start_time = reg.get("start_time", 0)
        if not isinstance(start_time, int):
            start_time = 0
        query = TestRun.query.filter(TestRun.id == test_run_id).first()
        if start_time != 0 and edited:
            if query.end_date == 0:
                if query.status.name in ["PASSED", "FAILED"]:
                    query.start_date = start_time
                    query.end_date = get_timestamp_now()
                    db.session.flush()
                    if start_time > query.end_date:
                        return send_error(message="Test run cannot start after finished date", is_dynamic=True)
                else:
                    query.start_date = start_time
                    query.end_date = 0
                    db.session.flush()
            else:
                if query.status.name in ["PASSED", "FAILED"]:
                    if start_time > query.end_date:
                        return send_error(message="Test run cannot start after finished date", is_dynamic=True)
                    query.start_date = start_time
                    db.session.flush()
                else:
                    query.start_date = start_time
                    query.end_date = 0
                    db.session.flush()
        else:
            if query.start_date == 0 and query.end_date == 0:
                if query.status.name in ["PASSED", "FAILED"]:
                    query.start_date = get_timestamp_now()
                    query.end_date = TestRun.start_date
                    db.session.flush()
                else:
                    query.start_date = get_timestamp_now()
                    db.session.flush()
            elif query.start_date != 0 and query.end_date == 0 and (query.status.name in ["PASSED", "FAILED"]):
                query.end_date = get_timestamp_now()
                db.session.flush()
            elif query.start_date == 0 and query.end_date != 0:
                if query.status.name not in ["PASSED", "FAILED"]:
                    query.end_date = get_timestamp_now()
                    query.end_date = 0
                    db.session.flush()
                else:
                    query.end_date = get_timestamp_now()
                    query.end_date = TestRun.start_date
                    db.session.flush()
            elif query.start_date != 0 and query.end_date != 0 and (query.status.name not in ["PASSED", "FAILED"]):
                query.end_date = 0
                db.session.flush()
        db.session.commit()
        return send_result(message="success")
    except Exception as ex:
        db.session.rollback()
        return send_error(message="failed")
