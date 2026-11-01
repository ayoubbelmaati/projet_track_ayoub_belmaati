"""Ligne de commande : venues, artist, programme, now, add, cancel, serve."""

import argparse
from collections.abc import Callable
from datetime import date, datetime
from pathlib import Path
from typing import Any

from deauville.errors import FestivalError, NotFoundError
from deauville.models import Performance
from deauville.storage import JsonStorage, Storage

DEFAULT_DATA = Path("data") / "festival.json"


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


# --- commandes : chacune reçoit le stockage et les arguments ---
def cmd_venues(storage: Storage, args: argparse.Namespace) -> None:
    """Affiche les salles."""
    for venue in storage.load().venues:
        print(venue.to_view())


def cmd_artist(storage: Storage, args: argparse.Namespace) -> None:
    """Affiche un artiste."""
    try:
        artist = storage.load().find_artist(args.slug)
    except NotFoundError:
        print("Artist not found")
    else:
        print(artist.to_view())


def cmd_programme(storage: Storage, args: argparse.Namespace) -> None:
    """Affiche les spectacles d'un jour du festival."""
    for performance in storage.load().programme(args.day):
        print(performance.to_view())


def cmd_now(storage: Storage, args: argparse.Namespace) -> None:
    """Affiche le spectacle en cours un jour du festival."""
    festival = storage.load()
    playing = [
        p for p in festival.now_playing(datetime.now())
        if p.festival_day == args.day
    ]
    print(playing[0].title if playing else "No performance at this time")


def cmd_add(storage: Storage, args: argparse.Namespace) -> int | None:
    """Ajoute un spectacle (1 si une règle le refuse)."""
    festival = storage.load()
    try:
        performance = festival.add_performance(ask_performance())
    except (FestivalError, ValueError) as error:
        print(f"Refused: {error}")
        return 1
    storage.save(festival)
    print(f"Added: {performance}")
    return None


def cmd_cancel(storage: Storage, args: argparse.Namespace) -> int | None:
    """Annule un spectacle (1 si une règle le refuse)."""
    festival = storage.load()
    try:
        performance = festival.cancel_performance(args.id)
    except FestivalError as error:
        print(f"Refused: {error}")
        return 1
    storage.save(festival)
    print(f"Cancelled: {performance}")
    return None


def cmd_serve(storage: Storage, args: argparse.Namespace) -> None:
    """Démarre le site et l'API."""
    import uvicorn

    from deauville.api import create_app

    storage.load()  # échoue tout de suite si le fichier est absent ou invalide
    uvicorn.run(create_app(storage), host=args.host, port=args.port)


def build_parser() -> argparse.ArgumentParser:
    """Construit le parseur d'arguments et ses sous-commandes."""
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument(
        "--data",
        type=Path,
        default=DEFAULT_DATA,
        help="data file (default: data/festival.json)",
    )

    parser = argparse.ArgumentParser(
        prog="deauville", description="Deauville Festival du Rire"
    )
    commands = parser.add_subparsers(dest="command", required=True)

    def command(
        name: str,
        func: Callable[[Storage, argparse.Namespace], int | None],
        help_text: str,
    ) -> argparse.ArgumentParser:
        sub = commands.add_parser(name, parents=[common], help=help_text)
        sub.set_defaults(func=func)
        return sub

    command("venues", cmd_venues, "list the venues")
    command("artist", cmd_artist, "show one artist").add_argument("slug")
    command(
        "programme", cmd_programme, "list the performances of a day"
    ).add_argument("day", type=date.fromisoformat)
    command(
        "now", cmd_now, "what is on stage now, for a festival day"
    ).add_argument("day", type=date.fromisoformat)
    command("add", cmd_add, "add a performance (asks questions)")
    command("cancel", cmd_cancel, "cancel a performance").add_argument("id")

    serve = command("serve", cmd_serve, "start the website and the API")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8000)
    return parser


def main(argv: list[str] | None = None) -> int | None:
    """Point d'entrée : exécute la commande, renvoie le code de sortie."""
    args = build_parser().parse_args(argv)
    storage = JsonStorage(args.data)
    try:
        return args.func(storage, args)
    except FileNotFoundError:
        print(f"Data file not found: {args.data}")
        return 1
    except (ValueError, KeyError) as error:
        print(f"Invalid data file: {error}")
        return 1