import json
import uuid
from operator import or_
from flask import Blueprint, request
from flask_jwt_extended import get_jwt_identity
from sqlalchemy import func, asc, and_

from app.api.v1.history_test import save_history_test_step
from app.api.v1.test_execution.test_execution import add_test_step_id_by_test_case_id
from app.gateway import authorization_require
from app.models import TestStep, db, TestStepField, TestRunField, TestCase, TestStepDetail, HistoryTest, TestRun, \
    TestExecution, TestCasesTestExecutions, TestStatus
from app.parser import TestStepSchema
from app.utils import send_result, send_error, data_preprocessing, get_timestamp_now
from app.api.v1.test_step_field.test_step_field import DEFAULT_DATA

api = Blueprint('test_step', __name__)


@api.route("/<test_case_id>", methods=["POST"])
@authorization_require()
def add_test_step(test_case_id):
    try:
        token = get_jwt_identity()
        cloud_id = token.get('cloudId')
        project_id = token.get('projectId')
        user_id = token.get('userId')
        test_case = TestCase.query.filter(TestCase.id == test_case_id).first()
        if test_case is None:
            return send_error(
                message="Test Case is not Exist", code=200,
                show=False)
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
        count_index = TestStep.query.filter(TestStep.test_case_id == test_case_id).count()
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
            test_case_id=test_case_id,
            created_date=get_timestamp_now()
        )
        db.session.add(test_step)
        db.session.flush()
        # check test run
        test_execution = TestCasesTestExecutions.query.filter(TestCasesTestExecutions.test_case_id
                                                              == test_case_id).all()
        test_execution_id = [item.test_execution_id for item in test_execution]
        test_runs = TestRun.query.filter(TestRun.project_id == project_id, TestRun.cloud_id == cloud_id,
                                         TestRun.test_case_id == test_case_id,
                                         TestRun.test_execution_id.in_(test_execution_id)).all()
        status = TestStatus.query.filter(TestStatus.cloud_id == cloud_id, TestStatus.project_id == project_id,
                                         TestStatus.name == 'TODO').first()
        for test_run in test_runs:
            test_step_detail = TestStepDetail(
                id=str(uuid.uuid4()),
                test_step_id=test_step_id,
                status_id=status.id,
                test_run_id=test_run.id,
                created_date=get_timestamp_now(),
                link=test_case_id+"/"
            )
            db.session.add(test_step_detail)
            db.session.flush()
        # Tạo test details cho test case khác call test case này
        add_test_detail_for_test_case_call(cloud_id, project_id, test_case_id, status.id, test_case_id + "/")
        detail_of_action = {}
        field_name = [item.name for item in test_step_fields]
        detail_of_action['Action'] = test_step.action
        detail_of_action['Data'] = test_step.data
        detail_of_action['Expected Result'] = test_step.result
        if len(field_name) > (len(test_step.custom_fields) + 3):
            for i, name in enumerate(test_step.custom_fields):
                detail_of_action[field_name[3 + i]] = name
            number = len(field_name) - (len(test_step.custom_fields) + 3)
            if number == 1:
                detail_of_action[field_name[len(field_name) - 1]] = ''
            if number == 2:
                detail_of_action[field_name[len(field_name) - 2]] = ''
                detail_of_action[field_name[len(field_name) - 1]] = ''
        elif len(field_name) == (len(test_step.custom_fields) + 3):
            for i, name in enumerate(test_step.custom_fields):
                detail_of_action[field_name[3 + i]] = name
        db.session.commit()
        # Save history
        save_history_test_step(test_case_id, user_id, 1, 2, detail_of_action, [count_index + 1])
        return send_result(data='add success')
    except Exception as ex:
        db.session.rollback()
        return send_error(message=str(ex))


def add_test_detail_for_test_case_call(cloud_id: str, project_id: str, test_case_id_reference: str,
                                       status_id: str, link: str):
    try:
        test_steps = TestStep.query.filter(TestStep.cloud_id == cloud_id, TestStep.project_id == project_id,
                                           TestStep.test_case_id_reference == test_case_id_reference) \
            .order_by(asc(TestStep.created_date)).all()
        for test_step in test_steps:
            new_link = test_step.test_case_id + "/" + link
            test_runs = TestRun.query.filter(TestRun.cloud_id == cloud_id,
                                             TestRun.project_id == project_id,
                                             TestRun.test_case_id == test_step.test_case_id).all()
            for test_run in test_runs:
                test_step_detail = TestStepDetail(
                    id=str(uuid.uuid4()),
                    test_step_id=test_step.id,
                    status_id=status_id,
                    test_run_id=test_run.id,
                    created_date=get_timestamp_now(),
                    link=new_link
                )
                db.session.add(test_step_detail)
                db.session.flush()
            add_test_detail_for_test_case_call(cloud_id, project_id, test_step.test_case_id, status_id, new_link)
        db.session.commit()
    except Exception as ex:
        db.session.rollback()


