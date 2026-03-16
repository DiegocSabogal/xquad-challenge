# ============================================================
# outputs.tf - Valores de salida para referencia post-deploy
# ============================================================

output "api_url" {
  description = "URL pública del servicio Cloud Run de la API de compliance."
  value       = google_cloud_run_v2_service.compliance_api.uri
}

output "gcs_bucket_name" {
  description = "Nombre del bucket GCS para documentos de clientes."
  value       = google_storage_bucket.client_docs.name
}

output "artifact_registry_url" {
  description = "URL del Artifact Registry para push de imágenes Docker."
  value       = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.compliance_agent.repository_id}"
}

output "service_account_email" {
  description = "Email del service account usado por Cloud Run."
  value       = google_service_account.compliance_runner.email
}

output "alloydb_connection_name" {
  description = "Connection name del cluster AlloyDB para el vector store."
  value       = google_alloydb_cluster.compliance_db.name
  sensitive   = false
}
