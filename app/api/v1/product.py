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
        file = request.files.get('file', None)
        name = request.form.get('name', '')
        price = request.form.get('price', 0)
        type_item = request.form.get('type_item', '')
        describe = request.form.get('describe', '')

        if name == "" or int(price) <= 0 or type_item not in ["ao", "quan", "phukien"]:
            return send_error(message="Vui lòng điền thêm thông tin", show=True)
        if check_coincided_name(name):
            return send_error(message="Tên sản phẩm đã tồn tại", is_dynamic=True)
        if file is None:
            product = Product(
                id=str(uuid.uuid4()),
                name=name,
                price=int(price),
                type=type_item,
                describe=describe,
                created_date=get_timestamp_now()
            )
        else:
            filename, file_extension = os.path.splitext(file.filename)
            id_product = str(uuid.uuid4())
            file_name = secure_filename(id_product + file_extension)
            if not os.path.exists(FILE_PATH_PRODUCT):
                os.makedirs(FILE_PATH_PRODUCT)
            file.save(os.path.join(FILE_PATH_PRODUCT + file_name))
            product = Product(
                id=id_product,
                name=name,
                price=int(price),
                type=type_item,
                describe=describe,
                created_date=get_timestamp_now(),
                picture=file_name
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
        else:
            order_by = "price"
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
        file = request.files.get('file', None)
        name = request.form.get('name', '')
        price_str = request.form.get('price', 0)
        type_item = request.form.get('type_item', '')
        describe = request.form.get('describe', '')
        if file is None and price_str == "" and name == "" and type_item == "" and describe == "":
            return send_error(message="Bạn không thay đổi thông tin nào", show=True)
        if price_str == "0":
            return send_error(message="Giá không hơp lệ", show=True)
        if price_str == "":
            price_str = 0
        try:
            price = int(price_str)
        except:
            return send_error(message="Giá phải là số")

        if price < 0:
            return send_error(message="Giá không hơp lệ", show=True)
        if type_item not in ["ao", "quan", "phukien", ""]:
            return send_error(message="Type không hơp lệ", show=True)
        product = Product.query.filter(Product.id == product_id).first()
        if product is None:
            return send_error(message="Sản phẩm không tồn tại")
        if check_coincided_name_product(name=name, product_id=product_id):
            return send_error(message="Tên sản phẩm đã tồn tại", is_dynamic=True)
        if name != "":
            product.name = name
            db.session.flush()

        if price != 0:
            product.price = price
            db.session.flush()

        if describe != "":
            product.describe = describe
            db.session.flush()

        if type_item != "":
            product.type = type_item
            db.session.flush()

        if file:
            filename, file_extension = os.path.splitext(file.filename)
            id_product = str(uuid.uuid4())
            file_name = secure_filename(id_product + file_extension)
            if not os.path.exists(FILE_PATH_PRODUCT):
                os.makedirs(FILE_PATH_PRODUCT)
            file.save(os.path.join(FILE_PATH_PRODUCT + file_name))
            product.picture = file_name
            db.session.flush()
        db.session.commit()
        return send_result(data=ProductSchema().dump(product),
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
        if check_item is None:
            return send_error(message="Sản phẩm không tồn tại, F5 lại web", is_dynamic=True)
        if check_item.picture is not None and check_item.picture != "":
            file_path = FILE_PATH_PRODUCT + check_item.picture
            if os.path.exists(os.path.join(file_path)):
                os.remove(file_path)
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


def check_coincided_name_product(name='', product_id=''):
    existed_name = Product.query.filter(Product.name == name, Product.id != product_id).first()
    if existed_name is None:
        return False
    return True
