import shutil
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from deauville.api import create_app
from deauville.storage import JsonStorage

SOURCE = Path(__file__).parent.parent / "data" / "festival.json"


@pytest.fixture(scope="session", autouse=True)
def real_data_file_is_never_touched() -> Iterator[None]:
    """Échoue si un test modifie le vrai data/festival.json."""
    before = SOURCE.read_bytes()
    yield
    assert SOURCE.read_bytes() == before, "a test changed data/festival.json"


@pytest.fixture
def data_file(tmp_path: Path) -> Path:
    """Une copie fraîche des données pour chaque test."""
    path = tmp_path / "festival.json"
    shutil.copy(SOURCE, path)
    return path


@pytest.fixture
def client(data_file: Path) -> TestClient:
    return TestClient(create_app(JsonStorage(data_file)))