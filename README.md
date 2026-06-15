PDF Batch Optimizer (v15.1.0)
Высокопроизводительный фоновый сервис (daemon) для пакетного сжатия и оптимизации PDF-файлов на серверах Ubuntu/Linux.
Использует трехступенчатый пайплайн деградации: **Ghostscript** (восстановление структуры и даунсэмплинг) → **pikepdf** (сборка мусора и линеаризация) → **MuPDF mutool** (глубокая очистка).

# ✨ Ключевые возможности
- **Фоновая работа по расписанию**: Встроенный APScheduler позволяет настроить cron-задачи для разных директорий.
- **Фильтрация по времени (Smart Scan)**: Обрабатывает только новые/измененные файлы (--since 24h, --since 7d).
- **Идемпотентность (SQLite WAL)**: Встроенный реестр запоминает обработанные файлы по хэшу и `mtime`. Защита от повторного сжатия одних и тех же файлов.
- **REST API**: Управляйте задачами, проверяйте статус и запускайте dry-run сканирование через HTTP.
- **Safe I/O**: Защита от повреждений файлов при сбоях (атомарная запись os.replace + эксклюзивные блокировки Linux `fcntl`).

# 🚀 Быстрый старт (Docker Compose)
Это рекомендуемый способ развертывания на серверах Ubuntu. Образ уже включает Python 3.12, Ghostscript и MuPDF.
**1. Клонируйте репозиторий:**
```
git clone <your-repo-url> /opt/CompresPDF
cd /opt/CompresPDF
```
**2. Настройте конфигурацию:**
```
cp config.sample.yaml config.yaml
# Отредактируйте config.yaml (настройте расписание и пути)
nano config.yaml 
```

**3. Запустите сервис:**
```
mkdir -p data logs
docker compose up -d
```
Сервис будет доступен на порту 8080 (по умолчанию).

# ⚙️ Конфигурация (config.yaml)
Настройки можно задавать через файл config.yaml или через переменные окружения (префикс PDF_OPTIMIZER__).
```
api:
  host: "0.0.0.0"
  port: 8080

log_level: "INFO"
no_backup: false # Оставьте false для создания .bak файлов (защита от потери данных)

scheduler:
  jobs:
    - name: "daily_inbox"
      cron: "0 2 * * *" # Каждый день в 02:00
      since: "24h"      # Искать файлы, измененные только за последние 24 часа
      root_dir: "/data/inbox"
      quality: "default"
      aggression: "gg"
```
Формат времени (since)Поддерживаемые единицы: m (минуты), h (часы), d (дни), w (недели), mo (месяцы), y (годы).
Примеры: 30m, 24h, 7d, 3mo, 1y.

# 📡 REST API Reference
Вы можете управлять сервисом удаленно с помощью HTTP-запросов (например, из других ваших систем).
1. Запуск задачи сжатия вручную (Async)Добавляет задачу в фоновую очередь.
```
curl -X POST http://localhost:8080/api/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "root_dir": "/data/documents",
    "since": "48h",
    "quality": "fast",
    "aggression": "ggg"
  }'
```
2. Симуляция сканирования (Dry-Run)
Позволяет узнать, какие файлы будут сжаты (с учетом времени и базы идемпотентности), до фактического запуска.
```
curl -X POST http://localhost:8080/api/scan \
  -H "Content-Type: application/json" \
  -d '{
    "root_dir": "/data/documents",
    "since": "7d"
  }'
```
3. История аудитаПолучить список последних выполненных задач и сэкономленное место.
```
curl http://localhost:8080/api/jobs?limit=10
```
4. Перезагрузка расписанияЕсли вы изменили config.yaml, примените новые cron-задачи без рестарта контейнера:
```
curl -X POST http://localhost:8080/api/scheduler/reload
```
# 💻 Использование через CLI (Для разработчиков)Если вы разрабатываете локально без Docker, можно использовать CLI.
```
 Установка (требуются установленные в системе ghostscript и mupdf-tools)
pip install -e .

# Запуск ручного сканирования
pdf-optimizer --dir /path/to/pdfs --since 7d --quality archive --aggression ggg

# Запуск API-сервера локально
uvicorn pdf_optimizer.api.app:app --reload
```

# 🛠 Тестирование
Проект покрыт тестами с помощью `pytest` (включая проверку идемпотентности SQLite и парсинг времени).
```
pip install -e ".[dev]"
pytest tests/ -v
```