import logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes

from extensions import db
from models import User, PracticeSession
from utils.translation_system import TranslationSystem
from .decorators import error_handler

logger = logging.getLogger(__name__)
trans = TranslationSystem()

# Define callback data constants for clarity
PRACTICE_CALLBACK_SPEAKING = "practice_speaking"
PRACTICE_CALLBACK_WRITING = "practice_writing"
PRACTICE_CALLBACK_READING = "practice_reading"
PRACTICE_CALLBACK_LISTENING = "practice_listening"

@error_handler
async def practice_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends a message with an inline keyboard for selecting a practice section."""
    user = update.effective_user
    lang_code = trans.detect_language(user.to_dict())

    keyboard = [
        [
            InlineKeyboardButton("🗣️ Speaking", callback_data=PRACTICE_CALLBACK_SPEAKING),
            InlineKeyboardButton("✍️ Writing", callback_data=PRACTICE_CALLBACK_WRITING),
        ],
        [
            InlineKeyboardButton("📖 Reading", callback_data=PRACTICE_CALLBACK_READING),
            InlineKeyboardButton("🎧 Listening", callback_data=PRACTICE_CALLBACK_LISTENING),
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    message = trans.get_message("practice", "select_section", lang_code)
    await update.message.reply_text(text=message, reply_markup=reply_markup)

@error_handler
async def practice_section_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles the callback from the practice section selection."""
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    section = query.data.replace("practice_", "")
    lang_code = trans.detect_language(query.from_user.to_dict())

    user = db.session.query(User).filter_by(user_id=user_id).first()
    if not user:
        await query.edit_message_text(text=trans.get_message("errors", "user_not_found", lang_code))
        return

    # Create a new practice session
    session = PracticeSession(user_id=user.id, section=section)
    db.session.add(session)
    db.session.flush()

    logger.info(f"User {user_id} started a new '{section}' practice session (ID: {session.id}).")
        
    # For now, we'll just use a generic "work in progress" message for all sections.
    message = trans.get_message(
        "practice", "session_wip", lang_code, section=section.capitalize()
    )
    await query.edit_message_text(text=message)

# Placeholder for translation keys that would be added to en.json/es.json:
# "practice": {
#     "select_section_prompt": "Please choose a section to practice:",
#     "button_speaking": "Speaking",
#     "button_writing": "Writing",
#     "button_reading": "Reading",
#     "button_listening": "Listening",
#     "speaking_selected_response": "Starting Speaking practice...",
#     "writing_selected_response": "Starting Writing practice...",
#     "reading_selected_response": "Starting Reading practice...",
#     "listening_selected_response": "Starting Listening practice...",
#     "no_reading_material": "Sorry, no reading materials available right now.",
#     "reading_session_complete": "Reading practice complete! Your score: {score} ({percentage}%)."
# },
# "errors": {
#     "invalid_selection": "That was an invalid selection. Please try choosing a section again.",
#     "user_not_found_error": "Error: User not registered. Please /start first.",
#     "session_creation_failed": "Could not start practice session. Please try again.",
#     "invalid_action_error": "Invalid action. Please try again.",
#     "session_expired_error": "Your session seems to have expired or is out of sync. Please try starting practice again.",
#     "session_not_found_error": "Practice session not found. Please restart the practice.",
#     "processing_answer_error": "Error processing your answer. Please try again or restart practice."
# } 