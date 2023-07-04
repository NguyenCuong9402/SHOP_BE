import os
import uuid
from flask import Blueprint, request, make_response, send_file, Response
from flask_jwt_extended import get_jwt_identity, create_access_token, create_refresh_token, jwt_required, get_jwt
from sqlalchemy import asc

from app.blocklist import BLOCKLIST
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
        if name_user == "" or phone_number == "" or address == "" or email == "email" or password =="":
            return send_error(message="Yêu cầu nhập thông tin")
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
        admin = body_request.get("admin", False)
        if admin:
            if email == "" or password == "":
                return send_error(message="Vui lòng điền email và mật khẩu", is_dynamic=True)
            user = User.query.filter(User.email == email).first()
            if user is None:
                return send_error(message="Tài khoản không tồn tại!", is_dynamic=True)
            if user.password != password:
                return send_error(message="Sai mật khẩu, vui lòng đăng nhập lại!", is_dynamic=True)
            if user.admin == 0:
                return send_error(message="Tài khoản không phải admin!", is_dynamic=True)
        else:
            if email == "" or password == "":
                return send_error(message="Vui lòng điền email và mật khẩu", is_dynamic=True)
            user = User.query.filter(User.email == email).first()
            if user is None:
                return send_error(message="Tài khoản không tồn tại!", is_dynamic=True)
            if user.password != password:
                return send_error(message="Sai mật khẩu, vui lòng đăng nhập lại!", is_dynamic=True)
            if user.admin == 1:
                return send_error(message="Tài khoản admin!", is_dynamic=True)
        access_token = create_access_token(identity=user.id, fresh=True)
        refresh_token = create_refresh_token(user.id)
        return send_result(data={"access_token": access_token, "refresh_token": refresh_token})
    except Exception as ex:
        db.session.rollback()
        return send_error(message=str(ex))


@api.route("/refresh", methods=["GET"])
@jwt_required(refresh=True)
def refresh():
    try:
        user_id = get_jwt_identity()
        new_token = create_access_token(identity=user_id, fresh=False)
        jti = get_jwt()["jti"]
        BLOCKLIST.add(jti)
        return send_result(data=new_token)
    except Exception as ex:
        return send_error(message=str(ex))


@api.route("/logout", methods=["GET"])
@jwt_required()
def logout():
    try:
        jti = get_jwt()["jti"]
        BLOCKLIST.add(jti)
        return send_result(message="Log out!")
    except Exception as ex:
        return send_error(message=str(ex))


@api.route("/change-password", methods=["PUT"])
@jwt_required()
def change_pass():
    try:
        user_id = get_jwt_identity()
        body_request = request.get_json()
        old_password = body_request.get("old_password", "")
        new_password = body_request.get("new_password", "")
        if new_password == "" or old_password == "":
            return send_error(message="Không để trống mật khẩu", is_dynamic=True)
        user = User.query.filter(User.id == user_id).first()
        if user.password != old_password:
            return send_error(message=" Password sai, xin moi nhap lai.")
        user.password = new_password
        db.session.commit()
        jti = get_jwt()["jti"]
        BLOCKLIST.add(jti)
        return send_result(message="Thay đổi mật khẩu thành công! \n Vui lòng đăng nhập lại")
    except Exception as ex:
        db.session.rollback()
        return send_error(message=str(ex))


@api.route("created-admin", methods=["POST"])
@jwt_required()
def add_admin():
    try:
        jwt = get_jwt()
        user_id = get_jwt_identity()
        user = User.query.filter(User.id == user_id).first()
        if user.admin == 0 or (not jwt.get("is_admin")):
            return send_result(message="Bạn không phải admin.")
        body_request = request.get_json()
        email = body_request.get("email", "")
        password = body_request.get("password", "")
        admin = body_request.get("admin", False)
    except Exception as ex:
        db.session.rollback()
        return send_error(message=str(ex))




