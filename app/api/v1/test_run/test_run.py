import json
import os
import uuid
from operator import or_
import datetime
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, create_access_token
from benedict import benedict
from numpy import double
from sqlalchemy import asc, desc
from werkzeug.utils import secure_filename, send_file

from app.api.v1.setting.setting_validator import UpdateMiscellaneousRequest
from app.api.v1.test_run.schema import TestRunSchema, CombineSchema
from app.api.v1.test_type.test_type import get_test_type_default
from app.enums import FILE_PATH, URL_SERVER
from app.gateway import authorization_require
from app.models import TestStep, TestCase, TestType, db, TestField, Setting, TestRun, TestExecution, \
    TestCasesTestExecutions, TestStatus, TestStepDetail, Defects, TestEvidence, TestSet, Timer, TestActivity
from app.utils import send_result, send_error, data_preprocessing, get_timestamp_now, validate_request
from app.validator import CreateTestValidator, SettingSchema, DefectsSchema, TestStepTestRunSchema, UploadValidation, \
    EvidenceSchema, PostDefectSchema, TimerSchema, TestActivitySchema
from app.parser import TestFieldSchema, TestStepSchema

api = Blueprint('test_run', __name__)


@api.route("/<test_run_id>/<new_name_status>", methods=["PUT"])
@authorization_require()
def change_status_test_run(test_run_id, new_name_status):
    try:
        token = get_jwt_identity()
        project_id = token.get("projectId")
        cloud_id = token.get("cloudId")
        user_id = token.get("userId")
        body_request = request.get_json()
        test_step_detail_id = body_request.get('test_step_detail_id', '')
        if test_step_detail_id == '':
            query = TestRun.query.filter(TestRun.id == test_run_id).first()
            if not query:
                return send_error(message="Test run is not exists")
            test_status = TestStatus.query.filter(TestStatus.id == query.test_status_id).first()
            status = TestStatus.query.filter(TestStatus.cloud_id == cloud_id, TestStatus.project_id == project_id,
                                             TestStatus.name == new_name_status).first()
            if not status:
                return send_error(message="status is not exists")
            detail = {"step": 0, "old_name": test_status.name,
                      "new_name": new_name_status.upper()}
            query.test_status_id = status.id
            db.session.flush()
            activity_test_run(user_id, test_run_id, detail, 1)
        else:
            query = TestStepDetail.query.filter(TestStepDetail.id == test_step_detail_id).first()
            stt = stt_step_detail_id(cloud_id, project_id, test_run_id, [])
            if not query:
                return send_error(message="Test run is not exists")
            test_status = TestStatus.query.filter(TestStatus.id == query.status_id).first()
            status = TestStatus.query.filter(TestStatus.cloud_id == cloud_id, TestStatus.project_id == project_id,
                                             TestStatus.name == new_name_status).first()
            if not status:
                return send_error(message="status is not exists")
            detail = {"step": stt.index(test_step_detail_id) + 1,
                      "old_name": test_status.name,
                      "new_name": new_name_status.upper()}
            query.status_id = status.id
            db.session.flush()
            activity_test_run(user_id, test_run_id, detail, 2)
        db.session.commit()
        return send_result(message="success")
    except Exception as ex:
        db.session.rollback()
        return send_error(message=str(ex))


