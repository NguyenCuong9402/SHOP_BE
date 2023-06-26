import typing

from marshmallow import Schema, fields, validate, ValidationError, types, validates_schema, post_dump
from flask_marshmallow import Marshmallow

ma = Marshmallow()


class ProductSchema(Schema):
    id = fields.String()
    name = fields.String()
    price = fields.Integer()
    type = fields.String()
    describe = fields.String()
    created_date = fields.Integer()


class OrdersSchema(Schema):
    id = fields.String()
    user_id = fields.String()
    phone_number = fields.String()
    address = fields.String()
    count = fields.Integer()
    created_date = fields.Integer()
