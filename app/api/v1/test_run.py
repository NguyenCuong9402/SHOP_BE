import uuid

from flask import Blueprint, request
from flask_jwt_extended import jwt_required, get_jwt_identity, create_access_token

from app.models import TestStep, Test, TestType, db
from app.utils import send_result, send_error, data_preprocessing
from app.validator import TestRunSchema
from app.parser import TestSchema, TestTypeSchema

api = Blueprint('test-run', __name__)

"""
Function helper
"""





@api.route("/<exec_id>", methods=["GET"])
def get_all_test_run(exec_id):
    return send_result(message="OK")


@api.route("/<test_run_id>", methods=["GET"])
def get_test(test_run_id):
    return send_result(message="OK")


@api.route("/<test_run_id>", methods=["GET"])
def get_test_before_after(test_run_id):
    return send_result(message="OK")


@api.route("/<test_run_id>/defects", methods=["POST"])
def create_defects(test_run_id):
    return send_result(message="OK")


@api.route("/<test_run_id>/defects", methods=["DELETE"])
def delete_defects(test_run_id):
    return send_result(message="OK")


@api.route("/<test_run_id>/evidence", methods=["POST"])
def create_evidence(test_run_id):
    return send_result(message="OK")


@api.route("/<test_run_id>/evidence", methods=["DELETE"])
def delete_evidence(test_run_id):
    return send_result(message="OK")


@api.route("/<test_run_id>/comment", methods=["POST"])
def create_comment(test_run_id):
    return send_result(message="OK")


@api.route("/<test_run_id>/comment", methods=["PUT"])
def update_comment(test_run_id):
    return send_result(message="OK")


@api.route("/<test_run_id>/comment", methods=["DELETE"])
def delete_comment(test_run_id):
    return send_result(message="OK")


@api.route("/<test_run_id>/activity", methods=["POST"])
def create_activity(test_run_id):
    return send_result(message="OK")


@api.route("/<test_run_id>/status", methods=["PUT"])
def update_test_status(test_run_id):
    return send_result(message="OK")


@api.route("/<test_run_id>/timer", methods=["PUT"])
def update_timer(test_run_id):
    return send_result(message="OK")


@api.route("/<test_run_id>/test-step/<test_step_id>/defects", methods=["POST"])
def create_step_defects(test_run_id, test_step_id):
    return send_result(message="OK")


@api.route("/<test_run_id>/test-step/<test_step_id>/defects", methods=["DELETE"])
def delete_step_defects(test_run_id, test_step_id):
    return send_result(message="OK")


@api.route("/<test_run_id>/test-step/<test_step_id>/evidence", methods=["POST"])
def create_step_evidence(test_run_id, test_step_id):
    return send_result(message="OK")


@api.route("/<test_run_id>/test-step/<test_step_id>/evidence", methods=["DELETE"])
def delete_step_evidence(test_run_id, test_step_id):
    return send_result(message="OK")


@api.route("/<test_run_id>/test-step/<test_step_id>/comment", methods=["POST"])
def create_comment_test_step(test_run_id, test_step_id):
    return send_result(message="OK")


@api.route("/<test_run_id>/test-step/<test_step_id>/comment", methods=["PUT"])
def update_comment_test_step(test_run_id, test_step_id):
    return send_result(message="OK")


@api.route("/<test_run_id>/test-step/<test_step_id>/comment", methods=["DELETE"])
def delete_comment_test_step(test_run_id, test_step_id):
    return send_result(message="OK")


@api.route("/<test_run_id>/test-step/<test_step_id>/status", methods=["PUT"])
def update_test_step_status(test_run_id):
    return send_result(message="OK")
