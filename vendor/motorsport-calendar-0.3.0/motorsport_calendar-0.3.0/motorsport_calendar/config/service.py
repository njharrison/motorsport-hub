"""ConfigService — lecture et validation de config.yaml."""

from __future__ import annotations

from pathlib import Path
from typing import ClassVar

import yaml

from motorsport_calendar.config.models import (
    AppConfig,
    CacheConfig,
    IcsConfig,
    ProvidersConfig,
    UpdateConfig,
)
from motorsport_calendar.utils.paths import user_config_dir


class ConfigService:
    """Charge et expose la configuration de l'application.

    Recherche ``config.yaml`` dans l'ordre suivant :
    1. Chemin explicite passé au constructeur
    2. ``config.yaml`` dans le répertoire courant (commodité — un fichier
       optionnel à lire, jamais écrit ; ce n'est pas un problème de
       packaging que la CLI accepte un override local)
    3. Répertoire utilisateur multi-plateforme (Sprint 49, ``utils/paths.py``) —
       ``~/.config/motorsport-calendar/config.yaml`` sur Linux,
       ``%APPDATA%\\motorsport-calendar\\config.yaml`` sur Windows

    Si aucun fichier n'est trouvé, les valeurs par défaut s'appliquent.
    La validation est assurée par Pydantic : un fichier invalide lève une erreur.

    Args:
        config_path: Chemin explicite vers un fichier ``config.yaml``.
                     Quand fourni, aucun autre chemin n'est cherché.
    """

    _DEFAULT_PATHS: ClassVar[list[Path]] = [
        Path("config.yaml"),
        user_config_dir("motorsport-calendar") / "config.yaml",
    ]

    def __init__(self, config_path: Path | None = None) -> None:
        self._config = self._load(config_path)

    # ------------------------------------------------------------------
    # Accès direct aux sous-sections
    # ------------------------------------------------------------------

    @property
    def config(self) -> AppConfig:
        """Configuration complète."""
        return self._config

    @property
    def timezone(self) -> str:
        """Fuseau horaire par défaut de la configuration."""
        return self._config.timezone

    @property
    def cache(self) -> CacheConfig:
        """Sous-section cache de la configuration."""
        return self._config.cache

    @property
    def ics(self) -> IcsConfig:
        """Sous-section export ICS de la configuration."""
        return self._config.ics

    @property
    def providers(self) -> ProvidersConfig:
        """Sous-section providers de la configuration."""
        return self._config.providers

    @property
    def update(self) -> UpdateConfig:
        """Sous-section vérification de mise à jour de la configuration."""
        return self._config.update

    # ------------------------------------------------------------------
    # Chargement interne
    # ------------------------------------------------------------------

    def _load(self, explicit_path: Path | None) -> AppConfig:
        paths = [explicit_path] if explicit_path is not None else self._DEFAULT_PATHS
        for path in paths:
            resolved = path.expanduser()
            if resolved.exists():
                raw = yaml.safe_load(resolved.read_text(encoding="utf-8")) or {}
                return AppConfig.model_validate(raw)
        return AppConfig()
