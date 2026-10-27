# AUDIT.md — Audit & Consolidation (Sprint 50)

> Rapport d'audit complet du projet, réalisé en amont de nouveaux
> développements fonctionnels. Aucune fonctionnalité, aucun provider,
> aucune page, aucun changement de comportement utilisateur n'a été ajouté
> ou modifié dans ce sprint — uniquement de la consolidation.

---

## Audit rapide

| Indicateur | Avant Sprint 50 | Après Sprint 50 |
|---|---|---|
| Tests | 1863 passants | **1865 passants**, 0 échouant (+2 tests de non-régression performance) |
| Couverture | ~97 % | ~97 % (inchangée — aucun scénario supprimé) |
| Dette Ruff | 149 erreurs | **0 erreur** |
| Dette mypy — `motorsport_calendar/` | 87 erreurs | **23 erreurs** (famille unique, documentée ci-dessous) |
| Dette mypy — `tests/` | 402 erreurs | **157 erreurs** (mêmes familles, voir ci-dessous) |
| TODO/FIXME/XXX dans le code source | 0 | 0 (déjà propre — le suivi se fait dans `docs/TODO.md`, 107 items ouverts, un backlog vivant sur 50 sprints, pas de la dette oubliée) |
| Dette supprimée | — | 149 erreurs Ruff, 64 erreurs mypy source, 245 erreurs mypy tests, 1 bug réel (`core/service.py`), 21 docstrings publiques manquantes, 2 duplications de test factorisées |
| Dette restante | — | 23 + 157 erreurs mypy (famille Flet stub-version + mocks dynamiques, voir §4) ; `main_view.py::build_main_view` 771 lignes (voir §6) |
| Optimisations réalisées | — | Fetch concurrent des providers (`cli.py::generate`, `gui/controller.py::generate_calendar`) — mesuré, pas seulement affirmé |
| Optimisations reportées | — | Découpage de `build_main_view` (771 lignes) — voir §6 et `docs/TODO.md` |

### Les 10 fichiers les plus volumineux

| Lignes | Fichier |
|---|---|
| 1170 | `tests/test_gui_views.py` |
| 864 | `motorsport_calendar/gui/main_view.py` |
| 740 | `tests/test_gui_controller.py` |
| 706 | `motorsport_calendar/cli.py` |
| 602 | `tests/test_cli_generate.py` |
| 552 | `tests/test_sro_timetable_base.py` |
| 538 | `motorsport_calendar/providers/sro_series/timetable_base.py` |
| 506 | `tests/test_wec_provider.py` |
| 464 | `tests/test_jolpica_source.py` |
| 454 | `tests/test_gui_notification_service.py` |

Les fichiers de test dominent le classement — normal et sain pour un projet
qui privilégie la couverture réelle (données capturées en direct, pas de
mocks superficiels) plutôt que des tests courts et superficiels. Côté code
source, `gui/main_view.py` et `cli.py` sont les deux seuls fichiers de
production dans le top 10 — voir §6 pour `main_view.py`.

---

## 1. État général du projet

Motorsport Calendar a traversé 49 sprints sans qu'aucune pause de
consolidation n'ait été demandée avant celle-ci — chaque sprint documente
scrupuleusement sa propre dette dans `docs/AI_CONTEXT.md`, mais rien
n'agrège une vue d'ensemble. Ce sprint confirme ce que l'historique
laissait supposer : **le projet est globalement sain**. Aucune duplication
structurelle grave, aucun import circulaire, aucune dépendance déclarée
inutilisée, zéro TODO oublié dans le code, et un seul bug réel détecté
(`core/service.py`, jamais exécuté par aucun code appelant — voir §3). La
dette identifiable se concentre presque entièrement dans deux zones bien
délimitées et déjà connues : le décalage entre les stubs de types Flet
0.80 (utilisés au moment d'écrire le code) et Flet 0.85.3 (réellement
installé), et le typage des tests utilisant `unittest.mock`.

