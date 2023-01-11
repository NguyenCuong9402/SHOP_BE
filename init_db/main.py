import json
from flask import Flask

from app.extensions import db
from app.models import User
from app.settings import DevConfig, PrdConfig, os

CONFIG = PrdConfig if os.environ.get('ENV') == 'prd' else DevConfig
default_file = "default.json"


class Worker:
    def __init__(self):
        app = Flask(__name__)

        app.config.from_object(CONFIG)
        db.app = app
        db.init_app(app)
        app_context = app.app_context()
        app_context.push()

        print("=" * 25, f"Starting init_db database on the uri: {CONFIG.SQLALCHEMY_DATABASE_URI}", "=" * 25)
        db.drop_all()  # drop all tables
        db.create_all()  # create a new schema

        with open(default_file, encoding='utf-8') as file:
            self.default_data = json.load(file)

    def insert_default_users(self):
        users = self.default_data.get('users', {})
        for item in users:
            instance = User()
            for key in item.keys():
                instance.__setattr__(key, item[key])
            db.session.add(instance)

        db.session.commit()

    def insert_default_test_step_fields(self):
        step_fields = self.default_data.get('test_step_fields', {})





if __name__ == '__main__':
    worker = Worker()
    worker.insert_default_users()
    print("=" * 50, "Database migration completed", "=" * 50)
