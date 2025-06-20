import pytest
from flask import session
from unittest.mock import patch
from models import User, Teacher, Group
from models.exercise import TeacherExercise
import os

class TestWebInterface:
    def test_login_page_loads(self, client):
        response = client.get('/login')
        assert response.status_code == 200
        assert b"Teacher Login" in response.data

    def test_successful_login(self, client, approved_teacher_user):
        #response = client.post('/login', data={'api_token': approved_teacher_user.
        #teacher_profile.api_token}, follow_redirects=True)
        response = client.post('/login', data={'api_token': 'valid-test-token'}, follow_redirects=True)
        assert response.status_code == 200
        assert b"Teacher Dashboard" in response.data
        with client.session_transaction() as sess:
            assert sess['user_id'] == approved_teacher_user.id

    def test_failed_login_invalid_token(self, client):
        response = client.post('/login', data={'api_token': 'invalid-token'}, follow_redirects=True)
        assert response.status_code == 200
        assert b"Invalid API Token" in response.data

    def test_dashboard_access_unauthorized(self, client):
        response = client.get('/dashboard', follow_redirects=True)
        assert response.status_code == 200
        assert b"Teacher Login" in response.data

    def test_dashboard_access_authorized(self, client, approved_teacher_user):
        # client.post('/login', data={'api_token': approved_teacher_user.teacher_profile.
        # api_token})
        client.post('/login', data={'api_token': 'valid-test-token'})
        response = client.get('/dashboard')
        assert response.status_code == 200
        assert f"Welcome, {approved_teacher_user.first_name}".encode() in response.data

    def test_logout(self, client, approved_teacher_user):
        client.post('/login', data={'api_token': 'valid-test-token'})
        # client.post('/login', data={'api_token': approved_teacher_user.teacher_profile.
        # api_token})
        response = client.get('/logout', follow_redirects=True)
        assert response.status_code == 200
        assert b"Teacher Login" in response.data

    def test_get_groups_unauthorized(self, client):
        response = client.get('/api/groups')
        assert response.status_code == 302

    def test_get_groups_authorized_empty(self, client, approved_teacher_user):
        client.post('/login', data={'api_token': 'valid-test-token'})
        # client.post('/login', data={'api_token': approved_teacher_user.teacher_profile.
        # api_token})
        response = client.get('/api/groups')
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert data['data'] == []

    def test_create_and_get_group(self, client, approved_teacher_user):
        client.post('/login', data={'api_token': 'valid-test-token'})
        # client.post('/login', data={'api_token': approved_teacher_user.teacher_profile.
        # api_token})
        create_response = client.post('/api/groups', json={'name': 'Test Group Alpha', 'description': 'A new test group.'})
        assert create_response.status_code == 201
        
        get_response = client.get('/api/groups')
        get_data = get_response.get_json()
        assert get_data['success'] is True
        assert len(get_data['data']) == 1
        assert get_data['data'][0]['name'] == 'Test Group Alpha'

    def test_get_exercises_unauthorized(self, client):
        response = client.get('/api/exercises')
        assert response.status_code == 302

    def test_get_exercises_authorized_empty(self, client, approved_teacher_user):
        client.post('/login', data={'api_token': 'valid-test-token'})
        # client.post('/login', data={'api_token': approved_teacher_user.teacher_profile.
        # api_token})
        response = client.get('/api/exercises')
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert data['data'] == []

    def test_create_and_get_exercise(self, client, approved_teacher_user, session):
        client.post('/login', data={'api_token': 'valid-test-token'})
        # client.post('/login', data={'api_token': approved_teacher_user.teacher_profile.
        # api_token})
        create_resp = client.post('/api/exercises', json={
            'title': 'New API Exercise', 'description': 'A detailed description.',
            'exercise_type': 'writing', 'difficulty': 'hard',
            'content': {'task': 'Write an essay.'}
        })
        assert create_resp.status_code == 201
        
        get_resp = client.get('/api/exercises')
        get_data = get_resp.get_json()
        assert get_data['success'] is True
        assert len(get_data['data']) >= 1
        assert get_data['data'][0]['title'] == 'New API Exercise'

    def test_get_specific_group_authorized(self, client, session, approved_teacher_user):
        client.post('/login', data={'api_token': 'valid-test-token'})
        # client.post('/login', data={'api_token': approved_teacher_user.teacher_profile.
        # api_token})
        group = Group(name="My Test Group", teacher_id=approved_teacher_user.id)
        session.add(group)
        session.commit()
        res = client.get(f'/api/groups/{group.id}')
        assert res.status_code == 200
        data = res.get_json()
        assert data['success'] is True
        assert data['data']['name'] == 'My Test Group'

    def test_get_specific_group_unauthorized(self, client, session, approved_teacher_user, another_teacher_user):
        client.post('/login', data={'api_token': "another-valid-token"})
        # client.post('/login', data={'api_token': approved_teacher_user.teacher_profile.
        # api_token})
        group = Group(name="Not My Group", teacher_id=approved_teacher_user.id)
        session.add(group)
        session.commit()
        res = client.get(f'/api/groups/{group.id}')
        assert res.status_code == 403

    def test_update_specific_group(self, client, session, approved_teacher_user):
        client.post('/login', data={'api_token': 'valid-test-token'})
        # client.post('/login', data={'api_token': approved_teacher_user.teacher_profile.
        # api_token})
        group = Group(name="Old Name", description="Old Desc", teacher_id=approved_teacher_user.id)
        session.add(group)
        session.commit()
        update_res = client.put(f'/api/groups/{group.id}', json={'name': 'New Name', 'description': 'New Desc'})
        assert update_res.status_code == 200
        updated_group = session.query(Group).get(group.id)
        assert updated_group.name == 'New Name'

    def test_get_specific_exercise_authorized(self, client, session, approved_teacher_user):
        client.post('/login', data={'api_token': 'valid-test-token'})
        # client.post('/login', data={'api_token': approved_teacher_user.teacher_profile.
        # api_token})
        exercise = TeacherExercise(
            title="My Exercise", creator_id=approved_teacher_user.id,
            exercise_type='speaking', difficulty='easy', content={'q': 'a'}
        )
        session.add(exercise)
        session.commit()
        resp = client.get(f'/api/exercises/{exercise.id}')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['success'] is True
        assert data['data']['title'] == "My Exercise"

    def test_get_specific_exercise_unauthorized(self, client, session, approved_teacher_user, another_teacher_user):
        client.post('/login', data={'api_token': "another-valid-token"})
        # client.post('/login', data={'api_token': approved_teacher_user.teacher_profile.
        # api_token})
        exercise = TeacherExercise(
            title="Not My Exercise", creator_id=approved_teacher_user.id,
            exercise_type='speaking', difficulty='easy', content={'q': 'a'}
        )
        session.add(exercise)
        session.commit()
        resp = client.get(f'/api/exercises/{exercise.id}')
        assert resp.status_code == 403

    def test_update_specific_exercise(self, client, session, approved_teacher_user):
        client.post('/login', data={'api_token': 'valid-test-token'})
        # client.post('/login', data={'api_token': approved_teacher_user.teacher_profile.
        # api_token})
        exercise = TeacherExercise(
            title="Old Title", description="Old Desc", creator_id=approved_teacher_user.id,
            exercise_type='speaking', difficulty='easy', content={'q': 'a'}
        )
        session.add(exercise)
        session.commit()
        update_data = {
            'title': 'New Title', 'description': 'New Desc',
            'difficulty': 'medium', 'is_published': True
        }
        resp = client.put(f'/api/exercises/{exercise.id}', json=update_data)
        assert resp.status_code == 200
        updated_exercise = session.query(TeacherExercise).get(exercise.id)
        assert updated_exercise.title == 'New Title'
        assert updated_exercise.is_published is True