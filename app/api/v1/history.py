
from flask import Blueprint
from flask_jwt_extended import get_jwt_identity, jwt_required, get_jwt
from sqlalchemy import desc
from app.models import User, Orders
from app.utils import send_error, send_result
from app.schema import OrdersSchema, HistoryOrdersSchema

api = Blueprint('history', __name__)


@api.route("/customer", methods=["GET"])
@jwt_required()
def history():
    try:
        user_id = get_jwt_identity()
        orders = Orders.query.filter(Orders.user_id == user_id).order_by(desc(Orders.created_date)).all()
        data = OrdersSchema(many=True).dump(orders)
        return send_result(data=data)
    except Exception as ex:
        return send_error(message=str(ex))


@api.route("/store", methods=["GET"])
@jwt_required()
def history_shop():
    try:
        jwt = get_jwt()
        user_id = get_jwt_identity()
        user = User.query.filter(User.id == user_id).first()
        if user.admin == 0 or (not jwt.get("is_admin")):
            return send_result(message="Bạn không phải admin.")
        orders = Orders.query.filter().order_by(desc(Orders.created_date)).all()
        data = HistoryOrdersSchema(many=True).dump(orders)
        return send_result(data=data)
    except Exception as ex:
        return send_error(message=str(ex))

