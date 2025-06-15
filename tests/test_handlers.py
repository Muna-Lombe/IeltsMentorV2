import pytest
from unittest.mock import patch, MagicMock
from handlers.core_handlers import start_command
from models.user import User
from utils.translation_system import TranslationSystem

@pytest.mark.asyncio
async def test_start_command_new_user(db_session, mock_update, mock_context):
    """Test the /start command for a new user."""
    # Arrange
    # The mock_update fixture provides a user that doesn't exist yet.
    # Initialize the translation system to ensure messages are loaded.
    TranslationSystem.initialize()

    # Act
    await start_command(mock_update, mock_context)

    # Assert
    # 1. Check if a reply was sent.
    mock_update.message.reply_text.assert_called_once()
    
    # 2. Verify the content of the reply.
    expected_message = TranslationSystem.get_message(
        "greetings", "welcome", "en"
    )
    mock_update.message.reply_text.assert_called_with(expected_message)

    # 3. Verify the user was added to the database.
    user_in_db = db_session.query(User).filter_by(user_id=mock_update.effective_user.id).first()
    assert user_in_db is not None
    assert user_in_db.username == "testuser"
    assert user_in_db.preferred_language == "en"

@pytest.mark.asyncio
async def test_start_command_existing_user(db_session, mock_update, mock_context):
    """Test the /start command for an existing user."""
    # Arrange
    # Add the user to the database first to simulate an existing user.
    existing_user = User(
        user_id=mock_update.effective_user.id,
        first_name="OldFirstName",
        username="oldusername",
        preferred_language="es" # Set a different language to test update
    )
    db_session.add(existing_user)
    db_session.commit()
    
    TranslationSystem.initialize()

    # Act
    await start_command(mock_update, mock_context)

    # Assert
    # 1. Check if a reply was sent.
    mock_update.message.reply_text.assert_called_once()

    # 2. Verify the content of the reply (should be the welcome_back message).
    expected_message = TranslationSystem.get_message(
        "greetings", "welcome_back", "en", name=mock_update.effective_user.first_name
    )
    mock_update.message.reply_text.assert_called_with(expected_message)

    # 3. Verify the user's details were updated in the database.
    user_in_db = db_session.query(User).filter_by(user_id=mock_update.effective_user.id).first()
    assert user_in_db is not None
    assert user_in_db.username == "testuser" # Check if username was updated
    assert user_in_db.first_name == "Test" # Check if first_name was updated
    assert user_in_db.preferred_language == "en" # Check if language was updated

@pytest.mark.asyncio
async def test_start_command_language_detection_es(db_session, mock_update, mock_context):
    """Test language detection for a Spanish-speaking user."""
    # Arrange
    mock_update.effective_user.language_code = "es"
    mock_update.effective_user.to_dict.return_value['language_code'] = 'es'
    TranslationSystem.initialize()
    
    # Act
    await start_command(mock_update, mock_context)
    
    # Assert
    # Check if the correct Spanish welcome message was sent.
    expected_message = TranslationSystem.get_message(
        "greetings", "welcome", "es"
    )
    mock_update.message.reply_text.assert_called_once_with(expected_message)
    
    # Verify the language was stored correctly in the database.
    user_in_db = db_session.query(User).filter_by(user_id=mock_update.effective_user.id).first()
    assert user_in_db.preferred_language == "es" 