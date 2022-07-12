import uuid

from flask import Blueprint, request
from flask_jwt_extended import jwt_required, get_jwt_identity, create_access_token

from app.models import TestStep, Test, TestType, db
from app.utils import send_result, send_error, data_preprocessing
from app.validator import CreateTestValidator
from app.parser import TestSchema, TestTypeSchema

api = Blueprint('test', __name__)


@api.route("", methods=["POST"])
# @jwt_required()
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

    # STEP 2 check project_id is existed
    # TODO: not necessary, remove in the future
    project_id = json_req.get("project_id", "")

    # STEP 3 check test type is existed, and create if needed
    # TODO: remove create test type in the future, because test type will create when setup btest for a project
    test_type = json_req.get("test_type", "")
    exist_type = TestType.query.filter_by(project_setting_id=project_id, name=test_type).first()
    if not exist_type:
        # create new test type
        map_test_type = {
           "Manual": "Steps",
           "Generic": "Unstructured",
           "Cucumber": "Gherkin",
        }
        exist_type = TestType(project_setting_id=project_id, name=test_type, kind=map_test_type[test_type])
        exist_type.id = str(uuid.uuid1())
        db.session.add(exist_type)
        db.session.commit()

    # Create an instance for new test
    test_instance = Test(
        id=str(uuid.uuid1()),
        issue_id=json_req.get("issue_id", ""),
        issue_jira_id=json_req.get("issue_jira_id", ""),
        test_repo=json_req.get("test_repo", ""),
        project_id=json_req.get("project_id", ""),
        test_type_id=exist_type.id
    )

    # create test sets and add issue to the test sets
    test_set_name = json_req.get("test_set_name", "")

    # submit new instance to mysql session
    db.session.add(test_instance)

    # STEP 4 create test steps for the test
    for test_step in test_steps:
        new_instance = TestStep(
            id=str(uuid.uuid1()),
            data=test_step.get("data", ""),
            result=test_step.get("result", ""),
            customFields=test_step.get("customFields", ""),
            attachments=test_step.get("attachments", ""),
            action=test_step.get("action", ""),
            test_id=test_instance.id
        )
        db.session.add(new_instance)

    # STEP 5: setup ok, commit change to mysql
    db.session.commit()
    return send_result(message="OK")


@api.route("/<test_id>", methods=["DELETE"])
def delete_test(test_id):
    Test.query.filter_by().delete()
    return send_result(message="OK")


@api.route("/<test_id>", methods=["GET"])
def get_test(test_id):
    test = Test.query.filter_by().first()
    test = TestSchema().dump(test)
    return send_result(data=test, message="OK")
