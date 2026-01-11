resource "google_cloud_scheduler_job" "reminder_scheduler" {
  name        = "reminder-scheduler"
  description = "Triggers reminder checks every minute"
  schedule    = var.scheduler_frequency
  time_zone   = "UTC"

  pubsub_target {
    topic_name = google_pubsub_topic.scheduler_tick.id
    data       = base64encode("{}")
  }

  depends_on = [google_project_service.cloudscheduler, google_pubsub_topic.scheduler_tick]
}
