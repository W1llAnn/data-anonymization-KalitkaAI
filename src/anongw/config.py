"""Настройки сервиса из переменных окружения."""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Все параметры читаются с префиксом ANONGW_ (см. .env.example)."""

    model_config = SettingsConfigDict(env_prefix="ANONGW_", env_file=".env", extra="ignore")

    # Раздельные ключи: клиент сервиса и доступ к внешней модели (ТЗ п.7)
    service_api_key: str = "dev-service-key"
    model_api_key: str = "dev-model-key"
    model_base_url: str = "http://localhost:9000"

    # Хранилище соответствий
    mapping_db_path: str = "./mapping.db"
    mapping_ttl_hours: int = 24

    # Ограничение размера inline-файлов (МБ)
    max_file_mb: int = 10
