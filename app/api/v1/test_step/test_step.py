import json
import os
import shutil
import uuid
from operator import or_
from flask import Blueprint, request
from flask_jwt_extended import get_jwt_identity
from sqlalchemy import func, asc, and_, desc

from app.api.v1.history_test import save_history_test_step
from app.api.v1.test_execution.test_execution import add_test_step_id_by_test_case_id
from app.api.v1.test_type.test_type import get_test_type_default
from app.enums import FILE_PATH
from app.gateway import authorization_require
from app.models import TestStep, db, TestStepField, TestRunField, TestCase, TestStepDetail, HistoryTest, TestRun, \
    TestExecution, TestCasesTestExecutions, TestStatus, Attachment, TestEvidence
from app.parser import TestStepSchema
from app.utils import send_result, send_error, data_preprocessing, get_timestamp_now
from app.api.v1.test_step_field.test_step_field import DEFAULT_DATA

api = Blueprint('test_step', __name__)


@api.route("/<issue_id>", methods=["POST"])
@authorization_require()
def add_test_step(issue_id):
    try:
        token = get_jwt_identity()
        cloud_id = token.get('cloudId')
        project_id = token.get('projectId')
        user_id = token.get('userId')
        issue_key = token.get('issue_key')
        test_case = TestCase.query.filter(TestCase.issue_id == issue_id, TestCase.project_id == project_id,
                                          TestCase.cloud_id == cloud_id).first()
        test_type_id = get_test_type_default(cloud_id, project_id)
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
        try:
            json_req = request.get_json()
        except Exception as ex:
            return send_error(message="Request Body incorrect json format: " + str(ex), code=442)
        # Strip body request
        body_request = {}
        for key, value in json_req.items():
            if isinstance(value, str):
                body_request.setdefault(key, value.strip())
            else:
                body_request.setdefault(key, value)
        test_step_fields = db.session.query(TestStepField).filter(
            or_(TestStepField.project_id == project_id, TestStepField.project_key == project_id),
            TestStepField.cloud_id == cloud_id).order_by(TestStepField.index.asc())
        test_step_fields_count = test_step_fields.count()
        if test_step_fields_count == 0:
            for test_step_field in DEFAULT_DATA:
                test_step_field = TestStepField(
                    id=str(uuid.uuid4()),
                    name=test_step_field['name'],
                    description=test_step_field['description'],
                    type=test_step_field['type'],
                    is_required=test_step_field['is_required'],
                    is_disabled=test_step_field['is_disabled'],
                    is_native=test_step_field['is_native'],
                    index=test_step_field['index'],
                    type_values=test_step_field['type_values'],
                    project_id=project_id,
                    cloud_id=cloud_id,
                )
                db.session.add(test_step_field)
                db.session.flush()
            test_step_fields_count = 3
        if len(body_request.get('custom_fields')) > (test_step_fields_count - 3):
            return send_error(message='custom fields failed')
        count_index = TestStep.query.filter(TestStep.test_case_id == test_case.id).count()
        test_step_id = str(uuid.uuid4())
        test_step = TestStep(
            id=test_step_id,
            cloud_id=cloud_id,
            project_id=project_id,
            action=body_request.get('action'),
            data=body_request.get('data'),
            result=body_request.get('result'),
            custom_fields=body_request.get('custom_fields'),
            index=count_index + 1,
            test_case_id=test_case.id,
            created_date=get_timestamp_now()
        )
        db.session.add(test_step)
        db.session.flush()
        # check test run
        test_runs = TestRun.query.filter(TestRun.project_id == project_id, TestRun.cloud_id == cloud_id,
                                         TestRun.test_case_id == test_case.id).all()
        status = TestStatus.query.filter(TestStatus.cloud_id == cloud_id, TestStatus.project_id == project_id,
                                         TestStatus.name == 'TODO').first()

        for test_run in test_runs:
            test_run.is_updated = 1
            test_step_detail = TestStepDetail(
                id=str(uuid.uuid4()),
                test_step_id=test_step_id,
                status_id=status.id,
                test_run_id=test_run.id,
                created_date=get_timestamp_now(),
                link=test_step.id+"/"
            )
            db.session.add(test_step_detail)
            db.session.flush()
        # Tạo test details cho test case khác call test case này
        add_test_detail_for_test_case_call(cloud_id, project_id, test_case.id, status.id, test_step.id + "/", test_step.id)
        detail_of_action = {}
        # field not native
        field_name = []
        for item in test_step_fields:
            if item.is_native == 0:
                field_name.append(item.name)
        # create detail of action
        detail_of_action['Action'] = test_step.action
        detail_of_action['Data'] = test_step.data
        detail_of_action['Expected Result'] = test_step.result
        if len(field_name) >= len(test_step.custom_fields):
            for i, name in enumerate(test_step.custom_fields):
                detail_of_action[field_name[i]] = name
        else:
            return send_error("check your request")
        # Save history
        save_history_test_step(test_case.id, user_id, 1, 2, detail_of_action, [count_index + 1])
        db.session.commit()
        return send_result(data='add success')
    except Exception as ex:
        db.session.rollback()
        return send_error(message=str(ex))


