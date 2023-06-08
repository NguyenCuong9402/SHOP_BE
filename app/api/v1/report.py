import uuid
from flask import Blueprint, request
from flask_jwt_extended import get_jwt_identity
from sqlalchemy import asc

from app.gateway import authorization_require
from app.models import HistoryTest, TestCase, db, TestSet, TestExecution, TestRun, TestExecutionsTestEnvironments, \
    TestEnvironment, Defects
from app.utils import send_result, send_error, get_timestamp_now
from app.validator import TestSetSchema

api = Blueprint('report', __name__)


@api.route("/traceability-report-detail", methods=['POST'])
@authorization_require()
def get_():
    try:
        token = get_jwt_identity()
        cloud_id = token.get('cloudId')
        project_id = token.get('projectId')
        body_request = request.get_json()
        stories = body_request.get("story", {})
        data = []
        for story in stories:
            report = {}
            test_sets = TestSet.query.filter(TestSet.issue_id.in_(story['test_sets']),
                                             TestSet.cloud_id == cloud_id, TestSet.project_id == project_id).all()
            report['test_set'] = TestSetSchema(many=True).dump(test_sets)
            infor_test_executions = []
            test_executions = TestExecution.query.filter(TestExecution.cloud_id == cloud_id, TestExecution.project_id,
                                                         TestExecution.issue_id.in_(story['test_executions'])).all()
            test_exe_id = [item.id for item in test_executions]
            for test_execution_issue_id in test_exe_id:
                infor_test_execution = {}
                test_execution = TestExecution.query.filter(TestExecution.project_id == project_id,
                                                            TestExecution.cloud_id == cloud_id,
                                                            TestExecution.issue_id == test_execution_issue_id).first()
                infor_test_execution['issue_key'] = test_execution.issue_key
                infor_test_execution['executed_on'] = test_execution.modified_date
                test_environments = db.session.query(TestEnvironment)\
                    .join(TestExecutionsTestEnvironments, TestExecutionsTestEnvironments.test_environment_id
                          == TestEnvironment.id)\
                    .filter(TestExecutionsTestEnvironments.test_execution_id == test_execution.id)\
                    .order_by(asc(TestEnvironment.name)).all()
                infor_test_execution['environment'] = [item.name for item in test_environments]
                infor_test_executions.append(infor_test_execution)
            report['test_execution'] = infor_test_executions
            test_runs = TestRun.query.filter(TestRun.cloud_id == cloud_id, TestRun.project_id == project_id,
                                             TestRun.test_execution_id.in_(test_exe_id)).all()
            test_run_ids = [item.id for item in test_runs]
            defect = Defects.query.filter(Defects.test_run_id.in_(test_run_ids)).all()
            bug = [item.issue_id for item in defect]
            report['test_execution'] = bug
            data.append(report)
        return send_result(data=data)
    except Exception as ex:
        return send_error(message=str(ex))