@api.route("/<test_case_id>/<test_step_id>", methods=["DELETE"])
@authorization_require()
def remove_test_step(test_step_id, test_case_id):
    try:
        token = get_jwt_identity()
        cloud_id = token.get('cloudId')
        project_id = token.get('projectId')
        user_id = token.get('userId')
        test_step = TestStep.query.filter(TestStep.id == test_step_id).first()
        if test_step is None:
            return send_error(
                message="Test Step is not exist",
                code=200, show=False)
        # create detail_of_action
        detail_of_action = {}
        test_step_fields = db.session.query(TestStepField).filter(
            or_(TestStepField.project_id == project_id, TestStepField.project_key == project_id),
            TestStepField.cloud_id == cloud_id).order_by(TestStepField.index.asc())
        field_name = [item.name for item in test_step_fields]
        detail_of_action['Action'] = test_step.action
        detail_of_action['Data'] = test_step.data
        detail_of_action['Expected Result'] = test_step.result
        if len(field_name) > (len(test_step.custom_fields) + 3):
            for i, name in enumerate(test_step.custom_fields):
                detail_of_action[field_name[3 + i]] = name
            number = len(field_name) - (len(test_step.custom_fields) + 3)
            if number == 1:
                detail_of_action[field_name[len(field_name) - 1]] = ''
            if number == 2:
                detail_of_action[field_name[len(field_name) - 2]] = ''
                detail_of_action[field_name[len(field_name) - 1]] = ''
        elif len(field_name) == (len(test_step.custom_fields) + 3):
            for i, name in enumerate(test_step.custom_fields):
                detail_of_action[field_name[3 + i]] = name
        index = test_step.index
        # delete test_step
        TestStepDetail.query.filter(TestStepDetail.test_step_id == test_step_id).delete()
        db.session.flush()
        TestStep.query.filter(TestStep.test_case_id == test_case_id).filter(TestStep.index > test_step.index) \
            .update(dict(index=TestStep.index - 1))
        db.session.delete(test_step)
        db.session.flush()
        db.session.commit()
        # Save history
        save_history_test_step(test_case_id, user_id, 2, 2, detail_of_action, [index])
        return send_result(data="", message="Test step removed successfully", code=200, show=True)
    except Exception as ex:
        db.session.rollback()
        return send_error(data='', message=str(ex))


@api.route("/<test_case_id>", methods=["PUT"])
@authorization_require()
def change_rank_test_step(test_case_id):
    try:
        token = get_jwt_identity()
        cloud_id = token.get('cloudId')
        project_id = token.get('projectId')
        user_id = token.get('userId')
        query = TestStep.query.filter(or_(TestStep.project_id == project_id, TestStep.project_key == project_id),
                                      TestStep.cloud_id == cloud_id, TestStep.test_case_id == test_case_id).all()
        if query is None:
            return send_error(message='PROJECT DOES NOT EXIST', status=404, show=False)

        json_req = request.get_json()
        index_drag = json_req['index_drag']
        index_drop = json_req['index_drop']
        index_max = db.session.query(TestStep).filter(
            or_(TestStep.project_id == project_id, TestStep.project_key == project_id),
            TestStep.cloud_id == cloud_id, TestStep.test_case_id == test_case_id).count()
        # vị trí drag to drop
        index_drag_to_drop = TestStep.query.filter(
            or_(TestStep.project_id == project_id, TestStep.project_key == project_id), TestStep.cloud_id == cloud_id,
                                                                                        TestStep.test_case_id == test_case_id).filter(
            TestStep.index == index_drag).first()
        if index_drag > index_drop:
            if index_drop < 1:
                return send_error(message=f'Must be a value between 1 and {index_max}', status=404, show=False)
            TestStep.query.filter(or_(TestStep.project_id == project_id, TestStep.project_key == project_id),
                                  TestStep.cloud_id == cloud_id, TestStep.test_case_id == test_case_id) \
                .filter(TestStep.index > index_drop - 1, TestStep.index < index_drag) \
                .update(dict(index=TestStep.index + 1))
            index_drag_to_drop.index = index_drop
            db.session.flush()
        else:
            if index_drop > index_max:
                return send_error(message=f'Must be a value between 1 and {index_max}', status=404, show=False)
            TestStep.query.filter(or_(TestStep.project_id == project_id, TestStep.project_key == project_id),
                                  TestStep.cloud_id == cloud_id, TestStep.test_case_id == test_case_id) \
                .filter(TestStep.index < index_drop + 1, TestStep.index > index_drag) \
                .update(dict(index=TestStep.index - 1))
            index_drag_to_drop.index = index_drop
            db.session.flush()
        db.session.commit()
        # Save history
        save_history_test_step(test_case_id, user_id, 3, 2, {}, [index_drag, index_drop])
        return send_result(data="", message="success", code=200, show=True)
    except Exception as ex:
        db.session.rollback()
        return send_error(data='', message=str(ex))


