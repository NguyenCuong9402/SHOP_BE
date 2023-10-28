import os
import uuid

import xlsxwriter
from flask import Blueprint, request, make_response, send_file, Response
from flask_jwt_extended import get_jwt_identity, get_jwt, jwt_required
from sqlalchemy import asc, desc
from io import BytesIO
import datetime
import io

from werkzeug.utils import secure_filename

from app.api.v1.picture import FILE_PATH, FILE_PATH_PRODUCT
from app.models import db, Product, User, Orders, OrderItems, CartItems
from app.schema import ProductSchema
from app.utils import send_error, get_timestamp_now, send_result, escape_wildcard

api = Blueprint('report', __name__)


@api.route("", methods=["GET"])
@jwt_required()
def report():
    try:
        jwt = get_jwt()
        user_id = get_jwt_identity()
        user = User.query.filter(User.id == user_id).first()
        if user.admin == 0 or (not jwt.get("is_admin")):
            return send_result(message="Bạn không phải admin.")
        products = Product.query.filter().order_by(desc(Product.revenue)).all()
        data = ProductSchema(many=True).dump(products)
        return send_result(data=data)
    except Exception as ex:
        return send_error(message=str(ex))


@api.route("/export", methods=["GET"])
@jwt_required()
def export():
    try:
        jwt = get_jwt()
        user_id = get_jwt_identity()
        day = datetime.date.today()
        output = io.BytesIO()
        filename = f'ThongKe_{day}.xlsx'
        workbook = xlsxwriter.Workbook(output)
        worksheet = workbook.add_worksheet(name="Sheet1")
        center_format = workbook.add_format({'align': 'center', 'border': 1, 'font_size': 11,
                                             'font_name': 'Times New Roman'})
        center_format_title = workbook.add_format({'align': 'center', 'border': 1, 'font_size': 11,
                                                   'bg_color': '#92d050', 'font_name': 'Times New Roman'})
        worksheet.set_column(0, 0, 30)
        worksheet.set_column(0, 1, 30)
        worksheet.set_column(0, 2, 20)
        worksheet.set_column(0, 3, 20)
        worksheet.set_column(0, 4, 35)
        worksheet.set_column(0, 5, 20)

        worksheet.merge_range(0, 0, 0, 4, f'Thống Kê',
                              workbook.add_format({'font_name': 'Times New Roman', 'bold': True, 'font_size': 14,
                                                   'align': 'center', 'valign': 'vcenter', 'border': 1}))
        worksheet.write(1, 0, "TÊN", center_format_title)
        worksheet.write(1, 1, "GIÁ", center_format_title)
        worksheet.write(1, 2, "Phân Loại", center_format_title)
        worksheet.write(1, 3, "Số lượng bán", center_format_title)
        worksheet.write(1, 4, "Doanh Thu($)", center_format_title)
        worksheet.write(1, 5, "Giảm giá", center_format_title)

        products = Product.query.filter().all()
        data = ProductSchema(many=True).dump(products)
        datas = sorted(data, key=lambda x: x["revenue"], reverse=True)

        for index, data in enumerate(datas):
            worksheet.write(2+index, 0, data["name"], center_format)
            worksheet.write(2+index, 1, data["old_price"], center_format)
            worksheet.write(2+index, 2, data["phan_loai"], center_format)
            worksheet.write(2+index, 3, data["count_sold"], center_format)
            worksheet.write(2+index, 4, data["revenue"], center_format)
            worksheet.write(2+index, 5, data["giam_gia"], center_format)

            # Sheet2
        chart = workbook.add_chart({'type': 'column'})
        worksheet2 = workbook.add_worksheet(name="Sheet2")
        # Tạo biểu đồ
        chart.add_series({
            'name': "Doanh thu(VND)",
            'categories': '=Sheet1!%s' % xlsxwriter.utility.xl_range(2, 0, 1 + len(datas), 0),
            'values': '=Sheet1!%s' % xlsxwriter.utility.xl_range(2, 4, 1 + len(datas), 4),
            'data_labels': {'value': True}
        })
        chart.add_series({
            'name': "Số lượng bán",
            'categories': '=Sheet1!%s' % xlsxwriter.utility.xl_range(2, 0, 1 + len(datas), 0),
            'values': '=Sheet1!%s' % xlsxwriter.utility.xl_range(2, 3, 1 + len(datas), 3),
            'data_labels': {'value': True}
        })
        chart.set_x_axis({'name': 'Tên Sản Phẩm'})
        chart.set_y_axis({'name': ''})
        # Đặt tiêu đề cho biểu đồ
        chart.set_title({'name': 'Thống kê'})
        chart.set_size({'width': 2 * chart.width, 'height': 2 * chart.height})

        # Thêm biểu đồ vào Sheet
        worksheet2.insert_chart('A1', chart)
        workbook.close()
        excel_data = output.getvalue()
        return send_file(io.BytesIO(excel_data), attachment_filename=filename, as_attachment=True)
    except Exception as ex:
        return send_error(message=str(ex))
