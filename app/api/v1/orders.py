import os
import uuid
from flask import Blueprint, request, make_response, send_file, Response
from flask_jwt_extended import get_jwt_identity, jwt_required
from sqlalchemy import asc, desc
from io import BytesIO
import datetime
import io

from app.schema import HistoryOrdersSchema, OrderItemsSchema
from app.utils import send_error, get_timestamp_now, send_result
from app.models import db, Product, User, Orders, OrderItems, CartItems


api = Blueprint('orders', __name__)


@api.route("", methods=["POST"])
@jwt_required()
def add_order():
    try:
        user_id = get_jwt_identity()
        body_request = request.get_json()
        phone_number = body_request.get("phone_number", "")
        address = body_request.get("address", "")
        user = User.query.filter(User.id == user_id).first()
        if phone_number == "":
            phone_number = user.phone_number
        if address == "":
            address = user.address
        cart_items = CartItems.query.filter(CartItems.user_id == user_id).all()
        if len(cart_items) == 0:
            return send_error(message="Bạn chưa có đơn hàng nào")
        order = Orders(
            id=str(uuid.uuid4()),
            user_id=user_id,
            phone_number=phone_number,
            address=address,
            created_date=get_timestamp_now()
        )
        db.session.add(order)
        db.session.flush()
        count = 0
        for cart_item in cart_items:
            product = Product.query.filter(Product.id == cart_item.product_id).first()
            count_order_item = product.price*cart_item.quantity
            order_item = OrderItems(
                id=str(uuid.uuid4()),
                order_id=order.id,
                product_id=product.id,
                quantity=cart_item.quantity,
                count=count_order_item,
                size=cart_item.size,
                color=cart_item.color,
                created_date=get_timestamp_now()
            )
            db.session.add(order_item)
            db.session.flush()
            count = count + count_order_item
        order.count = count
        user.count = user.count + count
        db.session.flush()
        # Xóa item trong giỏ hàng sau khi đặt hàng
        CartItems.query.filter(CartItems.user_id == user_id).delete()
        db.session.flush()
        db.session.commit()
        return send_result(data=count, message=f"Đơn hàng đã được đặt! \n"
                                               f" Hóa đơn của bạn là {count}", show=True)
    except Exception as ex:
        db.session.rollback()
        return send_error(message=str(ex))


@api.route("/buy-now", methods=["POST"])
@jwt_required()
def order_now():
    try:
        user_id = get_jwt_identity()
        body_request = request.get_json()
        product_id = body_request.get("product_id", "")
        if product_id == "":
            return send_error(message="invalid request")

        phone_number = body_request.get("phone_number", "")
        address = body_request.get("address", "")
        quantity = body_request.get("quantity", 1)
        size = body_request.get("size", "M")
        color = body_request.get("color", "M")

        product = Product.query.filter(Product.id == product_id).first()
        if product is None:
            return send_error(message="Sản phẩm không tồn tại, F5 lại web")
        user = User.query.filter(User.id == user_id).first()
        if phone_number == "":
            phone_number = user.phone_number
        if address == "":
            address = user.address

        order = Orders(
            id=str(uuid.uuid4()),
            user_id=user_id,
            phone_number=phone_number,
            address=address,
            created_date=get_timestamp_now(),
            count=product.price*quantity
        )
        db.session.add(order)
        db.session.flush()

        order_item = OrderItems(
            id=str(uuid.uuid4()),
            order_id=order.id,
            product_id=product.id,
            quantity=quantity,
            count=product.price*quantity,
            size=size,
            color=color,
            created_date=get_timestamp_now()
        )
        db.session.add(order_item)
        db.session.flush()
        db.session.commit()
        return send_result(message="Đặt hàng thành công", show=True)
    except Exception as ex:
        db.session.rollback()
        return send_error(message=str(ex))


@api.route("", methods=["GET"])
@jwt_required()
def get_order():
    try:
        user_id = get_jwt_identity()
        orders = Orders.query.filter(Orders.user_id == user_id).order_by(desc(Orders.created_date)).all()
        data = HistoryOrdersSchema(many=True).dump(orders)
        return send_result(data=data, message="oke", show=True)
    except Exception as ex:
        db.session.rollback()
        return send_error(message=str(ex))


@api.route("/<order_id>", methods=["GET"])
@jwt_required()
def get_order_detail(order_id):
    try:
        user_id = get_jwt_identity()
        orders = OrderItems.query.filter(OrderItems.order_id == order_id).order_by(desc(OrderItems.created_date)).all()
        data = OrderItemsSchema(many=True).dump(orders)
        return send_result(data=data, message="oke", show=True)
    except Exception as ex:
        db.session.rollback()
        return send_error(message=str(ex))
