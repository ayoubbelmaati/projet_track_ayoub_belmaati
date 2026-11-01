from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from deauville.api import create_app
from deauville.festival import Festival
from deauville.storage import JsonStorage


def make_artist(client: TestClient, name: str) -> str:
    response = client.post("/api/artists", json={"name": name})
    assert response.status_code == 201
    return response.json()["slug"]


def solo_body(
    artist: str,
    venue: str = "le-kiosque",
    start: str = "2027-06-13T07:00",
    duration: int = 45,
) -> dict[str, Any]:
    return {"kind": "solo", "title": "Test Solo", "venue": venue,
            "start": start, "duration_minutes": duration,
            "artist": artist, "min_age": 0}


def lineup_body(
    host: str,
    acts: list[str],
    venue: str = "grand-casino",
    start: str = "2027-06-13T07:00",
    duration: int = 60,
) -> dict[str, Any]:
    return {"kind": "lineup", "title": "Test Lineup", "venue": venue,
            "start": start, "duration_minutes": duration,
            "host": host, "acts": acts}


def workshop_body(
    teacher: str,
    maximum: int,
    venue: str = "le-kiosque",
    start: str = "2027-06-13T07:00",
) -> dict[str, Any]:
    return {"kind": "workshop", "title": "Test Lab", "venue": venue,
            "start": start, "duration_minutes": 60,
            "teacher": teacher, "max_participants": maximum}


def titles(items: list[dict[str, Any]]) -> list[str]:
    return [item["title"] for item in items]


# ------------------------------------------------------------ lecture
def test_festival(client: TestClient) -> None:
    response = client.get("/api/festival")
    assert response.status_code == 200
    assert response.json() == {
        "name": "Deauville Festival du Rire 2027",
        "first_day": "2027-06-10",
        "last_day": "2027-06-13",
        "days": ["2027-06-10", "2027-06-11", "2027-06-12", "2027-06-13"],
    }


def test_venues(client: TestClient) -> None:
    venues = client.get("/api/venues").json()
    assert len(venues) == 4
    for venue in venues:
        assert set(venue) == {"slug", "name", "capacity", "address"}
    assert "le-kiosque" in [v["slug"] for v in venues]


def test_artists_are_sorted_by_slug(client: TestClient) -> None:
    artists = client.get("/api/artists").json()
    assert len(artists) == 12
    slugs = [a["slug"] for a in artists]
    assert slugs == sorted(slugs)
    assert artists[0]["name"] == "Élodie Marchal"
    assert set(artists[0]) == {"slug", "name", "bio", "photo_url"}


def test_programme_of_a_day_ends_with_after_hours(client: TestClient) -> None:
    response = client.get("/api/programme", params={"day": "2027-06-11"})
    assert response.status_code == 200
    shows = response.json()
    assert {s["festival_day"] for s in shows} == {"2027-06-11"}
    assert shows[-1]["title"] == "After Hours"
    starts = [s["start"] for s in shows]
    assert starts == sorted(starts)


def test_programme_filter_by_venue(client: TestClient) -> None:
    shows = client.get("/api/programme",
                       params={"venue": "le-kiosque"}).json()
    assert len(shows) == 7
    assert {s["venue"] for s in shows} == {"le-kiosque"}


def test_programme_filters_combined(client: TestClient) -> None:
    shows = client.get("/api/programme", params={
        "day": "2027-06-11", "venue": "le-kiosque"}).json()
    assert shows
    assert {s["festival_day"] for s in shows} == {"2027-06-11"}
    assert {s["venue"] for s in shows} == {"le-kiosque"}


def test_programme_unknown_venue(client: TestClient) -> None:
    response = client.get("/api/programme", params={"venue": "nowhere"})
    assert response.status_code == 404
    assert response.json() == {"detail": "No venue 'nowhere'."}


def test_programme_bad_day(client: TestClient) -> None:
    response = client.get("/api/programme", params={"day": "June 11"})
    assert response.status_code == 422
    assert isinstance(response.json()["detail"], list)


