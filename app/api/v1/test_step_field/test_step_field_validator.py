import json
import typing
from datetime import date

from marshmallow import Schema, fields, validate, ValidationError, types, validates_schema, post_dump

# Validator
from app.parser import TestSchema


class CreateTestStepField(Schema):
    """
    Author: trunghn
    Create Date: 28/12/2022
    Marshmallow Schema
    """
    name = fields.String(required=True, validate=[validate.Length(min=1, max=100)])
    description = fields.String(required=False, allow_none=True, validate=[validate.Length(min=0, max=250)])
    type = fields.String(required=True,
                         validate=validate.OneOf(
                             choices=["Toggle Switch", "Date Picker", "Radio Buttons", "Select List", "Text"]))
    field_type_values = fields.List(fields.String(), required=True)
    is_required = fields.Boolean(required=True)


class UpdateTestStepField(Schema):
    """
    Author: trunghn
    Create Date: 28/12/2022
    Marshmallow Schema
    """
    name = fields.String(required=False, validate=[validate.Length(min=1, max=100)])
    description = fields.String(required=False, allow_none=True, validate=[validate.Length(min=0, max=250)])
    type = fields.String(required=False,
                         validate=validate.OneOf(
                             choices=["Toggle Switch", "Date Picker", "Radio Buttons", "Select List"]))
    field_type_values = fields.List(fields.String(), required=False)
    is_required = fields.Boolean(required=False)
    is_disabled = fields.Boolean(required=False)

