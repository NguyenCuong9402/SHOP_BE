from marshmallow import Schema, fields, validate


class CreateTestEnvironment(Schema):
    """
    Author: trunghn
    Create Date: 28/12/2022
    Marshmallow Schema
    """
    name = fields.String(required=True, validate=[validate.Length(min=1, max=100)])
    description = fields.String(required=False, allow_none=True, validate=[validate.Length(min=0, max=250)])
    url = fields.String(required=False, allow_none=True, validate=[validate.Length(min=0, max=1000)])


class UpdateTestEnvironment(Schema):
    """
    Author: trunghn
    Create Date: 28/12/2022
    Marshmallow Schema
    """
    description = fields.String(required=False, allow_none=True, validate=[validate.Length(min=0, max=250)])
    url = fields.String(required=False, allow_none=True, validate=[validate.Length(min=0, max=250)])


class DeleteTestEnvironment(Schema):
    """
    Author: trunghn
    Create Date: 28/12/2022
    Marshmallow Schema
    """
    ids = fields.List(fields.String)
    is_delete_all = fields.Boolean()


class AddTestEnvironment(Schema):
    """
        Author: CuongNguyen
        Create Date: 5/5/2023
        Marshmallow Schema
        """
    test_environment_ids = fields.List(fields.String)
