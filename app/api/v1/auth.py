from flask import Blueprint
from flask_jwt_extended import jwt_required, get_jwt_identity, create_access_token

from app.gateway import authorization_require
from app.utils import send_result

api = Blueprint('auth', __name__)


@api.route('/login', methods=['POST'])
def login():
    """ This is controller of the login api

    Requests Body:

    Returns:

    Examples::

    """

    data = {
        'access_token': "access_token",
        'refresh_token': "refresh_token",
        'username': "username",
        'user_id': "id",
        'display_name': "display_name"
    }
    access_token = create_access_token(identity="")

    return send_result(data=access_token, message="Logged in successfully!")


# Protect a route with jwt_required, which will kick out requests
# without a valid JWT present.
@api.route("/protected", methods=["GET"])
@authorization_require()
def protected():
    # Access the identity of the current user with get_jwt_identity
    return send_result(data={"status": "OK"}, message="Logged in successfully!")
