# ROADMAP.md

> Vision : générer automatiquement des calendriers ICS pour n'importe quelle discipline motorsport, à partir de sources de données publiques, sans configuration manuelle.

---

## Vision produit

`motorsport-calendar` est un outil CLI open source qui :

- récupère les calendriers de saison depuis des API publiques ou des sources officielles
- exporte en format ICS (compatible Google Calendar, Apple Calendar, Outlook…)
- supporte plusieurs disciplines via un système de providers/sources extensible
- est configurable via un simple `config.yaml` (sources, cache, rappels, opt-out par championnat)

---

## v0.1.0 — MVP multi-provider ✅ (2026-07-05)

| Fonctionnalité | Statut |
|---|---|
| Modèles métier Pydantic v2 frozen (Championship, Circuit, Session, Event) | ✅ |
| IcsExporter RFC 5545 — 1 VEVENT par session + VALARM configurable | ✅ |
| Architecture provider/source F1 | ✅ |
| OpenF1Source — API openf1.org (2023+, 25 circuits IANA) | ✅ |
| HttpCache — cache disque JSON, TTL configurable, flag --refresh | ✅ |
| WecProvider + OfficialWecSource stub (architecture complète) | ✅ |
| ConfigService — lit config.yaml, valeurs par défaut Pydantic | ✅ |
| ProviderRegistry — auto-découverte, opt-out config | ✅ |
| SourceRegistry — clé (championnat, source), auto-enregistrement | ✅ |
| CLI `generate-f1 YEAR OUTPUT.ics` | ✅ |
| CLI `generate-wec YEAR OUTPUT.ics` (exit propre si source non implémentée) | ✅ |
| CLI `generate YEAR OUTPUT.ics` — agrégateur résilient multi-provider | ✅ |
| CLI `providers` — liste les providers enregistrés | ✅ |
| 306 tests — couverture 92 % | ✅ |
| CI GitHub Actions (Python 3.12 + 3.13) | ✅ |

---

## v0.2.0 — Sources enrichies + Formula 2 ✅ (2026-07-05)

| Fonctionnalité | Statut |
|---|---|
| `JolpicaSource` — données historiques F1 (1950+), `api.jolpi.ca` (successeur Ergast, Apache-2.0) | ✅ |
| Data Acquisition Layer (`core/datasource/`) — `JsonDataSource`, `HtmlDataSource`, `IcsDataSource` | ✅ |
| `Formula2Provider` + `F1CalendarSource` — calendrier FIA F2 complet (JSON MIT, f1calendar.com) | ✅ |
| CLI `generate-f2 YEAR OUTPUT.ics` | ✅ |
| `generate` inclut automatiquement F2 (opt-out via config) | ✅ |
| 448 tests — couverture 93 % | ✅ |

---

## v0.2.x — Nouvelles disciplines (Sprints 20-21-QA03) ✅ (2026-07-06)

| Fonctionnalité | Statut |
|---|---|
| `Formula3Provider` + `F1CalendarSource` — FIA F3 complet (2022+) | ✅ |
| `F1AcademyProvider` + `F1CalendarSource` — F1 Academy complète (2023+) | ✅ |
| Support Series Framework — `F1CalendarBaseSource` partagé F2/F3/Academy | ✅ |
| Rétrocompatibilité F2 clés sessions 2024 (`fp1`/`sprintRace`) et 2025+ (`practice`/`sprint`) | ✅ |
| Dataset Reality Check — correction bug `"events"` → `"races"`, fixtures réelles | ✅ |
| 627 tests — couverture 94 % | ✅ |

---

## v0.3.0 — Desktop Edition ✅ Sprint 22 (2026-07-06)

| Fonctionnalité | Statut |
|---|---|
| GUI Flet — fenêtre native desktop (`motocal-gui`) | ✅ |
| Sélecteur de saison (année courante ±5) | ✅ |
| Championnats auto-découverts depuis ProviderRegistry (cases à cocher) | ✅ |
| FilePicker natif — dialogue OS de sauvegarde | ✅ |
| Progression asynchrone — anneau pendant les requêtes réseau | ✅ |
| Résumé par championnat (✓ N événements / ✗ erreur) | ✅ |
| Dépendance optionnelle `flet>=0.80` (`pip install motorsport-calendar[gui]`) | ✅ |
| Zéro duplication du moteur — même pipeline que la CLI | ✅ |
| 32 tests GUI (models + controller, sans Flet) | ✅ |
| 659 tests total — couverture ~93 % | ✅ |

---

## v0.3.1 — Desktop Alpha 2 — UX Polish ✅ Sprint 23 (2026-07-06)

| Fonctionnalité | Statut |
|---|---|
| Noms de championnats lisibles (Formula 1, F1 Academy, FIA WEC…) | ✅ |
| Formula 1 cochée par défaut au premier lancement | ✅ |
| Mémorisation des sélections entre sessions | ✅ |
| Bouton "Créer mon calendrier" (texte orienté utilisateur) | ✅ |
| Nom de fichier intelligent `motorsport-calendar-{année}.ics` | ✅ |
| Dernier dossier de sortie mémorisé | ✅ |
| Dialogue succès : événements, sessions, chemin, "Ouvrir le dossier" | ✅ |
| Toutes les chaînes centralisées dans `strings.py` | ✅ |
| `display_names.py`, `preferences.py`, `assets/` (placeholder icône) | ✅ |
| `docs/PRODUCT_VISION.md` | ✅ |
| 36 nouveaux tests — 695 total | ✅ |

---

## v0.4.33 — Correction du packaging Flet ✅ Sprint 59 (2026-07-14)

