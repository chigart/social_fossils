import os

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = os.environ.get("DATABASE_URL", "")

    airflow_base_url: str = os.environ.get(
        "AIRFLOW_BASE_URL",
        "http://airflow-api:8080",
    )
    airflow_dag_id: str = "import"
    ollama_base_url: str = os.environ.get(
        "OLLAMA_BASE_URL",
        "http://host.docker.internal:11434",
    )

    upload_max_size_bytes: int = 1000 * 1024 * 1024  # 1000 MB
    upload_staging_dir: str = os.environ.get(
        "UPLOAD_STAGING_DIR",
        "/tmp/uploads",
    )

    model_config = {
        "env_file": ".env",
        "case_sensitive": False,
    }


settings = Settings()