@api.route("/<test_case_id>/call/<test_case_id_reference>", methods=["POST"])
@authorization_require()
def call_test_case(test_case_id, test_case_id_reference):
    try:
        token = get_jwt_identity()
        cloud_id = token.get('cloudId')
        project_id = token.get('projectId')
        user_id = token.get('userId')
        test_case = TestCase.query.filter(TestCase.id == test_case_id).first()
        test_case_reference = TestCase.query.filter(TestCase.id == test_case_id_reference).first()
        if test_case is None:
            return send_error(
                message="Test Case is not Exist", code=200, show=False)
        if test_case_reference is None:
            return send_error(message="Call test case reference fail", code=200, show=False)
        check = TestStep.query.filter(TestStep.test_case_id == test_case_id_reference,
                                      TestStep.test_case_id_reference == test_case_id).first()
        if check:
            return send_error(message="not allowed to call because test was called called test", code=200,
                              is_dynamic=True)
        count_index = TestStep.query.filter(TestStep.test_case_id == test_case_id).count()
        test_step = TestStep(
            id=str(uuid.uuid4()),
            cloud_id=cloud_id,
            project_id=project_id,
            index=count_index + 1,
            test_case_id=test_case_id,
            test_case_id_reference=test_case_id_reference,
            created_date=get_timestamp_now()
        )
        db.session.add(test_step)
        db.session.flush()
        # check test run
        test_runs = TestRun.query.filter(TestRun.project_id == project_id, TestRun.cloud_id == cloud_id,
                                         TestRun.test_case_id == test_case_id).all()
        status = TestStatus.query.filter(TestStatus.cloud_id == cloud_id, TestStatus.project_id == project_id,
                                         TestStatus.name == 'TODO').first()
        step_calls = TestStep.query.filter(TestStep.cloud_id == cloud_id,
                                           TestStep.project_id == project_id, TestStep.test_case_id
                                           == test_case_id_reference).order_by(asc(TestStep.index)).all()
        # Add test details những test run tạo bởi test case id call
        link = test_case_id + "/" + test_case_id_reference + "/"
        for test_run in test_runs:
            for step_call in step_calls:
                if step_call.test_case_id_reference is None:
                    test_step_detail = TestStepDetail(
                        id=str(uuid.uuid4()),
                        test_step_id=step_call.id,
                        status_id=status.id,
                        test_run_id=test_run.id,
                        created_date=get_timestamp_now(),
                        link=link
                    )
                    db.session.add(test_step_detail)
                    db.session.flush()
                else:
                    add_test_step_id_by_test_case_id(cloud_id, project_id, test_step.test_case_id_reference,
                                                     test_run.id, status.id, [], link)
        # Add test details những test run tạo bởi test case có  test case id call  là reference
        test_steps = TestStep.query.filter(TestStep.cloud_id == cloud_id, TestStep.project_id == project_id,
                                           TestStep.test_case_id_reference == test_case_id).all()
        test_case_ids = [item.test_case_id for item in test_steps]
        link_2 = test_case_id + "/"
        for test_case_id in test_case_ids:
            test_runs_2 = TestRun.query.filter(TestRun.project_id == project_id, TestRun.cloud_id == cloud_id,
                                               TestRun.test_case_id == test_case_id).all()

            step_calls_2 = TestStep.query.filter(TestStep.cloud_id == cloud_id,
                                                 TestStep.project_id == project_id, TestStep.test_case_id
                                                 == test_case_id).order_by(asc(TestStep.index)).all()
            for test_run in test_runs_2:
                for step_call in step_calls_2:
                    if step_call.test_case_id_reference is None:
                        test_step_detail = TestStepDetail(
                            id=str(uuid.uuid4()),
                            test_step_id=step_call.id,
                            status_id=status.id,
                            test_run_id=test_run.id,
                            created_date=get_timestamp_now(),
                            link=test_case_id + "/" + link_2
                        )
                        db.session.add(test_step_detail)
                        db.session.flush()
                    else:
                        add_test_detail_for_test_case_call(cloud_id, project_id, step_call.test_case_id,
                                                           status.id, step_call.test_case_id + "/" + link_2)

        db.session.commit()
        # Create detail_of_action and Save history
        detail_of_action = {"Call test": test_case_reference.issue_key}
        save_history_test_step(test_case_id, user_id, 5, 2, detail_of_action, [test_step.index + 1])
        return send_result(data='call success')
    except Exception as ex:
        db.session.rollback()
        return send_error(data='', message=str(ex))


