import json
import uuid
from operator import or_

from flask import Blueprint, request
from flask_jwt_extended import jwt_required, get_jwt_identity, create_access_token
from benedict import benedict
from marshmallow import ValidationError
from sqlalchemy import desc, asc
from sqlalchemy.orm import joinedload

from app.api.v1.history_test import save_history_test_case, save_history_test_execution
from app.api.v1.test_run.schema import TestRunSchema
from app.enums import INVALID_PARAMETERS_ERROR, TestTimerType
from app.extensions import logger
from app.gateway import authorization_require
from app.models import TestStep, TestCase, TestType, db, TestField, Setting, TestRun, TestExecution, \
    TestCasesTestExecutions, TestStatus, TestStepDetail, TestCasesTestSets, TestSet, TestEnvironment, TestTimer
from app.utils import send_result, send_error, data_preprocessing, get_timestamp_now
from app.validator import TestCaseValidator, TestCaseSchema, TestSetSchema, TestCaseTestStepSchema

DELETE_SUCCESS = 13
ADD_SUCCESS = 16

api = Blueprint('test_case', __name__)


@api.route("/<issue_id>", methods=["GET"])
@authorization_require()
def get_test_case(issue_id):
    token = get_jwt_identity()
    cloud_id = token.get('cloudId')
    project_id = token.get('projectId')
    test_case = TestCase.query.filter(TestCase.project_id == project_id, TestCase.cloud_id == cloud_id,
                                      TestCase.issue_id == issue_id).first()
    try:
        return send_result(data=TestCaseSchema().dump(test_case), message="OK")
    except Exception:
        return send_error(message="not found")


@api.route("/<issue_id>/test-set", methods=["GET"])
@authorization_require()
def get_test_set_from_test_case(issue_id):
    token = get_jwt_identity()
    cloud_id = token.get('cloudId')
    project_id = token.get('projectId')
    # Get search params
    page = request.args.get('page', 1, type=int)
    page_size = request.args.get('page_size', 10, type=int)
    order_by = request.args.get('order_by', "issue_key", type=str)
    order = request.args.get('order', 'asc', type=str)
    test_case = TestCase.query.filter(TestCase.cloud_id == cloud_id, TestCase.issue_id == issue_id,
                                      TestCase.project_id == project_id).first()
    if test_case is None:
        return send_error("Not found test case")
    # sort
    query = db.session.query(TestSet).join(TestCasesTestSets).filter(TestCasesTestSets.test_case_id == test_case.id)
    column_sorted = getattr(TestRun, order_by)
    query = query.order_by(desc(column_sorted)) if order == "desc" else query.order_by(asc(column_sorted))
    test_sets = query.paginate(page=page, per_page=page_size, error_out=False).items
    total = query.count()
    extra = 1 if (total % page_size) else 0
    total_pages = int(total / page_size) + extra
    try:
        results = {
            "test_cases": TestSetSchema(many=True).dump(test_sets),
            "total": total,
            "total_pages": total_pages
        }
        return send_result(data=results)
    except Exception as ex:
        return send_error(message=str(ex), data={})


@api.route("/<issue_id>/test_run", methods=["GET"])
@authorization_require()
def get_test_run_from_test_case(issue_id):
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
    # Get test case
    test_case = TestCase.query.filter(TestCase.cloud_id == cloud_id, TestCase.issue_id == issue_id,
                                      TestCase.project_id == project_id).first()
    if test_case is None:
        return send_error("Not found test case")
    query = TestRun.query.filter(TestRun.cloud_id == cloud_id, TestRun.project_id == project_id,
                                 TestRun.test_case_id == test_case.id)
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


@api.route("/<issue_id>/test_step", methods=["GET"])
@authorization_require()
def get_test_step_from_test_case(issue_id):
    token = get_jwt_identity()
    cloud_id = token.get('cloudId')
    project_id = token.get('projectId')
    page = request.args.get('page', 1, type=int)
    page_size = request.args.get('page_size', 10, type=int)
    order_by = request.args.get('order_by', '', type=str)
    order = request.args.get('order', 'asc', type=str)
    if order_by == '':
        order_by = "index"
    else:
        if order_by not in ["created_date", "index"]:
            return send_error("Not a valid")
    column_sorted = getattr(TestStep, order_by)
    # Get test case
    test_case = TestCase.query.filter(TestCase.cloud_id == cloud_id, TestCase.issue_id == issue_id,
                                      TestCase.project_id == project_id).first()
    if test_case is None:
        return send_error("Not found test case")
    query = TestStep.query.filter(TestStep.project_id == project_id, TestStep.cloud_id == cloud_id,
                                  TestStep.test_case_id == test_case.id)
    query = query.order_by(desc(column_sorted)) if order == "desc" else query.order_by(asc(column_sorted))
    test_runs = query.paginate(page=page, per_page=page_size, error_out=False).items
    total = query.count()
    extra = 1 if (total % page_size) else 0
    total_pages = int(total / page_size) + extra
    try:
        results = {
            "test_cases": TestCaseTestStepSchema(many=True).dump(test_runs),
            "total": total,
            "total_pages": total_pages
        }
        return send_result(data=results)

    except Exception as ex:
        return send_error(message=str(ex))


