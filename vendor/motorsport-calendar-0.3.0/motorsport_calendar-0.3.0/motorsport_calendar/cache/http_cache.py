"""HttpCache — cache disque pour réponses JSON HTTP.

Indépendant de toute bibliothèque HTTP : le caller fournit une coroutine
``fetch`` qui effectue la vraie requête. Le cache l'enveloppe de façon
transparente.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
import hashlib
import json
from pathlib import Path
import time
from typing import Any

from motorsport_calendar.utils.paths import user_cache_dir

# Sprint 49 : le répertoire par défaut était auparavant ``Path(".cache")``
# (relatif au répertoire courant) — un problème de packaging réel : lancée
# depuis le dépôt Git en développement, l'app écrivait silencieusement dans
# le dépôt lui-même ; packagée, le répertoire courant au lancement n'est ni
# prévisible ni forcément inscriptible. Tout appelant qui passe
# explicitement ``cache_dir=`` (CLI/GUI via ``config.cache.resolved_path``)
# est inchangé — seul ce repli implicite change d'emplacement.
_DEFAULT_CACHE_DIR = user_cache_dir("motorsport-calendar")


class HttpCache:
    """Cache disque pour réponses JSON HTTP.

    Stocke les réponses dans des fichiers JSON dans un répertoire configurable.
    La validité est déterminée par un TTL (time-to-live) en secondes.

    Args:
        cache_dir: Répertoire de stockage des fichiers cache. Par défaut,
            le répertoire cache utilisateur multi-plateforme (voir
            ``utils/paths.py::user_cache_dir``), jamais le répertoire
            courant.
        ttl: Durée de vie en secondes (défaut : 86400 = 24 h).
    """

    def __init__(
        self,
        cache_dir: Path = _DEFAULT_CACHE_DIR,
        ttl: int = 86400,
    ) -> None:
        self._cache_dir = cache_dir
        self._ttl = ttl
        self._cache_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # API publique
    # ------------------------------------------------------------------

    async def get_json(
        self,
        url: str,
        params: dict[str, Any],
        fetch: Callable[[str, dict[str, Any]], Awaitable[list[Any] | dict[str, Any]]],
        *,
        refresh: bool = False,
    ) -> list[Any] | dict[str, Any]:
        """Retourne les données mises en cache ou appelle ``fetch`` et les stocke.

        Args:
            url: URL complète de la requête (composante de la clé de cache).
            params: Paramètres de requête (composante de la clé de cache).
            fetch: Coroutine ``(url, params) -> data`` appelée en cas de miss.
            refresh: Si True, ignore le cache et force un nouveau fetch.

        Returns:
            Les données JSON, depuis le cache ou depuis ``fetch``.
        """
        key = self._make_key(url, params)

        if not refresh:
            cached = self._read(key)
            if cached is not None:
                return cached

        data = await fetch(url, params)
        self._write(key, url, params, data)
        return data

    def invalidate(self, url: str, params: dict[str, Any]) -> bool:
        """Supprime une entrée de cache. Retourne True si l'entrée existait."""
        path = self._cache_path(self._make_key(url, params))
        if path.exists():
            path.unlink()
            return True
        return False

    def clear(self) -> int:
        """Supprime toutes les entrées de cache. Retourne le nombre supprimé."""
        count = 0
        for path in self._cache_dir.glob("*.json"):
            path.unlink()
            count += 1
        return count

    # ------------------------------------------------------------------
    # Méthodes internes
    # ------------------------------------------------------------------

    def _make_key(self, url: str, params: dict[str, Any]) -> str:
        """Clé déterministe depuis URL + paramètres triés."""
        payload = json.dumps({"url": url, "params": params}, sort_keys=True)
        return hashlib.sha256(payload.encode()).hexdigest()

    def _cache_path(self, key: str) -> Path:
        return self._cache_dir / f"{key}.json"

    def _read(self, key: str) -> list[Any] | dict[str, Any] | None:
        """Retourne les données si l'entrée existe et est valide, None sinon."""
        path = self._cache_path(key)
        if not path.exists():
            return None
        try:
            entry = json.loads(path.read_text(encoding="utf-8"))
            if time.time() - entry["cached_at"] > self._ttl:
                return None
            data: list[Any] | dict[str, Any] = entry["data"]
            return data
        except (json.JSONDecodeError, KeyError, OSError):
            return None

    def _write(
        self, key: str, url: str, params: dict[str, Any], data: list[Any] | dict[str, Any]
    ) -> None:
        """Écrit les données sur disque avec les métadonnées de cache."""
        entry = {
            "cached_at": time.time(),
            "url": url,
            "params": params,
            "data": data,
        }
        path = self._cache_path(key)
        path.write_text(json.dumps(entry, ensure_ascii=False, indent=2), encoding="utf-8")