def activity_test_run(user_id: str, test_run_id: str, comment: dict, index: int):
    if index == 1:
        activity = TestActivity(
            id=str(uuid.uuid4()),
            test_run_id=test_run_id,
            jira_user_id=user_id,
            created_date=get_timestamp_now(),
            status_change='Change final status of test run.',
            comment=comment
        )
        db.session.add(activity)
        db.session.flush()
    elif index == 2:
        activity = TestActivity(
            id=str(uuid.uuid4()),
            test_run_id=test_run_id,
            jira_user_id=user_id,
            created_date=get_timestamp_now(),
            status_change='Change status of any step (not final status)',
            comment=comment
        )
        db.session.add(activity)
        db.session.flush()

    elif index == 3:
        activity = TestActivity(
            id=str(uuid.uuid4()),
            test_run_id=test_run_id,
            jira_user_id=user_id,
            created_date=get_timestamp_now(),
            status_change='Change Actual result',
            comment=comment
        )
        db.session.add(activity)
        db.session.flush()

    elif index == 4:
        activity = TestActivity(
            id=str(uuid.uuid4()),
            test_run_id=test_run_id,
            jira_user_id=user_id,
            created_date=get_timestamp_now(),
            status_change='Change comment of each step',
            comment=comment
        )
        db.session.add(activity)
        db.session.flush()

    elif index == 5:
        activity = TestActivity(
            id=str(uuid.uuid4()),
            test_run_id=test_run_id,
            jira_user_id=user_id,
            created_date=get_timestamp_now(),
            status_change='Change comment in Finding section.',
            comment=comment
        )
        db.session.add(activity)
        db.session.flush()

    elif index == 6:
        activity = TestActivity(
            id=str(uuid.uuid4()),
            test_run_id=test_run_id,
            jira_user_id=user_id,
            created_date=get_timestamp_now(),
            status_change='Start the time',
            comment=comment
        )
        db.session.add(activity)
        db.session.flush()

    elif index == 7:
        activity = TestActivity(
            id=str(uuid.uuid4()),
            test_run_id=test_run_id,
            jira_user_id=user_id,
            created_date=get_timestamp_now(),
            status_change='Pause the time',
            comment=comment
        )
        db.session.add(activity)
        db.session.flush()

    elif index == 8:
        activity = TestActivity(
            id=str(uuid.uuid4()),
            test_run_id=test_run_id,
            jira_user_id=user_id,
            created_date=get_timestamp_now(),
            status_change='Reset timer',
            comment=comment
        )
        db.session.add(activity)
        db.session.flush()

    elif index == 9:
        activity = TestActivity(
            id=str(uuid.uuid4()),
            test_run_id=test_run_id,
            jira_user_id=user_id,
            created_date=get_timestamp_now(),
            status_change='Add defect in Finding section',
            comment=comment
        )
        db.session.add(activity)
        db.session.flush()

    elif index == 10:
        activity = TestActivity(
            id=str(uuid.uuid4()),
            test_run_id=test_run_id,
            jira_user_id=user_id,
            created_date=get_timestamp_now(),
            status_change='Remove defect in Finding section',
            comment=comment
        )
        db.session.add(activity)
        db.session.flush()

    elif index == 11:
        activity = TestActivity(
            id=str(uuid.uuid4()),
            test_run_id=test_run_id,
            jira_user_id=user_id,
            created_date=get_timestamp_now(),
            status_change='Remove evidence for each step',
            comment=comment
        )
        db.session.add(activity)
        db.session.flush()

    elif index == 12:
        activity = TestActivity(
            id=str(uuid.uuid4()),
            test_run_id=test_run_id,
            jira_user_id=user_id,
            created_date=get_timestamp_now(),
            status_change='Add evidence for each step',
            comment=comment
        )
        db.session.add(activity)
        db.session.flush()

    elif index == 13:
        activity = TestActivity(
            id=str(uuid.uuid4()),
            test_run_id=test_run_id,
            jira_user_id=user_id,
            created_date=get_timestamp_now(),
            status_change='Add defect for each step',
            comment=comment
        )
        db.session.add(activity)
        db.session.flush()

    elif index == 14:
        activity = TestActivity(
            id=str(uuid.uuid4()),
            test_run_id=test_run_id,
            jira_user_id=user_id,
            created_date=get_timestamp_now(),
            status_change='Remove defect for each step',
            comment=comment
        )
        db.session.add(activity)
        db.session.flush()

    elif index == 15:
        activity = TestActivity(
            id=str(uuid.uuid4()),
            test_run_id=test_run_id,
            jira_user_id=user_id,
            created_date=get_timestamp_now(),
            status_change='Add evidence Finding section',
            comment=comment
        )
        db.session.add(activity)
        db.session.flush()
    elif index == 16:
        activity = TestActivity(
            id=str(uuid.uuid4()),
            test_run_id=test_run_id,
            jira_user_id=user_id,
            created_date=get_timestamp_now(),
            status_change='Remove evidence Finding section',
            comment=comment
        )
        db.session.add(activity)
        db.session.flush()
    elif index == 17:
        activity = TestActivity(
            id=str(uuid.uuid4()),
            test_run_id=test_run_id,
            jira_user_id=user_id,
            created_date=get_timestamp_now(),
            status_change='Merged Execution',
            comment=comment
        )
        db.session.add(activity)
        db.session.flush()
    elif index == 18:
        activity = TestActivity(
            id=str(uuid.uuid4()),
            test_run_id=test_run_id,
            jira_user_id=user_id,
            created_date=get_timestamp_now(),
            status_change='Reseted Execution',
            comment=comment
        )
        db.session.add(activity)
        db.session.flush()
    elif index == 19:
        activity = TestActivity(
            id=str(uuid.uuid4()),
            test_run_id=test_run_id,
            jira_user_id=user_id,
            created_date=get_timestamp_now(),
            status_change='Change assignee of test run',
            comment=comment
        )
        db.session.add(activity)
        db.session.flush()


# call change status mới call set time
@api.route("/<test_run_id>/set_time", methods=["PUT"])
@authorization_require()
def set_time_test_run(test_run_id):
    try:
        token = get_jwt_identity()
        project_id = token.get("projectId")
        cloud_id = token.get("cloudId")
        user_id = token.get("userId")
        edited = request.args.get('edited', False, type=bool)
        reg = request.get_json()
        start_time = reg.get("start_time", 0)
        if not isinstance(start_time, int):
            start_time = 0
        query = TestRun.query.filter(TestRun.id == test_run_id).first()
        if start_time != 0 and edited:
            if query.end_date == 0:
                if query.status.name in ["PASSED", "FAILED"]:
                    query.start_date = start_time
                    query.end_date = get_timestamp_now()
                    db.session.flush()
                    if start_time > query.end_date:
                        return send_error(message="Test run cannot start after finished date", is_dynamic=True)
                else:
                    query.start_date = start_time
                    query.end_date = 0
                    db.session.flush()
            else:
                if query.status.name in ["PASSED", "FAILED"]:
                    if start_time > query.end_date:
                        return send_error(message="Test run cannot start after finished date", is_dynamic=True)
                    query.start_date = start_time
                    db.session.flush()
                else:
                    query.start_date = start_time
                    query.end_date = 0
                    db.session.flush()
        else:
            if query.start_date == 0 and query.end_date == 0:
                if query.status.name in ["PASSED", "FAILED"]:
                    query.start_date = get_timestamp_now()
                    query.end_date = TestRun.start_date
                    db.session.flush()
                else:
                    query.start_date = get_timestamp_now()
                    db.session.flush()
            elif query.start_date != 0 and query.end_date == 0 and (query.status.name in ["PASSED", "FAILED"]):
                query.end_date = get_timestamp_now()
                db.session.flush()
            elif query.start_date == 0 and query.end_date != 0:
                if query.status.name not in ["PASSED", "FAILED"]:
                    query.end_date = get_timestamp_now()
                    query.end_date = 0
                    db.session.flush()
                else:
                    query.end_date = get_timestamp_now()
                    query.end_date = TestRun.start_date
                    db.session.flush()
            elif query.start_date != 0 and query.end_date != 0 and (query.status.name not in ["PASSED", "FAILED"]):
                query.end_date = 0
                db.session.flush()
        db.session.commit()
        return send_result(message="success")
    except Exception as ex:
        db.session.rollback()
        return send_error(message="failed")