def add_test_detail_for_test_case_call(cloud_id: str, project_id: str, test_case_id_reference: str,
                                       status_id: str, link: str, test_step_id: str):
    try:
        stack = [(test_case_id_reference, link)]  # Khởi tạo stack và thêm (test_case_id_reference, link) vào stack
        while len(stack) > 0:
            current_test_case_id, current_link = stack.pop()  # Lấy phần tử cuối cùng từ stack
            test_steps = TestStep.query.filter(TestStep.cloud_id == cloud_id, TestStep.project_id == project_id,
                                               TestStep.test_case_id_reference == current_test_case_id).all()
            for test_step in test_steps:
                new_link = test_step.id + "/" + current_link
                test_runs = TestRun.query.filter(TestRun.cloud_id == cloud_id,
                                                 TestRun.project_id == project_id,
                                                 TestRun.test_case_id == test_step.test_case_id).all()
                for test_run in test_runs:
                    test_run.is_updated = 1
                    test_step_detail = TestStepDetail(
                        id=str(uuid.uuid4()),
                        test_step_id=test_step_id,
                        status_id=status_id,
                        test_run_id=test_run.id,
                        created_date=get_timestamp_now(),
                        link=new_link
                    )
                    db.session.add(test_step_detail)
                    db.session.flush()
                stack.append((test_step.test_case_id, new_link))  # Thêm (test_case_id liên quan, new_link) vào stack
    except Exception as ex:
        return send_error(message=str(ex))


