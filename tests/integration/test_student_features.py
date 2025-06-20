import pytest
from unittest.mock import AsyncMock, MagicMock
from telegram import InlineKeyboardMarkup

from handlers.practice_handler import practice_command
from handlers.core_handlers import stats_command
from models.user import User

@pytest.mark.asyncio
async def test_practice_command_shows_selection_menu(sample_user, mock_update, mock_context):
    """
    Tests that the /practice command replies with an inline keyboard for section selection.
    """
    # Ensure the mock_update uses the correct user ID and is configured for a message
    mock_update.effective_user.id = sample_user.user_id
    mock_update.callback_query = None
    mock_update.message.reply_text = AsyncMock()

    # Call the handler
    await practice_command(mock_update, mock_context)

    # Assertions
    mock_update.message.reply_text.assert_called_once()
    call_args = mock_update.message.reply_text.call_args
    assert "Please select a section to practice" in call_args[1]['text']
    assert isinstance(call_args[1]['reply_markup'], InlineKeyboardMarkup)
    
    # Check keyboard buttons
    keyboard = call_args[1]['reply_markup'].inline_keyboard
    assert len(keyboard) == 2
    assert len(keyboard[0]) == 2
    assert len(keyboard[1]) == 2
    assert keyboard[0][0].text == "🗣️ Speaking"
    assert keyboard[0][0].callback_data == "practice_speaking"
    assert keyboard[0][1].text == "✍️ Writing"
    assert keyboard[0][1].callback_data == "practice_writing"
    assert keyboard[1][0].text == "📖 Reading"
    assert keyboard[1][0].callback_data == "practice_reading"
    assert keyboard[1][1].text == "🎧 Listening"
    assert keyboard[1][1].callback_data == "practice_listening"

@pytest.mark.asyncio
async def test_stats_command_displays_user_stats(sample_user, mock_update, mock_context):
    """
    Tests that the /stats command correctly displays the user's statistics.
    """
    # Setup mock update with the correct user ID
    mock_update.effective_user.id = sample_user.user_id
    mock_update.callback_query = None
    mock_update.message.reply_text = AsyncMock()

    # Call the handler
    await stats_command(mock_update, mock_context)

    # Assertions
    mock_update.message.reply_text.assert_called_once()
    call_args = mock_update.message.reply_text.call_args.kwargs
    
    # Check that the stats are in the response
    assert "Your IELTS Progress" in call_args['text']
    assert "Reading" in call_args['text']
    assert "*5*/*10*" in call_args['text']
    assert "50.0%" in call_args['text']

@pytest.mark.asyncio
async def test_stats_command_for_new_user(regular_user, mock_update, mock_context):
    """
    Tests the /stats command for a user with no stats yet.
    """
    # Setup mock update for the new user
    mock_update.effective_user.id = regular_user.user_id
    mock_update.callback_query = None # This is a message command
    mock_update.message = AsyncMock() # Ensure message is an awaitable mock
    
    # Call the handler
    await stats_command(mock_update, mock_context)
    
    # Assertions
    mock_update.message.reply_text.assert_called_once()
    call_args = mock_update.message.reply_text.call_args.kwargs
    assert "No stats to show yet" in call_args['text']

@pytest.mark.asyncio
async def test_explain_command_with_valid_query(mock_update, mock_context, mock_openai_service):
    """
    Tests the /explain command with a valid query, ensuring it calls the AI service.
    """
    mock_context.args = ["grammar", "present", "perfect"]
    
    from handlers.ai_commands_handler import explain_command
    await explain_command(mock_update, mock_context)
    
    # Check that the AI service was called
    mock_openai_service.return_value.generate_explanation.assert_called_once_with(
        query="present perfect", context="grammar", language="en"
    )
    
    # Check that the thinking message is updated with the explanation
    mock_update.message.reply_text.return_value.edit_text.assert_called_once()
    call_args, call_kwargs = mock_update.message.reply_text.return_value.edit_text.call_args
    assert "This is a mock explanation." in call_args[0]

@pytest.mark.asyncio
async def test_define_command_with_valid_word(mock_update, mock_context, mock_openai_service):
    """
    Tests the /define command with a valid word, ensuring it calls the AI service.
    """
    mock_context.args = ["elaborate"]
    
    from handlers.ai_commands_handler import define_command
    await define_command(mock_update, mock_context)
    
    # Check that the AI service was called
    mock_openai_service.return_value.generate_definition.assert_called_once_with(
        word="elaborate", language="en"
    )
    
    # Check that the thinking message is updated with the definition
    mock_update.message.reply_text.return_value.edit_text.assert_called_once()
    call_args, call_kwargs = mock_update.message.reply_text.return_value.edit_text.call_args
    assert "This is a mock definition." in call_args[0] 