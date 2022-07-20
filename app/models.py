# coding: utf-8
from sqlalchemy.orm import relationship
from sqlalchemy import ForeignKey, TEXT, asc
from app.extensions import db
from sqlalchemy.dialects.mysql import INTEGER
from sqlalchemy.ext.hybrid import hybrid_property


class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.String(50), primary_key=True)
    username = db.Column(db.String(100), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)


"""
Many to many relationship
Read more: https://flask-sqlalchemy.palletsprojects.com/en/2.x/models/
Test Sets and Test Runs table
"""

test_testsets = db.Table('map_test_testsets',
                         db.Column('test_id', db.String(50), db.ForeignKey('tests.id'), primary_key=True),
                         db.Column('testset_id', db.String(50), db.ForeignKey('test_sets.id'), primary_key=True)
                         )


class Test(db.Model):
    __tablename__ = 'tests'

    id = db.Column(db.String(50), primary_key=True)
    cucumber = db.Column(db.String(255), nullable=True)
    generic = db.Column(db.String(255), nullable=True)
    issue_id = db.Column(db.String(255), nullable=False)
    issue_jira_id = db.Column(db.String(255), nullable=True)
    key = db.Column(db.String(255), nullable=True)
    name = db.Column(db.String(255), nullable=True)
    self = db.Column(db.String(255), nullable=True)
    test_repo = db.Column(db.String(255), nullable=True)
    project_id = db.Column(db.String(50), nullable=False)
    test_type_id = db.Column(db.String(50), db.ForeignKey('test_type.id'), nullable=True)
    test_steps = db.relationship('TestStep', backref='test_steps', lazy=True)
    test_type = db.relationship('TestType', backref='test_types', lazy=True)
    test_sets = db.relationship('TestSets', secondary=test_testsets, lazy='subquery',
                                backref=db.backref('test_sets', lazy=True), viewonly=True)


class ProjectSetting(db.Model):
    __tablename__ = 'project_setting'

    id = db.Column(db.String(50), primary_key=True)
    description = db.Column(db.Integer, nullable=True)
    project_name = db.Column(db.String(255), nullable=True)
    project_id = db.Column(db.String(255), nullable=False)


class TestType(db.Model):
    __tablename__ = 'test_type'

    id = db.Column(db.String(50), primary_key=True)
    index = db.Column(db.Integer, nullable=True, autoincrement=True)
    name = db.Column(db.String(255), nullable=False)
    kind = db.Column(db.String(255), nullable=True)
    order = db.Column(db.String(255), nullable=True)
    default = db.Column(db.String(255), nullable=True)
    project_setting_id = db.Column(db.String(50),
                                   db.ForeignKey('project_setting.id', ondelete='CASCADE', onupdate='CASCADE'),
                                   nullable=True)


class TestField(db.Model):
    __tablename__ = 'test_field'

    id = db.Column(db.String(50), primary_key=True)
    key = db.Column(db.Integer, nullable=True, autoincrement=True)
    name = db.Column(db.String(255), nullable=False)
    project_setting_id = db.Column(db.String(50),
                                   db.ForeignKey('project_setting.id', ondelete='CASCADE', onupdate='CASCADE'),
                                   nullable=True)


class TestStepsConfig(db.Model):
    __tablename__ = 'test_steps_config'

    id = db.Column(db.String(50), primary_key=True)
    key = db.Column(db.Integer, nullable=True, autoincrement=True)
    name = db.Column(db.String(255), nullable=False)
    project_setting_id = db.Column(db.String(50),
                                   db.ForeignKey('project_setting.id', ondelete='CASCADE', onupdate='CASCADE'),
                                   nullable=True)


class TestStep(db.Model):
    __tablename__ = 'test_steps'

    id = db.Column(db.String(50), primary_key=True)
    data = db.Column(db.Text, nullable=True)
    result = db.Column(db.Text, nullable=True)
    customFields = db.Column(db.Text, nullable=True)
    attachments = db.Column(db.Text, nullable=True)
    index = db.Column(db.Integer, nullable=True)
    action = db.Column(db.Text, nullable=True)
    test_id = db.Column(db.String(50), db.ForeignKey('tests.id', ondelete='CASCADE', onupdate='CASCADE'),
                        nullable=False)


class TestSets(db.Model):
    __tablename__ = 'test_sets'
    id = db.Column(db.String(50), primary_key=True)
    tests = db.relationship('Test', secondary=test_testsets, lazy='subquery',
                            backref=db.backref('tests', lazy=True))
    name = db.Column(db.String(255), nullable=True)
    key = db.Column(db.String(255), nullable=True)
    jira_id = db.Column(db.String(255), nullable=True)


