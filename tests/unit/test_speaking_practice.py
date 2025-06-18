import pytest
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from telegram import Update
from handlers.speaking_practice_handler import (
    start_speaking_practice,
    handle_part_1,
    handle_voice_message,
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