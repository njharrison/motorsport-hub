# DECISIONS.md — Architecture Decision Records

---

## ADR-050 — Correction du packaging Flet : manifeste de build dédié (`motorsport_calendar/gui/pyproject.toml`) + `tool.flet.dev_packages` installant le projet lui-même comme dépendance locale, jamais de duplication de la liste de dépendances

**Contexte**
Suite directe de l'audit du Sprint 58 (ADR-049) : le build Linux
compile mais le binaire produit plante au démarrage
(`ModuleNotFoundError: No module named 'motorsport_calendar'`).
Mission : identifier la méthode officiellement recommandée par Flet,
corriger proprement, sans bricolage ni casse du flux de développement
actuel. Contrainte du brief, prise au sérieux : "aucune modification
métier" — ce ADR documente une correction strictement packaging.

**Décision — vérifier chaque hypothèse par un rebuild réel, jamais par
lecture de code seule**
Le diagnostic du Sprint 58 (dépendances manquantes) était correct mais
incomplet. Plutôt que de supposer qu'ajouter une `pyproject.toml`
listant les 9 dépendances suffirait, cette hypothèse a été **appliquée
et testée pour de vrai** : rebuild complet, binaire relancé — même
erreur `ModuleNotFoundError`, à l'identique. Sans ce test, ce rapport
aurait pu conclure à tort que le problème était résolu. C'est ce test
qui a révélé la seconde cause, indépendante : `flet build` zip le
*contenu* du dossier ciblé (`motorsport_calendar/gui/`), aplati, sans
jamais l'envelopper dans un paquet `motorsport_calendar.` — aucune
liste de dépendances ne corrige un import absolu qui ne peut structurellement
pas se résoudre.

**Décision — `tool.flet.dev_packages` installe le projet lui-même comme
dépendance locale, plutôt que de dupliquer sa liste de dépendances**
Une fois la vraie cause identifiée, deux options : (1) une
`pyproject.toml` dans `gui/` listant manuellement les 9 dépendances
racine + `motorsport_calendar` d'une façon ou d'une autre, ou (2)
utiliser `tool.flet.dev_packages` — le mécanisme que Flet fournit
explicitement pour "une dépendance développée localement, pas encore
publiée" (confirmé en lisant `flet_cli/commands/build_base.py`, pas
supposé). L'option (2) a été retenue : `motorsport_calendar/gui/
pyproject.toml` déclare seulement `flet` et `motorsport-calendar`
(le projet lui-même) ; `tool.flet.dev_packages` réécrit cette seconde
entrée en `motorsport-calendar @ file:///…/motorsport-calendar`
(résolu relativement à `motorsport_calendar/gui/`, donc `../..` = la
racine du projet). Ceci déclenche un vrai build/install pip isolé du
projet, via la configuration hatchling **déjà existante** à la racine
(`packages = ["motorsport_calendar"]`) — installer le paquet ainsi
résout aussi ses propres dépendances déclarées de façon transitive,
directement depuis le seul endroit où elles sont réellement
déclarées. Aucune duplication de liste, donc aucun risque de dérive
future entre deux listes à synchroniser manuellement — exactement ce
que le brief demandait ("aucun contournement fragile").

**Décision — ne jamais changer la commande de build documentée ni
l'emplacement de sortie**
`python_app_path` reste `motorsport_calendar/gui/` (inchangé) — la
commande documentée (`flet build linux motorsport_calendar/gui
--module-name app`) et l'emplacement de sortie
(`motorsport_calendar/gui/build/linux/`) restent identiques. Une
alternative envisagée (pointer `flet build` sur la racine du projet
avec `tool.flet.app.path`) aurait déplacé la racine de build, forçant
une régénération complète du scaffold Flutter déjà en cache
(`motorsport_calendar/gui/build/flutter/`, plusieurs minutes) pour un
bénéfice nul — le fix retenu réutilise ce cache, rebuild vérifié en
~25 secondes.

**Décision — aucune modification de la `pyproject.toml` racine**
`motorsport_calendar/gui/pyproject.toml` est un manifeste de build
**uniquement** — jamais lu par pip/hatchling pour l'installation
normale du projet (`pip install -e .[gui]`, `motocal`/`motocal-gui`).
Vérifié explicitement après le correctif : `motorsport_calendar.gui.app`
et `motorsport_calendar.cli` s'importent toujours normalement depuis le
virtualenv de développement, sans aucun changement de comportement. Le
diff observé sur la `pyproject.toml` racine (`beautifulsoup4`/`lxml`/
`types-PyYAML`/`types-icalendar`) est une dérive historique
préexistante, non commise, antérieure à cette session — confirmé,
jamais introduit par ce correctif.

**Décision — un garde-fou automatisé plutôt qu'un commentaire seul**
Le principal risque résiduel de cette approche (bien que minimisé par
le choix de `tool.flet.dev_packages` plutôt qu'une duplication) est
qu'un futur éditeur réintroduise une duplication de liste par erreur.
`tests/test_packaging.py::TestFletBuildManifest` (8 tests) vérifie
explicitement : le manifeste de build ne redéclare jamais une
dépendance de la racine (`test_gui_manifest_never_duplicates_the_root_
dependency_list`), `project.name`/`version` restent synchronisés, et la
redirection `tool.flet.dev_packages` pointe vers un vrai projet
installable sur le disque — un échec de test, pas seulement un
commentaire ignoré, si l'un de ces invariants est un jour rompu.

**Conséquences**
- Le build Linux produit désormais un exécutable qui démarre réellement
  — vérifié par un rebuild complet et 2 lancements réels du binaire,
  aucune trace d'erreur dans les deux cas (contre une trace systématique
  avant le correctif).
- Identité de l'application corrigée au passage, sans effort
  supplémentaire (même manifeste) : exécutable/ID d'application/titre de
  fenêtre natif passent des défauts génériques Flet
  (`gui`/`com.flet.gui`) à `motorsport-calendar`/`com.flet.motorsport-
  calendar`.
- Un point cosmétique reste non résolu (version embarquée `1.0.0` au
  lieu de `0.2.0`) — documenté honnêtement plutôt que masqué, n'affecte
  ni le démarrage ni le comportement de l'app.
- Le flux de développement existant (`motocal`/`motocal-gui`, `pip
  install -e .[gui]`, la `pyproject.toml` racine) reste intact et
  vérifié inchangé.
- 8 nouveaux tests nets, aucune régression sur les 2033 précédents
  (2041 total, dont 1 skip Windows-only inchangé).
- Aucun commit effectué, conformément à la contrainte explicite de la
  mission.

---

## ADR-049 — Validation Packaging Beta : audit du build réel (pas du build théorique), cause racine identifiée par lecture du code source de `flet_cli`, aucun correctif appliqué ce sprint, `Release/` en zone de préparation locale jamais versionnée

