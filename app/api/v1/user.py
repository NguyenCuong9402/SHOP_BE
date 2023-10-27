import os
import uuid
import base64
from flask import Blueprint, request, make_response, send_file, Response, jsonify
from flask_jwt_extended import get_jwt_identity, create_access_token, create_refresh_token, jwt_required, get_jwt
from sqlalchemy import asc, desc
from app.schema import UserSchema, DiaChiVnSchema
from werkzeug.utils import secure_filename
import io
import pandas as pd
from sqlalchemy import distinct
from app.blocklist import BLOCKLIST
from app.extensions import mail
from app.models import db, User, DiaChiVN
from app.utils import send_error, get_timestamp_now, send_result, generate_password, is_valid_birthday, format_birthday
from flask_mail import Message as MessageMail

api = Blueprint('user', __name__)


@api.route("/register", methods=["POST"])
def register():
    try:
        body_request = request.get_json()
        for key, value in body_request.items():
            if isinstance(value, str):
                if value == "" and key != 'address':
                    return send_error("Không được để trống ngoài Địa chỉ bổ sung!")
                if key == 'birthday':
                    if not is_valid_birthday(value):
                        return send_error(message='Ngày sinh không hợp lệ!')
                body_request.update({key: value.strip()})
        name_user = body_request.get("fullName", "")
        phone_number = body_request.get("phoneNumber", "")
        address = body_request.get("address", "")
        email = body_request.get("email", "")
        password = body_request.get("password", "")
        confirm_password = body_request.get("confirmPassword", "")
        gender = body_request.get("gender", "")
        tinh = body_request.get("tinh")
        huyen = body_request.get("huyen")
        xa = body_request.get("xa")
        birthday = body_request.get('birthday')
        if len(password) < 8:
            send_error(message='Mật khẩu lớn hơn hoặc 8 kí tự.')
        if len(phone_number) != 10:
            return send_error(message='Số điện thoại chưa đúng.')
        if password != confirm_password:
            return send_error(message='Xác nhận mật khẩu sai')

        gender = 0 if gender == 'male' else 1

        check_user = User.query.filter(User.email == email).first()
        if check_user:
            return send_error(message="Email đã tồn tại", is_dynamic=True)
        user_phone_number = User.query.filter(User.phone_number == phone_number).first()
        if user_phone_number:
            return send_error(message="SĐT đã được đăng ký, vui lòng thay đổi SĐT")

        user = User(
            id=str(uuid.uuid4()),
            email=email,
            password=password,
            phone_number=phone_number,
            address=address,
            name_user=name_user,
            gender=gender,
            tinh=tinh,
            huyen=huyen,
            xa=xa,
            birthday=format_birthday(birthday),
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
            if user.admin != 0:
                return send_error(message="Tài khoản admin!", is_dynamic=True)
        access_token = create_access_token(identity=user.id, fresh=True, expires_delta=False)
        refresh_token = create_refresh_token(user.id)
        return send_result(data={"access_token": access_token, "refresh_token": refresh_token,
                                 "user": UserSchema().dump(user)})
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
        password = body_request.get("password", "")
        new_password = body_request.get("new_password", "")
        confirm_password = body_request.get("confirm_password", "")
        if password == "":
            return send_error(message='Chưa điền mật khẩu.')
        user = User.query.filter(User.id == user_id).first()
        if new_password == "":
            return send_error(message="Chưa điền mật khẩu mới.")
        if confirm_password == "":
            return send_error(message="Chưa điền xác nhận mật khẩu.")
        if new_password != confirm_password:
            return send_error(message="Xác nhận mật khẩu không đúng.")
        if len(new_password) < 8:
            return send_error(message="Mật khẩu phải lớn hơn hoặc bằng 8 kí tự.")

        if user.password != password:
            return send_error(message='Mật khẩu không đúng.')
        user.password = new_password
        db.session.commit()
        return send_result(message="Thay đổi mật khẩu thành công!")
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

        if user.admin == 2:
            return send_error(message='Bạn không có quyền!')
        body_request = request.get_json()
        email = body_request.get("email", "")
        name_user = body_request.get("name_user", "")
        phone_number = body_request.get("phone_number", "")
        user_admin = User.query.filter(User.email == email).first()
        if name_user == "":
            return send_error(message='Không để tên trống')
        if user_admin:
            return send_error(message="Email đã được đăng ký, vui lòng thay đổi Email")
        user_admin_phone_number = User.query.filter(User.phone_number == phone_number).first()

        if len(phone_number) != 10:
            return send_error(message='Số điện thoại chưa đúng')

        if user_admin_phone_number:
            return send_error(message="SĐT đã được đăng ký, vui lòng thay đổi SĐT")

        password = generate_password()
        user = User(
            id=str(uuid.uuid4()),
            email=email,
            password=password,
            phone_number=phone_number,
            name_user=name_user,
            created_date=get_timestamp_now(),
            gender=1,
            admin=1
        )
        db.session.add(user)
        db.session.flush()

        msg = MessageMail('Mật khẩu tài khoản admmin', recipients=[email])

        msg.body = f"Mật khẩu của bạn là : {password} "
        mail.send(msg)
        db.session.commit()
        return send_result(message="Tạo tài khoản thành công!", show=True)
    except Exception as ex:
        db.session.rollback()
        return send_error(message=str(ex))


@api.route("/list-user", methods=["GET"])
@jwt_required()
def get_list_user():
    try:
        user_id = get_jwt_identity()
        user = User.query.filter(User.id == user_id).first()
        if user.admin == 0:
            return send_result(message="Bạn không phải admin.")
        users = User.query.filter(User.admin == 0).order_by(desc(User.count_money_buy)).all()
        data = UserSchema(many=True).dump(users)
        return send_result(data=data)
    except Exception as ex:
        return send_error(message=str(ex))


@api.route("", methods=["GET"])
@jwt_required()
def get_user():
    try:
        user_id = get_jwt_identity()
        user = User.query.filter(User.id == user_id).first()
        data = UserSchema().dump(user)

        return send_result(data=data)
    except Exception as ex:
        return send_error(message=str(ex))


@api.route("/update", methods=["PUT"])
@jwt_required()
def update_user():
    try:
        user_id = get_jwt_identity()
        user = User.query.filter(User.id == user_id).first()

        body_request = request.get_json()

        for key, value in body_request.items():
            if isinstance(value, str):
                if value == "" and key != 'address':
                    return send_error("Không được để trống ngoài Địa chỉ bổ sung!")
                if key == 'birthday':
                    if not is_valid_birthday(value):
                        return send_error(message='Ngày sinh không hợp lệ!')
                body_request.update({key: value.strip()})
        for key, value in body_request.items():
            if key != "birthday":
                user.__setattr__(key, value)
            else:
                user.__setattr__(key, format_birthday(value))
        db.session.flush()
        db.session.commit()
        return send_result(data=UserSchema().dump(user), message='Thay đổi thông tin thành công!')
    except Exception as ex:
        return send_error(message=str(ex))


@api.route("import", methods=["POST"])
def import_dia_chi():
    try:
        file = request.files['file']
        if file:
            # Đọc dữ liệu từ tệp Excel bằng pandas
            df = pd.read_excel(file)
            # Lặp qua từng hàng của DataFrame và thêm vào cơ sở dữ liệu
            for index, row in df.iterrows():
                dia_chi = DiaChiVN(
                    id=str(uuid.uuid4()),
                    tinh=str(row['tinh']),
                    huyen=str(row['huyen']),
                    xa=str(row['xa'])
                )
                db.session.add(dia_chi)
                db.session.flush()
            db.session.commit()
            return send_result(message="Thành Công.")
        return send_error(message="No file uploaded.")
    except Exception as ex:
        return send_error(message=str(ex))


@api.route("tim_dia_chi", methods=["GET"])
def tim_dia_chi():
    try:
        tinh = request.args.get('tinh', "")
        huyen = request.args.get('huyen', "")
        xa = request.args.get('xa', "")

        data = {}
        cac_tinh = DiaChiVN.query.with_entities(DiaChiVN.tinh).distinct().order_by(DiaChiVN.tinh).all()
        data['tinh'] = [tinh.tinh for tinh in cac_tinh]

        cac_huyen = DiaChiVN.query.filter(DiaChiVN.tinh == tinh) \
            .with_entities(DiaChiVN.huyen) \
            .distinct().order_by(DiaChiVN.huyen).all()
        data['huyen'] = [row.huyen for row in cac_huyen]
        cac_xa = DiaChiVN.query.filter(DiaChiVN.tinh == tinh, DiaChiVN.huyen == huyen) \
            .with_entities(DiaChiVN.xa).distinct().order_by(DiaChiVN.xa).all()
        data['xa'] = [row.xa for row in cac_xa]

        return send_result(message='Done', data=data)
    except Exception as ex:
        return send_error(message=str(ex))


@api.route('/send_pass_email', methods=['POST'])
def send_email():
    try:
        body_request = request.get_json()
        email = body_request.get('email', "")
        msg = MessageMail('THAY ĐỔI MẬT KHẨU TÀI KHOẢN', recipients=[email])

        user = User.query.filter(User.email == email).first()
        if user is None:
            return send_error(message='Tài Khoản Không Tồn Tại')
        new_password = generate_password()
        msg.body = f"Mật khẩu của bạn là : {new_password} "
        mail.send(msg)
        user.password = new_password
        db.session.flush()
        db.session.commit()
        return send_result(message='Check EMAIL lấy mật khẩu')
    except Exception as ex:
        db.session.rollback()
        return send_error(message=str(ex))