## 2. Points forts

- **Architecture Provider/Source stable et cohérente** — 17 championnats,
  chacun suivant strictement le même patron (`Provider` ABC + `XSource`
  ABC + `sources/` avec factories enregistrées), zéro exception. Aucun
  import circulaire détecté sur l'ensemble du paquet (136 modules
  scannés).
- **Zéro dépendance runtime inutilisée** — les 9 dépendances déclarées
  (`typer`, `rich`, `pydantic`, `icalendar`, `httpx`, `pyyaml`,
  `beautifulsoup4`, `lxml`, `tzdata`) sont toutes réellement consommées,
  y compris les deux "invisibles" (`lxml` comme moteur de
  `BeautifulSoup`, `tzdata` pour `zoneinfo` sous Windows).
- **Zéro code mort significatif** — `vulture` (nouvellement installé
  pour cet audit) à 80 % de confiance ne remonte qu'un faux positif
  (un paramètre Typer lu par introspection). Le seul candidat réel
  (`BAppsColors`, voir §3) est une classe de documentation-as-code
  assumée, pas un oubli.
- **Docstrings globalement bonnes** — 367 fonctions/classes publiques
  scannées, 291 déjà documentées avant ce sprint. Les 76 "manques"
  restants après ce sprint sont *tous* des redéfinitions triviales d'une
  méthode déjà pleinement documentée sur son ABC (`Provider.name`,
  `Formula1Source.get_season`, etc.) — convention Python standard,
  volontairement non dupliquée.
- **Tests contre données réelles** — la discipline "jamais de fixture
  inventée, toujours un extrait capturé en direct" (`tests/fixtures/real/`)
  tenue depuis le Sprint 32 continue d'être respectée, et a permis de
  détecter plusieurs bugs réels par le passé (durée de course Le Mans,
  Sprint 48 ; voir `docs/JOURNAL.md`).

## 3. Points faibles / dette identifiée et corrigée ce sprint

- **`core/service.py::CalendarService.export_championship` — bug réel,
  corrigé.** Cette classe orchestratrice, exportée depuis `core/__init__.py`
  mais **jamais appelée par aucun code réel** (ni CLI, ni GUI — confirmé
  par recherche exhaustive), passait un `Championship` à
  `Exporter.export()` qui attend un `Iterable[Event]` — une confusion entre
  "les métadonnées du championnat" et "les événements à exporter". mypy ne
  l'avait jamais signalé car ce module n'était jamais inclus dans un scan
  mypy complet auparavant. Coverage confirmait 0 % sur le corps de la
  méthode (jamais exercée par un test). Corrigé pour de bon : la méthode
  récupère désormais réellement les événements via `provider.fetch_events`
  avant de les exporter — zéro impact utilisateur puisque rien n'appelait
  ce chemin, mais la classe est maintenant correcte si un futur sprint
  décide de l'exposer (API programmatique, par exemple).
- **`gui/theme.py::BAppsColors`** — classe de constantes (palette
  "écosystème BApps", distincte de `MotorsportColors`) jamais consommée
  par aucun token sémantique (`Colors`) ni aucune vue. Conservée
  volontairement : elle documente la provenance de la palette produit
  (voir le docstring du module, "Color sources"), un rôle de traçabilité
  de design system plutôt qu'un oubli de câblage. Signalée ici pour
  qu'un futur audit sache qu'elle a été examinée, pas manquée.
- **149 erreurs Ruff, désormais 0** — dominées par des règles mécaniques
  et sûres (imports non triés, imports inutilisés, `noqa` obsolètes,
  `datetime.timezone.utc` → `datetime.UTC`) plus une vingtaine de cas
  méritant une lecture individuelle (`pytest.raises(Exception)` trop
  large sur 4 tests de modèles frozen — réellement
  `pydantic.ValidationError`, jamais vérifié explicitement avant ; 6
  `lambda` assignées à un nom converties en `def` ; `raise ... from exc`
  ajouté sur 5 chaînes d'exception CLI pour préserver le contexte de
  débogage ; `Category(str, Enum)` aligné sur `enum.StrEnum`, déjà la
  convention de tous les autres enums du projet).
