import logging
import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    CommandHandler,
)
from models import User, PracticeSession
from services.openai_service import OpenAIService
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
SELECTING_TASK, AWAITING_ESSAY = range(2)

def _get_recommendation(current_section="writing"):
    """Gets a recommendation for the next practice section."""
    all_sections = ["speaking", "writing", "reading", "listening"]
    available_sections = [s for s in all_sections if s != current_section]
    return random.choice(available_sections)

async def start_writing_practice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Starts the writing practice session by showing task selection."""
    query = update.callback_query
    await query.answer()
    
    user = db.session.query(User).filter_by(user_id=query.from_user.id).first()
    lang_code = user.preferred_language

    keyboard = [
        [InlineKeyboardButton("Task 1: Report", callback_data="wp_task_1")],
        [InlineKeyboardButton("Task 2: Essay", callback_data="wp_task_2")],
        [InlineKeyboardButton(TranslationSystem.get_message("general", "cancel_button", lang_code), callback_data="wp_cancel")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        text=TranslationSystem.get_message("writing_practice", "welcome", lang_code),
        reply_markup=reply_markup
    )
    return SELECTING_TASK

async def handle_task_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles the user's task selection, generates a task, and asks for the essay."""
    query = update.callback_query
    await query.answer()

    task_type = int(query.data.split('_')[-1])
    
    user = db.session.query(User).filter_by(user_id=query.from_user.id).first()
    lang_code = user.preferred_language

    await query.edit_message_text(text=TranslationSystem.get_message("writing_practice", "generating_task", lang_code))

    openai_service = OpenAIService()
    try:
        task_data = openai_service.generate_writing_task(task_type)
        question = task_data.get("question")
        if not question:
            raise ValueError("Missing 'question' in task data from OpenAI")
        image_url = task_data.get("image_url")
    except Exception as e:
        logger.error(f"Error generating writing task: {e}")
        await query.edit_message_text(text=TranslationSystem.get_message("general", "error_generic_message", lang_code))
        return ConversationHandler.END

    # Create and store the practice session
    session = PracticeSession(user_id=user.id, section=f"writing_task_{task_type}", total_questions=1)
    db.session.add(session)
    db.session.commit()
    
    context.user_data["writing_session_id"] = session.id
    context.user_data["writing_question"] = question

    if image_url:
        await context.bot.send_photo(chat_id=query.message.chat_id, photo=image_url, caption=question)
    else:
        await context.bot.send_message(chat_id=query.message.chat_id, text=question)
    
    await context.bot.send_message(chat_id=query.message.chat_id, text=TranslationSystem.get_message("writing_practice", "task_prompt_single_message", lang_code))

    return AWAITING_ESSAY


async def handle_essay(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Receives the essay, gets feedback, and ends the conversation."""
    essay_text = update.message.text
    session_id = context.user_data.get("writing_session_id")

    session = db.session.query(PracticeSession).filter_by(id=session_id).first()
    if not session:
        await update.message.reply_text(TranslationSystem.get_message("writing_practice", "session_not_found", "en")) # Default to en if no user context
        return ConversationHandler.END
        
    user = db.session.query(User).filter_by(id=session.user_id).first()
    lang_code = user.preferred_language

    await update.message.reply_text(TranslationSystem.get_message("writing_practice", "analysis_in_progress", lang_code))

    openai_service = OpenAIService()
    question = context.user_data.get("writing_question")
    task_type = 1 if "task_1" in session.section else 2
    
    try:
        feedback = openai_service.provide_writing_feedback(essay_text, task_type, question)
    except Exception as e:
        logger.error(f"Error getting writing feedback: {e}")
        await update.message.reply_text(TranslationSystem.get_message("general", "error_generic_message", lang_code))
        context.user_data.clear()
        return ConversationHandler.END

    # Update session
    session.completed_at = datetime.utcnow()
    session.session_data = {"question": question, "essay": essay_text, "feedback": feedback}
    try:
        session.score = float(feedback.get("estimated_band", 0.0))
        if session.score > 0:
            session.correct_answers = 1
    except (ValueError, TypeError):
        session.score = 0.0

    flag_modified(session, "session_data")
    db.session.commit()
    
    # Format and send feedback
    feedback_text = format_writing_feedback(feedback, lang_code)
    await update.message.reply_text(feedback_text, parse_mode='Markdown')

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
    await update.message.reply_text(
        text=recommendation_text,
        reply_markup=InlineKeyboardMarkup([[recommendation_button]]),
    )

    context.user_data.clear()
    return ConversationHandler.END


def format_writing_feedback(feedback: dict, lang_code: str) -> str:
    """Formats the structured writing feedback into a user-friendly string."""
    
    def get_msg(key, **kwargs):
        return TranslationSystem.get_message("writing_practice", key, lang_code, **kwargs)

    strengths = "\\n- ".join(feedback.get('strengths', []))
    improvements = "\\n- ".join(feedback.get('areas_for_improvement', []))

    return (
        f"{get_msg('feedback_summary_title')}\\n\\n"
        f"{get_msg('estimated_band')} {feedback.get('estimated_band', 'N/A')}\\n\\n"
        f"{get_msg('task_achievement')}\\n{feedback.get('task_achievement', 'N/A')}\\n\\n"
        f"{get_msg('coherence_cohesion')}\\n{feedback.get('coherence_cohesion', 'N/A')}\\n\\n"
        f"{get_msg('lexical_resource')}\\n{feedback.get('lexical_resource', 'N/A')}\\n\\n"
        f"{get_msg('grammatical_range_accuracy')}\\n{feedback.get('grammatical_range_accuracy', 'N/A')}\\n\\n"
        f"{get_msg('strengths')}\\n- {strengths}\\n\\n"
        f"{get_msg('areas_for_improvement')}\\n- {improvements}"
    )


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancels and ends the conversation."""
    query = update.callback_query
    lang_code = TranslationSystem.detect_language(query.from_user.to_dict())
    
    await query.answer()
    await query.edit_message_text(text=TranslationSystem.get_message("general", "practice_canceled", lang_code))
    
    context.user_data.clear()
    return ConversationHandler.END


writing_practice_conv_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(start_writing_practice, pattern="^practice_writing$")],
    states={
        SELECTING_TASK: [
            CallbackQueryHandler(handle_task_selection, pattern="^wp_task_")
        ],
        AWAITING_ESSAY: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_essay)
        ],
    },
    fallbacks=[CallbackQueryHandler(cancel, pattern="^wp_cancel$")],
    per_user=True,
    per_chat=True,
    per_message=False,
) 