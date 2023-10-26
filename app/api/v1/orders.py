import os
import uuid
from flask import Blueprint, request, make_response, send_file, Response
from flask_jwt_extended import get_jwt_identity, jwt_required
from sqlalchemy import asc, desc
from io import BytesIO
import datetime
import io

from app.schema import HistoryOrdersSchema, OrderItemsSchema
from app.utils import send_error, get_timestamp_now, send_result, escape_wildcard
from app.models import db, Product, User, Orders, OrderItems, CartItems, Shipper

api = Blueprint('orders', __name__)


@api.route("", methods=["POST"])
@jwt_required()
def add_order():
    try:
        user_id = get_jwt_identity()
        body_request = request.get_json()
        ship_id = body_request.get("ship_id", "")
        phone_number = body_request.get("phone_number", "")
        address = body_request.get("address", "")
        loi_nhan = body_request.get("loi_nhan", "")
        tinh = body_request.get("tinh", "")
        huyen = body_request.get("huyen", "")
        xa = body_request.get("xa", "")
        cart_ids = body_request.get("cart_ids", [])

        user = User.query.filter(User.id == user_id).first()

        if len(cart_ids) == 0:
            return send_error(message='Chưa chọn đơn hàng nào.')
        if ship_id == "":
            return send_error(message='Chưa chọn đơn vị ship.')

        ship = Shipper.query.filter(Shipper.id == ship_id).first()
        if ship is None:
            return send_error(message='Chưa chọn đơn vị ship.')
        gia_ship = ship.gia_ship
        if "" in [address, tinh, huyen, xa]:
            return send_error(message='Thông tin địa chỉ chưa đầy đủ. '
                                      'Vui lòng điền thêm!')

        if len(phone_number) != 10:
            return send_error(message='Số điện thoại chưa đúng. '
                                      'Vui lòng điền thêm!')

        cart_items = CartItems.query.filter(CartItems.id.in_(cart_ids), CartItems.user_id == user_id).all()
        count = 0
        for cart_item in cart_items:
            count += cart_item.total
        # Tạo đơn hàng
        order = Orders(
            id=str(uuid.uuid4()),
            user_id=user_id,
            phone_number=phone_number,
            address=address,
            tinh=tinh,
            huyen=huyen,
            xa=xa,
            created_date=get_timestamp_now(),
            loi_nhan=loi_nhan,
            ship_id=ship_id,
            gia_ship=gia_ship,
            count=count,
            tong_thanh_toan=count + gia_ship
        )
        db.session.add(order)
        db.session.flush()

        # Thông tin chi tiết đơn hàng
        for cart_item in cart_items:
            order_item = OrderItems(
                id=str(uuid.uuid4()),
                order_id=order.id,
                quantity=cart_item.quantity,
                size=cart_item.size,
                color=cart_item.color,
                created_date=get_timestamp_now(),
                count=cart_item.total
            )
            db.session.add(order_item)
            db.session.flush()

        # Xóa item trong giỏ hàng sau khi đặt hàng
        CartItems.query.filter(CartItems.id.in_(cart_ids), CartItems.user_id == user_id).delete()
        db.session.flush()
        db.session.commit()
        return send_result()
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


@api.route("/manage", methods=["GET"])
@jwt_required()
def get_order_admin():
    try:
        text_search = request.args.get('text_search', '', type=str)
        user_id = get_jwt_identity()
        user = User.query.filter(User.id == user_id).first()
        if user.admin == 0:
            return send_result(message="Bạn không phải admin.")
        query = Orders.query.filter()
        if text_search is not None:
            text_search = text_search.strip()
            text_search = text_search.lower()
            text_search = escape_wildcard(text_search)
            text_search = "%{}%".format(text_search)
            query = query.filter(Orders.id.like(text_search))
        orders = query.order_by(desc(Orders.created_date)).all()
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
