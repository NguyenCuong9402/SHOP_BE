import os
import uuid

from flask import Blueprint, request, send_file, jsonify
from flask_jwt_extended import jwt_required
from werkzeug.utils import secure_filename
from app.validator import UploadValidation
from app.utils import send_result, send_error, get_timestamp_now_2
from app.enums import FILE_PATH, URL_SERVER
from app.models import FileDetail
from app.extensions import db


api = Blueprint('upload', __name__)

# ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'}

# os.makedirs("app/files", exist_ok=True)


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

    file_name = secure_filename(file.filename)
    real_name = file.filename
    file_path = "{}/{}".format(prefix, file_name)

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

        # Store file information such as name,path
        file_detail = FileDetail(id=str(uuid.uuid4()), attached_file=file_url, file_name=real_name,
                                 created_date=get_timestamp_now_2())
        db.session.add(file_detail)
        db.session.commit()
    except Exception as ex:
        db.session.rollback()
        return send_error(message=str(ex))

    dt = {
        "file_url": file_url
    }

    return send_result(data=dt, message="Ok")



# @api.route('/<name>', methods=['GET'])
# def download_file(name):
#     return send_file(os.path.join("files", name), as_attachment=True, download_name=name, attachment_filename=name)
