import pytest
from flask import session
from unittest.mock import patch
from models import User, Teacher

def test_login_page_loads(client):
    """Test that the login page loads correctly."""
    response = client.get('/login')
    assert response.status_code == 200
    assert b"Teacher Login" in response.data

def test_successful_login(client, session, approved_teacher_user):
    """Test a successful login with a valid token."""
    # Assign a token to the teacher
    token = "valid-test-token"
    teacher_profile = approved_teacher_user.teacher_profile
    teacher_profile.api_token = token
    session.commit()

    response = client.post('/login', data={'api_token': token}, follow_redirects=True)
    assert response.status_code == 200
    assert b"Welcome, Approved!" in response.data
    assert b"/logout" in response.data

def test_failed_login_invalid_token(client, session):
    """Test a failed login attempt with an invalid token."""
    response = client.post('/login', data={'api_token': 'invalid-token'}, follow_redirects=True)
    assert response.status_code == 200
    assert b"Invalid API Token" in response.data

def test_dashboard_access_unauthorized(client):
    """Test that unauthorized users are redirected from the dashboard."""
    response = client.get('/dashboard', follow_redirects=True)
    assert response.status_code == 200
    assert b"Teacher Login" in response.data # Should be on login page

def test_dashboard_access_authorized(client, approved_teacher_user, session):
    """Test that an authorized user can access the dashboard."""
    # Manually log in the user by setting the session
    with client.session_transaction() as sess:
        sess['user_id'] = approved_teacher_user.id
        sess['user_first_name'] = approved_teacher_user.first_name
    
    response = client.get('/dashboard')
    assert response.status_code == 200
    assert f"Welcome, {approved_teacher_user.first_name}!".encode() in response.data

def test_logout(client, approved_teacher_user):
    """Test that the logout function clears the session and redirects."""
    with client.session_transaction() as sess:
        sess['user_id'] = approved_teacher_user.id

    response = client.get('/logout', follow_redirects=True)
    assert response.status_code == 200
    assert b"Teacher Login" in response.data
    
    # Check that accessing dashboard again redirects to login
    response = client.get('/dashboard', follow_redirects=True)
    assert b"Teacher Login" in response.data

def test_get_groups_unauthorized(client):
    """Test that unauthorized users cannot get groups."""
    response = client.get('/api/groups')
    assert response.status_code == 302 # Redirect to login

def test_get_groups_authorized_empty(client, approved_teacher_user):
    """Test that an authorized teacher with no groups gets an empty list."""
    with client.session_transaction() as sess:
        sess['user_id'] = approved_teacher_user.id
    
    response = client.get('/api/groups')
    assert response.status_code == 200
    data = response.get_json()
    assert data['success'] is True
    assert data['data'] == []

def test_create_and_get_group(client, approved_teacher_user, session):
    """Test creating a group and then fetching it."""
    with client.session_transaction() as sess:
        sess['user_id'] = approved_teacher_user.id

    # Create a group
    create_response = client.post('/api/groups', json={
        'name': 'Test Group Alpha',
        'description': 'A new test group.'
    })
    assert create_response.status_code == 201
    create_data = create_response.get_json()
    assert create_data['success'] is True
    assert create_data['data']['name'] == 'Test Group Alpha'

    # Fetch groups and verify the new group is there
    get_response = client.get('/api/groups')
    assert get_response.status_code == 200
    get_data = get_response.get_json()
    assert get_data['success'] is True
    assert len(get_data['data']) == 1
    assert get_data['data'][0]['name'] == 'Test Group Alpha'

def test_get_exercises_unauthorized(client):
    """Test that unauthorized users cannot get exercises."""
    response = client.get('/api/exercises')
    assert response.status_code == 302 # Redirect to login

def test_get_exercises_authorized_empty(client, approved_teacher_user):
    """Test that an authorized teacher with no exercises gets an empty list."""
    with client.session_transaction() as sess:
        sess['user_id'] = approved_teacher_user.id
    
    response = client.get('/api/exercises')
    assert response.status_code == 200
    data = response.get_json()
    assert data['success'] is True
    assert data['data'] == []

def test_create_and_get_exercise(client, approved_teacher_user, session):
    """Test creating an exercise and then fetching it."""
    with client.session_transaction() as sess:
        sess['user_id'] = approved_teacher_user.id

    exercise_data = {
        'title': 'New Vocab Test',
        'description': 'A test for new vocabulary.',
        'exercise_type': 'vocabulary',
        'difficulty': 'hard',
        'content': {'questions': [{'q': 'What is a ...?'}]}
    }
    create_response = client.post('/api/exercises', json=exercise_data)
    assert create_response.status_code == 201
    create_data = create_response.get_json()
    assert create_data['success'] is True
    assert create_data['data']['title'] == 'New Vocab Test'

    # Fetch exercises and verify the new one is there
    get_response = client.get('/api/exercises')
    assert get_response.status_code == 200
    get_data = get_response.get_json()
    assert get_data['success'] is True
    assert len(get_data['data']) == 1
    assert get_data['data'][0]['title'] == 'New Vocab Test' 