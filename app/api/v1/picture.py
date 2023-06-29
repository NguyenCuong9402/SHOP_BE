import os
import uuid
from flask import Blueprint, request, make_response, send_file, Response
from flask_jwt_extended import get_jwt_identity, jwt_required, get_jwt
from sqlalchemy import asc
from io import BytesIO
import datetime
import io

from werkzeug.utils import secure_filename

from app.utils import send_error, get_timestamp_now, send_result
from app.models import db, Product, User, Orders, OrderItems, CartItems


api = Blueprint('picture', __name__)

FILE_PATH = "app/files/"


@api.route('/<product_id>', methods=['POST'])
@jwt_required()
def upload_picture(product_id):
    try:
        user_id = get_jwt_identity()
        jwt = get_jwt()
        user = User.query.filter(User.id == user_id).first()
        if user.admin == 0 or (not jwt.get("is_admin")):
            return send_result(message="Bạn không phải admin.")
        product = Product.query.filter(Product.id == product_id).first()
        if product is None:
            return send_error(message="F5 Web")
        file = request.files['file']
        filename, file_extension = os.path.splitext(file.filename)
        file_name = secure_filename(product.id + file_extension)
        if not os.path.exists(FILE_PATH):
            os.makedirs(FILE_PATH)

        file.save(os.path.join(FILE_PATH + file_name))
        product.picture = file_name
        db.session.flush()
        db.session.commit()
        dt = {
            "file_url": file_name
        }
        return send_result(data=dt, message="Ok")
    except Exception as ex:
        db.session.rollback()
        return send_error(message=str(ex))


@api.route('/<product_id>', methods=['GET'])
def get_picture(product_id):
    try:
        product = Product.query.filter(Product.id == product_id).first()
        if product is None:
            pass
        file_path = FILE_PATH + product.picture
        if not os.path.isfile(file_path):
            return send_error(message='File not found')
        file = os.path.abspath(file_path)
        return send_file(file, as_attachment=True)
    except Exception as ex:
        return send_error(message=str(ex))