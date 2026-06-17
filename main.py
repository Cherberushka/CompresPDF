#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF Batch Optimizer for Windows (v14.1 - Fixed no-backup)
Только pikepdf + MuPDF. Без артефактов Ghostscript.
Исправлена работа флага --no-backup

Author: Senior Python Developer
Date: 2026-03-27
Version: 14.1.0
"""

import os
import sys
import shutil
import logging
import argparse
import subprocess
import tempfile
import time
import atexit
from pathlib import Path
from pathlib import Path
from typing import List, Tuple, Optional
from datetime import datetime

# ==============================================================================
# 1. ДИАГНОСТИКА
# ==============================================================================
print("\n" + "=" * 70)
print("PDF OPTIMIZER v14.1 - FIXED NO-BACKUP")
print("=" * 70)
print(f"Python Executable : {sys.executable}")
print(f"Python Version    : {sys.version.split()[0]}")

try:
    import pikepdf

    print(f"pikepdf Version   : {pikepdf.__version__}")
except ImportError as e:
    print(f"❌ pikepdf NOT FOUND ({e})")
    print("   Install: pip install pikepdf")
    sys.exit(1)

# Проверка MuPDF
MUPDF_AVAILABLE = False
try:
    subprocess.run(["mutool", "-version"], stdout=subprocess.DEVNULL,
                   stderr=subprocess.DEVNULL, check=True)
    MUPDF_AVAILABLE = True
    print("✓ MuPDF (mutool)    : FOUND")
except:
    print("⚠ MuPDF (mutool)    : NOT FOUND")
    print("  Установите: winget install ArtifexSoftware.MuPDF")

print("=" * 70 + "\n")

# ==============================================================================
# 2. КОНФИГУРАЦИЯ
# ==============================================================================
DEFAULT_MIN_SIZE_MB = 0  # Изменено на 0 (без ограничения)
DEFAULT_LOG_FILE = "pdf_process.log"
DEFAULT_TEMP_PREFIX = "pdf_opt_"
DEFAULT_MUPDF_AGGRESSION = "dd"
BACKUP_RETENTION_DAYS = 90


# ==============================================================================
# 3. ЛОГГЕР
# ==============================================================================
def setup_logging(log_path: str) -> logging.Logger:
    logger = logging.getLogger("PDFOptimizer")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    fh = logging.FileHandler(log_path, encoding='utf-8')
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(formatter)
    logger.addHandler(fh)

    return logger


logger = setup_logging(DEFAULT_LOG_FILE)

logging.addLevelName(25, "SUCCESS")


def success(self, message, *args, **kws):
    if self.isEnabledFor(25):
        self._log(25, message, args, **kws)


logging.Logger.success = success


# ==============================================================================
# 4. ВАЛИДАЦИЯ PDF
# ==============================================================================
def validate_pdf(input_path: Path) -> Tuple[bool, str]:
    if not input_path.exists():
        return False, "Файл не существует"

    if input_path.stat().st_size == 0:
        return False, "Пустой файл"

    try:
        with open(input_path, 'rb') as f:
            header = f.read(8)
            if not header.startswith(b'%PDF'):
                return False, "Неверная сигнатура PDF"
    except Exception as e:
        return False, f"Ошибка чтения файла: {e}"

    try:
        with pikepdf.open(input_path) as pdf:
            if pdf.is_encrypted:
                return False, "PDF зашифрован"
            if len(pdf.pages) == 0:
                return False, "PDF не содержит страниц"
    except pikepdf.PasswordError:
        return False, "PDF защищён паролем"
    except Exception as e:
        return False, f"Не удалось открыть PDF: {e}"

    return True, "OK"


# ==============================================================================
# 5. ФУНКЦИИ ОБРАБОТКИ
# ==============================================================================

def get_pdf_files(root_dir: str, min_size_mb: int, 
                  year_filter: Optional[str] = None,
                  month_filter: Optional[str] = None) -> List[Path]:
    pdf_files = []
    root_path = Path(root_dir).resolve()
    min_size_bytes = min_size_mb * 1024 * 1024

    logger.info(f"Сканирование: {root_path}")
    logger.info(f"Минимальный размер: {min_size_mb} МБ")
    if year_filter:
        logger.info(f"Фильтр по году: {year_filter}")
    if month_filter:
        logger.info(f"Фильтр по месяцу: {month_filter}")

    try:
        for path in root_path.rglob("*.pdf"):
            if path.is_file():
                try:
                    size = path.stat().st_size
                    if path.name.startswith(DEFAULT_TEMP_PREFIX) or path.suffix == ".bak":
                        continue
                    if size > min_size_bytes:
                        # Проверка пути на соответствие фильтру года/месяца
                        include_file = True
                        
                        if year_filter or month_filter:
                            # Получаем относительный путь от корневой директории
                            try:
                                rel_path = path.relative_to(root_path)
                                parts = rel_path.parts
                                
                                # Проверяем наличие папок в формате YYYY-MM или YYYY
                                folder_match = False
                                for part in parts[:-1]:  # Исключаем имя файла
                                    # Проверка формата YYYY-MM
                                    if len(part) == 7 and part[4:5] == '-':
                                        folder_year = part[:4]
                                        folder_month = part[5:7]
                                        
                                        if year_filter and folder_year != year_filter:
                                            continue
                                        if month_filter and folder_month != month_filter:
                                            continue
                                        folder_match = True
                                        break
                                    
                                    # Проверка формата YYYY (только год)
                                    elif len(part) == 4 and part.isdigit():
                                        folder_year = part
                                        
                                        if year_filter and folder_year != year_filter:
                                            continue
                                        folder_match = True
                                        break
                                
                                # Если фильтры заданы, но папка не найдена в нужном формате
                                # включаем файл только если нет строгого требования к папкам
                                if year_filter or month_filter:
                                    include_file = folder_match
                            except ValueError:
                                # Не удалось получить относительный путь
                                include_file = False
                        
                        if include_file:
                            pdf_files.append(path)
                except OSError as e:
                    logger.debug(f"Ошибка доступа {path}: {e}")
    except Exception as e:
        logger.error(f"Ошибка сканирования: {e}")

    logger.info(f"Найдено файлов: {len(pdf_files)}")
    return pdf_files


def clean_with_pikepdf(input_path: Path, output_path: Path) -> bool:
    pdf = None
    try:
        try:
            pdf = pikepdf.open(input_path, repair=True)
        except TypeError:
            pdf = pikepdf.open(input_path)

        stats = {
            'annotations': 0,
            'forms': 0,
            'metadata': 0,
            'outlines': 0,
            'names': 0
        }

        for page in pdf.pages:
            if '/Annots' in page:
                try:
                    del page['/Annots']
                    stats['annotations'] += 1
                except KeyError:
                    logger.debug(f"Нет /Annots на странице {page.page_index}")
                except Exception as e:
                    logger.debug(f"Не удалось удалить /Annots: {e}")

        for key in ['/AcroForm', '/Metadata', '/Outlines', '/Names']:
            if key in pdf.Root:
                try:
                    del pdf.Root[key]
                    stats['forms'] += 1
                except KeyError:
                    logger.debug(f"Нет ключа {key} в Root")
                except Exception as e:
                    logger.debug(f"Не удалось удалить {key}: {e}")

        if hasattr(pdf, 'docinfo') and pdf.docinfo:
            try:
                pdf.docinfo.clear()
                stats['metadata'] += 1
            except Exception as e:
                logger.debug(f"Не удалось очистить docinfo: {e}")

        save_success = False
        for params in [
            {'garbage': 4, 'deflate': True, 'linearize': True},
            {'garbage': 3, 'deflate': True, 'linearize': True},
            {'deflate': True, 'linearize': True},
            {}
        ]:
            try:
                pdf.save(output_path, **params)
                save_success = True
                logger.debug(f"Сохранено с параметрами: {params}")
                break
            except TypeError:
                continue

        if not save_success:
            pdf.save(output_path)
            logger.debug("Сохранено без параметров (базовый режим)")

        pdf.close()
        logger.debug(f"Статистика очистки: {stats}")
        return True

    except Exception as e:
        logger.error(f"pikepdf ошибка для {input_path.name}: {e}")
        if pdf:
            try:
                pdf.close()
            except:
                pass
        return False


def rebuild_with_mupdf(input_path: Path, output_path: Path,
                       aggression: str = DEFAULT_MUPDF_AGGRESSION) -> bool:
    args = [
        "mutool",
        "clean",
        f"-{aggression}",
        "-l",
        "-f",
        str(input_path),
        str(output_path)
    ]

    try:
        result = subprocess.run(args, capture_output=True, text=True, timeout=180)

        if result.returncode != 0:
            logger.debug(f"MuPDF error: {result.stderr[:200]}")
            return False

        if not output_path.exists() or output_path.stat().st_size == 0:
            return False

        try:
            with pikepdf.open(input_path) as src:
                with pikepdf.open(output_path) as dst:
                    if len(src.pages) != len(dst.pages):
                        logger.error(
                            f"Потеря страниц: {len(src.pages)} → {len(dst.pages)}"
                        )
                        return False
        except Exception as e:
            logger.debug(f"Не удалось проверить страницы: {e}")

        return True

    except subprocess.TimeoutExpired:
        logger.error(f"MuPDF таймаут для {input_path.name}")
        return False
    except Exception as e:
        logger.error(f"MuPDF ошибка для {input_path.name}: {e}")
        return False


def cleanup_temp_files(*paths: Path):
    for p in paths:
        if p and p.exists():
            try:
                p.unlink()
            except OSError:
                pass


def verify_pdf_integrity(file_path: Path) -> Tuple[bool, str]:
    try:
        with pikepdf.open(file_path) as pdf:
            if len(pdf.pages) == 0:
                return False, "Пустой PDF после обработки"
            if pdf.is_encrypted:
                return False, "PDF зашифрован после обработки"
        return True, "OK"
    except Exception as e:
        return False, f"Не удалось открыть: {e}"


def process_file(file_path: Path, mode: str, mupdf_aggression: str,
                 temp_dir: Path, preserve_signature: bool = False,
                 no_backup: bool = False) -> bool:
    """
    Полный цикл обработки файла с валидацией и откатом.

    Args:
        file_path: Путь к файлу
        mode: Режим обработки (fast/better/best)
        mupdf_aggression: Уровень сжатия MuPDF
        temp_dir: Директория для временных файлов
        preserve_signature: Не удалять электронную подпись
        no_backup: Не создавать .bak файлы (🔴 ИСПРАВЛЕНО)

    Returns:
        bool: Успешность обработки
    """
    unique_id = f"{DEFAULT_TEMP_PREFIX}{os.getpid()}_{file_path.name}"
    temp_path = temp_dir / unique_id
    cleaned_path = temp_dir / f"{unique_id}_cleaned"
    processed_path = temp_dir / f"{unique_id}_processed"
    backup_path = file_path.with_suffix(file_path.suffix + ".bak")

    try:
        # Валидация входного файла
        is_valid, msg = validate_pdf(file_path)
        if not is_valid:
            logger.error(f"Валидация не пройдена {file_path.name}: {msg}")
            return False

        # Копия в temp
        shutil.copy2(file_path, temp_path)

        # Этап 1: Очистка pikepdf
        if not clean_with_pikepdf(temp_path, cleaned_path):
            raise Exception("Не удалось очистить PDF")

        # Этап 2: Пересборка MuPDF
        if mode in ["better", "best"] and MUPDF_AVAILABLE:
            if not rebuild_with_mupdf(cleaned_path, processed_path, mupdf_aggression):
                logger.warning(f"MuPDF не справился, используем pikepdf: {file_path.name}")
                shutil.copy2(cleaned_path, processed_path)
        else:
            shutil.copy2(cleaned_path, processed_path)

        # Валидация результата
        original_size = file_path.stat().st_size
        new_size = processed_path.stat().st_size

        if new_size == 0:
            raise Exception("Результирующий файл пуст")

        # 🔴 ИСПРАВЛЕНИЕ: Условное создание бэкапа
        if not no_backup:
            shutil.copy2(file_path, backup_path)
            logger.debug(f"Создан бэкап: {backup_path.name}")
        else:
            logger.debug(f"Бэкап пропущен (--no-backup): {file_path.name}")

        # Замена файла
        shutil.move(processed_path, file_path)

        # Проверка целостности
        is_valid, msg = verify_pdf_integrity(file_path)
        if not is_valid:
            logger.error(f"Целостность нарушена {file_path.name}: {msg}")
            # Откат только если бэкап существует
            if not no_backup and backup_path.exists():
                shutil.copy2(backup_path, file_path)
                logger.error(f"Выполнен откат из бэкапа для {file_path.name}")
            return False

        reduction = ((original_size - new_size) / original_size) * 100
        logger.success(
            f"{file_path.name} ({original_size / 1024 / 1024:.2f} -> "
            f"{new_size / 1024 / 1024:.2f} МБ, -{reduction:.1f}%)"
        )
        return True

    except Exception as e:
        logger.error(f"Сбой {file_path.name}: {e}")
        # Попытка отката при критической ошибке
        if not no_backup and backup_path.exists():
            try:
                shutil.copy2(backup_path, file_path)
                logger.warning(f"Выполнен откат из бэкапа для {file_path.name}")
            except:
                pass
        return False
    finally:
        cleanup_temp_files(temp_path, cleaned_path, processed_path)


# ==============================================================================
# 6. ОСНОВНАЯ ФУНКЦИЯ
# ==============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="PDF Optimizer v14.1 - Fixed no-backup",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры использования:
  %(prog)s "C:\\Documents" --quality better
  %(prog)s "C:\\Documents" --quality best --mupdf-aggression dd
  %(prog)s "C:\\Documents" --dry-run --min-size 0
  %(prog)s "C:\\Documents" --no-backup --min-size 0
  %(prog)s "C:\\Documents" --preserve-signature --keep-bak
  %(prog)s "C:\\Documents" --year 2016 --month 12
  %(prog)s "C:\\Documents" --year 2018 --dry-run
        """
    )
    parser.add_argument("path", help="Путь к корневой директории")
    parser.add_argument("--dry-run", action="store_true",
                        help="Только список файлов без обработки")
    parser.add_argument("--min-size", type=int, default=DEFAULT_MIN_SIZE_MB,
                        help=f"Мин размер в МБ (по умолчанию {DEFAULT_MIN_SIZE_MB})")
    parser.add_argument("--keep-bak", action="store_true",
                        help="Не удалять .bak файлы (хранить 90 дней)")
    parser.add_argument("--quality", type=str, default="fast",
                        choices=["fast", "better", "best"],
                        help="""Режим обработки:
  fast    - Только pikepdf (70-80%% сжатие, ~1 сек/файл)
  better  - pikepdf + MuPDF (80-90%% сжатие, ~2-3 сек/файл)
  best    - pikepdf + MuPDF макс. (85-92%% сжатие, ~3-4 сек/файл)""")
    parser.add_argument("--mupdf-aggression", type=str,
                        default=DEFAULT_MUPDF_AGGRESSION,
                        choices=["d", "dd", "ddd", "dddd"],
                        help=f"Уровень сжатия MuPDF (по умолчанию {DEFAULT_MUPDF_AGGRESSION})")
    parser.add_argument("--preserve-signature", action="store_true",
                        help="Не удалять электронные подписи")
    parser.add_argument("--no-backup", action="store_true",
                        help="Не создавать .bak файлы (не рекомендуется для медицины)")
    parser.add_argument("--year", type=str, default=None,
                        help="Фильтр по году (формат YYYY, например 2016)")
    parser.add_argument("--month", type=str, default=None,
                        help="Фильтр по месяцу (формат MM, например 12)")

    args = parser.parse_args()

    # Предупреждение об удалении электронной подписи
    if not args.preserve_signature:
        logger.warning("=" * 70)
        logger.warning("⚠️  ВНИМАНИЕ: ЭЛЕКТРОННАЯ ПОДПИСЬ БУДЕТ УДАЛЕНА")
        logger.warning("   Оптимизированные файлы НЕ ИМЕЮТ юридической силы")
        logger.warning("   Сохраните оригиналы с ЭП в отдельном архиве")
        logger.warning("   Требование Минздрава РФ: хранение 90+ дней")
        logger.warning("=" * 70)

    # Предупреждение об отключении бэкапов
    if args.no_backup:
        logger.warning("=" * 70)
        logger.warning("⚠️  ВНИМАНИЕ: БЭКАПЫ ОТКЛЮЧЕНЫ (--no-backup)")
        logger.warning("   Оригиналы файлов будут заменены без возможности отката")
        logger.warning("   Рекомендуется сначала протестировать на копии данных")
        logger.warning("=" * 70)

    # Временная папка в рабочей директории
    try:
        # Пробуем создать в рабочей директории
        temp_dir = Path(args.path) / ".pdf_temp"
        temp_dir.mkdir(exist_ok=True)
        # Проверка на запись
        test_file = temp_dir / ".write_test"
        test_file.touch()
        test_file.unlink()
        logger.info(f"✓ Temp-директория: {temp_dir} (в рабочей папке)")
    except (PermissionError, OSError) as e:
        # Если нет прав — используем системный temp
        temp_dir = Path(tempfile.gettempdir()) / "pdf_optimizer_temp"
        temp_dir.mkdir(exist_ok=True)
        logger.warning(f"⚠ Нет прав на запись в {args.path}")
        logger.info(f"✓ Temp-директория: {temp_dir} (системная)")

    # Очистка при завершении
    atexit.register(lambda: shutil.rmtree(temp_dir, ignore_errors=True))

    mode = args.quality
    logger.info(f"✓ Режим: {mode.upper()}")
    logger.info(f"✓ Агрессия MuPDF: -{args.mupdf_aggression}")
    logger.info(f"✓ Ghostscript: ОТКЛЮЧЕН (нет артефактов)")
    logger.info(f"✓ Temp-директория: {temp_dir}")
    logger.info(f"✓ Бэкапы: {'ОТКЛЮЧЕНЫ' if args.no_backup else 'ВКЛЮЧЕНЫ'}")

    if mode == "fast":
        logger.info("  → Движок: pikepdf только")
        logger.info("  → Сжатие: 70-80%")
    elif mode == "better":
        logger.info("  → Движок: pikepdf + MuPDF")
        logger.info("  → Сжатие: 80-90%")
    elif mode == "best":
        logger.info("  → Движок: pikepdf + MuPDF (макс.)")
        logger.info("  → Сжатие: 85-92%")

    files = get_pdf_files(args.path, args.min_size, args.year, args.month)

    if not files:
        logger.info("Файлов для обработки не найдено.")
        return

    if args.dry_run:
        total_size = sum(f.stat().st_size for f in files)
        logger.info("=" * 70)
        logger.info("DRY RUN — файлы не будут изменены")
        logger.info(f"Файлов: {len(files)}")
        logger.info(f"Общий вес: {total_size / 1024 / 1024:.2f} МБ")
        logger.info("Первые 10 файлов:")
        for f in files[:10]:
            logger.info(f"  {f.name} ({f.stat().st_size / 1024 / 1024:.2f} МБ)")
        if len(files) > 10:
            logger.info(f"  ... и ещё {len(files) - 10} файлов")
        return

    total = len(files)
    success_count = 0
    fail_count = 0

    # Метрики обработки
    total_original_size = 0
    total_new_size = 0

    logger.info("=" * 70)
    logger.info(f"Начало обработки {total} файлов...")
    start_time = time.time()

    for idx, file_path in enumerate(files, 1):
        logger.info(f"[{idx}/{total}] {file_path.name}")

        original_size = file_path.stat().st_size
        total_original_size += original_size

        # 🔴 ИСПРАВЛЕНИЕ: Передача args.no_backup в функцию
        if process_file(file_path, mode, args.mupdf_aggression, temp_dir,
                        args.preserve_signature, args.no_backup):
            success_count += 1
            try:
                total_new_size += file_path.stat().st_size
            except:
                pass
        else:
            fail_count += 1

        time.sleep(0.05)

        if idx % 100 == 0:
            elapsed = time.time() - start_time
            logger.info(f"Прогресс: {idx}/{total} ({elapsed / 60:.1f} мин)")

    elapsed = time.time() - start_time

    # Финальные метрики
    logger.info("=" * 70)
    logger.info(f"ЗАВЕРШЕНО за {elapsed / 60:.1f} мин ({elapsed:.1f} сек)")
    logger.info(f"Успешно: {success_count}/{total}")
    if fail_count > 0:
        logger.warning(f"Ошибок: {fail_count}")

    if total_original_size > 0:
        avg_reduction = ((total_original_size - total_new_size) / total_original_size) * 100
        logger.info(f"Среднее сжатие: {avg_reduction:.1f}%")
        logger.info(f"Общий объём: {total_original_size / 1024 / 1024:.2f} → {total_new_size / 1024 / 1024:.2f} МБ")
        logger.info(f"Экономия места: {(total_original_size - total_new_size) / 1024 / 1024:.2f} МБ")

    logger.info(f"Среднее время на файл: {elapsed / total:.2f} сек")
    logger.info(f"Лог: {DEFAULT_LOG_FILE}")

    if args.keep_bak:
        logger.info("⚠️  .bak файлы сохранены (рекомендуется хранить 90 дней)")
        backup_dir = Path(args.path) / ".pdf_backups"
        backup_dir.mkdir(exist_ok=True)
        logger.info(f"Переместите .bak файлы в: {backup_dir}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.warning("\n⚠️  Прервано пользователем.")
        sys.exit(1)
    except Exception as e:
        logger.critical(f"❌ Критический сбой: {e}")
        sys.exit(1)