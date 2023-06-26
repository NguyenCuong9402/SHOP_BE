import os
import uuid
from flask import Blueprint, request, make_response, send_file, Response
from flask_jwt_extended import get_jwt_identity
from sqlalchemy import asc, desc
from io import BytesIO
import datetime
import io
from app.models import db, Product, User, Orders, OrderItems, CartItems
from app.utils import send_error, get_timestamp_now, send_result
from app.schema import ProductSchema, OrdersSchema

api = Blueprint('history', __name__)


@api.route("", methods=["POST"])
def history():
    try:
        orders = Orders.query.filter().order_by(desc(Orders.created_date)).all()
        data = OrdersSchema(many=True).dump(orders)
        return send_result(data=data)
    except Exception as ex:
        return send_error(message=str(ex))