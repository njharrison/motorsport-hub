"""Provider Registry — registre central de tous les providers motorsport.

Chaque provider s'enregistre automatiquement à l'import de son __init__.py.
La CLI et les consommateurs n'ont jamais besoin de connaître les providers
individuellement : ils interrogent simplement le registre.

Usage :
    registry.discover()              # importe tous les sous-paquets providers/
    factory = registry.get("formula1")
    provider = factory(cfg, cache, refresh=False)

    for cid in registry.enabled(config.providers):
        factory = registry.get(cid)
        ...

Signature attendue pour une factory :
    def make_provider(
        cfg: ProviderConfig,
        cache: HttpCache | None,
        refresh: bool,
    ) -> Provider: ...
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

# Type alias documentaire — le vrai type est vérifié uniquement par mypy
ProviderFactory = Callable[..., Any]


class ProviderRegistry:
    """Registre central des providers motorsport.

    Stocke des factory callables indexées par championship_id.
    Thread-safe en lecture (pas d'écriture concurrente attendue après discover()).
    """

    def __init__(self) -> None:
        self._factories: dict[str, ProviderFactory] = {}

    def register(self, championship_id: str, factory: ProviderFactory) -> None:
        """Enregistre une factory pour un ID de championnat.

        Idempotent : un deuxième appel écrase l'entrée précédente.
        """
        self._factories[championship_id] = factory

    def get(self, championship_id: str) -> ProviderFactory:
        """Retourne la factory du provider, ou lève KeyError si inconnu."""
        try:
            return self._factories[championship_id]
        except KeyError:
            available = ", ".join(sorted(self._factories)) or "(aucun)"
            raise KeyError(
                f"Provider '{championship_id}' non enregistré. Disponibles : {available}"
            ) from None

    def list_all(self) -> list[str]:
        """Retourne tous les championship_ids enregistrés, triés."""
        return sorted(self._factories)

    def enabled(self, providers_config: Any) -> list[str]:
        """Retourne les IDs des providers activés selon la configuration.

        Logique opt-out : un provider absent de la config est activé par défaut.
        Pour désactiver : ajouter ``cid: { enabled: false }`` dans config.yaml.
        """
        result = []
        for cid in self.list_all():
            pc = providers_config.get(cid)
            # None = absent de la config → activé par défaut
            if pc is None or pc.enabled:
                result.append(cid)
        return result

    def discover(self) -> None:
        """Importe automatiquement tous les sous-paquets de providers/.

        Chaque __init__.py de provider appelle registry.register() à l'import.
        Cette méthode garantit que tous les providers sont découverts même si
        aucune autre partie du code ne les a encore importés (ex. : CLI cold start).
        """
        import importlib
        import pkgutil

        import motorsport_calendar.providers as _providers_pkg

        for _, name, is_pkg in pkgutil.iter_modules(_providers_pkg.__path__):
            # N'importe que les sous-paquets (dossiers) — ignore base.py, etc.
            if is_pkg:
                importlib.import_module(f"motorsport_calendar.providers.{name}")


# Singleton partagé par toute l'application.
# Les providers/ l'importent pour s'auto-enregistrer à l'import.
registry = ProviderRegistry()
