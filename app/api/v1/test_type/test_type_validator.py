import json
import typing
from datetime import date

from marshmallow import Schema, fields, validate, ValidationError, types, validates_schema, post_dump

# Validator
from app.parser import TestSchema


class CreateTestType(Schema):
    """
    Author: trunghn
    Create Date: 28/12/2022
    Marshmallow Schema
    """
    name = fields.String(required=True, validate=[validate.Length(min=1, max=100)])


class UpdateTestType(Schema):
    """
    Author: trunghn
    Create Date: 28/12/2022
    Marshmallow Schema
    """
    is_default = fields.Boolean(required=True)


class DeleteTestType(Schema):
    """
    Author: trunghn
    Create Date: 28/12/2022
    Marshmallow Schema
    """
    new_test_type_id = fields.String(required=True, validate=[validate.Length(min=1, max=100)])




