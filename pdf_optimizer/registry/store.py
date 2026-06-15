import sqlite3
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

logger = logging.getLogger("PDFOptimizer.registry")


class RegistryStore:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        """Создает подключение к БД с включенным режимом WAL для конкурентного доступа."""
        # Создаем директорию для БД, если её нет
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        conn = sqlite3.connect(
            self.db_path,
            detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES,
            timeout=30.0  # Ожидание разблокировки при высокой нагрузке
        )
        conn.row_factory = sqlite3.Row
        # Включаем WAL (Write-Ahead Logging)
        conn.execute('pragma journal_mode=wal')
        conn.execute('pragma synchronous=normal')
        return conn

    def _init_db(self):
        """Инициализирует структуру таблиц."""
        with self._get_connection() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS jobs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source TEXT NOT NULL,          -- 'api', 'scheduler', 'cli'
                    root_dir TEXT NOT NULL,
                    params_json TEXT NOT NULL,
                    status TEXT NOT NULL,          -- 'running', 'succeeded', 'failed', 'partial'
                    files_processed INTEGER DEFAULT 0,
                    bytes_saved INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    finished_at TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS processed_files (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_id INTEGER NOT NULL,
                    file_path TEXT NOT NULL,
                    mtime REAL NOT NULL,           -- timestamp файла на момент сжатия
                    size_before INTEGER NOT NULL,
                    size_after INTEGER NOT NULL,
                    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (job_id) REFERENCES jobs(id)
                );

                -- Индекс для быстрого поиска уже обработанных файлов
                CREATE INDEX IF NOT EXISTS idx_processed_files_path ON processed_files(file_path);
            """)

    def create_job(self, source: str, root_dir: str, params: Dict[str, Any]) -> int:
        """Создает новую запись о задаче и возвращает её ID."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO jobs (source, root_dir, params_json, status) VALUES (?, ?, ?, ?)",
                (source, root_dir, json.dumps(params), "running")
            )
            return cursor.lastrowid

    def exclude_already_processed(self, files: List[Path]) -> List[Path]:
        """
        Принимает список файлов и возвращает только те, которые:
        1. Ещё не обрабатывались.
        2. Были изменены с момента последней обработки (mtime файла > mtime в БД).
        """
        unprocessed = []
        with self._get_connection() as conn:
            cursor = conn.cursor()
            for file_path in files:
                try:
                    current_mtime = file_path.stat().st_mtime
                except OSError:
                    continue  # Пропускаем недоступные файлы

                cursor.execute(
                    "SELECT mtime FROM processed_files WHERE file_path = ? ORDER BY processed_at DESC LIMIT 1",
                    (str(file_path.absolute()),)
                )
                row = cursor.fetchone()

                # Если файла нет в БД, или он был изменен после последней обработки
                if not row or current_mtime > row['mtime']:
                    unprocessed.append(file_path)

        logger.info(f"Идемпотентность: пропущено {len(files) - len(unprocessed)} уже сжатых файлов.")
        return unprocessed

    def record_results(self, job_id: int, file_path: Path, current_mtime: float, size_before: int, size_after: int):
        """Записывает результат успешной обработки конкретного файла."""
        with self._get_connection() as conn:
            conn.execute(
                """INSERT INTO processed_files 
                   (job_id, file_path, mtime, size_before, size_after) 
                   VALUES (?, ?, ?, ?, ?)""",
                (job_id, str(file_path.absolute()), current_mtime, size_before, size_after)
            )

    def finish_job(self, job_id: int, status: str, files_processed: int, bytes_saved: int):
        """Обновляет статус задачи по завершению."""
        with self._get_connection() as conn:
            conn.execute(
                """UPDATE jobs 
                   SET status = ?, files_processed = ?, bytes_saved = ?, finished_at = CURRENT_TIMESTAMP
                   WHERE id = ?""",
                (status, files_processed, bytes_saved, job_id)
            )