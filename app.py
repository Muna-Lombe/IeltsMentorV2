import os
import logging
from flask import Flask, request, jsonify
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler

from extensions import db, migrate
from config import config
from handlers import (
    core_handlers, 
    practice_handler, 
    ai_commands_handler, 
    teacher_handler, 
    exercise_management_handler,
    speaking_practice_handler,
    writing_practice_handler
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize the Telegram Bot Application
telegram_bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
if not telegram_bot_token:
    raise ValueError("TELEGRAM_BOT_TOKEN environment variable not set!")

application = Application.builder().token(telegram_bot_token).build()

# Register handlers
application.add_handler(CommandHandler("start", core_handlers.start))
application.add_handler(CommandHandler("stats", core_handlers.stats_command))
application.add_handler(CommandHandler("practice", practice_handler.practice_command))
application.add_handler(CommandHandler("explain", ai_commands_handler.explain_command))
application.add_handler(CommandHandler("define", ai_commands_handler.define_command))
application.add_handler(teacher_handler.create_group_conv_handler)
application.add_handler(CommandHandler("my_exercises", exercise_management_handler.my_exercises_command))
application.add_handler(exercise_management_handler.create_exercise_conv_handler)
application.add_handler(speaking_practice_handler.speaking_practice_conv_handler)
application.add_handler(writing_practice_handler.writing_practice_conv_handler)

# Register callback query handlers
application.add_handler(CallbackQueryHandler(practice_handler.practice_section_callback, pattern=f"^{practice_handler.PRACTICE_CALLBACK_LISTENING}|{practice_handler.PRACTICE_CALLBACK_READING}|{practice_handler.PRACTICE_CALLBACK_SPEAKING}|{practice_handler.PRACTICE_CALLBACK_WRITING}"))
application.add_handler(CallbackQueryHandler(practice_handler.handle_reading_answer, pattern=f"^reading_answer:"))

# Fallback for unknown commands
application.add_handler(MessageHandler(filters.COMMAND, core_handlers.unknown_command))

def create_app(config_name='development'):
    """Create and configure an instance of the Flask application."""
    app = Flask(__name__)
    
    # Load config from config.py
    app.config.from_object(config[config_name])

    # Initialize extensions with the app
    db.init_app(app)
    migrate.init_app(app, db)

    # Import models and register routes within the app context
    with app.app_context():
        from models.user import User
        from models.practice_session import PracticeSession

        @app.route("/")
        def index():
            return "Hello, IELTS Prep Bot is alive! Flask is running."

        @app.route("/webhook", methods=["POST"])
        async def webhook():
            """Webhook endpoint to receive updates from Telegram."""
            if request.is_json:
                update_data = request.get_json()
                update = Update.de_json(update_data, application.bot)
                await application.process_update(update)
                return jsonify(status="ok")
            else:
                return jsonify(status="bad request", error="Request must be JSON"), 400
            
    return app

# The flask command will now call create_app
app = create_app()

# ... (rest of your Telegram bot setup) ... 