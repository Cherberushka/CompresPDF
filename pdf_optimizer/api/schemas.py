from pydantic import BaseModel, Field
from typing import List, Optional

class JobRequest(BaseModel):
    """Запрос на ручной старт сжатия через API."""
    root_dir: str = Field(..., description="Абсолютный путь к директории для обработки")
    since: str = Field("24h", description="Временной фильтр (например, 24h, 7d, 1mo)")
    quality: str = Field("default", description="Качество Ghostscript (fast/default/archive/maximum)")
    aggression: str = Field("gg", description="Уровень агрессии MuPDF (g/gg/ggg/gggg)")

class ScanRequest(BaseModel):
    """Запрос на dry-run (какие файлы попадут в обработку)."""
    root_dir: str
    since: str = "24h"

class ScanResponse(BaseModel):
    """Ответ на dry-run."""
    total_found: int
    filtered_by_time: int
    already_processed: int
    to_process: int
    files_to_process: List[str]