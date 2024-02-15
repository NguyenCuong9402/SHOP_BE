import os
import uuid
from flask import Blueprint, request, make_response, send_file, Response
from flask_jwt_extended import get_jwt_identity, get_jwt, jwt_required
from sqlalchemy import asc, desc
import datetime
import io
from app.models import db, Product, User, Orders, OrderItems, CartItems, Reviews
from app.schema import ProductSchema, ReviewsSchema
from app.utils import send_error, get_timestamp_now, send_result

api = Blueprint('reviews', __name__)


@api.route("/<product_id>", methods=["POST"])
@jwt_required()
def post_comment(product_id):
    try:
        user_id = get_jwt_identity()
        body_request = request.get_json()
        comment = body_request.get("comment", "")
        user = User.query.filter(User.id == user_id).first()
        if user is None:
            return send_error(message="Mời bạn đang nhập lại")
        product = Product.query.filter(Product.id == product_id).first()
        if product is None:
            return send_error(message="Sản phẩm không tồn tại, F5 lại web")
        if comment == "":
            return send_error(message="Vui lòng điền comment")
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
        return send_result(message="Comment thành công!")
    except Exception as ex:
        db.session.rollback()
        return send_error(message=str(ex))


@api.route("/<product_id>", methods=["GET"])
def get_comment(product_id):
    try:
        product = Product.query.filter(Product.id == product_id).first()
        if product is None:
            return send_error(message="Sản phẩm không tồn tại, F5 lại web")
        review = Reviews.query.filter(Reviews.product_id == product_id).order_by(desc(Reviews.created_date)).all()
        data = ReviewsSchema(many=True).dump(review)
        return send_result(data=data)
    except Exception as ex:
        return send_error(message=str(ex))


@api.route("/<product_id>", methods=["DELETE"])
@jwt_required()
def remove_comment(product_id):
    try:
        jwt = get_jwt()
        user_id = get_jwt_identity()
        user = User.query.filter(User.id == user_id).first()
        if user.admin == 0 or (not jwt.get("is_admin")):
            return send_result(message="Bạn không phải admin.")
        product = Product.query.filter(Product.id == product_id).first()
        if product is None:
            return send_error(message="Sản phẩm không tồn tại, F5 lại web", is_dynamic=True)
        body_request = request.get_json()
        review_ids = body_request.get("review_ids", [])
        if len(review_ids) == 0:
            return send_error(message="Chưa chọn comment nào!", is_dynamic=True)
        Reviews.query.filter(Reviews.id.in_(review_ids)).delete()
        return send_result(message="Xóa comments thành công", show=True)
    except Exception as ex:
        return send_error(message=str(ex))



