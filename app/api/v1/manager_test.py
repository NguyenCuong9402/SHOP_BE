import uuid

from flask import Blueprint, request
from flask_jwt_extended import jwt_required, get_jwt_identity, create_access_token

from app.models import TestStep, Test, TestType
from app.utils import send_result, send_error, data_preprocessing
from app.validator import CreateTestValidator

api = Blueprint('test', __name__)


@api.route("", methods=["POST"])
def create_test():
    """
    Example json request
    {
        "cucumber": "12321",
        "generic": "12321",
        "issue_id": "12321",
        "test_type": "12321",
        "test_set_name": 123,
        "test_step": [
            {
                "data": "123",
                "result": "",
                "customFields": "",
                "attachments": "",
                "action": ""
            }
        ]
    }
    """
    # Step 1: validate json input
    try:
        json_req = request.get_json()
    except Exception as ex:
        return send_error(message="Request body incorrect json format: " + str(ex), code=442)

    # validate request body
    json_valid, message_id, incorrect_data = data_preprocessing(cls_validator=CreateTestValidator, input_json=json_req)
    if not json_valid:
        return send_error(data=incorrect_data, message_id=message_id, code=442)

    test_steps = json_req.get("test_step")
    test_uuid = str(uuid.uuid1())  # generate unique test id

    # STEP 2 check project_id is existed
    # TODO: not necessary
    project_id = json_req.get("project_id", "")

    # STEP 3 check test type is existed, and create if needed
    # TODO: remove create test type in the future, because test type will create when setup btest for a project
    test_type = json_req.get("test_type", "")
    exist_type = TestType.query.filter_by(project_setting_id=project_id, name=test_type)
    # if not exist_type:
    #     # test type not found, create a new one
    #     new_instance = TestType(
    #         id="", value=test_type, type=test_type)

    test_instance = Test(
        id=test_uuid,
        cucumber=json_req.get("cucumber", ""),
        generic=json_req.get("generic", ""),
        issue_id=json_req.get("issue_id", ""),

    )

    for test_step in test_steps:
        new_instance = TestStep(
            id=str(uuid.uuid1())
        )
    return send_result(message="OK")
