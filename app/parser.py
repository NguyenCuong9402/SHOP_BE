from app.extensions import ma
from app.models import Test, TestStep, TestType, TestField, TestSets, TestExecutions


class TestTypeSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = TestType
        include_fk = True


class TestStepSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = TestStep
        include_fk = True


class TestSchema(ma.SQLAlchemySchema):
    class Meta:
        include_fk = True
        model = Test
        fields = ("id", "issue_id", "test_repo", "project_id", "test_steps", "test_type", "issue_jira_id", "key", "name")

    id = ma.auto_field()
    test_steps = ma.List(ma.Nested(TestStepSchema))
    test_type = ma.Nested(TestTypeSchema(only=("name",)))


class TestFieldSchema(ma.SQLAlchemySchema):
    class Meta:
        include_fk = True
        model = TestField
        fields = ("key", "name")


class TestStepSchema(ma.SQLAlchemySchema):
    class Meta:
        include_fk = True
        model = TestType
        fields = ("key", "name")


class TestSetsSchema(ma.SQLAlchemySchema):
    class Meta:
        include_fk = True
        model = TestSets
        fields = ("id", "name", "key", "jira_id", "tests")

    id = ma.auto_field()
    tests = ma.List(ma.Nested(TestSchema))


class TestExecSchema(ma.SQLAlchemySchema):
    class Meta:
        include_fk = True
        model = TestExecutions
        fields = ("id", "name", "key", "tests")

    id = ma.auto_field()
    tests = ma.Nested(TestSchema(only=("issue_id", "test_type", "key", "name")))
