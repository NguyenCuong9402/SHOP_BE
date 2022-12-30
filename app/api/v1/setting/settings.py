import json
import uuid
from operator import or_

from flask import Blueprint, request
from flask_jwt_extended import jwt_required, get_jwt_identity, create_access_token
from benedict import benedict

from app.api.v1.setting.setting_validator import UpdateMiscellaneousRequest
from app.gateway import authorization_require
from app.models import TestStep, Test, TestType, db, TestField, Setting
from app.utils import send_result, send_error, data_preprocessing
from app.validator import CreateTestValidator, SettingSchema
from app.parser import TestFieldSchema, TestStepSchema

api = Blueprint('', __name__)


@api.route("/<project_id>", methods=["GET"])
@authorization_require()
def get_project_setting(project_id):
    token = get_jwt_identity()
    cloud_id = token.get('cloudId')
    project_setting = db.session.query(Setting).filter(
        or_(Setting.project_id == project_id, Setting.project_key == project_id), Setting.cloud_id == cloud_id).first()
    result = SettingSchema().dump(project_setting)
    return send_result(data=result, message="OK")


@api.route("/miscellaneous/enable/<project_id>", methods=["POST"])
@authorization_require()
def enable_miscellaneous_setting(project_id):
    token = get_jwt_identity()
    cloud_id = token.get('cloudId')

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
        if body_request.get('enabled') is None:
            return send_error(message="Missing required data.")

        # Get cloud information:
        project_id = project_id
        cloud_id = cloud_id
        enabled = body_request['enabled']
        project_setting = Setting.query.filter(
            Setting.project_id == project_id, Setting.cloud_id == cloud_id).first()
        if project_setting is None:
            miscellaneous = {
                'enabled': enabled
            }
            miscellaneous = json.dumps(miscellaneous)
            project_setting = Setting(id=str(uuid.uuid1()), miscellaneous=miscellaneous, project_id=project_id,
                                      cloud_id=cloud_id)
            db.session.add(project_setting)
            db.session.commit()
            #  Get body request

        miscellaneous = benedict(json.loads(project_setting.miscellaneous))
        miscellaneous.merge({'enabled': body_request['enabled']})
        project_setting.miscellaneous = json.dumps(miscellaneous)
        db.session.commit()

        return send_result(data=SettingSchema().dump(project_setting), message="OK")
    except Exception as ex:
        return send_error(data='', message="Something was wrong!")


@api.route("/miscellaneous/<project_id>", methods=["PUT"])
@authorization_require()
def update_miscellaneous_setting(project_id):
    try:
        token = get_jwt_identity()
        cloud_id = token.get('cloudId')

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

        # Validate body request

        input_validation = UpdateMiscellaneousRequest()
        is_not_validate = input_validation.validate(body_request)
        if is_not_validate:
            return send_error(code=400, data=is_not_validate, message='Invalid request')

        project_setting = Setting.query.filter(
            Setting.project_id == project_id, Setting.cloud_id == cloud_id).first()
        if project_setting is None:
            return send_error(data='', message='Project is not configured.')

        miscellaneous = benedict(json.loads(project_setting.miscellaneous))
        miscellaneous.merge(body_request['miscellaneous'])
        project_setting.miscellaneous = json.dumps(miscellaneous)
        db.session.commit()

        return send_result(data=SettingSchema().dump(project_setting), message="OK")
    except Exception as ex:
        return send_error(data='', message="Something was wrong!")


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
