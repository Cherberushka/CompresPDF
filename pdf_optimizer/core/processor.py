import os
import shutil
import subprocess
import logging
from pathlib import Path
from typing import List, Optional
from dataclasses import dataclass
import pikepdf

# fcntl доступен только на Unix-системах (Ubuntu)
# Оборачиваем в try-except на случай локального запуска на Windows
try:
    import fcntl
except ImportError:
    fcntl = None

from pdf_optimizer.config.settings import settings

logger = logging.getLogger("PDFOptimizer.processor")


@dataclass
class ProcessItem:
    """Объект, описывающий задачу на сжатие одного файла."""
    pdf_path: Path
    quality: str = "default"
    aggression: str = "gg"


@dataclass
class ProcessResult:
    """Результат обработки одного файла для оркестратора."""
    success: bool
    original_path: Path
    original_size: int
    final_size: int
    error_message: Optional[str] = None


def get_pdf_files(root_dir: Path) -> List[Path]:
    """
    Рекурсивно ищет все PDF файлы в директории.
    (Временная фильтрация теперь делегирована модулю filtering.py)
    """
    return list(root_dir.rglob("*.pdf"))


class PDFProcessor:
    """
    Класс для обработки одиночного PDF-файла.
    Пайплайн: Ghostscript -> pikepdf -> MuPDF
    """

    def __init__(self):
        self.logger = logging.getLogger("PDFOptimizer.processor.PDFProcessor")
        self.gs_path = settings.ghostscript_path
        self.mutool_path = settings.mutool_path

    def _replace_file_safely(self, temp_pdf: Path, target_pdf: Path):
        """Атомарная замена файла с использованием fcntl.flock для защиты от гонок (Фаза 5)."""
        if fcntl:
            try:
                # Открываем целевой файл для установки эксклюзивной блокировки ОС
                with open(target_pdf, 'a') as f:
                    fcntl.flock(f, fcntl.LOCK_EX)
                    try:
                        # os.replace гарантирует атомарность на уровне ФС (POSIX)
                        # Если процесс убьют прямо сейчас, файл не повредится
                        os.replace(temp_pdf, target_pdf)
                    finally:
                        fcntl.flock(f, fcntl.LOCK_UN)
            except OSError as e:
                self.logger.error(f"Ошибка при атомарной записи {target_pdf}: {e}")
                raise
        else:
            # Fallback для разработки на Windows
            os.replace(temp_pdf, target_pdf)

    def _get_gs_quality_param(self, quality: str) -> str:
        """Отображение уровня качества на пресеты Ghostscript."""
        mapping = {
            "fast": "/screen",  # Низкое разрешение (72 dpi)
            "default": "/ebook",  # Среднее качество (150 dpi)
            "archive": "/printer",  # Высокое качество (300 dpi)
            "maximum": "/prepress"  # Максимальное качество (сохранение цветов)
        }
        return mapping.get(quality, "/ebook")

    def process_file(self, item: ProcessItem) -> ProcessResult:
        """
        Основной метод обработки одного файла.
        Выполняет цепочку преобразований и безопасно заменяет оригинал в случае успеха.
        """
        original_size = 0
        final_size = 0

        if not item.pdf_path.exists():
            return ProcessResult(False, item.pdf_path, 0, 0, "Файл не существует")

        original_size = item.pdf_path.stat().st_size

        # Определяем временные пути
        temp_dir = item.pdf_path.parent
        pid = os.getpid()
        gs_temp = temp_dir / f".~gs_{pid}_{item.pdf_path.name}"
        pike_temp = temp_dir / f".~pike_{pid}_{item.pdf_path.name}"
        mu_temp = temp_dir / f".~mu_{pid}_{item.pdf_path.name}"
        backup_path = temp_dir / f"{item.pdf_path.name}.bak"

        try:
            self.logger.debug(f"Начало обработки: {item.pdf_path.name} (Качество: {item.quality})")

            # ШАГ 1: Ghostscript (Исправление структуры и сжатие изображений)
            gs_cmd = [
                self.gs_path,
                "-sDEVICE=pdfwrite",
                "-dCompatibilityLevel=1.4",
                f"-dPDFSETTINGS={self._get_gs_quality_param(item.quality)}",
                "-dNOPAUSE",
                "-dQUIET",
                "-dBATCH",
                f"-sOutputFile={str(gs_temp)}",
                str(item.pdf_path)
            ]
            subprocess.run(gs_cmd, check=True, capture_output=True)

            # ШАГ 2: pikepdf (Очистка метаданных, сборка мусора, линеаризация)
            with pikepdf.open(str(gs_temp)) as pdf:
                pdf.save(
                    str(pike_temp),
                    linearize=True,
                    object_stream_mode=pikepdf.ObjectStreamMode.generate
                )

            # ШАГ 3: MuPDF mutool clean (Глубокая пересборка и финальная оптимизация)
            # Используем исправленную агрессию (g/gg/ggg/gggg)
            mu_cmd = [
                self.mutool_path,
                "clean",
                f"-{item.aggression}",
                str(pike_temp),
                str(mu_temp)
            ]
            subprocess.run(mu_cmd, check=True, capture_output=True)

            # Проверка результата
            if not mu_temp.exists() or mu_temp.stat().st_size == 0:
                raise ValueError("Сгенерирован пустой или поврежденный файл")

            final_size = mu_temp.stat().st_size

            # Если сжать удалось
            if final_size < original_size:
                # 1. Опционально создаем бэкап
                if not settings.no_backup:
                    shutil.copy2(str(item.pdf_path), str(backup_path))

                # 2. Атомарно заменяем оригинал новым сжатым файлом
                self._replace_file_safely(mu_temp, item.pdf_path)

                self.logger.info(
                    f"Успешно: {item.pdf_path.name} "
                    f"({original_size / 1024 / 1024:.2f}MB -> {final_size / 1024 / 1024:.2f}MB)"
                )
                return ProcessResult(True, item.pdf_path, original_size, final_size)
            else:
                self.logger.info(f"Пропущено (файл не стал меньше): {item.pdf_path.name}")
                return ProcessResult(True, item.pdf_path, original_size, original_size)

        except subprocess.CalledProcessError as e:
            err_msg = f"Ошибка subprocess: {e.stderr.decode('utf-8', errors='ignore')}"
            self.logger.error(f"{err_msg} при обработке {item.pdf_path}")
            return ProcessResult(False, item.pdf_path, original_size, 0, err_msg)

        except Exception as e:  # Устранен опасный bare except (Фаза 0)
            err_msg = str(e)
            self.logger.error(f"Произошла непредвиденная ошибка при обработке {item.pdf_path}: {err_msg}")

            # Если был сбой и бэкап уже создан, но оригинальный файл поврежден - восстанавливаем
            if backup_path.exists() and item.pdf_path.exists() and item.pdf_path.stat().st_size == 0:
                shutil.move(str(backup_path), str(item.pdf_path))

            return ProcessResult(False, item.pdf_path, original_size, 0, err_msg)

        finally:
            # Гарантированная очистка временных файлов (Фаза 0)
            for temp_file in [gs_temp, pike_temp, mu_temp]:
                try:
                    if temp_file.exists():
                        temp_file.unlink()
                except OSError:
                    pass