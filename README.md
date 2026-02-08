# 🚀 FreeTierBot — Telegram Bots on Free Cloud Infrastructure

**Build, deploy, and share Telegram bots for $0.**

**Do you have a Google Account, e.g., for Gmail? If yes — you already have everything you need to deploy a free AI bot! Isn't that cool?**

FreeTierBot is an open-source **Telegram bot platform + Terraform blueprint** for running production-ready bots entirely on **cloud free tiers** (Google Cloud out of the box). It is designed to be **reused and published** by the community.

---

## ⭐ Why FreeTierBot?

Most Telegram bots require hosting costs and infrastructure maintenance. FreeTierBot fixes that:

* 🆓 **Runs on cloud free tier** (Google Cloud)
* 🧱 **Reusable Terraform infrastructure**
* ⚡ **One-command deploy** (`./deploy.sh`)
* 🤖 **AI-ready** (Gemini included)
* 🌍 **Built for open source** — fork it, brand it, ship it

If you can write a Python function, you can ship a Telegram bot.

---

## 🧩 Built with FreeTierBot

FreeTierBot is designed to be **reused and remixed**.
Want to become a contributor and see your bot here?
- Put your bot in `/community_bots` folder
- Open a **pull request** to add your bot to the repo

### What is Reused

* Serverless infrastructure
* Deployment automation
* Standard bot interface

---

## 🧠 What’s Included

* ✅ **Production-grade serverless cloud architecture**
* ✅ **Terraform** for 100% reproducible deployments
* ✅ **Automated deployment script** for easy setup
* ✅ **Reusable bot setup** via optional deployment scripts
* ✅ **Example AI Bot** in `/community_bots/reminder_bot/` ([Documentation](./community_bots/reminder_bot/README.md))

---

## 🧩 Architecture Overview

```
Telegram ──▶ Cloud Functions (Python 3.11)
                │
                ▼
            Firestore
                │
Cloud Scheduler ─▶ Pub/Sub ─▶ Retry Queue
                │
                ▼
             Gemini API
```

### Core Components

* **Cloud Functions (2nd gen)** — webhook + scheduler workers
* **Firestore** — reminders, user state, retries
* **Cloud Scheduler** — minute-level cron
* **Pub/Sub** — async events & retries
* **Secret Manager** — bot tokens & API keys
* **Gemini API** — AI responses & coaching

---

## 🛠️ Prerequisites

* Google Cloud project with billing enabled (stays free on free tier)
* [Terraform installed](https://developer.hashicorp.com/terraform/tutorials/aws-get-started/install-cli)
* gcloud CLI authenticated for both CLI commands:
```bash
gcloud auth login
```
* And terraform:
```bash
gcloud auth application-default login
```
* [Telegram Bot Token](https://core.telegram.org/bots/tutorial#obtain-your-bot-token)
* [Gemini API Key](https://aistudio.google.com/api-keys) (use Free Tier for Free)

**Heads up:** Setting up gcloud on Windows can sometimes be tricky.
Check this [guide](https://docs.cloud.google.com/sdk/docs/install-sdk) and ask your AI agent for help.
Make sure before proceeding further that commands like ```gcloud auth list``` work otherwise the script will fail

## 🚀 One command deployment 

> ⏱️ ~5 minutes from zero to live bot

All initial deployment is handled by `deploy.sh`. **Important: Run it as a script, not with `source`!. Equally important, do not forget to authenticate with google for both auth login and auth application-default login**

### For macOS and Linux

1. **Make the script executable** (if not already):
   ```bash
   chmod +x deploy.sh
   ```

2. **Run the deployment script**:
   ```bash
   ./deploy.sh
   ```

### For Windows

1. **Using Git Bash** (recommended):
   ```bash
   chmod +x deploy.sh
   ./deploy.sh
   ```

2. **Using Windows Subsystem for Linux (WSL)**:
   ```bash
   chmod +x deploy.sh
   ./deploy.sh
   ```

3. **Using Command Prompt or PowerShell**:
   - Install [Git Bash](https://git-scm.com/downloads) or [WSL](https://learn.microsoft.com/en-us/windows/wsl/install)
   - Or run: `bash deploy.sh` (if you have bash installed)

### What the script does

The script will:

* Prompt for cloud project & bot token
* Enable required APIs
* Deploy infrastructure via Terraform
* Set Telegram webhook automatically

When it finishes — **your bot is live**.

---

## 💸 Free Tier Reality Check

| Service         | Free Tier              |
| --------------- | ---------------------- |
| Cloud Functions | ~43k invocations/month |
| Firestore       | 50k reads/day          |
| Cloud Scheduler | 3M jobs/month          |
| Pub/Sub         | 10GB/month             |
| Gemini API      | Generous free tier     |

> For personal bots and small communities, **cost stays at $0**.

Make sure to check current values for [Google Free Tier](https://cloud.google.com/free)

---

## 🧑‍💻 Contributing & Ecosystem Vision

FreeTierBot is more than a repo — it’s meant to become an **ecosystem**.

We welcome:

* 🧩 New bot templates
* 🏗️ Terraform improvements
* 📚 Documentation & examples
* 🤖 AI tooling integrations

If you publish a bot built on FreeTierBot, **open a PR and showcase it**.

## 📋 Creating New Bots

To create a new bot based on FreeTierBot:

1. **Copy the example bot structure:**
   ```bash
   cp -r community_bots/reminder_bot community_bots/your-bot-name
   ```

2. **Create your bot's optional deployment script:**
    Your bot might need specialized setup like Firestore indexes. If you need a custom setup - just create an `optional_deploy.sh` script and the deploy script will handle the rest.
   Create `community_bots/your-bot-name/optional_deploy.sh` with your requirements:
   ```bash
   #!/bin/bash
   PROJECT_ID=$1
   echo "🚀 Running custom setup..."
   gcloud firestore indexes composite create \
     --collection-group="your_collection" \
     --field-config field-path=field1,order=ascending \
     --project="$PROJECT_ID" \
     --quiet
   ```

3. **Customize your bot logic:**
   - Modify the bot code in `community_bots/your-bot-name/bot/`
   - Update the Terraform configuration if needed
   - Test your bot locally

4. **Deploy your bot:**
   ```bash
   ./deploy.sh
   ```

The deployment script will automatically detect and execute your bot's `optional_deploy.sh` if it exists.

---

## 🐛 Troubleshooting

* Check Cloud Function logs
* Verify webhook configuration
* Confirm secrets in Secret Manager
* Monitor Pub/Sub subscriptions

Most issues surface clearly in cloud logs.

---

## 📄 License

MIT — build cool things, no permission required.

---

## 🌍 Mission

> Make Telegram bots **cheap**, **open**, and **boring to deploy**.

If this saves you time, ⭐ star the repo and share your bot with the community.

**Built with ❤️ for open-source developers.**
