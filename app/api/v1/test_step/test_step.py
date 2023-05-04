import json
import uuid
from operator import or_
from flask import Blueprint, request
from flask_jwt_extended import get_jwt_identity
from sqlalchemy import func, asc, and_

from app.api.v1.history_test import save_history_test_step
from app.gateway import authorization_require
from app.models import TestStep, db, TestStepField, TestRunField, TestCase, TestStepDetail, HistoryTest
from app.parser import TestStepSchema
from app.utils import send_result, send_error, data_preprocessing, get_timestamp_now
from app.api.v1.test_step_field.test_step_field import DEFAULT_DATA

api = Blueprint('test_step', __name__)


@api.route("/<test_case_id>", methods=["POST"])
@authorization_require()
def add_test_step(test_case_id):
    try:
        token = get_jwt_identity()
        cloud_id = token.get('cloudId')
        project_id = token.get('projectId')
        user_id = token.get('userId')
        test_case = TestCase.query.filter(TestCase.id == test_case_id).first()
        if test_case is None:
            return send_error(
                message="Test Case is not Exist", code=200,
                show=False)
        try:
            json_req = request.get_json()
        except Exception as ex:
            return send_error(message="Request Body incorrect json format: " + str(ex), code=442)
        # Strip body request
        body_request = {}
        for key, value in json_req.items():
            if isinstance(value, str):
                body_request.setdefault(key, value.strip())
            else:
                body_request.setdefault(key, value)
        count_index = TestStep.query.filter(TestStep.test_case_id == test_case_id).count()
        test_step_id = str(uuid.uuid4())
        test_step = TestStep(
            id=test_step_id,
            cloud_id=cloud_id,
            project_id=project_id,
            action=body_request.get('action'),
            data=body_request.get('data'),
            result=body_request.get('result'),
            custom_fields=body_request.get('custom_fields'),
            index=count_index + 1,
            test_case_id=test_case_id,
            created_date=get_timestamp_now()
        )
        db.session.add(test_step)
        db.session.flush()

        test_step_fields = db.session.query(TestStepField).filter(
            or_(TestStepField.project_id == project_id, TestStepField.project_key == project_id),
            TestStepField.cloud_id == cloud_id).order_by(TestStepField.index.asc())
        test_step_fields_count = test_step_fields.count()
        detail_of_action = {}  # detail_of_action of history
        if test_step_fields_count == 0:
            """
            Create default test step field
            """
            test_step_field_ids = []
            for test_step_field in DEFAULT_DATA:
                test_step_field = TestStepField(
                    id=str(uuid.uuid4()),
                    name=test_step_field['name'],
                    description=test_step_field['description'],
                    type=test_step_field['type'],
                    is_required=test_step_field['is_required'],
                    is_disabled=test_step_field['is_disabled'],
                    is_native=test_step_field['is_native'],
                    index=test_step_field['index'],
                    type_values=test_step_field['type_values'],
                    project_id=project_id,
                    cloud_id=cloud_id,
                )
                db.session.add(test_step_field)
                db.session.flush()
                test_step_field_ids.append(test_step_field.id)
            for id_field in test_step_field_ids:
                test_step_detail = TestStepDetail(
                    id=str(uuid.uuid4()),
                    test_step_id=test_step_id,
                    test_step_field_id=id_field,
                    created_date=get_timestamp_now()
                )
                db.session.add(test_step_detail)
                db.session.flush()
                detail_of_action['Action'] = test_step.action
                detail_of_action['Data'] = test_step.data
                detail_of_action['Expected Result'] = test_step.result
        else:
            for test_step_field in test_step_fields:
                test_step_detail = TestStepDetail(
                    id=str(uuid.uuid4()),
                    test_step_id=test_step_id,
                    test_step_field_id=test_step_field.id,
                    created_date=get_timestamp_now()
                )
                db.session.add(test_step_detail)
                db.session.flush()
            # create detail_of_action
            field_name = [item.name for item in test_step_fields]
            detail_of_action['Action'] = test_step.action
            detail_of_action['Data'] = test_step.data
            detail_of_action['Expected Result'] = test_step.result
            for i, name in enumerate(test_step.custom_fields):
                detail_of_action[field_name[3+i]] = name
            db.session.flush()
        db.session.commit()
        # Save history
        save_history_test_step(test_case_id, user_id, 1, 2, detail_of_action, [count_index+1])
        return send_result(data='add success')
    except Exception as ex:
        db.session.rollback()
        return send_error(message=str(ex))


