import uuid

from flask import Blueprint, request
from flask_jwt_extended import jwt_required, get_jwt_identity, create_access_token

from app.models import TestStep, Test, TestType, db, TestField
from app.utils import send_result, send_error, data_preprocessing
from app.validator import CreateTestValidator
from app.parser import TestFieldSchema, TestStepSchema

api = Blueprint('settings', __name__)


@api.route("/fields/<project_id>", methods=["GET"])
def get_test_types_by_project(project_id):
    test = TestField.query.filter_by().all()
    test = TestFieldSchema().dump(test)
    return send_result(data=test, message="OK")


@api.route("/test-steps/<project_id>", methods=["GET"])
def get_test_steps_by_project(project_id):
    result = TestStep.query.filter_by().all()
    result = TestStepSchema().dump(result)
    return send_result(data=result, message="OK")