import pytest
from unittest.mock import AsyncMock, patch, mock_open

from telegram.ext import ConversationHandler
from handlers.listening_practice_handler import (
    start_listening_practice,
    select_exercise,
    handle_answer,
    SELECTING_EXERCISE,
    AWAITING_ANSWER,
)
from models import User, PracticeSession
from telegram import InlineKeyboardMarkup

MOCK_LISTENING_DATA = [
    {
        "id": "test_ex_1",
        "name": "Test Exercise 1",
        "audio_file": "data/seed-data/listening_tasks/test_audio.mp3",
        "questions": [
            {
                "question_number": 1,
                "question_text": "What is the main topic?",
                "options": {"A": "Weather", "B": "Sports", "C": "Music"},
                "correct_answer": "C",
            },
            {
                "question_number": 2,
                "question_text": "What instrument is mentioned?",
                "options": {"A": "Guitar", "B": "Piano", "C": "Drums"},
                "correct_answer": "B",
            },
        ],
    }
]


@pytest.fixture
def mock_listening_data():
    """Mocks the listening data by patching json.load."""
    with patch("json.load", return_value=MOCK_LISTENING_DATA) as mock_loader:
        yield mock_loader


@pytest.mark.asyncio
async def test_start_listening_practice(
    sample_user, mock_update, mock_context, mock_listening_data
):
    """Test that the listening practice starts and shows exercise selection."""
    mock_update.callback_query.data = "practice_listening"

    next_state = await start_listening_practice(mock_update, mock_context)

    assert next_state == SELECTING_EXERCISE
    mock_update.callback_query.edit_message_text.assert_called_once()
    call_args = mock_update.callback_query.edit_message_text.call_args.kwargs
    assert "Please choose a listening exercise" in call_args["text"]
    assert call_args["reply_markup"].inline_keyboard[0][0].text == "Test Exercise 1"
    assert (
        call_args["reply_markup"].inline_keyboard[0][0].callback_data
        == "lp_select_test_ex_1"
    )


@pytest.mark.asyncio
@patch("builtins.open", new_callable=mock_open, read_data=b"test_audio_data")
async def test_select_exercise_and_send_first_question(
    mock_file, sample_user, mock_update, mock_context, mock_listening_data, session
):
    """Test selecting an exercise sends audio and the first question."""
    mock_update.callback_query.data = "lp_select_test_ex_1"
    mock_context.bot.send_audio = AsyncMock()
    mock_context.bot.send_message = AsyncMock()

    next_state = await select_exercise(mock_update, mock_context)

    assert next_state == AWAITING_ANSWER
    mock_update.callback_query.edit_message_text.assert_called_once_with(
        text="Starting: Test Exercise 1"
    )
    mock_context.bot.send_audio.assert_called_once()
    mock_context.bot.send_message.assert_called_once()

    call_args = mock_context.bot.send_message.call_args.kwargs
    assert "Question 1" in call_args["text"]
    assert "What is the main topic?" in call_args["text"]

    assert "listening_session_id" in mock_context.user_data
    assert mock_context.user_data["exercise_id"] == "test_ex_1"
    assert mock_context.user_data["question_index"] == 0

    db_session = session.query(PracticeSession).filter_by(user_id=sample_user.id).first()
    assert db_session is not None
    assert db_session.section == "listening_test_ex_1"


@pytest.mark.asyncio
async def test_handle_answer_correct_and_continue(
    sample_user, mock_update, mock_context, mock_listening_data
):
    """Test that a correct answer triggers the next question."""
    mock_context.user_data = {
        "listening_session_id": 1,
        "exercise_id": "test_ex_1",
        "question_index": 0,
        "score": 0,
    }
    mock_update.callback_query.data = "lp_answer_C"  # Correct answer
    mock_context.bot.send_message = AsyncMock()
    mock_update.callback_query.message.delete = AsyncMock()

    next_state = await handle_answer(mock_update, mock_context)

    assert next_state == AWAITING_ANSWER
    assert mock_context.user_data["score"] == 1
    assert mock_context.user_data["question_index"] == 1

    # Check that "Correct!" was sent, then the next question
    assert mock_context.bot.send_message.call_count == 2
    first_call_text = mock_context.bot.send_message.call_args_list[0].kwargs["text"]
    second_call_text = mock_context.bot.send_message.call_args_list[1].kwargs["text"]

    assert "Correct!" in first_call_text
    assert "Question 2" in second_call_text
    assert "What instrument is mentioned?" in second_call_text


