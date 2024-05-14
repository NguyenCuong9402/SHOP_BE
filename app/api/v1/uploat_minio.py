from urllib import request

from flask import Response, jsonify, Blueprint

from app.api.minio import MinioClient, handle_image_upload
from app.utils import send_result

api = Blueprint("faces_v2", __name__)


@api.route("/upload", methods=["POST"])
def upload_image():
    file = request.files['file']
    minio_client = MinioClient()
    success, message = handle_image_upload(minio_client, file)
    return send_result(data={"success": success, "message": message})


@api.route("/get_file", methods=["POST"])
def get_file():
    minio_client = MinioClient()

    file_name = '1715652848_1711100207_right.png'
    success, response = minio_client.download_image_stream(file_name)

    if success:
        return Response(
            response,
            content_type='application/octet-stream',
            headers={"Content-Disposition": f"attachment;filename={file_name}"}
        )
    else:
        return jsonify({"error": response}), 500