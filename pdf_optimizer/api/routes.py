from fastapi import APIRouter, BackgroundTasks, Request, HTTPException
from pathlib import Path
import sqlite3
import os

from .schemas import JobRequest, ScanRequest, ScanResponse
from pdf_optimizer.core.processor import get_pdf_files
from pdf_optimizer.core.filtering import filter_by_mtime
from pdf_optimizer.config.settings import settings
from pdf_optimizer.scheduler.schedule import reload_jobs
from ..jobs import runner
from ..registry.store import RegistryStore

router = APIRouter()


def validate_path_safety(path: str) -> Path:
    """
    Валидация пути для предотвращения path traversal атак.
    Проверяет, что путь находится в разрешенной директории.
    """
    resolved_path = Path(path).resolve()
    
    # Разрешенные базовые директории
    allowed_bases = [
        settings.data_dir.resolve(),
    ]
    
    # Проверяем, начинается ли путь с одной из разрешенных базовых директорий
    is_safe = any(
        str(resolved_path).startswith(str(base)) 
        for base in allowed_bases
    )
    
    if not is_safe:
        raise HTTPException(
            status_code=403, 
            detail=f"Доступ к пути запрещен. Разрешены только пути внутри {settings.data_dir}"
        )
    
    return resolved_path


@router.post("/jobs", status_code=202)
async def create_job(request: Request, job_req: JobRequest, background_tasks: BackgroundTasks):
    """Запускает задачу сжатия в фоновом режиме."""
    runner = request.app.state.runner

    # Валидация пути перед использованием
    root_path = validate_path_safety(job_req.root_dir)

    # Добавляем выполнение run_job в background_tasks FastAPI
    background_tasks.add_task(
        runner.run_job,
        source="api",
        root_dir=str(root_path),
        since=job_req.since,
        quality=job_req.quality,
        aggression=job_req.aggression
    )
    return {"message": "Задача успешно добавлена в фоновую очередь", "params": job_req.model_dump()}

@router.get("/jobs")
async def list_jobs(request: Request, limit: int = 20):
    """Возвращает историю последних задач аудита."""
    registry = request.app.state.registry
    # Прямой SQL-запрос для быстрого чтения без перегрузки store.py
    with registry._get_connection() as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM jobs ORDER BY created_at DESC LIMIT ?", (limit,))
        jobs = [dict(row) for row in cursor.fetchall()]
    return {"jobs": jobs}


@router.post("/optimize")
async def start_optimization(background_tasks: BackgroundTasks):
    """
    Запуск оптимизации без блокировки Event Loop'а FastAPI.
    Задача передается в BackgroundTasks.
    """
    # Инициализируем хранилище (в реальном приложении лучше использовать Dependency Injection)
    registry = RegistryStore(settings.db_path)
    job_runner = runner.JobRunner(registry)

    # Запускаем метод run_job класса JobRunner в фоновом режиме
    # Передаем дефолтные параметры (их лучше брать из тела запроса)
    background_tasks.add_task(
        job_runner.run_job,
        source="api",
        root_dir=str(settings.data_dir),
        since="24h",
        quality="best",
        aggression="ggg"
    )
    return {"status": "success", "message": "Оптимизация запущена в фоновом режиме."}

@router.post("/scan", response_model=ScanResponse)
async def scan_directory(request: Request, scan_req: ScanRequest):
    """
    DRY-RUN: Показывает, сколько файлов будет обработано с заданными параметрами
    (с учетом временного фильтра и базы данных идемпотентности).
    """
    registry = request.app.state.registry
    
    # Валидация пути перед использованием
    root_path = validate_path_safety(scan_req.root_dir)

    if not root_path.exists():
        raise HTTPException(status_code=404, detail="Директория не найдена на сервере")

    # Симулируем пайплайн отбора
    all_files = get_pdf_files(root_path)
    recent_files = filter_by_mtime(all_files, scan_req.since)
    files_to_process = registry.exclude_already_processed(recent_files)

    return ScanResponse(
        total_found=len(all_files),
        filtered_by_time=len(recent_files),
        already_processed=len(recent_files) - len(files_to_process),
        to_process=len(files_to_process),
        files_to_process=[str(p.absolute()) for p in files_to_process]
    )


@router.get("/settings")
async def get_settings():
    """Возвращает текущую активную конфигурацию сервиса."""
    return settings.model_dump()


@router.post("/scheduler/reload")
async def trigger_scheduler_reload(request: Request):
    """Горячая перезагрузка расписания без рестарта сервера."""
    runner = request.app.state.runner
    reload_jobs(runner)
    return {"message": "Расписание успешно перезагружено из конфига"}