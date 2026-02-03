import requests
import os
from logging_config import logger

def get_bot_token():
    """Retrieve Telegram bot token from environment."""
    return os.environ['TELEGRAM_BOT_TOKEN']

def send_message(chat_id, text, bot_token=None, reply_markup=None):
    if bot_token is None:
        bot_token = get_bot_token()

    # Split text into chunks of 4000 characters
    messages = [text[i:i+4000] for i in range(0, len(text), 4000)]

    # Use Markdown only if there's a single chunk (short message)
    parse_mode = None #"Markdown" if len(messages) == 1 else None

    results = []
    for msg in messages:
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": msg,
        }
        if parse_mode:
            payload["parse_mode"] = parse_mode
        if reply_markup:
            payload["reply_markup"] = reply_markup
        response = requests.post(url, json=payload)
        logger.debug(f"Telegram API response status: {response.status_code}")
        logger.debug(f"Telegram API response body: {response.json()}")
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

def answer_callback_query(callback_query_id, text=None, bot_token=None):
    """Answer a callback query to acknowledge button press."""
    if bot_token is None:
        bot_token = get_bot_token()

    url = f"https://api.telegram.org/bot{bot_token}/answerCallbackQuery"
    payload = {
        "callback_query_id": callback_query_id
    }
    if text:
        payload["text"] = text
    response = requests.post(url, json=payload)
    return response.json()

def parse_command(text):
    """Parse incoming message text for commands."""
    if not text.startswith('/'):
        return None, None

    parts = text.split()
    command = parts[0].lower()
    args = parts[1:] if len(parts) > 1 else []

    return command, args
