"""Règles du festival : salles, artistes, spectacles et stockage JSON."""

import json
import unicodedata
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import Any

DATA_FILE = Path(__file__).parent.parent / "data" / "festival.json"

KINDS = ("lineup", "workshop", "solo")
MIN_DURATION, MAX_DURATION = 1, 360
ACT_MINUTES, HOST_MINUTES = 10, 3


class FestivalError(ValueError):
    """Base de toutes les erreurs des règles du festival."""


class NotFoundError(FestivalError):
    """Un élément n'existe pas (404)."""


class ConflictError(FestivalError):
    """La demande entre en conflit avec le programme (409)."""


class InvalidError(FestivalError):
    """Une valeur est invalide (422)."""


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
    """Un spectacle (lineup, atelier ou solo) qui applique ses propres règles."""

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
    capacity: int = 0
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
    def summary(self) -> str:
        """Phrase courte qui dit qui joue ou qui enseigne."""
        if self.kind == "lineup":
            host = self._artist_name(self.host)
            acts = [self._artist_name(s) for s in self.acts]
            return f"hosted by {host}, with {', '.join(acts)}"
        if self.kind == "workshop":
            return f"taught by {self._artist_name(self.teacher)}"
        return f"with {self._artist_name(self.artist)}"

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
            "capacity": self.capacity,
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


class Festival:
    """Détient salles, artistes et programme, et applique toutes les règles."""

    def __init__(
        self,
        name: str,
        first_day: date,
        last_day: date,
        venues: Iterable[Venue],
        artists: Iterable[Artist],
    ) -> None:
        self.name = name
        self.first_day = first_day
        self.last_day = last_day
        self._venues = list(venues)
        self._artists = list(artists)
        self._venues_by_slug = {v.slug: v for v in self._venues}
        self._artists_by_slug = {a.slug: a for a in self._artists}
        self._performances: list[Performance] = []

    @property
    def days(self) -> list[date]:
        """Tous les jours du festival, du premier au dernier."""
        count = (self.last_day - self.first_day).days + 1
        return [self.first_day + timedelta(days=i) for i in range(count)]

    @property
    def venues(self) -> list[Venue]:
        """Copie de la liste des salles."""
        return list(self._venues)

    @property
    def artists(self) -> list[Artist]:
        """Copie de la liste des artistes."""
        return list(self._artists)

    @property
    def performances(self) -> list[Performance]:
        """Spectacles triés par heure de début puis par salle."""
        return sorted(self._performances)

    def find_venue(self, slug: str) -> Venue:
        """Retourne la salle ou lève NotFoundError."""
        if slug not in self._venues_by_slug:
            raise NotFoundError(f"No venue '{slug}'.")
        return self._venues_by_slug[slug]

    def find_artist(self, slug: str) -> Artist:
        """Retourne l'artiste ou lève NotFoundError."""
        if slug not in self._artists_by_slug:
            raise NotFoundError(f"No artist '{slug}'.")
        return self._artists_by_slug[slug]

    def find_performance(self, performance_id: str) -> Performance:
        """Retourne le spectacle ou lève NotFoundError."""
        for performance in self._performances:
            if performance.id == performance_id:
                return performance
        raise NotFoundError(f"No performance '{performance_id}'.")

    def add_performance(self, performance: Performance) -> Performance:
        """Ajoute un spectacle si toutes les règles du programme le permettent."""
        venue = self.find_venue(performance.venue)
        for slug in performance.artist_slugs:
            self.find_artist(slug)

        performance.venue_name = venue.name
        performance.capacity = venue.capacity
        performance.artists = tuple(
            self._artists_by_slug[s] for s in performance.artist_slugs
        )

        if not self.first_day <= performance.festival_day <= self.last_day:
            raise InvalidError(
                f"{performance.festival_day} is outside the festival."
            )

        if (
            performance.places is not None
            and len(performance.participants) > performance.places
        ):
            raise ConflictError(
                f"'{performance.title}' has more participants than places."
            )

        for other in self._performances:
            if not performance.overlaps(other):
                continue
            if other.venue == performance.venue:
                raise ConflictError(
                    f"{venue.name} is busy with '{other.title}'."
                )
            shared = set(performance.artist_slugs) & set(other.artist_slugs)
            if shared:
                names = ", ".join(
                    self._artists_by_slug[s].name for s in sorted(shared)
                )
                raise ConflictError(
                    f"{names} is on stage in '{other.title}' at that time."
                )

        self._performances.append(performance)
        return performance

    def replace_performance(
        self, performance_id: str, new_performance: Performance
    ) -> Performance:
        """Remplace un spectacle ; si une règle refuse, rien ne change."""
        old = self.find_performance(performance_id)
        self._performances.remove(old)
        try:
            return self.add_performance(new_performance)
        except FestivalError:
            self._performances.append(old)
            raise

    def cancel_performance(self, performance_id: str) -> Performance:
        """Retire un spectacle du programme et le retourne."""
        performance = self.find_performance(performance_id)
        self._performances.remove(performance)
        return performance

    def register_participant(
        self, performance_id: str, name: str
    ) -> Performance:
        """Inscrit un participant à un atelier."""
        performance = self.find_performance(performance_id)
        performance.register(name)
        return performance

    def add_artist(self, artist: Artist) -> Artist:
        """Ajoute un artiste si le nom est valide et le slug libre."""
        if not artist.name.strip():
            raise InvalidError("An artist needs a name.")
        if artist.slug in self._artists_by_slug:
            raise ConflictError(f"Artist '{artist.name}' already exists.")
        self._artists.append(artist)
        self._artists_by_slug[artist.slug] = artist
        return artist

    def programme(
        self, day: date | None = None, venue: str | None = None
    ) -> list[Performance]:
        """Spectacles filtrés par jour du festival et/ou par salle."""
        return [
            p
            for p in self.performances
            if (day is None or p.festival_day == day)
            and (venue is None or p.venue == venue)
        ]

    def performances_of(self, artist: Artist | str) -> list[Performance]:
        """Spectacles où l'artiste participe."""
        return [p for p in self.performances if p.involves(artist)]

    def now_playing(self, at: datetime) -> list[Performance]:
        """Spectacles en cours à l'instant donné."""
        return [p for p in self.performances if p.start <= at < p.end]

    def up_next(self, at: datetime, limit: int = 3) -> list[Performance]:
        """Les prochains spectacles après l'instant donné."""
        return [p for p in self.performances if p.start > at][:limit]

    def to_view(self) -> dict[str, Any]:
        """Forme renvoyée par l'API."""
        return {
            "name": self.name,
            "first_day": self.first_day.isoformat(),
            "last_day": self.last_day.isoformat(),
            "days": [d.isoformat() for d in self.days],
        }


