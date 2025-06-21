import logging
import os
import uuid
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

# State definitions for ConversationHandler
SELECTING_PART, AWAITING_VOICE = range(2)

# Temporary directory for audio files
TEMP_AUDIO_DIR = "temp_audio"
if not os.path.exists(TEMP_AUDIO_DIR):
    os.makedirs(TEMP_AUDIO_DIR)

# Define skill levels and their score thresholds
SKILL_LEVELS = {
    "Advanced": 0.81,
    "Upper-Intermediate": 0.61,
    "Intermediate": 0.41,
    "Elementary": 0.21,
    "Beginner": 0.0,
}

def _update_skill_level(user: User, band_score: float) -> str | None:
    """
    Updates a user's skill level based on their performance in a speaking session.
    Returns the new skill level if it was changed, otherwise None.
    """
    if band_score is None:
        return None

    # Convert band score (1-9) to a percentage
    score_percent = band_score / 9.0

    new_skill_level = "Beginner"
    for level, threshold in SKILL_LEVELS.items():
        if score_percent >= threshold:
            new_skill_level = level
            break

    if user.skill_level != new_skill_level:
        user.update_skill_level(new_skill_level)
        return new_skill_level
    
    return None


def _get_recommendation(current_section="speaking"):
    """Gets a recommendation for the next practice section."""
    all_sections = ["speaking", "writing", "reading", "listening"]
    available_sections = [s for s in all_sections if s != current_section]
    return random.choice(available_sections)


async def start_speaking_practice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Starts the speaking practice session by showing part selection."""
    query = update.callback_query
    await query.answer()
    
    user = db.session.query(User).filter_by(user_id=query.from_user.id).first()
    if not user:
        await query.edit_message_text("User not found. Please /start the bot.")
        return ConversationHandler.END

    new_session = PracticeSession(user_id=user.id, section="speaking", total_questions=0)
    db.session.add(new_session)
    db.session.commit()
    context.user_data["practice_session_id"] = new_session.id
    
    lang_code = user.preferred_language
    keyboard = [
        [InlineKeyboardButton(TranslationSystem.get_message("speaking_practice", "part_1_button", lang_code), callback_data="sp_part_1")],
        [InlineKeyboardButton(TranslationSystem.get_message("speaking_practice", "part_2_button", lang_code), callback_data="sp_part_2")],
        [InlineKeyboardButton(TranslationSystem.get_message("general", "cancel_button", lang_code), callback_data="sp_cancel")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        text=TranslationSystem.get_message("speaking_practice", "intro", lang_code), reply_markup=reply_markup
    )
    return SELECTING_PART


async def handle_part_1(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles Speaking Part 1."""
    query = update.callback_query
    await query.answer()
    lang_code = TranslationSystem.detect_language(query.from_user.to_dict())
    
    openai_service = OpenAIService()
    question_data = openai_service.generate_speaking_question(part_number=1)
    
    question = question_data.get("question", "Let's talk about your hometown. What kind of place is it?")
    context.user_data["speaking_question"] = question
    context.user_data["speaking_part"] = 1

    message = TranslationSystem.get_message("speaking_practice", "please_send_voice_response", lang_code)
    await query.edit_message_text(text=f"Part 1: {question}\\n\\n{message}")
    return AWAITING_VOICE