@api.route("/<test_case_id>/<test_step_id>", methods=["DELETE"])
@authorization_require()
def remove_test_step(test_step_id, test_case_id):
    try:
        token = get_jwt_identity()
        cloud_id = token.get('cloudId')
        project_id = token.get('projectId')
        user_id = token.get('userId')
        test_step = TestStep.query.filter(TestStep.id == test_step_id).first()
        if test_step is None:
            return send_error(
                message="Test Step is not exist",
                code=200, show=False)
        # create detail_of_action
        detail_of_action = {}
        test_step_fields = db.session.query(TestStepField).filter(
            or_(TestStepField.project_id == project_id, TestStepField.project_key == project_id),
            TestStepField.cloud_id == cloud_id).order_by(TestStepField.index.asc())
        field_name = [item.name for item in test_step_fields]
        detail_of_action['Action'] = test_step.action
        detail_of_action['Data'] = test_step.data
        detail_of_action['Expected Result'] = test_step.result
        for i, name in enumerate(test_step.custom_fields):
            detail_of_action[field_name[3+i]] = name
        index = test_step.index
        # delete test_step
        TestStepDetail.query.filter(TestStepDetail.test_step_id == test_step_id).delete()
        TestStep.query.filter(TestStep.test_case_id == test_case_id).filter(TestStep.index > test_step.index) \
            .update(dict(index=TestStep.index - 1))
        db.session.delete(test_step)
        db.session.flush()
        db.session.commit()
        # Save history
        save_history_test_step(test_case_id, user_id, 2, 2, detail_of_action, [index])
        return send_result(data="", message="Test step removed successfully", code=200, show=True)
    except Exception as ex:
        db.session.rollback()
        return send_error(data='', message=str(ex))


@api.route("/<test_case_id>", methods=["PUT"])
@authorization_require()
def change_rank_test_step(test_case_id):
    try:
        token = get_jwt_identity()
        cloud_id = token.get('cloudId')
        project_id = token.get('projectId')
        user_id = token.get('userId')
        query = TestStep.query.filter(or_(TestStep.project_id == project_id, TestStep.project_key == project_id),
                                      TestStep.cloud_id == cloud_id, TestStep.test_case_id == test_case_id).all()
        if query is None:
            return send_error(message='PROJECT DOES NOT EXIST', status=404, show=False)

        json_req = request.get_json()
        index_drag = json_req['index_drag']
        index_drop = json_req['index_drop']
        index_max = db.session.query(TestStep).filter(
            or_(TestStep.project_id == project_id, TestStep.project_key == project_id),
            TestStep.cloud_id == cloud_id, TestStep.test_case_id == test_case_id).count()
        # vị trí drag to drop
        index_drag_to_drop = TestStep.query.filter(
            or_(TestStep.project_id == project_id, TestStep.project_key == project_id), TestStep.cloud_id == cloud_id,
            TestStep.test_case_id == test_case_id).filter(TestStep.index == index_drag).first()
        if index_drag > index_drop:
            if index_drop < 1:
                return send_error(message=f'Must be a value between 1 and {index_max}', status=404, show=False)
            TestStep.query.filter(or_(TestStep.project_id == project_id, TestStep.project_key == project_id),
                                  TestStep.cloud_id == cloud_id, TestStep.test_case_id == test_case_id) \
                .filter(TestStep.index > index_drop - 1, TestStep.index < index_drag) \
                .update(dict(index=TestStep.index + 1))
            index_drag_to_drop.index = index_drop
            db.session.flush()
        else:
            if index_drop > index_max:
                return send_error(message=f'Must be a value between 1 and {index_max}', status=404, show=False)
            TestStep.query.filter(or_(TestStep.project_id == project_id, TestStep.project_key == project_id),
                                  TestStep.cloud_id == cloud_id, TestStep.test_case_id == test_case_id) \
                .filter(TestStep.index < index_drop + 1, TestStep.index > index_drag) \
                .update(dict(index=TestStep.index - 1))
            index_drag_to_drop.index = index_drop
            db.session.flush()
        db.session.commit()
        # Save history
        save_history_test_step(test_case_id, user_id, 3, 2, {}, [index_drag, index_drop])
        return send_result(data="", message="success", code=200, show=True)
    except Exception as ex:
        db.session.rollback()
        return send_error(data='', message=str(ex))


