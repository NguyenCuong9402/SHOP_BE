# coding: utf-8
import json
from typing import List

from sqlalchemy.orm import relationship
from sqlalchemy import ForeignKey, TEXT, asc, CheckConstraint
from app.extensions import db
from sqlalchemy.dialects.mysql import INTEGER
from sqlalchemy.ext.hybrid import hybrid_property


# from app.utils import get_timestamp_now


class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.String(50), primary_key=True)
    username = db.Column(db.String(100), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)


# class Test(db.Model):
#     __tablename__ = 'tests'
#
#     id = db.Column(db.String(50), primary_key=True)
#     cucumber = db.Column(db.String(255), nullable=True)
#     generic = db.Column(db.String(255), nullable=True)
#     issue_id = db.Column(db.String(255), nullable=False)
#     cloud_id = db.Column(db.String(255), nullable=False)
#     issue_jira_id = db.Column(db.String(255), nullable=True)
#     key = db.Column(db.String(255), nullable=True)
#     name = db.Column(db.String(255), nullable=True)
#     self = db.Column(db.String(255), nullable=True)
#     test_repo = db.Column(db.String(255), nullable=True)
#     project_id = db.Column(db.String(50), nullable=False)
#     test_type_id = db.Column(db.String(50), db.ForeignKey('test_type.id'), nullable=True)
#     test_steps = db.relationship('TestStep', backref='test_steps', lazy=True)
#     test_type = db.relationship('TestType', backref='test_types', lazy=True)
#     test_sets = db.relationship('TestSets', secondary=test_testsets, lazy='subquery',
#                                 backref=db.backref('test_sets', lazy=True), viewonly=True)
#     created_date = db.Column(db.Integer, default=0)
#     modified_date = db.Column(db.Integer, default=0)


class ProjectSetting(db.Model):
    __tablename__ = 'project_setting'

    id = db.Column(db.String(50), primary_key=True)
    description = db.Column(db.Integer, nullable=True)
    project_name = db.Column(db.String(255), nullable=True)
    project_id = db.Column(db.String(255), nullable=False)


test_type_test_run_field = db.Table('test_type_test_run_field',
                                    db.Column('test_type_id', db.String(50), db.ForeignKey('test_type.id'),
                                              primary_key=True),
                                    db.Column('test_run_field_id', db.String(50), db.ForeignKey('test_run_field.id'),
                                              primary_key=True)
                                    )


class TestType(db.Model):
    __tablename__ = 'test_type'

    id = db.Column(db.String(50), primary_key=True)
    index = db.Column(db.Integer, nullable=True, autoincrement=True)
    name = db.Column(db.String(255), nullable=False)
    kind = db.Column(db.String(255), nullable=True)
    order = db.Column(db.String(255), nullable=True)
    is_default = db.Column(db.Boolean, nullable=True)
    project_setting_id = db.Column(db.String(50),
                                   db.ForeignKey('project_setting.id', ondelete='CASCADE', onupdate='CASCADE'),
                                   nullable=True)
    cloud_id = db.Column(db.String(255), nullable=True)
    project_key = db.Column(db.String(50))
    project_id = db.Column(db.String(50))
    index = db.Column(db.Integer, nullable=True)
    created_date = db.Column(db.Integer, default=0)
    modified_date = db.Column(db.Integer, default=0)

    @classmethod
    def get_by_id(cls, _id):
        return cls.query.get(_id)

    @hybrid_property
    def number_of_tests(self):
        count = TestCase.query.filter(TestCase.test_type_id == self.id).count()
        return count