"""
Many to many relationship
Read more: https://flask-sqlalchemy.palletsprojects.com/en/2.x/models/
Test Sets and Test Runs table
"""

test_test_executions = db.Table('map_test_executions',
                                db.Column('test_id', db.String(50), db.ForeignKey('tests.id'), primary_key=True),
                                db.Column('test_execution_id', db.String(50), db.ForeignKey('test_executions.id'),
                                          primary_key=True)
                                )


class TestExecutions(db.Model):
    __tablename__ = 'test_executions'
    id = db.Column(db.String(50), primary_key=True)
    tests = db.relationship('Test', secondary=test_test_executions, lazy='subquery',
                            backref=db.backref('test_execution_tests', lazy=True))
    name = db.Column(db.String(255), nullable=True)
    key = db.Column(db.String(255), nullable=True)


class Message(db.Model):
    __tablename__ = 'message'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    message_id = db.Column(db.String(50), unique=True)
    description = db.Column(db.String(255))
    show = db.Column(db.Boolean, default=0)
    duration = db.Column(db.Integer, default=5)
    status = db.Column(db.String(20), default='success')
    message = db.Column(db.String(500), nullable=False)
    dynamic = db.Column(db.Boolean, default=0)
    object = db.Column(db.String(255))


"""
Define table for handle run test execution
"""


class TestStatus(db.Model):
    __tablename__ = 'test_status'
    id = db.Column(db.String(50), primary_key=True)
    value = db.Column(db.String(255))
    type = db.Column(db.String(255))
    project_setting_id = db.Column(db.String(255), nullable=True)


class MapTestExec(db.Model):
    __tablename__ = 'map_test_exec'
    id = db.Column(db.String(50), primary_key=True)
    test_id = db.Column(db.String(50), db.ForeignKey('tests.id'), nullable=True)
    exec_id = db.Column(db.String(50), db.ForeignKey('test_executions.id'), nullable=True)
    index = db.Column(db.Integer)
    status_id = db.Column(db.String(50), db.ForeignKey('test_status.id'), nullable=True)
    comment = db.Column(db.Text, nullable=True)
    created_date = db.Column(db.Integer, default=0, index=True)
    modified_date = db.Column(db.Integer, default=0)
    tests = db.relationship('Test', backref=db.backref('tests_test_exec', lazy=True))
    total_seconds = db.Column(db.Integer, default=0)

    @hybrid_property
    def steps(self):
        steps = TestStepDetail.order_by(asc(TestStepDetail.created_date)).query.filter_by(
            map_test_exec_id=self.id).all()
        return steps

    @hybrid_property
    def defects(self):
        defects = Defects.query.order_by(asc(Defects.created_date)).filter_by(map_test_exec_id=self.id).all()
        return defects

    @hybrid_property
    def evidences(self):
        evidences = TestEvidence.query.order_by(asc(TestEvidence.created_date)).filter_by(
            map_test_exec_id=self.id).all()
        return evidences

    @hybrid_property
    def test_timer(self):
        test_timer = TestTimer.query.order_by(asc(TestTimer.created_date)).filter_by(map_test_exec_id=self.id).all()
        return test_timer

    @hybrid_property
    def list_activity(self):
        list_activity = TestActivity.query.order_by(asc(TestActivity.created_date)).filter_by(
            map_test_exec_id=self.id).all()
        return list_activity


class TestStepDetail(db.Model):
    __tablename__ = 'test_step_details'
    id = db.Column(db.String(50), primary_key=True)
    status_id = db.Column(db.String(50), db.ForeignKey('test_status.id', ondelete='CASCADE', onupdate='CASCADE'),
                          nullable=True)
    test_step_id = db.Column(db.String(50),
                             db.ForeignKey('test_steps.id', ondelete='CASCADE', onupdate='CASCADE'),
                             nullable=True)
    map_test_exec_id = db.Column(db.String(50),
                                 db.ForeignKey('map_test_exec.id', ondelete='CASCADE', onupdate='CASCADE'),
                                 nullable=True)
    comment = db.Column(db.Text, nullable=True)
    created_date = db.Column(db.Integer, default=0, index=True)
    modified_date = db.Column(db.Integer, default=0)

    @hybrid_property
    def defects(self):
        defects = Defects.query.order_by(asc(Defects.created_date)).filter_by(test_step_detail_id=self.id).all()
        return defects

    @hybrid_property
    def evidences(self):
        evidences = TestEvidence.query.order_by(asc(TestEvidence.created_date)).filter_by(
            test_step_detail_id=self.id).all()
        return evidences


