import logging
import json
from datetime import datetime # For completed_at timestamp

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes

from utils.decorators import safe_handler
from utils.translation_system import get_message # Assuming you might want to translate button texts or messages
from utils.database_manager import DatabaseManager # For DB interactions
from models.practice_session import PracticeSession # SQLAlchemy model
from models.user import User as DBUser # To get user.id for ForeignKey
from services.practice_service import PracticeService # To load questions

logger = logging.getLogger(__name__)

# Define callback data constants for clarity
PRACTICE_CALLBACK_SPEAKING = "practice_speaking"
PRACTICE_CALLBACK_WRITING = "practice_writing"
PRACTICE_CALLBACK_READING = "practice_reading"
PRACTICE_CALLBACK_LISTENING = "practice_listening"

# For Reading MCQ answers: answer_reading_{practice_session_id}_{question_index}_{option_index}
CALLBACK_DATA_ANSWER_READING_PREFIX = "answer_reading_"

# --- Helper Function to Send Reading Question ---
async def _send_reading_mcq_question(update: Update, context: ContextTypes.DEFAULT_TYPE, 
                                     practice_session_id: int, reading_set: dict, question_index: int):
    """Sends a specific reading MCQ question with its passage (if first question)."""
    question_data = reading_set["questions"][question_index]
    passage = reading_set["passage"]
    question_text = question_data["text"]
    options = question_data["options"]
    
    # Send passage only for the first question of the set
    full_message = ""
    if question_index == 0:
        full_message += f"<b>Reading Passage:</b>\n{passage}\n\n---\n\n"
    
    full_message += f"<b>Question {question_index + 1}:</b>\n{question_text}"

    keyboard = []
    for i, option_text in enumerate(options):
        callback_data = f"{CALLBACK_DATA_ANSWER_READING_PREFIX}{practice_session_id}_{question_index}_{i}"
        keyboard.append([InlineKeyboardButton(option_text, callback_data=callback_data)])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # If editing a previous message (like from section selection)
    if update.callback_query:
        await update.callback_query.edit_message_text(text=full_message, reply_markup=reply_markup, parse_mode='HTML')
    else: # Or sending a new message (less likely in this flow but possible)
        await context.bot.send_message(chat_id=update.effective_chat.id, text=full_message, reply_markup=reply_markup, parse_mode='HTML')

@safe_handler(error_category="errors", error_key="general_error")
async def practice_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends a message with inline keyboard for selecting a practice section."""
    user = update.effective_user
    if not user:
        logger.warning("/practice command received without an effective_user")
        return

    lang_code = user.language_code or "en"

    # Create Inline Keyboard Buttons
    # For now, button texts are hardcoded, but ideally, they would use get_message for localization
    # e.g., speaking_text = get_message("practice", "button_speaking", lang_code)
    keyboard = [
        [InlineKeyboardButton(get_message("practice", "button_speaking", lang_code, default="Speaking"), callback_data=PRACTICE_CALLBACK_SPEAKING)],
        [InlineKeyboardButton(get_message("practice", "button_writing", lang_code, default="Writing"), callback_data=PRACTICE_CALLBACK_WRITING)],
        [InlineKeyboardButton(get_message("practice", "button_reading", lang_code, default="Reading"), callback_data=PRACTICE_CALLBACK_READING)],
        [InlineKeyboardButton(get_message("practice", "button_listening", lang_code, default="Listening"), callback_data=PRACTICE_CALLBACK_LISTENING)],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    message_text = get_message("practice", "select_section_prompt", lang_code, default="Please choose a section to practice:")
    # Fallback if translation key doesn't exist yet:
    if "Translation not found" in message_text or message_text == "Critical Error": # Basic check
        message_text = "Please choose a section to practice:"
        
    await update.message.reply_text(message_text, reply_markup=reply_markup)

@safe_handler(error_category="errors", error_key="general_error")
async def practice_section_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles callback queries from the practice section selection."""
    query = update.callback_query
    await query.answer() # Acknowledge callback query

    user = update.effective_user
    lang_code = user.language_code if user else "en"
    
    section_selected = query.data
    response_text = f"You selected: {section_selected}. " # Placeholder

    if section_selected == PRACTICE_CALLBACK_SPEAKING:
        # response_text += get_message("practice", "speaking_selected_response", lang_code)
        response_text += "Starting Speaking practice... (Not implemented yet)"
    elif section_selected == PRACTICE_CALLBACK_WRITING:
        # response_text += get_message("practice", "writing_selected_response", lang_code)
        response_text += "Starting Writing practice... (Not implemented yet)"
    elif section_selected == PRACTICE_CALLBACK_READING:
        # response_text += get_message("practice", "reading_selected_response", lang_code)
        response_text += "Starting Reading practice... (Not implemented yet)"
    elif section_selected == PRACTICE_CALLBACK_LISTENING:
        # response_text += get_message("practice", "listening_selected_response", lang_code)
        response_text += "Starting Listening practice... (Not implemented yet)"
    else:
        # response_text = get_message("errors", "invalid_selection", lang_code)
        response_text = "Invalid selection. Please try again."
        logger.warning(f"Invalid callback data received: {section_selected}")

    await query.edit_message_text(text=response_text)
    # If you want to send a new message instead of editing:
    # await context.bot.send_message(chat_id=update.effective_chat.id, text=response_text)

