from datetime import datetime
from typing import Dict, Any, List, Tuple

import pytz
from dateutil import parser as date_parser
from google.cloud import firestore

db = firestore.Client()


def get_user_settings(user_id: int) -> Tuple[pytz.BaseTzInfo, str]:
    doc = db.collection("users").document(str(user_id)).get()
    data = doc.to_dict() if doc.exists else {}
    tz_name = data.get("timezone", "UTC")
    currency = data.get("currency", "INR")
    return pytz.timezone(tz_name), currency


def _parse_spent_at(value, user_tz) -> datetime:
    if isinstance(value, datetime):
        dt = value
    else:
        dt = date_parser.parse(str(value))
    if dt.tzinfo is None:
        dt = user_tz.localize(dt)
    return dt.astimezone(pytz.UTC)


def create_expense(user_id: int, expense: Dict[str, Any]) -> str:
    user_tz, default_currency = get_user_settings(user_id)

    amount = float(expense["amount"])
    currency = expense.get("currency") or default_currency
    spent_at_raw = expense.get("spent_at") or datetime.utcnow()
    spent_at = _parse_spent_at(spent_at_raw, user_tz)

    doc_ref = db.collection("expenses").document()
    data = {
        "user_id": str(user_id),
        "amount": amount,
        "currency": currency,
        "category": expense.get("category", "uncategorized"),
        "payment_method": expense.get("payment_method", "unspecified"),
        "description": expense.get("description", ""),
        "tags": expense.get("tags", []),
        "spent_at": spent_at,
        "created_at": firestore.SERVER_TIMESTAMP,
        "ai_confidence": float(expense.get("ai_confidence", 1.0)),
        "ai_raw_parse": expense.get("ai_raw_parse"),
    }
    doc_ref.set(data)
    return doc_ref.id


def list_expenses(user_id: int, limit: int = 20) -> List[Dict[str, Any]]:
    q = (
        db.collection("expenses")
        .where("user_id", "==", str(user_id))
        .order_by("spent_at", direction=firestore.Query.DESCENDING)
        .limit(limit)
    )
    return [{"id": d.id, **d.to_dict()} for d in q.stream()]


def list_expenses_in_range(user_id: int, start_utc: datetime, end_utc: datetime):
    q = (
        db.collection("expenses")
        .where("user_id", "==", str(user_id))
        .where("spent_at", ">=", start_utc)
        .where("spent_at", "<=", end_utc)
        .order_by("spent_at", direction=firestore.Query.DESCENDING)
    )
    return [{"id": d.id, **d.to_dict()} for d in q.stream()]


def get_expense_summary(user_id: int, start_utc: datetime, end_utc: datetime, group_by_category: bool = True):
    q = (
        db.collection("expenses")
        .where("user_id", "==", str(user_id))
        .where("spent_at", ">=", start_utc)
        .where("spent_at", "<=", end_utc)
    )

    total = 0.0
    by_category: Dict[str, float] = {}
    currency = None

    for doc in q.stream():
        data = doc.to_dict()
        amt = float(data.get("amount", 0))
        cat = data.get("category", "uncategorized")
        curr = data.get("currency")
        total += amt
        if group_by_category:
            by_category[cat] = by_category.get(cat, 0.0) + amt
        currency = currency or curr

    return {
        "total": total,
        "currency": currency,
        "by_category": by_category if group_by_category else None,
    }

