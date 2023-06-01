import json
import os
import shutil
import uuid
from operator import or_

from flask import Blueprint, request
from flask_jwt_extended import jwt_required, get_jwt_identity, create_access_token
from benedict import benedict
from sqlalchemy import desc, asc
from sqlalchemy.orm import joinedload
from app.api.v1.history_test import save_history_test_execution
from app.api.v1.test_run.schema import TestRunSchema
from app.enums import FILE_PATH
from app.gateway import authorization_require
from app.models import TestStep, TestCase, TestType, db, TestField, Setting, TestRun, TestExecution, \
    TestCasesTestExecutions, TestStatus, TestStepDetail, TestExecutionsTestEnvironments, TestEvidence
from app.parser import TestStepSchema
from app.utils import send_result, send_error, data_preprocessing, get_timestamp_now
from app.validator import TestExecutionSchema, TestStepTestRunSchema, TestExecutionTestRunSchema

api = Blueprint('test_execution', __name__)


@api.route("/<issue_id>/test_case", methods=["GET"])
@authorization_require()
def get_test_case_from_test_execution(issue_id):
    token = get_jwt_identity()
    cloud_id = token.get('cloudId')
    project_id = token.get('projectId')
    # Get search params
    page = request.args.get('page', 1, type=int)
    page_size = request.args.get('page_size', 10, type=int)
    order_by = request.args.get('order_by', "", type=str)
    order = request.args.get('order', 'asc')
    test_execution = TestExecution.query.filter(TestExecution.cloud_id == cloud_id, TestExecution.issue_id == issue_id,
                                                TestExecution.project_id == project_id).first()
    if order_by == "":
        order_by = "created_date"
    if order == "":
        order = "asc"
    if test_execution is None:
        return send_error("Not found test execution")
    # sort
    query = db.session.query(TestCase.id, TestCase.issue_id, TestCase.issue_key,
                             TestCase.project_id, TestCase.cloud_id,
                             TestCase.created_date.label('test_case_created_date'),
                             TestRun.id.label('test_run_id'), TestRun.test_status_id, TestRun.is_updated,
                             TestRun.start_date, TestRun.end_date, TestRun.issue_id.label('test_run_issue_id'),
                             TestRun.issue_key.label('test_run_issue_key'), TestRun.created_date)\
        .join(TestCasesTestExecutions, TestCasesTestExecutions.test_case_id == TestCase.id) \
        .join(TestRun, (TestCasesTestExecutions.test_case_id == TestRun.test_case_id)
              & (TestCasesTestExecutions.test_execution_id == TestRun.test_execution_id))\
        .filter(TestCasesTestExecutions.test_execution_id == test_execution.id)
    if order_by == "created_date":
        column_sorted = getattr(TestRun, order_by)
    else:
        column_sorted = getattr(TestCase, order_by)
    query = query.order_by(desc(column_sorted)) if order == "desc" else query.order_by(asc(column_sorted))
    test_cases = query.paginate(page=page, per_page=page_size, error_out=False).items
    total = query.count()
    extra = 1 if (total % page_size) else 0
    total_pages = int(total / page_size) + extra
    try:
        results = {
            "test_cases": TestExecutionTestRunSchema(many=True).dump(test_cases),
            "total": total,
            "total_pages": total_pages
        }
        return send_result(data=results)
    except Exception as ex:
        return send_error(message=str(ex), data={})


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
                default_status = TestStatus.query.filter(TestStatus.cloud_id == cloud_id,
                                                         TestStatus.project_id == project_id,
                                                         TestStatus.name == 'TODO').first()
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
                # Tạo test details
                add_test_step_id_by_test_case_id_2(cloud_id, project_id, test_case.id, test_run.id, default_status.id,'')
            else:
                return send_error(message='Test Executions were already associated with the Test',
                                  status=200, show=False)
        db.session.commit()
        save_history_test_execution(test_execution.id, user_id, 1, 3, test_case_ids)
        return send_result(message=f'Add {len(test_case_ids)} test case to execution case successfully')
    except Exception as ex:
        db.session.rollback()
        return send_error(message=str(ex))


