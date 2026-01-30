import functions_framework
from cloudevents.http import CloudEvent
import os
import random
from telegram import send_message, parse_command, answer_callback_query
from reminders import create_reminder, get_reminders, delete_reminder, get_due_reminders, mark_reminder_sent
from ai_agent import get_chat_response, set_user_system_prompt, set_user_api_exhausted_message, generate_agent_reachout_message
from setup_handlers import process_setup_callback, start_timezone_setup
from start_handler import handle_start_command, process_start_callback
from google.cloud import firestore
import datetime
import pytz
from utils import format_repeat_days
from logging_config import logger

db = firestore.Client()

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
        logger.debug(f"Received update: {update}")
        if not update:
            return 'Invalid request', 400

        if 'edited_message' in update:
            return 'OK'

        # Handle different update types
        if 'message' in update:
            message = update['message']
            chat_id = message.get('chat', {}).get('id')
            user_id = message.get('from', {}).get('id')
            text = message.get('text', '')

            if not chat_id or not text or not user_id:
                return 'Invalid message', 400

            # Check whitelist if configured
            whitelist = os.environ.get('WHITELIST_USER_IDS', '').strip()

            if whitelist:
                logger.debug(f"Checking whitelist for user_id: {user_id}")
                if str(user_id) not in [uid.strip() for uid in whitelist.split(',')]:
                    return 'OK'

            command, args = parse_command(text)

            if command == '/remind':
                # /remind <time> <text> [repeat_days]
                if len(args) < 2:
                    send_message(chat_id, "Usage: /remind <time> <text> [repeat_days]\nExample: /remind 2026-01-15T09:00:00+00:00 workout 1,3")
                    return 'OK'

                # Debug logging
                logger.info(f"Remind command args: {args}")

                # Parse arguments - handle repeat at end
                try:
                    repeat = [int(x.strip()) for x in args[-1].split(',')]
                    time_str = args[0]
                    reminder_text = ' '.join(args[1:-1])
                except (ValueError, IndexError):
                    time_str = args[0]
                    reminder_text = ' '.join(args[1:])
                    repeat = None

                logger.info(f"Parsed: time='{time_str}', text='{reminder_text}', repeat={repeat}")

                try:
                    next_run = datetime.datetime.fromisoformat(time_str)
                    # Don't convert to UTC here - pass the local time directly to create_reminder
                    # create_reminder will handle timezone conversion internally
                    reminder_id = create_reminder(chat_id, reminder_text, next_run, repeat)
                    # Get user timezone to display the time correctly
                    user_doc = db.collection('users').document(str(chat_id)).get()
                    user_data = user_doc.to_dict() if user_doc.exists else {}
                    user_tz_str = user_data.get('timezone', 'UTC')
                    user_tz = pytz.timezone(user_tz_str)
                    
                    if next_run.tzinfo is None:
                        next_run_local = user_tz.localize(next_run)
                    else:
                        next_run_local = next_run.astimezone(user_tz)
                    
                    send_message(chat_id, f"Reminder set for {next_run_local.strftime('%Y-%m-%d %H:%M')}")
                    logger.info(f"Reminder created: {reminder_id}")
                except Exception as e:
                    logger.error(f"Time parsing failed for '{time_str}': {str(e)}")
                    send_message(chat_id, f"Invalid time format '{time_str}'. Expected ISO datetime string (e.g., 2026-01-15T09:00:00 or 2026-01-15T09:00:00+02:00)")

            elif command == '/list':
                # Get user timezone
                user_doc = db.collection('users').document(str(chat_id)).get()
                user_data = user_doc.to_dict() if user_doc.exists else {}
                user_tz_str = user_data.get('timezone', 'UTC')
                user_tz = pytz.timezone(user_tz_str)

                reminders = get_reminders(chat_id)
                if not reminders:
                    send_message(chat_id, "No active reminders.")
                else:
                    msg = "Active reminders:\n"
                    for i, r in enumerate(reminders, 1):
                        # Use the display_time from get_reminders function
                        display_time = r.get('display_time', '')
                        repeat_info = format_repeat_days(r.get('repeat', []))
                        msg += f"{i}. {r['text']} - {display_time}{repeat_info}\n"
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

            elif command == '/system_prompt':
                if not args:
                    send_message(chat_id, "Usage: /system_prompt <your prompt text>\nExample: /system_prompt You are a fitness coach focused on strength training.")
                    return 'OK'
                prompt_text = ' '.join(args)
                set_user_system_prompt(chat_id, prompt_text)
                send_message(chat_id, f"System prompt updated! I'll now respond according to: {prompt_text}")

            elif command == '/set_api_exhausted_message':
                if not args:
                    send_message(chat_id, "Usage: /set_api_exhausted_message <your message>\nExample: /set_api_exhausted_message Sorry, the AI is taking a break. Try again!")
                    return 'OK'
                message_text = ' '.join(args)
                set_user_api_exhausted_message(chat_id, message_text)
                send_message(chat_id, f"API exhausted message updated! When the API is exhausted, I'll respond with: {message_text}")

            elif command == '/set_timezone':
                start_timezone_setup(chat_id)
                return 'OK'

            elif command == '/start':
                handle_start_command(chat_id)
                return 'OK'

            elif command is None:
                # Check if user is in start setup mode and handle accordingly
                from start_handler import process_start_message
                if process_start_message(chat_id, text):
                    return 'OK'
                
                # Not a command, treat as natural language message to AI
                ai_response = get_chat_response(chat_id, text, mode="respond_user")
                logger.debug(f"Sending AI response to user {chat_id}")
                result = send_message(chat_id, ai_response)
                logger.info(f"Message sent to user {chat_id}, result: {result}")
                # Update last AI message timestamp
                doc_ref = db.collection('users').document(str(chat_id))
                doc_ref.set({'last_ai_message': firestore.SERVER_TIMESTAMP}, merge=True)

            else:
                send_message(chat_id, "Unknown command. Use /remind, /list, /delete, /system_prompt, /set_api_exhausted_message, or /set_timezone.")

        elif 'callback_query' in update:
            callback_query = update['callback_query']
            chat_id = callback_query['message']['chat']['id']
            callback_data = callback_query['data']
            callback_query_id = callback_query['id']
            answer_callback_query(callback_query_id)
            
            # Handle different types of callbacks
            if callback_data.startswith('start_'):
                process_start_callback(chat_id, callback_data)
            else:
                process_setup_callback(chat_id, callback_data)
            return 'OK'

        return 'OK'

    except Exception as e:
        logger.error(f"Error in telegram_webhook: {e}")
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
            message_text = f"Reminder: {data['text']}"
            send_message(chat_id, message_text)
            # system type not handled here

            mark_reminder_sent(doc.reference)
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
                    message_text = generate_agent_reachout_message({'text': 'general check-in'}, chat_id, reachout_type='agent_reachout')
                    send_message(chat_id, message_text)
                    # Update last AI message timestamp
                    user_doc.reference.set({'last_ai_message': firestore.SERVER_TIMESTAMP}, merge=True)
                    reachout_count += 1

            logger.info(f"System reachout: checked users, sent {reachout_count} messages")

        return f"Processed {processed_count} reminders, {reachout_count if 'reachout_count' in locals() else 0} system reachouts"

    except Exception as e:
        logger.error(f"Error in scheduler_tick: {e}")
        return 'Error', 500
