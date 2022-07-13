import uuid

from flask import Blueprint, request
from flask_jwt_extended import jwt_required, get_jwt_identity, create_access_token

from app.models import TestStep, Test, TestType, db, MapTestExec, TestTimer, Defects, TestEvidence, TestStepDetail
from app.utils import send_result, send_error, data_preprocessing, get_timestamp_now
from app.validator import TestRunSchema, DefectsValidator, EvidenceValidator, CommentValidator
from app.parser import TestSchema, TestTypeSchema

api = Blueprint('test-run', __name__)

"""
Function helper
"""


# @api.route("/<exec_id>", methods=["GET"])
# def get_all_test_run(exec_id):
#     return send_result(message="OK")


@api.route("/<test_run_id>", methods=["GET"])
def get_test_run(test_run_id):
    try:
        test_run = MapTestExec.query.filter(MapTestExec.id == test_run_id).first()
        test_run_dump = TestRunSchema().dump(test_run)
        return send_result(data=test_run_dump, message="OK")
    except Exception as e:
        return send_error(data=e.__str__())


@api.route("/<test_run_id>", methods=["GET"])
def get_test_before_after(test_run_id):
    return send_result(message="OK")


@api.route("/<test_run_id>/defects", methods=["POST"])
def create_defects(test_run_id):
    try:
        json_req = request.get_json()
    except Exception as ex:
        return send_error(message="Request Body incorrect json format: " + str(ex), code=442)

    # # logged input fields
    # logged_input(json.dumps(json_req))

    # validate request body
    validator_input = DefectsValidator()
    is_not_validate = validator_input.validate(json_req)
    if is_not_validate:
        return send_error(data=is_not_validate, code=442)

    _id = get_jwt_identity()

    test_issue_id = json_req.get("test_issue_id")
    test_issue_key = json_req.get("test_issue_key")

    new_defects = Defects(id=_id, map_test_exec_id=test_run_id, test_issue_id=test_issue_id,
                          test_issue_key=test_issue_key, created_date=get_timestamp_now())
    db.session.add(new_defects)
    db.session.commit()

    return send_result(message="OK")


@api.route("/<test_run_id>/defects", methods=["DELETE"])
def delete_defects(test_run_id):
    return send_result(message="OK")


@api.route("/<test_run_id>/evidence", methods=["POST"])
def create_evidence(test_run_id):
    try:
        json_req = request.get_json()
    except Exception as ex:
        return send_error(message="Request Body incorrect json format: " + str(ex), code=442)

    # # logged input fields
    # logged_input(json.dumps(json_req))

    # validate request body
    validator_input = EvidenceValidator()
    is_not_validate = validator_input.validate(json_req)
    if is_not_validate:
        return send_error(data=is_not_validate, code=442)

    _id = get_jwt_identity()

    name_file = json_req.get("name_file")
    url_file = json_req.get("url_file")

    new_defects = TestEvidence(id=_id, map_test_exec_id=test_run_id, name_file=name_file,
                               url_file=url_file, created_date=get_timestamp_now())
    db.session.add(new_defects)
    db.session.commit()

    return send_result(message="OK")


@api.route("/<test_run_id>/evidence", methods=["DELETE"])
def delete_evidence(test_run_id):
    return send_result(message="OK")


@api.route("/<test_run_id>/comment", methods=["PUT"])
def update_comment(test_run_id):
    try:
        json_req = request.get_json()
    except Exception as ex:
        return send_error(message="Request Body incorrect json format: " + str(ex), code=442)

    # # logged input fields
    # logged_input(json.dumps(json_req))

    # validate request body
    validator_input = CommentValidator()
    is_not_validate = validator_input.validate(json_req)
    if is_not_validate:
        return send_error(data=is_not_validate, code=442)

    content = json_req.get("content", "")
    test_run = MapTestExec.query.filter(MapTestExec.id == test_run_id).first()
    test_run.comment = content
    db.session.commit()
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


@api.route("/<test_run_id>/test-step/<test_step_id>/comment", methods=["PUT"])
def update_comment_test_step(test_run_id, test_step_id):
    try:
        json_req = request.get_json()
    except Exception as ex:
        return send_error(message="Request Body incorrect json format: " + str(ex), code=442)

    # # logged input fields
    # logged_input(json.dumps(json_req))

    # validate request body
    validator_input = CommentValidator()
    is_not_validate = validator_input.validate(json_req)
    if is_not_validate:
        return send_error(data=is_not_validate, code=442)

    content = json_req.get("content", "")
    test_run_detail = TestStepDetail.query.filter(MapTestExec.id == test_run_id,
                                                  TestStepDetail.id == test_step_id).first()
    test_run_detail.comment = content
    test_run_detail.modified_date = get_timestamp_now()
    db.session.commit()

    return send_result(message="OK")


@api.route("/<test_run_id>/test-step/<test_step_id>/status", methods=["PUT"])
def update_test_step_status(test_run_id):
    return send_result(message="OK")
