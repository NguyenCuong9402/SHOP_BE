import os
import uuid

from flask import Blueprint, request, url_for, send_from_directory, send_file
from flask_jwt_extended import jwt_required, get_jwt_identity, create_access_token
from sqlalchemy import or_
from werkzeug.utils import secure_filename

from app.models import TestSets, Test, TestType, db
from app.utils import send_result, send_error, data_preprocessing
from app.validator import CreateTestValidator
from app.parser import TestSchema, TestTypeSchema, TestSetsSchema

api = Blueprint('upload', __name__)

ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'}


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@api.route('', methods=['POST'])
def upload_file():
    # check if the post request has the file part
    file = request.files
    # If the user does not select a file, the browser submits an
    # empty file without a filename.
    # if file:
    for key, value in file.items():
        data = file[key]
        filename = secure_filename(data.filename)
        file_id = str(uuid.uuid4()).split('-')[0]
        savename = f"{file_id}-{filename}"
        data.save(os.path.join("app/files", savename))
        return send_result(data={"filename": savename}, message="OK")
    return send_error()


@api.route('/<name>', methods=['GET'])
def download_file(name):
    return send_file(os.path.join("files", name))