- **87 → 23 erreurs mypy dans `motorsport_calendar/`** — la quasi-totalité
  provenait d'annotations `dict`/`list` sans paramètres génériques
  (`dict[str, Any]` au lieu de `dict` nu), corrigées mécaniquement dans
  `cache/http_cache.py`, `cli.py`, `config/`, `core/datasource/`,
  `providers/formula1/sources/{openf1,jolpica}.py`,
  `providers/support_series/f1calendar_base.py`,
  `providers/motogp_series/pulselive_base.py`,
  `providers/formula2/sources/f1calendar.py`, `gui/preferences.py`,
  `gui/strings.py`, `gui/controller.py`. Un cas non-mécanique corrigé à la
  main dans `jolpica.py::_get_json` (union `list | dict` mal réconciliée
  après le typage de `HttpCache.get_json`, résolue avec un `cast()`
  explicite documentant que l'API Jolpica ne renvoie jamais une liste à
  cet endpoint). Package de stubs manquant ajouté aux dépendances dev
  (`types-PyYAML`, `types-icalendar`) plutôt que suppressions locales —
  élimine 5 erreurs d'un coup et bénéficiera à tout futur sprint touchant
  `config/service.py` ou `exporters/ics.py`.
- **402 → 157 erreurs mypy dans `tests/`** — la configuration mypy pour
  les tests (`[mypy-tests.*]`, `mypy.ini`) était insuffisamment relâchée
  par rapport à la pratique standard pour du code utilisant
  `unittest.mock` intensivement : `disallow_untyped_calls`,
  `check_untyped_defs` et `warn_return_any` restaient actifs, générant
  des centaines de faux positifs sur des appels à des `AsyncMock`/objets
  dynamiquement typés — sans jamais attraper une vraie erreur de logique
  de test (les 1863 tests passaient déjà tous). Relâchés pour les tests
  uniquement (zéro impact sur `motorsport_calendar/`, toujours en
  `strict = True`), ce qui a fait tomber le compte à 210 sans toucher un
  seul fichier de test. Complété par : suppression de 24 commentaires
  `# type: ignore` devenus inutiles (mécanique, vérifié un par un via
  mypy lui-même) et une correction ciblée dans
  `test_aco_sports_event_base.py` (14 occurrences d'un même pattern
  `_session_type_for_label(...)[0]` non-narrowed, remplacées par un
  helper `_type_for()` qui fait `assert result is not None` une seule
  fois — double bénéfice, dette mypy ET duplication réduites par le même
  changement). Solde restant (157) : détaillé en §4, laissé en l'état
  délibérément.

## 4. Dette restante (documentée, non traitée ce sprint)

Deux familles bien identifiées, jamais mélangées avec autre chose :

