from datetime import date, datetime

import pytest

from deauville.errors import (
    ConflictError,
    FestivalError,
    InvalidError,
    NotFoundError,
)
from deauville.festival import Festival
from deauville.models import Artist, Performance, Venue


@pytest.fixture
def festival() -> Festival:
    return Festival(
        name="Test",
        first_day=date(2027, 6, 10),
        last_day=date(2027, 6, 13),
        venues=[Venue("Salle A", 100, "1 rue A"),
                Venue("Salle B", 50, "2 rue B"),
                Venue("Grand Casino", 650, "3 rue C")],
        artists=[Artist("Ana"), Artist("Ben"),
                 Artist("Cleo"), Artist("Dan")],
    )


def at(text: str) -> datetime:
    return datetime.fromisoformat(text)


def solo(
    venue: str = "salle-a",
    start: str = "2027-06-11T11:00",
    duration: int = 45,
    artist: str = "ana",
    min_age: int | None = None,
) -> Performance:
    return Performance(kind="solo", title="Solo", venue=venue,
                       start=at(start), duration_minutes=duration,
                       artist=artist, min_age=min_age)


def lineup(
    venue: str = "salle-a",
    start: str = "2027-06-11T20:00",
    duration: int = 60,
    host: str = "ana",
    acts: tuple[str, ...] = ("ben", "cleo"),
) -> Performance:
    return Performance(kind="lineup", title="Lineup", venue=venue,
                       start=at(start), duration_minutes=duration,
                       host=host, acts=acts)


def workshop(
    venue: str = "salle-a", start: str = "2027-06-11T10:00", maximum: int = 2
) -> Performance:
    return Performance(kind="workshop", title="Lab", venue=venue,
                       start=at(start), duration_minutes=60,
                       teacher="dan", max_participants=maximum)


# --- portes fermées ---
def test_collections_returned_are_copies(festival: Festival) -> None:
    festival.add_performance(solo())
    festival.performances.append("intrus")
    festival.venues.clear()
    festival.artists.clear()
    assert len(festival.performances) == 1
    assert len(festival.venues) == 3
    assert len(festival.artists) == 4


def test_acts_and_participants_cannot_be_changed(festival: Festival) -> None:
    show = festival.add_performance(lineup())
    lab = festival.add_performance(workshop())
    with pytest.raises(AttributeError):
        show.acts.append("dan")
    with pytest.raises(AttributeError):
        lab.participants.append("intrus")


# --- famille d'erreurs ---
def test_error_types(festival: Festival) -> None:
    festival.add_performance(solo())
    with pytest.raises(ConflictError):
        festival.add_performance(solo(start="2027-06-11T11:30", artist="ben"))
    with pytest.raises(NotFoundError):
        festival.add_performance(solo(venue="nowhere"))
    with pytest.raises(NotFoundError):
        festival.add_performance(solo(artist="nobody"))
    with pytest.raises(ConflictError):  # API.md : hors festival = 409
        festival.add_performance(solo(start="2027-06-20T11:00"))


def test_every_error_is_a_festival_error(festival: Festival) -> None:
    with pytest.raises(FestivalError):
        festival.find_performance("nope")


def test_artist_busy_in_another_venue(festival: Festival) -> None:
    festival.add_performance(solo())
    with pytest.raises(ConflictError):
        festival.add_performance(
            solo(venue="grand-casino", start="2027-06-11T11:30"))


# --- règles de l'étape 9 ---
@pytest.mark.parametrize("age", [-1, 19])
def test_solo_age_out_of_range(age: int) -> None:
    with pytest.raises(InvalidError):
        solo(min_age=age)


def test_lineup_needs_two_acts() -> None:
    with pytest.raises(InvalidError):
        lineup(acts=("ben",))


def test_lineup_act_only_once() -> None:
    with pytest.raises(InvalidError):
        lineup(acts=("ben", "ben"))


def test_lineup_host_is_not_an_act() -> None:
    with pytest.raises(InvalidError):
        lineup(host="ben")


def test_lineup_three_acts_need_36_minutes() -> None:
    acts = ("ben", "cleo", "dan")
    with pytest.raises(InvalidError):
        lineup(duration=35, acts=acts)
    assert lineup(duration=36, acts=acts).duration_minutes == 36


def test_workshop_needs_one_place() -> None:
    with pytest.raises(InvalidError):
        workshop(maximum=0)


def test_workshop_places_limited_by_the_venue(festival: Festival) -> None:
    lab = festival.add_performance(workshop(venue="grand-casino", maximum=999))
    assert lab.places == 650


# --- déplacer / remplacer ---
def test_replace_changes_the_id(festival: Festival) -> None:
    first = festival.add_performance(solo())
    moved = festival.replace_performance(
        first.id, solo(start="2027-06-11T12:00"))
    assert moved.id == "salle-a-2027-06-11-1200"
    with pytest.raises(NotFoundError):
        festival.find_performance(first.id)


def test_refused_move_leaves_the_schedule_unchanged(festival: Festival) -> None:
    first = festival.add_performance(solo())
    festival.add_performance(
        solo(venue="salle-b", start="2027-06-11T15:00", artist="ana"))
    before = festival.performances

    with pytest.raises(ConflictError):
        festival.replace_performance(
            first.id, solo(start="2027-06-11T15:00"))

    assert festival.performances == before
    assert festival.find_performance(first.id).start == at("2027-06-11T11:00")


def test_cancel_unknown_performance(festival: Festival) -> None:
    with pytest.raises(NotFoundError):
        festival.cancel_performance("nope")


# --- participants ---
def test_register_twice_the_same_name(festival: Festival) -> None:
    lab = festival.add_performance(workshop(maximum=5))
    festival.register_participant(lab.id, "Jo Doe")
    with pytest.raises(ConflictError):
        festival.register_participant(lab.id, "  jo   doe ")
    assert len(lab.participants) == 1


def test_register_in_a_full_workshop(festival: Festival) -> None:
    lab = festival.add_performance(workshop(maximum=1))
    festival.register_participant(lab.id, "Jo")
    with pytest.raises(ConflictError):
        festival.register_participant(lab.id, "Max")
    assert lab.places_left == 0


def test_only_workshops_take_participants(festival: Festival) -> None:
    show = festival.add_performance(solo())
    with pytest.raises(InvalidError):
        festival.register_participant(show.id, "Jo")


# --- artistes ---
def test_add_artist_twice(festival: Festival) -> None:
    festival.add_artist(Artist("Zoé Tanguy"))
    with pytest.raises(ConflictError):
        festival.add_artist(Artist("zoe tanguy"))
    assert len(festival.artists) == 5