class TestActivity(db.Model):
    __tablename__ = 'test_activity'
    id = db.Column(db.String(50), primary_key=True)
    map_test_exec_id = db.Column(db.String(50),
                                 db.ForeignKey('map_test_exec.id', ondelete='CASCADE', onupdate='CASCADE'),
                                 nullable=True)
    comment = db.Column(db.Text, nullable=True)
    status_change = db.Column(db.Text, nullable=True)
    jira_user_id = db.Column(db.Text, nullable=True)
    created_date = db.Column(db.Integer, default=0, index=True)
    modified_date = db.Column(db.Integer, default=0)


class Defects(db.Model):
    __tablename__ = 'defects'
    id = db.Column(db.String(50), primary_key=True)
    map_test_exec_id = db.Column(db.String(50),
                                 db.ForeignKey('map_test_exec.id', ondelete='CASCADE', onupdate='CASCADE'),
                                 nullable=True)
    test_step_detail_id = db.Column(db.String(50),
                                    db.ForeignKey('test_step_details.id', ondelete='CASCADE', onupdate='CASCADE'),
                                    nullable=True)

    test_issue_key = db.Column(db.Text, nullable=True)
    test_issue_id = db.Column(db.Text, nullable=True)
    created_date = db.Column(db.Integer, default=0, index=True)
    modified_date = db.Column(db.Integer, default=0)


class TestEvidence(db.Model):
    __tablename__ = 'test_evidence'
    id = db.Column(db.String(50), primary_key=True)
    map_test_exec_id = db.Column(db.String(50),
                                 db.ForeignKey('map_test_exec.id', ondelete='CASCADE', onupdate='CASCADE'),
                                 nullable=True)
    test_step_detail_id = db.Column(db.String(50),
                                    db.ForeignKey('test_step_details.id', ondelete='CASCADE', onupdate='CASCADE'),
                                    nullable=True)
    name_file = db.Column(db.Text, nullable=True)
    url_file = db.Column(db.Text, nullable=True)
    created_date = db.Column(db.Integer, default=0, index=True)
    modified_date = db.Column(db.Integer, default=0)


class TestTimer(db.Model):
    __tablename__ = 'test_timer'
    id = db.Column(db.String(50), primary_key=True)
    map_test_exec_id = db.Column(db.String(50),
                                 db.ForeignKey('map_test_exec.id', ondelete='CASCADE', onupdate='CASCADE'),
                                 nullable=True)
    time_type = db.Column(db.Integer, default=1)  # 1 start time, 2 end time
    date_time = db.Column(db.DATE)  # format %Y-%m-%d %H:%M:%S.%f
    str_date_time = db.Column(db.Text, nullable=True)
    created_date = db.Column(db.Integer, default=0, index=True)
    modified_date = db.Column(db.Integer, default=0)


class TestRepo(db.Model):
    __tablename__ = 'test_repo'
    id = db.Column(db.String(50), primary_key=True)
    folder_id = db.Column(db.String(50), unique=True)
    parent_id = db.Column(db.String(50))
    name = db.Column(db.String(500))
    create_date = db.Column(INTEGER(unsigned=True), default=0, index=True)
    project_id = db.Column(db.String(50))
    index = db.Column(db.Integer)

    @hybrid_property
    def map_test_repo(self):
        map_test_repo = MapRepo.query.filter_by(test_repo_id=self.id).order_by(MapRepo.index.asc()).all()
        return map_test_repo

    @hybrid_property
    def children_folder(self):
        children_repo = TestRepo.query.filter_by(parent_id=self.folder_id).order_by(TestRepo.index.asc()).all()
        return children_repo


class MapRepo(db.Model):
    __tablename__ = 'map_test_repo'
    id = db.Column(db.String(50), primary_key=True)
    test_id = db.Column(ForeignKey('tests.id', ondelete='SET NULL', onupdate='CASCADE'), index=True)
    test_repo_id = db.Column(ForeignKey('test_repo.id', ondelete='SET NULL', onupdate='CASCADE'), index=True)
    create_date = db.Column(INTEGER(unsigned=True), default=0, index=True)
    index = db.Column(db.Integer)

    test_issue = db.relationship('Test', foreign_keys="MapRepo.test_id")