1. **Décalage de stubs Flet** (23 erreurs source + une bonne partie des
   157 en tests) — `main_view.py` (20), `gui/components/
   championship_selector.py` (2), `gui/views/about.py` (1), plus leur
   écho dans les tests qui construisent/inspectent ces mêmes contrôles
   Flet (`"Control" has no attribute "content"/"controls"/...`). Cause
   racine documentée depuis le Sprint 26 : le code a été écrit contre les
   stubs de types Flet 0.80, mais Flet 0.85.3 est réellement installé et
   son typage des callbacks (`on_click`, `on_change`) et de certains
   attributs de contrôle a changé. Runtime non affecté (Flet reste
   permissif à l'exécution, tous les tests passent) — c'est une dette de
   *vérification statique*, pas un bug. Non corrigée ce sprint : la
   corriger correctement demanderait soit de réécrire les signatures de
   callback dans tout `main_view.py` (risque réel de régression
   comportementale pour un gain de vérification statique uniquement, hors
   périmètre "aucun changement fonctionnel"), soit d'attendre une release
   Flet dont les stubs matchent enfin le runtime.
2. **Typage dynamique `unittest.mock`** — le solde des 157 erreurs tests
   restantes (`assert_awaited_once_with` sur un `Callable` typé,
   `arg-type` sur des `AsyncMock` substitués à une vraie factory
   typée...) est le bruit résiduel normal de tout projet Python testant
   abondamment via des doubles de test dynamiques, sans plugin mypy dédié
   (`pytest-mock` avec stubs génériques n'existe pas de façon fiable pour
   ce patron). Non traité au cas par cas (des dizaines de sites d'appel,
   aucun ne révèle une vraie erreur de test) — un `cast()` par site serait
   pur bruit syntaxique pour zéro gain de sécurité réelle.

Aucune des deux familles ne bloque quoi que ce soit : `ruff` est à 0,
les 1865 tests passent, la couverture est stable à 97 %.

## 5. Architecture — vérifications effectuées

- **Imports circulaires** : aucun, sur les 136 modules du paquet
  `motorsport_calendar` (détection par parcours de graphe AST, DFS sur
  chaque module).
- **Dépendances déclarées vs réellement utilisées** : les 9 dépendances
  runtime sont toutes consommées (voir §2) ; aucune à retirer.
- **Cohérence des services GUI** (`FavoritesService`, `NotificationService`,
  `SearchService`, `CircuitService`, `SeasonExplorer`) : tous suivent le
  même patron établi au Sprint 44 et jamais dévié depuis — aucun état
  Flet, reconstruits à la demande, persistance uniquement via
  `gui/preferences.py` (read-modify-write sur le fichier partagé). Aucune
  incohérence trouvée.
- **Tables `_CIRCUIT_DATA` dupliquées entre providers** (9 fichiers) —
  examinées et **volontairement non fusionnées** : chaque table utilise un
  espace de clés différent (slug propre à chaque source de données), et
  cette non-exhaustivité par convention est déjà documentée dans
  `docs/AI_CONTEXT.md` pour chacune. Une fusion introduirait un couplage
  artificiel entre des providers qui n'ont aucune raison structurelle de
  partager une table, pour un gain de lignes cosmétique — écarté.
- **`config/service.py::ConfigService._DEFAULT_PATHS`** — la première
  entrée (`Path("config.yaml")`, relative au CWD) confirmée intentionnelle
  (voir ADR-040, Sprint 49), non une régression de ce sprint.

## 6. Fonctions et classes les plus volumineuses

| Lignes | Emplacement | Nature |
|---|---|---|
| **771** | `gui/main_view.py::build_main_view` | **Recommandation prioritaire ci-dessous** |
| 322 | `providers/sro_series/timetable_base.py::SroTimetableSource` | Classe de base partagée (4 championnats GT), volumineuse par nature (pipeline HTTP + cache + parsing complet) |
| 259 | `providers/motogp_series/pulselive_base.py::PulseliveGpSource` | Idem, 4 championnats moto |
| 254 | `providers/aco_series/sports_event_base.py::AcoSportsEventSource` | Idem, 3 championnats endurance ACO |
| 119 | `cli.py::generate` | Déjà factorisé au maximum raisonnable (délègue à `_fetch_one`/`_fetch_all`) |
| 110 | `cli.py::_run_generate_command` | Corps partagé des 17 commandes `generate-*` (Sprint 34) |

**`build_main_view` (771 lignes, 89 % du fichier `main_view.py`) est la
seule vraie anomalie de taille du projet.** Elle construit la totalité du
shell applicatif (navigation, chargement des 3 vues principales, 3 boîtes
de dialogue, gestion du redimensionnement) en une seule fonction. Ce
sprint ne la découpe **pas** : le brief interdit tout changement
fonctionnel, et une extraction sûre de closures qui capturent beaucoup
d'état partagé (page, contrôles de navigation, tâches asyncio en cours)
demande une analyse au cas par cas qui dépasse le format "consolidation
sans risque" de ce sprint. Recommandation documentée dans
`docs/TODO.md` pour un futur sprint dédié : extraire chaque
`_show_*_dialog` (déjà des fonctions imbriquées bien délimitées, ~55-86
lignes chacune) et le câblage de navigation vers des fonctions
module-level dans `main_view.py`, à l'image de ce qui a déjà été fait pour
`views/about.py`/`views/calendar.py`/`views/search.py`.

Les trois classes de base partagées (`SroTimetableSource`,
`PulseliveGpSource`, `AcoSportsEventSource`) sont volumineuses mais
**par conception assumée** : chacune encapsule tout le pipeline HTTP +
cache + parsing pour 3-4 championnats qui en héritent, exactement le
contraire de la duplication — ne pas les découper artificiellement.

## 7. Services les plus critiques

Par ordre d'impact utilisateur si une régression s'y introduisait :

1. **`exporters/ics.py::IcsExporter`** — le seul point de sortie réel du
   produit (tout export ICS, CLI et GUI, passe par là). Toute la couverture
   du projet en dépend indirectement (chaque test `generate-*` valide via
   le contenu du fichier produit). 12 classes de tests dédiées.
2. **`cache/http_cache.py::HttpCache`** — partagé par 15 des 17
   providers (tous sauf IMSA/WorldSBK, toujours des stubs) ; une
   régression silencieuse ici corromprait des données pour l'ensemble
   du calendrier sans qu'aucun message d'erreur n'apparaisse. Corrigé ce
   sprint pour son chemin par défaut (Sprint 49) ; 100 % typé désormais
   (0 erreur mypy).
3. **`core/registry.py`/`core/source_registry.py`** — point d'entrée
   unique de toute résolution provider/source ; une régression ici casse
   silencieusement N championnats à la fois plutôt qu'un seul. Aucun
   import circulaire, 0 erreur mypy, bien couvert.
4. **`gui/controller.py`** — unique frontière entre la GUI Flet (aucune
   logique métier) et le reste de l'architecture ; centralise
   `list_championships`/`generate_calendar`/`get_calendar_year_events`/
   `get_upcoming_weekend`/`get_dashboard_data`. Optimisé ce sprint
   (fetch concurrent, voir §8).
5. **`gui/preferences.py`** — fichier de persistance partagé par 5
   services GUI (favoris, notifications, sélection de calendrier...) ;
   une régression ici affecterait silencieusement tous les autres.

## 8. Performance — optimisations réalisées et reportées

### Réalisée : fetch concurrent des providers

**Constat** : `cli.py::generate` et `gui/controller.py::generate_calendar`
(l'agrégateur qui interroge tous les championnats activés pour produire
un seul fichier ICS) attendaient chaque provider **séquentiellement**
(`for cid, prov in provider_list: await prov.fetch_events(...)`) alors que
chaque provider interroge une API distante totalement indépendante des
16 autres — un cas d'école pour la concurrence asyncio.

**Mesure avant optimisation** (benchmark synthétique, 10 providers
simulés à latence égale) : séquentiel 1.006 s, concurrent 0.101 s — facteur
**~10x**. Sur le vrai code, un test de non-régression a été écrit pour
chacune des deux fonctions (`TestGenerateConcurrency` dans
`test_cli_generate.py`, `TestGenerateCalendarConcurrency` dans
`test_gui_controller.py`) : il mocke plusieurs providers avec un délai
artificiel identique et vérifie que leurs appels démarrent tous dans la
même fenêtre de temps (preuve de concurrence réelle, pas seulement un
budget de temps total qui serait pollué par le coût fixe et sans rapport
de `registry.discover()`). **Les deux tests ont été vérifiés pour échouer
contre l'ancienne implémentation séquentielle** (spread mesuré de 0.66 s
et 0.15 s respectivement, largement au-dessus du seuil) avant d'être
validés contre la nouvelle — pas un test qui passerait de toute façon.