@api.route("/<issue_id>/<test_step_id>", methods=["DELETE"])
@authorization_require()
def remove_test_step(test_step_id, issue_id):
    try:
        token = get_jwt_identity()
        cloud_id = token.get('cloudId')
        project_id = token.get('projectId')
        user_id = token.get('userId')
        test_case = TestCase.query.filter(TestCase.issue_id == issue_id, TestCase.project_id == project_id,
                                          TestCase.cloud_id == cloud_id).first()
        test_step = TestStep.query.filter(TestStep.id == test_step_id).first()
        if test_step is None:
            return send_error(
                message="Test Step is not exist",
                code=200, show=False, is_dynamic=True)
        # update test_run.is_update = 1 => merge/reset
        test_case_ids = get_test_case_id(cloud_id, project_id, test_case.id, {test_case.id})
        for test_case_id in test_case_ids:
            db.session.query(TestRun).filter(TestRun.project_id == project_id, TestRun.cloud_id == cloud_id,
                                             TestRun.test_case_id == test_case_id).update({"is_updated": 1})
            db.session.flush()
        index = test_step.index
        # create detail_of_action
        detail_of_action = {}
        if test_step.test_case_id_reference is None:
            test_step_fields = db.session.query(TestStepField).filter(
                or_(TestStepField.project_id == project_id, TestStepField.project_key == project_id),
                TestStepField.cloud_id == cloud_id).order_by(TestStepField.index.asc())
            field_name = []
            for item in test_step_fields:
                if item.is_native == 0:
                    field_name.append(item.name)
            detail_of_action['Action'] = test_step.action
            detail_of_action['Data'] = test_step.data
            detail_of_action['Expected Result'] = test_step.result
            if len(field_name) >= len(test_step.custom_fields):
                for i, name in enumerate(test_step.custom_fields):
                    detail_of_action[field_name[i]] = name
            else:
                for i, name in enumerate(field_name):
                    detail_of_action[name] = test_step.custom_fields[i]
            # Xóa file trong test step của test detail
            files = Attachment.query.filter(Attachment.cloud_id == cloud_id, Attachment.project_id,
                                            Attachment.test_step_id == test_step_id).all()
            for file in files:
                file_path = "{}/{}".format("app", file.attached_file)
                if os.path.exists(os.path.join(file_path)):
                    os.remove(file_path)
            Attachment.query.filter(Attachment.cloud_id == cloud_id, Attachment.project_id,
                                    Attachment.test_step_id == test_step_id).delete()
            db.session.flush()
            # xóa thư mục trong file (Evidence) 1 test step - nhiều => cặp test run id + test step detail
            paths = TestStepDetail.query.filter(TestStepDetail.test_step_id == test_step_id).all()
            for path in paths:
                folder_path = "{}/{}/{}".format("test-run", path.test_run_id, path.id)
                if os.path.isdir(FILE_PATH+folder_path):
                    try:
                        shutil.rmtree(FILE_PATH+folder_path)
                    except Exception as ex:
                        return send_error(message=str(ex))

                TestEvidence.query.filter(TestEvidence.test_run_id == path.test_run_id,
                                          TestEvidence.test_step_detail_id == path.id).delete()

                db.session.query(TestRun).filter(TestRun.project_id == project_id, TestRun.cloud_id == cloud_id,
                                                 TestRun.id == path.test_run_id)\
                    .update({"is_updated": 1})
                db.session.flush()
            # delete test_step
            TestStepDetail.query.filter(TestStepDetail.test_step_id == test_step_id).delete()
            db.session.flush()
            # Save history
            save_history_test_step(test_case.id, user_id, 2, 2, detail_of_action, [index])
        else:
            test_case_reference = TestCase.query.filter(TestCase.id == test_step.test_case_id_reference,
                                                        TestCase.cloud_id == cloud_id,
                                                        TestCase.project_id == project_id).first()
            detail_of_action["Call test"]: test_case_reference.issue_key
            # delete test_step_detail => tìm link => xóa theo link
            # link test case call
            links = get_link_detail_by_test_case_id_reference(cloud_id=cloud_id, project_id=project_id,
                                                              test_case_id=test_case_reference.id, link_details=[],
                                                              link=test_step.id + "/")
            # link test case khác call test case
            for link in links:
                links = links + get_link_detail_for_test_case_call(cloud_id, project_id,
                                                                   test_step.test_case_id, [], link)
            # xoa file Evidence
            paths = TestStepDetail.query.filter(TestStepDetail.link.in_(links)).all()
            for path in paths:
                folder_path = "{}/{}/{}".format("test-run", path.test_run_id, path.id)
                if os.path.isdir(FILE_PATH + folder_path):
                    try:
                        shutil.rmtree(FILE_PATH + folder_path)
                    except Exception as ex:
                        return send_error(message=str(ex))
                TestEvidence.query.filter(TestEvidence.test_run_id == path.test_run_id,
                                          TestEvidence.test_step_detail_id == path.id).delete()
                db.session.flush()

                db.session.query(TestRun).filter(TestRun.project_id == project_id, TestRun.cloud_id == cloud_id,
                                                 TestRun.id == path.test_run_id) \
                    .update({"is_updated": 1})
                db.session.flush()

            db.session.flush()
            TestStepDetail.query.filter(TestStepDetail.link.in_(links)).delete()
            db.session.flush()
            save_history_test_step(test_case.id, user_id, 6, 2, detail_of_action, [index])

        TestStep.query.filter(TestStep.test_case_id == test_case.id).filter(TestStep.index > test_step.index) \
            .update(dict(index=TestStep.index - 1))
        db.session.delete(test_step)
        db.session.flush()
        db.session.commit()
        return send_result(data="", message="Test step removed successfully", code=200, show=True)
    except Exception as ex:
        db.session.rollback()
        return send_error(data='', message=str(ex))


