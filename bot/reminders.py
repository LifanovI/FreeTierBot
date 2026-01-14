from google.cloud import firestore
import datetime
import pytz
from dateutil import parser as date_parser
from dateutil.relativedelta import relativedelta

db = firestore.Client()

def create_reminder(chat_id, text, next_run, interval=None, reminder_type='external'):
    """Create a new reminder in Firestore."""
    doc_ref = db.collection('reminders').document()
    data = {
        'chat_id': chat_id,
        'text': text,
        'next_run': next_run.isoformat() if isinstance(next_run, datetime.datetime) else next_run,
        'interval': interval,
        'type': reminder_type,
        'active': True,
        'created_at': firestore.SERVER_TIMESTAMP
    }
    doc_ref.set(data)
    return doc_ref.id

def get_reminders(chat_id, reminder_type=None):
    """Get all active reminders for a chat, optionally filtered by type."""
    query = db.collection('reminders').where('chat_id', '==', chat_id).where('active', '==', True)
    if reminder_type:
        query = query.where('type', '==', reminder_type)
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
    docs = db.collection('reminders').where('active', '==', True).where('next_run', '<=', now.isoformat()).stream()
    return list(docs)

def mark_reminder_sent(reminder_ref, interval=None):
    """Mark reminder as sent and schedule next run if recurring."""
    doc = reminder_ref.get()
    data = doc.to_dict()

    if interval:
        # Calculate next run based on interval
        next_run = date_parser.parse(data['next_run'])
        if interval == 'daily':
            next_run += relativedelta(days=1)
        elif interval == 'weekly':
            next_run += relativedelta(weeks=1)
        elif interval == 'monthly':
            next_run += relativedelta(months=1)
        # Update next_run
        reminder_ref.update({'next_run': next_run.isoformat()})
    else:
        # One-time reminder, delete to save space
        reminder_ref.delete()