@safe_handler(error_category="errors", error_key="general_error")
async def handle_reading_mcq_answer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles user's answer to a reading MCQ question."""
    query = update.callback_query
    await query.answer()
    user_telegram_id = update.effective_user.id
    lang_code = update.effective_user.language_code or "en"

    # Parse callback data: answer_reading_{practice_session_id}_{question_index}_{option_index}
    try:
        _, practice_session_id_str, question_idx_str, option_idx_str = query.data.split("_")
        practice_session_id = int(practice_session_id_str)
        question_index = int(question_idx_str)
        chosen_option_index = int(option_idx_str)
    except ValueError as e:
        logger.error(f"Invalid callback data format for reading answer: {query.data} - {e}")
        await query.edit_message_text(text=get_message("errors", "invalid_action_error", lang_code, default="Invalid action. Please try again."))
        return

    # Verify session and question index from user_data to prevent mismatches
    if context.user_data.get('current_practice_session_id') != practice_session_id or \
       context.user_data.get('current_reading_question_index') != question_index:
        logger.warning(f"Callback data mismatch for user {user_telegram_id}. Expected session/q_idx: "
                       f"{context.user_data.get('current_practice_session_id')}/{context.user_data.get('current_reading_question_index')}, "
                       f"Got: {practice_session_id}/{question_index}. Callback: {query.data}")
        await query.edit_message_text(text=get_message("errors", "session_expired_error", lang_code, default="Your session seems to have expired or is out of sync. Please try starting practice again."))
        return

    db_manager = DatabaseManager()
    practice_service = PracticeService()
    session = db_manager.get_session()

    try:
        current_session = session.query(PracticeSession).filter(PracticeSession.id == practice_session_id).first()
        if not current_session:
            logger.error(f"PracticeSession {practice_session_id} not found for user {user_telegram_id}.")
            await query.edit_message_text(text=get_message("errors", "session_not_found_error", lang_code, default="Practice session not found."))
            return

        reading_set_id = current_session.session_data.get("reading_set_id")
        reading_set = practice_service.get_reading_mcq_set(set_id=reading_set_id)
        if not reading_set:
            logger.error(f"Reading set {reading_set_id} not found for session {practice_session_id}.")
            await query.edit_message_text(text=get_message("practice", "no_reading_material", lang_code, default="Error: Could not load practice material."))
            return

        question_data = reading_set["questions"][question_index]
        correct_option_index = question_data["correct_option_index"]
        is_correct = (chosen_option_index == correct_option_index)

        feedback_text = "Correct!" if is_correct else f"Incorrect. The correct answer was: {question_data['options'][correct_option_index]}"
        
        # Update PracticeSession
        if is_correct:
            current_session.correct_answers = (current_session.correct_answers or 0) + 1
        
        # Update session_data with this answer
        session_answers = current_session.session_data.get("answers", [])
        session_answers.append({
            "question_id": question_data["question_id"],
            "chosen_option_index": chosen_option_index,
            "correct_option_index": correct_option_index,
            "is_correct": is_correct
        })
        current_session.session_data["answers"] = session_answers # Re-assign to trigger JSON mutation tracking if necessary
        session.add(current_session) # Add to session to mark as dirty
        session.commit()
        logger.info(f"User {user_telegram_id} answered Q{question_index} for session {practice_session_id}. Correct: {is_correct}")
        
        # Send feedback to user (e.g., as an alert or edit previous message then show next question)
        await query.answer(text=feedback_text, show_alert=False) # Quick feedback

        # Move to next question or end session
        next_question_index = question_index + 1
        if next_question_index < len(reading_set["questions"]):
            context.user_data['current_reading_question_index'] = next_question_index
            await _send_reading_mcq_question(update, context, practice_session_id, reading_set, next_question_index)
        else:
            # End of practice session
            current_session.completed_at = datetime.utcnow()
            current_session.score = (current_session.correct_answers / current_session.total_questions) * 100 if current_session.total_questions else 0
            session.add(current_session)
            session.commit()
            
            summary_message = get_message("practice", "reading_session_complete", lang_code, 
                                          score=f"{current_session.correct_answers}/{current_session.total_questions}", 
                                          percentage=f"{current_session.score:.2f}%")
            if "Translation not found" in summary_message or "Critical Error" in summary_message:
                 summary_message = f"Reading practice complete! Your score: {current_session.correct_answers}/{current_session.total_questions} ({current_session.score:.2f}%)."
            await query.edit_message_text(text=summary_message)
            
            # Clean up user_data for this practice type
            if 'current_practice_session_id' in context.user_data: del context.user_data['current_practice_session_id']
            if 'current_reading_set_id' in context.user_data: del context.user_data['current_reading_set_id']
            if 'current_reading_question_index' in context.user_data: del context.user_data['current_reading_question_index']
            logger.info(f"Reading session {practice_session_id} completed for user {user_telegram_id}.")

    except Exception as e:
        session.rollback()
        logger.error(f"Error in handle_reading_mcq_answer for user {user_telegram_id}, session {practice_session_id if 'practice_session_id' in locals() else 'unknown'}: {e}")
        # The @safe_handler will catch this and send a generic error message.
        # If a more specific message is needed here, it can be sent before re-raising or returning.
        await query.edit_message_text(text=get_message("errors", "processing_answer_error", lang_code, default="Error processing your answer. Please try again or restart practice."))
    finally:
        session.close()

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