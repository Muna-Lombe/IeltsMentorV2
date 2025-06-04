import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from telegram import Update, User as TelegramUser # Renamed to avoid conflict with our model
from telegram.ext import ContextTypes

from handlers.core_handlers import start_command
# Assuming models.user.User is your SQLAlchemy model
from models.user import User as DBUser 

# Mock context for ContextTypes.DEFAULT_TYPE if needed, though often not directly interacted with in simple handlers
class MockBot:
    def __init__(self):
        self.id = 123456 # Dummy bot ID
        # Add other attributes or methods if your context/bot interaction is more complex

class MockApplication:
    def __init__(self):
        self.bot = MockBot()
        # Add other attributes or methods if your application interaction is more complex

class TestCoreHandlers(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        """Set up common test objects and mocks."""
        self.telegram_user = TelegramUser(
            id=12345,
            first_name="TestFirstName",
            is_bot=False,
            last_name="TestLastName",
            username="testusername",
            language_code="en"
        )
        self.update = AsyncMock(spec=Update)
        self.update.effective_user = self.telegram_user
        self.update.message = AsyncMock()
        self.update.message.reply_text = AsyncMock()

        # If your context usage is simple and specific, you might mock it minimally
        # For ContextTypes.DEFAULT_TYPE, often you might not need to mock much of its internals
        # unless your handler uses specific attributes/methods from context.bot or context.application
        self.context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
        self.context.bot = MockBot() # or a MagicMock()
        self.context.application = MockApplication() # or a MagicMock()
        # If your handler uses context.args, context.chat_data, etc., mock those as needed.

    @patch('handlers.core_handlers.DatabaseManager')
    @patch('handlers.core_handlers.get_message')
    async def test_start_command_new_user(self, mock_get_message, MockDatabaseManager):
        """Test the /start command for a new user."""
        # --- Arrange ---
        # Mock DatabaseManager instance and its methods
        mock_db_manager_instance = MockDatabaseManager.return_value
        mock_db_manager_instance.get_user_by_telegram_id.return_value = None # Simulate new user
        
        # Simulate successful user creation
        created_db_user = DBUser(
            user_id=self.telegram_user.id, 
            first_name=self.telegram_user.first_name,
            username=self.telegram_user.username,
            preferred_language=self.telegram_user.language_code
        )
        mock_db_manager_instance.add_user.return_value = created_db_user
        
        # Mock translation
        expected_welcome_message = "Welcome new test user!"
        mock_get_message.return_value = expected_welcome_message

        # --- Act ---
        await start_command(self.update, self.context)

        # --- Assert ---
        # Check if user was searched for
        mock_db_manager_instance.get_user_by_telegram_id.assert_called_once_with(self.telegram_user.id)
        # Check if user was added
        mock_db_manager_instance.add_user.assert_called_once_with(
            user_id=self.telegram_user.id,
            first_name=self.telegram_user.first_name,
            last_name=self.telegram_user.last_name,
            username=self.telegram_user.username,
            preferred_language=self.telegram_user.language_code
        )
        # Check if welcome message for new user was requested
        mock_get_message.assert_called_once_with(
            "user", "welcome_new", self.telegram_user.language_code, name=self.telegram_user.first_name
        )
        # Check if reply was sent
        self.update.message.reply_text.assert_called_once_with(expected_welcome_message)

    @patch('handlers.core_handlers.DatabaseManager')
    @patch('handlers.core_handlers.get_message')
    async def test_start_command_existing_user(self, mock_get_message, MockDatabaseManager):
        """Test the /start command for an existing user."""
        # --- Arrange ---
        existing_db_user = DBUser(
            user_id=self.telegram_user.id, 
            first_name=self.telegram_user.first_name,
            username=self.telegram_user.username,
            preferred_language=self.telegram_user.language_code,
            # ... other fields if necessary for the test ...
        )
        mock_db_manager_instance = MockDatabaseManager.return_value
        mock_db_manager_instance.get_user_by_telegram_id.return_value = existing_db_user
        mock_db_manager_instance.get_session.return_value = MagicMock() # For update path
        
        # Mock translation
        expected_welcome_message = "Welcome back existing user!"
        mock_get_message.return_value = expected_welcome_message

        # --- Act ---
        await start_command(self.update, self.context)

        # --- Assert ---
        mock_db_manager_instance.get_user_by_telegram_id.assert_called_once_with(self.telegram_user.id)
        mock_db_manager_instance.add_user.assert_not_called() # Should not be called for existing user
        
        # Check if welcome message for existing user was requested
        mock_get_message.assert_called_once_with(
            "user", "welcome_back", self.telegram_user.language_code, name=self.telegram_user.first_name
        )
        # Check if reply was sent
        self.update.message.reply_text.assert_called_once_with(expected_welcome_message)
        
        # Further assertions can be made about user detail updates if the logic is more complex
        # For instance, if the username changed, assert that session.commit() was called.
        # This requires more detailed mocking of the session object and its methods.

    # You can add more tests, e.g., for when add_user fails, or when language code is different, etc.

if __name__ == '__main__':
    unittest.main() 