**Contexte**
Sprint 58. Le build Linux (`flet build linux motorsport_calendar/gui
--module-name app`) venait de se compiler avec succès pour la première
fois. `docs/PACKAGING.md` (Sprint 49) affirmait la configuration du
packaging "vérifiée... correcte de bout en bout", mais cette affirmation
n'avait jamais été testée contre un binaire réellement exécuté — le
build de Sprint 49 n'avait jamais dépassé l'étape de compilation
(outillage système manquant à l'époque). Ce sprint audite pour la
première fois le binaire produit pour de vrai.

**Décision — auditer le binaire réellement produit et exécuté, jamais la
configuration "en théorie"**
Plutôt que de relire `docs/PACKAGING.md` et supposer que ses affirmations
tiennent toujours, le binaire compilé a été directement lancé
(`./gui`) et son log réel inspecté
(`~/.cache/com.flet.gui/console.log`) — c'est cette vérification directe,
et uniquement elle, qui a révélé le `ModuleNotFoundError`. Une lecture de
la documentation Flet seule, ou une inspection statique du dossier de
build sans jamais lancer l'exécutable, n'aurait montré qu'un dossier
apparemment complet (exécutable présent, assets présents, bibliothèques
présentes) — le problème n'est visible qu'à l'exécution. Cette méthode
(vérifier en lançant réellement le binaire, jamais en supposant depuis
la structure de fichiers) est elle-même documentée dans
`docs/PACKAGING.md` §6 comme la leçon à retenir pour tout futur audit de
packaging sur ce projet.

**Décision — la cause racine est établie en lisant le code source de
`flet_cli`, jamais devinée depuis un message d'erreur**
`ModuleNotFoundError: No module named 'motorsport_calendar'` pointe vers
un problème d'imports, mais ne dit pas *pourquoi* le paquet est absent du
build. Plutôt que d'essayer des corrections au hasard, le code source
installé de `flet_cli` (`flet_cli/commands/build_base.py`,
`flet_cli/utils/project_dependencies.py`) a été lu directement : `self.
get_pyproject = load_pyproject_toml(self.python_app_path)` — Flet
cherche une `pyproject.toml` **à l'intérieur du chemin `python_app_path`
passé en argument** (`motorsport_calendar/gui/`), jamais à la racine du
projet où la vraie `pyproject.toml` (avec les 9 dépendances réelles)
existe déjà. Cette lecture directe du code source explique
simultanément 3 symptômes observés indépendamment (dépendances
absentes, paquet applicatif absent, identité générique `gui`/
`com.flet.gui`/`1.0.0`) par une seule et même cause — cohérence qui
confirme le diagnostic plutôt que de le supposer.

**Décision — documenter la correction, ne pas l'appliquer ce sprint**
Le brief est explicite : "Contraintes : aucune modification métier,
uniquement packaging / release." Une lecture stricte exclut même un
correctif purement technique (ajouter une `pyproject.toml`/section
`[tool.flet]`) tant qu'il n'est pas explicitement demandé — d'autant que
vérifier un tel correctif exigerait de relancer un build complet
(plusieurs minutes, dépendant de l'outillage système) et de re-tester le
binaire, un cycle de validation que le brief ne demande pas non plus
("audit complet du packaging", jamais "corrige le packaging"). Les deux
pistes de correction candidates sont documentées avec un niveau de détail
suffisant pour qu'un futur sprint les applique directement sans
redécouvrir le problème (`docs/PACKAGING.md` §6.3, `docs/TODO.md` piste
`-22`).

**Décision — corriger l'affirmation prématurée du Sprint 49 avec un
encart explicite, jamais une réécriture silencieuse**
`docs/PACKAGING.md` §5 (Sprint 49) reste inchangé dans son contenu
d'origine — ses constats sur les assets/icônes/chemins restent corrects
et vérifiés indépendamment ce sprint. Seule l'affirmation "correct de
bout en bout" était fausse (ou plutôt : jamais vérifiée, présentée comme
si elle l'était). Un encart `> ⚠ Correction (Sprint 58)` est ajouté en
tête du document, pointant vers la nouvelle section d'audit — plutôt que
d'éditer silencieusement la phrase d'origine, ce qui aurait effacé la
trace de l'erreur et empêché un futur lecteur de comprendre pourquoi le
Sprint 58 a été nécessaire. Même principe que `docs/JOURNAL.md` : chaque
session est un enregistrement historique, jamais réécrite après coup.

**Décision — `Release/` est une zone de préparation locale régénérée à
chaque release, jamais versionnée ni accumulée**
L'exemple du brief (`Release/Linux/`, `Release/Windows/`, `Release/
Source/`, `CHANGELOG.md`, `LICENSE`, `README.md`) est repris tel quel
plutôt que réinventé, avec 2 précisions ajoutées : (1) chaque plateforme
contient une archive compressée (`.tar.gz`/`.zip`) + son fichier de
somme de contrôle (`.sha256`), jamais le dossier brut de 112 Mo — un
utilisateur ou une Release GitHub ne doit jamais recevoir des milliers de
fichiers non compressés ; (2) `Release/` est ajouté à `.gitignore`
(même raisonnement que `build/`, déjà ignoré) — GitHub Releases est déjà
le système d'archivage/versionnage des releases publiées, dupliquer cet
historique dans le dépôt git lui-même n'apporterait rien et gonflerait
inutilement sa taille.

**Conséquences**
- Le statut réel de "Beta distribuable" est maintenant connu avec
  certitude : **non**, tant que le blocage `ModuleNotFoundError` n'est
  pas corrigé — un fait vérifié, documenté, avec une cause racine précise
  et deux corrections candidates prêtes à appliquer.
- `docs/PACKAGING.md` reflète désormais l'état réel du packaging, pas
  un état supposé depuis une compilation réussie.
- `docs/RELEASE.md` (nouveau) fournit la procédure complète une fois le
  blocage résolu — rien à réécrire dans ce document quand le correctif
  sera appliqué, seule la note d'avertissement en tête sera retirée.
- Aucune régression : aucun fichier source applicatif modifié, suite de
  tests intacte (2034 tests, 1 skip Windows-only, inchangé).
- Aucun commit effectué, conformément à la contrainte explicite du
  brief.

---

## ADR-048 — Préparation Beta (Nettoyage & Positionnement) : IMSA/WorldSBK masqués via un filtre GUI-only, "À propos"/"Soutenir le projet" reçoivent `url_launcher` directement, 2 duplications d'URL-opener/coming-soon-row fusionnées

**Contexte**
Sprint 57. Motorsport Calendar approche de sa première Beta publique —
ce sprint ne concerne que le positionnement du produit : masquer 2
championnats sans source fiable, transformer "À propos" en vraie
présentation, créer "Soutenir le projet" comme point de contact avec la
communauté. Aucune fonctionnalité, aucune logique métier, aucune
évolution des services.

**Décision — IMSA/WorldSBK sont filtrés dans `controller.list_championships()`
uniquement, jamais dans `registry`/`config.yaml`/`WEEKEND_CHAMPIONSHIP_IDS`**
`controller.list_championships()` est l'unique appelant vérifié dans tout
le projet — `main_view.py:327` en est le seul consommateur (confirmé par
recherche exhaustive). C'est donc le seul point qu'il fallait filtrer
pour que les deux championnats disparaissent de "Mon calendrier"/"Mes
favoris"/"Recherche" simultanément (`get_groups_for`/`search_service.
build_index` reçoivent tous les deux la même liste déjà filtrée). Options
rejetées :
- Exclure via `config.yaml` (`providers.imsa.enabled = false`) — aurait
  aussi changé `registry.enabled(...)`, donc le "championnats actifs" du
  Dashboard et potentiellement le comportement CLI (`motocal generate`),
  bien au-delà de "l'interface utilisateur" que le brief cible
  explicitement.
- Retirer les deux ids de `upcoming_weekend.py::WEEKEND_CHAMPIONSHIP_IDS`
  ("Ce week-end"/Dashboard) — non fait : les deux sources sont déjà des
  stubs qui échouent systématiquement (`OfficialImsaSource`/
  `OfficialWorldSbkSource` non implémentées, dette documentée depuis les
  Sprints 36/38/48), donc aucune carte visible n'en est jamais issue de
  toute façon ; les retirer n'aurait changé aucun comportement observable
  pour un risque de périmètre inutile.

`registry.list_all()` (utilisé par le CLI, `registry.enabled(...)`,
`ProviderRegistry` en général) reste totalement intact — "Aucune
suppression de code" pris au pied de la lettre : les deux providers
restent pleinement fonctionnels et generables via `cli.py
generate-imsa`/`generate-worldsbk`, exactement comme avant ce sprint.

**Décision — "À propos" et "Soutenir le projet" reçoivent `url_launcher`
directement, jamais un callback pré-câblé par main_view.py**
Chaque autre page interactive (Préférences, Mon calendrier, Favoris)
suit le patron "main_view.py construit et câble chaque contrôle, la vue
ne fait qu'arranger" — mais "À propos" fait exception depuis le Sprint 28
(la seule interactivité de la page est "ouvrir une URL externe", sans
état ni logique métier que main_view.py aurait besoin d'injecter).
"Soutenir le projet" suit exactement cette même exception, pour
exactement la même raison — ses deux boutons (Discussions/Issues) n'ont
besoin de rien d'autre que `url_launcher` + une URL déjà connue à la
construction. Créer un état/des callbacks dans `main_view.py` pour cette
page aurait ajouté de la complexité sans aucun bénéfice réel.

**Décision — deux duplications réelles (pas seulement risquées) sont
éliminées, la 3ème occurrence de chacune ayant rendu le problème concret**
Le principe déjà établi dans ce projet ("mutualiser à la 2ème/3ème
utilisation réelle", jamais en spéculant sur un futur besoin) s'applique
ici deux fois :
- `gui/url_opener.py::make_url_opener` — `views/about.py::on_github_click`
  (Sprint 26) et `main_view.py::_make_release_opener` (Sprint 51/53)
  étaient déjà deux implémentations indépendantes du même "ouvrir une URL
  avec repli `subprocess` Windows" ; "Soutenir le projet" avait besoin
  d'une 3ème occurrence (2 boutons) — plutôt que d'écrire une 3ème copie,
  les trois sites d'appel utilisent désormais la même fonction partagée.
- `gui/components/layout::ComingSoonRow` — `views/preferences.py::
  _pref_row` (privé depuis le Sprint 52) avait exactement la forme que
  les emplacements PayPal/GitHub Sponsors nécessitaient ; promu en
  composant partagé plutôt que redupliqué une seconde fois. La fonction
  privée d'origine est entièrement supprimée (jamais gardée comme alias
  de compatibilité) — même discipline que la promotion de
  `championship_selector.py` au Sprint 44, qui avait pareillement retiré
  le code d'origine de `calendar.py` plutôt que d'y laisser un doublon
  inerte.

**Décision — le contenu du "À propos"/"Soutenir le projet" réutilise le
vocabulaire déjà établi par `docs/PRODUCT_VISION.md`, jamais un nouveau
discours produit inventé pour l'occasion**
Les 3 nouvelles sections d'"À propos" (Objectifs, Philosophie Open
Source, Technologies) s'appuient sur les formulations déjà rédigées dans
`docs/PRODUCT_VISION.md` ("pourquoi Motorsport Calendar existe",
"philosophie") plutôt que d'inventer un ton distinct — cohérence de la
voix du produit à travers documentation et interface.

**Conséquences**
- IMSA/WorldSBK invisibles pour l'utilisateur GUI, toujours pleinement
  architecturés — un futur retrait de `_HIDDEN_FROM_GUI` suffira à les
  réintégrer sans autre changement.
- "À propos" devient une vraie vitrine du projet ; "Soutenir le projet"
  existe comme fondation prête à recevoir de vrais liens de don sans
  qu'aucun code supplémentaire ne soit nécessaire au-delà de remplir 2
  constantes.
- Deux duplications de code réelles éliminées (`url_opener`,
  `ComingSoonRow`), zéro comportement changé pour les appelants
  existants (Préférences/Dashboard/boîte de dialogue de mise à jour).
- mypy `motorsport_calendar/` : +2 (39 → 41, les 2 nouveaux boutons de
  "Soutenir le projet", même famille déjà acceptée). mypy `tests/` : +19
  (157 → 176, un nouveau fichier de test utilisant un double factice
  plutôt que le vrai type Flet, même famille de bruit déjà documentée).
- 34 nouveaux tests nets, aucune régression sur les 2000 précédents
  (2034 total, dont 1 test spécifique Windows `skip`é sur cet
  environnement Linux).
- Aucun commit effectué, conformément à la contrainte explicite du
  brief.

---

## ADR-047 — Notifications natives : Flet n'offre aucune notification système (fait vérifié), `gui/system_notifications.py` reste une abstraction sans implémentation, `NotificationService` intouché, préférence existante réutilisée via `controller.prepare_notifications`

**Contexte**
Sprint 56. `NotificationService` (Sprint 46) calcule déjà *quoi*/*quand*
notifier, entièrement indépendant de Flet et de toute plateforme ; les
préférences (Sprint 52) exposent déjà "notifications activées". L'objectif
de ce sprint est uniquement de connecter ce moteur à une implémentation
native — jamais de le modifier, jamais de lui faire connaître une
plateforme. Le brief est explicite sur la marche à suivre si Flet ne
fournit rien : "ne pas bricoler", "créer uniquement une abstraction prête
à recevoir une future implémentation."

**Décision — vérifier factuellement les capacités de Flet avant d'écrire
la moindre ligne de code, jamais supposer**
Recherche exhaustive dans le paquet `flet==0.85.3` réellement installé
dans l'environnement (pas la documentation en ligne, pas une connaissance
générale potentiellement obsolète) :
- `flet/controls/services/` (le dossier qui contient chaque service
  "pont natif" de Flet — clipboard, url_launcher, share, wakelock, etc.)
  liste 20 fichiers, énumérés un par un dans le docstring du nouveau
  module ; aucun ne s'appelle "notification"/"toast"/"tray".
- `flet/controls/core/window.py` (l'API `ft.Window`) n'expose que
  `wait_until_ready_to_show`/`destroy`/`center`/`close`/`to_front`/
  `start_dragging`/`start_resizing` — aucune icône de zone de
  notification, aucun hook de notification native.
- Le `CHANGELOG.md` Dart de Flet, bundlé avec le paquet pub.dev
  (`~/.pub-cache/hosted/pub.dev/flet-0.85.3/CHANGELOG.md`), mentionne
  "notifications" une seule fois dans tout l'historique des releases —
  pour les notifications de **scroll** (un événement d'interface sans
  rapport), jamais pour une notification système.

Conclusion vérifiée, pas une hypothèse : **Flet ne fournit aucune
capacité de notification système sur aucune plateforme, à la version
installée.** Cette méthode (grep exhaustif du paquet réellement
installé, jamais une supposition) est elle-même documentée dans le
docstring de `gui/system_notifications.py` pour qu'un futur sprint la
revérifie de la même façon plutôt que de faire confiance à une note
obsolète.

**Décision — ne jamais bricoler une solution avec une bibliothèque
tierce, livrer uniquement l'abstraction**
Des bibliothèques Python existent pour ce besoin (`plyer`, `winotify`,
`notify-py`, un pont D-Bus/`notify2` sous Linux). Le brief interdit
explicitement de "bricoler" une solution alors qu'aucune n'est
"propre" — ajouter une dépendance tierce est une décision réelle (choix
d'une bibliothèque par plateforme, permissions macOS/Windows,
implications de packaging documentées dans `docs/PACKAGING.md`), pas un
détail d'implémentation à trancher en passant dans un sprint dont
l'objectif est "connecter le moteur", pas "choisir et intégrer une
dépendance de notification". `gui/system_notifications.py` définit donc
la seule chose que ce sprint doit livrer : la forme que prendra une
future implémentation (`SystemNotifier`, un `Protocol` à deux méthodes),
et la seule implémentation honnête possible aujourd'hui
(`NullSystemNotifier`, toujours indisponible, par construction et non
par bug).

**Décision — `NotificationService` reste totalement intouché, `gui/
system_notifications.py` est le seul endroit à connaître une plateforme**
Aucune ligne de `gui/notification_service.py` n'est modifiée ce sprint
— vérifié explicitement (`git status`/`git diff` sur ce fichier avant
clôture). Le nouveau module importe `Notification`/`NotificationKind`
en lecture seule, jamais l'inverse. Le formatage texte (titre/corps
d'une notification) — que `NotificationService`'s propre docstring
délègue explicitement à "whichever future consumer" depuis le Sprint 46
— est ajouté dans `gui/system_notifications.py::_format()`, avec 5
nouvelles chaînes `strings.py` pour les libellés de `NotificationKind` :
la seule "logique" ajoutée ce sprint est de la présentation, jamais du
métier.

**Décision — la préférence `notifications_enabled` existante gate
l'orchestration dans `controller.py`, jamais dans `main_view.py` ni
dans `system_notifications.py`**
Même rôle que `update_check_enabled` court-circuitant déjà
`check_for_update` (Sprint 51) : `controller.py::prepare_notifications()`
lit la préférence, retourne `0` immédiatement si désactivée, sans même
construire `NotificationService.compute_notifications()` — testé en
patchant `compute_notifications` pour échouer si jamais atteint, exact
même technique que `TestCheckForUpdate::
test_disabled_preference_short_circuits_before_url_resolution`. Aucun
nouveau réglage créé — "aucune nécessité technique clairement
justifiée" n'existe pour en ajouter un, la préférence du Sprint 52
suffit intégralement. `main_view.py::_prepare_system_notifications()`
se limite à fournir les données que seul main_view.py détient
(`year_events`, la liste de favoris) — il n'importe jamais `gui/
system_notifications.py` directement, ni ne lit la préférence
lui-même, exactement le même partage des responsabilités que
`_check_for_update()`/`check_for_update()`.

**Conséquences**
- `gui/system_notifications.py` existe, testé, prêt — mais aucune
  notification système n'est jamais réellement affichée aujourd'hui, un
  fait assumé et documenté, pas une régression cachée.
- Une future implémentation ne touchera qu'un seul endroit
  (`get_system_notifier()`) pour devenir réelle ; tout le reste de la
  chaîne (moteur, préférences, orchestration, tests) reste stable par
  construction.
- mypy/ruff : deltas nuls (39/157/0 inchangés) — nouveau module propre,
  aucune signature de callback Flet en jeu.
- 22 nouveaux tests nets (16 pour `system_notifications.py`, 6 pour
  `controller.prepare_notifications`), aucune régression sur les 1978
  précédents (2000 total).
- Premier vrai consommateur de `utils.get_logger` — infrastructure de
  logging présente dans le projet depuis son tout début, jamais
  utilisée par le code applicatif jusqu'ici.
- Aucun commit effectué, conformément à la contrainte explicite du
  brief.

---

## ADR-046 — Recherche interactive : identité portée par `SearchResultItem` (jamais le domain object), résolution événement/circuit extraite en fonctions partagées, clic championnat navigue sans muter la sélection

**Contexte**
Sprint 55. "Recherche" (Sprint 45) indexe déjà championnats/événements/
circuits, mais ses résultats sont purement passifs — identifié comme
dette au Sprint 54 (piste `-18`, hors périmètre à l'époque car la
correction franchissait "aucune évolution des services"). Ce sprint lève
explicitement cette limite : rendre chaque résultat cliquable, en
réutilisant exclusivement `SearchService`/`EventDetails`/
`CircuitService`/la navigation déjà existante, sans nouveau service,
sans évolution des modèles métier.

**Décision — `SearchResultItem` porte une identité, jamais le domain
object lui-même, exactement comme `SeasonEventRow` depuis le Sprint 42**
Trois champs optionnels ajoutés (`championship_id`/`event_uid`/
`circuit_key`), jamais rendus à l'écran — un click handler les lit pour
résoudre quelle vue ouvrir. Exactement un des trois est peuplé selon le
type de résultat (championnat : `championship_id` seul ; événement :
`championship_id` + `event_uid` — la même paire que `SeasonEventRow` ;
circuit : `circuit_key` seul). L'alternative rejetée était de créer 3
dataclasses de résultat distinctes (une par type) — plus "type-safe"
sur le papier, mais cela aurait fait éclater `SearchResults`/
`_IndexedItem`/`_matches` (aujourd'hui génériques sur un seul type) en
code dupliqué trois fois pour un gain de sûreté de typage marginal
(`SearchResultItem` reste interne au module, jamais une API publique).
Le patron "champs optionnels, `None` = non applicable" est déjà établi
par `ChampionshipCardData.circuit_name`/`country` (Sprint 32) — pas un
nouveau principe de conception, sa troisième application.

**Décision — la résolution identité → vue existante est extraite en
fonctions partagées, jamais réimplémentée à un second site d'appel**
La contrainte "aucune duplication" est la plus explicite du brief.
Deux résolutions identiques existaient déjà, chacune enfouie dans une
fermeture locale à une seule boîte de dialogue :
- `_on_event_row_click` (season explorer, Sprint 42) faisait déjà
  "chercher un `Event` dans `year_events` par `championship_id`/
  `event_uid`, puis ouvrir la fiche" — son corps devient
  `_open_event_details(championship_id, event_uid)`, une fonction
  top-level de `build_main_view`, et `_on_event_row_click` devient un
  simple relais d'un seul appel.
- Le `on_circuit_click` interne à `_show_event_details_dialog`
  (Sprint 47) faisait déjà "résoudre un `circuit_key` via
  `CircuitService`, puis ouvrir la fiche Circuit" — devient
  `_open_circuit_details(circuit_key)`, même traitement.

Un clic résultat "événement"/"circuit" dans "Recherche" appelle
désormais ces deux mêmes fonctions — jamais une seconde implémentation
de la résolution. Même technique que `_make_release_opener` (Sprint 53,
ADR-044) : extraire une fermeture locale à un seul site en une fonction
partagée dès qu'un second site légitime apparaît, plutôt que la
dupliquer ou la généraliser prématurément avant qu'un second besoin
n'existe.

**Décision — un clic résultat "championnat" navigue vers "Mon
calendrier", ne mute jamais `state.selected_championships`**
Le brief demande, verbatim : "ouvre directement la page correspondante
(ou la meilleure destination existante)". Aucune page dédiée par
championnat n'existe dans l'app — "Mon calendrier" est la destination
existante la plus proche (c'est la page où l'on *parcourt* les
événements d'un championnat). La navigation réutilise
`_navigate_to("calendar")`, exactement le mécanisme de clé string du
Sprint 53 ("Accès rapides" du Dashboard) — aucune nouvelle logique de
navigation. Option envisagée et rejetée : sélectionner automatiquement
le championnat cliqué (l'ajouter à `state.selected_championships`,
réutilisant `_on_championship_click`) pour qu'il soit immédiatement
visible en arrivant sur la page. Rejetée parce que cela muterait un état
avec des effets de bord réels et persistés (`_save_prefs()` écrit
`selected_championships` sur disque, et ce choix pilote la génération
ICS) — un clic pour *consulter* un résultat de recherche ne doit jamais
modifier silencieusement ce que l'utilisateur a choisi d'exporter. La
brief ne demande pas cette automatisation ; "aucune nouvelle logique
métier" en interdit l'ajout non sollicité.

**Décision — le câblage `on_click` reste un attribut post-construction
(`card.on_click = lambda e: on_click(item)`), jamais un argument du
constructeur**
Suit exactement le patron déjà établi par `_championship_button`/
`_season_event_row` (`views/calendar.py`) plutôt que
`ft.Container(on_click=...)`. Choix confirmé rétroactivement par mypy :
les sites qui passent `on_click=`/`on_change=` au constructeur
(`views/dashboard.py`/`views/about.py`, notamment) contribuent chacun à
la dette Flet stub-version déjà documentée (Sprint 26, Sprint 50 §4,
Sprint 54 ADR-045) ; l'assignation post-construction n'y contribue
jamais. Ce sprint ajoute donc 0 nouvelle erreur mypy malgré 3 nouveaux
call-sites cliquables.

**Conséquences**
- "Recherche" devient un véritable point d'entrée : chaque résultat
  ouvre la vue existante correspondante, sans jamais dupliquer une
  résolution déjà écrite ailleurs.
- Deux fonctions nouvellement partagées (`_open_event_details`,
  `_open_circuit_details`) réduisent la duplication déjà latente entre
  season explorer/fiche événement et search/fiche événement — un
  bénéfice de maintenabilité au-delà du strict périmètre du brief.
- mypy : delta nul (39/157 inchangés) — chaque nouveau câblage suit le
  patron post-construction, jamais le patron constructeur qui aurait
  ajouté à la dette Flet stub-version.
- 10 nouveaux tests nets, aucune régression sur les 1968 précédents
  (1978 total).
- Aucun commit effectué, conformément à la contrainte explicite du
  brief.

---

## ADR-045 — Préparation Beta (Recette UX) : icône d'en-tête = variante pleine du rail de navigation, jamais d'emoji en interface, espacements toujours via `theme.Spacing`, titres `EmptyState` sans point final, "À propos" affiche la vraie version

**Contexte**
Sprint 54. Motorsport Calendar possède désormais toutes les fonctionnalités
majeures prévues pour l'Alpha (Sprints 1-53) — avant de poursuivre le
développement, le brief demande une phase de recette utilisateur pure :
relire les 7 pages, identifier les incohérences visuelles/textuelles
"clairement identifiées", les corriger, sans jamais ajouter de
fonctionnalité, provider, ou évolution des services/modèles. Cet ADR
documente les conventions établies (ou confirmées) par cette recette,
pour que les sprints suivants les respectent par défaut plutôt que de les
redécouvrir un point à la fois.

**Décision — l'icône d'un `PageHeader` doit toujours être la variante
*pleine* de l'icône du rail de navigation, jamais une troisième glyphe**
Chaque page du rail de navigation a deux icônes Material : une variante
`_OUTLINED` (état non sélectionné) et une variante pleine (état
sélectionné, `selected_icon`). Depuis le Sprint 43 ("Mon calendrier"),
la convention *implicite* était que le `PageHeader` de chaque page
reprenne la variante pleine — cohérent avec le fait que le header n'est
visible que lorsque cette page est *déjà* la page active/sélectionnée.
"Ce week-end"/"Mon calendrier"/"Recherche"/"Préférences" suivaient déjà
cette règle sans qu'elle n'ait jamais été écrite nulle part ; "Mes
favoris" (`STAR_BORDER`, une troisième glyphe étoile) et le Dashboard
(`SPACE_DASHBOARD_OUTLINED`, la variante contour au lieu de la pleine)
la violaient silencieusement depuis leur création (Sprints 39/44). La
règle est maintenant explicite : **l'icône d'un `PageHeader` est
toujours la même valeur que `selected_icon` du `NavigationRailDestination`
correspondant dans `main_view.py`** — un futur sprint qui ajoute une
page doit copier cette valeur, jamais en choisir une nouvelle par
ressemblance visuelle.

**Décision — jamais d'emoji dans l'interface rendue, uniquement des
icônes Material (`ft.Icon`/`ft.Icons.*`)**
La boîte de dialogue de succès préfixait son titre d'un "✅ " codé en
dur directement dans une f-string de `main_view.py` — le seul endroit de
toute l'application où un caractère emoji apparaissait dans du texte
réellement rendu (les emoji présents dans des docstrings de module, ex.
"📊 Tableau de bord", ne comptent pas : ils ne sont jamais affichés à
l'utilisateur). Remplacé par un `ft.Icon(ft.Icons.CHECK_CIRCLE,
color=Colors.SUCCESS)` dans un `ft.Row` aux côtés du texte du titre —
même construction que `theme.section_title()` utilise pour tout
`PageHeader`. Un emoji dépend de la police/plateforme de rendu pour son
apparence (peut différer entre Windows/macOS/Linux) ; une icône Material
est garantie identique partout, comme chaque autre icône de l'app.
``STRINGS.summary_ok``/``summary_error`` gardent leurs préfixes "✓"/"✗"
— ce ne sont pas des emoji couleur mais des caractères typographiques
ASCII-compatibles à l'intérieur d'un rapport texte multi-ligne compact
(``"\n".join(details)``), une structure différente qui ne justifie pas
le même changement (transformer chaque ligne en `Row(Icon, Text)`
casserait le rapport compact en une liste de cartes, une complexification
que le brief interdit explicitement — "ne jamais complexifier
l'interface").

**Décision — tout espacement `ft.Column`/`ft.Row` doit venir de
`theme.Spacing`, même quand la valeur littérale coïncide avec un token**
`theme.py` documente depuis le Sprint 26 : "No view should hardcode ...
a raw padding int." Une recherche exhaustive (`grep -rn "spacing=[0-9]"`)
a trouvé 8 violations silencieuses de cette règle, jamais détectées par
un outil automatique (ce n'est pas une règle ruff/mypy, seulement une
convention documentée) : 6 occurrences de `spacing=2` (une valeur qui
n'existe même pas dans l'échelle `theme.Spacing`) et 2 occurrences de
`spacing=4` (qui coïncide avec `theme.Spacing.XXS` mais sans passer par
le token) — dans `views/preferences.py`, `views/about.py`,
`views/search.py`, `views/calendar.py` (×3) et `main_view.py` (×2,
boîtes de dialogue). Toutes remplacées par `theme.Spacing.XXS` — un
changement visuel de 2px→4px dans les 6 premiers cas (jugé imperceptible
sur un espacement titre/sous-titre déjà serré), aucun changement dans
les 2 derniers. Ce ratissage n'était possible qu'en cherchant
explicitement les nombres bruts plutôt qu'en relisant page par page —
une leçon pour la prochaine recette de ce type : `grep` la règle, ne pas
compter sur la relecture visuelle pour la détecter.

**Décision — les titres `EmptyState` ne se terminent jamais par un
point ; seules les phrases instructives avec un verbe en gardent un**
Six titres `EmptyState` existaient avant ce sprint, à peu près à moitié
avec un point final, moitié sans, sans qu'aucune règle n'ait jamais
tranché la question (chaque sprint avait suivi son propre instinct :
`weekend_empty_title`/`dashboard_weekend_championships_empty`/
`search_no_results` en avaient un ; `dashboard_next_race_empty`/
`calendar_season_explorer_empty`/`calendar_summary_empty_selection`
n'en avaient pas). Règle retenue : un titre `EmptyState` est un label
court, une locution nominale ("Aucune course ce week-end"), jamais une
phrase complète — il ne prend donc jamais de point final, à l'image de
tous les autres labels courts de l'app (libellés de nav, en-têtes de
section, puces). Une *phrase* instructive avec un verbe conjugué
(``weekend_next_hint``: "Prochain week-end disponible le {date}.",
``search_empty_query``: "Commencez à taper pour rechercher.") reste
correctement ponctuée — la distinction est grammaticale, pas
esthétique.

**Décision — "À propos" affiche la vraie version, pas un texte statique
sans numéro**
`about_version` valait "Version Alpha" — un texte qui ne dit jamais
*quelle* version, alors que le Dashboard affiche déjà
`motorsport_calendar.__version__` en toutes lettres depuis le Sprint 53
(section "État"). C'est la seule page de l'app qui parlait "de la
version" sans jamais préciser laquelle — une incohérence d'information,
pas seulement de texte. `about_version` devient un gabarit
(`"Version {version} — Alpha"`), et `build_about_view()` gagne un
paramètre `version: str | None = None` qui, quand omis, importe le vrai
`__version__` (import local dans la fonction, même convention que
`controller.py::get_dashboard_data`/`generate_calendar` et
`cli.py::version_callback`) — pas une nouvelle fonctionnalité (la
donnée existe déjà et est déjà montrée ailleurs), une cohérence
d'affichage entre deux endroits qui parlent de la même chose. Le
paramètre `version` existe surtout pour que les tests puissent fixer une
valeur déterministe sans dépendre du numéro de version réel du dépôt.

**Décision — `nav_home`/`nav_calendar` supprimées, pas conservées "au
cas où"**
Ces deux chaînes portaient un commentaire "Kept for backward compat"
mais n'étaient référencées nulle part dans le code — ni dans une API
publique versionnée, ni dans un test, ni dans une vue. Il n'existe pas
de mécanisme de compatibilité descendante à préserver ici (`Strings` est
un singleton interne, jamais un contrat externe) : les garder ne
protégeait rien, seulement une confusion potentielle pour un futur
lecteur se demandant si elles sont utilisées quelque part. Supprimées
avec un test dédié (`test_dead_backward_compat_nav_strings_removed`,
même patron que `test_wizard_strings_removed` du Sprint 43) verrouillant
qu'elles ne reviennent pas par erreur.

**Décision — les résultats de "Recherche" restent non cliquables,
identifiés mais volontairement non corrigés**
`_season_event_row` (Mon calendrier) et `_result_row` (Recherche)
affichent la même sorte d'information (un événement), mais seul le
premier est cliquable (ouvre la "fiche événement", Sprint 42). Corriger
cette incohérence nécessiterait d'ajouter `championship_id`/
`event_uid` à `SearchResultItem` — une évolution du modèle de données de
`gui/search_service.py`, explicitement hors périmètre du brief ("Aucune
évolution des services"). Documenté comme dette identifiée
(`docs/AI_CONTEXT.md`, piste `-18`) plutôt que corrigé en franchissant
la limite du périmètre du sprint.

**Conséquences**
- Convention explicite pour tout futur `PageHeader` : icône = variante
  pleine du `selected_icon` du rail de navigation correspondant.
- Convention explicite : jamais d'emoji dans l'UI rendue, uniquement des
  icônes Material via `ft.Icon`.
- Convention explicite : tout espacement passe par `theme.Spacing`,
  jamais un nombre brut, même quand il coïncide avec un token existant.
- Convention explicite : titres `EmptyState` sans point final ; phrases
  instructives avec verbe conservent le leur.
- "À propos" et le Dashboard affichent désormais la même information de
  version, cohérente et réellement informative.
- mypy/ruff : deltas nuls (39/157/0 inchangés) — chaque correction est
  visuelle ou textuelle, aucune ne touche une signature de callback.
- 7 nouveaux tests nets, aucune régression sur les 1961 précédents (1968
  total).
- Aucun commit effectué, conformément à la contrainte explicite du
  brief.

---

## ADR-044 — Nouveautés & Centre d'accueil : "Nouveautés" s'omet entièrement (pas un état vide), fabrique de fermeture partagée pour le bouton "Voir la version", navigation par clé string, `functional_providers` dérivé des entrées déjà récupérées

**Contexte**
Sprint 53. Le Dashboard était déjà la page d'accueil de facto depuis le
Sprint 39, mais purement informatif (stats saison, "Ce week-end",
"Prochain départ") — objectif : en faire le véritable point d'entrée du
produit en ajoutant 3 sections ("Nouveautés", "Accès rapides", "État de
Motorsport Calendar"), en réutilisant exclusivement `Dashboard`/
`UpdateService`/`FavoritesService`/`ProviderRegistry`, sans aucune
logique métier dans la vue, sans nouveau service, sans nouveau provider.

**Décision — "Nouveautés" s'omet entièrement quand il n'y a rien à
montrer, contrairement à chaque autre section du Dashboard**
Toutes les sections existantes (`_weekend_championships_section`,
`_next_race_section`) affichent toujours au moins un en-tête + un
`EmptyState` quand elles n'ont rien à montrer — un patron cohérent
depuis le Sprint 39. Le brief Sprint 53 spécifie pourtant, verbatim :
"aucune mise à jour → ne rien afficher" — pas "afficher un état vide
Nouveautés". `_news_section()` renvoie donc `ft.Control | None`
(contrairement à toutes les autres fonctions de section, qui renvoient
toujours `ft.Control`), et `_loaded_state()` n'ajoute la section au
corps de page que si elle n'est pas `None` — la seule section du
Dashboard capable de disparaître complètement. La garde couvre aussi le
cas défensif `update_available=True` avec `manifest=None` (qui ne
devrait jamais se produire en pratique, `UpdateService` couple toujours
les deux), pour ne jamais rendre une carte à moitié renseignée si cet
invariant venait à être rompu ailleurs.

**Décision — le bouton "Voir la version" réutilise le handler du
Sprint 51 via une fabrique de fermeture extraite, jamais une seconde
implémentation**
`main_view.py::_show_update_dialog` avait, depuis le Sprint 51, sa
propre fermeture inline pour ouvrir l'URL de release (`url_launcher` +
repli `subprocess.Popen` si le lancement échoue). La carte "Nouveautés"
a besoin exactement du même comportement pour son propre bouton. Plutôt
que de dupliquer cette logique une seconde fois (ce que le brief
interdit explicitement : "Aucune logique dupliquée"), la fermeture est
extraite en fonction nommée `_make_release_opener(url) -> Callable[
[ft.ControlEvent], Awaitable[None]]`, appelée une fois par site
d'utilisation (`_show_update_dialog` et le chargement du Dashboard),
chacune produisant un handler indépendant fermé sur sa propre URL — une
seule implémentation de "ouvrir une URL de release avec repli", deux
appelants.

**Décision — "Accès rapides" navigue via une indirection par clé
string, jamais un index `NavigationRail` codé en dur dans la vue**
`views/dashboard.py` ne doit connaître ni l'existence de `NavigationRail`
ni l'ordre de ses destinations (le brief : "Ne créer aucune logique
métier dans la vue"). Chaque carte appelle `on_navigate(key)` avec une
des 4 clés `"weekend"`/`"calendar"`/`"search"`/`"favorites"` —
`main_view.py` seul possède la table `_quick_access_nav_index: dict[str,
int]` qui traduit une clé en index, et la fonction `_navigate_to(key)`
qui met à jour `nav_rail.selected_index` + `content_area.content` +
`page.update()`. Si l'ordre des onglets change un jour, seule cette
table change — la vue Dashboard reste inchangée par construction, même
principe de découplage que `on_navigate` sur les autres vues du projet.

**Décision — `functional_providers` dérivé des entrées déjà récupérées,
aucune nouvelle métadonnée de capacité provider inventée**
Le brief demande "le nombre de fournisseurs réellement fonctionnels"
sans jamais coder de valeur en dur. Une approche aurait été d'ajouter un
flag `is_functional`/une méthode de sonde à `Provider` — rejetée : ce
serait une évolution du modèle de provider, hors périmètre explicite du
sprint ("Aucune évolution des modèles métier"). À la place,
`gui/dashboard.py::build_dashboard_data()` compte les `championship_id`
distincts parmi les `entries` déjà récupérées par
`controller._fetch_weekend_entries()` (2 années, réutilisé tel quel) —
un provider qui échoue systématiquement (stubs IMSA/WorldSBK) ne
contribue jamais d'entrée, donc ne compte jamais ici, alors qu'il compte
bien dans `active_championships` (`registry.enabled(config.providers)`,
simple lecture de configuration). L'écart honnête entre les deux
nombres est exactement ce que la section "État" doit révéler à
l'utilisateur — pas un défaut de calcul à corriger.

**Décision — les fetches "entrées week-end" et "vérification de mise à
jour" tournent en concurrence (`asyncio.gather`), pas séquentiellement**
`controller.get_dashboard_data()` a désormais besoin des deux résultats
pour construire `DashboardData`. Les deux appels (I/O réseau/cache
indépendants) sont lancés via `asyncio.gather()` — même patron déjà
établi au Sprint 50 pour les fetches provider concurrents, réutilisé ici
plutôt qu'un nouveau motif de concurrence inventé pour l'occasion.

**Conséquences**
- Dashboard désormais un vrai point d'entrée : nouveautés (conditionnel),
  navigation directe vers 4 destinations, aperçu d'état complet — sans
  qu'aucune des 3 nouvelles sections ne duplique de logique déjà
  possédée par `UpdateService`/`FavoritesService`/`ProviderRegistry`.
- `DashboardData` gagne 5 champs passthrough + 1 champ réellement calculé
  (`functional_providers`) — tous documentés dans le docstring du
  dataclass, aucun n'est jamais codé en dur.
- mypy : +1 erreur dans la même famille déjà documentée et acceptée
  (décalage stubs Flet 0.80/runtime 0.85.3) — le nouveau
  `ft.Button(on_click=on_view_release)` de la carte "Nouveautés" ; pas
  une nouvelle catégorie.
- 29 nouveaux tests nets (`test_gui_dashboard.py` pour la couche
  "compute", `test_gui_views.py` pour la couche vue, couvrant
  explicitement les 4 scénarios nommés par le brief), aucune régression
  sur les 1932 précédents (1961 total).
- Aucun commit effectué, conformément à la contrainte explicite du
  brief.

---

## ADR-043 — Préférences avancées : `PreferencesViewControls` (patron `CalendarViewControls`, pas valeur+callbacks), 3 clés sans service dédié, `PreferencesModel` repensé plutôt que supprimé

**Contexte**
Sprint 52. La page Préférences était un placeholder statique depuis le
Sprint 26 (rows "Disponible prochainement", jamais reliées à rien de réel)
— objectif : la transformer en véritable centre de configuration en
réutilisant les services déjà construits (`NotificationService`,
`FavoritesService`, la préférence `update_check_enabled`), sans logique
métier dans la vue, sans la moindre évolution du Design/Layout System.

**Décision — `PreferencesViewControls` porte des contrôles Flet
pré-construits, pas des couples valeur+callback**
Deux patrons coexistaient déjà dans le projet pour une page interactive :
`views/favorites.py` (données pures + callables, `build_favorites_view
(category_groups, favorite_count, on_favorite_click, on_category_toggle)`)
et `views/calendar.py` (`CalendarViewControls`, un dataclass qui porte des
`ft.Dropdown`/`ft.TextField`/`ft.Button` déjà construits avec leur
`on_click`/`on_change` câblé par `main_view.py`). Pour une page à 6
contrôles interactifs indépendants (2 `Switch`, 3 `Dropdown`, chacun son
propre préférence/service cible), le patron `CalendarViewControls` a été
choisi plutôt que celui de `favorites.py` : passer 6 callables nommés
séparément (un par contrôle) aurait été plus verbeux et moins direct que
de simplement construire chaque contrôle une fois, correctement câblé,
et de le transmettre tel quel. `views/preferences.py` ne fait plus que
disposer des objets déjà complets dans les `Section`/`CardList` du Layout
System — zéro logique métier, conforme à la lettre du brief ("la vue ne
fait qu'afficher le résultat").

**Décision — `update_check_enabled`/`default_year`/`ics_alarm_minutes`
n'ont pas de service dédié**
Trois nouvelles clés de préférence pilotées par la page, mais aucune ne
justifie un service au sens de `FavoritesService`/`NotificationService`
(qui existent parce qu'ils encapsulent une vraie logique — ordre
d'insertion, calcul de notifications à venir). Ici, chacune est un
`load_preferences()`/mutation d'une clé/`save_preferences()` — exactement
le même patron déjà utilisé directement par `main_view.py::_save_prefs()`
pour `selected_championships`/`last_output_dir` depuis le Sprint 44.
Ajouter trois classes-service d'une clé chacune aurait été de
l'abstraction non justifiée par la seule échelle du problème ("créer
uniquement ce qui est réellement nécessaire", brief). Les handlers vivent
directement dans `main_view.py`, à côté des `Switch`/`Dropdown` qu'ils
pilotent.

**Décision — `default_year` est une sentinelle (`"current"`), jamais une
année codée en dur**
Une préférence "année par défaut" naïvement stockée comme un entier figé
au moment de la sauvegarde deviendrait fausse dès l'année suivante — un
utilisateur qui choisit "garder l'année en cours" en 2026 se retrouverait
avec "Mon calendrier" ouvrant sur 2026 pour toujours, y compris en 2028.
`gui/models.py::resolve_default_year()` (pure, sans Flet, testée
indépendamment) résout `"current"` en `date.today().year` à chaque
lecture plutôt qu'à l'écriture — la préférence par défaut ne devient
jamais obsolète. Une année littérale reste possible (l'utilisateur peut
explicitement épingler une saison), simplement pas la valeur par défaut.

**Décision — `ics_alarm_minutes` override `config.ics.alarm_minutes`
pour les exports GUI uniquement, jamais pour la CLI**
Le brief liste "rappel avant export (si pertinent)" pour la section
Calendrier. `IcsExporter(alarm_minutes=...)` et `IcsConfig.alarm_minutes`
existaient déjà (Sprint 1-ish) — la seule pièce manquante était un moyen,
pour un utilisateur GUI, de le changer sans éditer `config.yaml` à la
main. `gui/controller.py::generate_calendar()` lit désormais
`load_preferences().get("ics_alarm_minutes", config.ics.alarm_minutes)`
avant de construire l'exporteur — repli sur la config si jamais
enregistrée (comportement inchangé pour tout utilisateur qui n'ouvre
jamais la page Préférences, puisque le défaut de la préférence, `30`,
est identique au défaut de `IcsConfig`). `cli.py::generate`
(`motocal generate`) reste volontairement inchangé — la CLI n'a pas de
fichier de préférences GUI et ne doit pas en dépendre ; elle continue de
ne lire que `config.yaml`, exactement comme avant ce sprint.

**Décision — `PreferencesModel` repensé, pas supprimé**
Les 6 champs hérités (`timezone`/`first_day_of_week`/
`favorite_championships`/`preferred_calendar`/`bapps_sync_enabled`)
étaient tous décoratifs depuis leur création — `favorite_championships`
en particulier explicitement documenté comme "superseded" par
`FavoritesService` depuis le Sprint 44 (dette technique enregistrée dans
`docs/AI_CONTEXT.md`, désormais résolue par ce sprint). Plutôt que de
supprimer purement et simplement le dataclass, il a été repensé pour ne
porter que les 3 champs que le brief nomme explicitement pour la section
"Application" (`theme`/`language`/`time_format`) — le brief demande que
ces préférences soient "pensées pour évoluer" : un modèle typé, même
inerte (aucune persistance, aucune lecture ailleurs dans l'app), coûte
peu et évite qu'un futur sprint doive en inventer la forme depuis zéro.
`views/preferences.py::_PREF_ROWS` (rows "Disponible prochainement",
patron inchangé depuis le Sprint 31) pointe désormais vers ces 3 champs
au lieu des 6 précédents.

**Décision — `ft.Dropdown` utilise `on_select`, pas `on_change`**
Découverte par introspection directe (`inspect.signature`) avant d'écrire
le code, plutôt que supposée par analogie avec `ft.Switch` (qui utilise
bien `on_change`) : cette version de Flet (0.85.3) expose `on_select`
sur `Dropdown`, `on_change` sur `Switch` — deux noms différents pour un
concept similaire. `year_dropdown` (Sprint 43) utilisait déjà
`on_select`, un indice disponible dans le code existant qui aurait pu
suffire, mais vérifié quand même plutôt que supposé par lecture rapide.

**Conséquences**
- Page Préférences réelle : Notifications (3 réglages), Mises à jour (1),
  Calendrier (2), Application (3, préparés/inertes) — 9 contrôles au
  total, zéro nouvelle page, zéro nouveau provider.
- `NotificationService`/`update_check_enabled` (Sprints 46/51,
  respectivement "fondations sans interface" documentées comme telles)
  ont enfin leur UI — deux lignes de dette technique explicitement
  résolues par ce sprint.
- mypy : +12 erreurs dans la même famille déjà documentée et acceptée
  (décalage stubs Flet 0.80/runtime 0.85.3) — 2 `Switch` + 3 `Dropdown`
  chacun à son site d'appel ; pas une nouvelle catégorie.
- 9 nouveaux tests nets (plusieurs classes intégralement réécrites :
  `test_gui_preferences_model.py`, `test_gui_views.py::
  TestPreferencesView`), aucune régression sur les 1923 précédents.
- Section "Application" reste inerte par construction — documenté comme
  la limite assumée de ce sprint, pas un défaut caché.

---

## ADR-042 — Vérification des mises à jour : URL de manifeste en `config.yaml` (jamais codée en dur), préférence d'opt-out sans UI, aucune action automatique au-delà de l'ouverture du navigateur

**Contexte**
Sprint 51. Motorsport Calendar est désormais une Alpha distribuable
(Sprint 49) — objectif : informer l'utilisateur qu'une nouvelle version
existe, sans jamais rien télécharger, installer, ou redémarrer
automatiquement, et sans coupler la logique à GitHub ni à aucune
plateforme particulière ("le manifeste doit pouvoir provenir de n'importe
quelle URL").

**Décision — `UpdateService` (`gui/update_service.py`) totalement
indépendant de Flet et de toute plateforme d'hébergement**
Même contrat "utilisable seul, zéro `import flet`" que `FavoritesService`/
`NotificationService`/`SearchService` (Sprints 44-45-46) — vérifié par un
test dédié inspectant le source du module plutôt que de faire confiance à
une relecture manuelle. `manifest_url` et `current_version` sont des
paramètres du constructeur, jamais lus en interne (ni depuis
`motorsport_calendar.__version__`, ni depuis une constante d'URL) — la
même discipline "aucun état global caché, tout est injecté par
l'appelant" déjà établie pour `now` dans
`NotificationService.compute_notifications`. Conséquence directe : le
module lui-même n'a strictement aucune connaissance de GitHub, d'un CDN,
ou de tout autre hébergeur — un simple GET JSON sur une URL absolue,
n'importe laquelle.

**Décision — l'URL du manifeste vit dans `config.yaml`
(`UpdateConfig.manifest_url`), jamais codée en dur dans le code**
Deux endroits auraient pu porter cette URL : une constante dans
`update_service.py`, ou une entrée de configuration. La constante a été
écartée immédiatement — même une URL "neutre" en apparence coderait en
dur une dépendance à un hébergeur précis, contredisant "ne pas coupler la
logique à GitHub" pris au sens large (l'esprit de la règle, pas seulement
sa lettre). `config/models.py::UpdateConfig` (vide par défaut) suit
exactement le patron déjà établi par `CacheConfig`/`IcsConfig`/
`ProvidersConfig` : un `ConfigService().update.manifest_url` résolu via
`config.yaml`, avec un défaut inoffensif (chaîne vide = vérification
désactivée de fait, aucun appel réseau) plutôt qu'un placeholder qui
ressemblerait à une vraie URL. Conséquence assumée : la fonctionnalité
est fonctionnelle et entièrement testée dès ce sprint, mais reste un
no-op silencieux en usage réel tant que personne n'a publié de manifeste
et renseigné son URL — documenté comme piste `docs/TODO.md`, pas un défaut
de ce sprint.

**Décision — comparaison de versions numérique, jamais lexicographique,
avec complément à zéro pour les longueurs différentes**
`is_newer(current, candidate)` parse chaque version en tuple d'entiers
(`parse_version`) et compare les tuples plutôt que les chaînes — le piège
explicitement nommé par le brief (`"0.4.9" > "0.4.10"` en comparaison de
chaînes, car `'9' > '1'` au premier caractère différent) est vérifié en
direct dans un test comme sanity-check du bug évité, pas seulement
affirmé. Un second piège, plus subtil et non nommé par le brief, a été
découvert en réfléchissant à la comparaison de tuples Python natifs :
`(0, 5) < (0, 5, 0)` — comparer `"0.5"` et `"0.5.0"` sans compléter à la
même longueur aurait rendu la forme plus longue faussement "plus
récente". Les deux tuples sont donc complétés à zéro jusqu'à la longueur
du plus long avant comparaison, pour que `"0.5"` et `"0.5.0"` soient
traitées comme rigoureusement identiques.

**Décision — `UpdateService.check_for_update()` ne lève jamais, capture
tout dans `UpdateCheckResult.error`**
Un manifeste distant peut échouer de multiples façons indépendantes :
réseau absent, timeout, statut HTTP d'erreur, JSON malformé, champs
manquants, version illisible. Chacune de ces défaillances est capturée à
son niveau exact (fetch HTTP, parsing JSON, validation du manifeste,
parsing de version) et renvoyée via `UpdateCheckResult(update_available=
False, error=...)` — jamais propagée en exception. Une vérification de
mise à jour qui plante le démarrage de l'application serait
objectivement pire que l'absence de la fonctionnalité elle-même ;
`main_view.py`'s propre `except Exception` autour de l'appel n'est donc
qu'un filet de sécurité de dernier recours, pas le mécanisme principal.

**Décision — `update_check_enabled` : la préférence existe et est lue,
aucune UI ne l'expose ce sprint**
Le brief demande explicitement de "prévoir la possibilité d'ignorer la
vérification (préférence future)" — formulation qui invite à poser les
fondations sans nécessairement livrer une interface. Suit exactement le
précédent déjà posé par les préférences de notifications au Sprint 46
("moteur construit, aucune UI branchée dessus") : une nouvelle clé
`update_check_enabled` (défaut `True`, dans `gui/preferences.py`) que
`gui/controller.py::check_for_update()` lit et respecte avant toute
résolution d'URL — un futur sprint qui construit une vraie page
Préférences n'a besoin de brancher qu'une case à cocher, la logique
d'application existe déjà. `check_for_update()` accepte aussi des
overrides explicites (`current_version`/`manifest_url`) réservés aux
tests — même patron que `now: datetime | None = None` déjà utilisé par
`get_upcoming_weekend`/`get_dashboard_data`.

**Décision — la boîte de dialogue n'offre qu'une seule action : ouvrir le
navigateur**
`_show_update_dialog` (`main_view.py`) affiche version actuelle, nouvelle
version, résumé, et un bouton "Voir la version" qui ouvre `manifest.url`
via `url_launcher` — même patron exact (et même repli
`subprocess.Popen` sous Windows en cas d'échec) que le lien GitHub
d'`views/about.py::on_github_click`. Le champ `mandatory` du manifeste
est surfacé comme un simple badge textuel, jamais comme un blocage du
bouton Fermer ou une désactivation de la boîte de dialogue — inventer un
comportement "forcé" à partir de ce champ aurait été une forme
d'installation/mise à jour imposée, explicitement exclue par le brief
("aucune mise à jour automatique... aucun auto-restart"), alors même que
rien ne le demandait explicitement pour ce champ précis.

**Conséquences**
- Nouveau `gui/update_service.py`, `config/models.py::UpdateConfig`,
  clé `gui/preferences.py::update_check_enabled`,
  `gui/controller.py::check_for_update()`, boîte de dialogue dans
  `main_view.py` — zéro provider créé ou modifié, zéro changement de
  comportement pour toute fonctionnalité existante.
- 58 nouveaux tests, aucune régression sur les 1865 précédents.
- La fonctionnalité est un no-op silencieux tant qu'aucun manifeste réel
  n'est publié et référencé — documenté comme la seule vraie limite de ce
  sprint, pas un défaut caché.
- mypy : +3 erreurs dans la même famille déjà documentée et acceptée
  (décalage stubs Flet 0.80/runtime 0.85.3) — `update_check_task`, boutons
  de la nouvelle boîte de dialogue ; pas une nouvelle catégorie de dette.

---

## ADR-041 — Audit & Consolidation : `mypy.ini` relâché pour les tests (pas pour le code source), dette Flet stub-version documentée et non corrigée, fetch providers rendu concurrent

**Contexte**
Sprint 50. Premier sprint de consolidation pure après 49 sprints consécutifs de
développement fonctionnel — aucune fonctionnalité, aucun provider, aucune page,
aucun changement de comportement utilisateur. Objectif : auditer l'ensemble du
projet, réduire la dette technique au maximum, sans jamais risquer le
comportement existant. Baseline mesurée avant toute modification (`git stash`
temporaire vers le dernier commit réel, pour distinguer la dette héritée des
sprints précédents de toute dette qui aurait pu être introduite pendant ce
sprint lui-même) : 149 erreurs Ruff, 87 erreurs mypy sur
`motorsport_calendar/`, 402 erreurs mypy sur `tests/`.

**Décision — `mypy.ini` : exclure `gui/build/`, jamais scanné auparavant**
Les artefacts du premier build Flet réel (Sprint 49, `flet build linux`)
avaient laissé un arbre `motorsport_calendar/gui/build/` sur disque (gitignoré,
donc invisible en `git status`, mais toujours présent physiquement) qui
empêchait purement et simplement `mypy motorsport_calendar` de s'exécuter
("This file shadows library module 'types'"). Ajout d'un `exclude` dans
`mypy.ini` plutôt qu'une suppression manuelle du dossier — la prochaine
personne qui relance un build Flet ne cassera plus mypy par accident.

**Décision — relâcher `[mypy-tests.*]` au-delà de `disallow_untyped_defs`/
`disallow_any_generics`, jamais le code source**
402 erreurs mypy dans `tests/`, dont l'écrasante majorité provenait d'un seul
phénomène : `unittest.mock.AsyncMock`/`MagicMock` substitués à des attributs
typés précisément (ex. `provider.fetch_events: Callable[[str, int],
Coroutine[...]]` remplacé par un mock, puis `mock.assert_awaited_once_with(...)`
— `Callable` n'a pas cet attribut du point de vue de mypy, bien que ce soit
parfaitement valide à l'exécution). Ce n'est pas une dette de *test*, c'est un
angle mort connu et documenté de mypy face à `unittest.mock` sans plugin dédié
— confirmé en vérifiant qu'aucune de ces erreurs ne recouvrait un vrai bug
(les 1863 tests passaient déjà tous avant ce sprint). Plutôt que d'ajouter des
`cast()` un par un sur des dizaines de sites d'appel (bruit syntaxique pur,
zéro gain de sécurité réelle puisque le mock EST le comportement voulu du
test), la section `[mypy-tests.*]` de `mypy.ini` a été étendue
(`disallow_untyped_calls`, `check_untyped_defs`, `warn_return_any` désactivés
pour les tests uniquement) — pratique standard pour tout projet Python testant
abondamment via des doubles de test dynamiques. `motorsport_calendar/` reste
en `strict = True` intégral, sans aucune exception : cette décision ne réduit
la rigueur que là où elle produisait du bruit, jamais sur le code livré aux
utilisateurs. Effet : 402 → 210 erreurs sans toucher un seul fichier de test.
Complété par la suppression mécanique de 24 `# type: ignore` devenus
inutiles (certains rendus obsolètes par ce relâchement, d'autres déjà stables
— vérifiés un par un via mypy lui-même, jamais supposés) et par une
factorisation ciblée (`test_aco_sports_event_base.py::TestSessionTypeForLabel`,
14 occurrences d'un même pattern non-narrowed remplacées par un helper
`_type_for()`), portant le compte final à 157 — le solde restant est détaillé
dans `docs/AUDIT.md` §4 et laissé en l'état.

**Décision — dette mypy source (`dict`/`list` nus) corrigée mécaniquement,
sauf un cas nécessitant un `cast()` explicite**
87 → 23 erreurs. L'écrasante majorité provenait d'annotations `dict`/`list`
sans paramètres génériques (héritage d'un typage progressif jamais terminé
sprint après sprint) — remplacées par `dict[str, Any]`/`list[Any]`, sans
changement de comportement (ce sont des JSON bruts d'API tierces, `Any` est
la vérité honnête de leur contenu). Un seul cas a demandé une réflexion :
`jolpica.py::JolpicaSource._get_json` recevait `raw` typé
`list[Any] | dict[str, Any]` depuis `HttpCache.get_json` (union générique
côté signature de cache) mais l'API Jolpica ne renvoie **jamais** une liste à
cet endpoint précis — un `cast(dict[str, Any], raw)` documente cette
connaissance métier plutôt que de complexifier la fonction avec un
`isinstance` inutile à l'exécution. Deux packages de stubs manquants
(`types-PyYAML`, `types-icalendar`) ajoutés aux dépendances dev plutôt que
des suppressions locales `# type: ignore[import-untyped]` — élimine 5
erreurs d'un coup et bénéficiera à tout futur sprint touchant ces modules.

**Décision — le bug réel trouvé (`core/service.py::CalendarService`) est
corrigé, la classe reste orpheline**
L'audit mypy complet a révélé que `CalendarService.export_championship`
passait un `Championship` entier à `Exporter.export()`, qui attend une liste
d'`Event` — une confusion entre métadonnées de championnat et événements à
exporter, jamais détectée car cette classe n'est appelée par **aucun** code
réel (ni CLI, ni GUI, confirmé par recherche exhaustive ; coverage à 0 % sur
le corps de la méthode). Corrigée pour de bon (récupère désormais les
événements via `provider.fetch_events` avant export) : zéro risque puisque
rien n'exécute ce chemin aujourd'hui, mais laisser un bug connu dans le
code source — même mort — contredirait directement l'objectif du sprint. La
classe elle-même n'est **pas** supprimée ni câblée : elle n'a été demandée
par aucun brief, et "code mort mais correct" est un état strictement
meilleur que "code mort et buggé", sans qu'il soit nécessaire de trancher son
avenir dans ce sprint (voir piste dans `docs/TODO.md`).

**Décision — dette Flet stub-version (23 + partie des 157 erreurs) documentée,
délibérément non corrigée**
Famille connue depuis le Sprint 26 : le code a été écrit contre les stubs de
types Flet 0.80, mais Flet 0.85.3 est réellement installé et son typage des
callbacks (`on_click`, `on_change`) et de certains attributs de `Control` a
changé entre les deux versions. Non corrigée : la corriger correctement
demanderait de réécrire des signatures de callback dans `main_view.py`
(864 lignes, la plus grande fonction du projet en son sein) avec un risque
réel de régression comportementale pour un gain de vérification statique
uniquement — le runtime Flet reste permissif, tous les tests passent. Un
changement pesant ce risque pour ce bénéfice contredirait directement
"aucun changement fonctionnel". Réévaluation recommandée si/quand une
version de Flet aligne enfin ses stubs sur son propre runtime.

**Décision — fetch des providers rendu concurrent (`cli.py::generate`,
`gui/controller.py::generate_calendar`), mesuré avant et après**
Seule optimisation de performance réalisée ce sprint (brief : "ne réaliser
une optimisation que si elle est mesurable"). Les deux fonctions attendaient
chaque provider séquentiellement (`for cid, prov in provider_list: await
prov.fetch_events(...)`) alors que chacun des 17 championnats interroge une
API distante totalement indépendante des 16 autres — remplacé par
`asyncio.gather` sur une coroutine `_fetch_one` extraite par provider
(gestion d'erreur par provider strictement inchangée). Mesuré à deux
niveaux : (1) benchmark synthétique préalable (10 providers simulés à
latence égale) donnant ~10x ; (2) deux tests de non-régression permanents
(`TestGenerateConcurrency`, `TestGenerateCalendarConcurrency`) qui mesurent
le *spread* des timestamps de démarrage de chaque appel provider mocké
plutôt qu'un budget de temps total (qui serait pollué par le coût fixe et
sans rapport de `registry.discover()`/`ConfigService()` avant même d'atteindre
le fetch) — et qui ont été **vérifiés pour échouer contre l'ancienne
implémentation séquentielle** avant d'être validés contre la nouvelle,
plutôt que d'être des tests qui passeraient de toute façon quel que soit le
code. `asyncio.gather` préserve l'ordre de la liste d'entrée dans son
résultat : fichier ICS final, ordre des événements et résumés affichés
restent strictement identiques à avant — seul le temps d'exécution change.
Aucune donnée partagée entre providers à un niveau dangereux sous
concurrence (`HttpCache` partagé mais chaque écriture cible un fichier
distinct par clé URL+params ; chaque source construit son propre
`httpx.AsyncClient`, conçu pour l'usage concurrent).

**Décision — docstrings publiques : combler les vrais manques, jamais
dupliquer une méthode déjà documentée sur son ABC**
367 fonctions/classes publiques scannées par AST, 103 signalées sans
docstring au premier passage. Triage systématique avant toute correction :
lecture de chaque ABC concernée (`Provider`, `Formula1Source`, etc.) pour
vérifier si le contrat est déjà pleinement documenté à ce niveau — 76 des
103 cas sont des redéfinitions triviales d'une méthode déjà documentée
(`WecProvider.name -> "wec"`, etc.), convention Python standard de ne pas
dupliquer la documentation d'un override trivial. Les 21 vrais manques
(propriétés/méthodes qui n'overridaient rien) ont reçu des docstrings d'une
ligne, factuelles, jamais redondantes avec le nom déjà auto-documentant.

**Conséquences**
- Ruff : 149 → 0. mypy source : 87 → 23 (une seule famille documentée). mypy
  tests : 402 → 157 (deux familles documentées, `mypy.ini` relâché
  proportionnellement, jamais sur le code livré).
- Un bug réel corrigé, zéro risque (code jamais exécuté en pratique).
- Deux fonctions de production plus rapides pour de vrai (fetch concurrent),
  avec des tests qui prouvent la régression qu'ils préviennent plutôt que de
  l'affirmer.
- Nouveau `docs/AUDIT.md` : rapport d'audit complet, à ré-auditer plutôt qu'à
  maintenir en continu (contrairement à `docs/AI_CONTEXT.md`).
- `gui/main_view.py::build_main_view` (771 lignes) identifiée comme seule
  vraie anomalie de taille du projet — délibérément non découpée ce sprint,
  documentée comme recommandation prioritaire pour un futur sprint dédié
  avec vérification visuelle réelle.
- Aucune fonctionnalité, aucun provider, aucune page, aucun changement de
  comportement utilisateur — conforme au brief. 1863 → 1865 tests (+2,
  non-régression performance), 0 régression, couverture stable ~97 %.

---

## ADR-040 — Packaging Alpha : `utils/paths.py` remplace les chemins codés en dur, `assets_dir` résolu au fichier plutôt qu'au CWD, assets intégrés sans câbler les vues

**Contexte**
Sprint 49. Brief explicitement non-fonctionnel : "aucun nouveau provider, aucune
nouvelle page, aucune évolution métier, aucun changement de Design System" — objectif
unique, rendre Motorsport Calendar distribuable (Linux + Windows) via la procédure
officielle `flet build`, sans changer le comportement de l'application. Trois zones à
vérifier explicitement par le brief : préférences (créées automatiquement, conservées
après fermeture, fonctionnelles sous Linux et Windows), cache (idem + indépendant du
dépôt Git), exports ICS (aucun chemin du dépôt, uniquement des chemins fournis par
l'utilisateur).

**Décision — `utils/paths.py` (`user_config_dir`/`user_cache_dir`), jamais
`platformdirs`**
Trois emplacements par défaut se sont révélés soit codés en dur pour Linux/macOS
uniquement, soit relatifs au répertoire de travail du process (CWD) plutôt qu'à un
répertoire utilisateur stable — tous les trois de la même famille de bug :
`cache/http_cache.py::HttpCache.__init__` (`Path(".cache")`, CWD-relatif — écrivait
silencieusement dans le dépôt Git en développement), `gui/preferences.py::_PREFS_FILE`
(`~/.config/motorsport-calendar/`, codé en dur), `config/service.py::
ConfigService._DEFAULT_PATHS` (même limitation pour `config.yaml` niveau utilisateur).
Plutôt qu'ajouter une dépendance externe (`platformdirs`, la solution la plus courante
dans l'écosystème Python pour ce problème), un module interne minimal a été préféré :
le projet a déjà établi le patron `sys.platform == "win32"` pour ce type de branchement
(`gui/main_view.py::_open_folder`, `gui/views/about.py`), et le besoin réel se limite à
deux fonctions (config vs cache) suivant chacune une convention déjà standardisée —
XDG Base Directory sous Linux (`$XDG_CONFIG_HOME`/`$XDG_CACHE_HOME`, repli
`~/.config`/`~/.cache`), `%APPDATA%`/`%LOCALAPPDATA%` sous Windows (roaming/persisté vs
local/jetable, le pendant exact de la distinction XDG). Piège évité : `Path("")` est
*truthy* en Python (`== Path(".")`) — une variable d'environnement définie mais vide
aurait donc silencieusement gagné face au repli si le code avait testé
`Path(os.environ.get(...)) or fallback` ; la variable brute est testée pour sa
véracité (`if xdg`) avant d'être enveloppée dans `Path(...)`.

**Décision — le premier chemin `config.yaml` (`Path("config.yaml")`, relatif au CWD)
n'est pas un bug de packaging**
`ConfigService._DEFAULT_PATHS` a deux entrées : `Path("config.yaml")` (CWD, priorité 1)
puis désormais `user_config_dir("motorsport-calendar") / "config.yaml"` (priorité 2,
corrigée ce sprint). La première reste intentionnellement CWD-relative — c'est une
commodité de lecture explicite ("un `config.yaml` dans le dossier courant l'emporte"),
jamais un chemin d'écriture par défaut ni une dépendance cachée au dépôt Git ; un
utilisateur packagé qui place un `config.yaml` à côté de l'exécutable bénéficie du même
comportement qu'un développeur qui en place un à la racine du dépôt. Seule la seconde
entrée — le vrai "défaut si rien d'autre n'existe" — relevait du bug de packaging visé
par le brief.

**Décision — `gui/app.py::_ASSETS_DIR` résolu via `Path(__file__).parent`, jamais un
littéral, jamais CWD-relatif**
Quatrième bug, spécifique à Flet et découvert en lisant le source de `flet/app.py` :
`assets_dir` passé à `ft.run()` s'y résout via
`__get_assets_dir_path(assets_dir, relative_to_cwd=True)` — c'est-à-dire relativement
au **répertoire de travail au lancement du process**, pas au fichier appelant. Un
`assets_dir="assets"` (chaîne relative, la forme la plus naturelle à écrire) fonctionne
donc par pur hasard en développement (lancé depuis la racine du dépôt) et échoue
silencieusement à trouver les assets dès que packagé/lancé depuis n'importe quel autre
répertoire. Corrigé par `_ASSETS_DIR = str(Path(__file__).parent / "assets")` — un
chemin absolu **calculé à l'exécution**, jamais un littéral écrit en dur dans le
source : l'interdiction du brief ("aucun chemin absolu") vise les chaînes codées en dur
propres à une machine, pas ce patron portable standard de résolution de ressources
embarquées relativement au module qui les référence.

**Décision — assets officiels intégrés au build sans câbler les vues**
Tension explicite dans le brief entre "vérifier que tous les assets sont correctement
intégrés au build" (suggère une intégration réelle) et "aucune évolution du Design
System"/"ne pas modifier les vues autrement que pour résoudre un problème de packaging"
(interdit les changements visuels). Résolue en distinguant "intégré au build" (présent,
bundlé, adressable via `assets_dir` — satisfait par la copie octet-identique des 6
fichiers officiels `BApps-Studio/.../Branding/` dans `gui/assets/`) de "consommé par
chaque appel de vue" (remplacer `theme.logo_placeholder()` par les vraies images —
un chantier de Design System à part entière, explicitement hors périmètre). Seules deux
exceptions jugées relever du packaging plutôt que du Design System : `page.window.icon
= "icon.png"` (chrome de fenêtre géré par l'OS, pas une vue) et `icon_windows.ico`
(convention Flet pour l'icône de l'exécutable Windows lui-même). Documenté dans
`gui/assets/logo/README.md` pour qu'un futur sprint sache exactement où reprendre.

**Décision — export ICS vérifié, non modifié**
`exporters/ics.py::IcsExporter.export(events, output_path)` s'est révélé déjà
entièrement propre à la lecture du source : `output_path` est un `Path` fourni par
l'appelant sans aucun défaut ni référence au dépôt. Aucune modification nécessaire ;
plutôt que de laisser cette propriété implicite, `tests/test_ics_exporter.py::
TestExportIsPackagingSafe` la rend désormais explicite et vérifiée (export loin de tout
chemin du dépôt, indépendance au CWD via `monkeypatch.chdir`, acceptation d'un chemin
absolu).

**Décision — build Linux validé en direct sur cette machine, build Windows documenté
mais non exécuté**
Conformément au choix de l'utilisateur ("build réel plutôt que validation
structurelle seule"), `flet build linux motorsport_calendar/gui --module-name app` a
été exécuté pour de vrai (pas simulé) : deux corrections de la commande elle-même
découvertes en cours de route (`python_app_path` doit pointer sur le dossier contenant
`app.py`, pas la racine du dépôt ; `--module-name app` requis car l'entrée n'est pas
`main.py`), le SDK Flutter (3.41.7) s'installe seul au premier lancement, et le build
atteint l'étape de compilation native — confirmant que la configuration du packaging
elle-même est correcte de bout en bout. Seul blocage : outillage système manquant sur
cette machine de développement (`binutils clang cmake llvm lld ninja-build pkg-config
libgtk-3-dev libunwind-dev`, liste complète confirmée via la documentation officielle
Flet après qu'une première liste donnée à l'utilisateur se soit révélée incomplète) —
un gap machine, pas un bug projet, documenté avec la commande d'installation exacte
dans `docs/PACKAGING.md`. Le build Windows n'a jamais pu être exécuté (aucune machine
Windows disponible dans cet environnement, et Flet ne permet pas la cross-compilation
Windows depuis Linux/macOS) — procédure et prérequis transcrits fidèlement depuis la
documentation officielle Flet, avec une mention honnête "non exécuté ce sprint" plutôt
que de prétendre à une validation qui n'a pas eu lieu.

**Conséquences**
- Préférences, cache et `config.yaml` niveau utilisateur résolvent désormais tous les
  trois vers un répertoire utilisateur idiomatique par plateforme, jamais vers le CWD
  ni un chemin Linux-only codé en dur — testé par `tests/test_utils_paths.py` (12
  tests) et les nouvelles classes de `test_http_cache.py`/`test_config_service.py`/
  `test_gui_preferences.py`.
- `gui/app.py` charge désormais réellement ses assets (`assets_dir` décommenté et
  corrigé) — auparavant commenté depuis le Sprint 23, jamais actif.
- Piège de test évité deux fois : ni instancier `HttpCache()` avec son défaut (créerait
  un vrai répertoire sur la machine dev) ni lire `preferences._PREFS_FILE` en direct
  (toujours écrasé par le fixture autouse `_isolated_gui_prefs`) ne peuvent servir de
  test — vérifiés respectivement via `inspect.signature(...).parameters[...].default`
  et `inspect.getsource(...)`, sans jamais toucher le vrai système de fichiers.
- 26 nouveaux tests, 1863 total. Nouveau `docs/PACKAGING.md` documente la procédure
  officielle complète (Linux + Windows), ce qui a été réellement vérifié, et ce qui
  reste explicitement hors périmètre (installeur, auto-update, signature de code,
  macOS, CI/CD).
- `theme.logo_placeholder()` reste non câblé sur les vraies images (dette documentée,
  `docs/AI_CONTEXT.md`) ; le build Linux reste à finaliser une fois l'outillage système
  installé, et le build Windows reste entièrement à exécuter une fois une machine
  Windows disponible.

---

## ADR-039 — Finalisation des providers : WEC rejoint `AcoSportsEventSource` via des points d'extension, IMSA/WorldSBK restent des stubs après ré-investigation

**Contexte**
Sprint 48. Trois championnats restaient volontairement en mode "stub" depuis leurs
sprints respectifs (WEC Sprint 29, IMSA Sprint 36, WorldSBK Sprint 38) : `raise
NotImplementedError` dans leurs sources "officielles", enregistrées et intégrées
partout (registry, "Ce week-end", agrégateur CLI) pour valider l'architecture sans
inventer de données. Objectif du brief : remplacer les implémentations temporaires par
des providers fonctionnels, en recherchant activement — API officielle en priorité,
source stable à défaut, scraping en dernier recours — plutôt que de se contenter des
conclusions déjà écrites dans `docs/DATA_SOURCES.md`. Contrainte explicite : conserver
les abstractions existantes, ne jamais casser les providers déjà fonctionnels, créer
une nouvelle famille de providers seulement si elle apparaît naturellement.

**Décision — re-vérifier les trois pistes en direct plutôt que faire confiance à la
documentation existante**
Les investigations Sprint 36 (IMSA)/Sprint 38 (WorldSBK) sont détaillées et déjà
documentées comme des échecs, mais un site web change avec le temps — la seule façon
honnête de répondre à "rechercher la meilleure source disponible" était de refaire
chaque vérification en direct plutôt que de recopier une conclusion vieille de
plusieurs sprints. Pour WEC, la piste du Sprint 35 ("fiawec.com tourne peut-être sur le
même CMS qu'ELMS/MLMC, jamais vérifié sur une vraie manche") a été suivie jusqu'au bout
pour la première fois.

**Décision — WEC : sous-classer `AcoSportsEventSource`, jamais un nouveau scraper**
Vérification en direct sur `fiawec.com/en/race/6-hours-of-imola-2026` (et 7 autres
manches réelles de la saison 2026) : structure JSON-LD `SportsEvent`/`subEvent`
identique à celle déjà exploitée pour ELMS/MLMC (Sprint 35, `aco_series/
sports_event_base.py`). `OfficialWecSource` devient donc `class
OfficialWecSource(AcoSportsEventSource, WecSource)` — même patron exact que `AcoScraperSource`
pour ELMS/MLMC — plutôt qu'un scraper WEC indépendant, conforme à "conserver les
abstractions existantes". Nom de classe et clé d'enregistrement `"official"` conservés
tels quels (jamais renommés en `"aco_scraper"` comme ELMS/MLMC l'ont fait) : `ProvidersConfig.wec`
a un défaut explicite `source="official"` (`config/models.py`) — renommer la clé
enregistrée aurait cassé silencieusement tout `config.yaml` s'appuyant sur ce défaut,
violation directe de "ne jamais casser les providers existants". "official" reste par
ailleurs une description honnête : fiawec.com est bien le site officiel de la FIA WEC,
le scraping JSON-LD n'y change rien.

**Décision — étendre la base partagée via des points d'extension explicites, jamais la
dupliquer**
Trois divergences réelles de WEC par rapport à ELMS/MLMC ont été découvertes en
vérifiant les données, pas supposées à l'avance :

1. **Labels de session supplémentaires** ("Free Practice 4", "Hyperpole", "Warm-up",
   absents chez ELMS/MLMC) — ajoutés à `_LABEL_RULES` (partagé), purement additifs :
   aucun de ces libellés n'apparaît jamais dans le JSON-LD d'ELMS/MLMC, confirmé par
   leur suite de tests existante intégralement verte sans modification après l'ajout.
   "Free Practice 4" (Le Mans uniquement, une 4e séance d'essais libres de nuit) mappé
   sur le type générique `FREE_PRACTICE` plutôt que d'inventer un `SessionType.FP4` non
   supporté par le modèle de domaine ; "Hyperpole" mappé sur `SessionType.HYPERPOLE`
   (déjà présent depuis les tout premiers sprints WEC) ; "Warm-up" mappé sur `TEST`, le
   type existant le plus proche — délibérément distinct de `FREE_PRACTICE` bien que les
   deux libellés partagent une racine "essais/pratique", pour éviter que le mécanisme
   de fusion multi-slots existant ne les combine en une seule session absurde couvrant
   ~37 heures (FP4 le jeudi soir, Warm-up le samedi matin du même week-end du Mans).
2. **Exclusion de "prologue"** — ajoutée à `_EXCLUDED_SLUG_KEYWORDS` (partagé),
   symétrique à l'exclusion déjà existante des tests pré-saison ELMS/MLMC
   ("official-test"/"collective-test").
3. **Durée de course non déductible de l'`endDate` JSON-LD** — contrairement à
   ELMS/MLMC ("confirmé exact pour leurs manches régulières" selon la documentation
   existante du module), l'`endDate` de fiawec.com s'est révélé être systématiquement
   minuit du dernier jour annoncé, sans rapport avec l'heure de fin réelle de la course.
   Pour la plupart des manches WEC (formats de 6-10h), cette valeur échoue déjà le test
   de plausibilité existant (`_MAX_PLAUSIBLE_RACE_DURATION`, 26h) et se rabat
   correctement sur la durée par défaut. **Mais pour les 24 Heures du Mans, le delta
   (~8h entre le début de course et cet `endDate`) passe silencieusement ce test de
   plausibilité** — sans la vérification en direct sur cette manche spécifique, le
   provider aurait produit une session Course de 8 heures au lieu de 24, une donnée
   fausse exportée dans le calendrier ICS de l'utilisateur pour l'événement le plus
   emblématique du championnat.
4. **Mélange d'années sur la page saison** — `fiawec.com/en/season/2026` liste à la
   fois les manches 2026 ET 2027 dans le même DOM (jamais le cas pour ELMS/MLMC, dont
   les slugs ne portent même pas de suffixe d'année) — découvert en comparant le nombre
   de liens extraits au nombre réel de manches attendues pour une saison.

Plutôt que de dupliquer tout `_build_sessions()`/`_extract_race_urls()` dans
`OfficialWecSource` pour ces deux derniers points, deux méthodes ont été extraites de
`AcoSportsEventSource` en points d'extension explicites avec un comportement par défaut
strictement inchangé pour ELMS/MLMC : `_race_session_end(first_start, event_end,
event_name) -> datetime | None` (défaut : logique de plausibilité déjà existante) et
`_race_url_belongs_to_season(url, year) -> bool` (défaut : `True` inconditionnel).
`OfficialWecSource` surcharge les deux ; ELMS/MLMC n'y touchent pas, vérifié par leurs
106 tests existants intégralement verts sans aucune modification.

**Décision — durée de course WEC déduite du nom de l'épreuve, jamais devinée**
`_race_session_end` de WEC parse un motif `"X Hours"` (regex, insensible à la casse)
dans le nom brut de l'épreuve — couvre 6 des 8 manches 2026 ("6 Hours of Imola", "24
Hours of Le Mans", etc.). Les 2 exceptions nommées différemment ("Lone Star Le Mans",
"Qatar 1812km") ont des durées confirmées via une recherche factuelle (fiawec.com,
Wikipedia — 6h et 10h respectivement), jamais devinées ni inventées. Un repli générique
à 6h (le format WEC le plus courant) couvre un nom de course futur non reconnu par ni le
motif ni la table — documenté comme approximation assumée dans `docs/AI_CONTEXT.md`
(dette technique), cohérente avec la philosophie déjà établie du projet ("Durée de
session légèrement inexacte... comportement documenté", même formulation déjà utilisée
pour les durées par défaut de `JolpicaSource`/MotoGP).

**Décision — pays WEC résolu dynamiquement depuis l'adresse JSON-LD, pas une table
statique**
Contrairement à ELMS/MLMC (`ACO_CIRCUIT_DATA`, table statique nom→pays), le JSON-LD de
fiawec.com inclut un champ `location.address` structuré de façon fiable
(`"{ville}, {code ISO 3166-1 alpha-3}"`, confirmé sur les 8 manches 2026) —
`OfficialWecSource._build_circuit` résout donc le pays dynamiquement via
`WEC_ADDRESS_COUNTRY_CODES` (code → nom anglais) plutôt qu'un table par circuit,
exactement le même raisonnement "préférer la donnée en direct à une table
manuellement maintenue" déjà justifié pour `sro_series/circuit_data.py` (Sprint 37, GT
World Challenge). `WEC_CIRCUIT_DATA` (nom → fuseau IANA) reste statique — le JSON-LD ne
fournit qu'un décalage horaire numérique par timestamp (ex. "+02:00"), jamais un nom de
zone IANA capable de gérer correctement les changements d'heure sur toute la saison.

**Décision — IMSA/WorldSBK restent des stubs après ré-investigation, pas un échec de
sprint**
Aucune source structurée exploitable trouvée pour l'un ou l'autre malgré une recherche
active (voir `docs/DATA_SOURCES.md` pour le détail complet des nouvelles pistes
vérifiées et écartées ce sprint). Conformément au brief lui-même ("rechercher la
meilleure source disponible" — pas "en trouver une à tout prix"), les deux stubs
restent inchangés architecturalement (mêmes `raise NotImplementedError`, toujours
enregistrés et intégrés partout) plutôt que de céder à l'automatisation navigateur
(Playwright) ou de fabriquer des horaires de session inventés — cohérent avec la
décision déjà prise et confirmée avec l'utilisateur aux Sprints 36/38.

**Conséquences**
- Aucune nouvelle famille de providers créée — WEC rejoint la famille ACO existante,
  conforme à "conserver les abstractions existantes".
- Un bug réel (durée de course Le Mans silencieusement fausse à 8h au lieu de 24h) a
  été détecté et corrigé en cours de sprint, avant d'atteindre un calendrier exporté.
- Plusieurs tests existants s'appuyaient implicitement sur l'échec naturel
  (`NotImplementedError` non mocké) de WEC comme exemple de "provider non implémenté" —
  adaptés pour utiliser IMSA à la place (toujours un stub réel), sans changer
  l'intention ni la couverture de ces tests. Voir `docs/JOURNAL.md` pour le détail des
  fichiers concernés.
- `gui/circuit_service.py` (Sprint 47) fusionne désormais automatiquement WEC avec 4
  autres championnats sur le circuit de Spa-Francorchamps — confirmé en direct, aucune
  modification nécessaire à `CircuitService` lui-même.

---

## ADR-038 — Circuit Explorer : `normalize_key`/`circuit_display_name`/`resolve_country` promus publics dans `event_display.py`, `circuit_key` en lockstep avec `circuit_name`, `on_circuit_click` comme point d'extension de `ChampionshipCard`

**Contexte**
Sprint 47. Les circuits n'étaient jusqu'ici que du texte affiché sur une
`ChampionshipCard` — jamais interrogeables, jamais dédupliqués entre championnats. Le
brief demande une véritable base de données des circuits (nom, pays, nombre de
championnats, liste des championnats, nombre total d'événements, première/dernière
saison) construite uniquement à partir des événements déjà chargés (aucun nouveau
provider, aucun appel réseau), plus une fiche Circuit accessible en cliquant le nom du
circuit depuis la fiche événement (Sprint 42). Contraintes explicites : créer
`gui/circuit_service.py`, toute la logique dans ce service, aucune logique métier dans
les vues.

**Décision — promouvoir `normalize_key` en public plutôt que dupliquer la normalisation**
`gui/search_service.py` (Sprint 45) possédait déjà une normalisation "compacte" privée
(`_normalize` : NFKD + suppression des accents + `casefold()` + alphanumérique
uniquement) pour dédupliquer les circuits dans les résultats de recherche — exactement
le besoin d'identité qu'une base de données des circuits doit résoudre à plus grande
échelle (le même "Spa-Francorchamps" orthographié différemment selon 5 championnats doit
devenir une seule entité, pas cinq). Plutôt que de réimplémenter cette normalisation une
seconde fois dans `circuit_service.py` (violation directe de "ne pas créer de
doublons"), elle a été promue en fonction publique `normalize_key()` dans
`gui/event_display.py` — déjà le module canonique du projet pour "comment identifier/
présenter un circuit ou un événement" (ADR-023) — et `search_service.py` a été adapté
pour l'importer au lieu de sa propre copie privée. Comportement strictement inchangé :
les 29 tests existants de `SearchService` passent sans aucune modification après le
déplacement, confirmant qu'il s'agit d'un renommage/déplacement, pas d'une réécriture.
Même principe de mutualisation-au-second-usage déjà appliqué à `session_type_label`
(Sprint 42) et `championship_selector.py` (Sprint 44) : extraire seulement quand un
second consommateur réel apparaît, jamais par anticipation.

**Décision — `circuit_display_name`/`resolve_country` : le nom/pays d'un circuit,
indépendamment de tout événement précis**
`event_display.py` possédait déjà `_resolve_circuit_name`/`_resolve_country`, mais leur
contrat ne convient pas tel quel à une base de données de circuits : `_resolve_circuit_name`
répond à "cette ligne doit-elle s'afficher sous CET événement" (elle cache une valeur
redondante avec le titre de la carte — un choix de mise en page pour une carte précise,
pas une propriété du circuit lui-même) — l'utiliser aurait fait disparaître des circuits
entiers de la base de données chaque fois que leur nom coïncide avec le nom de
l'événement (le bug F2/F3 documenté depuis le Sprint 32). Une nouvelle fonction publique
`circuit_display_name(circuit)` répond à la question réellement posée par
`CircuitService` — "comment s'appelle ce circuit" — en reprenant le même ordre de repli
(`circuit.name` puis `circuit.city`) mais sans jamais rien masquer pour cause de
redondance. `resolve_country` (renommée depuis `_resolve_country`, comportement
identique) convient en revanche tel quel : sa règle ("jamais 'Unknown' affiché tel
quel") ne dépend d'aucun événement précis, seulement de la donnée du circuit — un
circuit sans pays connu doit rester sans pays connu partout dans l'app, jamais une
exception pour la fiche Circuit.

**Décision — "best available data" pour le pays d'un circuit à travers les providers**
Un même circuit physique est souvent partagé par plusieurs championnats dont les
providers ont une couverture de données inégale (déjà documenté depuis le Sprint 32 :
les tables `_CIRCUIT_DATA` de F2/F1 Academy sont incomplètes, "Unknown" y est fréquent
alors que F1/Jolpica a presque toujours un vrai pays pour le même circuit).
`CircuitService.build_index()` ne fige donc jamais le pays sur la première valeur
rencontrée : tant qu'aucune valeur non-`None` n'a été trouvée pour un circuit, chaque
nouvel événement est une nouvelle chance de résoudre un vrai pays — une fois trouvé, il
n'est plus jamais écrasé (ni par une valeur "Unknown" rencontrée ensuite, ni ré-résolu
inutilement). Le nom d'affichage, en revanche, reste sur la conviction "première
occurrence gagne" déjà établie par `SearchService` (Sprint 45) — un choix arbitraire mais
cohérent, la donnée disponible ne permettant pas de trancher objectivement laquelle des
variantes orthographiques d'un même nom est "la meilleure".

**Décision — `circuit_key` en lockstep avec `circuit_name`, jamais une source d'identité
séparée**
`EventDisplayData` (Sprint 32) gagne un nouveau champ `circuit_key: str | None`, calculé
dans `normalize_event_display()` comme `normalize_key(circuit_name)` — mais `None`
exactement quand `circuit_name` l'est déjà. Alternative rejetée : calculer `circuit_key`
indépendamment de la règle de redondance (toujours non-`None`, y compris quand la ligne
circuit est masquée). Cette alternative aurait rendu le nom de circuit "cliquable en
théorie" sur des cartes où il n'existe littéralement aucun texte affiché pour porter le
clic — un piège d'interface (un clic fantôme sur rien). En le gardant strictement en
lockstep, l'invariant devient trivial à raisonner : il existe un texte de circuit visible
si et seulement si il existe quelque chose à cliquer. `gui/event_details.py::EventDetails`
transmet ce même champ tel quel, sans aucune logique propre — juste un passe-plat, comme
`date_label` l'est déjà.

**Décision — `on_circuit_click` comme point d'extension de `ChampionshipCard`, jamais un
comportement par défaut**
`ChampionshipCard` (Sprint 30) est un composant partagé entre "Ce week-end", le
Dashboard, "Mes favoris" et la fiche événement — rendre le nom de circuit cliquable
*partout* n'était ni demandé par le brief ni désirable (un clic sur une carte de
tableau de bord ouvrant une boîte de dialogue serait une surprise). `build_championship_card`
gagne donc un nouveau paramètre optionnel `on_circuit_click: Callable[[], None] | None =
None` — exactement le même contrat que `footer` (Sprint 30) : `None` (partout ailleurs)
laisse la ligne circuit strictement identique à avant ce sprint (texte simple,
`theme.Colors.TEXT_MUTED`) ; seule `main_view.py::_show_event_details_dialog` l'active,
transformant alors la ligne en `ft.Container` cliquable (`theme.Colors.PRIMARY` — seul
jeton sémantique déjà existant réutilisé, aucune nouvelle couleur introduite). Les 32
tests existants de `ChampionshipCard` passent sans aucune modification, confirmant qu'il
s'agit d'un ajout strictement additif.

**Décision — la fiche Circuit suit le patron exact de la fiche événement/succès, pas un
nouveau patron**
`main_view.py::_show_circuit_details_dialog` réutilise le patron déjà établi trois fois
(`_show_event_details_dialog`, Sprint 42 ; `_show_success_dialog`, Sprint 22) —
`ft.AlertDialog`/`page.show_dialog`/`page.pop_dialog`, largeur fixe 400px, colonne
scrollable — plutôt que d'inventer une nouvelle mécanique de dialogue. Les championnats
sont rendus en puces (`theme.chip`), même patron que la section "Championnats ce
week-end" du Dashboard (Sprint 39) — aucun nouveau composant créé pour cette liste.

**Conséquences**
- Aucun nouveau provider, aucune nouvelle source de données, aucun appel réseau
  supplémentaire — conforme à la consigne du sprint.
- `gui/circuit_service.py`/`gui/event_display.py`/`gui/event_details.py`/
  `gui/search_service.py`/`gui/components/championship_card.py` passent tous à 0 erreur
  mypy. `main_view.py` gagne 1 nouvelle occurrence (pas une nouvelle catégorie) du schéma
  déjà toléré `Button.on_click` — le bouton de fermeture de la nouvelle fiche Circuit,
  même famille que les fiches événement/succès existantes.
- Aucune page "Circuits" dédiée, aucun clic-through depuis l'historique des événements
  de la fiche Circuit vers la fiche événement correspondante (bien que l'identité soit
  déjà portée par `CircuitEventEntry`) — non demandés par le brief, pistes documentées
  dans `docs/TODO.md` pour un futur sprint.

---

## ADR-037 — Moteur de notifications : fondations pures, `WEEKEND_START`/`FIRST_SESSION` co-ancrés, `kinds`/`lead_times` comme paramètres d'appel plutôt que des préférences multiples

**Contexte**
Sprint 46. Après Recherche (Sprint 45) et Favoris (Sprint 44), le brief demande de
préparer un moteur de notifications — délibérément sans interface ni notification
système réelle cette fois ("Aucune notification système... n'est attendue durant ce
sprint. L'objectif est de construire les fondations."). Contraintes explicites : un
`NotificationService` totalement indépendant de l'interface, aucune dépendance Flet,
capable de calculer toutes les notifications à venir à partir des données déjà chargées
(aucun nouvel appel réseau), 5 types de notification (début du week-end, première
session, qualifications, sprint, course), délais configurables, fonctionnement sur tous
les championnats ou uniquement les favoris, 3 préférences persistées (activées, délai par
défaut, favoris uniquement) sans interface complète, réutilisable plus tard par
Windows/Linux/macOS sans modification.

**Décision — un service à état, mirroring `FavoritesService`/`SearchService`, mais sans
index persistant**
Comme les favoris (Sprint 44) et la recherche (Sprint 45), les 3 préférences ont un état
qui doit survivre entre plusieurs appels — `NotificationService.__init__` les lit une
fois depuis `gui/preferences.py`. Contrairement à `SearchService`, ce service n'a
cependant pas besoin d'un index reconstruit explicitement : calculer les notifications
n'est jamais une opération répétée à haute fréquence (pas "à chaque frappe" comme une
recherche), donc `compute_notifications()` est une fonction pure de ses arguments
(`year_events`, `now`, ...) — aucun état de calcul mis en cache entre deux appels. Ce
choix simplifie directement le scénario de validation "changement de saison" : appeler
`compute_notifications()` avec un nouveau `year_events` ne peut jamais faire fuiter
l'ancienne saison, il n'y a rien à invalider.

**Décision — `now` requis, jamais lu sur l'horloge système**
Même convention que `upcoming_weekend.find_upcoming_weekend` (Sprint 29) : `now` est un
paramètre obligatoire de `compute_notifications()`, jamais un `datetime.now(UTC)` interne
par défaut. Un futur appelant réel (`main_view.py`, ou une couche plateforme) résoudra
`now` au point d'appel — cette pureté rend le moteur entièrement déterministe et
testable sans geler l'horloge, exactement ce qu'exigent les scénarios "aucune
notification"/"une notification"/"changement de fuseau horaire" du brief.

**Décision — `WEEKEND_START` et `FIRST_SESSION` co-ancrés sur la même session**
Le modèle de domaine (`Event.sessions`) n'a aucune notion de "début de week-end"
distincte de "première session" — les deux ne peuvent, à ce jour, être calculés que comme
la session la plus précoce de l'événement (même convention `min(sessions, key=
start_datetime)` que `season_explorer._earliest_start`, Sprint 41). Plutôt que de fusionner
les deux notions du brief en un seul `NotificationKind`, elles restent deux valeurs
distinctes de l'énumération : le brief les liste explicitement comme deux notifications
séparées, et rien n'empêche un futur sprint de les distinguer réellement si le modèle de
domaine gagne un jour une notion propre de "début de week-end" (ex. un jour d'essais
libres non chronométré avant la première session comptant réellement pour le classement).
Documenté comme une équivalence actuelle assumée, pas une confusion.

**Décision — `kinds` : un paramètre d'appel, pas (encore) une préférence persistée**
Le brief ne demande que 3 préférences persistées (activées, délai par défaut, favoris
uniquement) — "quels types de notification" n'en fait pas partie. `compute_notifications`
accepte néanmoins un paramètre optionnel `kinds` (`None` = les 5 types), pour deux
raisons : (1) sans lui, un événement mono-session produit toujours au minimum 3
notifications simultanées (`WEEKEND_START`, `FIRST_SESSION`, et son propre type
spécifique) — un filtre était nécessaire pour écrire des tests déterministes "une
notification"/"plusieurs notifications" (scénarios de validation explicites du brief) ;
(2) c'est cohérent avec `lead_times`, déjà un paramètre configurable par appel. `kinds`
n'est pas persisté par choix — rien dans le brief ne le demande, une préférence
supplémentaire non demandée aurait été une anticipation, documentée comme piste possible
dans `docs/TODO.md` plutôt que construite par avance.

**Décision — `lead_times` : une liste par appel, une seule valeur persistée**
Le moteur accepte n'importe quelle combinaison de délais simultanément (`lead_times:
Sequence[timedelta]`) — les 4 exemples du brief (24h/12h/1h/15min) produisent une
notification chacun pour la même session en un seul appel. La préférence persistée
(`notifications_default_lead_time_minutes`) reste en revanche un entier unique, lecture
littérale de "délai par défaut" (singulier) dans la section Préférences du brief — utilisée
uniquement comme repli (`lead_times=None` → `[self.default_lead_time]`), jamais comme la
seule forme possible.

**Décision — aucune notification déjà due n'est retournée**
"Calculer toutes les notifications à venir" est pris au pied de la lettre : seules les
notifications dont l'instant de déclenchement (`session.start_datetime - lead_time`) est
encore dans le futur (`trigger_at >= now`) sont retournées. Une notification dont
l'instant de déclenchement est déjà passé — même si la session elle-même est encore à
venir — est exclue : elle aurait dû se déclencher plus tôt si l'application avait tourné
en continu, la recalculer maintenant produirait une notification en retard, jamais
demandée par le brief.

**Décision — aucune interface, conformément au brief**
Aucun `gui/views/notifications.py`, aucune destination de navigation, aucune modification
de `main_view.py` : le service existe et est entièrement testé mais n'est câblé nulle
part. Décision directement dictée par le brief ("L'objectif est de construire les
fondations"), pas une omission — piste explicite pour un futur sprint dans
`docs/TODO.md`.

**Conséquences**
- Aucun nouveau provider, aucune nouvelle source de données, aucun appel réseau
  supplémentaire, aucune évolution graphique — conforme à la consigne du sprint.
- `gui/notification_service.py` passe à 0 erreur mypy ; `gui/preferences.py` conserve ses
  3 erreurs mypy préexistantes (`dict` sans paramètres de type), inchangées — seules 3
  nouvelles clés ont été ajoutées à `_DEFAULTS`, pas leur typage.
- Le moteur est prêt à être consommé par une future page GUI et par une future couche de
  notification système (Windows/Linux/macOS) sans qu'aucune de ses méthodes publiques
  n'ait besoin de changer — c'est la garantie explicitement demandée par le brief.

---

## ADR-036 — Recherche globale : normalisation "compacte" pour le matching, index reconstruit sur les données déjà en mémoire, aucun nouveau composant

**Contexte**
Sprint 45. Avec 17 championnats intégrés et un volume de données croissant, le brief
demande une recherche globale (championnats, événements, circuits) instantanée et
entièrement hors ligne — "aucun appel réseau supplémentaire", "exploiter uniquement les
données déjà chargées". Contraintes explicites : recherche insensible à la casse et aux
accents, correspondance sur nom complet ou partiel, index réutilisable jamais reconstruit
depuis les providers à chaque frappe, résultats groupés par type et triés par pertinence
puis alphabétiquement, aucune logique métier dans la vue, aucun nouveau composant si les
existants suffisent.

**Décision — normalisation "compacte", pas seulement accents/casse**
Les exemples du brief imposent des équivalences que la normalisation habituelle
(minuscules + suppression des accents, séparateurs conservés) ne suffit pas à satisfaire :
`Le Mans` doit retrouver la même chose que `lemans` (espace en moins), et
`spa francorchamps` doit retrouver "Spa-Francorchamps" (espace vs tiret). Vérifié en
direct avant d'aller plus loin : une normalisation légère échoue sur ces deux cas.
`_normalize()` (`gui/search_service.py`) applique donc `unicodedata.normalize("NFKD", ...)`
+ suppression des marques combinantes (accents) + `casefold()` + filtrage pour ne garder
que les caractères alphanumériques — une forme "compacte" où espaces, tirets et
ponctuation disparaissent entièrement, aussi bien côté requête que côté données indexées.
Compromis assumé : deux mots dont la concaténation coïncide avec un troisième ne sont plus
distingués par une frontière de mot explicite — acceptable pour un jeu de données petit et
curé (17 championnats, quelques centaines d'événements/circuits), pas pour un moteur de
recherche généraliste à grande échelle.

**Décision — un service à état (`SearchService`), mirroring `FavoritesService`**
Comme les favoris (Sprint 44, ADR-035), la recherche a un état qui doit survivre entre
plusieurs appels — ici l'index construit, pas une liste persistée sur disque. Les modules
`gui/*.py` de "compute" pure (fonctions sans état) ne conviennent pas : reconstruire
l'index à chaque appel de `search()` violerait directement "ne jamais reparcourir
l'ensemble des providers à chaque frappe". `SearchService` sépare donc explicitement
`build_index(championship_ids, year_events)` (coûteux, appelé seulement quand les données
changent) de `search(query)` (bon marché, O(taille de l'index), appelé à chaque frappe) —
même séparation "compute vs état" que `FavoritesService`, construit frais une fois par
session dans `main_view.py` plutôt qu'un singleton partagé.

**Décision — source de données : `year_events`, pas un second pipeline de fetch**
Deux pipelines existaient déjà : `_fetch_weekend_entries` (17 championnats "Ce week-end",
fenêtre de 2 ans, alimente Dashboard/Ce week-end) et `controller.get_calendar_year_events`
(tous les championnats enregistrés, une année à la fois, alimente "Mon calendrier" depuis
le Sprint 40). La recherche utilise le second : il couvre déjà tous les championnats
(pas seulement les 17 "week-end"), et le réutiliser tel quel évite un second pipeline de
fetch dédié à la recherche — cohérent avec "aucune nouvelle source de données" et
"exploiter uniquement les données déjà chargées". Coût assumé et documenté (pas un bug) :
la recherche ne couvre que l'année actuellement parcourue sur "Mon calendrier", jamais un
historique multi-année — élargir la portée nécessiterait un fetch multi-année, hors
périmètre explicite du brief ("aucun appel réseau supplémentaire").

**Décision — réutilisation intégrale de `event_display.normalize_event_display` et
`display_names.get_display_name`, aucune seconde normalisation d'affichage**
Le brief demande "réutiliser les modèles existants" et "ne pas créer de doublons". Plutôt
que de relire `event.name`/`circuit.name`/`circuit.country` directement (risque de
doublon "X / X" ou de "Unknown" affiché tel quel, l'exacte anomalie documentée au
Sprint 32, ADR-023), `SearchService.build_index()` appelle `normalize_event_display` pour
chaque événement — un circuit ou un événement ne s'affiche donc jamais différemment en
recherche qu'ailleurs dans l'application. Les circuits sont dédupliqués par nom normalisé
(le même circuit accueille plusieurs événements/années ; première occurrence conservée) —
la recherche ne doit jamais montrer "Spa-Francorchamps" douze fois pour douze courses.

**Décision — aucun nouveau composant, composition déjà anticipée depuis le Sprint 31**
`test_gui_components_layout.py::TestLayoutSystemIntegration` contenait déjà, depuis le
Sprint 31, un exemple illustratif utilisant `PageHeader("Recherche", icon=ft.Icons.SEARCH,
subtitle="3 résultats")` comme cas d'usage du Layout System — confirmant à la fois le
choix d'icône et la composition exacte à suivre plutôt que d'en inventer une nouvelle.
`gui/views/search.py::build_search_view()` compose donc `PageHeader` + `Section`/
`SectionHeader`/`CardList` par groupe non vide + `EmptyState` (deux messages distincts
pour "aucune saisie" vs "aucun résultat", brief explicite : "Vérifier : recherche
vide, [...], aucun résultat" comme deux scénarios séparés) — zéro nouveau composant créé,
la vue ne fait qu'arranger ce que `SearchService` lui fournit déjà groupé/trié.

**Décision — index reconstruit à deux points précis, jamais en continu**
`main_view.py` appelle `search_service.build_index()` exactement deux fois : une fois au
démarrage (avec `year_events or {}`, pour que les championnats soient cherchables
immédiatement même avant que le fetch en arrière-plan ne résolve) et une seconde fois dans
`_load_year_events()` à chaque résolution d'année — jamais à chaque frappe, jamais à
chaque changement de sélection de championnat (qui ne change pas `year_events` lui-même).
`_refresh_search_view()` est appelé aux deux mêmes points pour qu'une recherche déjà
affichée à l'écran ne reste jamais périmée après un changement d'année.

**Conséquences**
- Aucun nouveau provider, aucune nouvelle source de données, aucun appel réseau
  supplémentaire — conforme à la consigne du sprint.
- La recherche ne couvre que l'année actuellement parcourue sur "Mon calendrier" — limite
  de périmètre assumée et documentée dans `docs/TODO.md`/`docs/AI_CONTEXT.md`, pas un bug.
- `gui/search_service.py`/`gui/views/search.py` passent tous deux à 0 erreur mypy ; 1
  nouvelle occurrence (pas une nouvelle catégorie) du schéma déjà toléré
  `on_change: Callable[[Event[BaseControl]], None]` (Flet 0.80 code vs 0.85.3 installé)
  sur le nouveau `search_field`.

---

## ADR-035 — Favoris intelligents : `FavoritesService` centralisé sur le fichier de préférences existant, sélecteur de championnats extrait en composant partagé

**Contexte**
Sprint 44. "Mes favoris" était un placeholder depuis le Sprint 31. Le brief en fait une
fonctionnalité centrale : l'utilisateur doit pouvoir ajouter/retirer des championnats
favoris, les retrouver au prochain lancement, et les voir utilisés automatiquement dans
tout le reste de l'application (Dashboard, Ce week-end, Mon calendrier). Contraintes
explicites : créer un `FavoritesService` dédié, aucune logique métier dans les vues, ne
pas dupliquer le code de sélection des championnats, réutiliser les modèles existants,
persistance centralisée, aucun nouveau composant si ceux existants suffisent.

**Décision — un service, pas un module fonctionnel, mirroring `ConfigService`**
Tous les modules `gui/*.py` de "compute" pure établis depuis le Sprint 39
(`dashboard.py`, `season_explorer.py`, `event_details.py`, `calendar_selection.py`) sont
des collections de fonctions, jamais des classes — parce qu'aucun n'a d'état propre à
maintenir entre deux appels, seulement des données déjà fournies par l'appelant. Les
favoris sont différents : ils ont un état mutable (la liste courante) qui doit survivre
entre plusieurs appels (`add`, `remove`, `toggle`, `list`) sans que chaque appelant ne
recharge/refusionne le fichier de préférences lui-même. `ConfigService`
(`config/service.py`, Sprint 1) établit déjà le patron "service à état, construit frais à
chaque utilisation, méthodes sémantiques plutôt que manipulation de dict brut" pour
exactement ce besoin — `FavoritesService` (`gui/favorites_service.py`) suit ce même
patron plutôt que d'ajouter des fonctions de plus à `gui/preferences.py`. Comme
`ConfigService()`, il est construit frais partout où nécessaire (jamais un singleton
partagé) : `main_view.py` en construit une instance pour toute la session, `controller.py`
en construit une par appel à `get_upcoming_weekend`/`get_dashboard_data` — une lecture
disque locale bon marché à chaque fois, cohérent avec le coût déjà accepté de
`ConfigService()` frais dans `_fetch_weekend_entries`.

**Décision — persistance centralisée sur le fichier existant, jamais un second fichier**
`gui/preferences.py` (`gui_prefs.json`) est déjà le fichier de préférences GUI partagé,
utilisé jusqu'ici pour `selected_championships`/`last_output_dir`. Plutôt que
d'introduire un second fichier de configuration pour les favoris, `FavoritesService` lit/
écrit une nouvelle clé (`favorite_championships`) dans ce même fichier via les fonctions
`load_preferences()`/`save_preferences()` déjà existantes — c'est la lecture la plus
littérale possible de "la persistance doit être centralisée".

Cette décision a mis au jour un bug latent réel : `main_view.py::_save_prefs()`
construisait un dictionnaire littéral neuf à chaque sauvegarde
(`save_preferences({"selected_championships": ..., "last_output_dir": ...})`), ce qui
écrase silencieusement **toute** clé absente de ce littéral — y compris la nouvelle
`favorite_championships` dès qu'un utilisateur cocherait/décocherait un championnat sur
"Mon calendrier" après avoir défini des favoris. Corrigé en lecture-fusion-écriture :
`_save_prefs()` relit `load_preferences()` frais, ne remplace que les deux clés qu'il
possède, et sauvegarde le dictionnaire complet — `FavoritesService._save()` suit la même
discipline pour sa propre clé. Cette règle ("toujours lecture-fusion-écriture, jamais un
littéral neuf") est désormais documentée dans le docstring de `gui/preferences.py` comme
contrat obligatoire pour tout futur écrivain de ce fichier.

**Décision — extraction du sélecteur de championnats en composant partagé**
Le brief demande explicitement de "ne pas dupliquer le code de sélection des
championnats". "Mon calendrier" (Sprint 43) avait déjà construit exactement l'interface
nécessaire : un accordéon par catégorie, chaque championnat un bouton sélectionnable,
sélection multiple, jamais de bouton radio — seulement défini en privé dans
`gui/views/calendar.py`. Plutôt que de reconstruire cette même interface dans
`gui/views/favorites.py` avec une sémantique différente ("favori" au lieu de "sélectionné
pour cette génération"), `ChampionshipButtonData`/`ChampionshipCategoryData`/
`_championship_button`/`_category_accordion`/`_championships_section` ont été extraits
vers `gui/components/championship_selector.py` — le deuxième composant du paquet
`gui/components/` (après `championship_card.py`, Sprint 30, ADR-021), suivant exactement
le même patron : modèle de données propre au composant, construit uniquement à partir des
primitives `theme.py`, indifférent à ce que "sélectionné" signifie pour son appelant.
`gui/views/calendar.py` et le nouveau `gui/views/favorites.py` importent tous deux
`build_championship_selector()` ; aucun des deux ne redéfinit la logique de rendu de
l'accordéon. Les tests de l'ancien `TestCalendarViewChampionships` (`test_gui_views.py`)
ont été déplacés vers un nouveau `tests/test_gui_components_championship_selector.py`
testant le composant en isolation, cohérent avec le fait qu'il n'appartient plus à une
seule vue.

**Décision — tri "favoris en premier" mutualisé dans `upcoming_weekend.py`, jamais
dupliqué entre Dashboard et Ce week-end**
Le Dashboard et "Ce week-end" partagent déjà le même pipeline de recherche de week-end
(`upcoming_weekend.find_upcoming_weekend`, Sprint 39, ADR-030) — `DashboardData.weekend`
est littéralement un `WeekendResult`, construit par la même fonction. Le tri "favoris en
premier" a donc été ajouté à l'endroit unique où les deux pages convergent déjà :
`_group_entries_for_display(entries, favorite_ids)` applique un tri stable (favoris
d'abord, ordre catégorie/chronologique préservé entre eux et entre non-favoris) après le
regroupement par catégorie existant. `build_dashboard_data()` transmet `favorite_ids` tel
quel à `find_upcoming_weekend()` sans aucune logique de tri qui lui soit propre — il ne
peut structurellement pas exister deux implémentations divergentes du "favoris en
premier", exactement la contrainte du brief.

**Décision — pré-sélection "Mon calendrier" : un seed initial, pas une synchronisation
continue**
"Pré-sélectionner automatiquement les championnats favoris" a été interprété comme un
seed au lancement (`state.selected_championships` initialisé depuis
`favorites_service.list()` si non vide, sinon repli sur l'ancien comportement mémorisé)
plutôt qu'une synchronisation permanente pendant la session : forcer la sélection active
de génération à chaque changement de favori pendant que l'utilisateur explore "Mes
favoris" aurait silencieusement écrasé une sélection qu'il vient de personnaliser à la
main sur "Mon calendrier" — un comportement surprenant, non demandé par le brief et
contraire à l'esprit "aucune régression".

**Conséquences**
- Aucun nouveau provider, aucune nouvelle source de données, aucune modification de la
  logique métier ni des modèles de domaine — conforme à la consigne du sprint.
- Un bug latent de perte silencieuse de préférences a été détecté et corrigé en cours de
  sprint, avant qu'il ne cause une perte de données réelle pour un utilisateur.
- Un fichier de préférences réel (issu de l'usage précédent de ce projet) existait sur la
  machine de développement — une fixture `autouse` a été ajoutée à `tests/conftest.py`
  pour isoler tous les tests de l'état réel de la machine, un risque de non-déterminisme
  corrigé avant qu'il ne cause un test instable en CI ou sur une autre machine.
- `gui/views/calendar.py` perd ses 2 erreurs mypy historiques (`ExpansionTile.on_change`,
  déménagées vers `championship_selector.py`) — dette relocalisée, pas nouvelle.

---

## ADR-034 — Refonte UX de "Mon calendrier" : extension du Layout System (`trailing`/`footer`) plutôt qu'une structure bespoke

**Contexte**
Sprint 43. Premier sprint purement ergonomique du projet, explicitement cadré par le
brief : "Le moteur de génération est désormais mature. Les fonctionnalités sont
présentes. Le principal point faible est maintenant l'expérience utilisateur."
Contraintes explicites, plus strictes que les sprints précédents : aucune nouvelle
fonctionnalité métier, aucun nouveau provider, aucune modification de la logique métier,
aucune modification des modèles, aucun changement graphique global, réutiliser un
maximum de composants existants. L'assistant 4 étapes (Sprint 26) devait être remplacé
par une page unique reorganisée autour de 7 exigences précises : championnats en point
d'entrée regroupés par catégorie dans des accordéons à un seul niveau, chaque
championnat un bouton sélectionnable (jamais de case à cocher, jamais de bouton radio),
saison en contrôle secondaire en haut à droite, résumé de sélection permanent (avec le
nombre de championnats), explorateur de saison conditionnel à la sélection, bouton
"Créer" toujours visible sans jamais imposer de défilement de la page entière.

**Décision — portée de "aucune modification de logique métier / des modèles"**
Le brief interdit de toucher la logique métier et les modèles, mais le retrait complet
de l'assistant est impossible sans modifier `GenerateState` (`current_step`/
`STEP_COUNT`/`step_valid`/`can_advance`/`can_go_back`) — la notion même d'"étape"
disparaît. Décision (cohérente avec la distinction déjà établie sprint après sprint
entre "logique métier" et "état de présentation GUI") : les contraintes visent le moteur
de génération (`core/`, `providers/`, `exporters/`, le pipeline `controller.py`) et les
modèles de domaine Pydantic (`models/` — `Event`/`Session`/`Circuit`/`Championship`),
jamais les dataclasses d'état GUI (`gui/models.py::GenerateState`/`PreferencesModel`),
qui ont toujours été considérées comme de la présentation, pas du métier. Sur cette
base, `GenerateState` perd toute sa machinerie d'étapes — obsolète, pas remplacée —
tandis que `year`/`selected_championships`/`output_path`/`is_generating`/`is_ready()`
restent strictement inchangés. Aucun fichier sous `core/`, `providers/`, `exporters/`,
`models/` (domaine) n'a été touché.

De même, le nombre de championnats sélectionnés (une des 4 statistiques demandées pour
le résumé permanent) est calculé comme `len(state.selected_championships)` directement
dans `main_view.py`, jamais ajouté à `calendar_selection.py::SelectionSummary` (Sprint
40, ADR-031) : c'est une valeur triviale, déjà connue sans aucun fetch, qui n'a pas sa
place dans un module dont la raison d'être est d'agréger des données récupérées sur le
réseau. `calendar_selection.py` reste entièrement inchangé.

**Décision — extension du Layout System plutôt qu'une structure bespoke**
Deux besoins structurels nouveaux n'avaient pas d'équivalent dans le Layout System
existant (Sprint 31, ADR-022) : (1) un contrôle secondaire à côté du titre de page, et
(2) un pied de page fixe qui ne défile jamais avec le reste. Plutôt que de construire ces
deux besoins directement dans `gui/views/calendar.py` (une structure de page bespoke,
contournant `PageContainer`/`PageHeader`), ils ont été ajoutés comme paramètres optionnels
aux composants du Layout System eux-mêmes :
- `PageHeader(title, *, icon=None, subtitle=None, trailing=None)` — `trailing` insère un
  second contrôle dans la même ligne que le titre (`ft.Row(alignment=SPACE_BETWEEN)`),
  sans toucher au sous-titre ni au séparateur qui suivent.
- `PageContainer(*, header=None, body=(), footer=None)` — `footer is None` (chaque page
  sauf "Mon calendrier") emprunte exactement le même chemin de code qu'avant ce sprint
  (`theme.page_shell(*sections)`, sans aucune branche nouvelle) ; `footer` fourni bascule
  vers une structure à deux régions (en-tête+corps scrollables dans un `Container(expand=
  True)`, pied de page fixe en dehors) qui réutilise exactement les mêmes tokens
  (`theme.MAX_CONTENT_WIDTH`, `theme.page_padding()`, `theme.Spacing.SM`, alignement
  `TOP_CENTER`, colonne `STRETCH`) que `theme.page_shell` — un découpage structurel, pas
  un nouveau style visuel.

Ce choix est directement dicté par "réutiliser un maximum de composants existants" et
"aucun changement graphique global" : les 5 autres pages de l'application (Ce week-end,
Tableau de bord, Mes favoris, Préférences, À propos) restent structurellement et
visuellement identiques, byte pour byte, puisque `trailing`/`footer` valent `None` par
défaut — vérifié explicitement par `TestAllViewsShareTheSameGrid`, resté intégralement
vert sans aucune modification. Une structure bespoke dans `calendar.py` aurait
fonctionné aussi, mais aurait dupliqué cette logique de grille (largeur/padding/
alignement) une seconde fois plutôt que de l'étendre à l'endroit où elle vit déjà.

**Décision — le bouton championnat réutilise `theme.card(selected=True)`, jamais utilisé
jusqu'ici**
`theme.card()` porte un paramètre `selected: bool` depuis le Sprint 26/30, documenté
"used for step indicators and chosen options in the calendar wizard" — mais jamais
réellement consommé par aucun appelant avant ce sprint (vérifié par recherche : aucune
occurrence de `selected=True` dans tout `gui/`). Le "bouton sélectionnable" demandé par
le brief (championnat cliquable, sélection multiple, jamais de bouton radio) est
exactement ce que cette styling anticipée décrit : une carte à la bordure/fond différents
selon l'état sélectionné. `_championship_button()` construit une `theme.card(...,
selected=option.selected)` et assigne `.on_click` après coup — aucun nouveau token de
Design System, aucune nouvelle primitive dans `theme.py`, la seule "nouveauté" étant que
ce style dormant depuis trois sprints trouve enfin son premier consommateur réel.

**Décision — les accordéons et boutons restent des données pures, jamais construits
par `main_view.py`**
Contrairement au patron plus ancien de la liste de cases à cocher (Sprint 26 : `main_view.py`
construisait directement les `ft.Checkbox`), ce sprint suit le patron plus récent établi
depuis le Sprint 39 (`dashboard.py`, `season_explorer.py`, `event_details.py`) : deux
nouvelles dataclasses `ChampionshipButtonData`/`ChampionshipCategoryData` (display-ready,
mirroring `SeasonEventRow`/`ChampionshipCardData`) vivent dans `gui/views/calendar.py`,
peuplées par `main_view.py` (qui résout déjà `categories.get_groups_for`/
`display_names.get_display_name`) mais rendues intégralement par la vue
(`_championship_button`/`_category_accordion`/`_championships_section`), qui ne connaît
jamais `Category`/`get_display_name` elle-même. L'état "quel accordéon est ouvert"
(`expanded_categories: set[str]`, dans `main_view.py`) est initialisé une fois avec les
catégories contenant une présélection (ex. `formula1` par défaut), pour que le choix par
défaut soit visible sans clic supplémentaire — un choix de confort explicitement lié à
l'objectif du sprint ("rendre la sélection plus naturelle"), pas une exigence du brief.

**Conséquences**
- Aucun nouveau provider, aucune nouvelle source de données, aucune modification de la
  logique métier ni des modèles de domaine — conforme à la consigne du sprint.
- Les 5 autres pages de l'application restent structurellement et visuellement
  identiques — `TestAllViewsShareTheSameGrid` intégralement vert.
- Le nombre d'erreurs mypy dans `main_view.py` a diminué (21 → 15) : le retrait de
  l'assistant a supprimé plus d'occurrences du schéma `Callable[[Event[BaseControl]],
  ...]` déjà toléré qu'il n'en a introduit.
- Sprint le plus visuellement significatif à ce jour sans aucune vérification visuelle
  réelle possible dans ce bac à sable — documenté comme limite prioritaire dans
  `docs/TODO.md`/`docs/AI_CONTEXT.md`.

---

## ADR-033 — Fiche événement : réutilisation littérale de `ChampionshipCardData`, extraction de `session_type_label` au second usage

**Contexte**
Sprint 42. Quatrième sprint "valeur" consécutif, dans la continuité directe de
l'explorateur de saison (Sprint 41, ADR-032) : chaque ligne de la liste d'événements doit
devenir sélectionnable, et un clic doit ouvrir une fiche détaillée — championnat, nom de
l'épreuve, circuit, pays, date, et la liste chronologique des sessions (essais,
qualifications, sprint, warm-up, course) avec heure et type. Contraintes explicites :
créer un module dédié à la logique, aucune logique métier dans la vue, réutiliser les
**modèles** existants (formulation plus stricte que les sprints précédents, qui
demandaient de réutiliser les *composants*), aucun nouveau provider, aucune évolution
graphique, aucun travail sur les icônes.

**Investigation préalable — "Warm-up" n'existe pas dans le domaine**
Le brief liste "Warm-up" parmi les types de session à afficher. Vérification du modèle
domaine (`models/session.py::SessionType`) : `FP1`, `FP2`, `FP3`, `QUALIFYING`,
`SPRINT_QUALIFYING`, `SPRINT`, `RACE`, `FREE_PRACTICE`, `TEST`, `HYPERPOLE` — aucun
`WARM_UP`. Aucun provider du projet n'en produit non plus. Conformément à la contrainte
"aucun nouveau provider" et à l'esprit "réutiliser les modèles existants" (ne pas en
inventer), aucun type n'a été ajouté au domaine : la fiche affiche fidèlement les types
réellement présents dans les données fetchées, sans jamais inventer une session
"Warm-up" qui n'existe dans aucune source. Précédent similaire : le brief du Sprint 34
citait par erreur "F1 Academy" comme manquant alors qu'il était déjà intégré — même
principe de vérifier la réalité des données avant d'écrire du code plutôt que de suivre
le brief au pied de la lettre sur un point factuellement inexact.

**Décision — `ChampionshipCardData`/`SessionRow` réutilisés tels quels, jamais redéfinis**
En examinant la forme demandée par le brief (championnat, nom, circuit, pays,
sessions triées avec heure + type), elle correspond presque exactement au modèle déjà
défini par le composant `ChampionshipCard` (Sprint 30) : `ChampionshipCardData`
(`championship_id`, `championship_name`, `event_name`, `circuit_name`, `country`,
`sessions: tuple[SessionRow, ...]`). Plutôt que de définir un nouveau modèle "fiche
événement" qui dupliquerait ce shape, `gui/event_details.py::build_event_details()`
construit directement une `ChampionshipCardData` — c'est la lecture la plus littérale
possible de "réutiliser les modèles existants". Le seul champ que ce modèle ne porte pas
est un intitulé de date unique au niveau de l'événement (la carte ne montre que l'heure
de chaque session, jamais une date d'ensemble) : ajouté via un wrapper
`EventDetails(card: ChampionshipCardData, date_label: str | None)`, `date_label` étant
`None` exactement quand l'événement n'a aucune session — même contrat "None = rien à
montrer" que `SelectionSummary.period_start`/`period_end` (Sprint 40). `ChampionshipCard`
lui-même (`gui/components/championship_card.py`) n'a **pas** été modifié — un nouveau
champ `date` y aurait été un changement partagé par tous ses appelants existants ("Ce
week-end", Dashboard) pour un besoin propre à un seul nouvel usage, contraire au principe
déjà appliqué de ne mutualiser/modifier un composant partagé qu'au moment où le besoin
apparaît réellement pour *tous* ses consommateurs, pas un seul.

**Décision — extraction de `session_type_label` au moment du second usage réel**
`upcoming_weekend.py` possédait déjà, en privé, la table `SessionType -> libellé FR`
(`_SESSION_LABELS`/`_session_type_label`) construite au Sprint 29. `gui/event_details.py`
a besoin exactement de la même table. Suivant le principe déjà appliqué à
`_fetch_weekend_entries` (Sprint 39, ADR-030) et `_resolve_source_and_provider_factories`
(Sprint 40, ADR-031) — mutualiser au moment où un second consommateur réel apparaît,
jamais par anticipation — la table a été promue en `event_display.session_type_label()`
(public), `event_display.py` étant déjà le module canonique pour "comment présenter un
événement" (Sprint 32, ADR-023). `upcoming_weekend.py` a été mis à jour pour importer et
réutiliser cette même fonction ; comportement strictement préservé, vérifié par la suite
de tests existante (`test_gui_upcoming_weekend.py`, `test_gui_event_display.py`,
`test_gui_dashboard.py`, `test_gui_controller.py` — 101 tests) intégralement verte après
le refactor, sans qu'aucun test n'ait dû être modifié. À l'inverse, la table des noms de
jours FR (`_DAY_LABELS_FR`, 7 constantes triviales) n'a **pas** été mutualisée une
troisième fois (déjà dupliquée une fois dans `gui/season_explorer.py` au Sprint 41) —
cohérent avec la distinction déjà posée dans l'ADR-032 entre "vocabulaire substantiel"
(les 10 libellés de session, méritant une vraie extraction) et "boilerplate trivial" (7
noms de jours, dont la duplication reste moins coûteuse que le couplage entre modules).

**Décision — le clic : identité portée par la ligne, jamais l'objet domaine**
`SeasonEventRow` (Sprint 41) gagne deux champs, `championship_id`/`event_uid` —
délibérément pas l'`Event` domaine lui-même. Toutes les dataclasses "display-ready" de ce
paquet (`SelectionSummary`, `NextRaceStart`, `SeasonEventRow` déjà avant ce sprint) ne
portent jamais d'objet domaine, seulement des chaînes déjà formatées ou des identifiants
stables — cohérence délibérée : un clic sur une ligne transmet ces deux identifiants à
`main_view.py` (seul endroit propriétaire de `year_events`), qui retrouve l'`Event` réel
avant d'appeler `build_event_details()`. `gui/views/calendar.py` ne résout jamais rien
lui-même : `_season_event_row`/`_season_explorer_block` acceptent un callback
(`on_click`/`on_event_click`) qu'elles se contentent de transmettre, exactement comme
`on_step_click` l'était déjà depuis le Sprint 26. Mécaniquement, rendre une ligne
cliquable ne demande aucun nouveau composant ni changement de `theme.py` : `theme.card()`
retourne déjà un `ft.Container`, qui supporte nativement `on_click` — assigné après
construction (`card.on_click = lambda e: on_click(row)`), au lieu d'étendre la signature
de `theme.card()` pour un besoin qui n'existe qu'à un seul site d'appel aujourd'hui.

**Décision — la fiche s'affiche dans une boîte de dialogue, mirroir du patron déjà établi**
`main_view.py` possédait déjà un patron de boîte de dialogue (`_show_success_dialog`,
`ft.AlertDialog` + `page.show_dialog()`/`page.pop_dialog()`) pour le message de succès de
génération ICS. `_show_event_details_dialog()` suit exactement le même patron plutôt que
d'introduire un second mécanisme de dialogue — titre, contenu scrollable (`ft.Column` +
`ft.ScrollMode.AUTO`, un événement à beaucoup de sessions doit rester lisible), un seul
bouton "Fermer" (`STRINGS.close_btn`, déjà existant — aucune nouvelle chaîne pour ce
bouton). Aucune nouvelle requête réseau : l'événement cliqué est toujours déjà présent
dans `year_events` (Sprint 40), la fiche est un calcul purement local.

**Conséquences**
- Aucun nouveau provider, aucune nouvelle source de données — conforme à la consigne du
  sprint.
- `ChampionshipCard` reste un composant à un seul modèle (`ChampionshipCardData`), utilisé
  identiquement par "Ce week-end", le Dashboard et désormais la fiche événement — aucune
  divergence de comportement entre ces trois consommateurs.
- "Warm-up" reste absent de l'application tant qu'aucune source de données réelle n'en
  fournit — documenté comme limite connue plutôt que masqué par une session inventée.
- Une sélection large ou un événement à beaucoup de sessions n'a pas été vérifié
  visuellement (rendu Flet réel) — documenté dans `docs/TODO.md`/`docs/AI_CONTEXT.md`,
  même limitation que chaque sprint GUI précédent.

---

## ADR-032 — Explorateur de saison : ancré sur la session la plus précoce, aucun nouveau fetch

**Contexte**
Sprint 41. Troisième sprint "valeur" consécutif, dans la continuité directe du résumé de
sélection (Sprint 40, ADR-031) : "Mon calendrier" dispose déjà d'un filtrage par
année/championnat et d'un résumé (compteurs + période), mais aucun moyen de voir
concrètement *quels* événements composent la sélection avant de générer l'ICS. Le brief
demande d'ajouter un explorateur de saison affichant, pour chaque événement de la
sélection courante, son nom, son championnat, son circuit, son pays et sa date — trié
chronologiquement et regroupé naturellement par mois, mis à jour automatiquement à chaque
changement de sélection. Contraintes explicites, identiques à celles des Sprints 39/40 :
aucune logique métier dans la vue, réutiliser les composants existants, aucune évolution
graphique, aucun travail sur les icônes.

**Décision — aucun nouveau fetch, réutilisation directe de `year_events`**
`controller.get_calendar_year_events(year)` (Sprint 40) récupère déjà, en une seule
passe, les événements de tous les championnats enregistrés pour l'année parcourue — la
matière première nécessaire à l'explorateur de saison est donc déjà disponible en
mémoire dans `main_view.py`, sans qu'aucun second appel réseau ne soit nécessaire.
Nouveau module `gui/season_explorer.py`, mirroring exact de `calendar_selection.py`
(lui-même mirroring de `dashboard.py`/`upcoming_weekend.py`) : aucun import Flet, aucune
I/O — entièrement testable avec de simples fixtures `Event`/`Session`.
`build_season_explorer(year_events, selected_championships)` filtre localement les
mêmes données déjà utilisées par `build_selection_summary`, exactement comme cocher une
case ne redéclenche jamais de fetch (Sprint 40) — côté `main_view.py`, une nouvelle
fonction `_current_season_groups()` mirroir exact de `_current_selection_summary()` (même
convention `None` = fetch de l'année en cours toujours en vol / tuple vide = fetch résolu
mais rien ne correspond à la sélection) est la seule addition nécessaire ; le
rafraîchissement automatique à chaque changement de sélection (année ou championnat)
"vient gratuitement" du même `_refresh_calendar_view()` déjà appelé par
`on_year_change`/`_make_on_change` depuis le Sprint 26/40 — aucun nouveau code de câblage
d'événement n'a été nécessaire pour satisfaire "mis à jour automatiquement lorsque la
sélection change".

**Décision — tri et regroupement ancrés sur la session la plus précoce de chaque
événement, jamais sur `Event.season`**
Le modèle domaine `Event` n'a pas de champ date propre — seules ses `sessions` ont des
horodatages. Le tri chronologique et le regroupement mensuel sont donc calculés à partir
de `min(s.start_datetime for s in event.sessions)`, convertie en UTC avant d'en extraire
année/mois — même convention que `upcoming_weekend._session_utc_date` (limitation déjà
documentée pour les circuits loin de l'UTC, pas une nouvelle introduite ici). Utiliser
`Event.season` à la place aurait été trompeur : l'anomalie Formula E déjà observée et
documentée au Sprint 40 (un rond "2026" contenant une manche datée du 6 décembre 2025,
convention réelle du calendrier Formula E) prouve qu'une saison peut légitimement
déborder sur l'année civile précédente — un événement de ce type doit apparaître dans un
groupe "Décembre 2025" et non être mal classé sous une étiquette "2026" trompeuse. Un
test dédié (`TestBuildSeasonExplorerYearBoundary`) verrouille ce comportement. Un
événement sans aucune session (aucun horodatage à lui assigner) est simplement exclu du
résultat plutôt que de lever une erreur ou d'être placé arbitrairement.

**Décision — la vue : aucun nouveau composant, lignes séparées plutôt que combinées**
`gui/views/calendar.py::_season_explorer_block` est construite exclusivement à partir du
Layout System déjà existant (`Section`/`SectionHeader`/`CardList`/`EmptyState`) et de
`theme.card()` — un mois devient une `Section(SectionHeader(month_label),
CardList([...]))`, chaque événement une carte à deux colonnes (informations à gauche,
date à droite). Aucun nouveau composant `gui/components/` créé : une ligne d'événement
plate (nom/championnat/circuit/pays/date) est structurellement trop différente d'une
`ChampionshipCard` (orientée détail des sessions d'un seul événement déjà connu, un
week-end à la fois) pour justifier sa réutilisation — créer un composant sans un second
consommateur réel aurait été une anticipation, contraire au principe déjà appliqué aux
providers depuis le Sprint 35 (ADR-026) et repris à chaque sprint GUI depuis. À
l'intérieur d'une carte, nom/championnat/circuit/pays restent sur des lignes séparées,
jamais combinés par un séparateur "·" — règle déjà posée pour `ChampionshipCard` au
Sprint 30 (l'en-tête y est passé de "circuit · pays" combiné à 4 lignes distinctes) et
reconduite ici à l'identique pour la cohérence visuelle de l'application. Le bloc est
inséré juste après `_selection_summary_block`, visible sur les 4 étapes du wizard — même
placement/convention que le résumé de sélection (Sprint 40, ADR-031), pour la même
raison : parcourir la saison fait partie de l'exploration, pas seulement de l'étape
finale.

**Conséquences**
- Aucun nouveau provider, aucune nouvelle source de données — conforme à la consigne du
  sprint.
- Aucune requête réseau supplémentaire : l'explorateur de saison est un dérivé purement
  local de données déjà en mémoire pour le résumé de sélection.
- Le wizard 4 étapes existant reste strictement inchangé dans sa structure — seul un bloc
  supplémentaire s'intercale entre le résumé de sélection et le corps de chaque étape.
- Une sélection large (17 championnats, ~170 événements pour une saison complète) produit
  une liste longue — absorbée par le scroll de page déjà en place (`theme.page_shell`,
  Sprint 27), jamais testée visuellement à cette échelle ; documenté comme limite dans
  `docs/TODO.md`/`docs/AI_CONTEXT.md`.

---

## ADR-031 — Calendrier interactif : résumé persistant plutôt qu'un enrichissement du seul récapitulatif final

**Contexte**
Sprint 40. Deuxième sprint "valeur" du projet, dans la continuité du Dashboard
(Sprint 39, ADR-030) : aucun nouveau provider, aucune nouvelle source de données —
transformer "Mon calendrier" d'un formulaire de génération ICS en un véritable outil
d'exploration. L'assistant 4 étapes existant (saison/championnats/destination/créer,
inchangé depuis le Sprint 26) doit être **conservé intégralement** — la génération ICS
reste l'aboutissement de la navigation, pas son unique objectif. Travail demandé :
filtrer par année et par championnat (déjà présent, étapes 1-2 du wizard existant),
afficher le nombre d'événements sélectionnés, le nombre de sessions sélectionnées, la
période couverte, et un résumé de la sélection avant génération. Contraintes explicites :
aucune logique métier dans la vue, réutiliser les composants existants, créer des
composants uniquement si une vraie réutilisation apparaît, respecter intégralement le
Design System et le Layout System, aucun travail sur les icônes.

**Décision — où vit le fetch et le calcul**
Le wizard filtre déjà par année et par championnat, mais ces filtres ne produisaient
jusqu'ici aucun retour visible avant l'étape finale. Plutôt que de ne fetcher que les
championnats actuellement cochés (ce qui rendrait chaque coche de case coûteuse en
réseau), `controller.get_calendar_year_events(year)` (nouveau) récupère **en une seule
passe** les événements de **tous** les championnats enregistrés (`registry.list_all()`)
pour l'année parcourue — contrairement à `_fetch_weekend_entries` (Sprint 29/39, ADR-030)
limité aux 17 championnats "Ce week-end" et à deux années (courante + suivante), celui-ci
est scopé à exactement une année (l'utilisateur l'a choisie délibérément, aucun
lookahead) mais couvre l'intégralité des championnats, puisque les cases à cocher du
wizard les listent déjà tous. Conséquence directe : cocher/décocher un championnat
devient un **filtrage purement local et instantané** sur des données déjà en mémoire
(`gui/calendar_selection.py::build_selection_summary`) — aucune requête réseau par case
cochée ; seul un changement d'année (`on_year_change`) déclenche un nouveau fetch. Ne
raccroche jamais — un championnat dont le fetch échoue (WEC/IMSA/WorldSBK stubs
`NotImplementedError`, timeout réseau…) est simplement absent du résultat, cohérent avec
la règle de résilience partielle déjà appliquée à `_fetch_weekend_entries`/
`generate_calendar`.

Résolution championnat→source→provider identique entre `_fetch_weekend_entries` et
`get_calendar_year_events` (mêmes règles de config/opt-out/source par défaut, même
gestion d'échec silencieuse) — extraite en
`controller._resolve_source_and_provider_factories(cid, config)` une fois ce second
consommateur apparu, même principe de factorisation-au-second-usage déjà appliqué au
Sprint 39 (ADR-030) et aux providers depuis le Sprint 35 (ADR-026).
Délibérément **pas** appliqué à `generate_calendar()` : ses tests verrouillent des
messages d'erreur exacts par championnat que le retour `None`-générique de l'aide
partagée aurait perdus — refactoriser aurait risqué une régression pour aucun bénéfice
ce sprint.

Nouveau module `gui/calendar_selection.py`, mirroring exact de `dashboard.py`/
`upcoming_weekend.py` : aucun import Flet, aucune I/O — entièrement testable avec de
simples fixtures `Event`/`Session` (le fetch vit dans `controller.get_calendar_year_events`,
jamais dans ce module). `SelectionSummary(event_count, session_count, period_start,
period_end)` — `period_start`/`period_end` sont `None` **exactement** quand
`event_count == 0` (aucune sélection, ou une sélection dont les championnats n'ont aucun
événement pour l'année parcourue) : jamais de résumé à moitié rempli.

**Décision — où vit l'affichage : persistant, pas seulement au récapitulatif final**
Deux options ont été considérées : (a) enrichir uniquement le récapitulatif existant de
l'étape 4 avec les compteurs/période, ou (b) rendre le résumé **persistant sur les 4
étapes**. L'option (a) aurait satisfait "afficher un résumé avant génération" mais pas
l'esprit du sprint ("le calendrier doit devenir un véritable outil d'exploration" —
filtrer par année/championnat doit donner un retour *pendant* la navigation, pas
seulement au moment de générer). Décision : `_selection_summary_block(summary)` (nouvelle
fonction pure dans `gui/views/calendar.py`) est insérée dans `build_calendar_view` juste
après l'indicateur d'étapes, **avant** le corps spécifique à chaque étape — visible sur
les 4 étapes sans aucune duplication : les étapes "Saison"/"Championnats" donnent un
retour immédiat pendant le filtrage, et l'étape "Créer" affiche naturellement ce résumé
juste au-dessus de son récapitulatif existant (`_build_recap_controls()`, non modifié)
et du bouton de génération — satisfaisant "un résumé avant génération" sans dupliquer
aucun contenu.

Trois états rendus distinctement par `_selection_summary_block` :
1. `summary is None` — fetch de l'année en cours toujours en vol (`ProgressRing` +
   message de chargement) ; distinct à dessein d'un `SelectionSummary(event_count=0,
   ...)` résolu (sélection vide, fetch terminé) — deux états réels différents que
   `CalendarViewControls.selection_summary` doit pouvoir exprimer séparément.
2. `event_count == 0` — message dédié "Aucun championnat sélectionné".
3. Résumé peuplé — compteurs (pluralisation FR via `strings.plural`) + période
   `dd/mm/yyyy - dd/mm/yyyy`, ou un tiret si aucune session n'a d'heure de début
   (événement sans session, cas limite couvert par les tests).

`main_view.py` suit le même pattern de fetch en arrière-plan que `_load_weekend`/
`_load_dashboard` (Sprints 29/39) : `year_events` en closure (`dict[str, list[Event]] |
None`), `_load_year_events(year)` avec garde d'obsolescence (`if year != state.year:
return` — ignore une réponse tardive pour une année que l'utilisateur a déjà quittée),
déclenché une fois au lancement (année par défaut) puis à chaque changement d'année dans
`on_year_change` — jamais à chaque coche de case, le filtrage restant purement local.

**Conséquences**
- Aucun nouveau provider, aucune nouvelle source de données — conforme à la consigne du
  sprint.
- Le wizard 4 étapes existant est strictement inchangé dans sa structure (mêmes étapes,
  même navigation, même `GenerateState`) — seul un bloc supplémentaire s'intercale entre
  l'indicateur d'étapes et le corps de chaque étape.
- Une seule série de requêtes réseau par année parcourue (grâce au HttpCache existant) —
  changer de championnat coché ne coûte jamais de round-trip réseau supplémentaire.
- Le résumé reste volontairement simple (comptages + période, rien de plus) — pas de
  répartition par championnat, pas de fusion avec le récapitulatif de l'étape 4 ;
  documenté comme pistes futures dans `docs/TODO.md`, pas construit par anticipation.

---

## ADR-030 — Dashboard : logique dédiée réutilisant le pipeline de fetch existant, pas un second

**Contexte**
Sprint 39. Premier sprint "valeur" du projet après huit sprints d'extension de
championnats (Sprints 33-38) : aucun nouveau provider, aucune nouvelle source de données
— exploiter les 17 championnats déjà intégrés en construisant la première version d'un
Tableau de bord, qui devient la page d'accueil de l'application. Contraintes explicites :
créer une vue dédiée, ne déplacer aucune logique métier dans la GUI, réutiliser les
composants existants, respecter intégralement le Design System et le Layout System,
aucun travail sur les icônes, les placeholders restent utilisés.

**Ce que le Dashboard doit afficher** (six informations, brief du sprint) : le prochain
week-end de course, le nombre de championnats disponibles, le nombre d'événements de la
saison, le nombre de sessions, les championnats présents ce week-end, le prochain départ
(date + heure).

**Décision — où vit la logique**
En observant les six informations demandées, deux d'entre elles ("prochain week-end de
course", "championnats présents ce week-end") sont exactement ce que
`upcoming_weekend.find_upcoming_weekend` calcule déjà depuis le Sprint 29 — et les
quatre autres ("nombre de championnats disponibles", "nombre d'événements de la
saison", "nombre de sessions", "prochain départ") se dérivent de la **même matière
première** : la liste d'événements que `controller.get_upcoming_weekend` récupère déjà
pour chaque championnat (année courante + suivante). Plutôt que d'écrire un second
pipeline de fetch pour le Dashboard (dupliquant registries/HttpCache/gestion d'erreurs
déjà éprouvés), la boucle de fetch de `get_upcoming_weekend` a été extraite en
`controller._fetch_weekend_entries()` — un unique point d'entrée réseau, appelé par les
deux fonctions publiques (`get_upcoming_weekend()` pour "Ce week-end",
`get_dashboard_data()` pour le Dashboard). Comportement strictement préservé (vérifié
par la suite de tests `test_gui_controller.py`/`test_gui_upcoming_weekend.py`
intégralement verte après refactor, sans modification) — c'est une factorisation
justifiée par un second consommateur réel apparaissant dans ce sprint, pas une
anticipation, cohérente avec le principe déjà appliqué aux providers depuis le
Sprint 35 (ADR-026).

Nouveau module `gui/dashboard.py`, mirroring exact de `upcoming_weekend.py` :
- Aucun import Flet — entièrement testable avec de simples fixtures `Event`/`Session`,
  sans mock HTTP (le fetch vit dans `controller.get_dashboard_data`, jamais dans ce
  module).
- `build_dashboard_data(entries, total_championships, now) -> DashboardData` réutilise
  `find_upcoming_weekend(entries, now=now)` pour le week-end (jamais réimplémenté — "Ce
  week-end" et le Dashboard sont garantis de toujours s'accorder sur le prochain
  week-end, par construction, pas par convention).
- Les statistiques de saison filtrent `entries` sur `event.season == now.year` — les
  événements de l'année suivante (récupérés pour couvrir un week-end à cheval sur le
  nouvel an) ne polluent jamais le compte "de la saison".
- "Prochain départ" est défini comme la prochaine session `SessionType.RACE`
  (uniquement — jamais Sprint/Hyperpole) toutes classes confondues à partir de *now* —
  un choix délibéré et documenté : "départ" se lit comme "prochain Grand Prix/Course",
  pas "prochaine session sur piste".
- Nouvelle fonction publique `upcoming_weekend.format_session_datetime(start,
  circuit_timezone) -> str` ("Dimanche 12/07 15:00", fuseau local du circuit) — le
  "prochain départ" est un stat isolé qui, contrairement à une ligne de session déjà
  contextualisée à l'intérieur d'une ChampionshipCard sur un week-end connu, a besoin de
  la date complète, pas seulement du jour + heure. Réutilise `_circuit_zone` et
  `_DAY_LABELS_FR` déjà existants plutôt que de les dupliquer — même principe de
  factorisation-au-second-usage.

**Décision — la vue**
`gui/views/dashboard.py` suit exactement le patron établi par `views/weekend.py` :
2 états (`build_dashboard_view(None)` = chargement, `build_dashboard_view(data)` =
chargé), entièrement composé du Layout System (`PageContainer`/`PageHeader`/`Section`/
`SectionHeader`/`EmptyState`) plus `theme.card()`/`theme.chip()` pour respectivement les
4 stat cards et les puces de championnats du week-end — aucun nouveau composant, aucun
nouveau token de Design System introduit. Devient la page d'accueil : premier onglet de
la barre de navigation (`nav_rail.selected_index=0`, les 5 onglets existants décalés
d'un cran), chargé en arrière-plan au lancement via `page.dashboard_load_task`, exact
mirroir du pattern déjà établi pour "Ce week-end" (`page.weekend_load_task`, Sprint 29).

**Conséquences**
- Aucun nouveau provider, aucune nouvelle source de données — conforme à la consigne du
  sprint.
- Le Dashboard et "Ce week-end" ne peuvent jamais diverger sur "quel est le prochain
  week-end" ou "quels championnats y sont présents" : ils appellent littéralement la même
  fonction pure sur les mêmes données.
- Une seule série de requêtes réseau par lancement pour les deux pages combinées (grâce
  au HttpCache déjà en place + au pipeline désormais partagé) — pas de coût réseau
  supplémentaire pour la nouvelle page.
- Le Dashboard reste volontairement simple (exactement les 6 informations demandées) —
  aucune stat card cliquable, aucun historique, aucun raccourci vers d'autres pages ;
  documenté comme pistes futures dans `docs/TODO.md`, pas construit par anticipation.

---

## ADR-029 — `PulseliveGpSource` : abstraction API officielle partagée MotoGP/Moto2/Moto3 ; stub WorldSBK

**Contexte**
Sprint 38. Objectif : ajouter MotoGP, Moto2, Moto3 et World Superbike (WorldSBK), en
mutualisant "uniquement lorsqu'une abstraction apparaît naturellement" — sans factoriser
par anticipation, sans casser l'architecture existante. Consigne : étudier les meilleures
sources disponibles.

**Investigation — MotoGP/Moto2/Moto3**
Recherche du dataset `sportstimes/f1` (déjà utilisé pour F2/F3/F1 Academy/Formula E) :
contient bien un dossier `motogp/`, mais ne couvre QUE la classe reine (site
`motogpcal.com`), pas Moto2/Moto3, et aucune trace de WorldSBK dans l'écosystème
`sportstimes`. Recherche directe sur motogp.com (fetch HTML réel, pas de résumé IA) :
la page calendrier référence `api.pulselive.motogp.com`. Sondage direct de cette API
(`curl`, endpoints devinés puis affinés à partir des messages d'erreur 400 explicites du
serveur, ex. `"Required request parameter 'seasonYear'..."`) révèle une **API REST
officielle, non authentifiée, appartenant à Dorna Sports** :
`GET /motogp/v1/events?seasonYear={year}` retourne en une seule requête tous les
événements de la saison (tests, présentations média, et rounds réels distingués par
`kind: "GP"`), et chaque round de Grand Prix embarque déjà un tableau `broadcasts` avec
**toutes les sessions de toutes les classes** (`category.acronym`: `MGP`/`MT2`/`MT3`),
chacune avec une vraie heure de début ET de fin (`date_start`/`date_end`) — qualité de
données strictement supérieure au JSON-LD ACO (Sprint 35) et bien supérieure au scraping
HTML SRO (Sprint 37), sans que la moindre page HTML n'ait besoin d'être parsée.

**Décision — MotoGP/Moto2/Moto3**
`providers/motogp_series/pulselive_base.py::PulseliveGpSource(JsonDataSource, ABC)` —
toute la logique HTTP/cache/filtrage de saison/classification de broadcasts/fusion de
sessions vit ici. Les sous-classes ne déclarent que 3 propriétés : `_series_key`,
`_category_acronym`, `_race_duration_minutes`, plus `_make_championship()`.
`providers/motogp/`, `moto2/`, `moto3/` suivent chacun le patron Provider/Source déjà
établi. Aucune table de circuits à maintenir (contrairement à ACO/SRO) : le pays, la ville
et le fuseau horaire IANA (`time_zone`, ex. `"ASIA/BANGKOK"` → `.title()` →
`"Asia/Bangkok"`, vérifié valide via `zoneinfo` sur les 18 fuseaux distincts de la saison
2026) sont tous directement exposés par la source — une amélioration architecturale
naturelle par rapport aux deux sprints précédents, pas une simplification forcée.

Deux subtilités de données gérées **génériquement** (pas par classe) :
1. **3 séances PRACTICE par classe et par week-end, mais seules 2 numérotées.** Chaque
   classe court `FP1`, une séance simplement appelée `PR` ("Practice", sans numéro), puis
   `FP2` — la séance non numérotée tombe chronologiquement ENTRE les deux numérotées.
   Plutôt que de faire confiance aux libellés (qui ne mappent pas proprement sur les 3
   emplacements `FP1`/`FP2`/`FP3` du modèle), les 3 séances sont triées chronologiquement
   et assignées par ordre de créneau — `Session.title` conserve le libellé réel de la
   source, donc l'écart entre "notre FP2" (le "PR" source) et "notre FP3" (le "FP2"
   source) reste visible, jamais masqué.
2. **Qualifying en deux segments (Q1/Q2) par classe**, fusionnés en une seule session
   `QUALIFYING` allant du début de Q1 à la fin réelle de Q2 — contrairement à ACO/SRO, la
   source fournit déjà une vraie heure de fin, aucune durée n'est inventée pour cette
   fusion.

Seules les sessions `RACE`/`SPRINT` (Sprint MotoGP uniquement, jamais couru par Moto2/
Moto3) n'ont pas d'heure de fin réelle — la source renvoie systématiquement
`date_start == date_end` pour ces deux types. Durée par défaut documentée par classe/
format (`_race_duration_minutes`, propriété abstraite par sous-classe), cohérent avec
l'approche déjà établie par `JolpicaSource`/`OpenF1Source`/ACO/SRO pour leurs propres
durées par défaut.

**Bug réel détecté en vérification live (pas en test unitaire), corrigé avant
livraison :** la source rapporte chaque horodatage avec le décalage UTC local du circuit
(ex. `2026-02-27T10:45:00+0700`), jamais en UTC — contrairement à tous les autres
providers du projet, qui stockent systématiquement des horaires de session en UTC.
Conserver l'offset local tel quel faisait produire à `IcsExporter` un
`DTSTART;TZID="UTC+07:00"` synthétique, sans bloc `VTIMEZONE` correspondant dans le
calendrier exporté — un identifiant de fuseau non standard que certains clients calendrier
pourraient mal interpréter. Corrigé en normalisant chaque horodatage vers UTC dans
`_parse_datetime` (`.astimezone(UTC)`), rétablissant la cohérence avec le reste du projet
et un `DTSTART` simplement suffixé `Z`.

**Investigation — WorldSBK**
World Superbike est organisé par Dorna Sports depuis 2022 (même groupe que MotoGP), donc
l'hypothèse initiale d'une plateforme partagée était raisonnable — mais non confirmée en
pratique. worldsbk.com tourne bien sur la même famille de plateforme ("Pulse Live",
confirmé via un fichier de traductions multi-tenant partagé,
`translations.gplat-prod.pulselive.com/wsbk/en.js`), mais son calendrier/planning est
**entièrement rendu côté client** (aucune donnée exploitable dans le HTML brut, contrairement
aux sites SRO GT du Sprint 37). Un hôte API candidat a été identifié dans le code source de
la page (`window.SD_DOMAIN = 'https://wsbk-api-origin.gplat-test.pulselive.com'`), mais il
ne répond pas aux requêtes externes (timeout de connexion sur les trois IP résolues — un
service probablement interne, non exposé publiquement, et son nom `-test` suggère même que
ce ne serait pas l'hôte de production). Plusieurs routes plausibles suivant la convention de
nommage de l'API MotoGP (`/wsbk/v1/events`, `/sbk/v1/events`, etc.) ont été testées
directement sur `api.pulselive.worldsbk.com` — toutes renvoient un vrai 404 applicatif
(pas une erreur de passerelle générique), confirmant l'hôte actif mais aucune des routes
devinées correcte. L'API MotoGP elle-même ne couvre pas WorldSBK : ses `circuit.timing_ids`
n'exposent jamais de business unit SBK (seulement `MGP`/`RKC`/`CEV`/`ATC`), confirmant une
plateforme réellement distincte, pas un simple filtre à ajouter.

**Décision — WorldSBK**
Résultats présentés à l'utilisateur (AskUserQuestion, 3 options : stub à la WEC/IMSA /
reporter WorldSBK entièrement / source suggérée par l'utilisateur). Option retenue :
**stub à la WEC/IMSA**. `providers/worldsbk/` enregistré et intégré partout (registry,
wizard, "Ce week-end", agrégateur, catégories, noms lisibles), avec
`OfficialWorldSbkSource.get_season` levant `NotImplementedError` — aucun horaire inventé,
aucune automatisation de navigateur ajoutée pour contourner un widget JS-only.

**Conséquences**
- MotoGP/Moto2/Moto3 sont la première extension de championnat du projet où la source
  officielle s'est révélée strictement meilleure que toutes les alternatives déjà
  rencontrées (JSON-LD, HTML scrapé) — confirmant que la priorité "API officielle
  d'abord" de la politique de sourcing du projet paie quand elle existe vraiment.
- Nouveau groupe GUI "🏍 Moto" réutilise `Category.MOTO`, déjà présente dans l'énumération
  depuis le Sprint 37 (la docstring de `categories.py` anticipait explicitement ce
  scénario : "To add a new group (e.g. Moto): 1. Add MOTO... 2. Append a
  ChampionshipGroup...") — aucune modification d'énumération nécessaire ce sprint,
  seulement l'ajout du groupe lui-même.
- WorldSBK reste une dette technique explicite et documentée (`docs/DATA_SOURCES.md`,
  `docs/TODO.md`) : tant qu'aucune source n'est trouvée, il n'apparaîtra jamais dans
  "Ce week-end" ni dans un export réel — au même titre que WEC/IMSA.

---

## ADR-028 — `SroTimetableSource` : abstraction HTML partagée pour les séries SRO GT

**Contexte**
Sprint 37. Objectif : ajouter GT World Challenge Europe, America, Asia et
l'Intercontinental GT Challenge (IGTC), en factorisant "uniquement lorsque
cela est justifié" — sans factoriser par anticipation. Consigne stricte de
priorité de source : API officielle d'abord, sinon source stable et
documentée, scraping HTML en tout dernier recours.

**Investigation**
Aucune API publique documentée pour aucune des quatre séries. Fetch direct
du HTML réel des quatre sites `.com` (pas de résumé IA à cette étape — le
futur code de parsing doit correspondre au HTML octet pour octet) : les
quatre tournent sur un CMS identique (URL `/event/{id}/{slug}` partout,
mêmes classes CSS `timetable__container`/`timetable__table`/
`feature__heading`) — confirmé en comparant des pages réelles des quatre
domaines, pas supposé depuis un seul site. Contrairement à WEC/ELMS/MLMC
(Sprint 35), aucun bloc JSON-LD n'est présent nulle part sur ces sites —
seul un tableau HTML classique par jour donne les horaires de session
(colonnes Session / Local Time / GMT, aucune heure de fin). C'est donc la
seule des extensions de championnat menées jusqu'ici où le scraping HTML
"au sens littéral" (au lieu d'une donnée structurée intermédiaire comme le
JSON-LD ACO ou le JSON `sportstimes/f1`) est réellement le dernier recours
justifié par l'absence de toute alternative.

Deux difficultés de données rencontrées et résolues génériquement (pas par
série) :
1. **Format "Sprint Cup" à deux manches** (GT World Challenge Europe/Asia :
   deux blocs Qualifying, deux blocs Race, sur des jours différents) contre
   **format à une seule course** (Endurance Cup, GT World Challenge
   America, IGTC). Plutôt que supposer un nombre de sessions Race fixe par
   série, chaque événement compte lui-même ses propres entrées "Race" :
   une seule → `QUALIFYING`/`RACE` classiques ; deux → la première
   chronologiquement est relabellée `SPRINT_QUALIFYING`/`SPRINT` (même
   mécanisme déjà utilisé pour les week-ends Sprint F1), la seconde reste
   `QUALIFYING`/`RACE`. Les entrées Qualifying sont ensuite réparties selon
   la Race qu'elles précèdent chronologiquement — cette logique s'applique
   uniformément aux deux formats sans branche par série.
2. **Séances Free Practice en surnombre** (Bathurst 12 Hour : jusqu'à 6
   séances Free Practice numérotées sur deux jours, alors que le modèle de
   domaine n'a que 3 emplacements `FP1`/`FP2`/`FP3`). Les deux premières
   séances (par ordre chronologique) mappent normalement ; tout ce qui suit
   la 3ème est fusionné dans une seule session `FP3` (span étendu jusqu'à
   la dernière séance) plutôt que perdu — même philosophie de fusion que le
   contournement multi-classe d'ACO (Sprint 35, ADR-026), appliquée ici à
   un motif de données différent.

**Bug réel détecté en vérification live (pas en test unitaire), corrigé
avant livraison :** combiner directement la date locale de la légende du
tableau (ex. "Friday, 13 February") avec l'heure de la colonne GMT produit
un jour UTC incorrect chaque fois que le décalage horaire du circuit pousse
une séance du petit matin local vers la veille en UTC — confirmé sur
Bathurst 12 Hour (Sydney, UTC+10/+11) : la première séance d'essais libres
du vendredi matin local se retrouvait calculée sur jeudi UTC. Corrigé en
calculant le véritable instant UTC à partir de l'écart entre les colonnes
"Local Time" et "GMT" de chaque ligne du tableau (la date locale ancre
l'heure locale, cet écart la convertit en UTC) — aucune base de données de
fuseaux horaires externe requise, la source donne déjà les deux valeurs
nécessaires sur chaque ligne.

**Décision**
`providers/sro_series/timetable_base.py::SroTimetableSource(HtmlDataSource,
ABC)` — toute la logique HTTP/cache/scraping HTML/classification de
sessions/inférence de durée vit ici. Les sous-classes ne déclarent que
2 propriétés : `_series_key`, `_base_url`, plus `_make_championship()`.
`providers/gtwc_europe/`, `gtwc_america/`, `gtwc_asia/` et `igtc/` suivent
chacun le patron Provider/Source déjà établi, leur source concrète
(`sources/sro_scraper.py::SroScraperSource`) héritant de
`SroTimetableSource`. `sro_series/circuit_data.py` centralise les données
de circuit **partagées** entre les quatre séries, clé = slug d'URL — un
même slug (`crowdstrike-24-hours-of-spa`) identifie la même venue réelle
sur plusieurs domaines SRO, constaté empiriquement (pas supposé). Le pays
n'est volontairement PAS dans cette table : la balise `<title>` de chaque
page l'expose déjà de façon fiable et cohérente sur les quatre sites — plus
précis qu'une table maintenue à la main.

Durée de course inférée depuis un motif "N Hour(s)" trouvé dans le slug
d'URL de l'événement (`bathurst-12-hour` → 12h, `crowdstrike-24-hours-of-
spa` → 24h) — repli sur une durée par défaut générique pour les formats
sans motif horaire explicite (ex. `suzuka-1000km`), une approximation
assumée et documentée, cohérente avec les durées par défaut déjà utilisées
par `JolpicaSource`/`OpenF1Source` pour d'autres types de session.

Numérotation des rounds : chaque championnat re-numérote ses rounds
séquentiellement lui-même (comme `AcoSportsEventSource`), plutôt que
d'essayer de reproduire le texte "Round N" du site — nécessaire de toute
façon pour GT World Challenge Asia, qui étiquette certains rounds "Round N
& M" (un même week-end comptant double dans son propre système de points),
texte qu'il aurait été absurde de vouloir reproduire fidèlement.

**Conséquences**
- Aucun nouveau `SessionType` introduit — le format Sprint Cup réutilise
  `SPRINT_QUALIFYING`/`SPRINT` (déjà présents pour F1), et "Superpole" (une
  séance shootout à un tour, présente sur certains rounds Endurance
  Cup/IGTC) réutilise `HYPERPOLE` — sémantiquement apte, le terme
  "Superpole" étant d'ailleurs l'origine historique du terme "Hyperpole"
  utilisé par le WEC.
- Certains rounds éloignés dans le calendrier (ex. Indianapolis 8 Hour, GT
  World Challenge America 2026) n'ont pas encore de tableau d'horaires
  publié par SRO — ces événements sont silencieusement exclus de la saison
  retournée par `get_season()` plutôt que d'apparaître avec zéro session ;
  ils apparaîtront automatiquement dès que SRO publie leur planning.
- IGTC partage deux de ses cinq rounds (CrowdStrike 24 Hours of Spa,
  Indianapolis 8 Hour) avec GT World Challenge Europe/America respectivement
  — chaque site les numérote et les identifie indépendamment (IDs d'événement
  différents), et aucune déduplication inter-championnats n'existe nulle
  part dans ce projet (WEC/ELMS/MLMC ont déjà ce même chevauchement
  conceptuel autour de l'esprit du Mans) : ce n'est pas un défaut à
  corriger, c'est le même choix architectural que le reste du projet.

---

## ADR-027 — Provider IMSA : stub à la WEC après investigation exhaustive, aucune source viable trouvée

**Contexte**
Sprint 36. Objectif explicite de l'utilisateur : sortir de l'écosystème ACO et valider que
l'architecture Provider/Source généralise à un championnat majeur organisé par une entité
totalement extérieure — IMSA WeatherTech SportsCar Championship. Consigne stricte :
privilégier une API officielle, à défaut une source stable et documentée, le scraping HTML
en dernier recours seulement.

**Investigation (chaque piste vérifiée en direct, aucune supposition)**
- Aucune API publique documentée pour IMSA.
- `imsa.com` est bloqué au niveau infrastructure, pas seulement hostile au scraping :
  `curl` avec en-têtes navigateur complets renvoie HTTP 403 avec `cf-mitigated: challenge`
  sur absolument toutes les routes testées — page d'accueil, page calendrier, articles de
  presse, et même des PDF statiques sous `/wp-content/uploads/`. Un contournement
  nécessiterait une automatisation de navigateur complète (Playwright), une classe de
  dépendance bien plus lourde que tout ce qui existe déjà dans le projet, et plus proche
  d'un contournement actif d'anti-bot que d'un scraping raisonnable — non tenté.
- Le prestataire de chronométrage d'IMSA est Al Kamel Systems — le même que
  WEC/ELMS/MLMC (`imsa.results.alkamelcloud.com` est d'ailleurs accessible, contrairement
  à imsa.com). Mais ce portail est une **archive de résultats post-course** : les dossiers
  de session (ex. `202606261125_Practice 1`) n'existent qu'*après* que la session ait eu
  lieu. Aucune donnée de calendrier prévisionnel exploitable.
- Wikipedia expose un tableau de calendrier propre et stable via son API MediaWiki
  officielle (`action=parse`, page "2026 IMSA SportsCar Championship", section
  "Schedule") : round, nom de course, circuit, ville, date — mais **aucun horaire de
  session** (pas de FP1/FP2/Qualifying/Race), seulement des dates de course (parfois des
  plages) et une durée. Insuffisant pour construire un `Session` valide (qui exige un
  début et une fin) sans inventer des horaires.
- Les médias spécialisés (Sportscar365, 51gt3.com) publient des horaires de session, mais
  uniquement en prose libre à l'intérieur d'articles individuels ("qualifying gets
  underway at 3:40 p.m. EST") — pas de données structurées. 51gt3.com a lui-même renvoyé
  HTTP 403 au test. Parser du texte en langage naturel de façon fiable sur ~11 rounds x
  plusieurs sessions serait fragile et ne correspond pas à une "source stable et
  documentée" au sens de ce projet.

**Décision**
Présenter les résultats de l'investigation à l'utilisateur (AskUserQuestion, 3 options :
stub à la WEC / calendrier partiel basé sur Wikipedia avec horaires inventés / autre
source suggérée par l'utilisateur). Option retenue : **stub à la WEC**. Enregistrer
l'architecture Provider/Source complète — `providers/imsa/` (`ImsaProvider`/`ImsaSource`
ABC + `sources/official.py::OfficialImsaSource`), mirroring exact de `providers/wec/` —
et l'intégrer partout (registry, wizard, "Ce week-end", agrégateur `generate`, catégories,
noms lisibles), avec `OfficialImsaSource.get_season` levant `NotImplementedError`.
Aucun horaire de session n'est inventé ; aucun provider existant n'est modifié.

**Conséquences**
- IMSA apparaît dans toute l'UI (groupe "Endurance", aux côtés de WEC/ELMS/MLMC) et dans
  la CLI (`generate-imsa`), mais échoue proprement partout où une vraie source serait
  nécessaire — exactement le même comportement observable que WEC depuis le Sprint 26.
  "Ce week-end" et `generate` gèrent déjà ce cas nativement (aucun changement requis dans
  `upcoming_weekend.py`/`cli.py` au-delà de l'enregistrement du provider).
- Valide empiriquement que l'architecture Provider/Source ne suppose rien de spécifique
  aux sources déjà connues (JSON GitHub, API REST, JSON-LD schema.org) — un stub complet
  s'intègre sans aucune modification aux couches registry/GUI/CLI existantes.
- Dette technique explicite, documentée dans `docs/DATA_SOURCES.md` et `docs/TODO.md` :
  tant qu'aucune source n'est trouvée, IMSA n'apparaîtra jamais dans "Ce week-end" ni dans
  un export réel — au même titre que WEC.

---

## ADR-026 — `AcoSportsEventSource` : abstraction JSON-LD partagée pour les séries ACO

**Contexte**
Sprint 35. Objectif : ajouter ELMS et Michelin Le Mans Cup, sans copier-coller, en
factorisant avec WEC "si une logique commune apparaît" — sans factoriser par
anticipation. `OfficialWecSource` restait un stub (`NotImplementedError`) : aucune
logique WEC existante à refactoriser au départ.

Investigation (aucune API publique documentée pour aucune des trois séries, confirmé) :
fetch direct du HTML réel de `fiawec.com`, `europeanlemansseries.com` et `lemanscup.com`
(pas de résumé IA pour cette étape — le futur code de parsing doit matcher le HTML
octet pour octet). Constat empirique : les trois sites tournent sur le même CMS ACO
(nav secondaire de fiawec.com confirmée : "24H Le Mans, ELMS, MLMC, ALMS") et chaque page
course (`/en/race/{slug}`) embarque un unique bloc
`<script type="application/ld+json">` schema.org `SportsEvent`, avec un tableau
`subEvent` — un objet par session, horodatage ISO 8601 avec offset UTC exact. Le calendrier
saison (`/en/season/{year}`) n'a pas cette structure — seule la liste des liens
`/en/race/{slug}` y est scrapée en HTML classique.

Deux problèmes de données rencontrés et résolus génériquement (pas par série) :
1. Qualifications multi-classes (ex. Barcelone ELMS : 4 créneaux de 25 min consécutifs,
   un par classe LMGT3/LMP3/LMP2 PRO-AM/LMP2) mappent tous vers
   `SessionType.QUALIFYING` — collision d'UID (`{event_uid}-{session.type}`, voir
   `exporters/ics.py`). Contrairement au contournement F1 Academy (ADR-016 : relabelling
   d'une session vers un `SessionType` non lié, ex. `race2` → `FP3`), les créneaux
   identiques sont ici **fusionnés** en une seule `Session` couvrant le premier au
   dernier créneau — sémantiquement honnête (une seule "heure de qualifications" plutôt
   que 4 entrées de calendrier quasi dupliquées), et l'unicité d'UID est acquise sans
   aucun artifice.
2. Jours de tests pré-saison ("Official Tests"/"Collective Tests") : exclus de la liste
   des rounds scrapés. Ce ne sont pas des manches du championnat (aucun autre provider du
   projet n'inclut les essais privés F1 par exemple), et leur structure de sessions
   ("Morning Session"/"Afternoon Session" répétés sur plusieurs jours) recréerait le même
   problème de collision sans bénéfice pour l'utilisateur.

**Décision**
`providers/aco_series/sports_event_base.py::AcoSportsEventSource(HtmlDataSource, ABC)` —
toute la logique HTTP/cache/scraping HTML/parsing JSON-LD/fusion de sessions vit ici.
Les sous-classes ne déclarent que 4 propriétés : `_series_key`, `_base_url`,
`_event_name_prefix`, `_circuit_data`, plus `_make_championship()`. `providers/elms/` et
`providers/mlmc/` suivent chacun le patron Provider/Source déjà établi
(`ElmsProvider`/`ElmsSource`, `MlmcProvider`/`MlmcSource`), leur source concrète
(`sources/aco_scraper.py::AcoScraperSource`) héritant de `AcoSportsEventSource`.
`aco_series/circuit_data.py` centralise les données de circuit **partagées** entre ELMS
et MLMC (co-localisées sur les 6 mêmes circuits 2026, constaté empiriquement, pas
supposé) — factorisation justifiée par un fait, pas par anticipation. Road to Le Mans
n'obtient pas de `championship_id` séparé : elle apparaît comme un round de plus dans la
liste `mlmc`, exactement comme sur le site officiel — aucun code spécial requis.

WEC n'est **pas** rattachée à cette abstraction dans ce sprint (hors périmètre demandé,
et la structure exacte d'une vraie manche fiawec.com — par opposition à un Prologue —
n'a pas été confirmée) ; l'opportunité est documentée dans `docs/TODO.md` plutôt
qu'implémentée par anticipation.

**Bugs réels détectés en vérification live (pas en test unitaire), corrigés avant
livraison :**
- Durée de course "Road to Le Mans" calculée depuis `endDate` de l'événement top-level :
  +61h au lieu de ~3h, car cet `endDate` couvre toute la semaine des 24 Heures du Mans,
  pas seulement la course RTLM elle-même. Corrigé par un plafond de plausibilité
  (`_MAX_PLAUSIBLE_RACE_DURATION = timedelta(hours=26)`, couvre même Le Mans 24h) — au-delà,
  repli sur la durée par défaut documentée comme estimation.
- `fetch_html` devait être rendu transparent au cache (même contrat que
  `F1CalendarBaseSource.fetch_json`, qui encapsule sa propre logique de cache en interne).
  La conception initiale isolait le cache dans une méthode `_cached()` séparée
  au-dessus de `fetch_html` — un mock posé sur `fetch_html` en test ne suffisait donc pas
  à contourner le vrai cache disque, révélé par une pollution croisée entre tests dans
  `test_cli_generate.py`. Corrigé en déplaçant la logique de cache directement dans
  `fetch_html`, supprimant `_cached()` — aucun changement de comportement observable.

**Conséquences**
- Nouvelle dépendance : `beautifulsoup4`/`lxml` (`core/datasource/html_source.py`
  anticipait déjà cette classe d'implémentation dans sa docstring — "typical
  implementations use httpx or playwright... and BeautifulSoup / lxml").
- `AcoSportsEventSource.get_season(year)` ne fonctionne que pour la saison courante —
  aucun des deux sites ne publie d'archive par année à une URL prévisible
  (`/en/season/{year}` répond 404 pour toute année différente de l'année courante,
  vérifié en direct). Comportement documenté, pas contourné : propage
  `httpx.HTTPStatusError`, cohérent avec le reste du projet.
- Si `OfficialWecSource` rejoint un jour cette abstraction (voir `docs/TODO.md`),
  implémenter WEC pour de vrai deviendrait presque gratuit — même bénéfice que
  `F1CalendarBaseSource` a apporté à Formula E.

---

## ADR-025 — Formula E sur `F1CalendarBaseSource` + factorisation de `cli.py`

**Contexte**
Sprint 34. Objectif : prouver que l'architecture Provider/Source accueille un nouveau
championnat sans duplication de code, en ajoutant Formula E. Le brief citait "F1 Academy"
comme manquant ; vérification faite en début de sprint (confirmée avec l'utilisateur) —
F1 Academy existe déjà entièrement depuis le Sprint 29+ (provider, source, wizard, "Ce
week-end", CLI). Le périmètre réel était donc Formula E seule.

Recherche préalable (pas d'hypothèse) : le dataset déjà utilisé par F2/F3/F1 Academy
(`sportstimes/f1` sur GitHub, MIT) contient un dossier `_db/fe/` — Formula E y est déjà
présente, au même format (`{"races": [...]}`, `name`/`location`/`round`/`slug`/`sessions`).
Vérifié en direct (fetch réel de plusieurs saisons 2023-2025) avant d'écrire une seule
ligne de mapping.

**Décision**
1. `providers/formula_e/` suit exactement le patron F1 Academy : `FormulaEProvider`/
   `FormulaESource` (ABC) + `sources/f1calendar.py` qui hérite de
   `F1CalendarBaseSource` (ADR implicite du Sprint pré-15) sans aucune logique HTTP/cache/
   mapping propre — seuls `_series_key="fe"`, `_SESSION_MAP`
   (`practice1/practice2/practice3/qualifying/race`) et `_CIRCUIT_DATA` (16 circuits) sont
   spécifiques. Différence notable avec F1 Academy : un week-end Formula E double-header
   est déjà **deux rounds distincts** dans le dataset (chacun avec son propre `round` et sa
   propre session `race` unique) — aucun contournement d'UID façon SPRINT/FP3 n'est
   nécessaire ici.
2. `cli.py` : les 5 commandes `generate-f1/f2/f3/f1-academy/wec`, copiées-collées à chaque
   ajout de championnat depuis l'origine, sont factorisées vers un helper partagé
   `_run_generate_command()` (paramétré par `championship_id`, `fetch_label`,
   `default_source`, `error_prefix`, `not_implemented_message` optionnel pour le cas WEC).
   Chaque commande reste un wrapper Typer fin (conserve sa propre docstring/aide `--help`,
   Typer les introspecte). `generate-formula-e` est ajoutée sur ce même helper — sixième
   commande, code marginal ajouté ≈ 10 lignes au lieu de ≈ 75.
3. Intégration GUI : 3 lignes ajoutées (`categories.py` groupe "Formula",
   `display_names.py` nom lisible, `upcoming_weekend.py::WEEKEND_CHAMPIONSHIP_IDS`) —
   aucune ligne dans `main_view.py`/`calendar.py`, entièrement pilotés par
   `registry.list_all()`/`categories.get_groups_for()`/`display_names.get_display_name()`.

**Conséquences**
- Confirme empiriquement que l'architecture absorbe un nouveau championnat f1calendar en
  une seule nouvelle unité (`providers/X/`) + 4 lignes ailleurs (3 GUI + 1 CLI générique) —
  aucune modification de `core/registry.py`, `core/source_registry.py`,
  `config/models.py` (`ProvidersConfig.get()` gère déjà les extras via `model_extra`).
- La factorisation de `cli.py` est un changement de comportement zéro (verrouillé par les
  tests existants des 5 commandes déjà en place, tous passés sans modification) — réduction
  de dette pré-existante en prime : `cli.py` 355→182 lignes, 13→5 erreurs mypy, 48→19
  lignes non couvertes.
- La confusion initiale du brief sur F1 Academy est documentée ici plutôt que silencieusement
  corrigée — le vrai périmètre (Formula E seule) a été confirmé avec l'utilisateur avant
  tout développement.
- Prochain championnat sur ce même dataset (Porsche Supercup, mentionnée dans la docstring
  de `F1CalendarBaseSource`) : suivre ce même patron, vérifier le schéma JSON réel d'abord.

---

## ADR-024 — `gui/championship_assets.py` : registre central des identités visuelles

**Contexte**
Sprint 33. Objectif : afficher le logo officiel de chaque championnat à gauche du titre
dans `ChampionshipCard`, sans coder de chemin de fichier dans une vue ni de branche
`if championship_id == "formula1"` dans le composant. Recherche préalable (dans
`motorsport-calendar` et `BApps-Studio`, où vit le Brand Set) : **aucun fichier logo de
championnat n'existe dans le projet** — seuls les assets de la marque *Motorsport
Calendar* elle-même sont présents (et toujours au stade placeholder, non copiés). Décision
prise avec l'utilisateur : construire le registre "prêt à recevoir" plutôt que d'inventer
des fichiers factices faisant office de faux logos officiels.

**Décision**
Un module dédié, `gui/championship_assets.py`, expose un unique point d'entrée
`get_championship_asset(championship_id: str) -> ChampionshipAsset(logo_src: str | None)`.
`logo_src` est un chemin Flet-relatif (`"championships/formula1.png"`), résolu UNIQUEMENT
si le fichier existe réellement sur disque (`_ASSETS_DIR / filename`) ; sinon `None` — id
inconnu et id connu dont le logo n'a pas encore été livré produisent exactement le même
résultat, jamais distingué par l'appelant. `ChampionshipCard._header_title()` interroge ce
registre et rend soit un `ft.Text` nu (aucun logo — comportement strictement identique à
avant ce sprint pour tous les championnats aujourd'hui), soit un `ft.Row([ft.Image(...),
ft.Text(...)])`, logo en `theme.IconSize.LG` (24px, token déjà existant, aucun nouveau
token créé). Aucune branche par championnat dans le composant — la seule décision qu'il
prend est "un logo a été résolu ou non".

**Conséquences**
- Suit exactement le patron déjà validé pour le logo de l'app (`gui/assets/logo/
  README.md`, Sprint 26) : dossier `gui/assets/championships/` livré vide (`.gitkeep` +
  README documentant les fichiers attendus), aucune autre modification nécessaire le jour
  où un vrai logo est déposé — `get_championship_asset()` le détecte à l'exécution.
- Extensible sans casser l'appelant : une future couleur/icône par championnat serait un
  champ de plus sur `ChampionshipAsset`, jamais un second point d'entrée.
- Zéro impact visuel dans l'état actuel du dépôt (aucun fichier livré) — vérifié par les
  999 tests et un script de smoke-test direct ; le layout de `ChampionshipCard` reste
  pixel pour pixel identique tant qu'aucun logo n'est déposé.
- `assets_dir=` reste commenté dans `gui/app.py` (partagé avec le logo de l'app) — même un
  logo déposé ne se résoudra visuellement qu'après ce décommentage, hors périmètre de ce
  sprint (documenté comme limite, pas comme un défaut de cet ADR).

---

## ADR-023 — `gui/event_display.py` : normalisation des métadonnées, en amont de la carte

**Contexte**
Sprint 32. Les cartes de championnat affichaient des incohérences ("Belgian / Belgian /
🇧🇪 Belgique", "Unknown") sur F2/F3/F1 Academy mais pas F1. Investigation (voir JOURNAL,
session Sprint 32) : F1 (Jolpica/Ergast) fournit un nom de Grand Prix complet, un nom de
circuit distinct et un pays réel ; F2/F3/F1 Academy partagent tous les trois
`providers/support_series/f1calendar_base.py`, qui mappe `Circuit.name` sur le même
descriptif court que `Event.name` (dataset `sportstimes/f1`, plus pauvre, sans champ nom
de circuit dédié) — d'où le doublon. Le pays "Unknown" vient de tables de couverture
`_CIRCUIT_DATA` incomplètes, propres à chaque module support-series. Corriger cela dans
les providers est hors périmètre de ce sprint.

**Décision**
Un module dédié, `gui/event_display.py`, décide de tout ce qu'il faut afficher ou masquer
à partir d'un `Event` brut : `normalize_event_display(championship_id, event) ->
EventDisplayData(grand_prix_name, circuit_name: str | None, country: str | None)`. Quatre
règles, toutes dans ce seul module : (1) doublon Grand Prix/Circuit → une ligne ; (2)
circuit inconnu → `circuit.name` puis repli sur `circuit.city` puis `None` ; (3) pays
inconnu (sentinelle `"Unknown"` ou vide) → `None`, jamais affiché ; (4) nom de Grand Prix
absent → suffixe " Grand Prix" ajouté pour les séries à ce format (F1/F2/F3/F1 Academy,
jamais WEC), repli sur le nom du circuit, puis un texte générique en dernier recours.

`ChampionshipCardData.circuit_name`/`.country` deviennent `str | None` ; `build_
championship_card` (le composant, Sprint 30) se contente d'omettre une ligne dont la
valeur est `None` — une simple omission conditionnelle, pas une décision. Le composant ne
contient toujours aucune logique métier ; toute la logique vit dans `event_display.py`.

**Conséquences**
- Corrige le défaut à la source des DONNÉES affichées sans toucher aux providers : la
  bonne valeur (`circuit.city`, souvent un meilleur nom de circuit pour F2/F3/F1 Academy)
  était déjà présente sur le modèle, seul le choix d'affichage était mauvais.
- `country_label()` (Sprint 29, formatage drapeau+nom FR) déménage de
  `upcoming_weekend.py` vers `event_display.py`, qui est désormais le seul endroit
  responsable de "quelle métadonnée d'événement afficher".
- Réutilisable par n'importe quelle future vue construisant des `ChampionshipCardData` à
  partir d'`Event` (Favoris, Recherche, Historique, ...) — la même normalisation
  s'applique automatiquement, sans dépendre de "Ce week-end".
- Limite assumée et documentée : pas de table démonyme complète ("Canada Grand Prix" au
  lieu de "Canadian Grand Prix") — jugée hors de proportion pour ce sprint.
- La couverture des tables `_CIRCUIT_DATA` par pays reste incomplète en amont — la ligne
  pays disparaît proprement plutôt que d'afficher "Unknown", mais un vrai pays
  n'apparaîtra pas tant que le provider (hors périmètre) n'est pas complété.

---

## ADR-022 — Layout System (`gui/components/layout/`) : en-tête toujours séparé du corps

**Contexte**
Sprint 31. Les 5 vues dupliquaient chacune la construction de leur conteneur de page, de
leur en-tête, de leurs espacements et de leur encartage — exactement le problème résolu
au niveau des cartes par ADR-021 (Sprint 30), mais au niveau de la page entière cette
fois. Objectif explicite : qu'une future page (Recherche, Tableau de bord, Notifications,
Historique, ...) se construise sans recréer ce code.

**Décision**
Sept composants à responsabilité unique dans `gui/components/layout/` : `PageContainer`
(largeur/padding/alignement, délègue à `theme.page_shell`), `PageHeader` (icône, titre,
sous-titre, séparateur), `Section` (espacement entre blocs), `SectionHeader` (intitulé
secondaire à l'intérieur d'une Section), `CardList` (liste verticale de cartes),
`EmptyState` (le "rien ici" encarté), `PageSpacing` (espace nommé ponctuel). Nommage
PascalCase délibéré (widget-style), avec exception `ruff.toml` scopée (`N802` sur ce seul
paquet) plutôt que des `noqa` dispersés.

Choix structurant : `PageHeader` est **toujours** un composant séparé, jamais absorbé
dans une carte de contenu — y compris pour Favoris et Ce week-end (vide), qui absorbaient
leur titre dans la carte depuis le Sprint 28 pour éviter un doublon visuel. Ce choix est
révisé ici : une future page avec un en-tête ET un contenu variable (ex. Recherche : titre
+ barre de recherche + résultats OU `EmptyState`) ne peut pas se permettre que son
`EmptyState` porte AUSSI le titre de la page — les deux responsabilités doivent rester
séparées dès maintenant, plutôt que de re-décorréler plus tard.

**Conséquences**
- Le titre de "Ce week-end" et "Mes favoris" apparaît désormais au-dessus de la carte
  plutôt qu'à l'intérieur — changement visuel mineur, assumé et documenté (voir JOURNAL,
  session Sprint 31).
- Les lignes de Préférences retrouvent leur bordure individuelle : la carte englobante
  unique du Sprint 28 (qui rendait cette bordure redondante) n'existe plus, chaque ligne
  redevient sa propre carte via `CardList` sans double encadrement.
- `championship_card.py` (Sprint 30) reste à sa place actuelle dans `gui/components/` —
  pas de réorganisation en sous-dossiers pour "faire symétrique" avec `layout/`, qui
  aurait été un remaniement sans bénéfice fonctionnel.
- `SectionHeader` est construit sans consommateur actuel — seul composant du sprint dans
  ce cas, justifié par une demande explicite du brief (nommé dans la liste des composants
  à créer), verrouillé par tests, prêt pour la première page à plusieurs groupes de cartes.
- Toute nouvelle page suit désormais le même moule :
  `PageContainer(header=PageHeader(...), body=[Section(...)])` — verrouillé par
  `TestLayoutSystemIntegration` (`tests/test_gui_components_layout.py`), qui construit une
  page hypothétique ("Historique", 2 sections avec `SectionHeader` + `CardList` chacune)
  sans aucun code de mise en page manuel, preuve directe de l'objectif du sprint.

---

## ADR-021 — `gui/components/` : bibliothèque de composants, séparée des vues et du thème

**Contexte**
Sprint 30. Jusqu'ici, chaque vue (`gui/views/*.py`) construisait entièrement son propre
layout à partir des primitives de `theme.py` (`card()`, `section_title()`, ...). "Ce
week-end" a le premier vrai besoin de layout réutilisable : une carte "événement d'un
championnat" qui devra réapparaître à l'identique dans Favoris, Recherche, Tableau de
bord, Calendrier, Notifications et Historique. Continuer à la reconstruire dans chaque
vue aurait garanti une dérive visuelle progressive (exactement le problème résolu au
Sprint 27 pour les pages, mais au niveau des cartes cette fois).

**Décision**
Nouveau paquet `motorsport_calendar/gui/components/`, distinct de `gui/views/` (une page =
un module, propriétaire de son état) et de `gui/theme.py` (tokens et primitives bas niveau
sans opinion sur le contenu). Un composant :
1. Définit son propre modèle de données minimal, déjà mis en forme (chaînes françaises,
   heures déjà converties) — jamais un objet du domaine (`Event`, `Session`, `Championship`,
   `Circuit`) ni un concept métier ("week-end", "favori", ...).
2. Se construit uniquement à partir des primitives de `theme.py` — aucun nouveau token.
3. Expose un point d'extension explicite (ici `footer: ft.Control | None`) plutôt que
   d'anticiper des fonctionnalités non demandées — le composant place le contrôle fourni
   sans jamais l'interpréter.

Premier composant : `championship_card.py` (`ChampionshipCardData`, `SessionRow`,
`build_championship_card`). Son modèle remplace `upcoming_weekend.WeekendCard`/`SessionRow`,
qui remplissaient déjà exactement ce rôle mais vivaient dans un module couplé au concept
"Ce week-end" — désormais promus à un emplacement neutre, `upcoming_weekend.py` les importe
au lieu de les définir.

**Conséquences**
- `views/weekend.py` ne construit plus aucun layout de carte : `_found_state` produit une
  liste de `build_championship_card(card)` — exactement l'attente exprimée ("la vue devra
  simplement construire une liste de ChampionshipCard").
- Une future vue Favoris/Recherche/Tableau de bord n'a qu'à produire des
  `ChampionshipCardData` depuis sa propre source de données (favoris sauvegardés, résultats
  de recherche, ...) et appeler `build_championship_card` — aucune modification au
  composant nécessaire.
- Ajouter un bouton Favori/Notifications/Export/Partage/Résultats plus tard se fait en
  construisant le contrôle du footer dans l'appelant et en le passant à
  `build_championship_card(data, footer=...)` — pas de changement de signature.
- 23 tests dédiés (`tests/test_gui_components_championship_card.py`) verrouillent l'ordre
  de l'en-tête, l'alignement de la grille de sessions (indépendant de la longueur du
  libellé), le comportement du footer (absent par défaut, extensible sans interprétation),
  et le rendu pour les 5 championnats actuels + un événement de forme différente (24h du
  Mans) — preuve directe de réutilisabilité, pas seulement de non-régression.

---

## ADR-020 — `WeekendEntry` : transporter l'id de championnat plutôt que le déduire

**Contexte**
Sprint 29 — "Ce week-end" doit regrouper les événements du week-end trouvé par catégorie
(Formula puis Endurance, via `categories.get_groups_for`) et afficher un nom lisible
(`display_names.get_display_name`). Ces deux fonctions attendent l'id brut du registre
(`"formula1"`, `"wec"`, …). En développant avec de vraies données (pas seulement des
fixtures), le regroupement échouait silencieusement : tout finissait dans le groupe
"Autres" de secours de `get_groups_for`.

**Cause racine**
Chaque provider construit ses `Event` avec un `Championship.id` suffixé par l'année —
`f"{cid}-{year}"` (`"formula1-2026"`, `"f1-academy-2026"`, …), visible dans
`jolpica.py::_make_championship`, `f1calendar.py::_make_championship` (F2/F3/F1 Academy).
Ce n'est pas un bug de ces providers : c'est un identifiant de *saison*, cohérent avec son
usage existant (`Formula1Provider.fetch_championship` produit le même format). Mais rien
dans le reste de la GUI n'avait encore eu besoin de comparer cet id à l'id du registre —
`generate_calendar`/`list_championships` ne le font jamais.

**Décision**
`upcoming_weekend.WeekendEntry(championship_id, event)` — le contrôleur, qui connaît déjà
l'id du registre au moment de l'appel (`for cid in WEEKEND_CHAMPIONSHIP_IDS: ...
await provider.fetch_events(cid, year)`), l'attache explicitement à chaque événement
récupéré. Toute la logique de recherche/regroupement/affichage de `upcoming_weekend.py`
lit `entry.championship_id`, jamais `entry.event.championship.id`.

**Conséquences**
- Aucune modification aux providers ni aux modèles métier — la correction reste
  entièrement côté GUI, conforme à la contrainte du sprint.
- `test_championship_id_comes_from_the_entry_not_the_event` (`test_gui_upcoming_weekend.py`)
  verrouille explicitement la régression : construit un événement dont l'id diffère
  volontairement de l'id de registre, vérifie que la carte utilise bien ce dernier.
- Règle pour les futures fonctionnalités GUI qui agrègent plusieurs championnats : ne
  jamais supposer que `Event.championship.id` égale l'id du registre — le transporter
  explicitement depuis l'appelant, comme `WeekendEntry`.
- Effet de bord découvert au passage : `ProvidersConfig.formula1` défaut sur la source
  `"openf1"` (pas `"jolpica"`, pourtant enregistrée en premier) — déjà le comportement de
  `generate_calendar`, simplement jamais remarqué faute de test F1 dans
  `test_gui_controller.py` avant ce sprint.

---

## ADR-019 — Grille de page unique (`theme.page_shell`) pour toutes les vues GUI

**Contexte**
Sprint 27. Après validation visuelle du Design System (Sprint 26), incohérence constatée :
Ce week-end / Mes favoris / À propos centraient tout leur contenu au milieu de l'écran,
tandis que Mon calendrier / Préférences étaient alignés à gauche. Chaque vue construisait
son propre `Container(padding=..., alignment=...)` — rien n'empêchait la dérive.

**Décision**
Une seule fonction, `theme.page_shell(*sections)`, rend toutes les vues. Elle centre
*uniquement* un conteneur à largeur plafonnée (`MAX_CONTENT_WIDTH = 1000`, dans la
fourchette 900–1100 px demandée) horizontalement dans la fenêtre ; à l'intérieur, une
`Column` unique en `horizontal_alignment=STRETCH` fait remplir la largeur du gabarit à
toute carte/formulaire sans jamais centrer le contenu lui-même. Les 5 vues (`weekend.py`,
`calendar.py`, `favorites.py`, `preferences.py`, `about.py`) appellent cette fonction avec
la liste de leurs sections (`section_title` + `Divider` + contenu propre à la page) au lieu
de construire leur propre conteneur racine.

**Conséquences**
- Un futur changement de largeur max, de padding ou d'alignement se fait à un seul endroit ;
  aucune vue ne peut plus dériver silencieusement vers un layout différent.
- `TestAllViewsShareTheSameGrid` (`tests/test_gui_views.py`) construit les 5 vues et vérifie
  qu'elles partagent strictement la même largeur, le même centrage externe, le même
  alignement interne et le même padding — verrou anti-régression direct sur l'exigence
  "même gabarit partout".
- Le rétrécissement responsive sur fenêtre étroite ne nécessite aucun recalcul manuel :
  `ft.Container(width=MAX_CONTENT_WIDTH)` sous un parent `alignment=TOP_CENTER` est
  automatiquement bridé par les contraintes du parent quand l'espace disponible est
  inférieur à 1000 px (comportement standard `BoxConstraints.enforce` de Flutter).
- Mon calendrier perd son en-tête custom (logo + nom de l'app) au profit du même
  `section_title` que les autres pages, pour une uniformité réelle des titres — le
  placeholder logo (ADR-018) reste sur la page À propos.
- Aucun changement à `GenerateState`, `CalendarViewControls` ou aux handlers de
  `main_view.py` : uniquement le conteneur racine retourné par chaque `build_*_view()`.

---

## ADR-018 — Design system `gui/theme.py` + assistant par étapes pour "Mon calendrier"

**Contexte**
Sprint 26 — Release Alpha Phase 2. Le brief produit interdit toute couleur codée en dur
dans les vues et demande de transformer "Mon calendrier" en parcours guidé, sans toucher
au moteur ni aux pages Ce week-end / Mes favoris / Préférences au-delà de leur habillage
visuel. Le Brand Set Motorsport Calendar v1.0 est validé (voir `BApps-Studio/03-Products/
Motorsport-Calendar/Branding/Branding.md`) mais ses SVG définitifs ne sont pas encore
livrés dans ce dépôt.

**Décision**
1. Un seul module, `motorsport_calendar/gui/theme.py`, porte toutes les couleurs
   (`BAppsColors`, `MotorsportColors`, puis `Colors` en rôles sémantiques), les échelles
   d'espacement/rayon/icône/typo, et les constructeurs de composants partagés
   (`card()`, `chip()`, `button_style()`, `page_padding()`, `section_title()`,
   `logo_placeholder()`). Toute vue qui a besoin d'une couleur ou d'une taille importe
   ces tokens — jamais `ft.Colors.*` ni un entier brut directement.
2. "Mon calendrier" (`gui/views/calendar.py`) devient un assistant à 4 étapes (saison →
   championnats → destination → créer) au lieu d'un formulaire long. La navigation avant
   est gatée par la validité de l'étape courante (`GenerateState.can_advance()`) ; le
   retour et le clic sur une puce d'étape déjà visitée sont toujours autorisés.
3. `logo_placeholder()` matérialise l'emplacement du futur logo (nav/À propos/en-tête du
   wizard) sans qu'aucun SVG définitif soit copié dans le dépôt — voir
   `gui/assets/logo/README.md`.

**Conséquences**
- Un changement de palette de marque ne touche plus qu'un seul fichier.
- `GenerateState` gagne `current_step`/`step_valid`/`can_advance`/`can_go_back` — logique
  de wizard 100 % testable sans Flet, comme le reste de `models.py`.
- `calendar.py` reste un module de layout pur : `main_view.py` continue de porter tout
  l'état et les handlers, conformément à la règle établie au Sprint 25.
- Effet de bord positif : centraliser les couleurs a fait apparaître (et corrigé en un
  seul endroit) l'usage de noms `ft.Colors.WHITE12/30/38/54/60/70` dépréciés depuis
  Flet 0.85 — remplacés par `WHITE_12/30/38/54/60/70`.
- Le remplacement du vrai logo, quand les SVG seront livrés, se limite à modifier
  `logo_placeholder()`'s call sites listés dans `gui/assets/logo/README.md` — aucun
  rework de layout attendu.

---

## ADR-001 — Pydantic v2 avec `frozen=True` pour tous les modèles

**Contexte**
Les modèles de calendrier (Event, Session, Circuit…) sont produits par des providers et consommés par des exporteurs. Ils ne doivent jamais être mutés après création.

**Décision**
Tous les modèles héritent de `pydantic.BaseModel` avec `model_config = ConfigDict(frozen=True)`.
Les collections utilisent `tuple[T, ...]` et non `list[T]` : `frozen=True` interdit la réassignation du champ mais pas la mutation d'une liste.

**Conséquences**
- Les modèles sont hashables et thread-safe.
- La validation Pydantic garantit les invariants à la construction.
- Les tests peuvent comparer des modèles par valeur (`==`).

---

## ADR-002 — Architecture Provider / Source par injection de dépendance

**Contexte**
Plusieurs sources de données F1 existent (OpenF1, Ergast, site officiel). Le provider ne doit pas être couplé à une source spécifique.

**Décision**
`Formula1Provider` reçoit une `Formula1Source` (ABC) au constructeur.
La source effectue tous les appels réseau et le parsing ; le provider ne fait que déléguer.

**Conséquences**
- On peut changer de source sans toucher au provider.
- Les sources sont testables indépendamment.
- L'ajout d'un `CachedFormula1Source` (décorateur) ne nécessite pas de modifier le provider.

---

## ADR-003 — `httpx` pour tous les appels HTTP asynchrones

**Contexte**
Les sources doivent appeler des API REST de manière asynchrone et être testables sans réseau.

**Décision**
Utiliser `httpx.AsyncClient` injecté optionnellement au constructeur de chaque Source.
En production, la Source crée son propre client avec les bons timeouts.
En test, un mock est injecté directement.

**Conséquences**
- Zéro appel réseau en CI.
- Timeout configuré à 10 secondes (constante `_TIMEOUT` dans chaque source).
- `httpx.HTTPStatusError` et `httpx.TimeoutException` sont les seules exceptions HTTP propagées.

---

## ADR-004 — `icalendar` pour la génération ICS (RFC 5545)

**Contexte**
Le format de sortie principal est `.ics` (iCalendar). Il faut respecter strictement RFC 5545 pour la compatibilité Google Calendar / Apple Calendar / Outlook.

**Décision**
Utiliser la bibliothèque `icalendar` (≥ 5.0). Un VEVENT est généré par Session (et non par Event/weekend).

**Conséquences**
- Compatibilité maximale avec les clients calendrier.
- `METHOD:PUBLISH` est ajouté pour indiquer un flux en lecture seule.
- Les datetimes timezone-aware sont sérialisés correctement par la lib.

---

## ADR-005 — `asyncio.run()` comme pont sync→async dans la CLI

**Contexte**
La CLI Typer est synchrone. Les providers sont async. Il faut un pont.

**Décision**
Chaque commande CLI crée une coroutine interne `_fetch()` et l'exécute avec `asyncio.run()`.
Pas de framework async au niveau CLI (pas de `anyio`, pas de `click-asyncio`).

**Conséquences**
- La CLI reste simple et sans dépendances supplémentaires.
- `asyncio.run()` crée un nouveau loop à chaque appel de commande — acceptable pour un outil CLI.
- Les tests CLI utilisent `CliRunner` (synchrone) sans conflit de loop.

---

## ADR-006 — `unittest.mock` uniquement pour les mocks HTTP

**Contexte**
Des bibliothèques comme `respx` ou `pytest-httpx` facilitent le mock HTTP mais ajoutent des dépendances.

**Décision**
Utiliser uniquement `unittest.mock.AsyncMock` + `MagicMock`. Le client httpx est soit injecté directement (tests OpenF1Source), soit patché via `patch.object` sur `_get_json` (tests CLI).

**Conséquences**
- Zéro dépendance de test supplémentaire.
- Les mocks sont explicites et lisibles.
- Le pattern est cohérent dans tout le projet.

---

## ADR-007 — Timezone via mapping `circuit_short_name` → IANA

**Contexte**
L'API OpenF1 retourne des datetimes en UTC + un champ `gmt_offset` (string, ex: "+03:00"). Elle ne fournit pas de nom de timezone IANA.

**Décision**
Maintenir un dictionnaire statique `_CIRCUIT_TZ_MAP` dans `openf1.py` : 25 circuits → timezone IANA. Fallback : `"UTC"`. Les sessions sont converties dans le fuseau local du circuit.

**Conséquences**
- Les VEVENTs ICS affichent les horaires locaux (meilleure UX).
- Le dict doit être maintenu manuellement quand un nouveau circuit apparaît.
- Fallback UTC évite un crash sur un circuit inconnu.

---

## ADR-008 — Cache HTTP centralisé indépendant de httpx

**Contexte**
Sans cache, chaque exécution de `motocal generate-f1` effectue 2 appels HTTP à OpenF1. Les futurs providers (Ergast, MotoGP…) auraient le même problème. Un cache ad hoc dans chaque provider violerait le principe DRY.

**Décision**
Créer `motorsport_calendar/cache/HttpCache` : cache disque JSON avec TTL.
L'API reçoit une coroutine `fetch` (pas d'httpx.AsyncClient) pour rester indépendant de la bibliothèque HTTP.
`OpenF1Source` active le cache uniquement si aucun client custom n'est injecté (heuristique "client injecté = mode test").
Option `--refresh` en CLI propage `refresh=True` jusqu'au cache.

**Conséquences**
- Tous les futurs providers utilisent `HttpCache` sans code supplémentaire.
- Les tests existants (`OpenF1Source(client=mock)`) ne nécessitent aucune modification.
- Le cache est dans `.cache/` (CWD) — simple mais pas idéal pour un outil installé globalement (dette technique documentée).
- `invalidate()` et `clear()` disponibles pour les cas avancés.

---

## ADR-009 — `ConfigService` + Pydantic pour la configuration centrale

**Contexte**
Plusieurs valeurs étaient codées en dur : chemin du cache (`.cache/`), TTL (86400s), alarm ICS, source F1. Avec l'ajout de WEC et des futures disciplines, la configuration doit être externalisée.

**Décision**
Créer `motorsport_calendar/config/` avec :
- Modèles Pydantic v2 `frozen=True` pour chaque section (`CacheConfig`, `IcsConfig`, `ProviderConfig`, `ProvidersConfig`, `AppConfig`)
- `ConfigService` qui lit `config.yaml` (CWD → `~/.config/…` → défauts)
- `config.yaml` dans `.gitignore`, `config.example.yaml` commité comme référence
- Dépendance : `pyyaml>=6.0`

**Conséquences**
- Plus aucun chemin ou TTL codé en dur dans les providers ou la CLI
- La sélection de source F1/WEC est pilotée par `providers.formula1.source` dans le YAML
- Pydantic valide la configuration au démarrage — erreur claire si malformée
- Le VALARM ICS est configurable via `ics.alarm_minutes` (0 = désactivé)
- Les tests passent un `config_path` explicite pour l'isolation

---

## ADR-012 — SourceRegistry : inversion de responsabilité source → registre

**Contexte**
Après le Sprint 9, la factory du provider connaissait ses sources (`if source == "openf1": ...`). Chaque nouvelle source (Ergast, Jolpica, Official) aurait ajouté un `elif`. Violation du principe ouvert/fermé.

**Décision**
Créer `motorsport_calendar/core/source_registry.py` avec un `SourceRegistry` singleton, symétrique au `ProviderRegistry`.
Chaque `providers/X/sources/__init__.py` enregistre ses sources :
```python
source_registry.register("formula1", "openf1", lambda cache, refresh: OpenF1Source(...))
```
La factory provider devient triviale : `_make_provider(source) → Formula1Provider(source)`.
La CLI orchestre : `source = source_registry.get("formula1", "openf1")(cache, refresh)`.

**Conséquences**
- Ajouter une source F1 (Ergast, Jolpica…) = une ligne dans `formula1/sources/__init__.py`. Zéro autre modification.
- La factory provider ne connaît aucune source concrète.
- `source_registry.discover()` importe `providers/X/sources/` de chaque championnat.
- 24 tests unitaires + d'intégration couvrent le registre.

**Note** : cette ADR marque la fin des refactorings structurels. L'architecture Provider/Source/Registry est désormais figée. Les prochains sprints ajoutent des fonctionnalités.

---

## ADR-011 — ProviderRegistry : auto-enregistrement par import

**Contexte**
Avec F1 et WEC coexistant, la CLI commençait à contenir `if source == "openf1": ...` et devrait grossir à chaque nouveau championnat. Il faut découpler la CLI de la connaissance des providers.

**Décision**
Créer `motorsport_calendar/core/registry.py` avec un `ProviderRegistry` singleton.
Chaque `providers/X/__init__.py` s'enregistre automatiquement à l'import :
```python
registry.register("formula1", _make_provider)
```
La CLI appelle `registry.discover()` (qui importe tous les sous-paquets via `pkgutil.iter_modules`), puis `registry.get("formula1")` pour obtenir une factory.
Pour ajouter un championnat : créer `providers/elms/` avec son `__init__.py` — zéro autre modification.

**Conséquences**
- La CLI ne connaît aucun provider individuellement.
- `registry.enabled(config.providers)` filtre selon `enabled: bool` dans le YAML (logique opt-out : absent = activé).
- `ProviderConfig` gagne `enabled: bool = True` et `source: str = ""` (optionnel).
- `ProvidersConfig` gagne `extra="allow"` + méthode `get(championship_id)` pour les providers hors champs nommés.
- 25 tests unitaires + d'intégration couvrent le registre à 100 %.

---

## ADR-013 — Data Acquisition Layer : interfaces abstraites dans `core/datasource/`

**Contexte**
Les sources de données (`OpenF1Source`, `JolpicaSource`, futurs scrapers WEC/ELMS) mélangent
deux responsabilités distinctes : acquisition réseau brute (HTTP, HTML, ICS) et mapping vers
les modèles métier. À mesure que le nombre de sources grandit, ce couplage ralentit les tests
et rend l'ajout de nouvelles sources moins prévisible.

**Décision**
Créer `motorsport_calendar/core/datasource/` avec quatre classes abstraites :
- `DataSource(ABC)` — marqueur commun
- `JsonDataSource(DataSource)` — `@abstractmethod fetch_json(url, params) → list | dict`
- `HtmlDataSource(DataSource)` — `@abstractmethod fetch_html(url) → str`
- `IcsDataSource(DataSource)` — `@abstractmethod fetch_ics(url) → str`

Chaque source implémente l'interface de sa catégorie **en plus** de l'interface domaine
existante (`Formula1Source`, `WecSource`…). Aucun provider ni modèle ne change.

`OpenF1Source` migre vers `JsonDataSource` comme validation du concept :
`fetch_json` est l'implémentation réelle (HTTP + cache) ; `_get_json` reste comme wrapper
pour la rétrocompatibilité avec les mocks CLI existants.

**Conséquences**
- Chaque nouvelle source sait quelle interface de transport implémenter avant même de coder.
- Le DAL est testable indépendamment des modèles et providers.
- Les mocks CLI (`patch.object(OpenF1Source, "_get_json", ...)`) restent valides sans modification.
- `JolpicaSource`, `OfficialWecSource` etc. migrent vers leur interface DAL au moment de leur implémentation.
- 374 tests, 0 régression, couverture 93 %.

---

## ADR-015 — Support Series Framework : extraction de la base commune avant les sprints F3/Academy/Supercup

**Contexte**
F2 est implémentée. F3, F1 Academy, et Porsche Supercup utilisent le même dataset f1calendar
avec la même structure JSON. Si chaque provider répète le code HTTP/cache/mapping, un fix ou
une amélioration devra être répliquée N fois.

**Décision**
Extraire `F1CalendarBaseSource` dans `providers/support_series/f1calendar_base.py` AVANT
d'implémenter F3/Academy/Supercup. `F1CalendarSource` (F2) est refactorisée pour en hériter.

Les 4 propriétés abstraites de la base : `_series_key`, `_session_map`, `_circuit_data`,
`_make_championship(year)`. Tout le reste est fourni par la base.

Les fonctions module-level de `f1calendar.py` (F2-spécifiques) sont conservées pour les tests
existants — elles ne sont plus utilisées en production mais restent comme unités testables
de la config F2.

**MRO** : `F1CalendarSource(F1CalendarBaseSource, Formula2Source)` — base class en premier pour
que `get_season` et `fetch_json` de la base priment sur les méthodes abstraites de `Formula2Source`.

**Conséquences**
- F3/Academy/Supercup : ~15 lignes de code chacun (4 overrides, rien d'autre).
- Zéro changement de comportement pour F2.
- 484 tests, 0 régression, couverture 94 %.

---

## ADR-014 — Formula 2 : source f1calendar.com JSON (MIT) plutôt que scraping HTML

**Contexte**
Plusieurs sources sont envisageables pour le calendrier F2 (voir `DATA_SOURCES.md`) :
scraping HTML de `fiaformula2.com`, scraping de `formula2.com`, ou le dataset JSON MIT
maintenu par `sportstimes` sur GitHub (`github.com/sportstimes/f1`).

**Décision**
Utiliser `https://raw.githubusercontent.com/sportstimes/f1/main/_db/f2/{year}.json`
(dataset MIT, mis à jour manuellement, stable) comme source primaire via `F1CalendarSource`,
qui implémente `JsonDataSource`.

Raisons du choix :
- Format JSON structuré → implémente directement `JsonDataSource`, pas de parsing HTML fragile
- Licence MIT → utilisation libre, sans restriction
- Un seul GET par saison → compatible avec `HttpCache` sans changement
- Aucun scraping JavaScript ou authentification requise
- Réutilise exactement le même pattern d'injection de dépendance que `OpenF1Source`

**Conséquences**
- La source dépend d'un dépôt tiers maintenu bénévolement ; si le dépôt disparaît, un fallback
  vers `fiaformula2.com` (HTML) devra être implémenté comme source alternative.
- Les timestamps sont en UTC, les end-times sont inférés (même approche que `JolpicaSource`).
- `F1CalendarSource` n'a pas de wrapper `_get_json` (pas de legacy mocks à maintenir).
- 448 tests, 0 régression, couverture 93 %.

**Mise à jour 2026-07-06 (Sprint 21.2)** :
Audit Sprint 21.1 révèle un renommage de clés dans le dataset à partir de 2025 :
- `"fp1"` → `"practice"`
- `"sprintRace"` → `"sprint"`

F3 utilisait déjà `"practice"` et `"sprint"` depuis 2022 — le dataset a donc aligné F2 sur F3.
Conséquence : les calendriers F2 2025+ n'exportaient que 2 sessions sur 4 (qualifying + feature).

Correction : `_SESSION_MAP` inclut désormais les deux formes pour chaque clé renommée.
Les deux anciennes clés (`fp1`, `sprintRace`) sont conservées pour la rétrocompatibilité des
saisons 2024 et antérieures. Si un event contient à la fois `fp1` et `practice` (impossible
en pratique), les deux seraient exportés — un UID collision ICS en résulterait, mais cela
ne se produit pas dans le dataset réel.

---

## ADR-016 — F1 Academy : mapping SessionType contraint par l'absence de RACE2/RACE3

**Contexte**
F1 Academy court un format à trois courses par week-end (`race1`, `race2`, `race3`) depuis 2023.
Le format est le suivant :
- `fp1` / `fp2` : deux séances d'entraînement
- `qualifying1` (et `qualifying2` en 2023-2024) : qualifications
- `race1` / `race2` : courses sprint (~30 min chacune)
- `race3` : course principale (~30 min)

Le problème : `SessionType` ne possède pas de valeurs `RACE2` / `RACE3`. Si `race1`, `race2`
et `race3` sont tous mappés à `SessionType.RACE`, l'ICS généré contiendra trois VEVENTs
avec le même UID (`event_uid-RACE`) — ce qui viole RFC 5545 et provoque des collisions
dans les clients calendrier (un seul event visible sur trois).

**Décision**
Contrainte du sprint : "Aucun changement des modèles métier" → on ne peut pas ajouter
`RACE2`/`RACE3` à l'enum `SessionType`.

Mapping retenu pour garantir l'unicité des UIDs :
- `race1` → `SessionType.SPRINT`   "Race 1"  (sprint = course courte ✓)
- `race2` → `SessionType.FP3`      "Race 2"  (workaround — FP3 = type disponible non utilisé ailleurs)
- `race3` → `SessionType.RACE`     "Race 3"  (course principale ✓)

Le champ `title` affiché dans le calendrier est correct ("Race 1", "Race 2", "Race 3").
Le `type` FP3 n'est visible qu'en interne (logs, filtrage programmatique).

**Conséquences**
- Aucun UID en collision — calendrier RFC 5545 valide. ✓
- Les titres des sessions sont corrects pour l'utilisateur final. ✓
- Le type FP3 pour "Race 2" est sémantiquement incorrect — confusant pour les développeurs
  qui filtrent par `session.type == SessionType.FP3`.
- **Recommandation pour une prochaine version** : ajouter `RACE2 = "RACE2"` et
  `RACE3 = "RACE3"` à `SessionType` (changement purement additif, zéro régression),
  puis mettre à jour ce mapping.

---

## ADR-015 — Formula 3 : source f1calendar.com JSON, clés de sessions différentes de F2

**Contexte**
Le dataset `sportstimes/f1` couvre aussi F3 avec le même pattern d'URL
(`_db/f3/{year}.json`) et la même licence MIT. La question était de savoir si
les clés de sessions F3 sont identiques à celles de F2.

**Décision**
Utiliser `https://raw.githubusercontent.com/sportstimes/f1/main/_db/f3/{year}.json`
comme source primaire via `F1CalendarSource(F1CalendarBaseSource, Formula3Source)`.

Les clés de sessions F3 confirmées (2022-2025) différent de F2 sur deux points :
- `"practice"` (F3) au lieu de `"fp1"` (F2) → `SessionType.FP1`, 45 min
- `"sprint"` (F3) au lieu de `"sprintRace"` (F2) → `SessionType.SPRINT`, 30 min
- `"qualifying"` identique → `SessionType.QUALIFYING`, 30 min
- `"feature"` identique → `SessionType.RACE`, 40 min (vs 65 min pour F2)

Les saisons antérieures à 2022 utilisaient `"race1"/"race2"/"race3"` — ces sessions
ne sont pas mappées et sont silencieusement ignorées.

F3 ne couvre que les circuits F1 européens + Bahreïn + Melbourne (13 slugs connus).

**Conséquences**
- `F3CalendarSource` : uniquement `_series_key`, `_session_map`, `_circuit_data`,
  `_make_championship` — 4 overrides, ~50 lignes en tout (dont 13 entrées circuit).
- Aucune fonction module-level de backward-compat (F3 n'a pas de tests hérités qui
  importent directement ces helpers).
- Mutualisation : ~85 % de la logique héritée de `F1CalendarBaseSource`.

---

## ADR-017 — Dataset `sportstimes/f1` : clé `"races"`, pas `"events"`

**Contexte**
Sprint QA-03 — audit de l'environnement réel (`python -m motorsport_calendar generate 2026`).
F2, F3 et F1 Academy retournaient systématiquement 0 événements depuis l'introduction du
Support Series Framework (Sprint 14). La commande `generate 2026` produisait 26 événements
F1 mais 0 pour chaque série support.

**Cause racine**
`F1CalendarBaseSource._get_season()` lisait `raw.get("events", [])`. Mais le dataset
`sportstimes/f1` sur GitHub (source officielle, MIT) utilise `"races"` comme clé de premier
niveau — pas `"events"`. Le payload réel ressemble à :
```json
{ "races": [ { "name": "...", "sessions": {...} } ] }
```
Les tests unitaires et d'intégration utilisaient eux-mêmes la clé `"events"` dans leurs
fixtures (copié/collé du code incorrect), masquant le bug pendant tout le développement.

**Décision**
1. `f1calendar_base.py` ligne 111 : `raw.get("events", [])` → `raw.get("races", [])`.
2. Toutes les fixtures de test (`test_f1calendar_base.py`, `test_f1calendar_source.py`,
   `test_cli_generate_f2.py`, `test_cli_generate_f3.py`, `test_cli_generate_f1_academy.py`)
   corrigées (`"events"` → `"races"`).
3. Ajout de `tests/fixtures/real/` : extraits minimaux (2 événements) tirés directement
   du dataset réel GitHub (F2, F3, F1 Academy — saison 2025). Ces fixtures sont la
   référence de vérité : si le dataset change de structure, les tests `test_real_fixtures.py`
   le détectent immédiatement.
4. `TestRacesKeyRegression` dans `test_f1calendar_base.py` : 3 tests qui documentent et
   protègent ce comportement (`"races"` lu, `"events"` ignoré, les deux présents → seul
   `"races"` est lu).

**Règle pour les futurs tests**
Toute fixture mock renvoyée par `fetch_json` doit utiliser `{"races": [...]}`.
Ne jamais utiliser `{"events": [...]}` — c'est silencieusement ignoré.

**Conséquences**
- F2/F3/F1 Academy retournent maintenant les données réelles en production. ✓
- 627 tests passent (16 nouveaux).
- `tests/fixtures/real/` : référence vivante du format dataset — à mettre à jour si la
  structure du dataset `sportstimes/f1` change.
- **Comment éviter que cela se reproduise** : les nouveaux providers support series
  doivent ajouter une fixture dans `tests/fixtures/real/` et un test `test_real_fixtures.py`
  AVANT d'écrire la moindre fixture mock. Vérifier le dataset réel en premier.

---

## ADR-010 — VALARM dans IcsExporter via `alarm_minutes`

**Contexte**
Les utilisateurs souhaitent des rappels calendrier avant chaque session motorsport.

**Décision**
`IcsExporter(alarm_minutes=N)` — si N>0, chaque VEVENT contient un composant VALARM `ACTION:DISPLAY` avec `TRIGGER:-PTNm`. Valeur lue depuis `config.ics.alarm_minutes`.

**Conséquences**
- Compatible RFC 5545 — fonctionne dans Google Calendar, Apple Calendar, Outlook
- Rétrocompatible : `IcsExporter()` sans argument = `alarm_minutes=0` = aucun VALARM
- Les tests existants (`IcsExporter()`) ne nécessitent aucune modification
