# 🚀 FreeTierBot — Telegram Bots on Free Cloud Infrastructure

**Build, deploy, and share Telegram bots for $0.**

**Do you have a Google Account, e.g., for Gmail? If yes — you already have everything you need to deploy a free AI bot! Isn't that cool?**

FreeTierBot is an open-source **Telegram bot platform + Terraform blueprint** for running production-ready bots entirely on **cloud free tiers** (Google Cloud out of the box). It ships with a working **example bot** (AI reminders & coaching powered by Gemini) and is designed to be **reused and published** by the community.

> Think of FreeTierBot as **"create-react-app for Telegram bots — serverless, Terraform-first, and free-tier friendly."**

---

## ⭐ Why FreeTierBot?

Most Telegram bots require:

* Hosting costs
* Building and maintaining infrastructure

FreeTierBot fixes that:

* 🆓 **Runs on cloud free tier** (just monitor usage)
* 🧱 **Reusable Terraform infrastructure**
* ⚡ **One-command deploy**
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

* ✅ Working **AI reminder & coaching bot** in `/bot/`
* ✅ Production-grade **serverless cloud architecture**
* ✅ **Terraform** for 100% reproducible deployments
* ✅ Secure secrets via **Secret Manager**
* ✅ Scheduling, retries, and state handling

Use it as-is **or** replace the bot logic and publish your own in `/community_bots`.

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



## 🤖 Using the Example Bot
Bot can be used with just natural language, the only command you really need is
* `/start` — onboarding

However, you can override bot parameters with
* `/system_prompt` — customize AI personality
* `/set_timezone` — set timezone

You can also manually set and check reminders: 
* `/remind 2026-01-26T09:00:00 Brush my teeth 1,2,3,5` will set a reminder to brush teeth at 9 a.m. 26 of Jan at your local timezone and will repeat Monday, Tuesday, Wednesday, and Friday
* `/list_reminders`, `/delete [index]` - list, delete recurring reminders

This bot is a **reference implementation** — swap it with your own idea.

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