@api.route("/<test_run_id>/create_data", methods=["POST"])
@authorization_require()
def post_data_and_comment_test_detail(test_run_id):
    try:
        token = get_jwt_identity()
        cloud_id = token.get('cloudId')
        project_id = token.get('projectId')
        user_id = token.get('userId')
        req = request.get_json()
        data = req.get('data')
        test_step_detail_id = req.get('test_step_detail_id', '')
        where = request.args.get('where', 'comment', type=str)
        test_run = TestRun.query.filter(TestRun.cloud_id == cloud_id, TestRun.project_id == project_id,
                                        TestRun.id == test_run_id).first()
        if test_run is None:
            return send_error("Not found test run")
        if test_step_detail_id == '':
            test_run.comment = data
            detail = {"new_value": data}
            activity_test_run(user_id, test_run_id, detail, 5)
            db.session.flush()
        else:
            stt = stt_step_detail_id(cloud_id, project_id, test_run_id, [])
            test_step_detail = TestStepDetail.query.filter(TestStepDetail.id == test_step_detail_id).first()
            if test_step_detail is None:
                return send_error("Not found test detail")
            if where == 'comment':
                test_step_detail.comment = data
                db.session.flush()
                detail = {"step": stt.index(test_step_detail_id) + 1, "new_value": data}
                activity_test_run(user_id, test_run_id, detail, 4)
            elif where == 'actual':
                test_step_detail.data = data
                detail = {"step": stt.index(test_step_detail_id) + 1, "new_value": data}
                activity_test_run(user_id, test_run_id, detail, 3)
                db.session.flush()
            else:
                return send_error(message='Please check your request params')
        db.session.commit()
        return send_result(message="successfully")
    except Exception as ex:
        db.session.rollback()
        return send_error(message=str(ex))


@api.route("/<test_run_id>/get_data", methods=["POST"])
@authorization_require()
def get_data_and_comment_test_detail(test_run_id):
    try:
        token = get_jwt_identity()
        cloud_id = token.get('cloudId')
        project_id = token.get('projectId')
        req = request.get_json()
        test_step_detail_id = req.get('test_step_detail_id')
        where = request.args.get('where', 'comment', type=str)
        test_run = TestRun.query.filter(TestRun.cloud_id == cloud_id, TestRun.project_id == project_id,
                                        TestRun.id == test_run_id).first()
        if test_run is None:
            return send_error("Not found test run")
        test_step_detail = TestStepDetail.query.filter(TestStepDetail.id == test_step_detail_id).first()
        if test_step_detail is None:
            return send_error("Not found test detail")
        if where == 'comment':
            data = test_step_detail.comment
        elif where == 'actual':
            data = test_step_detail.data
        else:
            return send_error(message='Please check your request params')
        return send_result(data=data)
    except Exception as ex:
        db.session.rollback()
        return send_error(message=str(ex))


