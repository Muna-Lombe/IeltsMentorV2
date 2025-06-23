import pytest
from flask import session
from unittest.mock import patch
from models import User, Teacher, Group, GroupMembership, Homework, HomeworkSubmission
from models.exercise import TeacherExercise
from models.practice_session import PracticeSession
import os
from datetime import datetime, timedelta

class TestWebInterface:
    def test_login_page_loads(self, client):
        response = client.get('/login')
        assert response.status_code == 200
        assert b"Teacher Login" in response.data

    def test_successful_login(self, client, approved_teacher_user):
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
        client.post('/login', data={'api_token': 'valid-test-token'})
        response = client.get('/dashboard')
        assert response.status_code == 200
        assert f"Welcome, {approved_teacher_user.first_name}".encode() in response.data

    def test_logout(self, client, approved_teacher_user):
        client.post('/login', data={'api_token': 'valid-test-token'})
        response = client.get('/logout', follow_redirects=True)
        assert response.status_code == 200
        assert b"Teacher Login" in response.data

    def test_get_groups_unauthorized(self, client):
        response = client.get('/api/groups')
        assert response.status_code == 302 # Redirect to login

    def test_get_groups_authorized_empty(self, client, approved_teacher_user):
        client.post('/login', data={'api_token': 'valid-test-token'})
        response = client.get('/api/groups')
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert data['data'] == []

    def test_create_and_get_group(self, client, approved_teacher_user):
        client.post('/login', data={'api_token': 'valid-test-token'})
        create_response = client.post('/api/groups', json={'name': 'Test Group Alpha', 'description': 'A new test group.'})
        assert create_response.status_code == 201
        
        get_response = client.get('/api/groups')
        get_data = get_response.get_json()
        assert get_data['success'] is True
        assert len(get_data['data']) == 1
        assert get_data['data'][0]['name'] == 'Test Group Alpha'

    def test_get_exercises_unauthorized(self, client):
        response = client.get('/api/exercises')
        assert response.status_code == 302 # Redirect to login

    def test_get_exercises_authorized_empty(self, client, approved_teacher_user):
        client.post('/login', data={'api_token': 'valid-test-token'})
        response = client.get('/api/exercises')
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert data['data'] == []

    def test_create_and_get_exercise(self, client, approved_teacher_user):
        client.post('/login', data={'api_token': 'valid-test-token'})
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
        group = Group(name="My Test Group", teacher_id=approved_teacher_user.id)
        session.add(group)
        session.commit()
        res = client.get(f'/api/groups/{group.id}')
        assert res.status_code == 200
        data = res.get_json()
        assert data['success'] is True
        assert data['data']['name'] == 'My Test Group'

    def test_get_specific_group_unauthorized(self, client, session, approved_teacher_user, another_teacher):
        client.post('/login', data={'api_token': 'another-valid-token'})
        group = Group(name="Not My Group", teacher_id=approved_teacher_user.id)
        session.add(group)
        session.commit()
        res = client.get(f'/api/groups/{group.id}')
        assert res.status_code == 403

    def test_update_specific_group(self, client, session, approved_teacher_user):
        client.post('/login', data={'api_token': 'valid-test-token'})
        group = Group(name="Old Name", description="Old Desc", teacher_id=approved_teacher_user.id)
        session.add(group)
        session.commit()
        update_res = client.put(f'/api/groups/{group.id}', json={'name': 'New Name', 'description': 'New Desc'})
        assert update_res.status_code == 200
        updated_group = session.get(Group, group.id)
        assert updated_group.name == 'New Name'

    def test_get_specific_exercise_authorized(self, client, session, approved_teacher_user):
        client.post('/login', data={'api_token': 'valid-test-token'})
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

    def test_get_specific_exercise_unauthorized(self, client, session, approved_teacher_user, another_teacher):
        client.post('/login', data={'api_token': 'another-valid-token'})
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
        updated_exercise = session.get(TeacherExercise, exercise.id)
        assert updated_exercise.title == 'New Title'
        assert updated_exercise.is_published is True

    def test_add_and_remove_group_member(self, client, session, approved_teacher_user, regular_user):
        client.post('/login', data={'api_token': 'valid-test-token'})
        group_res = client.post('/api/groups', json={'name': 'Member Management Test', 'description': 'A group for testing member management.'})
        group_id = group_res.json['data']['id']
        
        add_res = client.post(f'/api/groups/{group_id}/members', json={'student_id': regular_user.id})
        assert add_res.status_code == 201
        
        get_res = client.get(f'/api/groups/{group_id}')
        members = get_res.json['data']['members']
        assert len(members) == 1
        assert members[0]['id'] == regular_user.id

        remove_res = client.delete(f'/api/groups/{group_id}/members/{regular_user.id}')
        assert remove_res.status_code == 200

        get_res_after_remove = client.get(f'/api/groups/{group_id}')
        members_after_remove = get_res_after_remove.json['data']['members']
        assert len(members_after_remove) == 0

    def test_get_student_details_authorized(self, client, session, approved_teacher_user, regular_user):
        client.post('/login', data={'api_token': 'valid-test-token'})
        group = Group(name="Test Group", teacher_id=approved_teacher_user.id)
        session.add(group)
        session.commit()
        membership = GroupMembership(group_id=group.id, student_id=regular_user.id)
        session.add(membership)
        session.commit()

        response = client.get(f'/api/students/{regular_user.id}')
        assert response.status_code == 200
        assert response.json['data']['id'] == regular_user.id

    def test_get_student_details_unauthorized(self, client, session, approved_teacher_user, another_teacher, regular_user):
        client.post('/login', data={'api_token': 'another-valid-token'})
        group = Group(name="Test Group", teacher_id=approved_teacher_user.id)
        session.add(group)
        session.commit()
        membership = GroupMembership(group_id=group.id, student_id=regular_user.id)
        session.add(membership)
        session.commit()

        response = client.get(f'/api/students/{regular_user.id}')
        assert response.status_code == 403
        assert response.json['error'] == "Unauthorized to view this student"

    def test_assign_and_get_homework(self, client, session, approved_teacher_user, regular_user):
        client.post('/login', data={'api_token': 'valid-test-token'})
        
        group = Group(name="Homework Group", teacher_id=approved_teacher_user.id)
        exercise = TeacherExercise(title="Homework Exercise", creator_id=approved_teacher_user.id, exercise_type='reading', difficulty='easy', content={'q':'a'})
        session.add_all([group, exercise])
        session.commit()
        
        due_date = datetime.utcnow() + timedelta(days=7)
        response = client.post('/api/homework', json={
            'exercise_id': exercise.id,
            'group_id': group.id,
            'due_date': due_date.isoformat(),
            'instructions': 'Test instructions'
        })
        assert response.status_code == 201
        homework_id = response.get_json()['data']['id']

        response = client.get('/api/homework')
        assert response.status_code == 200
        data = response.get_json()
        assert len(data['data']) == 1
        assert data['data'][0]['exercise_title'] == 'Homework Exercise'

        response = client.get(f'/api/homework/{homework_id}/submissions')
        assert response.status_code == 200
        assert len(response.get_json()['data']) == 0

    def test_assign_homework_unauthorized(self, client, session, approved_teacher_user, another_teacher):
        client.post('/login', data={'api_token': 'another-valid-token'})
        
        group = Group(name="Owned Group", teacher_id=approved_teacher_user.id)
        exercise = TeacherExercise(title="Owned Exercise", creator_id=approved_teacher_user.id, exercise_type='reading', difficulty='easy', content={'q':'a'})
        session.add_all([group, exercise])
        session.commit()

        response = client.post('/api/homework', json={
            'exercise_id': exercise.id,
            'group_id': group.id,
            'due_date': (datetime.utcnow() + timedelta(days=7)).isoformat(),
            'instructions': 'Test instructions'
        })
        assert response.status_code == 403
    
    def test_publish_exercise(self, client, session, approved_teacher_user):
        """Test publishing an exercise."""
        client.post('/login', data={'api_token': 'valid-test-token'})
        exercise = TeacherExercise(
            title="Publish Test", creator_id=approved_teacher_user.id,
            exercise_type='reading', difficulty='medium', content={'q':'1'},
            is_published=False
        )
        session.add(exercise)
        session.commit()

        response = client.post(f'/api/exercises/{exercise.id}/publish')
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert data['data']['is_published'] is True

        # Verify in DB
        updated_exercise = session.get(TeacherExercise, exercise.id)
        assert updated_exercise.is_published is True

    def test_get_group_analytics(self, client, session, approved_teacher_user, regular_user):
        client.post('/login', data={'api_token': 'valid-test-token'})

        # 1. Create a group and add the student
        group = Group(name="Analytics Test Group", teacher_id=approved_teacher_user.id)
        session.add(group)
        session.commit()
        membership = GroupMembership(group_id=group.id, student_id=regular_user.id)
        session.add(membership)
        
        # 2. Create some practice data
        p1 = PracticeSession(user_id=regular_user.id, section='reading', score=80)
        p2 = PracticeSession(user_id=regular_user.id, section='reading', score=90)
        p3 = PracticeSession(user_id=regular_user.id, section='writing', score=75)
        session.add_all([p1, p2, p3])
        session.commit()

        # 3. Call the analytics endpoint
        response = client.get(f'/api/analytics/groups/{group.id}')
        assert response.status_code == 200
        data = response.get_json()['data']

        # 4. Assert the analytics are correct
        assert data['group_name'] == "Analytics Test Group"
        assert data['member_count'] == 1
        assert data['average_scores_by_section']['reading'] == 85.0
        assert data['average_scores_by_section']['writing'] == 75.0

    def test_get_student_progress_authorized(self, client, session, approved_teacher_user, regular_user):
        """Test getting a student's progress data as an authorized teacher."""
        client.post('/login', data={'api_token': 'valid-test-token'})
        
        # Setup group and membership
        group = Group(name="Progress Test Group", teacher_id=approved_teacher_user.id)
        session.add(group)
        session.commit()
        membership = GroupMembership(group_id=group.id, student_id=regular_user.id)
        session.add(membership)

        # Setup practice session data for the student
        ps1 = PracticeSession(user_id=regular_user.id, section='reading', score=80, total_questions=10, correct_answers=8, completed_at=datetime.utcnow())
        ps2 = PracticeSession(user_id=regular_user.id, section='writing', score=75, total_questions=2, correct_answers=1, completed_at=datetime.utcnow())
        session.add_all([ps1, ps2])
        session.commit()

        response = client.get(f'/api/students/{regular_user.id}/progress')
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert len(data['data']['practice_sessions']) == 2
        assert data['data']['skill_level'] == regular_user.skill_level

    def test_get_student_progress_unauthorized(self, client, session, another_teacher, regular_user):
        """Test getting a student's progress as an unauthorized teacher."""
        client.post('/login', data={'api_token': 'another-valid-token'})
        
        # Student exists but is not in any of this teacher's groups
        response = client.get(f'/api/students/{regular_user.id}/progress')
        assert response.status_code == 403

    def test_get_exercise_analytics_authorized(self, client, session, approved_teacher_user, regular_user):
        """Test getting analytics for a specific exercise."""
        client.post('/login', data={'api_token': 'valid-test-token'})

        # Setup exercise, group, and homework
        exercise = TeacherExercise(title="Analytics Exercise", creator_id=approved_teacher_user.id, exercise_type='reading', difficulty='easy', content={'q':'a'})
        group = Group(name="Analytics Group", teacher_id=approved_teacher_user.id)
        session.add_all([exercise, group])
        session.commit()
        
        homework = Homework(exercise_id=exercise.id, group_id=group.id, assigned_by_id=approved_teacher_user.id)
        session.add(homework)
        session.commit()

        # Setup submissions
        sub1 = HomeworkSubmission(homework_id=homework.id, student_id=regular_user.id, score=80, content={"answer": "Student 1's answer"})
        # Create another user for more data
        student2 = User(user_id=998, first_name="Student", last_name="Two", username="studenttwo")
        session.add(student2)
        session.commit()
        sub2 = HomeworkSubmission(homework_id=homework.id, student_id=student2.id, score=90, content={"answer": "Student 2's answer"})
        session.add_all([sub1, sub2])
        session.commit()

        response = client.get(f'/api/analytics/exercises/{exercise.id}')
        assert response.status_code == 200
        data = response.get_json()['data']

        assert data['exercise_title'] == "Analytics Exercise"
        assert data['submission_count'] == 2
        assert data['average_score'] == 85.0