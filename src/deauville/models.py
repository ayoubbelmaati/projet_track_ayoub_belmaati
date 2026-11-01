"""Modèles du festival : salles, artistes et spectacles avec leurs règles."""

import unicodedata
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from typing import Any

from deauville.errors import ConflictError, InvalidError

KINDS = ("lineup", "workshop", "solo")
MIN_DURATION, MAX_DURATION = 1, 360
ACT_MINUTES, HOST_MINUTES = 10, 3


def make_slug(name: str) -> str:
    """Transforme un nom en identifiant sans accents, en minuscules."""
    name = unicodedata.normalize("NFKD", name)
    name = "".join(c for c in name if not unicodedata.combining(c))
    return "-".join(name.lower().split())


@dataclass
class Venue:
    """Une salle du festival, avec sa capacité et son adresse."""

    name: str
    capacity: int
    address: str
    slug: str = ""

    def __post_init__(self) -> None:
        if not self.slug:
            self.slug = make_slug(self.name)

    def to_view(self) -> dict[str, Any]:
        """Forme renvoyée par l'API."""
        return {
            "slug": self.slug,
            "name": self.name,
            "capacity": self.capacity,
            "address": self.address,
        }


@dataclass(eq=False)
class Artist:
    """Un artiste ; deux artistes sont égaux s'ils ont le même slug."""

    name: str
    bio: str = ""
    photo_url: str = ""
    slug: str = ""

    def __post_init__(self) -> None:
        if not self.slug:
            self.slug = make_slug(self.name)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Artist) and self.slug == other.slug

    def __hash__(self) -> int:
        return hash(self.slug)

    def __str__(self) -> str:
        return self.name

    def to_view(self) -> dict[str, str]:
        """Forme renvoyée par l'API."""
        return {
            "slug": self.slug,
            "name": self.name,
            "bio": self.bio,
            "photo_url": self.photo_url,
        }


