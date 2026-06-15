# PDF Batch Optimizer v15.0

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Многопроцессорный оптимизатор PDF файлов** — инструмент для пакетной обработки и сжатия PDF документов с сохранением целостности данных.

## 🚀 Возможности

- **Многопроцессорная обработка** — параллельная обработка файлов с использованием всех ядер CPU
- **Два движка оптимизации**:
  - `pikepdf` — быстрая очистка и сжатие (70-80%)
  - `MuPDF` — глубокая оптимизация (80-92%)
- **Три режима качества**:
  - `fast` — только pikepdf (~1 сек/файл)
  - `better` — pikepdf + MuPDF (~2-3 сек/файл)
  - `best` — максимальное сжатие (~3-4 сек/файл)
- **Безопасность**:
  - Автоматическое создание бэкапов (.bak)
  - Проверка целостности после обработки
  - Откат при ошибках
- **Улучшенный CLI**:
  - Красивый вывод с цветами (Rich library)
  - Индикатор прогресса
  - Итоговые таблицы статистики
- **Конфигурация через JSON** — сохранение и загрузка настроек

## 📦 Установка

### Требования

- Python 3.8+
- pikepdf
- MuPDF (опционально, для режимов better/best)

### Быстрая установка

```bash
pip install -r requirements.txt
```

### Установка MuPDF (Windows)

```powershell
winget install ArtifexSoftware.MuPDF
```

### Установка MuPDF (Linux)

```bash
sudo apt-get install mupdf-tools
```

## 📁 Структура проекта

```
pdf_optimizer/
├── __init__.py          # Основной пакет
├── __main__.py          # Точка входа
├── config/
│   ├── __init__.py
│   └── settings.py      # Управление конфигурацией
├── core/
│   ├── __init__.py
│   ├── processor.py     # Основные функции обработки
│   └── multiprocessing.py  # Многопроцессорная обработка
├── cli/
│   ├── __init__.py
│   └── main.py          # Консольный интерфейс
└── utils/
    ├── __init__.py
    └── helpers.py       # Вспомогательные функции
```

## 💻 Использование

### Базовые команды

```bash
# Запуск с настройками по умолчанию
python -m pdf_optimizer "C:\Documents"

# Режим лучшего качества с 4 процессами
python -m pdf_optimizer "C:\Documents" --quality better --workers 4

# Максимальное сжатие
python -m pdf_optimizer "C:\Documents" --quality best --mupdf-aggression dd

# Только просмотр без обработки
python -m pdf_optimizer "C:\Documents" --dry-run

# Без создания бэкапов (не рекомендуется!)
python -m pdf_optimizer "C:\Documents" --no-backup

# Сохранение электронных подписей
python -m pdf_optimizer "C:\Documents" --preserve-signature

# Простой текстовый вывод (без Rich)
python -m pdf_optimizer "C:\Documents" --no-rich
```

### Работа с конфигурацией

```bash
# Сохранить текущие настройки в файл
python -m pdf_optimizer . --save-config my_config.json

# Загрузить настройки из файла
python -m pdf_optimizer "C:\Documents" --config my_config.json
```

### Пример конфигурации (JSON)

```json
{
  "processing": {
    "quality": "better",
    "mupdf_aggression": "dd",
    "min_size_mb": 1,
    "preserve_signature": false,
    "no_backup": false
  },
  "display": {
    "verbose": true,
    "show_progress": true
  }
}
```

## 📊 Параметры командной строки

| Параметр | Описание | По умолчанию |
|----------|----------|--------------|
| `path` | Путь к корневой директории | *обязательно* |
| `--quality` | Режим обработки (fast/better/best) | fast |
| `--mupdf-aggression` | Уровень сжатия MuPDF (d/dd/ddd/dddd) | dd |
| `--workers` | Количество процессов (auto/N) | auto |
| `--min-size` | Минимальный размер файла в МБ | 0 |
| `--preserve-signature` | Сохранять электронные подписи | ❌ |
| `--no-backup` | Не создавать бэкапы | ❌ |
| `--keep-bak` | Не удалять .bak файлы | ❌ |
| `--dry-run` | Только список файлов | ❌ |
| `--no-rich` | Отключить красивый вывод | ❌ |
| `--verbose, -v` | Подробный вывод | ❌ |
| `--config` | Путь к файлу конфигурации | - |
| `--save-config` | Сохранить настройки в файл | - |

## 🔧 API для разработчиков

```python
from pdf_optimizer import (
    ParallelProcessor,
    ConfigManager,
    validate_pdf,
    process_file
)

# Использование конфигурации
config = ConfigManager()
settings = config.settings

# Параллельная обработка
processor = ParallelProcessor(max_workers=4)
results = processor.process_files(
    files=pdf_files,
    mode="better",
    mupdf_aggression="dd",
    temp_dir=temp_path
)

# Обработка результатов
for result in results:
    if result.success:
        print(f"✓ {result.file_path.name}: -{result.reduction_percent:.1f}%")
```

## ⚠️ Важные предупреждения

### Электронные подписи
При обработке **электронные подписи удаляются**. Оптимизированные файлы теряют юридическую силу. 

**Рекомендация**: Используйте `--preserve-signature` для файлов с ЭП или сохраняйте оригиналы.

### Бэкапы
По умолчанию создаются копии оригиналов с расширением `.bak`. 

**Требование Минздрава РФ**: хранение бэкапов медицинских документов минимум 90 дней.

## 🐛 Troubleshooting

### Ошибка: "MuPDF NOT FOUND"
```bash
# Windows
winget install ArtifexSoftware.MuPDF

# Linux
sudo apt-get install mupdf-tools

# macOS
brew install mupdf
```

### Ошибка доступа к файлам
Запустите от имени администратора или проверьте права доступа к директории.

### Проблемы с кодировкой
Убедитесь, что в путях нет специальных символов. Используйте короткие пути или 8.3 имена.

## 📈 Производительность

| Режим | Сжатие | Скорость | Использование CPU |
|-------|--------|----------|-------------------|
| fast | 70-80% | ~1 сек/файл | Низкое |
| better | 80-90% | ~2-3 сек/файл | Среднее |
| best | 85-92% | ~3-4 сек/файл | Высокое |

**Оптимизация**: Используйте `--workers auto` для автоматического выбора количества процессов.

## 🤝 Вклад в проект

1. Fork репозитория
2. Создайте ветку (`git checkout -b feature/amazing-feature`)
3. Commit изменений (`git commit -m 'Add amazing feature'`)
4. Push (`git push origin feature/amazing-feature`)
5. Откройте Pull Request

## 📄 Лицензия

MIT License — см. файл [LICENSE](LICENSE) для деталей.

## 👨‍💻 Автор

Senior Python Developer  
Version 15.0.0 (Multiprocessing Edition)  
Дата: 2026-03-27

---

**Предыдущие версии**: v14.1 (Fixed no-backup), v14.0, v13.x
