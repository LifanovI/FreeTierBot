# Contributing to FreeTierBot

Thanks for your interest in contributing to **FreeTierBot** 🎉  
The goal of this project is to make Telegram bots **free, reusable, and boring to deploy**.

We welcome contributions of all kinds — especially new bot templates.

---

## 🧭 How to Contribute

### 1. Fork the repository
Click the **Fork** button on GitHub to create your own copy.

### 2. Create a branch
Create a feature branch in your fork:

```bash
git checkout -b my-bot-or-fix
```

### 3. Make your changes
Depending on what you’re contributing:

#### 🧩 Adding a new bot
- Add your bot under:
  ```
  /community_bots/<your-bot-name>/
  ```
- Include a `README.md` explaining:
  - What the bot does
  - Any special configuration
- Follow the same interface as the example bot (`/bot`)

> Please do **not** modify Terraform when adding a bot template.

#### 🏗️ Improving infrastructure
- Terraform changes are welcome
- Please open an issue or discussion first for non-trivial changes

#### 📚 Docs, fixes, improvements
- Typos, clarifications, examples, and refactors are welcome

---

## 🚫 What Not to Do

- ❌ Do not commit secrets, tokens, or API keys
- ❌ Do not include Terraform state files (`*.tfstate`)
- ❌ Do not push directly to `main` (it is protected)

---

## 🔀 Submitting a Pull Request

1. Push your branch to your fork
2. Open a Pull Request against the `main` branch
3. Clearly describe:
   - What you added or changed
   - Why it’s useful
4. Be open to feedback — reviews are part of the process 🙂

All PRs require approval before merging.

---

## 💡 Guidelines

- Keep things simple and readable
- Prefer clarity over cleverness
- Follow existing project structure
- Small, focused PRs are easier to review

---

## 🧑‍🚀 Community

This project is early-stage and evolving.
If you’re unsure about something:
- Open an issue
- Start a discussion
- Ask questions in your PR

Friendly collaboration > perfection.

---

Thanks for helping build the FreeTierBot ecosystem ❤️
