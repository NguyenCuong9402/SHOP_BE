import json
import uuid
from operator import or_

from flask import Blueprint, request
from flask_jwt_extended import get_jwt_identity
from sqlalchemy import func, asc, and_, desc

from app.api.v1.test_environment.test_environment_validator import CreateTestEnvironment, DeleteTestEnvironment, \
    UpdateTestEnvironment, AddTestEnvironment
from app.gateway import authorization_require
from app.models import TestType, db, TestEnvironment
from app.utils import send_result, send_error, validate_request, escape_wildcard
from app.validator import TestEnvironmentSchema

api = Blueprint('test_environment', __name__)


@api.route("/<project_id>", methods=["GET"])
@authorization_require()
def get_test_environments(project_id):
    """
    Get test environments paginated by project id
    Returns:

    """
    token = get_jwt_identity()
    cloud_id = token.get('cloudId')
    query = TestEnvironment.query.filter(TestEnvironment.cloud_id == cloud_id)

    # Get search params
    page = request.args.get('page', 1, type=int)
    page_size = request.args.get('page_size', 10, type=int)
    text_search = request.args.get('text_search', "", type=str)
    order_by = request.args.get('order_by', "name", type=str)
    order = request.args.get('order', 'desc', type=str)

    """
    If search_other=true, search all test environments in other projects, which have not been added in this project 
    Skip all rest params, default sorted by name A-Z
    """
    search_other = request.args.get('search_other', False, type=bool)
    if search_other:
        existed_test_environments = db.session.query(TestEnvironment.parent_id).filter(
            TestEnvironment.project_id == project_id,
            TestEnvironment.parent_id.is_not(None),
            TestEnvironment.cloud_id == cloud_id).all()

        existed_parent_ids = [item.parent_id for item in existed_test_environments]

        query = query.filter(TestEnvironment.project_id != project_id,
                             TestEnvironment.parent_id.is_(None),
                             TestEnvironment.id.not_in(existed_parent_ids),
                             TestEnvironment.cloud_id == cloud_id).order_by(desc(TestEnvironment.name))
    else:
        query = query.filter(TestEnvironment.project_id == project_id,
                             TestEnvironment.cloud_id == cloud_id)

        # Search by text
        if text_search is not None:
            text_search = text_search.strip()
            text_search = text_search.lower()
            text_search = escape_wildcard(text_search)
            text_search = "%{}%".format(text_search)
            query = query.filter(TestEnvironment.name.like(text_search))

        # Sort test env
        column_sorted = getattr(TestEnvironment, order_by)
        query = query.order_by(desc(column_sorted)) if order == "desc" else query.order_by(asc(column_sorted))

    # paginate
    test_environments = query.paginate(page=page, per_page=page_size, error_out=False).items

    total = query.count()

    extra = 1 if (total % page_size) else 0
    total_pages = int(total / page_size) + extra

    try:
        results = {
            "test_environments": TestEnvironmentSchema(many=True).dump(test_environments),
            "total": total,
            "total_pages": total_pages
        }

        return send_result(data=results)
    except Exception as ex:
        return send_error(data={})


@api.route("/<project_id>/add", methods=["POST"])
@authorization_require()
def add_test_environment(project_id):
    try:
        token = get_jwt_identity()
        cloud_id = token.get('cloudId')
        is_valid, data, body_request = validate_request(AddTestEnvironment(), request)
        if not is_valid:
            return send_error(data=data, code=200, is_dynamic=True)
        ids_to_add = body_request['ids']
        if len(ids_to_add) == 0:
            return send_error(message="This field is required")
        check_id = TestEnvironment.query.filter(TestEnvironment.id.in_(ids_to_add),
                                                TestEnvironment.parent_id.is_(None),
                                                TestEnvironment.cloud_id == cloud_id,
                                                TestEnvironment.project_id != project_id).count()
        if check_id < len(ids_to_add):
            return send_error(message=f" Test Environment is not exist ")
        check_parent_id = TestEnvironment.query.filter(TestEnvironment.cloud_id == cloud_id,
                                                       TestEnvironment.project_id == project_id,
                                                       TestEnvironment.parent_id.in_(ids_to_add)).count()
        if check_parent_id > 0:
            return send_error(message=f"{check_parent_id} in {len(ids_to_add)} Test Environment has been added "
                                      f"\n Please refresh the page to view the changes")

        query = TestEnvironment.query.filter(TestEnvironment.id.in_(ids_to_add)).all()
        for item in query:
            coincided = check_coincided_name(name=item.name, cloud_id=cloud_id, project_id=project_id)
            if coincided is True:
                return send_error(code=200, data={"name": "Test Environment already exists. Please try again"},
                                  message='Invalid request', show=False, is_dynamic=True)

            test_environment = TestEnvironment(
                id=str(uuid.uuid4()),
                project_id=project_id,
                cloud_id=cloud_id,
                name=item.name,
                description=item.description,
                url=item.url,
                parent_id=item.id
            )
            db.session.add(test_environment)
            db.session.flush()
        db.session.commit()
        return send_result(message=f"{len(ids_to_add)} Test Environments added", show=True)
    except Exception as ex:
        db.session.rollback()
        return send_error(data='', message=str(ex))


