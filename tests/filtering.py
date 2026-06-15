import os
import pytest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from pdf_optimizer.core.filtering import parse_since, filter_by_mtime


def test_parse_since_valid():
    """Проверка корректного парсинга грамматики времени."""
    assert parse_since("24h") == timedelta(hours=24)
    assert parse_since("7d") == timedelta(days=7)
    assert parse_since("30m") == timedelta(minutes=30)
    assert parse_since("2w") == timedelta(weeks=2)
    assert parse_since("1y") == timedelta(days=365)


def test_parse_since_invalid():
    """Проверка выброса исключения при неверном формате."""
    with pytest.raises(ValueError):
        parse_since("24hours")
    with pytest.raises(ValueError):
        parse_since("abc")


def test_filter_by_mtime(tmp_path: Path):
    """Проверка фильтрации файлов по времени модификации."""
    now = datetime.now(timezone.utc)

    # Создаем два тестовых файла
    old_file = tmp_path / "old.pdf"
    new_file = tmp_path / "new.pdf"
    old_file.touch()
    new_file.touch()

    # Эмулируем mtime: один файл изменен 2 дня назад, другой — 2 часа назад
    old_time = (now - timedelta(days=2)).timestamp()
    new_time = (now - timedelta(hours=2)).timestamp()

    os.utime(old_file, (old_time, old_time))
    os.utime(new_file, (new_time, new_time))

    # Фильтруем за последние 24 часа
    filtered = filter_by_mtime([old_file, new_file], "24h", now=now)

    # Должен остаться только новый файл
    assert len(filtered) == 1
    assert filtered[0] == new_file