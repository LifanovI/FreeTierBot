#!/bin/bash

# Automated deployment script for Telegram Coach Bot
# This script handles the complete setup from GCP project to live bot

set -e  # Exit on any error

echo "🤖 Telegram Coach Bot - Automated Deployment"
echo "=============================================="

# Check prerequisites
echo "📋 Checking prerequisites..."
if ! command -v terraform &> /dev/null; then
    echo "❌ Terraform is not installed. Please install it first."
    exit 1
fi

if ! command -v gcloud &> /dev/null; then
    echo "❌ gcloud CLI is not installed. Please install it first."
    exit 1
fi

# Check if authenticated
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | head -n 1 > /dev/null; then
    echo "❌ Not authenticated with gcloud. Please run 'gcloud auth login' first."
    exit 1
fi

echo "✅ Prerequisites check passed"

# Get user inputs
echo ""
echo "🔧 Configuration"
echo "----------------"

read -p "Enter your GCP Project ID: " PROJECT_ID
if [ -z "$PROJECT_ID" ]; then
    echo "❌ Project ID is required"
    exit 1
fi

read -p "Enter your Telegram Bot Token (from @BotFather): " BOT_TOKEN
if [ -z "$BOT_TOKEN" ]; then
    echo "❌ Bot token is required"
    exit 1
fi

# Create terraform.tfvars
echo ""
echo "📝 Creating terraform configuration..."
cat > terraform/terraform.tfvars << EOF
project_id         = "$PROJECT_ID"
telegram_bot_token = "$BOT_TOKEN"
EOF

echo "✅ Configuration created"

# Navigate to terraform directory
cd terraform

# Initialize Terraform
echo ""
echo "🚀 Initializing Terraform..."
terraform init -upgrade

# Apply infrastructure
echo ""
echo "🏗️  Deploying infrastructure..."
terraform apply -auto-approve

# Get function URL and webhook secret
echo ""
echo "🔗 Getting deployment details..."
FUNCTION_URL=$(terraform output -raw telegram_webhook_function_url)
WEBHOOK_SECRET=$(terraform output -raw webhook_secret)

if [ -z "$FUNCTION_URL" ] || [ -z "$WEBHOOK_SECRET" ]; then
    echo "❌ Failed to get function URL or webhook secret"
    exit 1
fi

echo "✅ Function URL: $FUNCTION_URL"
echo "✅ Webhook Secret: [HIDDEN]"

# Set Telegram webhook with authentication
echo ""
echo "📡 Setting Telegram webhook..."
WEBHOOK_URL="${FUNCTION_URL}?token=${WEBHOOK_SECRET}"
WEBHOOK_RESPONSE=$(curl -s -X POST "https://api.telegram.org/bot${BOT_TOKEN}/setWebhook" \
    -H "Content-Type: application/json" \
    -d "{\"url\": \"${WEBHOOK_URL}\"}")

# Check if webhook was set successfully
if echo "$WEBHOOK_RESPONSE" | grep -q '"ok":true'; then
    echo "✅ Webhook set successfully!"
else
    echo "❌ Failed to set webhook. Response: $WEBHOOK_RESPONSE"
    exit 1
fi

# Success message
echo ""
echo "🎉 Deployment Complete!"
echo "======================"
echo "Your Telegram Coach Bot is now live!"
echo ""
echo "Bot Features:"
echo "• /remind <time> <message> [interval] - Set reminders"
echo "• /list - View active reminders"
echo "• /delete <number> - Delete reminders"
echo ""
echo "Time formats: 'tomorrow 3pm', '2026-01-10 09:00', 'in 2 hours'"
echo "Intervals: daily, weekly, monthly"
echo ""
echo "💡 Tip: The bot checks for due reminders every minute"
echo ""
echo "To destroy the infrastructure later: cd terraform && terraform destroy"
