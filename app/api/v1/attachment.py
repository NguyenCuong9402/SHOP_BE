import os
import uuid
from marshmallow import Schema, fields

from flask import Blueprint, request, send_file
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy import asc
from werkzeug.utils import secure_filename
from app.validator import UploadValidation
from app.utils import send_result, send_error, get_timestamp_now
from app.enums import FILE_PATH, URL_SERVER
from app.models import Attachment
from app.extensions import db

api = Blueprint('attachment', __name__)


@api.route('/<test_step_id>', methods=['POST'])
@jwt_required()
def upload_attachment(test_step_id):
    token = get_jwt_identity()
    cloud_id = token.get('cloudId')
    project_id = token.get('projectId')
    prefix = request.args.get('prefix', "", type=str).strip()
    # validate request params
    validator_upload = UploadValidation()
    is_invalid = validator_upload.validate({"prefix": prefix})
    if is_invalid:
        return send_error(data=is_invalid, message='Please check your request params')

    try:
        file = request.files['file']
    except Exception as ex:
        return send_error(message=str(ex))
    real_name = file.filename
    file_name = secure_filename(file.filename)
    file_path = "{}/{}".format(prefix, file_name)
    if not os.path.exists(FILE_PATH + prefix):
        os.makedirs(FILE_PATH + prefix)
    if os.path.exists(os.path.join(FILE_PATH + file_path)):
        i = 1
        filename, file_extension = os.path.splitext(file_path)
        file_path = f"{filename}_{i}{file_extension}"
        while True:
            if os.path.exists(os.path.join(FILE_PATH + file_path)):
                i += 1
                file_path = f"{filename}_{i}{file_extension}"
            else:
                break

    file_url = os.path.join(URL_SERVER + file_path)
    try:
        file.save(os.path.join(FILE_PATH + file_path))
        attachment = Attachment(id=str(uuid.uuid4()),
                                project_id=project_id,
                                cloud_id=cloud_id,
                                attached_file=file_url,
                                file_name=real_name,
                                test_step_id=test_step_id,
                                created_date=get_timestamp_now())
        db.session.add(attachment)
        db.session.flush()
        db.session.commit()
    except Exception as ex:
        db.session.rollback()
        return send_error(message=str(ex))

    dt = {
        "file_url": file_url
    }

    return send_result(data=dt, message="Ok")


@api.route("/<test_step_id>", methods=['GET'])
@jwt_required()
def get_attachment(test_step_id):
    token = get_jwt_identity()
    cloud_id = token.get('cloudId')
    project_id = token.get('projectId')
    files = Attachment.query.filter(Attachment.cloud_id == cloud_id, Attachment.project_id == project_id,
                                    Attachment.test_step_id == test_step_id)\
        .order_by(asc(Attachment.created_date)).all()
    files = AttachmentSchema(many=True).dump(files)
    return send_result(data=files, message="ok")


class AttachmentSchema(Schema):
    id = fields.String()
    name = fields.String()
    attached_file = fields.String()
    file_name = fields.String()
    prefix = fields.String()
    project_id = fields.String()
    cloud_id = fields.String()
    test_step_id = fields.String()
    created_date = fields.Integer()


@api.route('', methods=['POST'])
@jwt_required()
def download_attachment():
    token = get_jwt_identity()
    cloud_id = token.get('cloudId')
    project_id = token.get('projectId')
    req = request.get_json()
    attached_file = req.get('attached_file', '')
    file_path = "app"+attached_file
    if not os.path.isfile(file_path):
        return send_error(message='File not found')
    try:
        file = os.path.abspath(file_path)
        return send_file(file, as_attachment=True)
    except Exception as e:
        return send_error(message='Error while downloading file: {}'.format(str(e)))


@api.route("/<test_step_id>", methods=['DELETE'])
@jwt_required()
def delete_file(test_step_id):
    try:
        token = get_jwt_identity()
        cloud_id = token.get('cloudId')
        project_id = token.get('projectId')
        body_request = request.get_json()
        attached_file = body_request.get("attached_file")
        Attachment.query.filter(Attachment.project_id == project_id, Attachment.cloud_id == cloud_id,
                                Attachment.test_step_id == test_step_id,
                                Attachment.attached_file == attached_file).delete()
        db.session.flush()
        file_path = "app" + attached_file
        if os.path.exists(os.path.join(file_path)):
            os.remove(file_path)
        db.session.commit()
        return send_result(message="Remove success")
    except Exception as ex:
        db.session.rollback()
        return send_error(message=str(ex))
