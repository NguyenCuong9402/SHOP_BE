import uuid
from flask import Blueprint, request
from flask_jwt_extended import get_jwt_identity
from sqlalchemy import asc

from app.gateway import authorization_require
from app.models import HistoryTest, TestCase, db, TestSet, TestExecution, TestRun, TestExecutionsTestEnvironments, \
    TestEnvironment, Defects, TestStatus
from app.utils import send_result, send_error, get_timestamp_now
from app.validator import TestSetSchema

api = Blueprint('report', __name__)


@api.route("/traceability-report-detail", methods=['POST'])
@authorization_require()
def get_traceability():
    try:
        token = get_jwt_identity()
        cloud_id = token.get('cloudId')
        project_id = token.get('projectId')
        body_request = request.get_json()
        stories = body_request.get("story", {})
        data = []
        for story in stories:
            infor_test_executions = []
            test_executions = TestExecution.query.filter(TestExecution.cloud_id == cloud_id, TestExecution.project_id,
                                                         TestExecution.issue_id.in_(story['test_execution'])) \
                .order_by(asc(TestExecution.issue_key)).all()
            test_exe_ids = [item.id for item in test_executions]
            test_runs = TestRun.query.filter(TestRun.cloud_id == cloud_id, TestRun.project_id == project_id,
                                             TestRun.test_execution_id.in_(test_exe_ids))
            test_run_ids = [item.id for item in test_runs.all()]
            defect = Defects.query.filter(Defects.test_run_id.in_(test_run_ids)).all()
            issue_id_bug = [item.issue_id for item in defect]
            for test_execution_id in test_exe_ids:
                test_execution = TestExecution.query.filter(TestExecution.project_id == project_id,
                                                            TestExecution.cloud_id == cloud_id,
                                                            TestExecution.id == test_execution_id).first()

                test_environments = db.session.query(TestEnvironment) \
                    .join(TestExecutionsTestEnvironments, TestExecutionsTestEnvironments.test_environment_id
                          == TestEnvironment.id) \
                    .filter(TestExecutionsTestEnvironments.test_execution_id == test_execution.id) \
                    .order_by(asc(TestEnvironment.name)).all()

                test_status = TestStatus.query.filter(TestStatus.project_id == project_id,
                                                      TestStatus.cloud_id == cloud_id) \
                    .order_by(asc(TestStatus.created_date)).all()
                dict_testing = {}
                sum_status = 0
                test_run = TestRun.query.filter(TestRun.cloud_id == cloud_id, TestRun.project_id == project_id,
                                                TestRun.test_execution_id == test_execution_id)
                for i, status in enumerate(test_status):
                    count_status = test_run.filter(TestRun.test_status_id == status.id).count()
                    if (i + 1) < len(test_status):
                        dict_testing[status.name] = {"percent": int(count_status * 100 / len(test_runs.all())),
                                                     "count": count_status}
                        sum_status += int(count_status * 100 / len(test_runs.all()))
                    else:
                        dict_testing[status.name] = {"percent": 100 - sum_status,
                                                     "count": count_status}
                infor_test_execution = {
                    'issue_key': test_execution.issue_key,
                    'executed_on': test_execution.modified_date,
                    'environment': [test_environment.name for test_environment in test_environments],
                    'testing': dict_testing
                }
                infor_test_executions.append(infor_test_execution)
            report = {
                "test_execution": infor_test_executions,
                "bug": {
                    "issue_id": issue_id_bug,
                    "count": len(issue_id_bug)
                }
            }
            data.append(report)
        return send_result(data=data)
    except Exception as ex:
        return send_error(message=str(ex))


@api.route("/execution-report-by-coverage", methods=['POST'])
@authorization_require()
def report_execution_coverage():
    try:
        token = get_jwt_identity()
        cloud_id = token.get('cloudId')
        project_id = token.get('projectId')
        body_request = request.get_json()
        test_execution_ids = body_request.get("test_execution_ids", [])
        test_executions = TestExecution.query.filter(TestExecution.cloud_id == cloud_id,
                                                     TestExecution.project_id == project_id,
                                                     TestExecution.issue_id.in_(test_execution_ids)) \
            .order_by(asc(TestExecution.issue_key)).all()
        test_status = TestStatus.query.filter(TestStatus.project_id == project_id,
                                              TestStatus.cloud_id == cloud_id) \
            .order_by(asc(TestStatus.created_date)).all()
        data = []
        for test_execution in test_executions:
            sum_status = 0
            dict_testing = {}
            test_runs = TestRun.query.filter(TestRun.test_execution_id == test_execution,
                                             TestRun.project_id == project_id, TestRun.cloud_id == cloud_id)
            for i, status in enumerate(test_status):
                count_status = test_runs.filter(TestRun.test_status_id == status.id).count()
                if (i + 1) < len(test_status):
                    dict_testing[status.name] = {"percent": int(count_status * 100 / len(test_runs.all())),
                                                 "count": count_status}
                    sum_status += int(count_status * 100 / len(test_runs.all()))
                else:
                    dict_testing[status.name] = {"percent": 100-sum_status,
                                                 "count": count_status}
            add_data = {
                "issue_key": test_execution.issue_key,
                "testing": dict_testing
            }
            data.append(add_data)
        return send_result(data=data)
    except Exception as ex:
        return send_error(message=str(ex))


@api.route("/execution-report-by-environment", methods=['POST'])
@authorization_require()
def report_execution_environment():
    try:
        token = get_jwt_identity()
        cloud_id = token.get('cloudId')
        project_id = token.get('projectId')
        body_request = request.get_json()
        environment_ids = body_request.get("environment_ids", [])
        test_status = TestStatus.query.filter(TestStatus.project_id == project_id,
                                              TestStatus.cloud_id == cloud_id) \
            .order_by(asc(TestStatus.created_date)).all()
        data = []
        environments = TestEnvironment.query.filter(TestEnvironment.project_id == project_id,
                                                    TestEnvironment.cloud_id == cloud_id,
                                                    TestEnvironment.id.in_(environment_ids))\
            .order_by(asc(TestEnvironment.name)).all()
        for environment in environments:
            test_executions = TestExecutionsTestEnvironments.query.filter(TestExecutionsTestEnvironments.
                                                                          test_environment_id == environment.id).all()
            test_execution_ids = [test_execution.id for test_execution in test_executions]
            dict_testing = {}
            sum_status = 0
            test_runs = TestRun.query.filter(TestRun.project_id == project_id, TestRun.cloud_id == cloud_id,
                                             TestRun.test_execution_id.in_(test_execution_ids))
            for i, status in enumerate(test_status):
                count_status = test_runs.query.filter(TestRun.test_status_id == status.id).all()

                if (i + 1) < len(test_status):
                    dict_testing[status.name] = {"percent": int(count_status * 100 / len(test_runs.all())),
                                                 "count": count_status}
                    sum_status += int(count_status * 100 / len(test_runs.all()))
                else:
                    dict_testing[status.name] = {"percent": 100 - sum_status,
                                                 "count": count_status}
            add_data = {
                "environment": environment.name,
                "testing": dict_testing
            }
            data.append(add_data)
    except Exception as ex:
        return send_error(message=str(ex))