@api.route("/<test_run_id>/defect", methods=["POST"])
@authorization_require()
def post_defect(test_run_id):
    try:
        token = get_jwt_identity()
        cloud_id = token.get('cloudId')
        project_id = token.get('projectId')
        user_id = token.get('userId')
        is_valid, data, body_request = validate_request(PostDefectSchema(), request)
        if not is_valid:
            return send_error(data=data, code=200, is_dynamic=True)
        type_kind = body_request['test_kind']
        issue_id = body_request['issue_id']
        issue_key = body_request['issue_key']
        test_step_detail_id = body_request.get('test_step_detail_id', '')
        test_run = TestRun.query.filter(TestRun.cloud_id == cloud_id, TestRun.project_id == project_id,
                                        TestRun.id == test_run_id).first()
        if test_run is None:
            return send_error("Not found test run")
        # 1 : test case  2: test set  3:test_execution
        if type_kind == "Test Case":
            test_type_id = get_test_type_default(cloud_id, project_id)
            test_case = TestCase.query.filter(TestCase.cloud_id == cloud_id, TestCase.project_id == project_id,
                                              TestCase.issue_id == issue_id, TestCase.issue_key == issue_key).first()
            if test_case is None:
                test_case = TestCase(
                    id=str(uuid.uuid4()),
                    issue_id=issue_id,
                    issue_key=issue_key,
                    project_id=project_id,
                    cloud_id=cloud_id,
                    created_date=get_timestamp_now(),
                    test_type_id=test_type_id
                )
                db.session.add(test_case)
                db.session.flush()
        elif type_kind == "Test Set":
            test_set = TestSet.query.filter(TestSet.cloud_id == cloud_id, TestSet.project_id == project_id,
                                            TestSet.issue_id == issue_id, TestSet.issue_key == issue_key).first()
            if test_set is None:
                test_set = TestSet(
                    id=str(uuid.uuid4()),
                    issue_id=issue_id,
                    issue_key=issue_key,
                    project_id=project_id,
                    cloud_id=cloud_id,
                    created_date=get_timestamp_now()
                )
                db.session.add(test_set)
                db.session.flush()
        elif type_kind == "Test Execution":
            test_execution = TestExecution.query.filter(TestExecution.cloud_id == cloud_id,
                                                        TestExecution.project_id == project_id,
                                                        TestExecution.issue_id == issue_id,
                                                        TestExecution.issue_key == issue_key).first()
            if test_execution is None:
                test_execution = TestExecution(
                    id=str(uuid.uuid4()),
                    issue_id=issue_id,
                    issue_key=issue_key,
                    project_id=project_id,
                    cloud_id=cloud_id,
                    created_date=get_timestamp_now()
                )
                db.session.add(test_execution)
                db.session.flush()
        if test_step_detail_id == '':
            defect_exist = Defects.query.filter(Defects.test_run_id == test_run_id, Defects.test_issue_id == issue_id,
                                                Defects.test_step_detail_id.is_(None),
                                                Defects.test_issue_key == issue_key).first()
            if defect_exist:
                return send_error("Defect existed")
            defect = Defects(
                id=str(uuid.uuid4()),
                test_issue_id=issue_id,
                test_issue_key=issue_key,
                test_run_id=test_run_id,
                created_date=get_timestamp_now()
            )
            db.session.add(defect)
            db.session.flush()
            detail = {"step": 0, "issue_key": issue_key}
            activity_test_run(user_id, test_run_id, detail, 9)
        else:
            test_detail = TestStepDetail.query.filter(TestStepDetail.id == test_step_detail_id,
                                                      TestStepDetail.test_run_id == test_run_id).first()
            if test_detail is None:
                return send_error("Not found test detail")

            defect_exist = Defects.query.filter(Defects.test_run_id == test_run_id, Defects.test_issue_id == issue_id,
                                                Defects.test_step_detail_id == test_step_detail_id,
                                                Defects.test_issue_key == issue_key).first()
            if defect_exist:
                return send_error("Defect existed")
            defect = Defects(
                id=str(uuid.uuid4()),
                test_issue_id=issue_id,
                test_issue_key=issue_key,
                test_step_detail_id=test_step_detail_id,
                test_run_id=test_run_id,
                created_date=get_timestamp_now()
            )
            db.session.add(defect)
            db.session.flush()
            stt = stt_step_detail_id(cloud_id, project_id, test_run_id, [])
            detail = {"step": stt.index(test_step_detail_id) + 1, "issue_key": issue_key}
            activity_test_run(user_id, test_run_id, detail, 13)
        db.session.commit()
        return send_result(message="Successfully")
    except Exception as ex:
        db.session.rollback()
        return send_error(message=str(ex))


@api.route("/<test_run_id>/get-defect", methods=["POST"])
@authorization_require()
def get_defect(test_run_id):
    try:
        token = get_jwt_identity()
        cloud_id = token.get('cloudId')
        project_id = token.get('projectId')
        body_request = request.get_json()
        test_step_detail_id = body_request.get('test_step_detail_id', '')
        search_other = request.args.get('search_other', False, type=bool)
        test_run = TestRun.query.filter(TestRun.cloud_id == cloud_id, TestRun.project_id == project_id,
                                        TestRun.id == test_run_id).first()
        if test_run is None:
            return send_error("Not found test run")
        if test_step_detail_id == '':
            dict_defect = {}
            # query global
            defects = Defects.query.filter(Defects.test_run_id == test_run_id,
                                           Defects.test_step_detail_id.is_(None)) \
                .order_by(asc(Defects.created_date)).all()
            defect_global = DefectsSchema(many=True).dump(defects)
            dict_defect['Global'] = defect_global
            if not search_other:
                test_detail_ids = stt_step_detail_id(cloud_id, project_id, test_run_id, [])
                # query - step
                for i, test_detail_id in enumerate(test_detail_ids):
                    defect = Defects.query.filter(Defects.test_run_id == test_run_id,
                                                  Defects.test_step_detail_id == test_detail_id) \
                        .order_by(asc(Defects.created_date)).all()
                    defect_step = DefectsSchema(many=True).dump(defect)
                    if len(defect_step) > 0:
                        dict_defect[f'Step {i + 1}'] = defect_step
            return send_result(data=dict_defect)
        else:
            test_detail = TestStepDetail.query.filter(TestStepDetail.id == test_step_detail_id,
                                                      TestStepDetail.test_run_id == test_run_id).first()
            if test_detail is None:
                return send_error("Not found test detail")
            defects = Defects.query.filter(Defects.test_run_id == test_run_id,
                                           Defects.test_step_detail_id == test_step_detail_id) \
                .order_by(asc(Defects.created_date))
            return send_result(data=DefectsSchema(many=True).dump(defects))
    except Exception as ex:
        return send_error(message=str(ex))


