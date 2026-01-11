resource "google_storage_bucket" "function_bucket" {
  name     = "${var.project_id}-functions"
  location = var.region
}

data "archive_file" "bot_source" {
  type        = "zip"
  source_dir  = "../bot"
  output_path = "/tmp/bot.zip"
}

resource "google_storage_bucket_object" "bot_zip" {
  name   = "bot-${data.archive_file.bot_source.output_md5}.zip"
  bucket = google_storage_bucket.function_bucket.name
  source = data.archive_file.bot_source.output_path
}

resource "google_cloudfunctions2_function" "telegram_webhook" {
  name        = "telegram-webhook"
  location    = var.region
  description = "Handles incoming Telegram messages"

  build_config {
    runtime     = "python311"
    entry_point = "telegram_webhook"
    source {
      storage_source {
        bucket = google_storage_bucket.function_bucket.name
        object = google_storage_bucket_object.bot_zip.name
      }
    }
  }

  service_config {
    max_instance_count = 1
    available_memory   = "256M"
    timeout_seconds    = 60
    environment_variables = {
      PROJECT_ID     = var.project_id
      WEBHOOK_SECRET = random_password.webhook_secret.result
    }
    secret_environment_variables {
      key        = "TELEGRAM_BOT_TOKEN"
      project_id = var.project_id
      secret     = var.telegram_bot_token_secret
      version    = "latest"
    }
    secret_environment_variables {
      key        = "GEMINI_API_KEY"
      project_id = var.project_id
      secret     = "gemini-api-key"
      version    = "latest"
    }
  }

  depends_on = [
    google_project_service.cloudfunctions,
    google_project_service.cloudbuild,
    google_project_service.secretmanager,
    google_project_service.artifactregistry,
    google_project_service.compute,
    google_project_service.run,
    google_project_service.eventarc
  ]
}

resource "google_cloudfunctions2_function" "scheduler_tick" {
  name        = "scheduler-tick"
  location    = var.region
  description = "Checks for due reminders and sends them"

  build_config {
    runtime     = "python311"
    entry_point = "scheduler_tick"
    source {
      storage_source {
        bucket = google_storage_bucket.function_bucket.name
        object = google_storage_bucket_object.bot_zip.name
      }
    }
  }

  service_config {
    max_instance_count = 1
    available_memory   = "256M"
    timeout_seconds    = 60
    environment_variables = {
      PROJECT_ID = var.project_id
    }
    secret_environment_variables {
      key        = "TELEGRAM_BOT_TOKEN"
      project_id = var.project_id
      secret     = var.telegram_bot_token_secret
      version    = "latest"
    }
    secret_environment_variables {
      key        = "GEMINI_API_KEY"
      project_id = var.project_id
      secret     = "gemini-api-key"
      version    = "latest"
    }
  }

  event_trigger {
    trigger_region = var.region
    event_type     = "google.cloud.pubsub.topic.v1.messagePublished"
    pubsub_topic   = google_pubsub_topic.scheduler_tick.id
    retry_policy   = "RETRY_POLICY_DO_NOT_RETRY"
  }

  depends_on = [
    google_project_service.cloudfunctions,
    google_project_service.cloudbuild,
    google_project_service.secretmanager,
    google_project_service.artifactregistry,
    google_project_service.compute,
    google_project_service.run,
    google_project_service.eventarc
  ]
}
