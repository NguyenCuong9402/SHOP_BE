import json
import typing
from datetime import date

from marshmallow import Schema, fields, validate, ValidationError, types, validates_schema, post_dump


# Validator
class BaseValidation(Schema):

    def custom_validate(
            self,
            data: typing.Mapping,
            *,
            many: typing.Optional[bool] = None,
            partial: typing.Optional[typing.Union[bool, types.StrSequenceOrSet]] = None
    ) -> (bool, str):
        """Validate `data` against the schema, returning a dictionary of
        validation errors.

        :param data: The data to validate.
        :param many: Whether to validate `data` as a collection. If `None`, the
            value for `self.many` is used.
        :param partial: Whether to ignore missing fields and not require
            any fields declared. Propagates down to ``Nested`` fields as well. If
            its value is an iterable, only missing fields listed in that iterable
            will be ignored. Use dot delimiters to specify nested fields.
        :return:
            status validate and message_id.
            exc: data with incorrect format

        .. versionadded:: 1.1.0
        """
        try:
            self._do_load(data, many=many, partial=partial, postprocess=False)
        except ValidationError as exc:
            check = typing.cast(typing.Dict[str, typing.List[str]], exc.messages)
            if hasattr(self, 'define_message'):
                for key in check:
                    if key in self.define_message:
                        return False, self.define_message[key], exc.messages
                return False, "", exc.messages
            else:
                # return check
                return False, "", exc.messages

        return True, "", {}  # default return


class TestStepValidator(BaseValidation):
    data = fields.String(required=False)
    result = fields.String(required=True)
    customFields = fields.String(required=False)
    attachments = fields.String(required=False)
    action = fields.String(required=True)
    define_message = {
        "data": "003",
        "result": "004",
        "customFields": "005",
        "attachments": "006",
        "action": "007",
    }


class CreateTestValidator(BaseValidation):
    """
    Author: TienNguyen
    Create Date: 26/01/2022
    Marshmallow Schema
    Target: validate parameters of partner
    """
    project_id = fields.String(required=True, validates=[validate.Length(min=1, max=50)])
    cucumber = fields.String(required=False, validates=[validate.Length(min=0, max=255)])
    generic = fields.String(required=False, validates=[validate.Length(min=0, max=255)])
    issue_id = fields.String(required=False, validates=[validate.Length(min=0, max=255)])
    issue_jira_id = fields.Number(required=False)
    test_repo = fields.String(required=False, validates=[validate.Length(min=0, max=255)])
    test_type = fields.String(required=True, validates=validate.OneOf(["Manual", "Generic", "Cucumber"]))
    test_set_name = fields.String(required=False, validates=validate.Length(min=0, max=255))
    test_step = fields.List(fields.Nested(TestStepValidator))
    define_message = {
        "issue_id": "001",
        "test_type_id": "002",
        "test_set_name": "008",
        "test_step": "009",
        "project_id": "010",
        "test_type": "011"
    }


class IssueIDSchema(Schema):
    """
    Author: hungVD
    Create Date: 11/07/2022
    Marshmallow Schema
    """
    id = fields.String()


class IssueIDValidator(BaseValidation):
    """
    Author: hungVD
    Create Date: 11/07/2022
    Marshmallow Schema
    """
    issue_id = fields.List(fields.String(), required=True)


class TestRunSchema(Schema):
    """
    Author: hungVD
    Create Date: 11/07/2022
    Marshmallow Schema
    """
    id = fields.String()
    test_id = fields.String()
    exec_id = fields.String()
    index = fields.Integer()
    status_id = fields.String()
    comment = fields.String()