@api.route("/<test_run_id>/defect", methods=["DELETE"])
@authorization_require()
def delete_defect(test_run_id):
    try:
        token = get_jwt_identity()
        cloud_id = token.get('cloudId')
        project_id = token.get('projectId')
        user_id = token.get('userId')
        is_valid, data, body_request = validate_request(PostDefectSchema(), request)
        test_step_detail_id = body_request.get('test_step_detail_id', '')
        if not is_valid:
            return send_error(data=data, code=200, is_dynamic=True)
        issue_id = body_request['issue_id']
        issue_key = body_request['issue_key']
        test_run = TestRun.query.filter(TestRun.cloud_id == cloud_id, TestRun.project_id == project_id,
                                        TestRun.id == test_run_id).first()
        if test_run is None:
            return send_error("Not found test run")
        if test_step_detail_id == '':
            Defects.query.filter(Defects.test_run_id == test_run_id, Defects.test_issue_id == issue_id,
                                 Defects.test_step_detail_id.is_(None),
                                 Defects.test_issue_key == issue_key).delete()
            db.session.flush()
            detail = {"step": 0, "issue_key": issue_key}
            activity_test_run(user_id, test_run_id, detail, 10)
        else:
            test_detail = TestStepDetail.query.filter(TestStepDetail.id == test_step_detail_id,
                                                      TestStepDetail.test_run_id == test_run_id).first()
            if test_detail is None:
                return send_error("Not found test detail")
            Defects.query.filter(Defects.test_run_id == test_run_id, Defects.test_issue_id == issue_id,
                                 Defects.test_step_detail_id == test_step_detail_id,
                                 Defects.test_issue_key == issue_key).delete()
            db.session.flush()
            stt = stt_step_detail_id(cloud_id, project_id, test_run_id, [])
            detail = {"step": stt.index(test_step_detail_id) + 1, "issue_key": issue_key}
            activity_test_run(user_id, test_run_id, detail, 14)
        db.session.commit()
        return send_result(message="Successfully")
    except Exception as ex:
        db.session.rollback()
        return send_error(message=str(ex))


@api.route("/<issue_id>/<test_issue_id>", methods=["GET"])
@authorization_require()
def load_test_run(issue_id, test_issue_id):
    token = get_jwt_identity()
    cloud_id = token.get('cloudId')
    project_id = token.get('projectId')
    test_execution = TestExecution.query.filter(TestExecution.cloud_id == cloud_id, TestExecution.issue_id == issue_id,
                                                TestExecution.project_id == project_id).first()
    if test_execution is None:
        return send_error("Not found test execution")
    test_case = TestCase.query.filter(TestCase.cloud_id == cloud_id, TestCase.issue_id == test_issue_id,
                                      TestCase.project_id == project_id).first()
    if test_case is None:
        return send_error("Not found test case")
    test_run = TestRun.query.filter(TestRun.cloud_id == cloud_id, TestRun.project_id == project_id,
                                    TestRun.test_execution_id == test_execution.id,
                                    TestRun.test_case_id == test_case.id).first()
    if test_run is None:
        return send_error("Not found test run")
    test_steps = db.session.query(TestStep).filter(TestStep.project_id == project_id, TestStep.cloud_id == cloud_id,
                                                   TestStep.test_case_id == test_case.id).order_by(asc(TestStep.index)) \
        .all()
    result = []
    for test_step in test_steps:
        link = test_step.id + "/"
        if test_step.test_case_id_reference:
            result_child = get_test_step_id_by_test_case_id_reference(cloud_id, project_id,
                                                                      test_step.test_case_id_reference, [],
                                                                      link, test_run.id)
            result = result + result_child
        else:
            data = TestStepTestRunSchema().dump(test_step)
            data['link'] = link
            test_step_detail = TestStepDetail.query.filter(TestStepDetail.test_step_id == data['id'],
                                                           TestStepDetail.test_run_id == test_run.id,
                                                           TestStepDetail.link == data['link']).first()
            data['test_step_detail_id'] = test_step_detail.id
            result.append(data)
    try:
        return send_result(data=result)
    except Exception as ex:
        return send_error(message=str(ex))


# lấy tất cả id test step trong test case call
def get_test_step_id_by_test_case_id_reference(cloud_id, project_id, test_case_id_reference,
                                               test_details: list, link: str, test_run_id):
    test_step_reference = db.session.query(TestStep.id, TestStep.cloud_id, TestStep.project_id, TestStep.action,
                                           TestStep.attachments, TestStep.result, TestStep.data, TestStep.created_date,
                                           TestStep.test_case_id, TestStep.test_case_id_reference, TestCase.issue_key,
                                           TestStep.custom_fields) \
        .join(TestCase, TestCase.id == TestStep.test_case_id) \
        .filter(TestStep.project_id == project_id, TestStep.cloud_id == cloud_id,
                TestStep.test_case_id == test_case_id_reference).all()

    for step in test_step_reference:
        new_link = link + step.id + "/"
        if step.test_case_id_reference is None:
            data = TestStepTestRunSchema().dump(step)
            data['link'] = new_link
            test_step_detail = TestStepDetail.query.filter(TestStepDetail.test_step_id == data['id'],
                                                           TestStepDetail.test_run_id == test_run_id,
                                                           TestStepDetail.link == data['link']).first()
            data['test_step_detail_id'] = test_step_detail.id
            test_details.append(data)
        else:
            get_test_step_id_by_test_case_id_reference(cloud_id, project_id, step.test_case_id_reference,
                                                       test_details, new_link, test_run_id)
    return test_details