@dataclass
class Performance:
    """Un spectacle (lineup, atelier ou solo) qui applique ses règles."""

    kind: str
    title: str
    venue: str
    start: datetime
    duration_minutes: int
    description: str = ""
    id: str = ""
    host: str | None = None
    acts: tuple[str, ...] = ()
    artist: str | None = None
    teacher: str | None = None
    max_participants: int | None = None
    participants: tuple[str, ...] = ()
    min_age: int | None = None
    venue_name: str = ""
    capacity: int = 0  # sièges de la salle
    artists: tuple[Artist, ...] = ()

    def __post_init__(self) -> None:
        self.acts = tuple(self.acts)
        self.participants = tuple(self.participants)
        self.artists = tuple(self.artists)
        self._check_rules()
        if not self.id:
            self.id = f"{self.venue}-{self.start.strftime('%Y-%m-%d-%H%M')}"

    def _check_rules(self) -> None:
        """Vérifie les règles propres au spectacle, lève InvalidError."""
        if self.kind not in KINDS:
            raise InvalidError(f"Unknown kind '{self.kind}'.")
        if not self.title.strip():
            raise InvalidError("A performance needs a title.")
        if not MIN_DURATION <= self.duration_minutes <= MAX_DURATION:
            raise InvalidError(
                f"Duration must be between {MIN_DURATION} "
                f"and {MAX_DURATION} minutes."
            )

        if self.kind == "solo":
            if not self.artist:
                raise InvalidError("A solo show needs an artist.")
            if self.min_age is None:
                self.min_age = 0
            if not 0 <= self.min_age <= 18:
                raise InvalidError("Minimum age must be between 0 and 18.")

        elif self.kind == "lineup":
            if not self.host:
                raise InvalidError("A lineup needs a host.")
            count = len(self.acts)
            if count < 2:
                raise InvalidError("A lineup needs at least two acts.")
            if len(set(self.acts)) != count:
                raise InvalidError("Each act can appear only once.")
            if self.host in self.acts:
                raise InvalidError("The host cannot also be an act.")
            needed = ACT_MINUTES * count + HOST_MINUTES * (count - 1)
            if self.duration_minutes < needed:
                raise InvalidError(
                    f"{count} acts need at least {needed} minutes."
                )

        else:  # workshop
            if not self.teacher:
                raise InvalidError("A workshop needs a teacher.")
            if self.max_participants is None or self.max_participants < 1:
                raise InvalidError("A workshop needs at least one place.")

    @property
    def end(self) -> datetime:
        """Heure de fin du spectacle."""
        return self.start + timedelta(minutes=self.duration_minutes)

    @property
    def festival_day(self) -> date:
        """Jour du festival : avant 6h, le spectacle compte pour la veille."""
        day = self.start.date()
        if self.start.time() < time(6, 0):
            day -= timedelta(days=1)
        return day

    @property
    def places(self) -> int | None:
        """Places d'un atelier : min(max demandé, sièges de la salle)."""
        if self.kind != "workshop":
            return None
        seats = self.capacity or self.max_participants
        return min(self.max_participants, seats)

    @property
    def places_left(self) -> int | None:
        """Places restantes d'un atelier (None pour les autres spectacles)."""
        if self.places is None:
            return None
        return max(0, self.places - len(self.participants))

    @property
    def artist_slugs(self) -> list[str]:
        """Slugs de tous les artistes du spectacle, sans doublon."""
        slugs = []
        for slug in [self.host, *self.acts, self.artist, self.teacher]:
            if slug and slug not in slugs:
                slugs.append(slug)
        return slugs

    @property
    def summary(self) -> str | None:
        """Phrase courte qui dit qui joue ou qui enseigne."""
        if self.kind == "lineup":
            host = self._artist_name(self.host)
            acts = [self._artist_name(s) for s in self.acts]
            return f"hosted by {host}, with {', '.join(acts)}"
        if self.kind == "workshop":
            return (
                f"with {self._artist_name(self.teacher)}, "
                f"{len(self.participants)}/{self.places} places taken"
            )
        return self._artist_name(self.artist)

    def _artist_name(self, slug: str | None) -> str | None:
        """Nom de l'artiste pour un slug, ou le slug si introuvable."""
        for artist in self.artists:
            if artist.slug == slug:
                return artist.name
        return slug

    def overlaps(self, other: "Performance") -> bool:
        """Vrai si les deux spectacles se chevauchent dans le temps."""
        return self.start < other.end and other.start < self.end

    def involves(self, artist: Artist | str) -> bool:
        """Vrai si l'artiste (objet ou slug) participe au spectacle."""
        slug = artist.slug if isinstance(artist, Artist) else str(artist)
        return slug in self.artist_slugs

    def register(self, name: str) -> None:
        """Inscrit un participant (ateliers seulement)."""
        if self.kind != "workshop":
            raise InvalidError("Only workshops take participants.")
        name = " ".join(name.split())
        if not name:
            raise InvalidError("A participant needs a name.")
        known = {make_slug(n) for n in self.participants}
        if make_slug(name) in known:
            raise ConflictError(f"{name} is already registered.")
        if self.places_left == 0:
            raise ConflictError(f"'{self.title}' is full.")
        self.participants = (*self.participants, name)

    def __lt__(self, other: "Performance") -> bool:
        return (self.start, self.venue_name) < (other.start, other.venue_name)

    def __str__(self) -> str:
        return (
            f"{self.start:%H:%M}-{self.end:%H:%M} "
            f"{self.title} ({self.venue_name})"
        )

    def to_view(self) -> dict[str, Any]:
        """Forme renvoyée par l'API."""
        result = {
            "id": self.id,
            "kind": self.kind,
            "title": self.title,
            "venue": self.venue,
            "venue_name": self.venue_name,
            "start": self.start.isoformat(timespec="minutes"),
            "end": self.end.isoformat(timespec="minutes"),
            "duration_minutes": self.duration_minutes,
            "festival_day": self.festival_day.isoformat(),
            "description": self.description,
            "summary": self.summary,
            # API.md : sièges de la salle, ou places pour un atelier
            "capacity": (
                self.places if self.places is not None else self.capacity
            ),
            "host": self.host,
            "acts": list(self.acts),
            "artists": [
                {"slug": a.slug, "name": a.name} for a in self.artists
            ],
        }
        if self.kind == "workshop":
            result.update(
                {
                    "teacher": self.teacher,
                    "max_participants": self.max_participants,
                    "participants": list(self.participants),
                    "places_left": self.places_left,
                }
            )
        elif self.kind == "solo":
            result.update({"artist": self.artist, "min_age": self.min_age})
        return result

    def to_raw(self) -> dict[str, Any]:
        """Forme écrite dans festival.json."""
        raw = {
            "id": self.id,
            "kind": self.kind,
            "title": self.title,
            "venue": self.venue,
            "start": self.start.isoformat(timespec="minutes"),
            "duration_minutes": self.duration_minutes,
            "description": self.description,
        }
        for key in (
            "host",
            "artist",
            "teacher",
            "max_participants",
            "min_age",
        ):
            if getattr(self, key) is not None:
                raw[key] = getattr(self, key)
        if self.acts:
            raw["acts"] = list(self.acts)
        if self.kind == "workshop":
            raw["participants"] = list(self.participants)
        return raw