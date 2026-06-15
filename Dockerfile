FROM python:3.12-slim

# Запрещаем Python писать .pyc файлы и буферизовать stdout/stderr (полезно для логов в Docker)
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Устанавливаем системные зависимости: Ghostscript и MuPDF
RUN apt-get update && apt-get install -y --no-install-recommends \
    ghostscript \
    mupdf-tools \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Устанавливаем pip-зависимости (используем кэширование слоев Docker)
COPY pyproject.toml README.md ./
COPY pdf_optimizer/ ./pdf_optimizer/

# Устанавливаем проект
RUN pip install --no-cache-dir -e .

# Создаем рабочие директории по умолчанию, чтобы не было проблем с правами
RUN mkdir -p /data /var/log/pdf-optimizer

# Открываем порт для FastAPI
EXPOSE 8080

# Запускаем FastAPI через uvicorn
CMD ["uvicorn", "pdf_optimizer.api.app:app", "--host", "0.0.0.0", "--port", "8080"]