@api.route("/<test_case_id>/<test_step_id>", methods=["POST"])
@authorization_require()
def clone_test_step(test_case_id, test_step_id):
    try:
        token = get_jwt_identity()
        cloud_id = token.get('cloudId')
        project_id = token.get('projectId')
        user_id = token.get('userId')
        test_step = TestStep.query.filter(TestStep.test_case_id == test_case_id, TestStep.id == test_step_id).first()
        if test_step is None:
            return send_error(
                message="Test Step is not exist", code=200,
                show=False)
        # Sắp xếp lại index khi clone
        TestStep.query.filter(TestStep.test_case_id == test_case_id) \
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
            test_case_id=test_case_id,
            created_date=get_timestamp_now()
        )
        db.session.add(test_step_clone)
        db.session.flush()
        test_step_fields = db.session.query(TestStepField).filter(
            or_(TestStepField.project_id == project_id, TestStepField.project_key == project_id),
            TestStepField.cloud_id == cloud_id).order_by(TestStepField.index.asc())
        # check test run
        test_execution = TestCasesTestExecutions.query.filter(TestCasesTestExecutions.test_case_id
                                                              == test_case_id).all()
        test_execution_id = [item.test_execution_id for item in test_execution]
        test_runs = TestRun.query.filter(TestRun.project_id == project_id, TestRun.cloud_id == cloud_id,
                                         TestRun.test_case_id == test_case_id,
                                         TestRun.test_execution_id.in_(test_execution_id)).all()
        status = TestStatus.query.filter(TestStatus.cloud_id == cloud_id, TestStatus.project_id == project_id,
                                         TestStatus.name == 'TODO').first()
        for test_run in test_runs:
            test_step_detail = TestStepDetail(
                id=str(uuid.uuid4()),
                test_step_id=test_step_id,
                status_id=status.id,
                test_run_id=test_run.id,
                created_date=get_timestamp_now(),
                link=test_case_id + "/"
            )
            db.session.add(test_step_detail)
            db.session.flush()
        # Tạo test details cho test case khác call test case này
        add_test_detail_for_test_case_call(cloud_id, project_id, test_case_id, status.id, test_case_id + "/")
        db.session.commit()
        # Create detail_of_action and Save history
        detail_of_action = {}
        field_name = [item.name for item in test_step_fields]
        detail_of_action['Action'] = test_step.action
        detail_of_action['Data'] = test_step.data
        detail_of_action['Expected Result'] = test_step.result
        if len(field_name) > (len(test_step.custom_fields) + 3):
            for i, name in enumerate(test_step.custom_fields):
                detail_of_action[field_name[3 + i]] = name
            number = len(field_name) - (len(test_step.custom_fields) + 3)
            if number == 1:
                detail_of_action[field_name[len(field_name) - 1]] = ''
            if number == 2:
                detail_of_action[field_name[len(field_name) - 2]] = ''
                detail_of_action[field_name[len(field_name) - 1]] = ''
        elif len(field_name) == (len(test_step.custom_fields) + 3):
            for i, name in enumerate(test_step.custom_fields):
                detail_of_action[field_name[3 + i]] = name
        save_history_test_step(test_case_id, user_id, 4, 2, detail_of_action, [test_step.index + 1])
        return send_result(data='', message="Step clone successfully",
                           show=True)
    except Exception as ex:
        db.session.rollback()
        return send_error(data='', message="Something was wrong!")
