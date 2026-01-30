from google.cloud import firestore
import datetime
import pytz
from dateutil import parser as date_parser

db = firestore.Client()

def create_reminder(chat_id, text, next_run, repeat=None, reminder_id=None):
    """Create a new reminder or update existing one in Firestore."""
    # Get user timezone
    user_doc = db.collection('users').document(str(chat_id)).get()
    user_data = user_doc.to_dict() if user_doc.exists else {}
    user_tz_str = user_data.get('timezone', 'UTC')
    user_tz = pytz.timezone(user_tz_str)
    
    # Parse and normalize the datetime
    if isinstance(next_run, str):
        next_run = date_parser.parse(next_run)
    
    if next_run.tzinfo is None:
        # If no timezone info, assume it's in user's local timezone
        next_run_local = user_tz.localize(next_run)
    else:
        # Convert to user's timezone
        next_run_local = next_run.astimezone(user_tz)
    
    if reminder_id:
        doc_ref = db.collection('reminders').document(reminder_id)
        doc = doc_ref.get()
        if not doc.exists() or doc.to_dict().get('chat_id') != chat_id:
            return None
        update_data = {
            'text': text,
            'next_run': next_run_local.isoformat(),
            'repeat': repeat,
            'timezone_hint': user_tz_str  # Store for reference
        }
        doc_ref.update(update_data)
        return reminder_id
    else:
        doc_ref = db.collection('reminders').document()
        data = {
            'chat_id': chat_id,
            'text': text,
            'next_run': next_run_local.isoformat(),
            'repeat': repeat,
            'timezone_hint': user_tz_str,  # Store for reference
            'created_at': firestore.SERVER_TIMESTAMP
        }
        doc_ref.set(data)
        return doc_ref.id

def get_reminders(chat_id):
    """Get all active reminders for a chat, optionally filtered by type."""
    query = db.collection('reminders').where('chat_id', '==', chat_id)
    docs = query.stream()
    
    # Get user's current timezone
    user_doc = db.collection('users').document(str(chat_id)).get()
    user_data = user_doc.to_dict() if user_doc.exists else {}
    user_tz_str = user_data.get('timezone', 'UTC')
    user_tz = pytz.timezone(user_tz_str)
    
    reminders = []
    for doc in docs:
        data = doc.to_dict()
        
        # Convert to user's current timezone for display
        if 'next_run' in data:
            next_run_str = data['next_run']
            next_run = date_parser.parse(next_run_str)
            
            # Convert to user's current timezone for display
            if next_run.tzinfo is None:
                next_run_local = user_tz.localize(next_run)
            else:
                next_run_local = next_run.astimezone(user_tz)
            
            # Format for display
            formatted_time = next_run_local.strftime('%Y-%m-%d %H:%M')
            
            # Add timezone info to data for display
            data['display_time'] = formatted_time
            data['timezone'] = user_tz_str
        
        reminders.append({'id': doc.id, **data})
    
    return reminders

def delete_reminder(chat_id, reminder_id):
    """Delete a reminder."""
    doc_ref = db.collection('reminders').document(reminder_id)
    doc = doc_ref.get()
    if doc.exists and doc.to_dict()['chat_id'] == chat_id:
        doc_ref.delete()
        return True
    return False

