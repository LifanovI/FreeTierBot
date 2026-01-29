import os
import requests
from google.cloud import firestore
import datetime
import pytz
from dateutil import parser as date_parser
import json
import logging
from reminders import get_reminders, delete_reminder
from utils import format_repeat_days

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

def get_user_api_exhausted_message(chat_id):
    """Get user's api_exhausted_message from Firestore."""
    doc_ref = db.collection('users').document(str(chat_id))
    doc = doc_ref.get()
    if doc.exists:
        return doc.to_dict().get('api_exhausted_message', '')
    return ''

def set_user_api_exhausted_message(chat_id, message):
    """Set user's api_exhausted_message in Firestore."""
    doc_ref = db.collection('users').document(str(chat_id))
    doc_ref.set({
        'api_exhausted_message': message,
        'updated_at': firestore.SERVER_TIMESTAMP
    }, merge=True)

def get_chat_history(chat_id, limit=10):
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

def create_reminder_from_ai(chat_id, next_run_str, text, repeat=None, reminder_id=None):
    """Create or update a reminder from AI function call. next_run_str is in user's local timezone."""
    from reminders import create_reminder  # Import here to avoid circular import

    # Get user timezone
    user_doc = db.collection('users').document(str(chat_id)).get()
    user_data = user_doc.to_dict() if user_doc.exists else {}
    user_tz_str = user_data.get('timezone', 'UTC')
    user_tz = pytz.timezone(user_tz_str)

    action = "Updating" if reminder_id else "Creating"
    print(f"DEBUG: {action} reminder - next_run: '{next_run_str}', text: '{text}', repeat: {repeat}, id: {reminder_id}")
    try:
        # Parse next_run_str as local time
        next_run_local = datetime.datetime.fromisoformat(next_run_str)
        if next_run_local.tzinfo is None:
            next_run_local = user_tz.localize(next_run_local)

        # Pass the local datetime directly to create_reminder
        # create_reminder will handle the timezone conversion internally
        result_id = create_reminder(chat_id, text, next_run_local, repeat, reminder_id)
        if result_id:
            action_done = "updated" if reminder_id else "created"
            repeat_info = format_repeat_days(repeat)
            if repeat_info:
                repeat_info = f". This is a repeated reminder for{repeat_info[1:]}"  # Remove leading space, add period
            print(f"DEBUG: Reminder {action_done} successfully: {result_id}")
            return f"Reminder {action_done}: {text} for {next_run_str} (local time){repeat_info}"
        else:
            return "Failed to update reminder: invalid ID or permission denied"
    except Exception as e:
        print(f"DEBUG: Reminder creation/update failed: {str(e)}")
        import traceback
        print(f"DEBUG: Traceback: {traceback.format_exc()}")
        return f"Failed to set reminder: {str(e)}"

