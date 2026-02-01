#!/bin/bash

# Automated deployment script for Telegram Coach Bot
# This script handles the complete setup from GCP project to live bot

# Error handler function to keep terminal open
handle_error() {
    echo ""
    echo "🛑 Script stopped due to error: $1"
    echo ""
    echo "Press Enter to exit..."
    read -r
    exit 1
}

echo "🤖 Telegram Coach Bot - Automated Deployment"
echo "=============================================="

# Check prerequisites
echo "📋 Checking prerequisites..."
if ! command -v terraform &> /dev/null; then
    echo "❌ Terraform is not installed. Please install it first."
    handle_error "Terraform not installed"
fi

if ! command -v gcloud &> /dev/null; then
    echo "❌ gcloud CLI is not installed. Please install it first."
    handle_error "gcloud CLI not installed"
fi

# Check if authenticated
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | head -n 1 > /dev/null; then
    echo "❌ Not authenticated with gcloud. Please run 'gcloud auth login' first."
    handle_error "Not authenticated with gcloud"
fi

echo "✅ Prerequisites check passed"

# Get user inputs
echo ""
echo "🔧 Configuration"
echo "----------------"

read -p "Enter your GCP Project ID: " PROJECT_ID
if [ -z "$PROJECT_ID" ]; then
    echo "❌ Project ID is required"
    handle_error "Project ID is required"
fi

read -p "Enter your Telegram Bot Token (from @BotFather): " BOT_TOKEN
if [ -z "$BOT_TOKEN" ]; then
    echo "❌ Bot token is required"
    handle_error "Bot token is required"
fi

read -p "Enter your Gemini API Key (from Google AI Studio): " GEMINI_KEY
if [ -z "$GEMINI_KEY" ]; then
    echo "❌ Gemini API key is required"
    handle_error "Gemini API key is required"
fi

read -p "Enter whitelist user IDs (comma-separated, leave empty for public access, numbers only(!) like 1016669999, NOT @UseName): " WHITELIST_IDS

# Create terraform.tfvars
echo ""
echo "📝 Creating terraform configuration..."
cat > terraform/terraform.tfvars << EOF
project_id         = "$PROJECT_ID"
telegram_bot_token = "$BOT_TOKEN"
gemini_api_key     = "$GEMINI_KEY"
whitelist_user_ids = "$WHITELIST_IDS"
EOF

echo "✅ Configuration created"

# Navigate to terraform directory
cd terraform || { echo "❌ Failed to navigate to terraform directory"; handle_error "Failed to navigate to terraform directory"; }

# Select or create workspace for the project
echo ""
echo "🔄 Selecting Terraform workspace..."
if terraform workspace select $PROJECT_ID 2>/dev/null; then
    echo "✅ Switched to existing workspace '$PROJECT_ID'"
else
    terraform workspace new $PROJECT_ID || { echo "❌ Failed to create new workspace '$PROJECT_ID'"; handle_error "Failed to create new workspace"; }
    echo "✅ Created new workspace '$PROJECT_ID'"
fi

# Initialize Terraform
echo ""
echo "🚀 Initializing Terraform..."
terraform init -upgrade || { echo "❌ Terraform initialization failed"; handle_error "Terraform initialization failed"; }

# Apply infrastructure
echo ""
echo "🏗️  Deploying infrastructure..."
terraform apply -auto-approve || { echo "❌ Terraform apply failed"; handle_error "Terraform apply failed"; }

# Get function URL and webhook secret
echo ""
echo "🔗 Getting deployment details..."
FUNCTION_URL=$(terraform output -raw telegram_webhook_function_url 2>/dev/null)
WEBHOOK_SECRET=$(terraform output -raw webhook_secret 2>/dev/null)

if [ -z "$FUNCTION_URL" ] || [ -z "$WEBHOOK_SECRET" ]; then
    echo "❌ Failed to get function URL or webhook secret"
    handle_error "Failed to get function URL or webhook secret"
fi

echo "✅ Function URL: $FUNCTION_URL"
echo "✅ Webhook Secret: [HIDDEN]"

# Create Firestore composite index for chat history
echo ""
echo "📊 Creating Firestore index for chat history..."
echo "   Note: Index creation may take 5-10 minutes to complete"
if gcloud firestore indexes composite create \
  --collection-group=chat_history \
  --field-config field-path=chat_id,order=ascending \
  --field-config field-path=timestamp,order=descending \
  --project=$PROJECT_ID \
  --quiet; then
    echo "✅ Firestore index creation initiated"
else
    echo "⚠️  Index creation failed or already exists (this is usually OK)"
fi

# Create Firestore composite index for reminders
echo ""
echo "📊 Creating Firestore index for reminders..."
echo "   Note: Index creation may take 5-10 minutes to complete"
if gcloud firestore indexes composite create \
  --collection-group=reminders \
  --field-config field-path=active,order=ascending \
  --field-config field-path=next_run,order=ascending \
  --project=$PROJECT_ID \
  --quiet; then
    echo "✅ Reminders Firestore index creation initiated"
else
    echo "⚠️  Reminders index creation failed or already exists (this is usually OK)"
fi

# Set Telegram webhook with authentication
echo ""
echo "📡 Setting Telegram webhook..."
WEBHOOK_URL="${FUNCTION_URL}?token=${WEBHOOK_SECRET}"
WEBHOOK_RESPONSE=$(curl -s -X POST "https://api.telegram.org/bot${BOT_TOKEN}/setWebhook" \
    -H "Content-Type: application/json" \
    -d "{\"url\": \"${WEBHOOK_URL}\"}" || { echo "❌ Failed to execute webhook curl command"; handle_error "Failed to execute webhook curl command"; })

# Check if webhook was set successfully
if echo "$WEBHOOK_RESPONSE" | grep -q '"ok":true'; then
    echo "✅ Webhook set successfully!"
else
    echo "❌ Failed to set webhook. Response: $WEBHOOK_RESPONSE"
    handle_error "Failed to set webhook"
fi

# Success message
echo ""
echo "🎉 Deployment Complete!"
echo "======================"
echo "Your Telegram Coach Bot is now live!"
echo "It will guide you through setup process once it receives /start command"
echo ""
echo "To destroy the infrastructure later: cd terraform && terraform workspace select $PROJECT_ID && terraform destroy"
