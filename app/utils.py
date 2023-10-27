
from flask import jsonify

from werkzeug.security import generate_password_hash
from pytz import timezone
import datetime
from app.models import Message
from time import time
import string
import random
from datetime import datetime


def send_result(data: any = None, message_id: str = '', message: str = "OK", code: int = 200,
                status: str = 'success', show: bool = False, duration: int = 0,
                val_error: dict = None, is_dynamic=False):
    """
    Args:
        data: simple result object like dict, string or list
        message: message send to client, default = OK
        code: code default = 200
        version: version of api
    :param data:
    :param message_id:
    :param message:
    :param code:
    :param status:
    :param show:
    :param duration:
    :param val_error:
    :param is_dynamic:
    :return:
    json rendered sting result
    """
    message_dict = {
        "id": message_id,
        "text": message,
        "status": status,
        "show": show,
        "duration": duration,
        "dynamic": is_dynamic
    }
    message_obj = Message.query.filter_by(message_id=message_id).first()
    if message_obj:
        if message_dict['dynamic'] == 0:
            message_dict['text'] = message_obj.message
        else:
            message_dict['text'] = message_obj.message.format(**val_error)
        message_dict['status'] = message_obj.status
        message_dict['show'] = message_obj.show
        message_dict['duration'] = message_obj.duration

    res = {
        "code": code,
        "data": data,
        "message": message_dict,
    }

    return jsonify(res), 200


def send_error(data: any = None, message_id: str = '', message: str = "Error", code: int = 200,
               status: str = 'error', show: bool = False, duration: int = 0,
               val_error: dict = None, is_dynamic=False):
    """
    :param data:
    :param message_id:
    :param message:
    :param code:
    :param status:
    :param show:
    :param duration:
    :param is_dynamic:
    :param val_error:
    :return:
    """
    if val_error is None:
        val_error = {}
    message_dict = {
        "id": message_id,
        "text": message,
        "status": status,
        "show": show,
        "duration": duration,
        "dynamic": is_dynamic
    }
    message_obj = Message.query.filter_by(message_id=message_id).first()
    if message_obj:
        if message_dict['dynamic'] == 0:
            message_dict['text'] = message_obj.message
        else:
            message_dict['text'] = message_obj.message.format(**val_error)

        message_dict['status'] = message_obj.status
        message_dict['show'] = message_obj.show
        message_dict['duration'] = message_obj.duration

    res = {
        "code": code,
        "data": data,
        "message": message_dict,
    }

    return jsonify(res), code


def hash_password(str_pass):
    """

    Args:
        str_pass:

    Returns:

    """
    return generate_password_hash(str_pass)


def get_timestamp_now():
    """
        Returns:
            current time in timestamp
    """
    return int(time())


def get_datetime_now() -> datetime:
    """
        Returns:
            current datetime
    """
    time_zon_sg = timezone('Asia/Ho_Chi_Minh')
    return datetime.datetime.now(time_zon_sg)


def data_preprocessing(cls_validator, input_json: dict):
    """
    Data preprocessing trim then check validate
    :param cls_validator:
    :param input_json:
    :return: status of class validate
    """
    for key, value in input_json.items():
        if isinstance(value, str):
            input_json[key] = value.strip()
    return cls_validator().custom_validate(input_json)


def validate_request(validator, request):
    try:
        json_req = request.get_json()
    except Exception as ex:
        return send_error(message="Request Body incorrect json format: " + str(ex), code=442)

        # Strip body request
    body_request = {}
    for key, value in json_req.items():
        if isinstance(value, str):
            body_request.setdefault(key, value.strip())
        else:
            body_request.setdefault(key, value)

    # Validate body request
    is_not_validate = validator.validate(body_request)
    if is_not_validate:
        return False, is_not_validate, body_request
    else:
        return True, {}, body_request


def escape_wildcard(search):
    """
    :param search:
    :return:
    """
    search1 = str.replace(search, '\\', r'\\')
    search2 = str.replace(search1, r'%', r'\%')
    search3 = str.replace(search2, r'_', r'\_')
    search4 = str.replace(search3, r'[', r'\[')
    search5 = str.replace(search4, r'"', r'\"')
    search6 = str.replace(search5, r"'", r"\'")
    return search6


def generate_password():
    """
    :return: random password
    """
    symbol_list = ["a", "b", "c", "d", "e", "f", "k"]
    number = '0123456789'
    letters_and_digits = string.ascii_letters + string.digits
    result_str = ''.join(random.choices(letters_and_digits, k=6))
    return '{}{}{}'.format(result_str, random.choice(symbol_list), random.choice(number))


def format_birthday(date_string):
    # Chuyển đổi chuỗi thành đối tượng datetime
    date_obj = datetime.strptime(date_string, '%Y-%m-%dT%H:%M:%S.%fZ')

    # Chuyển đối tượng datetime thành chuỗi định dạng mong muốn
    formatted_birthday = date_obj.strftime('%Y-%m-%d')

    return formatted_birthday


def is_valid_birthday(date_string):
    try:
        date_obj = datetime.strptime(date_string, '%Y-%m-%dT%H:%M:%S.%fZ')
        return True
    except ValueError:
        return False