@pytest.mark.asyncio
async def test_handle_answer_incorrect_and_finish(
    sample_user, mock_update, mock_context, mock_listening_data, session
):
    """Test an incorrect answer for the last question finishes the practice."""
    practice_session = PracticeSession(
        user_id=sample_user.id, section="listening_test_ex_1"
    )
    session.add(practice_session)
    session.commit()

    mock_context.user_data = {
        "listening_session_id": practice_session.id,
        "exercise_id": "test_ex_1",
        "question_index": 1,  # Last question
        "score": 1,
    }
    mock_update.callback_query.data = "lp_answer_A"  # Incorrect
    mock_context.bot.send_message = AsyncMock()
    mock_update.callback_query.message.delete = AsyncMock()

    # We patch the recommendation to make the test deterministic
    with patch(
        "handlers.listening_practice_handler._get_recommendation",
        return_value="reading",
    ):
        next_state = await handle_answer(mock_update, mock_context)

    assert next_state == ConversationHandler.END
    assert mock_context.user_data == {}  # Check that user_data is cleared

    # We expect 3 messages: incorrect feedback, final score, and recommendation
    assert mock_context.bot.send_message.call_count == 3
    
    # 1. Feedback for incorrect answer
    feedback_call = mock_context.bot.send_message.call_args_list[0]
    assert "Incorrect" in feedback_call.kwargs["text"]

    # 2. Final score summary
    summary_call = mock_context.bot.send_message.call_args_list[1]
    assert "Listening practice complete!" in summary_call.kwargs["text"]
    assert "Your score: 1/2" in summary_call.kwargs["text"]

    # 3. Recommendation message
    recommendation_call = mock_context.bot.send_message.call_args_list[2]
    assert "challenge yourself with a Reading practice" in recommendation_call.kwargs["text"]
    assert isinstance(
        recommendation_call.kwargs["reply_markup"], InlineKeyboardMarkup
    )

    session.expire_all()
    updated_session = (
        session.query(PracticeSession).filter_by(id=practice_session.id).one()
    )
    assert updated_session.score == 1
    assert updated_session.correct_answers == 1
    assert updated_session.completed_at is not None


@pytest.mark.asyncio
@patch("handlers.listening_practice_handler._get_recommendation", return_value="writing")
async def test_handle_answer_finish_sends_recommendation(
    mock_get_recommendation,
    sample_user,
    mock_update,
    mock_context,
    mock_listening_data,
    session,
):
    """
    Tests that a recommendation is sent after the listening practice finishes.
    """
    practice_session = PracticeSession(user_id=sample_user.id, section="listening")
    session.add(practice_session)
    session.commit()

    mock_context.user_data = {
        "listening_session_id": practice_session.id,
        "exercise_id": "test_ex_1",
        "question_index": 1,  # Last question
        "score": 1,
    }
    mock_update.callback_query.data = "lp_answer_B"  # Correct
    mock_context.bot.send_message = AsyncMock()
    mock_update.callback_query.message.delete = AsyncMock()

    result = await handle_answer(mock_update, mock_context)

    assert result == ConversationHandler.END
    mock_get_recommendation.assert_called_once()

    # The last call should be the recommendation
    last_call = mock_context.bot.send_message.call_args_list[-1].kwargs
    assert (
        "challenge yourself with a Writing practice next" in last_call["text"]
    )
    reply_markup = last_call["reply_markup"]
    assert len(reply_markup.inline_keyboard) == 1
    assert reply_markup.inline_keyboard[0][0].text == "Start Writing Practice"
    assert reply_markup.inline_keyboard[0][0].callback_data == "practice_writing"