def test_lineup_detail(client: TestClient) -> None:
    response = client.get("/api/performances/le-kiosque-2027-06-12-0100")
    assert response.status_code == 200
    expected = {
        "id": "le-kiosque-2027-06-12-0100",
        "kind": "lineup",
        "title": "After Hours",
        "venue": "le-kiosque",
        "venue_name": "Le Kiosque",
        "start": "2027-06-12T01:00",
        "end": "2027-06-12T02:00",
        "duration_minutes": 60,
        "festival_day": "2027-06-11",
        "description": "The last show of Friday night, after midnight.",
        "summary": "hosted by Tom Vasseur, with Hugo Lemaire, Maya Choukri",
        "capacity": 120,
        "host": "tom-vasseur",
        "acts": ["hugo-lemaire", "maya-choukri"],
        "artists": [
            {"slug": "tom-vasseur", "name": "Tom Vasseur"},
            {"slug": "hugo-lemaire", "name": "Hugo Lemaire"},
            {"slug": "maya-choukri", "name": "Maya Choukri"},
        ],
    }
    body = response.json()
    for key, value in expected.items():
        assert body[key] == value, key


def test_workshop_detail(client: TestClient) -> None:
    body = client.get("/api/performances/la-cabane-2027-06-11-1030").json()
    assert body["kind"] == "workshop"
    assert body["places_left"] == 9
    for key in ("teacher", "max_participants", "participants"):
        assert key in body


@pytest.mark.parametrize("performance_id, expected", [
    ("le-kiosque-2027-06-12-0100",
     "hosted by Tom Vasseur, with Hugo Lemaire, Maya Choukri"),
    ("la-cabane-2027-06-11-1030", "with Inès Moreau, 3/12 places taken"),
    ("grand-casino-2027-06-11-2030", "Léa Fontaine"),
])
def test_summaries_follow_the_brief(client: TestClient, performance_id: str, expected: str) -> None:
    body = client.get(f"/api/performances/{performance_id}").json()
    assert body["summary"] == expected


def test_performance_not_found(client: TestClient) -> None:
    response = client.get("/api/performances/nope")
    assert response.status_code == 404
    assert response.json() == {"detail": "No performance 'nope'."}


def test_artist_page(client: TestClient) -> None:
    response = client.get("/api/artists/max-pellerin")
    assert response.status_code == 200
    body = response.json()
    assert body["slug"] == "max-pellerin"
    shows = titles(body["performances"])
    assert len(shows) == 4
    assert shows[0] == "Opening Gala"
    assert shows[-1] == "Closing Gala"


def test_artist_not_found(client: TestClient) -> None:
    response = client.get("/api/artists/nobody")
    assert response.status_code == 404
    assert response.json() == {"detail": "No artist 'nobody'."}


def test_now_on_stage_and_up_next(client: TestClient) -> None:
    body = client.get("/api/now", params={"at": "2027-06-11T21:00"}).json()
    assert body["at"] == "2027-06-11T21:00"
    assert titles(body["now_playing"]) == ["Tall Tales"]
    assert titles(body["up_next"]) == [
        "Straight Face", "Late Laughs", "After Hours"]


def test_now_after_midnight(client: TestClient) -> None:
    body = client.get("/api/now", params={"at": "2027-06-12T01:30"}).json()
    assert titles(body["now_playing"]) == ["After Hours"]


def test_now_without_at_has_the_three_keys(client: TestClient) -> None:
    body = client.get("/api/now").json()
    assert set(body) == {"at", "now_playing", "up_next"}
    assert len(body["up_next"]) <= 3


def test_website_admin_and_docs_are_served(client: TestClient) -> None:
    for path in ("/", "/admin/", "/docs"):
        response = client.get(path)
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]


# ------------------------------------------------------------ création
def test_create_a_solo_show(client: TestClient) -> None:
    artist = make_artist(client, "Zed Test")
    response = client.post("/api/performances", json=solo_body(artist))
    assert response.status_code == 201
    created = response.json()
    assert created["id"] == "le-kiosque-2027-06-13-0700"
    assert created["kind"] == "solo"
    assert created["festival_day"] == "2027-06-13"

    day = client.get("/api/programme", params={"day": "2027-06-13"}).json()
    assert created["id"] in [s["id"] for s in day]
    assert client.get(f"/api/performances/{created['id']}").status_code == 200


