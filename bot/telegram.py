import requests
import json
import os

def get_bot_token():
    """Retrieve Telegram bot token from environment."""
    return os.environ['TELEGRAM_BOT_TOKEN']

def send_message(chat_id, text, bot_token=None):
    """Send a message via Telegram Bot API."""
    if bot_token is None:
        bot_token = get_bot_token()

    # Split text into chunks of 4000 characters
    messages = [text[i:i+4000] for i in range(0, len(text), 4000)]

    results = []
    for msg in messages:
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": msg,
            "parse_mode": "Markdown",
        }
        response = requests.post(url, json=payload)
        results.append(response.json())

    return results

def set_webhook(url, bot_token=None):
    """Set Telegram webhook URL."""
    if bot_token is None:
        bot_token = get_bot_token()

    webhook_url = f"https://api.telegram.org/bot{bot_token}/setWebhook"
    payload = {
        "url": url
    }
    response = requests.post(webhook_url, json=payload)
    return response.json()

def parse_command(text):
    """Parse incoming message text for commands."""
    if not text.startswith('/'):
        return None, None

    parts = text.split()
    command = parts[0].lower()
    args = parts[1:] if len(parts) > 1 else []

    return command, args
