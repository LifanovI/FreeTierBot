from telegram import send_message
from google.cloud import firestore

from ai_agent import get_user_currency
from setup_handlers import start_timezone_setup, get_user_setup_state, set_user_setup_state, clear_user_setup_state

db = firestore.Client()


def handle_start_command(chat_id: int):
    """Handle /start: intro + currency + timezone setup."""
    default_currency = get_user_currency(chat_id)
    msg = (
        "👋 Hi! I'm your Expense Tracker bot.\n\n"
        "You can tell me about your spending in natural language, for example:\n"
        "- 'I spent 500 on food yesterday via UPI'\n"
        "- 'Coffee 200 cash'\n\n"
        "I'll store it securely and you can ask things like:\n"
        "- 'How much did I spend this week?'\n"
        "- 'Show my expenses for last 3 days'\n\n"
        f"Your current currency is {default_currency} (default is EUR if not set).\n"
        "Please reply with your preferred 3-letter currency code now "
        "(for example: EUR, USD, INR, JPY, GBP). "
        "You can also change it later with /set_currency.\n\n"
        "After that, we'll set your timezone so I can understand dates like 'today' and 'last week'."
    )
    send_message(chat_id, msg)

    # Mark that we are waiting for initial currency selection
    state = {
        "flow": "currency",
        "step": "awaiting_currency",
        "data": {},
    }
    set_user_setup_state(chat_id, state)


def handle_timezone_setup_complete(chat_id: int):
    """Called when timezone setup finishes (from setup_handlers)."""
    # Just inform the user that setup is done for this simple bot.
    tz = _get_user_timezone(chat_id)
    currency = get_user_currency(chat_id)
    msg = (
        "✅ Setup complete!\n\n"
        f"Timezone: {tz}\n"
        f"Currency: {currency}\n\n"
        "You can start logging expenses or asking for analytics anytime."
    )
    send_message(chat_id, msg)
    clear_user_setup_state(chat_id)


def _get_user_timezone(chat_id: int) -> str:
    doc = db.collection("users").document(str(chat_id)).get()
    if doc.exists:
        data = doc.to_dict()
        return data.get("timezone", "UTC")
    return "UTC"


def process_start_message(chat_id: int, message_text: str) -> bool:
    """
    Handle messages during initial setup.
    Returns True if the message was consumed by setup logic.
    """
    state = get_user_setup_state(chat_id)
    flow = state.get("flow")
    step = state.get("step")

    if flow != "currency":
        return False

    if step == "awaiting_currency":
        code = message_text.strip().upper()
        # Allow free typing but require 3-letter code for safety
        if len(code) != 3:
            send_message(
                chat_id,
                "Currency code should be a 3-letter code like EUR, USD, INR, JPY, GBP.\n"
                "Please send just the code, for example: EUR",
            )
            return True

        # Save currency and move to timezone setup
        db.collection("users").document(str(chat_id)).set({"currency": code}, merge=True)
        send_message(chat_id, f"✅ Currency set to {code}. Now let's set your timezone.")

        # Reuse existing timezone flow from setup_handlers
        state = {
            "flow": "start",
            "step": "awaiting_timezone",
            "data": {"currency": code},
        }
        set_user_setup_state(chat_id, state)
        start_timezone_setup(chat_id)
        return True

    return False

