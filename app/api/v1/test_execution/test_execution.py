import json
import os
import shutil
import uuid
from operator import or_
from app.extensions import logger
from flask import Blueprint, request
from flask_jwt_extended import jwt_required, get_jwt_identity, create_access_token
from benedict import benedict
from marshmallow import ValidationError
from sqlalchemy import desc, asc
from sqlalchemy.orm import joinedload
from app.api.v1.history_test import save_history_test_execution
from app.api.v1.test_run.schema import TestRunSchema
from app.api.v1.test_type.test_type import get_test_type_default
from app.enums import FILE_PATH
from app.gateway import authorization_require
from app.models import TestStep, TestCase, TestType, db, TestField, Setting, TestRun, TestExecution, \
    TestCasesTestExecutions, TestStatus, TestStepDetail, TestExecutionsTestEnvironments, TestEvidence, TestSet, \
    TestCasesTestSets
from app.parser import TestStepSchema
from app.utils import send_result, send_error, data_preprocessing, get_timestamp_now
from app.validator import TestExecutionSchema, TestStepTestRunSchema, TestExecutionTestRunSchema, TestCaseValidator

api = Blueprint('test_execution', __name__)


@api.route("/get-test-case", methods=["POST"])
@authorization_require()
def get_test_case_from_test_execution():
    try:
        token = get_jwt_identity()
        cloud_id = token.get('cloudId')
        project_id = token.get('projectId')
        issue_key = token.get('issueKey')
        issue_id = token.get('issueId')
        search_other = request.args.get('search_other', False, type=bool)
        body_request = request.get_json()
        tests_type = body_request.get("tests_type", [])
        test_set_issue_ids = body_request.get("test_set_issue_ids", [])
        test_status_ids = body_request.get("test_status_ids", [])
        test_execution = TestExecution.query.filter(TestExecution.cloud_id == cloud_id,
                                                    TestExecution.issue_id == issue_id,
                                                    TestExecution.project_id == project_id).first()
        if test_execution is None:
            test_execution = TestExecution(
                id=str(uuid.uuid4()),
                issue_id=issue_id,
                issue_key=issue_key,
                project_id=project_id,
                cloud_id=cloud_id,
                created_date=get_timestamp_now()
            )
            db.session.add(test_execution)
            db.session.flush()
        # sort
        query = db.session.query(TestCase.id, TestCase.issue_id, TestCase.issue_key,
                                 TestCase.project_id, TestCase.cloud_id,
                                 TestCase.created_date.label('test_case_created_date'),
                                 TestRun.id.label('test_run_id'), TestRun.test_status_id, TestRun.is_updated,
                                 TestRun.start_date, TestRun.end_date, TestRun.issue_id.label('test_run_issue_id'),
                                 TestRun.issue_key.label('test_run_issue_key'), TestRun.created_date,
                                 TestCasesTestExecutions.index, TestCasesTestExecutions.is_archived) \
            .join(TestCasesTestExecutions, TestCasesTestExecutions.test_case_id == TestCase.id) \
            .join(TestRun, (TestCasesTestExecutions.test_case_id == TestRun.test_case_id)
                  & (TestCasesTestExecutions.test_execution_id == TestRun.test_execution_id)) \
            .filter(TestCasesTestExecutions.test_execution_id == test_execution.id)
        if len(tests_type) > 0:
            tests_type = db.session.query(TestType.id).filter(TestType.name.in_(tests_type),
                                                              TestType.cloud_id == cloud_id,
                                                              TestType.project_id == project_id).subquery()

            query = query.filter(TestCase.test_type_id.in_(tests_type))
        if len(test_set_issue_ids) > 0:
            test_sets = TestSet.query.filter(TestSet.project_id == project_id, TestSet.cloud_id == cloud_id,
                                             TestSet.issue_id.in_(test_set_issue_ids)).all()
            test_set_ids = [test_set.id for test_set in test_sets]
            query = query.join(TestCasesTestSets, TestCase.id == TestCasesTestSets.test_case_id) \
                .filter(TestCasesTestSets.test_set_id.in_(test_set_ids))
        if len(test_status_ids) > 0:
            query = query.filter(TestRun.test_status_id.in_(test_status_ids))
        if search_other:
            query = query.filter(TestCasesTestExecutions.is_archived != 0)\
                .order_by(asc(TestCasesTestExecutions.is_archived)).all()
        else:
            query = query.filter(TestCasesTestExecutions.is_archived == 0)\
                .order_by(asc(TestCasesTestExecutions.index)).all()
        data = TestExecutionTestRunSchema(many=True).dump(query)
        return send_result(data=data)
    except Exception as ex:
        return send_error(message=str(ex), data={})


