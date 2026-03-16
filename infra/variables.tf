# ============================================================
# variables.tf - FinServ LATAM Compliance Agent
# Infraestructura GCP para el sistema multi-agente
# ============================================================

variable "project_id" {
  description = "ID del proyecto GCP. Debe existir previamente."
  type        = string
  default     = "finserv-latam-compliance"
}

variable "region" {
  description = "Región GCP. CRÍTICO: debe ser us-central1 por restricción regulatoria de datos personales."
  type        = string
  default     = "us-central1"
  validation {
    condition     = var.region == "us-central1"
    error_message = "La restricción regulatoria (UIAF/CNBV/SBS) exige que los datos permanezcan en us-central1."
  }
}

variable "environment" {
  description = "Ambiente de despliegue: dev | staging | prod"
  type        = string
  default     = "dev"
  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "El ambiente debe ser dev, staging o prod."
  }
}

variable "api_image" {
  description = "Imagen Docker de la API publicada en Artifact Registry."
  type        = string
  default     = "us-central1-docker.pkg.dev/finserv-latam-compliance/compliance-agent/api:latest"
}

variable "cloud_run_min_instances" {
  description = "Mínimo de instancias Cloud Run (0 para dev, >0 para prod — elimina cold start)."
  type        = number
  default     = 0
}

variable "cloud_run_max_instances" {
  description = "Máximo de instancias Cloud Run para auto-scaling."
  type        = number
  default     = 10
}

variable "cloud_run_memory" {
  description = "Memoria asignada por instancia Cloud Run."
  type        = string
  default     = "2Gi"
}

variable "cloud_run_cpu" {
  description = "CPUs asignadas por instancia Cloud Run."
  type        = string
  default     = "2"
}

variable "alloydb_cpu_count" {
  description = "Número de CPUs para la instancia AlloyDB (vector store)."
  type        = number
  default     = 2
}

variable "gcs_docs_bucket_name" {
  description = "Nombre del bucket GCS para documentos PDF de clientes."
  type        = string
  default     = "finserv-latam-client-docs"
}

variable "llm_mode" {
  description = "Modo LLM: mock | claude | gemini. En producción siempre 'gemini' (Vertex AI)."
  type        = string
  default     = "gemini"
}

variable "anthropic_api_key_secret" {
  description = "Nombre del secret en Secret Manager con la API key de Anthropic (si llm_mode=claude)."
  type        = string
  default     = "anthropic-api-key"
}
