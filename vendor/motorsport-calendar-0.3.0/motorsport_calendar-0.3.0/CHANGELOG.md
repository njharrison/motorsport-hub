# Changelog

All notable changes to this project will be documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
This project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.3.0] — 2026-07-23

Consolidation de tous les sprints jamais publiés depuis `[0.2.0]` (CLI multi-provider
uniquement, avant l'application desktop) : l'intégralité de l'app GUI Flet, 12
championnats supplémentaires, favoris, recherche, notifications, tableau de bord,
préférences, et le packaging desktop Linux/Windows. Chaque sprint est conservé
ci-dessous tel quel (aucun contenu résumé ni supprimé), simplement regroupé sous une
unique version au lieu de dizaines d'entrées `[Unreleased]` distinctes jamais taguées.

### MC-002 — Sprint P0 v1.0

Traitement exhaustif des points P0 identifiés par l'audit de préparation v1.0 (programme
MC-001) avant toute Release Candidate. Un P0 à la fois, un commit dédié par P0 — voir
l'historique Git pour le détail commit par commit.

#### Fixed

- **WEC / ELMS / MLMC : fuseau horaire invalide dans l'export ICS (P0-1).** Les horaires
  JSON-LD de ces trois séries (organisées par l'ACO) étaient conservés avec leur décalage
  UTC local d'origine (ex. `+02:00`) au lieu d'être normalisés en UTC — `icalendar`
  produisait alors un `TZID="UTC+02:00"` synthétique, non conforme RFC 5545 (aucun
  identifiant IANA, aucun bloc `VTIMEZONE` associé), que certains clients calendrier
  affichent avec une heure fausse ou rejettent purement et simplement. Corrigé en alignant
  `AcoSportsEventSource._parse_datetime` sur la convention déjà en place pour MotoGP/Moto2/
  Moto3 et les séries GT (SRO) : toute heure de session est désormais normalisée en UTC dès
  le parsing, avant de construire un `Session`. `IcsExporter` n'a pas eu besoin d'être
  modifié — un horodatage UTC se sérialise nativement en `DTSTART`/`DTEND` suffixés `Z`,
  sans `TZID` ni `VTIMEZONE`.
- **Préférences : la section Notifications ne notifiait jamais, silencieusement (P0-2).**
  Les 3 réglages (activées / favoris uniquement / délai) étaient de vrais interrupteurs,
  entièrement fonctionnels en apparence — mais Flet ne fournit aucun service de
  notification système sur aucune plateforme (`gui/system_notifications.py`,
  `NullSystemNotifier`), donc aucune notification n'était jamais réellement affichée, sans
  la moindre indication à l'utilisateur. Corrigé en remplaçant ces 3 contrôles par des
  lignes « Disponible prochainement » (`ComingSoonRow`), déjà utilisées pour la section
  Application — la section redeviendra des contrôles réels le jour où un vrai backend de
  notification OS existe. `NotificationService` (le calcul quoi/quand notifier) n'est pas
  modifié : il reste prêt, seule l'illusion d'un réglage actif disparaît.
- **CLI : la commande `export` était un stub qui échouait toujours (P0-3).** Commande
  publique, documentée (`motocal export --help`), qui affichait un message « bientôt
  disponible » puis quittait systématiquement en erreur (`exit 1`) — aucun argument ne
  pouvait la faire réussir. Retirée entièrement plutôt que masquée : elle n'avait jamais eu
  d'implémentation à préserver, et `generate`/`generate-*` couvrent déjà tout le besoin réel
  d'export. `motocal export` retourne désormais l'erreur standard Typer/Click « No such
  command », cohérente avec toute commande qui n'existe pas.
- **CI rouge : `mypy motorsport_calendar` échouait (34 erreurs), et `ruff format --check`
  aussi, sur 95 fichiers sans lien avec mypy (P0-4).** Deux causes distinctes, aucune
  n'étant un vrai bug :
  - `mypy` : les stubs de types fournis par Flet (écrits pour ~0.80) sont plus permissifs
    que la version réellement installée (0.85.3) sur les signatures `on_click`/`on_change`/
    `on_select` et quelques attributs de `Control` — famille déjà identifiée et
    délibérément non corrigée au Sprint 50 (réécrire ces signatures dans `main_view.py`
    représentait un risque réel de régression comportementale pour un gain de vérification
    statique seulement). `mypy.ini` gagne 5 sections `[mypy-motorsport_calendar.gui.*]`
    scopées aux seuls modules concernés (jamais `gui/*` entier) qui désactivent
    précisément `attr-defined`/`arg-type`/`assignment` — le reste de `gui/` (tout code
    futur inclus) reste sous vérification stricte complète. Un vrai bug distinct, lui
    corrigé plutôt que masqué : `main_view.py::on_page_resize` comparait `page.width`
    (`int | float | None` chez Flet) directement à `900`, `(page.width or 0)` corrige le
    cas `None` proprement.
  - `ruff format --check` : le projet n'a aucun `uv.lock` committé — `ruff>=0.8` non figé
    dans `pyproject.toml` signifie que chaque `uv sync` peut résoudre une version de ruff
    différente, et le formateur de ruff n'est pas garanti stable à l'octet près entre
    versions (même politique que Prettier/Black). 95 fichiers, jamais reformatés depuis
    l'installation d'une version plus récente de ruff, corrigés par un simple
    `ruff format` sur l'ensemble de l'arbre — aucun changement de comportement, uniquement
    des sauts de ligne/largeurs de ligne.
- **Versioning des builds desktop : `data/flutter_assets/version.json` affichait toujours
  `1.0.0` (P0-5).** Cause racine confirmée en lisant le source installé de `flet_cli` :
  `--build-name` (dérivé de `project.version`) stamp bien les métadonnées natives du
  paquet final, mais ne réécrit jamais le `pubspec.yaml` du scaffold Flutter sur disque —
  et c'est ce fichier que Flutter lit directement pour générer `version.json`, jamais
  `--build-name`. `motorsport_calendar/gui/pyproject.toml` déclare désormais
  `[tool.flet.flutter.pubspec] version = "0.3.0+1"`, le point d'extension officiel de Flet
  pour ce cas — gardé par un nouveau test (`test_gui_manifest_pins_flutter_pubspec_
  version_to_root`). Point de vigilance documenté dans `docs/RELEASE.md` : ce correctif ne
  s'applique que si le scaffold Flutter est réellement régénéré (Flet le saute quand un
  `build/` existant est réutilisé — exactement ce qui avait produit `1.0.0` la première
  fois) ; les procédures de build Linux et Windows suppriment désormais explicitement
  `motorsport_calendar/gui/build/` avant chaque build de release.