@api.route('/add', methods=["POST"])
@authorization_require()
def add_test_to_test_execution():
    try:
        body_request = request.get_json()
        token = get_jwt_identity()
        user_id = token.get('userId')
        cloud_id = token.get('cloudId')
        project_id = token.get('projectId')
        test_execution_issue_key = token.get('issueKey')
        test_execution_issue_id = token.get('issueId')
        test_cases = body_request.get('test_cases', {})
        if len(test_cases) == 0:
            return send_error(message="There are no Test Cases selected")
        """
            Get test execution, create new if not exist
        """
        test_execution = TestExecution.query.filter(TestExecution.issue_id == test_execution_issue_id,
                                                    TestExecution.cloud_id == cloud_id,
                                                    TestExecution.project_id == project_id).first()
        default_status = TestStatus.query.filter(TestStatus.cloud_id == cloud_id,
                                                 TestStatus.project_id == project_id,
                                                 TestStatus.name == 'TODO').first()
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
        test_type_id = get_test_type_default(cloud_id, project_id)
        i = 1
        index_max = TestCasesTestExecutions.query.filter(TestCasesTestExecutions.test_execution_id == test_execution.id,
                                                         TestCasesTestExecutions.is_archived == 0).count()
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
                    created_date=get_timestamp_now(),
                    test_type_id=test_type_id
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
                    index=index_max+i
                )
                db.session.add(test_case_test_execution)
                db.session.flush()
                i += 1
                test_case_ids.append(test_case.id)

            """
            Generate test run
            """
            test_run = TestRun.query.filter(TestRun.test_execution_id == test_execution.id,
                                            TestRun.test_case_id == test_case.id,
                                            ).first()
            if test_run is None:

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
                add_test_step_id_by_test_case_id(cloud_id, project_id, test_case.id, test_run.id, default_status.id, '')
            else:
                return send_error(message='Test Executions were already associated with the Test',
                                  status=200, show=False)
        if len(test_case_ids) == 0:
            return send_error(message="No new tests were added to this Test Execution", show=True)
        save_history_test_execution(test_execution.id, user_id, 1, 3, test_case_ids, [])
        db.session.commit()
        return send_result(message=f'Add {len(test_case_ids)} test case to execution case successfully', show=True)
    except Exception as ex:
        db.session.rollback()
        return send_error(message=str(ex))


def add_test_step_id_by_test_case_id(cloud_id: str, project_id: str, test_case_id: str,
                                     test_run_id, status_id, link: str):
    stack = [(test_case_id, link)]
    list_test_step_detail = []
    while stack:
        curr_id, current_link = stack.pop()
        step_calls = TestStep.query.filter(TestStep.cloud_id == cloud_id, TestStep.project_id == project_id,
                                           TestStep.test_case_id == curr_id) \
            .order_by(asc(TestStep.index)).all()
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
                list_test_step_detail.append(test_step_detail)
            else:
                stack.append((step.test_case_id_reference, new_link))
    db.session.bulk_save_objects(list_test_step_detail)


@api.route('/remove', methods=["DELETE"])
@authorization_require()
def remove_test_to_test_execution():
    try:
        token = get_jwt_identity()
        user_id = token.get('userId')
        body_request = request.get_json()
        cloud_id = token.get('cloudId')
        project_id = token.get('projectId')
        test_execution_issue_id = token.get('issueId')
        archived = request.args.get('archived', False, type=bool)
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
        if archived:
            # xóa test_cases_test_executions
            TestCasesTestExecutions.query.filter(
                TestCasesTestExecutions.test_execution_id == test_execution.id) \
                .filter(TestCasesTestExecutions.test_case_id.in_(test_case_ids)).delete()
            db.session.flush()
            # Lấy ra tất cả các record not in archived trong bảng
            query_all = TestCasesTestExecutions.query.filter(
                TestCasesTestExecutions.test_execution_id == test_execution.id) \
                .filter(TestCasesTestExecutions.is_archived != 0) \
                .order_by(TestCasesTestExecutions.is_archived.asc())
            # Cập nhật lại giá trị của cột "archived"
            for i, query in enumerate(query_all):
                query.is_archived = i + 1
                db.session.flush()
        else:
            # xóa test_cases_test_executions
            TestCasesTestExecutions.query.filter(
                TestCasesTestExecutions.test_execution_id == test_execution.id) \
                .filter(TestCasesTestExecutions.test_case_id.in_(test_case_ids)).delete()
            db.session.flush()
            # Lấy ra tất cả các record not in archived trong bảng
            query_all = TestCasesTestExecutions.query.filter(TestCasesTestExecutions.test_execution_id == test_execution.id)\
                .filter(TestCasesTestExecutions.is_archived == 0)\
                .order_by(TestCasesTestExecutions.index.asc())
            # Cập nhật lại giá trị của cột "index"
            for i, query in enumerate(query_all):
                query.index = i + 1
                db.session.flush()
        save_history_test_execution(test_execution.id, user_id, 2, 3, test_case_ids, [])
        db.session.commit()
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
        project_id = token.get('projectId')
        body_request = request.get_json()
        test_execution = body_request.get('test_execution')
        for issue_id, issue_key in test_execution.items():
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
        db.session.commit()
        return send_result(message="done")
    except Exception as ex:
        print(ex)