@api.route("/<test_run_id>/evidence", methods=['POST'])
@authorization_require()
def upload_evidence(test_run_id):
    try:
        token = get_jwt_identity()
        cloud_id = token.get('cloudId')
        project_id = token.get('projectId')
        user_id = token.get('userId')
        prefix = request.args.get('prefix', "", type=str).strip()
        test_step_detail_id = request.form.get('test_step_detail_id', '')
        # validate request params
        validator_upload = UploadValidation()
        is_invalid = validator_upload.validate({"prefix": prefix})
        if is_invalid:
            return send_error(data=is_invalid, message='Please check your request params')

        try:
            file = request.files['file']
        except Exception as ex:
            return send_error(message=str(ex))
        if len(file.read()) > 100000000:
            return send_error(message="Can not upload file(s) bigger than 100MB.", is_dynamic=True)
        file_name = secure_filename(file.filename)
        real_name = file.filename
        if test_step_detail_id == '':
            file_path = "{}/{}/{}".format(prefix, test_run_id, file_name)
            if not os.path.exists(FILE_PATH + prefix + "/" + test_run_id):
                os.makedirs(FILE_PATH + prefix + "/" + test_run_id)
            if os.path.exists(os.path.join(FILE_PATH + file_path)):
                i = 1
                filename, file_extension = os.path.splitext(file_path)
                file_path = f"{filename}_{i}{file_extension}"
                while True:
                    if os.path.exists(os.path.join(FILE_PATH + file_path)):
                        i += 1
                        file_path = f"{filename}_{i}{file_extension}"
                    else:
                        break
            file_url = os.path.join(URL_SERVER + file_path)
            file.save(os.path.join(FILE_PATH + file_path))
            # Store file information such as name,path
            test_evidence = TestEvidence(
                id=str(uuid.uuid4()),
                test_run_id=test_run_id,
                url_file=file_url,
                name_file=real_name,
                created_date=get_timestamp_now())
            db.session.add(test_evidence)
            db.session.flush()
            detail = {"step": 0, "real_name": real_name}
            activity_test_run(user_id, test_run_id, detail, 15)
            db.session.commit()
        else:
            file_path = "{}/{}/{}/{}".format(prefix, test_run_id, test_step_detail_id, file_name)
            if not os.path.exists(FILE_PATH + prefix + "/" + test_run_id + "/" + test_step_detail_id):
                os.makedirs(FILE_PATH + prefix + "/" + test_run_id + "/" + test_step_detail_id)
            if os.path.exists(os.path.join(FILE_PATH + file_path)):
                i = 1
                filename, file_extension = os.path.splitext(file_path)
                file_path = f"{filename}_{i}{file_extension}"
                while True:
                    if os.path.exists(os.path.join(FILE_PATH + file_path)):
                        i += 1
                        file_path = f"{filename}_{i}{file_extension}"
                    else:
                        break
            file_url = os.path.join(URL_SERVER + file_path)
            file.save(os.path.join(FILE_PATH + file_path))
            # Store file information such as name,path
            test_evidence = TestEvidence(
                id=str(uuid.uuid4()),
                test_run_id=test_run_id,
                test_step_detail_id=test_step_detail_id,
                url_file=file_url,
                name_file=real_name,
                created_date=get_timestamp_now())
            db.session.add(test_evidence)
            db.session.flush()
            stt = stt_step_detail_id(cloud_id, project_id, test_run_id, [])
            detail = {"step": stt.index(test_step_detail_id) + 1, "real_name": real_name}
            activity_test_run(user_id, test_run_id, detail, 12)
            db.session.commit()

        dt = {
            "file_url": file_url
        }
        return send_result(data=dt, message="Add evidence success")
    except Exception as ex:
        db.session.rollback()
        return send_error(message=str(ex))


@api.route('<test_run_id>/get-evidence', methods=['POST'])
@authorization_require()
def get_evidence(test_run_id):
    try:
        token = get_jwt_identity()
        cloud_id = token.get('cloudId')
        project_id = token.get('projectId')
        req = request.get_json()
        test_step_detail_id = req.get('test_step_detail_id', '')
        search_other = request.args.get('search_other', False, type=bool)
        if test_step_detail_id == '':
            dict_evidence = {}
            # query global
            files = TestEvidence.query.filter(TestEvidence.test_run_id == test_run_id,
                                              TestEvidence.test_step_detail_id.is_(None)) \
                .order_by(asc(TestEvidence.created_date)).all()
            file_global = EvidenceSchema(many=True).dump(files)
            dict_evidence['Global'] = file_global
            if not search_other:
                test_detail_ids = stt_step_detail_id(cloud_id, project_id, test_run_id, [])
                # query - step
                for i, test_detail_id in enumerate(test_detail_ids):
                    files = TestEvidence.query.filter(TestEvidence.test_run_id == test_run_id,
                                                      TestEvidence.test_step_detail_id == test_detail_id) \
                        .order_by(asc(TestEvidence.created_date)).all()
                    files = EvidenceSchema(many=True).dump(files)
                    if len(files) > 0:
                        dict_evidence[f'Step {i + 1}'] = files
            return send_result(data=dict_evidence)
        else:
            files = TestEvidence.query.filter(TestEvidence.test_run_id == test_run_id,
                                              TestEvidence.test_step_detail_id == test_step_detail_id) \
                .order_by(asc(TestEvidence.created_date)).all()
            files = EvidenceSchema(many=True).dump(files)
            return send_result(data=files)
    except Exception as ex:
        return send_error(message=str(ex))


