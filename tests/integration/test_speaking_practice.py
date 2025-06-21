import pytest
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from telegram import Update
from telegram.ext import ConversationHandler
from sqlalchemy.orm import Session
import os

from handlers.speaking_practice_handler import (
    start_speaking_practice,
    handle_part_1,
    handle_voice_message,
    cancel,
    SELECTING_PART,
    AWAITING_VOICE,
)
from models import User, PracticeSession


@pytest.mark.asyncio
@patch("handlers.speaking_practice_handler.db.session")
async def test_start_speaking_practice(mock_session, app):
    """Test the start of the speaking practice conversation."""
    with app.app_context():
        mock_user = User(id=1, user_id=123, preferred_language='en')
        mock_session.query.return_value.filter_by.return_value.first.return_value = mock_user

        update = Mock(spec=Update)
        update.callback_query = AsyncMock()
        update.callback_query.from_user.id = 123
        context = MagicMock()
        context.user_data = {}

        result = await start_speaking_practice(update, context)

        update.callback_query.edit_message_text.assert_called_once()
        assert result == SELECTING_PART
        assert "practice_session_id" in context.user_data


@pytest.mark.asyncio
@patch("handlers.speaking_practice_handler.OpenAIService")
async def test_handle_part_1(MockOpenAIService, app):
    """Test the handler for Speaking Part 1."""
    with app.app_context():
        mock_openai_instance = MockOpenAIService.return_value
        mock_openai_instance.generate_speaking_question.return_value = {
            "question": "Tell me about your favorite hobby.",
            "topic": "Hobbies",
        }

        update = Mock(spec=Update)
        update.callback_query = AsyncMock()
        update.callback_query.from_user = MagicMock()
        update.callback_query.from_user.to_dict = MagicMock(return_value={'language_code': 'en'})
        context = MagicMock()
        context.user_data = {}

        result = await handle_part_1(update, context)

        update.callback_query.edit_message_text.assert_called_once()
        assert "favorite hobby" in update.callback_query.edit_message_text.call_args[1]['text']
        assert result == AWAITING_VOICE
        assert context.user_data["speaking_part"] == 1 

@pytest.mark.asyncio
async def test_handle_part_1(mock_update: Update, mock_context: MagicMock):
    """Test that selecting Part 1 sends a question and waits for a voice message."""
    mock_update.callback_query.answer = AsyncMock()
    mock_update.callback_query.edit_message_text = AsyncMock()

    with patch('services.openai_service.OpenAIService.generate_speaking_question', return_value={"question": "Test question?"}) as mock_generate:
        result = await handle_part_1(mock_update, mock_context)

        assert result == AWAITING_VOICE
        mock_generate.assert_called_once_with(part_number=1)
        mock_update.callback_query.edit_message_text.assert_called_once()
        assert "Test question?" in mock_update.callback_query.edit_message_text.call_args[1]['text']

@pytest.mark.asyncio
@patch("os.remove")
@patch("os.path.exists", return_value=True)
@patch("builtins.open")
@patch("services.openai_service.OpenAIService.speech_to_text", return_value="This is a test transcript.")
@patch("services.openai_service.OpenAIService.generate_speaking_feedback")
async def test_handle_voice_message_part_1(
    mock_generate_feedback: MagicMock,
    mock_speech_to_text: MagicMock,
    mock_open: MagicMock,
    mock_exists: MagicMock,
    mock_remove: MagicMock,
    mock_update: Update,
    mock_context: MagicMock,
    sample_user: User,
    session: Session,
):
    """Test handling a voice message for Part 1, including transcription, feedback, and cleanup."""
    mock_update.message.voice.file_id = "test_file_id"
    mock_update.message.reply_text = AsyncMock()

    # Setup a realistic practice session
    practice_session = PracticeSession(user_id=sample_user.id, section="speaking", total_questions=0, correct_answers=0)
    session.add(practice_session)
    session.commit()

    # This patch ensures that the handler uses the same DB session as the test
    with patch('handlers.speaking_practice_handler.db.session', session):
        # Set a real user_id on the mock update
        mock_update.message.from_user.id = sample_user.user_id

        mock_context.user_data = {
            "practice_session_id": practice_session.id,
            "speaking_part": 1,
            "speaking_question": "Test question?",
        }

        mock_file = AsyncMock()
        mock_context.bot.get_file.return_value = mock_file

        # Mock feedback
        feedback_data = {"estimated_band": 7.5, "strengths": ["Good fluency"], "areas_for_improvement": ["Grammar"]}
        mock_generate_feedback.return_value = feedback_data

        result = await handle_voice_message(mock_update, mock_context)

    # Assertions
    assert result == ConversationHandler.END
    mock_context.bot.get_file.assert_called_once_with("test_file_id")
    mock_file.download_to_drive.assert_called_once()
    mock_speech_to_text.assert_called_once()
    mock_generate_feedback.assert_called_once_with("This is a test transcript.", 1, "Test question?")
    
    session.refresh(practice_session)
    assert practice_session.total_questions == 1
    assert practice_session.score == 7.5
    assert len(practice_session.session_data) == 1
    assert practice_session.session_data[0]["transcript"] == "This is a test transcript."
    
    mock_remove.assert_called_once()
    assert mock_update.message.reply_text.call_count == 3
    
    # Check the content of the messages sent.
    # The first two are positional args, the last one uses kwargs.
    assert "processing" in mock_update.message.reply_text.call_args_list[0].args[0].lower()
    assert "summary" in mock_update.message.reply_text.call_args_list[1].args[0].lower()

