import os
from pathlib import Path
from typing import List, Literal, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import BaseModel, Field, field_validator


class SchedulerJobConfig(BaseModel):
    name: str = "default_job"
    cron: str = "0 * * * *"  # Раз в час по умолчанию
    since: str = "24h"
    root_dir: str
    quality: Literal["fast", "default", "archive", "maximum"] = "default"
    aggression: str = "gg"

    @field_validator('aggression', mode='before')
    @classmethod
    def validate_aggression(cls, v: str) -> str:
        valid_levels = {'g', 'gg', 'ggg', 'gggg'}
        val = str(v).lower().strip()
        if val not in valid_levels:
            # Исправлен баг v14.1 (d/dd/ddd/dddd -> g/gg/ggg/gggg)
            raise ValueError(f"MuPDF aggression must be one of {valid_levels}")
        return val


class SchedulerConfig(BaseModel):
    jobs: List[SchedulerJobConfig] = Field(default_factory=list)


class ApiConfig(BaseModel):
    host: str = "0.0.0.0"
    port: int = 8080


class AppSettings(BaseSettings):
    """
    12-factor конфигурация сервиса.
    Порядок: дефолты -> конфигурационный файл (опционально) -> переменные окружения.
    """
    # Пути (серверные дефолты)
    data_dir: Path = Field(default=Path("/data"))
    log_dir: Path = Field(default=Path("/var/log/pdf-optimizer"))
    db_path: Path = Field(default=Path("/data/registry.sqlite"))

    # Вложенные конфигурации
    api: ApiConfig = Field(default_factory=ApiConfig)
    scheduler: SchedulerConfig = Field(default_factory=SchedulerConfig)

    # Глобальные параметры процесса
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    no_backup: bool = False  # SAFE DEFAULT: Для сервера бэкапы ВКЛЮЧЕНЫ
    backup_retention_days: int = 30

    # Системные бинарники
    ghostscript_path: str = "gs"
    mutool_path: str = "mutool"

    # Настройки загрузки из Env
    model_config = SettingsConfigDict(
        env_prefix="PDF_OPTIMIZER__",
        env_nested_delimiter="__",  # Пример: PDF_OPTIMIZER__API__PORT=8000
        env_file=".env",
        extra="ignore"
    )


# Глобальный инстанс настроек для импорта в модулях
# Вызывает валидацию конфигурации при старте приложения
settings = AppSettings()


def load_yaml_config(config_path: Path) -> None:
    """Опциональный загрузчик конфигурации из YAML файла"""
    import yaml
    global settings

    if config_path.exists():
        with open(config_path, 'r', encoding='utf-8') as f:
            yaml_data = yaml.safe_load(f) or {}

        # Обновляем инстанс settings с приоритетом YAML (если env не заданы)
        # В Pydantic v2 это делается через копирование или переинициализацию
        current_dump = settings.model_dump()

        # Простой merge словарей (в реальности лучше использовать глубокий merge)
        def deep_update(d, u):
            for k, v in u.items():
                if isinstance(v, dict):
                    d[k] = deep_update(d.get(k, {}), v)
                else:
                    d[k] = v
            return d

        merged_data = deep_update(current_dump, yaml_data)
        settings = AppSettings(**merged_data)