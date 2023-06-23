# -*- coding: utf-8 -*-
import os
import traceback

from time import strftime
from flask import Flask, request

from flask_cors import CORS
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView
from werkzeug.exceptions import NotFound

from app.extensions import jwt, migrate, ma
from app.models import db, Message
from app.api import v1 as api_v1
from app.settings import DevConfig
from app.utils import send_result, send_error


def create_app():
    """
    Init App
    :return:
    """
    config_object =  DevConfig
    app = Flask(__name__, static_url_path="", static_folder="./files")
    app.config.from_object(config_object)
    register_extensions(app)
    register_blueprints(app)
    CORS(app, resources={r"/api/v1/*": {"origins": "*"}})

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

    app.register_blueprint(api_v1.product.api, url_prefix='/api/v1/report')