def get_link_detail_for_test_case_call(cloud_id: str, project_id: str, test_case_id_reference: str,
                                       link_details: list, link: str):
    try:
        stack = [(test_case_id_reference, link)]  # Khởi tạo stack và thêm (test_case_id_reference, link) vào stack
        while len(stack) > 0:
            current_test_case_id, current_link = stack.pop()  # Lấy phần tử cuối cùng từ stack
            test_steps = TestStep.query.filter(TestStep.cloud_id == cloud_id, TestStep.project_id == project_id,
                                               TestStep.test_case_id_reference == current_test_case_id).all()
            for test_step in test_steps:
                new_link = test_step.id + "/" + current_link
                stack.append((test_step.test_case_id, new_link))  # Thêm (test_case_id liên quan, new_link) vào stack
                link_details.append(new_link)
        return link_details
    except Exception as ex:
        return send_error(message=str(ex))


@api.route("/<issue_id>", methods=["PUT"])
@authorization_require()
def change_rank_test_step(issue_id):
    try:
        token = get_jwt_identity()
        cloud_id = token.get('cloudId')
        project_id = token.get('projectId')
        user_id = token.get('userId')
        test_case = TestCase.query.filter(TestCase.project_id == project_id, TestCase.cloud_id,
                                          TestCase.issue_id == issue_id).first()
        query = TestStep.query.filter(or_(TestStep.project_id == project_id, TestStep.project_key == project_id),
                                      TestStep.cloud_id == cloud_id, TestStep.test_case_id == test_case.id).all()
        if query is None:
            return send_error(message='TEST STEP DOES NOT EXIST', status=404, show=False, is_dynamic=True)

        json_req = request.get_json()
        index_drag = json_req['index_drag']
        index_drop = json_req['index_drop']
        index_max = db.session.query(TestStep).filter(
            or_(TestStep.project_id == project_id, TestStep.project_key == project_id),
            TestStep.cloud_id == cloud_id, TestStep.test_case_id == test_case.id).count()
        # vị trí drag to drop
        index_drag_to_drop = TestStep.query.filter(
            or_(TestStep.project_id == project_id, TestStep.project_key == project_id), TestStep.cloud_id == cloud_id,
                TestStep.test_case_id == test_case.id).filter(
            TestStep.index == index_drag).first()
        if index_drag > index_drop:
            if index_drop < 1:
                return send_error(message=f'Must be a value between 1 and {index_max}', status=404, show=False,
                                  is_dynamic=True)
            TestStep.query.filter(or_(TestStep.project_id == project_id, TestStep.project_key == project_id),
                                  TestStep.cloud_id == cloud_id, TestStep.test_case_id == test_case.id) \
                .filter(TestStep.index > index_drop - 1, TestStep.index < index_drag) \
                .update(dict(index=TestStep.index + 1))
            index_drag_to_drop.index = index_drop
            db.session.flush()
        else:
            if index_drop > index_max:
                return send_error(message=f'Must be a value between 1 and {index_max}', status=404,
                                  show=False, is_dynamic=True)
            TestStep.query.filter(or_(TestStep.project_id == project_id, TestStep.project_key == project_id),
                                  TestStep.cloud_id == cloud_id, TestStep.test_case_id == test_case.id) \
                .filter(TestStep.index < index_drop + 1, TestStep.index > index_drag) \
                .update(dict(index=TestStep.index - 1))
            index_drag_to_drop.index = index_drop
            db.session.flush()
        # update test_run.is_update = 1 => merge/reset
        test_case_ids = get_test_case_id(cloud_id, project_id, test_case.id, {test_case.id})
        for test_case_id in test_case_ids:
            db.session.query(TestRun).filter(TestRun.project_id == project_id, TestRun.cloud_id == cloud_id,
                                             TestRun.test_case_id == test_case_id).update({"is_updated": 1})
            db.session.flush()
        # Save history
        save_history_test_step(test_case.id, user_id, 3, 2, {}, [index_drag, index_drop])
        db.session.commit()
        return send_result(data="", message="success", code=200, show=True)
    except Exception as ex:
        db.session.rollback()
        return send_error(data='', message=str(ex))


