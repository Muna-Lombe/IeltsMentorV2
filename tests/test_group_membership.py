import pytest
from app import db
from models import User, Group, GroupMembership

def test_add_member_to_group_success(client, approved_teacher_user, regular_user, session):
    """Test successfully adding a student to a group."""
    with client.session_transaction() as sess:
        sess['user_id'] = approved_teacher_user.id
    
    group = Group(name="Test Group", teacher_id=approved_teacher_user.id)
    session.add(group)
    session.commit()

    res = client.post(f'/api/groups/{group.id}/members', json={'student_id': regular_user.id})
    assert res.status_code == 201
    data = res.get_json()
    assert data['success'] is True
    assert "Student added to group successfully" in data['message']

    membership = db.session.query(GroupMembership).filter_by(group_id=group.id, student_id=regular_user.id).one_or_none()
    assert membership is not None

def test_add_member_unauthorized(client, another_teacher_user, regular_user, approved_teacher_user, session):
    """Test that a teacher cannot add members to a group they don't own."""
    with client.session_transaction() as sess:
        sess['user_id'] = another_teacher_user.id # Logged in as the wrong teacher
    
    group = Group(name="Owned Group", teacher_id=approved_teacher_user.id)
    session.add(group)
    session.commit()

    res = client.post(f'/api/groups/{group.id}/members', json={'student_id': regular_user.id})
    assert res.status_code == 404 # or 403, depending on implementation
    data = res.get_json()
    assert data['success'] is False

def test_add_member_student_not_found(client, approved_teacher_user, session):
    """Test adding a non-existent student to a group."""
    with client.session_transaction() as sess:
        sess['user_id'] = approved_teacher_user.id
    
    group = Group(name="Test Group", teacher_id=approved_teacher_user.id)
    session.add(group)
    session.commit()

    res = client.post(f'/api/groups/{group.id}/members', json={'student_id': 9999})
    assert res.status_code == 404
    data = res.get_json()
    assert "Student not found" in data['error']

def test_add_member_already_in_group(client, approved_teacher_user, regular_user, session):
    """Test adding a student who is already in the group."""
    with client.session_transaction() as sess:
        sess['user_id'] = approved_teacher_user.id
    
    group = Group(name="Test Group", teacher_id=approved_teacher_user.id)
    session.add(group)
    session.commit()
    
    # Add member first
    membership = GroupMembership(group_id=group.id, student_id=regular_user.id)
    session.add(membership)
    session.commit()

    # Try to add again
    res = client.post(f'/api/groups/{group.id}/members', json={'student_id': regular_user.id})
    assert res.status_code == 409
    data = res.get_json()
    assert "Student is already in this group" in data['error']

def test_remove_member_from_group_success(client, approved_teacher_user, regular_user, session):
    """Test successfully removing a student from a group."""
    with client.session_transaction() as sess:
        sess['user_id'] = approved_teacher_user.id
    
    group = Group(name="Test Group", teacher_id=approved_teacher_user.id)
    session.add(group)
    session.flush() # Ensure group.id is available

    membership = GroupMembership(group_id=group.id, student_id=regular_user.id)
    session.add(membership)
    session.commit()
    
    res = client.delete(f'/api/groups/{group.id}/members/{regular_user.id}')
    assert res.status_code == 200
    data = res.get_json()
    assert data['success'] is True
    assert "Student removed from group successfully" in data['message']
    
    assert db.session.query(GroupMembership).count() == 0

def test_remove_member_unauthorized(client, another_teacher_user, regular_user, approved_teacher_user, session):
    """Test that a teacher cannot remove members from a group they don't own."""
    with client.session_transaction() as sess:
        sess['user_id'] = another_teacher_user.id
    
    group = Group(name="Owned Group", teacher_id=approved_teacher_user.id)
    session.add(group)
    session.flush() # Ensure group.id is available

    membership = GroupMembership(group_id=group.id, student_id=regular_user.id)
    session.add(membership)
    session.commit()
    
    res = client.delete(f'/api/groups/{group.id}/members/{regular_user.id}')
    assert res.status_code == 404 # or 403
    
    assert db.session.query(GroupMembership).count() == 1 