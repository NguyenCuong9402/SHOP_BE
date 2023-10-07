import os

os_env = os.environ


class Config(object):
    SECRET_KEY = 'AHA'
    APP_DIR = os.path.abspath(os.path.dirname(__file__))  # This directory
    PROJECT_ROOT = os.path.abspath(os.path.join(APP_DIR, os.pardir))
    VERSION = "v1.0.0"
    FLASK_ADMIN_SWATCH = "cerulean"


class DevConfig(Config):
    """Development configuration."""
    # app config
    ENV = 'dev'
    DEBUG = True
    DEBUG_TB_ENABLED = True  # Disable Debug toolbar
    TEMPLATES_AUTO_RELOAD = True
    HOST = '0.0.0.0'
    PORT = 5000
    # JWT Config
    JWT_SECRET_KEY = 'HA560##$shls12'
    JWT_BLACKLIST_ENABLED = True
    JWT_BLACKLIST_TOKEN_CHECKS = ['access', 'refresh']

    # mysql config
    SQLALCHEMY_DATABASE_URI = 'mysql://root:cuong942002@127.0.0.1:3306/shop_quan_ao'
    SQLALCHEMY_TRACK_MODIFICATIONS = True

    # upload config
    UPLOAD_FOLDER = "app/files"
