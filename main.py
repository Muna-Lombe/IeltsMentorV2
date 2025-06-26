import asyncio
from pydub.audio_segment import os, sys
from app import app
from set_webhook import set_webhook


if __name__ == '__main__':
  # The bot polling and Flask app running are mutually exclusive in this script.
  # For production, you'd run the Flask app with a WSGI server (like Gunicorn)
  # and set up the Telegram webhook to point to your server's /webhook endpoint.
  # You would not run application.run_polling().

  # To run the bot with polling for development (without web interface):
  # import asyncio
  # asyncio.run(application.run_polling())

  # To run the Flask app for development (for web interface):
  token = os.environ['TELEGRAM_BOT_TOKEN']
  if not token:
      print("Error: TELEGRAM_BOT_TOKEN environment variable not set!")
      sys.exit(1)

  # if len(sys.argv) < 2:
  #     print("Usage: python set_webhook.py <your_https_webhook_url>")
  #     sys.exit(1)

  url = os.environ['DOMAIN_URL']
  if not url.startswith("https://"):
      print("Error: Webhook URL must start with https://")
      sys.exit(1)

  webhook_url_with_path = f"{url}/webhook"

  asyncio.run(set_webhook(token, webhook_url_with_path)) 
  app.run(host="0.0.0.0", port=5000, debug=True)