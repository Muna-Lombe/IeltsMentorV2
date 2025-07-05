import asyncio
import logging
import os
import requests
import json
from telegram import Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    filters,
)

from handlers.core_handlers import (
    start,
    stats_command,
    unknown_command,
)
from handlers.practice_handler import (
    practice_command,
    practice_section_callback,
)
from handlers.ai_commands_handler import (
    explain_command,
    define_command,
)
from handlers.teacher_handler import (
    create_group_conv_handler,
    assign_homework_conv_handler,
    group_analytics_conv_handler,
    student_progress_conv_handler,
)
from handlers.exercise_management_handler import (
    create_exercise_conv_handler,
    my_exercises_command,

)
from handlers.speaking_practice_handler import speaking_practice_conv_handler
from handlers.writing_practice_handler import writing_practice_conv_handler
from handlers.listening_practice_handler import listening_practice_conv_handler
from handlers.reading_practice_handler import reading_practice_conv_handler
from handlers.botmaster_handler import approve_teacher_conv_handler, system_stats, manage_content_conv_handler

logger = logging.getLogger(__name__)

# Global application object
application = None

def setup_bot():
    """Create and configure the bot application."""
    global application
    logger.info("Setting up bot...")
    
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        logger.error("TELEGRAM_BOT_TOKEN not set!")
        raise ValueError("TELEGRAM_BOT_TOKEN not set!")

    application = Application.builder().token(token).build()

    # Register handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler("practice", practice_command))
    application.add_handler(CallbackQueryHandler(practice_section_callback, pattern=r"practice_"))
    application.add_handler(CommandHandler("explain", explain_command))
    application.add_handler(CommandHandler("define", define_command))
    application.add_handler(CommandHandler("my_exercises", my_exercises_command))
    application.add_handler(CommandHandler("system_stats", system_stats))

    # Add conversation handlers
    application.add_handler(create_group_conv_handler)
    application.add_handler(create_exercise_conv_handler)
    application.add_handler(assign_homework_conv_handler)
    application.add_handler(group_analytics_conv_handler)
    application.add_handler(student_progress_conv_handler)
    application.add_handler(speaking_practice_conv_handler)
    application.add_handler(writing_practice_conv_handler)
    application.add_handler(listening_practice_conv_handler)
    application.add_handler(reading_practice_conv_handler)
    application.add_handler(approve_teacher_conv_handler)
    application.add_handler(manage_content_conv_handler)

    # Must be the last handler
    application.add_handler(MessageHandler(filters.COMMAND, unknown_command))
    
    logger.info("Bot setup complete.")
    return application

def get_application():
    """Return the application instance, creating it if it doesn't exist."""
    global application
    if application is None:
        setup_bot()
    return application

async def process_update(update_data):
    """Process a single update from the webhook."""
    app_instance = get_application()
    try:
        update = Update.de_json(update_data, app_instance.bot)
        await app_instance.process_update(update)
    except Exception as e:
        logger.error(f"Error processing update: {e}")
        import traceback
        logger.error(traceback.format_exc())

def set_webhook():
    """Set the bot's webhook URL."""
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        logger.error("No bot token available to set webhook.")
        return False, "No bot token available"

    domain_url = os.environ.get("DOMAIN_URL")
    if not domain_url:
        logger.error("DOMAIN_URL environment variable not set. Cannot set webhook.")
        return False, "DOMAIN_URL not set"

    webhook_url = f"https://{domain_url}/webhook"
    
    try:
        delete_response = requests.get(f"https://api.telegram.org/bot{token}/deleteWebhook")
        logger.info(f"Deleted existing webhook: {delete_response.json()}")

        allowed_updates = [
            "message", "edited_message", "channel_post", "edited_channel_post",
            "inline_query", "chosen_inline_result", "callback_query",
            "shipping_query", "pre_checkout_query", "poll", "poll_answer",
            "my_chat_member", "chat_member", "message_reaction", "message_reaction_count"
        ]
        allowed_updates_json = json.dumps(allowed_updates)

        response = requests.get(
            f"https://api.telegram.org/bot{token}/setWebhook?url={webhook_url}&allowed_updates={allowed_updates_json}"
        )
        result = response.json()
        logger.info(f"Set webhook response: {result}")

        if result.get("ok"):
            return True, result
        else:
            return False, result
    except Exception as e:
        logger.error(f"Error setting webhook: {e}")
        return False, str(e) 