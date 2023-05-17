import json
import uuid
from flask import Blueprint, request
from flask_jwt_extended import get_jwt_identity
from sqlalchemy import desc, asc
from sqlalchemy.orm import joinedload

from app.api.v1.history_test import save_history_test_set
from app.api.v1.test_run.schema import TestRunSchema
from app.gateway import authorization_require
from app.models import TestStep, TestCase, db, TestRun, TestExecution, \
    TestStatus, TestStepDetail, TestSet, TestCasesTestSets, HistoryTest
from app.utils import send_result, send_error, data_preprocessing, get_timestamp_now
from app.validator import TestSetSchema, TestCaseSchema, HistorySchema
from operator import or_

INVALID_PARAMETERS_ERROR = 'g1'

api = Blueprint('test_set', __name__)


@api.route("/<test_case_id>", methods=["GET"])
@authorization_require()
def get_test_case(test_case_id):
    token = get_jwt_identity()
    cloud_id = token.get('cloudId')
    test_case = TestCase.get_by_id(test_case_id)
    return send_result(data=TestCaseSchema().dumps(test_case), message="OK")


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


@api.route("/<test_set_issue_id>/test_case", methods=["POST"])
@authorization_require()
def add_test_to_test_set(test_set_issue_id):
    try:
        token = get_jwt_identity()
        project_id = token.get('projectId')
        cloud_id = token.get('cloudId')
        user_id = token.get('userId')
        body_request = request.get_json()
        test_set_issue_key = body_request.get("test_set_issue_key")
        test_cases = body_request.get("test_cases")
        test_set = TestSet.query.filter(TestSet.issue_id == test_set_issue_id,
                                        TestSet.cloud_id == cloud_id,
                                        TestSet.project_id == project_id).first()

        if test_set is None:
            test_set = TestSet(
                id=str(uuid.uuid4()),
                issue_id=test_set_issue_id,
                issue_key=test_set_issue_key,
                project_id=project_id,
                cloud_id=cloud_id,
                created_date=get_timestamp_now()
            )
            db.session.add(test_set)
            db.session.flush()
        test_case_ids = []
        index_max = TestCasesTestSets.query.filter(TestCasesTestSets.test_set_id == test_set.id).count()
        i = 1
        for test_case_issue_id, test_case_issue_key in test_cases.items():
            """
               Get test case, create new if not exist
            """
            test_case = TestCase.query.filter(TestCase.issue_id == test_case_issue_id,
                                              TestCase.cloud_id == cloud_id,
                                              TestCase.project_id == project_id).first()
            if test_case is None:
                test_case = TestCase(
                    id=str(uuid.uuid4()),
                    issue_id=test_set_issue_id,
                    issue_key=test_case_issue_key,
                    project_id=project_id,
                    cloud_id=cloud_id,
                    created_date=get_timestamp_now()
                )
                db.session.add(test_case)
                db.session.flush()
            exist_test_case = TestCasesTestSets \
                .query.filter(TestCasesTestSets.test_case_id == test_case.id,
                              TestCasesTestSets.test_set_id == test_set.id).first()
            if exist_test_case is None:
                """
                  Add this test case to test set
                  """
                test_set_test_case = TestCasesTestSets(
                    test_case_id=test_case.id,
                    test_set_id=test_set.id,
                    index=index_max + i
                )
                test_case_ids.append(test_case.id)
                i += 1
                db.session.add(test_set_test_case)
                db.session.flush()
        db.session.commit()
        # save history
        save_history_test_set(test_set.id, user_id, 1, 1, test_case_ids, [])
        message = f'{len(test_case_ids)} Test case(s) add to the Test Set'
        return send_result(message=message)

    except Exception as ex:
        db.session.rollback()
        return send_error(message=str(ex))


