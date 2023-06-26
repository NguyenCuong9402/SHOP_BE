import os
import uuid
from flask import Blueprint, request, make_response, send_file, Response
from flask_jwt_extended import get_jwt_identity
from sqlalchemy import asc, desc
from io import BytesIO
import datetime
import io
from app.models import db, Product, User, Orders, OrderItems, CartItems
from app.schema import ProductSchema
from app.utils import send_error, get_timestamp_now, send_result

api = Blueprint('product', __name__)


@api.route("", methods=["POST"])
def add_product():
    try:
        body_request = request.get_json()
        name = body_request.get("name", "")
        price = body_request.get("price", 0)
        type_item = body_request.get("type")
        describe = body_request.get("describe")
        if name == "" or price <= 0 or type_item == "":
            return send_result(message="Vui lòng điền thêm thông tin", show=True)
        if check_coincided_name(name):
            return send_error(message="Tên sản phẩm đã tồn tại", is_dynamic=True)
        product = Product(
            id=str(uuid.uuid4()),
            name=name,
            price=price,
            type=type_item,
            describe=describe,
            created_date=get_timestamp_now()
        )
        db.session.add(product)
        db.session.flush()
        db.session.commit()
        return send_result(message="Thêm sản phẩm thành công", show=True)
    except Exception as ex:
        db.session.rollback()
        return send_error(message=str(ex))


@api.route("", methods=["GET"])
def get_list_item():
    try:
        product = Product.query.filter().order_by(desc(Product.created_date)).all()
        data = ProductSchema(many=True).dump(product)
        return send_result(data=data)
    except Exception as ex:
        return send_error(message=str(ex))


@api.route("/<product_id>", methods=["PUT"])
def fix_item(product_id):
    try:
        body_request = request.get_json()
        name = body_request.get("name", "")
        price = body_request.get("price", 0)
        type_item = body_request.get("type","")
        describe = body_request.get("describe","")
        check_item = Product.query.filter(Product.id == product_id).first()
        if check_item:
            return send_error(message="Sản phẩm không tồn tại, F5 lại web", is_dynamic=True)
        if name != "":
            check_item.name = name
        if price != 0:
            check_item.price = price
        if type_item != "":
            check_item.type = type_item
        if describe != "":
            check_item.describe = describe
        db.session.flush()
        db.session.commit()
        return send_result(message="Thay đổi thông tin sản phẩm thành công", show=True)
    except Exception as ex:
        db.session.rollback()
        return send_error(message=str(ex))


@api.route("/<product_id>", methods=["DELETE"])
def remove_item(product_id):
    try:
        check_item = Product.query.filter(Product.id == product_id).first()
        if check_item:
            return send_error(message="Sản phẩm không tồn tại, F5 lại web", is_dynamic=True)
        db.session.delete(check_item)
        db.session.flush()
        db.session.commit()
        return send_result(message="Thay đổi thông tin sản phẩm thành công", show=True)
    except Exception as ex:
        db.session.rollback()
        return send_error(message=str(ex))


@api.route("/<product_id>", methods=["GET"])
def get_item(product_id):
    try:
        check_item = Product.query.filter(Product.id == product_id).first()
        if check_item:
            return send_error(message="Sản phẩm không tồn tại, F5 lại web", is_dynamic=True)
        data = ProductSchema().dump(check_item)
        return send_result(data=data)
    except Exception as ex:
        db.session.rollback()
        return send_error(message=str(ex))


def check_coincided_name(name=''):
    existed_name = Product.query.filter(Product.name == name).first()
    if existed_name is None:
        return False
    return True
