import json
import uuid
from operator import or_

from flask import Blueprint, request
from flask_jwt_extended import get_jwt_identity
from sqlalchemy import func, asc, and_, update

from app.api.v1.test_status.test_status_validator import CreateTestStatus, UpdateTestStatus
from app.gateway import authorization_require
from app.models import TestType, db, TestRunField, TestStatus
from app.utils import send_result, send_error, validate_request, get_timestamp_now
from app.validator import TestRunFieldSchema, TestStatusSchema

api = Blueprint('test_status', __name__)


@api.route("/<project_id>", methods=["GET"])
@authorization_require()
def get_test_status(project_id):
    try:
        token = get_jwt_identity()
        cloud_id = token.get('cloudId')
        test_status_count = db.session.query(TestStatus).filter(
            or_(TestStatus.project_id == project_id, TestStatus.project_key == project_id),
            TestStatus.cloud_id == cloud_id).count()
        if test_status_count == 0:
            for default_data in DEFAULT_DATA:
                test_status_count += 1
                test_type = TestStatus(
                    id=str(uuid.uuid4()),
                    name=default_data['name'],
                    description=default_data['description'],
                    is_show=default_data['is_show'],
                    is_default=default_data['is_default'],
                    color=default_data['color'],
                    project_id=project_id,
                    cloud_id=cloud_id,
                    created_date=get_timestamp_now() + test_status_count
                )
                db.session.add(test_type)
        db.session.commit()

        # Get default status
        test_statuses_default = db.session.query(TestStatus).filter(
            or_(TestStatus.project_id == project_id,
                TestStatus.project_key == project_id),
            TestStatus.is_default == 1,
            TestStatus.cloud_id == cloud_id).order_by(asc(TestStatus.created_date))

        # Get status created by user
        test_statuses_optional = db.session.query(TestStatus).filter(
            or_(TestStatus.project_id == project_id,
                TestStatus.project_key == project_id),
            TestStatus.is_default == 0,
            TestStatus.cloud_id == cloud_id).order_by(asc(TestStatus.name))

        test_statuses = test_statuses_default.union(test_statuses_optional)

        result = TestStatusSchema(many=True).dump(test_statuses.all())
        return send_result(data=result, message="OK", show=False)
    except Exception as ex:
        db.session.rollback()
        return send_error(message="Something wrong!")


@api.route("/<project_id>", methods=["POST"])
@authorization_require()
def create_test_status(project_id):
    """
    Update or create miscellaneous setting
    """

    try:
        token = get_jwt_identity()
        cloud_id = token.get('cloudId')

        is_valid, data, body_request = validate_request(CreateTestStatus(), request)

        if not is_valid:
            return send_error(data=data, code=200, is_dynamic=True)

        errors = {}
        # Check coincided name
        coincided = check_coincided(keyword=body_request.get('name'), field_name='name', cloud_id=cloud_id,
                                    project_id=project_id)
        if coincided is True:
            errors['name'] = 'Execution Status already exists. Please try again'

        # Check coincided color
        coincided = check_coincided(keyword=body_request.get('color'), field_name='color', cloud_id=cloud_id,
                                    project_id=project_id)
        if coincided is True:
            errors['color'] = 'This color already exists. Please try again'

        if errors != {}:
            return send_error(code=200, data=errors,
                              message='Invalid request', show=False, is_dynamic=True)

        # Create new test step

        test_status = TestStatus(
            id=str(uuid.uuid4()),
            project_id=project_id,
            cloud_id=cloud_id,
            name=body_request.get('name'),
            color=body_request.get('color'),
            description=body_request.get('description'),
            is_show=body_request['is_show'],
            is_default=False,
            created_date=get_timestamp_now()
        )
        db.session.add(test_status)
        db.session.flush()
        db.session.commit()

        return send_result(data=TestStatusSchema().dump(test_status), message="Execution Status created",
                           show=True)
    except Exception as ex:
        db.session.rollback()
        return send_error(data='', message="Something was wrong!")


class UpdateTestStatusField:
    pass


@api.route("/<project_id>/validation", methods=["POST"])
@authorization_require()
def validation_update(project_id, test_status_id):
    """
    Update test status
    """
    try:
        token = get_jwt_identity()
        cloud_id = token.get('cloudId')
        test_status = TestStatus.get_by_id(test_status_id)
        if test_status is None:
            return send_error(
                message="Execution Status has been changed \n Please refresh the page to view the changes",
                code=200,
                show=False)

        is_valid, data, body_request = validate_request(UpdateTestStatus(), request)

        if not is_valid:
            return send_error(data=data, code=200, is_dynamic=True)

        errors = {}
        # Check coincided name
        coincided = check_coincided(keyword=body_request.get('name'), field_name='name', cloud_id=cloud_id,
                                    self_id=test_status_id,
                                    project_id=project_id)
        if coincided is True:
            errors['name'] = 'Execution Status already exists. Please try again'

        # Check coincided color
        coincided = check_coincided(keyword=body_request.get('color'), self_id=test_status_id, field_name='color',
                                    cloud_id=cloud_id,
                                    project_id=project_id)
        if coincided is True:
            errors['color'] = 'This color already exists. Please try again'

        if errors != {}:
            return send_error(code=200, data=errors,
                              message='Invalid request', show=False, is_dynamic=True)

        return send_result(data=TestStatusSchema().dump(test_status),
                           message="Validate", show=True)
    except Exception as ex:
        db.session.rollback()
        return send_error(data='', message="Something was wrong!")