# --- fichier JSON <-> objets ---
def load_festival() -> Festival:
    """Lit festival.json et reconstruit le festival en appliquant les règles."""
    with open(DATA_FILE, encoding="utf-8") as file:
        data = json.load(file)

    festival = Festival(
        name=data["name"],
        first_day=date.fromisoformat(data["first_day"]),
        last_day=date.fromisoformat(data["last_day"]),
        venues=[
            Venue(name=v["name"], capacity=v["capacity"], address=v["address"])
            for v in data["venues"]
        ],
        artists=[
            Artist(
                name=a["name"],
                bio=a.get("bio", ""),
                photo_url=a.get("photo_url", ""),
            )
            for a in data["artists"]
        ],
    )

    for item in data["performances"]:
        festival.add_performance(
            Performance(
                id=item.get("id", ""),
                kind=item["kind"],
                title=item["title"],
                venue=item["venue"],
                start=datetime.fromisoformat(item["start"]),
                duration_minutes=item["duration_minutes"],
                description=item.get("description", ""),
                host=item.get("host"),
                acts=tuple(item.get("acts", [])),
                artist=item.get("artist"),
                teacher=item.get("teacher"),
                max_participants=item.get("max_participants"),
                participants=tuple(item.get("participants", [])),
                min_age=item.get("min_age"),
            )
        )
    return festival


def save_festival(festival: Festival) -> None:
    """Écrit le festival dans festival.json."""
    data = {
        "name": festival.name,
        "first_day": festival.first_day.isoformat(),
        "last_day": festival.last_day.isoformat(),
        "venues": [
            {"name": v.name, "capacity": v.capacity, "address": v.address}
            for v in festival.venues
        ],
        "artists": [
            {"name": a.name, "bio": a.bio, "photo_url": a.photo_url}
            for a in festival.artists
        ],
        "performances": [p.to_raw() for p in festival.performances],
    }
    with open(DATA_FILE, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=2, ensure_ascii=False)


def get_festival(festival: Festival) -> dict[str, Any]:
    """Infos générales du festival."""
    return festival.to_view()


def get_venues(festival: Festival) -> list[dict[str, Any]]:
    """Liste des salles."""
    return [
        {
            "slug": v.slug,
            "name": v.name,
            "capacity": v.capacity,
            "address": v.address,
        }
        for v in festival.venues
    ]


def get_artists(festival: Festival) -> list[dict[str, str]]:
    """Liste des artistes triés par slug."""
    return [
        a.to_view() for a in sorted(festival.artists, key=lambda a: a.slug)
    ]


def get_artist(festival: Festival, slug: str) -> Artist | None:
    """Retourne l'artiste, ou None s'il n'existe pas."""
    try:
        return festival.find_artist(slug)
    except NotFoundError:
        return None


def get_programme(
    festival: Festival, day: date | None = None, venue: str | None = None
) -> list[Performance]:
    """Programme filtré par jour et/ou par salle."""
    return festival.programme(day, venue)


def get_now(
    festival: Festival, day: str, at: datetime | None = None
) -> None:
    """Affiche le spectacle en cours le jour donné (YYYY-MM-DD)."""
    at = at or datetime.now()
    selected_day = date.fromisoformat(day)
    playing = [
        p for p in festival.now_playing(at) if p.festival_day == selected_day
    ]
    print(playing[0].title if playing else "No performance at this time")