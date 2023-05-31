import json
import uuid

from flask import Blueprint, request
from flask_jwt_extended import get_jwt_identity

from app.api.v1.user_setting.user_setting_validator import UserSettingValidator, UserSettingSchema
from app.extensions import db
from app.gateway import authorization_require
from app.models import UserSetting
from app.utils import send_error, send_result, validate_request, get_timestamp_now

api = Blueprint('user_setting', __name__)


@api.route('', methods=['GET'])
@authorization_require()
def get_user_setting():
    try:
        token = get_jwt_identity()
        user_id = token.get('userId')
        user_setting = UserSetting.query.filter(UserSetting.user_id == user_id).first()
        if not user_setting:
            new_user_setting = UserSetting(id=str(uuid.uuid4()),
                                           display_column=json.dumps(SETTING_DEFAULT),
                                           created_date=get_timestamp_now(),
                                           modified_date=get_timestamp_now(),
                                           user_id=user_id)
            db.session.add(new_user_setting)
            db.session.commit()
            user_setting = new_user_setting.copy()
        data = UserSettingSchema().dump(user_setting)
        return send_result(data=data)
    except Exception as ex:
        return send_error(message=str(ex))


@api.route('', methods=['PUT'])
@authorization_require()
def update_user_setting():
    try:
        token = get_jwt_identity()
        user_id = token.get('userId')
        is_valid, data, body_request = validate_request(UserSettingValidator(), request)
        if not is_valid:
            return send_error(data=data, code=200, is_dynamic=True)

        display_column = body_request.get('display_column', None)

        user_setting = UserSetting.query.filter(UserSetting.user_id == user_id).first()
        if user_setting:
            user_setting.display_column = json.dumps(display_column)
            user_setting.modified_date = get_timestamp_now()
            data = user_setting
        else:
            new_user_setting = UserSetting(id=str(uuid.uuid4()),
                                           display_column=json.dumps(display_column),
                                           created_date=get_timestamp_now(),
                                           modified_date=get_timestamp_now(),
                                           user_id=user_id)
            db.session.add(new_user_setting)
            data = new_user_setting
        db.session.commit()
        result = UserSettingSchema().dump(data)
        return send_result(data=result)
    except Exception as ex:
        db.session.rollback()
        return send_error(message=str(ex))


SETTING_DEFAULT = {
    "panelTestSet": [
        {
            "key": "issuekey",
            "name": "Key"
        },
        {
            "key": "summary",
            "name": "Summary"
        },
        {
            "key": "status",
            "name": "Status"
        }
    ],
    "panelDetailTestSet": [
        {
            "key": "issuekey",
            "name": "Key"
        },
        {
            "key": "summary",
            "name": "Summary"
        },
        {
            "key": "status",
            "name": "Status"
        },
        {
            "key": "assignee",
            "name": "Assignee"
        }
    ]
}
