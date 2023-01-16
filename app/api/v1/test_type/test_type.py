import json
import uuid
from operator import or_

from flask import Blueprint, request
from flask_jwt_extended import get_jwt_identity

from sqlalchemy import func, asc, and_

from app.gateway import authorization_require
from app.models import TestType, db
from app.utils import send_result, send_error
from app.validator import TestTypeSchema

api = Blueprint('test_type', __name__)


@api.route("/<project_id>", methods=["GET"])
@authorization_require()
def get_test_type(project_id):
    try:
        token = get_jwt_identity()
        cloud_id = token.get('cloudId')
        test_types_count = db.session.query(TestType).filter(
            or_(TestType.project_id == project_id, TestType.project_key == project_id),
            TestType.cloud_id == cloud_id).count()
        if test_types_count == 0:
            test_type = TestType(
                id=str(uuid.uuid4()),
                name=DEFAUT_DATA['name'],
                kind=DEFAUT_DATA['kind'],
                is_default=DEFAUT_DATA['is_default'],
                index=DEFAUT_DATA['index'],
                project_id=project_id,
                cloud_id=cloud_id,
            )
            db.session.add(test_type)
        db.session.commit()
        test_types = db.session.query(TestType).filter(
            or_(TestType.project_id == project_id, TestType.project_key == project_id),
            TestType.cloud_id == cloud_id).order_by(asc(TestType.index)).all()
        result = TestTypeSchema(many=True).dump(test_types)
        return send_result(data=result, message="OK")
    except Exception as ex:
        db.session.rollback()
        return send_error(message="Something wrong!")


"""
Helper function
"""


def check_coincided_name(name='', self_id=None, project_id='', cloud_id=''):
    existed_test_step = TestType.query.filter(
        and_(TestType.name == name, TestType.id != self_id, TestType.cloud_id == cloud_id,
             TestType.project_id == project_id)).first()
    if existed_test_step is None:
        return False
    return True


DEFAUT_DATA = {
    "name": "Manual",
    "kind": "Steps",
    "is_default": True,
    "index": 0
}
