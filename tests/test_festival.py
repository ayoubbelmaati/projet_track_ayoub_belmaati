from datetime import date, datetime

import pytest

from deauville.festival import Festival
from deauville.models import Artist, Performance, Venue


@pytest.fixture
def festival() -> Festival:
    return Festival(
        name="Test",
        first_day=date(2027, 6, 10),
        last_day=date(2027, 6, 13),
        venues=[Venue("Salle A", 100, "1 rue A"),
                Venue("Salle B", 50, "2 rue B")],
        artists=[Artist("Ana"), Artist("Ben"), Artist("Cleo")],
    )


def solo(venue: str, start: str, duration: int, artist: str) -> Performance:
    return Performance(kind="solo", title="Solo", venue=venue,
                       start=datetime.fromisoformat(start),
                       duration_minutes=duration, artist=artist)


def lineup(
    venue: str, start: str, duration: int, host: str, acts: list[str]
) -> Performance:
    return Performance(kind="lineup", title="Lineup", venue=venue,
                       start=datetime.fromisoformat(start),
                       duration_minutes=duration, host=host, acts=acts)


def test_venue_busy(festival: Festival) -> None:
    festival.add_performance(solo("salle-a", "2027-06-10T20:00", 60, "ana"))
    with pytest.raises(ValueError):
        festival.add_performance(
            solo("salle-a", "2027-06-10T20:30", 60, "ben"))


def test_artist_busy_in_another_venue(festival: Festival) -> None:
    festival.add_performance(solo("salle-a", "2027-06-10T20:00", 60, "ana"))
    with pytest.raises(ValueError):
        festival.add_performance(
            solo("salle-b", "2027-06-10T20:30", 60, "ana"))


def test_artist_busy_as_act_of_a_lineup(festival: Festival) -> None:
    festival.add_performance(solo("salle-a", "2027-06-10T20:00", 60, "ana"))
    with pytest.raises(ValueError):
        festival.add_performance(
            lineup("salle-b", "2027-06-10T20:30", 60, "ben", ["ana", "cleo"]))


def test_back_to_back_is_allowed(festival: Festival) -> None:
    festival.add_performance(solo("salle-a", "2027-06-10T20:00", 60, "ana"))
    festival.add_performance(solo("salle-a", "2027-06-10T21:00", 60, "ana"))
    assert len(festival.performances) == 2


def test_show_at_1am_belongs_to_previous_day(festival: Festival) -> None:
    performance = festival.add_performance(
        solo("salle-a", "2027-06-11T01:00", 60, "ana"))
    assert performance.festival_day == date(2027, 6, 10)
    assert festival.programme(date(2027, 6, 10)) == [performance]


def test_day_outside_festival(festival: Festival) -> None:
    with pytest.raises(ValueError):
        festival.add_performance(
            solo("salle-a", "2027-06-20T20:00", 60, "ana"))


@pytest.mark.parametrize("duration", [0, 361])
def test_invalid_duration(duration: int) -> None:
    with pytest.raises(ValueError):
        solo("salle-a", "2027-06-10T20:00", duration, "ana")


def test_unknown_venue(festival: Festival) -> None:
    with pytest.raises(ValueError):
        festival.add_performance(
            solo("nowhere", "2027-06-10T20:00", 60, "ana"))


def test_unknown_artist(festival: Festival) -> None:
    with pytest.raises(ValueError):
        festival.add_performance(
            solo("salle-a", "2027-06-10T20:00", 60, "nobody"))


def test_now_playing_and_up_next(festival: Festival) -> None:
    first = festival.add_performance(
        solo("salle-a", "2027-06-10T20:00", 60, "ana"))
    second = festival.add_performance(
        solo("salle-a", "2027-06-10T21:00", 60, "ben"))
    at = datetime(2027, 6, 10, 20, 30)
    assert festival.now_playing(at) == [first]
    assert festival.up_next(at) == [second]


def test_cancel_frees_the_slot(festival: Festival) -> None:
    performance = festival.add_performance(
        solo("salle-a", "2027-06-10T20:00", 60, "ana"))
    festival.cancel_performance(performance.id)
    festival.add_performance(solo("salle-a", "2027-06-10T20:00", 60, "ana"))