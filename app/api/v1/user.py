import os
import uuid
from flask import Blueprint, request, make_response, send_file, Response
from flask_jwt_extended import get_jwt_identity
from sqlalchemy import asc
from io import BytesIO
import datetime
import io

from app.utils import send_error, send_result

api = Blueprint('user', __name__)


@api.route("/register", methods=["POST"])
def register():
    try:
        pass
    except Exception as ex:
        return send_error(message=str(ex))