class TestRunField(db.Model):
    __tablename__ = 'test_run_field'
    id = db.Column(db.String(50), primary_key=True)
    name = db.Column(db.String(250))
    description = db.Column(db.String(250))
    type_values \
        = db.Column(db.Text())
    type = db.Column(db.String(250))
    is_required = db.Column(db.Boolean, default=0)
    is_disabled = db.Column(db.Boolean, default=0)
    is_native = db.Column(db.Boolean, default=0)
    # Index order of list
    index = db.Column(db.Integer)
    cloud_id = db.Column(db.String(50), nullable=True)
    project_key = db.Column(db.String(50))
    project_id = db.Column(db.String(50))
    site_url = db.Column(db.String(255), nullable=True)
    test_types = db.relationship('TestType', order_by=TestType.created_date, secondary=test_type_test_run_field,
                                 lazy='subquery',
                                 backref=db.backref('test_run_fields', lazy=True))
    created_date = db.Column(db.Integer, default=0)
    modified_date = db.Column(db.Integer, default=0)

    @classmethod
    def get_by_id(cls, _id):
        return cls.query.get(_id)

    @hybrid_property
    def field_type_values(self):
        _type_values = json.loads(self.type_values)
        return _type_values


class TestField(db.Model):
    __tablename__ = 'test_field'

    id = db.Column(db.String(50), primary_key=True)
    key = db.Column(db.Integer, nullable=True, autoincrement=True)
    name = db.Column(db.String(255), nullable=False)
    project_setting_id = db.Column(db.String(50),
                                   db.ForeignKey('project_setting.id', ondelete='CASCADE', onupdate='CASCADE'),
                                   nullable=True)
    created_date = db.Column(db.Integer, default=0)
    modified_date = db.Column(db.Integer, default=0)


class TestStepsConfig(db.Model):
    __tablename__ = 'test_steps_config'

    id = db.Column(db.String(50), primary_key=True)
    key = db.Column(db.Integer, nullable=True, autoincrement=True)
    name = db.Column(db.String(255), nullable=False)
    project_setting_id = db.Column(db.String(50),
                                   db.ForeignKey('project_setting.id', ondelete='CASCADE', onupdate='CASCADE'),
                                   nullable=True)
    created_date = db.Column(db.Integer, default=0)
    modified_date = db.Column(db.Integer, default=0)


# class TestSets(db.Model):
#     __tablename__ = 'test_sets'
#     id = db.Column(db.String(50), primary_key=True)
#     tests = db.relationship('Test', secondary=test_testsets, lazy='subquery',
#                             backref=db.backref('tests', lazy=True))
#     name = db.Column(db.String(255), nullable=True)
#     key = db.Column(db.String(255), nullable=True)
#     jira_id = db.Column(db.String(255), nullable=True)
#     cloud_id = db.Column(db.String(255), nullable=True)
#     created_date = db.Column(db.Integer, default=0)
#     modified_date = db.Column(db.Integer, default=0)
#
#
# """
# Many to many relationship
# Read more: https://flask-sqlalchemy.palletsprojects.com/en/2.x/models/
# Test Sets and Test Runs table
# """
#
# test_test_executions = db.Table('map_test_executions',
#                                 db.Column('test_id', db.String(50), db.ForeignKey('tests.id'), primary_key=True),
#                                 db.Column('test_execution_id', db.String(50), db.ForeignKey('test_executions.id'),
#                                           primary_key=True)
#                                 )


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


class TestStatus(db.Model):
    __tablename__ = 'test_status'
    id = db.Column(db.String(50), primary_key=True)
    name = db.Column(db.String(255))
    description = db.Column(db.String(255))
    color = db.Column(db.String(255))
    is_show = db.Column(db.Boolean, nullable=True)
    is_default = db.Column(db.Boolean, nullable=True)
    cloud_id = db.Column(db.String(50), nullable=True)
    project_key = db.Column(db.String(50))
    project_id = db.Column(db.String(50))
    site_url = db.Column(db.String(255), nullable=True)
    created_date = db.Column(db.Integer, default=0)
    modified_date = db.Column(db.Integer, default=0)

    @classmethod
    def get_by_id(cls, _id):
        return cls.query.get(_id)