| Fonctionnalité | Statut |
|---|---|
| Le build Linux produit désormais un exécutable qui démarre réellement — `ModuleNotFoundError` corrigé | ✅ |
| Nouveau `motorsport_calendar/gui/pyproject.toml` — manifeste de build dédié, mécanisme officiel `tool.flet.dev_packages` | ✅ |
| Une seule source de vérité pour les dépendances — jamais de liste dupliquée entre le manifeste racine et le manifeste de build | ✅ |
| Identité de l'application corrigée (exécutable/ID d'application/titre de fenêtre) | ✅ |
| Vérifié pour de vrai — rebuild complet + binaire lancé deux fois, aucune trace d'erreur | ✅ |
| Aucune modification métier — `pyproject.toml` racine et points d'entrée de développement existants intacts et vérifiés | ✅ |
| Aucune régression — 8 nouveaux tests garde-fous | ✅ |

---

## v0.4.32 — Validation Packaging Beta ✅ Sprint 58 (2026-07-14)

| Fonctionnalité | Statut |
|---|---|
| Build Linux compilé et exécuté pour de vrai pour la première fois (Sprint 49 ne l'avait jamais fait tourner) | ✅ |
| Constat critique documenté : le binaire plante au démarrage (`ModuleNotFoundError: No module named 'motorsport_calendar'`), cause racine identifiée dans le code source de `flet_cli` | ✅ |
| Cartographie complète du dossier produit (exécutable/lib/python/site-packages/data), 112 Mo au total | ✅ |
| Autonomie confirmée : Python et bibliothèques système embarqués, aucune installation requise sur la machine cible (une fois le blocage corrigé) | ✅ |
| Nom de fenêtre/ID d'application/version embarquée audités — encore les valeurs par défaut génériques de Flet | ✅ |
| Chemins de préférences/cache/configuration confirmés corrects et indépendants de Flet (Sprint 49) | ✅ |
| Nouveau `docs/RELEASE.md` — procédure Linux/Windows/publication GitHub Release | ✅ |
| Arborescence `Release/` proposée et ajoutée à `.gitignore` | ✅ |
| `docs/PACKAGING.md` mis à jour — affirmation prématurée du Sprint 49 corrigée | ✅ |
| Aucune modification métier, aucune évolution des services, aucun correctif appliqué (audit uniquement) | ✅ |
| Aucune régression — suite de tests intacte | ✅ |

---

## v0.4.31 — Préparation Beta : Nettoyage & Positionnement ✅ Sprint 57 (2026-07-13)

| Fonctionnalité | Statut |
|---|---|
| IMSA/WorldSBK masqués des sélecteurs de championnat (Mon calendrier/Mes favoris/Recherche) — aucune suppression de code, restent enregistrés dans `ProviderRegistry` | ✅ |
| "À propos" devient une véritable présentation — objectifs, philosophie Open Source, technologies utilisées | ✅ |
| Nouvelle page "Soutenir le projet" — 4 sections (Soutenir Motorsport Calendar, Voter pour les prochaines fonctionnalités, Suggestions, Signaler un problème) | ✅ |
| `gui/url_opener.py` — nettoyage : 2 implémentations dupliquées de "ouvrir une URL" fusionnées en une seule | ✅ |
| `gui/components/layout::ComingSoonRow` — nettoyage : promu depuis un helper privé de `views/preferences.py` | ✅ |
| Aucun nouveau provider, aucune évolution métier, aucune évolution des services, aucun système de vote/dons local | ✅ |
| Aucune régression | ✅ |
| 34 nouveaux tests — 2034 total | ✅ |

---

## v0.4.30 — Notifications natives ✅ Sprint 56 (2026-07-13)

| Fonctionnalité | Statut |
|---|---|
| `gui/system_notifications.py` — seule couche dépendante du système d'exploitation, `NotificationService` reste indépendant de Flet | ✅ |
| Fait vérifié : Flet 0.85.3 ne fournit aucun service de notification système sur aucune plateforme (source auditée, pas une hypothèse) | ✅ |
| `SystemNotifier`/`NullSystemNotifier` — abstraction prête à recevoir une future implémentation, aucun bricolage avec une bibliothèque tierce | ✅ |
| `controller.py::prepare_notifications()` — "au démarrage, si activées, préparer les prochaines notifications", réutilise la préférence existante `notifications_enabled` | ✅ |
| Dégradation systématique — ne plante jamais, journalisé, jamais d'erreur technique affichée | ✅ |
| Aucun nouveau provider, aucun nouveau service métier, aucune nouvelle dépendance, aucun nouveau réglage | ✅ |
| Aucune régression | ✅ |
| 22 nouveaux tests — 2000 total | ✅ |

---

## v0.4.29 — Recherche interactive ✅ Sprint 55 (2026-07-13)

| Fonctionnalité | Statut |
|---|---|
| Résultats de recherche cliquables — championnat, événement, circuit | ✅ |
| Clic championnat → navigue vers "Mon calendrier" (meilleure destination existante, aucune page dédiée) | ✅ |
| Clic événement → ouvre la "fiche événement" existante (Sprint 42), via un helper partagé (aucune duplication) | ✅ |
| Clic circuit → ouvre la "fiche Circuit" existante (Sprint 47), via un helper partagé (aucune duplication) | ✅ |
| `SearchResultItem` porte désormais une identité (`championship_id`/`event_uid`/`circuit_key`), jamais affichée | ✅ |
| Aucun nouveau service, aucun nouveau provider, aucune nouvelle logique métier | ✅ |
| Design System/Layout System strictement respectés — les cartes deviennent interactives, rien de plus | ✅ |
| Aucune régression | ✅ |
| 10 nouveaux tests — 1978 total | ✅ |

---

## v0.4.28 — Préparation Beta (Recette UX) ✅ Sprint 54 (2026-07-13)

| Fonctionnalité | Statut |
|---|---|
| Audit UX complet des 7 pages (Dashboard, Ce week-end, Mon calendrier, Recherche, Favoris, Préférences, À propos) | ✅ |
| Cohérence des icônes — 3 corrections (en-têtes Favoris/Dashboard alignés sur la variante pleine du rail de navigation, emoji "✅" de la boîte de dialogue de succès remplacé par une icône Material thématisée) | ✅ |
| Cohérence des espacements — 8 valeurs codées en dur remplacées par le token `theme.Spacing.XXS` | ✅ |
| Cohérence des messages vides — ponctuation des titres `EmptyState` standardisée | ✅ |
| Cohérence des textes — "À propos" affiche désormais le vrai numéro de version (`motorsport_calendar.__version__`) au lieu d'un texte statique sans numéro | ✅ |
| Doublons supprimés — `nav_home`/`nav_calendar`, chaînes mortes jamais référencées | ✅ |
| Aucune nouvelle fonctionnalité, aucun nouveau provider, aucune évolution des services/providers/modèles | ✅ |
| Aucune régression | ✅ |
| 7 nouveaux tests — 1968 total | ✅ |

---

## v0.4.27 — Nouveautés & Centre d'accueil ✅ Sprint 53 (2026-07-13)

| Fonctionnalité | Statut |
|---|---|
| Dashboard transformé en véritable page d'accueil du produit | ✅ |
| Section "Nouveautés" — carte discrète (nouvelle version, résumé, bouton "Voir la version") si une mise à jour est disponible, rien sinon — réutilise `UpdateService` (Sprint 51) et son handler de bouton, sans duplication | ✅ |
| Section "Accès rapides" — 4 cartes de navigation (Ce week-end, Mon calendrier, Recherche, Favoris), navigation pure | ✅ |
| Section "État de Motorsport Calendar" — version actuelle, championnats actifs, fournisseurs réellement fonctionnels (dérivé des entrées récupérées, jamais codé en dur), favoris — toutes issues des services existants | ✅ |
| `gui/dashboard.py::DashboardData`/`build_dashboard_data()` étendus (5 champs passthrough + 1 champ agrégé) | ✅ |
| `gui/controller.py::get_dashboard_data()` — récupération concurrente (`asyncio.gather`) des entrées week-end et de la vérification de mise à jour | ✅ |
| Aucun nouveau service, aucun nouveau provider, aucune nouvelle dépendance | ✅ |
| Aucune logique métier dans la vue — uniquement `Dashboard`, `UpdateService`, `FavoritesService`, `ProviderRegistry` réutilisés | ✅ |
| Design System/Layout System/Components strictement respectés — aucune évolution graphique | ✅ |
| Aucune régression | ✅ |
| 29 nouveaux tests — 1961 total | ✅ |

---

## v0.4.26 — Préférences avancées ✅ Sprint 52 (2026-07-12)

| Fonctionnalité | Statut |
|---|---|
| Page Préférences transformée en centre de configuration réel — 4 sections (Notifications/Mises à jour/Calendrier/Application) | ✅ |
| Notifications configurables (activées, favoris uniquement, délai par défaut) — réutilise `NotificationService` | ✅ |
| Vérification des mises à jour configurable (activer/désactiver) — réutilise la préférence `update_check_enabled` (Sprint 51) | ✅ |
| Année par défaut ("Année en cours" ou année fixe) — `gui/models.py::resolve_default_year()` | ✅ |
| Rappel avant export (VALARM 0/15/30/60 min) — override `config.ics.alarm_minutes` pour les exports GUI uniquement | ✅ |
| Section Application préparée (Thème/Langue/Format horaire) — `PreferencesModel` repensé, non implémenté (brief explicite) | ✅ |
| Aucune logique métier dans la vue — tous les contrôles construits/câblés par `main_view.py` | ✅ |
| Design System/Layout System/Components strictement respectés — aucune évolution graphique | ✅ |
| Aucun nouveau provider, aucune nouvelle page | ✅ |
| Aucune régression | ✅ |
| 9 nouveaux tests nets (dont plusieurs classes de tests réécrites) — 1932 total | ✅ |

---

## v0.4.25 — Vérification des mises à jour ✅ Sprint 51 (2026-07-12)

| Fonctionnalité | Statut |
|---|---|
| `gui/update_service.py::UpdateService` — récupère un manifeste JSON distant, aucune dépendance Flet, aucun couplage plateforme (GitHub ou autre) | ✅ |
| Comparaison de versions numérique (`is_newer()`) — jamais lexicographique, `0.4.9 < 0.4.10 < 0.5.0 < 1.0.0` correctement ordonné | ✅ |
| `config/models.py::UpdateConfig` — URL du manifeste configurable via `config.yaml`, vide par défaut (aucune plateforme codée en dur) | ✅ |
| `gui/controller.py::check_for_update()` — résout version courante + URL + préférence, délègue toute la logique à `UpdateService` | ✅ |
| Préférence `update_check_enabled` (défaut activé, fondations seulement, aucune UI de bascule ce sprint) | ✅ |
| Boîte de dialogue "nouvelle version disponible" au démarrage — version actuelle, nouvelle version, résumé, bouton "Voir la version" | ✅ |
| Aucune mise à jour/installation/redémarrage automatique | ✅ |
| Aucun nouveau provider, aucune évolution des providers existants | ✅ |
| Aucune régression | ✅ |
| 58 nouveaux tests — 1923 total | ✅ |

---

## v0.4.24 — Audit & Consolidation ✅ Sprint 50 (2026-07-12)

| Fonctionnalité | Statut |
|---|---|
| Audit complet du projet — `docs/AUDIT.md` (état général, points forts/faibles, dette restante, 10 fichiers les plus volumineux, services critiques, recommandations) | ✅ |
| Dette Ruff : 149 → 0 erreur | ✅ |
| Dette mypy `motorsport_calendar/` : 87 → 23 erreurs (une seule famille documentée, décalage stubs Flet) | ✅ |
| Dette mypy `tests/` : 402 → 157 erreurs (`mypy.ini` relâché pour les tests, pratique standard `unittest.mock`) | ✅ |
| Bug réel corrigé — `core/service.py::CalendarService.export_championship` (jamais appelée par aucun code réel) | ✅ |
| 21 docstrings publiques manquantes ajoutées, après triage des redéfinitions ABC déjà documentées | ✅ |
| Duplication de tests réduite — `tests/conftest.py::load_real_fixture()` factorisé depuis 8 fichiers | ✅ |
| Optimisation mesurée — fetch concurrent des providers (`cli.py::generate`, `gui/controller.py::generate_calendar`), ~10x, comportement strictement identique | ✅ |
| Aucune fonctionnalité, aucun provider, aucune page, aucun changement de comportement utilisateur (conforme à la consigne) | ✅ |
| Aucune régression | ✅ |
| 2 nouveaux tests (non-régression performance) — 1865 total | ✅ |

---

## v0.4.23 — Packaging Alpha ✅ Sprint 49 (2026-07-12)

| Fonctionnalité | Statut |
|---|---|
| `utils/paths.py` — répertoires utilisateur multi-plateforme (Linux XDG, Windows `%APPDATA%`/`%LOCALAPPDATA%`), réutilisés par préférences GUI, `HttpCache`, `ConfigService` | ✅ |
| Cache HTTP et préférences GUI ne s'écrivent plus jamais dans le dépôt Git ni un chemin Linux-only codé en dur | ✅ |
| Icône application officielle (Brand Set v1.0) intégrée — fenêtre/barre des tâches et build Windows (`icon_windows.ico`) ; favicon et logos SVG intégrés au build, non consommés par les vues (aucune évolution du Design System) | ✅ |
| `gui/app.py::assets_dir` résolu depuis le fichier, jamais depuis le répertoire de lancement | ✅ |
| Export ICS confirmé déjà indépendant du dépôt — validé par de nouveaux tests explicites | ✅ |
| Build Linux validé en direct (`flet build linux`) — voir `docs/PACKAGING.md`/`docs/JOURNAL.md` pour le détail exact | ✅ |
| `docs/PACKAGING.md` — procédure officielle de build documentée (Linux + Windows) | ✅ |
| Aucune fonctionnalité utilisateur, aucun provider, aucun service métier modifié (conforme à la consigne) | ✅ |
| Aucune régression | ✅ |
| 26 nouveaux tests — 1863 total | ✅ |

---

## v0.4.22 — Finalisation des providers (WEC) ✅ Sprint 48 (2026-07-12)

| Fonctionnalité | Statut |
|---|---|
| `OfficialWecSource` — implémentation réelle, fiawec.com (même CMS/JSON-LD que ELMS/MLMC, sous-classe `AcoSportsEventSource`) | ✅ |
| Saison WEC 2026 validée en direct : 8 événements, 50 sessions, UID uniques, fuseaux horaires corrects sur 8 circuits | ✅ |
| Intégration confirmée : Dashboard, Ce week-end, Recherche, agrégateur `generate`/`generate-wec` | ✅ |
| `aco_series/sports_event_base.py` étendu (Free Practice 4/Hyperpole/Warm-up, exclusion prologue, points d'extension `_race_session_end`/`_race_url_belongs_to_season`) — purement additif, ELMS/MLMC inchangés | ✅ |
| Bug réel détecté et corrigé en conditions live (durée de course WEC déduite du nom de l'épreuve — l'`endDate` JSON-LD aurait silencieusement donné 8h au lieu de 24h pour Le Mans) | ✅ |
| IMSA/WorldSBK ré-investigués — toujours aucune source exploitable trouvée (imsa.com bloque désormais son propre robots.txt ; nouveaux hôtes Pulselive découverts pour WorldSBK mais aucun endpoint exploitable) | ✅ |
| Aucune régression — tests adaptés là où ils s'appuyaient sur l'ancien stub WEC (IMSA prend le relai comme exemple de source non implémentée) | ✅ |
| 37 nouveaux tests — 1837 total | ✅ |

---

## v0.4.21 — Circuit Explorer ✅ Sprint 47 (2026-07-12)

| Fonctionnalité | Statut |
|---|---|
| `gui/circuit_service.py` — nouveau `CircuitService`, base de données des circuits construite uniquement à partir des événements déjà chargés (aucun provider, aucun appel réseau) | ✅ |
| Chaque circuit : nom, pays, nombre de championnats, liste des championnats, nombre total d'événements, première/dernière saison disponibles | ✅ |
| Circuits dédupliqués/fusionnés entre championnats (même normalisation "compacte" que la recherche globale, Sprint 45) | ✅ |
| Fiche Circuit — nom du circuit cliquable depuis la fiche événement, ouvre une boîte de dialogue (nom, pays, championnats, historique des événements, nombre total de courses) | ✅ |
| `ChampionshipCard` gagne un point d'extension optionnel `on_circuit_click`, `None` par défaut partout ailleurs — zéro changement visuel pour Ce week-end/Dashboard/Favoris | ✅ |
| Zéro nouveau provider, zéro nouvelle source de données (conforme à la consigne) | ✅ |
| Aucune régression | ✅ |
| 35 nouveaux tests — 1800 total | ✅ |

---

## v0.4.20 — Moteur de notifications ✅ Sprint 46 (2026-07-12)

| Fonctionnalité | Statut |
|---|---|
| `gui/notification_service.py` — nouveau `NotificationService`, moteur de calcul hors-ligne (aucun appel réseau), indépendant de l'interface (zéro dépendance Flet), réutilisable plus tard par Windows/Linux/macOS sans modification | ✅ |
| 5 types de notifications (début du week-end, première session, qualifications, sprint, course), délais configurables (24h/12h/1h/15min ou toute combinaison) | ✅ |
| Fonctionne sur tous les championnats ou uniquement les favoris (`favorites_only`/`favorite_ids`) | ✅ |
| 3 préférences persistées (activées, délai par défaut, favoris uniquement) sur le fichier de préférences centralisé existant | ✅ |
| Aucune notification système envoyée ce sprint — fondations uniquement, conforme à la consigne | ✅ |
| Zéro nouveau provider, zéro nouvelle source de données, zéro évolution graphique (conforme à la consigne) | ✅ |
| Aucune régression | ✅ |
| 33 nouveaux tests — 1765 total | ✅ |

---

## v0.4.19 — Recherche globale ✅ Sprint 45 (2026-07-12)

| Fonctionnalité | Statut |
|---|---|
| `gui/search_service.py` — nouveau `SearchService`, recherche instantanée hors-ligne sur championnats/événements/circuits déjà chargés en mémoire, index reconstruit uniquement quand les données changent | ✅ |
| Normalisation accents/casse/séparateurs — `spa`/`Spa`/`SPA`/`spa francorchamps` et `Le Mans`/`lemans` retrouvent tous les mêmes résultats | ✅ |
| Résultats regroupés par type (Championnats/Événements/Circuits), triés par pertinence puis alphabétiquement | ✅ |
| Nouvelle page "Recherche" (`gui/views/search.py`) — nouvelle destination de navigation, 100 % Layout System + composants existants (`PageHeader`/`Section`/`CardList`/`EmptyState`), aucun nouveau composant | ✅ |
| Recherche instantanée pendant la saisie, `EmptyState` distinct pour "aucune saisie" et "aucun résultat" | ✅ |
| Zéro nouveau provider, zéro nouvelle source de données, zéro appel réseau supplémentaire (conforme à la consigne) | ✅ |
| Aucune régression — Design System, Layout System, Components réutilisés au maximum | ✅ |
| 46 nouveaux tests — 1732 total | ✅ |

---

## v0.4.18 — Favoris intelligents ✅ Sprint 44 (2026-07-12)

| Fonctionnalité | Statut |
|---|---|
| `gui/favorites_service.py` — nouveau `FavoritesService`, source de vérité unique pour les championnats favoris, persisté dans le fichier de préférences centralisé | ✅ |
| "Mes favoris" devient une vraie page — accordéon de championnats sélectionnables réutilisé de "Mon calendrier" via `gui/components/championship_selector.py` (extraction, aucune duplication) | ✅ |
| Favoris utilisés automatiquement partout — Dashboard/Ce week-end (favoris en premier), Mon calendrier (pré-sélection automatique) | ✅ |
| Correction d'un bug latent de `_save_prefs()` qui écrasait silencieusement les autres clés du fichier de préférences | ✅ |
| Zéro nouveau provider, zéro nouvelle source de données (conforme à la consigne) | ✅ |
| Aucune régression — Design System, Layout System, Components réutilisés au maximum | ✅ |
| 36 nouveaux tests — 1686 total | ✅ |

---

## v0.4.17 — Refonte UX de "Mon calendrier" ✅ Sprint 43 (2026-07-11)

| Fonctionnalité | Statut |
|---|---|
| Assistant 4 étapes remplacé par une page unique réorganisée — championnats en point d'entrée (accordéons par catégorie, boutons sélectionnables), saison en contrôle secondaire (haut droite), résumé permanent, explorateur conditionnel, bouton "Créer" toujours visible (pied de page fixe) | ✅ |
| `PageHeader`/`PageContainer` (Layout System) — nouveaux slots optionnels `trailing`/`footer`, `None` par défaut, zéro impact sur les 5 autres pages | ✅ |
| `GenerateState` simplifié — machinerie de l'assistant (`current_step`/`STEP_COUNT`/`step_valid`/`can_advance`/`can_go_back`) retirée | ✅ |
| Sprint purement ergonomique — aucune nouvelle fonctionnalité métier, aucun nouveau provider, aucune modification de la logique métier ni des modèles de domaine | ✅ |
| Aucune régression — Design System, Components réutilisés au maximum | ✅ |
| Tests adaptés + nouveaux tests — 1650 total | ✅ |

---

## v0.4.16 — Fiche événement ✅ Sprint 42 (2026-07-10)

| Fonctionnalité | Statut |
|---|---|
| `gui/event_details.py` — logique pure (sans Flet, sans I/O), construit la fiche (championnat/nom/circuit/pays/date + sessions triées chronologiquement) en réutilisant `ChampionshipCardData`/`SessionRow` | ✅ |
| Chaque événement de l'explorateur de saison (Sprint 41) devient cliquable — ouvre une fiche via `ChampionshipCard` réutilisé tel quel dans une boîte de dialogue | ✅ |
| `event_display.session_type_label` — labels de session extraits de `upcoming_weekend.py` pour un second consommateur, aucune duplication | ✅ |
| Zéro nouveau provider, zéro nouvelle source de données (conforme à la consigne) | ✅ |
| Aucune régression — Design System, Layout System, wizard, providers inchangés | ✅ |
| 20 nouveaux tests — 1639 total | ✅ |

---

## v0.4.15 — Explorer une saison ✅ Sprint 41 (2026-07-10)

| Fonctionnalité | Statut |
|---|---|
| `gui/season_explorer.py` — logique pure (sans Flet, sans I/O), liste d'événements triée chronologiquement et regroupée par mois pour la sélection courante | ✅ |
| "Mon calendrier" gagne un explorateur de saison — nom/championnat/circuit/pays/date par événement, sous le résumé de sélection (Sprint 40), visible sur les 4 étapes de l'assistant existant (inchangé) | ✅ |
| Mise à jour automatique à chaque changement de sélection (année/championnat) — aucun nouveau fetch réseau, réutilise `year_events` déjà récupéré | ✅ |
| Zéro nouveau provider, zéro nouvelle source de données (conforme à la consigne) | ✅ |
| Aucune régression — Design System, Layout System, wizard, providers inchangés | ✅ |
| 23 nouveaux tests — 1619 total | ✅ |

---

## v0.4.14 — Calendrier interactif ✅ Sprint 40 (2026-07-10)

| Fonctionnalité | Statut |
|---|---|
| `gui/calendar_selection.py` — logique pure (sans Flet, sans I/O), agrégation événements/sessions/période pour la sélection année/championnats courante | ✅ |
| `controller.get_calendar_year_events(year)` — un seul fetch par année pour tous les championnats enregistrés ; bascule de championnat = filtrage local instantané, aucune requête réseau par case cochée | ✅ |
| "Mon calendrier" devient un navigateur de calendrier — résumé persistant (événements/sessions/période) visible sur les 4 étapes de l'assistant existant (inchangé) | ✅ |
| Zéro nouveau provider, zéro nouvelle source de données (conforme à la consigne) | ✅ |
| Aucune régression — Design System, Layout System, wizard, providers inchangés | ✅ |
| 25 nouveaux tests — 1596 total | ✅ |

---

## v0.4.13 — Dashboard Motorsport ✅ Sprint 39 (2026-07-10)

| Fonctionnalité | Statut |
|---|---|
| `gui/dashboard.py` — logique pure (sans Flet), agrégation des statistiques de saison + prochain week-end + prochain départ | ✅ |
| `gui/views/dashboard.py` — nouvelle vue, 100 % Layout System + composants existants, aucun nouveau token | ✅ |
| Le Tableau de bord devient la page d'accueil (premier onglet de navigation) | ✅ |
| Zéro nouveau provider, zéro nouvelle source de données (conforme à la consigne) | ✅ |
| `controller.get_dashboard_data()` réutilise le pipeline de fetch existant — aucune requête réseau supplémentaire dédiée | ✅ |
| Aucune régression — Design System, navigation, providers inchangés | ✅ |
| 32 nouveaux tests — 1571 total, couverture 96 % | ✅ |

---

## v0.4.12 — Motorcycle Racing (MotoGP, Moto2, Moto3, WorldSBK) ✅ Sprint 38 (2026-07-10)

| Fonctionnalité | Statut |
|---|---|
| `providers/motogp_series/` — abstraction partagée découverte en cours de sprint (MotoGP/Moto2/Moto3 sur la même API officielle Dorna, une requête par saison pour les 3 classes) | ✅ |
| `providers/motogp/`, `moto2/`, `moto3/` — trois nouveaux championnats sur API officielle réelle, aucun scraping | ✅ |
| CLI `generate-motogp`, `generate-moto2`, `generate-moto3` | ✅ |
| `providers/worldsbk/` — architecture complète + stub `OfficialWorldSbkSource` après investigation exhaustive (aucune source publique exploitable trouvée) | ✅ |
| CLI `generate-worldsbk` (exit propre si source non implémentée, comme WEC/IMSA) | ✅ |
| Nouveau groupe GUI "🏍 Moto" (catégorie `Category.MOTO`, déjà anticipée depuis le Sprint 37) | ✅ |
| Bug réel détecté et corrigé en conditions live (DTSTART non normalisé en UTC, TZID synthétique sans VTIMEZONE) | ✅ |
| Aucune régression — Design System, navigation, autres providers inchangés | ✅ |
| 166 nouveaux tests — 1539 total, couverture 96 % | ✅ |

---

## v0.4.11 — GT Racing (GTWC Europe/America/Asia, IGTC) ✅ Sprint 37 (2026-07-10)

| Fonctionnalité | Statut |
|---|---|
| `providers/sro_series/` — abstraction partagée découverte en cours de sprint (les 4 sites SRO tournent sur le même CMS, tableaux HTML `timetable__table`) | ✅ |
| `providers/gtwc_europe/`, `gtwc_america/`, `gtwc_asia/`, `igtc/` — quatre nouveaux championnats, zéro duplication de scraping/mapping | ✅ |
| CLI `generate-gtwc-europe`, `generate-gtwc-america`, `generate-gtwc-asia`, `generate-igtc` | ✅ |
| Nouveau groupe GUI "🚗 GT" (catégories, noms lisibles, Wizard, "Ce week-end") | ✅ |
| Détection dynamique du format Sprint Cup (2 Race) vs Endurance (1 Race), sans supposer un nombre fixe de sessions | ✅ |
| Bug réel détecté et corrigé en conditions live (jour UTC incorrect pour les circuits loin de l'UTC, ex. Bathurst — calcul d'offset local/GMT par ligne, pas de base de fuseaux externe) | ✅ |
| Aucune régression — Design System, navigation, autres providers inchangés | ✅ |
| 184 nouveaux tests — 1373 total, couverture 96 % | ✅ |

---

## v0.4.10 — Extension IMSA — sortie de l'écosystème ACO ✅ Sprint 36 (2026-07-10)

| Fonctionnalité | Statut |
|---|---|
| `providers/imsa/` — premier championnat entièrement hors écosystème ACO, valide que l'architecture Provider/Source généralise à un organisateur totalement nouveau | ✅ |
| CLI `generate-imsa` (exit propre si source non implémentée, comme WEC) | ✅ |
| IMSA disponible dans le Wizard, "Ce week-end", l'agrégateur, catégories (groupe Endurance), noms lisibles | ✅ |
| Investigation exhaustive des sources : imsa.com bloqué (Cloudflare 403), Al Kamel = archive post-course, Wikipedia = pas d'horaires de session, Sportscar365 = prose non structurée | ✅ |
| `OfficialImsaSource` — stub confirmé avec l'utilisateur (`NotImplementedError`), même traitement que WEC — aucun horaire inventé | ✅ |
| Aucun provider existant modifié — architecture validée sans casse | ✅ |
| 39 nouveaux tests — 1189 total, zéro régression | ✅ |

---

## v0.4.9 — Extension Endurance (ELMS, Michelin Le Mans Cup) ✅ Sprint 35 (2026-07-10)

| Fonctionnalité | Statut |
|---|---|
| `providers/aco_series/` — abstraction partagée découverte en cours de sprint (WEC/ELMS/MLMC sur le même CMS ACO, JSON-LD schema.org) | ✅ |
| `providers/elms/` et `providers/mlmc/` — deux nouveaux championnats, zéro duplication HTTP/parsing | ✅ |
| CLI `generate-elms` et `generate-mlmc` | ✅ |
| ELMS/MLMC disponibles dans le Wizard, "Ce week-end", catégories (groupe Endurance), noms lisibles | ✅ |
| Road to Le Mans traitée comme un round MLMC, pas un championnat séparé (fidèle au site officiel) | ✅ |
| Bug réel détecté et corrigé en conditions live (durée de course "Road to Le Mans" à +61h au lieu de ~3h, cap de plausibilité ajouté) | ✅ |
| Aucune régression — Design System, navigation, icônes, préférences inchangés | ✅ |
| 105 nouveaux tests — 1150 total, couverture 96 % | ✅ |

---

## v0.4.8 — Extension Formula (Formula E) ✅ Sprint 34 (2026-07-10)

| Fonctionnalité | Statut |
|---|---|
| `providers/formula_e/` — nouveau championnat, réutilise entièrement `F1CalendarBaseSource` (aucune duplication HTTP/cache/mapping) | ✅ |
| CLI `generate-formula-e YEAR OUTPUT.ics` | ✅ |
| Formula E disponible dans le Wizard, "Ce week-end", les catégories, les noms lisibles | ✅ |
| `cli.py` : 5 commandes `generate-*` copiées-collées factorisées vers un helper partagé, comportement inchangé | ✅ |
| F1 Academy vérifié déjà entièrement intégré (aucune régression, aucune modification nécessaire) | ✅ |
| Aucune régression — Design System, navigation, icônes, préférences inchangés | ✅ |
| 46 nouveaux tests — 1045 total, couverture 96 % | ✅ |

---

## v0.4.7 — Registre des identités visuelles de championnat ✅ Sprint 33 (2026-07-07)

| Fonctionnalité | Statut |
|---|---|
| `gui/championship_assets.py` — registre central `championship_id` → logo (extensible couleur/icône) | ✅ |
| Point d'entrée unique `get_championship_asset()` — aucune vue/composant ne connaît un chemin de fichier | ✅ |
| `ChampionshipCard` : logo affiché à gauche du titre, `IconSize.LG` (24px), aucun `if championnat == ...` | ✅ |
| Aucun fichier logo officiel livré — repli gracieux, layout actuel inchangé pixel pour pixel | ✅ |
| Aucune régression — Design System, navigation, providers, layout inchangés | ✅ |
| 16 nouveaux tests — 999 total, couverture 95 % | ✅ |

---

## v0.4.6 — Normalisation des métadonnées des événements ✅ Sprint 32 (2026-07-07)

| Fonctionnalité | Statut |
|---|---|
| `gui/event_display.py` — normalisation dédiée (jamais "Unknown", jamais de doublon) | ✅ |
| Règle documentée pour le nom de Grand Prix absent/court/déjà complet | ✅ |
| Investigation F1 vs F2/F3/F1 Academy documentée (cause API + cause mapping) | ✅ |
| `ChampionshipCardData` : circuit/pays optionnels, composant toujours sans logique métier | ✅ |
| Aucune régression — providers, Design System, navigation inchangés | ✅ |
| 26 nouveaux tests — 983 total, couverture 95 % | ✅ |

---

## v0.4.5 — Layout System ✅ Sprint 31 (2026-07-07)

| Fonctionnalité | Statut |
|---|---|
| `gui/components/layout/` — PageContainer, PageHeader, Section, SectionHeader, CardList, EmptyState, PageSpacing | ✅ |
| Les 5 vues migrées : plus aucune ne construit son propre conteneur/en-tête/carte | ✅ |
| Une nouvelle page se compose désormais sans code de mise en page manuel | ✅ |
| Aucune régression — Design System, couleurs, icônes, navigation, providers inchangés | ✅ |
| 51 nouveaux tests — 957 total, couverture 95 % | ✅ |

---

## v0.4.4 — Composant ChampionshipCard ✅ Sprint 30 (2026-07-07)

| Fonctionnalité | Statut |
|---|---|
| `gui/components/` — première bibliothèque de composants réutilisables | ✅ |
| `ChampionshipCard` — carte unique extraite de "Ce week-end", réutilisable partout | ✅ |
| En-tête (championnat, Grand Prix, circuit, pays), grille de sessions alignée | ✅ |
| Point d'extension `footer` prêt pour Favori/Notifications/Export ICS/Partage/Résultats | ✅ |
| "Ce week-end" migré : la vue construit une liste de `ChampionshipCard`, aucun layout propre | ✅ |
| Aucune régression — Design System, navigation, providers inchangés | ✅ |
| 23 nouveaux tests — 903 total, couverture 95 % | ✅ |

---

## v0.4.3 — Ce week-end : version fonctionnelle ✅ Sprint 29 (2026-07-07)

| Fonctionnalité | Statut |
|---|---|
| Recherche automatique du prochain week-end de course (F1, F2, F3, F1 Academy, WEC) | ✅ |
| Une carte par championnat — Grand Prix, circuit, pays (drapeau), sessions chronologiques | ✅ |
| Tri Formula puis Endurance, chronologique à l'intérieur de chaque catégorie | ✅ |
| 3 états : chargement / aucune course (avec prochaine date connue) / trouvé | ✅ |
| Fetch une seule fois par lancement, cache HTTP existant réutilisé (jamais de réseau à chaque ouverture) | ✅ |
| Aucun nouveau provider — réutilise `registry`/`source_registry`/`HttpCache` tels quels | ✅ |
| 34 nouveaux tests — 880 total, couverture 95 % | ✅ |

---

## v0.4.2 — Uniformisation du layout (UX) ✅ Sprint 27 (2026-07-07)

| Fonctionnalité | Statut |
|---|---|
| `theme.page_shell()` — grille de page unique (max-width 1000px, centrée, contenu toujours aligné à gauche) | ✅ |
| Ce week-end / Mes favoris / À propos alignés à gauche (fin du centrage mid-écran) | ✅ |
| En-tête uniforme (`section_title` + `Divider`) sur les 5 pages, y compris Mon calendrier | ✅ |
| Largeurs de cartes uniformisées (suppression des largeurs fixes ad hoc) | ✅ |
| `TestAllViewsShareTheSameGrid` — verrou anti-régression sur le gabarit partagé | ✅ |
| 18 nouveaux tests — 837 total, couverture 94 % | ✅ |

---

## v0.4.1 — Release Alpha Phase 2 — UX & Design System ✅ Sprint 26 (2026-07-07)

| Fonctionnalité | Statut |
|---|---|
| `gui/theme.py` — design system (couleurs BApps + Motorsport Calendar, spacing, radius, icônes, boutons, cartes) | ✅ |
| "Mon calendrier" transformé en assistant 4 étapes (saison / championnats / destination / créer) | ✅ |
| Navigation étapes gatée par validité, retour + puces d'étapes déjà visitées cliquables | ✅ |
| Récapitulatif étape finale avec liens "Modifier" vers chaque étape | ✅ |
| Uniformisation visuelle Ce week-end / Mes favoris / Préférences / À propos (theme uniquement, contenu inchangé) | ✅ |
| Emplacement logo préparé (`logo_placeholder()`, `gui/assets/logo/README.md`) — placeholder, pas d'asset définitif | ✅ |
| Correction warnings dépréciation `ft.Colors.WHITE12` → `WHITE_12` (Flet 0.85) | ✅ |
| 55 nouveaux tests — 819 total, couverture 94 % | ✅ |

---

## v0.4.0 — Release Alpha Phase 1 ✅ Sprint 25 (2026-07-06)

| Fonctionnalité | Statut |
|---|---|
| Navigation 5 pages : Ce week-end / Mon calendrier / Mes favoris / Préférences / À propos | ✅ |
| Architecture `views/` — une vue par module, indépendante et testable | ✅ |
| `views/weekend.py` — skeleton layout (Circuit, Pays, Championnat, Sessions) | ✅ |
| `views/favorites.py` — placeholder Mes favoris | ✅ |
| `views/preferences.py` — 6 rubriques préférences avec chip "prochainement" | ✅ |
| `PreferencesModel` — dataclass frozen avec 6 champs typés | ✅ |
| `main_view.py` refactorisé : shell de navigation uniquement | ✅ |
| 44 nouveaux tests — 764 total | ✅ |

---

## v0.3.2 — Desktop Alpha 3 — Product Polish ✅ Sprint 24 (2026-07-06)

| Fonctionnalité | Statut |
|---|---|
| Navigation multi-pages : Accueil / Calendrier / À propos | ✅ |
| `ft.NavigationRail` 3 destinations, responsive (étendu >900px) | ✅ |
| Championnats groupés visuellement : 🏎 Formula / 🏁 Endurance | ✅ |
| Architecture catégories extensible (`categories.py`) : FORMULA, ENDURANCE, MOTO, RALLY, AMERICA | ✅ |
| Écran Accueil : icône, description, CTA vers Calendrier | ✅ |
| Écran À propos : version, développeur BApps, GitHub, Licence MIT | ✅ |
| `strings.py` étendu (nav + about) | ✅ |
| 25 nouveaux tests (`test_gui_categories.py`) — 720 total | ✅ |

---

## Backlog non daté (mis à jour 2026-07-14)

> Ce bloc était à l'origine trois sections de planification pré-Sprint 25
> ("v0.4.0 Phase 2", "v0.5.0", "v1.0.0") jamais purgées au fur et à mesure
> que leur contenu était réalisé (`OfficialWecSource` ✅ Sprint 48,
> `ELMSProvider` ✅ Sprint 35 — tous deux listés ici comme encore à faire
> jusqu'à cette mise à jour). Regroupé en un seul backlog, débarrassé des
> items déjà faits ; ce qui reste est vérifié contre l'état réel du code
> et de `docs/RELEASE.md`.

| Fonctionnalité | Priorité |
|---|---|
| ~~Packaging Windows `.exe` via `flet build windows`~~ — ✅ validé pour de vrai sur une machine Windows 11 (Sprint RC-01), voir `docs/PACKAGING.md` §8 | ~~🔴 HAUTE~~ |
| Publication PyPI (`pip install motorsport-calendar`) — préparation terminée (MC-002 P0-9 : nom disponible, `twine check` OK, workflow tag-triggered déjà en place) ; reste à enregistrer le trusted publisher côté pypi.org puis pousser le premier tag `v*.*.*`, voir `docs/RELEASE.md` §6.1 | 🔴 HAUTE |
| ~~Corriger la troncature du dropdown "Année par défaut" (Préférences)~~ — ✅ résolu (MC-002 P0-8) | ~~🟡 MOYENNE~~ |
| `PorscheSupercupProvider` — scraping `racing.porsche.com` + venues F1 (voir `docs/DATA_SOURCES.md`) | 🟢 BASSE |
| Mémorisation du dernier fichier de sortie (Mon calendrier) | 🟡 MOYENNE |
| `DESCRIPTION` dans les VEVENTs (circuit, pays, type de session) | 🟡 MOYENNE |
| Export JSON (machine-readable) | 🟢 BASSE |
| Documentation MkDocs complète (API + guides utilisateur) | 🟡 MOYENNE |
| API Python publique documentée et stable | 🟡 MOYENNE |
| Badge couverture dans README | 🟢 BASSE |
| GitHub Release avec assets ICS précalculés | 🟢 BASSE |
| Source réelle IMSA / WorldSBK, si une API publique apparaît un jour (voir `docs/DATA_SOURCES.md`) | 🟢 BASSE |