@api.route("/<test_case_id>/call/<test_case_id_reference>", methods=["POST"])
@authorization_require()
def call_test_case(test_case_id, test_case_id_reference):
    try:
        token = get_jwt_identity()
        cloud_id = token.get('cloudId')
        project_id = token.get('projectId')
        user_id = token.get('userId')
        test_case = TestCase.query.filter(TestCase.id == test_case_id).first()
        test_case_reference = TestCase.query.filter(TestCase.id == test_case_id_reference).first()
        if test_case is None:
            return send_error(
                message="Test Case is not Exist", code=200, show=False)
        if test_case_reference is None:
            return send_error(message="Call test case reference fail", code=200, show=False)
        count_index = TestStep.query.filter(TestStep.test_case_id == test_case_id).count()
        test_step = TestStep(
            id=str(uuid.uuid4()),
            cloud_id=cloud_id,
            project_id=project_id,
            index=count_index + 1,
            test_case_id=test_case_id,
            test_case_id_reference=test_case_id_reference,
            created_date=get_timestamp_now()
        )
        db.session.add(test_step)
        db.session.flush()
        db.session.commit()
        # Create detail_of_action and Save history
        detail_of_action = {"Call test": test_case_reference.issue_key}
        save_history_test_step(test_case_id, user_id, 5, 2, detail_of_action, [test_step.index + 1])
        return send_result(data='call success')
    except Exception as ex:
        db.session.rollback()
        return send_error(data='', message="Something was wrong!")


@api.route("/<test_case_id>/<test_step_id>", methods=["POST"])
@authorization_require()
def clone_test_step(test_case_id, test_step_id):
    try:
        token = get_jwt_identity()
        cloud_id = token.get('cloudId')
        project_id = token.get('projectId')
        user_id = token.get('userId')
        test_step = TestStep.query.filter(TestStep.test_case_id == test_case_id, TestStep.id == test_step_id).first()
        if test_step is None:
            return send_error(
                message="Test Step is not exist", code=200,
                show=False)
        # Sắp xếp lại index khi clone
        TestStep.query.filter(TestStep.test_case_id == test_case_id) \
            .filter(TestStep.index > test_step.index) \
            .update(dict(index=TestStep.index + 1))
        db.session.flush()
        # Create new test step
        clone_test_step_id = str(uuid.uuid4())
        test_step_clone = TestStep(
            id=clone_test_step_id,
            cloud_id=cloud_id,
            project_id=project_id,
            action=test_step.action,
            data=test_step.data,
            result=test_step.result,
            custom_fields=test_step.custom_fields,
            index=test_step.index + 1,
            test_case_id=test_case_id,
            created_date=get_timestamp_now()
        )
        db.session.add(test_step_clone)
        db.session.flush()
        test_step_fields = db.session.query(TestStepField).filter(
            or_(TestStepField.project_id == project_id, TestStepField.project_key == project_id),
            TestStepField.cloud_id == cloud_id).order_by(TestStepField.index.asc())
        for test_step_field in test_step_fields:
            test_step_detail = TestStepDetail(
                id=str(uuid.uuid4()),
                test_step_id=clone_test_step_id,
                test_step_field_id=test_step_field.id,
                created_date=get_timestamp_now()
            )
            db.session.add(test_step_detail)
            db.session.flush()
        db.session.commit()
        # Create detail_of_action and Save history
        detail_of_action = {}
        field_name = [item.name for item in test_step_fields]
        detail_of_action['Action'] = test_step.action
        detail_of_action['Data'] = test_step.data
        detail_of_action['Expected Result'] = test_step.result
        for i, name in enumerate(test_step.custom_fields):
            detail_of_action[field_name[3+i]] = name
        save_history_test_step(test_case_id, user_id, 4, 2, detail_of_action, [test_step.index + 1])
        return send_result(data='', message="Step clone successfully",
                           show=True)
    except Exception as ex:
        db.session.rollback()
        return send_error(data='', message="Something was wrong!")

