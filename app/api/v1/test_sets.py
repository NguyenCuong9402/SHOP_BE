import uuid

from flask import Blueprint, request
from flask_jwt_extended import jwt_required, get_jwt_identity, create_access_token
from sqlalchemy import or_
from app.models import TestSets, Test, TestType, db
from app.utils import send_result, send_error, data_preprocessing
from app.validator import CreateTestValidator
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