async def handle_part_2(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles Speaking Part 2, which then leads to Part 3."""
    query = update.callback_query
    await query.answer()
    lang_code = TranslationSystem.detect_language(query.from_user.to_dict())
    
    openai_service = OpenAIService()
    question_data = openai_service.generate_speaking_question(part_number=2)

    question = question_data.get("question", "Describe a memorable journey you have taken.")
    topic = question_data.get("topic", "A memorable journey")
    
    context.user_data["speaking_question"] = question
    context.user_data["speaking_topic"] = topic
    context.user_data["speaking_part"] = 2

    message = TranslationSystem.get_message("speaking_practice", "please_send_voice_response", lang_code)
    await query.edit_message_text(text=f"Part 2: {question}\\n\\n{message}")
    return AWAITING_VOICE


async def handle_part_3_question(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Generates and asks a Part 3 question."""
    user = db.session.query(User).filter_by(user_id=update.effective_user.id).first()
    lang_code = user.preferred_language
    
    part_2_topic = context.user_data.get("speaking_topic", "your previous answer")
    
    openai_service = OpenAIService()
    question_data = openai_service.generate_speaking_question(part_number=3, topic=part_2_topic)
    question = question_data.get("question", f"Let's discuss more about {part_2_topic}. Why is it important?")
    
    context.user_data["speaking_question"] = question
    context.user_data["speaking_part"] = 3

    message = TranslationSystem.get_message("speaking_practice", "please_send_voice_response", lang_code)
    await context.bot.send_message(chat_id=update.effective_chat.id, text=f"Part 3: {question}\\n\\n{message}")
    return AWAITING_VOICE


async def handle_voice_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles the user's voice message, transcribes, gets feedback, and replies."""
    message = update.message
    voice = message.voice
    
    user = db.session.query(User).filter_by(user_id=message.from_user.id).first()
    lang_code = user.preferred_language
    
    session_id = context.user_data.get("practice_session_id")
    session = db.session.query(PracticeSession).filter_by(id=session_id).first()

    if not session:
        await message.reply_text(TranslationSystem.get_error_message("general", lang_code))
        return ConversationHandler.END

    if not voice:
        await message.reply_text(TranslationSystem.get_message("speaking_practice", "please_send_voice_prompt", lang_code))
        return AWAITING_VOICE

    await message.reply_text(TranslationSystem.get_message("speaking_practice", "processing_voice_message", lang_code))

    try:
        file = await context.bot.get_file(voice.file_id)
        file_name = f"{uuid.uuid4()}.ogg"
        file_path = os.path.join(TEMP_AUDIO_DIR, file_name)
        await file.download_to_drive(file_path)

        openai_service = OpenAIService()
        question = context.user_data.get("speaking_question", "")
        transcript = openai_service.speech_to_text(audio_file_path=file_path)
        
        part_number = context.user_data.get("speaking_part", 1)
        feedback = openai_service.generate_speaking_feedback(transcript, part_number, question)

        session.total_questions = (session.total_questions or 0) + 1
        current_session_data = session.session_data or []
        current_session_data.append({
            "part": part_number,
            "question": question,
            "transcript": transcript,
            "feedback": feedback,
        })
        session.session_data = current_session_data
        
        try:
            estimated_band = float(feedback.get('estimated_band', 0.0))
            session.score = ((session.score or 0.0) * (session.total_questions - 1) + estimated_band) / session.total_questions
            if estimated_band > 0:
                session.correct_answers = (session.correct_answers or 0) + 1
        except (ValueError, TypeError):
            pass # Keep score as is

        flag_modified(session, "session_data")
        db.session.commit()

        summary_message = format_feedback(feedback, lang_code)
        
        # Update skill level based on band score
        new_level = _update_skill_level(user, estimated_band)
        if new_level:
            level_up_message = TranslationSystem.get_message(
                "practice", "skill_level_up", lang_code, new_skill_level=new_level
            )
            summary_message += f"\\n\\n{level_up_message}"

        await message.reply_text(summary_message, parse_mode='Markdown')
        
        os.remove(file_path)

        if part_number == 2:
            return await handle_part_3_question(update, context)

    except Exception as e:
        logger.error(f"Error processing voice message: {e}", exc_info=True)
        await message.reply_text(TranslationSystem.get_error_message("general", lang_code))
        db.session.rollback()
        return ConversationHandler.END

    # If the practice session is over (not continuing to Part 3)
    session.completed_at = datetime.utcnow()
    db.session.commit()
    
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
    await message.reply_text(
        text=recommendation_text,
        reply_markup=InlineKeyboardMarkup([[recommendation_button]]),
    )

    return ConversationHandler.END


def format_feedback(feedback: dict, lang_code: str) -> str:
    """Formats the structured feedback into a user-friendly string."""
    try:
        band = feedback.get('estimated_band', 'N/A')
        strengths = "\\n- ".join(feedback.get('strengths', []))
        improvements = "\\n- ".join(feedback.get('areas_for_improvement', []))
        
        return (
            f"*{TranslationSystem.get_message('feedback', 'summary_title', lang_code)}*\\n\\n"
            f"*{TranslationSystem.get_message('feedback', 'estimated_band_label', lang_code)}:* {band}\\n\\n"
            f"*{TranslationSystem.get_message('feedback', 'strengths_label', lang_code)}:*\\n- {strengths}\\n\\n"
            f"*{TranslationSystem.get_message('feedback', 'improvements_label', lang_code)}:*\\n- {improvements}\\n\\n"
            f"*{TranslationSystem.get_message('feedback', 'vocabulary_label', lang_code)}:*\\n{feedback.get('vocabulary_feedback', '')}\\n\\n"
            f"*{TranslationSystem.get_message('feedback', 'grammar_label', lang_code)}:*\\n{feedback.get('grammar_feedback', '')}\\n\\n"
            f"*{TranslationSystem.get_message('feedback', 'fluency_label', lang_code)}:*\\n{feedback.get('fluency_feedback', '')}\\n\\n"
            f"*{TranslationSystem.get_message('feedback', 'pronunciation_label', lang_code)}:*\\n{feedback.get('pronunciation_feedback', '')}\\n\\n"
            f"*{TranslationSystem.get_message('feedback', 'next_tip_label', lang_code)}:*\\n_{feedback.get('tips_for_next', '')}_"
        )
    except Exception as e:
        logger.error(f"Error formatting feedback: {e}")
        return TranslationSystem.get_error_message("general", lang_code)


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancels and ends the conversation."""
    session_id = context.user_data.get("practice_session_id")
    if session_id:
        session = db.session.query(PracticeSession).filter_by(id=session_id).first()
        if session:
            db.session.delete(session)
            db.session.commit()

    query = update.callback_query
    if query:
        lang_code = TranslationSystem.detect_language(query.from_user.to_dict())
        await query.answer()
        await query.edit_message_text(text=TranslationSystem.get_message("general", "practice_canceled", lang_code))
    else:
        lang_code = TranslationSystem.detect_language(update.message.from_user.to_dict())
        await update.message.reply_text(TranslationSystem.get_message("general", "practice_canceled", lang_code))
        
    context.user_data.clear()
    return ConversationHandler.END


speaking_practice_conv_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(start_speaking_practice, pattern="^practice_speaking$")],
    states={
        SELECTING_PART: [
            CallbackQueryHandler(handle_part_1, pattern="^sp_part_1$"),
            CallbackQueryHandler(handle_part_2, pattern="^sp_part_2$"),
            CallbackQueryHandler(cancel, pattern="^sp_cancel$"),
        ],
        AWAITING_VOICE: [
            MessageHandler(filters.VOICE, handle_voice_message)
        ],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
    per_user=True,
    per_chat=True,
    per_message=False,
) 