#!/bin/bash

# Set Telegram webhook for the bot with authentication
# Usage: ./set_webhook.sh <function_url> <webhook_secret> <bot_token>

if [ $# -ne 3 ]; then
    echo "Usage: $0 <function_url> <webhook_secret> <bot_token>"
    exit 1
fi

FUNCTION_URL=$1
WEBHOOK_SECRET=$2
BOT_TOKEN=$3

# Append token to URL for authentication
WEBHOOK_URL="${FUNCTION_URL}?token=${WEBHOOK_SECRET}"

curl -X POST "https://api.telegram.org/bot${BOT_TOKEN}/setWebhook" \
     -H "Content-Type: application/json" \
     -d "{\"url\": \"${WEBHOOK_URL}\"}"

echo "Webhook set to ${WEBHOOK_URL}"
