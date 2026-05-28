#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF Optimizer Utils Module
Вспомогательные утилиты
"""

import logging
import shutil
from pathlib import Path
from datetime import datetime, timedelta
from typing import List


def setup_logging(log_path: str, verbose: bool = False) -> logging.Logger:
    """
    Настройка логгера
    
    Args:
        log_path: Путь к файлу лога
        verbose: Включить debug уровень
        
    Returns:
        Настроенный logger
    """
    logger = logging.getLogger("PDFOptimizer")
    logger.setLevel(logging.DEBUG if verbose else logging.INFO)
    logger.handlers.clear()
    
    formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Console handler
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG if verbose else logging.INFO)
    ch.setFormatter(formatter)
    logger.addHandler(ch)
    
    # File handler
    fh = logging.FileHandler(log_path, encoding='utf-8')
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(formatter)
    logger.addHandler(fh)
    
    return logger


def add_success_level():
    """Добавление уровня SUCCESS в logging"""
    logging.addLevelName(25, "SUCCESS")
    
    def success(self, message, *args, **kws):
        if self.isEnabledFor(25):
            self._log(25, message, args, **kws)
    
    logging.Logger.success = success


def cleanup_old_backups(backup_dir: Path, retention_days: int = 90) -> int:
    """
    Очистка старых бэкапов
    
    Args:
        backup_dir: Директория с бэкапами
        retention_days: Количество дней хранения
        
    Returns:
        Количество удалённых файлов
    """
    if not backup_dir.exists():
        return 0
    
    cutoff_date = datetime.now() - timedelta(days=retention_days)
    removed_count = 0
    
    for file_path in backup_dir.glob("*.bak"):
        try:
            file_time = datetime.fromtimestamp(file_path.stat().st_mtime)
            if file_time < cutoff_date:
                file_path.unlink()
                removed_count += 1
        except (OSError, ValueError):
            continue
    
    return removed_count


def create_backup_directory(root_path: Path) -> Path:
    """
    Создание директории для бэкапов
    
    Args:
        root_path: Корневая директория
        
    Returns:
        Путь к директории бэкапов
    """
    backup_dir = root_path / ".pdf_backups"
    backup_dir.mkdir(exist_ok=True)
    return backup_dir


def move_backups_to_archive(backup_files: List[Path], archive_dir: Path) -> int:
    """
    Перемещение бэкап файлов в архив
    
    Args:
        backup_files: Список файлов бэкапов
        archive_dir: Директория архива
        
    Returns:
        Количество перемещённых файлов
    """
    archive_dir.mkdir(exist_ok=True)
    moved_count = 0
    
    for backup_file in backup_files:
        if backup_file.exists():
            try:
                dest = archive_dir / backup_file.name
                shutil.move(str(backup_file), str(dest))
                moved_count += 1
            except (OSError, shutil.Error):
                continue
    
    return moved_count


def get_temp_dir(root_path: Path, use_system: bool = False) -> Path:
    """
    Получение директории для временных файлов
    
    Args:
        root_path: Корневая директория
        use_system: Использовать системную temp директорию
        
    Returns:
        Путь к temp директории
    """
    if use_system:
        import tempfile
        temp_dir = Path(tempfile.gettempdir()) / "pdf_optimizer_temp"
    else:
        temp_dir = root_path / ".pdf_temp"
    
    temp_dir.mkdir(exist_ok=True)
    return temp_dir


def format_size(size_bytes: int) -> str:
    """
    Форматирование размера файла в человекочитаемый вид
    
    Args:
        size_bytes: Размер в байтах
        
    Returns:
        Строка с размером (KB, MB, GB)
    """
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} TB"


def estimate_processing_time(file_count: int, mode: str) -> str:
    """
    Оценка времени обработки
    
    Args:
        file_count: Количество файлов
        mode: Режим обработки
        
    Returns:
        Строка с оценкой времени
    """
    time_per_file = {
        'fast': 1.0,
        'better': 2.5,
        'best': 3.5
    }
    
    seconds = file_count * time_per_file.get(mode, 1.0)
    
    if seconds < 60:
        return f"~{seconds:.0f} сек"
    elif seconds < 3600:
        return f"~{seconds/60:.1f} мин"
    else:
        return f"~{seconds/3600:.1f} ч"