def test_changes_are_saved_in_the_file(client: TestClient, data_file: Path) -> None:
    teacher = make_artist(client, "Prof Test")
    lab = client.post("/api/performances",
                      json=workshop_body(teacher, 3)).json()
    client.post(f"/api/performances/{lab['id']}/participants",
                json={"name": "Jo Doe"})

    again = TestClient(create_app(JsonStorage(data_file)))
    saved = again.get(f"/api/performances/{lab['id']}").json()
    assert saved["participants"] == ["Jo Doe"]
    assert "prof-test" in [a["slug"] for a in again.get("/api/artists").json()]


def test_venue_busy(client: TestClient) -> None:
    first = make_artist(client, "Zed Test")
    second = make_artist(client, "Yan Test")
    client.post("/api/performances", json=solo_body(first))
    before = client.get("/api/programme").json()

    response = client.post(
        "/api/performances", json=solo_body(second, start="2027-06-13T07:30"))
    assert response.status_code == 409
    assert "busy" in response.json()["detail"]
    assert client.get("/api/programme").json() == before


def test_artist_busy_in_another_venue(client: TestClient) -> None:
    artist = make_artist(client, "Zed Test")
    client.post("/api/performances", json=solo_body(artist))
    response = client.post("/api/performances", json=solo_body(
        artist, venue="grand-casino", start="2027-06-13T07:15"))
    assert response.status_code == 409
    assert "Zed Test" in response.json()["detail"]


def test_artist_busy_as_an_act_of_a_lineup(client: TestClient) -> None:
    busy = make_artist(client, "Zed Test")
    host = make_artist(client, "Hana Test")
    other = make_artist(client, "Yan Test")
    client.post("/api/performances", json=solo_body(busy))
    response = client.post("/api/performances", json=lineup_body(
        host, [busy, other], start="2027-06-13T07:15"))
    assert response.status_code == 409
    assert "Zed Test" in response.json()["detail"]


@pytest.mark.parametrize("start", ["2027-06-09T12:00", "2027-06-14T12:00"])
def test_date_outside_the_festival(client: TestClient, start: str) -> None:
    artist = make_artist(client, "Zed Test")
    response = client.post("/api/performances",
                           json=solo_body(artist, start=start))
    assert response.status_code == 409
    assert "outside the festival" in response.json()["detail"]


def test_lineup_with_one_act(client: TestClient) -> None:
    host = make_artist(client, "Hana Test")
    act = make_artist(client, "Zed Test")
    response = client.post("/api/performances", json=lineup_body(host, [act]))
    assert response.status_code == 422
    assert "two acts" in response.json()["detail"]


def test_lineup_three_acts_need_36_minutes(client: TestClient) -> None:
    host = make_artist(client, "Hana Test")
    acts = [make_artist(client, f"Act {n} Test") for n in (1, 2, 3)]
    short = client.post("/api/performances",
                        json=lineup_body(host, acts, duration=35))
    assert short.status_code == 422
    ok = client.post("/api/performances",
                     json=lineup_body(host, acts, duration=36))
    assert ok.status_code == 201


def test_unknown_venue_and_artist_in_the_body(client: TestClient) -> None:
    artist = make_artist(client, "Zed Test")
    venue = client.post("/api/performances",
                        json=solo_body(artist, venue="nowhere"))
    assert venue.status_code == 404
    unknown = client.post("/api/performances", json=solo_body("nobody"))
    assert unknown.status_code == 404


@pytest.mark.parametrize("change", [
    {"duration_minutes": 0},
    {"duration_minutes": 361},
    {"min_age": 19},
    {"title": "   "},
    {"kind": "circus"},
])
def test_invalid_values_are_refused(client: TestClient, change: dict[str, Any]) -> None:
    artist = make_artist(client, "Zed Test")
    body = {**solo_body(artist), **change}
    assert client.post("/api/performances", json=body).status_code == 422


