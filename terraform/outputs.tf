output "telegram_webhook_topic" {
  description = "Pub/Sub topic name for Telegram webhook"
  value       = google_pubsub_topic.telegram_webhook.name
}

output "scheduler_tick_topic" {
  description = "Pub/Sub topic name for scheduler ticks"
  value       = google_pubsub_topic.scheduler_tick.name
}

output "telegram_webhook_function_url" {
  description = "URL of the Telegram webhook Cloud Function"
  value       = google_cloudfunctions2_function.telegram_webhook.url
}

output "scheduler_tick_function_name" {
  description = "Name of the scheduler tick Cloud Function"
  value       = google_cloudfunctions2_function.scheduler_tick.name
}

output "function_bucket" {
  description = "GCS bucket for function sources"
  value       = google_storage_bucket.function_bucket.name
}

output "webhook_secret" {
  description = "Generated webhook secret for authentication"
  value       = random_password.webhook_secret.result
  sensitive   = true
}
