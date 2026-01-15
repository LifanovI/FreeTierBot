from google.cloud import firestore
import datetime
import pytz
from dateutil import parser as date_parser
from dateutil.relativedelta import relativedelta

db = firestore.Client()

def create_reminder(chat_id, text, next_run, repeat=None, reminder_id=None):
    """Create a new reminder or update existing one in Firestore."""
    if reminder_id:
        doc_ref = db.collection('reminders').document(reminder_id)
        doc = doc_ref.get()
        if not doc.exists or doc.to_dict().get('chat_id') != chat_id:
            return None
        update_data = {
            'text': text,
            'next_run': next_run.isoformat() if isinstance(next_run, datetime.datetime) else next_run,
            'repeat': repeat
        }
        doc_ref.update(update_data)
        return reminder_id
    else:
        doc_ref = db.collection('reminders').document()
        data = {
            'chat_id': chat_id,
            'text': text,
            'next_run': next_run.isoformat() if isinstance(next_run, datetime.datetime) else next_run,
            'repeat': repeat,
            'created_at': firestore.SERVER_TIMESTAMP
        }
        doc_ref.set(data)
        return doc_ref.id

def get_reminders(chat_id):
    """Get all active reminders for a chat, optionally filtered by type."""
    query = db.collection('reminders').where('chat_id', '==', chat_id)
    docs = query.stream()
    return [{'id': doc.id, **doc.to_dict()} for doc in docs]

def delete_reminder(chat_id, reminder_id):
    """Delete a reminder."""
    doc_ref = db.collection('reminders').document(reminder_id)
    doc = doc_ref.get()
    if doc.exists and doc.to_dict()['chat_id'] == chat_id:
        doc_ref.delete()
        return True
    return False

def get_due_reminders():
    """Get all reminders that are due (next_run <= now)."""
    now = datetime.datetime.utcnow().replace(tzinfo=pytz.UTC)
    docs = db.collection('reminders').where('next_run', '<=', now.isoformat()).stream()
    return list(docs)

def get_next_weekday(last_run_dt, repeat_days):
    """
    Calculate the next occurrence based on repeat days (1=Monday, ..., 7=Sunday).
    last_run_dt: The datetime when the reminder was originally supposed to run.
    """
    if not repeat_days:
        return last_run_dt

    # Convert 1-7 (ISO) to 0-6 (Python)
    target_weekdays = sorted([(d - 1) for d in repeat_days])
    current_wd = last_run_dt.weekday()

    days_ahead = None
    # Look for the next day later this week
    for wd in target_weekdays:
        if wd > current_wd:
            days_ahead = wd - current_wd
            break
    
    # If no days left this week, take the first day of next week
    if days_ahead is None:
        days_ahead = (7 - current_wd) + target_weekdays[0]

    return last_run_dt + datetime.timedelta(days=days_ahead)

def mark_reminder_sent(reminder_ref):
    """Mark reminder as sent and schedule next run if recurring."""
    doc = reminder_ref.get()
    if not doc.exists:
        return
        
    data = doc.to_dict()
    repeat = data.get('repeat')
    
    # --- IMPORTANT: Re-add your follow-up logic here ---
    # (If you still want the AI check-ins we discussed earlier)

    if repeat and len(repeat) > 0:
        # Calculate next run based on the ORIGINAL scheduled time
        # to prevent "time drift" caused by execution delays.
        scheduled_time = date_parser.parse(data['next_run'])
        if scheduled_time.tzinfo is None:
            scheduled_time = scheduled_time.replace(tzinfo=pytz.UTC)
            
        next_run = get_next_weekday(scheduled_time, repeat)
        
        reminder_ref.update({
            'next_run': next_run.isoformat()
        })
    else:
        # One-time reminder
        reminder_ref.delete()
