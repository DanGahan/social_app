import sys
import os
import pytest
from unittest.mock import patch, MagicMock
from app import app, session
from models import User, Connection, ConnectionRequest, Post
from werkzeug.security import generate_password_hash
import jwt
import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

@pytest.fixture
def mock_jwt_decode():
    with patch('jwt.decode') as mock_decode:
        mock_decode.return_value = {'user_id': 1}
        yield mock_decode

@patch('app.session.query')
def test_register_user_email_exists(mock_query, client):
    mock_query.return_value.filter_by.return_value.first.return_value = User(email='existing@example.com')
    response = client.post('/auth/register', json={
        'email': 'existing@example.com',
        'password': 'password123'
    })
    assert response.status_code == 409

@patch('app.session.query')
def test_login_user_success(mock_query, client):
    mock_user = User(id=1, email='test@example.com', password_hash=generate_password_hash('password123'))
    mock_query.return_value.filter_by.return_value.first.return_value = mock_user
    response = client.post('/auth/login', json={
        'email': 'test@example.com',
        'password': 'password123'
    })
    assert response.status_code == 200

@patch('app.session.query')
def test_get_current_user_success(mock_query, client, mock_jwt_decode):
    mock_user = User(id=1, email='current@example.com', display_name='Current User')
    mock_query.return_value.filter_by.return_value.first.return_value = mock_user
    response = client.get('/users/me', headers={'x-access-token': 'valid_token'})
    assert response.status_code == 200
    assert response.json['email'] == 'current@example.com'

@patch('app.session.query')
def test_get_user_profile_success(mock_query, client, mock_jwt_decode):
    mock_user = User(id=2, email='other@example.com', display_name='Other User')
    mock_query.return_value.filter_by.return_value.first.return_value = mock_user
    response = client.get('/users/2/profile', headers={'x-access-token': 'valid_token'})
    assert response.status_code == 200

@patch('app.session.query')
def test_request_connection_success(mock_query, client, mock_jwt_decode):
    mock_current_user = User(id=1)
    mock_to_user = User(id=2)
    mock_query.return_value.filter_by.side_effect = [
        MagicMock(first=MagicMock(return_value=mock_current_user)), # for token_required
        MagicMock(first=MagicMock(return_value=None)), # for existing_connection
    ]
    with patch('app.session.add'), patch('app.session.commit'):
        response = client.post('/connections/request', json={'to_user_id': 2}, headers={'x-access-token': 'valid_token'})
    assert response.status_code == 201

@patch('app.session.query')
def test_request_connection_already_connected(mock_query, client, mock_jwt_decode):
    mock_current_user = User(id=1)
    mock_to_user = User(id=2)
    mock_query.return_value.filter_by.side_effect = [
        MagicMock(first=MagicMock(return_value=mock_current_user)), # for token_required
        MagicMock(first=MagicMock(return_value=Connection(user_id1=1, user_id2=2))), # for existing_connection
    ]
    response = client.post('/connections/request', json={'to_user_id': 2}, headers={'x-access-token': 'valid_token'})
    assert response.status_code == 409

@patch('app.session.query')
def test_accept_connection_success(mock_query, client, mock_jwt_decode):
    mock_current_user = User(id=1)
    mock_request = ConnectionRequest(id=1, from_user_id=2, to_user_id=1, status='pending')
    mock_query.return_value.filter_by.side_effect = [
        MagicMock(first=MagicMock(return_value=mock_current_user)), # for token_required
        MagicMock(first=MagicMock(return_value=mock_request)),
    ]
    with patch('app.session.add'), patch('app.session.commit'):
        response = client.post('/connections/accept', json={'request_id': 1}, headers={'x-access-token': 'valid_token'})
    assert response.status_code == 200
    assert response.json['message'] == 'Connection accepted successfully'

@patch('app.session.query')
def test_get_sent_requests_success(mock_query, client, mock_jwt_decode):
    mock_current_user = User(id=1)
    mock_user_2 = User(id=2, email='user2@example.com', display_name='User Two')
    mock_request_1 = ConnectionRequest(id=10, from_user_id=1, to_user_id=2, status='pending', created_at=datetime.datetime.utcnow())
    mock_query.return_value.filter_by.side_effect = [
        MagicMock(first=MagicMock(return_value=mock_current_user)), # for token_required
        MagicMock(all=MagicMock(return_value=[mock_request_1])),
        MagicMock(first=MagicMock(return_value=mock_user_2))
    ]
    response = client.get('/users/1/sent_requests', headers={'x-access-token': 'valid_token'})
    assert response.status_code == 200

@patch('app.session.query')
def test_get_pending_requests_success(mock_query, client, mock_jwt_decode):
    mock_current_user = User(id=1)
    mock_user_2 = User(id=2, email='user2@example.com', display_name='User Two')
    mock_request_1 = ConnectionRequest(id=10, from_user_id=2, to_user_id=1, status='pending', created_at=datetime.datetime.utcnow())
    mock_query.return_value.filter_by.side_effect = [
        MagicMock(first=MagicMock(return_value=mock_current_user)), # for token_required
        MagicMock(all=MagicMock(return_value=[mock_request_1])),
        MagicMock(first=MagicMock(return_value=mock_user_2))
    ]
    response = client.get('/users/1/pending_requests', headers={'x-access-token': 'valid_token'})
    assert response.status_code == 200

@patch('app.session.query')
def test_get_user_connections_success(mock_query, client, mock_jwt_decode):
    mock_current_user = User(id=1)
    mock_user_2 = User(id=2, email='user2@example.com', display_name='User Two')
    mock_connection_1 = Connection(user_id1=1, user_id2=2)
    mock_query.return_value.filter.return_value.all.return_value = [mock_connection_1]
    mock_query.return_value.filter_by.side_effect = [
        MagicMock(first=MagicMock(return_value=mock_current_user)), # for token_required
        MagicMock(first=MagicMock(return_value=mock_user_2))
    ]
    response = client.get('/users/1/connections', headers={'x-access-token': 'valid_token'})
    assert response.status_code == 200

@patch('app.session.query')
def test_get_user_posts_success(mock_query, client, mock_jwt_decode):
    mock_current_user = User(id=1, display_name='Test User', profile_picture_url='test.jpg')
    mock_post_1 = Post(id=1, caption='My first post', image_url='url1', created_at=datetime.datetime.utcnow(), user_id=1)
    mock_query.return_value.filter_by.return_value.order_by.return_value.all.return_value = [mock_post_1]
    mock_query.return_value.filter_by.return_value.first.return_value = mock_current_user # for token_required
    response = client.get('/users/1/posts', headers={'x-access-token': 'valid_token'})
    assert response.status_code == 200
    assert len(response.json) == 1

@patch('app.session.query')
def test_get_connections_posts_no_connections(mock_query, client, mock_jwt_decode):
    mock_current_user = User(id=1)
    mock_query.return_value.filter.return_value.all.return_value = []
    mock_query.return_value.filter_by.return_value.first.return_value = mock_current_user # for token_required
    response = client.get('/users/1/connections/posts', headers={'x-access-token': 'valid_token'})
    assert response.status_code == 200
