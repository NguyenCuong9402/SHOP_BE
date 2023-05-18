import json
import os
import uuid
from operator import or_

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, create_access_token
from benedict import benedict
from sqlalchemy import asc
from werkzeug.utils import secure_filename

from app.api.v1.setting.setting_validator import UpdateMiscellaneousRequest
from app.api.v1.test_run.schema import TestRunSchema, CombineSchema
from app.enums import FILE_PATH, URL_SERVER
from app.gateway import authorization_require
from app.models import TestStep, TestCase, TestType, db, TestField, Setting, TestRun, TestExecution, \
    TestCasesTestExecutions, TestStatus, TestStepDetail, Defects, TestEvidence
from app.utils import send_result, send_error, data_preprocessing, get_timestamp_now
from app.validator import CreateTestValidator, SettingSchema, DefectsSchema, TestStepTestRunSchema, UploadValidation, \
    EvidenceSchema
from app.parser import TestFieldSchema, TestStepSchema

api = Blueprint('test_run', __name__)


@api.route("/search", methods=["POST"])
@authorization_require()
def search_test_run():
    try:
        token = get_jwt_identity()
        cloud_id = token.get('cloudId')
        project_id = token.get('projectId')

        body_request = request.get_json()

        test_case_issue_id = body_request.get('test_case_issue_id', None)
        test_execution_issue_id = body_request.get('test_execution_issue_id', None)
        test_status_ids = body_request.get('test_status_id', None)

        query = db.session.query(TestRun). \
            join(TestCase, TestCase.id == TestRun.test_case_id). \
            join(TestExecution, TestExecution.id == TestRun.test_execution_id). \
            join(TestStatus, TestStatus.id == TestRun.test_status_id)

        if test_case_issue_id:
            query = query.filter(TestCase.issue_id == test_case_issue_id, TestCase.cloud_id == cloud_id,
                                 TestCase.project_id == project_id)

        if test_execution_issue_id:
            query = query.filter(TestExecution.issue_id == test_execution_issue_id)

        if test_status_ids:
            query = query.filter(TestRun.test_status_id.in_(test_status_ids))

        test_runs = query.all()

        return send_result(data=CombineSchema(many=True).dump(test_runs), message="OK")

    except Exception as ex:
        return send_result(data='', message="OK")


@api.route("/<issue_id>/test_run", methods=["GET"])
@authorization_require()
def get_test_run(issue_id):
    try:
        token = get_jwt_identity()
        cloud_id = token.get('cloudId')
        project_id = token.get('projectId')

        # Get test case
        test_case = TestCase.query.filter(TestCase.cloud_id == cloud_id, TestCase.issue_id == issue_id,
                                          TestCase.project_id == project_id).first()

        # test_executions = test_case.test_execution.all()
        # test_execution_ids = [item.id for item in test_executions]

        test_runs = db.session.query(TestRun) \
            .join(TestExecution, TestExecution.id == TestRun.test_execution_id). \
            join(TestCase, TestExecution.test_cases). \
            filter(TestCase.issue_id == test_case.issue_id).all()

        return send_result(data='Done', message="OK")

    except Exception as ex:
        print(ex)