@api.route("/test-case", methods=["PUT"])
@authorization_require()
def change_rank_test_case_in_test_execution():
    try:
        token = get_jwt_identity()
        user_id = token.get("userId")
        cloud_id = token.get("cloudId")
        project_id = token.get("projectId")
        issue_id = token.get('issueId')
        json_req = request.get_json()
        index_drag = json_req['index_drag']
        index_drop = json_req['index_drop']
        test_execution = TestExecution.query.filter(TestExecution.cloud_id == cloud_id,
                                                    TestExecution.project_id == project_id,
                                                    TestExecution.issue_id == issue_id).first()
        # lấy index_drag
        index_max = db.session.query(TestCasesTestExecutions)\
            .filter(TestCasesTestExecutions.test_execution_id == test_execution.id).count()
        query = TestCasesTestExecutions.query.filter(TestCasesTestExecutions.test_execution_id == test_execution.id) \
            .filter(TestCasesTestExecutions.index == index_drag).first()
        if index_drag > index_drop:
            if index_drop < 1:
                return send_error(message=f'Must be a value between 1 and {index_max}')
            TestCasesTestExecutions.query.filter(TestCasesTestExecutions.test_execution_id == test_execution.id) \
                .filter(TestCasesTestExecutions.index > index_drop - 1).filter(TestCasesTestExecutions.index < index_drag) \
                .update(dict(index=TestCasesTestExecutions.index + 1))
            query.index = index_drop
            db.session.flush()
        else:
            if index_drop > index_max:
                return send_error(message=f'Must be a value between 1 and {index_max}')
            TestCasesTestExecutions.query.filter(TestCasesTestExecutions.test_execution_id == test_execution.id) \
                .filter(TestCasesTestExecutions.index > index_drag).filter(TestCasesTestExecutions.index < index_drop + 1) \
                .update(dict(index=TestCasesTestExecutions.index - 1))
            query.index = index_drop
            db.session.flush()
        # save history
        save_history_test_execution(test_execution.id, user_id, 3, 3, [query.test_case_id], [index_drag, index_drop])
        db.session.commit()
        return send_result(message='Update successfully')
    except Exception as ex:
        db.session.rollback()
        return send_error(message=str(ex))


@api.route("/archive", methods=["PUT"])
@authorization_require()
def archive_test_case_in_test_execution():
    try:
        token = get_jwt_identity()
        user_id = token.get("userId")
        cloud_id = token.get("cloudId")
        project_id = token.get("projectId")
        issue_key = token.get("issueKey")
        issue_id = token.get("issueId")
        try:
            body = request.get_json()
            params = TestCaseValidator().load(body) if body else dict()
        except ValidationError as err:
            logger.error(json.dumps({
                "message": err.messages,
                "data": err.valid_data
            }))
            return send_error(data=err.messages)
        issue_ids = params.get('issue_ids', [])
        test_execution = TestExecution.query.filter(TestExecution.issue_id == issue_id,
                                                    TestExecution.cloud_id == cloud_id,
                                                    TestExecution.project_id == project_id).first()
        if test_execution is None:
            test_execution = TestExecution(
                id=str(uuid.uuid4()),
                issue_id=issue_id,
                issue_key=issue_key,
                project_id=project_id,
                cloud_id=cloud_id,
                created_date=get_timestamp_now()
            )
            db.session.add(test_execution)
            db.session.flush()
        test_cases = TestCase.query.filter(TestCase.cloud_id == cloud_id, TestCase.project_id,
                                           TestCase.issue_id.in_(issue_ids)).all()
        test_case_ids = [test_case.id for test_case in test_cases]
        add_tests_archived = TestCasesTestExecutions\
            .query.filter(TestCasesTestExecutions.test_execution_id == test_execution.id)\
                  .filter(TestCasesTestExecutions.test_case_id.in_(test_case_ids)).all()
        archived_count = TestCasesTestExecutions\
            .query.filter(TestCasesTestExecutions.test_execution_id == test_execution.id)\
                  .filter(TestCasesTestExecutions.is_archived != 0).count()
        for i, add_test_archived in enumerate(add_tests_archived):
            add_test_archived.is_archived = archived_count + i + 1
            db.session.flush()
        # Lấy ra tất cả các record trong bảng
        query_all = TestCasesTestExecutions.query.filter(TestCasesTestExecutions.test_execution_id == test_execution.id) \
            .filter(TestCasesTestExecutions.is_archived == 0) \
            .order_by(TestCasesTestExecutions.index.asc())
        # Cập nhật lại giá trị của cột "index"
        for i, query in enumerate(query_all):
            query.index = i + 1
            db.session.flush()
        db.session.commit()
        if len(issue_ids) == 0:
            return send_error(message="No Test(s) archived from the Test Execution")
        return send_result(message=f"{len(issue_ids)} Test(s) archived from the Test Execution")
    except Exception as ex:
        db.session.rollback()
        return send_error(message=str(ex))