class TestStepField(db.Model):
    __tablename__ = 'test_step_field'
    id = db.Column(db.String(50), primary_key=True)
    name = db.Column(db.String(250))
    description = db.Column(db.String(250))
    type_values \
        = db.Column(db.Text())
    type = db.Column(db.String(250))
    is_required = db.Column(db.Boolean, default=0)
    is_disabled = db.Column(db.Boolean, default=0)
    is_native = db.Column(db.Boolean, default=0)
    # Index order of list
    index = db.Column(db.Integer)
    cloud_id = db.Column(db.String(50), nullable=True)
    project_key = db.Column(db.String(50))
    project_id = db.Column(db.String(50))
    site_url = db.Column(db.String(255), nullable=True)
    created_date = db.Column(db.Integer, default=0)
    modified_date = db.Column(db.Integer, default=0)

    @classmethod
    def get_by_id(cls, _id):
        return cls.query.get(_id)

    @hybrid_property
    def field_type_values(self):
        _type_values = json.loads(self.type_values)
        return _type_values


class TestStepDetail(db.Model):
    __tablename__ = 'test_step_detail'
    id = db.Column(db.String(50), primary_key=True)
    status_id = db.Column(db.String(50), db.ForeignKey('test_status.id', ondelete='CASCADE', onupdate='CASCADE'),
                          nullable=True)
    test_step_id = db.Column(db.String(50),
                             db.ForeignKey('test_step.id', ondelete='CASCADE', onupdate='CASCADE'),
                             nullable=True)
    test_run_id = db.Column(db.String(50),
                            db.ForeignKey('test_run.id', ondelete='CASCADE', onupdate='CASCADE'),
                            nullable=True)
    test_step_field_id = db.Column(db.String(50),
                                   db.ForeignKey('test_step_field.id', ondelete='CASCADE', onupdate='CASCADE'),
                                   nullable=True)
    data = db.Column(db.Text, nullable=True)
    comment = db.Column(db.Text, nullable=True)
    created_date = db.Column(db.Integer, default=0, index=True)
    modified_date = db.Column(db.Integer, default=0)


class TestActivity(db.Model):
    __tablename__ = 'test_activity'
    id = db.Column(db.String(50), primary_key=True)
    test_run_id = db.Column(db.String(50),
                            db.ForeignKey('test_run.id', ondelete='CASCADE', onupdate='CASCADE'),
                            nullable=True)
    comment = db.Column(db.Text, nullable=True)
    status_change = db.Column(db.Text, nullable=True)
    jira_user_id = db.Column(db.Text, nullable=True)
    created_date = db.Column(db.Integer, default=0, index=True)
    modified_date = db.Column(db.Integer, default=0)


class Defects(db.Model):
    __tablename__ = 'defect'
    id = db.Column(db.String(50), primary_key=True)
    test_run_id = db.Column(db.String(50),
                            db.ForeignKey('test_run.id', ondelete='CASCADE', onupdate='CASCADE'),
                            nullable=True)
    test_step_detail_id = db.Column(db.String(50),
                                    db.ForeignKey('test_step_detail.id', ondelete='CASCADE', onupdate='CASCADE'),
                                    nullable=True)

    test_issue_key = db.Column(db.Text, nullable=True)
    test_issue_id = db.Column(db.Text, nullable=True)
    created_date = db.Column(db.Integer, default=0, index=True)
    modified_date = db.Column(db.Integer, default=0)


class TestEvidence(db.Model):
    __tablename__ = 'test_evidence'
    id = db.Column(db.String(50), primary_key=True)
    test_run_id = db.Column(db.String(50),
                            db.ForeignKey('test_run.id', ondelete='CASCADE', onupdate='CASCADE'),
                            nullable=True)
    test_step_detail_id = db.Column(db.String(50),
                                    db.ForeignKey('test_step_detail.id', ondelete='CASCADE', onupdate='CASCADE'),
                                    nullable=True)
    name_file = db.Column(db.Text, nullable=True)
    url_file = db.Column(db.Text, nullable=True)
    created_date = db.Column(db.Integer, default=0, index=True)
    modified_date = db.Column(db.Integer, default=0)


