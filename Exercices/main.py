"""Ligne de commande du festival : venues, artist, programme, now, add, cancel."""

import sys
from datetime import date, datetime
from typing import Any

from festival import (
    FestivalError,
    Performance,
    get_artist,
    get_now,
    get_programme,
    get_venues,
    load_festival,
    save_festival,
)


def ask_performance() -> Performance:
    """Pose les questions au clavier et construit un spectacle."""
    kind = input("Kind (lineup/workshop/solo): ").strip()
    data: dict[str, Any] = dict(
        kind=kind,
        title=input("Title: "),
        venue=input("Venue slug: "),
        start=datetime.fromisoformat(input("Start (YYYY-MM-DDTHH:MM): ")),
        duration_minutes=int(input("Duration (minutes): ")),
        description=input("Description: "),
    )
    if kind == "lineup":
        data["host"] = input("Host slug: ")
        acts = input("Acts slugs (comma separated): ")
        data["acts"] = tuple(s.strip() for s in acts.split(",") if s.strip())
    elif kind == "workshop":
        data["teacher"] = input("Teacher slug: ")
        data["max_participants"] = int(input("Max participants: "))
    elif kind == "solo":
        data["artist"] = input("Artist slug: ")
        data["min_age"] = int(input("Min age: "))
    return Performance(**data)


def main() -> None:
    """Lit la commande dans sys.argv et l'exécute."""
    if len(sys.argv) < 2:
        print("Please enter a command")
        return

    command = sys.argv[1]
    festival = load_festival()

    if command == "venues":
        for venue in get_venues(festival):
            print(venue)

    elif command == "artist" and len(sys.argv) > 2:
        artist = get_artist(festival, sys.argv[2])
        print("Artist not found" if artist is None else artist.to_view())

    elif command == "programme" and len(sys.argv) > 2:
        day = date.fromisoformat(sys.argv[2])
        for performance in get_programme(festival, day):
            print(performance.to_view())

    elif command == "now" and len(sys.argv) > 2:
        get_now(festival, sys.argv[2])

    elif command == "add":
        try:
            performance = festival.add_performance(ask_performance())
        except (FestivalError, ValueError) as error:
            print(f"Refused: {error}")
        else:
            save_festival(festival)
            print(f"Added: {performance}")

    elif command == "cancel" and len(sys.argv) > 2:
        try:
            performance = festival.cancel_performance(sys.argv[2])
        except FestivalError as error:
            print(f"Refused: {error}")
        else:
            save_festival(festival)
            print(f"Cancelled: {performance}")

    else:
        print("Unknown command")


if __name__ == "__main__":
    main()