@api.route("/<issue_id>/call/<issue_id_reference>", methods=["POST"])
@authorization_require()
def call_test_case(issue_id, issue_id_reference):
    try:
        token = get_jwt_identity()
        cloud_id = token.get('cloudId')
        project_id = token.get('projectId')
        user_id = token.get('userId')
        issue_key = token.get('issue_key')
        test_case = TestCase.query.filter(TestCase.issue_id == issue_id, TestCase.project_id == project_id,
                                          TestCase.cloud_id == cloud_id).first()
        test_case_reference = TestCase.query.filter(TestCase.issue_id == issue_id_reference,
                                                    TestCase.project_id == project_id,
                                                    TestCase.cloud_id == cloud_id).first()
        test_type_id = get_test_type_default(cloud_id, project_id)
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
        if test_case_reference is None:
            return send_error(message="Call test case reference fail", code=200, show=False, is_dynamic=True)
        # tìm test case id là reference
        check_up = get_test_case_id(cloud_id, project_id, test_case.id, {test_case.id})
        # test case refence là  test case id
        check_down = get_test_case_reference(cloud_id, project_id, test_case_reference.id, {test_case_reference.id})
        if len(check_up & check_down) > 0:
            return send_error(message="not allowed to call because test was called called test", code=200,
                              is_dynamic=True)
        count_index = TestStep.query.filter(TestStep.test_case_id == test_case.id).count()
        test_step = TestStep(
            id=str(uuid.uuid4()),
            cloud_id=cloud_id,
            project_id=project_id,
            index=count_index + 1,
            test_case_id=test_case.id,
            test_case_id_reference=test_case_reference.id,
            created_date=get_timestamp_now()
        )
        db.session.add(test_step)
        db.session.flush()
        # check test run
        test_runs = TestRun.query.filter(TestRun.project_id == project_id, TestRun.cloud_id == cloud_id,
                                         TestRun.test_case_id == test_case.id).all()
        status = TestStatus.query.filter(TestStatus.cloud_id == cloud_id, TestStatus.project_id == project_id,
                                         TestStatus.name == 'TODO').first()
        # Add test details những test run tạo bởi test case id call
        for test_run in test_runs:
            add_test_step_id_by_test_case_id(cloud_id, project_id, test_case_reference.id,
                                             test_run.id, status.id,  test_step.id + "/")
        # Add test details những test run tạo bởi test case có  test case id call là reference
        links = get_link_detail_by_test_case_id_reference(cloud_id=cloud_id, project_id=project_id,
                                                          test_case_id=test_case_reference.id, link_details=[],
                                                          link=test_step.id + "/")
        for link in links:
            add_test_detail_for_test_case_call(cloud_id=cloud_id, project_id=project_id,
                                               test_case_id_reference=test_case.id, status_id=status.id, link=link,
                                               test_step_id=test_step.id)
        # update test_run.is_update =1 -> merge/reset
        db.session.query(TestRun).filter(TestRun.project_id == project_id, TestRun.cloud_id == cloud_id,
                                         TestRun.test_case_id.in_(check_up)).update({"is_updated": 1})
        db.session.flush()
        # Create detail_of_action and Save history
        detail_of_action = {"Call test": test_case_reference.issue_key}
        save_history_test_step(test_case.id, user_id, 5, 2, detail_of_action, [test_step.index + 1])
        db.session.commit()
        return send_result(data='Call success', show=True)
    except Exception as ex:
        db.session.rollback()
        return send_error(data='', message=str(ex))


# Get link (test step detail)
def get_link_detail_by_test_case_id_reference(cloud_id: str, project_id: str, test_case_id: str,
                                              link_details: list, link: str):
    stack = [(test_case_id, link)]
    while stack:
        test_case_id, cur_link = stack.pop()
        test_steps = TestStep.query.filter(TestStep.project_id == project_id, TestStep.cloud_id == cloud_id,
                                           TestStep.test_case_id == test_case_id)\
            .order_by(asc(TestStep.index))
        for step in test_steps:
            new_link = cur_link + step.id + "/"
            if step.test_case_id_reference is None:
                data = new_link
                link_details.append(data)
            else:
                stack.append((step.test_case_id_reference, new_link))
    return link_details