def test_missing_field_and_wrong_type(client: TestClient) -> None:
    artist = make_artist(client, "Zed Test")
    missing = solo_body(artist)
    del missing["venue"]
    response = client.post("/api/performances", json=missing)
    assert response.status_code == 422
    assert isinstance(response.json()["detail"], list)

    wrong = {**solo_body(artist), "duration_minutes": "long"}
    assert client.post("/api/performances", json=wrong).status_code == 422


# ------------------------------------------------------- PUT et DELETE
def test_put_changes_the_id(client: TestClient) -> None:
    artist = make_artist(client, "Zed Test")
    old = client.post("/api/performances", json=solo_body(artist)).json()

    response = client.put(f"/api/performances/{old['id']}",
                          json=solo_body(artist, start="2027-06-13T08:00"))
    assert response.status_code == 200
    assert response.json()["id"] == "le-kiosque-2027-06-13-0800"
    assert client.get(f"/api/performances/{old['id']}").status_code == 404
    assert client.get(
        "/api/performances/le-kiosque-2027-06-13-0800").status_code == 200


def test_put_to_another_venue(client: TestClient) -> None:
    artist = make_artist(client, "Zed Test")
    old = client.post("/api/performances", json=solo_body(artist)).json()
    response = client.put(f"/api/performances/{old['id']}",
                          json=solo_body(artist, venue="grand-casino"))
    assert response.status_code == 200
    assert response.json()["id"] == "grand-casino-2027-06-13-0700"


def test_refused_put_changes_nothing(client: TestClient) -> None:
    artist = make_artist(client, "Zed Test")
    mine = client.post("/api/performances", json=solo_body(artist)).json()
    busy = [s for s in client.get(
        "/api/programme", params={"venue": "le-kiosque"}).json()
        if s["id"] != mine["id"]][0]
    before = client.get("/api/programme").json()

    response = client.put(f"/api/performances/{mine['id']}",
                          json=solo_body(artist, start=busy["start"]))
    assert response.status_code == 409
    assert client.get("/api/programme").json() == before
    unchanged = client.get(f"/api/performances/{mine['id']}").json()
    assert unchanged["start"] == "2027-06-13T07:00"


def test_put_to_an_unknown_venue_changes_nothing(client: TestClient) -> None:
    artist = make_artist(client, "Zed Test")
    mine = client.post("/api/performances", json=solo_body(artist)).json()
    before = client.get("/api/programme").json()
    response = client.put(f"/api/performances/{mine['id']}",
                          json=solo_body(artist, venue="nowhere"))
    assert response.status_code == 404
    assert client.get("/api/programme").json() == before


def test_put_unknown_performance(client: TestClient) -> None:
    artist = make_artist(client, "Zed Test")
    response = client.put("/api/performances/nope", json=solo_body(artist))
    assert response.status_code == 404


def test_put_keeps_the_participants_of_a_workshop(client: TestClient) -> None:
    teacher = make_artist(client, "Prof Test")
    lab = client.post("/api/performances",
                      json=workshop_body(teacher, 3)).json()
    client.post(f"/api/performances/{lab['id']}/participants",
                json={"name": "Jo Doe"})

    moved = client.put(f"/api/performances/{lab['id']}", json=workshop_body(
        teacher, 3, start="2027-06-13T08:00")).json()
    assert moved["participants"] == ["Jo Doe"]


def test_delete_twice(client: TestClient) -> None:
    artist = make_artist(client, "Zed Test")
    created = client.post("/api/performances", json=solo_body(artist)).json()
    url = f"/api/performances/{created['id']}"

    first = client.delete(url)
    assert first.status_code == 204
    assert first.content == b""

    second = client.delete(url)
    assert second.status_code == 404
    assert isinstance(second.json()["detail"], str)


