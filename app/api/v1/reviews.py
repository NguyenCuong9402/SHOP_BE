import os
import uuid
from flask import Blueprint, request, make_response, send_file, Response
from flask_jwt_extended import get_jwt_identity, get_jwt, jwt_required
from sqlalchemy import asc, desc
from io import BytesIO
import datetime
import io
from app.models import db, Product, User, Orders, OrderItems, CartItems, Reviews
from app.schema import ProductSchema
from app.utils import send_error, get_timestamp_now, send_result

api = Blueprint('reviews', __name__)


@api.route("/<product_id>", methods=["POST"])
@jwt_required()
def post_comment(product_id):
    try:
        user_id = get_jwt_identity()
        body_request = request.get_json()
        comment = body_request.get("comment", "")
        product = Product.query.filter(Product.id == product_id).first()
        if product is None:
            return send_error(message="Sản phẩm không tồn tại, F5 lại web", is_dynamic=True)
        if comment == "":
            return send_error(message="Vui lòng điền comment", is_dynamic=True)
        review = Reviews(
            id=str(uuid.uuid4()),
            product_id=product_id,
            user_id=user_id,
            created_date=get_timestamp_now(),
            comment=comment
        )
        db.session.add(review)
        db.session.flush()
        db.session.commit()
    except Exception as ex:
        db.session.rollback()
        return send_error(message=str(ex))


@api.route("/<product_id>", methods=["GET"])
def get_comment(product_id):
    try:
        product = Product.query.filter(Product.id == product_id).first()
        if product is None:
            return send_error(message="Sản phẩm không tồn tại, F5 lại web", is_dynamic=True)
        review = Reviews.query.filter(Reviews.product_id == product_id).order_by(desc(Reviews.created_date)).all()
    except Exception as ex:
        return send_error(message=str(ex))


