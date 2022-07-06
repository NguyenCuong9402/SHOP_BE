import os

from flask import Flask
from flask_admin import Admin

from flask_admin.contrib.sqla import ModelView

from app.extensions import db
from app.models import Message
from app.settings import PrdConfig, DevConfig

app = Flask(__name__)
config_object = PrdConfig if os.environ.get('ENV') == 'prd' else DevConfig
app.config.from_object(config_object)
db.app = app
db.init_app(app)
# Flask and Flask-SQLAlchemy initialization here

admin = Admin(app, name='microblog', template_mode='bootstrap3')
admin.add_view(ModelView(Message, db.session))

app.run()