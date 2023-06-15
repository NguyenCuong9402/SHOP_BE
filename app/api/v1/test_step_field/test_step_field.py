import json
import uuid
from operator import or_

from flask import Blueprint, request
from flask_jwt_extended import jwt_required, get_jwt_identity, create_access_token
from benedict import benedict
from sqlalchemy import func, asc, and_

from app.api.v1.setting.setting_validator import UpdateMiscellaneousRequest
from app.api.v1.test_step_field.test_step_field_validator import CreateTestStepField, UpdateTestStepField
from app.gateway import authorization_require
from app.models import TestStep, TestType, db, TestField, Setting, TestStepField, TestRunField, TestRun
from app.utils import send_result, send_error, data_preprocessing, validate_request
from app.validator import CreateTestValidator, SettingSchema, TestStepFieldSchema
from app.parser import TestFieldSchema, TestStepSchema

api = Blueprint('test_step_field', __name__)


@api.route("/<project_id>", methods=["GET"])
@authorization_require()
def get_test_step_field(project_id):
    try:
        token = get_jwt_identity()
        cloud_id = token.get('cloudId')
        test_step_fields_count = db.session.query(TestStepField).filter(
            or_(TestStepField.project_id == project_id, TestStepField.project_key == project_id),
            TestStepField.cloud_id == cloud_id).count()
        if test_step_fields_count == 0:
            """
            Create default test step field   
            """
            for test_step_field in DEFAULT_DATA:
                test_step = TestStepField(
                    id=str(uuid.uuid4()),
                    name=test_step_field['name'],
                    description=test_step_field['description'],
                    type=test_step_field['type'],
                    is_required=test_step_field['is_required'],
                    is_disabled=test_step_field['is_disabled'],
                    is_native=test_step_field['is_native'],
                    index=test_step_field['index'],
                    type_values=test_step_field['type_values'],
                    project_id=project_id,
                    cloud_id=cloud_id,
                )
                db.session.add(test_step)
        db.session.commit()

        test_step_fields = db.session.query(TestStepField).filter(
            or_(TestStepField.project_id == project_id, TestStepField.project_key == project_id),
            TestStepField.cloud_id == cloud_id).order_by(asc(TestStepField.index)).all()
        result = TestStepFieldSchema(many=True).dump(test_step_fields)
        return send_result(data=result, message="OK")
    except Exception as ex:
        db.session.rollback()
        return send_error(message="Something wrong!")


@api.route("/<project_id>", methods=["POST"])
@authorization_require()
def create_test_step(project_id):
    """
    Update or create miscellaneous setting
    """

    try:
        token = get_jwt_identity()
        cloud_id = token.get('cloudId')

        # Check if test field is creatable
        test_step_fields_count = db.session.query(TestStepField).filter(
            or_(TestStepField.project_id == project_id, TestStepField.project_key == project_id),
            TestStepField.cloud_id == cloud_id).count()
        if test_step_fields_count >= 6:
            return send_error(code=200, data="",
                              message='Can not create this test step field because it has reached 3 non-native fields',
                              show=False, is_dynamic=True)

        try:
            json_req = request.get_json()
        except Exception as ex:
            return send_error(message="Request Body incorrect json format: " + str(ex), code=442)

            # Strip body request
        body_request = {}
        for key, value in json_req.items():
            if isinstance(value, str):
                body_request.setdefault(key, value.strip())
            else:
                body_request.setdefault(key, value)

        # Validate body request
        input_validation = CreateTestStepField()
        is_not_validate = input_validation.validate(body_request)
        if is_not_validate:
            return send_error(code=400, data=is_not_validate, message='Invalid request')

        # Check coincided name
        coincided = check_coincided_name(name=body_request.get('name'), cloud_id=cloud_id, project_id=project_id)
        if coincided is True:
            return send_error(code=200, data={"name": "Test Step Field already exists. Please try again"},
                              message='Invalid request', show=False, is_dynamic=True)

        # Create new test step
        max_index = TestStepField.query.filter(TestStepField.cloud_id == cloud_id,
                                               TestStepField.project_id == project_id).count()
        test_step_field = TestStepField(
            id=str(uuid.uuid4()),
            project_id=project_id,
            cloud_id=cloud_id,
            name=body_request.get('name'),
            description=body_request.get('description', ''),
            is_required=body_request['is_required'],
            type=body_request['type'],
            type_values=json.dumps(body_request['field_type_values']),
            index=max_index + 1
        )
        db.session.add(test_step_field)
        db.session.flush()
        db.session.query(TestRun).filter(TestRun.project_id == project_id, TestRun.cloud_id == cloud_id)\
            .update({"is_updated": 1})
        db.session.flush()
        db.session.commit()
        return send_result(data=TestStepFieldSchema().dump(test_step_field), message="Test Step Field created",
                           show=True)
    except Exception as ex:
        db.session.rollback()
        return send_error(data='', message="Something was wrong!")


