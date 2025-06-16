import logging
from telegram import Update
from telegram.ext import ContextTypes
from models import User
from extensions import db
from utils.translation_system import TranslationSystem
from .decorators import error_handler

# Initialize translation system and logger
trans = TranslationSystem()
logger = logging.getLogger(__name__)

@error_handler
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles the /start command. Registers new users and welcomes them."""
    effective_user = update.effective_user
    lang_code = TranslationSystem.detect_language(effective_user.to_dict())

    user = db.session.query(User).filter_by(user_id=effective_user.id).first()

    if not user:
        # Create a new user if they don't exist
        user = User(
            user_id=effective_user.id,
            first_name=effective_user.first_name,
            last_name=effective_user.last_name,
            username=effective_user.username,
            preferred_language=lang_code
        )
        db.session.add(user)
        db.session.flush()  # Use flush to assign an ID within the transaction
        message = trans.get_message(
            'welcome',
            'new_user',
            lang_code,
            first_name=effective_user.first_name
        )
    else:
        # Update language preference if it has changed
        if user.preferred_language != lang_code:
            user.preferred_language = lang_code
        message = trans.get_message(
            'welcome',
            'returning_user',
            lang_code,
            first_name=effective_user.first_name
        )
    
    db.session.flush()
    await update.message.reply_text(text=message)


@error_handler
async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Displays the user's practice statistics."""
    user_id = update.effective_user.id
    lang_code = TranslationSystem.detect_language(update.effective_user.to_dict())

    user = db.session.query(User).filter_by(user_id=user_id).first()

    if user and user.stats:
        # Build the statistics message
        header = trans.get_message('stats', 'header', lang_code)
        stats_parts = []
        for section, section_stats in user.stats.items():
            correct = section_stats.get('correct', 0)
            total = section_stats.get('total', 0)
            if total > 0: # Only show sections with activity
                percentage = (correct / total) * 100
                stats_parts.append(
                    f"_{section.capitalize()}_: *{correct}*/*{total}* ({percentage:.1f}%)"
                )
        
        if stats_parts:
            stats_message = header + "\n" + "\n".join(stats_parts)
        else:
            stats_message = trans.get_message('stats', 'no_stats', lang_code)
        
        await update.message.reply_text(text=stats_message)
    else:
        # User has no stats record at all
        stats_message = trans.get_message('stats', 'no_stats', lang_code)
        await update.message.reply_text(text=stats_message)


@error_handler
async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles unknown commands."""
    user = update.effective_user
    lang_code = TranslationSystem.detect_language(user.to_dict())
    message = TranslationSystem.get_message("errors", "unknown_command", lang_code)
    await update.message.reply_text(text=message)