class TestTimer(db.Model):
    __tablename__ = 'test_timer'
    id = db.Column(db.String(50), primary_key=True)
    test_run_id = db.Column(db.String(50),
                            db.ForeignKey('test_run.id', ondelete='CASCADE', onupdate='CASCADE'),
                            nullable=True)
    time_type = db.Column(db.Integer, default=1)  # 1 start time, 2 end time
    date_time = db.Column(db.DATE)  # format %Y-%m-%d %H:%M:%S.%f
    str_date_time = db.Column(db.Text, nullable=True)
    created_date = db.Column(db.Integer, default=0, index=True)
    modified_date = db.Column(db.Integer, default=0)


class Repository(db.Model):
    __tablename__ = 'repository'
    id = db.Column(db.String(50), primary_key=True)
    folder_id = db.Column(db.String(50), unique=True)
    parent_id = db.Column(db.String(50))
    name = db.Column(db.String(500))
    create_date = db.Column(INTEGER(unsigned=True), default=0, index=True)
    project_id = db.Column(db.String(50))
    index = db.Column(db.Integer)
    cloud_id = db.Column(db.String(255), nullable=True)
    created_date = db.Column(db.Integer, default=0)
    modified_date = db.Column(db.Integer, default=0)

    @hybrid_property
    def map_test_repo(self):
        map_test_repo = Test_Repository.query.filter_by(test_repo_id=self.id).order_by(
            Test_Repository.index.asc()).all()
        return map_test_repo

    @hybrid_property
    def children_folder(self):
        children_repo = Repository.query.filter_by(parent_id=self.folder_id).order_by(Repository.index.asc()).all()
        return children_repo


class Test_Repository(db.Model):
    __tablename__ = 'test_case_repositories'
    id = db.Column(db.String(50), primary_key=True)
    test_id = db.Column(ForeignKey('test_case.id', ondelete='SET NULL', onupdate='CASCADE'), index=True)
    repository_id = db.Column(ForeignKey('repository.id', ondelete='SET NULL', onupdate='CASCADE'), index=True)
    create_date = db.Column(INTEGER(unsigned=True), default=0, index=True)
    index = db.Column(db.Integer)


class Setting(db.Model):
    __tablename__ = 'setting'
    id = db.Column(db.String(50), primary_key=True)
    miscellaneous = db.Column(db.Text())
    test_type = db.Column(db.Text())
    test_environment = db.Column(db.Text())
    test_step_field = db.Column(db.Text())
    test_run_custom_field = db.Column(db.Text())
    test_test_executions_status = db.Column(db.Text())
    reindex = db.Column(db.Text())
    index = db.Column(db.Integer)
    project_id = db.Column(db.String(50))
    project_key = db.Column(db.String(50))
    index = db.Column(db.Integer)
    cloud_id = db.Column(db.String(255), nullable=True)
    site_url = db.Column(db.String(255), nullable=True)
    created_date = db.Column(db.Integer, default=0)
    modified_date = db.Column(db.Integer, default=0)


class TestEnvironment(db.Model):
    __tablename__ = 'test_environment'
    id = db.Column(db.String(50), primary_key=True)
    parent_id = db.Column(db.String(50), nullable=True, default=None)
    name = db.Column(db.String(250))
    description = db.Column(db.String(250))
    url = db.Column(db.String(250))
    cloud_id = db.Column(db.String(50), nullable=True)
    project_id = db.Column(db.String(50))
    created_date = db.Column(db.Integer, default=0)
    modified_date = db.Column(db.Integer, default=0)

    @classmethod
    def get_by_id(cls, _id):
        return cls.query.get(_id)


"""
New Design
"""

"""
Many to many relationship
Test Executions and Test Case
"""
test_cases_test_executions = db.Table('test_cases_test_executions',
                                      db.Column('test_case_id', db.String(50), db.ForeignKey('test_case.id'),
                                                primary_key=True),
                                      db.Column('test_execution_id', db.String(50), db.ForeignKey('test_execution.id'),
                                                primary_key=True),
                                      db.Column('index', db.Integer, nullable=True)
                                      )

"""
Many to many relationship
Test Set and Test Case
"""
test_cases_test_sets = db.Table('test_cases_test_sets',
                                db.Column('test_case_id', db.String(50), db.ForeignKey('test_case.id'),
                                          primary_key=True),
                                db.Column('test_set_id', db.String(50), db.ForeignKey('test_set.id'),
                                          primary_key=True),
                                db.Column('index', db.Integer, nullable=True)
                                )

