from fastapi import APIRouter, BackgroundTasks, Request, HTTPException
from pathlib import Path
import sqlite3

from .schemas import JobRequest, ScanRequest, ScanResponse
from pdf_optimizer.core.processor import get_pdf_files
from pdf_optimizer.core.filtering import filter_by_mtime
from pdf_optimizer.config.settings import settings
from pdf_optimizer.scheduler.schedule import reload_jobs

router = APIRouter()


@router.post("/jobs", status_code=202)
async def create_job(request: Request, job_req: JobRequest, background_tasks: BackgroundTasks):
    """Запускает задачу сжатия в фоновом режиме."""
    runner = request.app.state.runner

    # Добавляем выполнение run_job в background_tasks FastAPI
    background_tasks.add_task(
        runner.run_job,
        source="api",
        root_dir=job_req.root_dir,
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


@router.post("/scan", response_model=ScanResponse)
async def scan_directory(request: Request, scan_req: ScanRequest):
    """
    DRY-RUN: Показывает, сколько файлов будет обработано с заданными параметрами
    (с учетом временного фильтра и базы данных идемпотентности).
    """
    registry = request.app.state.registry
    root_path = Path(scan_req.root_dir)

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