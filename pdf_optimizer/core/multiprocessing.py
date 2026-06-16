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

from .processor import PDFProcessor, ProcessItem, ProcessResult as ProcessorResult


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


def _process_single_file(args: Tuple[Path, str, str]) -> ProcessResult:
    """
    Обработка одного файла (wrapper для multiprocessing)
    
    Args:
        args: Кортеж параметров (file_path, quality, aggression)
        
    Returns:
        ProcessResult с результатами обработки
    """
    file_path, quality, aggression = args
    
    logger = logging.getLogger(__name__)
    
    try:
        processor = PDFProcessor()
        item = ProcessItem(pdf_path=file_path, quality=quality, aggression=aggression)
        result = processor.process_file(item)
        
        return ProcessResult(
            file_path=result.original_path,
            success=result.success,
            original_size=result.original_size,
            new_size=result.final_size,
            error_message=result.error_message or ""
        )
            
    except Exception as e:
        logger.error(f"Error processing {file_path.name}: {e}")
        original_size = file_path.stat().st_size if file_path.exists() else 0
        return ProcessResult(
            file_path=file_path,
            success=False,
            original_size=original_size,
            new_size=0,
            error_message=str(e)
        )


class ParallelProcessor:
    """
    Класс для параллельной обработки PDF файлов
    """
    
    def __init__(self, max_workers: Optional[int] = None, quality: str = "default", aggression: str = "gg"):
        """
        Инициализация параллельного процессора
        
        Args:
            max_workers: Максимальное количество процессов (по умолчанию = число CPU)
            quality: Качество обработки
            aggression: Уровень агрессии MuPDF
        """
        self.max_workers = max_workers or cpu_count()
        self.quality = quality
        self.aggression = aggression
        self.logger = logging.getLogger(__name__)
        
    def process_files(self, 
                      files: List[Path],
                      quality: Optional[str] = None,
                      aggression: Optional[str] = None) -> List[ProcessResult]:
        """
        Параллельная обработка списка файлов
        
        Args:
            files: Список путей к файлам
            quality: Режим обработки (fast/default/archive/maximum)
            aggression: Уровень сжатия MuPDF (g/gg/ggg/gggg)
            
        Returns:
            Список ProcessResult с результатами обработки
        """
        quality = quality or self.quality
        aggression = aggression or self.aggression
        
        self.logger.info(f"Запуск параллельной обработки {len(files)} файлов")
        self.logger.info(f"Количество процессов: {self.max_workers}")
        
        # Подготовка аргументов для каждого файла
        args_list = [
            (file_path, quality, aggression)
            for file_path in files
        ]
        
        results = []
        
        with Pool(processes=self.max_workers) as pool:
            # Используем imap_unordered для лучшей производительности
            for result in pool.imap_unordered(_process_single_file, args_list, chunksize=4):
                results.append(result)
        
        return results
    
    def process_files_sequential(self,
                                  files: List[Path],
                                  quality: Optional[str] = None,
                                  aggression: Optional[str] = None) -> List[ProcessResult]:
        """
        Последовательная обработка файлов (для отладки или когда multiprocessing недоступен)
        
        Args:
            files: Список путей к файлам
            quality: Режим обработки
            aggression: Уровень сжатия MuPDF
            
        Returns:
            Список ProcessResult с результатами обработки
        """
        quality = quality or self.quality
        aggression = aggression or self.aggression
        
        self.logger.info(f"Запуск последовательной обработки {len(files)} файлов")
        
        processor = PDFProcessor()
        results = []
        
        for file_path in files:
            item = ProcessItem(pdf_path=file_path, quality=quality, aggression=aggression)
            result = processor.process_file(item)
            
            results.append(ProcessResult(
                file_path=result.original_path,
                success=result.success,
                original_size=result.original_size,
                new_size=result.final_size,
                error_message=result.error_message or ""
            ))
        
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
