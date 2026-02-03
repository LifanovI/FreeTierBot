# AI Reminder & Coaching Bot

A reference implementation of a Telegram bot built on the **FreeTierBot** platform. This bot uses Google's Gemini AI to help users manage reminders and provides coaching through natural language.

## 🧠 Features

* **Natural Language Processing**: Set reminders by simply talking to the bot.
* **AI Coaching**: Receive guidance and encouragement along with your reminders.
* **Smart Scheduling**: Handles complex recurring patterns and timezones.
* **Persistent State**: Stores your reminders and preferences securely in Firestore.

---

## 🚀 Usage

The bot is designed to be used with natural language, but also supports specific commands:

### Core Commands
* `/start` — Start the onboarding process and setup your profile.
* `/remind [time] [task]` — Manually set a reminder (e.g., `/remind 2026-01-26T09:00:00 Brush my teeth 1,2,3,5`).
* `/list_reminders` — See all your active and recurring reminders.
* `/delete [index]` — Delete a specific reminder by its index from the list.

### Configuration
* `/system_prompt` — Customize the AI's personality and behavior.
* `/set_timezone` — Set or update your local timezone for accurate reminders.

---

## 🛠️ Bot-Specific Setup

This bot requires specific Firestore composite indexes to function correctly (e.g., for querying pending reminders across all users).

These are handled automatically by the `optional_deploy.sh` script:

```bash
# This script is called by the main deploy.sh
./optional_deploy.sh [PROJECT_ID]
```

It deploys the following indexes:
1. `reminders` (user_id ASC, status ASC, remind_at ASC)
2. `reminders` (status ASC, remind_at ASC)

---

## 🧑‍💻 Customization

You can modify the bot's behavior by editing the files in this directory:
* `ai_agent.py`: Logic for interacting with Gemini.
* `reminders.py`: Firestore interaction and reminder management.
* `main.py`: Entry point and webhook handler.
