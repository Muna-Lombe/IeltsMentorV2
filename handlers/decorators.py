from functools import wraps
import logging
from flask import current_app
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
from models import User
from extensions import db
from utils.translation_system import TranslationSystem

# Initialize translation system and logger
trans = TranslationSystem()
logger = logging.getLogger(__name__)

def error_handler(func):
    """
    A decorator to handle exceptions in bot command handlers, log them,
    and send a user-friendly error message.
    """
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        try:
            return await func(update, context, *args, **kwargs)
        except Exception as e:
            # Log the error with stack trace
            logger.error(f"Error in handler {func.__name__}: {e}", exc_info=True)
            language = trans.detect_language(update.effective_user.to_dict())
            if update.message:
                await update.message.reply_text(text=trans.get_message('errors', 'general_error', language))
            # Potentially return a specific state or ConversationHandler.END if in a conversation
    return wrapper

def teacher_required(func):
    """
    Decorator to ensure a user is an approved teacher.
    Passes the user object from the database to the decorated function.
    """
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        if not update.effective_user:
            return ConversationHandler.END

        with current_app.app_context():
            user_id = update.effective_user.id
            user = db.session.query(User).filter(User.user_id == user_id).first()
            
            language = user.preferred_language if user and user.preferred_language else trans.detect_language(update.effective_user.to_dict())

            if not user:
                if update.message:
                    await update.message.reply_text(text=trans.get_message('errors', 'user_not_found', language))
                return ConversationHandler.END

            print(f"user: {user}")
            print(f"user.teacher_profile: {user.teacher_profile}")
            
            is_teacher = user.is_admin
            # Correctly check for teacher_profile relationship and its is_approved status
            is_approved_teacher = is_teacher and hasattr(user, 'teacher_profile') and user.teacher_profile and user.teacher_profile.is_approved

            if not is_approved_teacher:
                if update.message:
                    await update.message.reply_text(text=trans.get_message('errors', 'permission_denied_teacher', language))
                return ConversationHandler.END

            return await func(update, context, user=user, *args, **kwargs)
    return wrapper

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