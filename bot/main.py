import functions_framework
from cloudevents.http import CloudEvent
import json
import logging
import os
from telegram import send_message, parse_command
from reminders import create_reminder, get_reminders, delete_reminder, get_due_reminders, mark_reminder_sent
import datetime
import pytz
from dateutil import parser as date_parser

logging.basicConfig(level=logging.INFO)

@functions_framework.http
def telegram_webhook(request):
    """Handle incoming Telegram messages with token authentication."""
    try:
        # Check webhook authentication token
        expected_token = os.environ.get('WEBHOOK_SECRET')
        request_token = request.args.get('token')

        if not expected_token or request_token != expected_token:
            return 'Unauthorized', 401

        # Request body is the Telegram update JSON
        update = request.get_json()
        if not update or 'message' not in update:
            return 'Invalid Telegram update', 400

        message = update['message']
        chat_id = message.get('chat', {}).get('id')
        text = message.get('text', '')

        if not chat_id or not text:
            return 'Invalid message', 400

        command, args = parse_command(text)

        if command == '/remind':
            # /remind <time> <text> [interval]
            if len(args) < 2:
                send_message(chat_id, "Usage: /remind <time> <text> [interval]\nExamples:\n/remind tomorrow 'brush teeth' daily\n/remind '2026-01-10 09:00' workout")
                return 'OK'

            # Debug logging
            logging.info(f"Remind command args: {args}")

            # Parse arguments - handle interval at end
            if len(args) >= 3 and args[-1] in ['daily', 'weekly', 'monthly']:
                time_str = args[0]
                reminder_text = ' '.join(args[1:-1])
                interval = args[-1]
            else:
                time_str = args[0]
                reminder_text = ' '.join(args[1:])
                interval = None

            logging.info(f"Parsed: time='{time_str}', text='{reminder_text}', interval={interval}")

            try:
                next_run = date_parser.parse(time_str)
                if next_run.tzinfo is None:
                    next_run = pytz.UTC.localize(next_run)
                reminder_id = create_reminder(chat_id, reminder_text, next_run, interval)
                send_message(chat_id, f"Reminder set for {next_run.strftime('%Y-%m-%d %H:%M %Z')}")
                logging.info(f"Reminder created: {reminder_id}")
            except Exception as e:
                logging.error(f"Time parsing failed for '{time_str}': {str(e)}")
                send_message(chat_id, f"Invalid time format '{time_str}'. Error: {str(e)}\n\nTry formats like:\n• tomorrow\n• 2026-01-10 09:00\n• in 2 hours\n• 8am")

        elif command == '/list':
            reminders = get_reminders(chat_id)
            if not reminders:
                send_message(chat_id, "No active reminders.")
            else:
                msg = "Active reminders:\n"
                for i, r in enumerate(reminders, 1):
                    msg += f"{i}. {r['text']} - {r['next_run']}\n"
                send_message(chat_id, msg)

        elif command == '/delete':
            if not args:
                send_message(chat_id, "Usage: /delete <reminder_number>")
                return 'OK'
            try:
                idx = int(args[0]) - 1
                reminders = get_reminders(chat_id)
                if 0 <= idx < len(reminders):
                    reminder_id = reminders[idx]['id']
                    if delete_reminder(chat_id, reminder_id):
                        send_message(chat_id, "Reminder deleted.")
                    else:
                        send_message(chat_id, "Failed to delete reminder.")
                else:
                    send_message(chat_id, "Invalid reminder number.")
            except ValueError:
                send_message(chat_id, "Invalid number.")

        else:
            send_message(chat_id, "Unknown command. Use /remind, /list, or /delete.")

        return 'OK'

    except Exception as e:
        logging.error(f"Error in telegram_webhook: {e}")
        return 'Error', 500

@functions_framework.cloud_event
def scheduler_tick(cloud_event: CloudEvent):
    """Check for due reminders and send them."""
    try:
        due_reminders = get_due_reminders()
        for doc in due_reminders:
            data = doc.to_dict()
            chat_id = data['chat_id']
            text = data['text']
            interval = data.get('interval')
            send_message(chat_id, f"Reminder: {text}")
            mark_reminder_sent(doc.reference, interval)

        return f"Processed {len(due_reminders)} reminders"

    except Exception as e:
        logging.error(f"Error in scheduler_tick: {e}")
        return 'Error', 500
