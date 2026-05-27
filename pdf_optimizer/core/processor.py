#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF Optimizer Core Module
Основные функции обработки PDF файлов
"""

import os
import shutil
import logging
import subprocess
from pathlib import Path
from typing import Tuple, List, Optional
from enum import Enum

import pikepdf

from ..config.settings import AppSettings


class ProcessingMode(Enum):
    """Режимы обработки PDF"""
    FAST = "fast"
    BETTER = "better"
    BEST = "best"


class ValidationResult:
    """Результат валидации PDF файла"""
    
    def __init__(self, is_valid: bool, message: str, error: Optional[Exception] = None):
        self.is_valid = is_valid
        self.message = message
        self.error = error
    
    def __bool__(self) -> bool:
        return self.is_valid
    
    def __str__(self) -> str:
        return f"Valid: {self.is_valid}, Message: {self.message}"


def validate_pdf(input_path: Path) -> ValidationResult:
    """
    Валидация PDF файла
    
    Args:
        input_path: Путь к файлу
        
    Returns:
        ValidationResult с информацией о валидности
    """
    if not input_path.exists():
        return ValidationResult(False, "Файл не существует")
    
    if input_path.stat().st_size == 0:
        return ValidationResult(False, "Пустой файл")
    
    try:
        with open(input_path, 'rb') as f:
            header = f.read(8)
            if not header.startswith(b'%PDF'):
                return ValidationResult(False, "Неверная сигнатура PDF")
    except Exception as e:
        return ValidationResult(False, f"Ошибка чтения файла: {e}", e)
    
    try:
        with pikepdf.open(input_path) as pdf:
            if pdf.is_encrypted:
                return ValidationResult(False, "PDF зашифрован")
            if len(pdf.pages) == 0:
                return ValidationResult(False, "PDF не содержит страниц")
    except pikepdf.PasswordError:
        return ValidationResult(False, "PDF защищён паролем")
    except Exception as e:
        return ValidationResult(False, f"Не удалось открыть PDF: {e}", e)
    
    return ValidationResult(True, "OK")


def get_pdf_files(root_dir: str, min_size_mb: int, 
                  temp_prefix: str = "pdf_opt_") -> List[Path]:
    """
    Поиск PDF файлов в директории
    
    Args:
        root_dir: Корневая директория для поиска
        min_size_mb: Минимальный размер файла в МБ
        temp_prefix: Префикс временных файлов для исключения
        
    Returns:
        Список путей к PDF файлам
    """
    pdf_files = []
    root_path = Path(root_dir).resolve()
    min_size_bytes = min_size_mb * 1024 * 1024
    
    logger = logging.getLogger(__name__)
    logger.info(f"Сканирование: {root_path}")
    logger.info(f"Минимальный размер: {min_size_mb} МБ")
    
    try:
        for path in root_path.rglob("*.pdf"):
            if path.is_file():
                try:
                    size = path.stat().st_size
                    # Исключаем временные файлы по префиксу И по директории .pdf_temp
                    if (path.name.startswith(temp_prefix) or 
                        path.suffix == ".bak" or
                        '.pdf_temp' in path.parts):
                        continue
                    if size > min_size_bytes:
                        pdf_files.append(path)
                except OSError as e:
                    logger.debug(f"Ошибка доступа {path}: {e}")
    except Exception as e:
        logger.error(f"Ошибка сканирования: {e}")
    
    logger.info(f"Найдено файлов: {len(pdf_files)}")
    return pdf_files


def clean_with_pikepdf(input_path: Path, output_path: Path,
                       preserve_signature: bool = False) -> bool:
    """
    Очистка PDF с помощью pikepdf
    
    Args:
        input_path: Входной файл
        output_path: Выходной файл
        preserve_signature: Сохранять ли электронные подписи
        
    Returns:
        True если успешно
    """
    pdf = None
    logger = logging.getLogger(__name__)
    
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
        
        # Не удаляем подписи если включен режим сохранения
        if not preserve_signature:
            for page in pdf.pages:
                if '/Annots' in page:
                    try:
                        del page['/Annots']
                        stats['annotations'] += 1
                    except (KeyError, Exception) as e:
                        logger.debug(f"Не удалось удалить /Annots: {e}")
            
            for key in ['/AcroForm', '/Metadata', '/Outlines', '/Names']:
                if key in pdf.Root:
                    try:
                        del pdf.Root[key]
                        stats['forms'] += 1
                    except (KeyError, Exception) as e:
                        logger.debug(f"Не удалось удалить {key}: {e}")
        
        if hasattr(pdf, 'docinfo') and pdf.docinfo and not preserve_signature:
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
                       aggression: str = "dd") -> bool:
    """
    Пересборка PDF с помощью MuPDF
    
    Args:
        input_path: Входной файл
        output_path: Выходной файл
        aggression: Уровень агрессии сжатия
        
    Returns:
        True если успешно
    """
    args = [
        "mutool",
        "clean",
        f"-{aggression}",
        "-l",
        "-f",
        str(input_path),
        str(output_path)
    ]
    
    logger = logging.getLogger(__name__)
    
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


def cleanup_temp_files(*paths: Path) -> None:
    """Очистка временных файлов"""
    for p in paths:
        if p and p.exists():
            try:
                p.unlink()
            except OSError:
                pass


def verify_pdf_integrity(file_path: Path) -> Tuple[bool, str]:
    """
    Проверка целостности PDF после обработки
    
    Args:
        file_path: Путь к файлу
        
    Returns:
        Кортеж (успешность, сообщение)
    """
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
                 no_backup: bool = False, temp_prefix: str = "pdf_opt_",
                 keep_bak: bool = False) -> bool:
    """
    Полный цикл обработки файла с валидацией и откатом
    
    Args:
        file_path: Путь к файлу
        mode: Режим обработки (fast/better/best)
        mupdf_aggression: Уровень сжатия MuPDF
        temp_dir: Директория для временных файлов
        preserve_signature: Не удалять электронную подпись
        no_backup: Не создавать .bak файлы
        temp_prefix: Префикс временных файлов
        keep_bak: Сохранять ли .bak файлы после обработки
        
    Returns:
        bool: Успешность обработки
    """
    logger = logging.getLogger(__name__)
    unique_id = f"{temp_prefix}{os.getpid()}_{file_path.name}"
    temp_path = temp_dir / unique_id
    cleaned_path = temp_dir / f"{unique_id}_cleaned"
    processed_path = temp_dir / f"{unique_id}_processed"
    backup_path = file_path.with_suffix(file_path.suffix + ".bak")
    
    try:
        # Валидация входного файла
        validation = validate_pdf(file_path)
        if not validation:
            logger.error(f"Валидация не пройдена {file_path.name}: {validation.message}")
            return False
        
        # Копия в temp
        shutil.copy2(file_path, temp_path)
        
        # Этап 1: Очистка pikepdf
        if not clean_with_pikepdf(temp_path, cleaned_path, preserve_signature):
            raise Exception("Не удалось очистить PDF")
        
        # Этап 2: Пересборка MuPDF
        if mode in ["better", "best"]:
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
        
        # Создание бэкапа (условное)
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
        logger.info(
            f"✓ {file_path.name} ({original_size / 1024 / 1024:.2f} -> "
            f"{new_size / 1024 / 1024:.2f} МБ, -{reduction:.1f}%)"
        )
        
        # Удаление бэкапа если не нужно сохранять
        if not keep_bak and not no_backup and backup_path.exists():
            try:
                backup_path.unlink()
                logger.debug(f"Удалён бэкап: {backup_path.name}")
            except OSError as e:
                logger.warning(f"Не удалось удалить бэкап {backup_path.name}: {e}")
        
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
