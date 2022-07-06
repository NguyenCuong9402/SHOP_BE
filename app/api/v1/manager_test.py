from flask import Blueprint, request
from flask_jwt_extended import jwt_required, get_jwt_identity, create_access_token

from app.utils import send_result, send_error, data_preprocessing
from app.validator import CreateTestValidator

api = Blueprint('test', __name__)


@api.route("", methods=["POST"])
def create_test():
    # Step 1: validate json input
    try:
        json_req = request.get_json()
    except Exception as ex:
        return send_error(message="Request body incorrect json format: " + str(ex), code=442)

    # validate request body
    json_valid, message_id = data_preprocessing(cls_validator=CreateTestValidator, input_json=json_req)
    if not json_valid:
        return send_error(message_id=message_id, code=442)

    return send_result(message="OK")
