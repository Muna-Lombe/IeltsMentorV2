import functools
import logging
from telegram import Update
from telegram.ext import ContextTypes
from typing import Callable, Any, Optional

from utils.translation_system import TranslationSystem

logger = logging.getLogger(__name__)

def safe_handler(error_message: Optional[str] = None) -> Callable:
    """
    Decorator for safely handling errors in Telegram bot command handlers.
    
    Args:
        error_message: Optional custom error message key for translation
        
    Returns:
        Decorated function with error handling
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args: Any, **kwargs: Any) -> None:
            try:
                # Get user's language for error messages
                user_language = 'en'  # Default to English
                if update.effective_user:
                    user_data = update.effective_user.to_dict()
                    user_language = TranslationSystem.detect_language(user_data)
                
                # Execute the handler function
                return await func(update, context, *args, **kwargs)
                
            except Exception as e:
                # Log the error with context
                logger.error(
                    f"Error in handler {func.__name__}: {str(e)}",
                    exc_info=True,
                    extra={
                        'user_id': update.effective_user.id if update.effective_user else None,
                        'chat_id': update.effective_chat.id if update.effective_chat else None,
                        'message_id': update.effective_message.message_id if update.effective_message else None
                    }
                )
                
                # Send error message to user
                if update.effective_message:
                    error_key = error_message or 'general'
                    message = TranslationSystem.get_error_message(error_key, user_language)
                    await update.effective_message.reply_text(message)
                
        return wrapper
    return decorator

class BotError(Exception):
    """Base exception class for bot-specific errors."""
    def __init__(self, message: str, error_type: str = 'general'):
        self.message = message
        self.error_type = error_type
        super().__init__(self.message)

class PermissionError(BotError):
    """Exception raised when a user doesn't have required permissions."""
    def __init__(self, message: str = "Permission denied"):
        super().__init__(message, 'permission_denied')

class ValidationError(BotError):
    """Exception raised when user input validation fails."""
    def __init__(self, message: str = "Invalid input"):
        super().__init__(message, 'invalid_input')

class AIError(BotError):
    """Exception raised when AI service encounters an error."""
    def __init__(self, message: str = "AI service error"):
        super().__init__(message, 'ai_error') 