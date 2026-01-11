# Topic for Telegram webhook messages
resource "google_pubsub_topic" "telegram_webhook" {
  name = "telegram-webhook"
}

# Topic for scheduler ticks
resource "google_pubsub_topic" "scheduler_tick" {
  name = "scheduler-tick"
}
