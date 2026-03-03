resource "google_firestore_database" "database" {
  name        = "(default)"
  location_id = var.region
  type        = "FIRESTORE_NATIVE"

  depends_on = [google_project_service.firestore]
}

resource "google_firestore_index" "expenses_user_spent_at" {
  project    = var.project_id
  collection = "expenses"

  fields {
    field_path = "user_id"
    order      = "ASCENDING"
  }

  fields {
    field_path = "spent_at"
    order      = "ASCENDING"
  }

  depends_on = [
    google_project_service.firestore,
    google_firestore_database.database,
  ]
}

resource "google_firestore_index" "expenses_user_category_spent_at" {
  project    = var.project_id
  collection = "expenses"

  fields {
    field_path = "user_id"
    order      = "ASCENDING"
  }

  fields {
    field_path = "category"
    order      = "ASCENDING"
  }

  fields {
    field_path = "spent_at"
    order      = "ASCENDING"
  }

  depends_on = [
    google_project_service.firestore,
    google_firestore_database.database,
  ]
}

