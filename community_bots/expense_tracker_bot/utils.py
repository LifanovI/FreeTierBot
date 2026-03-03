from datetime import datetime, timedelta


def format_currency(amount: float, currency: str) -> str:
    """Format amount with currency code."""
    return f"{amount:.2f} {currency}"


def get_predefined_range(label: str, now: datetime):
    """Resolve a predefined time range label into (start, end) datetimes in the same timezone as now."""
    label = label.lower()
    today = now.date()

    if label == "today":
        start = datetime.combine(today, datetime.min.time(), tzinfo=now.tzinfo)
        end = now
    elif label == "yesterday":
        yest = today - timedelta(days=1)
        start = datetime.combine(yest, datetime.min.time(), tzinfo=now.tzinfo)
        end = datetime.combine(yest, datetime.max.time(), tzinfo=now.tzinfo)
    elif label == "last_3_days":
        start = now - timedelta(days=3)
        end = now
    elif label == "this_week":
        # Monday as start of week
        start = datetime.combine(today - timedelta(days=today.weekday()), datetime.min.time(), tzinfo=now.tzinfo)
        end = now
    elif label == "last_week":
        # Previous calendar week (Mon-Sun)
        end_of_last_week = datetime.combine(today - timedelta(days=today.weekday() + 1), datetime.max.time(), tzinfo=now.tzinfo)
        start_of_last_week = end_of_last_week - timedelta(days=6)
        start, end = start_of_last_week, end_of_last_week
    elif label == "this_month":
        start = datetime.combine(today.replace(day=1), datetime.min.time(), tzinfo=now.tzinfo)
        end = now
    elif label == "last_month":
        first_this_month = today.replace(day=1)
        last_month_end = first_this_month - timedelta(days=1)
        last_month_start = last_month_end.replace(day=1)
        start = datetime.combine(last_month_start, datetime.min.time(), tzinfo=now.tzinfo)
        end = datetime.combine(last_month_end, datetime.max.time(), tzinfo=now.tzinfo)
    else:
        # Fallback: last 7 days
        start = now - timedelta(days=7)
        end = now

    return start, end