@api.route("/<test_case_id>/<test_type_id>", methods=["PUT"])
@authorization_require()
def change_test_type(test_case_id, test_type_id):
    try:
        token = get_jwt_identity()
        cloud_id = token.get('cloudId')
        project_id = token.get('projectId')
        user_id = token.get('userId')
        test_case = TestCase.query.filter(TestCase.id == test_case_id).first()
        new_type = TestType.query.filter(TestType.id == test_type_id).first()
        if new_type is None:
            return send_error(message="Error changing test type. '[new test type name]' no longer exists",
                              status="success", show=False)
        old_type = TestType.query.filter(TestType.id == test_case.test_type_id).first()
        old_type_name = old_type.name
        test_case.test_type_id = new_type.id
        db.session.flush()
        db.session.commit()
        save_history_test_case(test_case_id, user_id, 2, [old_type_name,new_type.name])
        return send_result(message="success")

    except Exception as ex:
        db.session.rollback()
        return send_error(message=str(ex))


@api.route("/<test_issue_id>/test_execution", methods=["POST"])
@authorization_require()
def add_test_execution(test_issue_id):
    try:
        body_request = request.get_json()
        token = get_jwt_identity()
        cloud_id = token.get('cloudId')
        project_id = token.get('projectId')
        user_id = token.get('userId')
        test_executions = body_request.get('test_executions')
        test_case_issue_key = body_request.get('test_case_issue_key')
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
                issue_key=test_case_issue_key,
                project_id=project_id,
                cloud_id=cloud_id,
                created_date=get_timestamp_now()
            )
            db.session.add(test_case)
            db.session.flush()
        test_execution_ids = []
        for test_execution_issue_id, test_execution_issue_key in test_executions.items():
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

            exist_test_case = TestCasesTestExecutions \
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
                test_execution_ids.append(test_execution.id)

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
                return send_error(message='Some Test Executions were already associated with the Test',
                                  status=200, show=False)

        db.session.commit()
        save_history_test_case(test_case.id, user_id, 4, 2, test_execution_ids, [])
        return send_result(message=f'Add {len(test_execution_ids)} test execution to test case successfully', show=True)
    except Exception as ex:
        db.session.rollback()
        return send_error(message=str(ex))


@api.route("/<test_case_id>/test_execution", methods=["DELETE"])
@authorization_require()
def remove_test_execution(test_case_id):
    try:
        body_request = request.get_json()
        token = get_jwt_identity()
        cloud_id = token.get('cloudId')
        project_id = token.get('projectId')
        user_id = token.get('userID')
        test_execution_ids = body_request.get('test_execution_ids')
        # xóa test run
        TestRun.query.filter(TestRun.test_case_id == test_case_id) \
            .filter(TestRun.test_execution_id.in_(test_execution_ids)) \
            .delete()
        db.session.flush()
        # xóa test_cases_test_executions
        TestCasesTestExecutions.query.filter(
            TestCasesTestExecutions.test_case_id == test_case_id) \
            .filter(TestCasesTestExecutions.test_execution_id.in_(test_execution_ids)).delete()
        db.session.flush()
        db.session.commit()
        save_history_test_case(test_case_id, user_id, 5, 2, test_execution_ids, [])
        return send_result(message=f'Remove {len(test_execution_ids)} test to test case execution successfully')
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

        test_case = TestCase(
            id=str(uuid.uuid4()),
            issue_id=issue_id,
            project_id=project_id,
            cloud_id=cloud_id,
            created_date=get_timestamp_now()
        )
        db.session.add(test_case)
        db.session.flush()

        return send_result(data='Done', message="OK")

    except Exception as ex:
        print(ex)


