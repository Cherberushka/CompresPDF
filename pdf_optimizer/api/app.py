import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI

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

    # 3. Запуск планировщика
    start_scheduler(runner)

    yield  # Приложение работает...

    # 4. Graceful Shutdown
    logger.info("Завершение работы сервиса...")
    stop_scheduler()


def create_app() -> FastAPI:
    """Фабрика для создания инстанса FastAPI."""
    app = FastAPI(
        title="PDF Batch Optimizer Service",
        version="15.1.0",
        description="Фоновый сервис пакетного сжатия PDF с идемпотентностью и расписанием",
        lifespan=lifespan
    )

    app.include_router(router, prefix="/api")

    return app


# Инстанс по умолчанию для uvicorn
app = create_app()