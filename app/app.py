# -*- coding: utf-8 -*-
import json
import os
import traceback

from flask import Flask, jsonify

from flask_cors import CORS
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView

from app.blocklist import BLOCKLIST
from app.extensions import jwt, migrate, ma, mail, red
from app.models import Message
from app.api import v1 as api_v1
from app.settings import DevConfig
from app.models import db, User
import firebase_admin
from firebase_admin import credentials, storage

def create_app():
    """
    Init App
    :return:
    """
    config_object = DevConfig
    app = Flask(__name__, static_url_path="", static_folder="./files")
    app.config.from_object(config_object)
    register_extensions(app)
    register_blueprints(app)
    CORS(app, resources={r"/api/v1/*": {"origins": "*"}})

    # cred = credentials.Certificate("app/private_key_firebase.json")
    # firebase_admin.initialize_app(cred, {
    #     'storageBucket': 'fir-b13c4.appspot.com'
    # })

    @app.before_first_request
    def setup_redis():
        add_messages_to_redis()

    @jwt.token_in_blocklist_loader
    def check_if_token_in_blocklist(jwt_header, jwt_payload):
        return jwt_payload["jti"] in BLOCKLIST

    # mã đã thu hồi
    @jwt.revoked_token_loader
    def revoked_token_callback(jwt_header, jwt_payload):
        return (
            jsonify(
                {"description": "Mã token đã bị thu hồi.", "error": "token_revoked"}
            ), 401
        )

    # yêu cầu làm mới
    @jwt.needs_fresh_token_loader
    def token_not_fresh_callback(jwt_header, jwt_payload):
        return (
            jsonify(
                {
                    "description": "Hãy làm mới token.",
                    "error": "fresh_token_required"
                }
            ), 401
        )

    # set admin
    @jwt.additional_claims_loader
    def add_claims_to_jwt(identity):
        user = User.query.filter(User.id == identity).first()
        if user.admin != 0:
            return {"is_admin": True}
        return {"is_admin": False}

    # mã đã hết hạn
    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        return jsonify({"message": "Mã token đã hết hạn.", "error": "token_expired"}), 401

    # mã không hợp lệ
    @jwt.invalid_token_loader
    def invalid_token_callback(error):
        return jsonify({"message": "Mã token không hợp lệ.", "error": "invalid_expired"}), 401

    @jwt.unauthorized_loader
    def missing_token_callback(error):
        return (jsonify(
            {"description": "Request does not contain an access token",
             "error": "authorization_required"}
        ), 401)
    return app


def register_extensions(app):
    """
    Init extension
    :param app:
    :return:
    """
    db.app = app
    db.init_app(app)  # SQLAlchemy
    jwt.init_app(app)
    migrate.init_app(app, db)
    ma.init_app(app)
    mail.init_app(app)
    red.init_app(app)


def register_blueprints(app):
    """
    Init blueprint for api url
    :param app:
    :return:
    """

    app.register_blueprint(api_v1.product.api, url_prefix='/api/v1/product')
    app.register_blueprint(api_v1.orders.api, url_prefix='/api/v1/orders')
    app.register_blueprint(api_v1.cart_items.api, url_prefix='/api/v1/cart_items')
    app.register_blueprint(api_v1.user.api, url_prefix='/api/v1/user')
    app.register_blueprint(api_v1.history.api, url_prefix='/api/v1/history')
    app.register_blueprint(api_v1.reviews.api, url_prefix='/api/v1/reviews')
    app.register_blueprint(api_v1.picture.api, url_prefix='/api/v1/picture')
    app.register_blueprint(api_v1.report.api, url_prefix='/api/v1/report')
    app.register_blueprint(api_v1.fire_base.api, url_prefix='/api/v1/fire_base')


def add_messages_to_redis():
    messages = Message.query.all()
    for message in messages:
        key = f"message:{message.message_id}"
        value = {
            "id": message.id,
            "message_id": message.message_id,
            "description": message.description,
            "status": message.status,
            "message": message.message,
        }
        red.set(key, json.dumps(value))





