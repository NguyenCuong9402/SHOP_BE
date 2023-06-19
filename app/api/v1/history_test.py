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
        token = get_jwt_identity()
        cloud_id = token.get('cloudId')
        project_id = token.get('projectId')
        issue_key = token.get('issue_key')
        user_id = token.get('userId')
        # 1:Test Set , 2: Test Case , 3: Test Execution
        if history_category == '1':
            test = TestSet.query.filter(TestSet.project_id == project_id, TestSet.cloud_id == cloud_id,
                                        TestSet.issue_id == id_reference).first()
            if test is None:
                test = TestSet(
                    id=str(uuid.uuid4()),
                    issue_id=id_reference,
                    issue_key=issue_key,
                    project_id=project_id,
                    cloud_id=cloud_id,
                    created_date=get_timestamp_now()
                )
                db.session.add(test)
                db.session.flush()
        elif history_category == '2':
            test = TestCase.query.filter(TestCase.project_id == project_id, TestCase.cloud_id == cloud_id,
                                         TestCase.issue_id == id_reference).first()
            if test is None:
                test = TestExecution(
                    id=str(uuid.uuid4()),
                    issue_id=id_reference,
                    issue_key=issue_key,
                    project_id=project_id,
                    cloud_id=cloud_id,
                    created_date=get_timestamp_now()
                )
                db.session.add(test)
                db.session.flush()
        elif history_category == '3':
            test = TestExecution.query.filter(TestExecution.project_id == project_id,
                                              TestExecution.cloud_id == cloud_id,
                                              TestExecution.issue_id == id_reference).first()
            if test is None:
                test = TestExecution(
                    id=str(uuid.uuid4()),
                    issue_id=id_reference,
                    issue_key=issue_key,
                    project_id=project_id,
                    cloud_id=cloud_id,
                    created_date=get_timestamp_now()
                )
                db.session.add(test)
                db.session.flush()

        else:
            return send_error(message="Error ")
        query = HistoryTest.query.filter(HistoryTest.id_reference == test.id,
                                         HistoryTest.history_category == history_category)\
            .order_by(HistoryTest.created_date.desc()).all()
        return send_result(data=HistorySchema(many=True).dump(query), message="OK")
    except Exception as ex:
        return send_error(message=str(ex))


def save_history_test_set(id_reference: str, user_id: str, action: int, history_category: int, btest_ids: list,
                          change_rank: list):
    # 1: add   2: remove  3:change rank

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


def save_history_test_step(id_reference: str, user_id: str, action: int,
                           history_category: int, detail_of_action: dict, index_step: list):
    # 1: add step   2: remove  3:change rank  4: clone   5:call 6: remove step call  7: update
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
            action_name='updated Tests Steps',
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
    elif action == 4:
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
    elif action == 5:
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
    elif action == 6:
        new_history = HistoryTest(
            id_reference=id_reference,
            user_id=user_id,
            id=str(uuid.uuid4()),
            history_category=history_category,
            activities='remove call',
            action_name='updated Test Steps',
            detail_of_action={"Test Step": index_step[0], "data": detail_of_action},
            created_date=get_timestamp_now())
        db.session.add(new_history)
    elif action == 7:
        new_history = HistoryTest(
            id_reference=id_reference,
            user_id=user_id,
            id=str(uuid.uuid4()),
            history_category=history_category,
            activities='update',
            action_name='updated Test Steps',
            detail_of_action={"Test Step": index_step[0], "data": detail_of_action},
            created_date=get_timestamp_now())
        db.session.add(new_history)
    db.session.flush()


def save_history_test_case(id_reference: str, user_id: str, action: int,
                           history_category: int, btest_ids: list, change: list):
    # 1: change type   2: add test set  3:remove test set  4: add test execution   5: remove test execution
    # 6: change repo
    if action == 1:
        new_history = HistoryTest(
            id_reference=id_reference,
            user_id=user_id,
            id=str(uuid.uuid4()),
            history_category=history_category,
            activities='change',
            action_name='changed the Test Type',
            detail_of_action={"old": change[0], "new": change[1]},
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
    elif action == 6:
        new_history = HistoryTest(
            id_reference=id_reference,
            user_id=user_id,
            id=str(uuid.uuid4()),
            activities='change',
            history_category=history_category,
            action_name='changed the Test Repository Folder',
            detail_of_action={"old": change[0], "new": change[1]},
            created_date=get_timestamp_now())
        db.session.add(new_history)
    db.session.flush()


def save_history_test_execution(id_reference: str, user_id: str, action: int, history_category: int, ids: list,
                                change_rank: list):
    # 1: add test case  2: remove test case
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
    elif action == 3:
        query = TestCase.query.filter(TestCase.id == ids[0]).first()
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
