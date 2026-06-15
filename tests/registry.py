import os
import pytest
from pathlib import Path
from pdf_optimizer.registry.store import RegistryStore


@pytest.fixture
def registry(tmp_path: Path):
    """Фикстура, создающая временную БД для каждого теста."""
    db_path = tmp_path / "test_registry.sqlite"
    return RegistryStore(db_path)


def test_create_job(registry: RegistryStore):
    """Проверка создания записи о задаче в таблице jobs."""
    job_id = registry.create_job("api", "/data/pdfs", {"quality": "fast"})
    assert job_id == 1


def test_exclude_already_processed(registry: RegistryStore, tmp_path: Path):
    """Проверка логики идемпотентности (пропуск уже сжатых файлов)."""
    pdf_path = tmp_path / "test.pdf"
    pdf_path.touch()

    # 1. Файл новый, его нет в БД -> должен попасть в обработку
    assert len(registry.exclude_already_processed([pdf_path])) == 1

    # 2. Записываем результат обработки в БД
    current_mtime = pdf_path.stat().st_mtime
    registry.record_results(job_id=1, file_path=pdf_path, current_mtime=current_mtime, size_before=1000, size_after=500)

    # 3. Теперь файл должен быть исключен (уже обработан)
    assert len(registry.exclude_already_processed([pdf_path])) == 0

    # 4. Имитируем модификацию файла (изменился mtime)
    new_mtime = current_mtime + 100
    os.utime(pdf_path, (new_mtime, new_mtime))

    # 5. Файл обновился -> должен снова попасть в обработку
    assert len(registry.exclude_already_processed([pdf_path])) == 1