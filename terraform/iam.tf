# Grant Compute Engine service account access to Secret Manager
resource "google_project_iam_member" "compute_secretmanager" {
  project = var.project_id
  role    = "roles/secretmanager.secretAccessor"
  member  = "serviceAccount:${data.google_project.project.number}-compute@developer.gserviceaccount.com"

  depends_on = [google_project_service.secretmanager, google_project_service.compute]
}

# Grant Compute Engine service account access to Firestore
resource "google_project_iam_member" "compute_firestore" {
  project = var.project_id
  role    = "roles/datastore.user"
  member  = "serviceAccount:${data.google_project.project.number}-compute@developer.gserviceaccount.com"

  depends_on = [google_project_service.compute]
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
resource "google_project_iam_member" "scheduler_pubsub" {
  project = var.project_id
  role    = "roles/pubsub.publisher"
  member  = "serviceAccount:service-${data.google_project.project.number}@gcp-sa-cloudscheduler.iam.gserviceaccount.com"

  depends_on = [google_project_service.cloudscheduler]
}

# Grant Cloud Functions Service Agent access to Artifact Registry
resource "google_project_iam_member" "gcf_artifactregistry" {
  project = var.project_id
  role    = "roles/artifactregistry.reader"
  member  = "serviceAccount:service-${data.google_project.project.number}@gcf-admin-robot.iam.gserviceaccount.com"

  depends_on = [google_project_service.cloudfunctions]
}

# Grant Storage Object Admin to the deployer (if email is provided)
resource "google_project_iam_member" "deployer_storage" {
  count   = var.deployer_email != null ? 1 : 0
  project = var.project_id
  role    = "roles/storage.objectAdmin"
  member  = "user:${var.deployer_email}"
}

# Data source for project number
data "google_project" "project" {
  project_id = var.project_id
}
