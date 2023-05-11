import json
import uuid
from operator import or_

from flask import Blueprint, request
from flask_jwt_extended import jwt_required, get_jwt_identity, create_access_token
from benedict import benedict
from sqlalchemy import desc, asc
from sqlalchemy.orm import joinedload
from app.api.v1.history_test import save_history_test_execution
from app.api.v1.test_run.schema import TestRunSchema
from app.gateway import authorization_require
from app.models import TestStep, TestCase, TestType, db, TestField, Setting, TestRun, TestExecution, \
    TestCasesTestExecutions, TestStatus, TestStepDetail, TestExecutionsTestEnvironments
from app.parser import TestStepSchema
from app.utils import send_result, send_error, data_preprocessing, get_timestamp_now
from app.validator import TestExecutionSchema, TestStepTestRunSchema

api = Blueprint('test_execution', __name__)


@api.route("/<issue_id>/test_run", methods=["GET"])
@authorization_require()
def get_test_run_from_test_execution(issue_id):
    token = get_jwt_identity()
    cloud_id = token.get('cloudId')
    project_id = token.get('projectId')
    page = request.args.get('page', 1, type=int)
    page_size = request.args.get('page_size', 10, type=int)
    order_by = request.args.get('order_by', '', type=str)
    order = request.args.get('order', 'asc', type=str)
    if order_by == '':
        order_by = "created_date"
    else:
        if order_by not in ["issue_id", "issue_key", "created_date"]:
            return send_error("Not a valid")
    column_sorted = getattr(TestRun, order_by)
    test_execution = TestExecution.query.filter(TestExecution.cloud_id == cloud_id, TestExecution.issue_id == issue_id,
                                                TestExecution.project_id == project_id).first()
    if test_execution is None:
        return send_error("Not found test execution")
    query = TestRun.query.filter(TestRun.cloud_id == cloud_id, TestRun.project_id == project_id,
                                 TestRun.test_execution_id == test_execution.id)
    query = query.order_by(desc(column_sorted)) if order == "desc" else query.order_by(asc(column_sorted))
    test_runs = query.paginate(page=page, per_page=page_size, error_out=False).items
    total = query.count()
    extra = 1 if (total % page_size) else 0
    total_pages = int(total / page_size) + extra
    try:
        results = {
            "test_cases": TestRunSchema(many=True).dump(test_runs),
            "total": total,
            "total_pages": total_pages
        }
        return send_result(data=results)

    except Exception as ex:
        return send_error(message=str(ex))


@api.route("/<issue_id>/<test_issue_id>/test_run", methods=["GET"])
@authorization_require()
def get_test_step_in_test_run(issue_id, test_issue_id):
    token = get_jwt_identity()
    cloud_id = token.get('cloudId')
    project_id = token.get('project_Id')
    test_execution = TestExecution.query.filter(TestExecution.cloud_id == cloud_id, TestExecution.issue_id == issue_id,
                                                TestExecution.project_id == project_id).first()
    if test_execution is None:
        return send_error("Not found test execution")
    test_case = TestCase.query.filter(TestCase.cloud_id == cloud_id, TestCase.issue_id == test_issue_id,
                                      TestCase.project_id == project_id).first()
    if test_case is None:
        return send_error("Not found test case")
    test_run = TestRun.query.filter(TestRun.cloud_id == cloud_id, TestRun.project_id == project_id,
                                    TestRun.test_execution_id == test_execution.id,
                                    TestRun.test_case_id == test_case.id).first()
    if test_run is None:
        return send_error("Not found test run")
    test_steps = db.session.query(TestStep).filter(TestStep.project_id == project_id, TestStep.cloud_id == cloud_id,
                                                   TestStep.test_case_id == test_case.id).order_by(asc(TestStep.index))\
        .all()
    result = []
    for test_step in test_steps:
        if test_step.test_case_id_reference:
            test_step_reference = db.session.query(TestStep.id, TestStep.action, TestStep.attachments, TestStep.result,
                                                   TestStep.cloud_id, TestStep.project_id, TestStep.created_date,
                                                   TestStep.test_case_id, TestStep.index, TestStep.project_key,
                                                   TestStep.data, TestCase.issue_key, TestStep.custom_fields)\
                .join(TestCase, TestCase.id == TestStep.test_case_id)\
                .filter(TestStep.project_id == project_id, TestStep.cloud_id == cloud_id,
                        TestStep.test_case_id == test_step.test_case_id_reference).all()

            data = TestStepTestRunSchema(many=True).dump(test_step_reference)
        else:
            data = [TestStepTestRunSchema().dump(test_step)]
        result = result + data
    try:
        return send_result(data=result)
    except Exception as ex:
        return send_error(message=str(ex))


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
                    issue_key=test_case.issue_key,
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
