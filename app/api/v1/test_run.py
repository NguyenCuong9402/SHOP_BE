import uuid

from flask import Blueprint, request
from flask_jwt_extended import jwt_required, get_jwt_identity, create_access_token

from app.models import TestStep, Test, TestType, db, MapTestExec, TestTimer, Defects, TestEvidence, TestStepDetail, \
    TestStatus, TestActivity
from app.utils import send_result, send_error, data_preprocessing, get_timestamp_now
from app.validator import TestRunSchema, DefectsValidator, EvidenceValidator, CommentValidator, TestStatusValidator, \
    TestTimerValidator, TestRunBackNextSchema, TestActivityValidator, TestActivitySchema, TestTimerSchema
from sqlalchemy import desc, func, asc, or_, and_, text, cast, Numeric

api = Blueprint('test-run', __name__)

"""
Function helper
"""


# @api.route("/<exec_id>", methods=["GET"])
# def get_all_test_run(exec_id):
#     return send_result(message="OK")


@api.route("/<test_run_id>", methods=["GET"])
def get_test_run(test_run_id):
    """
    Author: phongnv
    Create Date: 13/07/2022
    Handle get test run
    """
    try:
        test_run = MapTestExec.query.filter(MapTestExec.id == test_run_id).first()
        test_run_dump = TestRunSchema().dump(test_run)
        return send_result(data=test_run_dump, message="OK")
    except Exception as e:
        return send_error(data=e.__str__())


@api.route("/<test_run_id>/back-next", methods=["GET"])
def get_test_back_next(test_run_id):
    """
    Author: phongnv
    Create Date: 13/07/2022
    Handle get back next
    """

    result = {
        "back_id": "",
        "next_id": ""
    }

    test_run = MapTestExec.query.filter(MapTestExec.id == test_run_id).first()
    back_test = MapTestExec.query.order_by(desc(MapTestExec.index)).filter(
        MapTestExec.exec_id == test_run.exec_id, MapTestExec.id != test_run.id,
        MapTestExec.index < test_run.index).first()
    if back_test is not None:
        result["back_id"] = back_test.id

    next_test = MapTestExec.query.order_by(asc(MapTestExec.index)).filter(
        MapTestExec.exec_id == test_run.exec_id, MapTestExec.id != test_run.id,
        MapTestExec.index > test_run.index).first()

    if next_test is not None:
        result["next_id"] = next_test.id

    try:
        result_dump = TestRunBackNextSchema().dump(result)
        return send_result(data=result_dump, message="OK")
    except Exception as ex:
        return send_error(message="Request back-next: " + str(ex), code=442)


@api.route("/<test_run_id>/defects", methods=["POST"])
def create_defects(test_run_id):
    """
    Author: phongnv
    Create Date: 13/07/2022
    Handle create defects
    """
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

    _id = str(uuid.uuid1())

    test_issue_id = json_req.get("test_issue_id")
    test_issue_key = json_req.get("test_issue_key")

    new_defects = Defects(id=_id, map_test_exec_id=test_run_id, test_issue_id=test_issue_id,
                          test_issue_key=test_issue_key, created_date=get_timestamp_now())
    db.session.add(new_defects)
    db.session.commit()

    return send_result(message="OK")


@api.route("/<test_run_id>/defects/<defect_id>", methods=["DELETE"])
def delete_defects(test_run_id, defect_id):
    """
    Author: phongnv
    Create Date: 13/07/2022
    Handle delete defects
    """
    defects = Defects.query.filter(Defects.map_test_exec_id == test_run_id,
                                   Defects.id == defect_id).first()
    if defects is None:
        return send_error(message=" Test defects id {0} is none".format(defect_id), code=442)
    try:
        Defects.query.filter(Defects.map_test_exec_id == test_run_id,
                             Defects.id == defect_id).delete()
        db.session.commit()
    except Exception as ex:
        return send_error(message="Delete defects error: " + str(ex), code=442)
    return send_result(message="OK")


@api.route("/<test_run_id>/evidence", methods=["POST"])
def create_evidence(test_run_id):
    """
    Author: phongnv
    Create Date: 13/07/2022
    Handle create evidence
    """
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

    _id = str(uuid.uuid1())

    name_file = json_req.get("name_file")
    url_file = json_req.get("url_file")

    new_evidence = TestEvidence(id=_id, map_test_exec_id=test_run_id, name_file=name_file,
                                url_file=url_file, created_date=get_timestamp_now())
    db.session.add(new_evidence)
    db.session.commit()

    return send_result(message="OK")


