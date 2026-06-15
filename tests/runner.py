import pytest
from fastapi.testclient import TestClient
from pdf_optimizer.api.app import app
from pdf_optimizer.registry.store import RegistryStore

# Мок для оркестратора
class DummyRunner:
    def run_job(self, *args, **kwargs):
        pass

@pytest.fixture
def client(tmp_path):
    """Настройка TestClient с подмененными state-переменными."""
    db_path = tmp_path / "test_api.sqlite"
    app.state.registry = RegistryStore(db_path)
    app.state.runner = DummyRunner()
    return TestClient(app)

def test_get_settings(client: TestClient):
    """Тест получения текущей конфигурации."""
    response = client.get("/api/settings")
    assert response.status_code == 200
    data = response.json()
    assert "log_level" in data
    assert "scheduler" in data

def test_create_job_endpoint(client: TestClient):
    """Тест ручного запуска задачи через API."""
    payload = {
        "root_dir": "/tmp/fake_dir",
        "since": "12h",
        "quality": "archive",
        "aggression": "ggg"
    }
    response = client.post("/api/jobs", json=payload)
    assert response.status_code == 202
    assert "успешно добавлена" in response.json()["message"]

def test_scan_directory_not_found(client: TestClient):
    """Тест dry-run сканирования несуществующей папки."""
    payload = {
        "root_dir": "/path/that/does/not/exist/999",
        "since": "24h"
    }
    response = client.post("/api/scan", json=payload)
    assert response.status_code == 404
    assert response.json()["detail"] == "Директория не найдена на сервере"