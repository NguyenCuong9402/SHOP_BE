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

api = Blueprint('setting', __name__)

DEFAULT_VALUES = {
    "test_run": [
        "edit_date",
        "fail_all",
        "track_time"
    ],
    "defect_link": [
        "defect_with_test",
        "defect_with_test_execution"
    ],
    "dissalow_test_case": [],
    "dissalow_test_execution": [],
    "enabled": False
}


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
    """
    Enable/Disable  miscellaneous setting
    Args:
        project_id:

    Returns:

    """

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
            project_setting = Setting(id=str(uuid.uuid1()), miscellaneous=json.dumps(DEFAULT_VALUES),
                                      project_id=project_id,
                                      cloud_id=cloud_id)
            db.session.add(project_setting)
            db.session.commit()
            #  Get body request

        miscellaneous = benedict(DEFAULT_VALUES)
        miscellaneous.merge({'enabled': body_request['enabled']})
        project_setting.miscellaneous = json.dumps(miscellaneous)
        db.session.commit()

        return send_result(data=SettingSchema().dump(project_setting), message="OK")
    except Exception as ex:
        return send_error(data='', message="Something was wrong!")


@api.route("/miscellaneous/<project_id>", methods=["PUT"])
@authorization_require()
def update_miscellaneous_setting(project_id):
    """
    Update or create miscellaneous setting
    """

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
        body_request['miscellaneous']['enabled'] = True
        miscellaneous.merge(body_request['miscellaneous'])
        project_setting.miscellaneous = json.dumps(miscellaneous)
        db.session.commit()

        return send_result(data=SettingSchema().dump(project_setting), message="OK")
    except Exception as ex:
        return send_error(data='', message="Something was wrong!")


@api.route("/test_type/enable/<project_id>", methods=["POST"])
@authorization_require()
def enable_test_type(project_id):
    """
       Enable/Disable  miscellaneous setting
       Args:
           project_id:

       Returns:

       """
    try:
        json_req = request.get_json()
    except Exception as ex:
        return send_error(message="Request Body incorrect json format: " + str(ex), code=442)

    if json_req.get('enabled') is None:
        return send_error(message="Missing required data.")

    token = get_jwt_identity()
    cloud_id = token.get('cloudId')

    # Get cloud information:
    project_id = project_id
    cloud_id = cloud_id

    enabled = json_req['enabled']
    project_setting = Setting.query.filter(
        Setting.project_id == project_id, Setting.cloud_id == cloud_id).first()
    if project_setting is None:
        project_setting = Setting(id=str(uuid.uuid1()), miscellaneous=json.dumps(DEFAULT_VALUES),
                                  project_id=project_id,
                                  cloud_id=cloud_id)
        db.session.add(project_setting)
        db.session.commit()

    project_setting.test_type = enabled
    db.session.commit()

    return send_result(data=SettingSchema().dump(project_setting), message="Project Test Type settings saved",
                       show=True)
