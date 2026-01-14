import os
import requests
from google.cloud import firestore
import datetime
import pytz
from dateutil import parser as date_parser
import json
import logging
from reminders import get_reminders, delete_reminder

db = firestore.Client()

def get_user_system_prompt(chat_id):
    """Get user's system prompt from Firestore."""
    doc_ref = db.collection('users').document(str(chat_id))
    doc = doc_ref.get()
    if doc.exists:
        return doc.to_dict().get('system_prompt', '')
    return ''

def set_user_system_prompt(chat_id, prompt):
    """Set user's system prompt in Firestore."""
    doc_ref = db.collection('users').document(str(chat_id))
    doc_ref.set({
        'system_prompt': prompt,
        'updated_at': firestore.SERVER_TIMESTAMP
    }, merge=True)

def get_chat_history(chat_id, limit=3):
    """Get recent chat history for user."""
    docs = db.collection('chat_history').where('chat_id', '==', chat_id).order_by('timestamp', direction=firestore.Query.DESCENDING).limit(limit).stream()
    messages = []
    for doc in reversed(list(docs)):
        data = doc.to_dict()
        messages.append({
            'role': data['role'],
            'content': data['content']
        })
    return messages

def add_chat_message(chat_id, role, content):
    """Add a message to chat history."""
    doc_ref = db.collection('chat_history').document()
    doc_ref.set({
        'chat_id': chat_id,
        'role': role,
        'content': content,
        'timestamp': firestore.SERVER_TIMESTAMP
    })

def create_reminder_from_ai(chat_id, next_run_str, text, interval=None, reminder_type='external', followup=10):
    """Create a reminder from AI function call with pre-formatted Firebase data."""
    from reminders import create_reminder  # Import here to avoid circular import
    if followup == -1:
        followup = None
    print(f"DEBUG: Creating reminder - next_run: '{next_run_str}', text: '{text}', interval: {interval}")
    try:
        # next_run_str is already in ISO format, pass it directly
        reminder_id = create_reminder(chat_id, text, next_run_str, interval, reminder_type, followup)
        print(f"DEBUG: Reminder created successfully: {reminder_id}")
        return f"Reminder created: {text} for {next_run_str} {interval}"
    except Exception as e:
        print(f"DEBUG: Reminder creation failed: {str(e)}")
        import traceback
        print(f"DEBUG: Traceback: {traceback.format_exc()}")
        return f"Failed to create reminder: {str(e)}"