@api.route("/<test_issue_id>/test_execution/<test_execution_issue_id>", methods=["POST"])
@authorization_require()
def add_test_execution(test_issue_id, test_execution_issue_id):
    try:
        token = get_jwt_identity()
        cloud_id = token.get('cloudId')
        project_id = token.get('projectId')

        """
            Get test case, create new if not exist
        """
        test_case = TestCase.query.filter(TestCase.issue_id == test_issue_id,
                                          TestCase.cloud_id == cloud_id,
                                          TestExecution.project_id == project_id).first()
        if test_case is None:
            test_case = TestCase(
                id=str(uuid.uuid4()),
                issue_id=test_issue_id,
                project_id=project_id,
                cloud_id=cloud_id,
                created_date=get_timestamp_now()
            )
            db.session.add(test_case)
            db.session.flush()

        """
           Get test execution, create new if not exist
        """
        test_execution = TestExecution.query.filter(TestExecution.issue_id == test_execution_issue_id,
                                                    TestExecution.cloud_id == cloud_id,
                                                    TestExecution.project_id == project_id).first()
        if test_execution is None:
            test_execution = TestExecution(
                id=str(uuid.uuid4()),
                issue_id=test_execution_issue_id,
                project_id=project_id,
                cloud_id=cloud_id,
                created_date=get_timestamp_now()
            )
            db.session.add(test_execution)
            db.session.flush()

        """
        Generate test run
        """
        test_run = TestRun.query.filter(TestRun.test_execution_id == test_execution.id,
                                        TestRun.test_case_id == test_case.id,
                                        ).first()
        if test_run is None:
            default_status = TestStatus.query.filter(TestStatus.cloud_id == cloud_id,
                                                     TestStatus.project_id == project_id,
                                                     TestStatus.name == 'TODO').first()
            test_run = TestRun(
                id=str(uuid.uuid4()),
                project_id=project_id, cloud_id=cloud_id, test_case_id=test_case.id,
                test_execution_id=test_execution.id, activities='{}', test_steps='{}', findings='{}',
                meta_data='{}',
                issue_id=test_case.issue_id,
                created_date=get_timestamp_now(),
                test_status_id=default_status.id
            )
            db.session.add(test_run)
            db.session.flush()

        db.session.commit()
        return send_result(data='', message='Add test execution to test case successfully', show=True)
    except Exception as ex:
        db.session.rollback()


@api.route("/<test_case_id>/test_run_id", methods=["GET"])
@authorization_require()
def get_test_run_by_id(test_case_id):
    try:
        token = get_jwt_identity()

        cloud_id = token.get('cloudId')
        issue_id = 100002
        project_id = 10003
        test_run = TestRun.query.first()
        status = test_run.status
        return send_result(data='Done', message="OK")

    except Exception as ex:
        print(ex)


@api.route("/<test_run_id>/<new_name_status>", methods=["PUT"])
@authorization_require()
def change_status_test_run(test_run_id, new_name_status):
    try:
        token = get_jwt_identity()
        project_id = token.get("projectId")
        cloud_id = token.get("cloudId")
        user_id = token.get("userId")
        query = TestRun.query.filter(TestRun.id == test_run_id).first()
        if not query:
            return send_error(message="Test run is not exists")
        status = TestStatus.query.filter(TestStatus.cloud_id == cloud_id, TestStatus.project_id == project_id,
                                         TestStatus.name == new_name_status).first()
        if not status:
            return send_error(message="status is not exists")
        query.test_status_id = status.id
        db.session.flush()
        db.session.commit()
        return send_result(message="success")
    except Exception as ex:
        db.session.rollback()
        return send_error(message=str(ex))


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


@api.route("/<test_execution_issue_id>/<test_case_issue_id>/<test_step_id>/comment", methods=["POST"])
@authorization_require()
def post_comment_test_detail(test_execution_issue_id, test_case_issue_id, test_step_id):
    try:
        token = get_jwt_identity()
        cloud_id = token.get('cloudId')
        project_id = token.get('project_Id')
        req = request.get_json()
        comment = req.get('comment')
        link = req.get('link')

        test_execution = TestExecution.query.filter(TestExecution.project_id == project_id,
                                                    TestExecution.cloud_id == cloud_id,
                                                    TestExecution.issue_id == test_execution_issue_id).first()
        if test_execution is None:
            return send_error(message="not found test execution")
        test_case = TestCase.query.filter(TestCase.project_id == project_id,
                                          TestCase.cloud_id == cloud_id,
                                          TestCase.issue_id == test_case_issue_id).first()
        if test_case is None:
            return send_error(message="not found test case")
        test_run = TestRun.query.filter(TestRun.cloud_id == cloud_id, TestRun.project_id == project_id,
                                        TestRun.test_execution_id == test_execution.id,
                                        TestRun.test_case_id == test_case.id).first()
        if test_run is None:
            return send_error("Not found test run")
        test_step_detail = TestStepDetail.query.filter(TestStepDetail.test_step_id == test_step_id,
                                                       TestStepDetail.link == link,
                                                       TestStepDetail.test_run_id == test_run.id).first()
        if test_step_detail is None:
            return send_error("Not found test detail")
        test_step_detail.comment = comment
        db.session.flush()
        db.session.commit()
        return send_result(message="Comment successfully")
    except Exception as ex:
        db.session.rollback()
        return send_error(message=str(ex))


