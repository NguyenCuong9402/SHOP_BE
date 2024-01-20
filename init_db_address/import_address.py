import json
import os
import uuid

import pandas as pd
from flask import Flask

from app.models import DiaChiVN
from app.extensions import db
from app.settings import DevConfig

CONFIG = DevConfig


class Worker:
    def __init__(self):
        app = Flask(__name__)
        app.config.from_object(CONFIG)
        db.app = app
        db.init_app(app)
        app_context = app.app_context()
        app_context.push()

    def import_message(self):
        file_name = "DiaChiVN.xls"
        # import permission
        df = pd.read_excel(file_name, sheet_name='Sheet1')
        list_add_message = []
        # Lặp qua từng hàng của DataFrame và thêm vào cơ sở dữ liệu
        for index, row in df.iterrows():
            if pd.isna(row["ID"]):
                print(index)
                continue  # Skip the current iteration
            address = DiaChiVN(
                id=str(uuid.uuid4()),
                tinh=row["Tên Tỉnh"],
                huyen=row["Tên QH"],
                xa=row["Tên Xã"]
            )
            list_add_message.append(address)
        db.session.bulk_save_objects(list_add_message)
        db.session.commit()


if __name__ == '__main__':
    print("=" * 10, f"Starting update message to the database on the uri: {CONFIG.SQLALCHEMY_DATABASE_URI}", "=" * 10)
    worker = Worker()
    worker.import_message()
    print("=" * 50, "update rbac", "=" * 50)