@api.route("/<test_run_id>/evidences/<evidence_id>", methods=["DELETE"])
def delete_evidence(test_run_id, evidence_id):
    """
    Author: phongnv
    Create Date: 13/07/2022
    Handle delete evidence
    """
    test_evidence = TestEvidence.query.filter(TestEvidence.map_test_exec_id == test_run_id,
                                              TestEvidence.id == evidence_id).first()
    if test_evidence is None:
        return send_error(message=" Test defects id {0} is none".format(evidence_id), code=442)
    try:
        TestEvidence.query.filter(TestEvidence.map_test_exec_id == test_run_id,
                                  TestEvidence.id == evidence_id).delete()
        db.session.commit()
    except Exception as ex:
        return send_error(message="Delete evidence: " + str(ex), code=442)
    return send_result(message="OK")


@api.route("/<test_run_id>/comments", methods=["PUT"])
def update_comment(test_run_id):
    """
    Author: phongnv
    Create Date: 13/07/2022
    Handle update test comment
    """
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
    if test_run is None:
        return send_error(message=" Test run id {0} is none".format(test_run_id), code=442)
    test_run.comment = content
    db.session.commit()
    return send_result(message="OK")


@api.route("/<test_run_id>/activity", methods=["POST"])
def create_activity(test_run_id):
    """
        Author: phongnv
        Create Date: 13/07/2022
        Handle create evidence
        """
    try:
        json_req = request.get_json()
    except Exception as ex:
        return send_error(message="Request Body incorrect json format: " + str(ex), code=442)

    # # logged input fields
    # logged_input(json.dumps(json_req))

    # validate request body
    validator_input = TestActivityValidator()
    is_not_validate = validator_input.validate(json_req)
    if is_not_validate:
        return send_error(data=is_not_validate, code=442)

    _id = str(uuid.uuid1())

    comment = json_req.get("comment")
    status_change = json_req.get("status_change")
    jira_user_id = json_req.get("jira_user_id")

    new_activity = TestActivity(id=_id, map_test_exec_id=test_run_id, comment=comment,
                                status_change=status_change, jira_user_id=jira_user_id,
                                created_date=get_timestamp_now())
    db.session.add(new_activity)
    db.session.commit()

    new_activity_dump = TestActivitySchema().dump(new_activity)
    return send_result(data=new_activity_dump, message="OK")


@api.route("/<test_run_id>/status", methods=["PUT"])
def update_test_status(test_run_id):
    """
    Author: phongnv
    Create Date: 13/07/2022
    Handle update test status
    """
    try:
        json_req = request.get_json()
    except Exception as ex:
        return send_error(message="Request Body incorrect json format: " + str(ex), code=442)

    # # logged input fields
    # logged_input(json.dumps(json_req))

    # validate request body
    validator_input = TestStatusValidator()
    is_not_validate = validator_input.validate(json_req)
    if is_not_validate:
        return send_error(data=is_not_validate, code=442)

    status_id = json_req.get("status_id", "")

    test_status = TestStatus.query.filter(TestStatus.id == status_id).first()

    if test_status is None:
        return send_error(data={"status_id": "status none"}, code=442)

    map_test_exec = MapTestExec.query.filter(MapTestExec.id == test_run_id).first()
    if map_test_exec is None:
        return send_error(message=" Test test run {0} is none".format(test_run_id), code=442)
    map_test_exec.status_id = status_id
    map_test_exec.modified_date = get_timestamp_now()
    db.session.commit()

    return send_result(message="OK")


@api.route("/<test_run_id>/timer", methods=["POST"])
def create_timer(test_run_id):
    """
    Author: phongnv
    Create Date: 13/07/2022
    Handle update timer
    """
    try:
        json_req = request.get_json()
    except Exception as ex:
        return send_error(message="Request Body incorrect json format: " + str(ex), code=442)

    # # logged input fields
    # logged_input(json.dumps(json_req))

    # validate request body
    validator_input = TestTimerValidator()
    is_not_validate = validator_input.validate(json_req)
    if is_not_validate:
        return send_error(data=is_not_validate, code=442)

    time_type = json_req.get("time_type", 0)
    date_time = json_req.get("date_time", "")

    _id = str(uuid.uuid1())
    new_timer = TestTimer(id=_id, time_type=time_type, date_time=date_time, created_date=get_timestamp_now())
    db.session.add(new_timer)

    db.session.commit()
    new_timer_dump = TestTimerSchema().dump(new_timer)
    return send_result(data=new_timer_dump, message="OK")


