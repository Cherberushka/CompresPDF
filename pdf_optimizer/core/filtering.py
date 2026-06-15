import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Optional
import logging

logger = logging.getLogger("PDFOptimizer.filtering")


def parse_since(spec: str) -> timedelta:
    """
    Парсит строку времени в объект timedelta.
    Поддерживаемые форматы: 30m (минуты), 24h (часы), 7d (дни), 2w (недели), 3mo (месяцы), 1y (годы).
    """
    spec = spec.strip().lower()

    # Регулярное выражение для поиска числа и единицы измерения
    match = re.fullmatch(r'^(\d+)(m|h|d|w|mo|y)$', spec)
    if not match:
        raise ValueError(
            f"Неверный формат времени: '{spec}'. "
            "Используйте формат вида '24h', '7d', '2w', '3mo', '1y', '30m'."
        )

    value = int(match.group(1))
    unit = match.group(2)

    if unit == 'm':
        return timedelta(minutes=value)
    elif unit == 'h':
        return timedelta(hours=value)
    elif unit == 'd':
        return timedelta(days=value)
    elif unit == 'w':
        return timedelta(weeks=value)
    elif unit == 'mo':
        # Приближенно считаем месяц за 30 дней
        return timedelta(days=value * 30)
    elif unit == 'y':
        # Приближенно считаем год за 365 дней
        return timedelta(days=value * 365)

    raise ValueError(f"Неизвестная единица измерения: {unit}")


def filter_by_mtime(files: List[Path], since_spec: str, now: Optional[datetime] = None) -> List[Path]:
    """
    Отфильтровывает список файлов, оставляя только те, которые были изменены
    не позднее, чем `since_spec` времени назад.
    """
    try:
        time_delta = parse_since(since_spec)
    except ValueError as e:
        logger.error(f"Ошибка фильтрации времени: {e}")
        # Если формат неверный, лучше вернуть пустой список, чтобы не обработать случайно всё
        return []

    if now is None:
        now = datetime.now(timezone.utc)

    threshold_time = now - time_delta
    filtered_files = []

    for file_path in files:
        try:
            # Получаем mtime файла (время последней модификации)
            # st_mtime возвращает timestamp в секундах
            mtime_timestamp = file_path.stat().st_mtime
            # Конвертируем в datetime (UTC) для корректного сравнения
            file_mtime = datetime.fromtimestamp(mtime_timestamp, tz=timezone.utc)

            if file_mtime >= threshold_time:
                filtered_files.append(file_path)

        except OSError as e:
            logger.warning(f"Не удалось получить доступ к файлу для проверки mtime {file_path}: {e}")
            continue

    logger.info(
        f"Фильтрация по времени (since={since_spec}): "
        f"осталось {len(filtered_files)} из {len(files)} файлов."
    )
    return filtered_files