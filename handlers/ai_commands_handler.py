import logging
from telegram import Update
from telegram.ext import ContextTypes

from utils.translation_system import TranslationSystem
from services.openai_service import OpenAIService
from .decorators import error_handler

logger = logging.getLogger(__name__)

@error_handler
async def explain_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles the /explain command to provide AI-powered explanations."""
    user = update.effective_user
    lang_code = TranslationSystem.detect_language(user.to_dict())

    if not context.args or len(context.args) < 2:
        message = TranslationSystem.get_message("ai_commands", "explain_usage", lang_code)
        await update.message.reply_text(message)
        return

    # e.g., /explain grammar present perfect
    ai_context = context.args[0]
    query = " ".join(context.args[1:])
    
    # Let the user know the bot is working
    thinking_message = await update.message.reply_text(
        TranslationSystem.get_message('ai', 'thinking', lang_code)
    )

    ai_service = OpenAIService()
    try:
        explanation = ai_service.generate_explanation(
            query=query, context=ai_context, language=lang_code
        )
        final_message = f"{TranslationSystem.get_message('ai', 'explanation_header', lang_code, query=query)}\n\n{explanation}"
        await thinking_message.edit_text(final_message)
    except Exception as e:
        logger.error(f"Error calling OpenAI service for /explain: {e}", exc_info=True)
        error_message = TranslationSystem.get_error_message("general", lang_code)
        await thinking_message.edit_text(error_message)


@error_handler
async def define_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles the /define command to provide AI-powered definitions."""
    user = update.effective_user
    lang_code = TranslationSystem.detect_language(user.to_dict())

    if not context.args or len(context.args) > 1:
        message = TranslationSystem.get_message("ai_commands", "define_usage", lang_code)
        await update.message.reply_text(message)
        return

    word_to_define = context.args[0]

    # Let the user know the bot is working
    thinking_message = await update.message.reply_text(
        TranslationSystem.get_message('ai', 'thinking', lang_code)
    )

    ai_service = OpenAIService()
    try:
        definition = ai_service.generate_definition(
            word=word_to_define, language=lang_code
        )
        final_message = f"{TranslationSystem.get_message('ai', 'definition_header', lang_code, word=word_to_define)}\n\n{definition}"
        await thinking_message.edit_text(final_message)
    except Exception as e:
        logger.error(f"Error calling OpenAI service for /define: {e}", exc_info=True)
        error_message = TranslationSystem.get_error_message("general", lang_code)
        await thinking_message.edit_text(error_message)

# Suggested translation keys for en.json / es.json:
# "ai_commands": {
#     "explain_usage": "Please provide something to explain. Usage: /explain <your query>",
#     "processing_explanation": "Generating explanation, please wait...",
#     "explanation_failed": "Sorry, I couldn't generate an explanation for that. Please try again or rephrase your query.",
#     "define_usage": "Please provide a single word to define. Usage: /define <word>",
#     "processing_definition": "Looking up definition, please wait...",
#     "definition_failed": "Sorry, I couldn't find a definition for '{word}'. Please ensure it's a valid word and try again."
# },
# "errors": {
#     "general_ai_error": "Sorry, there was an issue with the AI service. Please try again later."
# } 