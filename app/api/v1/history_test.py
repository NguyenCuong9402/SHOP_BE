import json
import uuid
from flask import Blueprint, request
from flask_jwt_extended import get_jwt_identity

from app.gateway import authorization_require
from app.models import HistoryTest, TestCase, db, TestSet, TestExecution
from app.utils import send_result, send_error, get_timestamp_now
from app.validator import HistorySchema

api = Blueprint('history_test', __name__)


@api.route("/<id_reference>/<history_category>", methods=["GET"])
@authorization_require()
def get_history(id_reference, history_category):
    try:
        query = HistoryTest.query.filter(HistoryTest.id_reference == id_reference,
                                         HistoryTest.history_category == history_category)\
            .order_by(HistoryTest.created_date.desc()).all()
        return send_result(data=HistorySchema(many=True).dump(query), message="OK")
    except Exception as ex:
        return send_error(message=str(ex))


def save_history_test_set(id_reference: str, user_id: str, action: int, history_category: int, btest_ids: list,
                          change_rank: list):
    # 1: add   2: remove  3:change rank
    try:
        if action == 1:
            query = TestCase.query.filter(TestCase.id.in_(btest_ids)).all()
            test_case_keys = [item.issue_key for item in query]
            new_history = HistoryTest(
                id_reference=id_reference,
                user_id=user_id,
                id=str(uuid.uuid4()),
                history_category=history_category,
                activities='add',
                action_name='updated Tests',
                detail_of_action={"Add": test_case_keys},
                created_date=get_timestamp_now())
            db.session.add(new_history)

        elif action == 2:
            query = TestCase.query.filter(TestCase.id.in_(btest_ids)).all()
            test_case_keys = [item.issue_key for item in query]
            new_history = HistoryTest(
                id_reference=id_reference,
                user_id=user_id,
                id=str(uuid.uuid4()),
                activities='remove',
                history_category=history_category,
                action_name='updated Tests',
                detail_of_action={"Remove": test_case_keys},
                created_date=get_timestamp_now())
            db.session.add(new_history)

        elif action == 3:
            query = TestCase.query.filter(TestCase.id == btest_ids[0]).first()
            new_history = HistoryTest(
                id_reference=id_reference,
                user_id=user_id,
                id=str(uuid.uuid4()),
                activities='change',
                history_category=history_category,
                action_name=f'changed Rank of Test {query.issue_key} ',
                detail_of_action={"old rank": change_rank[0], "new rank": change_rank[1]},
                created_date=get_timestamp_now())
            db.session.add(new_history)
        db.session.flush()
        db.session.commit()
    except Exception:
        db.session.rollback()


def save_history_test_step(id_reference: str, user_id: str, action: int,
                           history_category: int, detail_of_action: dict, index_step: list):
    # 1: add step   2: remove  3:change rank  4: clone   5:call
    try:
        if action == 1:
            new_history = HistoryTest(
                id_reference=id_reference,
                user_id=user_id,
                id=str(uuid.uuid4()),
                history_category=history_category,
                activities='add',
                action_name='updated Test Steps',
                detail_of_action={"Test Step": index_step[0], "data": detail_of_action},
                created_date=get_timestamp_now())
            db.session.add(new_history)

        elif action == 2:
            new_history = HistoryTest(
                id_reference=id_reference,
                user_id=user_id,
                id=str(uuid.uuid4()),
                activities='remove',
                history_category=history_category,
                action_name='updated Tests',
                detail_of_action={"Test Step": index_step[0], "data": detail_of_action},
                created_date=get_timestamp_now())
            db.session.add(new_history)

        elif action == 3:
            new_history = HistoryTest(
                id_reference=id_reference,
                user_id=user_id,
                id=str(uuid.uuid4()),
                activities='change',
                history_category=history_category,
                action_name='updated Test Steps',
                detail_of_action={"old rank": index_step[0], "new rank": index_step[1]},
                created_date=get_timestamp_now())
            db.session.add(new_history)
        if action == 4:
            new_history = HistoryTest(
                id_reference=id_reference,
                user_id=user_id,
                id=str(uuid.uuid4()),
                history_category=history_category,
                activities='clone',
                action_name='updated Test Steps',
                detail_of_action={"Test Step": index_step[0], "data": detail_of_action},
                created_date=get_timestamp_now())
            db.session.add(new_history)
        if action == 5:
            new_history = HistoryTest(
                id_reference=id_reference,
                user_id=user_id,
                id=str(uuid.uuid4()),
                history_category=history_category,
                activities='call',
                action_name='updated Test Steps',
                detail_of_action={"Test Step": index_step[0], "data": detail_of_action},
                created_date=get_timestamp_now())
            db.session.add(new_history)
        db.session.flush()
        db.session.commit()
    except Exception:
        db.session.rollback()


