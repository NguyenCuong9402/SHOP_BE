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
    test_id = fields.String()


class IssueIDValidator(BaseValidation):
    """
    Author: hungVD
    Create Date: 11/07/2022
    Marshmallow Schema
    """
    issue_id = fields.List(fields.String(), required=True)


class DefectsSchema(Schema):
    """
    Author: phongnv
    Create Date: 12/07/2022
    Marshmallow Schema
    """
    id = fields.String()
    test_issue_key = fields.String()
    test_issue_id = fields.String()


class DefectsValidator(Schema):
    """
    Author: phongnv
    Create Date: 12/07/2022
    Marshmallow Schema
    """
    test_issue_id = fields.String(required=True, validates=[validate.Length(min=1, max=255)])
    test_issue_key = fields.String(required=True, validates=[validate.Length(min=1, max=255)])


class EvidenceSchema(Schema):
    """
    Author: phongnv
    Create Date: 12/07/2022
    Marshmallow Schema
    """
    id = fields.String()
    name_file = fields.String()
    url_file = fields.String()


class EvidenceValidator(Schema):
    """
    Author: phongnv
    Create Date: 12/07/2022
    Marshmallow Schema
    """
    name_file = fields.String(required=True, validates=[validate.Length(min=1, max=255)])
    url_file = fields.String(required=True, validates=[validate.Length(min=1, max=500)])


class TestStatusValidator(Schema):
    """
    Author: phongnv
    Create Date: 12/07/2022
    Marshmallow Schema
    """
    status_id = fields.String(required=True, validates=[validate.Length(min=1, max=50)])


class CommentValidator(Schema):
    """
    Author: phongnv
    Create Date: 12/07/2022
    Marshmallow Schema
    """
    content = fields.String(required=False, validates=[validate.Length(min=0, max=500)])


class TestStepRunSchema(Schema):
    """
    Author: phongnv
    Create Date: 12/07/2022
    Marshmallow Schema
    """
    id = fields.String()
    status_id = fields.String()
    comment = fields.String()
    defects = fields.List(fields.Nested(DefectsSchema))
    evidences = fields.List(fields.Nested(EvidenceSchema))


class TestTimerSchema(Schema):
    """
    Author: phongnv
    Create Date: 12/07/2022
    Marshmallow Schema
    """
    id = fields.String()
    time_type = fields.String()
    date_time = fields.DateTime()


class TestTimerValidator(Schema):
    """
    Author: phongnv
    Create Date: 12/07/2022
    Marshmallow Schema
    """
    time_type = fields.Number(required=True)
    date_time = fields.DateTime()


class TestRunSchema(Schema):
    """
    Author: phongnv
    Create Date: 12/07/2022
    Marshmallow Schema
    """
    id = fields.String()
    test_id = fields.String()
    exec_id = fields.String()
    index = fields.Integer()
    status_id = fields.String()
    comment = fields.String()
    steps = fields.List(fields.Nested(TestStepRunSchema))
    defects = fields.List(fields.Nested(DefectsSchema))
    evidences = fields.List(fields.Nested(EvidenceSchema))
    test_timer = fields.List(fields.Nested(TestTimerSchema))


class TestRunBackNextSchema(Schema):
    """
    Author: phongnv
    Create Date: 12/07/2022
    Marshmallow Schema
    """
    back_id = fields.String()
    next_id = fields.String()


class TestExecValidator(BaseValidation):
    """
    Author: hungVD
    Create Date: 11/07/2022
    Marshmallow Schema
    """
    id = fields.String(required=True)
    name = fields.String(required=True)
    key = fields.String(required=True)


class RepoValidator(BaseValidation):
    """
    Author: hungVD
    Create Date: 11/07/2022
    Marshmallow Schema
    """
    id = fields.String(required=True, validates=[validate.Length(min=1, max=50)])
    name = fields.String(required=True, validates=[validate.Length(min=1, max=255)])
    parent_folder_id = fields.String(required=True)
    project_id = fields.String(required=True)


class MoveRepoValidator(BaseValidation):
    """
    Author: hungVD
    Create Date: 11/07/2022
    Marshmallow Schema
    """
    id = fields.String(required=True, validates=[validate.Length(min=1, max=50)])
    index = fields.Number(required=True)
    parent_folder_id = fields.String(required=True)
    project_id = fields.String(required=True)


class RepositoryAddIssueValidator(BaseValidation):
    """
    Author: hungVD
    Create Date: 11/07/2022
    Marshmallow Schema
    """
    issue_id = fields.List(fields.String(), required=True)
    index = fields.Number(required=True)
    folder_id = fields.String(required=True)
    project_id = fields.String(required=True)


class GetRepositoryValidator(BaseValidation):
    """
    Author: hungVD
    Create Date: 11/07/2022
    Marshmallow Schema
    """
    folder_id = fields.String(required=True)
    project_id = fields.String(required=True)


