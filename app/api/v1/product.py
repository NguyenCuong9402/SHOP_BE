import os
import uuid
from flask import Blueprint, request, make_response, send_file, Response
from flask_jwt_extended import get_jwt_identity, get_jwt, jwt_required
from sqlalchemy import asc, desc
from io import BytesIO
import datetime
import io
import shutil

from sqlalchemy_pagination import paginate
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
        page = request.args.get('page', 1, int)
        page_size = request.args.get('page_size', 10, int)
        order = request.args.get('order', 'desc')
        text_search = request.args.get('text_search', None)
        type = request.args.get('type', None)
        if type == "" or type is None:
            query = Product.query.filter()
            if query.count() < 1:
                add_pro()
        else:
            if type not in ["quan", "ao", "phukien"]:
                return send_error(message="Invalid request", is_dynamic=True)
            query = Product.query.filter(Product.type == type)
        if text_search is not None and text_search != "":
            text_search = text_search.strip()
            text_search = text_search.lower()
            text_search = escape_wildcard(text_search)
            text_search = "%{}%".format(text_search)
            query = query.filter(Product.name.ilike(text_search))

        query = query.order_by(desc(Product.created_date)) if order == "desc" else query.order_by(asc(Product.created_date))
        paginator = paginate(query, page, page_size)

        products = ProductSchema(many=True).dump(paginator.items)
        response_data = dict(
            items=products,
            total_pages=paginator.pages if paginator.pages > 0 else 1,
            total=paginator.total
        )
        return send_result(data=response_data)
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


def add_pro():
    try:

        FILE_PATH_MAU_ANH = "app/files/mau_anh"
        FILE_PATH_PRODUCT = "app/files/product/"

        product_default = [{'name': 'quần âu caro trẻ trung', 'picture': 'quan_au_caro.jpg', "old_price":100, "type": "quan","giam_gia": 10},
                           {'name': 'quần beggy', 'picture': 'quan_beggy.jpg', "old_price": 100, "type": "quan","giam_gia": 10},
                           {'name': 'quần âu nâu', 'picture': 'quan_au_nau.jpg', "old_price": 100, "type": "quan", "giam_gia": 10},
                           {'name': 'quần thanh lịch', 'picture': 'quan_thanh_lich.jpg', "old_price": 100, "type": "quan", "giam_gia": 10}]
        list_add_data = []
        for i, product in enumerate(product_default):
            check = Product.query.filter(Product.name == product['name']).first()
            if check is None:
                product_id = str(uuid.uuid4())
                old_image_path = os.path.join(FILE_PATH_MAU_ANH, f"{product['picture']}")
                new_image_path = os.path.join(FILE_PATH_PRODUCT, f"{product_id}.jpg")
                shutil.copyfile(old_image_path, new_image_path)
                add_pro = Product(
                    id=product_id,
                    name=product['name'],
                    old_price=product['old_price'],
                    giam_gia=product['giam_gia'],
                    price=product['old_price']*(100-product['giam_gia'])/100,
                    type=product['type'],
                    describe="Sản phẩm tuyệt vời",
                    picture=product_id + '.jpg',
                    created_date=get_timestamp_now() + i
                )
                list_add_data.append(add_pro)
        db.session.bulk_save_objects(list_add_data)
        db.session.commit()
    except Exception as ex:
        return send_error(message=str(ex))