@api.route("/<test_set_id>/test_case", methods=["DELETE"])
@authorization_require()
def remove_test_to_test_set(test_set_id):
    try:
        token = get_jwt_identity()
        user_id = token.get('userId')
        body_request = request.get_json()
        test_case_ids = body_request.get("test_cases_id")
        TestCasesTestSets.query.filter(TestCasesTestSets.test_set_id == test_set_id,
                                       TestCasesTestSets.test_case_id.in_(test_case_ids)).delete()
        db.session.flush()
        # Lấy ra tất cả các record trong bảng
        query_all = TestCasesTestSets.query.filter(TestCasesTestSets.test_set_id == test_set_id) \
            .order_by(TestCasesTestSets.index.asc())
        # Cập nhật lại giá trị của cột "index"
        new_index = 1
        for query in query_all:
            query.index = new_index
            new_index += 1
        db.session.flush()
        db.session.commit()
        message = f'{len(test_case_ids)} Test case(s) remove to the Test Set'
        # save history
        save_history_test_set(test_set_id, user_id, 2, 1, test_case_ids, [])
        return send_result(message=message)
    except Exception as ex:
        db.session.rollback()
        return send_error(message=str(ex))


@api.route("/<test_set_id>/test_case", methods=["PUT"])
@authorization_require()
def change_rank_test_case_in_test_set(test_set_id):
    try:
        token = get_jwt_identity()
        user_id = token.get("userId")
        json_req = request.get_json()
        index_drag = json_req['index_drag']
        index_drop = json_req['index_drop']
        # lấy index_drag
        index_max = db.session.query(TestCasesTestSets).filter(TestCasesTestSets.test_set_id == test_set_id).count()
        query = TestCasesTestSets.query.filter(TestCasesTestSets.test_set_id == test_set_id) \
            .filter(TestCasesTestSets.index == index_drag).first()
        if index_drag > index_drop:
            if index_drop < 1:
                return send_error(message=f'Must be a value between 1 and {index_max}')
            TestCasesTestSets.query.filter(TestCasesTestSets.test_set_id == test_set_id) \
                .filter(TestCasesTestSets.index > index_drop - 1).filter(TestCasesTestSets.c.index < index_drag) \
                .update(dict(index=TestCasesTestSets.index + 1))
            query.index = index_drop
            db.session.flush()
        else:
            if index_drop > index_max:
                return send_error(message=f'Must be a value between 1 and {index_max}')
            TestCasesTestSets.query.filter(TestCasesTestSets.test_set_id == test_set_id) \
                .filter(TestCasesTestSets.index > index_drag).filter(TestCasesTestSets.index < index_drop + 1) \
                .update(dict(index=TestCasesTestSets.index - 1))
            query.index = index_drop
            db.session.flush()
        db.session.commit()
        # save history
        save_history_test_set(test_set_id, user_id, 3, 1, [query.test_case_id], [index_drag, index_drop])
        return send_result(message='Update successfully')
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

        test_execution_issue_ids = body_request.get('test_execution_issue_ids')

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

        for test_execution_issue_id in test_execution_issue_ids:
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

            exist_test_case = test_execution.test_cases.filter(TestCase.id == test_case.id).first()
            if exist_test_case is None:
                """
                  Add this test case to test execution
                  """
                test_execution.test_cases.append(test_case)

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
                return send_error(message='Some Test Executions were already associated with the Test',
                                  status=200, show=False)

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

        test_set = TestSet(
            id=str(uuid.uuid4()),
            issue_id=issue_id,
            project_id=project_id,
            cloud_id=cloud_id,
            created_date=get_timestamp_now()
        )
        db.session.add(test_set)
        db.session.flush()

        return send_result(TestSetSchema().dump(test_set), message="OK")

    except Exception as ex:
        print(ex)


@api.route("/filter/test-case", methods=["POST"])
@authorization_require()
def filter_test_case():
    try:
        body_request = request.get_json()
        token = get_jwt_identity()

        issue_id = token.get('issueId')
        test_type_ids = body_request.get("test_type_ids", [])

        test_cases = db.session.query(TestCasesTestSets.test_case_id).join(TestCase).filter(
            TestCasesTestSets.test_set_id == issue_id,
            TestCase.test_type_id.in_(test_type_ids)).all()

        data = [test_case.test_case_id for test_case in test_cases]
        return send_result(data=data)
    except Exception as ex:
        print(ex)
