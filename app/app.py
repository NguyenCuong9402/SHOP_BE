# -*- coding: utf-8 -*-
import os
import traceback

from time import strftime
from flask import Flask, request

from flask_cors import CORS
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView
from werkzeug.exceptions import NotFound

from app.extensions import jwt, logger, migrate, ma
from app.models import db, Message, TestType
from app.api import v1 as api_v1
from app.settings import DevConfig, PrdConfig
from app.utils import send_result, send_error


def create_app():
    """
    Init App
    :return:
    """
    config_object = PrdConfig if os.environ.get('ENV') == 'prd' else DevConfig
    app = Flask(__name__, static_url_path="", static_folder="./files")
    app.config.from_object(config_object)
    register_extensions(app)
    register_monitor(app)
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
    admin = Admin(app, name='Btest admin management', template_mode='bootstrap3')
    admin.add_view(ModelView(Message, db.session))
    admin.add_view(ModelView(TestType, db.session))

    @app.after_request
    def after_request(response):
        """

        :param response:
        :return:
        """
        # This IF avoids the duplication of registry in the log, since that 500 is already logged via @app.errorhandler.
        if response.status_code != 500:
            ts = strftime('[%Y-%b-%d %H:%M]')
            logger.error('%s %s %s %s %s %s',
                         ts,
                         request.remote_addr,
                         request.method,
                         request.scheme,
                         request.full_path,
                         response.status)
        return response

    @app.errorhandler(Exception)
    def exceptions(e):
        """
        Handling exceptions
        :param e:
        :return:
        """
        ts = strftime('[%Y-%b-%d %H:%M]')
        tb = traceback.format_exc()
        message = "5xx INTERNAL SERVER ERROR"
        error = '{} {} {} {} {} {} {} \n{}'.format(ts, request.remote_addr, request.method, request.scheme,
                                                   request.full_path, message, str(e), tb)
        logger.error(error)
        db.session.rollback()  # rollback session

        return send_error(message=error, code=500)

    @app.errorhandler(NotFound)
    def exceptions(e):
        """
        Handling exceptions
        :param e:
        :return:
        """
        # ts = strftime('[%Y-%b-%d %H:%M]')
        # tb = traceback.format_exc()
        # message = "5xx INTERNAL SERVER ERROR"
        # error = '{} {} {} {} {} {} {} \n{}'.format(ts, request.remote_addr, request.method, request.scheme,
        #                                            request.full_path, message, str(e), tb)
        # logger.error(error)
        # db.session.rollback()  # rollback session

        return send_error(message="Request not found", code=400)


def register_monitor(app):
    @app.route("/", methods=['GET'])
    def health_check():
        return send_result()

    @app.route("/api/v1/helper/site-map", methods=['GET'])
    def site_map():
        links = []
        for rule in app.url_map.iter_rules():
            request_method = ""
            if "GET" in rule.methods:
                request_method = "get"
            if "PUT" in rule.methods:
                request_method = "put"
            if "POST" in rule.methods:
                request_method = "post"
            if "DELETE" in rule.methods:
                request_method = "delete"
            permission_route = "{0}@{1}".format(request_method.lower(), rule)
            links.append(permission_route)
        return send_result(data=sorted(links, key=lambda resource: str(resource).split('@')[-1]))


def register_blueprints(app):
    """
    Init blueprint for api url
    :param app:
    :return:
    """
    app.register_blueprint(api_v1.auth.api, url_prefix='/api/v1/auth')
    app.register_blueprint(api_v1.settings.api, url_prefix='/api/v1/setting')
    app.register_blueprint(api_v1.attachment.api, url_prefix='/api/v1/attachment')
    app.register_blueprint(api_v1.history_test.api, url_prefix='/api/v1/history_test')
    app.register_blueprint(api_v1.test_step_field.api, url_prefix='/api/v1/test_step_field')
    app.register_blueprint(api_v1.test_step.api, url_prefix='/api/v1/test_step')
    app.register_blueprint(api_v1.test_run_field.api, url_prefix='/api/v1/test_run_field')
    app.register_blueprint(api_v1.test_type.api, url_prefix='/api/v1/test_type')
    app.register_blueprint(api_v1.test_status.api, url_prefix='/api/v1/test_status')
    app.register_blueprint(api_v1.test_environment.api, url_prefix='/api/v1/test_environment')
    app.register_blueprint(api_v1.test_case.api, url_prefix='/api/v1/test_case')
    app.register_blueprint(api_v1.test_run.api, url_prefix='/api/v1/test_run')
    app.register_blueprint(api_v1.test_execution.api, url_prefix='/api/v1/test_execution')
    app.register_blueprint(api_v1.test_set.api, url_prefix='/api/v1/test_set')
    app.register_blueprint(api_v1.user_setting.api, url_prefix='/api/v1/user_setting')
    app.register_blueprint(api_v1.test_repository.api, url_prefix='/api/v1/test_repository')






