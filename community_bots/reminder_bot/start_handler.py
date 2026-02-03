from telegram import send_message
from google.cloud import firestore
from ai_agent import set_user_system_prompt, set_user_api_exhausted_message, generate_api_exhausted_message, generate_welcome_message
from setup_handlers import start_timezone_setup

db = firestore.Client()

# Setup flow states
SETUP_STATES = {
    'start_mode': 'start_mode',
    'awaiting_system_prompt': 'awaiting_system_prompt', 
    'awaiting_timezone': 'awaiting_timezone'
}

def get_user_setup_state(chat_id):
    """Get current setup state for user."""
    doc = db.collection('users').document(str(chat_id)).get()
    if doc.exists:
        data = doc.to_dict()
        return data.get('setup_state', {})
    return {}

def set_user_setup_state(chat_id, state):
    """Set setup state for user."""
    doc_ref = db.collection('users').document(str(chat_id))
    doc_ref.set({'setup_state': state}, merge=True)

def clear_user_setup_state(chat_id):
    """Clear setup state for user."""
    doc_ref = db.collection('users').document(str(chat_id))
    doc_ref.update({'setup_state': firestore.DELETE_FIELD})

def handle_start_command(chat_id):
    """Handle /start command - initiate setup mode."""
    # Create inline keyboard for auto/manual options
    keyboard = {
        "inline_keyboard": [
            [
                {"text": "Automatic Setup", "callback_data": "start_auto"},
                {"text": "Manual Setup", "callback_data": "start_manual"}
            ]
        ]
    }
    
    message = ("Hey, I am your reminder bot up and running. Would you like to set me up automatically (recommended), or manually?\n\n"
               "to check all commands type /list_commands")
    send_message(chat_id, message, reply_markup=keyboard)
    
    # Set initial setup state
    state = {
        'flow': 'start',
        'step': SETUP_STATES['start_mode'],
        'data': {}
    }
    set_user_setup_state(chat_id, state)

def process_start_callback(chat_id, callback_data):
    """Process callback queries for start command setup."""
    state = get_user_setup_state(chat_id)
    flow = state.get('flow')
    
    if flow != 'start':
        return
    
    step = state.get('step')
    
    if callback_data == 'start_auto':
        # Automatic setup flow
        state['step'] = SETUP_STATES['awaiting_system_prompt']
        set_user_setup_state(chat_id, state)
        
        message = ("🤖 Automatic Setup\n\n"
                  "Please enter your system prompt (your AI role).\n\n"
                  "Examples:\n"
                  "- 'You are a fitness coach focused on strength training'\n"
                  "- 'You are a productivity assistant for software developers'\n"
                  "- 'You are a language tutor specializing in Spanish'")
        send_message(chat_id, message)
        
    elif callback_data == 'start_manual':
        # Manual setup flow
        clear_user_setup_state(chat_id)
        
        message = ("📋 Manual Setup\n\n"
                  "This is a reminder bot, optimized to be your personal coach. To set it up, please add system prompt, defining the role with command /system_prompt.\n\n" 
                  "If you are using free API key, it might be rate limited. In case, API key is exhausted - bot will return you some message. you can set this message with /set_api_exhausted_message\n\n"
                  "Finally, bot needs to understand your timezone. Please, set it with /set_timezone command\n\n"
                  "All the available commands are listed below\n"
                  "Check all available commands with /list_commands\n"
                  "Use these commands to configure your bot according to your needs.")
        send_message(chat_id, message)

def handle_system_prompt_input(chat_id, system_prompt):
    """Handle user input for system prompt during automatic setup."""
    state = get_user_setup_state(chat_id)
    flow = state.get('flow')
    step = state.get('step')
    
    if flow != 'start' or step != SETUP_STATES['awaiting_system_prompt']:
        return False
    
    # Set system prompt
    set_user_system_prompt(chat_id, system_prompt)
    
    # Generate API exhausted message automatically
    api_message = generate_api_exhausted_message(chat_id, system_prompt)
    set_user_api_exhausted_message(chat_id, api_message)
    
    # Update state to timezone setup
    state['step'] = SETUP_STATES['awaiting_timezone']
    state['data']['system_prompt'] = system_prompt
    set_user_setup_state(chat_id, state)
    
    # Start timezone setup
    message = (f"✅ System prompt set: {system_prompt}\n\n"
              f"✅ Response in case API is exhausted generated\n\n"
              "🌍 Now let's set your timezone...")
    send_message(chat_id, message)
    
    # Trigger existing timezone setup flow
    start_timezone_setup(chat_id)
    
    return True

def handle_timezone_setup_complete(chat_id):
    """Handle completion of timezone setup in automatic flow."""
    state = get_user_setup_state(chat_id)
    flow = state.get('flow')
    step = state.get('step')
    
    if flow != 'start' or step != SETUP_STATES['awaiting_timezone']:
        return
    
    system_prompt = state.get('data', {}).get('system_prompt', 'your role')
    
    # Generate personalized welcome message in user's language
    welcome_message = generate_welcome_message(chat_id, system_prompt)
    
    # Setup complete with personalized welcome!
    message = (f"🎉 Setup Complete!\n\n"
              f"Your AI role: {system_prompt}\n"
              f"Timezone: {get_user_timezone(chat_id)}\n\n"
              f"{welcome_message}")
    send_message(chat_id, message)
    
    # Clear setup state
    clear_user_setup_state(chat_id)

def get_user_timezone(chat_id):
    """Get user's timezone from Firestore."""
    doc = db.collection('users').document(str(chat_id)).get()
    if doc.exists:
        data = doc.to_dict()
        return data.get('timezone', 'UTC')
    return 'UTC'

def process_start_message(chat_id, message_text):
    """Process text messages during start setup flow."""
    state = get_user_setup_state(chat_id)
    flow = state.get('flow')
    step = state.get('step')
    
    if flow != 'start':
        return False
    
    if step == SETUP_STATES['awaiting_system_prompt']:
        return handle_system_prompt_input(chat_id, message_text)
    
    return False