import os
import uuid
from flask import Blueprint, request, make_response, send_file, Response
from flask_jwt_extended import get_jwt_identity
from sqlalchemy import asc
from io import BytesIO
import datetime
from app.enums import FILE_PATH
from app.gateway import authorization_require
from app.models import db, TestExecution, TestRun, TestExecutionsTestEnvironments, \
    TestEnvironment, Defects, TestStatus
from app.utils import send_result, send_error, get_timestamp_now
import xlsxwriter
import io


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
                dict_testing = []
                sum_status = 0
                test_run = TestRun.query.filter(TestRun.cloud_id == cloud_id, TestRun.project_id == project_id,
                                                TestRun.test_execution_id == test_execution_id)
                for i, status in enumerate(test_status):
                    count_status = test_run.filter(TestRun.test_status_id == status.id).count()
                    if (i + 1) < len(test_status):
                        dict_testing.append({
                            "status_name": status.name,
                            "percent": int(count_status * 100 / len(test_runs.all())),
                            "count": count_status})
                        sum_status += int(count_status * 100 / len(test_runs.all()))
                    else:
                        dict_testing.append({
                            "status_name": status.name,
                            "percent":  100 - sum_status,
                            "count": count_status})
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
        stories = body_request.get("stories", [])
        """
            request  stories:[{ "story_name":"" , "test_execution_issue_id":[]},{}]
            return   data = [{"story_name":"", "testing":[{"percent":"","count":"","status_name":""},{}]}]
        """
        data = []
        test_status = TestStatus.query.filter(TestStatus.project_id == project_id,
                                              TestStatus.cloud_id == cloud_id) \
            .order_by(asc(TestStatus.created_date)).all()
        for story in stories:
            test_executions = TestExecution.query.filter(TestExecution.cloud_id == cloud_id,
                                                         TestExecution.project_id == project_id,
                                                         TestExecution.issue_id.in_(story["test_execution_issue_id"]))\
                .all()
            test_execution_ids = [test_execution.id for test_execution in test_executions]
            test_runs = TestRun.query.filter(TestRun.test_execution_id.in_(test_execution_ids))
            dict_testing = []
            for i, status in enumerate(test_status):
                count_status = test_runs.filter(TestRun.test_status_id == status.id).count()
                dict_testing.append({"percent": int(count_status * 100 / len(test_runs.all())),
                                     "count": count_status, "status_name": status.name})
            data.append({"story_name": story["story_name"], "testing": dict_testing})
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
            dict_testing = []
            sum_status = 0
            test_runs = TestRun.query.filter(TestRun.project_id == project_id, TestRun.cloud_id == cloud_id,
                                             TestRun.test_execution_id.in_(test_execution_ids))
            for i, status in enumerate(test_status):
                count_status = test_runs.query.filter(TestRun.test_status_id == status.id).all()

                if (i + 1) < len(test_status):
                    dict_testing.append({"percent": int(count_status * 100 / len(test_runs.all())),
                                         "count": count_status})
                    sum_status += int(count_status * 100 / len(test_runs.all()))
                else:
                    dict_testing.append({"percent": 100 - sum_status,
                                         "count": count_status})
            add_data = {
                "environment": environment.name,
                "testing": dict_testing
            }
            data.append(add_data)
        return send_result(data=data)
    except Exception as ex:
        return send_error(message=str(ex))


@api.route("/traceability-report-detail/export", methods=['POST'])
@authorization_require()
def export_traceability():
    try:
        token = get_jwt_identity()
        cloud_id = token.get('cloudId')
        project_id = token.get('projectId')
        project_name = token.get('projectName')
        body_request = request.get_json()
        day = datetime.date.today()
        output = io.BytesIO()
        stories = body_request.get("stories", [])
        if len(stories) == 0:
            return send_error(message="No data export")
        filename = f'BTest_Traceability Report Detail_{day}.xlsx'
        if len(stories) == 0:
            return send_error(message="No data export")
        # Khởi tạo Workbook mới
        workbook = xlsxwriter.Workbook(output)
        # Tạo Worksheet mới
        worksheet = workbook.add_worksheet()
        list_testing = stories[0]["test_execution"][0]["testing"]
        list_bug = stories[0]["bug"]
        # create column of execution
        col_execution = len(list_testing) * 2 + 1
        # create column of bug
        col_bug = len(list_bug) * 2
        """
            create table with number of columns = 2 row(story, test_set) + col_execution + col_bug
        """
        col_file = 2 + col_execution + col_bug

        format_cell = workbook.add_format({'align': 'center', 'valign': 'vcenter'})
        # merge cell : TRACEABILITY REPORT DETAIL - NAME PROJECT
        worksheet.merge_range(0, 0, 0, col_file - 1, f'TRACEABILITY REPORT DETAIL - {project_name}', format_cell)
        # merge cell : story
        worksheet.merge_range(1, 0, 3, 0, "Story", format_cell)
        # merge cell : test set
        worksheet.merge_range(1, 1, 3, 1, "Test Set", format_cell)
        # merge cell : Execution Result
        worksheet.merge_range(1, 2, 1, col_execution + 1, "Execution Result", format_cell)
        # merge cell : Bug
        worksheet.merge_range(1, col_execution + 2, 1, col_file - 1, "Bug", format_cell)
        # merge cell : issue_test_execution
        worksheet.merge_range(2, 2, 3, 2, "Issue Key", format_cell)
        col = 3
        for i, testing in enumerate(list_testing):
            worksheet.merge_range(2, col, 2, col + 1, testing["status_name"], format_cell)
            col = col + 2
        for i, bug in enumerate(list_bug):
            worksheet.merge_range(2, col, 2, col + 1, bug["status_name"], format_cell)
            col = col + 2
        # write column count, percent for Execution and Bug
        for i in range(3, col_file, 2):
            worksheet.write(3, i, 'Count')
            worksheet.write(3, i + 1, 'Percent')
        row = 4
        for story in stories:
            set_column = 3
            # write data to exel : column test_set
            for i, test_set_key in enumerate(story["test_set"]):
                worksheet.write(row + i, 1, test_set_key)
            # write data to exel : column test_execution
            for i, execution in enumerate(story["test_execution"]):
                worksheet.write(row + i, 2, execution["issue_key"])
                for index, status in enumerate(execution["testing"]):
                    worksheet.write(row + i, set_column + index * 2, status["count"])
                    worksheet.write(row + i, set_column + index * 2 + 1, status["percent"])
            set_column = set_column + col_execution - 1
            # write data to exel : column bug
            for status_bug in story["bug"]:
                worksheet.merge_range(row, set_column, row + len(story["test_execution"]) - 1, set_column,
                                      status_bug["count"], format_cell)
                worksheet.merge_range(row, set_column + 1, row + len(story["test_execution"]) - 1, set_column + 1,
                                      status_bug["percent"], format_cell)
                set_column = set_column + 2
            # up row and write data to exel : column story
            if len(story["test_set"]) > len(story["test_execution"]):
                row = row + len(story["test_set"])
                row_up = len(story["test_set"])
            else:
                row = row + len(story["test_execution"])
                row_up = len(story["test_execution"])
            worksheet.merge_range(row - row_up, 0, row - 1, 0, story["story_name"], format_cell)
        # all border 0,0  -> row,colum_file
        # add after FE fix
        workbook.close()
        # Lấy nội dung của Workbook và gửi đi như là file đính kèm
        excel_data = output.getvalue()
        return send_file(io.BytesIO(excel_data), attachment_filename=filename, as_attachment=True)
    except Exception as ex:
        return send_error(message=str(ex))
