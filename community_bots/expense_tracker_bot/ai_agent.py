import os
import datetime
from typing import Any, Dict

import pytz
import requests
from google.cloud import firestore

from expenses import create_expense, get_expense_summary, list_expenses_in_range
from logging_config import logger
from utils import get_predefined_range

db = firestore.Client()


def get_user_timezone(chat_id: int):
    doc = db.collection("users").document(str(chat_id)).get()
    data = doc.to_dict() if doc.exists else {}
    tz_name = data.get("timezone", "UTC")
    return pytz.timezone(tz_name)


def get_user_currency(chat_id: int) -> str:
    doc = db.collection("users").document(str(chat_id)).get()
    data = doc.to_dict() if doc.exists else {}
    return data.get("currency", "EUR")


def get_chat_history(chat_id, limit=10):
    docs = (
        db.collection("chat_history")
        .where("chat_id", "==", chat_id)
        .order_by("timestamp", direction=firestore.Query.DESCENDING)
        .limit(limit)
        .stream()
    )
    messages = []
    for doc in reversed(list(docs)):
        data = doc.to_dict()
        messages.append({"role": data["role"], "content": data["content"]})
    return messages


def add_chat_message(chat_id, role, content):
    doc_ref = db.collection("chat_history").document()
    doc_ref.set(
        {
            "chat_id": chat_id,
            "role": role,
            "content": content,
            "timestamp": firestore.SERVER_TIMESTAMP,
        }
    )


def _resolve_time_range(chat_id: int, tr: Dict[str, Any]):
    user_tz = get_user_timezone(chat_id)
    now_local = datetime.datetime.utcnow().replace(tzinfo=pytz.UTC).astimezone(user_tz)

    if tr.get("type") == "predefined":
        start_local, end_local = get_predefined_range(tr.get("value", "last_7_days"), now_local)
    elif tr.get("type") == "custom":
        from dateutil import parser as date_parser

        start_local = date_parser.parse(tr.get("start"))
        end_local = date_parser.parse(tr.get("end"))
        if start_local.tzinfo is None:
            start_local = user_tz.localize(start_local)
        if end_local.tzinfo is None:
            end_local = user_tz.localize(end_local)
    else:
        start_local, end_local = get_predefined_range("last_7_days", now_local)

    return start_local.astimezone(pytz.UTC), end_local.astimezone(pytz.UTC)


