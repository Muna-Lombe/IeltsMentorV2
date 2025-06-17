import logging
import json
import os
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from sqlalchemy.orm.attributes import flag_modified

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

# Path to the practice data
DATA_FILE_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'reading_mcq.json')

def load_reading_data():
    """Loads reading practice data from the JSON file."""
    try:
        with open(DATA_FILE_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logger.error(f"Error loading reading data: {e}")
        return []

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
        
    if section == "reading":
        reading_data = load_reading_data()
        if not reading_data:
            await query.edit_message_text(text=trans.get_message("practice", "no_reading_material", lang_code))
            return
        
        # For simplicity, we'll use the first set and first question
        practice_set = reading_data[0]
        question_data = practice_set["questions"][0]
        context.user_data['current_question'] = {
            "session_id": session.id,
            "question_id": question_data["question_id"],
            "correct_option_index": question_data["correct_option_index"]
        }

        # Format the message with the passage and question
        passage_text = practice_set["passage"]
        question_text = question_data["text"]
        
        buttons = []
        for i, option in enumerate(question_data["options"]):
            callback_data = f"reading_answer:{question_data['question_id']}:{i}"
            buttons.append([InlineKeyboardButton(option, callback_data=callback_data)])
        
        reply_markup = InlineKeyboardMarkup(buttons)

        full_message = f"**Reading Passage**\n\n{passage_text}\n\n**Question**\n\n{question_text}"
        await query.edit_message_text(text=full_message, reply_markup=reply_markup, parse_mode='Markdown')

    else:
        # For other sections, we'll just use a generic "work in progress" message.
        message = trans.get_message(
            "practice", "session_wip", lang_code, section=section.capitalize()
        )
        await query.edit_message_text(text=message)

async def handle_reading_answer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles the user's answer to a reading question."""
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    lang_code = trans.detect_language(query.from_user.to_dict())

    # Parse callback data
    try:
        _, question_id, selected_index_str = query.data.split(':')
        selected_index = int(selected_index_str)
    except (ValueError, IndexError):
        await query.edit_message_text(text=trans.get_message("errors", "invalid_action", lang_code))
        return

    current_question = context.user_data.get('current_question')
    if not current_question or current_question.get("question_id") != question_id:
        await query.edit_message_text(text=trans.get_message("errors", "session_expired", lang_code))
        return

    session = db.session.query(PracticeSession).filter_by(id=current_question["session_id"]).first()
    if not session:
        await query.edit_message_text(text=trans.get_message("errors", "session_not_found", lang_code))
            return

    is_correct = (selected_index == current_question["correct_option_index"])
    
    # Update stats
    session.total_questions += 1
    user = db.session.query(User).filter_by(user_id=user_id).first()
    
    stats = user.stats or {}
    reading_stats = stats.get("reading", {"correct": 0, "total": 0})
    reading_stats["total"] += 1
    
    feedback_message = ""
        if is_correct:
        session.correct_answers += 1
        reading_stats["correct"] += 1
        feedback_message = trans.get_message("practice", "correct_answer", lang_code)
    else:
        # Find the correct answer text to show the user
        reading_data = load_reading_data()
        correct_text = ""
        # This is inefficient but simple. A better approach would be to not reload the file.
        for p_set in reading_data:
            for q in p_set['questions']:
                if q['question_id'] == question_id:
                    correct_text = q['options'][current_question["correct_option_index"]]
                    break
            if correct_text:
                break
        feedback_message = trans.get_message("practice", "incorrect_answer", lang_code, correct_answer=correct_text)

    user.stats = stats
    flag_modified(user, "stats")
    db.session.add(session)
    db.session.add(user)
    db.session.commit()
    
    await query.edit_message_text(text=feedback_message)

    # Clean up user_data
    del context.user_data['current_question']

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