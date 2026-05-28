"""
PDF Batch Optimizer v15.0 - Multiprocessing Edition
Модульная версия с многопроцессорной обработкой

Author: Senior Python Developer
Date: 2026-03-27
Version: 15.0.0
"""

from .config.settings import (
    ProcessingConfig,
    PathsConfig,
    DisplayConfig,
    AppSettings,
    ConfigManager,
    config_manager
)

from .core.processor import (
    ProcessingMode,
    ValidationResult,
    validate_pdf,
    get_pdf_files,
    clean_with_pikepdf,
    rebuild_with_mupdf,
    cleanup_temp_files,
    verify_pdf_integrity,
    process_file
)

from .core.multiprocessing import (
    ProcessResult,
    ParallelProcessor,
    get_optimal_worker_count
)

from .cli.main import PDFOptimizerCLI

from .utils.helpers import (
    setup_logging,
    add_success_level,
    format_size,
    estimate_processing_time
)

__version__ = "15.0.0"
__author__ = "Senior Python Developer"
__all__ = [
    # Config
    'ProcessingConfig',
    'PathsConfig',
    'DisplayConfig',
    'AppSettings',
    'ConfigManager',
    'config_manager',
    
    # Core
    'ProcessingMode',
    'ValidationResult',
    'validate_pdf',
    'get_pdf_files',
    'clean_with_pikepdf',
    'rebuild_with_mupdf',
    'cleanup_temp_files',
    'verify_pdf_integrity',
    'process_file',
    
    # Multiprocessing
    'ProcessResult',
    'ParallelProcessor',
    'get_optimal_worker_count',
    
    # CLI
    'PDFOptimizerCLI',
    
    # Utils
    'setup_logging',
    'add_success_level',
    'format_size',
    'estimate_processing_time',
]
