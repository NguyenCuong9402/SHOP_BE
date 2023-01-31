import json
import uuid
from operator import or_

from flask import Blueprint, request
from flask_jwt_extended import get_jwt_identity

from sqlalchemy import func, asc, and_

from app.api.v1.test_type.test_type_validator import CreateTestType, UpdateTestType
from app.gateway import authorization_require
from app.models import TestType, db
from app.utils import send_result, send_error, validate_request, get_timestamp_now
from app.validator import TestTypeSchema

api = Blueprint('test_type', __name__)


@api.route("/<project_id>", methods=["GET"])
@authorization_require()
def get_test_type(project_id):
    try:
        token = get_jwt_identity()
        cloud_id = token.get('cloudId')
        test_types_count = db.session.query(TestType).filter(
            or_(TestType.project_id == project_id, TestType.project_key == project_id),
            TestType.cloud_id == cloud_id).count()
        if test_types_count == 0:
            test_type = TestType(
                id=str(uuid.uuid4()),
                name=DEFAULT_DATA['name'],
                kind=DEFAULT_DATA['kind'],
                is_default=DEFAULT_DATA['is_default'],
                index=DEFAULT_DATA['index'],
                project_id=project_id,
                cloud_id=cloud_id,
                created_date=get_timestamp_now()

            )
            db.session.add(test_type)
        db.session.commit()
        test_types = db.session.query(TestType).filter(
            or_(TestType.project_id == project_id, TestType.project_key == project_id),
            TestType.cloud_id == cloud_id).order_by(asc(TestType.created_date)).all()
        result = TestTypeSchema(many=True).dump(test_types)
        return send_result(data=result, message="OK")
    except Exception as ex:
        db.session.rollback()
        return send_error(message="Something wrong!")


@api.route("/<project_id>", methods=["POST"])
@authorization_require()
def create_test_type(project_id):
    try:
        token = get_jwt_identity()
        cloud_id = token.get('cloudId')
        is_valid, data, body_request = validate_request(CreateTestType(), request)
        if not is_valid:
            return send_error(data=data, code=200, is_dynamic=True)

        # Check coincided name
        coincided = check_coincided_name(name=body_request.get('name'), cloud_id=cloud_id, project_id=project_id)
        if coincided is True:
            return send_error(code=200, data={"name": "Test Type Option already exists. Please try again"},
                              message='Invalid request', show=False, is_dynamic=True)

        test_type = TestType(
            id=str(uuid.uuid4()),
            name=body_request['name'],
            kind="Steps",
            is_default=False,
            project_id=project_id,
            cloud_id=cloud_id,
            created_date=get_timestamp_now()
        )
        db.session.add(test_type)
        db.session.commit()
        return send_result(data=TestTypeSchema().dump(test_type), message="Test Type created", show=True)
    except Exception as ex:
        db.session.rollback()
        return send_error(message="Something wrong!", code=200, show=False)


@api.route("/<project_id>/<test_type_id>", methods=["DELETE"])
@authorization_require()
def delete(project_id, test_type_id):
    try:
        test_type = TestType.get_by_id(test_type_id)
        test_type_name = test_type.name
        if test_type is None or test_type.is_default:
            return send_error(
                message="Test Type have been changed \n Please refresh the page to view the changes",
                code=200,
                show=False)
        db.session.delete(test_type)
        db.session.commit()
        return send_result(data="", message=f"Test Type {test_type_name} removed", code=200, show=True)
    except Exception as ex:
        db.session.rollback()
        return send_error(data='', message="Something was wrong!")


@api.route("/<project_id>/<test_type_id>", methods=["PUT"])
@authorization_require()
def update(project_id, test_type_id):
    try:
        test_type = TestType.get_by_id(test_type_id)
        if test_type is None:
            return send_error(
                message="Test Type have been changed \n Please refresh the page to view the changes",
                code=200,
                show=False)
        is_valid, data, body_request = validate_request(UpdateTestType(), request)
        if not is_valid:
            return send_error(data=data, code=200, is_dynamic=True)
        for key, value in body_request:
            setattr(test_type, key, value)
        db.session.commit()
        return send_result(data="", message="Project Test Type settings saved", code=200, show=True)
    except Exception as ex:
        db.session.rollback()
        return send_error(data='', message="Something was wrong!")

# @api.route("/tests/<project_id>", methods=["POST"])
# @authorization_require()
# def get_tests_by_test_type(project_id):
#     try:
#
#         return send_result(data=TestTypeSchema().dump(test_type), message="Test Type created", show=True)
#     except Exception as ex:
#         db.session.rollback()
#         return send_error(message="Something wrong!", code=200, show=False)



"""
Helper function
"""


def check_coincided_name(name='', self_id=None, project_id='', cloud_id=''):
    existed_test_step = TestType.query.filter(
        and_(TestType.name == name, TestType.id != self_id, TestType.cloud_id == cloud_id,
             TestType.project_id == project_id)).first()
    if existed_test_step is None:
        return False
    return True


DEFAULT_DATA = {
    "name": "Manual",
    "kind": "Steps",
    "is_default": True,
    "index": 0
}
