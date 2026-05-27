#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF Optimizer CLI Module
Консольный интерфейс с улучшенным UI/UX
"""

import sys
import argparse
import logging
from pathlib import Path
from typing import Optional
from datetime import datetime

try:
    from rich.console import Console
    from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeRemainingColumn, TaskProgressColumn
    from rich.table import Table
    from rich.panel import Panel
    from rich import box
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    Console = None

from ..config.settings import ConfigManager, AppSettings
from ..core.processor import get_pdf_files, process_file
from ..core.multiprocessing import ParallelProcessor, ProcessResult, get_optimal_worker_count


class PDFOptimizerCLI:
    """Класс для управления консольным интерфейсом"""
    
    def __init__(self, use_rich: bool = True):
        self.use_rich = use_rich and RICH_AVAILABLE
        self.console = Console() if self.use_rich else None
        self.config_manager = ConfigManager()
        self.logger = logging.getLogger(__name__)
        
    def print_banner(self) -> None:
        """Вывод заголовка программы"""
        if self.use_rich:
            self.console.print(Panel.fit(
                "[bold blue]PDF Batch Optimizer v15.0[/bold blue]\n"
                "[dim]Multiprocessing Edition | Senior Python Developer[/dim]",
                box=box.DOUBLE,
                border_style="blue"
            ))
        else:
            print("\n" + "=" * 70)
            print("PDF OPTIMIZER v15.0 - MULTIPROCESSING EDITION")
            print("=" * 70)
    
    def print_system_info(self) -> None:
        """Вывод информации о системе"""
        import sys
        
        if self.use_rich:
            from rich.tree import Tree
            
            tree = Tree("📊 [bold]System Information[/bold]")
            tree.add(f"Python: [green]{sys.version.split()[0]}[/green]")
            tree.add(f"Executable: [cyan]{sys.executable}[/cyan]")
            
            try:
                import pikepdf
                tree.add(f"pikepdf: [green]v{pikepdf.__version__}[/green]")
            except ImportError:
                tree.add("pikepdf: [red]NOT INSTALLED[/red]")
            
            # Проверка MuPDF
            import subprocess
            try:
                subprocess.run(["mutool", "-version"], 
                             stdout=subprocess.DEVNULL, 
                             stderr=subprocess.DEVNULL, 
                             check=True)
                tree.add("MuPDF: [green]FOUND[/green]")
            except:
                tree.add("MuPDF: [yellow]NOT FOUND[/yellow]")
            
            self.console.print(tree)
        else:
            print(f"Python: {sys.version.split()[0]}")
            print(f"Executable: {sys.executable}")
            
            try:
                import pikepdf
                print(f"pikepdf: v{pikepdf.__version__}")
            except ImportError:
                print("pikepdf: NOT INSTALLED")
    
    def print_warnings(self, no_backup: bool, preserve_signature: bool) -> None:
        """Вывод предупреждений"""
        if not preserve_signature:
            if self.use_rich:
                self.console.print(Panel(
                    "⚠️  [bold yellow]ЭЛЕКТРОННАЯ ПОДПИСЬ БУДЕТ УДАЛЕНА[/bold yellow]\n"
                    "Оптимизированные файлы НЕ ИМЕЮТ юридической силы\n"
                    "Сохраните оригиналы с ЭП в отдельном архиве",
                    title="WARNING",
                    border_style="yellow"
                ))
            else:
                print("\n" + "=" * 70)
                print("⚠️  ВНИМАНИЕ: ЭЛЕКТРОННАЯ ПОДПИСЬ БУДЕТ УДАЛЕНА")
                print("   Оптимизированные файлы НЕ ИМЕЮТ юридической силы")
                print("=" * 70)
        
        if no_backup:
            if self.use_rich:
                self.console.print(Panel(
                    "⚠️  [bold red]БЭКАПЫ ОТКЛЮЧЕНЫ (--no-backup)[/bold red]\n"
                    "Оригиналы файлов будут заменены без возможности отката",
                    title="CRITICAL WARNING",
                    border_style="red"
                ))
            else:
                print("\n" + "=" * 70)
                print("⚠️  ВНИМАНИЕ: БЭКАПЫ ОТКЛЮЧЕНЫ (--no-backup)")
                print("   Оригиналы файлов будут заменены без возможности отката")
                print("=" * 70)
    
    def create_progress(self) -> Optional[Progress]:
        """Создание индикатора прогресса"""
        if self.use_rich:
            return Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(bar_width=40),
                TaskProgressColumn(),
                TimeRemainingColumn(),
                expand=True
            )
        return None
    
    def print_summary_table(self, results: list, elapsed_time: float) -> None:
        """Вывод итоговой таблицы результатов"""
        total = len(results)
        success = sum(1 for r in results if r.success)
        failed = total - success
        
        total_original = sum(r.original_size for r in results)
        total_new = sum(r.new_size for r in results if r.success)
        
        if self.use_rich:
            table = Table(title="📈 Processing Summary", box=box.ROUNDED)
            
            table.add_column("Metric", style="cyan")
            table.add_column("Value", style="green")
            
            table.add_row("Total Files", str(total))
            table.add_row("Successful", f"[green]{success}[/green]")
            table.add_row("Failed", f"[red]{failed}[/red]" if failed > 0 else str(failed))
            table.add_row("Success Rate", f"{(success/total*100):.1f}%")
            table.add_row("Time Elapsed", f"{elapsed_time:.1f}s ({elapsed_time/60:.1f} min)")
            
            if total_original > 0:
                reduction = ((total_original - total_new) / total_original) * 100
                table.add_row("Original Size", f"{total_original/1024/1024:.2f} MB")
                table.add_row("New Size", f"{total_new/1024/1024:.2f} MB")
                table.add_row("Reduction", f"[green]-{reduction:.1f}%[/green]")
                table.add_row("Space Saved", f"[green]{(total_original-total_new)/1024/1024:.2f} MB[/green]")
            
            self.console.print(table)
        else:
            print("\n" + "=" * 70)
            print("PROCESSING SUMMARY")
            print("=" * 70)
            print(f"Total Files: {total}")
            print(f"Successful: {success}")
            print(f"Failed: {failed}")
            print(f"Success Rate: {(success/total*100):.1f}%")
            print(f"Time Elapsed: {elapsed_time:.1f}s ({elapsed_time/60:.1f} min)")
            
            if total_original > 0:
                reduction = ((total_original - total_new) / total_original) * 100
                print(f"Original Size: {total_original/1024/1024:.2f} MB")
                print(f"New Size: {total_new/1024/1024:.2f} MB")
                print(f"Reduction: -{reduction:.1f}%")
                print(f"Space Saved: {(total_original-total_new)/1024/1024:.2f} MB")
    
    def print_dry_run(self, files: list) -> None:
        """Вывод результатов dry-run"""
        total_size = sum(f.stat().st_size for f in files)
        
        if self.use_rich:
            self.console.print(Panel(
                f"[bold]DRY RUN MODE[/bold]\n"
                f"Files to process: {len(files)}\n"
                f"Total size: {total_size/1024/1024:.2f} MB",
                title="ℹ️  INFO",
                border_style="cyan"
            ))
            
            if files:
                table = Table(title="Files to Process (first 10)", show_header=True)
                table.add_column("#", style="dim")
                table.add_column("Filename", style="cyan")
                table.add_column("Size (MB)", justify="right")
                
                for i, f in enumerate(files[:10], 1):
                    size_mb = f.stat().st_size / 1024 / 1024
                    table.add_row(str(i), f.name, f"{size_mb:.2f}")
                
                self.console.print(table)
                
                if len(files) > 10:
                    self.console.print(f"[dim]... and {len(files) - 10} more files[/dim]")
        else:
            print("\n" + "=" * 70)
            print("DRY RUN — файлы не будут изменены")
            print(f"Файлов: {len(files)}")
            print(f"Общий вес: {total_size / 1024 / 1024:.2f} МБ")
            print("Первые 10 файлов:")
            for f in files[:10]:
                print(f"  {f.name} ({f.stat().st_size / 1024 / 1024:.2f} МБ)")
            if len(files) > 10:
                print(f"  ... и ещё {len(files) - 10} файлов")
    
    def create_argument_parser(self) -> argparse.ArgumentParser:
        """Создание парсера аргументов командной строки"""
        parser = argparse.ArgumentParser(
            description="PDF Batch Optimizer v15.0 - Multiprocessing Edition",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Примеры использования:
  %(prog)s "C:\\Documents" --quality better --workers 4
  %(prog)s "C:\\Documents" --quality best --mupdf-aggression dd
  %(prog)s "C:\\Documents" --dry-run --min-size 0
  %(prog)s "C:\\Documents" --no-backup --no-rich
  %(prog)s "C:\\Documents" --preserve-signature --workers auto
  
Режимы качества:
  fast    - Только pikepdf (70-80%% сжатие, ~1 сек/файл)
  better  - pikepdf + MuPDF (80-90%% сжатие, ~2-3 сек/файл)
  best    - pikepdf + MuPDF макс. (85-92%% сжатие, ~3-4 сек/файл)

Уровни агрессии MuPDF:
  d       - Минимальное сжатие
  dd      - Стандартное сжатие (по умолчанию)
  ddd     - Сильное сжатие
  dddd    - Максимальное сжатие
            """
        )
        
        parser.add_argument("path", help="Путь к корневой директории")
        parser.add_argument("--dry-run", action="store_true",
                          help="Только список файлов без обработки")
        parser.add_argument("--min-size", type=int, default=0,
                          help="Мин размер в МБ (по умолчанию 0)")
        parser.add_argument("--keep-bak", action="store_true",
                          help="Не удалять .bak файлы (хранить 90 дней)")
        parser.add_argument("--quality", type=str, default="fast",
                          choices=["fast", "better", "best"],
                          help="Режим обработки (fast/better/best)")
        parser.add_argument("--mupdf-aggression", type=str, default="dd",
                          choices=["d", "dd", "ddd", "dddd"],
                          help="Уровень сжатия MuPDF")
        parser.add_argument("--preserve-signature", action="store_true",
                          help="Не удалять электронные подписи")
        parser.add_argument("--no-backup", action="store_true",
                          help="Не создавать .bak файлы")
        parser.add_argument("--workers", type=str, default="auto",
                          help="Количество процессов (auto/N, по умолчанию auto)")
        parser.add_argument("--no-rich", action="store_true",
                          help="Отключить красивый вывод (использовать простой текст)")
        parser.add_argument("--verbose", "-v", action="store_true",
                          help="Подробный вывод")
        parser.add_argument("--config", type=Path,
                          help="Путь к файлу конфигурации JSON")
        parser.add_argument("--save-config", type=Path,
                          help="Сохранить текущие настройки в файл")
        
        return parser
    
    def parse_workers(self, workers_str: str) -> int:
        """Парсинг количества рабочих процессов"""
        if workers_str.lower() == "auto":
            return get_optimal_worker_count()
        try:
            n = int(workers_str)
            return max(1, min(n, get_optimal_worker_count() * 2))
        except ValueError:
            return get_optimal_worker_count()
    
    def run(self, args: Optional[list] = None) -> int:
        """
        Запуск приложения
        
        Args:
            args: Аргументы командной строки (по умолчанию sys.argv[1:])
            
        Returns:
            Код возврата (0 = успех, 1 = ошибка)
        """
        parser = self.create_argument_parser()
        parsed_args = parser.parse_args(args)
        
        # Переопределение use_rich если указан флаг --no-rich
        if parsed_args.no_rich:
            self.use_rich = False
            self.console = None
        
        # Вывод заголовка
        self.print_banner()
        self.print_system_info()
        
        # Загрузка конфигурации из файла если указано
        if parsed_args.config:
            try:
                self.config_manager.load_from_file(parsed_args.config)
                self.logger.info(f"Configuration loaded from {parsed_args.config}")
            except Exception as e:
                self.logger.error(f"Failed to load config: {e}")
        
        # Сохранение конфигурации если указано
        if parsed_args.save_config:
            self.config_manager.create_default_config(parsed_args.save_config)
            self.logger.info(f"Configuration saved to {parsed_args.save_config}")
            return 0
        
        # Переопределение аргументов командной строки значениями из конфига
        # Если конфиг загружен, используем его значения для keep_bak и других параметров
        if parsed_args.config:
            settings = self.config_manager.settings
            # Используем значения из конфига, если они не были явно указаны в CLI
            if not hasattr(parsed_args, '_keep_bak_from_cli') or not parsed_args.keep_bak:
                parsed_args.keep_bak = settings.processing.keep_bak
            if not hasattr(parsed_args, '_no_backup_from_cli') or not parsed_args.no_backup:
                parsed_args.no_backup = settings.processing.no_backup
            if not hasattr(parsed_args, '_quality_from_cli') or parsed_args.quality == "fast":
                parsed_args.quality = settings.processing.quality
            if not hasattr(parsed_args, '_mupdf_aggression_from_cli') or parsed_args.mupdf_aggression == "dd":
                parsed_args.mupdf_aggression = settings.processing.mupdf_aggression
            if not hasattr(parsed_args, '_min_size_from_cli') or parsed_args.min_size == 0:
                parsed_args.min_size = settings.processing.min_size_mb
            if not hasattr(parsed_args, '_preserve_signature_from_cli') or not parsed_args.preserve_signature:
                parsed_args.preserve_signature = settings.processing.preserve_signature
        
        # Вывод предупреждений
        self.print_warnings(parsed_args.no_backup, parsed_args.preserve_signature)
        
        # Определение количества процессов
        num_workers = self.parse_workers(parsed_args.workers)
        
        # Настройка путей
        root_path = Path(parsed_args.path).resolve()
        temp_dir = root_path / ".pdf_temp"
        
        try:
            temp_dir.mkdir(exist_ok=True)
        except (PermissionError, OSError):
            import tempfile
            temp_dir = Path(tempfile.gettempdir()) / "pdf_optimizer_temp"
            temp_dir.mkdir(exist_ok=True)
            self.logger.warning(f"Using system temp: {temp_dir}")
        
        # Поиск файлов
        files = get_pdf_files(
            str(root_path), 
            parsed_args.min_size
        )
        
        if not files:
            self.logger.info("Файлов для обработки не найдено.")
            return 0
        
        # Dry run режим
        if parsed_args.dry_run:
            self.print_dry_run(files)
            return 0
        
        # Обработка файлов
        processor = ParallelProcessor(max_workers=num_workers)
        results = []
        
        if self.use_rich:
            with self.create_progress() as progress:
                task = progress.add_task(
                    f"[cyan]Processing {len(files)} files...",
                    total=len(files)
                )
                
                def update_progress(result: ProcessResult):
                    progress.update(task, advance=1)
                    if result.success:
                        progress.console.print(
                            f"[green]✓[/green] {result.file_path.name} "
                            f"({result.size_mb_original:.2f}→{result.size_mb_new:.2f} MB, "
                            f"-{result.reduction_percent:.1f}%)"
                        )
                    else:
                        progress.console.print(
                            f"[red]✗[/red] {result.file_path.name}: {result.error_message}"
                        )
                
                results = processor.process_files(
                    files=files,
                    mode=parsed_args.quality,
                    mupdf_aggression=parsed_args.mupdf_aggression,
                    temp_dir=temp_dir,
                    preserve_signature=parsed_args.preserve_signature,
                    no_backup=parsed_args.no_backup,
                    keep_bak=parsed_args.keep_bak,
                    progress_callback=update_progress
                )
        else:
            print(f"\nProcessing {len(files)} files with {num_workers} workers...")
            
            def simple_progress(result: ProcessResult):
                status = "✓" if result.success else "✗"
                if result.success:
                    print(f"{status} {result.file_path.name} "
                          f"({result.size_mb_original:.2f}→{result.size_mb_new:.2f} MB, "
                          f"-{result.reduction_percent:.1f}%)")
                else:
                    print(f"{status} {result.file_path.name}: {result.error_message}")
            
            results = processor.process_files(
                files=files,
                mode=parsed_args.quality,
                mupdf_aggression=parsed_args.mupdf_aggression,
                temp_dir=temp_dir,
                preserve_signature=parsed_args.preserve_signature,
                no_backup=parsed_args.no_backup,
                keep_bak=parsed_args.keep_bak,
                progress_callback=simple_progress
            )
        
        # Вывод итогов
        import time
        elapsed = getattr(processor, '_elapsed_time', 0) or sum(
            1 for _ in results
        ) * 0.1  # Заглушка, нужно добавить замер времени
        
        self.print_summary_table(results, elapsed)
        
        # Возврат кода ошибки если есть неудачные обработки
        failed = sum(1 for r in results if not r.success)
        return 1 if failed > 0 else 0
