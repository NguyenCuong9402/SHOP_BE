import os
import uuid
from flask import Blueprint, request, make_response, send_file, Response
from flask_jwt_extended import get_jwt_identity, create_access_token, create_refresh_token
from sqlalchemy import asc

from app.models import db, Product, User, Orders, OrderItems, CartItems

from app.utils import send_error, get_timestamp_now, send_result

api = Blueprint('user', __name__)


@api.route("/register", methods=["POST"])
def register():
    try:
        body_request = request.get_json()
        name_user = body_request.get("name_user", "")
        phone_number = body_request.get("phone_number", "")
        address = body_request.get("address", "")
        email = body_request.get("email", "")
        password = body_request.get("password", "")
        check_user = User.query.filter(User.email == email).first()
        if check_user:
            return send_error(message="Email đã tồn tại", is_dynamic=True)
        user = User(
            id=str(uuid.uuid4()),
            email=email,
            password=password,
            phone_number=phone_number,
            address=address,
            name_user=name_user,
            created_date=get_timestamp_now()
        )
        db.session.add(user)
        db.session.flush()
        db.session.commit()
        return send_result(message="Đăng ký toàn khoản thành công", show=True)
    except Exception as ex:
        db.session.rollback()
        return send_error(message=str(ex))


@api.route("/login", methods=["POST"])
def login():
    try:
        body_request = request.get_json()
        email = body_request.get("email", "")
        password = body_request.get("password", "")
        if email == "" or password == "":
            return send_error(message="Vui lòng điền email và mật khẩu", is_dynamic=True)
        user = User.query.filter(User.email == email).first()
        if user is None:
            return send_error(message="Tài khoản không tồn tại!", is_dynamic=True)
        else:
            if user.password != password:
                return send_error(message="Sai mật khẩu, vui lòng đăng nhập lại!", is_dynamic=True)

        access_token = create_access_token(identity=user.id, fresh=True)
        refresh_token = create_refresh_token(user.id)
        return send_result(data={"access_token": access_token, "refresh_token":refresh_token})
    except Exception as ex:
        db.session.rollback()
        return send_error(message=str(ex))


