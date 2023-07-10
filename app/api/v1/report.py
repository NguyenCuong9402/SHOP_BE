import os
import uuid
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