import datetime
import os

import functions_framework
import pytz
from cloudevents.http import CloudEvent
from google.cloud import firestore

from ai_agent import get_chat_response
from logging_config import logger
from telegram import answer_callback_query, parse_command, send_message
from utils import format_currency
from expenses import list_expenses
from setup_handlers import start_timezone_setup
from start_handler import handle_start_command

db = firestore.Client()


@functions_framework.http
def telegram_webhook(request):
    """Webhook entrypoint for Telegram updates."""
    try:
        expected_token = os.environ.get("WEBHOOK_SECRET")
        request_token = request.args.get("token")
        if not expected_token or request_token != expected_token:
            return "Unauthorized", 401

        update = request.get_json()
        logger.debug(f"Received update: {update}")
        if not update:
            return "Invalid request", 400

        if "edited_message" in update:
            return "OK"

        if "message" in update:
            message = update["message"]
            chat_id = message.get("chat", {}).get("id")
            user_id = message.get("from", {}).get("id")
            text = message.get("text", "")

            if not chat_id or not text or not user_id:
                return "Invalid message", 400

            whitelist = os.environ.get("WHITELIST_USER_IDS", "").strip()
            if whitelist:
                if str(user_id) not in [uid.strip() for uid in whitelist.split(",")]:
                    return "OK"

            command, args = parse_command(text)

            if command == "/list_expenses":
                _handle_list_expenses(chat_id)

            elif command == "/list_commands":
                _handle_list_commands(chat_id)

            elif command == "/set_timezone":
                start_timezone_setup(chat_id)
                return "OK"

            elif command == "/set_currency":
                _handle_set_currency(chat_id, args)

            elif command == "/start":
                handle_start_command(chat_id)
                return "OK"

            elif command is None:
                # Check if user is in currency setup flow
                from start_handler import process_start_message

                if process_start_message(chat_id, text):
                    return "OK"

                ai_response = get_chat_response(chat_id, text)
                logger.debug(f"Sending AI response to user {chat_id}")
                send_message(chat_id, ai_response)

            else:
                send_message(chat_id, "Unknown command. Use /list_commands to see options.")

        elif "callback_query" in update:
            callback_query = update["callback_query"]
            chat_id = callback_query["message"]["chat"]["id"]
            callback_data = callback_query["data"]
            callback_query_id = callback_query["id"]
            answer_callback_query(callback_query_id)
            # currently callbacks are only used for timezone setup from shared handlers
            from setup_handlers import process_setup_callback

            process_setup_callback(chat_id, callback_data)
            return "OK"

        return "OK"

    except Exception as e:
        logger.error(f"Error in telegram_webhook (expense bot): {e}")
        return "Error", 500


def _handle_list_expenses(chat_id: int):
    user_doc = db.collection("users").document(str(chat_id)).get()
    data = user_doc.to_dict() if user_doc.exists else {}
    tz_name = data.get("timezone", "UTC")
    user_tz = pytz.timezone(tz_name)

    rows = list_expenses(chat_id, limit=20)
    if not rows:
        send_message(chat_id, "No expenses recorded yet.")
        return

    lines = ["Recent expenses:"]
    for r in rows:
        spent_at = r.get("spent_at")
        if isinstance(spent_at, datetime.datetime):
            dt_local = spent_at.astimezone(user_tz)
            ts = dt_local.strftime("%Y-%m-%d %H:%M")
        else:
            ts = "unknown time"
        amount_str = format_currency(float(r.get("amount", 0)), r.get("currency", ""))
        category = r.get("category", "uncategorized")
        desc = r.get("description", "")
        lines.append(f"- {ts} | {category}: {amount_str} – {desc}")

    send_message(chat_id, "\n".join(lines))


def _handle_list_commands(chat_id: int):
    commands_msg = """Available commands:
/start - Show intro and basic setup
/set_timezone - Set your timezone
/set_currency <CODE> - Set your default currency (e.g. EUR, INR, USD)
/list_expenses - Show your most recent expenses

You can also talk to me naturally, for example:
- I spent 500 on food yesterday
- How much did I spend this week on transport?
- Show my expenses for last 3 days
"""
    send_message(chat_id, commands_msg)


def _handle_set_currency(chat_id: int, args):
    if not args:
        send_message(chat_id, "Usage: /set_currency <CODE>\nExample: /set_currency EUR")
        return
    code = args[0].upper()
    if len(code) != 3:
        send_message(chat_id, "Currency code should be a 3-letter code like EUR, INR, USD.")
        return
    db.collection("users").document(str(chat_id)).set({"currency": code}, merge=True)
    send_message(chat_id, f"✅ Currency set to {code}. I will use this in all summaries and when logging expenses without an explicit currency.")


@functions_framework.cloud_event
def scheduler_tick(cloud_event: CloudEvent):
    """Placeholder scheduler for future periodic analytics or summaries."""
    try:
        # For now, no periodic work is required; keeping the function so infra wiring matches template.
        return "OK"
    except Exception as e:
        logger.error(f"Error in scheduler_tick (expense bot): {e}")
        return "Error", 500