@pytest.mark.asyncio
@patch("handlers.speaking_practice_handler._get_recommendation", return_value="writing")
@patch("os.remove")
@patch("os.path.exists", return_value=True)
@patch("builtins.open")
@patch("services.openai_service.OpenAIService.speech_to_text", return_value="Test transcript.")
@patch("services.openai_service.OpenAIService.generate_speaking_feedback")
async def test_handle_voice_message_sends_recommendation(
    mock_generate_feedback: MagicMock,
    mock_speech_to_text: MagicMock,
    mock_open: MagicMock,
    mock_exists: MagicMock,
    mock_remove: MagicMock,
    mock_get_recommendation: MagicMock,
    mock_update: Update,
    mock_context: MagicMock,
    sample_user: User,
    session: Session,
):
    """
    Tests that a recommendation is sent after the speaking practice session ends.
    """
    mock_update.message.voice.file_id = "test_file_id"
    mock_update.message.reply_text = AsyncMock()

    practice_session = PracticeSession(user_id=sample_user.id, section="speaking")
    session.add(practice_session)
    session.commit()

    with patch('handlers.speaking_practice_handler.db.session', session):
        mock_update.message.from_user.id = sample_user.user_id
        mock_context.user_data = {
            "practice_session_id": practice_session.id,
            "speaking_part": 1,
            "speaking_question": "Test question?",
        }
        mock_file = AsyncMock()
        mock_context.bot.get_file.return_value = mock_file
        mock_generate_feedback.return_value = {"estimated_band": 7.0}

        result = await handle_voice_message(mock_update, mock_context)

    assert result == ConversationHandler.END
    mock_get_recommendation.assert_called_once()

    # The last call to reply_text should be the recommendation
    last_call = mock_update.message.reply_text.call_args_list[-1].kwargs
    assert "challenge yourself with a Writing practice next" in last_call["text"]
    reply_markup = last_call["reply_markup"]
    assert len(reply_markup.inline_keyboard) == 1
    assert reply_markup.inline_keyboard[0][0].text == "Start Writing Practice"
    assert reply_markup.inline_keyboard[0][0].callback_data == "practice_writing"


@pytest.mark.asyncio
async def test_cancel_flow(
    mock_update: Update,
    mock_context: MagicMock,
    sample_user: User,
    session: Session,
):
    """Test that the conversation can be cancelled and the session is cleaned up."""
    mock_update.callback_query.answer = AsyncMock()
    mock_update.callback_query.edit_message_text = AsyncMock()

    # Setup context and session
    practice_session = PracticeSession(user_id=sample_user.id, section="speaking")
    session.add(practice_session)
    session.commit()
    mock_context.user_data = {"practice_session_id": practice_session.id}

    # This patch ensures that the handler uses the same DB session as the test
    with patch('handlers.speaking_practice_handler.db.session', session):
        result = await cancel(mock_update, mock_context)

    assert result == ConversationHandler.END
    mock_update.callback_query.edit_message_text.assert_called_once()
    assert "canceled" in mock_update.callback_query.edit_message_text.call_args[1]['text'].lower()
    
    # Verify session is deleted
    cancelled_session = session.query(PracticeSession).filter_by(id=practice_session.id).first()
    assert cancelled_session is None

# More tests will be added here for part 2/3, and cancellation. 