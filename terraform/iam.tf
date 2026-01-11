# Grant Compute Engine service account access to Secret Manager
resource "google_project_iam_member" "compute_secretmanager" {
  project = var.project_id
  role    = "roles/secretmanager.secretAccessor"
  member  = "serviceAccount:${data.google_project.project.number}-compute@developer.gserviceaccount.com"

  depends_on = [google_project_service.secretmanager, google_project_service.compute]
}

# Allow unauthenticated access to webhook function
resource "google_cloud_run_service_iam_member" "webhook_invoker" {
  service  = google_cloudfunctions2_function.telegram_webhook.name
  location = google_cloudfunctions2_function.telegram_webhook.location
  role     = "roles/run.invoker"
  member   = "allUsers"

  depends_on = [google_cloudfunctions2_function.telegram_webhook]
}

# Grant Cloud Scheduler Pub/Sub publisher
# resource "google_project_iam_member" "scheduler_pubsub" {
#   project = var.project_id
#   role    = "roles/pubsub.publisher"
#   member  = "serviceAccount:${data.google_project.project.number}@cloudscheduler.gserviceaccount.com"

#   depends_on = [google_project_service.cloudscheduler]
# }

# Data source for project number
data "google_project" "project" {
  project_id = var.project_id
}
