import pytest
import time
from models.user import User

def test_user_creation(session):
    """Test basic user creation and default values."""
    user = User(
        user_id=98765,
        first_name="Test",
        last_name="User",
        username="testuser_models",
        preferred_language="en"
    )
    session.add(user)
    session.commit()
    
    retrieved_user = session.query(User).filter_by(user_id=98765).first()
    
    assert retrieved_user is not None
    assert retrieved_user.username == "testuser_models"
    assert retrieved_user.is_admin is False
    assert "reading" in retrieved_user.stats
    assert retrieved_user.stats['reading']['correct'] == 0
    assert retrieved_user.skill_level == "Beginner"
    assert abs(retrieved_user.joined_at - time.time()) < 5

def test_update_stats(sample_user, session):
    """Test the update_stats method on the User model."""
    # The 'reading' stat for sample_user is {'correct': 5, 'total': 10}
    
    # Test incrementing existing stats
    current_stats = sample_user.get_section_stats('reading')
    sample_user.update_stats('reading', {
        'correct': current_stats.get('correct', 0) + 1,
        'total': current_stats.get('total', 0) + 1
    })
    session.commit()
    
    assert sample_user.stats['reading']['correct'] == 6
    assert sample_user.stats['reading']['total'] == 11
    
    # Test adding stats for a new section
    sample_user.update_stats('writing', {'tasks_submitted': 1, 'avg_score': 85})
    session.commit()
    
    assert sample_user.stats['writing']['tasks_submitted'] == 1
    assert sample_user.stats['writing']['avg_score'] == 85
    
    # Test a different user to ensure no conflicts
    new_user = User(user_id=54321, first_name="New")
    session.add(new_user)
    session.commit()
    
    new_user.update_stats('speaking', {'sessions_completed': 1})
    session.commit()
    
    assert new_user.stats['speaking']['sessions_completed'] == 1
    assert 'reading' not in new_user.get_section_stats('speaking')

if __name__ == '__main__':
    pytest.main() 