@api.route("/<issue_id>/<test_step_id>", methods=["POST"])
@authorization_require()
def clone_test_step(issue_id, test_step_id):
    try:
        token = get_jwt_identity()
        cloud_id = token.get('cloudId')
        project_id = token.get('projectId')
        user_id = token.get('userId')
        test_case = TestCase.query.filter(TestCase.issue_id == issue_id, TestCase.project_id == project_id,
                                          TestCase.cloud_id == cloud_id).first()
        test_step = TestStep.query.filter(TestStep.test_case_id == test_case.id, TestStep.id == test_step_id).first()
        if test_step is None:
            return send_error(
                message="Test Step is not exist", code=200,
                show=False, is_dynamic=True)
        # Sắp xếp lại index khi clone
        TestStep.query.filter(TestStep.test_case_id == test_case.id) \
            .filter(TestStep.index > test_step.index) \
            .update(dict(index=TestStep.index + 1))
        db.session.flush()
        # Create new test step
        clone_test_step_id = str(uuid.uuid4())
        test_step_clone = TestStep(
            id=clone_test_step_id,
            cloud_id=cloud_id,
            project_id=project_id,
            action=test_step.action,
            data=test_step.data,
            result=test_step.result,
            custom_fields=test_step.custom_fields,
            index=test_step.index + 1,
            test_case_id=test_case.id,
            created_date=get_timestamp_now()
        )
        db.session.add(test_step_clone)
        db.session.flush()
        test_step_fields = db.session.query(TestStepField).filter(
            or_(TestStepField.project_id == project_id, TestStepField.project_key == project_id),
            TestStepField.cloud_id == cloud_id).order_by(TestStepField.index.asc())
        # check test run
        test_runs = TestRun.query.filter(TestRun.project_id == project_id, TestRun.cloud_id == cloud_id,
                                         TestRun.test_case_id == test_case.id).all()
        status = TestStatus.query.filter(TestStatus.cloud_id == cloud_id, TestStatus.project_id == project_id,
                                         TestStatus.name == 'TODO').first()
        for test_run in test_runs:
            test_run.is_updated = 1
            test_step_detail = TestStepDetail(
                id=str(uuid.uuid4()),
                test_step_id=test_step_id,
                status_id=status.id,
                test_run_id=test_run.id,
                created_date=get_timestamp_now(),
                link=test_step.id + "/"
            )
            db.session.add(test_step_detail)
            db.session.flush()
        # Tạo test details cho test case khác call test case này
        add_test_detail_for_test_case_call(cloud_id, project_id, test_case.id, status.id, test_step.id + "/",
                                           test_step.id)
        db.session.commit()
        # Create detail_of_action and Save history
        detail_of_action = {}
        field_name = []
        for item in test_step_fields:
            if item.is_native == 0:
                field_name.append(item.name)
        detail_of_action['Action'] = test_step.action
        detail_of_action['Data'] = test_step.data
        detail_of_action['Expected Result'] = test_step.result
        if len(field_name) >= len(test_step.custom_fields):
            for i, name in enumerate(test_step.custom_fields):
                detail_of_action[field_name[i]] = name
        else:
            for i, name in enumerate(field_name):
                detail_of_action[name] = test_step.custom_fields[i]
        save_history_test_step(test_case.id, user_id, 4, 2, detail_of_action, [test_step.index + 1])
        db.session.commit()
        return send_result(data='', message="Step clone successfully",
                           show=True)
    except Exception as ex:
        db.session.rollback()
        return send_error(data='', message="Something was wrong!")


