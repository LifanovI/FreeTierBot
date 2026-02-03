#!/bin/bash
# Firestore Index Deployment for Reminder Bot
PROJECT_ID=$1

echo "   🚀 Deploying Firestore indexes for Reminder Bot..."

# Index 1: Pending reminders for a user
echo "   📋 Index: Pending reminders for a user"
gcloud firestore indexes composite create \
    --collection-group="reminders" \
    --field-config field-path=user_id,order=ascending \
    --field-config field-path=status,order=ascending \
    --field-config field-path=remind_at,order=ascending \
    --project="$PROJECT_ID" \
    --quiet

# Index 2: All active reminders across all users (for the scheduler)
echo "   📋 Index: All active reminders across all users"
gcloud firestore indexes composite create \
    --collection-group="reminders" \
    --field-config field-path=status,order=ascending \
    --field-config field-path=remind_at,order=ascending \
    --project="$PROJECT_ID" \
    --quiet

echo "   ✅ Index deployment commands sent"
