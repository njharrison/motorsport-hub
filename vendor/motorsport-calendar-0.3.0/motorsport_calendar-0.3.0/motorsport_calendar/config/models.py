"""Modèles Pydantic pour la configuration de l'application."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from motorsport_calendar.utils.paths import user_cache_dir


class CacheConfig(BaseModel):
    """Configuration du cache HTTP disque."""

    model_config = ConfigDict(frozen=True)

    enabled: bool = True
    # Sprint 49 : répertoire utilisateur multi-plateforme (utils/paths.py) —
    # ``~/.cache/motorsport-calendar`` sur Linux, ``%LOCALAPPDATA%\motorsport-calendar``
    # sur Windows. Reste surchargeable via config.yaml (``cache.path``).
    path: Path = Field(default_factory=lambda: user_cache_dir("motorsport-calendar"))
    ttl_hours: int = Field(default=24, ge=1)

    @property
    def resolved_path(self) -> Path:
        """Chemin absolu avec `~` résolu."""
        return self.path.expanduser()

    @property
    def ttl_seconds(self) -> int:
        """TTL converti en secondes."""
        return self.ttl_hours * 3600


class IcsConfig(BaseModel):
    """Configuration de l'exporteur ICS."""

    model_config = ConfigDict(frozen=True)

    alarm_minutes: int = Field(default=30, ge=0)


class UpdateConfig(BaseModel):
    """Configuration de la vérification de mise à jour (Sprint 51).

    ``manifest_url`` est vide par défaut : aucune URL n'est codée en dur
    dans le projet (ni GitHub, ni aucune autre plateforme — voir
    ``gui/update_service.py``) ; tant que l'utilisateur n'a pas renseigné
    une URL dans ``config.yaml``, la vérification est un no-op silencieux.
    """

    model_config = ConfigDict(frozen=True)

    manifest_url: str = ""


class ProviderConfig(BaseModel):
    """Configuration d'un provider (source sélectionnée + état activé)."""

    model_config = ConfigDict(frozen=True)

    enabled: bool = True
    source: str = ""


class ProvidersConfig(BaseModel):
    """Configuration de tous les providers.

    Les champs nommés (formula1, wec) ont des défauts explicites.
    Les futurs championnats apparaissent dans model_extra (extra="allow")
    et sont accessibles via ProvidersConfig.get(championship_id).
    """

    model_config = ConfigDict(frozen=True, extra="allow")

    formula1: ProviderConfig = Field(default_factory=lambda: ProviderConfig(source="openf1"))
    wec: ProviderConfig = Field(default_factory=lambda: ProviderConfig(source="official"))

    def get(self, championship_id: str) -> ProviderConfig | None:
        """Retourne la config d'un provider par son ID, ou None si absent.

        Cherche d'abord dans les champs nommés (formula1, wec),
        puis dans les extras YAML (f2, elms, etc.).
        """
        if championship_id in type(self).model_fields:
            value: ProviderConfig = getattr(self, championship_id)
            return value
        extras = self.model_extra or {}
        if championship_id in extras:
            val = extras[championship_id]
            if isinstance(val, dict):
                return ProviderConfig.model_validate(val)
            if isinstance(val, ProviderConfig):
                return val
        return None


class AppConfig(BaseModel):
    """Configuration globale de l'application.

    Correspond à la structure de ``config.yaml``.
    Toutes les valeurs ont des défauts — le fichier est entièrement optionnel.
    """

    model_config = ConfigDict(frozen=True)

    timezone: str = "Europe/Paris"
    cache: CacheConfig = Field(default_factory=CacheConfig)
    ics: IcsConfig = Field(default_factory=IcsConfig)
    providers: ProvidersConfig = Field(default_factory=ProvidersConfig)
    update: UpdateConfig = Field(default_factory=UpdateConfig)
