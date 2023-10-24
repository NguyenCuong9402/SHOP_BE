import os
import uuid
import base64
from flask import Blueprint, request, make_response, send_file, Response, jsonify
from flask_jwt_extended import get_jwt_identity, create_access_token, create_refresh_token, jwt_required, get_jwt
from sqlalchemy import asc, desc
from app.schema import UserSchema
from werkzeug.utils import secure_filename
import io
import pandas as pd
from sqlalchemy import distinct
from app.blocklist import BLOCKLIST
from app.extensions import mail
from app.models import db, User, DiaChiVN
from app.utils import send_error, get_timestamp_now, send_result, generate_password
from flask_mail import Message as MessageMail

api = Blueprint('user', __name__)


@api.route("/register", methods=["POST"])
def register():
    try:
        body_request = request.get_json()
        name_user = body_request.get("fullName", "")
        phone_number = body_request.get("phoneNumber", "")
        address = body_request.get("address", "")
        email = body_request.get("email", "")
        password = body_request.get("password", "")
        confirmPassword = body_request.get("confirmPassword", "")
        gender = body_request.get("gender", "")
        if name_user == "":
            return send_error(message="Không được để trống thông tin")
        if "phone_number" == "":
            return send_error(message='Không được để trống thông tin')
        if email == "":
            return send_error(message='Không được để trống thông tin')
        if password == "":
            return send_error(message='Không được để trống thông tin')
        if confirmPassword == "":
            return send_error(message='Không được để trống thông tin')

        if password != confirmPassword:
            return send_error(message='Confirm false')
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
        new_password = body_request.get("new_password", "")
        confirm_password = body_request.get("confirm_password", "")
        if new_password == "" or confirm_password == "":
            return send_error(message="Không để trống mật khẩu", is_dynamic=True)
        user = User.query.filter(User.id == user_id).first()
        if new_password != confirm_password:
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
        name_user = body_request.get("name_user", "")
        phone_number = body_request.get("phone_number", "")
        address = body_request.get("address", "")
        user_admin = User.query.filter(User.email == email).first()
        if user_admin:
            return send_error(message="Email đã được đăng ký, vui lòng thay đổi Email")
        user_admin_phone_number = User.query.filter(User.phone_number == phone_number).first()
        if user_admin_phone_number:
            return send_error(message="SĐT đã được đăng ký, vui lòng thay đổi SĐT")
        user = User(
            id=str(uuid.uuid4()),
            email=email,
            password=password,
            phone_number=phone_number,
            address=address,
            name_user=name_user,
            created_date=get_timestamp_now(),
            admin=1
        )
        db.session.add(user)
        db.session.flush()
        db.session.commit()
        return send_result(message="Đăng ký toàn khoản thành công", show=True)
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
        name_user = body_request.get("name_user", None)
        phone_number = body_request.get("phone_number", None)
        address = body_request.get("address", None)
        if name_user == "" or phone_number == "" or address == "":
            return send_error(message="Data empty")
        if name_user is not None:
            user.name_user = name_user
        if phone_number is not None:
            user.phone_number = phone_number
        if address is not None:
            user.address = address
        db.session.flush()
        db.session.commit()
        return send_result(data=UserSchema().dump(user))
    except Exception as ex:
        return send_error(message=str(ex))


@api.route("import", methods=["POST"])
@jwt_required()
def import_dia_chi():
    try:
        user_id = get_jwt_identity()
        user = User.query.filter(User.id == user_id).first()
        if user.admin == 0:
            return send_error(message='Chỉ có admin mới có quyền!')
        file = request.files['file']
        if file:
            # Đọc dữ liệu từ tệp Excel bằng pandas
            df = pd.read_excel(file)
            list_chia_chi = []
            # Lặp qua từng hàng của DataFrame và thêm vào cơ sở dữ liệu
            for index, row in df.iterrows():
                dia_chi = DiaChiVN.query.filter(DiaChiVN.tinh == str(row['tinh']),
                                                DiaChiVN.huyen == str(row['huyen']),
                                                DiaChiVN.xa == str(row['xa'])).first()
                if dia_chi is None:
                    dia_chi = DiaChiVN(
                        id=str(uuid.uuid4()),
                        tinh=str(row['tinh']),
                        huyen=str(row['huyen']),
                        xa=str(row['xa'])
                    )
                    list_chia_chi.append(dia_chi)

            db.session.bulk_save_objects(list_chia_chi)
            db.session.commit()
            return send_result(message="Thành Công.")
        return send_error(message="No file uploaded.")
    except Exception as ex:
        return send_error(message=str(ex))


@api.route("tim_dia_chi", methods=["GET"])
@jwt_required()
def tim_dia_chi():
    try:
        tinh = request.args.get('tinh', "")
        huyen = request.args.get('huyen', "")
        xa = request.args.get('xa', "")
        if tinh == "" or tinh is None:
            cac_tinh = DiaChiVN.query.with_entities(DiaChiVN.tinh).distinct().order_by(DiaChiVN.tinh).all()
            data = [tinh.tinh for tinh in cac_tinh]
            send_result(data=data, message='Danh sách tỉnh', status='tinh')
        if huyen == "" or tinh is None:
            cac_huyen = DiaChiVN.query.filter(DiaChiVN.tinh == tinh) \
                .with_entities(DiaChiVN.huyen) \
                .distinct().order_by(DiaChiVN.huyen).all()
            data = [row.huyen for row in cac_huyen]
            send_result(data=data, message='Danh sách huyện', status='huyen')
        if xa == "" or xa is None:
            cac_huyen = DiaChiVN.query.filter(DiaChiVN.tinh == tinh, DiaChiVN.huyen == huyen) \
                .with_entities(DiaChiVN.xa).distinct().order_by(DiaChiVN.xa).all()
            data = [row.xa for row in cac_huyen]
            send_result(data=data, message='Danh sách xã', status='xa')
        return send_result(message='Done')
    except Exception as ex:
        return send_error(message=str(ex))


@api.route('/send_pass_email', methods=['POST'])
def send_email():
    try:
        body_request = request.get_json()
        email = body_request.get('email', "")
        msg = MessageMail('THAY ĐỔI MẬT KHẨU TÀI KHOẢN', recipients=[email])
        html_content = """
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                .container {
              padding: 100px;
            }
            .envelop {
              width: 300px;
              height: 200px;
              box-sizing: border-box;
              border-color: grey;
              border-style: solid;
              border-top: 100px solid #F4F9F9;
              border-right: 150px solid #CCF2F4;
              border-bottom: 100px solid #A4EBF3;
              border-left: 150px solid #A4EBF3;
            }
            </style>
        </head>
        <div class="container">
          <div class="envelop"></div>
        </div>
        <div>Xin chào UserName</div>
        <div>Mật Khẩu của bạn là: NEWPASSWORD</div>

        </html>
        """
        user = User.query.filter(User.email == email).first()
        if user is None:
            return send_error(message='Tài Khoản Không Tồn Tại')
        html_content = html_content.replace("UserName", user.name_user)
        new_password = generate_password()
        html_content = html_content.replace("NEWPASSWORD", new_password)
        msg.html = html_content
        mail.send(msg)
        user.password = new_password
        db.session.flush()
        db.session.commit()
        return send_result(message='Check EMAIL lấy mật khẩu')
    except Exception as ex:
        db.session.rollback()
        return send_error(message=str(ex))