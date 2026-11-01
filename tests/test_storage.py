from datetime import date, datetime
from pathlib import Path

import pytest

from deauville.cli import main
from deauville.festival import Festival
from deauville.models import Artist, Performance, Venue
from deauville.storage import JsonStorage, MemoryStorage, Storage


@pytest.fixture
def festival() -> Festival:
    festival = Festival(
        name="Test",
        first_day=date(2027, 6, 10),
        last_day=date(2027, 6, 13),
        venues=[Venue("Salle A", 100, "1 rue A")],
        artists=[Artist("Ana")],
    )
    festival.add_performance(Performance(
        kind="solo", title="Solo Test", venue="salle-a",
        start=datetime(2027, 6, 11, 11, 0), duration_minutes=45,
        artist="ana"))
    return festival


def test_storage_is_abstract() -> None:
    with pytest.raises(TypeError):
        Storage()


def test_memory_storage_keeps_the_festival(festival: Festival) -> None:
    storage = MemoryStorage(festival)
    assert storage.load() is festival
    storage.save(festival)
    assert storage.saves == 1


def test_json_storage_round_trip(festival: Festival, tmp_path: Path) -> None:
    storage = JsonStorage(tmp_path / "festival.json")
    storage.save(festival)
    again = storage.load()
    assert [p.id for p in again.performances] == [
        p.id for p in festival.performances]
    assert [a.slug for a in again.artists] == ["ana"]


def test_cli_uses_the_data_option(festival: Festival, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    path = tmp_path / "other.json"
    JsonStorage(path).save(festival)
    main(["programme", "2027-06-11", "--data", str(path)])
    assert "Solo Test" in capsys.readouterr().out


def test_cli_missing_data_file(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    missing = tmp_path / "nope.json"
    assert main(["venues", "--data", str(missing)]) == 1
    assert "Data file not found" in capsys.readouterr().out