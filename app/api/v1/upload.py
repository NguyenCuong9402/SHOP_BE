import os
import uuid
from marshmallow import Schema, fields, validate, ValidationError, types, validates_schema, post_dump

from flask import Blueprint, request, send_file, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from werkzeug.utils import secure_filename, send_from_directory
from app.validator import UploadValidation
from app.utils import send_result, send_error, get_timestamp_now
from app.enums import FILE_PATH, URL_SERVER
from app.models import FileDetail
from app.extensions import db


api = Blueprint('upload', __name__)

# ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'}

os.makedirs("app/files", exist_ok=True)


# def allowed_file(filename):
#     return '.' in filename and \
#            filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# @api.route('', methods=['POST'])
# @jwt_required()
# def upload_file():
#     # check if the post request has the file part
#     files = request.files
#     # If the user does not select a file, the browser submits an
#     # empty file without a filename.
#     # if file:
#     for key, data in files.items():
#         filename = secure_filename(data.filename)
#         file_id = str(uuid.uuid4()).split('-')[0]
#         savename = f"{file_id}-{filename}"
#         data.save(os.path.join("app/files", savename))
#         return send_result(data={"filename": savename}, message="OK")
#     return send_error(message="File not found")


@api.route('', methods=['POST'])
@jwt_required()
def upload_file():
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
    if FileDetail.query.filter(FileDetail.file_name == real_name).first() is not None:
        i = 1
        name, file_extension = os.path.splitext(real_name)
        real_name = f"{name}({i}){file_extension}"
        while True:
            if FileDetail.query.filter(FileDetail.file_name == real_name).first() is not None:
                i += 1
                real_name = f"{name}({i}){file_extension}"
            else:
                break
    file_name = secure_filename(real_name)
    file_path = "{}/{}".format(prefix, file_name)
    if not os.path.exists(FILE_PATH+prefix):
        os.makedirs(FILE_PATH+prefix)
    if os.path.exists(os.path.join(FILE_PATH + file_path)):
        i = 1
        filename, file_extension = os.path.splitext(file_path)
        file_path = f"{filename}({i}){file_extension}"
        while True:
            if os.path.exists(os.path.join(FILE_PATH + file_path)):
                i += 1
                file_path = f"{filename}({i}){file_extension}"
            else:
                break

    file_url = os.path.join(URL_SERVER + file_path)
    try:
        file.save(os.path.join(FILE_PATH + file_path))
        # Store file information such as name,path
        file_detail = FileDetail(id=str(uuid.uuid4()),
                                 attached_file=file_url,
                                 file_name=real_name,
                                 created_date=get_timestamp_now())
        db.session.add(file_detail)
        db.session.flush()
        db.session.commit()
    except Exception as ex:
        db.session.rollback()
        return send_error(message=str(ex))

    dt = {
        "file_url": file_url
    }

    return send_result(data=dt, message="Ok")


@api.route('', methods=['GET'])
@jwt_required()
def get_file():
    attached_files = request.args.getlist('attached_files[]', None)
    files = FileDetail.query.filter(FileDetail.attached_file.in_(attached_files)).all()
    files = FileDetailSchema(many=True).dump(files)
    return send_result(data=files, message="ok")


class FileDetailSchema(Schema):
    name = fields.String()
    attached_file = fields.String()
    file_name = fields.String()
    extension = fields.String()
    prefix = fields.String()


@api.route('/<name>', methods=['GET'])
@jwt_required()
def download_file(name):
    prefix = request.args.get('prefix', "", type=str).strip()
    # validate request params
    validator_upload = UploadValidation()
    is_invalid = validator_upload.validate({"prefix": prefix})
    if is_invalid:
        return send_error(data=is_invalid, message='Please check your request params')
    file_path = "{}/{}".format(prefix, name)
    if not os.path.isfile(FILE_PATH + file_path):
        return send_error(message='File not found')
    try:
        return send_file(os.path.join(FILE_PATH + file_path), as_attachment=True)
    except Exception as e:
        return send_error(message='Error while downloading file: {}'.format(str(e)))


@api.route("/<name>", methods=['DELETE'])
@jwt_required()
def delete_file(name):
    try:
        prefix = request.args.get('prefix', "", type=str).strip()
        # validate request params
        validator_upload = UploadValidation()
        is_invalid = validator_upload.validate({"prefix": prefix})
        if is_invalid:
            return send_error(data=is_invalid, message='Please check your request params')
        file_name = secure_filename(name)
        file_path = "{}/{}".format(prefix, file_name)
        FileDetail.query.filter(FileDetail.file_name == name).delete()
        db.session.flush()
        if os.path.exists(os.path.join(FILE_PATH+file_path)):
            os.remove(FILE_PATH+file_path)
        db.session.commit()
        return send_result(message="Remove success")
    except Exception as ex:
        db.session.rollback()
        return send_error(message=str(ex))