**Fix** : extraction du corps de la boucle en une coroutine `_fetch_one`
par provider (gestion d'erreur par provider inchangée à l'identique),
puis `asyncio.gather(*(_fetch_one(...) for ...))` au lieu du for/await.
`asyncio.gather` préserve l'ordre de la liste d'entrée dans son résultat
— le fichier ICS final, l'ordre des événements, et les résumés affichés
restent **strictement identiques** à avant, seul le temps d'exécution
change. Aucune donnée partagée entre providers à un niveau qui rendrait
l'exécution concurrente dangereuse (`HttpCache` partagé mais chaque
écriture cible un fichier distinct par clé URL+params ; chaque source a
son propre `httpx.AsyncClient`, conçu pour l'usage concurrent).

Impact utilisateur réel : `motocal generate` (tous providers activés) et
le bouton "Générer" de "Mon calendrier" (GUI) passent d'un temps
proportionnel au nombre de championnats sélectionnés à un temps proche du
provider le plus lent — significatif dès que plus de 2-3 championnats
sont sélectionnés simultanément.

### Reportées (identifiées, non réalisées — pas de gain mesurable garanti ou hors périmètre)

- **`build_main_view` (771 lignes)** — aucun problème de performance
  identifié (c'est une fonction de construction d'UI exécutée une fois au
  démarrage, pas une boucle chaude), le découpage recommandé en §6 est un
  sujet de lisibilité/maintenabilité, pas de performance.
