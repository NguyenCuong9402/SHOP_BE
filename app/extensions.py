import logging
import os

from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from flask_migrate import Migrate
from flask_marshmallow import Marshmallow

from logging.handlers import RotatingFileHandler


jwt = JWTManager()

# init SQLAlchemy
db = SQLAlchemy()
migrate = Migrate()
ma = Marshmallow()

os.makedirs("logs", exist_ok=True)
# logger
logger = logging.getLogger('api')
logger.setLevel(logging.INFO)
# create file handler which logs even debug messages
# fh = logging.FileHandler('app.log')
fh = RotatingFileHandler('logs/app.log', maxBytes=1000000, backupCount=30, encoding="UTF-8")
fh.setLevel(logging.ERROR)
# create console handler with a higher log level
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
# create formatter and add it to the handlers
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
fh.setFormatter(formatter)
ch.setFormatter(formatter)
# add the handlers to the logger
logger.addHandler(fh)
logger.addHandler(ch)
