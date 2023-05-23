from marshmallow import Schema, fields


class UserSettingValidator(Schema):
    display_column = fields.Dict()


class UserSettingSchema(Schema):
    display_column = fields.String()
