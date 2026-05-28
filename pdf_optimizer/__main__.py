#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF Batch Optimizer v15.0 - Multiprocessing Edition
Точка входа приложения

Author: Senior Python Developer
Date: 2026-03-27
Version: 15.0.0
"""

import sys
from pathlib import Path

# Добавляем родительскую директорию в path для импорта модулей
sys.path.insert(0, str(Path(__file__).parent.parent))

from pdf_optimizer.cli.main import PDFOptimizerCLI
from pdf_optimizer.utils.helpers import setup_logging, add_success_level


def main():
    """Точка входа приложения"""
    # Настройка логгера
    add_success_level()
    logger = setup_logging("pdf_process.log", verbose=False)
    
    # Создание и запуск CLI
    cli = PDFOptimizerCLI(use_rich=True)
    
    try:
        exit_code = cli.run()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logger.warning("\n⚠️  Прервано пользователем.")
        sys.exit(1)
    except Exception as e:
        logger.critical(f"❌ Критический сбой: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
