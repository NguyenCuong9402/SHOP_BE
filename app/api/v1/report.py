import os
import uuid
from flask import Blueprint, request, make_response, send_file, Response
from flask_jwt_extended import get_jwt_identity, get_jwt, jwt_required
from sqlalchemy import asc, desc
from io import BytesIO
import datetime
import io

from werkzeug.utils import secure_filename

from app.api.v1.picture import FILE_PATH, FILE_PATH_PRODUCT
from app.models import db, Product, User, Orders, OrderItems, CartItems
from app.schema import ProductSchema
from app.utils import send_error, get_timestamp_now, send_result, escape_wildcard

api = Blueprint('report', __name__)


@api.route("", methods=["GET"])
@jwt_required()
def report():
    try:
        jwt = get_jwt()
        user_id = get_jwt_identity()
        user = User.query.filter(User.id == user_id).first()
        if user.admin == 0 or (not jwt.get("is_admin")):
            return send_result(message="Bạn không phải admin.")
        products = Product.query.filter().order_by(desc(Product.revenue)).all()
        data = ProductSchema(many=True).dump(products)
        return send_result(data=data)
    except Exception as ex:
        return send_error(message=str(ex))