def get_chat_response(chat_id, message):
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        logger.error("GEMINI_API_KEY environment variable not set")
        return "AI is not configured yet. Ask admin to set GEMINI_API_KEY."

    user_tz = get_user_timezone(chat_id)
    now_utc = datetime.datetime.utcnow().replace(tzinfo=pytz.UTC)
    now_local = now_utc.astimezone(user_tz)
    today = now_local.strftime("%Y-%m-%d")
    current_time = now_local.strftime("%H:%M")
    currency = get_user_currency(chat_id)

    system_prompt_text = (
        "You are an expense tracking assistant for a Telegram bot. "
        f"User's default currency is {currency}. Today is {today} and current local time is {current_time}. "
        "You must keep track of the user's expenses and answer questions about their spending. "
        "Use the provided tools to store and query expenses. "
        "Never make up stored data; always call tools when user refers to past expenses or summaries. "
        "When you receive results from get_expense_summary, you MUST always: "
        " (1) state the TOTAL amount for the requested period, "
        " (2) if by_category is present, list ALL categories and their totals, and "
        " (3) make it clear that these numbers are based on the stored expenses. "
        "Do not ignore categories or expenses unless the user explicitly filtered them in their question."
    )

    history = get_chat_history(chat_id)
    contents = []
    for msg in history:
        role = "user" if msg["role"] == "user" else "model"
        contents.append({"role": role, "parts": [{"text": msg["content"]}]})

    contents.append({"role": "user", "parts": [{"text": message}]})

    tools = [
        {
            "functionDeclarations": [
                {
                    "name": "add_expense",
                    "description": "Add a single expense entry parsed from user's natural language.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "amount": {"type": "number", "description": "Expense amount"},
                            "currency": {
                                "type": "string",
                                "description": "Currency code like INR or USD. If missing, backend will use user default.",
                            },
                            "category": {
                                "type": "string",
                                "description": "High-level category such as food, transport, rent, shopping, entertainment, bills, other.",
                            },
                            "payment_method": {
                                "type": "string",
                                "description": "Payment method such as cash, card, upi, bank_transfer.",
                            },
                            "description": {
                                "type": "string",
                                "description": "Short human readable note for the expense.",
                            },
                            "spent_at": {
                                "type": "string",
                                "description": "ISO datetime in user's local timezone when money was actually spent (e.g. 2026-02-25T09:00:00).",
                            },
                            "tags": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Optional list of tags like office, reimbursable, personal.",
                            },
                            "ai_confidence": {
                                "type": "number",
                                "description": "Model's confidence 0-1 in this parse.",
                            },
                        },
                        "required": ["amount", "category", "description", "spent_at"],
                    },
                },
                {
                    "name": "get_expense_summary",
                    "description": "Get numeric summary of expenses for a time range and optional category.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "time_range": {
                                "type": "object",
                                "description": "Time range for summary.",
                                "properties": {
                                    "type": {
                                        "type": "string",
                                        "enum": ["predefined", "custom"],
                                    },
                                    "value": {
                                        "type": "string",
                                        "description": "Predefined label such as today, yesterday, last_3_days, this_week, last_week, this_month, last_month.",
                                    },
                                    "start": {
                                        "type": "string",
                                        "description": "Start date (YYYY-MM-DD or ISO) if type is custom.",
                                    },
                                    "end": {
                                        "type": "string",
                                        "description": "End date (YYYY-MM-DD or ISO) if type is custom.",
                                    },
                                },
                                "required": ["type"],
                            },
                            "category": {
                                "type": "string",
                                "description": "Optional category filter for the summary.",
                            },
                        },
                        "required": ["time_range"],
                    },
                },
                {
                    "name": "list_expenses",
                    "description": "List individual expenses for a time range, optionally filtered by category.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "time_range": {
                                "type": "object",
                                "description": "Time range for listing expenses.",
                                "properties": {
                                    "type": {
                                        "type": "string",
                                        "enum": ["predefined", "custom"],
                                    },
                                    "value": {
                                        "type": "string",
                                        "description": "Predefined label such as today, yesterday, last_3_days, this_week, last_week, this_month, last_month.",
                                    },
                                    "start": {
                                        "type": "string",
                                        "description": "Start date (YYYY-MM-DD or ISO) if type is custom.",
                                    },
                                    "end": {
                                        "type": "string",
                                        "description": "End date (YYYY-MM-DD or ISO) if type is custom.",
                                    },
                                },
                                "required": ["type"],
                            },
                            "category": {
                                "type": "string",
                                "description": "Optional category filter for the list.",
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Maximum number of expenses to return (default 20).",
                            },
                        },
                        "required": ["time_range"],
                    },
                },
            ]
        }
    ]

    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"
    headers = {"x-goog-api-key": api_key, "Content-Type": "application/json"}

    max_turns = 5
    current_turn = 0

    while current_turn < max_turns:
        current_turn += 1

        payload: Dict[str, Any] = {
            "contents": contents,
            "system_instruction": {"parts": {"text": system_prompt_text}},
            "tools": tools,
        }

        try:
            logger.debug(f"Turn {current_turn} - Sending request to Gemini for expense bot...")
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            data = response.json()

            if "candidates" not in data or not data["candidates"]:
                return "Sorry, I didn't get a response."

            candidate = data["candidates"][0]
            content = candidate.get("content", {})
            parts = content.get("parts", [])

            function_calls = [part["functionCall"] for part in parts if "functionCall" in part]

            if not function_calls:
                text_response = "".join([p.get("text", "") for p in parts])
                add_chat_message(chat_id, "user", message)
                add_chat_message(chat_id, "assistant", text_response)
                return text_response

            contents.append(content)

            for func_call in function_calls:
                func_name = func_call["name"]
                func_args = func_call.get("args", {})
                logger.debug(f"Executing function: {func_name}")

                api_response: Dict[str, Any] = {}

                if func_name == "add_expense":
                    try:
                        expense_data = dict(func_args)
                        expense_data["ai_raw_parse"] = dict(func_args)
                        expense_id = create_expense(chat_id, expense_data)
                        api_response = {
                            "result": f"Expense saved with id {expense_id}.",
                            "stored_amount": float(expense_data["amount"]),
                            "stored_category": expense_data.get("category"),
                            "stored_currency": expense_data.get("currency") or currency,
                        }
                    except Exception as e:
                        logger.error(f"Error in add_expense: {e}")
                        api_response = {
                            "error": f"Failed to save expense: {str(e)}",
                        }

                elif func_name == "get_expense_summary":
                    try:
                        time_range = func_args.get("time_range", {})
                        start_utc, end_utc = _resolve_time_range(chat_id, time_range)
                        summary = get_expense_summary(chat_id, start_utc, end_utc, group_by_category=True)
                        api_response = {
                            "total": summary["total"],
                            "currency": summary["currency"] or currency,
                            "by_category": summary["by_category"],
                        }
                    except Exception as e:
                        logger.error(f"Error in get_expense_summary: {e}")
                        api_response = {
                            "error": f"Failed to get summary: {str(e)}",
                        }

                elif func_name == "list_expenses":
                    try:
                        time_range = func_args.get("time_range", {})
                        category = func_args.get("category")
                        limit = int(func_args.get("limit", 20))
                        start_utc, end_utc = _resolve_time_range(chat_id, time_range)
                        rows = list_expenses_in_range(chat_id, start_utc, end_utc)
                        if category:
                            rows = [r for r in rows if r.get("category") == category]
                        rows = rows[:limit]
                        api_response = {
                            "expenses": [
                                {
                                    "amount": float(r.get("amount", 0)),
                                    "currency": r.get("currency") or currency,
                                    "category": r.get("category", "uncategorized"),
                                    "description": r.get("description", ""),
                                    "spent_at": r.get("spent_at").isoformat() if r.get("spent_at") else None,
                                }
                                for r in rows
                            ]
                        }
                    except Exception as e:
                        logger.error(f"Error in list_expenses: {e}")
                        api_response = {
                            "error": f"Failed to list expenses: {str(e)}",
                        }

                contents.append(
                    {
                        "role": "function",
                        "parts": [
                            {
                                "functionResponse": {
                                    "name": func_name,
                                    "response": api_response,
                                }
                            }
                        ],
                    }
                )

            continue

        except Exception as e:
            logger.error(f"Error in Gemini loop for expense bot: {e}")
            return f"Error: {str(e)}"

    return "Sorry, the conversation got stuck in a loop."

