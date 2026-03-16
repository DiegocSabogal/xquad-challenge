"""
Configuracion central del sistema.
Usa pydantic-settings para leer desde variables de entorno o .env
"""
from pathlib import Path
from pydantic_settings import BaseSettings
from pydantic import Field
from dotenv import load_dotenv

# Ruta absoluta al .env — funciona sin importar el directorio de trabajo
_ENV_FILE = Path(__file__).parent / ".env"

# Cargar .env explicitamente antes de que pydantic-settings lo procese
load_dotenv(dotenv_path=_ENV_FILE, override=True)


class Settings(BaseSettings):
    # LLM
    llm_mode: str = Field(default="mock", description="mock | claude | gemini")
    anthropic_api_key: str = Field(default="", description="API key de Anthropic Claude")
    google_cloud_project: str = Field(default="finserv-latam-dev")
    vertex_ai_location: str = Field(default="us-central1")

    # API
    api_host: str = Field(default="0.0.0.0")
    api_port: int = Field(default=8000)

    # ChromaDB
    chroma_host: str = Field(default="localhost")
    chroma_port: int = Field(default=8001)

    # Langfuse
    langfuse_public_key: str = Field(default="")
    langfuse_secret_key: str = Field(default="")
    langfuse_host: str = Field(default="http://localhost:3000")
    langfuse_enabled: bool = Field(default=False)

    # Umbrales de negocio
    risk_threshold_escalate: int = Field(default=7, description="Riesgo >= este valor escala al humano")
    risk_threshold_discard: int = Field(default=3, description="Riesgo <= este valor descarta la alerta")

    model_config = {"env_file": str(_ENV_FILE), "env_file_encoding": "utf-8", "extra": "ignore"}


settings = Settings()
