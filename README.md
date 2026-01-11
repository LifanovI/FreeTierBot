# Personal Telegram Coach/Reminder Bot

A minimal personal Telegram bot that handles reminders using Google Cloud Platform serverless services (free tier).

## Architecture

- **Cloud Functions (2nd gen, Python)**: `telegram_webhook` (HTTP triggered) and `scheduler_tick` (Pub/Sub triggered)
- **Firestore**: Stores reminders and user state
- **Cloud Scheduler**: Triggers reminder checks every minute
- **Pub/Sub**: Used for scheduler events
- **Secret Manager**: Stores Telegram bot token

## Features

- `/remind <time> <message> [interval]`: Set a one-time or recurring reminder
- `/list`: List all active reminders
- `/delete <number>`: Delete a reminder by number

## Time Formats

Supports natural language and ISO formats:
- "2026-01-10 09:00"
- "tomorrow 3pm"
- "in 2 hours"

## Intervals

- `daily`
- `weekly`
- `monthly`

## Quick Start (Automated)

For the easiest deployment, use the automated script:

```bash
# Make sure you have Terraform and gcloud CLI installed and authenticated
./deploy.sh
```

The script will:
- ✅ Check prerequisites
- ✅ Prompt for your GCP project ID and bot token
- ✅ Deploy all infrastructure automatically
- ✅ Set up the Telegram webhook
- ✅ Confirm successful deployment

## Manual Deployment

If you prefer manual control:

### Prerequisites

- Google Cloud Project with billing enabled (stays at $0 with free tier)
- Terraform installed
- gcloud CLI authenticated
- Telegram Bot Token (get from @BotFather)

### Steps

1. **Get your Telegram Bot Token:**
   - Message @BotFather on Telegram
   - Create a new bot and copy the token

2. **Create terraform.tfvars file:**
   ```hcl
   project_id          = "your-gcp-project-id"
   telegram_bot_token  = "your-bot-token-here"
   ```

3. **Navigate to terraform directory and initialize:**
   ```bash
   cd terraform
   terraform init
   ```

4. **Apply Terraform infrastructure:**
   ```bash
   terraform apply
   ```

5. **Set Telegram webhook:**
   ```bash
   cd ../scripts
   ./set_webhook.sh $(terraform output -raw telegram_webhook_function_url) $(terraform output -raw webhook_secret) your-bot-token-here
   ```

6. **Bot is live!**

## Usage

Start a chat with your bot and use the commands above.

## Free Tier Limits

- ~43k function invocations/month
- Firestore reads/writes minimal
- Single scheduler job

## Cleanup

```bash
cd terraform
terraform destroy