def get_chat_response(chat_id, message, mode="respond_user"):
    """Get AI response using direct Gemini API calls with proper Function Calling recursion.
    mode defines the behavior of the function:
    "respond_user" - direct response to user
    "agent_reachout" - continue conversation based on internal agent prompt (e.g. to continue chat after delay)
    "agent_reminder" - agent generates message for scheduled reminder"""
    api_key = os.environ.get('GEMINI_API_KEY')
    if not api_key:
        logging.error("GEMINI_API_KEY environment variable not set")
        return "Sorry, my AI brain isn't configured properly right now."

    # --- 1. Setup Initial Context ---
    today = datetime.datetime.utcnow().strftime('%Y-%m-%d')
    current_time = datetime.datetime.utcnow().strftime('%H:%M UTC')
    system_prompt_text = f"You are a telegram reminder chat bot designed to serve user in a role they define. Today is {today} an current time is {current_time}. User defined role: "
    system_prompt_text += get_user_system_prompt(chat_id)
    if mode == "agent_reminder":
        system_prompt_text += f"!IMPORTANT! You are reaching out regarding a reminder focus on it and not on the chat history! The reminder you must bring is: {message}"
    
    # Load history
    history = get_chat_history(chat_id)
    contents = []
    for msg in history:
        role = 'user' if msg['role'] == 'user' else 'model'
        contents.append({
            'role': role,
            'parts': [{'text': msg['content']}]
        })

    # Add the trigger message
    if mode == "respond_user":
        contents.append({
            'role': 'user',
            'parts': [{'text': message}]
        })
    elif mode == "agent_reachout" or mode == "agent_reminder":
        contents.append({
            'role': 'model',
            'parts': [{'text': message}]
        })

    # --- 2. Define Tools ---
    tools = [{
        'functionDeclarations': [
            {
                "name": "set_reminder",
                "description": "Set a reminder for the user. Generate the exact Firebase-compatible format.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "next_run": {"type": "string", "description": "ISO datetime string in UTC (e.g., 2026-01-15T09:00:00)"},
                        "text": {"type": "string", "description": "Reminder message text"},
                        "interval": {"type": "string", "enum": ["daily", "weekly", "monthly"], "description": "Optional recurrence"},
                        "followup": {"type": "integer", "description": "Minutes after reminder to follow up (default 10), or -1 for none"}
                    },
                    "required": ["next_run", "text"]
                }
            },
            {
                "name": "check_reminders",
                "description": "Retrieve and display all current reminders for the user",
                "parameters": {"type": "object", "properties": {}}
            },
            {
                "name": "delete_reminders",
                "description": "Delete reminders by ID",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "ids": {"type": "array", "items": {"type": "string"}, "description": "IDs to delete"}
                    },
                    "required": ["ids"]
                }
            }
        ]
    }]

    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"
    headers = {
        'x-goog-api-key': api_key,
        'Content-Type': 'application/json'
    }

    # --- 3. Main Interaction Loop ---
    # We loop to handle potential multiple function calls in a row (e.g., check -> delete -> respond)
    max_turns = 5
    current_turn = 0

    while current_turn < max_turns:
        current_turn += 1
        
        payload = {
            'contents': contents,
            'system_instruction': {'parts': {'text': system_prompt_text}},
            'tools': tools
        }

        try:
            print(f"DEBUG: Turn {current_turn} - Sending request to Gemini...")
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            data = response.json()

            if 'candidates' not in data or not data['candidates']:
                return "Sorry, I didn't get a response."

            candidate = data['candidates'][0]
            content = candidate.get('content', {})
            parts = content.get('parts', [])

            # Check if we got a pure text response or a function call
            function_calls = [part['functionCall'] for part in parts if 'functionCall' in part]

            if not function_calls:
                # -- FINAL TEXT RESPONSE --
                text_response = "".join([p.get('text', '') for p in parts])
                
                # Save to DB and return
                if mode == "respond_user":
                    add_chat_message(chat_id, "user", message) # Only save user msg on first valid completion
                add_chat_message(chat_id, "assistant", text_response)
                
                return text_response

            else:
                # -- HANDLE FUNCTION CALL --
                # 1. Add the Assistant's "Function Call" message to history so Gemini knows it asked for it
                contents.append(content)

                # 2. Process each function call
                for func_call in function_calls:
                    func_name = func_call['name']
                    func_args = func_call.get('args', {})
                    print(f"DEBUG: Executing function: {func_name}")

                    api_response = {}

                    # Execute Python Logic
                    if func_name == 'set_reminder':
                        followup = func_args.get('followup', 10)
                        res_str = create_reminder_from_ai(
                            chat_id,
                            func_args.get('next_run', ''),
                            func_args.get('text', ''),
                            func_args.get('interval'),
                            'internal',
                            followup
                        )
                        api_response = {"result": res_str}

                    elif func_name == 'check_reminders':
                        reminders = get_reminders(chat_id)
                        if not reminders:
                            api_response = {"result": "No active reminders found."}
                        else:
                            # Send simplified list back to AI
                            rem_list = [{"id": r['id'], "text": r['text'], "time": r['next_run']} for r in reminders]
                            api_response = {"result": rem_list}

                    elif func_name == 'delete_reminders':
                        ids = func_args.get('ids', [])
                        deleted_count = 0
                        for rid in ids:
                            if delete_reminder(chat_id, rid):
                                deleted_count += 1
                        api_response = {"result": f"Deleted {deleted_count} reminders."}

                    # 3. Append the Function Response to history
                    # Gemini REST API expects a specific 'functionResponse' structure
                    contents.append({
                        "role": "function",
                        "parts": [{
                            "functionResponse": {
                                "name": func_name,
                                "response": api_response
                            }
                        }]
                    })
                
                # Loop continues immediately to send the result back to Gemini
                continue

        except Exception as e:
            print(f"Error in Gemini Loop: {e}")
            return f"Error: {str(e)}"

    return "Sorry, the conversation got stuck in a loop."
def generate_agent_reachout_message(reminder_data, chat_id, reachout_type="agent_reachout"):
    """Generate a personalized message for agent reachout using AI."""
    purpose = reminder_data.get('text', '').replace('AI check-in: ', '')
    ai_prompt = f"Generate a friendly, natural check-in message about: {purpose}"
    doc_ref = db.collection('users').document(str(chat_id))
    doc_ref.set({'last_ai_message': firestore.SERVER_TIMESTAMP}, merge=True)
    return get_chat_response(chat_id, ai_prompt, mode=reachout_type)
