import json
from urllib3.util import Url
import uuid
from flask import Blueprint, request
from flask_jwt_extended import get_jwt_identity
from sqlalchemy import desc, asc
from sqlalchemy.orm import joinedload

from app.api.v1.test_run.schema import TestRunSchema
from app.gateway import authorization_require
from app.models import TestStep, TestCase, db, TestRun, TestExecution, \
    TestStatus, TestStepDetail, TestSet, test_cases_test_sets, HistoryTestSet
from app.utils import send_result, send_error, data_preprocessing, get_timestamp_now, get_timestamp_now_2
from app.validator import TestSetSchema, TestCaseSchema, HistorySchema

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


@api.route("/add_to_test_set/<test_set_id>", methods=["POST"])
@authorization_require()
def add_test_to_test_set(test_set_id):
    try:
        token = get_jwt_identity()
        user_id = token.get('userId')
        body_request = request.get_json()
        test_cases_id = body_request.get("test_cases_id")
        # check Test Set
        check_test_set = TestSet.query.filter(TestSet.id == test_set_id).first()
        if not check_test_set:
            return send_error(message='TEST SET DOES NOT EXIST', status=404, show=False)
        # Query max index
        query = test_cases_test_sets.select().where(test_cases_test_sets.c.test_set_id == test_set_id) \
            .order_by(desc(test_cases_test_sets.columns.index)).limit(1)
        result = db.session.execute(query)
        index_max = [{'test_case_id': row[0], 'test_set_id': row[1], 'index': row[2]} for row in result]

        record = []
        for test_case_id in test_cases_id:
            # check Test Case
            check_test_case = TestCase.query.filter(TestCase.id == test_case_id).first()
            if not check_test_case:
                return send_error(message='TEST CASE DOES NOT EXIST', status=404, show=False)
            if not index_max:
                new_record = {'test_case_id': test_case_id,
                              'test_set_id': test_set_id,
                              'index': 1 + test_cases_id.index(test_case_id)
                              }
            else:
                new_record = {'test_case_id': test_case_id,
                              'test_set_id': test_set_id,
                              'index': index_max[0]['index'] + 1 + test_cases_id.index(test_case_id)
                              }
            record.append(new_record)
        stmt = test_cases_test_sets.insert().values(record)
        db.session.execute(stmt)
        db.session.commit()
        # save history
        save_history(test_set_id, user_id, 1, test_cases_id, [])
        return send_result(message='Add test case to test set successfully', status=201, show=True)

    except Exception as ex:
        db.session.rollback()
        return send_error(message=str(ex))


@api.route("/remove_from_test_set/<test_set_id>", methods=["DELETE"])
@authorization_require()
def remove_test_to_test_set(test_set_id):
    try:
        token = get_jwt_identity()
        user_id = token.get('userId')
        body_request = request.get_json()
        test_cases_id = body_request.get("test_cases_id")
        # check Test Set
        check_test_set = TestSet.query.filter(TestSet.id == test_set_id).first()
        if not check_test_set:
            return send_error(message='TEST SET DOES NOT EXIST', status=404, show=False)
        # check Test Case
        for test_case_id in test_cases_id:
            check_test_case = TestCase.query.filter(TestCase.id == test_case_id).first()
            if not check_test_case:
                return send_error(message='TEST CASE DOES NOT EXIST ', status=404, show=False)
        # remove
        remove_query = test_cases_test_sets.delete().where(
            test_cases_test_sets.c.test_case_id.in_(test_cases_id))
        db.session.execute(remove_query)
        # Lấy ra tất cả các record trong bảng
        query_all = test_cases_test_sets.select().order_by(asc(test_cases_test_sets.c.index))
        rows = db.session.execute(query_all)
        # Cập nhật lại giá trị của cột "index"
        new_index = 1
        for row in rows:
            stmt = test_cases_test_sets.update() \
                .where(test_cases_test_sets.c.test_case_id == row.test_case_id) \
                .where(test_cases_test_sets.c.test_set_id == row.test_set_id) \
                .values(index=new_index)
            db.session.execute(stmt)
            new_index += 1
        db.session.commit()
        # save history
        save_history(test_set_id, user_id, 2, test_cases_id, [])
        return send_result(message='remove test case to test set successfully', status=201, show=True)
    except Exception as ex:
        db.session.rollback()
        return send_error(message=str(ex))


