# Personal AI Telegram Coach/Reminder Bot

An intelligent personal Telegram bot powered by Gemini AI that handles reminders and provides natural language coaching using Google Cloud Platform serverless services (free tier).

## Architecture

- **Cloud Functions (2nd gen, Python)**: `telegram_webhook` (HTTP triggered) and `scheduler_tick` (Pub/Sub triggered)
- **Firestore**: Stores reminders and user state
- **Cloud Scheduler**: Triggers reminder checks every minute
- **Pub/Sub**: Used for scheduler events
- **Secret Manager**: Stores Telegram bot token

## Reminders
Reminders can be:
- External - standard user set reminders which are verbose and result in messages in chat
- Internal - reminders triggering AI agent to message
- System - not visible to user/ai agent. Can be used for system actions (e.g. setting other reminders or triggers). If during last 12 hours, there was no interactions with AI agent, a system reminders ticking every hour will prompt AI agent to reach out with probability of 20% every hour (excluding night hours) 

To save space, inactive reminders are removed

## AI Features and Reminders

All messages except for command will be processed by AI agent, which can Get Reminders, Modify/delete Reminders and Set reminders
- If during last 
- To save space, incative reminders will be removed

Syntax for setting reminders:
```bash
set reminder_from_ai(chat_id, next_run_str, text, interval=None, reminder_type='internal', folowup=10)
```


## User Commands

- `/initiate`: Configure the system from start
- `/remind <time> <message> [interval]`: Set a one-time or recurring external reminder
- `/list`: List all active external reminders
- `/delete <number>`: Delete a reminder by number
- `/system_prompt <text>`: Configure the AI's behavior and personality


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
- Gemini API Key (get from [Google AI Studio](https://aistudio.google.com/app/apikey))

### Steps

1. **Get your Telegram Bot Token:**
   - Message @BotFather on Telegram
   - Create a new bot and copy the token

2. **Create terraform.tfvars file:**
   ```hcl
   project_id          = "your-gcp-project-id"
   telegram_bot_token  = "your-bot-token-here"
   gemini_api_key      = "your-gemini-api-key-here"
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
