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
    type = fields.String()
    describe = fields.String()
    created_date = fields.Integer()
    picture = fields.String()
    reviews = fields.List(fields.Nested(ReviewsSchema))


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
    count = fields.Integer()
    created_date = fields.Integer()


class UserSchema(Schema):
    id = fields.String()
    name_user = fields.String()
    phone_number = fields.String()
    email = fields.String()
    address = fields.String()
    created_date = fields.Integer()
    picture = fields.String()
    admin = fields.Integer()
    count_money_buy = fields.Integer()





class CartItemsSchema(Schema):
    id = fields.String()
    product_id = fields.String()
    name_product = fields.String()
    price = fields.Integer()
    created_date = fields.Integer()
    quantity = fields.Integer()
    size = fields.String()
    color = fields.String()