- **Vérification de virtualisation des longues listes GUI** (ex.
  "Mon calendrier" avec 17 championnats × plusieurs dizaines d'événements
  chacun) — non mesurée ce sprint (nécessiterait un poste avec affichage
  réel, indisponible dans cet environnement, même limitation documentée
  depuis les premiers sprints GUI).
- **Réutilisation d'une seule instance `httpx.AsyncClient` entre
  providers** plutôt qu'une par source — actuellement chaque source crée
  son propre client HTTP ; les regrouper économiserait la mise en place de
  connexions TCP/TLS redondantes vers des hôtes potentiellement partagés.
  Non mesuré (nécessiterait des appels réseau réels pour un résultat
  significatif, hors du périmètre "sans dépendre du réseau" de la suite de
  tests) — piste documentée dans `docs/TODO.md` pour un futur sprint avec
  mesure en conditions réelles.

## 9. Recommandations pour les prochains sprints

Par ordre de priorité décroissante (voir aussi `docs/TODO.md`, section
dédiée à ce sprint, pour le détail actionnable) :

1. **Découpage de `build_main_view`** (§6) — le seul vrai point de dette
   structurelle du projet ; à traiter dans un sprint dédié avec
   vérification visuelle réelle (poste avec affichage), pas en aveugle.
2. **Terminer le packaging Sprint 49** — build Linux bloqué sur
   l'outillage système, build Windows jamais exécuté (voir
   `docs/PACKAGING.md`) ; sans rapport avec cet audit mais toujours ouvert.
3. **IMSA/WorldSBK** — toujours des stubs après trois cycles
   d'investigation (Sprints 36/38/48) ; aucune piste nouvelle identifiée
   pendant cet audit.
4. **Réévaluer la dette Flet stub-version** (§4) si/quand une version de
   Flet dont les stubs matchent le runtime 0.85+ devient disponible —
   pourrait faire tomber les 23 + une bonne part des 157 erreurs mypy
   restantes d'un coup, sans toucher une ligne de code applicatif.
5. **Mesurer la virtualisation des listes GUI et la mutualisation des
   clients HTTP** (§8) une fois un poste de test avec affichage/réseau
   réel disponible.

---

*Document généré lors du Sprint 50 (Audit & Consolidation). À ne pas
confondre avec `docs/AI_CONTEXT.md` (état courant du projet, mis à jour
à chaque sprint) — celui-ci est un instantané d'audit, à ré-auditer
plutôt qu'à maintenir en continu.*
