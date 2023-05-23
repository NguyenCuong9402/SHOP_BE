import json
import uuid
from operator import or_

from flask import Blueprint, request
from flask_jwt_extended import get_jwt_identity
from sqlalchemy import func, asc, and_

from app.api.v1.test_run_field.test_run_field_validator import CreateTestRunField, UpdateTestRunField
from app.gateway import authorization_require
from app.models import TestType, db, TestRunField
from app.utils import send_result, send_error, validate_request
from app.validator import TestRunFieldSchema

api = Blueprint('test_run_field', __name__)


@api.route("/<project_id>", methods=["GET"])
@authorization_require()
def get_test_run_field(project_id):
    try:
        token = get_jwt_identity()
        cloud_id = token.get('cloudId')
        test_run_fields = db.session.query(TestRunField).filter(
            or_(TestRunField.project_id == project_id, TestRunField.project_key == project_id),
            TestRunField.cloud_id == cloud_id).order_by(asc(TestRunField.index)).all()
        result = TestRunFieldSchema(many=True).dump(test_run_fields)
        return send_result(data=result, message="OK")
    except Exception as ex:
        db.session.rollback()
        return send_error(message="Something wrong!")


@api.route("/<project_id>", methods=["POST"])
@authorization_require()
def create_test_run_field(project_id):
    """
    Update or create miscellaneous setting
    """

    try:
        token = get_jwt_identity()
        cloud_id = token.get('cloudId')

        is_valid, data, body_request = validate_request(CreateTestRunField(), request)

        if not is_valid:
            return send_error(data=data, code=200, is_dynamic=True)

        # Check coincided name
        coincided = check_coincided_name(name=body_request.get('name'), cloud_id=cloud_id, project_id=project_id)
        if coincided is True:
            return send_error(code=200, data={"name": "Test Run Custom Field already exists. Please try again"},
                              message='Invalid request', show=False, is_dynamic=True)

        # Create new test step
        max_index = db.session.query(func.max(TestRunField.index)).scalar()
        if max_index is None:
            max_index = 0
        max_index = max_index + 1
        test_run_field = TestRunField(
            id=str(uuid.uuid4()),
            project_id=project_id,
            cloud_id=cloud_id,
            name=body_request.get('name'),
            description=body_request.get('description', ''),
            is_required=body_request['is_required'],
            type=body_request['type'],
            type_values=json.dumps(body_request['field_type_values']),
            index=max_index
        )
        db.session.add(test_run_field)
        db.session.flush()

        # Add test type
        test_type_ids = body_request.get('test_types', [])
        test_run_field.test_types = TestType.query.filter(TestType.id.in_(test_type_ids)).all()
        db.session.commit()
        return send_result(data=TestRunFieldSchema().dump(test_run_field), message="Test Run Custom Field created",
                           show=True)
    except Exception as ex:
        db.session.rollback()
        return send_error(data='', message="Something was wrong!")


@api.route("/<project_id>/<test_run_field_id>", methods=["PUT"])
@authorization_require()
def update_test_run_field(project_id, test_run_field_id):

    try:
        token = get_jwt_identity()
        cloud_id = token.get('cloudId')
        test_run_field = TestRunField.get_by_id(test_run_field_id)
        if test_run_field is None:
            return send_error(
                message="Test Run Custom Fields have been changed \n Please refresh the page to view the changes",
                code=200,
                show=False, is_dynamic=True)

        try:
            json_req = request.get_json()
        except Exception as ex:
            return send_error(message="Request Body incorrect json format: " + str(ex), code=442)

        is_valid, data, body_request = validate_request(UpdateTestRunField(), request)

        if not is_valid:
            return send_error(data=data, code=200, is_dynamic=True)

        # Strip body request
        for key, value in json_req.items():
            if isinstance(value, str):
                body_request.setdefault(key, value.strip())
            else:
                body_request.setdefault(key, value)

        # Check coincided name
        coincided = check_coincided_name(name=body_request.get('name'), self_id=test_run_field_id, cloud_id=cloud_id,
                                         project_id=project_id)
        if coincided is True:
            return send_error(code=200, data={"name": "Test Run Custom Field already exists. Please try again"},
                              message='Invalid request', show=False, is_dynamic=True)

        # Update new test step
        if body_request.get('field_type_values') is not None:
            body_request['type_values'] = json.dumps(body_request.get('field_type_values'))
            del body_request['field_type_values']

        # Update test type
        if body_request.get('test_types') is not None:
            test_type_ids = body_request['test_types']
            test_run_field.test_types.clear()
            test_run_field.test_types = TestType.query.filter(TestType.id.in_(test_type_ids)).all()
            del body_request['test_types']

        # Update other props
        update_data = body_request.items()
        for key, value in update_data:
            setattr(test_run_field, key, value)
        db.session.commit()
        return send_result(data=TestRunFieldSchema().dump(test_run_field),
                           message="Test Run Custom Fields were saved successfully", show=True)
    except Exception as ex:
        db.session.rollback()
        return send_error(data='', message="Something was wrong!")


@api.route("/reorder/<project_id>", methods=["POST"])
@authorization_require()
def reorder(project_id):
    try:
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

        # Reorder all test step
        ids = body_request['ids']
        for _id in ids:
            index = ids.index(_id)
            test_step = TestRunField.get_by_id(_id)
            test_step.index = index + 1
            db.session.flush()

        db.session.commit()
        return send_result(data="", message="Order has been changed successfully", show=True)
    except Exception as ex:
        db.session.rollback()
        return send_error(data='', message="Something was wrong!", show=True)


@api.route("/<project_id>/<test_run_field_id>", methods=["DELETE"])
@authorization_require()
def delete(project_id, test_run_field_id):
    try:
        test_run_field = TestRunField.get_by_id(test_run_field_id)
        if test_run_field is None:
            return send_error(
                message="Test Run Custom Fields have been changed \n Please refresh the page to view the changes",
                code=200,
                show=False, is_dynamic=True)
        db.session.delete(test_run_field)
        db.session.commit()
        return send_result(data="", message="Test Run Custom Field removed successfully", code=200, show=True)
    except Exception as ex:
        db.session.rollback()
        return send_error(data='', message="Something was wrong!")


"""
Helper function
"""


def check_coincided_name(name='', self_id=None, project_id='', cloud_id=''):
    existed_test_step = TestRunField.query.filter(
        and_(TestRunField.name == name, TestRunField.id != self_id, TestRunField.cloud_id == cloud_id,
             TestRunField.project_id == project_id)).first()
    if existed_test_step is None:
        return False
    return True