"""
Many to many relationship
Test Step and Test Case
"""
test_cases_test_steps = db.Table('test_cases_test_steps',
                                 db.Column('test_case_id', db.String(50), db.ForeignKey('test_case.id'),
                                           primary_key=True),
                                 db.Column('test_step_id', db.String(50), db.ForeignKey('test_step.id'),
                                           primary_key=True),
                                 db.Column('index', db.Integer, nullable=True)
                                 )

"""
Many to many relationship
Test Executions and Test Environments
"""
test_executions_test_environments = db.Table('test_executions_test_environments',
                                             db.Column('test_execution_id', db.String(50),
                                                       db.ForeignKey('test_execution.id'),
                                                       primary_key=True),
                                             db.Column('test_environment_id', db.String(50),
                                                       db.ForeignKey('test_environment.id'),
                                                       primary_key=True),
                                             )


class TestCase(db.Model):
    __tablename__ = 'test_case'

    id = db.Column(db.String(50), primary_key=True)
    cloud_id = db.Column(db.String(50), nullable=True)
    project_id = db.Column(db.String(50))
    issue_id = db.Column(db.String(50))
    issue_key = db.Column(db.String(50))
    meta_data = db.Text()

    test_steps = relationship("TestStep", primaryjoin='TestStep.test_case_id == TestCase.id', lazy="noload",
                              order_by="asc(TestStep.index)")

    created_date = db.Column(db.Integer, default=0)
    modified_date = db.Column(db.Integer, default=0)
    deleted_date = db.Column(db.Integer, default=0)

    @classmethod
    def get_by_id(cls, _id):
        return cls.query.get(_id)


class TestSet(db.Model):
    __tablename__ = 'test_set'

    id = db.Column(db.String(50), primary_key=True)
    cloud_id = db.Column(db.String(50), nullable=True)
    project_id = db.Column(db.String(50))
    issue_id = db.Column(db.String(50))
    issue_key = db.Column(db.String(50))
    meta_data = db.Text()

    test_cases = db.relationship('TestCase', secondary=test_cases_test_sets,
                                 backref=db.backref('test_set', lazy='dynamic'))

    created_date = db.Column(db.Integer, default=0)
    modified_date = db.Column(db.Integer, default=0)
    deleted_date = db.Column(db.Integer, default=0)


class TestExecution(db.Model):
    __tablename__ = 'test_execution'

    id = db.Column(db.String(50), primary_key=True)
    cloud_id = db.Column(db.String(50), nullable=True)
    project_id = db.Column(db.String(50))
    issue_id = db.Column(db.String(50))
    issue_key = db.Column(db.String(50))
    meta_data = db.Text()

    test_cases = db.relationship('TestCase', secondary=test_cases_test_executions, lazy='dynamic',
                                 backref=db.backref('test_execution'))

    test_runs = db.relationship('TestRun', primaryjoin='TestExecution.id == TestRun.test_execution_id',
                                backref=db.backref('test_execution'))

    test_environments = db.relationship('TestEnvironment', secondary=test_executions_test_environments,
                                        backref=db.backref('test_cases', lazy='dynamic'))

    created_date = db.Column(db.Integer, default=0)
    modified_date = db.Column(db.Integer, default=0)
    deleted_date = db.Column(db.Integer, default=0)


