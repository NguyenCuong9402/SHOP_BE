from app.extensions import ma
from app.models import Test, TestStep, TestType


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
        fields = ("issue_id", "test_repo", "project_id", "test_steps", "test_type")

    id = ma.auto_field()
    test_steps = ma.List(ma.Nested(TestStepSchema))
    test_type = ma.Nested(TestTypeSchema(only=("name",)))
