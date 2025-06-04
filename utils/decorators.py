import functools
import logging
from telegram import Update
# from telegram.ext import ContextTypes # Not strictly needed for the decorator itself if not type hinting context

from utils.translation_system import get_message

logger = logging.getLogger(__name__)

def safe_handler(error_category: str = "errors", error_key: str = "general_error"):
    """
    A decorator to safely handle exceptions in Telegram bot command handlers.
    It logs the error and sends a generic error message to the user.

    Args:
        error_category (str): The category for the error message in the translation system.
        error_key (str): The key for the error message in the translation system.
    """
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(update: Update, context, *args, **kwargs):
            # context is typically ContextTypes.DEFAULT_TYPE but avoiding direct import for broader compatibility
            # if only Update is needed for error reporting.
            user_id = None
            handler_name = func.__name__
            try:
                if update and update.effective_user:
                    user_id = update.effective_user.id
                logger.debug(f"User {user_id} calling handler: {handler_name}")
                return await func(update, context, *args, **kwargs)
            except Exception as e:
                error_message_log = f"Error in handler '{handler_name}' for user {user_id}: {e}"
                logger.exception(error_message_log) # Logs with stack trace

                # Determine language for error message
                lang_code = "en" # Default
                if update and update.effective_user and update.effective_user.language_code:
                    lang_code = update.effective_user.language_code
                
                user_friendly_error_message = get_message(error_category, error_key, lang_code)
                
                try:
                    if update and hasattr(update, 'message') and update.message:
                        await update.message.reply_text(user_friendly_error_message)
                    elif update and hasattr(update, 'callback_query') and update.callback_query and update.callback_query.message:
                        # For callback queries, replying to the message might be better than answering the query with an error.
                        await update.callback_query.message.reply_text(user_friendly_error_message)
                        # Optionally, answer the callback query to remove the loading state
                        # await update.callback_query.answer(text=get_message("errors", "action_failed", lang_code), show_alert=True)
                    else:
                        logger.warning(f"Could not send error message for handler {handler_name} to user {user_id} - no obvious reply target.")
                except Exception as send_error:
                    logger.error(f"Failed to send error message to user {user_id} in handler {handler_name}: {send_error}")
            return None # Or some other default/error indicator if the handler was expected to return something specific
        return wrapper
    return decorator

# Example of how it might be used (won't run here, just for illustration)
# @safe_handler(error_key="start_command_error")
# async def example_start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
#     # ... command logic that might raise an exception ...
#     raise ValueError("Something went wrong in example_start_command")
#     await update.message.reply_text("This won't be reached if error is raised before it") 