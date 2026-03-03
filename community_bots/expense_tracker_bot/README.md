# AI Expense Tracker Bot

A production-ready expense tracking Telegram bot built on the **FreeTierBot** platform.
This bot uses Google's Gemini API to:

- Parse natural language messages into structured expenses
- Store them in Firestore
- Answer questions about your spending over dynamic ranges (today, this week, last 3 days, this month, etc.)

---

## 🧠 Features

- **Natural Language Logging**  
  Examples:
  - `I spent 500 on food yesterday via card`
  - `Coffee 200 cash`
  - `Paid rent 12000 first of this month`

- **Dynamic Analytics via NLP**  
  Ask:
  - `How much did I spend today?`
  - `How much this week on food?`
  - `Show my expenses for last 3 days`
  - `What are my top categories this month?`

- **Persistent State in Firestore**  
  - Each expense is stored with amount, currency, category, description, payment method and timestamp.
  - Uses your timezone so “today / this week / last 3 days” are accurate.

---

## 🚀 Usage

The bot is designed to be used with natural language, but also supports commands:

### Core Commands

- `/start` — Intro and quick onboarding.
- `/list_expenses` — Show your most recent expenses (up to 20).
- `/list_commands` — Show available commands and examples.
- `/set_timezone` — Set or update your local timezone.

Most of the time you will just talk to the bot in plain English (or your language) and it will:

1. Parse intent (log expense vs analytics question)
2. Call Firestore-backed tools to store or query data
3. Reply with friendly, human-readable summaries

---

## 🛠️ Bot-Specific Setup

This bot requires specific Firestore composite indexes to efficiently query expenses by user, category and time.

These are handled automatically by the `optional_deploy.sh` script:

```bash
# Called by main deploy.sh
./optional_deploy.sh [PROJECT_ID]
```

It deploys indexes for:

1. `chat_history` (chat_id ASC, timestamp DESC) – shared with other AI bots
---

## 🧑‍💻 Customization

You can tune the bot's behaviour by editing:

- `ai_agent.py` — Gemini tools and conversation logic for NLP, expense logging and analytics.
- `expenses.py` — Firestore schema and helper queries for expenses.
- `main.py` — Telegram webhook entrypoint and basic command routing.
- `utils.py` — Time range helpers and currency formatting.

The bot is designed to be easy to extend (e.g. budgets, alerts, weekly summary pushes) while reusing the shared FreeTierBot infrastructure.