def get_chat_response(chat_id, message, mode="respond_user"):
    """Get AI response using direct Gemini API calls with proper Function Calling recursion.
    mode defines the behavior of the function:
    "respond_user" - direct response to user
    "agent_reachout" - continue conversation based on internal agent prompt (e.g. to continue chat after delay)
    "generate_api_message" - generate a custom API exhausted message based on system prompt
    "generate_welcome_message" - generate a personalized welcome message in user's language
    """
    print(f"DEBUG: calling Gemini with {message} in mode: {mode}")
    api_key = os.environ.get('GEMINI_API_KEY')
    if not api_key:
        logging.error("GEMINI_API_KEY environment variable not set")
        return "Sorry, my AI brain isn't configured properly right now."

    # --- 1. Setup Initial Context ---
    # Get user timezone
    user_doc = db.collection('users').document(str(chat_id)).get()
    user_data = user_doc.to_dict() if user_doc.exists else {}
    user_tz_str = user_data.get('timezone', 'UTC')
    user_tz = pytz.timezone(user_tz_str)

    # Get current time in user's timezone
    now_utc = datetime.datetime.utcnow().replace(tzinfo=pytz.UTC)
    now_local = now_utc.astimezone(user_tz)
    today = now_local.strftime('%Y-%m-%d')
    current_time = now_local.strftime('%H:%M')
    system_prompt_text = f"You are a telegram reminder chat bot designed to serve user in a role they define. Today is {today} an current time is {current_time}. User defined role: "
    system_prompt_text += get_user_system_prompt(chat_id)
    
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
    elif mode == "agent_reachout":
                # Even for reachout, we treat the 'purpose' as a user-like request 
                # so the model generates the response
                contents.append({
                    'role': 'user',
                    'parts': [{'text': f"(Internal System Trigger): Continue the conversation naturally and convey the following: {message}"}]
                })
    elif mode == "generate_api_message":
        # For API message generation, use the prompt directly without conversation history
        # This ensures the message is generated based purely on the system prompt
        contents = [{
            'role': 'user',
            'parts': [{'text': message}]
        }]

    # --- 2. Define Tools (CONDITIONALLY) ---
    # We ONLY define tools if we are responding to a user. 
    tools = None
    
    if mode == "respond_user": 
        tools = [{
            'functionDeclarations': [
                {
                    "name": "set_reminder",
                    "description": "Set a reminder for the user. Generate the exact Firebase-compatible format.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "next_run": {"type": "string", "description": "ISO datetime string in user's local timezone (e.g., 2026-01-15T09:00:00)"},
                            "text": {"type": "string", "description": "Reminder message text"},
                            "repeat": {"type": "array", "items": {"type": "integer"}, "description": "Make reminder repeatable for the following days: 1=Mon, 2=Tue, 3=Wed, 4=Thu, 5=Fri, 6=Sat, 7=Sun"},
                            "id": {"type": "string", "description": "Optional reminder ID to update existing reminder"},
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
    max_turns = 5
    current_turn = 0

    while current_turn < max_turns:
        current_turn += 1
        
        payload = {
            'contents': contents,
            'system_instruction': {'parts': {'text': system_prompt_text}},
        }
        
        # Only add tools to payload if they are defined
        if tools:
            payload['tools'] = tools

        try:
            print(f"DEBUG: Turn {current_turn} - Sending request to Gemini (Mode: {mode})...")
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            data = response.json()

            if 'candidates' not in data or not data['candidates']:
                return "Sorry, I didn't get a response."

            candidate = data['candidates'][0]
            content = candidate.get('content', {})
            parts = content.get('parts', [])

            function_calls = [part['functionCall'] for part in parts if 'functionCall' in part]

            if not function_calls:
                # -- FINAL TEXT RESPONSE --
                text_response = "".join([p.get('text', '') for p in parts])
                
                if mode == "respond_user":
                    add_chat_message(chat_id, "user", message)
                add_chat_message(chat_id, "assistant", text_response)
                
                return text_response

            else:
                # -- HANDLE FUNCTION CALL (Only happens if tools were provided) --
                contents.append(content)

                for func_call in function_calls:
                    func_name = func_call['name']
                    func_args = func_call.get('args', {})
                    print(f"DEBUG: Executing function: {func_name}")

                    api_response = {}

                    if func_name == 'set_reminder':
                        res_str = create_reminder_from_ai(
                            chat_id,
                            func_args.get('next_run', ''),
                            func_args.get('text', ''),
                            func_args.get('repeat'),
                            func_args.get('id'),
                        )
                        api_response = {"result": res_str}

                    elif func_name == 'check_reminders':
                        reminders = get_reminders(chat_id)
                        if not reminders:
                            api_response = {"result": "No active reminders found."}
                        else:
                            rem_list = []
                            for r in reminders:
                                dt_utc = datetime.datetime.fromisoformat(r['next_run'])
                                dt_local = dt_utc.astimezone(user_tz)
                                formatted_time = dt_local.strftime('%Y-%m-%d %H:%M')
                                repeat_info = format_repeat_days(r.get('repeat', []))
                                rem_list.append({"id": r['id'], "text": r['text'], "time": f"{formatted_time} {repeat_info}"})
                            api_response = {"reminders": rem_list, "instruction": "Do not disclose reminder IDs to the user."}

                    elif func_name == 'delete_reminders':
                        ids = func_args.get('ids', [])
                        deleted_count = 0
                        for rid in ids:
                            if delete_reminder(chat_id, rid):
                                deleted_count += 1
                        api_response = {"result": f"Deleted {deleted_count} reminders."}

                    contents.append({
                        "role": "function",
                        "parts": [{
                            "functionResponse": {
                                "name": func_name,
                                "response": api_response
                            }
                        }]
                    })
                
                continue

        except Exception as e:
            print(f"Error in Gemini Loop: {e}")
            if isinstance(e, requests.HTTPError) and e.response.status_code == 429:
                custom_message = get_user_api_exhausted_message(chat_id)
                if custom_message:
                    return custom_message
                else:
                    return "API is currently exhausted, please try again later."
            return f"Error: {str(e)}"

    return "Sorry, the conversation got stuck in a loop."

def generate_api_exhausted_message(chat_id, system_prompt):
    """Generate an appropriate API exhausted message using LLM based on the system prompt."""
    if not system_prompt:
        return "Sorry, the AI is taking a break. Try again later."
    
    # Create a prompt for the LLM to generate an appropriate unavailable message
    prompt = f"""Based on this AI role description: "{system_prompt}"
    
    Generate a friendly, natural message that this AI would say when it's temporarily unavailable or taking a break. 
    The message should:
    - Be consistent with the AI's role and personality
    - Sound natural and conversational
    - Indicate that the AI is temporarily unavailable
    - Suggest trying again later
    
    Keep the message under 5 sentences and make it sound helpful and professional."""
    
    # Use the existing get_chat_response function with a special mode
    return get_chat_response(chat_id, prompt, mode="generate_api_message")

def generate_welcome_message(chat_id, system_prompt):
    """Generate a personalized welcome message in the user's preferred language based on system prompt."""
    if not system_prompt:
        return "Welcome! I'm ready to help you. You can now set up your first reminder using /remind command."
    
    # Create a prompt for the LLM to generate a welcome message in the appropriate language
    prompt = f"""Based on this AI role description: "{system_prompt}"
    
    Generate a warm, friendly welcome message that:
    - Greets the user in the appropriate language (detect from the role description)
    - Confirms that setup is complete and the bot is ready to operate
    - Introduces the bot's main capabilities
    - Invites the user to set up their first reminder
    - Provides a simple example relevant to the bot's role
    - Sounds natural
    
    The message should be 2-3 sentences and match the tone of the AI's role."""
    
    # Use the existing get_chat_response function with a special mode
    return get_chat_response(chat_id, prompt, mode="generate_welcome_message")

def generate_agent_reachout_message(reminder_data, chat_id, reachout_type="agent_reachout"):
    """Generate a personalized message for agent reachout using AI."""
    purpose = reminder_data.get('text', '').replace('AI check-in: ', '')
    ai_prompt = f"Generate a friendly, natural check-in message about: {purpose}"
    doc_ref = db.collection('users').document(str(chat_id))
    doc_ref.set({'last_ai_message': firestore.SERVER_TIMESTAMP}, merge=True)
    return get_chat_response(chat_id, ai_prompt, mode=reachout_type)
