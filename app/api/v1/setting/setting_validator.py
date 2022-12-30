import json
import typing
from datetime import date

from marshmallow import Schema, fields, validate, ValidationError, types, validates_schema, post_dump

# Validator
from app.parser import TestSchema


class UpdateMiscellaneousRequest(Schema):
    """
    Author: trunghn
    Create Date: 28/12/2022
    Marshmallow Schema
    """
    miscellaneous = fields.Dict(required=True)
    enabled = fields.Boolean(required=False)
