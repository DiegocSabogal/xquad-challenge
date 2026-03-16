# ============================================================
# main.tf - FinServ LATAM Compliance Agent
# Recursos críticos de GCP para producción
# ============================================================

terraform {
  required_version = ">= 1.6.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }
  # Backend remoto en GCS para estado compartido del equipo
  backend "gcs" {
    bucket = "finserv-latam-tf-state"
    prefix = "compliance-agent/terraform/state"
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# ============================================================
# APIs de GCP habilitadas
# ============================================================
resource "google_project_service" "apis" {
  for_each = toset([
    "run.googleapis.com",
    "artifactregistry.googleapis.com",
    "alloydb.googleapis.com",
    "storage.googleapis.com",
    "aiplatform.googleapis.com",  # Vertex AI
    "secretmanager.googleapis.com",
    "cloudresourcemanager.googleapis.com",
  ])
  service            = each.value
  disable_on_destroy = false
}

# ============================================================
# Artifact Registry — Imágenes Docker
# ============================================================
resource "google_artifact_registry_repository" "compliance_agent" {
  location      = var.region
  repository_id = "compliance-agent"
  description   = "Imágenes Docker del sistema de compliance agéntico"
  format        = "DOCKER"
  depends_on    = [google_project_service.apis]
}

# ============================================================
# GCS Bucket — Documentos PDF de clientes
# CRÍTICO: location us-central1 por restricción regulatoria
# ============================================================
resource "google_storage_bucket" "client_docs" {
  name          = "${var.gcs_docs_bucket_name}-${var.environment}"
  location      = var.region  # us-central1 — restricción regulatoria UIAF/CNBV/SBS
  force_destroy = false       # Nunca destruir en producción

  versioning {
    enabled = true  # Permite auditoría de cambios en documentos
  }

  lifecycle_rule {
    condition { age = 365 }
    action { type = "SetStorageClass"; storage_class = "NEARLINE" }
  }

  # Bloquear acceso público — datos sensibles de clientes
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"
}

# ============================================================
# AlloyDB — Vector store (pgvector) para RAG
# AlloyDB soporta pgvector natively y tiene mejor performance
# que Cloud SQL para búsquedas vectoriales en producción
# ============================================================
resource "google_alloydb_cluster" "compliance_db" {
  cluster_id = "compliance-vector-store-${var.environment}"
  location   = var.region

  initial_user {
    user     = "compliance_app"
    password = random_password.db_password.result
  }

  depends_on = [google_project_service.apis]
}

resource "google_alloydb_instance" "compliance_db_primary" {
  cluster       = google_alloydb_cluster.compliance_db.name
  instance_id   = "primary"
  instance_type = "PRIMARY"

  machine_config {
    cpu_count = var.alloydb_cpu_count
  }

  database_flags = {
    "max_connections" = "100"
  }
}

resource "random_password" "db_password" {
  length  = 32
  special = true
}

resource "google_secret_manager_secret" "db_password" {
  secret_id = "alloydb-compliance-password-${var.environment}"
  replication { auto {} }
  depends_on = [google_project_service.apis]
}

resource "google_secret_manager_secret_version" "db_password" {
  secret      = google_secret_manager_secret.db_password.id
  secret_data = random_password.db_password.result
}

# ============================================================
# Cloud Run — API del sistema de compliance
# ============================================================
resource "google_cloud_run_v2_service" "compliance_api" {
  name     = "compliance-api-${var.environment}"
  location = var.region

  template {
    service_account = google_service_account.compliance_runner.email

    scaling {
      min_instance_count = var.cloud_run_min_instances
      max_instance_count = var.cloud_run_max_instances
    }

    containers {
      image = var.api_image

      resources {
        limits = {
          memory = var.cloud_run_memory
          cpu    = var.cloud_run_cpu
        }
      }

      env {
        name  = "LLM_MODE"
        value = var.llm_mode
      }

      env {
        name  = "GOOGLE_CLOUD_PROJECT"
        value = var.project_id
      }

      env {
        name  = "VERTEX_AI_LOCATION"
        value = var.region
      }

      # Contraseña DB desde Secret Manager (nunca hardcodeada)
      env {
        name = "DB_PASSWORD"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.db_password.secret_id
            version = "latest"
          }
        }
      }
    }
  }

  depends_on = [
    google_project_service.apis,
    google_alloydb_instance.compliance_db_primary,
  ]
}

# ============================================================
# IAM — Principio de mínimo privilegio
# ============================================================
resource "google_service_account" "compliance_runner" {
  account_id   = "compliance-runner-${var.environment}"
  display_name = "Compliance Agent Cloud Run SA"
  description  = "Service account para el agente de compliance. Solo permisos necesarios."
}

# Leer documentos de clientes (solo lectura — el agente no escribe en GCS)
resource "google_storage_bucket_iam_member" "runner_gcs_reader" {
  bucket = google_storage_bucket.client_docs.name
  role   = "roles/storage.objectViewer"
  member = "serviceAccount:${google_service_account.compliance_runner.email}"
}

# Acceso a Vertex AI (Gemini) para inferencia LLM
resource "google_project_iam_member" "runner_vertex_user" {
  project = var.project_id
  role    = "roles/aiplatform.user"
  member  = "serviceAccount:${google_service_account.compliance_runner.email}"
}

# Leer secrets de Secret Manager
resource "google_project_iam_member" "runner_secret_accessor" {
  project = var.project_id
  role    = "roles/secretmanager.secretAccessor"
  member  = "serviceAccount:${google_service_account.compliance_runner.email}"
}

# Acceso a BigQuery para historial transaccional (solo lectura)
resource "google_project_iam_member" "runner_bigquery_reader" {
  project = var.project_id
  role    = "roles/bigquery.dataViewer"
  member  = "serviceAccount:${google_service_account.compliance_runner.email}"
}
