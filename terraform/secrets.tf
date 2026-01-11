# Generate random webhook secret
resource "random_password" "webhook_secret" {
  length  = 32
  special = false
}

resource "google_secret_manager_secret" "telegram_bot_token" {
  secret_id = var.telegram_bot_token_secret

  replication {
    auto {}
  }

  depends_on = [google_project_service.secretmanager]
}

resource "google_secret_manager_secret_version" "telegram_bot_token" {
  secret      = google_secret_manager_secret.telegram_bot_token.id
  secret_data = var.telegram_bot_token

  depends_on = [google_secret_manager_secret.telegram_bot_token]
}