# lọc thứ tự step trong test run -> trả theo thứ tự
def stt_step_detail_id(cloud_id, project_id, test_run_id, ids: list):
    test_run = TestRun.query.filter(test_run_id == test_run_id).first()
    # lọc thứ tự step trong test run -> trả theo thứ tự
    test_steps = db.session.query(TestStep).filter(TestStep.project_id == project_id,
                                                   TestStep.cloud_id == cloud_id,
                                                   TestStep.test_case_id == test_run.test_case_id) \
        .order_by(asc(TestStep.index)).all()
    for test_step in test_steps:
        link = test_step.id + "/"
        if test_step.test_case_id_reference:
            result_child = get_test_step_detail_id(cloud_id, project_id, test_step.test_case_id_reference, [],
                                                   link, test_run_id)
            ids = ids + result_child
        else:
            test_step_detail = TestStepDetail.query.filter(TestStepDetail.test_step_id == test_step.id,
                                                           TestStepDetail.test_run_id == test_run_id,
                                                           TestStepDetail.link == link).first()
            data = test_step_detail.id
            ids.append(data)
    return ids


# lấy tất cả id test step trong test case call
def get_test_step_detail_id(cloud_id, project_id, test_case_id_reference, test_details: list, link: str, test_run_id):
    test_step_reference = db.session.query(TestStep.id, TestStep.cloud_id, TestStep.project_id,
                                           TestStep.test_case_id, TestStep.test_case_id_reference, TestCase.issue_key,
                                           TestStep.custom_fields) \
        .join(TestCase, TestCase.id == TestStep.test_case_id) \
        .filter(TestStep.project_id == project_id, TestStep.cloud_id == cloud_id,
                TestStep.test_case_id == test_case_id_reference).order_by(asc(TestStep.index)).all()

    for step in test_step_reference:
        new_link = link + step.id + "/"
        if step.test_case_id_reference is None:
            test_step_detail = TestStepDetail.query.filter(TestStepDetail.test_step_id == step.id,
                                                           TestStepDetail.test_run_id == test_run_id,
                                                           TestStepDetail.link == new_link).first()
            data = test_step_detail.id
            test_details.append(data)
        else:
            get_test_step_detail_id(cloud_id, project_id, step.test_case_id_reference,
                                    test_details, new_link, test_run_id)
    return test_details


@api.route('<test_run_id>/evidence', methods=['DELETE'])
@authorization_require()
def delete_evidence(test_run_id):
    try:
        token = get_jwt_identity()
        cloud_id = token.get('cloudId')
        project_id = token.get('projectId')
        user_id = token.get('userId')
        req = request.get_json()
        url_file = req.get('url_file')
        test_step_detail_id = req.get('test_step_detail_id', '')
        if test_step_detail_id == '':
            test = TestEvidence.query.filter(TestEvidence.test_run_id == test_run_id,
                                             TestEvidence.test_step_detail_id.is_(None),
                                             TestEvidence.url_file == url_file).first()
            detail = {"step": 0, "name_file": test.name_file}
            activity_test_run(user_id, test_run_id, detail, 16)
        else:
            test = TestEvidence.query.filter(TestEvidence.test_run_id == test_run_id,
                                             TestEvidence.test_step_detail_id == test_step_detail_id,
                                             TestEvidence.url_file == url_file).first()
            stt = stt_step_detail_id(cloud_id, project_id, test_run_id, [])
            detail = {"step": stt.index(test_step_detail_id) + 1, "real_name": test.name_file}
            activity_test_run(user_id, test_run_id, detail, 11)
        db.session.delete(test)
        db.session.flush()
        file_path = "app" + url_file
        if os.path.exists(os.path.join(file_path)):
            os.remove(file_path)
        db.session.commit()
        return send_result(message="Remove evidence success")
    except Exception as ex:
        db.session.rollback()
        return send_error(message=str(ex))


@api.route('/evidence-download', methods=['POST'])
@authorization_require()
def download_evidence():
    try:
        req = request.get_json()
        url_file = req.get('url_file')
        file_path = "app/" + url_file
        if not os.path.isfile(file_path):
            return send_error(message='File not found')
        try:
            file = os.path.abspath(file_path)
            return send_file(file, as_attachment=True, environ=request.environ)
        except Exception as e:
            return send_error(message='Error while downloading file: {}'.format(str(e)))
    except Exception as ex:
        return send_error(message=str(ex))


@api.route("/<test_run_id>/start", methods=['POST'])
@authorization_require()
def start_time(test_run_id):
    try:
        token = get_jwt_identity()
        cloud_id = token.get('cloudId')
        project_id = token.get('projectId')
        user_id = token.get('userId')
        test_run = TestRun.query.filter(TestRun.id == test_run_id).first()
        if test_run is None:
            return send_error(message="Not found test run")
        time_start = round(double(datetime.datetime.now().timestamp()), 3)
        timer = Timer.query.filter(Timer.test_run_id == test_run_id).first()
        if timer is None:
            timer = Timer(
                id=str(uuid.uuid4()),
                test_run_id=test_run_id,
                time_type=1,
                time_start=time_start,
                delta_time=0,
                created_date=get_timestamp_now()
            )
            db.session.add(timer)
            db.session.flush()
            detail = {"start": 0}
            activity_test_run(user_id, test_run_id, detail, 6)
        else:
            if timer.time_type == 1:
                return send_error(message="Timer is running")
            timer.time_type = 1
            timer.time_start = time_start
            db.session.flush()
            detail = {"start": timer.delta_time}
            activity_test_run(user_id, test_run_id, detail, 6)
        db.session.commit()
        return send_result(message="Oke")
    except Exception as ex:
        db.session.rollback()
        return send_error(message=str(ex))