@api.route("/<test_execution_issue_id>/<test_case_issue_id>/<test_step_id>/get_comment", methods=["POST"])
@authorization_require()
def get_comment_test_detail(test_execution_issue_id, test_case_issue_id, test_step_id):
    try:
        token = get_jwt_identity()
        cloud_id = token.get('cloudId')
        project_id = token.get('project_Id')
        req = request.get_json()
        link = req.get('link')
        test_execution = TestExecution.query.filter(TestExecution.project_id == project_id,
                                                    TestExecution.cloud_id == cloud_id,
                                                    TestExecution.issue_id == test_execution_issue_id).first()
        if test_execution is None:
            return send_error(message="not found test execution")
        test_case = TestCase.query.filter(TestCase.project_id == project_id,
                                          TestCase.cloud_id == cloud_id,
                                          TestCase.issue_id == test_case_issue_id).first()
        if test_case is None:
            return send_error(message="not found test case")
        test_run = TestRun.query.filter(TestRun.cloud_id == cloud_id, TestRun.project_id == project_id,
                                        TestRun.test_execution_id == test_execution.id,
                                        TestRun.test_case_id == test_case.id).first()
        if test_run is None:
            return send_error("Not found test run")
        test_step_detail = TestStepDetail.query.filter(TestStepDetail.test_step_id == test_step_id,
                                                       TestStepDetail.link == link,
                                                       TestStepDetail.test_run_id == test_run.id).first()
        if test_step_detail is None:
            return send_error("Not found test detail")
        comment = test_step_detail.comment
        return send_result(data=comment)
    except Exception as ex:
        db.session.rollback()
        return send_error(message=str(ex))


@api.route("/<test_run_id>/<test_step_detail_id>/defect", methods=["POST"])
@authorization_require()
def post_defect(test_run_id, test_step_detail_id):
    try:
        token = get_jwt_identity()
        cloud_id = token.get('cloudId')
        project_id = token.get('project_Id')
        req = request.get_json()
        issue_id = req.get('issue_id')
        issue_key = req.get('issue_key')
        type_key = req.get('type_key')
        test_run = TestRun.query.filter(TestRun.cloud_id == cloud_id, TestRun.project_id == project_id,
                                        TestRun.id == test_run_id).first()
        if test_run is None:
            return send_error("Not found test run")
        # 1 : test case  2: test set  3:test execution
        if type_key == 1:
            test_case = TestCase.query.filter(TestCase.cloud_id == cloud_id, TestCase.project_id == project_id,
                                              TestCase.issue_id == issue_id, TestCase.issue_key == issue_key).first()
            if test_case is None:
                test_case = TestCase(
                    test_case=TestCase(
                        id=str(uuid.uuid4()),
                        issue_id=issue_id,
                        issue_key=issue_key,
                        project_id=project_id,
                        cloud_id=cloud_id,
                        created_date=get_timestamp_now()
                    )
                )
                db.session.add(test_case)
                db.session.flush()
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
        db.session.commit()
        return send_result(message="Successfully")
    except Exception as ex:
        db.session.rollback()
        return send_error(message=str(ex))


@api.route("/<test_run_id>/<test_step_detail_id>/defect", methods=["GET"])
@authorization_require()
def get_defect(test_run_id, test_step_detail_id):
    try:
        token = get_jwt_identity()
        cloud_id = token.get('cloudId')
        project_id = token.get('project_Id')
        test_run = TestRun.query.filter(TestRun.cloud_id == cloud_id, TestRun.project_id == project_id,
                                        TestRun.id == test_run_id).first()
        if test_run is None:
            return send_error("Not found test run")
        test_detail = TestStepDetail.query.filter(TestStepDetail.id == test_step_detail_id,
                                                  TestStepDetail.test_run_id == test_run_id).first()
        if test_detail is None:
            return send_error("Not found test detail")
        defects = Defects.query.filter(Defects.test_run_id == test_run_id,
                                       Defects.test_step_detail_id == test_step_detail_id)\
            .over(asc(Defects.created_date)).all()
        return send_result(data=DefectsSchema(many=True).dump(defects))
    except Exception as ex:
        return send_error(message=str(ex))


