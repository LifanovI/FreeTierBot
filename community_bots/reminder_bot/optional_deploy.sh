#!/bin/bash
# Firestore Index Deployment for Reminder Bot
PROJECT_ID=$1

echo "   🚀 Deploying Firestore indexes for Reminder Bot..."

# Index: Chat history by user (for AI context)
echo "   📋 Index: Chat history by user"
gcloud firestore indexes composite create \
    --collection-group="chat_history" \
    --field-config field-path=chat_id,order=ascending \
    --field-config field-path=timestamp,order=descending \
    --project="$PROJECT_ID" \
    --quiet

echo "   ✅ Index deployment commands sent"
