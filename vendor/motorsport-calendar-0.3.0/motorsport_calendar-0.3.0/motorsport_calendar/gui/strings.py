"""Centralized UI strings for Motorsport Calendar GUI.

All user-visible text lives here.

To add a language in the future:
  1. Create gui/i18n/fr.json (or en.json) with the same attribute names as keys
  2. Load it at startup: Strings.from_dict(json.loads(path.read_text()))
  3. Replace the module-level STRINGS singleton

Sprint 54 (Beta UX recette) — two cleanups, no new strings/behavior:
  - ``EmptyState`` titles standardized to never end with a period — they
    read as short labels ("Aucune course ce week-end"), not full
    sentences; only genuine instructional sentences with a verb
    (``weekend_next_hint``, ``search_empty_query``, ``about_description``)
    keep one. ``weekend_empty_title``/``dashboard_weekend_championships_
    empty``/``search_no_results`` lost their trailing period to match the
    (already period-less) majority.
  - ``nav_home``/``nav_calendar`` removed — dead "backward compat" labels
    that nothing has referenced since ``nav_dashboard``/``nav_my_calendar``
    were introduced; keeping unused, near-duplicate vocabulary next to the
    real ones invites confusion, not compatibility.
"""

from __future__ import annotations

from typing import Any


class Strings:
    """All user-visible text. Replace the STRINGS singleton to switch language."""

    # App chrome
    app_title: str = "Motorsport Calendar"
    app_subtitle: str = "Calendrier des courses automobiles"

    # Section labels
    season_label: str = "Saison"
    championships_label: str = "Championnats"
    output_label: str = "Fichier de sortie"

    # File picker
    output_hint: str = "Cliquer sur l'icône pour choisir l'emplacement…"
    browse_tooltip: str = "Choisir l'emplacement du fichier"
    save_dialog_title: str = "Enregistrer le calendrier"

    # Manual refresh (MC-002 P0-7) — Tableau de bord, Ce week-end, Mon calendrier
    refresh_tooltip: str = "Rafraîchir (ignorer le cache)"

    # Generate
    generate_btn: str = "Créer mon calendrier"
    generating_status: str = "Création du calendrier en cours…"

    # Calendar selection summary (Sprint 40 — "Mon calendrier" navigateur)
    # Sprint 43: the 4-step wizard (saison/championnats/destination/créer)
    # was replaced by a single reorganized page — the wizard_step_*/
    # wizard_back_btn/wizard_next_btn/wizard_edit_btn/wizard_recap_*
    # strings it used are gone with it.
    calendar_summary_championships: str = "Championnat{s}"
    calendar_summary_events: str = "Événement{s}"
    calendar_summary_sessions: str = "Session{s}"
    calendar_summary_period: str = "Période couverte"
    calendar_summary_period_empty: str = "—"
    calendar_summary_loading: str = "Chargement du calendrier…"
    calendar_summary_empty_selection: str = "Aucun championnat sélectionné"

    # Season explorer (Sprint 41 — "Mon calendrier" devient explorable)
    calendar_season_explorer_title: str = "Événements de la saison"
    calendar_season_explorer_empty: str = "Aucun événement pour cette sélection"
    calendar_season_explorer_loading: str = "Chargement des événements…"

    # Event details dialog (Sprint 42 — "fiche événement")
    event_details_title: str = "Détails de l'événement"

    # Success dialog
    success_title: str = "Calendrier créé avec succès"
    success_saved_at: str = "Enregistré dans :"
    open_folder_btn: str = "Ouvrir le dossier"
    close_btn: str = "Fermer"

    # Update dialog (Sprint 51 — vérification des mises à jour)
    update_title: str = "Une nouvelle version est disponible"
    update_current_version: str = "Version actuelle :"
    update_new_version: str = "Nouvelle version :"
    update_mandatory_badge: str = "Mise à jour importante"
    update_view_btn: str = "Voir la version"

    # Error messages
    error_no_events: str = "Aucun événement exporté"
    error_unexpected: str = "Erreur inattendue : {msg}"

    # Per-championship result lines (shown inside success dialog)
    summary_ok: str = "✓ {name} — {n} événement{s}"
    summary_error: str = "✗ {name} : {err}"

    # Navigation rail
    nav_dashboard: str = "Tableau de bord"
    nav_weekend: str = "Ce week-end"
    nav_my_calendar: str = "Mon calendrier"
    nav_search: str = "Recherche"
    nav_favorites: str = "Mes favoris"
    nav_preferences: str = "Préférences"
    nav_about: str = "À propos"
    nav_support: str = "Soutenir le projet"

    # Weekend screen (Sprint 29 — version fonctionnelle)
    weekend_loading: str = "Chargement..."
    weekend_empty_title: str = "Aucune course ce week-end"
    weekend_next_hint: str = "Prochain week-end disponible le {date}."

    # Dashboard screen (Sprint 39 — page d'accueil)
    dashboard_stat_next_weekend: str = "Prochain week-end"
    dashboard_stat_championships: str = "Championnats disponibles"
    dashboard_stat_events: str = "Événements cette saison"
    dashboard_stat_sessions: str = "Sessions cette saison"
    dashboard_next_weekend_none: str = "Aucune course prévue"
    dashboard_section_weekend_championships: str = "Championnats ce week-end"
    dashboard_weekend_championships_empty: str = "Aucun championnat en course ce week-end"
    dashboard_section_next_race: str = "Prochain départ"
    dashboard_next_race_empty: str = "Aucun départ prévu"

    # Dashboard — home page sections (Sprint 53)
    dashboard_section_news: str = "Nouveautés"
    dashboard_section_quick_access: str = "Accès rapides"
    dashboard_section_status: str = "État de Motorsport Calendar"
    dashboard_stat_version: str = "Version"
    dashboard_stat_active_championships: str = "Championnats actifs"
    dashboard_stat_functional_providers: str = "Fournisseurs fonctionnels"
    dashboard_stat_favorites: str = "Favoris"

    # Event display normalization (Sprint 32) — last-resort fallback when a
    # provider gives no event name at all (see gui/event_display.py).
    event_name_fallback: str = "Événement"

    # Favorites screen (Sprint 44 — vraie page, plus un placeholder)
    favorites_count: str = "{n} favori{s}"

    # Search screen (Sprint 45 — recherche globale)
    search_hint: str = "Rechercher un championnat, un événement, un circuit…"
    search_results_count: str = "{n} résultat{s}"
    search_section_championships: str = "Championnats"
    search_section_events: str = "Événements"
    search_section_circuits: str = "Circuits"
    search_empty_query: str = "Commencez à taper pour rechercher."
    search_no_results: str = "Aucun résultat pour cette recherche"

    # Circuit explorer (Sprint 47 — fiche Circuit)
    circuit_name_fallback: str = "Circuit inconnu"
    circuit_details_title: str = "Détails du circuit"
    circuit_championships_count: str = "{n} championnat{s}"
    circuit_events_count: str = "{n} course{s}"
    circuit_section_championships: str = "Championnats"
    circuit_section_history: str = "Historique des événements"

    # Preferences screen (Sprint 52 — real configuration center)
    prefs_title: str = "Préférences"
    prefs_coming_soon: str = "Disponible prochainement"

    prefs_section_notifications: str = "Notifications"
    prefs_notifications_enabled: str = "Notifications activées"
    prefs_notifications_favorites_only: str = "Favoris uniquement"
    prefs_notifications_lead_time: str = "Délai par défaut"

    prefs_section_updates: str = "Mises à jour"
    prefs_update_check_enabled: str = "Vérifier les mises à jour au démarrage"

    prefs_section_calendar: str = "Calendrier"
    prefs_default_year: str = "Année par défaut"
    prefs_default_year_current: str = "Année en cours"
    prefs_export_reminder: str = "Rappel avant export"
    prefs_reminder_none: str = "Aucun rappel"

    prefs_section_application: str = "Application"
    prefs_theme: str = "Thème"
    prefs_language: str = "Langue"
    prefs_time_format: str = "Format horaire"

    # Shared duration labels (export reminder dropdown)
    prefs_duration_15min: str = "15 minutes"
    prefs_duration_30min: str = "30 minutes"
    prefs_duration_1h: str = "1 heure"

    # System notifications (Sprint 56) — title/body used only if/when a
    # real OS notifier ever exists (see gui/system_notifications.py);
    # NotificationService itself never formats text, this is the one
    # place that turns its structured Notification into words.
    notification_kind_weekend_start: str = "Début du week-end"
    notification_kind_first_session: str = "Première séance"
    notification_kind_qualifying: str = "Qualifications"
    notification_kind_sprint: str = "Course sprint"
    notification_kind_race: str = "Course"
    notification_title: str = "{kind} — {event}"

    # About screen
    # Sprint 54: carries the actual version number ({version} ->
    # motorsport_calendar.__version__, same value already shown on the
    # Dashboard's "État" section since Sprint 53) — was a bare "Version
    # Alpha" with no number at all, the one place in the app that talked
    # about "the version" without saying which one.
    about_version: str = "Version {version} — Alpha"
    about_developer: str = "Développé par BApps Studio"
    about_github_label: str = "Voir sur GitHub"
    about_license: str = "Licence MIT"
    about_description: str = (
        "Motorsport Calendar agrège les calendriers de saison de plusieurs "
        "championnats automobiles et les exporte au format ICS standard, "
        "prêt à importer dans n'importe quelle application calendrier."
    )

    # About screen — real project presentation (Sprint 57, Préparation Beta)
    about_section_objectives: str = "Objectifs du projet"
    about_objectives: tuple[str, ...] = (
        "Centraliser tous les calendriers de courses automobiles dans un "
        "seul fichier standard, importable dans n'importe quelle "
        "application calendrier — Google Calendar, Apple Calendar, "
        "Outlook, ou tout client iCalendar.",
        "Rester fidèle aux sources officielles : un événement incorrect "
        "est pire qu'un événement absent.",
        "Fonctionner entièrement en local — aucun compte, aucun serveur, aucun abonnement cloud.",
    )

    about_section_open_source: str = "Philosophie Open Source"
    about_open_source_text: str = (
        "Motorsport Calendar est un projet Open Source sous licence MIT. "
        "Le code source est public, les décisions d'architecture sont "
        "documentées, et toute contribution — code, retour d'expérience, "
        "suggestion — est la bienvenue."
    )

    about_section_tech: str = "Technologies utilisées"
    about_tech_stack: tuple[str, ...] = (
        "Python 3.12+",
        "Flet (interface)",
        "Typer (CLI)",
        "Pydantic (modèles)",
        "httpx (réseau)",
        "icalendar (export ICS)",
    )

    # "Soutenir le projet" screen (Sprint 57 — Préparation Beta)
    support_intro: str = (
        "Motorsport Calendar est un projet Open Source, développé et "
        "maintenu sur du temps libre. Voici comment vous pouvez aider — "
        "ou simplement suivre ce qui se prépare."
    )

    support_section_donate: str = "Soutenir Motorsport Calendar"
    support_paypal_label: str = "PayPal"
    support_github_sponsors_label: str = "GitHub Sponsors"
    # Reuses prefs_coming_soon ("Disponible prochainement") — same concept
    # (a prepared-but-not-yet-real slot), never a second "coming soon"
    # vocabulary for the exact same idea.

    support_section_roadmap: str = "Voter pour les prochaines fonctionnalités"
    support_roadmap_intro: str = "Les grandes pistes actuellement envisagées pour la suite :"
    support_roadmap_ideas: tuple[str, ...] = (
        "Classements",
        "Diffusion TV",
        "Mobile",
        "Motorsport API",
        "Résultats",
        "Pilotes",
        "Équipes",
        "Widgets",
    )

    support_section_suggestions: str = "Suggestions"
    support_suggestions_text: str = "Une idée, une remarque ? Partagez-la avec la communauté."
    support_suggestions_btn: str = "Ouvrir les Discussions GitHub"

    support_section_report: str = "Signaler un problème"
    support_report_text: str = "Un bug, un comportement inattendu ? Faites-le savoir."
    support_report_btn: str = "Signaler un bug"

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Strings:
        """Build a Strings instance from a dict (future i18n use).

        Unknown keys are ignored; existing attributes are overridden.
        """
        obj = cls()
        for key, value in data.items():
            if hasattr(obj, key):
                setattr(obj, key, value)
        return obj


def plural(n: int) -> str:
    """Return 's' when n != 1, '' otherwise (French pluralisation)."""
    return "s" if n != 1 else ""


# Module-level singleton — replace to change language application-wide
STRINGS: Strings = Strings()