@api.route("/<project_id>/<test_status_id>", methods=["PUT"])
@authorization_require()
def update_test_status(project_id, test_status_id):
    """
    Update test status
    """

    try:
        token = get_jwt_identity()
        cloud_id = token.get('cloudId')
        test_status = TestStatus.get_by_id(test_status_id)
        if test_status is None:
            return send_error(
                message="Execution Status has been changed \n Please refresh the page to view the changes",
                code=200,
                show=False)

        is_valid, data, body_request = validate_request(UpdateTestStatus(), request)

        if not is_valid:
            return send_error(data=data, code=200, is_dynamic=True)

        errors = {}
        # Check coincided name
        coincided = check_coincided(keyword=body_request.get('name'), field_name='name', cloud_id=cloud_id,
                                    self_id=test_status_id,
                                    project_id=project_id)
        if coincided is True:
            errors['name'] = 'Execution Status already exists. Please try again'

        # Check coincided color
        coincided = check_coincided(keyword=body_request.get('color'), self_id=test_status_id, field_name='color',
                                    cloud_id=cloud_id,
                                    project_id=project_id)
        if coincided is True:
            errors['color'] = 'This color already exists. Please try again'

        if errors != {}:
            return send_error(code=200, data=errors,
                              message='Invalid request', show=False, is_dynamic=True)

        # Only update description if is default status
        if test_status.is_default:
            body_request = {"description": body_request.get('description')}

        # Update test status
        update_data = body_request.items()
        for key, value in update_data:
            setattr(test_status, key, value)
        db.session.commit()
        return send_result(data=TestStatusSchema().dump(test_status),
                           message="Execution Status were saved successfully", show=True)
    except Exception as ex:
        db.session.rollback()
        return send_error(data='', message="Something was wrong!")


@api.route("/<project_id>/<test_status_id>", methods=["DELETE"])
@authorization_require()
def delete(project_id, test_status_id):
    try:
        token = get_jwt_identity()
        cloud_id = token.get('cloudId')
        test_status = TestStatus.get_by_id(test_status_id)
        if test_status is None:
            return send_error(
                message="Execution Status has been changed \n Please refresh the page to view the changes",
                code=200,
                show=False)

        """
         1. 'EXECUTING' is default value when a execution status of test run is deleted, and this label can not changed.
         2.  All test runs/test step have this status will be moved to EXECUTING
        """

        executing_status = db.session.query(TestStatus).filter(
            TestStatus.project_id == project_id,
            TestStatus.name == 'EXECUTING',
            TestStatus.cloud_id == cloud_id).first()

        """
        Todo:
            1. Move all status in execution 
            2. Move all status in test step 
        """
        # Move all status deleted to EXECUTING status

        db.session.delete(test_status)
        db.session.commit()
        return send_result(data="", message="Execution Status removed successfully", code=200, show=True)
    except Exception as ex:
        db.session.rollback()
        return send_error(data='', message="Something was wrong!")


@api.route("/test", methods=["GET"])
def test():
    try:
        TestStatus.query.filter(TestStatus.is_show == 1).update({TestStatus.is_show: 0})
        db.session.commit()
        return send_result(data="", message="Test step field removed successfully", code=200, show=True)
    except Exception as ex:
        db.session.rollback()
        return send_error(data='', message="Something was wrong!")


"""
Helper function
"""


def check_coincided(keyword='', field_name='', self_id=None, project_id='', cloud_id=''):
    existed = TestStatus.query.filter(
        and_(getattr(TestStatus, field_name) == keyword, TestStatus.id != self_id, TestStatus.cloud_id == cloud_id,
             TestStatus.project_id == project_id)).first()
    if existed is None:
        return False
    return True


DEFAULT_DATA = [
    {
        "name": "TODO",
        "description": "The test run has not started",
        "is_show": True,
        "is_default": True,
        "color": "#999999"
    },
    {
        "name": "EXECUTING",
        "description": "The test is currently being executed",
        "is_show": True,
        "is_default": True,
        "color": "#FFD966"
    },
    {
        "name": "PASSED",
        "description": "The test run has passed",
        "is_show": True,
        "is_default": True,
        "color": "#009E0F"
    },
    {
        "name": "FAILED",
        "description": "The test run has failed",
        "is_show": True,
        "is_default": True,
        "color": "#CF2A27"
    }
]
