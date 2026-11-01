"""Erreurs du festival : une classe par famille de règle violée."""


class FestivalError(ValueError):
    """Base de toutes les erreurs des règles du festival."""


class NotFoundError(FestivalError):
    """Un élément n'existe pas (404)."""


class ConflictError(FestivalError):
    """La demande entre en conflit avec le programme (409)."""


class InvalidError(FestivalError):
    """Une valeur est invalide (422)."""


class StorageError(FestivalError):
    """Le fichier de données ne peut pas être lu ou écrit (500)."""