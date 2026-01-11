variable "project_id" {
  description = "GCP Project ID"
  type        = string
}

variable "region" {
  description = "GCP Region"
  type        = string
  default     = "us-central1"
}

variable "telegram_bot_token_secret" {
  description = "Name of the Secret Manager secret for Telegram bot token"
  type        = string
  default     = "telegram-bot-token"
}

variable "scheduler_frequency" {
  description = "Cron schedule for reminder checks"
  type        = string
  default     = "* * * * *"  # Every minute
}

variable "telegram_bot_token" {
  description = "Telegram bot token from BotFather"
  type        = string
  sensitive   = true
}

variable "gemini_api_key" {
  description = "Google Gemini API key for AI agent"
  type        = string
  sensitive   = true
}

variable "webhook_secret" {
  description = "Secret token for webhook authentication"
  type        = string
  sensitive   = true
  default     = null
}
