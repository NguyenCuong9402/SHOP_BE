import typing

from marshmallow import Schema, fields, validate, ValidationError, types, validates_schema, post_dump
from flask_marshmallow import Marshmallow

ma = Marshmallow()


class ReviewsSchema(Schema):
    id = fields.String()
    user_id = fields.String()
    user_name = fields.String()
    comment = fields.String()
    created_date = fields.Integer()


class ProductSchema(Schema):
    id = fields.String()
    name = fields.String()
    price = fields.Integer()
    phan_loai_id = fields.String()
    describe = fields.String()
    created_date = fields.Integer()
    picture = fields.String()
    reviews = fields.List(fields.Nested(ReviewsSchema))
    old_price = fields.Integer()
    giam_gia = fields.Integer()
    sold_count = fields.Integer()
    cac_mau = fields.List(fields.String())


class OrderItemsSchema(Schema):
    id = fields.String()
    product_id = fields.String()
    quantity = fields.Integer()
    size = fields.String()
    color = fields.String()
    created_date = fields.Integer()
    product_name = fields.String()
    count = fields.Integer()


class OrdersSchema(Schema):
    phone_number = fields.String()
    address = fields.String()
    count = fields.Integer()
    order_items = fields.List(fields.Nested(OrderItemsSchema))
    created_date = fields.Integer()


class HistoryOrdersSchema(Schema):
    id = fields.String()
    user_id = fields.String()
    user_name = fields.String()
    phone_number = fields.String()
    address = fields.String()
    tinh = fields.String()
    huyen = fields.String()
    xa = fields.String()
    loi_nhan = fields.String()
    ship_id = fields.String()
    count = fields.Integer()
    created_date = fields.Integer()
    order_items = fields.List(fields.Nested(OrderItemsSchema))
    tong_thanh_toan = fields.Integer()
    don_vi_ship = fields.String()
    gia_ship = fields.Integer()
    trang_thai = fields.Bool()


class UserSchema(Schema):
    id = fields.String()
    name_user = fields.String()
    phone_number = fields.String()
    email = fields.String()
    address = fields.String()
    tinh = fields.String()
    huyen = fields.String()
    xa = fields.String()
    created_date = fields.Integer()
    gender = fields.Integer()
    picture = fields.String()
    admin = fields.Integer()
    count_money_buy = fields.Integer()
    birthday = fields.Date()
    is_active = fields.Bool()


class CartItemsSchema(Schema):
    id = fields.String()
    product_id = fields.String()
    name_product = fields.String()
    price = fields.Integer()
    created_date = fields.Integer()
    quantity = fields.Integer()
    size = fields.String()
    color = fields.String()
    total = fields.Integer()
    cac_mau = fields.List(fields.String)


class GetTypeSchema(Schema):
    id = fields.String()
    name = fields.String()


class DiaChiVnSchema(Schema):
    tinh = fields.String()
    huyen = fields.String()
    xa = fields.String()


class ShipperSchema(Schema):
    id = fields.String()
    name = fields.String()
    gia_ship = fields.Integer()