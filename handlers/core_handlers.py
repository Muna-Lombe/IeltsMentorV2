import logging
from telegram import Update
from telegram.ext import ContextTypes

from utils.database_manager import DatabaseManager 
from utils.translation_system import get_message 
from utils.decorators import safe_handler

logger = logging.getLogger(__name__)

@safe_handler(error_category="errors", error_key="start_command_error")
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles the /start command. Registers new users and welcomes them."""
    effective_user = update.effective_user
    if not effective_user:
        logger.warning("/start command received without an effective_user")
        return

    user_id = effective_user.id
    first_name = effective_user.first_name
    last_name = effective_user.last_name
    username = effective_user.username
    language_code = effective_user.language_code

    db_manager = DatabaseManager() # Initialize DatabaseManager

    existing_user = db_manager.get_user_by_telegram_id(user_id)

    if existing_user:
        updated = False
        if existing_user.username != username:
            existing_user.username = username
            updated = True
        if existing_user.first_name != first_name:
            existing_user.first_name = first_name
            updated = True
        if existing_user.last_name != last_name:
            existing_user.last_name = last_name
            updated = True
        if existing_user.preferred_language != language_code:
            existing_user.preferred_language = language_code
            updated = True
        
        if updated:
            session = db_manager.get_session()
            try:
                session.add(existing_user) 
                session.commit()
                logger.info(f"User {user_id} details updated.")
            except Exception as e_update: # Specific exception handling for DB update
                session.rollback()
                logger.error(f"Error updating user {user_id}: {e_update}")
                # Depending on desired behavior, you might re-raise or let safe_handler catch a generic version
                # For now, we log it and the user gets the generic error from safe_handler if this path is problematic.
            finally:
                session.close()

        welcome_message = get_message("user", "welcome_back", language_code, name=first_name)
        logger.info(f"Existing user {user_id} ({username}) started the bot with lang: {language_code}.")
    else:
        new_user = db_manager.add_user(
            user_id=user_id,
            first_name=first_name,
            last_name=last_name,
            username=username,
            preferred_language=language_code
        )
        if new_user:
            welcome_message = get_message("user", "welcome_new", language_code, name=first_name)
            logger.info(f"New user {user_id} ({username}) registered with language: {language_code}.")
        else:
            # add_user itself logs errors. The safe_handler will catch this if add_user returns None
            # and we try to use welcome_message before it's set, or if add_user re-raises.
            # For a more direct error to user here, we'd need to throw an exception or handle differently.
            # The current safe_handler sends a generic message if an unhandled exception bubbles up.
            # If add_user fails and returns None, welcome_message won't be defined for the new user case.
            # This path will lead to an UnboundLocalError if not handled before reply_text,
            # which the safe_handler will then catch and report generically.
            # To provide a more specific error message in this exact case:
            # raise Exception("User registration failed in DB an new_user is None") # this will be caught by safe_handler
            # Or, more gracefully, set a specific error message:
            welcome_message = get_message("errors", "registration_error", language_code)
            logger.error(f"Failed to register new user {user_id} (add_user returned None).")
            
    await update.message.reply_text(welcome_message)
