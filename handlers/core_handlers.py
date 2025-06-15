import logging
from telegram import Update
from telegram.ext import ContextTypes

from utils.database_manager import DatabaseManager
from utils.translation_system import TranslationSystem
from utils.error_handler import safe_handler, ValidationError, BotError

logger = logging.getLogger(__name__)

@safe_handler()
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
    
    # Detect user's language
    user_data = effective_user.to_dict()
    language_code = TranslationSystem.detect_language(user_data)

    db_manager = DatabaseManager()

    try:
        existing_user = db_manager.get_user_by_telegram_id(user_id)

        if existing_user:
            # Update user information if needed
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
                except Exception as e:
                    session.rollback()
                    raise BotError(f"Failed to update user details: {str(e)}")
                finally:
                    session.close()

            welcome_message = TranslationSystem.get_message(
                "greetings", "welcome_back", language_code, name=first_name
            )
            logger.info(f"Existing user {user_id} ({username}) started the bot with lang: {language_code}.")
        else:
            # Register new user
            new_user = db_manager.add_user(
                user_id=user_id,
                first_name=first_name,
                last_name=last_name,
                username=username,
                preferred_language=language_code
            )
            
            if not new_user:
                raise BotError("Failed to register new user")
                
            welcome_message = TranslationSystem.get_message(
                "greetings", "welcome", language_code
            )
            logger.info(f"New user {user_id} ({username}) registered with language: {language_code}.")

        await update.message.reply_text(welcome_message)
        
    except Exception as e:
        logger.error(f"Error in start_command: {str(e)}", exc_info=True)
        raise  # Let safe_handler handle the error message
