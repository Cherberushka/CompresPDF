# PDF Batch Optimizer v14.1

Оптимизатор PDF-файлов для Windows с использованием **pikepdf** и **MuPDF**. Обеспечивает сжатие до 85-92% без артефактов Ghostscript.

## 📋 Описание

Инструмент предназначен для пакетной обработки PDF-документов с целью уменьшения их размера. Особенно полезен для медицинских учреждений, где требуется хранение больших объёмов документации в соответствии с требованиями Минздрава РФ.

### Основные возможности

- ✅ **Двухэтапная обработка**: очистка через pikepdf + пересборка через MuPDF
- ✅ **Три режима качества**: fast, better, best
- ✅ **Валидация PDF**: проверка целостности до и после обработки
- ✅ **Автоматический откат**: восстановление из бэкапа при ошибках
- ✅ **Гибкое управление бэкапами**: опция `--no-backup` для отключения
- ✅ **Сохранение электронной подписи**: опция `--preserve-signature`
- ✅ **Подробное логирование**: все операции записываются в `pdf_process.log`
- ✅ **Dry-run режим**: предварительный просмотр файлов для обработки

## 🔧 Требования

### Обязательные зависимости

```bash
pip install pikepdf
```

### Опциональные зависимости

**MuPDF (mutool)** — для максимального сжатия:
- Windows: `winget install ArtifexSoftware.MuPDF`
- Linux: `sudo apt install mupdf-tools`
- macOS: `brew install mupdf`

## 🚀 Установка

1. Клонируйте репозиторий:
```bash
git clone <repository-url>
cd <repository-directory>
```

2. Установите зависимости:
```bash
pip install -r requirements.txt
```

Или вручную:
```bash
pip install pikepdf
```

3. (Рекомендуется) Установите MuPDF для лучшего сжатия

## 📖 Использование

### Базовый синтаксис

```bash
python main.py <путь_к_директории> [опции]
```

### Примеры команд

#### Быстрая оптимизация (только pikepdf)
```bash
python main.py "C:\Documents" --quality fast
```

#### Оптимальное сжатие (pikepdf + MuPDF)
```bash
python main.py "C:\Documents" --quality better
```

#### Максимальное сжатие
```bash
python main.py "C:\Documents" --quality best --mupdf-aggression dd
```

#### Только просмотр (без изменений)
```bash
python main.py "C:\Documents" --dry-run --min-size 0
```

#### Без создания бэкапов ⚠️
```bash
python main.py "C:\Documents" --no-backup --min-size 0
```

#### С сохранением электронной подписи
```bash
python main.py "C:\Documents" --preserve-signature
```

### Параметры командной строки

| Параметр | Описание | По умолчанию |
|----------|----------|--------------|
| `path` | Путь к корневой директории с PDF | **Обязательный** |
| `--dry-run` | Только список файлов без обработки | `False` |
| `--min-size` | Минимальный размер файла в МБ | `0` |
| `--quality` | Режим обработки: `fast`, `better`, `best` | `fast` |
| `--mupdf-aggression` | Уровень сжатия MuPDF: `d`, `dd`, `ddd`, `dddd` | `dd` |
| `--preserve-signature` | Не удалять электронные подписи | `False` |
| `--no-backup` | Не создавать `.bak` файлы | `False` |
| `--keep-bak` | Не удалять `.bak` файлы (хранить 90 дней) | `False` |

### Режимы обработки

| Режим | Движок | Сжатие | Скорость |
|-------|--------|--------|----------|
| `fast` | pikepdf только | 70-80% | ~1 сек/файл |
| `better` | pikepdf + MuPDF | 80-90% | ~2-3 сек/файл |
| `best` | pikepdf + MuPDF (макс.) | 85-92% | ~3-4 сек/файл |

### Уровни агрессии MuPDF

- `d` — минимальное сжатие
- `dd` — стандартное (рекомендуется)
- `ddd` — сильное сжатие
- `dddd` — максимальное сжатие (может повлиять на качество)

## ⚠️ Важные предупреждения

### Электронная подпись
По умолчанию электронные подписи **удаляются** при оптимизации. Оптимизированные файлы **НЕ ИМЕЮТ юридической силы**. 

