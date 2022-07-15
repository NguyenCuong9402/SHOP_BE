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
def get_test_by_id(test_set_id):
    results = TestSets.query.filter(or_(TestSets.key==test_set_id, TestSets.jira_id==test_set_id)).first()
    results = TestSetsSchema().dump(results)
    return send_result(data=results, message="OK")


@api.route("", methods=["GET"])
def get_test_sets():
    results = TestSets.query.filter().all()
    results = TestSetsSchema(many=True).dump(results)
    return send_result(data=results, message="OK")
