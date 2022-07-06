import os

os_env = os.environ


class Config(object):
    SECRET_KEY = 'HA560##$shls12'
    APP_DIR = os.path.abspath(os.path.dirname(__file__))  # This directory
    PROJECT_ROOT = os.path.abspath(os.path.join(APP_DIR, os.pardir))


class PrdConfig(Config):
    """Production configuration."""
    # app config
    ENV = 'prd'
    DEBUG = False
    DEBUG_TB_ENABLED = False  # Disable Debug toolbar
    HOST = '0.0.0.0'
    PORT = 5000
    TEMPLATES_AUTO_RELOAD = False

    # JWT Config
    JWT_SECRET_KEY = 'HA560##$shls12'
    JWT_BLACKLIST_ENABLED = True
    JWT_BLACKLIST_TOKEN_CHECKS = ['access', 'refresh']

    # mysql config
    SQLALCHEMY_DATABASE_URI = 'mysql://<username>:<password>@<host>:<port>/<db_name>'
    SQLALCHEMY_TRACK_MODIFICATIONS = True


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
    SQLALCHEMY_DATABASE_URI = 'mysql://<username>:<password>@<host>:<port>/<db_name>'
    SQLALCHEMY_TRACK_MODIFICATIONS = True