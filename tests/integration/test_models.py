import pytest
import time
from models.user import User
from models.practice_session import PracticeSession

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

def test_skill_level_updates_from_reading_session(sample_user, session):
    """
    Tests that a user's skill level is correctly updated from 'Beginner'
    to 'Advanced' after a high-scoring reading practice session.
    """
    from handlers.reading_practice_handler import _update_skill_level as update_skill_from_reading
    
    assert sample_user.skill_level == "Beginner"

    # Simulate a high-scoring reading session
    practice_session = PracticeSession(
        user_id=sample_user.id,
        section="reading",
        total_questions=10,
        correct_answers=9,
    )
    session.add(practice_session)
    session.commit()

    new_level = update_skill_from_reading(sample_user, practice_session)
    session.commit()

    assert new_level == "Advanced"
    assert sample_user.skill_level == "Advanced"

def test_skill_level_updates_from_writing_session(sample_user, session):
    """
    Tests that a user's skill level is correctly updated from 'Beginner'
    to 'Upper-Intermediate' after a good writing practice session.
    """
    from handlers.writing_practice_handler import _update_skill_level as update_skill_from_writing
    
    assert sample_user.skill_level == "Beginner"

    # Simulate a writing session with a band score of 7.0
    band_score = 7.0
    new_level = update_skill_from_writing(sample_user, band_score)
    session.commit()

    assert new_level == "Upper-Intermediate"
    assert sample_user.skill_level == "Upper-Intermediate"

def test_skill_level_no_update_for_low_score(sample_user, session):
    """
    Tests that a user's skill level does not change if the score is too low.
    """
    from handlers.reading_practice_handler import _update_skill_level as update_skill_from_reading

    assert sample_user.skill_level == "Beginner"

    # Simulate a low-scoring session
    practice_session = PracticeSession(
        user_id=sample_user.id,
        section="reading",
        total_questions=10,
        correct_answers=1,
    )
    session.add(practice_session)
    session.commit()

    new_level = update_skill_from_reading(sample_user, practice_session)
    session.commit()

    assert new_level is None
    assert sample_user.skill_level == "Beginner"

if __name__ == '__main__':
    pytest.main() 