import pytest
from unittest.mock import Mock, AsyncMock, MagicMock
from telegram import Update
from telegram.ext import ConversationHandler

from handlers.speaking_practice_handler import (
    start_speaking_practice,
    handle_part_1,
    SELECTING_PART,
    AWAITING_VOICE,
)

@pytest.mark.asyncio
async def test_start_speaking_practice():
    """Test the start of the speaking practice conversation."""
    update = Mock()
    update.callback_query = AsyncMock()
    update.callback_query.from_user = MagicMock()
    update.callback_query.from_user.to_dict.return_value = {'language_code': 'en'}
    context = Mock()

    result = await start_speaking_practice(update, context)

    update.callback_query.edit_message_text.assert_called_once()
    assert "Welcome to Speaking Practice!" in update.callback_query.edit_message_text.call_args.kwargs['text']
    assert result == SELECTING_PART

@pytest.mark.asyncio
async def test_handle_part_1():
    """Test the handler for Speaking Part 1."""
    update = Mock()
    update.callback_query = AsyncMock()
    update.callback_query.from_user = MagicMock()
    update.callback_query.from_user.to_dict.return_value = {'language_code': 'en'}
    context = Mock()
    context.user_data = {}

    result = await handle_part_1(update, context)

    update.callback_query.edit_message_text.assert_called_once()
    assert "Part 1" in update.callback_query.edit_message_text.call_args.kwargs['text']
    assert "hometown" in update.callback_query.edit_message_text.call_args.kwargs['text']
    assert context.user_data["speaking_part"] == 1
    assert result == AWAITING_VOICE 