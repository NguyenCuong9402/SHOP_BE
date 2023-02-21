import uuid

from flask import Blueprint, request
from flask_jwt_extended import jwt_required, get_jwt_identity, create_access_token
from sqlalchemy import or_
from app.models import TestSet, TestCase, TestType, db
from app.utils import send_result, send_error, data_preprocessing
from app.validator import CreateTestValidator, TestSetsValidator
from app.parser import TestSchema, TestTypeSchema, TestSetsSchema

api = Blueprint('test_sets', __name__)


@api.route("/<test_set_id>", methods=["GET"])
@jwt_required()
def get_test_by_id(test_set_id):
    token = get_jwt_identity()
    cloud_id = token.get('cloudId')
    results = TestSets.query.filter(
        or_(
            TestSets.key == test_set_id,
            TestSets.jira_id == test_set_id,
            TestSets.name == test_set_id),
        TestSets.cloud_id == cloud_id
    ).first()
    results = TestSetsSchema().dump(results)
    return send_result(data=results, message="OK")


@api.route("", methods=["GET"])
@jwt_required()
def get_test_sets():
    token = get_jwt_identity()
    cloud_id = token.get('cloudId')
    results = TestSets.query.filter(TestSets.cloud_id == cloud_id).all()
    results = TestSetsSchema(many=True).dump(results)
    return send_result(data=results, message="OK")


@api.route("", methods=["POST"])
@jwt_required()
def create_a_new_test_set():
    try:
        json_req = request.get_json()
        token = get_jwt_identity()
        cloud_id = token.get('cloudId')
    except Exception as ex:
        return send_error(message="Request body incorrect json format: " + str(ex), code=442)

    # validate request body
    json_valid, message_id, incorrect_data = data_preprocessing(cls_validator=TestSetsValidator, input_json=json_req)
    if not json_valid:
        return send_error(data=incorrect_data, message_id=message_id, code=442)

    test_set_id = json_req.get("id", "")
    test_set_name = json_req.get("name", "")
    test_set_key = json_req.get("key", "")

    existed = TestSets.query.filter(
        TestSets.key == test_set_key,
        TestSets.jira_id == test_set_id,
        TestSets.name == test_set_name,
        TestSets.cloud_id == cloud_id
    ).first()
    if existed:
        results = TestSetsSchema().dump(existed)
        return send_result(data=results, message="Test Set Existed")

    new_test_set = TestSets(
        id=str(uuid.uuid4()),
        name=test_set_name,
        key=test_set_key,
        jira_id=test_set_id,
        cloud_id=cloud_id
    )
    db.session.add(new_test_set)
    db.session.commit()
    results = TestSetsSchema().dump(new_test_set)
    return send_result(data=results, message="OK")
