#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF Optimizer Configuration Module
Управление конфигурацией приложения
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, List
import json


@dataclass
class ProcessingConfig:
    """Конфигурация обработки PDF файлов"""
    quality: str = "fast"  # fast, better, best
    mupdf_aggression: str = "dd"  # d, dd, ddd, dddd
    min_size_mb: int = 0
    preserve_signature: bool = False
    no_backup: bool = False
    keep_bak: bool = False


@dataclass
class PathsConfig:
    """Конфигурация путей"""
    root_dir: str = ""
    temp_dir: Optional[Path] = None
    log_file: str = "pdf_process.log"
    backup_retention_days: int = 90


@dataclass
class DisplayConfig:
    """Конфигурация отображения"""
    verbose: bool = True
    show_progress: bool = True
    use_colors: bool = True
    dry_run: bool = False


@dataclass
class AppSettings:
    """Основные настройки приложения"""
    processing: ProcessingConfig = field(default_factory=ProcessingConfig)
    paths: PathsConfig = field(default_factory=PathsConfig)
    display: DisplayConfig = field(default_factory=DisplayConfig)
    
    # Константы
    DEFAULT_TEMP_PREFIX: str = "pdf_opt_"
    VERSION: str = "15.0.0"
    APP_NAME: str = "PDF Batch Optimizer"


class ConfigManager:
    """Менеджер конфигурации приложения"""
    
    def __init__(self, config_file: Optional[Path] = None):
        self.config_file = config_file
        self.settings = AppSettings()
        
    def load_from_file(self, path: Path) -> AppSettings:
        """Загрузка конфигурации из JSON файла"""
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {path}")
        
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if 'processing' in data:
            proc = data['processing']
            self.settings.processing = ProcessingConfig(
                quality=proc.get('quality', 'fast'),
                mupdf_aggression=proc.get('mupdf_aggression', 'dd'),
                min_size_mb=proc.get('min_size_mb', 0),
                preserve_signature=proc.get('preserve_signature', False),
                no_backup=proc.get('no_backup', False),
                keep_bak=proc.get('keep_bak', False)
            )
        
        if 'paths' in data:
            paths = data['paths']
            self.settings.paths = PathsConfig(
                root_dir=paths.get('root_dir', ''),
                temp_dir=Path(paths['temp_dir']) if paths.get('temp_dir') else None,
                log_file=paths.get('log_file', 'pdf_process.log'),
                backup_retention_days=paths.get('backup_retention_days', 90)
            )
        
        if 'display' in data:
            disp = data['display']
            self.settings.display = DisplayConfig(
                verbose=disp.get('verbose', True),
                show_progress=disp.get('show_progress', True),
                use_colors=disp.get('use_colors', True),
                dry_run=disp.get('dry_run', False)
            )
        
        return self.settings
    
    def save_to_file(self, path: Path) -> None:
        """Сохранение конфигурации в JSON файл"""
        data = {
            'processing': {
                'quality': self.settings.processing.quality,
                'mupdf_aggression': self.settings.processing.mupdf_aggression,
                'min_size_mb': self.settings.processing.min_size_mb,
                'preserve_signature': self.settings.processing.preserve_signature,
                'no_backup': self.settings.processing.no_backup,
                'keep_bak': self.settings.processing.keep_bak
            },
            'paths': {
                'root_dir': self.settings.paths.root_dir,
                'temp_dir': str(self.settings.paths.temp_dir) if self.settings.paths.temp_dir else None,
                'log_file': self.settings.paths.log_file,
                'backup_retention_days': self.settings.paths.backup_retention_days
            },
            'display': {
                'verbose': self.settings.display.verbose,
                'show_progress': self.settings.display.show_progress,
                'use_colors': self.settings.display.use_colors,
                'dry_run': self.settings.display.dry_run
            }
        }
        
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def create_default_config(self, path: Path) -> None:
        """Создание файла конфигурации по умолчанию"""
        self.save_to_file(path)
    
    @staticmethod
    def validate_quality(value: str) -> bool:
        """Валидация режима качества"""
        return value in ['fast', 'better', 'best']
    
    @staticmethod
    def validate_aggression(value: str) -> bool:
        """Валидация уровня агрессии MuPDF"""
        return value in ['d', 'dd', 'ddd', 'dddd']


# Глобальный экземпляр для быстрого доступа
config_manager = ConfigManager()
