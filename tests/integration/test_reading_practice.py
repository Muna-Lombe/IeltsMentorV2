import pytest
from unittest.mock import AsyncMock, patch
from telegram.ext import ConversationHandler

from handlers.reading_practice_handler import (
    start_reading_practice,
    handle_reading_answer,
    AWAITING_ANSWER,
)
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
                "correct_option_index": 0,
            }
        ],
    }
]


@pytest.fixture
def mock_reading_data():
    """Fixture to mock the reading data loading."""
    with patch(
        "handlers.reading_practice_handler.load_reading_data",
        return_value=MOCK_READING_DATA,
    ) as mock_loader:
        yield mock_loader


@pytest.mark.asyncio
async def test_reading_practice_starts_correctly(
    sample_user, mock_update, mock_context, mock_reading_data, session
):
    """
    Tests that the reading practice conversation starts correctly.
    """
    mock_update.callback_query.data = "practice_reading"
    mock_update.callback_query.answer = AsyncMock()
    mock_update.callback_query.edit_message_text = AsyncMock()

    # Start the conversation
    next_state = await start_reading_practice(mock_update, mock_context)

    # Assertions
    assert next_state == AWAITING_ANSWER
    mock_reading_data.assert_called_once()
    mock_update.callback_query.edit_message_text.assert_called_once()

    call_args = mock_update.callback_query.edit_message_text.call_args.kwargs
    assert "Reading Passage" in call_args["text"]
    assert MOCK_READING_DATA[0]["passage"] in call_args["text"]
    assert MOCK_READING_DATA[0]["questions"][0]["text"] in call_args["text"]

    # Check that session data is stored in user_data
    assert "reading_session_id" in mock_context.user_data
    assert mock_context.user_data["reading_question_id"] == "rs1_q1"

    # Check the keyboard
    reply_markup = call_args["reply_markup"]
    assert len(reply_markup.inline_keyboard) == 4
    assert reply_markup.inline_keyboard[0][0].text == "Syntaxgrad"
    assert reply_markup.inline_keyboard[0][0].callback_data == "reading_answer:rs1_q1:0"

    # Check that a practice session was created
    db_session = session.query(PracticeSession).filter_by(user_id=sample_user.id).first()
    assert db_session is not None
    assert db_session.section == "reading"


@pytest.mark.asyncio
async def test_handle_reading_answer_correct(
    sample_user, mock_update, mock_context, mock_reading_data, session
):
    """
    Tests that a correct answer is processed correctly and ends the conversation.
    """
    # Reset stats for a clean test
    sample_user.stats = {"reading": {"correct": 0, "total": 0}}
    session.commit()

    practice_session = PracticeSession(
        user_id=sample_user.id, section="reading", total_questions=0, correct_answers=0
    )
    session.add(practice_session)
    session.commit()

    mock_context.user_data["reading_session_id"] = practice_session.id
    mock_context.user_data["reading_question_id"] = "rs1_q1"
    mock_context.user_data["reading_correct_option"] = 0

    mock_update.callback_query.data = "reading_answer:rs1_q1:0"
    mock_update.callback_query.message.reply_text = AsyncMock()

    # Call the handler
    next_state = await handle_reading_answer(mock_update, mock_context)

    assert next_state == ConversationHandler.END
    mock_update.callback_query.edit_message_text.assert_called_once()
    call_args = mock_update.callback_query.edit_message_text.call_args.kwargs
    assert "Correct!" in call_args["text"]

    session.expire_all()
    updated_session = (
        session.query(PracticeSession).filter_by(id=practice_session.id).one()
    )
    updated_user = session.query(User).filter_by(id=sample_user.id).one()

    assert updated_session.total_questions == 1
    assert updated_session.correct_answers == 1
    assert updated_user.stats["reading"]["total"] == 1
    assert updated_user.stats["reading"]["correct"] == 1

    # Check that session data is cleaned up
    assert "reading_session_id" not in mock_context.user_data


@pytest.mark.asyncio
async def test_handle_reading_answer_incorrect(
    sample_user, mock_update, mock_context, mock_reading_data, session
):
    """
    Tests that an incorrect answer is processed correctly and ends the conversation.
    """
    # Reset stats for a clean test
    sample_user.stats = {"reading": {"correct": 0, "total": 0}}
    session.commit()

    practice_session = PracticeSession(
        user_id=sample_user.id, section="reading", total_questions=0, correct_answers=0
    )
    session.add(practice_session)
    session.commit()

    mock_context.user_data["reading_session_id"] = practice_session.id
    mock_context.user_data["reading_question_id"] = "rs1_q1"
    mock_context.user_data["reading_correct_option"] = 0

    mock_update.callback_query.data = "reading_answer:rs1_q1:1"
    mock_update.callback_query.message.reply_text = AsyncMock()

    # Call the handler
    next_state = await handle_reading_answer(mock_update, mock_context)

    assert next_state == ConversationHandler.END
    mock_update.callback_query.edit_message_text.assert_called_once()
    call_args = mock_update.callback_query.edit_message_text.call_args.kwargs
    assert "Not quite" in call_args["text"]
    assert "Syntaxgrad" in call_args["text"]

    session.expire_all()
    updated_session = (
        session.query(PracticeSession).filter_by(id=practice_session.id).one()
    )
    updated_user = session.query(User).filter_by(id=sample_user.id).one()

    assert updated_session.total_questions == 1
    assert updated_session.correct_answers == 0
    assert updated_user.stats["reading"]["total"] == 1
    assert updated_user.stats["reading"]["correct"] == 0

    assert "reading_session_id" not in mock_context.user_data


@pytest.mark.asyncio
@patch("handlers.reading_practice_handler._get_recommendation", return_value="speaking")
async def test_handle_reading_answer_sends_recommendation(
    mock_get_recommendation,
    sample_user,
    mock_update,
    mock_context,
    mock_reading_data,
    session,
):
    """
    Tests that a recommendation is sent after the practice session ends.
    """
    practice_session = PracticeSession(user_id=sample_user.id, section="reading")
    session.add(practice_session)
    session.commit()

    mock_context.user_data["reading_session_id"] = practice_session.id
    mock_context.user_data["reading_question_id"] = "rs1_q1"
    mock_context.user_data["reading_correct_option"] = 0
    mock_update.callback_query.data = "reading_answer:rs1_q1:0"
    mock_update.callback_query.message.reply_text = AsyncMock()

    # Call the handler
    await handle_reading_answer(mock_update, mock_context)

    # Assert that the recommendation was called and the reply was sent
    mock_get_recommendation.assert_called_once()
    mock_update.callback_query.message.reply_text.assert_called_once()

    # Check the content of the recommendation message
    call_args = mock_update.callback_query.message.reply_text.call_args.kwargs
    assert "challenge yourself with a Speaking practice next" in call_args["text"]
    reply_markup = call_args["reply_markup"]
    assert len(reply_markup.inline_keyboard) == 1
    assert reply_markup.inline_keyboard[0][0].text == "Start Speaking Practice"
    assert reply_markup.inline_keyboard[0][0].callback_data == "practice_speaking"