@api.route("/change_rank_test_case/<test_set_id>", methods=["PUT"])
@authorization_require()
def change_rank_case_in_test_set(test_set_id):
    try:
        token = get_jwt_identity()
        user_id = token.get("userId")
        json_req = request.get_json()
        index_drag = json_req['index_drag']
        index_drop = json_req['index_drop']
        # lấy index_drag
        query = test_cases_test_sets.select().where(test_cases_test_sets.c.test_set_id == test_set_id) \
            .where(test_cases_test_sets.c.index == index_drag)
        result = db.session.execute(query)
        data = [{'test_case_id': row[0], 'test_set_id': row[1], 'index': row[2]} for row in result]

        if index_drag > index_drop:
            # Cập nhật vị trí của các test case ở giữa giá trị drop-1 và giá trị drag
            pos = test_cases_test_sets.update().where(
                (test_cases_test_sets.c.test_set_id == test_set_id) &
                (test_cases_test_sets.c.index > index_drop - 1) &
                (test_cases_test_sets.c.index < index_drag)).values(index=test_cases_test_sets.c.index + 1)
            db.session.execute(pos)
            # Gán đến vị trí drop
            pos1 = test_cases_test_sets.update().where(
                (test_cases_test_sets.c.test_set_id == test_set_id) &
                (test_cases_test_sets.c.test_case_id == data[0]['test_case_id']) &
                (test_cases_test_sets.c.index == data[0]['index'])).values(index=index_drop)
        else:

            # Cập nhật vị trí của các test case ở giữa giá trị drag và drop+1
            pos = test_cases_test_sets.update().where(
                (test_cases_test_sets.c.test_set_id == test_set_id) &
                (test_cases_test_sets.c.index > index_drag) &
                (test_cases_test_sets.c.index < index_drop + 1)).values(index=test_cases_test_sets.c.index - 1)
            db.session.execute(pos)
            # Gán đến vị trí drop
            pos1 = test_cases_test_sets.update().where(
                (test_cases_test_sets.c.test_set_id == test_set_id) &
                (test_cases_test_sets.c.test_case_id == data[0]['test_case_id']) &
                (test_cases_test_sets.c.index == data[0]['index'])).values(index=index_drop)
        db.session.execute(pos1)
        db.session.commit()
        # save history
        save_history(test_set_id, user_id, 3, [data[0]['test_case_id']], [index_drag, index_drop])

        return send_result(message='Update test case to test set successfully', status=201, show=True)
    except Exception as ex:
        db.session.rollback()
        return send_error(message=str(ex))


def save_history(test_set_id: str, user_id: str, action: int, btest_id: list, change_rank: list):
    # 1: add   2: remove  3:change rank
    if action == 1:
        query = TestCase.query.filter(TestCase.id.in_(btest_id)).all()
        test_case_keys = [item.issue_key for item in query]
        new_history = HistoryTestSet(
            test_set_id=test_set_id,
            user_id=user_id,
            id=str(uuid.uuid4()),
            activities='add',
            action_name='updated Tests',
            detail_of_action=test_case_keys,
            created_date=get_timestamp_now_2())
        db.session.add(new_history)

    elif action == 2:
        query = TestCase.query.filter(TestCase.id.in_(btest_id)).all()
        test_case_keys = [item.issue_key for item in query]
        new_history = HistoryTestSet(
            test_set_id=test_set_id,
            user_id=user_id,
            id=str(uuid.uuid4()),
            activities='remove',
            action_name='updated Tests',
            detail_of_action=test_case_keys,
            created_date=get_timestamp_now_2())
        db.session.add(new_history)

    elif action == 3:
        query = TestCase.query.filter(TestCase.id == btest_id[0]).first()
        new_history = HistoryTestSet(
            test_set_id=test_set_id,
            user_id=user_id,
            id=str(uuid.uuid4()),
            activities='change',
            action_name=f'changed Rank of Test {query.issue_id} ',
            detail_of_action=change_rank,
            created_date=get_timestamp_now_2())
        db.session.add(new_history)
    db.session.commit()


@api.route("/history/<test_set_id>", methods=["GET"])
@authorization_require()
def get_history(test_set_id):
    try:
        token = get_jwt_identity()
        user_id = token.get("userId")
        query = HistoryTestSet.query.filter(HistoryTestSet.test_set_id == test_set_id).all()
        return send_result(data=HistorySchema(many=True).dump(query), message="OK")
    except Exception as ex:
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
