"""
Author: LucDV
Created Date: 21/01/2022
Target: UT for APIs Admin manage News & Events
"""
import json

from app.utils import get_timestamp_now

ARTICLE_ID = ''
TEST_EXECUTION_NOT_EXIST = '119'
ADD_ISSUE_TO_EXECUTION = '18'
REMOVE_ISSUE_TO_EXECUTION = '16'


def test_get_issue_in_test_execution(client):
    """Login with admin user
    Return:
        access_token: string
    """
    # get access token
    response = client.get(
        '/api/v1/testexec/1'
    )
    json_response = json.loads(response.data.decode())
    message = json_response['message']
    data = json_response['data']
    assert 200 == json_response['code']


def test_add_issue_in_test_execution(client):
    """
    GIVEN admin access_token
    WHEN input correct parameter
    THEN check status
    """
    # access_token = login_with_admin_user(client)
    response = client.post(
        '/api/v1/testexec/1',
        json={
            "issue_id": ['1', '2'],
        }
    )
    json_response = json.loads(response.data.decode())
    message = json_response['message']
    data = json_response['data']
    assert 200 == json_response['code']  # check code is 200
    assert message.get('status') == 'success'
    assert message.get('id') == ADD_ISSUE_TO_EXECUTION  # message id add issue successfully


def test_remove_issue_in_test_execution(client):
    """
    GIVEN admin access_token
    WHEN get articles by pagesize and page number
    THEN check status
    """
    response = client.delete(
        '/api/v1/testexec/1',
        json={
            "issue_id": ['1', '2'],
        }
    )
    json_response = json.loads(response.data.decode())
    message = json_response['message']
    data = json_response['data']
    assert 200 == json_response['code']  # check code is 200
    assert message.get('id') == REMOVE_ISSUE_TO_EXECUTION  # message id remove issue successfully



