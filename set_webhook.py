import os
import asyncio
import sys
from telegram import Bot

async def set_webhook(token, webhook_url):
    """Sets the webhook for the bot."""
    bot = Bot(token=token)
    await bot.set_webhook(url=webhook_url)
    print(f"Webhook set to {webhook_url}")

# if __name__ == "__main__":
#     token = os.getenv('TELEGRAM_BOT_TOKEN')
#     if not token:
#         print("Error: TELEGRAM_BOT_TOKEN environment variable not set!")
#         sys.exit(1)
        
#     if len(sys.argv) < 2:
#         print("Usage: python set_webhook.py <your_https_webhook_url>")
#         sys.exit(1)

#     url = sys.argv[1]
#     if not url.startswith("https://"):
#         print("Error: Webhook URL must start with https://")
#         sys.exit(1)
        
#     webhook_url_with_path = f"{url}/webhook"

#     asyncio.run(set_webhook(token, webhook_url_with_path)) 