class TestRun(db.Model):
    __tablename__ = 'test_run'

    id = db.Column(db.String(50), primary_key=True)
    cloud_id = db.Column(db.String(50), nullable=True)
    project_id = db.Column(db.String(50))
    issue_id = db.Column(db.String(50))
    issue_key = db.Column(db.String(50))
    test_case_id = db.Column(db.String(50), db.ForeignKey('test_case.id', ondelete='CASCADE', onupdate='CASCADE'),
                             nullable=False, primary_key=True)
    test_execution_id = db.Column(db.String(50),
                                  db.ForeignKey('test_execution.id', ondelete='CASCADE', onupdate='CASCADE'),
                                  nullable=False, primary_key=True)

    # Test run data (in string_json format)
    activities = db.Text()
    test_steps = db.Text()
    findings = db.Text()

    test_status_id = db.Column(db.String(50), ForeignKey("test_status.id", ondelete='SET NULL', onupdate='SET NULL'))
    status = relationship("TestStatus", primaryjoin='TestRun.test_status_id == TestStatus.id', lazy=True)

    meta_data = db.Text()

    assignee_account_id = db.Column(db.String(50))
    executed_account_id = db.Column(db.String(50))

    is_updated = db.Column(db.Boolean, default=0)

    start_date = db.Column(db.Integer, default=0)
    end_date = db.Column(db.Integer, default=0)

    created_date = db.Column(db.Integer, default=0)
    modified_date = db.Column(db.Integer, default=0)
    deleted_date = db.Column(db.Integer, default=0)

    @classmethod
    def get_by_id(cls, _id):
        return cls.query.get(_id)


class TestStep(db.Model):
    __tablename__ = 'test_step'

    id = db.Column(db.String(50), primary_key=True)

    cloud_id = db.Column(db.String(255), nullable=True)
    project_key = db.Column(db.String(50))
    project_id = db.Column(db.String(50))

    # Data
    action = db.Column(db.Text, nullable=True)
    data = db.Column(db.Text, nullable=True)
    result = db.Column(db.Text, nullable=True)
    custom_fields = db.Column(db.JSON, nullable=True)

    attachments = db.Column(db.Text, nullable=True)
    index = db.Column(db.Integer, nullable=True)

    test_case_id = db.Column(db.String(50), db.ForeignKey('test_case.id', ondelete='CASCADE', onupdate='CASCADE'),
                             nullable=False)
    test_case_id_reference = db.Column(db.String(50), nullable=True)
    test_details = relationship("TestStepDetail", primaryjoin='TestStepDetail.test_step_id == TestStep.id',
                                lazy='noload')

    created_date = db.Column(db.Integer, default=0)
    modified_date = db.Column(db.Integer, default=0)
    deleted_date = db.Column(db.Integer, default=0)


class Attachment(db.Model):
    __tablename__ = 'attachment'
    id = db.Column(db.String(50), primary_key=True)
    file_name = db.Column(db.String(255), nullable=True)
    size = db.Column(db.BigInteger, default=0)
    in_btest = db.Column(db.Boolean, nullable=True)
    created_date = db.Column(db.Integer, default=0)
    modified_date = db.Column(db.Integer, default=0)
    deleted_date = db.Column(db.Integer, default=0)


class UserSetting(db.Model):
    __tablename__ = 'user_setting'
    id = db.Column(db.String(50), primary_key=True)
    user_id = db.Column(db.String(50), index=True)
    display_column = db.Column(db.Text)
    created_date = db.Column(INTEGER(unsigned=True))
    modified_date = db.Column(INTEGER(unsigned=True))


class FileDetail(db.Model):
    __tablename__ = "file_detail"

    id = db.Column(db.String(50), primary_key=True)
    attached_file = db.Column(db.Text(), nullable=True)
    file_name = db.Column(db.String(500), nullable=True)
    extension = db.Column(db.Text(), nullable=True)
    prefix = db.Column(db.Text(), nullable=True)
    created_date = db.Column(INTEGER(unsigned=True), default=0)
    modified_date = db.Column(INTEGER(unsigned=True), default=0)


class HistoryTest(db.Model):
    __tablename__ = "history_test"
    id = db.Column(db.String(50), primary_key=True)
    user_id = db.Column(db.String(50), nullable=False)
    history_category = db.Column(db.Integer, default=1, index=True) # test  set : 1    # test case -  test set:2  /test run:3   test
    activities = db.Column(db.String(50), nullable=False)
    action_name = db.Column(db.String(50), nullable=False)
    detail_of_action = db.Column(db.JSON, nullable=False)
    created_date = db.Column(db.Integer, default=0, index=True)
    id_reference = db.Column(db.String(50), nullable=False)



