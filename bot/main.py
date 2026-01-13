import functions_framework
from cloudevents.http import CloudEvent
import json
import logging
import os
import random
from telegram import send_message, parse_command
from reminders import create_reminder, get_reminders, delete_reminder, get_due_reminders, mark_reminder_sent
from ai_agent import get_chat_response, set_user_system_prompt, generate_agent_reachout_message
from google.cloud import firestore
import datetime
import pytz

db = firestore.Client()

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
        print(f"update is: {update}")
        if not update:
            return 'Invalid request', 400

        if 'edited_message' in update:
            return 'OK'

        # Handle different update types
        if 'message' in update:
            # Process message as before
            message = update['message']

        message = update['message']
        chat_id = message.get('chat', {}).get('id')
        text = message.get('text', '')

        if not chat_id or not text:
            return 'Invalid message', 400

        command, args = parse_command(text)

        if command == '/remind':
            # /remind <time> <text> [interval]
            if len(args) < 2:
                send_message(chat_id, "Usage: /remind <time> <text> [interval]\nExample: /remind 2026-01-15T09:00:00+00:00 workout daily")
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
                next_run = datetime.datetime.fromisoformat(time_str)
                if next_run.tzinfo is None:
                    next_run = pytz.UTC.localize(next_run)
                else:
                    next_run = next_run.astimezone(pytz.UTC)

                reminder_id = create_reminder(chat_id, reminder_text, next_run, interval, 'external')
                send_message(chat_id, f"Reminder set for {next_run.strftime('%Y-%m-%d %H:%M %Z')}")
                logging.info(f"Reminder created: {reminder_id}")
            except Exception as e:
                logging.error(f"Time parsing failed for '{time_str}': {str(e)}")
                send_message(chat_id, f"Invalid time format '{time_str}'. Expected ISO datetime string in UTC (e.g., 2026-01-15T09:00:00+00:00)")

        elif command == '/list':
            reminders = get_reminders(chat_id, 'external')
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
                reminders = get_reminders(chat_id, 'external')
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

        elif command == '/system_prompt':
            if not args:
                send_message(chat_id, "Usage: /system_prompt <your prompt text>\nExample: /system_prompt You are a fitness coach focused on strength training.")
                return 'OK'
            prompt_text = ' '.join(args)
            set_user_system_prompt(chat_id, prompt_text)
            send_message(chat_id, f"System prompt updated! I'll now respond according to: {prompt_text}")

        elif command is None:
            # Not a command, treat as natural language message to AI
            ai_response = get_chat_response(chat_id, text, mode="respond_user")
            print(f"sending AI message: {ai_response}")
            result = send_message(chat_id, ai_response)
            logging.info(f"Send message results: {result}")
            # Update last AI message timestamp
            doc_ref = db.collection('users').document(str(chat_id))
            doc_ref.set({'last_ai_message': firestore.SERVER_TIMESTAMP}, merge=True)

        else:
            send_message(chat_id, "Unknown command. Use /remind, /list, /delete, or /system_prompt.")

        return 'OK'

    except Exception as e:
        logging.error(f"Error in telegram_webhook: {e}")
        return 'Error', 500

@functions_framework.cloud_event
def scheduler_tick(cloud_event: CloudEvent):
    """Check for due reminders and send them."""
    try:
        due_reminders = get_due_reminders()
        processed_count = 0
        for doc in due_reminders:
            data = doc.to_dict()
            chat_id = data['chat_id']
            reminder_type = data.get('type', 'external')
            interval = data.get('interval')

            if reminder_type == 'external':
                # Regular reminder
                message_text = f"Reminder: {data['text']}"
                send_message(chat_id, message_text)
            elif reminder_type == 'internal':
                # AI-triggered reminder
                message_text = generate_agent_reachout_message(data, chat_id)
                send_message(chat_id, message_text)
            # system type not handled here

            mark_reminder_sent(doc.reference, interval)
            processed_count += 1

        # System reachout check every hour at :00 minutes
        now = datetime.datetime.utcnow().replace(tzinfo=pytz.UTC)
        if now.minute == 0 and 6 <= now.hour < 22:  # Exclude night hours 22:00-06:00 UTC
            twelve_hours_ago = now - datetime.timedelta(hours=12)
            users_to_reachout = db.collection('users').where('last_ai_message', '<', twelve_hours_ago).stream()
            reachout_count = 0
            for user_doc in users_to_reachout:
                chat_id = int(user_doc.id)

                # Check if last 3 messages were from AI agent
                last_messages = db.collection('chat_history').where('chat_id', '==', chat_id).order_by('timestamp', direction=firestore.Query.DESCENDING).limit(3).stream()
                last_three_from_ai = all(doc.to_dict().get('role') == 'assistant' for doc in last_messages)

                if not last_three_from_ai and random.random() < 0.2:  # 20% probability, but skip if last 3 were from AI
                    message_text = generate_agent_reachout_message({'text': 'general check-in'}, chat_id)
                    send_message(chat_id, message_text)
                    # Update last AI message timestamp
                    user_doc.reference.set({'last_ai_message': firestore.SERVER_TIMESTAMP}, merge=True)
                    reachout_count += 1

            logging.info(f"System reachout: checked users, sent {reachout_count} messages")

        return f"Processed {processed_count} reminders, {reachout_count if 'reachout_count' in locals() else 0} system reachouts"

    except Exception as e:
        logging.error(f"Error in scheduler_tick: {e}")
        return 'Error', 500
