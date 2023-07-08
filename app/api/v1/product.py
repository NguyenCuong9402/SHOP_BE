import os
import uuid
from flask import Blueprint, request, make_response, send_file, Response
from flask_jwt_extended import get_jwt_identity, get_jwt, jwt_required
from sqlalchemy import asc, desc
from io import BytesIO
import datetime
import io

from app.api.v1.picture import FILE_PATH
from app.models import db, Product, User, Orders, OrderItems, CartItems
from app.schema import ProductSchema
from app.utils import send_error, get_timestamp_now, send_result, escape_wildcard

api = Blueprint('product', __name__)


@api.route("", methods=["POST"])
@jwt_required()
def add_product():
    try:
        jwt = get_jwt()
        user_id = get_jwt_identity()
        user = User.query.filter(User.id == user_id).first()
        if user.admin == 0 or (not jwt.get("is_admin")):
            return send_result(message="Bạn không phải admin.")
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
        type = request.args.get('type', '', type=str)
        text_search = request.args.get('text_search', '', type=str)
        order_by = request.args.get('order_by', '', type=str)
        order = request.args.get('order', 'desc', type=str)
        if order_by == "":
            order_by = "created_date"
        if order == "":
            order = "desc"

        if type == "":
            query = Product.query.filter()
        else:
            if type not in ["quan", "ao", "phukien"]:
                return send_error(message="Invalid request", is_dynamic=True)
            query = Product.query.filter(Product.type == type)
        if text_search is not None:
            text_search = text_search.strip()
            text_search = text_search.lower()
            text_search = escape_wildcard(text_search)
            text_search = "%{}%".format(text_search)
            query = query.filter(Product.name.like(text_search))
        column_sorted = getattr(Product, order_by)
        query = query.order_by(desc(column_sorted)) if order == "desc" else query.order_by(asc(column_sorted))
        products = query.all()
        results = {
            "products": ProductSchema(many=True).dump(products),
        }

        return send_result(data=results)
    except Exception as ex:
        return send_error(message=str(ex))


@api.route("/<product_id>", methods=["PUT"])
@jwt_required()
def fix_item(product_id):
    try:
        jwt = get_jwt()
        user_id = get_jwt_identity()
        user = User.query.filter(User.id == user_id).first()
        if user.admin == 0 or (not jwt.get("is_admin")):
            return send_result(message="Bạn không phải admin.")
        body_request = request.get_json()
        name = body_request.get("name", "")
        price = body_request.get("price", 0)
        type_item = body_request.get("type", "")
        describe = body_request.get("describe", "")
        check_item = Product.query.filter(Product.id == product_id).first()
        if check_item is None:
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
        return send_result(data=ProductSchema().dump(check_item),
                           message="Thay đổi thông tin sản phẩm thành công", show=True)
    except Exception as ex:
        db.session.rollback()
        return send_error(message=str(ex))


@api.route("/<product_id>", methods=["DELETE"])
@jwt_required()
def remove_item(product_id):
    try:
        jwt = get_jwt()
        user_id = get_jwt_identity()
        user = User.query.filter(User.id == user_id).first()
        if user.admin == 0 or (not jwt.get("is_admin")):
            return send_result(message="Bạn không phải admin.")
        check_item = Product.query.filter(Product.id == product_id).first()
        file_path = FILE_PATH + check_item.picture
        if os.path.exists(os.path.join(file_path)):
            os.remove(file_path)
        if check_item is None:
            return send_error(message="Sản phẩm không tồn tại, F5 lại web", is_dynamic=True)
        Product.query.filter(Product.id == product_id).delete()
        db.session.flush()
        db.session.commit()
        return send_result(message="Xóa sản phẩm thành công", show=True)
    except Exception as ex:
        db.session.rollback()
        return send_error(message=str(ex))


@api.route("/<product_id>", methods=["GET"])
def get_item(product_id):
    try:

        check_item = Product.query.filter(Product.id == product_id).first()
        if check_item is None:
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
