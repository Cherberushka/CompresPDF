"""PDF Optimizer Core Package"""

from .processor import (
    PDFProcessor,
    ProcessItem,
    ProcessResult,
    get_pdf_files
)

from .multiprocessing import (
    ParallelProcessor,
    get_optimal_worker_count
)

__all__ = [
    'PDFProcessor',
    'ProcessItem',
    'ProcessResult',
    'get_pdf_files',
    'ParallelProcessor',
    'get_optimal_worker_count'
]
