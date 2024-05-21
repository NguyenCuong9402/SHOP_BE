import io
import json
import os

from firebase_admin import storage
from flask import Blueprint, request, send_file
from flask_jwt_extended import get_jwt_identity, jwt_required, get_jwt
from sqlalchemy import desc
from app.models import User, Orders
from app.utils import send_error, send_result
from app.schema import OrdersSchema, HistoryOrdersSchema

api = Blueprint('firebase', __name__)


@api.route("/upload", methods=["POST"])
def upload_file():
    try:
        if 'file' not in request.files:
            return "No file part"

        file = request.files['file']

        if file.filename == '':
            return "No selected file"

        # Lưu file lên Firebase Storage
        bucket = storage.bucket()
        blob = bucket.blob(file.filename)
        blob.upload_from_string(file.read(), content_type=file.content_type)
        return send_result(message="Upload")
    except Exception as ex:
        return send_error(message=str(ex))


@api.route('/download/<filename>', methods=['GET'])
def download_file(filename):
    try:
        # Truy cập Firebase Storage bucket
        bucket = storage.bucket()
        blob = bucket.blob(filename)

        # Tạo liên kết tải xuống tạm thời hoặc tải xuống nội dung tệp
        file_content = blob.download_as_bytes()
        file_extension = os.path.splitext(filename)[1].lower()

        if file_extension in ['.jpg', '.jpeg', '.png']:
            # Trả về nội dung tệp ảnh
            return send_file(io.BytesIO(file_content),
                             mimetype=blob.content_type,
                             attachment_filename=filename,
                             as_attachment=True)
        elif file_extension == '.json':
            # Đọc nội dung tệp JSON
            data = json.loads(file_content)
            return send_result(data=data)
        else:
            return send_result(data={"error": "Unsupported file type"})
    except Exception as ex:
        return send_error(message=str(ex))