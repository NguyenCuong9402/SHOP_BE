from app.extensions import ma
from app.models import Test, TestStep, TestType, TestField, \
    TestSets, TestExecutions, MapTestExec, Defects, TestEvidence


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


# class TestTypeSchema(ma.SQLAlchemySchema):
#     class Meta:
#         include_fk = True
#         model = TestType
#         fields = ("key", "name")


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
    tests = ma.Nested(TestSchema(only=("id", "issue_id", "test_type", "key", "name")))


class TestInTestRunSchema(ma.SQLAlchemySchema):
    class Meta:
        include_fk = True
        model = Test
        fields = ("id", "issue_id", "cloud_id", "issue_jira_id", "key",
                  "name", "self", "test_repo", "project_id", "test_steps", "test_type")

    id = ma.auto_field()
    test_steps = ma.List(ma.Nested(TestStepSchema))
    test_type = ma.Nested(TestTypeSchema())


class DefectsSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        include_fk = True
        model = Defects


class TestEvidenceSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        include_fk = True
        model = TestEvidence


class TestRunExecSchema(ma.SQLAlchemySchema):
    class Meta:
        include_fk = True
        model = MapTestExec
        fields = ("id", "test_id", "exec_id", "index", "status_id", "comment",
                  "created_date", "modified_date", "tests", "total_seconds", "defects", "evidences")

    # test_id = db.Column(db.String(50), db.ForeignKey('tests.id'), nullable=True)
    # exec_id = db.Column(db.String(50), db.ForeignKey('test_executions.id'), nullable=True)
    # index = db.Column(db.Integer)
    # status_id = db.Column(db.String(50), db.ForeignKey('test_status.id'), nullable=True)
    # comment = db.Column(db.Text, nullable=True)
    # created_date = db.Column(db.Integer, default=0, index=True)
    # modified_date = db.Column(db.Integer, default=0)
    # tests = db.relationship('Test', backref=db.backref('tests_test_exec', lazy=True))
    # total_seconds = db.Column(db.Integer, default=0)
    id = ma.auto_field()
    tests = ma.Nested(TestInTestRunSchema())
    defects = ma.List(ma.Nested(DefectsSchema(only=("test_issue_id", "test_issue_key", "test_step_detail_id"))))
    evidences = ma.List(ma.Nested(TestEvidenceSchema(only=("id", "name_file", "url_file", "created_date"))))