@api.route("/<test_case_id>/test-set", methods=['DELETE'])
@authorization_require()
def delete_tests_set_from_testcase(test_case_id):
    try:
        token = get_jwt_identity()
        user_id = token.get('userId')
        try:
            body = request.get_json()
            params = TestCaseValidator().load(body) if body else dict()
        except ValidationError as err:
            logger.error(json.dumps({
                "message": err.messages,
                "data": err.valid_data
            }))
            return send_error(message_id=INVALID_PARAMETERS_ERROR, data=err.messages)

        ids = params.get('ids', [])
        is_delete_all = params.get('is_delete_all', False)

        if is_delete_all:
            # sắp xếp lại index của test set
            query = TestCasesTestSets.query.filter(TestCasesTestSets.test_case_id == test_case_id,
                                                   TestCasesTestSets.test_set_id.notin_(ids)).all()
            ids_to_delete = [item.test_set_id for item in query]
            number_test_set = len(ids_to_delete)

            for test_set_id in ids_to_delete:
                max_index = TestCasesTestSets.query.filter(TestCasesTestSets.test_set_id == test_set_id,
                                                           TestCasesTestSets.test_case_id == test_case_id).first()
                TestCasesTestSets.query.filter(TestCasesTestSets.test_set_id == test_set_id) \
                    .filter(TestCasesTestSets.index > max_index.index).update(dict(index=TestCasesTestSets.index - 1))
            db.session.flush()
            # delete
            TestCasesTestSets.query.filter(TestCasesTestSets.test_set_id.notin_(ids),
                                           TestCasesTestSets.test_case_id == test_case_id).delete()
            db.session.flush()
        else:
            # sắp xếp lại index
            for test_set_id in ids:
                max_index = TestCasesTestSets.query.filter(TestCasesTestSets.test_set_id == test_set_id,
                                                           TestCasesTestSets.test_case_id == test_case_id).first()
                TestCasesTestSets.query.filter(TestCasesTestSets.test_set_id == test_set_id) \
                    .filter(TestCasesTestSets.index > max_index.index).update(dict(index=TestCasesTestSets.index - 1))
            db.session.flush()
            # delete
            TestCasesTestSets.query.filter(TestCasesTestSets.test_set_id.in_(ids),
                                           TestCasesTestSets.test_case_id == test_case_id).delete()
            number_test_set = len(ids)
            db.session.flush()
            ids_to_delete = ids
        db.session.commit()
        message = f'{number_test_set} Test Set(s) removed from the Test'
        # save history
        save_history_test_case(test_case_id, user_id, 3, 2, ids_to_delete, [])
        return send_result(message_id=DELETE_SUCCESS, message=message, show=True)
    except Exception as ex:
        db.session.rollback()
        return send_error(message=str(ex))


@api.route("/<test_case_id>/test-set", methods=['POST'])
@authorization_require()
def add_tests_set_for_testcase(test_case_id):
    try:
        token = get_jwt_identity()
        user_id = token.get('userId')
        try:
            body = request.get_json()
            params = TestCaseValidator().load(body) if body else dict()
        except ValidationError as err:
            logger.error(json.dumps({
                "message": err.messages,
                "data": err.valid_data
            }))
            return send_error(message_id=INVALID_PARAMETERS_ERROR, data=err.messages)

        ids = params.get('ids', [])

        index_max = TestCasesTestSets.query.filter(TestCasesTestExecutions.test_case_id == test_case_id).count()
        for index, test_set_id in enumerate(ids):
            new_item = TestCasesTestSets(test_set_id=test_set_id,
                                         test_case_id=test_case_id,
                                         index=index_max+1+index)
            db.session.add(new_item)
            db.session.flush()
        db.session.commit()
        # save history
        save_history_test_case(test_case_id, user_id, 2, 2, ids, [])
        message = f'{len(ids)} Test Set(s) added to the Test'
        return send_result(message_id=ADD_SUCCESS, message=message, show=True)
    except Exception as ex:
        db.session.rollback()
        return send_error(message=str(ex))


@api.route("/filter/testrun", methods=['POST'])
def filter_test_run():
    try:
        body = request.get_json()
        body_req = TestCaseFilterValidator().load(body) if body else dict()
    except ValidationError as err:
        logger.error(json.dumps({
            "message": err.messages,
            "data": err.valid_data
        }))
        return send_error(message_id=INVALID_PARAMETERS_ERROR, data=err.messages)

    statuses = body_req.get("statuses", [])
    environments = body_req.get("environments", [])
    testrun_started = body_req.get("testrun_started", {})
    testrun_finished = body_req.get("testrun_finished", {})
    token = get_jwt_identity()
    issue_id = token.get('issueId')

    query = db.session.query(TestCase.issue_id)
    if len(statuses) > 0:
        query = query.join(TestStatus).filter(TestStatus.name.in_(statuses))
    if len(environments) > 0:
        query = query.join(TestEnvironment, TestExecution.test_environments).filter(
            TestEnvironment.name.in_(environments))
    if len(testrun_started) > 0:
        if testrun_started.get('from') and not testrun_started.get('to'):
            query = query.join(TestTimer).filter(TestTimer.date_time >= testrun_started.get('from'),
                                                 TestTimer.time_type == TestTimerType.START_TIME)
        else:
            query = query.join(TestTimer).filter(TestTimer.date_time >= testrun_started.get('from'),
                                                 TestTimer.date_time <= testrun_started.get('to'),
                                                 TestTimer.time_type == TestTimerType.START_TIME)
    if len(testrun_finished) > 0:
        if testrun_finished.get('from') and not testrun_finished.get('to'):
            query = query.join(TestTimer).filter(TestTimer.date_time >= testrun_finished.get('from'),
                                                 TestTimer.time_type == TestTimerType.END_TIME)
        else:
            query = query.join(TestTimer).filter(TestTimer.date_time >= testrun_finished.get('from'),
                                                 TestTimer.date_time <= testrun_finished.get('to'),
                                                 TestTimer.time_type == TestTimerType.END_TIME)

    query = query.filter(TestRun.issue_id == issue_id).all()

    data = TestCaseFilterSchema(many=True).dump(query)
    return send_result(data=data)
