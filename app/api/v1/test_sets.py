import uuid

from flask import Blueprint, request
from flask_jwt_extended import jwt_required, get_jwt_identity, create_access_token

from app.models import TestStep, Test, TestType, db
from app.utils import send_result, send_error, data_preprocessing
from app.validator import CreateTestValidator
from app.parser import TestSchema, TestTypeSchema

api = Blueprint('test_sets', __name__)
