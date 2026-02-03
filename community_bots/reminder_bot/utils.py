def format_repeat_days(repeat_list):
    """Format repeat days list into readable string."""
    if not repeat_list: return ""
    days = ["Mondays", "Tuesdays", "Wednesdays", "Thursdays", "Fridays", "Saturdays", "Sundays"]
    day_names = [days[d-1] for d in repeat_list if 1 <= d <= 7]
    if not day_names: return ""
    if len(day_names) == 1:
        return f" (repeat {day_names[0]})"
    elif len(day_names) == 2:
        return f" (repeat {day_names[0]} and {day_names[1]})"
    else:
        return f" (repeat {', '.join(day_names[:-1])} and {day_names[-1]})"