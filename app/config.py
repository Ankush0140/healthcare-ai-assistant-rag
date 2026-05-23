import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # Application
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    log_level: str = "INFO"

    # LLM (Local Ollama)
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "gemma:2b"
    llm_timeout: int = 120
    llm_temperature: float = 0.1

    # Embeddings
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"

    # Vector DB
    chroma_db_dir: str = "./vector_store"
    chroma_collection: str = "healthcare_docs"

    # RAG Pipeline
    chunk_size: int = 500
    chunk_overlap: int = 50
    top_k: int = 3
    similarity_threshold: float = 0.3

    # File Paths
    upload_dir: str = "./data"
    log_dir: str = "./logs"
    slots_config_path: str = "./config/slots.json"
    intents_config_path: str = "./config/intents.json"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()

# Ensure directories exist
os.makedirs(settings.upload_dir, exist_ok=True)
os.makedirs(settings.log_dir, exist_ok=True)
os.makedirs(settings.chroma_db_dir, exist_ok=True)
