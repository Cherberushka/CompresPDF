"""
PDF Batch Optimizer v15.0 - Multiprocessing Edition
Модульная версия с многопроцессорной обработкой

Author: Senior Python Developer
Date: 2026-03-27
Version: 15.0.0
"""

from .config.settings import (
    AppSettings,
    settings
)

from .core.processor import (
    PDFProcessor,
    ProcessItem,
    ProcessResult,
    get_pdf_files
)

from .core.multiprocessing import (
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
    'AppSettings',
    'settings',
    
    # Core
    'PDFProcessor',
    'ProcessItem',
    'ProcessResult',
    'get_pdf_files',
    
    # Multiprocessing
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
