import typing

from marshmallow import Schema, fields, validate, ValidationError, types, validates_schema, post_dump
from flask_marshmallow import Marshmallow

from app.models import TestRun

ma = Marshmallow()

# Validator
from app.parser import TestSchema


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


class TestSetsValidator(BaseValidation):
    id = fields.String(required=False)
    name = fields.String(required=False)
    key = fields.String(required=False)
    define_message = {
        "id": "",
        "name": "003",
        "key": "004",
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
    test_set_key = fields.String(required=False, validates=[validate.Length(min=0, max=255)])
    test_set_id = fields.String(required=False, validates=[validate.Length(min=0, max=255)])
    issue_jira_id = fields.Number(required=False)
    test_repo = fields.String(required=False, validates=[validate.Length(min=0, max=255)])
    test_type = fields.String(required=True, validates=validate.OneOf(["Manual", "Generic", "Cucumber"]))
    test_sets = fields.List(fields.Nested(TestSetsValidator))
    test_step = fields.List(fields.Nested(TestStepValidator))
    define_message = {
        "issue_id": "001",
        "test_type_id": "002",
        "test_set_name": "008",
        "test_step": "009",
        "project_id": "010",
        "test_type": "011"
    }


class UpdateTestValidator(BaseValidation):
    """
    Author: Thinh le
    Create Date: 17/7/2022
    Marshmallow Schema
    Target: validate parameters of partner
    """
    issue_jira_id = fields.String(required=False, validates=[validate.Length(min=0, max=50)])
    key = fields.String(required=False, validates=[validate.Length(min=0, max=50)])
    name = fields.String(required=False, validates=[validate.Length(min=0, max=255)])
    self = fields.String(required=False, validates=[validate.Length(min=0, max=255)])


class IssueIDSchema(Schema):
    """
    Author: hungVD
    Create Date: 11/07/2022
    Marshmallow Schema
    """
    tests = fields.Nested(TestSchema)


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
    created_date = fields.Integer()
    test_step_detail_id = fields.String()


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
    test_step_detail_id = fields.String()
    created_date = fields.Integer()


class EvidenceValidator(Schema):
    """
    Author: phongnv
    Create Date: 12/07/2022
    Marshmallow Schema
    """
    name_file = fields.String(required=True, validates=[validate.Length(min=1, max=255)])
    url_file = fields.String(required=True, validates=[validate.Length(min=1, max=500)])


class TestActivitySchema(Schema):
    """
    Author: phongnv
    Create Date: 12/07/2022
    Marshmallow Schema
    """
    id = fields.String()
    comment = fields.Dict(fields.String())
    status_change = fields.String()
    jira_user_id = fields.String()
    created_date = fields.Int()


class TestActivityValidator(Schema):
    """
    Author: phongnv
    Create Date: 12/07/2022
    Marshmallow Schema
    """
    comment = fields.String(required=True, validates=[validate.Length(min=1, max=500)])
    status_change = fields.String(required=True, validates=[validate.Length(min=1, max=500)])
    jira_user_id = fields.String(required=True, validates=[validate.Length(min=1, max=500)])


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


class TestCaseValidator(Schema):
    issue_ids = fields.List(fields.String(), required=True)
    is_delete_all = fields.Boolean()


class TestCaseFilterValidator(Schema):
    statuses = fields.List(fields.String())
    environments = fields.List(fields.String())
    testrun_started = fields.Dict()
    testrun_finished = fields.Dict()


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


class TimerSchema(Schema):
    id = fields.String()
    time_type = fields.Integer()
    test_timer = fields.Float()
    delta_time = fields.Float()
    created_date = fields.String()


class TestRunDetailSchema(Schema):
    """
    Author: HungVD
    Create Date: 21/07/2022
    Marshmallow Schema
    """
    issue_id = fields.String()
    test_repo = fields.String()
    project_id = fields.Integer()
    issue_jira_id = fields.String()
    key = fields.String()
    name = fields.String()
    test_type_id = fields.String()
    steps = fields.List(fields.Nested(TestStepRunSchema))


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
    total_seconds = fields.Integer()
    steps = fields.List(fields.Nested(TestStepRunSchema))
    defects = fields.List(fields.Nested(DefectsSchema))
    evidences = fields.List(fields.Nested(EvidenceSchema))
    test_timer = fields.List(fields.Nested(TimerSchema))
    list_activity = fields.List(fields.Nested(TestActivitySchema))
    tests = fields.Nested(TestRunDetailSchema)


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
    issue_id = fields.String(required=True)
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


class FiltersRepositoryValidator(BaseValidation):
    """
    Author: hungVD
    Create Date: 11/07/2022
    Marshmallow Schema
    """
    test_issue_ids = fields.List(fields.String(), required=False)
    statuses = fields.List(fields.String(), required=False)
    test_sets = fields.List(fields.String(), required=False)


class GetExecutionValidator(BaseValidation):
    """
    Author: hungVD
    Create Date: 11/07/2022
    Marshmallow Schema
    """
    fields_column = fields.List(
        fields.String(validates=validate.OneOf(["defects", "comment", "status_id"]), required=True), required=False)
    filters = fields.Nested(FiltersRepositoryValidator, required=False)


class TestMapRepoSchema(Schema):
    """
    Author: hungVD
    Create Date: 11/07/2022
    Marshmallow Schema
    """
    id = fields.String()
    issue_id = fields.String()
    issue_jira_id = fields.String()


class MapRepoSchema(Schema):
    """
    Author: hungVD
    Create Date: 11/07/2022
    Marshmallow Schema
    """
    test_id = fields.String()
    test_issue = fields.Nested(TestMapRepoSchema)


class RepositorySchema(Schema):
    """
    Author: hungVD
    Create Date: 11/07/2022
    Marshmallow Schema
    """
    id = fields.String()
    parent_id = fields.String()
    name = fields.String()
    index = fields.Integer()
    created_date = fields.Integer()
    children_folder = fields.List(fields.Nested(lambda: RepositorySchema()))
    count_test = fields.Integer()


class RepositoryProjectSchema(Schema):
    id = fields.String()
    name = fields.String()
    children_folder = fields.List(fields.Nested(lambda: RepositorySchema()))


class TestExecutionSchema(Schema):
    """
    Author: hungvd
    Create Date: 21/07/2022
    Marshmallow Schema
    """
    id = fields.String()
    project_id = fields.String()
    cloud_id = fields.String()
    issue_id = fields.String()
    issue_key = fields.String()
    created_date = fields.String()


class SettingSchema(Schema):
    """
    Author: trunghn
    Create Date: 28/12/2022
    Marshmallow Schema
    """
    id = fields.String()
    miscellaneous = fields.String()
    test_type = fields.String()
    test_environment = fields.String()
    test_step_field = fields.String()
    test_run_custom_field = fields.String()
    test_test_executions_status = fields.String()
    project_id = fields.String()
    project_key = fields.String()
    cloud_id = fields.String()
    site_url = fields.String()


class TestStepFieldSchema(Schema):
    id = fields.String()
    name = fields.String()
    description = fields.String()
    field_type_values = fields.Raw()
    type = fields.String()
    is_required = fields.Boolean()
    is_disabled = fields.Boolean()
    is_native = fields.Boolean()
    index = fields.Integer()


class TestTypeSchema(Schema):
    id = fields.String()
    name = fields.String()
    kind = fields.String()
    index = fields.Integer()
    is_default = fields.Boolean()
    number_of_tests = fields.Integer()


class TestRunFieldSchema(Schema):
    id = fields.String()
    name = fields.String()
    description = fields.String()
    field_type_values = fields.Raw()
    type = fields.String()
    is_required = fields.Boolean()
    is_disabled = fields.Boolean()
    is_native = fields.Boolean()
    index = fields.Integer()
    test_types = fields.List(fields.Nested(TestTypeSchema))


class TestStatusSchema(Schema):
    id = fields.String()
    name = fields.String()
    description = fields.String()
    color = fields.String()
    is_show = fields.Boolean()
    is_default = fields.Boolean()


class TestEnvironmentSchema(Schema):
    id = fields.String()
    name = fields.String()
    description = fields.String()
    url = fields.String()


class TestCaseSchema(Schema):
    id = fields.String()
    issue_id = fields.String()
    issue_key = fields.String()
    project_id = fields.String()
    cloud_id = fields.String()
    created_date = fields.Integer()


class TestSetSchema(Schema):
    id = fields.String()
    issue_id = fields.String()
    issue_key = fields.String()
    project_id = fields.String()
    cloud_id = fields.String()
    created_date = fields.Integer()


class TestSetTestCasesSchema(Schema):
    id = fields.String()
    index = fields.Int()
    issue_id = fields.String()
    issue_key = fields.String()
    project_id = fields.String()
    cloud_id = fields.String()
    created_date = fields.Integer()


class TestExecutionSchema(Schema):
    id = fields.String()
    issue_id = fields.String()
    project_id = fields.String()
    cloud_id = fields.String()
    created_date = fields.Integer()


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


class UploadValidation(Schema):
    """
    Validator
    Ex:
    {
        "file_name": "default_avatars.png",
        "prefix": "avatars"
    }
    """
    file_name = fields.String(required=False, validate=validate.Length(min=1, max=50))
    prefix = fields.String(required=True,
                           validate=validate.OneOf(choices=["test-case", "test-run"],
                                                   error="Prefix must be 'test-case','test-run'."))


class HistorySchema(Schema):
    user_id = fields.String()
    activities = fields.String()
    history_category = fields.Integer()
    action_name = fields.String()
    detail_of_action = fields.Dict()
    created_date = fields.Integer()


class TestCaseTestStepSchema(Schema):
    id = fields.String()
    cloud_id = fields.String()
    project_key = fields.String()
    project_id = fields.String()
    action = fields.String()
    data = fields.String()
    result = fields.String()
    custom_fields = fields.List(fields.String())
    attachments = fields.String()
    index = fields.Integer()
    test_case_id_reference = fields.String()


class TestStepTestRunSchema(Schema):
    test_step_id = fields.String()
    action = fields.String()
    data = fields.String()
    result = fields.String()
    custom_fields = fields.List(fields.String())
    attachments = fields.String()
    created_date = fields.Integer()
    issue_key = fields.String()
    test_step_detail_id = fields.String()


class PostDefectSchema(Schema):
    issue_key = fields.String()
    issue_id = fields.String()
    test_kind = fields.String()
    test_step_detail_id = fields.String()


class TestCaseTestRunSchema(Schema):
    id = fields.String()
    issue_id = fields.String()
    issue_key = fields.String()
    project_id = fields.String()
    cloud_id = fields.String()
    test_execution_created_date = fields.Integer()
    test_run_id = fields.String()
    test_run_issue_id = fields.String()
    test_run_issue_key = fields.String()
    created_date = fields.Integer()
    test_status_id = fields.String()
    is_updated = fields.Boolean()
    start_date = fields.Integer()
    end_date = fields.Integer()


class TestExecutionTestRunSchema(Schema):
    id = fields.String()
    test_type_id = fields.String()
    issue_id = fields.String()
    issue_key = fields.String()
    project_id = fields.String()
    cloud_id = fields.String()
    test_case_created_date = fields.Integer()
    test_run_id = fields.String()
    test_run_issue_id = fields.String()
    test_run_issue_key = fields.String()
    created_date = fields.Integer()
    test_status_id = fields.String()
    is_updated = fields.Boolean()
    start_date = fields.Integer()
    end_date = fields.Integer()
    index = fields.Integer()
    is_archived = fields.Integer()
    test_type_name = fields.String()