# ------------------------------------------------------- participants
def test_workshop_full_and_duplicate_name(client: TestClient) -> None:
    teacher = make_artist(client, "Prof Test")
    lab = client.post("/api/performances",
                      json=workshop_body(teacher, 2)).json()
    assert lab["places_left"] == 2
    assert lab["capacity"] == 2
    url = f"/api/performances/{lab['id']}/participants"

    first = client.post(url, json={"name": "Jo Doe"})
    assert first.status_code == 201
    assert first.json()["kind"] == "workshop"
    assert first.json()["places_left"] == 1

    duplicate = client.post(url, json={"name": "  jo   doe "})
    assert duplicate.status_code == 409

    assert client.post(url, json={"name": "Max"}).status_code == 201
    full = client.post(url, json={"name": "Zoe"})
    assert full.status_code == 409
    after = client.get(f"/api/performances/{lab['id']}").json()
    assert after["places_left"] == 0
    assert after["participants"] == ["Jo Doe", "Max"]


def test_workshop_places_limited_by_the_venue(client: TestClient) -> None:
    teacher = make_artist(client, "Prof Test")
    seats = {v["slug"]: v["capacity"]
             for v in client.get("/api/venues").json()}["grand-casino"]
    response = client.post("/api/performances", json=workshop_body(
        teacher, 999, venue="grand-casino"))
    assert response.status_code == 201
    body = response.json()
    assert body["capacity"] == min(999, seats)
    assert body["places_left"] == min(999, seats)


def test_only_workshops_take_participants(client: TestClient) -> None:
    artist = make_artist(client, "Zed Test")
    show = client.post("/api/performances", json=solo_body(artist)).json()
    response = client.post(f"/api/performances/{show['id']}/participants",
                           json={"name": "Jo"})
    assert response.status_code == 422


def test_register_in_an_unknown_performance(client: TestClient) -> None:
    response = client.post("/api/performances/nope/participants",
                           json={"name": "Jo"})
    assert response.status_code == 404


def test_register_without_a_name(client: TestClient) -> None:
    teacher = make_artist(client, "Prof Test")
    lab = client.post("/api/performances",
                      json=workshop_body(teacher, 2)).json()
    url = f"/api/performances/{lab['id']}/participants"
    assert client.post(url, json={}).status_code == 422
    assert client.post(url, json={"name": "   "}).status_code == 422


# ------------------------------------------------------------ artistes
def test_create_artist_then_duplicate(client: TestClient) -> None:
    created = client.post("/api/artists", json={"name": "Zoé Tanguy"})
    assert created.status_code == 201
    assert created.json()["slug"] == "zoe-tanguy"

    duplicate = client.post("/api/artists", json={"name": "zoe tanguy"})
    assert duplicate.status_code == 409
    assert "already exists" in duplicate.json()["detail"]
    assert len(client.get("/api/artists").json()) == 13


def test_create_artist_without_a_name(client: TestClient) -> None:
    assert client.post("/api/artists", json={}).status_code == 422
    assert client.post("/api/artists",
                       json={"name": "  "}).status_code == 422


# ------------------------------------- fichier illisible ou non écrivable
class BrokenStorage(JsonStorage):
    """Se lit normalement mais ne peut jamais écrire."""

    def save(self, festival: Festival) -> None:
        raise OSError("disk is full")


def test_unwritable_file_gives_500_and_changes_nothing(data_file: Path) -> None:
    client = TestClient(create_app(BrokenStorage(data_file)))
    artist = client.get("/api/artists").json()[0]["slug"]

    response = client.post("/api/performances", json=solo_body(artist))
    assert response.status_code == 500
    assert response.json() == {"detail": "The data file cannot be written."}
    assert client.get(
        "/api/performances/le-kiosque-2027-06-13-0700").status_code == 404

    refused = client.post("/api/artists", json={"name": "Zoé Tanguy"})
    assert refused.status_code == 500
    assert len(client.get("/api/artists").json()) == 12


def test_missing_data_file_gives_500(client: TestClient, data_file: Path) -> None:
    data_file.unlink()
    response = client.get("/api/venues")
    assert response.status_code == 500
    assert response.json() == {"detail": "The data file cannot be read."}


def test_corrupted_data_file_gives_500(client: TestClient, data_file: Path) -> None:
    data_file.write_text("{ not json", encoding="utf-8")
    response = client.post("/api/artists", json={"name": "Zoé Tanguy"})
    assert response.status_code == 500
    assert response.json() == {"detail": "The data file cannot be read."}