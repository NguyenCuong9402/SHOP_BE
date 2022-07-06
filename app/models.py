# coding: utf-8
from app.extensions import db


class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.String(50), primary_key=True)
    username = db.Column(db.String(100), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)


class Test(db.Model):
    __tablename__ = 'tests'

    id = db.Column(db.String(50), primary_key=True)
    cucumber = db.Column(db.String(255), nullable=True)
    generic = db.Column(db.String(255), nullable=True)
    issue_id = db.Column(db.String(255), nullable=False)
    test_type_id = db.Column(db.String(50), db.ForeignKey('test_type.id'), nullable=False)
    test_steps = db.relationship('TestStep', backref='test_steps', lazy=True)


class TestType(db.Model):
    __tablename__ = 'test_type'

    id = db.Column(db.String(50), primary_key=True)
    value = db.Column(db.String(255), nullable=False)
    type = db.Column(db.String(255), nullable=False)
    project_setting_id = db.Column(db.String(255), nullable=True)


class TestStep(db.Model):
    __tablename__ = 'test_steps'

    id = db.Column(db.String(50), primary_key=True)
    data = db.Column(db.Text, nullable=True)
    result = db.Column(db.Text, nullable=True)
    customFields = db.Column(db.Text, nullable=True)
    attachments = db.Column(db.Text, nullable=True)
    index = db.Column(db.Integer, nullable=True)
    action = db.Column(db.Text, nullable=True)
    test_id = db.Column(db.String(50), db.ForeignKey('tests.id'),  nullable=False)


"""
Many to many relationship
Read more: https://flask-sqlalchemy.palletsprojects.com/en/2.x/models/
Test Sets and Test Runs table
"""

test_testsets = db.Table('map_test_testsets',
    db.Column('test_id', db.String(50), db.ForeignKey('tests.id'), primary_key=True),
    db.Column('testset_id', db.String(50), db.ForeignKey('test_sets.id'), primary_key=True)
)


class TestSets(db.Model):
    __tablename__ = 'test_sets'
    id = db.Column(db.String(50), primary_key=True)
    tests = db.relationship('Test', secondary=test_testsets, lazy='subquery',
                            backref=db.backref('tests', lazy=True))
    name = db.Column(db.String(255), nullable=True)


"""
Many to many relationship
Read more: https://flask-sqlalchemy.palletsprojects.com/en/2.x/models/
Test Sets and Test Runs table
"""

test_test_executions = db.Table('map_test_executions',
    db.Column('test_id', db.String(50), db.ForeignKey('tests.id'), primary_key=True),
    db.Column('test_execution_id', db.String(50), db.ForeignKey('test_executions.id'), primary_key=True)
)


class TestExecutions(db.Model):
    __tablename__ = 'test_executions'
    id = db.Column(db.String(50), primary_key=True)
    tests = db.relationship('Test', secondary=test_test_executions, lazy='subquery',
                            backref=db.backref('test_execution_tests', lazy=True))
    name = db.Column(db.String(255), nullable=True)


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