@api.route("/<project_id>/<test_step_id>", methods=["PUT"])
@authorization_require()
def update_test_step(project_id, test_step_id):
    """
    Update or create miscellaneous setting
    """

    try:
        token = get_jwt_identity()
        cloud_id = token.get('cloudId')
        test_step = TestStepField.get_by_id(test_step_id)
        if test_step is None:
            return send_error(
                message="Test Step Fields have been changed \n Please refresh the page to view the changes", code=200,
                show=False, is_dynamic=True)

        try:
            json_req = request.get_json()
        except Exception as ex:
            return send_error(message="Request Body incorrect json format: " + str(ex), code=442)
            # Strip body request
        body_request = {}
        for key, value in json_req.items():
            if isinstance(value, str):
                body_request.setdefault(key, value.strip())
            else:
                body_request.setdefault(key, value)
        # Validate body request
        input_validation = UpdateTestStepField()
        is_not_validate = input_validation.validate(body_request)
        if is_not_validate:
            return send_error(code=400, data=is_not_validate, message='Invalid request')
        # Check coincided name
        coincided = check_coincided_name(name=body_request.get('name'), self_id=test_step_id, cloud_id=cloud_id,
                                         project_id=project_id)
        if coincided is True:
            return send_error(code=200, message='Test Step Field already exists. Please try again"',
                              show=False, is_dynamic=True)

        # Update new test step
        if body_request.get('field_type_values') is not None:
            body_request['type_values'] = json.dumps(body_request.get('field_type_values'))
            del body_request['field_type_values']

        update_data = body_request.items()
        for key, value in update_data:
            setattr(test_step, key, value)
        db.session.flush()
        db.session.query(TestRun).filter(TestRun.project_id == project_id, TestRun.cloud_id == cloud_id) \
            .update({"is_updated": 1})
        db.session.flush()
        db.session.commit()
        return send_result(data=TestStepFieldSchema().dump(test_step),
                           message="Test Step Fields were saved successfully", show=True)
    except Exception as ex:
        db.session.rollback()
        return send_error(data='', message="Something was wrong!")


@api.route("/reorder/<project_id>", methods=["POST"])
@authorization_require()
def reorder(project_id):
    try:
        try:
            json_req = request.get_json()
        except Exception as ex:
            return send_error(message="Request Body incorrect json format: " + str(ex), code=442)

            # Strip body request
        body_request = {}
        for key, value in json_req.items():
            if isinstance(value, str):
                body_request.setdefault(key, value.strip())
            else:
                body_request.setdefault(key, value)

        # Reorder all test step
        ids = body_request['ids']
        for _id in ids:
            index = ids.index(_id)
            test_step = TestStepField.get_by_id(_id)
            test_step.index = index + 1
            db.session.flush()

        db.session.commit()
        return send_result(data="", message="Order has been changed successfully", show=True)
    except Exception as ex:
        db.session.rollback()
        return send_error(data='', message="Something was wrong!", show=True)


