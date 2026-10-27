# TODO.md

> Légende priorité : 🔴 HAUTE — 🟡 MOYENNE — 🟢 BASSE
> Légende état : `[ ]` à faire — `[~]` en cours — `[x]` terminé

---

## Providers WEC

- [x] 🔴 `OfficialWecSource` — implémenter `get_season()` via fiawec.com — **terminé Sprint 48** :
  fiawec.com confirmé sur le même CMS ACO qu'ELMS/MLMC, `OfficialWecSource(AcoSportsEventSource,
  WecSource)`. Voir ADR-039.

- [x] 🔴 CLI `generate-wec YEAR OUTPUT.ics` — déjà présente depuis Sprint 34 (mirroring
  `generate-f1`), fonctionnelle pour de vrai depuis que `OfficialWecSource` est implémentée
  (Sprint 48)

- [x] 🔴 CLI `generate YEAR OUTPUT.ics` — merge F1 + WEC dans un seul ICS — terminé Sprint 12

---

## Providers F1

- [ ] 🔴 `ErgastSource` — implémenter `get_season()` via API Ergast (données historiques 1950+)
  - Dépend de : rien
  - Estimation : 3-4h (mapping + tests)
  - Note : API Ergast v1, endpoint `/api/f1/{year}/races.json`

- [ ] 🔴 `CachedFormula1Source` — implémenter le cache fichier (JSON local)
  - Dépend de : aucune source spécifique
  - Estimation : 2h
  - Note : invalider le cache après 24h, chemin configurable

- [ ] 🟡 `OfficialFormula1Source` — récupérer depuis l'API officielle formula1.com
  - Dépend de : investigation endpoint (non documenté)
  - Estimation : 4-6h

---

## CLI

- [x] 🔴 CLI `generate-wec YEAR OUTPUT.ics` — terminé, 16 tests (+ NotImplementedError géré gracieusement)

- [x] 🔴 CLI `generate YEAR OUTPUT.ics` — terminé Sprint 12, 17 tests, résilience partielle intégrée

- [x] 🔴 Commande `export` — MC-002 (P0-3) : retirée plutôt qu'implémentée. Un stub
  qui échoue toujours était un vrai P0 bloquant (commande publique, documentée,
  ne pouvant jamais réussir) — `generate`/`generate-*` couvrent déjà tout le
  besoin réel ; réintroduire `export` un jour exigerait de redéfinir son
  périmètre (format/portée différents de `generate`), pas juste de remplir ce
  stub.

- [x] 🟡 Commande `providers` — liste les providers enregistrés via registry.list_all()
  - Terminé Sprint 9

- [ ] 🟡 Option `--year` avec validation (≥ 1950 pour Ergast, ≥ 2023 pour OpenF1)
  - Estimation : 30min

---

## Qualité des VEVENTs ICS

- [ ] 🟡 Ajouter `DESCRIPTION` dans chaque VEVENT (infos weekend, circuit, pays)
  - Dépend de : IcsExporter (ne pas modifier les modèles)
  - Estimation : 1h + tests

- [ ] 🟡 Ajouter `URL` dans chaque VEVENT (lien OpenF1 ou source officielle)
  - Estimation : 30min

- [ ] 🟢 Ajouter `CATEGORIES` (GP, Qualifying, Practice…)
  - Estimation : 30min

---

## Robustesse

- [ ] 🟡 Retry avec backoff exponentiel sur `httpx.TimeoutException`
  - Estimation : 1h
  - Note : max 3 tentatives, délais 1s / 2s / 4s

- [ ] 🟢 Validation de l'année dans `generate-f1` (ex: OpenF1 ne couvre que 2023+)
  - Estimation : 30min

---

## Infrastructure

- [ ] 🟡 Publier sur PyPI (configuration `hatchling` déjà en place)
  - Dépend de : v0.1.0 complète
  - Estimation : 1h

- [ ] 🟢 Documentation MkDocs
  - Estimation : 4h

- [ ] 🟢 Badge couverture dans README
  - Estimation : 30min

---

## Correction du packaging Flet — suites possibles (Sprint 59)

- [x] 🔴 ~~Corriger le blocage `ModuleNotFoundError` du build Linux~~ —
  **corrigé Sprint 59** : `motorsport_calendar/gui/pyproject.toml` +
  `tool.flet.dev_packages`, vérifié par un rebuild réel et 2 lancements
  du binaire (`docs/PACKAGING.md` §7).
- [x] 🟡 ~~Configurer l'identité de l'application dans le build~~ —
  **corrigé Sprint 59**, même manifeste : exécutable/ID d'application/
  titre de fenêtre natif passent de `gui`/`com.flet.gui` à
  `motorsport-calendar`/`com.flet.motorsport-calendar`.
- [x] 🔴 Retracer pourquoi la version embarquée du build reste `1.0.0` —
  **résolu, MC-002 (P0-5)**. Cause racine : `--build-name` stamp les
  métadonnées natives mais ne réécrit jamais le `pubspec.yaml` du
  scaffold Flutter, dont `data/flutter_assets/version.json` dépend
  directement. Fixé via `[tool.flet.flutter.pubspec]` dans
  `motorsport_calendar/gui/pyproject.toml`, gardé par un test. Ne
  s'applique que si le scaffold est régénéré — `docs/RELEASE.md` impose
  désormais de supprimer `build/` avant chaque release.
- [x] 🟡 Vérifier le correctif Sprint 59 sur le build Windows — **terminé
  Sprint RC-01** : construit et lancé pour de vrai sur une machine
  Windows 11, même manifeste/mécanisme confirmé fonctionnel. Deux
  blocages machine/toolchain (pas le code du projet) rencontrés et
  corrigés, voir `docs/PACKAGING.md` §8.
- [x] 🟡 Corriger la troncature du dropdown "Année par défaut" — **résolu,
  MC-002 (P0-8)**. C'était bien une largeur de `Dropdown` insuffisante :
  `width` élargi de 160 à 190 (`gui/main_view.py::
  _build_preferences_controls`), seul le libellé « Année en cours »
  (les autres options sont de simples années sur 4 chiffres) avait
  besoin de la place supplémentaire.
- [ ] 🟡 Vérification visuelle réelle du binaire Linux corrigé — le crash
  Python est résolu et vérifié (processus reste actif, aucune trace
  d'erreur), mais aucun rendu de fenêtre réel n'a pu être confirmé (pas
  de compositeur d'affichage dans cet environnement) ; à confirmer sur un
  poste avec affichage avant toute distribution publique. Le binaire
  Windows, lui, a été rendu et contrôlé visuellement pour de vrai (Sprint
  RC-01, `docs/PACKAGING.md` §8) — le code GUI étant partagé entre
  plateformes, ceci réduit le risque résiduel côté Linux sans
  complètement le lever.
- [ ] 🟢 Ajouter un fichier `.desktop` Linux pour une intégration menu
  Applications — non nécessaire pour une distribution en simple archive
  `.tar.gz`, attendu pour un futur `.deb`/AppImage/Flatpak.
- [ ] 🟢 Mettre en place un workflow GitHub Actions déclenché sur tag qui
  exécute automatiquement le build Linux + la suite de tests/ruff/mypy
  (voir `docs/RELEASE.md` §8) — retire le risque d'oubli d'une étape
  manuelle ; le build Windows nécessiterait un runner Windows séparé.
- [ ] 🟢 Ajouter la signature de code (Windows Authenticode, signature de
  paquet Linux) avant toute distribution publique large — acceptable de
  différer pour une Beta distribuée à une audience restreinte/de
  confiance.

---

## Préparation Beta : Nettoyage & Positionnement — suites possibles (Sprint 57)

- [ ] 🟡 Fournir de vrais liens PayPal/GitHub Sponsors dès qu'une décision
  produit est prise d'accepter des dons — remplacer les 2 `ComingSoonRow`
  de "Soutenir le projet" par de vrais boutons `make_url_opener`,
  exactement comme les boutons Discussions/Issues le sont déjà.
- [ ] 🟡 Réintégrer IMSA/WorldSBK dans le sélecteur GUI dès qu'une source
  fiable existe pour l'un des deux (voir ADR-027/ADR-029,
  `docs/DATA_SOURCES.md`) — il suffit de retirer l'id concerné de
  `controller.py::_HIDDEN_FROM_GUI`, aucun autre changement requis.
- [ ] 🟢 Vérification visuelle réelle d'"À propos"/"Soutenir le projet"
  sur un poste avec affichage — structure des contrôles + 19 tests nets
  vérifiés, aucun rendu pixel confirmé.
- [ ] 🟢 Envisager d'ajouter un lien vers "Soutenir le projet" depuis le
  Dashboard (aux côtés des "Accès rapides" du Sprint 53) une fois la page
  validée visuellement — non demandé par le brief Sprint 57, resterait
  une pure question de découvrabilité, pas de logique nouvelle.

---

## Notifications natives — suites possibles (Sprint 56)

- [ ] 🟡 Implémenter un vrai `SystemNotifier` dès qu'une solution native
  propre existe — Flet ajoute un service de notification officiel (à
  surveiller à chaque montée de version), ou décision délibérée d'ajouter
  une dépendance tierce (`plyer`/`winotify`/`notify-py`/D-Bus selon la
  plateforme) ; seul `get_system_notifier()` change, tout le reste de
  l'app (moteur, préférences, orchestration) reste inchangé par
  construction.
- [ ] 🟢 Réévaluer périodiquement les nouvelles versions de Flet — l'audit
  du Sprint 56 est un instantané de la version 0.85.3 installée, à
  revérifier avant toute Beta si une version majeure sort entretemps.
- [ ] 🟢 Envisager un affichage "notifications à venir" dans l'app
  elle-même (liste dans la page Préférences ou un futur panneau dédié)
  comme solution intermédiaire tant qu'aucune notification système réelle
  n'est possible — non demandé par le brief Sprint 56, resterait une
  vraie fonctionnalité de consultation, pas une notification système.

---

## Recherche interactive — suites possibles (Sprint 55)

- [ ] 🟢 Vérification visuelle réelle des 3 nouveaux types de clic (résultat
  championnat/événement/circuit) sur un poste avec affichage — structure
  des contrôles + 10 tests nets vérifiés, aucun clic/rendu pixel confirmé.
- [ ] 🟢 Envisager un raccourci clavier/Entrée pour ouvrir le premier
  résultat sans clic souris — non nécessaire aujourd'hui, aucune demande
  d'accessibilité clavier n'a été formulée pour cette page ni pour aucune
  autre du projet.
- [ ] 🟢 Envisager de surligner/indiquer visuellement qu'une carte de
  résultat est cliquable (curseur, léger effet au survol) — Flet propose
  peu de contrôle sur le curseur de survol pour un `ft.Container`, non
  exploré ce sprint, cohérent avec le choix déjà fait pour le lien circuit
  de la fiche événement (Sprint 47, jamais eu d'indication visuelle
  dédiée non plus).

---

## Préparation Beta (Recette UX) — suites possibles (Sprint 54)

- [ ] 🟢 Vérification visuelle réelle des corrections de ce sprint sur un
  poste avec affichage — icônes d'en-tête, boîte de dialogue de succès,
  espacements, aucun rendu pixel confirmé (même limitation que chaque
  sprint GUI précédent).
- [ ] 🟢 Étendre l'audit UX à un second passage une fois un poste avec
  affichage disponible — cette recette a porté sur la structure/cohérence
  du code (icônes, espacements, textes), jamais sur un rendu réel ; un
  passage visuel pourrait révéler des points invisibles à la seule lecture
  du code (alignement, densité, contraste réel).

---

## Nouveautés & Centre d'accueil — suites possibles (Sprint 53)

- [ ] 🟢 Vérification visuelle réelle des 3 nouvelles sections du Dashboard sur
  un poste avec affichage — structure des contrôles + 29 tests nets vérifiés,
  aucun rendu pixel confirmé (carte "Nouveautés", 4 cartes "Accès rapides", 4
  cartes "État").
- [ ] 🟡 Publier un vrai manifeste de mise à jour (`config.update.manifest_url`)
  — la carte "Nouveautés" est fonctionnelle et testée mais reste un no-op
  silencieux tant qu'aucune URL réelle n'est configurée ; ce manque se voit
  maintenant à deux endroits (boîte de dialogue de démarrage + carte
  Dashboard) au lieu d'un seul.
- [ ] 🟢 Envisager un lien "voir toutes les nouveautés" (changelog complet) si
  un jour plusieurs versions sont publiées entre deux lancements de l'app —
  non nécessaire aujourd'hui, `UpdateService` ne compare qu'à la dernière
  version connue du manifeste.

---

## Préférences avancées — suites possibles (Sprint 52)

- [ ] 🟡 Implémenter réellement Thème/Langue/Format horaire — `PreferencesModel`
  porte déjà le typage (`theme`/`language`/`time_format`) mais rien n'est
  persisté ni lu ailleurs dans l'app ; volontairement laissé en "Disponible
  prochainement" ce sprint (brief : "préparer, sans forcément implémenter").
  - Thème : `page.theme_mode` est actuellement câblé en dur sur
    `ft.ThemeMode.DARK` dans `main_view.py` — un futur sprint devra le lire
    depuis la préférence à la place.
  - Langue : `strings.py::Strings.from_dict` existe déjà depuis les tout
    premiers sprints, jamais appelé — la mécanique i18n est prête, seul le
    chargement/la persistance manquent.
  - Format horaire : aucune vue ne formate actuellement une heure
    conditionnellement à ce réglage.
- [ ] 🟢 Vérification visuelle réelle de la page Préférences sur un poste avec
  affichage — structure des contrôles + 9 tests nets vérifiés, aucun rendu
  pixel confirmé ; premier usage de `ft.Switch`/`ft.Dropdown` dans ce projet.
- [ ] 🟢 Envisager une validation des bornes pour une valeur de préférence hors
  des options proposées par l'UI (ex. `ics_alarm_minutes` corrompu à une
  valeur non listée) — non nécessaire aujourd'hui, ces 3 clés ne peuvent
  être écrites que via les Dropdowns de la page elle-même.

---

## Vérification des mises à jour — suites possibles (Sprint 51)

- [ ] 🔴 Publier un manifeste `manifest.json` réel et référencer son URL dans
  `config.yaml` (`update.manifest_url`) — sans ça, la fonctionnalité reste un
  no-op silencieux en usage réel bien qu'entièrement fonctionnelle et testée.
  N'importe quel hébergement statique convient (`update_service.py` n'a
  aucune connaissance de GitHub ni d'aucune plateforme particulière).
  - Estimation : 30min (juste l'hébergement + la ligne de config, aucun code
    à écrire)
- [ ] 🟢 UI de préférence pour `update_check_enabled` — la préférence existe
  et est lue (`gui/controller.py::check_for_update`) mais aucune page ne la
  bascule encore ; à câbler le jour où la page Préférences (toujours un
  placeholder) devient réelle, même statut que les préférences de
  notifications (Sprint 46).
- [ ] 🟢 Vérification visuelle réelle de la boîte de dialogue "nouvelle
  version disponible" sur un poste avec affichage — structure des contrôles
  + 58 tests vérifiés, aucun rendu pixel confirmé (même limitation que
  chaque sprint GUI précédent).
- [ ] 🟢 Envisager un cache/throttle sur la vérification (ex. une fois par
  jour maximum, pas à chaque lancement) si un manifeste réel révèle que
  les lancements fréquents génèrent un trafic non négligeable — non
  nécessaire tant qu'aucun manifeste n'est publié.

---

## Audit & Consolidation — suites possibles (Sprint 50)

- [ ] 🟡 Découper `gui/main_view.py::build_main_view` (771 lignes, 89 % du fichier) —
  seule vraie anomalie de taille du projet identifiée par l'audit (`docs/AUDIT.md`
  §6). Piste : extraire chaque `_show_*_dialog` (déjà des fonctions imbriquées bien
  délimitées, ~55-86 lignes chacune) et le câblage de navigation vers des fonctions
  module-level, à l'image de `views/about.py`/`calendar.py`/`search.py`. Nécessite
  une vérification visuelle réelle (poste avec affichage) avant/après, pas un
  découpage à l'aveugle — sprint dédié.
- [ ] 🟢 Réévaluer la dette mypy Flet stub-version (23 erreurs `motorsport_calendar/`
  + une bonne part des 157 erreurs `tests/`, `docs/AUDIT.md` §4) si/quand une version
  de Flet aligne enfin ses stubs de types sur le runtime 0.85+ — pourrait faire
  tomber ce solde d'un coup sans toucher une ligne de code applicatif.
- [ ] 🟢 Mesurer la mutualisation des clients HTTP entre providers (une instance
  `httpx.AsyncClient` partagée plutôt qu'une par source) une fois un environnement
  avec accès réseau réel disponible pour le benchmark — piste identifiée mais non
  mesurée (`docs/AUDIT.md` §8).
- [ ] 🟢 Mesurer la virtualisation des longues listes GUI (ex. "Mon calendrier" avec
  17 championnats sélectionnés) une fois un poste avec affichage réel disponible —
  même limitation que chaque sprint GUI précédent (`docs/AUDIT.md` §8).
- [ ] 🟢 Décider du sort de `core/service.py::CalendarService` — bug corrigé Sprint
  50 mais la classe reste sans aucun appelant réel (ni CLI, ni GUI). Soit la câbler
  un jour derrière une future API programmatique, soit la retirer si elle reste
  orpheline après plusieurs sprints supplémentaires.

---

## Packaging Alpha — suites possibles (Sprint 49)

- [ ] 🟡 Terminer le build Linux — `flet build linux motorsport_calendar/gui
  --module-name app` atteint l'étape de compilation native mais reste bloqué par
  l'outillage système manquant (`binutils clang cmake llvm lld ninja-build pkg-config
  libgtk-3-dev libunwind-dev`, liste complète officielle Flet, voir `docs/PACKAGING.md`
  §2). Une fois installé, relancer la même commande (SDK Flutter déjà en cache) et
  exécuter la checklist de validation complète du brief (démarre, charge les assets,
  ouvre toutes les pages, lit/écrit les préférences, crée le cache, génère un ICS,
  fonctionne sans le dépôt Git) contre le binaire réellement compilé.
- [x] 🟡 Exécuter le build Windows — **terminé Sprint RC-01**, exécuté et
  validé pour de vrai sur une machine Windows 11 (voir
  `docs/PACKAGING.md` §8 pour la procédure complète et les deux
  blocages machine/toolchain rencontrés et corrigés).
- [ ] 🟢 Câbler `theme.logo_placeholder()` sur les vraies images Brand Set v1.0
  (`gui/assets/logo/mc-icon.svg`, `logo-horizontal.svg`, `logo-vertical.svg`, livrées
  Sprint 49 mais volontairement non consommées par les vues — remplacer des
  placeholders visuels par de vraies images est un chantier de Design System,
  explicitement hors périmètre du brief Sprint 49).
- [ ] 🟢 CI/CD build automation — automatiser `flet build linux`/`flet build windows`
  dans GitHub Actions une fois les deux builds validés manuellement au moins une fois ;
  explicitement hors périmètre Sprint 49 (procédure manuelle uniquement).
- [ ] 🟢 Installeur/auto-update — explicitement hors périmètre du brief Sprint 49
  ("aucune installation automatique", "aucun auto-update") ; `flet build` produit un
  dossier/exécutable brut, à copier/lancer manuellement.

---

## Finalisation des providers — suites possibles (Sprint 48)

- [ ] 🔴 Trouver une source IMSA exploitable — imsa.com bloque désormais jusqu'à son
  propre `robots.txt` (Cloudflare), Al Kamel reste une archive post-course, Wikipedia
  n'a pas d'heures de session. Pistes non explorées : automatisation navigateur
  (Playwright), contact direct IMSA pour un accès API partenaire. Voir
  `docs/DATA_SOURCES.md` et ADR-027/ADR-039.
- [ ] 🔴 Trouver une source WorldSBK exploitable — deux nouveaux hôtes Pulselive
  découverts au Sprint 48 (`api.wsbk.pulselive.com`, `wsbk.pulselive.com`), aucun
  n'expose d'endpoint événements exploitable. Pistes non explorées : automatisation
  navigateur, contact direct Dorna/WorldSBK. Voir `docs/DATA_SOURCES.md` et
  ADR-029/ADR-039.
- [ ] 🟢 Compléter `WEC_CIRCUIT_DATA`/`WEC_ADDRESS_COUNTRY_CODES`
  (`providers/wec/circuit_data.py`) au fil des nouveaux circuits WEC rencontrés (ex.
  Silverstone, déjà au calendrier 2027 mais pas encore dans la table) — même pattern
  que les autres tables `_CIRCUIT_DATA` du projet, non exhaustif par convention.
- [ ] 🟢 Surveiller les futurs noms de course WEC ne correspondant ni au motif "X
  Hours" ni à `_NAMED_RACE_DURATION_HOURS` (`providers/wec/sources/official.py`) —
  repli générique à 6h actuellement, correct pour la saison 2026.
- [ ] 🟢 Vérification visuelle réelle de WEC dans "Ce week-end"/Dashboard sur un poste
  avec affichage (pipeline entièrement revérifié en direct sans mock côté données,
  aucun rendu pixel confirmé — même limitation que chaque sprint GUI précédent).

---

## Circuit Explorer — suites possibles (Sprint 47)

- [ ] 🟡 Page "Circuits" dédiée — lister `CircuitService.list_circuits()` dans son
  ensemble (même patron Layout System que "Recherche", Sprint 45), avec une destination
  de navigation propre. Aujourd'hui la fiche Circuit ne s'ouvre que depuis un clic dans
  la fiche événement.
- [ ] 🟢 Rendre l'historique des événements de la fiche Circuit cliquable — chaque
  `CircuitEventEntry` porte déjà `championship_id`/`event_uid`, jamais interprétés à ce
  jour ; cliquer une ligne ouvrirait la fiche événement correspondante (même patron que
  `SeasonEventRow`, Sprint 42).
- [ ] 🟢 Vérification visuelle réelle de la fiche Circuit et du nom de circuit cliquable
  sur un poste avec affichage (structure des contrôles + 35 tests vérifiés, dont un
  smoke test de bout en bout en direct sans mock — clic réel simulé sur un événement
  réel jusqu'à la fiche Circuit résolue — aucun rendu pixel confirmé).

---

## Moteur de notifications — suites possibles (Sprint 46)

- [ ] 🟡 Câbler `NotificationService` dans l'interface — page dédiée listant les
  prochaines échéances (même patron Layout System que "Recherche", Sprint 45) et/ou
  destination de navigation. Hors périmètre du Sprint 46, qui ne demandait que les
  fondations du moteur.
- [ ] 🟡 Notification système réelle par plateforme (Windows/Linux/macOS), consommant
  `NotificationService.compute_notifications()` tel quel — le moteur a été conçu pour ça
  ("sans modification"), mais aucune implémentation plateforme n'existe encore.
- [ ] 🟢 Persister `kinds` (quels types de notification sont activés) comme préférence,
  au même titre que `notifications_default_lead_time_minutes` — aujourd'hui un paramètre
  d'appel uniquement.
- [ ] 🟢 Persister plusieurs délais simultanés plutôt qu'un seul "délai par défaut" — le
  moteur (`compute_notifications(lead_times=...)`) le supporte déjà, seule la préférence
  persistée est actuellement singulière, conforme au brief ("délai par défaut").
- [ ] 🟢 Distinguer réellement "début du week-end" de "première session" si un jour la
  donnée le permet (aujourd'hui les deux s'ancrent sur la même session la plus précoce
  d'un événement, faute d'une notion de "début de week-end" dans le modèle de domaine —
  voir ADR-037) — piste pour un futur sprint, pas un bug.

---

## Recherche globale — suites possibles (Sprint 45)

- [ ] 🟡 Vérification visuelle réelle de "Recherche" sur un poste avec affichage
  (structure des contrôles + 46 tests vérifiés, dont un smoke test en direct sans mock
  contre chaque exemple explicite du brief : spa/Spa/SPA/spa francorchamps, Le
  Mans/lemans, Moto/MotoGP, Formula, GT — aucun rendu pixel confirmé). Attention
  particulière : la recherche instantanée à chaque frappe reste-t-elle fluide
  visuellement, et le `TextField` conserve-t-il le focus clavier après chaque
  `page.update()` ?
- [ ] 🟢 Clic sur un résultat de recherche ouvrant directement la fiche événement
  (Sprint 42) ou la page du championnat correspondant — piste pour un futur sprint, pas
  demandée ce sprint (résultats en lecture seule).
- [ ] 🟢 Historique des dernières recherches — piste pour un futur sprint.
- [ ] 🟢 Élargir la portée de la recherche au-delà de l'année actuellement parcourue sur
  "Mon calendrier" (aujourd'hui volontairement limité à `year_events`, cohérent avec
  "aucun appel réseau supplémentaire") — piste pour un futur sprint si le besoin
  apparaît.

---

## Favoris intelligents — suites possibles (Sprint 44)

- [ ] 🟡 Vérification visuelle réelle de "Mes favoris" sur un poste avec affichage
  (structure des contrôles + 36 tests vérifiés, aucun rendu pixel confirmé). Attention
  particulière au sous-titre "N favoris" du `PageHeader` (accord singulier/pluriel à 0,
  1, et plusieurs favoris).
- [ ] 🟢 Brancher `PreferencesModel.favorite_championships` sur `FavoritesService` le
  jour où la page Préférences (toujours un placeholder) devient réelle — piste pour un
  futur sprint, hors périmètre du Sprint 44.
- [ ] 🟢 Export ICS dédié "mes favoris uniquement" en un clic depuis le Dashboard —
  piste pour un futur sprint, pas demandée ce sprint.
- [ ] 🟢 Notification/rappel pour les championnats favoris (prochain départ favori,
  etc.) — piste pour un futur sprint.
- [ ] 🟢 Repli local (sans nouveau fetch réseau) du tri "favoris en premier" sur
  Dashboard/Ce week-end déjà chargés, au lieu du re-fetch actuel (cache HTTP existant
  absorbe déjà le coût réseau réel, mais un tri purement local serait plus rapide) —
  optimisation, pas un bug.

---

## Refonte UX de "Mon calendrier" — suites possibles (Sprint 43)

- [ ] 🟡 Vérification visuelle réelle de la page réorganisée sur un poste avec affichage
  (structure des contrôles Flet + ~65 tests vérifiés, aucun rendu pixel confirmé — le
  sprint le plus visuellement significatif à ce jour). Attention particulière : le pied
  de page fixe (destination + "Créer") reste-t-il visible sans scroll même sur la plus
  petite fenêtre supportée (`min_height=580`) ? Les accordéons s'animent-ils
  correctement ? Le style "sélectionné" d'un bouton championnat est-il assez lisible ?
- [ ] 🟢 Mémoriser l'état ouvert/fermé des accordéons dans les préférences utilisateur
  (aujourd'hui remis à zéro à chaque lancement, sauf la catégorie de la présélection) —
  piste pour un futur sprint, pas demandée ce sprint.
- [ ] 🟢 Badge indiquant le nombre de championnats sélectionnés directement sur le titre
  de chaque accordéon (ex. "🏎 Formula (2)") — piste pour un futur sprint.
- [ ] 🟢 Réduire la largeur/densité du pied de page fixe sur petite fenêtre — piste pour
  un futur sprint, pas demandée ce sprint.

---

## Fiche événement — suites possibles (Sprint 42)

- [ ] 🟡 Vérification visuelle réelle de la fiche événement (boîte de dialogue) sur un
  poste avec affichage (structure des contrôles Flet + 20 tests vérifiés, rendu pixel non
  confirmé — attention particulière au scroll interne sur un événement à beaucoup de
  sessions, ex. week-end MotoGP à 6 sessions).
- [ ] 🟢 Action "Exporter cet événement seul" en ICS depuis la fiche — non nécessaire
  pour cette première version, volontairement gardée simple (exactement les champs
  demandés par le brief : championnat, nom, circuit, pays, date, sessions).
- [ ] 🟢 Lien retour depuis la fiche vers "Ce week-end" quand l'événement affiché est
  celui du week-end en cours — piste pour un futur sprint, pas demandée ce sprint.
- [ ] 🟢 Favoris par événement (distinct des favoris par championnat déjà anticipés
  dans `docs/TODO.md`) — piste pour un futur sprint.

---

## Explorer une saison — suites possibles (Sprint 41)

- [ ] 🟡 Vérification visuelle réelle de l'explorateur de saison sur un poste avec
  affichage (structure des contrôles Flet + 23 tests vérifiés, rendu pixel non confirmé
  — attention particulière à une sélection large : 17 championnats × plusieurs
  événements chacun, jamais rendu réellement dans un navigateur avant ce sprint).
- [x] 🟢 Lien direct entre une ligne d'événement et `ChampionshipCard` (voir le détail
  des sessions) — terminé Sprint 42 (`gui/event_details.py` + boîte de dialogue).
- [ ] 🟢 Filtre texte/recherche dans la liste d'événements, ou repli automatique des
  mois déjà passés — pistes pour un futur sprint, pas demandées ce sprint.
- [ ] 🟢 Persister `year_events` d'une année à l'autre dans la session GUI (déjà noté
  comme piste pour le résumé de sélection, Sprint 40) bénéficierait aussi à
  l'explorateur de saison, puisqu'il consomme la même donnée.

---

## Calendrier interactif — suites possibles (Sprint 40)

- [ ] 🟡 Vérification visuelle réelle du résumé de sélection sur un poste avec affichage
  (structure des contrôles Flet + 25 tests vérifiés, rendu pixel non confirmé — même
  limitation que chaque sprint GUI précédent).
- [ ] 🟢 Répartition du résumé par championnat (ex. "Formula 1 : 26 événements, MotoGP :
  22 événements") en plus des totaux agrégés — non nécessaire pour cette première
  version, volontairement gardée simple (comptages + période, rien de plus).
- [ ] 🟢 Fusionner visuellement le résumé persistant et le récapitulatif de l'étape 4
  (aujourd'hui deux blocs Flet distincts, juxtaposés) si la redondance devient gênante à
  l'usage réel.
- [ ] 🟢 Cache en mémoire de `year_events` par année déjà visitée dans la session
  (aujourd'hui un aller-retour entre deux années déjà vues redéclenche un fetch complet,
  simplement absorbé par le TTL HttpCache existant) — optimisation, pas un bug.

---

## Dashboard Motorsport — suites possibles (Sprint 39)

- [ ] 🟡 Vérification visuelle réelle du Dashboard sur un poste avec affichage (structure
  des contrôles Flet vérifiée par tests, rendu pixel non confirmé — même limitation que
  chaque sprint GUI précédent).
- [ ] 🟢 Rendre les stat cards cliquables (ex. cliquer "Prochain week-end" bascule vers
  l'onglet "Ce week-end") — non nécessaire pour cette première version, volontairement
  gardée simple.
- [ ] 🟢 Mini-historique des derniers événements passés, ou raccourci vers "Mon
  calendrier" pré-rempli avec les championnats du prochain week-end — pistes pour un
  futur sprint "valeur", pas demandées ce sprint.
- [ ] 🟢 Une fois des logos de championnat livrés : les stat cards et puces du Dashboard
  n'en affichent aucun aujourd'hui (contrairement à `ChampionshipCard`) — décision
  délibérée pour rester glaçable/compact, à revisiter si souhaité.

---

## Motorcycle Racing — suites possibles (Sprint 38)

- [ ] 🔴 `OfficialWorldSbkSource` — trouver une source exploitable pour `get_season()`.
  Aucune n'a été identifiée au Sprint 38 malgré une investigation approfondie (voir
  `docs/DATA_SOURCES.md` section WorldSBK et ADR-029) : calendrier worldsbk.com
  entièrement rendu côté client, hôte API candidat (`wsbk-api-origin.gplat-test.
  pulselive.com`) injoignable depuis l'extérieur. Pistes à explorer : automatisation
  navigateur (Playwright — coût de dépendance à évaluer), contact direct Dorna/WorldSBK
  pour un accès partenaire, ou surveiller une éventuelle publication future d'un hôte API
  public équivalent à `api.pulselive.motogp.com`. Depuis le Sprint 57, WorldSBK (comme
  IMSA) est masquée des sélecteurs de la GUI (`_HIDDEN_FROM_GUI`) en attendant une vraie
  source — n'apparaît donc plus nulle part côté app tant que ce point reste ouvert.
- [ ] 🟢 Vérification visuelle réelle de "Mon calendrier"/"Ce week-end" avec
  MotoGP/Moto2/Moto3 affichés, sur un poste avec affichage.
- [ ] 🟢 Une fois `OfficialWorldSbkSource` implémentée : ajouter `worldsbk` (et
  `motogp`/`moto2`/`moto3` si des logos sont fournis) à
  `championship_assets.py::_LOGO_FILENAMES`.
- [ ] 🟡 Vérifier si `PulseliveGpSource.get_season(year)` fonctionne pour une saison
  passée (non testé au Sprint 38, hors périmètre demandé) — probable mais à confirmer
  avant de s'appuyer dessus pour un archivage historique.

---

## GT Racing — suites possibles (Sprint 37)

- [ ] 🟢 Compléter `providers/sro_series/circuit_data.py` au fil des nouveaux circuits GT
  rencontrés sans mapping (nom propre + fuseau IANA) — repli actuel propre
  (`feature__heading` + `"UTC"`), juste incomplet pour l'instant.
- [ ] 🟢 Vérifier périodiquement si un round initialement ignoré (timetable non publié au
  Sprint 37, ex. Indianapolis 8 Hour GT World Challenge America 2026) apparaît une fois
  SRO publie ses horaires — aucun changement de code nécessaire, `get_season()` l'inclura
  automatiquement.
- [ ] 🟡 Vérifier `AcoSportsEventSource`-style : `SroTimetableSource.get_season(year)`
  fonctionne-t-il pour une saison passée, ou uniquement pour la saison publiée courante
  comme ACO ? Non testé au Sprint 37 (hors périmètre demandé).
- [ ] 🟢 Ajouter `gtwc-europe`/`gtwc-america`/`gtwc-asia`/`igtc` à
  `championship_assets.py::_LOGO_FILENAMES` le jour où des logos sont prévus
  (volontairement absent ce sprint — "aucun travail sur les icônes").
- [ ] 🟢 Vérification visuelle réelle de "Mon calendrier"/"Ce week-end" avec les 4 nouveaux
  championnats GT affichés, sur un poste avec affichage.
- [ ] 🟡 Autres championnats GT candidats (SRO organise aussi le British GT Championship,
  l'Italian GT Championship, etc., probablement sur le même CMS `/event/{id}/{slug}`) —
  suivre exactement le patron de ce sprint : vérifier le vrai schéma HTML avant d'écrire
  quoi que ce soit, ne jamais supposer.

---

## Extension IMSA — suites possibles (Sprint 36)

- [ ] 🔴 `OfficialImsaSource` — trouver une source exploitable pour `get_season()`. Aucune
  n'a été identifiée au Sprint 36 malgré une investigation exhaustive (voir
  `docs/DATA_SOURCES.md` section IMSA et ADR-027) : imsa.com bloqué par Cloudflare (403 sur
  toutes les routes testées), Al Kamel Systems = archive de résultats post-course
  uniquement, Wikipedia = calendrier sans horaires de session, Sportscar365 = horaires en
  prose non structurée. Pistes à explorer : automatisation navigateur (Playwright — coût
  de dépendance à évaluer), contact direct IMSA/SRO pour un accès partenaire, ou surveiller
  une éventuelle publication future d'un flux structuré.
- [x] 🟢 Vérification visuelle de "Mon calendrier"/"Ce week-end" avec IMSA — **devenue sans
  objet Sprint 57** : IMSA (toujours un stub `NotImplementedError`) a été masquée des
  sélecteurs de la GUI (`_HIDDEN_FROM_GUI`, `gui/controller.py`) en attendant une vraie
  source, elle n'apparaît donc plus nulle part côté app.
- [ ] 🟢 Une fois `OfficialImsaSource` implémentée : ajouter `imsa` à
  `championship_assets.py::_LOGO_FILENAMES` si un logo officiel est fourni.

---

## Extension Endurance — suites possibles (Sprint 35)

- [x] 🔴 `OfficialWecSource` — **terminé Sprint 48** : fiawec.com confirmé sur le même
  schéma JSON-LD `SportsEvent`/`subEvent` qu'ELMS/MLMC, branché sur `AcoSportsEventSource`
  comme anticipé ici.
- [ ] 🟡 Porsche Supercup — probablement sur le dataset f1calendar (pas ACO) ; vérifier le
  vrai schéma JSON avant d'écrire quoi que ce soit, suivre le patron Formula E plutôt que
  celui d'ELMS/MLMC.
- [ ] 🟢 Ajouter `elms`/`mlmc` à `championship_assets.py::_LOGO_FILENAMES` le jour où des
  logos sont prévus (volontairement absent ce sprint — "aucun travail sur les icônes").
- [ ] 🟢 Compléter `aco_series/circuit_data.py` au fil des nouveaux circuits ELMS/MLMC
  rencontrés sans mapping (même pattern de repli propre que les autres championnats).
- [ ] 🟢 Vérification visuelle réelle de "Mon calendrier"/"Ce week-end" avec ELMS/MLMC
  affichés, sur un poste avec affichage.

---

## Extension Formula — suites possibles (Sprint 34)

- [ ] 🟢 Ajouter `formula-e` à `championship_assets.py::_LOGO_FILENAMES` le jour où un logo
  Formula E est prévu (volontairement absent ce sprint — "aucun travail sur les icônes").
- [ ] 🟢 Compléter `_CIRCUIT_DATA` (`providers/formula_e/sources/f1calendar.py`) au fil des
  nouveaux circuits Formula E rencontrés sans mapping (même pattern que F2/F1 Academy —
  repli propre sur ligne masquée, jamais "Unknown").
- [ ] 🟡 Porsche Supercup — candidat naturel suivant, probablement sur le même dataset
  f1calendar (mentionné dans la docstring de `F1CalendarBaseSource`, déjà anticipé dans
  `display_names.py`) — vérifier le vrai schéma JSON avant d'écrire quoi que ce soit,
  suivre exactement le patron Formula E de ce sprint.
- [x] 🟢 ELMS — **terminé Sprint 35** (le sprint suivant celui-ci) : pas sur le dataset
  f1calendar, mais scrapée en JSON-LD depuis europeanlemansseries.com via
  `AcoSportsEventSource`.
- [ ] 🟢 Vérification visuelle réelle de "Mon calendrier"/"Ce week-end" avec Formula E
  affichée, sur un poste avec affichage.

---

## Registre des identités visuelles de championnat — suites possibles (Sprint 33)

- [ ] 🔴 Livrer les logos officiels (F1, F2, F3, F1 Academy, WEC) dans
  `gui/assets/championships/` (voir README de ce dossier pour les noms de fichiers exacts)
  — aujourd'hui la fonctionnalité est architecturalement complète mais invisible faute de
  fichiers réels.
- [ ] 🔴 Décommenter `assets_dir=` dans `gui/app.py` une fois au moins un logo livré
  (partagé avec le logo de l'app elle-même — voir `gui/assets/logo/README.md`) — sans ça
  `ft.Image(src=...)` ne se résout pas visuellement même si le fichier est présent sur
  disque.
- [ ] 🟢 Étendre `ChampionshipAsset` avec un champ couleur/icône par championnat si un futur
  sprint en a besoin (Tableau de bord, Recherche) — un champ de plus, jamais un second
  point d'entrée à côté de `get_championship_asset()`.
- [ ] 🟢 Vérification visuelle réelle du logo aligné à gauche du titre (taille, alignement
  vertical) sur un poste avec affichage, une fois un vrai fichier livré.

---

## Normalisation des métadonnées — suites possibles (Sprint 32)

- [ ] 🟡 Corriger `f1calendar_base.py::_build_circuit` pour utiliser `event_data["location"]`
  comme `Circuit.name` (F2/F3/F1 Academy) au lieu de réutiliser `event_data["name"]` —
  réduirait le besoin de repli sur `circuit.city` dans `event_display.py`. Touche le
  provider, explicitement hors périmètre de ce sprint.
- [ ] 🟢 Compléter les tables `_CIRCUIT_DATA` (pays) de F2/F1 Academy pour réduire le
  nombre de lignes pays masquées dans "Ce week-end". Touche le provider, hors périmètre.
- [ ] 🟢 Envisager une table démonyme (pays → adjectif, "Canada"→"Canadian") si "Canada
  Grand Prix" au lieu de "Canadian Grand Prix" devient gênant visuellement.
- [ ] 🟢 Vérification visuelle réelle des cartes normalisées (F1/F2/F3, avec et sans pays)
  sur un poste avec affichage.

---

## Layout System — suites possibles (Sprint 31)

- [ ] 🟡 Utiliser `PageContainer`/`PageHeader`/`Section`/`CardList` dès la première future
  page (Favoris fonctionnel, Recherche, Tableau de bord, ...) — c'est exactement leur
  raison d'être, aucun code de mise en page à réécrire.
- [ ] 🟢 Premier consommateur réel de `SectionHeader` dès qu'une page affichera plusieurs
  groupes de cartes distincts (Tableau de bord probable en premier).
- [ ] 🟢 Vérification visuelle réelle du nouvel en-tête séparé (Ce week-end/Favoris/
  Préférences) et des bordures restaurées des lignes de Préférences, sur un poste avec
  affichage.
- [ ] 🟢 Envisager un séparateur optionnel dans `CardList` si une future liste en a
  vraiment besoin (point d'extension documenté, non codé).

---

## Bibliothèque de composants — suites possibles (Sprint 30)

- [ ] 🟡 Réutiliser `components.championship_card.build_championship_card` dès
  l'implémentation de "Mes favoris" — c'est exactement le cas d'usage visé.
- [ ] 🟢 Ajouter un bouton Favori ⭐ dans le `footer` de `ChampionshipCard` une fois la
  persistance des favoris disponible — le point d'extension existe déjà, aucun changement
  de signature nécessaire.
- [ ] 🟢 Documenter dans `gui/components/__init__.py` chaque nouveau composant au fur et à
  mesure de son ajout (index simple de la bibliothèque).

---

## Ce week-end — suites possibles (Sprint 29)

- [x] 🔴 `OfficialWecSource` — **terminé Sprint 48** : "Ce week-end" affiche désormais WEC
  en conditions réelles (voir aussi la tâche WEC équivalente plus bas, partagée avec
  `generate-wec`).
- [ ] 🟢 Ancrer le découpage vendredi-dimanche sur le fuseau du circuit plutôt que UTC —
  cas limite pour les circuits très à l'est (Japon, Singapour, Chine, Australie).
- [ ] 🟢 Compléter `_COUNTRY_LABELS` (`gui/upcoming_weekend.py`) au fil des circuits
  effectivement rencontrés sans mapping (fallback actuel : nom brut, souvent anglais, sans
  drapeau).
- [ ] 🟢 Vérification visuelle réelle des 3 états (chargement/aucune course/trouvé) sur un
  poste avec affichage.

---

## Uniformisation finale de l'interface — suites possibles (Sprint 28)

- [ ] 🟢 Vérification visuelle réelle des cartes centrales (Ce week-end, Mes favoris,
  Préférences) et de la présentation compacte d'À propos sur un poste avec affichage.
- [ ] 🟢 Évaluer si les 6 lignes de Préférences ont besoin d'un séparateur visuel léger
  entre elles maintenant qu'elles n'ont plus leur propre bordure (actuellement juste de
  l'espacement) — purement cosmétique, à trancher après retour visuel.

---

## Uniformisation du layout — suites possibles (Sprint 27)

- [ ] 🟢 Vérification visuelle réelle du gabarit partagé (`theme.page_shell`) sur un poste
  avec affichage — comportement responsive attendu au redimensionnement (rétrécit sous
  1000px, plafonne au-delà), vérifié uniquement par structure/tests dans ce sandbox.

---

## Release Alpha Phase 2 — suites possibles (Sprint 26)

- [~] 🔴 Intégrer les SVG définitifs du Brand Set v1.0 — **SVG livrés** (`logo-horizontal.svg`,
  `logo-vertical.svg`, `mc-icon.svg` dans `gui/assets/logo/`, branding officiel mergé), mais
  **le câblage reste à faire** : `theme.logo_placeholder(...)` est toujours l'appel utilisé
  dans `theme.py`/`views/about.py`, les SVG ne sont pas encore chargés à sa place.
  - Estimation : 30min (layout déjà prêt, pas de rework attendu)
- [ ] 🟡 Audit mypy `main_view.py` — signatures `on_click` Flet 0.80 vs 0.85.3 installé
  - 21 erreurs préexistantes avant Sprint 26 (26 après, proportionnel aux handlers du wizard)
  - Estimation : 2-3h (vérifier les stubs Flet actuels, éventuellement caster les handlers)
- [ ] 🟢 Écran/capture réels de l'assistant "Mon calendrier" (devenu depuis une page
  unique réorganisée, Sprint 43) une fois un environnement graphique disponible
  - Ce sprint a été vérifié par tests unitaires (100 % theme/calendar/models) + simulation
    de parcours via une fausse `Page` (aucun display dans ce sandbox)

---

## Terminé ✅

- [x] Scaffold projet (pyproject.toml, CI, structure)
- [x] Modèles métier Pydantic v2 frozen
- [x] EventStatus + event_uid
- [x] IcsExporter (RFC 5545)
- [x] Architecture Provider/Source F1
- [x] OpenF1Source (httpx, mapping, 45 tests)
- [x] CLI `generate-f1 YEAR OUTPUT.ics` (11 tests intégration)
- [x] HttpCache — cache disque JSON centralisé, TTL, refresh, 24 tests
- [x] Migration OpenF1Source → HttpCache
- [x] CLI `--refresh` flag
- [x] WecProvider — architecture complète (provider + source ABC + OfficialWecSource stub), 24 tests
- [x] ConfigService — config.yaml, Pydantic, valeurs par défaut, 30 tests
- [x] IcsExporter — VALARM configurable (alarm_minutes), 7 tests
- [x] CLI generate-f1 — wiring ConfigService (cache path/TTL, source selection, alarm)
- [x] ProviderRegistry — register/get/list_all/enabled/discover, auto-enregistrement à l'import, 25 tests
- [x] SourceRegistry — register/get/list_for/list_all/discover, clé (championship, source), 24 tests
