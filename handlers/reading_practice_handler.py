import logging
import json
import os
import random
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CallbackQueryHandler,
    CommandHandler,
)
from sqlalchemy.orm.attributes import flag_modified

from extensions import db
from models import User, PracticeSession
from utils.translation_system import TranslationSystem

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Conversation states
AWAITING_ANSWER = range(1)

# Path to the practice data
DATA_FILE_PATH = os.path.join(
    os.path.dirname(__file__), "..", "data", "reading_mcq.json"
)

# Define skill levels and their score thresholds
SKILL_LEVELS = {
    "Advanced": 0.81,
    "Upper-Intermediate": 0.61,
    "Intermediate": 0.41,
    "Elementary": 0.21,
    "Beginner": 0.0,
}

def _update_skill_level(user: User, session: PracticeSession) -> str | None:
    """
    Updates a user's skill level based on their performance in a practice session.
    Returns the new skill level if it was changed, otherwise None.
    """
    if not session.total_questions or session.total_questions == 0:
        return None

    score_percent = (session.correct_answers or 0) / session.total_questions

    new_skill_level = "Beginner"
    for level, threshold in SKILL_LEVELS.items():
        if score_percent >= threshold:
            new_skill_level = level
            break

    if user.skill_level != new_skill_level:
        user.update_skill_level(new_skill_level)
        return new_skill_level
    
    return None


def load_reading_data():
    """Loads reading practice data from the JSON file."""
    try:
        with open(DATA_FILE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logger.error(f"Error loading reading data: {e}")
        return []


def _get_recommendation(current_section="reading"):
    """Gets a recommendation for the next practice section."""
    all_sections = ["speaking", "writing", "reading", "listening"]
    available_sections = [s for s in all_sections if s != current_section]
    return random.choice(available_sections)


async def start_reading_practice(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Starts the reading practice session."""
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    lang_code = TranslationSystem.detect_language(query.from_user.to_dict())

    user = db.session.query(User).filter_by(user_id=user_id).first()
    if not user:
        await query.edit_message_text(
            text=TranslationSystem.get_message("errors", "user_not_found", lang_code)
        )
        return ConversationHandler.END

    reading_data = load_reading_data()
    if not reading_data:
        await query.edit_message_text(
            text=TranslationSystem.get_message(
                "practice", "no_reading_material", lang_code
            )
        )
        return ConversationHandler.END

    session = PracticeSession(user_id=user.id, section="reading")
    db.session.add(session)
    db.session.commit()

    # For simplicity, use the first set and question
    practice_set = reading_data[0]
    question_data = practice_set["questions"][0]
    context.user_data["reading_session_id"] = session.id
    context.user_data["reading_question_id"] = question_data["question_id"]
    context.user_data["reading_correct_option"] = question_data["correct_option_index"]

    passage_text = practice_set["passage"]
    question_text = question_data["text"]

    buttons = [
        [
            InlineKeyboardButton(
                option, callback_data=f"reading_answer:{question_data['question_id']}:{i}"
            )
        ]
        for i, option in enumerate(question_data["options"])
    ]
    reply_markup = InlineKeyboardMarkup(buttons)

    full_message = f"**Reading Passage**\\n\\n{passage_text}\\n\\n**Question**\\n\\n{question_text}"
    await query.edit_message_text(
        text=full_message, reply_markup=reply_markup, parse_mode="Markdown"
    )

    return AWAITING_ANSWER


async def handle_reading_answer(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Handles the user's answer to a reading question."""
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    lang_code = TranslationSystem.detect_language(query.from_user.to_dict())

    try:
        _, question_id, selected_index_str = query.data.split(":")
        selected_index = int(selected_index_str)
    except (ValueError, IndexError):
        await query.edit_message_text(
            text=TranslationSystem.get_message("errors", "invalid_action", lang_code)
        )
        return ConversationHandler.END

    session_id = context.user_data.get("reading_session_id")
    current_question_id = context.user_data.get("reading_question_id")

    if not session_id or not current_question_id or current_question_id != question_id:
        await query.edit_message_text(
            text=TranslationSystem.get_message("errors", "session_expired", lang_code)
        )
        return ConversationHandler.END

    session = db.session.query(PracticeSession).filter_by(id=session_id).first()
    user = db.session.query(User).filter_by(user_id=user_id).first()

    if not session or not user:
        await query.edit_message_text(
            text=TranslationSystem.get_message("errors", "session_not_found", lang_code)
        )
        return ConversationHandler.END

    correct_option = context.user_data.get("reading_correct_option")
    is_correct = selected_index == correct_option

    # Update stats
    session.total_questions = (session.total_questions or 0) + 1
    stats = user.stats or {}
    reading_stats = stats.get("reading", {"correct": 0, "total": 0})
    reading_stats["total"] += 1

    feedback_message = ""
    if is_correct:
        session.correct_answers = (session.correct_answers or 0) + 1
        reading_stats["correct"] += 1
        feedback_message = TranslationSystem.get_message(
            "practice", "correct_answer", lang_code
        )
    else:
        reading_data = load_reading_data()
        correct_text = ""
        for p_set in reading_data:
            for q in p_set["questions"]:
                if q["question_id"] == question_id:
                    correct_text = q["options"][correct_option]
                    break
            if correct_text:
                break
        feedback_message = TranslationSystem.get_message(
            "practice", "incorrect_answer", lang_code, correct_answer=correct_text
        )

    user.stats = stats
    flag_modified(user, "stats")
    
    # Update skill level
    new_level = _update_skill_level(user, session)
    
    db.session.commit()

    feedback_message_parts = [feedback_message]
    if new_level:
        level_up_message = TranslationSystem.get_message(
            "practice", "skill_level_up", lang_code, new_skill_level=new_level
        )
        feedback_message_parts.append(level_up_message)
    
    full_feedback = "\\n\\n".join(feedback_message_parts)

    await query.edit_message_text(text=full_feedback)

    # Offer a new practice recommendation
    recommendation = _get_recommendation()
    recommendation_text = TranslationSystem.get_message(
        "practice",
        "recommendation_prompt",
        lang_code,
        next_section=recommendation.capitalize(),
    )
    recommendation_button = InlineKeyboardButton(
        text=TranslationSystem.get_message(
            "practice",
            "start_next_section_button",
            lang_code,
            section=recommendation.capitalize(),
        ),
        callback_data=f"practice_{recommendation}",
    )
    await query.message.reply_text(
        text=recommendation_text,
        reply_markup=InlineKeyboardMarkup([[recommendation_button]]),
    )

    # Clean up user_data for the reading session
    context.user_data.pop("reading_session_id", None)
    context.user_data.pop("reading_question_id", None)
    context.user_data.pop("reading_correct_option", None)

    return ConversationHandler.END


async def cancel_reading(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancels the reading practice."""
    query = update.callback_query
    await query.answer()
    lang_code = TranslationSystem.detect_language(query.from_user.to_dict())
    await query.edit_message_text(
        text=TranslationSystem.get_message("general", "practice_canceled", lang_code)
    )
    context.user_data.clear()
    return ConversationHandler.END


reading_practice_conv_handler = ConversationHandler(
    entry_points=[
        CallbackQueryHandler(start_reading_practice, pattern="^practice_reading$")
    ],
    states={
        AWAITING_ANSWER: [
            CallbackQueryHandler(handle_reading_answer, pattern="^reading_answer:"),
        ],
    },
    fallbacks=[CallbackQueryHandler(cancel_reading, pattern="^cancel_reading$")],
    per_user=True,
    per_chat=True,
    per_message=False,
)