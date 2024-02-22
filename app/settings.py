import os

os_env = os.environ


class Config(object):
    SECRET_KEY = 'AHA'
    APP_DIR = os.path.abspath(os.path.dirname(__file__))  # This directory
    PROJECT_ROOT = os.path.abspath(os.path.join(APP_DIR, os.pardir))
    VERSION = "v1.0.0"


class DevConfig(Config):
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
    # email config
    MAIL_SERVER = 'smtp.gmail.com'
    MAIL_PORT = 465
    MAIL_USERNAME = 'cuong09042002@gmail.com'
    MAIL_PASSWORD = 'cyeb cioq ynmo zirk'
    MAIL_DEFAULT_SENDER = 'cuong09042002@gmail.com'
    MAIL_USE_TLS = False
    MAIL_USE_SSL = True
    # redis config
    REDIS_HOST = '127.0.0.1'
    REDIS_PORT = 6379
    REDIS_DB = 1
    # REDIS_PASSWORD = 'cuong123456789'