@api.route("/<test_run_id>/<test_step_detail_id>/defect", methods=["DELETE"])
@authorization_require()
def delete_defect(test_run_id, test_step_detail_id):
    try:
        token = get_jwt_identity()
        cloud_id = token.get('cloudId')
        project_id = token.get('project_Id')
        req = request.get_json()
        issue_id = req.get('issue_id')
        issue_key = req.get('issue_key')
        test_run = TestRun.query.filter(TestRun.cloud_id == cloud_id, TestRun.project_id == project_id,
                                        TestRun.id == test_run_id).first()
        if test_run is None:
            return send_error("Not found test run")
        test_detail = TestStepDetail.query.filter(TestStepDetail.id == test_step_detail_id,
                                                  TestStepDetail.test_run_id == test_run_id).first()
        if test_detail is None:
            return send_error("Not found test detail")
        Defects.query.filter(Defects.test_run_id == test_run_id, Defects.test_issue_id == issue_id,
                             Defects.test_step_detail_id == test_step_detail_id,
                             Defects.test_issue_key == issue_key).delete()
        db.session.flush()
        db.session.commit()
        return send_result(message="Successfully")
    except Exception as ex:
        db.session.rollback()
        return send_error(message=str(ex))


@api.route("/<issue_id>/<test_issue_id>/test_run", methods=["GET"])
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
                                                   TestStep.test_case_id == test_case.id).order_by(asc(TestStep.index))\
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
                                           TestStep.custom_fields)\
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


@api.route("/<test_run_id>/<test_step_detail_id>", methods=['POST'])
@jwt_required()
def upload_evidence(test_run_id, test_step_detail_id):
    token = get_jwt_identity()
    cloud_id = token.get('cloudId')
    project_id = token.get('projectId')
    prefix = request.args.get('prefix', "", type=str).strip()
    # validate request params
    validator_upload = UploadValidation()
    is_invalid = validator_upload.validate({"prefix": prefix})
    if is_invalid:
        return send_error(data=is_invalid, message='Please check your request params')

    try:
        file = request.files['file']
    except Exception as ex:
        return send_error(message=str(ex))

    file_name = secure_filename(file.filename)
    real_name = file.filename
    file_path = "{}/{}/{}/{}".format(prefix, test_run_id, test_step_detail_id, file_name)

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
    try:
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
        db.session.commit()
    except Exception as ex:
        db.session.rollback()
        return send_error(message=str(ex))
    dt = {
        "file_url": file_url
    }
    return send_result(data=dt, message="Ok")


@api.route('<test_run_id>/<test_step_detail_id>', methods=['GET'])
def get_evidence(test_run_id, test_step_detail_id):
    url_files = request.args.getlist('url_files[]', None)
    files = TestEvidence.query.filter(TestEvidence.test_run_id == test_run_id,
                                      TestEvidence.test_step_detail_id == test_step_detail_id,
                                      TestEvidence.url_file.in_(url_files)).all()
    files = EvidenceSchema(many=True).dump(files)
    return send_result(data=files, message="ok")


@api.route('<test_run_id>/<test_step_detail_id>', methods=['DELETE'])
def delete_evidence(test_run_id, test_step_detail_id):
    try:
        token = get_jwt_identity()
        cloud_id = token.get('cloudId')
        project_id = token.get('projectId')
        req = request.get_json()
        url_file = req.get('url_file')
        TestEvidence.query.filter(TestEvidence.test_run_id == test_run_id,
                                  TestEvidence.test_step_detail_id == test_step_detail_id,
                                  TestEvidence.url_file == url_file).delete()
        os.remove(url_file)
        db.session.flush()
        db.session.commit()
        return send_result(message="Ok")
    except Exception as ex:
        db.session.rollback()
        return send_error(message=str(ex))
