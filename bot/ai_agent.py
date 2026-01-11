import os
import requests
from google.cloud import firestore
import datetime
import pytz
from dateutil import parser as date_parser
import json
import logging

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

def create_reminder_from_ai(chat_id, next_run_str, text, interval=None, reminder_type='reminder'):
    """Create a reminder from AI function call with pre-formatted Firebase data."""
    from reminders import create_reminder  # Import here to avoid circular import

    print(f"DEBUG: Creating reminder - next_run: '{next_run_str}', text: '{text}', interval: {interval}")
    try:
        # next_run_str is already in ISO format, pass it directly
        reminder_id = create_reminder(chat_id, text, next_run_str, interval, reminder_type)
        print(f"DEBUG: Reminder created successfully: {reminder_id}")
        return f"Reminder created: {reminder_id}"
    except Exception as e:
        print(f"DEBUG: Reminder creation failed: {str(e)}")
        import traceback
        print(f"DEBUG: Traceback: {traceback.format_exc()}")
        return f"Failed to create reminder: {str(e)}"

def get_chat_response(chat_id, user_message):
    """Get AI response using direct Gemini API calls."""
    api_key = os.environ.get('GEMINI_API_KEY')
    if not api_key:
        logging.error("GEMINI_API_KEY environment variable not set")
        return "Sorry, my AI brain isn't configured properly right now."

    print(f"DEBUG: Using Gemini API key (first 10 chars): {api_key[:10]}...")

    # Get system prompt and history
    system_prompt = get_user_system_prompt(chat_id)
    if not system_prompt:
        system_prompt = "You are a helpful personal coach and reminder assistant. When users ask you to set reminders or schedule activities, ALWAYS respond with a friendly conversational message AND use the appropriate function (set_reminder or set_agent_reachout) to actually create the reminder. For example: 'Got it! I'll remind you to workout on Monday at 9 AM.' (then call set_reminder function)"

    history = get_chat_history(chat_id)

    # Convert chat history to Gemini format
    contents = []
    for msg in history:
        if msg['role'] == 'user':
            contents.append({
                'role': 'user',
                'parts': [{'text': msg['content']}]
            })
        elif msg['role'] == 'assistant':
            contents.append({
                'role': 'model',
                'parts': [{'text': msg['content']}]
            })

    # Add current user message
    contents.append({
        'role': 'user',
        'parts': [{'text': user_message}]
    })

    # Define function declarations for Gemini
    function_declarations = [
        {
            'name': 'set_reminder',
            'description': 'Set a reminder for the user. Generate the exact Firebase-compatible format.',
            'parameters': {
                'type': 'object',
                'properties': {
                    'next_run': {
                        'type': 'string',
                        'description': 'ISO datetime string in UTC (e.g., "2026-01-15T09:00:00+00:00")'
                    },
                    'text': {
                        'type': 'string',
                        'description': 'Reminder message text'
                    },
                    'interval': {
                        'type': ['string', 'null'],
                        'enum': ['daily', 'weekly', 'monthly', None],
                        'description': 'Optional recurrence interval (null for one-time reminders)'
                    }
                },
                'required': ['next_run', 'text']
            }
        },
        {
            'name': 'set_agent_reachout',
            'description': 'Schedule an AI-initiated check-in with the user',
            'parameters': {
                'type': 'object',
                'properties': {
                    'next_run': {
                        'type': 'string',
                        'description': 'ISO datetime string in UTC for the reachout'
                    },
                    'purpose': {
                        'type': 'string',
                        'description': 'Purpose of the reachout (e.g., "check workout progress")'
                    }
                },
                'required': ['next_run', 'purpose']
            }
        }
    ]

    # Prepare Generative Language API request with header authentication
    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"

    headers = {
        'x-goog-api-key': api_key,
        'Content-Type': 'application/json'
    }

    payload = {
        'contents': contents,
        #'tools': [{
        #    'functionDeclarations': function_declarations
        #}],
    }

    print(f"DEBUG: Calling Gemini API with {len(contents)} messages")

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()

        data = response.json()
        print("DEBUG: Gemini API call successful")
        print(f"DEBUG: Raw API response: {json.dumps(data, indent=2)}")

        # Parse response
        if 'candidates' not in data or not data['candidates']:
            logging.error("No candidates in Gemini response")
            return "Sorry, I didn't get a proper response from my AI brain."

        candidate = data['candidates'][0]

        if 'content' not in candidate:
            logging.error("No content in Gemini response candidate")
            return "Sorry, I got an incomplete response from my AI brain."

        content = candidate['content']

        # Extract text response
        text_response = ""
        function_results = []

        if 'parts' in content:
            for part in content['parts']:
                if 'text' in part:
                    text_response += part['text']
                elif 'function_call' in part:
                    # Handle function call
                    func_call = part['function_call']
                    func_name = func_call['name']
                    func_args = func_call.get('args', {})

                    print(f"DEBUG: Processing function call: {func_name}")

                    if func_name == 'set_reminder':
                        result = create_reminder_from_ai(
                            chat_id,
                            func_args.get('next_run', ''),
                            func_args.get('text', ''),
                            func_args.get('interval')
                        )
                        function_results.append(result)
                    elif func_name == 'set_agent_reachout':
                        result = create_reminder_from_ai(
                            chat_id,
                            func_args.get('next_run', ''),
                            f"AI check-in: {func_args.get('purpose', '')}",
                            reminder_type='agent_reachout'
                        )
                        function_results.append(result)

        # Combine text response with function results
        final_response = text_response
        if function_results:
            final_response += "\n\n" + "\n".join(function_results)

        # Store messages
        add_chat_message(chat_id, "user", user_message)
        add_chat_message(chat_id, "assistant", final_response)
        print(f"Final response is: {final_response}")
        return final_response

    except requests.exceptions.RequestException as e:
        print(f"Gemini API request error: {str(e)}")
        error_msg = f"Sorry, I couldn't connect to my AI brain right now: {str(e)}"
        add_chat_message(chat_id, "user", user_message)
        add_chat_message(chat_id, "assistant", error_msg)
        return error_msg
    except json.JSONDecodeError as e:
        print(f"JSON decode error: {str(e)}")
        error_msg = "Sorry, I got a malformed response from my AI brain."
        add_chat_message(chat_id, "user", user_message)
        add_chat_message(chat_id, "assistant", error_msg)
        return error_msg
    except Exception as e:
        print(f"Unexpected error in Gemini API call: {str(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        error_msg = f"Sorry, I encountered an unexpected error: {str(e)}"
        add_chat_message(chat_id, "user", user_message)
        add_chat_message(chat_id, "assistant", error_msg)
        return error_msg

def generate_agent_reachout_message(reminder_data):
    """Generate a personalized message for agent reachout."""
    purpose = reminder_data.get('text', '').replace('AI check-in: ', '')

    # Simple template for now - could be enhanced with AI
    messages = [
        f"Hey! Just checking in on your {purpose}. How's it going?",
        f"Time for our regular check-in about {purpose}. What's new?",
        f"Hi there! I wanted to touch base about {purpose}. How are you doing?",
    ]

    # Could use AI here for more personalized messages
    return messages[0]  # For now, just return first template
