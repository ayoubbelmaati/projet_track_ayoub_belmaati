"""API HTTP du festival (FastAPI) : lecture, écriture admin et sites web."""

import threading
from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from datetime import date, datetime
from pathlib import Path
from typing import Any, Literal

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from deauville.errors import (
    ConflictError,
    FestivalError,
    InvalidError,
    NotFoundError,
    StorageError,
)
from deauville.festival import Festival
from deauville.models import Artist, Performance
from deauville.storage import Storage

PACKAGE_DIR = Path(__file__).parent
WEB_DIR = PACKAGE_DIR / "web" / "public"
ADMIN_DIR = PACKAGE_DIR / "web" / "admin"

# type d'erreur -> statut HTTP (section Errors de API.md)
STATUSES = (
    (NotFoundError, 404),
    (ConflictError, 409),
    (InvalidError, 422),
    (StorageError, 500),
)


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


def create_app(storage: Storage) -> FastAPI:
    """Construit l'application autour d'un stockage donné.

    Le fichier est la source de vérité : chaque requête relit le festival,
    et une écriture le sauvegarde. Un verrou évite que deux requêtes
    simultanées s'écrasent.
    """
    app = FastAPI(title="Deauville Festival du Rire")
    lock = threading.Lock()

    def read_file() -> Festival:
        try:
            return storage.load()
        except (OSError, ValueError, KeyError) as error:
            raise StorageError("The data file cannot be read.") from error

    def write_file(festival: Festival) -> None:
        try:
            storage.save(festival)
        except OSError as error:
            raise StorageError("The data file cannot be written.") from error

    @contextmanager
    def opened() -> Iterator[Festival]:
        with lock:
            yield read_file()

    @app.exception_handler(FestivalError)
    async def festival_error_handler(
        request: Request, error: FestivalError
    ) -> JSONResponse:
        status = 400
        for error_type, code in STATUSES:
            if isinstance(error, error_type):
                status = code
                break
        return JSONResponse(
            status_code=status, content={"detail": str(error)}
        )

    # --- lecture ---
    @app.get("/api/festival")
    def festival_info() -> dict[str, Any]:
        with opened() as festival:
            return festival.to_view()

    @app.get("/api/venues")
    def list_venues() -> list[dict[str, Any]]:
        with opened() as festival:
            return [v.to_view() for v in festival.venues]

    @app.get("/api/artists")
    def list_artists() -> list[dict[str, str]]:
        with opened() as festival:
            artists = sorted(festival.artists, key=lambda a: a.slug)
            return [a.to_view() for a in artists]

    @app.get("/api/programme")
    def programme(
        day: date | None = None, venue: str | None = None
    ) -> list[dict[str, Any]]:
        with opened() as festival:
            if venue is not None:
                festival.find_venue(venue)  # 404 si inconnue
            return [p.to_view() for p in festival.programme(day, venue)]

    @app.get("/api/now")
    def now(at: datetime | None = None) -> dict[str, Any]:
        moment = (at or datetime.now()).replace(tzinfo=None)
        with opened() as festival:
            return {
                "at": moment.isoformat(timespec="minutes"),
                "now_playing": [
                    p.to_view() for p in festival.now_playing(moment)
                ],
                "up_next": [p.to_view() for p in festival.up_next(moment, 3)],
            }

    @app.get("/api/performances/{performance_id}")
    def performance_detail(performance_id: str) -> dict[str, Any]:
        with opened() as festival:
            return festival.find_performance(performance_id).to_view()

    @app.get("/api/artists/{slug}")
    def artist_detail(slug: str) -> dict[str, Any]:
        with opened() as festival:
            artist = festival.find_artist(slug)
            return {
                **artist.to_view(),
                "performances": [
                    p.to_view() for p in festival.performances_of(artist)
                ],
            }

    # --- écriture (admin) ---
    @app.post("/api/artists", status_code=201)
    def create_artist(body: ArtistBody) -> dict[str, str]:
        with opened() as festival:
            artist = festival.add_artist(
                Artist(name=body.name, bio=body.bio, photo_url=body.photo_url)
            )
            write_file(festival)
            return artist.to_view()

    @app.post("/api/performances", status_code=201)
    def create_performance(body: PerformanceBody) -> dict[str, Any]:
        with opened() as festival:
            performance = festival.add_performance(body.to_performance())
            write_file(festival)
            return performance.to_view()

    @app.put("/api/performances/{performance_id}")
    def replace_performance(
        performance_id: str, body: PerformanceBody
    ) -> dict[str, Any]:
        with opened() as festival:
            old = festival.find_performance(performance_id)
            participants = (
                old.participants
                if body.participants is None
                else body.participants
            )
            new = festival.replace_performance(
                performance_id, body.to_performance(participants)
            )
            write_file(festival)
            return new.to_view()

    @app.delete("/api/performances/{performance_id}", status_code=204)
    def cancel_performance(performance_id: str) -> Response:
        with opened() as festival:
            festival.cancel_performance(performance_id)
            write_file(festival)
        return Response(status_code=204)

    @app.post(
        "/api/performances/{performance_id}/participants", status_code=201
    )
    def register_participant(
        performance_id: str, body: ParticipantBody
    ) -> dict[str, Any]:
        with opened() as festival:
            performance = festival.register_participant(
                performance_id, body.name
            )
            write_file(festival)
            return performance.to_view()

    # --- sites : /admin avant / ---
    app.mount(
        "/admin", StaticFiles(directory=ADMIN_DIR, html=True), name="admin"
    )
    app.mount("/", StaticFiles(directory=WEB_DIR, html=True), name="website")

    return app