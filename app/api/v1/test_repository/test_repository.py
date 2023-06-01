import json
import os
import shutil
import uuid
from operator import or_
from flask import Blueprint, request
from flask_jwt_extended import get_jwt_identity
from sqlalchemy import func, asc, and_

from app.api.v1.history_test import save_history_test_step
from app.api.v1.test_execution.test_execution import add_test_step_id_by_test_case_id
from app.enums import FILE_PATH
from app.gateway import authorization_require
from app.models import TestStep, db, TestStepField, TestRunField, TestCase, TestStepDetail, HistoryTest, TestRun, \
    TestExecution, TestCasesTestExecutions, TestStatus, Attachment
from app.parser import TestStepSchema
from app.utils import send_result, send_error, data_preprocessing, get_timestamp_now

api = Blueprint('test_repository', __name__)
