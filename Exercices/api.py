"""API HTTP du festival (FastAPI) : lecture, écriture admin et sites web."""

from collections.abc import Iterable
from datetime import date, datetime
from pathlib import Path
from typing import Any, Literal

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from festival import (
    Artist,
    ConflictError,
    FestivalError,
    InvalidError,
    NotFoundError,
    Performance,
    get_artists,
    get_festival,
    get_programme,
    get_venues,
    load_festival,
    save_festival,
)

app = FastAPI()
festival = load_festival()


STATUSES = (
    (NotFoundError, 404),
    (ConflictError, 409),
    (InvalidError, 422),
)


@app.exception_handler(FestivalError)
async def festival_error_handler(
    request: Request, error: FestivalError
) -> JSONResponse:
    """Traduit une erreur de règle en réponse HTTP (404, 409, 422 ou 400)."""
    status = 400
    for error_type, code in STATUSES:
        if isinstance(error, error_type):
            status = code
            break
    return JSONResponse(status_code=status, content={"detail": str(error)})


class PerformanceBody(BaseModel):
    """Corps JSON pour créer ou remplacer un spectacle."""

    kind: Literal["lineup", "workshop", "solo"]
    title: str
    venue: str
    start: datetime
    duration_minutes: int
    description: str = ""
    host: str | None = None
    acts: list[str] = []
    artist: str | None = None
    min_age: int | None = None
    teacher: str | None = None
    max_participants: int | None = None
    participants: list[str] | None = None

    def to_performance(self, participants: Iterable[str] = ()) -> Performance:
        """Construit le Performance du festival (les règles s'y appliquent)."""
        return Performance(
            kind=self.kind,
            title=self.title,
            venue=self.venue,
            start=self.start.replace(tzinfo=None),
            duration_minutes=self.duration_minutes,
            description=self.description,
            host=self.host,
            acts=tuple(self.acts),
            artist=self.artist,
            min_age=self.min_age,
            teacher=self.teacher,
            max_participants=self.max_participants,
            participants=tuple(participants),
        )


class ParticipantBody(BaseModel):
    """Corps JSON pour inscrire un participant à un atelier."""

    name: str


class ArtistBody(BaseModel):
    """Corps JSON pour créer un artiste."""

    name: str
    bio: str = ""
    photo_url: str = ""


# --- lecture ---
@app.get("/api/festival")
def festival_info() -> dict[str, Any]:
    """Infos générales du festival."""
    return get_festival(festival)


@app.get("/api/venues")
def list_venues() -> list[dict[str, Any]]:
    """Liste des salles."""
    return get_venues(festival)


@app.get("/api/artists")
def list_artists() -> list[dict[str, str]]:
    """Liste des artistes."""
    return get_artists(festival)


@app.get("/api/programme")
def programme(
    day: date | None = None, venue: str | None = None
) -> list[dict[str, Any]]:
    """Programme, filtrable par jour et par salle."""
    if venue is not None:
        festival.find_venue(venue)  # 404 si inconnue
    return [p.to_view() for p in get_programme(festival, day, venue)]


@app.get("/api/now")
def now(at: datetime | None = None) -> dict[str, Any]:
    """Spectacles en cours et trois prochains spectacles."""
    moment = (at or datetime.now()).replace(tzinfo=None)
    return {
        "now_playing": [p.to_view() for p in festival.now_playing(moment)],
        "up_next": [p.to_view() for p in festival.up_next(moment, 3)],
    }


@app.get("/api/performances/{performance_id}")
def performance_detail(performance_id: str) -> dict[str, Any]:
    """Détail d'un spectacle."""
    return festival.find_performance(performance_id).to_view()


@app.get("/api/artists/{slug}")
def artist_detail(slug: str) -> dict[str, Any]:
    """Détail d'un artiste avec ses spectacles."""
    artist = festival.find_artist(slug)
    return {
        **artist.to_view(),
        "performances": [
            p.to_view() for p in festival.performances_of(artist)
        ],
    }


# --- écriture (admin) ---
@app.post("/api/performances", status_code=201)
def create_performance(body: PerformanceBody) -> dict[str, Any]:
    """Crée un spectacle."""
    performance = festival.add_performance(body.to_performance())
    save_festival(festival)
    return performance.to_view()


@app.put("/api/performances/{performance_id}")
def replace_performance(
    performance_id: str, body: PerformanceBody
) -> dict[str, Any]:
    """Remplace un spectacle en gardant ses participants si non fournis."""
    old = festival.find_performance(performance_id)
    participants = (
        old.participants if body.participants is None else body.participants
    )
    new = festival.replace_performance(
        performance_id, body.to_performance(participants)
    )
    save_festival(festival)
    return new.to_view()


@app.delete("/api/performances/{performance_id}", status_code=204)
def cancel_performance(performance_id: str) -> Response:
    """Annule un spectacle."""
    festival.cancel_performance(performance_id)
    save_festival(festival)
    return Response(status_code=204)


@app.post("/api/performances/{performance_id}/participants", status_code=201)
def register_participant(
    performance_id: str, body: ParticipantBody
) -> dict[str, Any]:
    """Inscrit un participant à un atelier."""
    performance = festival.register_participant(performance_id, body.name)
    save_festival(festival)
    return performance.to_view()


@app.post("/api/artists", status_code=201)
def create_artist(body: ArtistBody) -> dict[str, str]:
    """Crée un artiste."""
    artist = festival.add_artist(
        Artist(name=body.name, bio=body.bio, photo_url=body.photo_url)
    )
    save_festival(festival)
    return artist.to_view()


# --- sites : /admin avant / ---
WEB_DIR = Path(__file__).parent.parent / "web" / "public"
ADMIN_DIR = Path(__file__).parent.parent / "web" / "admin"

app.mount("/admin", StaticFiles(directory=ADMIN_DIR, html=True), name="admin")
app.mount("/", StaticFiles(directory=WEB_DIR, html=True), name="website")