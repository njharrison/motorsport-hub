"""Source Registry — registre central de toutes les sources de données.

Symétrique au ProviderRegistry.

Chaque source s'enregistre automatiquement à l'import de son sources/__init__.py.

Usage :
    source_registry.discover()
    make_source = source_registry.get("formula1", "openf1")
    source = make_source(cache, refresh=False)

Signature attendue pour une source factory :
    def make_source(cache: HttpCache | None, refresh: bool) -> Source: ...
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

# Type alias documentaire
SourceFactory = Callable[..., Any]


class SourceRegistry:
    """Registre central des sources de données motorsport.

    Indexé par (championship_id, source_name).
    Les sources factory reçoivent (cache, refresh) et retournent une instance de Source.
    """

    def __init__(self) -> None:
        self._factories: dict[tuple[str, str], SourceFactory] = {}

    def register(
        self,
        championship_id: str,
        source_name: str,
        factory: SourceFactory,
    ) -> None:
        """Enregistre une factory pour un couple (championnat, source).

        Idempotent : un deuxième appel écrase l'entrée précédente.
        """
        self._factories[(championship_id, source_name)] = factory

    def get(self, championship_id: str, source_name: str) -> SourceFactory:
        """Retourne la factory, ou lève KeyError si la combinaison est inconnue."""
        key = (championship_id, source_name)
        try:
            return self._factories[key]
        except KeyError:
            available = ", ".join(f"{c}/{s}" for (c, s) in sorted(self._factories)) or "(aucune)"
            raise KeyError(
                f"Source '{source_name}' inconnue pour le championnat '{championship_id}'. "
                f"Disponibles : {available}"
            ) from None

    def list_for(self, championship_id: str) -> list[str]:
        """Retourne les noms de sources disponibles pour un championnat, triés."""
        return sorted(s for (c, s) in self._factories if c == championship_id)

    def list_all(self) -> list[tuple[str, str]]:
        """Retourne toutes les paires (championship_id, source_name), triées."""
        return sorted(self._factories)

    def discover(self) -> None:
        """Importe le sous-paquet sources/ de chaque provider pour déclencher l'enregistrement.

        Chaque providers/X/sources/__init__.py appelle source_registry.register()
        pour chaque source disponible.
        """
        import contextlib
        import importlib
        import pkgutil

        import motorsport_calendar.providers as _providers_pkg

        for _, name, is_pkg in pkgutil.iter_modules(_providers_pkg.__path__):
            if is_pkg:
                # provider sans sous-paquet sources/ — ignoré
                with contextlib.suppress(ImportError):
                    importlib.import_module(f"motorsport_calendar.providers.{name}.sources")


# Singleton partagé par toute l'application.
source_registry = SourceRegistry()
