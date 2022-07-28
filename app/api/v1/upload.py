import os
import uuid

from flask import Blueprint, request, send_file, jsonify
from flask_jwt_extended import jwt_required
from werkzeug.utils import secure_filename

from app.utils import send_result, send_error

api = Blueprint('upload', __name__)

ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'}

os.makedirs("app/files", exist_ok=True)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@api.route('', methods=['POST'])
@jwt_required()
def upload_file():
    # check if the post request has the file part
    files = request.files
    # If the user does not select a file, the browser submits an
    # empty file without a filename.
    # if file:
    for key, data in files.items():
        filename = secure_filename(data.filename)
        file_id = str(uuid.uuid4()).split('-')[0]
        savename = f"{file_id}-{filename}"
        data.save(os.path.join("app/files", savename))
        return send_result(data={"filename": savename}, message="OK")
    return send_error(message="File not found")


@api.route('/<name>', methods=['GET'])
def download_file(name):
    return send_file(os.path.join("files", name), as_attachment=True, download_name=name, attachment_filename=name)
