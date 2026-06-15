import logging
import threading
from pathlib import Path

from pdf_optimizer.core.filtering import filter_by_mtime
from pdf_optimizer.registry.store import RegistryStore
from pdf_optimizer.config.settings import settings

# Предполагается, что эти функции есть в вашем core-модуле
from pdf_optimizer.core.processor import get_pdf_files
from pdf_optimizer.core.multiprocessing import ParallelProcessor

logger = logging.getLogger("PDFOptimizer.runner")

# Глобальная блокировка защищает от гонок, если планировщик (cron)
# попытается запустить новую задачу, пока старая еще не завершила тяжелую работу
_job_lock = threading.Lock()


class JobRunner:
    def __init__(self, registry: RegistryStore):
        self.registry = registry

    def run_job(self, source: str, root_dir: str, since: str, quality: str, aggression: str):
        """
        Главный пайплайн обработки. Вызывается из API или Планировщика.
        """
        logger.info(f"Начало задачи (source={source}, dir={root_dir}, since={since})")

        # Не даем запустить параллельно две задачи на одном инстансе для защиты I/O
        if not _job_lock.acquire(blocking=False):
            logger.warning(f"Задача для {root_dir} уже выполняется. Пропуск триггера.")
            return

        try:
            # 1. Регистрация намерения в БД
            params = {"since": since, "quality": quality, "aggression": aggression}
            job_id = self.registry.create_job(source, root_dir, params)

            # 2. Сканирование ФС
            root_path = Path(root_dir)
            if not root_path.exists():
                logger.error(f"Директория {root_dir} не существует")
                self.registry.finish_job(job_id, "failed", 0, 0)
                return

            all_files = get_pdf_files(root_path)

            # 3. Фильтрация по времени (Фаза 2)
            recent_files = filter_by_mtime(all_files, since)

            # 4. Исключение уже сжатых файлов (Фаза 3 - Идемпотентность)
            files_to_process = self.registry.exclude_already_processed(recent_files)

            if not files_to_process:
                logger.info("Нет новых файлов для обработки.")
                self.registry.finish_job(job_id, "succeeded", 0, 0)
                return

            # 5. Запуск пула процессов
            logger.info(f"Файлов к обработке: {len(files_to_process)}")
            processor = ParallelProcessor(quality=quality, aggression=aggression)

            # Ожидаем, что process_files возвращает объекты с результатами
            results = processor.process_files(files_to_process)

            # 6. Фиксация результатов аудита
            files_processed = 0
            bytes_saved = 0

            for res in results:
                # Предполагаем, что res имеет атрибуты: success, original_path, original_size, final_size
                if getattr(res, 'success', False):
                    self.registry.record_results(
                        job_id=job_id,
                        file_path=res.original_path,
                        current_mtime=res.original_path.stat().st_mtime,
                        size_before=res.original_size,
                        size_after=res.final_size
                    )
                    files_processed += 1
                    bytes_saved += (res.original_size - res.final_size)

            # 7. Финализация статуса задачи
            status = "succeeded" if files_processed == len(files_to_process) else "partial"
            self.registry.finish_job(job_id, status, files_processed, bytes_saved)
            logger.info(f"Задача {job_id} завершена. Сэкономлено: {bytes_saved / 1024 / 1024:.2f} MB")

        except Exception as e:
            logger.exception(f"Критическая ошибка в пайплайне задачи: {e}")
            if 'job_id' in locals():
                self.registry.finish_job(job_id, "failed", 0, 0)
        finally:
            _job_lock.release()