@api.route("/<project_id>/<test_step_id>", methods=["DELETE"])
@authorization_require()
def delete(project_id, test_step_id):
    try:
        token = get_jwt_identity()
        cloud_id = token.get('cloudId')
        test_step_field = TestStepField.get_by_id(test_step_id)

        if test_step_field is None:
            return send_error(
                message="Test Step Fields have been changed \n Please refresh the page to view the changes", code=200,
                show=False, is_dynamic=True)
        default_name = ["Action  (action)", "Data (data)", "Expected Result (result)"]
        if test_step_field.name in default_name:
            return send_error(message="not allowed to delete this test step field", is_dynamic=True)
        test_step_field_project = TestStepField.query.filter(TestStepField.cloud_id == cloud_id,
                                                             TestStepField.project_id == project_id,
                                                             TestStepField.name.notin_(default_name)).all()
        custom_field = [item.name for item in test_step_field_project]
        index = custom_field.index(test_step_field.name)
        test_steps = TestStep.query.filter(TestStep.custom_fields.isnot(None),
                                           func.json_length(TestStep.custom_fields) >= index + 1).all()
        for test_step in test_steps:
            custom_fields = test_step.custom_fields.copy()
            if custom_fields:
                if len(custom_fields) == 3:
                    del custom_fields[index]
                    test_step.custom_fields = custom_fields
                    db.session.flush()
                # index (list) : 0 ,1 ,2
                elif len(custom_fields) == 2 and index <= 1:
                    del custom_fields[index]
                    test_step.custom_fields = custom_fields
                    db.session.flush()
                elif len(custom_fields) == 1 and index == 0:
                    del custom_fields[index]
                    test_step.custom_fields = custom_fields
                    db.session.flush()
        # update index Test Step field
        db.session.query(TestStepField).filter(TestStepField.cloud_id == test_step_field.cloud_id,
                                               TestStepField.project_id == project_id)\
            .filter(TestStepField.index > test_step_field.index).update(dict(index=TestStepField.index - 1))
        db.session.flush()
        db.session.delete(test_step_field)
        db.session.flush()
        db.session.query(TestRun).filter(TestRun.project_id == project_id, TestRun.cloud_id == cloud_id) \
            .update({"is_updated": 1})
        db.session.commit()
        return send_result(data="", message="Test step field removed successfully", code=200, show=True)
    except Exception as ex:
        db.session.rollback()
        return send_error(data='', message="Something was wrong!")


@api.route("/<project_id>/<test_step_field_id>", methods=["GET"])
@authorization_require()
def number_test_delete(project_id, test_step_field_id):
    try:
        token = get_jwt_identity()
        cloud_id = token.get('cloudId')
        test_step_field = TestStepField.query.filter(TestStepField.id == test_step_field_id).first()
        if test_step_field is None:
            return send_error(
                message="Test Step Fields have been changed \n Please refresh the page to view the changes", code=200,
                show=False, is_dynamic=True)
        default_name = ["Action  (action)", "Data (data)", "Expected Result (result)"]
        if test_step_field.name in default_name:
            return send_error(message="not allowed to delete this test step field")
        # SQLAlchemy để tính tổng trực tiếp trong câu truy vấn
        test_step_field_project = TestStepField.query.filter(TestStepField.cloud_id == cloud_id,
                                                             TestStepField.project_id == project_id,
                                                             TestStepField.name.notin_(default_name)).all()
        custom_field = [item.name for item in test_step_field_project]
        count = TestStep.query.with_entities(func.count())\
            .filter(TestStep.cloud_id == cloud_id, TestStep.project_id == project_id,
                    TestStep.custom_fields.isnot(None),
                    func.json_length(TestStep.custom_fields) >= custom_field.index(test_step_field.name)+1).scalar()
        return send_result(message=f'There are {count} Test(s) with steps using the Test Step Field.')
    except Exception as ex:
        return send_error(data='', message=str(ex))


@api.route("/test", methods=["GET"])
def test():
    try:
        test2 = TestRunField.query.first()
        test2.test_types.clear()
        db.session.commit()

        return send_result(data="", message="Test step field removed successfully", code=200, show=True)
    except Exception as ex:
        db.session.rollback()
        return send_error(data='', message="Something was wrong!")


"""
Helper function
"""


def check_coincided_name(name='', self_id=None, project_id='', cloud_id=''):
    existed_test_step = TestStepField.query.filter(
        and_(TestStepField.name == name, TestStepField.id != self_id, TestStepField.cloud_id == cloud_id,
             TestStepField.project_id == project_id)).first()
    if existed_test_step is None:
        return False
    return True


DEFAULT_DATA = [
    {
        "name": "Data (data)",
        "description": "Any data the related step requests (e.g., login credentials) to be used by the tester.",
        "type": "Text",
        "index": 2,
        "is_native": True,
        "is_required": False,
        "is_disabled": False,
        "type_values": "[]"
    },
    {
        "name": "Expected Result (result)",
        "description": "The behavior that the step should accomplish.",
        "type": "Text",
        "index": 3,
        "is_native": True,
        "is_required": True,
        "is_disabled": False,
        "type_values": "[]"
    },
    {
        "name": "Action  (action)",
        "description": "The action to be reproduced by the tester.",
        "type": "Text",
        "index": 1,
        "is_native": True,
        "is_required": True,
        "is_disabled": False,
        "type_values": "[]"
    }
]
