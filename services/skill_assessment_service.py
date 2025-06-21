from models import User, PracticeSession

# Define skill levels and their score thresholds
SKILL_LEVELS = {
    "Advanced": 0.81,
    "Upper-Intermediate": 0.61,
    "Intermediate": 0.41,
    "Elementary": 0.21,
    "Beginner": 0.0,
}

def update_skill_level_from_session(user: User, session: PracticeSession) -> str | None:
    """
    Updates a user's skill level based on their performance in a practice session.

    Args:
        user: The User object.
        session: The PracticeSession object.

    Returns:
        The new skill level if it was changed, otherwise None.
    """
    if not session.total_questions or session.total_questions == 0:
        return None

    score_percent = (session.correct_answers or 0) / session.total_questions

    new_skill_level = "Beginner"
    for level, threshold in SKILL_LEVELS.items():
        if score_percent >= threshold:
            new_skill_level = level
            break

    if user.skill_level != new_skill_level:
        user.update_skill_level(new_skill_level)
        return new_skill_level
    
    return None
