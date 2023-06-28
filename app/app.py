# -*- coding: utf-8 -*-
import os
import traceback

from flask import Flask, jsonify

from flask_cors import CORS
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView

from app.blocklist import BLOCKLIST
from app.extensions import jwt, migrate, ma
from app.models import db, Message
from app.api import v1 as api_v1
from app.settings import DevConfig
from app.models import db, Product, User, Orders, OrderItems, CartItems


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

    @jwt.token_in_blocklist_loader
    def check_if_token_in_blocklist(jwt_header, jwt_payload):
        return jwt_payload["jti"] in BLOCKLIST

    # mã đã thu hồi
    @jwt.revoked_token_loader
    def revoked_token_callback(jwt_header, jwt_payload):
        return (
            jsonify(
                {"description": "the token has been revoked", "error": " token_revoked"}
            ), 401
        )

    # yêu cầu làm mới
    @jwt.needs_fresh_token_loader
    def token_not_fresh_callback(jwt_header, jwt_payload):
        return (
            jsonify(
                {
                    "description": "the token is not fresh",
                    "error": " fresh_token_required"
                }
            ), 401
        )

    # set admin
    @jwt.additional_claims_loader
    def add_claims_to_jwt(identity):
        user = User.query.filter(User.id == identity).first()
        if user.admin == 1:
            return {"is_admin": True}
        return {"is_admin": False}

    # mã đã hết hạn
    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        return jsonify({"mes": "the token has expired.", "error": " token_expired"}), 401

    # mã không hợp lệ
    @jwt.invalid_token_loader
    def invalid_token_callback(error):
        return jsonify({"mes": "signature verification failed.", "error": " invalid_expired"}), 401

    @jwt.unauthorized_loader
    def missing_token_callback(error):
        return (jsonify(
            {"description": " Request does not contain an access token",
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

    # Flask Admin
    admin = Admin(app, name='admin management', template_mode='bootstrap3')
    admin.add_view(ModelView(Message, db.session))


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