- **README public inexact sur les Préférences et les notifications (P0-6).** La page
  Préférences était annoncée avec des réglages « timezone, cache » qui n'ont jamais existé
  dans le schéma réel, et les notifications étaient présentées comme une fonctionnalité
  livrée (liste des fonctionnalités, description de la page, table de roadmap) alors
  qu'elles n'ont jamais notifié quoi que ce soit et sont désormais explicitement « à venir »
  depuis le P0-2. Les trois mentions corrigées pour refléter l'état réel : réglages
  effectivement présents (mise à jour au démarrage, saison par défaut, délai de rappel
  d'export), et notifications décrites comme un moteur de calcul interne déjà testé mais
  pas encore exposé (aucun backend OS natif chez Flet).
- **Troncature du dropdown « Année par défaut » en Préférences (P0-8).** Trouvé pendant le
  contrôle visuel réel Sprint RC-01 : « Année en cours » s'affichait tronqué en
  « Année en co ». C'était bien une largeur de `Dropdown` insuffisante, comme
  soupçonné à l'époque — `width` élargi de 160 à 190
  (`gui/main_view.py::_build_preferences_controls`) ; les autres options de ce dropdown
  sont de simples années sur 4 chiffres, seul ce libellé avait besoin de la place
  supplémentaire.
- **CI configurée pour des branches `main`/`develop` qui n'ont jamais existé dans ce dépôt
  (P0-9).** Découvert en préparant la diffusion PyPI, pas par MC-001 : `.github/workflows/
  ci.yml` ne se déclenchait que sur push/PR vers `main`/`develop`, alors que la branche
  réelle et unique de ce dépôt est `master` (confirmé : `git branch -a`, `remotes/origin/
  HEAD -> origin/master`) — la CI ne s'est donc probablement jamais exécutée sur un vrai
  push depuis un moment, ce qui explique en partie comment la dérive de formatage corrigée
  au P0-4 (95 fichiers) a pu s'accumuler sans être détectée. Déclencheurs corrigés vers
  `master`. Découverte apparentée : `pyproject.toml`'s `[project.urls] Changelog` pointait
  vers `/blob/main/CHANGELOG.md` (404 confirmé par requête réelle) au lieu de `/blob/
  master/CHANGELOG.md` (200 confirmé) — lien cassé qui aurait été visible sur la fiche
  PyPI du projet dès la première publication.

#### Added

- **Rafraîchissement manuel dans la GUI (P0-7).** Le Tableau de bord, Ce week-end et Mon
  calendrier n'avaient aucun moyen, depuis l'app, de forcer un nouveau téléchargement après
  un problème réseau ou une donnée visiblement fausse (ex. le bug fuseau horaire du P0-1) —
  seule option : supprimer le cache disque à la main. Chaque page expose désormais un bouton
  de rafraîchissement (icône, en haut à droite de l'en-tête) qui relance le fetch avec
  `refresh=True`, exactement l'équivalent du flag CLI `--refresh`. Le paramètre `refresh`
  (défaut `False`, comportement inchangé) est ajouté à `controller.get_calendar_year_events`,
  `get_upcoming_weekend`, `get_dashboard_data` et à leur pipeline partagé
  `_fetch_weekend_entries`, jusqu'au constructeur de chaque `Source`. Le clic affiche
  immédiatement l'état de chargement déjà existant (même motif que le changement de saison)
  avant de re-rendre la page une fois le fetch terminé.
- **Diffusion PyPI préparée, non déclenchée (P0-9).** Canal retenu (arbitrage CTO) : PyPI,
  en plus des binaires GitHub Releases déjà couverts par `docs/RELEASE.md`. Le workflow
  `.github/workflows/publish.yml` (déclenché par tag `v*.*.*`, OIDC trusted publishing)
  existait déjà mais n'avait jamais été documenté ni vérifié. Vérifié sans rien publier :
  nom `motorsport-calendar` disponible sur PyPI (404 confirmé), `twine check` PASSED sur
  le sdist et le wheel. Reste explicitement hors de ce commit, nécessitant un geste
  humain délibéré : enregistrer le trusted publisher côté pypi.org, puis pousser le
  premier tag — `docs/RELEASE.md` §6.1 documente désormais ces deux étapes, et alerte
  explicitement que le simple push du tag (déjà décrit à l'étape 7 du checklist) déclenche
  aussi, silencieusement jusqu'ici, la publication PyPI — pas seulement la Release GitHub.

### Sprint RC-01 — Validation Windows

#### Fixed

- **Le build Windows (`flet build windows motorsport_calendar/gui
  --module-name app`) est désormais vérifié pour de vrai sur une
  machine Windows 11** — jamais exécuté sur Windows auparavant (le
  correctif du Sprint 59 n'avait été validé que sur Linux). Deux
  blocages machine/toolchain rencontrés et corrigés, aucun des deux
  causé par le code du projet :
  - Le rendu console `rich` de `flet_cli` plantait immédiatement
    (`UnicodeEncodeError`) sur un terminal en page de code non-UTF-8 —
    corrigé en forçant `PYTHONUTF8=1` avant le build.
  - Le `cmake.exe` 32 bits fourni avec Visual Studio Build Tools,
    redirigé par WOW64, ne pouvait jamais trouver
    `vcruntime140_1.dll` (DLL strictement x64, sans équivalent 32
    bits) — corrigé en dupliquant ce fichier dans `SysWOW64`.
  - Deux tests (`test_config_service.py`, `test_utils_paths.py`)
    corrigés : ils reposaient sur des suppositions Linux jamais
    vérifiées sous Windows (le code applicatif, lui, était déjà
    correct).
- Binaire Windows lancé et **contrôlé visuellement pour de vrai** — une
  première pour ce projet. Les 8 pages de l'app desktop parcourues avec
  captures d'écran réelles, aucun crash, aucun widget cassé.

#### Notes

- Correctif uniquement packaging/tests — aucune nouvelle fonctionnalité,
  aucun refactoring non indispensable (phase Release Candidate : gel
  fonctionnel).
- Un bug cosmétique pré-existant trouvé pendant le contrôle visuel : le
  dropdown "Année par défaut" (Préférences) tronque son texte — non
  bloquant, ajouté à `docs/TODO.md`.
- 0 régression — 2041 → 2042 tests (le test auparavant marqué
  "Windows-only skip" tourne désormais pour de vrai et passe). Ruff : 0
  erreur. Mypy : dette inchangée (41/176, déjà documentée).
- Détail complet : `docs/JOURNAL.md`, session Sprint RC-01 ;
  `docs/PACKAGING.md` §8.

---

### Sprint 59 — Correction du packaging Flet

#### Fixed

- **Le build Linux (`flet build linux motorsport_calendar/gui
  --module-name app`) produit désormais un exécutable qui démarre
  réellement** — corrige le `ModuleNotFoundError: No module named
  'motorsport_calendar'` identifié au Sprint 58. Deux problèmes
  distincts, tous deux nécessaires à corriger (le premier seul, testé
  en conditions réelles, s'est révélé insuffisant) :
  - Dépendances réelles manquantes du build (pydantic, icalendar,
    typer, rich, tzdata, pyyaml, beautifulsoup4, lxml).
  - Le paquet `motorsport_calendar` lui-même jamais inclus dans une
    structure importable (`flet build` aplatit le contenu du dossier
    ciblé, sans jamais l'englober dans son propre paquet).
  - **Nouveau `motorsport_calendar/gui/pyproject.toml`** — manifeste
    dédié à la construction Flet uniquement (jamais lu par pip/
    hatchling pour l'installation normale du projet), utilisant le
    mécanisme officiel `tool.flet.dev_packages` pour installer le
    projet lui-même comme dépendance locale — une seule source de
    vérité pour les 9 dépendances réelles (jamais dupliquées).
  - Corrige au passage l'identité générique de l'application (nom
    d'exécutable/ID d'application/titre de fenêtre : `gui`/
    `com.flet.gui` → `motorsport-calendar`/`com.flet.motorsport-
    calendar`).
  - **Vérifié pour de vrai** : rebuild complet exécuté, binaire lancé
    deux fois, aucune trace d'erreur — pas seulement une compilation
    réussie.

#### Notes

- Correctif uniquement packaging/release — **aucune modification
  métier**, la `pyproject.toml` racine et les points d'entrée de
  développement existants (`motocal`/`motocal-gui`, `pip install
  -e .[gui]`) restent intacts et vérifiés inchangés.
- Point cosmétique restant, non bloquant : la version embarquée dans le
  build affiche encore `1.0.0` au lieu de `0.2.0` — non causé à la
  racine, documenté pour une future investigation ciblée.
- 0 régression — 2033 → 2041 tests (8 nouveaux, garde-fou contre toute
  divergence future entre le manifeste de build et le manifeste racine).
- Détail complet : `docs/JOURNAL.md`, session Sprint 59 ;
  `docs/PACKAGING.md` §7 pour l'analyse technique complète.

---

### Sprint 58 — Validation Packaging Beta

#### Added

- **`docs/RELEASE.md`** (nouveau) — procédure de release pas-à-pas :
  générer le build Linux, générer le build Windows, assembler le dossier
  `Release/` local, publier une Release GitHub (`gh release create`).
- **Dossier `Release/` ajouté à `.gitignore`** — zone de préparation
  locale régénérée à chaque release, jamais versionnée (même logique que
  `build/`).

#### Documentation

- **`docs/PACKAGING.md` — audit complet du build Linux réellement compilé
  et exécuté pour la première fois** (Sprint 49 n'avait jamais dépassé
  l'étape de compilation, l'outillage système manquait alors). Résultat :
  - **Constat critique** : le binaire produit par la commande documentée
    plante au démarrage (`ModuleNotFoundError: No module named
    'motorsport_calendar'`) — cause racine identifiée avec précision en
    lisant le code source de `flet_cli` (aucune `pyproject.toml` au
    chemin `python_app_path` pointé, donc ni les dépendances du projet
    ni le paquet `motorsport_calendar` lui-même ne sont embarqués).
  - Cartographie complète du dossier produit (exécutable, `lib/`,
    `python3.12/`, `site-packages/`, `data/`) — taille totale 112 Mo.
  - Confirmation que Python et les bibliothèques système (GTK3, etc.)
    sont bien embarqués/déjà présents sur un Ubuntu Desktop standard —
    l'autonomie de l'exécutable est réelle une fois le blocage ci-dessus
    corrigé.
  - Constat que le nom de fenêtre natif, l'ID d'application et la
    version embarquée valent encore les valeurs par défaut génériques de
    Flet (`"gui"`/`com.flet.gui`/`1.0.0`) au lieu de celles du projet.
  - Confirmation que les chemins de préférences/cache/configuration
    (`utils/paths.py`, Sprint 49) restent corrects et indépendants des
    variables de stockage propres à Flet.
  - Correction d'une affirmation prématurée de Sprint 49 ("vérifié...
    correct de bout en bout") — jamais réellement vérifié à l'époque,
    le build n'avait alors jamais tourné jusqu'au bout.

#### Notes

- Audit et documentation uniquement — **aucune modification métier**,
  aucune évolution des services, suite de tests intacte (2033 passants +
  1 `skip` spécifique Windows, inchangé).
- Aucun correctif appliqué au blocage identifié (hors périmètre de ce
  sprint, explicitement un audit) — voir `docs/PACKAGING.md` §6.3 pour
  les deux pistes de correction candidates, tracées dans `docs/TODO.md`.
- Détail complet : `docs/JOURNAL.md`, session Sprint 58.

---

### Sprint 57 — Préparation Beta : Nettoyage & Positionnement

#### Added

- **Nouvelle page "Soutenir le projet"** (`gui/views/support.py`) — le
  point de contact entre Motorsport Calendar et sa communauté, purement
  informative (aucun système de vote local, aucun système de dons
  local, aucun formulaire local) :
  - **Soutenir Motorsport Calendar** — emplacements PayPal/GitHub
    Sponsors, préparés mais pas encore reliés à une vraie URL
    (`ComingSoonRow`).
  - **Voter pour les prochaines fonctionnalités** — présentation des
    grandes pistes envisagées (Classements, Diffusion TV, Mobile,
    Motorsport API, Résultats, Pilotes, Équipes, Widgets).
  - **Suggestions** — bouton ouvrant GitHub Discussions.
  - **Signaler un problème** — bouton "Signaler un bug" ouvrant GitHub
    Issues.
  - Tous les liens sont de simples constantes de module, facilement
    configurables.
- **`gui/url_opener.py`** (nouveau) — le seul endroit qui sait ouvrir
  une URL dans le navigateur système (avec repli `subprocess` Windows).
  Remplace 2 implémentations indépendantes déjà existantes
  (`views/about.py`, `main_view.py::_make_release_opener`) — nettoyage
  explicite du sprint, aucune duplication restante.
- **`gui/components/layout/coming_soon_row.py`** (nouveau) —
  `ComingSoonRow`, promu depuis `views/preferences.py`'s `_pref_row`
  privé une fois "Soutenir le projet" ayant besoin de la même forme
  pour ses emplacements PayPal/GitHub Sponsors.

#### Changed

- **"À propos" devient une véritable présentation du projet** — conserve
  la version réelle/licence/lien GitHub déjà existants (Sprints 26-54),
  et ajoute : objectifs du projet, philosophie Open Source, technologies
  utilisées (Python, Flet, Typer, Pydantic, httpx, icalendar).
- **IMSA et WorldSBK masqués de l'interface utilisateur** —
  `controller.list_championships()` ne les propose plus dans les
  sélecteurs de championnat (Mon calendrier, Mes favoris, Recherche)
  tant qu'ils ne disposent pas d'une source fiable. **Aucune suppression
  de code** : les deux restent entièrement enregistrés dans
  `ProviderRegistry`, `cli.py generate-imsa`/`generate-worldsbk`
  inchangés.

#### Notes

- Aucun nouveau provider, aucune évolution métier, aucune évolution des
  services, aucun système de vote/dons local.
- 0 régression — 2000 → 2034 tests (34 nouveaux, dont 1 spécifique à
  Windows, `skip`é sur cet environnement Linux). Ruff : 0 erreur
  (inchangé). mypy `motorsport_calendar/` : 39 → 41 (+2, 2 nouveaux
  boutons `on_click` dans `support.py`, même famille de dette Flet
  stub-version déjà acceptée). mypy `tests/` : 157 → 176 (+19, même
  famille de bruit résiduel déjà documentée — tests utilisant un double
  factice au lieu du vrai type Flet, ou accédant à `.content`/`.icon`
  sur un `ft.Control` non affiné — aucune vraie erreur de logique
  derrière).
- Détail complet, y compris la réponse argumentée à la question de
  clôture du brief : `docs/JOURNAL.md`, session Sprint 57.

---

### Sprint 56 — Notifications natives

#### Added

- **`gui/system_notifications.py`** (nouveau) — la seule couche
  dépendante du système d'exploitation de toute l'application.
  `NotificationService` (Sprint 46) reste totalement indépendant de
  Flet et ne connaît toujours ni Windows, ni Linux, ni macOS ; ce
  module décide uniquement *comment* (ou si) une `Notification` déjà
  calculée devient une vraie notification système.
  - `SystemNotifier` (Protocol) — l'interface qu'une future
    implémentation devra remplir.
  - `NullSystemNotifier` — la seule implémentation livrée ce sprint,
    toujours indisponible : **fait vérifié, pas une hypothèse** —
    Flet 0.85.3 ne fournit aucun service de notification système sur
    aucune plateforme (les 20 services officiels listés dans
    `flet.controls.services.*` ne comportent ni "notification", ni
    "toast", ni "tray" ; `ft.Window` n'expose aucune icône de zone de
    notification ; le changelog de Flet ne mentionne jamais les
    notifications système, seulement les notifications de scroll, un
    concept sans rapport). Conformément au brief, aucune bibliothèque
    tierce n'a été ajoutée pour combler ce manque — "ne pas bricoler".
  - `notify_all(notifications)` — point d'entrée unique, ne lève
    jamais, dégrade toujours silencieusement (journalisé via
    `utils.get_logger`, jamais d'erreur technique affichée).
- **`gui/controller.py::prepare_notifications()`** (nouveau) — "au
  démarrage, si les notifications sont activées, préparer les
  prochaines notifications" (brief, verbatim). Réutilise exclusivement
  la préférence `notifications_enabled` déjà existante (aucun nouveau
  réglage) ; calcule via `NotificationService.compute_notifications()`
  inchangé, puis délègue l'affichage à `notify_all()`.
- **`gui/main_view.py`** — `_prepare_system_notifications()` appelée
  une fois au démarrage et à chaque rafraîchissement de `year_events`
  (changement d'année), même déclencheur que les index recherche/
  circuits.

#### Notes

- Aucun nouveau provider, aucune évolution métier, aucune nouvelle
  dépendance, aucun nouveau réglage de préférence.
- `NotificationService` n'a subi aucune modification.
- 0 régression — 1978 → 2000 tests (22 nouveaux). Ruff : 0 erreur
  (inchangé). mypy `motorsport_calendar/` : 39 → 39 (inchangé). mypy
  `tests/` : 157 → 157 (inchangé).
- Détail complet, y compris la réponse argumentée aux deux questions du
  brief (disponibilité réelle des notifications natives, stratégie
  retenue pour la Beta) : `docs/JOURNAL.md`, session Sprint 56.

---

### Sprint 55 — Recherche interactive

#### Added

- **Les résultats de "Recherche" deviennent cliquables** — selon leur
  nature, réutilisant intégralement les vues déjà existantes, sans
  aucune duplication :
  - **Championnat** → navigue vers "Mon calendrier" (`_navigate_to`,
    Sprint 53), la destination existante la plus proche en l'absence de
    page dédiée par championnat ; ne modifie jamais la sélection de
    génération de l'utilisateur.
  - **Événement** → ouvre la "fiche événement" existante (Sprint 42),
    via un nouveau helper partagé `_open_event_details(championship_id,
    event_uid)` extrait de la logique déjà utilisée par l'explorateur de
    saison "Mon calendrier" — une seule implémentation de cette
    résolution, deux appelants.
  - **Circuit** → ouvre la "fiche Circuit" existante (Sprint 47), via un
    nouveau helper partagé `_open_circuit_details(circuit_key)` extrait
    de la logique déjà utilisée par le lien circuit de la fiche
    événement — même principe.
- **`gui/search_service.py::SearchResultItem`** — 3 nouveaux champs
  d'identité (`championship_id`/`event_uid`/`circuit_key`), jamais
  affichés, portés à travers l'index jusqu'à la vue (même convention
  que `SeasonEventRow` depuis le Sprint 42) pour que main_view.py puisse
  résoudre quelle vue existante ouvrir.
- **`gui/views/search.py::build_search_view()`** — 3 nouveaux
  callbacks optionnels (`on_championship_click`/`on_event_click`/
  `on_circuit_click`), chacun appelé avec le `SearchResultItem` cliqué ;
  la vue ne résout toujours rien elle-même, elle relaie uniquement.

#### Notes

- Aucun nouveau service, aucun nouveau provider, aucune nouvelle
  logique métier — uniquement `SearchService`, `EventDetails`,
  `CircuitService` et la navigation existante réutilisés.
- Point identifié en Sprint 54 (piste `-18`) et corrigé ce sprint.
- 0 régression — 1968 → 1978 tests (10 nouveaux). Ruff : 0 erreur
  (inchangé). mypy `motorsport_calendar/` : 39 → 39 (inchangé). mypy
  `tests/` : 157 → 157 (inchangé).
- Détail complet : `docs/JOURNAL.md`, session Sprint 55.

---

### Sprint 54 — Préparation Beta (Recette UX)

#### Changed

- **Cohérence des icônes** — trois incohérences visuelles corrigées, sans
  toucher au Design System ni à la logique :
  - "Mes favoris" affichait `STAR_BORDER` dans son en-tête, un troisième
    glyphe "étoile" différent des deux déjà utilisés pour cette page dans
    le rail de navigation (`STAR_OUTLINE` non sélectionné, `STAR`
    sélectionné) — aligné sur `STAR`, la convention déjà suivie par
    "Ce week-end"/"Mon calendrier"/"Recherche"/"Préférences".
  - Le Dashboard affichait l'icône `SPACE_DASHBOARD_OUTLINED` (contour)
    dans son en-tête au lieu de la variante pleine `SPACE_DASHBOARD` —
    même correction de cohérence.
  - La boîte de dialogue de succès ("Calendrier créé avec succès")
    affichait un emoji "✅" codé en dur — remplacé par un `ft.Icon`
    thématisé (`CHECK_CIRCLE`, couleur `Colors.SUCCESS`), cohérent avec
    le reste de l'application qui n'utilise jamais d'emoji dans son
    interface, uniquement des icônes Material.
- **Cohérence des espacements** — 8 occurrences d'un espacement codé en
  dur (`spacing=2` ×6, `spacing=4` ×2) remplacées par le token
  `theme.Spacing.XXS` du Design System, dans `views/preferences.py`,
  `views/about.py`, `views/search.py`, `views/calendar.py` (×3) et
  `main_view.py` (×2, boîtes de dialogue succès/mise à jour).
- **Cohérence des messages vides** — ponctuation des titres `EmptyState`
  standardisée : `weekend_empty_title`/`dashboard_weekend_championships_
  empty`/`search_no_results` perdent leur point final pour rejoindre la
  majorité déjà sans point (`dashboard_next_race_empty`/`calendar_season_
  explorer_empty`/`calendar_summary_empty_selection`) — seules les
  phrases instructives avec un verbe (`weekend_next_hint`, `search_empty_
  query`) gardent la leur.
- **Cohérence des textes — "À propos" affiche enfin un vrai numéro de
  version** — remplace le texte statique "Version Alpha" (sans numéro)
  par `motorsport_calendar.__version__` (ex. "Version 0.2.0 — Alpha"),
  la même valeur déjà affichée par la section "État" du Dashboard
  (Sprint 53) ; c'était le seul endroit de l'application qui parlait "de
  la version" sans jamais dire laquelle.
- **Doublons** — `nav_home`/`nav_calendar`, deux chaînes "gardées pour
  compatibilité" mais jamais référencées nulle part depuis l'introduction
  de `nav_dashboard`/`nav_my_calendar`, supprimées.

#### Notes

- Aucune nouvelle fonctionnalité, aucun nouveau provider, aucune
  évolution des services/providers/modèles métier — recette UX pure,
  conforme au brief.
- 0 régression — 1961 → 1968 tests (7 nouveaux, tous protègent une des
  corrections ci-dessus). Ruff : 0 erreur (inchangé). mypy
  `motorsport_calendar/` : 39 → 39 (inchangé). mypy `tests/` : 157 → 157
  (inchangé).
- Détail complet, y compris les points identifiés mais volontairement
  non corrigés (résultats de recherche non cliquables — nécessiterait une
  évolution de `SearchResults`, hors périmètre "aucune évolution des
  services") : `docs/JOURNAL.md`, session Sprint 54.

---

### Sprint 53 — Nouveautés & Centre d'accueil

#### Added

- **Dashboard transformé en véritable page d'accueil** — 3 nouvelles
  sections ajoutées à la page existante (stats saison, "Ce week-end",
  "Prochain départ" inchangés), aucune logique métier dans
  `gui/views/dashboard.py` : la vue ne fait que disposer des données déjà
  résolues via le Design/Layout System existant
  (`PageContainer`/`PageHeader`/`Section`/`SectionHeader`/`theme.card`) —
  aucune évolution graphique.
  - **"Nouveautés"** : réutilise `UpdateService` (Sprint 51) tel quel.
    Aucune mise à jour → section entièrement omise (pas même un
    en-tête, contrairement aux autres sections qui affichent toujours au
    moins un état vide) ; nouvelle version disponible → carte discrète
    (nouvelle version, résumé, bouton "Voir la version"). Le bouton
    réutilise exactement le handler du Sprint 51 (extrait en fabrique de
    fermeture `_make_release_opener` dans `main_view.py`, utilisée à la
    fois par la boîte de dialogue de démarrage et cette carte — aucune
    logique dupliquée).
  - **"Accès rapides"** : 4 cartes de navigation (Ce week-end, Mon
    calendrier, Recherche, Favoris) — navigation pure via une
    indirection par clé string (`on_navigate: Callable[[str], None]`),
    `main_view.py` seul connaît la correspondance clé → index de
    `NavigationRail`.
  - **"État de Motorsport Calendar"** : version actuelle, championnats
    actifs, fournisseurs réellement fonctionnels, favoris — toutes
    calculées par les services existants (`ProviderRegistry`,
    `FavoritesService`, `motorsport_calendar.__version__`), jamais codées
    en dur.
- **`gui/dashboard.py::DashboardData`/`build_dashboard_data()`** — 5
  nouveaux champs passthrough (`active_championships`, `favorite_count`,
  `current_version`, `update`) résolus par l'appelant, plus un champ
  réellement calculé ici (`functional_providers` — championnats distincts
  ayant produit au moins une entrée parmi celles déjà récupérées ; un
  provider qui échoue systématiquement — stubs IMSA/WorldSBK — n'y
  contribue jamais, l'écart honnête avec `active_championships` étant
  précisément l'intérêt d'afficher les deux).
- **`gui/controller.py::get_dashboard_data()`** — récupère désormais les
  entrées week-end et la vérification de mise à jour en concurrence
  (`asyncio.gather`), résout `active_championships` via
  `registry.enabled(config.providers)`.

#### Notes

- Aucun nouveau service, aucun nouveau provider, aucune nouvelle
  dépendance, aucune évolution des modèles métier.
- Aucune logique métier dans la vue — uniquement `Dashboard`,
  `UpdateService`, `FavoritesService`, `ProviderRegistry` réutilisés.
- 0 régression — 1932 → 1961 tests.
- Détail complet : `docs/JOURNAL.md`, session Sprint 53.

---

### Sprint 52 — Préférences avancées

#### Added

- **Page Préférences transformée en véritable centre de configuration** —
  4 sections : Notifications, Mises à jour, Calendrier, Application. Plus
  aucune logique métier dans `gui/views/preferences.py` : main_view.py
  construit chaque contrôle Flet (`Switch`/`Dropdown`) déjà câblé à son
  gestionnaire, la vue ne fait que les disposer via le Design/Layout
  System existant (`PageContainer`/`PageHeader`/`Section`/
  `SectionHeader`/`CardList`) — aucune évolution graphique.
  - **Notifications** (réutilise `NotificationService`, Sprint 46) :
    activées/désactivées, favoris uniquement (avec indication du nombre
    de favoris via `FavoritesService`), délai par défaut (15 min → 24 h).
  - **Mises à jour** (réutilise la préférence `update_check_enabled`,
    Sprint 51) : activer/désactiver la vérification au démarrage — la
    préférence existait déjà, elle a enfin une UI pour la piloter.
  - **Calendrier** : année par défaut ("Année en cours" — sentinelle qui
    ne devient jamais obsolète — ou une année fixe) et rappel avant
    export (VALARM 0/15/30/60 min, remplace `config.ics.alarm_minutes`
    pour les exports GUI uniquement — la CLI continue de ne lire que
    `config.yaml`).
  - **Application** (préparé, non implémenté — brief explicite) : Thème,
    Langue, Format horaire — lignes "Disponible prochainement" identiques
    au patron déjà existant, adossées à un `PreferencesModel` repensé
    (voir Changed).
- **`gui/preferences.py`** — deux nouvelles clés : `default_year` (défaut
  `"current"`) et `ics_alarm_minutes` (défaut `30`, identique à
  `config.ics.alarm_minutes` pour un comportement inchangé tant que
  l'utilisateur ne touche pas la page).
- **`gui/models.py::resolve_default_year()`** (nouveau, pure/sans Flet) —
  décode la préférence `default_year` en année réelle ; ne plante jamais
  sur une valeur corrompue (repli sur l'année courante).

#### Changed

- **`gui/models.py::PreferencesModel`** repensé — les 6 champs
  décoratifs hérités (Sprints 23-31, jamais reliés à rien de réel :
  `timezone`/`first_day_of_week`/`favorite_championships`/
  `preferred_calendar`/`bapps_sync_enabled`) retirés au profit des 3
  seuls champs demandés par le brief Sprint 52 pour la section
  "Application" (`theme`/`language`/`time_format`) — un typage prêt à
  recevoir de vraies valeurs le jour où l'un d'eux devient réel, sans
  qu'un futur sprint n'ait à en inventer la forme.
- **`gui/controller.py::generate_calendar()`** — l'export ICS lit
  désormais `ics_alarm_minutes` depuis les préférences (repli sur
  `config.ics.alarm_minutes` si jamais enregistrée) au lieu de lire
  uniquement `config.yaml`.

#### Notes

- Aucun nouveau provider, aucune nouvelle page, aucune évolution
  graphique (Design System/Layout System/Components strictement
  respectés).
- 0 régression — 1923 → 1932 tests.
- Détail complet : `docs/JOURNAL.md`, session Sprint 52.

---

### Sprint 51 — Vérification des mises à jour

#### Added

- **`gui/update_service.py`** (nouveau) — `UpdateService`, totalement
  indépendant de Flet (aucun `import flet`, vérifié par un test dédié) :
  récupère un manifeste JSON distant (URL entièrement fournie par
  l'appelant, aucune plateforme codée en dur — pas de couplage GitHub),
  compare les versions numériquement (`is_newer()` — jamais lexicographique,
  gère correctement `0.4.9 < 0.4.10 < 0.5.0 < 1.0.0`), et retourne un
  `UpdateCheckResult` prêt à afficher. Ne télécharge, n'installe et ne
  redémarre jamais rien — le seul effet de bord est une requête HTTP GET.
  Aucune erreur (réseau absent, timeout, JSON invalide, manifeste
  incomplet, version illisible) n'est jamais levée — toujours capturée et
  renvoyée via `UpdateCheckResult.error`.
- **`config/models.py::UpdateConfig`** (nouveau, `config.update.manifest_url`)
  — URL du manifeste configurable via `config.yaml`, vide par défaut (la
  vérification est un no-op silencieux tant qu'aucune URL n'est renseignée).
- **`gui/controller.py::check_for_update()`** (nouveau) — résout la
  version courante (`motorsport_calendar.__version__`) et l'URL du
  manifeste (`ConfigService().update.manifest_url`), respecte la
  préférence `update_check_enabled` (voir ci-dessous), puis délègue à
  `UpdateService`. Toute la logique métier reste dans `update_service.py` ;
  ce wrapper ne fait que la câbler à la config/aux préférences, comme
  `generate_calendar`/`get_dashboard_data`.
- **`gui/preferences.py::update_check_enabled`** (nouvelle clé, défaut
  `True`) — permet de désactiver la vérification (opt-out). Fondations
  seulement : aucune UI de préférences ne l'expose encore ce sprint (même
  statut "fondations, pas d'UI" que `notifications_*` au Sprint 46).
- **Boîte de dialogue "nouvelle version disponible"** (`main_view.py`) —
  affichée une fois par lancement, si une mise à jour est disponible :
  version actuelle, nouvelle version, résumé, bouton "Voir la version"
  (ouvre l'URL officielle via `url_launcher`, même patron que le lien
  GitHub d'À propos). Aucune mise à jour automatique, aucune installation,
  aucun redémarrage — uniquement une ouverture de navigateur sur clic
  explicite.
- 58 nouveaux tests (`test_update_service.py` complet + ajouts dans
  `test_config_service.py`, `test_gui_preferences.py`,
  `test_gui_controller.py`) couvrant : même version, version plus récente
  (patch/mineure/majeure), version courante en avance sur le manifeste,
  manifeste invalide/incomplet, absence de réseau, timeout, erreurs HTTP,
  JSON malformé, préférence désactivée, aucune URL configurée.

#### Notes

- Aucun provider, aucune évolution de providers existants.
- Aucun changement de comportement pour les fonctionnalités existantes —
  0 régression sur les 1865 tests précédents.
- Détail complet : `docs/JOURNAL.md`, session Sprint 51.

---

### Sprint 50 — Audit & Consolidation

Sprint non-fonctionnel : aucune fonctionnalité, aucun provider, aucune
page, aucun changement de comportement utilisateur. Audit complet du
projet + réduction de dette technique. Rapport complet :
`docs/AUDIT.md`.

#### Fixed

- **Bug réel dans `core/service.py::CalendarService.export_championship`**
  (jamais appelée par aucun code réel, détecté par mypy lors du scan
  complet de ce sprint) — passait un `Championship` à `Exporter.export()`
  qui attend une liste d'`Event` ; corrigée pour récupérer réellement les
  événements via `provider.fetch_events` avant export. Zéro impact
  utilisateur (classe jamais exercée par le CLI ni la GUI).

#### Changed

- **Dette Ruff : 149 → 0 erreur** — imports non triés/inutilisés, `noqa`
  obsolètes, `datetime.timezone.utc` → `datetime.UTC`, `lambda` assignées
  converties en `def`, `raise ... from exc` sur 5 chaînes d'exception CLI,
  `pytest.raises(Exception)` trop large narrowé en `ValidationError` sur 4
  tests de modèles frozen, `Category(str, Enum)` aligné sur `enum.StrEnum`
  (convention déjà utilisée par tous les autres enums du projet).
- **Dette mypy `motorsport_calendar/` : 87 → 23 erreurs** — annotations
  `dict`/`list` nues remplacées par des génériques précis
  (`dict[str, Any]`, etc.) dans `cache/http_cache.py`, `cli.py`,
  `config/`, `core/datasource/`, providers Formula 1/2/support-series/
  MotoGP, `gui/preferences.py`, `gui/strings.py`, `gui/controller.py`.
  Nouvelles dépendances dev `types-PyYAML`/`types-icalendar` (stubs
  manquants, plutôt que des suppressions locales). Les 23 erreurs
  restantes sont une seule famille documentée (décalage stubs Flet
  0.80/runtime 0.85.3, `main_view.py`/`championship_selector.py`/
  `about.py`) — voir `docs/AUDIT.md` §4.
- **Dette mypy `tests/` : 402 → 157 erreurs** — `mypy.ini` relâché pour
  les tests uniquement (`disallow_untyped_calls`/`check_untyped_defs`/
  `warn_return_any` désactivés, pratique standard pour du code
  `unittest.mock`-intensif ; `motorsport_calendar/` reste en
  `strict = True` intégral) + suppression de 24 `# type: ignore`
  devenus inutiles + factorisation de `test_aco_sports_event_base.py`
  (14 occurrences d'un même pattern non-narrowed → 1 helper).
- **`mypy.ini`** — exclut désormais `motorsport_calendar/gui/build/`
  (artefacts du build Flet Sprint 49, jamais censés être scannés).
- **Duplication de tests réduite** — un helper `_load()` identique
  copié-collé dans 8 fichiers de test (`test_aco_sports_event_base.py`,
  `test_sro_timetable_base.py`, `test_cli_generate_{elms,mlmc,igtc,
  gtwc_america,gtwc_asia,gtwc_europe}.py`) factorisé en
  `tests/conftest.py::load_real_fixture()`.
- **21 docstrings ajoutées** sur des fonctions/propriétés publiques qui
  n'en avaient pas encore (`config/service.py`, `gui/favorites_service.py`,
  `gui/notification_service.py`, `gui/search_service.py`,
  `gui/theme.py::Spacing/Radius/IconSize/FontSize`) — après triage
  distinguant les vrais manques des redéfinitions triviales d'une méthode
  déjà documentée sur son ABC (76 cas, volontairement non dupliqués,
  convention Python standard).

#### Performance

- **Fetch concurrent des providers** dans `cli.py::generate` et
  `gui/controller.py::generate_calendar` — chaque championnat interroge
  une API distante indépendante ; remplacé un `for`/`await` séquentiel par
  `asyncio.gather`, mesuré ~10x plus rapide sur un banc synthétique à
  latence égale. Comportement strictement identique (ordre des résultats
  et du fichier ICS final préservé par `asyncio.gather`) — deux nouveaux
  tests de non-régression (`TestGenerateConcurrency`,
  `TestGenerateCalendarConcurrency`) vérifiés pour échouer contre
  l'ancienne implémentation séquentielle avant validation contre la
  nouvelle.

#### Added

- **`docs/AUDIT.md`** (nouveau) — rapport d'audit complet : état général,
  points forts/faibles, dette restante documentée, 10 fichiers les plus
  volumineux, services les plus critiques, optimisations
  réalisées/reportées, recommandations pour les prochains sprints.

#### Notes

- **1863 → 1865 tests** (+2, tests de non-régression performance),
  couverture inchangée (~97 %), 0 régression.
- Détail complet : `docs/JOURNAL.md`, session Sprint 50. `docs/AUDIT.md`
  pour le rapport d'audit complet.

---

### Sprint 49 — Packaging Alpha

#### Added

- **`motorsport_calendar/utils/paths.py`** (nouveau) — `user_config_dir()`/`user_cache_dir()`,
  répertoires utilisateur multi-plateforme (Linux : XDG Base Directory ; Windows :
  `%APPDATA%`/`%LOCALAPPDATA%`), réutilisés par les préférences GUI, `HttpCache` et
  `ConfigService`.
- **Icône application officielle intégrée** — Brand Set v1.0
  (`gui/assets/icon.png`, `icon_windows.ico`), fenêtre/barre des tâches (`page.window.icon`)
  et build Windows (convention Flet `icon_windows.ico`). Favicon et logos SVG
  (`mc-icon.svg`, `logo-horizontal.svg`, `logo-vertical.svg`) intégrés au build
  (`assets_dir`), pas encore consommés par les vues (aucune évolution du Design System
  ce sprint, conforme à la consigne).
- **`docs/PACKAGING.md`** (nouveau) — procédure officielle de build Flet (Linux validé en
  direct, Windows documenté précisément mais non exécuté faute de machine Windows),
  structure générée, assets embarqués, limitations.

#### Fixed

- **Cache HTTP jamais dans le dépôt Git** — `HttpCache`'s repli implicite (`Path(".cache")`,
  relatif au répertoire courant) devient le répertoire cache utilisateur
  (`utils/paths.py`) ; `ConfigService`/`CacheConfig` (déjà corrects en usage normal via
  `config.yaml`) alignés sur la même convention multi-plateforme.
- **Préférences GUI multi-plateforme** — `gui/preferences.py` utilisait un chemin
  Linux/macOS codé en dur (`~/.config/motorsport-calendar/`) ; utilise désormais
  `utils/paths.py`, fonctionnel sous Windows (`%APPDATA%`) sans changement de
  comportement sous Linux.
- **`gui/app.py::assets_dir`** — résolu depuis `Path(__file__).parent`, jamais relatif au
  répertoire courant au lancement (Flet résout un `assets_dir` relatif à la CWD, pas au
  fichier appelant — un exécutable packagé lancé depuis un autre répertoire aurait
  silencieusement perdu ses assets).
- Export ICS (`exporters/ics.py`) confirmé déjà propre (chemin entièrement fourni par
  l'appelant, aucune dépendance au dépôt) — non modifié, validé par de nouveaux tests
  explicites.

#### Notes

- Build Linux validé en direct : `flet build linux motorsport_calendar/gui --module-name
  app` résout correctement l'entrée/les assets, installe le SDK Flutter et atteint
  l'étape de compilation native — voir `docs/JOURNAL.md` pour l'issue exacte de la
  session.
- 26 nouveaux tests, zéro régression, aucune fonctionnalité utilisateur ajoutée, aucun
  provider ni service métier modifié (conforme à la consigne du sprint).

Détail complet : `docs/JOURNAL.md`, session Sprint 49. ADR-040 dans `docs/DECISIONS.md`.

---

### Sprint 48 — Finalisation des providers

#### Added

- **`OfficialWecSource` devient une implémentation réelle** — FIA WEC rejoint ELMS/MLMC :
  fiawec.com utilise exactement le même CMS/JSON-LD schema.org (confirmé en direct),
  désormais implémenté en sous-classant `AcoSportsEventSource` plutôt qu'un nouveau
  scraper. Saison 2026 complète validée en direct : 8 événements, 50 sessions, UID
  uniques, fuseaux horaires corrects sur les 8 circuits. Intégration confirmée dans le
  Dashboard, Ce week-end, Recherche et l'agrégateur `generate`/`generate-wec`.
- **`aco_series/sports_event_base.py`** (partagé ELMS/MLMC/WEC) étendu de façon purement
  additive : nouveaux types de session "Free Practice 4", "Hyperpole", "Warm-up"
  (spécifiques à WEC, jamais présents chez ELMS/MLMC) ; exclusion du prologue
  pré-saison ; nouveau point d'extension `_race_session_end()` (la durée de course WEC
  ne peut pas être déduite de son `endDate`, contrairement à ELMS/MLMC — un vrai bug
  détecté en direct sur les 24 Heures du Mans, qui aurait silencieusement produit une
  course de 8h au lieu de 24h) ; nouveau point d'extension `_race_url_belongs_to_season()`
  (la page saison de fiawec.com mélange l'année demandée et la suivante, contrairement à
  ELMS/MLMC).
- **`wec/circuit_data.py`** (nouveau) — pays résolu dynamiquement depuis l'adresse
  JSON-LD de fiawec.com (code ISO 3166-1 alpha-3), plutôt qu'une table statique par
  circuit — même principe déjà appliqué à GT World Challenge (Sprint 37).

#### Investigated (no viable source found — stubs unchanged)

- **IMSA WeatherTech** — ré-investigué : imsa.com bloque désormais jusqu'à son propre
  `robots.txt` (Cloudflare, plus strict qu'au Sprint 36), le portail Al Kamel reste une
  archive de résultats post-course, et le tableau Wikipedia n'a toujours aucune heure de
  session. Aucune source exploitable trouvée.
- **WorldSBK** — ré-investigué : nouveaux hôtes candidats de la famille Pulselive
  découverts (`api.wsbk.pulselive.com`, `wsbk.pulselive.com`) mais aucun n'expose
  d'endpoint événements exploitable sans automatisation navigateur. Aucune source
  exploitable trouvée.

#### Fixed

- 37 nouveaux tests au total, zéro régression — dont l'adaptation de plusieurs tests qui
  s'appuyaient implicitement sur l'échec naturel (`NotImplementedError`) de WEC (CLI
  `generate`/`generate-wec`, contrôleur GUI) : WEC étant désormais une source réelle, ces
  scénarios "un provider échoue" utilisent IMSA (toujours un stub réel) à la place —
  même couverture, même intention, provider différent.

Détail complet : `docs/JOURNAL.md`, session Sprint 48. ADR-039 dans `docs/DECISIONS.md`.

---

### Sprint 47 — Circuit Explorer

#### Added

- **`motorsport_calendar/gui/circuit_service.py`** — nouveau `CircuitService`, une
  véritable base de données des circuits construite uniquement à partir des événements
  déjà chargés (aucun nouveau provider, aucun appel réseau). Chaque circuit possède :
  nom, pays, nombre de championnats, liste des championnats, nombre total d'événements,
  première et dernière saison disponibles. Circuits dédupliqués et fusionnés entre
  providers/championnats grâce à la même normalisation "compacte" que la recherche
  globale (Sprint 45) — le même circuit physique (ex. Spa-Francorchamps, orthographié
  différemment selon 5 championnats) devient une seule entité.
- **Fiche Circuit** — depuis la fiche événement, le nom du circuit devient cliquable et
  ouvre une nouvelle boîte de dialogue affichant nom, pays, championnats, historique
  chronologique des événements et nombre total de courses.
- **`ChampionshipCard`** (composant partagé) gagne un nouveau point d'extension optionnel
  `on_circuit_click` — `None` par défaut partout ailleurs (Ce week-end, Dashboard,
  Favoris) : aucun changement visuel ni comportemental pour ces pages, seule la fiche
  événement l'active.
- **`gui/event_display.py`** — `normalize_key` (promu depuis `search_service.py`,
  Sprint 45) et deux nouvelles fonctions publiques, `circuit_display_name`/
  `resolve_country`, réutilisées par le nouveau `CircuitService` sans dupliquer la
  normalisation déjà établie (ADR-023).
- 35 nouveaux tests, zéro nouveau provider, zéro nouvelle source de données, aucune
  régression (conforme à la consigne du sprint).

Détail complet : `docs/JOURNAL.md`, session Sprint 47. ADR-038 dans `docs/DECISIONS.md`.

---

### Sprint 46 — Moteur de notifications

#### Added

- **`motorsport_calendar/gui/notification_service.py`** — nouveau `NotificationService`,
  fondations d'un moteur de notifications entièrement indépendant de l'interface (aucune
  dépendance Flet) et hors-ligne (aucun appel réseau supplémentaire) : calcule toutes les
  notifications à venir à partir des données déjà chargées (`year_events`, le même dict
  que "Mon calendrier"/"Recherche" utilisent déjà). Aucune notification système envoyée ce
  sprint — uniquement le calcul structuré, réutilisable plus tard par une couche
  spécifique Windows/Linux/macOS sans modification.
- **5 types de notifications** : début du week-end, première session, qualifications,
  sprint, course — calculées par événement à partir de ses sessions déjà en mémoire.
  Début du week-end et première session s'ancrent tous deux sur la session la plus
  précoce de l'événement (le modèle de domaine n'a pas de notion distincte de "début de
  week-end" à ce jour — voir ADR-037).
- **Délais configurables** — `compute_notifications(..., lead_times=...)` accepte
  n'importe quelle combinaison de délais (ex. 24h/12h/1h/15min simultanément), une
  notification étant produite par combinaison session × délai encore à venir
  (`trigger_at >= now`, jamais une notification déjà due).
- **Favoris uniquement** — `compute_notifications(..., favorites_only=..., favorite_ids=...)`
  restreint le calcul aux championnats favoris ; sinon fonctionne sur tous les
  championnats chargés.
- **3 préférences persistées** (sans interface complète, comme demandé) : notifications
  activées, délai par défaut, favoris uniquement — sur le même fichier de préférences
  centralisé que le reste de l'état GUI (`gui/preferences.py`), lecture-fusion-écriture,
  jamais un second fichier.
- 33 nouveaux tests (31 `NotificationService` + 2 préférences), zéro nouveau provider,
  zéro nouvelle source de données, zéro évolution graphique (conforme à la consigne du
  sprint).

Détail complet : `docs/JOURNAL.md`, session Sprint 46. ADR-037 dans `docs/DECISIONS.md`.

---

### Sprint 45 — Recherche globale

#### Added

- **`motorsport_calendar/gui/search_service.py`** — nouveau `SearchService`, recherche
  instantanée et entièrement hors-ligne (aucun appel réseau supplémentaire) sur les
  championnats, événements et circuits déjà chargés en mémoire. Normalisation
  "compacte" (décomposition NFKD + suppression des accents + casefold + ne conserver
  que les caractères alphanumériques) pour satisfaire les exemples du sprint : `spa` /
  `Spa` / `SPA` / `spa francorchamps` retrouvent tous "Spa-Francorchamps" ; `Le Mans` /
  `lemans` retrouvent tous "Michelin Le Mans Cup" et "European Le Mans Series".
  Résultats regroupés par type (Championnats / Événements / Circuits), chacun trié par
  pertinence (correspondance exacte, puis préfixe, puis sous-chaîne) puis
  alphabétiquement.
- **Index réutilisable** — construit une seule fois par changement de données (au
  démarrage, puis reconstruit uniquement quand l'année de "Mon calendrier" change), et
  jamais reparcouru à chaque frappe : `search()` est O(taille de l'index), jamais O(un
  nouveau parcours des providers).
- **Nouvelle page "Recherche"** (`gui/views/search.py`) — nouvelle destination de
  navigation au même titre que Dashboard / Ce week-end / Mon calendrier / Mes favoris /
  Préférences / À propos. Réutilise intégralement le Layout System existant
  (`PageHeader`/`Section`/`SectionHeader`/`CardList`/`EmptyState`) — composition déjà
  anticipée depuis le Sprint 31 dans les tests du Layout System, aucun nouveau
  composant. `EmptyState` distinct pour "aucune saisie" et "aucun résultat".
- Recherche câblée dans `main_view.py` : champ de recherche avec recherche instantanée
  pendant la saisie (`on_change`), index reconstruit et vue rafraîchie chaque fois que
  les événements de l'année courante changent.
- 46 nouveaux tests (29 `SearchService` + 17 vue "Recherche"), zéro régression, zéro
  nouveau provider, zéro nouvelle source de données (conforme à la consigne du sprint).

Détail complet : `docs/JOURNAL.md`, session Sprint 45. ADR-036 dans `docs/DECISIONS.md`.

---

### Sprint 44 — Favoris intelligents

#### Added

- **`motorsport_calendar/gui/favorites_service.py`** — nouveau `FavoritesService`,
  source de vérité unique pour les championnats favoris (`list`/`is_favorite`/`add`/
  `remove`/`toggle`), persisté dans le même fichier de préférences centralisé que le
  reste de l'état GUI (`gui/preferences.py`, nouvelle clé `favorite_championships`) —
  jamais un second fichier.
- **"Mes favoris" devient une vraie page** — remplace le placeholder : chaque
  championnat enregistré, regroupé par catégorie, présenté comme un bouton
  sélectionnable ("favori" au lieu de "sélectionné pour cette génération") — réutilise
  intégralement l'accordéon de "Mon calendrier" (Sprint 43), désormais extrait dans
  `gui/components/championship_selector.py` (composant partagé, plus de duplication du
  code de sélection des championnats).
- **Les favoris deviennent une préférence globale automatiquement utilisée partout** :
  - **Dashboard** / **Ce week-end** : les championnats favoris apparaissent en premier
    parmi les cartes du week-end (`upcoming_weekend.find_upcoming_weekend`, une seule
    implémentation du tri partagée par les deux pages).
  - **Mon calendrier** : les championnats favoris pré-sélectionnent automatiquement la
    génération au lancement (favoris disponibles → priorité sur l'ancienne sélection
    mémorisée).
  - Basculer un favori déclenche un nouveau chargement (cache HTTP existant, pas de
    round-trip réseau réel) du Dashboard et de "Ce week-end" pour refléter le nouvel
    ordre sans redémarrage.
- Correction d'un bug latent : `_save_prefs()` (sauvegarde de la sélection "Mon
  calendrier") écrivait un dictionnaire neuf à chaque fois, effaçant silencieusement
  toute autre clé du fichier de préférences (dont les favoris) — corrigé en lecture-
  fusion-écriture, cohérent avec la persistance désormais centralisée.
- Isolation des tests du fichier de préférences réel de la machine (nouvelle fixture
  `autouse` dans `tests/conftest.py`) — un fichier réel avec des données de session
  précédentes existait sur cette machine, un risque de non-déterminisme corrigé avant
  qu'il ne cause un test instable.
- 36 nouveaux tests, zéro nouveau provider, zéro nouvelle source de données (conforme à
  la consigne du sprint).

Détail complet : `docs/JOURNAL.md`, session Sprint 44. ADR-035 dans `docs/DECISIONS.md`.

---

### Sprint 43 — Refonte UX de "Mon calendrier"

#### Changed

- **"Mon calendrier" abandonne son assistant 4 étapes (Sprint 26) pour une page unique
  réorganisée** — objectif purement ergonomique, aucune nouvelle fonctionnalité métier,
  aucun nouveau provider :
  - Les championnats deviennent le point d'entrée de la page, affichés immédiatement
    sous le titre, regroupés par catégorie dans des accordéons à un seul niveau
    (`ft.ExpansionTile`) — plus la longue liste de cases à cocher.
  - Chaque championnat est désormais un bouton sélectionnable (réutilise le style
    `selected` de `theme.card()`, anticipé au Sprint 26 mais jamais utilisé jusqu'ici) —
    sélection multiple conservée, jamais de boutons radio.
  - Le sélecteur de saison devient un contrôle secondaire, déplacé en haut à droite de
    l'en-tête de page (nouveau slot `trailing` de `PageHeader`).
  - Le résumé de sélection (Sprint 40) devient réellement permanent — plus de
    conditionnement par étape — et affiche désormais aussi le nombre de championnats
    sélectionnés, connu instantanément.
  - L'explorateur de saison (Sprint 41) ne s'affiche que si au moins un championnat est
    sélectionné ; un `EmptyState` s'affiche sinon (comportement déjà existant, simplement
    plus jamais masqué par une étape).
  - "Créer mon calendrier" (et le champ de destination) reste toujours visible dans un
    pied de page fixe qui ne défile jamais avec le reste de la page (nouveau slot
    `footer` de `PageContainer`).
- `gui/components/layout/page_header.py`/`page_container.py` — deux nouveaux paramètres
  optionnels (`trailing`, `footer`), tous deux `None` par défaut : chaque autre page de
  l'application reste strictement inchangée, structurellement et visuellement.
- `GenerateState` (`gui/models.py`) perd la machinerie de l'assistant
  (`current_step`/`STEP_COUNT`/`step_valid`/`can_advance`/`can_go_back`), devenue
  obsolète — `year`/`selected_championships`/`output_path`/`is_generating`/`is_ready()`
  inchangés.
- ~30 tests adaptés, ~35 nouveaux tests, zéro nouveau provider, zéro nouvelle source de
  données, zéro modification de la logique métier ou des modèles de domaine (conforme à
  la consigne du sprint).

Détail complet : `docs/JOURNAL.md`, session Sprint 43. ADR-034 dans `docs/DECISIONS.md`.

---

### Sprint 42 — Fiche événement

#### Added

- **`motorsport_calendar/gui/event_details.py`** — nouveau module de logique pure (sans
  Flet, sans I/O, entièrement testable avec de simples fixtures `Event`/`Session`) qui
  construit la "fiche événement" : championnat, nom de l'épreuve, circuit, pays, date, et
  la liste chronologique des sessions (type + heure). Réutilise intégralement les modèles
  existants — `ChampionshipCardData`/`SessionRow` (composant `ChampionshipCard`, Sprint
  30), `event_display.normalize_event_display` (Sprint 32, ADR-023) et le nouveau
  `event_display.session_type_label` (extrait de `upcoming_weekend.py` à l'occasion de ce
  sprint, un second consommateur en ayant besoin) — plutôt que d'en réinventer.
- **Chaque événement de l'explorateur de saison (Sprint 41) devient cliquable** — un clic
  ouvre une fiche dans une boîte de dialogue réutilisant tel quel le composant
  `ChampionshipCard` existant, sans aucune requête réseau supplémentaire (l'événement est
  retrouvé dans les données déjà en mémoire).
- 20 nouveaux tests (logique pure + vue), zéro nouveau provider, zéro nouvelle source de
  données (conforme à la consigne du sprint).

Détail complet : `docs/JOURNAL.md`, session Sprint 42. ADR-033 dans `docs/DECISIONS.md`.

---

### Sprint 41 — Explorer une saison

#### Added

- **`motorsport_calendar/gui/season_explorer.py`** — nouveau module de logique pure (sans
  Flet, sans I/O, entièrement testable avec de simples fixtures `Event`/`Session`) qui
  transforme la sélection année/championnats courante en une liste d'événements triée
  chronologiquement et regroupée par mois (`SeasonEventRow`/`SeasonMonthGroup`/
  `build_season_explorer`). Réutilise `event_display.normalize_event_display` (Sprint 32,
  ADR-023) pour le nom/circuit/pays de chaque événement — jamais de "Unknown", jamais de
  ligne dupliquée.
- **"Mon calendrier" gagne un explorateur de saison** — affiché sous le résumé de
  sélection (Sprint 40), visible sur les 4 étapes de l'assistant existant (inchangé) :
  pour chaque événement de la sélection courante, nom / championnat / circuit / pays /
  date, trié chronologiquement (chaque événement ancré sur sa session la plus précoce) et
  regroupé par mois. Se met à jour automatiquement à chaque changement de sélection
  (année ou championnat) — aucun nouveau fetch réseau, réutilise les événements déjà
  récupérés par `controller.get_calendar_year_events()` (Sprint 40).
- 26 nouveaux tests (logique pure + vue), zéro nouveau provider, zéro nouvelle source de
  données (conforme à la consigne du sprint).

Détail complet : `docs/JOURNAL.md`, session Sprint 41. ADR-032 dans `docs/DECISIONS.md`.

---

### Sprint 40 — Calendrier interactif

#### Added

- **`motorsport_calendar/gui/calendar_selection.py`** — nouveau module de logique pure
  (sans Flet, sans I/O, entièrement testable avec de simples fixtures `Event`/`Session`)
  agrégeant, pour la sélection année/championnats courante, le nombre d'événements, le
  nombre de sessions et la période couverte (`SelectionSummary`/`build_selection_summary`).
  Mêmes séparations "fetch" (controller) / "compute" (ce module) que `upcoming_weekend.py`
  et `dashboard.py`.
- `controller.get_calendar_year_events(year)` — récupère en une seule passe les événements
  de tous les championnats enregistrés pour une année donnée. Bascule de championnat dans
  l'assistant devient un filtrage local instantané sur ces données déjà récupérées : aucune
  nouvelle requête réseau par case cochée, seul un changement d'année déclenche un nouveau
  fetch.
- **"Mon calendrier" devient un navigateur de calendrier** — un résumé persistant
  (événements / sessions / période couverte) s'affiche entre l'indicateur d'étapes et le
  corps de l'étape, visible sur les 4 étapes de l'assistant existant (inchangé) : les étapes
  "Saison"/"Championnats" donnent un retour immédiat pendant le filtrage, et l'étape "Créer"
  affiche naturellement ce résumé juste au-dessus du récapitulatif et du bouton de
  génération.
- 25 nouveaux tests (logique pure, controller, vue), zéro nouveau provider, zéro nouvelle
  source de données (conforme à la consigne du sprint).

Détail complet : `docs/JOURNAL.md`, session Sprint 40. ADR-031 dans `docs/DECISIONS.md`.

---

### Sprint 39 — Dashboard Motorsport

#### Added

- **`motorsport_calendar/gui/dashboard.py`** — nouveau module de logique pure (sans Flet,
  entièrement testable avec de simples fixtures `Event`/`Session`) agrégeant les
  statistiques du Tableau de bord : nombre de championnats disponibles, nombre
  d'événements/sessions de la saison en cours, prochain week-end de course et
  championnats présents (réutilise `upcoming_weekend.find_upcoming_weekend`), prochain
  départ (prochaine session `RACE`, tous championnats confondus).
- **`motorsport_calendar/gui/views/dashboard.py`** — nouvelle vue, entièrement composée
  via le Layout System (`PageContainer`/`PageHeader`/`Section`/`SectionHeader`/
  `EmptyState`) et le composant `ChampionshipCard` existant (indirectement, via ses
  données) — aucun nouveau token de Design System, aucun nouveau composant de mise en
  page introduit.
- **Le Tableau de bord devient la page d'accueil de l'application** — premier onglet de
  la barre de navigation, chargé au lancement (même pattern de fetch en arrière-plan que
  "Ce week-end" depuis le Sprint 29).
- `controller.get_dashboard_data()` — réutilise le pipeline de fetch déjà existant
  (`_fetch_weekend_entries`, extrait de `get_upcoming_weekend` lors de ce sprint) : aucune
  seconde série de requêtes réseau dédiée, les statistiques de saison sont dérivées des
  mêmes événements déjà récupérés pour trouver le prochain week-end.
- `upcoming_weekend.format_session_datetime()` — nouvelle fonction publique (jour + date
  + heure, fuseau local du circuit) pour l'affichage du "prochain départ", un stat isolé
  qui — contrairement à une ligne de session dans une ChampionshipCard déjà contextualisée
  à un week-end connu — a besoin de la date complète.
- 32 nouveaux tests, zéro nouveau provider, zéro nouvelle source de données (conforme à la
  consigne du sprint).

Détail complet : `docs/JOURNAL.md`, session Sprint 39. ADR-030 dans `docs/DECISIONS.md`.

---

### Sprint 38 — Motorcycle Racing (MotoGP, Moto2, Moto3, WorldSBK)

#### Added

- **`motorsport_calendar/providers/motogp_series/`** — nouvelle abstraction partagée
  `PulseliveGpSource`, découverte en cours de sprint (pas anticipée) : MotoGP, Moto2 et
  Moto3 courent le même week-end de Grand Prix, au même circuit, et sont exposés par
  **l'API REST officielle et non authentifiée de Dorna Sports**
  (`api.pulselive.motogp.com`) — une seule requête par saison couvre les trois classes
  (le tableau `broadcasts` de chaque round embarque déjà toutes les sessions, taguées par
  `category.acronym`). Aucun scraping nécessaire.
- **`motorsport_calendar/providers/motogp/`**, **`moto2/`** et **`moto3/`** — trois
  nouveaux championnats implémentés pour de vrai, sur cette API officielle.
- **`motorsport_calendar/providers/worldsbk/`** — architecture complète enregistrée avec
  une source stub (`OfficialWorldSbkSource.get_season` lève `NotImplementedError`) : après
  investigation, aucune API/source publique exploitable trouvée pour World Superbike (voir
  section "Investigated" ci-dessous). Décision confirmée avec l'utilisateur.
- **CLI `generate-motogp`**, **`generate-moto2`**, **`generate-moto3`** et
  **`generate-worldsbk`** (`YEAR OUTPUT.ics`).
- Les 4 championnats rendus disponibles dans le Wizard, "Ce week-end", l'agrégateur
  `generate`, les catégories (nouveau groupe "🏍 Moto", utilisant `Category.MOTO` — déjà
  anticipée dans l'énumération depuis le Sprint 37) et les noms lisibles.
- 166 nouveaux tests, dont une fixture réelle non retouchée
  (`tests/fixtures/real/motogp_events_2026.json`) extraite de l'API en direct.

#### Investigated — no viable data source found for WorldSBK

- **Aucune API publique documentée** pour WorldSBK.
- Le site worldsbk.com tourne bien sur la même famille de plateforme que MotoGP ("Pulse
  Live"), mais son calendrier/planning est **entièrement rendu côté client** — aucune
  donnée exploitable dans le HTML brut.
- Un hôte API candidat a été identifié (`wsbk-api-origin.gplat-test.pulselive.com`,
  référencé dans le code source de la page) mais ne répond pas depuis l'extérieur (timeout
  de connexion — probablement un service interne non exposé publiquement).
- L'API MotoGP elle-même ne couvre pas WorldSBK (ses `timing_ids` n'exposent jamais de
  business unit SBK, confirmant une plateforme réellement distincte).

#### Fixed

- **`PulseliveGpSource._parse_datetime`** normalise désormais chaque horodatage vers UTC
  (l'API renvoie l'heure locale du circuit avec son propre décalage, ex. `+07:00`) — sans
  cette normalisation, `IcsExporter` produisait un `DTSTART;TZID="UTC+07:00"` synthétique
  sans bloc `VTIMEZONE` correspondant, potentiellement mal interprété par certains clients
  calendrier. Détecté et corrigé avant livraison (vérification live, pas en test unitaire).

Détail complet : `docs/JOURNAL.md`, session Sprint 38. ADR-029 dans `docs/DECISIONS.md`.

---

### Sprint 37 — GT Racing (GT World Challenge Europe/America/Asia, IGTC)

#### Added

- **`motorsport_calendar/providers/sro_series/`** — nouvelle abstraction partagée
  `SroTimetableSource`, découverte en cours de sprint (pas anticipée) : GT World Challenge
  Europe, America, Asia et l'Intercontinental GT Challenge sont tous les quatre organisés
  par SRO Motorsports Group sur le même CMS — chaque page course (`/event/{id}/{slug}`)
  expose un tableau HTML `<table class="timetable__table">` par jour (Session / Local Time
  / GMT). Aucune API publique, aucun JSON-LD (contrairement à WEC/ELMS/MLMC) — scraping
  HTML classique en dernier recours, comme prévu par la consigne du sprint.
- **`motorsport_calendar/providers/gtwc_europe/`**, **`gtwc_america/`**, **`gtwc_asia/`** et
  **`igtc/`** — quatre nouveaux championnats, intégrés selon le même patron que les
  précédents (`Provider`/`Source` ABC + source concrète réutilisant `SroTimetableSource`).
- **CLI `generate-gtwc-europe`**, **`generate-gtwc-america`**, **`generate-gtwc-asia`** et
  **`generate-igtc`** (`YEAR OUTPUT.ics`).
- Les 4 championnats rendus disponibles dans le Wizard, "Ce week-end", l'agrégateur
  `generate`, les catégories (nouveau groupe "🚗 GT") et les noms lisibles.
- Nouvelle catégorie GUI `Category.GT` — le groupe "Endurance" reste inchangé (WEC/ELMS/
  MLMC/IMSA), les séries GT-only vivent dans leur propre groupe.
- 184 nouveaux tests (1189 → 1373), dont des fixtures réelles non retouchées
  (`tests/fixtures/real/`) extraites des quatre sites en direct (calendrier + une page
  course par site).

#### Notable design decisions

- Format double manche "Sprint Cup" (GT World Challenge Europe/Asia — deux Qualifying et
  deux Race par week-end) détecté dynamiquement par comptage des sessions "Race" plutôt que
  supposé fixe : une seule Race → QUALIFYING/RACE classique ; deux Race → la première
  chronologiquement devient SPRINT_QUALIFYING/SPRINT (même mécanisme que les week-ends
  Sprint F1), la seconde reste QUALIFYING/RACE.
- Aucune donnée d'heure de fin fournie par la source (contrairement au JSON-LD ACO) : durée
  de course inférée depuis le motif "N Hour(s)" dans le slug de l'URL de l'événement
  (`bathurst-12-hour` → 12h, `crowdstrike-24-hours-of-spa` → 24h), avec repli sur une durée
  par défaut pour les formats non explicites (ex. `suzuka-1000km`).
- Bug réel détecté et corrigé en conditions live (pas en test unitaire) : combiner la date
  locale de la légende du tableau avec l'heure de la colonne GMT produisait un jour UTC
  incorrect pour les circuits loin de l'UTC (ex. Bathurst/Sydney) — corrigé en calculant le
  véritable instant UTC à partir de l'écart entre les colonnes "Local Time" et "GMT" de
  chaque ligne, sans dépendre d'une base de fuseaux horaires externe.

Détail complet : `docs/JOURNAL.md`, session Sprint 37. ADR-028 dans `docs/DECISIONS.md`.

---

### Sprint 36 — Extension IMSA (sortie de l'écosystème ACO)

#### Added

- **`motorsport_calendar/providers/imsa/`** — nouveau provider dédié à l'IMSA WeatherTech
  SportsCar Championship, premier championnat de l'application organisé par une entité
  totalement extérieure à l'ACO. Architecture Provider/Source ABC identique à celle des
  huit championnats précédents (aucun provider existant modifié).
- **CLI `generate-imsa YEAR OUTPUT.ics`**, ajoutée juste après `generate-wec` et suivant
  exactement le même patron (`_run_generate_command`).
- IMSA rendu disponible dans le Wizard, "Ce week-end", l'agrégateur `generate`, les
  catégories (groupe "Endurance", aux côtés de WEC/ELMS/MLMC) et les noms lisibles
  (`"IMSA WeatherTech SportsCar Championship"`).
- 39 nouveaux tests (`tests/test_imsa_provider.py`, `tests/test_cli_generate_imsa.py`),
  mirroring exact des suites WEC. Zéro régression sur les 1150 tests existants.

#### Investigated — no viable data source found

- **Aucune API publique documentée** pour IMSA.
- **imsa.com est bloqué au niveau infrastructure** (Cloudflare, HTTP 403 avec
  `cf-mitigated: challenge` sur absolument toutes les routes testées — page d'accueil,
  calendrier, articles, PDF statiques). Contourner ce blocage nécessiterait une
  automatisation de navigateur complète (Playwright), hors de portée des sources déjà
  utilisées dans ce projet et plus proche du contournement actif d'une protection anti-bot
  que du scraping.
- **Le prestataire de chronométrage (Al Kamel Systems)** est le même que WEC/ELMS/MLMC,
  mais son portail (`imsa.results.alkamelcloud.com`) n'est qu'une archive de résultats
  *post-course* — aucune donnée de calendrier prévisionnel.
- **Wikipedia** fournit un tableau de calendrier propre (round, nom de course, circuit,
  ville, date) via son API MediaWiki, mais **sans horaires de sessions** — insuffisant
  pour construire des objets `Session` valides sans inventer des horaires.
- **Sportscar365** publie des horaires de sessions, mais uniquement en prose libre dans
  des articles individuels — pas de données structurées, non fiable à parser
  systématiquement sur ~11 rounds.

#### Decision

- Provider IMSA enregistré et intégré partout, avec une source officielle stub
  (`OfficialImsaSource.get_season` lève `NotImplementedError`) — exactement le même
  traitement que WEC depuis Sprint 26. Confirmé avec l'utilisateur plutôt que d'inventer
  des horaires de sessions non fiables. Voir ADR-027 dans `docs/DECISIONS.md`.

Détail complet : `docs/JOURNAL.md`, session Sprint 36.

---

### Sprint 35 — Extension Endurance (ELMS, Michelin Le Mans Cup)

#### Added

- **`motorsport_calendar/providers/aco_series/`** — nouvelle abstraction partagée
  `AcoSportsEventSource`, découverte en cours de sprint (pas anticipée) : WEC, ELMS et
  Michelin Le Mans Cup sont tous les trois organisés par l'ACO sur le même
  CMS — chaque page de course (`/en/race/{slug}`) embarque un bloc
  `<script type="application/ld+json">` schema.org `SportsEvent`/`subEvent` avec des
  horaires ISO 8601 exacts. Aucune API publique, mais des données structurées bien plus
  fiables qu'un scraping HTML classique.
- **`motorsport_calendar/providers/elms/`** et **`motorsport_calendar/providers/mlmc/`** —
  deux nouveaux championnats, intégrés selon le même patron que les précédents
  (`Provider`/`Source` ABC + source concrète réutilisant `AcoSportsEventSource`). Road to
  Le Mans n'est pas un championnat séparé — elle apparaît comme un round de plus dans le
  calendrier MLMC, exactement comme sur le site officiel.
- **CLI `generate-elms YEAR OUTPUT.ics`** et **`generate-mlmc YEAR OUTPUT.ics`**.
- ELMS et MLMC rendus disponibles dans le Wizard, "Ce week-end", les catégories (groupe
  "Endurance", aux côtés de WEC) et les noms lisibles.
- 105 nouveaux tests, dont des fixtures réelles non retouchées (`tests/fixtures/real/`)
  extraites des deux sites en direct.
- `beautifulsoup4`/`lxml` ajoutés aux dépendances (parsing HTML/JSON-LD).

#### Fixed

- **`AcoSportsEventSource.fetch_html`** rendu transparent au cache (même contrat que
  `F1CalendarBaseSource.fetch_json`) après qu'un test d'intégration ait révélé qu'un
  mock posé sur `fetch_html` ne suffisait pas à contourner le cache disque réel — un
  détail interne à ce nouveau module, sans impact sur le comportement observable.

Détail complet : `docs/JOURNAL.md`, session Sprint 35. ADR-026 dans `docs/DECISIONS.md`.

---

### Sprint 34 — Extension Formula (Formula E)

#### Added

- **`motorsport_calendar/providers/formula_e/`** — nouveau championnat, intégré selon le
  même patron que F1 Academy : `FormulaEProvider`/`FormulaESource` (ABC) +
  `sources/f1calendar.py` réutilisant entièrement `F1CalendarBaseSource` (aucune nouvelle
  logique HTTP/cache/mapping — seuls la clé de série `"fe"`, la table de sessions et la
  table de circuits sont spécifiques). Enregistré dans `ProviderRegistry`/`SourceRegistry`
  sous l'id `"formula-e"`.
- **CLI `generate-formula-e YEAR OUTPUT.ics`** — mêmes garanties que les commandes
  existantes (cache, `--refresh`, gestion d'erreurs HTTP/timeout).
- Formula E rendue disponible dans le Wizard, "Ce week-end", les catégories (groupe
  "Formula") et les noms lisibles — automatiquement pour le Wizard/"Ce week-end" grâce à
  l'architecture registre déjà en place, avec une ligne ajoutée dans `categories.py`,
  `display_names.py` et `upcoming_weekend.py::WEEKEND_CHAMPIONSHIP_IDS`.
- 46 nouveaux tests (provider, source réelle, CLI, fixture réelle du dataset).

#### Changed

- **`motorsport_calendar/cli.py`** — les 5 commandes `generate-f1/f2/f3/f1-academy/wec`
  (copier-coller quasi identique depuis leur création) factorisées vers un helper partagé
  `_run_generate_command()`. Comportement/sorties strictement inchangés (verrouillé par les
  tests existants) ; `cli.py` passe de 355 à 182 lignes, dette ruff/mypy pré-existante
  réduite (13 → 5 erreurs mypy, 48 → 19 lignes non couvertes), aucune nouvelle dette.

Détail complet : `docs/JOURNAL.md`, session Sprint 34. ADR-025 dans `docs/DECISIONS.md`.

---

### Sprint 25 — Release Alpha Phase 1 — Navigation Architecture

#### Added

- **`motorsport_calendar/gui/views/`** — package de vues indépendantes (une par destination).
  Chaque module expose une fonction `build_*_view()` qui retourne un `ft.Control`.
  `main_view.py` ne contient plus que le shell de navigation et l'état partagé.
- **`views/weekend.py`** — 🏁 Ce week-end : placeholder structuré avec card skeleton
  (Championnat, Circuit, Pays, Sessions) + message "Aucune course ce week-end".
- **`views/calendar.py`** — 📅 Mon calendrier : `CalendarViewControls` dataclass + `build_calendar_view()`.
  Layout extrait de `main_view.py`, logique/état inchangés.
- **`views/favorites.py`** — ⭐ Mes favoris : placeholder "Vous pourrez bientôt retrouver ici…".
- **`views/preferences.py`** — ⚙ Préférences : liste des 6 rubriques futures (Langue, Fuseau
  horaire, Premier jour, Championnats favoris, Calendrier préféré, Synchronisation BApps)
  chacune avec chip "Disponible prochainement". `_PREF_ROWS` ordonné, lié à `PreferencesModel`.
- **`views/about.py`** — ℹ À propos : extrait de `main_view.py`, reçoit `url_launcher` en paramètre.
- **`PreferencesModel`** dans `gui/models.py` — dataclass `frozen=True` avec 6 champs typés :
  `language`, `timezone`, `first_day_of_week`, `favorite_championships`, `preferred_calendar`,
  `bapps_sync_enabled`. Pas de logique métier — structure uniquement.
- **`strings.py`** : +16 chaînes — nav (weekend, my_calendar, favorites, preferences) + weekend
  (empty_title, coming_soon, section_*) + favorites + prefs (6 rubriques + coming_soon).
- **44 nouveaux tests** : `test_gui_preferences_model.py` (22) + `test_gui_views.py` (22).

#### Changed

- **Navigation** : 3 destinations → 5 destinations : 🏁 Ce week-end / 📅 Mon calendrier /
  ⭐ Mes favoris / ⚙ Préférences / ℹ À propos. "Accueil" supprimé.
- **`main_view.py`** refactorisé : ne contient plus que le shell de navigation (`NavigationRail`,
  services, état partagé, handlers). Les layouts sont délégués aux modules `views/`.
- **Flet 0.85 fixes bonus** : `ft.border.all()` → `ft.Border.all()` (module ≠ classe).

#### Tests

- 44 nouveaux tests. Total : **764 tests** — couverture 94 %.

---

### Sprint 24 — Desktop Alpha 3 — Product Polish

#### Added

- **`motorsport_calendar/gui/categories.py`** — modèle de données pour les groupes visuels
  de championnats. `Category` (StrEnum : FORMULA, ENDURANCE, MOTO, RALLY, AMERICA),
  `ChampionshipGroup` (dataclass frozen), `GROUPS` (registre ordonné), `get_groups_for()`
  (retourne les groupes filtrés sur les IDs disponibles, IDs inconnus dans un groupe "Autres").
  Architecture extensible : ajouter un groupe = 1 entrée dans `GROUPS`.
- **Navigation interne** : `ft.NavigationRail` avec 3 destinations (Accueil, Calendrier,
  À propos). Contenu switché sans reconstruction des vues.
- **Écran Accueil** : icône, titre, sous-titre, description, bouton CTA vers le Calendrier.
- **Écran À propos** : Motorsport Calendar, Version Alpha, développeur BApps, lien GitHub
  (via `ft.UrlLauncher`), Licence MIT.
- **`strings.py`** : 8 nouvelles chaînes — `nav_home`, `nav_calendar`, `nav_about`,
  `home_title`, `home_body`, `home_cta`, `about_version`, `about_developer`,
  `about_github_label`, `about_license`, `about_description`.
- **25 nouveaux tests** : `test_gui_categories.py`.

#### Changed

- **Championnats groupés visuellement** : dans l'écran Calendrier, les cases à cocher sont
  regroupées sous des en-têtes `🏎 Formula` et `🏁 Endurance` (avec séparateur entre groupes).
- **Rail responsive** : `nav_rail.extended = True` quand `page.width > 900` (géré via
  `page.on_resize`). Labels toujours visibles en mode compact (`label_type=ALL`).
- **Fenêtre** : `width=700`, `min_width=560` (rail + contenu), `height=720`.
- **Layout** : `ft.Row([nav_rail, VerticalDivider, content_area])` au lieu d'une `Column`
  unique. `page.padding = 0` (padding géré par chaque vue).
- **`UrlLauncher`** et `FilePicker` inscrits dans `page.services` (tous deux Services Flet).

#### Tests

- 25 nouveaux tests : `test_gui_categories.py`. Total : **720 tests**.

---

### Sprint 23 — Desktop Alpha 2 — UX Polish

#### Added

- **`motorsport_calendar/gui/strings.py`** — module de centralisation de toutes les chaînes
  UI. `Strings` dataclass + singleton `STRINGS`. `Strings.from_dict()` prépare l'i18n future
  (chargement depuis un fichier `fr.json` / `en.json` sans réécriture). Fonction `plural(n)`.
- **`motorsport_calendar/gui/display_names.py`** — mapping IDs techniques → noms lisibles.
  `get_display_name()` : `"formula1"` → `"Formula 1"`, `"f1-academy"` → `"F1 Academy"`,
  `"wec"` → `"FIA WEC"`. Fallback title-case pour les IDs inconnus. `DEFAULT_SELECTED`.
- **`motorsport_calendar/gui/preferences.py`** — persistance des préférences GUI entre
  sessions dans `~/.config/motorsport-calendar/gui_prefs.json`.
  `load_preferences()` / `save_preferences()`. Gestion silencieuse des erreurs I/O.
- **`motorsport_calendar/gui/assets/`** — dossier prévu pour l'icône de l'application.
  Commentaire dans `app.py` explique les 3 étapes pour la brancher.
- **`docs/PRODUCT_VISION.md`** — vision produit (≤ 2 pages) : pourquoi / pour qui /
  philosophie / périmètre négatif.

#### Changed

- **Championnats lisibles** : les cases à cocher affichent désormais `"Formula 1"`,
  `"Formula 2"`, `"Formula 3"`, `"F1 Academy"`, `"FIA WEC"` au lieu des IDs techniques.
- **Valeurs par défaut intelligentes** : Formula 1 cochée au premier lancement.
  Les sélections sont mémorisées entre les sessions.
- **Bouton** : `"Générer"` → `"Créer mon calendrier"` (via `STRINGS`).
- **Nom de fichier intelligent** : le dialogue de sauvegarde pré-remplit
  `motorsport-calendar-{année}.ics` (calculé depuis la saison sélectionnée).
- **Dernier dossier mémorisé** : le FilePicker rouvre dans le dernier dossier utilisé.
- **Message de succès** : dialogue modal après génération réussie affichant :
  - ✅ total d'événements et de sessions
  - chemin complet du fichier enregistré
  - résumé par championnat (✓ / ✗)
  - boutons `[Ouvrir le dossier]` et `[Fermer]`
- **Textes via `STRINGS`** : `main_view.py` ne contient plus aucun texte en dur.
- **Dimensions fenêtre** : `min_width=520`, `min_height=580`, `width=560`, `height=700`
  via `page.window`.
- **`controller.generate_calendar()`** : retourne désormais
  `dict[str, tuple[int, int] | str]` au lieu de `dict[str, int | str]`.
  Le tuple est `(event_count, session_count)`.

#### Tests

- 36 nouveaux tests : `test_gui_strings.py` (14), `test_gui_display_names.py` (13),
  `test_gui_preferences.py` (9). Total : 695 tests.

---

### Hotfix GUI-02 — FilePicker / page.services

#### Fixed

- **`FilePicker` enregistré dans `page.services` et non `page.overlay`** : dans Flet 0.85,
  `FilePicker` hérite de `Service` (et non de `Control`). Le placer dans `page.overlay`
  causait l'erreur `Unknown control: FilePicker` à l'affichage. Correction :
  `page.services.append(file_picker)`.
- Parcours complet validé : fenêtre ouverte sans bande rouge, `generate_calendar()` crée un
  fichier `.ics` valide (F2 2025 — 14 événements, 15 707 octets).

---

### Hotfix GUI-01 — Compatibilité Flet 0.85

#### Fixed

- **`ft.Dropdown.on_change` → `on_select`** : l'argument `on_change` a été supprimé dans
  Flet 0.80+ au profit de `on_select` pour les menus déroulants. Le sélecteur de saison
  levait `TypeError: Dropdown.__init__() got an unexpected keyword argument 'on_change'`
  au lancement.
- **`ft.Button(text=...)` → `content=`** : dans Flet 0.80+, `ft.Button` (et tous les boutons)
  n'acceptent plus `text` mais `content: str | Control`. Le texte du bouton "Générer"
  n'était pas affiché et causait un `TypeError` au démarrage.
- La GUI s'ouvre désormais correctement sous Flet 0.85.3.

---

### Sprint 22 — Desktop Edition (Phase 1)

#### Added

- **Interface graphique desktop** — `motocal-gui` (ou `python -m motorsport_calendar.gui`).
  Fenêtre Flet avec :
  - Sélecteur de saison (année courante ±5)
  - Cases à cocher par championnat (liste automatique depuis `ProviderRegistry`)
  - Sélecteur de fichier de sortie via `FilePicker` natif
  - Bouton "Générer" (actif seulement si tous les champs sont remplis)
  - Anneau de progression pendant la génération
  - Affichage du résultat par championnat (✓ N événements / ✗ erreur)
- **`motorsport_calendar/gui/`** — package dédié, zéro duplication du moteur :
  - `models.py` — `GenerateState` (dataclass, état mutable de la vue)
  - `controller.py` — `list_championships()` + `async generate_calendar()` (miroir exact du pipeline CLI `generate`)
  - `main_view.py` — vue Flet complète (requiert `flet>=0.80`)
  - `app.py` — point d'entrée `ft.run()`
  - `__main__.py` — support `python -m motorsport_calendar.gui`
- **Dépendance optionnelle** `flet>=0.80` : `pip install motorsport-calendar[gui]`
  (la CLI reste installable sans Flet)
- **Entrée script** `motocal-gui` dans `pyproject.toml`
- **32 tests GUI** : `test_gui_models.py` (12 tests) + `test_gui_controller.py` (20 tests).
  Aucune dépendance Flet dans les tests — `controller.py` et `models.py` sont purement Python.

#### Technical

- Flet 0.85 API : `ft.run()` (remplace `ft.app()` déprécié), `ft.Button` (remplace `ft.ElevatedButton`), `ft.Icons` / `ft.Colors` (capitalisés), `FilePicker.save_file()` async.
- Génération dans le thread de l'event loop Flet — les appels httpx s'exécutent dans la boucle asyncio de Flet, l'anneau de progression tourne pendant les requêtes réseau.

---

### Sprint QA-03

#### Fixed

- **Bug critique : F2/F3/F1 Academy retournaient systématiquement 0 événements** (ADR-017).
  `F1CalendarBaseSource._get_season()` utilisait `raw.get("events", [])` mais le dataset
  `sportstimes/f1` (GitHub) utilise la clé `"races"` — pas `"events"`. Ce bug existait
  depuis l'introduction du Support Series Framework (Sprint 14) et a masqué 100 % des données
  F2/F3/F1 Academy en production depuis le début.
  Correction : `raw.get("races", [])` dans `f1calendar_base.py`.
  **Pourquoi les tests n'ont rien détecté** : les fixtures de tests utilisaient aussi `"events"`
  (copiées/collées depuis le code), ce qui faisait correspondre les tests au code incorrect
  sans jamais tester le comportement réel du dataset.

#### Added

- **Fixtures réelles** `tests/fixtures/real/` : extraits minimaux (2 events) du dataset réel
  `sportstimes/f1` pour F2 (Australian + Bahrain 2025), F3 (Australian + Bahrain 2025) et
  F1 Academy (Chinese + Jeddah 2025). Utilisent la clé `"races"` et les clés de sessions
  réelles. Ces fixtures servent de garde-fou contre toute régression similaire.
- **Tests `tests/test_real_fixtures.py`** : 3 classes (`TestF2RealFixture`, `TestF3RealFixture`,
  `TestF1AcademyRealFixture`), chacune vérifiant que le fixture contient `"races"`, que 2 events
  sont chargés, et que le CLI produit le bon nombre de VEVENTs.
- **`TestRacesKeyRegression`** dans `test_f1calendar_base.py` : 3 tests documentant que
  `"races"` est lu, `"events"` est ignoré, et que si les deux clés coexistent seul `"races"`
  est lu.
- **Isolation des tests CLI `generate`** : fixture `autouse=True` `_isolate_support_series`
  dans `test_cli_generate.py` empêche F2/F3/F1 Academy de faire de vrais appels réseau vers
  GitHub pendant les tests d'intégration F1/WEC.

#### Changed

- `tests/test_f1calendar_base.py` : `"events"` → `"races"` dans `_TEST_RESPONSE` et
  `_EMPTY_RESPONSE` (fixtures alignées sur le dataset réel).
- `tests/test_f1calendar_source.py` : `"events"` → `"races"` dans toutes les fixtures.
- `tests/test_cli_generate_f2.py`, `test_cli_generate_f3.py`, `test_cli_generate_f1_academy.py` :
  `"events"` → `"races"` dans toutes les fixtures de chaque fichier.

---

### Sprint 21.2

#### Fixed

- **Formula 2 : rétrocompatibilité des clés de sessions** (hotfix — ADR-014 mis à jour).
  Le dataset `sportstimes/f1` a renommé deux clés F2 à partir de 2025 :
  `fp1` → `practice` et `sprintRace` → `sprint`.
  Conséquence : les calendriers F2 2025+ n'exportaient que 2 sessions sur 4.
  `_SESSION_MAP` accepte désormais les quatre formes ; les saisons 2024 et antérieures
  continuent de fonctionner sans modification.
  6 tests de régression ajoutés dans `test_cli_generate_f2.py` (`TestF2SessionKeyCompat`) :
  3 tests unitaires `_build_event` et 3 tests CLI VEVENT pour 2024, 2025 et 2026.

---

### Sprint 21

#### Added

- **F1 Academy provider** — `motocal generate-f1-academy YEAR OUTPUT.ics` génère le calendrier F1 Academy complet.
  - `F1AcademyProvider` + `F1AcademySource` (ABC) — même architecture que F1/F2/F3/WEC.
  - `F1CalendarSource(F1CalendarBaseSource, F1AcademySource)` — ~60 lignes, 4 overrides uniquement.
    Source : `https://raw.githubusercontent.com/sportstimes/f1/main/_db/f1-academy/{year}.json` (MIT).
    Sessions : Free Practice 1 (45 min), Free Practice 2 (30 min), Qualifying 1/2 (30 min),
    Race 1 (30 min), Race 2 (30 min), Race 3 (30 min). 15 circuits avec fuseaux IANA.
  - Format de sessions propre à F1 Academy : `fp1`, `fp2`, `qualifying1`, `qualifying2` (2023-2024),
    `race1`, `race2`, `race3`. `qualifying2` absent en 2025+.
  - Couverture : 2023 → présent.
  - Auto-inclus dans `motocal generate` (opt-out via `config.yaml`).
  - `config.example.yaml` mis à jour avec la section `f1-academy`.
  - ADR-016 : mapping `race2 → FP3` pour garantir l'unicité des UIDs ICS sans modifier
    les modèles métier. Recommandation : ajouter `RACE2`/`RACE3` à `SessionType` dans v0.4.
  - 41 nouveaux tests (F1AcademyProvider : 13, CLI generate-f1-academy : 28).

---

### Sprint 20

#### Added

- **Formula 3 provider** — `motocal generate-f3 YEAR OUTPUT.ics` génère le calendrier FIA F3 complet.
  - `Formula3Provider` + `Formula3Source` (ABC) — même architecture que F1/F2/WEC.
  - `F1CalendarSource(F1CalendarBaseSource, Formula3Source)` — ~50 lignes, 4 overrides uniquement.
    Source : `https://raw.githubusercontent.com/sportstimes/f1/main/_db/f3/{year}.json` (MIT).
    Sessions mappées : Free Practice (45 min), Qualifying (30 min), Sprint Race (30 min),
    Feature Race (40 min). Clés dataset F3 : `practice`, `qualifying`, `sprint`, `feature`
    (diffèrent de F2). 13 circuits avec fuseaux IANA (couverts 2021-2025).
  - Couverture : 2022 → présent (avant 2022, les sessions `race1/race2/race3` sont ignorées).
  - Auto-inclus dans `motocal generate` (opt-out via `config.yaml`).
  - Enregistré sous `source: f1calendar` dans `config.yaml`.
  - `config.example.yaml` mis à jour avec la section `formula3`.
  - 36 nouveaux tests (Formula3Provider : 12, CLI generate-f3 : 24).

---

## [0.2.0] — 2026-07-05

### Fixed

- **`typer[all]` extra supprimé** — typer 0.26.x n'expose pas d'extra `all` ; causait un WARNING
  à chaque `pip install`. Remplacé par `typer>=0.12` (rich reste une dépendance directe).
- **`python-dateutil` supprimé** — dépendance déclarée mais jamais utilisée dans le code.
- **Version `0.1.0` → `0.2.0`** dans `pyproject.toml` et `__init__.py` (incohérence depuis Sprint 15).

### Added

- **`python -m motorsport_calendar`** — `__main__.py` ajouté : permet de lancer la CLI sans que le
  dossier `Scripts` soit dans le PATH (utile sur Windows). Toutes les commandes sont disponibles.
- **Tests de packaging** (`tests/test_packaging.py`, 36 tests) — vérifient que le package installé
  est correctement câblé : version metadata, `python -m` entry point, commandes CLI enregistrées,
  imports publics, auto-découverte des registries.
- **CI multi-plateforme** — ajout de `macos-latest` et `windows-latest` dans la matrice GitHub Actions.

- **Support Series Framework** (`providers/support_series/f1calendar_base.py`) — base commune pour
  F2, F3, F1 Academy, Porsche Supercup. Extrait la logique partagée de `F1CalendarSource` :
  - `F1CalendarBaseSource(JsonDataSource, ABC)` — `__init__`, `get_season`, `fetch_json`,
    `_resolve_circuit_data`, `_build_circuit`, `_build_event` tous paramétrés via 4 propriétés abstraites.
  - `_build_session()` — fonction pure module-level, générique.
  - Chaque nouveau support series ne nécessite que ~15 lignes : `_series_key`, `_session_map`,
    `_circuit_data`, `_make_championship`.
  - `F1CalendarSource` (F2) refactorisée pour hériter de la base — aucun changement de comportement.
  - 36 nouveaux tests dans `tests/test_f1calendar_base.py`.

- **Formula 2 provider** — `motocal generate-f2 YEAR OUTPUT.ics` génère le calendrier FIA F2 complet.
  - `Formula2Provider` + `Formula2Source` (ABC) — même architecture que F1/WEC.
  - `F1CalendarSource` — source JSON MIT via `github.com/sportstimes/f1`, un seul GET par saison.
    Requête : `https://raw.githubusercontent.com/sportstimes/f1/main/_db/f2/{year}.json`.
    Sessions mappées : FP (45 min), Qualifying (30 min), Sprint Race (45 min), Feature Race (65 min).
    23 circuits avec fuseaux IANA ; fallback `"Unknown"` / `"UTC"` pour les circuits inconnus.
  - Auto-inclus dans `motocal generate` (opt-out via `config.yaml`).
  - Enregistré sous `source: f1calendar` dans `config.yaml`.
  - `config.example.yaml` mis à jour avec la section `formula2`.
  - 74 nouveaux tests (F1CalendarSource : 44, Formula2Provider : 9, CLI generate-f2 : 21).

- **Data Acquisition Layer** (`motorsport_calendar/core/datasource/`) — abstract interfaces
  separating raw data retrieval from domain mapping:
  - `DataSource` — common ABC marker
  - `JsonDataSource` — abstract `fetch_json(url, params)` for REST JSON APIs
  - `HtmlDataSource` — abstract `fetch_html(url)` for HTML scraping
  - `IcsDataSource` — abstract `fetch_ics(url)` for iCalendar feeds
- **`OpenF1Source` migrated to `JsonDataSource`** — implements `fetch_json`, validating the
  DAL pattern. `_get_json` is preserved as a thin wrapper for backward-compatible test mocks.
  Zero change to the public `get_season()` API.
- 25 new tests in `tests/test_datasource.py`.

- **`JolpicaSource`** — full implementation of `Formula1Source` using the Jolpica API
  (`http://api.jolpi.ca/ergast/f1/{year}/races.json`), the Ergast-compatible successor
  (Apache-2.0). Covers F1 data from 1950 onwards. Single request per season; session end
  times inferred from session type; 34 circuits with IANA timezones; historical races without
  time data fall back to noon UTC. Registered as `source: jolpica` in `config.yaml`.
- `ErgastSource` is now a backward-compatibility alias for `JolpicaSource` (Ergast was shut
  down end-2024). Its test now asserts the alias relationship.
- 43 new tests in `tests/test_jolpica_source.py`.

---

## [0.1.0] — 2026-07-05

Initial release. Formula 1 calendars are fully functional; WEC architecture is in place
pending a working data source.

### Added

#### Architecture
- **`ProviderRegistry`** — central registry with auto-discovery (`pkgutil.iter_modules`).
  Provider factories register themselves at import time; the CLI calls `registry.discover()`
  once and never hardcodes provider names.
- **`SourceRegistry`** — symmetric registry keyed by `(championship_id, source_name)`.
  Source factories auto-register in each `providers/X/sources/__init__.py`.
- **Opt-out configuration** — a provider absent from `config.yaml` is enabled by default;
  set `enabled: false` to exclude it.

#### Data models (Pydantic v2, `frozen=True`)
- `Championship` / `ChampionshipCategory` (SINGLE_SEATER, ENDURANCE, …)
- `Circuit` with IANA timezone
- `Session` / `SessionType` (RACE, QUALIFYING, FREE_PRACTICE, HYPERPOLE, …)
- `Event` / `EventStatus` with `event_uid`

#### Providers
- **Formula 1** — `Formula1Provider` + `OpenF1Source` (openf1.org API, 2023 onwards).
  Mapping covers 25 circuits with correct IANA timezones. Stubs: `ErgastSource`,
  `OfficialFormula1Source`, `CachedFormula1Source`.
- **WEC** — `WecProvider` + `OfficialWecSource` stub (architecture complete, HTTP not yet
  implemented).

#### Exporters
- **`IcsExporter`** — RFC 5545 compliant. One VEVENT per session. Configurable VALARM
  reminder via `alarm_minutes`. Supports `export()` (file) and `export_to_string()`.

#### Cache
- **`HttpCache`** — disk-based JSON cache. Key: SHA-256(url + sorted params). Configurable
  TTL (default 24 h). `--refresh` flag bypasses cache on demand.

#### Configuration
- **`ConfigService`** — reads `config.yaml` from CWD then `~/.config/motorsport-calendar/`.
  Falls back to Pydantic defaults when no file is found.
- **`config.example.yaml`** — fully commented reference configuration.

#### CLI (`motocal`)
- `generate-f1 YEAR OUTPUT.ics [--refresh]` — Formula 1 calendar via OpenF1.
- `generate-wec YEAR OUTPUT.ics [--refresh]` — WEC calendar (exits cleanly with a
  descriptive message while the source is unimplemented).
- `generate YEAR OUTPUT.ics [--refresh]` — fetches all enabled providers and merges them
  into a single ICS file. Per-provider resilience: if one fails, the others continue.
  Exit 0 if at least one provider succeeds.
- `providers` — lists all auto-discovered providers.
- `version` — shows the current version.

#### Tests & quality
- 306 tests — 0 failures — 92 % coverage.
- `pytest-asyncio` with `asyncio_mode = "auto"`.
- `ruff` + `mypy` + `pre-commit` hooks.
- GitHub Actions CI on Python 3.12 and 3.13.

[Unreleased]: https://github.com/naviss29/motorsport-calendar/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/naviss29/motorsport-calendar/releases/tag/v0.1.0