def save_history_test_case(id_reference: str, user_id: str, action: int,
                           history_category: int, btest_ids: list, test_type_name: list):
    try:
        # 1: change type   2: add test set  3:remove test set  3: add test execution   4: remove test execution
        if action == 1:
            new_history = HistoryTest(
                id_reference=id_reference,
                user_id=user_id,
                id=str(uuid.uuid4()),
                history_category=history_category,
                activities='change',
                action_name='changed the Test Type',
                detail_of_action={"Old Type": test_type_name[0], "New Type": test_type_name[1]},
                created_date=get_timestamp_now()
            )
            db.session.add(new_history)
        elif action == 2:
            query = TestSet.query.filter(TestSet.id.in_(btest_ids)).all()
            test_set_keys = [item.issue_key for item in query]
            new_history = HistoryTest(
                id_reference=id_reference,
                user_id=user_id,
                id=str(uuid.uuid4()),
                history_category=history_category,
                activities='add',
                action_name='updated Test Sets',
                detail_of_action={"Added": test_set_keys},
                created_date=get_timestamp_now())
            db.session.add(new_history)
        elif action == 3:
            query = TestSet.query.filter(TestSet.id.in_(btest_ids)).all()
            test_set_keys = [item.issue_key for item in query]
            new_history = HistoryTest(
                id_reference=id_reference,
                user_id=user_id,
                id=str(uuid.uuid4()),
                history_category=history_category,
                activities='remove',
                action_name='updated Test Sets',
                detail_of_action={"Removed": test_set_keys},
                created_date=get_timestamp_now())
            db.session.add(new_history)
        elif action == 4:
            query = TestExecution.query.filter(TestExecution.id.in_(btest_ids)).all()
            test_keys = [item.issue_key for item in query]
            new_history = HistoryTest(
                id_reference=id_reference,
                user_id=user_id,
                id=str(uuid.uuid4()),
                activities='add',
                history_category=history_category,
                action_name='updated Test Executions',
                detail_of_action={"Added": test_keys},
                created_date=get_timestamp_now())
            db.session.add(new_history)
        elif action == 5:
            query = TestExecution.query.filter(TestExecution.id.in_(btest_ids)).all()
            test_keys = [item.issue_key for item in query]
            new_history = HistoryTest(
                id_reference=id_reference,
                user_id=user_id,
                id=str(uuid.uuid4()),
                activities='remove',
                history_category=history_category,
                action_name='updated Test Executions',
                detail_of_action={"Removed": test_keys},
                created_date=get_timestamp_now())
            db.session.add(new_history)
        db.session.flush()
        db.session.commit()
    except Exception:
        db.session.rollback()


def save_history_test_execution(id_reference: str, user_id: str, action: int, history_category: int, ids: list):
    # 1: add test case  2: remove test case
    try:
        if action == 1:
            query = TestCase.query.filter(TestCase.id.in_(ids)).all()
            test_keys = [item.issue_key for item in query]
            new_history = HistoryTest(
                id_reference=id_reference,
                user_id=user_id,
                id=str(uuid.uuid4()),
                history_category=history_category,
                activities='add',
                action_name='updated Test Executions',
                detail_of_action={"Added": test_keys},
                created_date=get_timestamp_now())
            db.session.add(new_history)
        elif action == 2:
            query = TestCase.query.filter(TestCase.id.in_(ids)).all()
            test_keys = [item.issue_key for item in query]
            new_history = HistoryTest(
                id_reference=id_reference,
                user_id=user_id,
                id=str(uuid.uuid4()),
                activities='remove',
                history_category=history_category,
                action_name='updated Test Executions',
                detail_of_action={"Removed": test_keys},
                created_date=get_timestamp_now())
            db.session.add(new_history)
        db.session.flush()
        db.session.commit()
    except Exception:
        db.session.rollback()