def get_due_reminders():
    """Get all reminders that are due (next_run <= now) with timezone awareness."""
    now_utc = datetime.datetime.utcnow().replace(tzinfo=pytz.UTC)
    due_reminders = []
    
    # Get all reminders
    all_reminders = db.collection('reminders').stream()
    
    for doc in all_reminders:
        data = doc.to_dict()
        chat_id = data['chat_id']
        
        # Get user's current timezone
        user_doc = db.collection('users').document(str(chat_id)).get()
        user_data = user_doc.to_dict() if user_doc.exists else {}
        user_tz_str = user_data.get('timezone', 'UTC')
        user_tz = pytz.timezone(user_tz_str)
        
        # Convert current UTC time to user's local time
        now_local = now_utc.astimezone(user_tz)
        
        # Check if this is a new format reminder (with next_run) or old format
        if 'next_run' in data:
            # New format: parse next_run and convert to UTC for comparison
            next_run_str = data['next_run']
            next_run = date_parser.parse(next_run_str)
            
            # Convert to UTC for comparison (next_run is stored in user's local timezone)
            if next_run.tzinfo is None:
                next_run_local = user_tz.localize(next_run)
            else:
                next_run_local = next_run.astimezone(user_tz)
            
            next_run_utc = next_run_local.astimezone(pytz.UTC)
            
            # Check if due
            if next_run_utc <= now_utc:
                due_reminders.append(doc)
        else:
            # Old format: use existing logic for backward compatibility
            next_run_str = data['next_run']
            next_run = date_parser.parse(next_run_str)
            if next_run.tzinfo is None:
                next_run = next_run.replace(tzinfo=pytz.UTC)
            
            if next_run <= now_utc:
                due_reminders.append(doc)
    
    return due_reminders

def get_next_weekday(last_run_dt, repeat_days):
    """
    Calculate the next occurrence based on repeat days (1=Monday, ..., 7=Sunday).
    last_run_dt: The datetime when the reminder was originally supposed to run.
    """
    if not repeat_days:
        return last_run_dt

    # Convert 1-7 (ISO) to 0-6 (Python)
    target_weekdays = sorted([(d - 1) for d in repeat_days])
    
    # Use current date as starting point if last_run_dt is in the past
    # This prevents setting future reminders in the past when reminders are triggered late
    today = datetime.datetime.now(last_run_dt.tzinfo).date()
    last_run_date = last_run_dt.date()
    
    if last_run_date < today:
        # Reminder is being triggered late, use today as starting point
        start_date = today
    else:
        # Reminder is on time or in future, use original date
        start_date = last_run_date
    
    current_wd = start_date.weekday()

    days_ahead = None
    # Look for the next day later this week
    for wd in target_weekdays:
        if wd > current_wd:
            days_ahead = wd - current_wd
            break
    
    # If no days left this week, take the first day of next week
    if days_ahead is None:
        days_ahead = (7 - current_wd) + target_weekdays[0]

    # Create new datetime with the calculated date but preserve time and timezone
    next_date = start_date + datetime.timedelta(days=days_ahead)
    return datetime.datetime.combine(
        next_date, 
        last_run_dt.time(),
        tzinfo=last_run_dt.tzinfo
    )

def mark_reminder_sent(reminder_ref):
    """Mark reminder as sent and schedule next run if recurring."""
    doc = reminder_ref.get()
    if not doc.exists:
        return
        
    data = doc.to_dict()
    chat_id = data['chat_id']
    repeat = data.get('repeat')
    
    # --- IMPORTANT: Re-add your follow-up logic here ---
    # (If you still want the AI check-ins we discussed earlier)

    if repeat and len(repeat) > 0:
        # Get user's current timezone
        user_doc = db.collection('users').document(str(chat_id)).get()
        user_data = user_doc.to_dict() if user_doc.exists else {}
        user_tz_str = user_data.get('timezone', 'UTC')
        user_tz = pytz.timezone(user_tz_str)
        
        # Parse the stored next_run
        next_run_str = data['next_run']
        next_run = date_parser.parse(next_run_str)
        
        # Convert to user's current timezone
        if next_run.tzinfo is None:
            next_run_local = user_tz.localize(next_run)
        else:
            next_run_local = next_run.astimezone(user_tz)
        
        # Calculate next occurrence in local timezone
        next_run_local = get_next_weekday(next_run_local, repeat)
        
        reminder_ref.update({
            'next_run': next_run_local.isoformat(),
            'repeat': repeat
        })
    else:
        # One-time reminder
        reminder_ref.delete()
