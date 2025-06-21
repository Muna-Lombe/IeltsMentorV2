import pytest
from models import User, PracticeSession
from handlers.reading_practice_handler import _update_skill_level as update_skill_from_reading
from handlers.writing_practice_handler import _update_skill_level as update_skill_from_writing
from handlers.speaking_practice_handler import _update_skill_level as update_skill_from_speaking


def test_skill_level_updates_from_reading_session(sample_user, session):
    """
    Tests that a user's skill level is correctly updated from 'Beginner'
    to 'Advanced' after a high-scoring reading practice session.
    """
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