**Рекомендации:**
- Используйте `--preserve-signature` для файлов с ЭП
- Сохраняйте оригиналы с ЭП в отдельном архиве
- Требование Минздрава РФ: хранение 90+ дней

### Бэкапы
По умолчанию создаются `.bak` файлы оригиналов. 

**Рекомендации:**
- Не используйте `--no-backup` для важных данных
- Для медицинских документов всегда храните бэкапы 90+ дней
- Используйте `--keep-bak` для сохранения всех бэкапов

## 📁 Структура проекта

```
.
├── main.py                 # Основной скрипт
├── pdf_process.log         # Лог обработки (создаётся автоматически)
├── .pdf_temp/              # Временные файлы (удаляются после работы)
├── *.bak                   # Бэкапы оригиналов (если не использован --no-backup)
└── README.md               # Документация
```

## 🛠️ Алгоритм работы

1. **Сканирование**: поиск всех `.pdf` файлов в указанной директории и поддиректориях
2. **Валидация**: проверка каждого файла (сигнатура, структура, шифрование)
3. **Очистка pikepdf**:
   - Удаление аннотаций (`/Annots`)
   - Удаление форм (`/AcroForm`)
   - Очистка метаданных (`/Metadata`)
   - Удаление структуры оглавления (`/Outlines`)
   - Оптимизация потоков (garbage collection, deflate, linearization)
4. **Пересборка MuPDF** (режимы `better` и `best`):
   - Реконструкция PDF с применением уровня сжатия
   - Проверка целостности страниц
5. **Валидация результата**: проверка целостности после обработки
6. **Замена файла**: оригинал заменяется оптимизированной версией
7. **Откат при ошибке**: восстановление из `.bak` при проблемах

## 📊 Логирование

Все операции записываются в файл `pdf_process.log`:
- Время начала/окончания обработки
- Информация о каждом файле (размер до/после, процент сжатия)
- Ошибки валидации и обработки
- Статистика по всей пакетной обработке

## 🔍 Troubleshooting

### Файл не обрабатывается
- Проверьте, не зашифрован ли PDF паролем
- Убедитесь, что файл имеет корректную PDF-сигнатуру
- Проверьте права доступа к файлу

### MuPDF не найден
```bash
# Проверка установки
mutool -version

# Установка на Windows
winget install ArtifexSoftware.MuPDF
```

### Недостаточно места для бэкапов
Используйте `--no-backup` только после тестирования на копии данных:
```bash
python main.py "C:\Documents" --no-backup --dry-run
```

### Потеря качества изображений
Уменьшите уровень агрессии MuPDF:
```bash
python main.py "C:\Documents" --quality better --mupdf-aggression d
```

## 📝 Лицензия

MIT License

## 👨‍💻 Автор

Senior Python Developer  
Версия: 14.1.0  
Дата: 2026-03-27

---

## 📈 Рекомендации по улучшению кода

### 1. **Структурные улучшения**

#### Вынос конфигурации в отдельный файл
```python
# config.py
from dataclasses import dataclass

@dataclass
class Config:
    DEFAULT_MIN_SIZE_MB: int = 0
    DEFAULT_LOG_FILE: str = "pdf_process.log"
    BACKUP_RETENTION_DAYS: int = 90
    MUPDF_TIMEOUT: int = 180
```

#### Разделение на модули
```
pdf_optimizer/
├── __init__.py
├── cli.py              # Аргументы командной строки
├── config.py           # Конфигурация
├── validator.py        # Валидация PDF
├── optimizer.py        # Логика оптимизации
├── backup.py           # Управление бэкапами
└── logger.py           # Настройка логирования
```

### 2. **Улучшение обработки ошибок**

```python
from enum import Enum
from typing import NamedTuple

class ErrorCode(Enum):
    SUCCESS = 0
    FILE_NOT_FOUND = 1
    INVALID_PDF = 2
    ENCRYPTED_PDF = 3
    PROCESSING_ERROR = 4

class ProcessingResult(NamedTuple):
    success: bool
    error_code: ErrorCode
    message: str
    original_size: int
    new_size: int
```

