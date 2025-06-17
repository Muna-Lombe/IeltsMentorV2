import logging
import os
import uuid
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    CommandHandler,
)

from services.openai_service import OpenAIService
from utils.translation_system import TranslationSystem

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# State definitions for ConversationHandler
SELECTING_PART, IN_PART_1, IN_PART_2, IN_PART_3, AWAITING_VOICE = range(5)

# Temporary directory for audio files
TEMP_AUDIO_DIR = "temp_audio"


async def start_speaking_practice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Starts the speaking practice session by showing part selection."""
    query = update.callback_query
    await query.answer()
    lang_code = TranslationSystem.detect_language(query.from_user.to_dict())

    keyboard = [
        [InlineKeyboardButton(TranslationSystem.get_message("speaking_practice", "part_1_button", lang_code), callback_data="sp_part_1")],
        [InlineKeyboardButton(TranslationSystem.get_message("speaking_practice", "part_2_button", lang_code), callback_data="sp_part_2")],
        [InlineKeyboardButton(TranslationSystem.get_message("speaking_practice", "part_3_button", lang_code), callback_data="sp_part_3")],
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
    
    # For now, using a hardcoded question. This will be replaced by OpenAI generation.
    question = "Let's talk about your hometown. What kind of place is it?"
    context.user_data["speaking_question"] = question
    context.user_data["speaking_part"] = 1

    message = TranslationSystem.get_message("speaking_practice", "please_send_voice_response", lang_code)
    await query.edit_message_text(text=f"Part 1: {question}\n\n{message}")
    return AWAITING_VOICE


async def handle_voice_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles the user's voice message, transcribes, gets feedback, and replies."""
    message = update.message
    voice = message.voice
    lang_code = TranslationSystem.detect_language(message.from_user.to_dict())

    if not voice:
        await message.reply_text(TranslationSystem.get_message("speaking_practice", "please_send_voice_prompt", lang_code))
        return AWAITING_VOICE

    await message.reply_text(TranslationSystem.get_message("speaking_practice", "processing_voice_message", lang_code))

    try:
        # Download the voice file
        file = await context.bot.get_file(voice.file_id)
        file_name = f"{uuid.uuid4()}.ogg"
        file_path = os.path.join(TEMP_AUDIO_DIR, file_name)
        await file.download_to_drive(file_path)

        # Transcribe the audio
        openai_service = OpenAIService()
        question = context.user_data.get("speaking_question", "")
        transcript = openai_service.speech_to_text(audio_file_path=file_path, prompt=question)
        logger.info(f"Transcript for user {update.effective_user.id}: {transcript}")

        # Get feedback from AI
        part_number = context.user_data.get("speaking_part", 1)
        feedback = openai_service.generate_speaking_feedback(transcript, part_number, question)

        # Format and send feedback
        feedback_text = format_feedback(feedback, lang_code)
        await message.reply_text(feedback_text)

        # Clean up the audio file
        os.remove(file_path)

    except Exception as e:
        logger.error(f"Error processing voice message: {e}", exc_info=True)
        await message.reply_text(TranslationSystem.get_error_message("general", lang_code))
        return ConversationHandler.END

    await message.reply_text(TranslationSystem.get_message("speaking_practice", "completed", lang_code))
    return ConversationHandler.END


def format_feedback(feedback: dict, lang_code: str) -> str:
    """Formats the structured feedback into a user-friendly string."""
    try:
        band = feedback.get('estimated_band', 'N/A')
        strengths = "\n- ".join(feedback.get('strengths', []))
        improvements = "\n- ".join(feedback.get('areas_for_improvement', []))
        
        return (
            f"*{TranslationSystem.get_message('feedback', 'summary_title', lang_code)}*\n\n"
            f"*{TranslationSystem.get_message('feedback', 'estimated_band_label', lang_code)}:* {band}\n\n"
            f"*{TranslationSystem.get_message('feedback', 'strengths_label', lang_code)}:*\n- {strengths}\n\n"
            f"*{TranslationSystem.get_message('feedback', 'improvements_label', lang_code)}:*\n- {improvements}\n\n"
            f"*{TranslationSystem.get_message('feedback', 'vocabulary_label', lang_code)}:*\n{feedback.get('vocabulary_feedback', '')}\n\n"
            f"*{TranslationSystem.get_message('feedback', 'grammar_label', lang_code)}:*\n{feedback.get('grammar_feedback', '')}\n\n"
            f"*{TranslationSystem.get_message('feedback', 'fluency_label', lang_code)}:*\n{feedback.get('fluency_feedback', '')}\n\n"
            f"*{TranslationSystem.get_message('feedback', 'pronunciation_label', lang_code)}:*\n{feedback.get('pronunciation_feedback', '')}\n\n"
            f"*{TranslationSystem.get_message('feedback', 'next_tip_label', lang_code)}:*\n_{feedback.get('tips_for_next', '')}_"
        )
    except Exception as e:
        logger.error(f"Error formatting feedback: {e}")
        return TranslationSystem.get_error_message("general", lang_code)


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancels and ends the conversation."""
    query = update.callback_query
    if query:
        lang_code = TranslationSystem.detect_language(query.from_user.to_dict())
        await query.answer()
        await query.edit_message_text(text=TranslationSystem.get_message("general", "practice_canceled", lang_code))
    else:
        lang_code = TranslationSystem.detect_language(update.message.from_user.to_dict())
        await update.message.reply_text(TranslationSystem.get_message("general", "practice_canceled", lang_code))
        
    logger.info(f"User {update.effective_user.id} canceled the speaking practice.")
    context.user_data.pop("speaking_question", None)
    context.user_data.pop("speaking_part", None)
    return ConversationHandler.END


# Dummy handlers for parts 2 and 3 for now
async def handle_part_2(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    lang_code = TranslationSystem.detect_language(query.from_user.to_dict())
    await query.edit_message_text(text=TranslationSystem.get_message("general", "feature_not_implemented", lang_code))
    return ConversationHandler.END

async def handle_part_3(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    lang_code = TranslationSystem.detect_language(query.from_user.to_dict())
    await query.edit_message_text(text=TranslationSystem.get_message("general", "feature_not_implemented", lang_code))
    return ConversationHandler.END


speaking_practice_conv_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(start_speaking_practice, pattern="^practice_speaking$")],
    states={
        SELECTING_PART: [
            CallbackQueryHandler(handle_part_1, pattern="^sp_part_1$"),
            CallbackQueryHandler(handle_part_2, pattern="^sp_part_2$"),
            CallbackQueryHandler(handle_part_3, pattern="^sp_part_3$"),
            CallbackQueryHandler(cancel, pattern="^sp_cancel$"),
        ],
        AWAITING_VOICE: [
            MessageHandler(filters.VOICE, handle_voice_message)
        ],
        # IN_PART_1, IN_PART_2, IN_PART_3 will be used for multi-turn conversations
    },
    fallbacks=[CommandHandler("cancel", cancel)],
    per_user=True,
    per_chat=True
) 