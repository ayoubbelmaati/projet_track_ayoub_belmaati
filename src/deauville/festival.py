"""Le festival : détient salles, artistes et programme, applique les règles."""

from collections.abc import Iterable
from datetime import date, datetime, timedelta
from typing import Any

from deauville.errors import (
    ConflictError,
    FestivalError,
    InvalidError,
    NotFoundError,
)
from deauville.models import Artist, Performance, Venue


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

    # --- lecture : toujours des copies ---
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

    # --- écriture : les seules portes d'entrée ---
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
            raise ConflictError(
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

    # --- consultation ---
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