@api.route("/<test_run_id>/test-step/<test_step_id>/defects", methods=["POST"])
def create_step_defects(test_run_id, test_step_id):
    """
    Author: phongnv
    Create Date: 13/07/2022
    Handle create step defects
    """
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

    _id = str(uuid.uuid1())

    test_issue_id = json_req.get("test_issue_id")
    test_issue_key = json_req.get("test_issue_key")

    new_defects = Defects(id=_id, test_step_detail_id=test_step_id, test_issue_id=test_issue_id,
                          test_issue_key=test_issue_key, created_date=get_timestamp_now())
    db.session.add(new_defects)
    db.session.commit()
    return send_result(message="OK")


@api.route("/<test_run_id>/test-step/<test_step_id>/defects/<defect_id>", methods=["DELETE"])
def delete_step_defects(test_run_id, test_step_id, defect_id):
    """
    Author: phongnv
    Create Date: 13/07/2022
    Handle delete step defects
    """
    defects = Defects.query.filter(Defects.test_step_detail_id == test_step_id,
                                   Defects.id == defect_id).first()
    if defects is None:
        return send_error(message=" Test defects id {0} is none".format(defect_id), code=442)
    try:
        Defects.query.filter(Defects.test_step_detail_id == test_step_id,
                             Defects.id == defect_id).delete()
        db.session.commit()
    except Exception as ex:
        return send_error(message="Delete defects: " + str(ex), code=442)
    return send_result(message="OK")


@api.route("/<test_run_id>/test-step/<test_step_id>/evidences", methods=["POST"])
def create_step_evidence(test_run_id, test_step_id):
    """
    Author: phongnv
    Create Date: 13/07/2022
    Handle create step evidence
    """
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

    _id = str(uuid.uuid1())

    name_file = json_req.get("name_file")
    url_file = json_req.get("url_file")

    new_evidence = TestEvidence(id=_id, test_step_detail_id=test_step_id,
                                name_file=name_file,
                                url_file=url_file, created_date=get_timestamp_now())
    db.session.add(new_evidence)
    db.session.commit()

    return send_result(message="OK")


@api.route("/<test_run_id>/test-step/<test_step_id>/evidences/<evidence_id>", methods=["DELETE"])
def delete_step_evidence(test_run_id, test_step_id, evidence_id):
    """
    Author: phongnv
    Create Date: 13/07/2022
    Handle delete step evidence
    """

    step_evidence = TestEvidence.query.filter(TestEvidence.test_step_detail_id == test_step_id,
                                              TestEvidence.id == evidence_id).first()
    if step_evidence is None:
        return send_error(message=" Test evidence id {0} is none".format(evidence_id), code=442)
    try:
        TestEvidence.query.filter(TestEvidence.test_step_detail_id == test_step_id,
                                  TestEvidence.id == evidence_id).delete()
        db.session.commit()
    except Exception as ex:
        return send_error(message="Delete evidence: " + str(ex), code=442)
    return send_result(message="OK")


@api.route("/<test_run_id>/test-step/<test_step_id>/comments", methods=["PUT"])
def update_comment_test_step(test_run_id, test_step_id):
    """
    Author: phongnv
    Create Date: 13/07/2022
    Handle update step comment
    """
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
    test_run_detail = TestStepDetail.query.filter(TestStepDetail.id == test_step_id).first()
    if test_run_detail is None:
        return send_error(message=" Test test step run {0} is none".format(test_step_id), code=442)
    test_run_detail.comment = content
    test_run_detail.modified_date = get_timestamp_now()
    db.session.commit()

    return send_result(message="OK")


@api.route("/<test_run_id>/test-step/<test_step_id>/status", methods=["PUT"])
def update_test_step_status(test_run_id, test_step_id):
    """
    Author: phongnv
    Create Date: 13/07/2022
    Handle update step status
    """
    try:
        json_req = request.get_json()
    except Exception as ex:
        return send_error(message="Request Body incorrect json format: " + str(ex), code=442)

    # # logged input fields
    # logged_input(json.dumps(json_req))

    # validate request body
    validator_input = TestStatusValidator()
    is_not_validate = validator_input.validate(json_req)
    if is_not_validate:
        return send_error(data=is_not_validate, code=442)

    status_id = json_req.get("status_id", "")

    test_status = TestStatus.query.filter(TestStatus.id == status_id).first()

    if test_status is None:
        return send_error(data={"status_id": "status none"}, code=442)

    test_run_detail = TestStepDetail.query.filter(TestStepDetail.id == test_step_id).first()
    if test_run_detail is None:
        return send_error(message=" Test test step run {0} is none".format(test_run_detail), code=442)
    test_run_detail.status_id = status_id
    test_run_detail.modified_date = get_timestamp_now()
    db.session.commit()

    return send_result(message="OK")
