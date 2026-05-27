#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF Optimizer Multiprocessing Module
Многопроцессорная обработка PDF файлов
"""

import os
import logging
from pathlib import Path
from typing import List, Tuple, Optional
from multiprocessing import Pool, cpu_count
from functools import partial
from dataclasses import dataclass

from .processor import process_file


@dataclass
class ProcessResult:
    """Результат обработки файла"""
    file_path: Path
    success: bool
    original_size: int = 0
    new_size: int = 0
    error_message: str = ""
    
    @property
    def reduction_percent(self) -> float:
        if self.original_size == 0:
            return 0.0
        return ((self.original_size - self.new_size) / self.original_size) * 100
    
    @property
    def size_mb_original(self) -> float:
        return self.original_size / 1024 / 1024
    
    @property
    def size_mb_new(self) -> float:
        return self.new_size / 1024 / 1024


def _process_single_file(args: Tuple[Path, str, str, Path, bool, bool, str]) -> ProcessResult:
    """
    Обработка одного файла (wrapper для multiprocessing)
    
    Args:
        args: Кортеж параметров (file_path, mode, mupdf_aggression, temp_dir, 
              preserve_signature, no_backup, temp_prefix)
              
    Returns:
        ProcessResult с результатами обработки
    """
    file_path, mode, mupdf_aggression, temp_dir, preserve_signature, no_backup, temp_prefix = args
    
    logger = logging.getLogger(__name__)
    
    try:
        original_size = file_path.stat().st_size
        
        success = process_file(
            file_path=file_path,
            mode=mode,
            mupdf_aggression=mupdf_aggression,
            temp_dir=temp_dir,
            preserve_signature=preserve_signature,
            no_backup=no_backup,
            temp_prefix=temp_prefix
        )
        
        if success:
            new_size = file_path.stat().st_size
            return ProcessResult(
                file_path=file_path,
                success=True,
                original_size=original_size,
                new_size=new_size
            )
        else:
            return ProcessResult(
                file_path=file_path,
                success=False,
                original_size=original_size,
                new_size=0,
                error_message="Processing failed"
            )
            
    except Exception as e:
        logger.error(f"Error processing {file_path.name}: {e}")
        return ProcessResult(
            file_path=file_path,
            success=False,
            original_size=file_path.stat().st_size if file_path.exists() else 0,
            new_size=0,
            error_message=str(e)
        )


class ParallelProcessor:
    """
    Класс для параллельной обработки PDF файлов
    """
    
    def __init__(self, max_workers: Optional[int] = None):
        """
        Инициализация параллельного процессора
        
        Args:
            max_workers: Максимальное количество процессов (по умолчанию = число CPU)
        """
        self.max_workers = max_workers or cpu_count()
        self.logger = logging.getLogger(__name__)
        
    def process_files(self, 
                      files: List[Path],
                      mode: str,
                      mupdf_aggression: str,
                      temp_dir: Path,
                      preserve_signature: bool = False,
                      no_backup: bool = False,
                      temp_prefix: str = "pdf_opt_",
                      progress_callback: Optional[callable] = None) -> List[ProcessResult]:
        """
        Параллельная обработка списка файлов
        
        Args:
            files: Список путей к файлам
            mode: Режим обработки (fast/better/best)
            mupdf_aggression: Уровень сжатия MuPDF
            temp_dir: Директория для временных файлов
            preserve_signature: Сохранять ли электронные подписи
            no_backup: Не создавать бэкапы
            temp_prefix: Префикс временных файлов
            progress_callback: Callback функция для отображения прогресса
            
        Returns:
            Список ProcessResult с результатами обработки
        """
        self.logger.info(f"Запуск параллельной обработки {len(files)} файлов")
        self.logger.info(f"Количество процессов: {self.max_workers}")
        
        # Подготовка аргументов для каждого файла
        # Примечание: каждый процесс будет иметь свой temp_dir
        args_list = [
            (file_path, mode, mupdf_aggression, temp_dir, 
             preserve_signature, no_backup, temp_prefix)
            for file_path in files
        ]
        
        results = []
        
        with Pool(processes=self.max_workers) as pool:
            # Используем imap_unordered для лучшей производительности
            for result in pool.imap_unordered(_process_single_file, args_list, chunksize=4):
                results.append(result)
                
                if progress_callback:
                    progress_callback(result)
        
        return results
    
    def process_files_sequential(self,
                                  files: List[Path],
                                  mode: str,
                                  mupdf_aggression: str,
                                  temp_dir: Path,
                                  preserve_signature: bool = False,
                                  no_backup: bool = False,
                                  temp_prefix: str = "pdf_opt_",
                                  progress_callback: Optional[callable] = None) -> List[ProcessResult]:
        """
        Последовательная обработка файлов (для отладки или когда multiprocessing недоступен)
        
        Args:
            files: Список путей к файлам
            mode: Режим обработки
            mupdf_aggression: Уровень сжатия MuPDF
            temp_dir: Директория для временных файлов
            preserve_signature: Сохранять ли электронные подписи
            no_backup: Не создавать бэкапы
            temp_prefix: Префикс временных файлов
            progress_callback: Callback функция для отображения прогресса
            
        Returns:
            Список ProcessResult с результатами обработки
        """
        self.logger.info(f"Запуск последовательной обработки {len(files)} файлов")
        
        results = []
        
        for file_path in files:
            original_size = file_path.stat().st_size
            
            success = process_file(
                file_path=file_path,
                mode=mode,
                mupdf_aggression=mupdf_aggression,
                temp_dir=temp_dir,
                preserve_signature=preserve_signature,
                no_backup=no_backup,
                temp_prefix=temp_prefix
            )
            
            if success:
                new_size = file_path.stat().st_size
                result = ProcessResult(
                    file_path=file_path,
                    success=True,
                    original_size=original_size,
                    new_size=new_size
                )
            else:
                result = ProcessResult(
                    file_path=file_path,
                    success=False,
                    original_size=original_size,
                    new_size=0,
                    error_message="Processing failed"
                )
            
            results.append(result)
            
            if progress_callback:
                progress_callback(result)
        
        return results


def get_optimal_worker_count() -> int:
    """
    Получение оптимального количества рабочих процессов
    
    Returns:
        Рекомендуемое количество процессов
    """
    cpu_cores = cpu_count()
    
    # Для I/O-bound операций (чтение/запись файлов) можно использовать больше процессов
    # Для CPU-bound операций лучше использовать cpu_count() или меньше
    # Обработка PDF - смешанная операция, поэтому используем cpu_count()
    return cpu_cores
