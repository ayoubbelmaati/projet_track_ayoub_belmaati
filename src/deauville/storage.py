"""Stockage du festival : une interface abstraite, JSON et mémoire."""

import json
import os
from abc import ABC, abstractmethod
from datetime import date, datetime
from pathlib import Path

from deauville.festival import Festival
from deauville.models import Artist, Performance, Venue


class Storage(ABC):
    """Où vit le festival : le reste du code ne le sait pas."""

    @abstractmethod
    def load(self) -> Festival:
        """Renvoie le festival."""

    @abstractmethod
    def save(self, festival: Festival) -> None:
        """Enregistre le festival."""


class JsonStorage(Storage):
    """Stockage dans un fichier JSON (écriture atomique)."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def load(self) -> Festival:
        """Lit le fichier et reconstruit le festival en appliquant les règles."""
        with open(self.path, encoding="utf-8") as file:
            data = json.load(file)

        festival = Festival(
            name=data["name"],
            first_day=date.fromisoformat(data["first_day"]),
            last_day=date.fromisoformat(data["last_day"]),
            venues=[
                Venue(
                    name=v["name"],
                    capacity=v["capacity"],
                    address=v["address"],
                )
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

    def save(self, festival: Festival) -> None:
        """Écrit le festival dans le fichier JSON."""
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
        # On écrit dans un fichier temporaire puis on le renomme :
        # si l'écriture échoue, l'ancien fichier reste intact.
        temp = self.path.with_name(self.path.name + ".tmp")
        with open(temp, "w", encoding="utf-8") as file:
            json.dump(data, file, indent=2, ensure_ascii=False)
        os.replace(temp, self.path)


class MemoryStorage(Storage):
    """Pour les tests : rien n'est écrit sur le disque."""

    def __init__(self, festival: Festival) -> None:
        self.festival = festival
        self.saves = 0

    def load(self) -> Festival:
        """Renvoie le festival gardé en mémoire."""
        return self.festival

    def save(self, festival: Festival) -> None:
        """Garde le festival en mémoire et compte les sauvegardes."""
        self.festival = festival
        self.saves += 1