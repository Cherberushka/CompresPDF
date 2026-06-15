import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from pdf_optimizer.config.settings import settings
from pdf_optimizer.jobs.runner import JobRunner

logger = logging.getLogger("PDFOptimizer.scheduler")

# Используем BackgroundScheduler, так как он отлично работает в одном процессе с FastAPI
scheduler = BackgroundScheduler(timezone="UTC")


def reload_jobs(runner: JobRunner):
    """Очищает текущее расписание и загружает его заново из конфига."""
    scheduler.remove_all_jobs()

    for job_cfg in settings.scheduler.jobs:
        scheduler.add_job(
            func=runner.run_job,
            trigger=CronTrigger.from_crontab(job_cfg.cron),
            args=["scheduler", job_cfg.root_dir, job_cfg.since, job_cfg.quality, job_cfg.aggression],
            id=job_cfg.name,
            name=job_cfg.name,
            max_instances=1,  # Запрещаем запуск той же задачи, если предыдущая еще идет
            coalesce=True,  # Схлопываем пропущенные запуски в один
            replace_existing=True
        )
        logger.info(f"Запланирована задача '{job_cfg.name}': cron='{job_cfg.cron}', since='{job_cfg.since}'")


def start_scheduler(runner: JobRunner):
    """Запуск планировщика при старте приложения."""
    if scheduler.running:
        logger.warning("Планировщик уже запущен.")
        return

    reload_jobs(runner)
    scheduler.start()
    logger.info("APScheduler успешно запущен.")


def stop_scheduler():
    """Корректная остановка при выключении сервиса."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("APScheduler остановлен.")