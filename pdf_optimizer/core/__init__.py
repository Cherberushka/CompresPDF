"""PDF Optimizer Core Package"""

from .processor import (
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

from .multiprocessing import (
    ProcessResult,
    ParallelProcessor,
    get_optimal_worker_count,
    _process_single_file
)

__all__ = [
    'get_pdf_files',
    'ProcessResult',
    'ParallelProcessor',
    'get_optimal_worker_count',
    '_process_single_file'
]
