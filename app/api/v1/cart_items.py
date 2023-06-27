import os
import uuid
from flask import Blueprint, request, make_response, send_file, Response
from flask_jwt_extended import get_jwt_identity, jwt_required
from sqlalchemy import asc
from io import BytesIO
import datetime
import io
from app.models import db, Product, User, Orders, OrderItems, CartItems
from app.utils import send_error, get_timestamp_now, send_result
from app.schema import ProductSchema


api = Blueprint('cart_items', __name__)


# Thêm User ID để kiểm soát
@api.route("<product_id>", methods=["POST"])
@jwt_required()
def add_item_to_cart(product_id):
    try:
        body_request = request.get_json()
        quantity = body_request.get("quantity", 1)
        size = body_request.get("size")
        color = body_request.get("color")
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
                created_date=get_timestamp_now()
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
        body_request = request.get_json()
        cart_item_ids = body_request.get("cart_item_ids",[])
        if len(cart_item_ids) == 0:
            return send_error(message="Chưa chọn sản phẩm nào!", is_dynamic=True)
        check_item_cart = CartItems.query.filter(CartItems.id.in_(cart_item_ids)).first()
        if check_item_cart is None:
            return send_error(message="Sản phẩm không có trong giỏ hàng, vui lòng F5", is_dynamic=True)
        db.session.delete(check_item_cart)
        db.session.flush()
        db.session.commit()
        return send_result(message="Bỏ ra giỏ hàng thành công", show=True)
    except Exception as ex:
        db.session.rollback()
        return send_error(message=str(ex))


@api.route("<cart_item_id>", methods=["PUT"])
@jwt_required()
def put_item_to_cart(cart_item_id):
    try:
        body_request = request.get_json()
        quantity = body_request.get("quantity", 0)
        if quantity <= 0:
            return send_error(message="Số lượng sản phẩm > 0 hoặc xóa ra khỏi giỏ hàng")
        check_item_cart = CartItems.query.filter(CartItems.id == cart_item_id).first()
        if check_item_cart is None:
            return send_error(message="Sản phẩm không có trong giỏ hàng, vui lòng F5", is_dynamic=True)
        check_item_cart.quantity = quantity
        db.session.flush()
        db.session.commit()
        return send_result(message="Thay đổi số lượng sản phẩm trong giỏ hàng thành công", show=True)
    except Exception as ex:
        db.session.rollback()
        return send_error(message=str(ex))