@api.route("/<test_run_id>/pause", methods=['PUT'])
@authorization_require()
def pause_time(test_run_id):
    try:
        token = get_jwt_identity()
        cloud_id = token.get('cloudId')
        project_id = token.get('projectId')
        user_id = token.get('userId')
        test_run = TestRun.query.filter(TestRun.id == test_run_id).first()
        if test_run is None:
            return send_error(message="Not found test run")
        time_start = double(datetime.datetime.now().timestamp())
        timer = Timer.query.filter(Timer.test_run_id == test_run_id).first()
        if timer is None:
            return send_error(message="Not found")
        if timer.time_type == 2:
            return send_error(message="time stopped")
        delta_time = round(time_start - double(timer.time_start) + double(timer.delta_time), 3)
        timer.delta_time = delta_time
        timer.time_type = 2
        db.session.flush()
        detail = {"pause": delta_time}
        activity_test_run(user_id, test_run_id, detail, 7)
        db.session.commit()
        return send_result(message="oke")
    except Exception as ex:
        db.session.rollback()
        return send_error(message=str(ex))


@api.route("/<test_run_id>/reset", methods=['PUT'])
@authorization_require()
def reset_time(test_run_id):
    try:
        token = get_jwt_identity()
        cloud_id = token.get('cloudId')
        project_id = token.get('projectId')
        user_id = token.get('userId')
        test_run = TestRun.query.filter(TestRun.id == test_run_id).first()
        if test_run is None:
            return send_error(message="Not found test run")
        test_timer = Timer.query.filter(Timer.test_run_id == test_run_id).first()
        test_timer.time_type = 2
        test_timer.time_start = 0
        test_timer.delta_time = 0
        db.session.flush()
        activity_test_run(user_id, test_run_id, {}, 8)
        db.session.commit()
        return send_result(message="oke")

    except Exception as ex:
        db.session.rollback()
        return send_error(message=str(ex))


@api.route("/<test_run_id>/timer", methods=['GET'])
@authorization_require()
def get_time(test_run_id):
    try:
        token = get_jwt_identity()
        cloud_id = token.get('cloudId')
        project_id = token.get('projectId')
        test_run = TestRun.query.filter(TestRun.id == test_run_id).first()
        if test_run is None:
            return send_error(message="Not found test run")
        test_timer = Timer.query.filter(Timer.test_run_id == test_run_id).first()
        if test_timer is None:
            timer = Timer(
                id=str(uuid.uuid4()),
                test_run_id=test_run_id,
                time_type=2,
                created_date=get_timestamp_now()
            )
            db.session.add(timer)
            db.session.flush()
            db.session.commit()
        return send_result(data=TimerSchema().dump(test_timer))
    except Exception as ex:
        db.session.rollback()
        return send_error(message=str(ex))


@api.route("/<test_run_id>/activity", methods=['GET'])
@authorization_require()
def get_activity(test_run_id):
    try:
        token = get_jwt_identity()
        cloud_id = token.get('cloudId')
        project_id = token.get('projectId')
        test_activity = TestActivity.query.filter(TestActivity.test_run_id == test_run_id) \
            .order_by(desc(TestActivity.created_date)).all()
        return send_result(data=TestActivitySchema(many=True).dump(test_activity))
    except Exception as ex:
        return send_error(message=str(ex))


@api.route("/<test_run_id>/update", methods=['PUT'])
@authorization_require()
def update_test_run(test_run_id):
    try:
        token = get_jwt_identity()
        cloud_id = token.get('cloudId')
        project_id = token.get('projectId')
        user_id = token.get('userId')
        is_update = request.args.get('is_update', "", type=str)
        if is_update not in ["merge", "reset"]:
            return send_error(message="Please check your request params")
        test_run = TestRun.query.filter(TestRun.id == test_run_id).first()
        if test_run.is_updated == 0:
            return send_result(data="Nothing to update")
        if is_update == "merge":
            test_run.is_updated = 0
            db.session.flush()
            activity_test_run(user_id, test_run_id, {}, 17)
            db.session.commit()
            return send_result(message="Execution data was merged successfully")
        elif is_update == "reset":
            test_status = TestStatus.query.filter(TestStatus.project_id == project_id, TestStatus.cloud_id == cloud_id,
                                                  TestStatus.name == "TODO").first()
            test_run.is_updated = 0
            test_run.comment = None
            test_run.test_status_id = test_status.id
            db.session.query(TestStepDetail) \
                .filter_by(test_run_id=test_run_id) \
                .update({"status_id": test_status.id, "comment": None, "data": None})
            TestEvidence.query.filter(TestEvidence.test_run_id == test_run_id).delete()
            Defects.query.filter(Defects.test_run_id == test_run_id).delete()
            Timer.query.filter(Timer.test_run_id == test_run_id).delete()
            db.session.flush()
            activity_test_run(user_id, test_run_id, {}, 18)
            db.session.commit()
            return send_result(message="Execution data was reset successfully")
    except Exception as ex:
        db.session.rollback()
        return send_error(message=str(ex))


@api.route("/<test_run_id>/activity", methods=['POST'])
@authorization_require()
def post_activity_jira(test_run_id):
    try:
        token = get_jwt_identity()
        cloud_id = token.get('cloudId')
        project_id = token.get('projectId')
        user_id = token.get('userId')
        assignee_id = request.args.get('assignee_id', "", type=str)
        if assignee_id == '':
            return send_error(message="Please check your request params")
        detail = {"id": assignee_id}
        activity_test_run(user_id, test_run_id, detail, 19)
        db.session.flush()
        db.session.commit()
    except Exception as ex:
        db.session.rollback()
        return send_error(message=str(ex))

