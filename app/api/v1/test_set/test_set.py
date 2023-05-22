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
from app.utils import send_result, send_error, data_preprocessing, get_timestamp_now, escape_wildcard
from app.validator import TestSetSchema, TestCaseSchema, HistorySchema, TestSetTestCasesSchema
from operator import or_

INVALID_PARAMETERS_ERROR = 'g1'

api = Blueprint('test_set', __name__)


@api.route("/<issue_id>", methods=["GET"])
@authorization_require()
def get_test_set(issue_id):
    token = get_jwt_identity()
    cloud_id = token.get('cloudId')
    project_id = token.get('projectId')
    test_set = TestSet.query.filter(TestSet.project_id == project_id, TestSet.cloud_id == cloud_id,
                                    TestSet.issue_id == issue_id).first()
    try:
        return send_result(data=TestSetSchema().dump(test_set), message="OK")
    except Exception:
        return send_error(message="not found")


@api.route("/<issue_id>/test_case", methods=["GET"])
@authorization_require()
def get_test_case_from_test_set(issue_id):
    token = get_jwt_identity()
    cloud_id = token.get('cloudId')
    project_id = token.get('projectId')
    # Get search params
    page = request.args.get('page', 1, type=int)
    page_size = request.args.get('page_size', 10, type=int)
    order_by = request.args.get('order_by', '', type=str)
    order = request.args.get('order', 'asc', type=str)
    test_set = TestSet.query.filter(TestSet.cloud_id == cloud_id, TestCase.issue_id == issue_id,
                                    TestSet.project_id == project_id).first()
    if test_set is None:
        return send_error("Not found test set")
    # sort
    if order_by == "index" or order_by == '':
        order_by = "index"
        column_sorted = getattr(TestCasesTestSets, order_by)
    else:
        if order_by not in ["issue_id", "issue_key", "created_date"]:
            return send_error("Not a valid")
        column_sorted = getattr(TestCase, order_by)
    query = db.session.query(TestCase.id, TestCase.issue_id, TestCase.issue_key, TestCase.project_id, TestCase.cloud_id,
                             TestCase.created_date, TestCasesTestSets.index).join(TestCasesTestSets)\
        .filter(TestCasesTestSets.test_set_id == test_set.id)
    query = query.order_by(desc(column_sorted)) if order == "desc" else query.order_by(asc(column_sorted))
    test_cases = query.paginate(page=page, per_page=page_size, error_out=False).items
    total = query.count()
    extra = 1 if (total % page_size) else 0
    total_pages = int(total / page_size) + extra
    try:
        results = {
            "test_cases": TestSetTestCasesSchema(many=True).dump(test_cases),
            "total": total,
            "total_pages": total_pages
        }
        return send_result(data=results)
    except Exception as ex:
        return send_error(data={})


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
                    issue_id=test_case_issue_id,
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
                    index=index_max+i
                )
                test_case_ids.append(test_case.id)
                i += 1
                db.session.add(test_set_test_case)
                db.session.flush()
        db.session.commit()
        # save history
        save_history_test_set(test_set.id, user_id, 1, 1, test_case_ids, [])
        message = f'{len(test_case_ids)} Test case(s) add to the Test Set'
        return send_result(message=message, show=True)

    except Exception as ex:
        db.session.rollback()
        return send_error(message=str(ex))


@api.route("/<test_set_issue_id>/test_case", methods=["DELETE"])
@authorization_require()
def remove_test_to_test_set(test_set_issue_id):
    try:
        token = get_jwt_identity()
        user_id = token.get('userId')
        project_id = token.get('projectId')
        cloud_id = token.get('cloudId')

        body_request = request.get_json()
        issue_ids = body_request.get("issue_ids")
        is_delete_all = body_request.get("is_delete_all", False)
        test_cases = TestCase.query.filter(TestCase.cloud_id == cloud_id, TestCase.project_id,
                                           TestCase.issue_id.in_(issue_ids)).all()
        test_case_ids = [test_case.id for test_case in test_cases]
        test_set = TestSet.query.filter(TestSet.cloud_id == cloud_id, TestSet.project_id == project_id,
                                        TestSet.issue_id == test_set_issue_id).first()
        if is_delete_all:
            query = TestCasesTestSets.query.filter(TestCasesTestSets.test_set_id == test_set.id,
                                                   TestCasesTestSets.test_case_id.notin_(test_case_ids)).all()
            ids_to_delete = [item.test_case_id for item in query]
            TestCasesTestSets.query.filter(TestCasesTestSets.test_set_id == test_set.id,
                                           TestCasesTestSets.test_case_id.in_(ids_to_delete)).delete()
            db.session.flush()

        else:
            TestCasesTestSets.query.filter(TestCasesTestSets.test_set_id == test_set.id,
                                           TestCasesTestSets.test_case_id.in_(test_case_ids)).delete()
            db.session.flush()
            ids_to_delete = test_case_ids
        message = f'{len(ids_to_delete)} Test case(s) remove to the Test Set'
        # Lấy ra tất cả các record trong bảng
        query_all = TestCasesTestSets.query.filter(TestCasesTestSets.test_set_id == test_set.id)\
            .order_by(TestCasesTestSets.index.asc())
        # Cập nhật lại giá trị của cột "index"
        new_index = 1
        for query in query_all:
            query.index = new_index
            new_index += 1
        db.session.flush()
        db.session.commit()
        # save history
        save_history_test_set(test_set.id, user_id, 2, 1, ids_to_delete, [])
        return send_result(message=message, show=True)
    except Exception as ex:
        db.session.rollback()
        return send_error(message=str(ex))


@api.route("/<test_set_issue_id>/test_case", methods=["PUT"])
@authorization_require()
def change_rank_test_case_in_test_set(test_set_issue_id):
    try:
        token = get_jwt_identity()
        user_id = token.get("userId")
        cloud_id = token.get("cloudId")
        project_id = token.get("projectId")
        json_req = request.get_json()
        index_drag = json_req['index_drag']
        index_drop = json_req['index_drop']
        test_set = TestSet.query.filter(TestSet.cloud_id == cloud_id, TestSet.project_id == project_id,
                                        TestSet.issue_id == test_set_issue_id).first()
        # lấy index_drag
        index_max = db.session.query(TestCasesTestSets).filter(TestCasesTestSets.test_set_id == test_set.id).count()
        query = TestCasesTestSets.query.filter(TestCasesTestSets.test_set_id == test_set.id) \
            .filter(TestCasesTestSets.index == index_drag).first()
        if index_drag > index_drop:
            if index_drop < 1:
                return send_error(message=f'Must be a value between 1 and {index_max}')
            TestCasesTestSets.query.filter(TestCasesTestSets.test_set_id == test_set.id)\
                .filter(TestCasesTestSets.index > index_drop - 1).filter(TestCasesTestSets.index < index_drag)\
                .update(dict(index=TestCasesTestSets.index + 1))
            query.index = index_drop
            db.session.flush()
        else:
            if index_drop > index_max:
                return send_error(message=f'Must be a value between 1 and {index_max}')
            TestCasesTestSets.query.filter(TestCasesTestSets.test_set_id == test_set.id)\
                .filter(TestCasesTestSets.index > index_drag).filter(TestCasesTestSets.index < index_drop + 1)\
                .update(dict(index=TestCasesTestSets.index - 1))
            query.index = index_drop
            db.session.flush()
        db.session.commit()
        # save history
        save_history_test_set(test_set.id, user_id, 3, 1, [query.test_case_id], [index_drag, index_drop])
        return send_result(message='Update successfully')
    except Exception as ex:
        db.session.rollback()
        return send_error(message=str(ex))




