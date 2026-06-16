import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from pdf_optimizer.config.settings import settings
from pdf_optimizer.registry.store import RegistryStore
from pdf_optimizer.jobs.runner import JobRunner
from pdf_optimizer.scheduler.schedule import start_scheduler, stop_scheduler
from pdf_optimizer.api.routes import router

# Базовая настройка логирования (улучшим ее в utils/helpers.py позже)
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("PDFOptimizer.app")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Управление жизненным циклом приложения FastAPI (Startup / Shutdown)."""
    logger.info("Инициализация сервиса PDF Optimizer...")

    # 1. Инициализация БД
    registry = RegistryStore(settings.db_path)

    # 2. Инициализация оркестратора
    runner = JobRunner(registry)

    # Сохраняем зависимости в state для доступа из роутов
    app.state.registry = registry
    app.state.runner = runner
    
    # 3. Инициализация rate limiter
    limiter = Limiter(key_func=get_remote_address, default_limits=[f"{settings.rate_limit}/minute"])
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    # 4. Запуск планировщика
    start_scheduler(runner)

    yield  # Приложение работает...

    # 5. Graceful Shutdown
    logger.info("Завершение работы сервиса...")
    stop_scheduler()


def create_app() -> FastAPI:
    """Фабрика для создания инстанса FastAPI."""
    from slowapi.middleware import SlowAPIMiddleware
    
    app = FastAPI(
        title="PDF Batch Optimizer Service",
        version="15.1.0",
        description="Фоновый сервис пакетного сжатия PDF с идемпотентностью и расписанием",
        lifespan=lifespan
    )
    
    # Добавляем middleware до регистрации роутов
    app.add_middleware(SlowAPIMiddleware)

    app.include_router(router, prefix="/api")
    
    # Добавляем health check и metrics endpoints
    @app.get("/health", tags=["Health"])
    async def health_check():
        """Проверка работоспособности сервиса."""
        return {"status": "healthy", "version": "15.1.0"}
    
    @app.get("/metrics", tags=["Metrics"])
    async def get_metrics(request: Request):
        """Базовые метрики сервиса."""
        import sqlite3
        
        # Проверяем, что приложение инициализировано (lifespan запущен)
        if not hasattr(request.app.state, 'registry'):
            return {
                "error": "Service not fully initialized",
                "status": "starting"
            }
        
        registry = request.app.state.registry
        runner = request.app.state.runner
        
        # Получаем количество активных задач из реестра
        try:
            with registry._get_connection() as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) as total FROM jobs")
                total_jobs = cursor.fetchone()["total"]
                
                cursor.execute("SELECT COUNT(*) as pending FROM jobs WHERE status = 'pending'")
                pending_jobs = cursor.fetchone()["pending"]
                
                cursor.execute("SELECT COUNT(*) as completed FROM jobs WHERE status = 'completed'")
                completed_jobs = cursor.fetchone()["completed"]

            return {
                "total_jobs": total_jobs,
                "pending_jobs": pending_jobs,
                "completed_jobs": completed_jobs,
                "scheduler_active": runner.scheduler_running if hasattr(runner, 'scheduler_running') else True
            }
        except Exception as e:
            return {
                "error": str(e),
                "total_jobs": 0,
                "pending_jobs": 0,
                "completed_jobs": 0
            }

    return app


# Инстанс по умолчанию для uvicorn
app = create_app()