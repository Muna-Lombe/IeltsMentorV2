import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from handlers.practice_handler import practice_section_callback, handle_reading_answer
from models import User, PracticeSession

# Sample data to be returned by the mocked load_reading_data function
MOCK_READING_DATA = [
    {
        "id": "reading_set_1",
        "passage": "This is a test passage.",
        "questions": [
            {
                "question_id": "rs1_q1",
                "text": "What is the capital of Pythonia?",
                "options": ["Syntaxgrad", "Pythontown", "Flaskville", "Django City"],
                "correct_option_index": 0
            }
        ]
    }
]

@pytest.fixture
def mock_reading_data():
    """Fixture to mock the reading data loading."""
    with patch('handlers.practice_handler.load_reading_data', return_value=MOCK_READING_DATA) as mock_loader:
        yield mock_loader

@pytest.mark.asyncio
async def test_reading_practice_starts_correctly(sample_user, mock_update, mock_context, mock_reading_data):
    """
    Tests that selecting the reading section correctly loads and displays the first question.
    """
    # Setup mock update for a callback query
    mock_update.callback_query.data = "practice_reading"
    mock_update.callback_query.answer = AsyncMock()
    mock_update.callback_query.edit_message_text = AsyncMock()

    # Call the handler
    await practice_section_callback(mock_update, mock_context)

    # Assertions
    mock_reading_data.assert_called_once()
    mock_update.callback_query.edit_message_text.assert_called_once()
    
    call_args = mock_update.callback_query.edit_message_text.call_args.kwargs
    assert "Reading Passage" in call_args['text']
    assert MOCK_READING_DATA[0]['passage'] in call_args['text']
    assert MOCK_READING_DATA[0]['questions'][0]['text'] in call_args['text']
    
    # Check that the question is stored in user_data
    assert 'current_question' in mock_context.user_data
    assert mock_context.user_data['current_question']['question_id'] == 'rs1_q1'
    
    # Check the keyboard
    reply_markup = call_args['reply_markup']
    assert len(reply_markup.inline_keyboard) == 4
    assert reply_markup.inline_keyboard[0][0].text == "Syntaxgrad"
    assert reply_markup.inline_keyboard[0][0].callback_data == "reading_answer:rs1_q1:0"

@pytest.mark.asyncio
async def test_handle_reading_answer_correct(sample_user, mock_update, mock_context, mock_reading_data, session):
    """
    Tests that a correct answer is processed correctly, with stats updated.
    """
    # Create a dummy session for the test
    practice_session = PracticeSession(user_id=sample_user.id, section="reading", total_questions=0, correct_answers=0)
    session.add(practice_session)
    session.commit()

    # Setup context from a practice session start
    mock_context.user_data['current_question'] = {
        "session_id": practice_session.id,
        "question_id": "rs1_q1",
        "correct_option_index": 0
    }
    
    # Setup mock update for a correct answer
    mock_update.callback_query.data = f"reading_answer:rs1_q1:0"
    
    # Call the handler
    await handle_reading_answer(mock_update, mock_context)
    
    # Assertions for bot response
    mock_update.callback_query.edit_message_text.assert_called_once()
    call_args = mock_update.callback_query.edit_message_text.call_args.kwargs
    assert "Correct!" in call_args['text']
    
    # Verify database state by re-querying the objects
    session.expire_all() # Ensure fresh data is loaded from the DB
    updated_session = session.query(PracticeSession).filter_by(id=practice_session.id).one()
    updated_user = session.query(User).filter_by(id=sample_user.id).one()

    assert updated_session.total_questions == 1
    assert updated_session.correct_answers == 1
    assert updated_user.stats['reading']['total'] == 11
    assert updated_user.stats['reading']['correct'] == 6

@pytest.mark.asyncio
async def test_handle_reading_answer_incorrect(sample_user, mock_update, mock_context, mock_reading_data, session):
    """
    Tests that an incorrect answer is processed correctly, with stats updated.
    """
    # Create a dummy session for the test
    practice_session = PracticeSession(user_id=sample_user.id, section="reading", total_questions=0, correct_answers=0)
    session.add(practice_session)
    session.commit()

    # Setup context from a practice session start
    mock_context.user_data['current_question'] = {
        "session_id": practice_session.id,
        "question_id": "rs1_q1",
        "correct_option_index": 0 # Correct answer is index 0
    }

    # Setup mock update for an incorrect answer (index 1)
    mock_update.callback_query.data = f"reading_answer:rs1_q1:1"

    # Call the handler
    await handle_reading_answer(mock_update, mock_context)

    # Assertions for bot response
    mock_update.callback_query.edit_message_text.assert_called_once()
    call_args = mock_update.callback_query.edit_message_text.call_args.kwargs
    assert "Not quite" in call_args['text']
    assert "A test" in call_args['text'] # Check that the correct answer text is included

    # Verify database state by re-querying the objects
    session.expire_all()
    updated_session = session.query(PracticeSession).filter_by(id=practice_session.id).one()
    updated_user = session.query(User).filter_by(id=sample_user.id).one()
    
    assert updated_session.total_questions == 1
    assert updated_session.correct_answers == 0
    assert updated_user.stats['reading']['total'] == 11
    assert updated_user.stats['reading']['correct'] == 5 