@api.route("/<project_id>", methods=["POST"])
@authorization_require()
def create_test_environment(project_id):
    """
    Create test environment
    """

    try:
        token = get_jwt_identity()
        cloud_id = token.get('cloudId')

        is_valid, data, body_request = validate_request(CreateTestEnvironment(), request)

        if not is_valid:
            return send_error(data=data, code=200, is_dynamic=True)

        # Check coincided name
        coincided = check_coincided_name(name=body_request.get('name'), cloud_id=cloud_id, project_id=project_id)
        if coincided is True:
            return send_error(code=200, data={"name": "Test Environment already exists. Please try again"},
                              message='Invalid request', show=False, is_dynamic=True)

        test_environment = TestEnvironment(
            id=str(uuid.uuid4()),
            project_id=project_id,
            cloud_id=cloud_id,
            name=body_request.get('name'),
            description=body_request.get('description', ''),
            url=body_request.get('url', ''),
            parent_id=None

        )
        db.session.add(test_environment)
        db.session.flush()

        db.session.commit()
        return send_result(data=TestEnvironmentSchema().dump(test_environment), message="The Test Environments created",
                           show=True)
    except Exception as ex:
        db.session.rollback()
        return send_error(data='', message="Something was wrong!")


@api.route("/<project_id>", methods=["DELETE"])
@authorization_require()
def delete_test_environments(project_id):
    """
    Delete multiples records
    Returns:

    """
    try:

        is_valid, data, body_request = validate_request(DeleteTestEnvironment(), request)

        if not is_valid:
            return send_error(data=data, code=200, is_dynamic=True)

        ids_to_delete = body_request['ids']
        is_delete_all = body_request['is_delete_all']

        """
        1. Delete all parents id
        """
        if is_delete_all:
            db.session.query(TestEnvironment).filter(TestEnvironment.parent_id.in_(ids_to_delete)).update(
                {TestEnvironment.parent_id: None})
            """
        1. Delete all test_environments by id
            """
            for id_to_delete in ids_to_delete:
                test_environment = TestEnvironment.get_by_id(id_to_delete)
                if test_environment is None:
                    return send_error(
                        message="Test Environment has been changed \n Please refresh the page to view the changes",
                        code=200,
                        show=False)
                db.session.delete(test_environment)
                db.session.flush()
            number = len(ids_to_delete)
        else:
            number = TestEnvironment.query.filter(TestEnvironment.id.notin_(ids_to_delete)).count()
            db.session.query(TestEnvironment).filter(TestEnvironment.parent_id.notin_(ids_to_delete)).update(
                {TestEnvironment.parent_id: None})
            db.session.query(TestEnvironment).filter(TestEnvironment.id.notin_(ids_to_delete)).delete()
            db.session.flush()
        db.session.commit()
        return send_result(data="", message=f"{number} Test Environment(s) removed", code=200, show=True)
    except Exception as ex:
        db.session.rollback()
        return send_error(data='', message="Something was wrong!")


@api.route("/<project_id>/<test_environment_id>", methods=["PUT"])
@authorization_require()
def update_test_environment(project_id, test_environment_id):
    try:

        test_environment = TestEnvironment.get_by_id(test_environment_id)
        if test_environment is None:
            return send_error(
                message="Test Environment has been changed \n Please refresh the page to view the changes",
                code=200,
                show=False)

        is_valid, data, body_request = validate_request(UpdateTestEnvironment(), request)
        if not is_valid:
            return send_error(data=data, code=200, is_dynamic=True)

        # Update model
        update_data = body_request.items()
        for key, value in update_data:
            setattr(test_environment, key, value)
        db.session.commit()
        return send_result(data=TestEnvironmentSchema().dump(test_environment),
                           message="The Test Environments were saved successfully", show=True)

    except Exception as ex:
        db.session.rollback()
        return send_error(data='', message="Something was wrong!")


def check_coincided_name(name='', self_id=None, project_id='', cloud_id=''):
    if project_id is None:
        existed_test_step = TestEnvironment.query.filter(
            and_(func.lower(TestEnvironment.name) == func.lower(name), TestEnvironment.id != self_id,
                 TestEnvironment.cloud_id == cloud_id)).first()
    else:
        existed_test_step = TestEnvironment.query.filter(
            and_(func.lower(TestEnvironment.name) == func.lower(name), TestEnvironment.id != self_id,
                 TestEnvironment.cloud_id == cloud_id, TestEnvironment.project_id == project_id)).first()
    if existed_test_step is None:
        return False
    return True
