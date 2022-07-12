import uuid

from flask import Blueprint, request
from flask_jwt_extended import jwt_required, get_jwt_identity, create_access_token

from app.models import TestStep, Test, TestType, db
from app.utils import send_result, send_error, data_preprocessing
from app.validator import CreateTestValidator
from app.parser import TestSchema, TestTypeSchema

api = Blueprint('test-run', __name__)


@api.route("/<test_run_id>", methods=["GET"])
def get_test(test_run_id):
    test = Test.query.filter_by().first()
    test = TestSchema().dump(test)
    return send_result(data=test, message="OK")


@api.route("/<test_run_id>/comment", methods=["POST"])
def create_comment():
    return send_result(message="OK")


@api.route("/<test_run_id>/evidence", methods=["POST"])
def create_evidence():
    return send_result(message="OK")


@api.route("/<test_run_id>/activity", methods=["POST"])
def create_activity():
    return send_result(message="OK")


@api.route("/<test_run_id>/defects", methods=["POST"])
def create_defects():
    return send_result(message="OK")


@api.route("/<test_run_id>/status", methods=["PUT"])
def delete_test(test_run_id):
    return send_result(message="OK")


@api.route("/<test_run_id>/test-step/<test_step_id>/comment", methods=["POST"])
def create_comment_test_step(test_run_id, test_step_id):
    return send_result(message="OK")


@api.route("/<test_run_id>/test-step/<test_step_id>/comment", methods=["POST"])
def create_comment_test_step(test_run_id, test_step_id):
    return send_result(message="OK")


@api.route("/<test_run_id>/test-step/<test_step_id>/comment", methods=["POST"])
def create_comment_test_step(test_run_id, test_step_id):
    return send_result(message="OK")
