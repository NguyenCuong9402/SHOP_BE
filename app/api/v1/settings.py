import uuid

from flask import Blueprint, request
from flask_jwt_extended import jwt_required, get_jwt_identity, create_access_token

from app.models import TestStep, Test, TestType, db, TestField
from app.utils import send_result, send_error, data_preprocessing
from app.validator import CreateTestValidator
from app.parser import TestFieldSchema, TestStepSchema

api = Blueprint('settings', __name__)


@api.route("/<project_id>/fields", methods=["GET"])
def get_test_types_by_project(project_id):
    # test = TestField.query.filter_by().all()
    # test = TestFieldSchema().dump(test)
    data_mock = [
        {
            "name": "Issue ID",
            "key": "btest_field_01"
        },
        {
            "name": "Test Type",
            "key": "btest_field_02"
        },
        {
            "name": "Test Set Name",
            "key": "btest_field_03"
        },
        {
            "name": "Test Repository Folder",
            "key": "btest_field_04"
        }
    ]
    return send_result(data=data_mock, message="OK")


@api.route("/<project_id>/test-steps", methods=["GET"])
def get_test_steps_by_project(project_id):
    data_mock = [
        {
            "name": "Action",
            "key": "btest_step_field_01"
        },
        {
            "name": "Expected Result",
            "key": "btest_step_field_02"
        }
    ]
    return send_result(data=data_mock, message="OK")


@api.route("/<project_id>/testexec", methods=["GET"])
def get_test_execution_by_project(project_id):
    data_mock = [
        {
            "filters": ["statuses", "test_sets", "test_issue_ids"],
            "fields_column": ["defects", "comment", "status_id"]
        }
    ]
    return send_result(data=data_mock, message="OK")