def add_test_step_id_by_test_case_id(cloud_id: str, project_id: str, test_case_id: str,
                                     test_run_id, status_id, link: str):
    step_calls = TestStep.query.filter(TestStep.cloud_id == cloud_id, TestStep.project_id == project_id,
                                       TestStep.test_case_id == test_case_id) \
        .order_by(asc(TestStep.index)).all()
    for step in step_calls:
        new_link = link + step.id + "/"
        if step.test_case_id_reference is None:
            test_step_detail = TestStepDetail(
                id=str(uuid.uuid4()),
                test_step_id=step.id,
                status_id=status_id,
                test_run_id=test_run_id,
                created_date=get_timestamp_now(),
                link=new_link
            )
            db.session.add(test_step_detail)
            db.session.flush()
        else:
            add_test_step_id_by_test_case_id(cloud_id, project_id, step.test_case_id_reference, test_run_id, status_id,
                                             new_link)


def add_test_step_id_by_test_case_id_2(cloud_id: str, project_id: str, test_case_id: str,
                                       test_run_id, status_id, link: str):
    stack = [(test_case_id, link)]
    while stack:
        curr_id, current_link = stack.pop()
        step_calls = TestStep.query.filter(TestStep.cloud_id == cloud_id, TestStep.project_id == project_id,
                                           TestStep.test_case_id == curr_id) \
            .order_by(desc(TestStep.index)).all()
        for step in step_calls:
            new_link = current_link + step.id + "/"
            if step.test_case_id_reference is None:
                test_step_detail = TestStepDetail(
                    id=str(uuid.uuid4()),
                    test_step_id=step.id,
                    status_id=status_id,
                    test_run_id=test_run_id,
                    created_date=get_timestamp_now(),
                    link=new_link
                )
                db.session.add(test_step_detail)
                db.session.flush()
            else:
                stack.append((step.test_case_id_reference, new_link))


@api.route("/<test_execution_issue_id>", methods=["DELETE"])
@authorization_require()
def remove_test_to_test_execution(test_execution_issue_id):
    try:
        token = get_jwt_identity()
        user_id = token.get('userId')
        body_request = request.get_json()
        cloud_id = token.get('cloudId')
        project_id = token.get('projectId')
        test_case_issue_ids = body_request.get('test_case_issue_ids')
        test_cases = TestCase.query.filter(TestCase.cloud_id == cloud_id, TestCase.project_id == project_id,
                                           TestCase.issue_id.in_(test_case_issue_ids)).all()
        test_case_ids = [test_case.id for test_case in test_cases]
        test_execution = TestExecution.query.filter(TestExecution.project_id == project_id,
                                                    TestExecution.cloud_id == cloud_id,
                                                    TestExecution.issue_id == test_execution_issue_id).first()

        test_runs = TestRun.query.filter(TestRun.test_execution_id == test_execution.id)\
            .filter(TestRun.test_case_id.in_(test_case_ids)).all()
        test_run_id = [test_run.id for test_run in test_runs]

        for id_test_run in test_run_id:
            folder_path = "{}/{}".format("test-run", id_test_run)
            if os.path.isdir(FILE_PATH + folder_path):
                try:
                    shutil.rmtree(FILE_PATH + folder_path)
                except Exception as ex:
                    return send_error(message=str(ex))
        TestEvidence.query.filter(TestEvidence.test_run_id.in_(test_run_id)).delete()
        db.session.flush()

        TestStepDetail.query.filter(TestStepDetail.test_run_id.in_(test_run_id)).delete()
        db.session.flush()

        TestRun.query.filter(TestRun.test_execution_id == test_execution.id) \
            .filter(TestRun.test_case_id.in_(test_case_ids)).delete()
        db.session.flush()
        # xóa test_cases_test_executions
        TestCasesTestExecutions.query.filter(
            TestCasesTestExecutions.test_execution_id == test_execution.id) \
            .filter(TestCasesTestExecutions.test_case_id.in_(test_case_ids)).delete()
        db.session.flush()
        db.session.commit()
        save_history_test_execution(test_execution.id, user_id, 2, 3, test_case_ids)
        return send_result(message=f'Remove {len(test_case_ids)} test to test case execution successfully')
    except Exception as ex:
        db.session.rollback()
        return send_error(message=str(ex))


@api.route("/", methods=["POST"])
@authorization_require()
def create_test_execution():
    try:
        token = get_jwt_identity()

        cloud_id = token.get('cloudId')
        issue_id = token.get('issueId')
        issue_key = token.get('issueKey')
        project_id = token.get('projectId')

        test_execution = TestExecution(
            id=str(uuid.uuid4()),
            issue_id=issue_id,
            project_id=project_id,
            issue_key=issue_key,
            cloud_id=cloud_id,
            created_date=get_timestamp_now()
        )
        db.session.add(test_execution)
        db.session.flush()

        return send_result(data=TestExecutionSchema().dump(test_execution))

    except Exception as ex:
        print(ex)
