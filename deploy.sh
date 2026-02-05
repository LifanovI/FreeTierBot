#!/bin/bash

# Automated deployment script for Telegram Coach Bot
# This script handles the complete setup from GCP project to live bot

# Save the root directory absolute path
SCRIPT_ROOT=$(pwd)

# Error handler function to keep terminal open
handle_error() {
    echo ""
    echo "🛑 Script stopped due to error: $1"
    echo ""
    echo "Press Enter to exit..."
    read -r
    exit 1
}

echo "🤖 FreeTierBot - Automated Deployment"
echo "====================================="

# Bot Selection
echo ""
echo "📋 Select Bot to Deploy"
echo "----------------------"

# Find all bot directories in community_bots
BOT_DIRS=()
if [ -d "community_bots" ]; then
    for dir in community_bots/*/; do
        if [ -d "$dir" ]; then
            # Extract bot name from directory path
            bot_name=$(basename "$dir")
            BOT_DIRS+=("$bot_name")
        fi
    done
fi

# If no bots found, check if we're in a bot directory directly
if [ ${#BOT_DIRS[@]} -eq 0 ]; then
        echo "❌ No bots found. Please ensure community_bots/ directory exists with bot subdirectories."
        handle_error "No bots found"
else
    # Display available bots
    echo "Available bots:"
    for i in "${!BOT_DIRS[@]}"; do
        echo "$((i+1))) ${BOT_DIRS[$i]}"
    done
    echo ""
    
    # Get user selection
    while true; do
        read -p "Please select a bot to deploy (1-${#BOT_DIRS[@]}) (enter number only): " selection
        
        # Validate input
        if [[ "$selection" =~ ^[0-9]+$ ]] && [ "$selection" -ge 1 ] && [ "$selection" -le "${#BOT_DIRS[@]}" ]; then
            selected_index=$((selection - 1))
            SELECTED_BOT_DIR="community_bots/${BOT_DIRS[$selected_index]}/"
        BOT_OPTIONAL_DEPLOY_SCRIPT="${SCRIPT_ROOT}/${SELECTED_BOT_DIR}optional_deploy.sh"
        echo "✅ Selected bot: ${BOT_DIRS[$selected_index]}"
            break
        else
            echo "❌ Invalid selection. Please enter a number between 1 and ${#BOT_DIRS[@]}."
        fi
    done
fi

echo ""
echo "🤖 Selected Bot: $SELECTED_BOT_DIR"
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
CURRENT_USER_EMAIL=$(gcloud auth list --filter=status:ACTIVE --format="value(account)" | head -n 1)
if [ -z "$CURRENT_USER_EMAIL" ]; then
    echo "❌ Not authenticated with gcloud. Please run 'gcloud auth login' first."
    handle_error "Not authenticated with gcloud"
fi

echo "✅ Prerequisites check passed (Logged in as: $CURRENT_USER_EMAIL)"

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
# Adjust path to be relative to terraform directory (../community_bots/...)My Project 25968
BOT_SOURCE_PATH="../${SELECTED_BOT_DIR}"
cat > terraform/terraform.tfvars << EOF
project_id         = "$PROJECT_ID"
telegram_bot_token = "$BOT_TOKEN"
gemini_api_key     = "$GEMINI_KEY"
whitelist_user_ids = "$WHITELIST_IDS"
bot_source_path    = "$BOT_SOURCE_PATH"
deployer_email     = "$CURRENT_USER_EMAIL"
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
echo "� Initializing Terraform..."
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

# Run bot-specific optional deployment steps
echo ""
echo "📊 Running bot-specific optional deployment..."
run_optional_deploy() {
    local project_id=$1
    
    if [ -f "$BOT_OPTIONAL_DEPLOY_SCRIPT" ]; then
        echo "   Found optional deployment script: $BOT_OPTIONAL_DEPLOY_SCRIPT"
        bash "$BOT_OPTIONAL_DEPLOY_SCRIPT" "$project_id"
    else
        echo "   ⚠️ No optional_deploy.sh found at $BOT_OPTIONAL_DEPLOY_SCRIPT, skipping"
    fi
}

# Call the function to run optional deployment
run_optional_deploy "$PROJECT_ID"

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
echo "Your Telegram Bot is now live!"
echo "It will guide you through setup process once it receives /start command"
echo ""
echo "To destroy the infrastructure later: cd terraform && terraform workspace select $PROJECT_ID && terraform destroy"