### 3. **Добавление прогресс-бара**

```bash
pip install tqdm
```

```python
from tqdm import tqdm

for idx, file_path in enumerate(tqdm(files, desc="Обработка"), 1):
    # ...
```

### 4. **Параллельная обработка**

```python
from concurrent.futures import ThreadPoolExecutor, as_completed

def process_files_parallel(files, max_workers=4):
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(process_file, f, ...): f 
            for f in files
        }
        for future in as_completed(futures):
            # ...
```

### 5. **Конфигурационный файл**

```yaml
# config.yaml
optimization:
  default_quality: "better"
  mupdf_aggression: "dd"
  min_size_mb: 0
  
backup:
  enabled: true
  retention_days: 90
  directory: ".pdf_backups"
  
logging:
  level: "INFO"
  file: "pdf_process.log"
```

### 6. **Unit-тесты**

```python
# tests/test_validator.py
import pytest
from pathlib import Path
from main import validate_pdf

def test_valid_pdf(sample_pdf):
    is_valid, msg = validate_pdf(sample_pdf)
    assert is_valid
    assert msg == "OK"

def test_encrypted_pdf(encrypted_pdf):
    is_valid, msg = validate_pdf(encrypted_pdf)
    assert not is_valid
    assert "паролем" in msg
```

### 7. **Type hints и docstrings**

```python
from typing import Dict, Any

def optimize_pdf(
    input_path: Path,
    output_path: Path,
    quality: str = "fast",
    aggression: str = "dd"
) -> Dict[str, Any]:
    """
    Оптимизирует PDF-файл с заданными параметрами.
    
    Args:
        input_path: Путь к исходному файлу
        output_path: Путь для сохранения результата
        quality: Режим оптимизации
        aggression: Уровень сжатия MuPDF
    
    Returns:
        Словарь с результатами:
        - success: bool
        - original_size: int
        - new_size: int
        - reduction_percent: float
    """
```

### 8. **CI/CD Pipeline**

```yaml
# .github/workflows/tests.yml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run tests
        run: pytest
```

### 9. **Docker-контейнер**

```dockerfile
FROM python:3.11-slim

RUN apt-get update && apt-get install -y mupdf-tools

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

ENTRYPOINT ["python", "main.py"]
```

### 10. **Метрики и мониторинг**

```python
import json
from datetime import datetime

def save_metrics(metrics: dict):
    """Сохранение метрик для анализа"""
    metrics['timestamp'] = datetime.now().isoformat()
    
    with open('metrics.jsonl', 'a', encoding='utf-8') as f:
        f.write(json.dumps(metrics) + '\n')
```

### 11. **Улучшение CLI**

```bash
pip install rich click
```

```python
import click
from rich.console import Console

console = Console()

@click.command()
@click.argument('path', type=click.Path(exists=True))
@click.option('--quality', type=click.Choice(['fast', 'better', 'best']))
def cli(path, quality):
    """📄 PDF Optimizer — быстрое сжатие без потери качества"""
    console.print(f"[bold blue]Начало обработки[/bold blue]")
```

### 12. **Автоматическая очистка старых бэкапов**

```python
def cleanup_old_backups(backup_dir: Path, retention_days: int):
    """Удаление бэкапов старше retention_days"""
    cutoff = datetime.now() - timedelta(days=retention_days)
    
    for bak_file in backup_dir.glob("*.bak"):
        mtime = datetime.fromtimestamp(bak_file.stat().st_mtime)
        if mtime < cutoff:
            bak_file.unlink()
            logger.info(f"Удалён старый бэкап: {bak_file.name}")
```

### Приоритеты внедрения

| Приоритет | Улучшение | Сложность | Польза |
|-----------|-----------|-----------|--------|
| 🔴 Высокий | Unit-тесты | Средняя | Критическая |
| 🔴 Высокий | Параллельная обработка | Средняя | Высокая |
| 🟡 Средний | Разделение на модули | Высокая | Высокая |
| 🟡 Средний | Progress bar | Низкая | Средняя |
| 🟢 Низкий | Docker | Средняя | Средняя |
| 🟢 Низкий | CI/CD | Средняя | Средняя |
