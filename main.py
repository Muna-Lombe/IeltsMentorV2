import os
import logging
from flask import Flask, request, jsonify
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler

# Load environment variables from .env file
load_dotenv()

# Environment variables
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
FLASK_SECRET_KEY = os.getenv("FLASK_SECRET_KEY")
# WEBHOOK_URL = os.getenv("WEBHOOK_URL") # We might need this later for setting the webhook

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Set up file logging
log_file_path = "ielts_bot.log"
file_handler = logging.FileHandler(log_file_path)
file_handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
logging.getLogger().addHandler(file_handler) # Add to root logger to catch all logs

# Initialize Flask app
app = Flask(__name__)
app.secret_key = FLASK_SECRET_KEY

# Import handlers
from handlers.core_handlers import start_command
from handlers.practice_handler import practice_command, practice_section_callback, \
    PRACTICE_CALLBACK_SPEAKING, PRACTICE_CALLBACK_WRITING, \
    PRACTICE_CALLBACK_READING, PRACTICE_CALLBACK_LISTENING, \
    handle_reading_mcq_answer, CALLBACK_DATA_ANSWER_READING_PREFIX
from handlers.ai_commands_handler import explain_command, define_command # Import new AI command handlers

# Initialize Telegram Bot Application
if not TELEGRAM_BOT_TOKEN:
    logger.error("TELEGRAM_BOT_TOKEN not found in environment variables.")
    ptb_application = None # Or handle error as appropriate
else:
    ptb_application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Register handlers
    ptb_application.add_handler(CommandHandler("start", start_command))
    ptb_application.add_handler(CommandHandler("practice", practice_command)) # Add /practice handler
    
    # Add callback query handler for practice sections
    # Regex to match any of the defined practice callback data
    practice_callback_pattern = f"^({PRACTICE_CALLBACK_SPEAKING}|{PRACTICE_CALLBACK_WRITING}|{PRACTICE_CALLBACK_READING}|{PRACTICE_CALLBACK_LISTENING})$"
    ptb_application.add_handler(CallbackQueryHandler(practice_section_callback, pattern=practice_callback_pattern))

    # Add callback query handler for reading MCQ answers
    ptb_application.add_handler(CallbackQueryHandler(handle_reading_mcq_answer, pattern=f"^{CALLBACK_DATA_ANSWER_READING_PREFIX}"))

    # Register AI command handlers
    ptb_application.add_handler(CommandHandler("explain", explain_command))
    ptb_application.add_handler(CommandHandler("define", define_command))

    # Add other handlers here as they are developed

# Basic Flask route
@app.route("/")
def index():
    return "Hello, IELTS Prep Bot is alive! Flask is running."

# Webhook endpoint for Telegram
@app.route("/webhook", methods=["POST"])
async def webhook():
    if ptb_application:
        update_json = request.get_json(force=True)
        update = Update.de_json(update_json, ptb_application.bot)
        await ptb_application.process_update(update)
        return jsonify(status="ok"), 200
    else:
        logger.error("Telegram application not initialized, cannot process webhook.")
        return jsonify(status="error", message="Telegram bot not configured"), 500

async def main_bot_logic():
    if ptb_application:
        # Register handlers (ensure this is done if not above)
        # if not ptb_application.handlers: # Check if handlers are already added
        #     ptb_application.add_handler(CommandHandler("start", start_command))
        #     ptb_application.add_handler(CommandHandler("practice", practice_command))
        #     ptb_application.add_handler(CallbackQueryHandler(practice_section_callback, pattern=practice_callback_pattern))
        #     ptb_application.add_handler(CallbackQueryHandler(handle_reading_mcq_answer, pattern=f"^{CALLBACK_DATA_ANSWER_READING_PREFIX}"))
        #     ptb_application.add_handler(CommandHandler("explain", explain_command))
        #     ptb_application.add_handler(CommandHandler("define", define_command))

        # In a webhook setup, we don't usually run ptb_application.run_polling()
        # Instead, Telegram sends updates to our /webhook endpoint.
        # If you need to set the webhook URL for Telegram:
        # await ptb_application.bot.set_webhook(url=f"{WEBHOOK_URL}/webhook")
        # logger.info(f"Webhook set to {WEBHOOK_URL}/webhook")
        
        # For development without a public URL/SSL, you might use polling temporarily.
        # But for production with Flask, webhook is preferred.
        # Example: Start polling (remove or comment out for webhook deployment)
        # logger.info("Starting bot in polling mode for development...")
        # ptb_application.run_polling()
        pass # Webhook handles updates
    else:
        logger.error("Telegram bot application could not be started.")

if __name__ == "__main__":
    # Note: For production, use a WSGI server like Gunicorn, not Flask's dev server.
    # e.g., gunicorn --bind 0.0.0.0:5000 main:app
    
    # The bot logic (like setting webhook or starting polling) might be called here
    # or handled by a separate startup script for the bot component.
    # For now, we just ensure the Flask app can run.
    
    # If not using a WSGI server and want to run Flask dev server directly:
    # import asyncio
    # if ptb_application:
    #     asyncio.run(main_bot_logic()) # To set webhook or start polling if needed
    # app.run(debug=True, host="0.0.0.0", port=5000) # Port 5000 is from project_guide.md docker CMD
    logger.info("Flask app ready. Run with a WSGI server like Gunicorn for production.")
    logger.info("Example: gunicorn --bind 0.0.0.0:8000 main:app --worker-class uvicorn.workers.UvicornWorker")
    logger.info("Ensure TELEGRAM_BOT_TOKEN is set and (for webhooks) your app is accessible via a public URL.") 