# -*- coding: utf-8 -*-

import traceback
from time import strftime
from flask import Flask, request
from flask_cors import CORS
from app.extensions import jwt, logger, db, migrate
from .api import v1 as api_v1
from .settings import PrdConfig
from .utils import send_result


def create_app(config_object=PrdConfig):
    """
    Init App
    :param config_object:
    :return:
    """
    app = Flask(__name__, static_url_path="", static_folder="./files")
    app.config.from_object(config_object)
    register_extensions(app)
    register_monitor(app)
    register_blueprints(app)
    CORS(app)

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

        return "Internal Server Error", 500


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
