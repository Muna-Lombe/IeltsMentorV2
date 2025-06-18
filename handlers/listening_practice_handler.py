import logging
import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CallbackQueryHandler,
)

from models import User, PracticeSession
from utils.translation_system import TranslationSystem
from extensions import db
from datetime import datetime
from sqlalchemy.orm.attributes import flag_modified

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Conversation states
SELECTING_EXERCISE, AWAITING_ANSWER = range(2)

# Load listening exercises from JSON file
def load_listening_exercises():
    try:
        with open("data/listening_mcq.json", "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        logger.error("Failed to load listening_mcq.json")
        return []

LISTENING_EXERCISES = load_listening_exercises()

async def start_listening_practice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Starts the listening practice session by showing exercise selection."""
    query = update.callback_query
    await query.answer()

    user = db.session.query(User).filter_by(user_id=query.from_user.id).first()
    lang_code = user.preferred_language

    if not LISTENING_EXERCISES:
        await query.edit_message_text(text="Sorry, no listening exercises are available at the moment.")
        return ConversationHandler.END

    keyboard = [
        [InlineKeyboardButton(ex["name"], callback_data=f"lp_select_{ex['id']}")]
        for ex in LISTENING_EXERCISES
    ]
    keyboard.append([InlineKeyboardButton("Cancel", callback_data="lp_cancel")])
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        text="Please choose a listening exercise:",
        reply_markup=reply_markup
    )
    return SELECTING_EXERCISE

async def select_exercise(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Sends the selected exercise audio and the first question."""
    query = update.callback_query
    await query.answer()
    
    exercise_id = query.data.split('_')[-1]
    exercise = next((ex for ex in LISTENING_EXERCISES if ex["id"] == exercise_id), None)

    if not exercise:
        await query.edit_message_text(text="Sorry, that exercise could not be found.")
        return ConversationHandler.END

    await query.edit_message_text(text=f"Starting: {exercise['name']}")

    # Send audio file
    try:
        with open(exercise["audio_file"], "rb") as audio:
            await context.bot.send_audio(chat_id=query.message.chat_id, audio=audio)
    except FileNotFoundError:
        await context.bot.send_message(chat_id=query.message.chat_id, text="Sorry, the audio file for this exercise is missing.")
        return ConversationHandler.END

    user = db.session.query(User).filter_by(user_id=query.from_user.id).first()
    session = PracticeSession(user_id=user.id, section=f"listening_{exercise_id}", total_questions=len(exercise["questions"]))
    db.session.add(session)
    db.session.commit()

    context.user_data["listening_session_id"] = session.id
    context.user_data["exercise_id"] = exercise_id
    context.user_data["question_index"] = 0
    context.user_data["score"] = 0

    await send_question(update, context)
    return AWAITING_ANSWER

async def send_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sends the current question to the user."""
    exercise_id = context.user_data["exercise_id"]
    question_index = context.user_data["question_index"]
    exercise = next((ex for ex in LISTENING_EXERCISES if ex["id"] == exercise_id), None)
    
    question_data = exercise["questions"][question_index]
    question_text = f"Question {question_data['question_number']}:\n{question_data['question_text']}"
    
    keyboard = [
        [InlineKeyboardButton(f"{opt_key}: {opt_val}", callback_data=f"lp_answer_{opt_key}")]
        for opt_key, opt_val in question_data["options"].items()
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Use query from callback_query if available, otherwise use update for subsequent messages
    if update.callback_query:
        await context.bot.send_message(chat_id=update.callback_query.message.chat_id, text=question_text, reply_markup=reply_markup)
    else:
        await update.message.reply_text(question_text, reply_markup=reply_markup)

async def handle_answer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles the user's answer, sends the next question, or ends the practice."""
    query = update.callback_query
    await query.answer()

    selected_option = query.data.split('_')[-1]
    
    exercise_id = context.user_data["exercise_id"]
    question_index = context.user_data["question_index"]
    exercise = next((ex for ex in LISTENING_EXERCISES if ex["id"] == exercise_id), None)
    question_data = exercise["questions"][question_index]

    if selected_option == question_data["correct_answer"]:
        context.user_data["score"] += 1
        await context.bot.send_message(chat_id=query.message.chat_id, text="Correct!")
    else:
        await context.bot.send_message(chat_id=query.message.chat_id, text=f"Incorrect. The correct answer was {question_data['correct_answer']}.")
    
    await query.message.delete()

    context.user_data["question_index"] += 1
    if context.user_data["question_index"] < len(exercise["questions"]):
        await send_question(update, context)
        return AWAITING_ANSWER
    else:
        # End of practice
        session_id = context.user_data["listening_session_id"]
        score = context.user_data["score"]
        
        session = db.session.query(PracticeSession).filter_by(id=session_id).first()
        session.score = score
        session.correct_answers = score
        session.completed_at = datetime.utcnow()
        session.session_data = {"exercise_id": exercise_id, "score": score, "total_questions": len(exercise["questions"])}
        flag_modified(session, "session_data")
        db.session.commit()

        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=f"Listening practice complete!\nYour score: {score}/{len(exercise['questions'])}"
        )
        context.user_data.clear()
        return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancels and ends the conversation."""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(text="Listening practice canceled.")
    context.user_data.clear()
    return ConversationHandler.END

listening_practice_conv_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(start_listening_practice, pattern="^practice_listening$")],
    states={
        SELECTING_EXERCISE: [
            CallbackQueryHandler(select_exercise, pattern="^lp_select_")
        ],
        AWAITING_ANSWER: [
            CallbackQueryHandler(handle_answer, pattern="^lp_answer_")
        ],
    },
    fallbacks=[CallbackQueryHandler(cancel, pattern="^lp_cancel$")],
    per_user=True,
    per_chat=True,
)
