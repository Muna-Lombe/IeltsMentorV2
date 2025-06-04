import logging
from telegram import Update
from telegram.ext import ContextTypes

from utils.decorators import safe_handler
from utils.translation_system import get_message
from services.openai_service import OpenAIService

logger = logging.getLogger(__name__)

@safe_handler(error_category="errors", error_key="general_ai_error") # Using a general AI error key
async def explain_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles the /explain command to provide AI-powered explanations."""
    user = update.effective_user
    lang_code = user.language_code if user else "en"

    if not context.args:
        message = get_message("ai_commands", "explain_usage", lang_code, 
                                default="Please provide something to explain. Usage: /explain <your query>")
        await update.message.reply_text(message)
        return

    query_to_explain = " ".join(context.args)
    
    # Notify user that we are working on it
    processing_message = get_message("ai_commands", "processing_explanation", lang_code, default="Generating explanation, please wait...")
    await update.message.reply_text(processing_message)

    try:
        ai_service = OpenAIService()
        explanation = ai_service.generate_explanation(query=query_to_explain, language=lang_code)

        if explanation:
            # The explanation from AI is directly sent.
            # If we wanted to wrap it, e.g. "Here is the explanation for ...:", we would use get_message here.
            await update.message.reply_text(explanation)
        else:
            error_message = get_message("ai_commands", "explanation_failed", lang_code, default="Sorry, I couldn't generate an explanation for that. Please try again.")
            await update.message.reply_text(error_message)
    except Exception as e:
        logger.error(f"Error in /explain command for query '{query_to_explain}': {e}")
        # The @safe_handler will catch this and send its generic message, or we can send a specific one here too.
        # For now, let the safe_handler manage it.
        raise # Re-raise for the safe_handler to catch and send a translated error message

@safe_handler(error_category="errors", error_key="general_ai_error")
async def define_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles the /define command to provide AI-powered definitions."""
    user = update.effective_user
    lang_code = user.language_code if user else "en"

    if not context.args or len(context.args) > 1:
        message = get_message("ai_commands", "define_usage", lang_code, default="Please provide a single word to define. Usage: /define <word>")
        await update.message.reply_text(message)
        return

    word_to_define = context.args[0]

    # Notify user that we are working on it
    processing_message = get_message("ai_commands", "processing_definition", lang_code, default="Looking up definition, please wait...")
    await update.message.reply_text(processing_message)

    try:
        ai_service = OpenAIService()
        definition = ai_service.generate_definition(word=word_to_define, language=lang_code)

        if definition:
            await update.message.reply_text(definition)
        else:
            error_message = get_message("ai_commands", "definition_failed", lang_code, default=f"Sorry, I couldn't find a definition for '{word_to_define}'. Please ensure it's a valid word.")
            await update.message.reply_text(error_message)
    except Exception as e:
        logger.error(f"Error in /define command for word '{word_to_define}': {e}")
        raise # Re-raise for the safe_handler

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