@api.route("/restore-archive", methods=["PUT"])
@authorization_require()
def restore_archive_test_case_in_test_execution():
    try:
        token = get_jwt_identity()
        user_id = token.get("userId")
        cloud_id = token.get("cloudId")
        project_id = token.get("projectId")
        issue_key = token.get("issueKey")
        issue_id = token.get("issueId")
        try:
            body = request.get_json()
            params = TestCaseValidator().load(body) if body else dict()
        except ValidationError as err:
            logger.error(json.dumps({
                "message": err.messages,
                "data": err.valid_data
            }))
            return send_error(data=err.messages)
        issue_ids = params.get('issue_ids', [])
        test_execution = TestExecution.query.filter(TestExecution.issue_id == issue_id,
                                                    TestExecution.cloud_id == cloud_id,
                                                    TestExecution.project_id == project_id).first()
        if test_execution is None:
            test_execution = TestExecution(
                id=str(uuid.uuid4()),
                issue_id=issue_id,
                issue_key=issue_key,
                project_id=project_id,
                cloud_id=cloud_id,
                created_date=get_timestamp_now()
            )
            db.session.add(test_execution)
            db.session.flush()
        test_cases = TestCase.query.filter(TestCase.cloud_id == cloud_id, TestCase.project_id,
                                           TestCase.issue_id.in_(issue_ids)).all()
        test_case_ids = [test_case.id for test_case in test_cases]
        restore_tests_archived = TestCasesTestExecutions \
            .query.filter(TestCasesTestExecutions.test_execution_id == test_execution.id) \
            .filter(TestCasesTestExecutions.test_case_id.in_(test_case_ids)).all()
        count_not_archived = TestCasesTestExecutions \
            .query.filter(TestCasesTestExecutions.test_execution_id == test_execution.id) \
            .filter(TestCasesTestExecutions.is_archived == 0).count()
        for i, restore_test_archived in enumerate(restore_tests_archived):
            restore_test_archived.is_archived = 0
            restore_test_archived.index = count_not_archived + i + 1
            db.session.flush()
        query_all = TestCasesTestExecutions.query.filter(TestCasesTestExecutions.test_execution_id == test_execution.id) \
            .filter(TestCasesTestExecutions.is_archived != 0) \
            .order_by(TestCasesTestExecutions.is_archived.asc())
        # Cập nhật lại giá trị của cột "is_archived"
        for i, query in enumerate(query_all):
            query.index = i + 1
            db.session.flush()
        db.session.commit()
        return send_result(message=f"{len(issue_ids)} Archived Test(s) add to Test execution")
    except Exception as ex:
        db.session.rollback()
        return send_error(message=str(ex))


@api.route("/executed-on", methods=["PUT"])
@authorization_require()
def time_modified_date():
    try:
        token = get_jwt_identity()
        user_id = token.get("userId")
        cloud_id = token.get("cloudId")
        project_id = token.get("projectId")
        issue_key = token.get("issueKey")
        issue_id = token.get("issueId")
        body_request = request.get_json()
        time = body_request.get('time')
        test_execution = TestExecution.query.filter(TestExecution.cloud_id == cloud_id,
                                                    TestExecution.project_id == project_id,
                                                    TestExecution.issue_id == issue_id).first()
        if test_execution is None:
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
        test_execution.modified_date = time
        db.session.flush()
        db.session.commit()
        return send_result(message="success")
    except Exception as ex:
        db.session.rollback()
        return send_error(message=str(ex))