import pytz
from telegram import send_message
from google.cloud import firestore

db = firestore.Client()


def get_timezone_regions():
    regions = set()
    for tz in pytz.common_timezones:
        region = tz.split("/")[0]
        regions.add(region)
    return sorted(list(regions))


def get_timezones_for_region(region):
    if region == "UTC":
        return ["UTC"]
    return sorted([tz for tz in pytz.common_timezones if tz.startswith(region + "/")])


def create_inline_keyboard(options, callback_prefix):
    keyboard = []
    for i in range(0, len(options), 3):
        row = []
        for option in options[i : i + 3]:
            row.append(
                {
                    "text": option,
                    "callback_data": f"{callback_prefix}:{option}",
                }
            )
        keyboard.append(row)
    return {"inline_keyboard": keyboard}


def create_region_keyboard():
    regions = get_timezone_regions()
    return create_inline_keyboard(regions, "tz_region")


def create_timezone_keyboard(region):
    timezones = get_timezones_for_region(region)
    return create_inline_keyboard(timezones, "tz_select")


TIMEZONE_SETUP_FLOW = {
    "start": {
        "message": "🌍 Select your region:",
        "keyboard_func": lambda: create_region_keyboard(),
        "next_step": "region_selected",
    },
    "region_selected": {
        "handler": "send_timezone_options",
        "next_step": "timezone_selected",
    },
    "timezone_selected": {
        "handler": "save_timezone",
    },
}


def get_user_setup_state(chat_id):
    doc = db.collection("users").document(str(chat_id)).get()
    if doc.exists:
        data = doc.to_dict()
        return data.get("setup_state", {})
    return {}


def set_user_setup_state(chat_id, state):
    doc_ref = db.collection("users").document(str(chat_id))
    doc_ref.set({"setup_state": state}, merge=True)


def clear_user_setup_state(chat_id):
    doc_ref = db.collection("users").document(str(chat_id))
    doc_ref.update({"setup_state": firestore.DELETE_FIELD})


def process_setup_callback(chat_id, callback_data):
    state = get_user_setup_state(chat_id)
    flow = state.get("flow")

    if flow == "timezone":
        if callback_data.startswith("tz_region:"):
            region = callback_data.split(":", 1)[1]
            state["data"] = {"region": region}
            state["step"] = "region_selected"
            set_user_setup_state(chat_id, state)
            send_timezone_options(chat_id, region)
        elif callback_data.startswith("tz_select:"):
            timezone = callback_data.split(":", 1)[1]
            save_timezone(chat_id, timezone)


def send_timezone_options(chat_id, region):
    keyboard = create_timezone_keyboard(region)
    send_message(chat_id, f"🕐 Select your timezone in {region}:", reply_markup=keyboard)


def save_timezone(chat_id, timezone):
    doc_ref = db.collection("users").document(str(chat_id))
    doc_ref.set({"timezone": timezone}, merge=True)

    state = get_user_setup_state(chat_id)
    if state.get("flow") == "start" and state.get("step") == "awaiting_timezone":
        from start_handler import handle_timezone_setup_complete

        handle_timezone_setup_complete(chat_id)
    else:
        clear_user_setup_state(chat_id)
        send_message(chat_id, f"✅ Timezone set to {timezone}")


def start_timezone_setup(chat_id):
    state = {
        "flow": "timezone",
        "step": "start",
        "data": {},
    }
    set_user_setup_state(chat_id, state)
    step_config = TIMEZONE_SETUP_FLOW["start"]
    keyboard = step_config["keyboard_func"]()
    send_message(chat_id, step_config["message"], reply_markup=keyboard)

