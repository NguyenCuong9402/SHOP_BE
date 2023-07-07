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
        size = body_request.get("size", "").upper()
        color = body_request.get("color", "").lower()
        if size == "":
            size = "M"
        if color == "":
            color = "black"
        check_item = Product.query.filter(Product.id == product_id).first()
        if check_item is None:
            return send_error(message="Sản phẩm không tồn tại, F5 lại web", is_dynamic=True)
        check_to_cart = CartItems.query.filter(CartItems.product_id == product_id, CartItems.color == color.lower(),
                                               CartItems.size == size.upper()).first()
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


@api.route("/<cart_item_id>", methods=["DELETE"])
@jwt_required()
def delete_item_to_cart(cart_item_id):
    try:
        user_id = get_jwt_identity()
        check_item_cart = CartItems.query.filter(CartItems.id == cart_item_id, CartItems.user_id == user_id)
        if check_item_cart is None:
            return send_error(message="Sản phẩm không có trong giỏ hàng, vui lòng F5", is_dynamic=True)
        check_item_cart.delete()
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
        user_id = get_jwt_identity()
        body_request = request.get_json()
        quantity = body_request.get("quantity", 0)
        size = body_request.get("size", "")
        color = body_request.get("color", "")
        if quantity <= 0:
            return send_error(message="Số lượng sản phẩm > 0 hoặc xóa ra khỏi giỏ hàng")
        check_item_cart = CartItems.query.filter(CartItems.id == cart_item_id, CartItems.user_id == user_id).first()

        if check_item_cart is None:
            return send_error(message="Sản phẩm không có trong giỏ hàng, vui lòng F5", is_dynamic=True)
        if size == "" and color == "":
            check_item_cart.quantity = quantity
        elif size != "" and color == "":
            cart_new = CartItems.query.filter(CartItems.user_id == user_id, CartItems.color == check_item_cart.color,
                                              CartItems.product_id == check_item_cart.product_id,
                                              CartItems.size == size.upper()).first()
            if cart_new is None:
                check_item_cart.size = size
                check_item_cart.quantity = quantity
            else:
                cart_new.quantity = cart_new.quantity + quantity
                db.session.delete(check_item_cart)
            db.session.flush()

        elif size == "" and color != "":
            cart_new = CartItems.query.filter(CartItems.user_id == user_id, CartItems.size == check_item_cart.size,
                                              CartItems.product_id == check_item_cart.product_id
                                              , CartItems.color == color.lower()).first()
            if cart_new is None:
                check_item_cart.color = color
                check_item_cart.quantity = quantity
            else:
                cart_new.quantity = cart_new.quantity + quantity
                db.session.delete(check_item_cart)
            db.session.flush()

        elif size != "" and color != "":
            cart_new = CartItems.query.filter(CartItems.user_id == user_id, CartItems.size == size.upper(),
                                              CartItems.product_id == check_item_cart.product_id
                                              , CartItems.color == color.lower()).first()
            if cart_new is None:
                check_item_cart.color = color.lower()
                check_item_cart.size = size.upper()
                check_item_cart.quantity = quantity

            else:
                cart_new.quantity = cart_new.quantity + quantity
                db.session.delete(check_item_cart)
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
        sum_money = 0
        for item in resul:
            sum_money = sum_money + item["price"]
        data = {
            "data": resul,
            "sum_money": sum_money
        }
        return send_result(data=data)
    except Exception as ex:
        return send_error(message=str(ex))