@api.route("/<issue_id>/<test_step_id>", methods=["PUT"])
@authorization_require()
def update_test_step(issue_id, test_step_id):
    try:
        token = get_jwt_identity()
        cloud_id = token.get('cloudId')
        project_id = token.get('projectId')
        user_id = token.get('userId')
        issue_key = token.get('issue_key')
        test_case = TestCase.query.filter(TestCase.issue_id == issue_id, TestCase.project_id == project_id,
                                          TestCase.cloud_id == cloud_id).first()
        test_type_id = get_test_type_default(cloud_id, project_id)

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
        try:
            json_req = request.get_json()
        except Exception as ex:
            return send_error(message="Request Body incorrect json format: " + str(ex), code=442)
        # Strip body request
        body_request = {}
        detail_of_action = {}
        for key, value in json_req.items():
            if isinstance(value, str):
                body_request.setdefault(key, value.strip())
            else:
                body_request.setdefault(key, value)
        test_step = TestStep.query.filter(TestStep.test_case_id == test_case.id, TestStep.id == test_step_id).first()
        if test_step is None:
            return send_error(
                message="Test Step is not exist", code=200,
                show=False)
        test_step_fields = db.session.query(TestStepField).filter(
            or_(TestStepField.project_id == project_id, TestStepField.project_key == project_id),
            TestStepField.cloud_id == cloud_id).order_by(TestStepField.index.asc())
        field_name = []
        for item in test_step_fields:
            if item.is_native == 0:
                field_name.append(item.name)
        # create detail of action old step
        detail_of_action["old"] = {}
        detail_of_action["old"]['Action'] = test_step.action
        detail_of_action["old"]['Data'] = test_step.data
        detail_of_action["old"]['Expected Result'] = test_step.result
        if len(field_name) >= len(test_step.custom_fields):
            for i, name in enumerate(test_step.custom_fields):
                detail_of_action["old"][field_name[i]] = name
        else:
            for i, name in enumerate(field_name):
                detail_of_action[name] = test_step.custom_fields[i]
        # update test step
        test_step.action = body_request.get('action'),
        test_step.data = body_request.get('data'),
        test_step.result = body_request.get('result'),
        test_step.custom_fields = body_request.get('custom_fields')
        db.session.flush()
        # update test_run.is_update = 1 => merge/reset
        test_case_ids = get_test_case_id(cloud_id, project_id, test_case.id, {test_case.id})
        db.session.query(TestRun).filter(TestRun.project_id == project_id, TestRun.cloud_id == cloud_id,
                                         TestRun.test_case_id.in_(test_case_ids)).update({"is_updated": 1})
        db.session.flush()

        # Create detail_of_action new data and Save history
        detail_of_action["new"] = {}
        detail_of_action["new"]['Action'] = body_request.get('action')
        detail_of_action["new"]['Data'] = body_request.get('data')
        detail_of_action["new"]['Expected Result'] = body_request.get('result')
        custom_fields = body_request.get('custom_fields', [])
        if len(field_name) >= len(custom_fields):
            for i, name in enumerate(custom_fields):
                detail_of_action["new"][field_name[i]] = name
        else:
            return send_error("check your request")
        save_history_test_step(test_case.id, user_id, 4, 2, detail_of_action, [test_step.index])
        db.session.commit()
        return send_result(message=" Update successfully")
    except Exception as ex:
        db.session.rollback()
        return send_error(message=str(ex))


def get_test_case_id(cloud_id: str, project_id: str, test_case_id: str, set_id: set):
    stack = [test_case_id]
    while True:
        if not stack:
            break
        current_test_id = stack.pop()
        test_step_call_test_case_id = TestStep.query.filter(TestStep.cloud_id == cloud_id,
                                                            TestStep.project_id == project_id,
                                                            TestStep.test_case_id_reference == current_test_id).all()
        for test_step in test_step_call_test_case_id:
            set_id.add(test_step.test_case_id)
            stack.append(test_step.test_case_id)
    return set_id


def get_test_case_reference(cloud_id: str, project_id: str, test_case_id_reference: str, set_id: set):
    stack = [test_case_id_reference]
    while True:
        if not stack:
            break
        current_test_id = stack.pop()
        test_step_test_case_id_call = TestStep.query.filter(TestStep.cloud_id == cloud_id,
                                                            TestStep.project_id == project_id,
                                                            TestStep.test_case_id == current_test_id).all()
        for test_step in test_step_test_case_id_call:
            set_id.add(test_step.test_case_id_reference)
            stack.append(test_step.test_case_id_reference)
    return set_id
