import os
import uuid
from flask import Blueprint, request, make_response, send_file, Response
from flask_jwt_extended import get_jwt_identity, jwt_required
from sqlalchemy import asc, desc
from io import BytesIO
import datetime
import io
from app.models import db, Product, User, Orders, OrderItems, CartItems
from app.utils import send_error, get_timestamp_now, send_result
from app.schema import ProductSchema, CartItemsSchema

api = Blueprint('cart_items', __name__)


@api.route("<product_id>", methods=["POST"])
@jwt_required()
def add_item_to_cart(product_id):
    try:
        user_id = get_jwt_identity()
        body_request = request.get_json()
        quantity = body_request.get("quantity", 1)
        size = body_request.get("size", "")
        color = body_request.get("color", "")
        if size == "":
            return send_error(message='Chưa chọn Size')
        if color == "":
            return send_error(message='Chưa chọn Màu')
        check_item = Product.query.filter(Product.id == product_id).first()
        if check_item is None:
            return send_error(message="Sản phẩm không tồn tại, F5 lại web", is_dynamic=True)
        check_to_cart = CartItems.query.filter(CartItems.product_id == product_id, CartItems.color == color,
                                               CartItems.size == size).first()
        if check_to_cart:
            check_to_cart.quantity = check_to_cart.quantity + quantity
        else:
            cart_item = CartItems(
                id=str(uuid.uuid4()),
                product_id=product_id,
                quantity=quantity,
                size=size,
                color=color,
                created_date=get_timestamp_now(),
                user_id=user_id
            )
            db.session.add(cart_item)
        db.session.flush()
        db.session.commit()
        return send_result(message="Thêm sản phẩm thành công", show=True)
    except Exception as ex:
        db.session.rollback()
        return send_error(message=str(ex))


@api.route("", methods=["DELETE"])
@jwt_required()
def delete_item_to_cart():
    try:
        user_id = get_jwt_identity()
        body_request = request.get_json()
        list_id = body_request.get("list_id", [])
        check_item_cart = CartItems.query.filter(CartItems.id.in_(list_id), CartItems.user_id == user_id)
        if check_item_cart.count == 0:
            return send_error(message="Bạn chưa chọn sản phẩm nào")
        check_item_cart.delete()
        db.session.flush()
        db.session.commit()
        return send_result(message="Bỏ ra giỏ hàng thành công")
    except Exception as ex:
        db.session.rollback()
        return send_error(message=str(ex))


@api.route("/get-total", methods=["POST"])
@jwt_required()
def get_to_tal_item_to_cart():
    try:
        user_id = get_jwt_identity()
        body_request = request.get_json()
        list_id = body_request.get("list_id", [])
        count = 0
        check_item_cart = CartItems.query.filter(CartItems.id.in_(list_id), CartItems.user_id == user_id).all()
        for item in check_item_cart:
            count += item.total
        return send_result(data=count)
    except Exception as ex:
        db.session.rollback()
        return send_error(message=str(ex))


@api.route("<cart_item_id>", methods=["PUT"])
@jwt_required()
def put_item_to_cart(cart_item_id):
    try:
        user_id = get_jwt_identity()
        body_request = request.get_json()
        quantity = body_request.get("new_quantity", None)
        if quantity is None:
            return send_error(status='none', message='None')
        if quantity <= 0:
            return send_error(message="Số lượng sản phẩm > 0 hoặc xóa ra khỏi giỏ hàng", status='<0')
        check_item_cart = CartItems.query.filter(CartItems.id == cart_item_id, CartItems.user_id == user_id).first()
        if check_item_cart is None:
            return send_error(message="Sản phẩm không có trong giỏ hàng, vui lòng F5", is_dynamic=True)
        if check_item_cart.quantity == quantity:
            return send_error(message='Không thay đổi gì', status='nochange')
        check_item_cart.quantity = quantity
        db.session.commit()
        return send_result(message="Thay đổi số lượng sản phẩm trong giỏ hàng thành công", show=True)
    except Exception as ex:
        db.session.rollback()
        return send_error(message=str(ex))


@api.route("/change/<cart_item_id>", methods=["PUT"])
@jwt_required()
def put_cart(cart_item_id):
    try:
        user_id = get_jwt_identity()
        body_request = request.get_json()
        size = body_request.get("size", "")
        color = body_request.get("color", "")
        item_cart = CartItems.query.filter(CartItems.id == cart_item_id, CartItems.user_id == user_id).first()
        if item_cart is None:
            return send_error(message="Sản phẩm không có trong giỏ hàng, vui lòng F5", is_dynamic=True)
        if item_cart.size != size and size in ['S', 'M', 'L', 'XL']:
            item_cart.size = size
            db.session.flush()
        if item_cart.color != color and color in item_cart.cac_mau:
            item_cart.color = color
            db.session.flush()
        check = CartItems.query.filter(CartItems.product_id == item_cart.product_id, CartItems.color == item_cart.color,
                                       CartItems.size == item_cart.size).first()
        if check is not None:
            item_cart.quantity = item_cart.quantity + check.quantity
            CartItems.query.filter(CartItems.id == check.id).delete()
            db.session.flush()
        db.session.commit()
        return send_result(message="Thay đổi số lượng sản phẩm trong giỏ hàng thành công", show=True)
    except Exception as ex:
        db.session.rollback()
        return send_error(message=str(ex))


@api.route("", methods=["GET"])
@jwt_required()
def get_item_to_cart():
    try:
        user_id = get_jwt_identity()
        carts = CartItems.query.filter(CartItems.user_id == user_id).order_by(desc(CartItems.created_date))
        resul = CartItemsSchema(many=True).dump(carts)
        return send_result(data=resul)
    except Exception as ex:
        return send_error(message=str(ex))


