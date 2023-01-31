import json
import typing
from datetime import date

from marshmallow import Schema, fields, validate, ValidationError, types, validates_schema, post_dump

# Validator
from app.parser import TestSchema


class CreateTestStatus(Schema):
    """
    Author: trunghn
    Create Date: 28/12/2022
    Marshmallow Schema
    """
    name = fields.String(required=True, validate=[validate.Length(min=1, max=100)])
    description = fields.String(required=True, validate=[validate.Length(min=1, max=250)])
    color = fields.String(required=True, validate=[validate.Length(min=1, max=100)])
    is_show = fields.Boolean(required=True)


class UpdateTestStatus(Schema):
    """
    Author: trunghn
    Create Date: 28/12/2022
    Marshmallow Schema
    """
    name = fields.String(required=False, validate=[validate.Length(min=1, max=100)])
    description = fields.String(required=False, validate=[validate.Length(min=1, max=250)])
    color = fields.String(required=False, validate=[validate.Length(min=1, max=100)])
    is_show = fields.Boolean(required=False)
