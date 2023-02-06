from marshmallow import Schema, fields, validate, ValidationError, types, validates_schema, post_dump

from app.validator import TestStatusSchema


class TestRunSchema(Schema):
    id = fields.String()
    cloud_id = fields.String()
    project_id = fields.String()

    issue_id = fields.String()
    issue_key = fields.String()
    test_case_id = fields.String()
    test_execution_id = fields.String()
    activities = fields.String()
    test_steps = fields.String()
    findings = fields.String()
    test_status_id = fields.String()
    status = fields.Nested(TestStatusSchema)
    meta_data = fields.String()
    assignee_account_id = fields.String()
    executed_account_id = fields.String()
    is_updated = fields.Boolean()
    start_date = fields.Integer()
    end_date = fields.Integer()


class CombineSchema(Schema):
    TestRun: fields.Nested(TestRunSchema)
    TestStatus: fields.Nested(TestStatusSchema)
