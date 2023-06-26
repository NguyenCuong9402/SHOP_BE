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