# JOURNAL.md

---

## Session 2026-07-14 — Sprint RC-01 : Validation Windows

### Objectif
Premier sprint de la phase Release Candidate : développement fonctionnel
gelé, objectif unique — valider le packaging Windows sur une vraie
machine Windows 11 (le correctif Sprint 59 n'avait jamais été exécuté
sur Windows faute de machine disponible). Aucune nouvelle fonctionnalité,
aucun refactoring non indispensable ; toute modification devait être
directement liée au packaging ou à un bug empêchant la publication.

### Prérequis machine — aucun présent au départ
Aucun composant nécessaire n'était installé sur cette machine :
- **Visual Studio Build Tools 2022** (workload "Desktop development with
  C++") — installé via winget (`--override "--quiet --wait --add
  Microsoft.VisualStudio.Workload.VCTools --includeRecommended"`).
- **Windows Developer Mode** — désactivé par défaut ; activé par
  l'utilisateur (nécessite les droits Administrateur, hors de portée
  d'un shell non élevé).
- **Environnement Python** — aucun `.venv` existant ; créé et peuplé via
  `pip install -e ".[gui,dev]"` (Python 3.14, flet 0.85.3).

### Premier échec — crash immédiat, avant toute compilation
`flet build windows motorsport_calendar/gui --module-name app --yes`
plantait instantanément avec `UnicodeEncodeError: 'charmap' codec can't
encode character '●'` — le rendu console `rich` (dépendance de
`flet_cli`) tentait d'afficher un caractère Unicode sur un terminal en
page de code `cp1252`/`850`, pas UTF-8. **Correctif** :
`PYTHONUTF8=1`/`PYTHONIOENCODING=utf-8` avant d'invoquer `flet build` —
purement environnemental, aucun code du projet modifié.

### Deuxième échec — CMake install, `vcruntime140_1.dll` introuvable
La compilation native a réussi (`Building Windows application... 91,6s`)
mais l'étape d'installation CMake échouait avec `file INSTALL cannot
find "C:/WINDOWS/System32/vcruntime140_1.dll"`. MSBuild n'affichait que
le bruit générique `MSB3073` (écho du batch wrapper), pas la vraie
erreur — trouvée en relançant directement `cmake -DBUILD_TYPE=Release -P
cmake_install.cmake`. **Cause racine** (confirmée, pas supposée) : le
`cmake.exe` fourni avec Visual Studio Build Tools est un binaire **32
bits** (`file cmake.exe` → `PE32 ... Intel i386`). Étant 32 bits, son
accès à `C:\WINDOWS\System32\` est transparent redirigé par WOW64 vers
`C:\WINDOWS\SysWOW64\` — où `vcruntime140_1.dll` ne peut, par
construction, jamais exister : cette DLL est strictement réservée à x64
(optimisation `/d2FH4`), aucune version 32 bits n'est jamais produite
par aucun installeur Microsoft. Installer le VC++ Redistributable x64
**et** x86 via winget était nécessaire mais **insuffisant** — le paquet
x86 ne fournit jamais ce fichier spécifique, par design.
**Correctif** (contournement documenté par la communauté Flutter/Windows
pour ce problème connu, confirmé fonctionnel ici) : copier
`C:\WINDOWS\System32\vcruntime140_1.dll` vers
`C:\WINDOWS\SysWOW64\vcruntime140_1.dll` (droits Administrateur requis
— fait par l'utilisateur) — un ajout pur, aucun fichier écrasé,
facilement réversible. Le contenu copié dans le bundle final de l'app
reste le vrai binaire x64 correct ; seule la *lecture source*
redirigée par WOW64 est satisfaite par cette copie.

### Résultat — build réussi, vérifié pour de vrai
`flet build windows motorsport_calendar/gui --module-name app --yes` →
`Successfully built your Windows app!`. `motorsport-calendar.exe` (314
Ko), bundle complet 105 Mo, `site-packages/motorsport_calendar/`
correctement imbriqué (même structure que le build Linux du Sprint 59),
version 0.2.0 confirmée.

**Lancement réel et confirmation visuelle — une première pour ce
projet** (chaque sprint GUI précédent notait l'absence de compositeur
d'affichage). Processus lancé, répond, titre de fenêtre natif `"gui"` au
premier rendu (défaut compilé attendu) puis `"Motorsport Calendar"` une
fois le démarrage Python terminé. Aucune trace dans
`console.log` à aucun moment. **Les 8 pages parcourues avec captures
d'écran réelles** (Tableau de bord, Ce week-end, Mon calendrier,
Recherche, Mes favoris, Préférences, À propos, Soutenir le projet) —
données réelles correctement affichées partout (Tableau de bord : 17
championnats, 180 événements, 865 sessions ; Mon calendrier : arbre de
catégories avec compteurs live ; Recherche : 108 résultats live). Aucun
crash, aucun widget cassé, aucun problème de thème. Fermeture propre via
le bouton de fermeture natif, processus terminé de lui-même.

**Un bug cosmétique pré-existant trouvé pendant ce contrôle visuel** : le
dropdown "Année par défaut" (page Préférences) tronque son texte
("Année en co" au lieu de "Année en cours") — non bloquant, ajouté à
`docs/TODO.md`.

### Suite de tests — deux bugs de test réels trouvés en tournant sur Windows pour la première fois
`pytest` (2042 tests) a d'abord signalé 3 échecs, tous dans des
suppositions de test jamais vérifiées en conditions Windows réelles, pas
dans le code applicatif :
- `test_default_cache_path_contains_cache_dir` — supposait `.cache` dans
  le chemin, alors que la convention Windows documentée
  (`utils/paths.py`) est `%LOCALAPPDATA%\motorsport-calendar`, sans
  segment `.cache`. Corrigé en rendant l'assertion spécifique à la
  plateforme.
- `test_falls_back_to_home_appdata_roaming_when_appdata_unset` et son
  équivalent cache — vidaient tout l'environnement (`clear=True`), ce
  qui neutralise aussi `USERPROFILE`. Ça fonctionnait par coïncidence
  sous Linux (`Path.home()` retombe sur la base `pwd`, indépendante de
  l'environnement) mais échoue légitimement sous Windows
  (`Path.home()` n'a aucun repli sans variable d'environnement). Corrigé
  en ne vidant que la variable pertinente (`APPDATA`/`LOCALAPPDATA`),
  comme le fait déjà le test équivalent Linux du même fichier.

Aucun code applicatif modifié — uniquement `tests/test_config_service.py`
et `tests/test_utils_paths.py`. Suite complète : **2042 passants, 0
skip** (le test auparavant marqué "Windows-only skip" tourne désormais
pour de vrai et passe). Ruff : 0 erreur. Mypy : 41 `motorsport_calendar/`
/ 176 `tests/` — identique à la dette déjà documentée, aucune régression.

### Documentation mise à jour
`docs/PACKAGING.md` (nouveau §8, compte-rendu complet du sprint),
`docs/RELEASE.md` (§3 et §8, retrait de la mention "non vérifié"),
`docs/ROADMAP.md` (item backlog Windows marqué fait), `docs/TODO.md`
(item Windows marqué fait, nouvel item dropdown tronqué), `README.md`
(tableau de statut : Windows packaging ✅).

### Fichiers modifiés
| Fichier | Action |
|---|---|
| `tests/test_config_service.py` | Assertion `.cache` rendue spécifique à la plateforme |
| `tests/test_utils_paths.py` | Fallback `Path.home()` : ne vide plus tout l'environnement |
| `docs/PACKAGING.md` | Nouveau §8 — validation Windows complète |
| `docs/RELEASE.md` | §3/§8 mis à jour — build Windows vérifié |
| `docs/ROADMAP.md` | Backlog — item Windows marqué fait |
| `docs/TODO.md` | Items Windows marqués faits, nouvel item dropdown |
| `README.md` | Tableau de statut — Windows packaging ✅ |

---

## Session 2026-07-14 — Sprint 59 : Correction du packaging Flet

### Objectif
Suite directe du Sprint 58 : le build Linux compile mais le binaire
plante au démarrage (`ModuleNotFoundError: No module named
'motorsport_calendar'`). Mission (formulée directement par
l'utilisateur, pas un brief de sprint numéroté, documentée avec la même
rigueur) : identifier la méthode officiellement recommandée par Flet,
corriger proprement l'organisation, ne créer aucun contournement
fragile, ne jamais casser le développement actuel. Résultat attendu,
verbatim : "Un utilisateur Ubuntu télécharge Motorsport Calendar. Il
double-clique. L'application démarre. Rien d'autre."

### Audit rapide (préalable)
- Tests : 2033 passants (1 skip Windows-only), 0 échouant — état de fin
  de session du Sprint 58, rien n'a changé entretemps.
- Dette Ruff : 0 erreur. Dette mypy : 41 `motorsport_calendar/` / 176
  `tests/` — identique à la fin du Sprint 58, aucun nouveau `ft.Button`
  ni signature de callback en jeu dans ce correctif (packaging pur).
- `git status --short` : dette héritée, aucun commit tenté.

### Recherche — la méthode officiellement recommandée par Flet
Lecture directe du code source installé de `flet_cli`
(`flet_cli/commands/build_base.py`, `flet_cli/utils/
project_dependencies.py`, `flet_cli/utils/pyproject_toml.py`), jamais
supposée depuis la documentation générale : `self.get_pyproject =
load_pyproject_toml(self.python_app_path)` — confirme le diagnostic du
Sprint 58 (aucune `pyproject.toml` au chemin ciblé = aucune dépendance
ni identité résolue). Recherche complémentaire de la mécanique exacte de
packaging (`serious_python:main package <path>` — le chemin passé est
zippé *tel quel*, son contenu directement, sans jamais l'envelopper dans
un dossier portant son propre nom) — cette découverte n'était pas
présente dans l'audit du Sprint 58, qui s'était arrêté au diagnostic
"dépendances manquantes".

### Première tentative — testée, insuffisante
Une `pyproject.toml` dans `motorsport_calendar/gui/` déclarant les 9
dépendances racine + `flet` a été écrite, puis **testée par un rebuild
réel** (jamais supposée suffisante depuis la seule lecture du code) :
`flet build linux motorsport_calendar/gui --module-name app`, puis
lancement du binaire. `site-packages/` contenait bien
pydantic/icalendar/typer/rich/tzdata/pyyaml/beautifulsoup4/lxml —
confirmé par listing direct. Le binaire a pourtant planté avec
**exactement la même erreur** `ModuleNotFoundError: No module named
'motorsport_calendar'`. Ce test raté, plutôt qu'un échec, a révélé la
vraie second cause : le paquet `motorsport_calendar` (avec `core/`/
`providers/`/`config/`/`cache/`/`exporters/`, l'enveloppe qui rend
`motorsport_calendar.gui.main_view` résoluble) n'était toujours nulle
part dans le build — seul le contenu aplati de `gui/` lui-même l'était.

### Correction retenue et appliquée
`motorsport_calendar/gui/pyproject.toml` (fichier final) déclare
uniquement `flet>=0.80` et `motorsport-calendar` (le projet lui-même),
plus :
```toml
[tool.flet.app]
module = "app"

[tool.flet.dev_packages]
motorsport-calendar = "../.."
```
`tool.flet.dev_packages` est le mécanisme que Flet fournit explicitement
pour "une dépendance développée localement, pas encore publiée"
(confirmé par lecture du code, pas deviné depuis le nom de la clé) — il
réécrit la dépendance en `motorsport-calendar @ file:///…/motorsport-
calendar` avant packaging, déclenchant un vrai build/install pip isolé
du projet **depuis sa racine réelle**, via la configuration hatchling
déjà existante (`packages = ["motorsport_calendar"]`, rien de nouveau à
maintenir). Installer le projet ainsi résout aussi ses propres
dépendances déclarées de façon transitive — aucune duplication de liste
entre le manifeste de build et le manifeste racine, contrairement à la
première tentative.

### Vérification — rebuild réel + lancement réel, deux fois
1. Rebuild complet exécuté (`flet build linux motorsport_calendar/gui
   --module-name app`), ~25 secondes — le scaffold Flutter déjà en
   cache à `motorsport_calendar/gui/build/flutter/` a pu être réutilisé
   (`python_app_path` jamais changé par ce correctif), évitant une
   régénération complète.
2. `site-packages/motorsport_calendar/` confirmé présent et correctement
   imbriqué (`__init__.py`, `core/`, `providers/`, `config/`, `cache/`,
   `exporters/`, `gui/`, `cli.py`, `models/`), version `0.2.0` (via
   `motorsport_calendar-0.2.0.dist-info`).
3. Binaire relancé deux fois séparément (`./motorsport-calendar`, le nom
   corrigé) — les deux fois, `~/.cache/motorsport-calendar/console.log`
   est resté **vide** (contre une trace systématique de
   `ModuleNotFoundError` avant ce correctif), et le processus est resté
   actif bien au-delà du point où l'ancien build plantait instantanément
   (confirmé par `ps` à la marque des 6 secondes, état "running").
4. Non vérifié : le rendu réel d'une fenêtre — aucun compositeur
   d'affichage disponible dans cet environnement pour une capture
   visuelle, même limitation que chaque sprint GUI précédent de ce
   projet. Le crash Python au démarrage — le bug concret demandé à
   corriger — est en revanche définitivement résolu et vérifié.

Effet de bord positif, sans coût supplémentaire (même manifeste) :
l'identité générique de l'application (exécutable `gui`, ID
`com.flet.gui`, titre de fenêtre natif `"gui"`) devient
`motorsport-calendar`/`com.flet.motorsport-calendar`/
`"motorsport-calendar"` — lue depuis le même `project.name` que le
correctif principal.

Point non résolu, documenté honnêtement : la version embarquée dans le
build (`data/flutter_assets/version.json`) affiche toujours `1.0.0` au
lieu de `0.2.0`, malgré `project.version = "0.2.0"` dans le manifeste —
`flet_cli` lit bien cette valeur et la transmet via `--build-name`, mais
ce fichier précis ne semble pas en dépendre ; cosmétique, n'affecte ni
le démarrage ni le comportement, non retracé plus loin faute de temps
utile pour ce correctif.

### Vérification — aucune casse du développement actuel
`motorsport_calendar/gui/pyproject.toml` est un manifeste de build
**uniquement**, jamais lu par pip/hatchling pour l'installation normale
du projet. Vérifié explicitement après le correctif :
`motorsport_calendar.gui.app`/`motorsport_calendar.cli` s'importent
toujours normalement depuis le virtualenv de développement. `git diff
pyproject.toml` (racine) a montré un diff — vérifié qu'il s'agit d'une
dérive historique préexistante (beautifulsoup4/lxml/types-PyYAML/
types-icalendar), jamais introduite par ce correctif : aucun outil
d'édition n'a touché ce fichier durant cette session.

### Tests

`tests/test_packaging.py::TestFletBuildManifest` (8 tests, réécrite une
fois après la découverte que la première approche — dupliquer la liste
de dépendances — était insuffisante) : le manifeste de build déclare
`flet`, déclare le projet lui-même, ne redéclare **jamais** une
dépendance de la racine (garde-fou contre la réintroduction de la
duplication), `project.name`/`version` restent synchronisés avec la
racine, le module d'entrée déclaré existe réellement sur le disque, et
la redirection `tool.flet.dev_packages` pointe vers un vrai projet
installable (racine confirmée, `pyproject.toml` + paquet
`motorsport_calendar` tous deux présents).

### Fichiers modifiés / créés

| Fichier | Action |
|---|---|
| `motorsport_calendar/gui/pyproject.toml` | Créé — manifeste de build Flet dédié |
| `tests/test_packaging.py` | Modifié — `TestFletBuildManifest` (8 tests) |
| `docs/PACKAGING.md` | Modifié — §7 (nouveau, le correctif complet), encart de tête mis à jour |
| `docs/RELEASE.md` | Modifié — avertissement de blocage retiré, taille du build mise à jour |
| `CHANGELOG.md` | Mis à jour |
| `docs/ROADMAP.md` | Mis à jour — v0.4.33 |
| `docs/AI_CONTEXT.md` | Mis à jour — entrée #59, 3 lignes de dette (2 résolues, 1 nouvelle), 3 nouvelles pistes |
| `docs/TODO.md` | Mis à jour — 2 items cochés résolus |
| `docs/DECISIONS.md` | ADR-050 ajouté |

Aucun fichier source applicatif de `motorsport_calendar/` (hors le
nouveau manifeste de build, jamais exécuté par le code applicatif
lui-même) modifié. `pyproject.toml` racine non touché.

### Tests exécutés
```
2033 passed → 2041 passed, 1 skipped — 0 failed
```

Ruff : 0 erreur (inchangé). mypy `motorsport_calendar/`/`tests/` :
41/176, inchangés par ce correctif (le nouveau fichier est un TOML, non
vu par mypy ; les 8 nouveaux tests n'introduisent aucune erreur).

`git status --short` confirmé en fin de session : **aucun commit
effectué**, conforme à la contrainte explicite de la mission.

### Limites
- **Aucune confirmation visuelle réelle** d'une fenêtre rendue — pas de
  compositeur d'affichage dans cet environnement ; le crash Python est
  résolu et vérifié, le rendu final reste à confirmer sur un poste avec
  affichage avant toute distribution publique.
- **Le build Windows reste non vérifié** avec ce correctif — le même
  manifeste/mécanisme devrait s'appliquer identiquement (rien de
  spécifique à Linux), mais jamais exécuté sur une vraie machine
  Windows dans cet environnement.
- **La version embarquée dans le build reste incorrecte** (`1.0.0` au
  lieu de `0.2.0`) — cosmétique, documenté, non retracé jusqu'à sa
  cause exacte.

---

## Session 2026-07-14 — Sprint 58 : Validation Packaging Beta

### Objectif
Le build Linux (`flet build linux motorsport_calendar/gui --module-name
app`) venait de se compiler avec succès pour la première fois
("Successfully built your app for Linux!"). Objectif : un audit complet
du packaging — où Flet produit les livrables, si l'application compilée
est réellement autonome, l'identité de l'app (nom de fenêtre/icône/
chemins de config/cache/préférences), ce qui manque pour une vraie Beta
distribuable, et proposer l'arborescence idéale d'un dossier `Release/`
— puis écrire `docs/RELEASE.md`. Explicitement un audit/documentation,
aucune modification métier, uniquement packaging/release.

### Audit rapide (préalable)
- Tests : 2034 passants (1 skip Windows-only), 0 échouant — inchangé
  tout au long de la session, aucun fichier source applicatif modifié.
- Dette Ruff/mypy : inchangée (aucune modification de code).
- `git status --short` : dette héritée des sprints précédents, aucun
  commit tenté ce sprint non plus.

### Exploration — méthode : vérifier en lançant réellement le binaire
Cartographie du dossier de build par exploration directe
(`find`/`du`/`file`/`ldd`) plutôt que par lecture de la documentation
Flet : la sortie utile n'est pas `motorsport_calendar/gui/build/flutter/`
(le projet Flutter de travail, à ignorer) mais
`motorsport_calendar/gui/build/linux/` — une copie exacte de
`build/flutter/build/linux/x64/release/bundle/`, le dossier réellement
redistribuable. Inventaire : exécutable `gui` (24 Ko), `lib/` (88 Mo —
`libflutter_linux_gtk.so` 42 Mo, `libpython3.12.so.1.0` 31 Mo,
`libapp.so` 16 Mo statiquement lié, 6 plugins Flet natifs),
`python3.12/` (13 Mo, stdlib CPython compilée), `site-packages/`
(7,3 Mo), `data/` (3,9 Mo — `icudtl.dat` + `flutter_assets/`, dont
`app/app.zip` 315 Ko contenant le code Python applicatif). Total : 112
Mo.

**Découverte décisive** : plutôt que de s'arrêter à l'inspection
statique du dossier (qui semble complet — exécutable présent, assets
présents), le binaire a été réellement lancé (`timeout 10 ./gui`). Le
processus tourne plus de 10 secondes sans crash apparent en shell — mais
`~/.cache/com.flet.gui/console.log` (le fichier de log que le lanceur
Flet écrit lui-même, révélé par les variables d'environnement
`FLET_APP_CONSOLE`/`FLET_APP_STORAGE_*` visibles dans la sortie de
lancement) contient la vraie information : un traceback Python complet
se terminant par `ModuleNotFoundError: No module named
'motorsport_calendar'`. Sans cette étape (lancer le binaire pour de vrai
et consulter son log), ce constat serait resté invisible.

**Cause racine, établie par lecture du code source de `flet_cli`
installé** (`flet_cli/commands/build_base.py`,
`flet_cli/utils/project_dependencies.py`), jamais devinée : `self.
get_pyproject = load_pyproject_toml(self.python_app_path)` — Flet
cherche une `pyproject.toml` à l'intérieur du chemin passé en argument
(`motorsport_calendar/gui/`), jamais à la racine du projet où la vraie
`pyproject.toml` (9 dépendances déclarées : typer/rich/pydantic/
icalendar/httpx/tzdata/pyyaml/beautifulsoup4/lxml) existe déjà. Aucune
`pyproject.toml` n'existe dans `gui/`, donc : (1) `get_project_dependencies`/
`get_poetry_dependencies` ne trouvent rien à embarquer au-delà de Flet
et ses propres dépendances transitives (confirmé en listant
`site-packages/` du build : uniquement httpx/anyio/oauthlib/certifi/h11/
httpcore/idna/msgpack/repath/six/typing_extensions — aucune des 9
dépendances réelles, ni `motorsport_calendar` lui-même) ; (2) sans
`project.name`/`tool.flet.product`, Flet retombe sur le nom du dossier
pointé, `"gui"` — confirmé indépendamment à 3 endroits :
`flutter/linux/CMakeLists.txt` (`BINARY_NAME "gui"`,
`APPLICATION_ID "com.flet.gui"`), `my_application.cc`
(`gtk_window_set_title(window, "gui")`), et
`data/flutter_assets/version.json`
(`{"app_name":"gui","version":"1.0.0",...}` au lieu de `0.2.0`) — la
cohérence de ces 3 symptômes indépendants confirme le diagnostic plutôt
que de le supposer.

Vérification complémentaire de l'autonomie réelle : `ldd gui`/`ldd
lib/libapp.so` — `libapp.so` "statically linked" (aucun Python système
requis, `libpython3.12.so.1.0` + stdlib compilée sont bien embarqués) ;
toutes les bibliothèques système (GTK3/GLib/Pango/Cairo/ATK/X11/Wayland/
fontconfig/D-Bus) résolues sans "not found" sur cette machine Ubuntu —
aucune installation supplémentaire nécessaire sur la machine cible, pour
la partie qui fonctionnerait une fois le blocage corrigé. Vérification
des chemins de préférences/cache/config (`utils/paths.py`, Sprint 49) :
confirmés corrects et indépendants des variables `FLET_APP_STORAGE_DATA`/
`FLET_APP_STORAGE_TEMP` propres à Flet (jamais lues par le code de
l'app) — bonne nouvelle de cet audit.

### Travail effectué

**`docs/PACKAGING.md`** — encart de correction ajouté en tête (sans
réécrire silencieusement l'affirmation prématurée du Sprint 49) +
nouvelle section §6 complète : cartographie du dossier de build,
verdict d'autonomie détaillé, cause racine avec les 2 corrections
candidates, tableau de vérification identité/icônes/chemins, liste des
7 éléments manquants pour une vraie Beta distribuable.

**`docs/RELEASE.md`** (nouveau) — procédure de release pas-à-pas :
générer Linux (§2), générer Windows (§3, jamais exécuté pour de vrai —
inchangé depuis le Sprint 49), assembler `Release/` (§4), vérification
pré-release (§5, tests/ruff/mypy), publier une Release GitHub via `gh
release create` avec extraction automatique de la section CHANGELOG
correspondante (§6). Avertissement explicite en tête pointant vers le
blocage non résolu.

**`.gitignore`** — `Release/` ajouté (zone de préparation locale
régénérée à chaque release, jamais versionnée, même raisonnement que
`build/` déjà ignoré).

### Arborescence `Release/` proposée

```
Release/
├── Linux/
│   ├── motorsport-calendar-<version>-linux-x64.tar.gz
│   └── motorsport-calendar-<version>-linux-x64.tar.gz.sha256
├── Windows/
│   ├── motorsport-calendar-<version>-windows-x64.zip
│   └── motorsport-calendar-<version>-windows-x64.zip.sha256
├── Source/
│   └── motorsport-calendar-<version>-source.tar.gz
├── CHANGELOG.md
├── LICENSE
└── README.md
```

Toujours des archives compressées + somme de contrôle, jamais les
dossiers bruts (112 Mo de fichiers non compressés n'ont rien à faire
dans une Release GitHub) — détail complet et justification de chaque
entrée dans `docs/RELEASE.md` §4.

### Tests

Aucun test nouveau — ce sprint ne touche aucun fichier source
applicatif (audit + documentation uniquement). Suite complète relancée
pour confirmer l'absence de régression : `pytest`/`ruff`/`mypy` tous
identiques à l'état de fin du Sprint 57.

### Fichiers modifiés / créés

| Fichier | Action |
|---|---|
| `docs/PACKAGING.md` | Modifié — encart de correction + §6 (audit complet) |
| `docs/RELEASE.md` | Créé |
| `.gitignore` | Modifié — `Release/` ajouté |
| `CHANGELOG.md` | Mis à jour |
| `docs/ROADMAP.md` | Mis à jour — v0.4.32 |
| `docs/AI_CONTEXT.md` | Mis à jour — entrée #58, 3 lignes de dette, 4 nouvelles pistes |
| `docs/TODO.md` | Mis à jour |
| `docs/DECISIONS.md` | ADR-049 ajouté |

Aucun fichier source de `motorsport_calendar/` modifié.

### Tests exécutés
```
2034 passed (1 skipped, Windows-only) — inchangé, 0 failed
```

Ruff : 0 erreur (inchangé). mypy `motorsport_calendar/`/`tests/` :
inchangés (41/176, identiques à la fin du Sprint 57) — aucune
modification de code source ce sprint.

`git status --short` confirmé en fin de session : **aucun commit
effectué**, conforme à la clôture de sprint demandée.

### Limites
- **Le correctif du blocage `ModuleNotFoundError` n'a pas été appliqué**
  ni vérifié — explicitement hors périmètre ("audit complet", jamais
  "corrige le packaging"). Les 2 pistes candidates sont documentées avec
  suffisamment de détail pour qu'un futur sprint les applique sans
  redécouvrir le problème.
- **Le build Windows reste totalement non vérifié** — aucune machine
  Windows disponible dans cet environnement, inchangé depuis le
  Sprint 49 ; tout le contenu de `docs/RELEASE.md` §3 reste transcrit
  depuis la documentation officielle de Flet, jamais confirmé pour de
  vrai contre ce projet.
- **Quelques fichiers de cache/log créés hors du dépôt** pendant le test
  du binaire (`~/.cache/com.flet.gui/`, `~/Documents/flet/gui`,
  ~1 Mo au total) — artefacts inoffensifs du lancement de test, non
  supprimés (hors du dépôt, sans rapport avec le projet lui-même), signalés
  ici par transparence plutôt que supprimés sans le signaler.

---

## Session 2026-07-13 — Sprint 57 : Préparation Beta : Nettoyage & Positionnement

### Objectif
Motorsport Calendar approche de sa première Beta publique. L'objectif
n'est plus d'ajouter des fonctionnalités mais de préparer une
application réellement distribuable — ce sprint concerne uniquement le
positionnement du produit : (1) masquer IMSA/WorldSBK de l'interface
tant qu'ils n'ont pas de source fiable, sans supprimer de code ; (2)
transformer "À propos" en véritable présentation du projet ; (3) créer
une nouvelle page "Soutenir le projet", point de contact avec la
communauté (soutien financier, vote de fonctionnalités, suggestions,
signalement de bugs) — purement informative, aucun système de vote ou
de dons local.

### Audit rapide (préalable, demandé par le brief)
- Tests : 2000 passants, 0 échouant.
- Couverture : ~97 %.
- Dette Ruff : 0 erreur.
- Dette mypy `motorsport_calendar/` : 39 erreurs (une seule famille
  documentée depuis le Sprint 26 — décalage stubs Flet 0.80/runtime
  0.85.3).
- Dette mypy `tests/` : 157 erreurs (même famille, bruit résiduel du
  typage dynamique).
- `git status --short` : dette héritée des sprints précédents, aucun
  commit tenté ce sprint non plus.

### Exploration préalable
Recherche du seul appelant de `controller.list_championships()` (grep
exhaustif) : `main_view.py:327`, aucun autre — confirme que filtrer à cet
unique endroit suffit à masquer IMSA/WorldSBK partout dans la GUI
(sélecteurs de "Mon calendrier"/"Mes favoris", résultats de
"Recherche"), sans toucher `registry.list_all()`
(`ProviderRegistry`/CLI) ni `config.yaml`. Relecture de `gui/
categories.py::get_groups_for()` — déjà conçu pour ignorer silencieusement
les ids absents de `available_ids` ("Only IDs actually present in
ProviderRegistry will appear — the rest are silently ignored"), donc
aucun cas d'accordéon vide à gérer : ENDURANCE (wec/elms/mlmc/imsa) et
MOTO (motogp/moto2/moto3/worldsbk) gardent chacun 3 championnats visibles
une fois imsa/worldsbk retirés. Vérification de
`upcoming_weekend.py::WEEKEND_CHAMPIONSHIP_IDS` ("Ce week-end"/
Dashboard) : IMSA/WorldSBK y figurent mais leurs sources
(`OfficialImsaSource`/`OfficialWorldSbkSource`) sont des stubs qui
échouent systématiquement (dette documentée depuis les Sprints 36/38/48)
— aucune carte n'en est jamais issue de toute façon, donc les retirer de
cette liste n'aurait changé aucun comportement observable ; décision de
ne pas y toucher (scope minimal). Relecture de `docs/PRODUCT_VISION.md`
(déjà rédigé : "pourquoi Motorsport Calendar existe", "philosophie",
"pour qui") pour réutiliser le vocabulaire déjà établi du produit plutôt
que d'inventer un nouveau discours pour "À propos". Recherche de 2
duplications déjà identifiées dans des sprints précédents mais jamais
traitées : la logique "ouvrir une URL avec repli Windows" existait
indépendamment dans `views/about.py` (Sprint 26) et `main_view.py::
_make_release_opener` (Sprint 51/53) ; la forme "icône + label + puce
Disponible prochainement" existait dans `views/preferences.py::_pref_row`
(Sprint 52, privé). Les besoins de "Soutenir le projet" (2 boutons
GitHub, 2 emplacements de don) en faisaient des 3èmes/2èmes occurrences
réelles, pas seulement théoriques.

### Travail effectué

**1. Championnats masqués** — `controller.py` gagne
`_HIDDEN_FROM_GUI: frozenset[str] = frozenset({"imsa", "worldsbk"})` et
`list_championships()` filtre désormais `registry.list_all()` contre cet
ensemble avant de le retourner. `registry.list_all()` lui-même,
`registry.enabled(...)` et `cli.py generate-imsa`/`generate-worldsbk`
restent intégralement inchangés.

**2. "À propos" devient une vraie présentation** — `views/about.py`
conserve le bloc branding/version/développeur/GitHub/licence déjà
existant (Sprints 26-54) et ajoute 3 nouvelles `Section`s : "Objectifs du
projet" (3 points, `theme.card`), "Philosophie Open Source" (un
paragraphe, `theme.card`), "Technologies utilisées" (6 `theme.chip`,
même patron que les chips de championnat de la fiche Circuit — aucun
nouveau composant). Le lien GitHub réutilise désormais
`gui/url_opener.py::make_url_opener` au lieu de sa fermeture locale.

**3. Nouvelle page "Soutenir le projet"** (`gui/views/support.py`, 8ème
destination du rail de navigation, icône `VOLUNTEER_ACTIVISM`) — 4
sections dans l'ordre du brief : "Soutenir Motorsport Calendar" (2
`ComingSoonRow`, PayPal/GitHub Sponsors, aucun lien réel) ; "Voter pour
les prochaines fonctionnalités" (8 `theme.chip` — Classements, Diffusion
TV, Mobile, Motorsport API, Résultats, Pilotes, Équipes, Widgets —
présentation pure, aucun vote) ; "Suggestions" (bouton → GitHub
Discussions) ; "Signaler un problème" (bouton "Signaler un bug" → GitHub
Issues). Reçoit `url_launcher` directement, comme "À propos" (aucun état
à injecter par main_view.py pour cette page).

**Nettoyage** — deux fonctions partagées créées, remplaçant chacune 2
implémentations indépendantes :
- `gui/url_opener.py::make_url_opener(url_launcher, url)` — remplace
  `views/about.py::on_github_click` et `main_view.py::
  _make_release_opener` (supprimée), désormais utilisée à 4 sites
  d'appel (About, Dashboard "Nouveautés", boîte de dialogue de mise à
  jour, les 2 boutons de "Soutenir le projet").
- `gui/components/layout::ComingSoonRow(icon, label)` — remplace
  `views/preferences.py::_pref_row` (supprimée), utilisée par la section
  Application des Préférences et les 2 emplacements de don de "Soutenir
  le projet".

### Tests

- `tests/test_gui_controller.py` (+3, `TestListChampionships`) — IMSA/
  WorldSBK absents de `list_championships()` mais toujours présents dans
  `registry.list_all()`.
- `tests/test_gui_views.py` (+4 `TestAboutView`, +15 `TestSupportView`,
  +1 import dans `TestAllViewsShareTheSameGrid`) — couvrant les 3
  nouvelles sections d'"À propos", et les 4 scénarios de "Soutenir le
  projet" (chaque section présente, les 2 boutons ouvrent la bonne URL
  GitHub, les placeholders de don et les idées de vote ne sont jamais
  cliquables).
- `tests/test_gui_components_layout.py` (+5, `TestComingSoonRow`).
- `tests/test_gui_url_opener.py` (nouveau, 7 tests dont 1 spécifique
  Windows — `skip`é sur cet environnement Linux, jamais désactivé
  silencieusement).

### Fichiers modifiés / créés

| Fichier | Action |
|---|---|
| `motorsport_calendar/gui/controller.py` | Modifié — `_HIDDEN_FROM_GUI`, `list_championships()` filtré |
| `motorsport_calendar/gui/views/about.py` | Modifié — 3 nouvelles sections, GitHub via `make_url_opener` |
| `motorsport_calendar/gui/views/support.py` | Créé |
| `motorsport_calendar/gui/views/preferences.py` | Modifié — `_pref_row` retiré, utilise `ComingSoonRow` |
| `motorsport_calendar/gui/url_opener.py` | Créé |
| `motorsport_calendar/gui/components/layout/coming_soon_row.py` | Créé |
| `motorsport_calendar/gui/components/layout/__init__.py` | Modifié — export `ComingSoonRow` |
| `motorsport_calendar/gui/strings.py` | Modifié — chaînes About (objectifs/philosophie/tech) + Support |
| `motorsport_calendar/gui/main_view.py` | Modifié — `_make_release_opener` retiré, nav "Soutenir le projet" ajoutée |
| `tests/test_gui_controller.py` | Modifié — 3 tests ajoutés |
| `tests/test_gui_views.py` | Modifié — 20 tests ajoutés |
| `tests/test_gui_components_layout.py` | Modifié — 5 tests ajoutés |
| `tests/test_gui_url_opener.py` | Créé — 7 tests |
| `CHANGELOG.md` | Mis à jour |
| `docs/ROADMAP.md` | Mis à jour — v0.4.31 |
| `docs/AI_CONTEXT.md` | Mis à jour — entrée #57, 4 lignes de dette, 2 nouvelles pistes |
| `docs/TODO.md` | Mis à jour |
| `docs/DECISIONS.md` | ADR-048 ajouté |

Aucun nouveau provider, aucune évolution métier, aucune évolution des
services, aucun système de vote/dons local — conforme au brief.

### Tests exécutés
```
2000 passed → 2033 passed, 1 skipped — 0 failed
```

Ruff : 0 erreur sur l'ensemble du dépôt (inchangé). mypy
`motorsport_calendar/` : 39 → 41 (+2, les 2 boutons `on_click` de
"Soutenir le projet", même famille Flet stub-version déjà acceptée).
mypy `tests/` : 157 → 176 (+19, `test_gui_url_opener.py` utilisant un
double factice plutôt que le vrai type Flet + `TestComingSoonRow`
accédant à `.content`/`.icon` sur un `ft.Control` non affiné — même
famille de bruit résiduel déjà documentée, aucune vraie erreur de
logique de test).

`git status --short` confirmé en fin de session : **aucun commit
effectué**, conforme à la clôture de sprint demandée.

### Limites
- **Aucune vérification visuelle réelle** d'"À propos"/"Soutenir le
  projet" — poste avec affichage indisponible dans cet environnement,
  comme chaque sprint GUI précédent ; les 19 nouveaux tests verrouillent
  la structure (bon texte, bonnes sections, bons liens) mais jamais le
  rendu pixel.
- **PayPal/GitHub Sponsors restent des emplacements vides** — assumé et
  documenté, pas un oubli : le brief demande explicitement de préparer
  la structure sans lien réel.
- **IMSA/WorldSBK restent invisibles** tant qu'aucune source fiable
  n'existe — un futur retrait de `_HIDDEN_FROM_GUI` suffira à les
  réintégrer, aucun autre changement requis.

### Réponse à la question de clôture du brief

**"La page 'Soutenir le projet' donne-t-elle envie de rejoindre la
communauté ?"**

Oui, dans une mesure raisonnable pour ce stade du projet, avec une
réserve honnête sur ce qui reste à vérifier. La page réunit en un seul
endroit les 4 façons naturelles de s'impliquer (financièrement, en
influençant la direction du produit, en proposant des idées, en
signalant des problèmes) — c'est structurellement complet et couvre
exactement ce que la brief demande. Les points forts : la section
"Voter pour les prochaines fonctionnalités" rend visibles des pistes
concrètes et attrayantes (Classements, Diffusion TV, Mobile, Motorsport
API...) qui donnent une idée tangible de ce que le projet pourrait
devenir — c'est ce qui donne le plus envie de revenir voir où en est le
projet. Les boutons Discussions/Issues abaissent la friction à zéro
clic vers GitHub, sans détour par un formulaire local à remplir. La
réserve : les 2 emplacements de don ("Bientôt disponible") sont
honnêtes mais pourraient se lire comme une déception pour un visiteur
qui cherche activement à soutenir financièrement dès aujourd'hui — un
compromis assumé par le brief lui-même ("aucun lien réel n'est encore
nécessaire"), pas un défaut de cette implémentation. Et comme pour
chaque page GUI de ce projet, l'appréciation réelle de "donne envie"
dépend d'un rendu visuel jamais vérifié dans cet environnement sans
affichage — cette réponse porte sur la structure et le contenu, pas sur
l'expérience pixel par pixel.

---

## Session 2026-07-13 — Sprint 56 : Notifications natives

### Objectif
Motorsport Calendar dispose déjà d'un `NotificationService` (Sprint 46,
moteur pur — calcule quoi/quand notifier), des préférences utilisateur
(Sprint 52), des favoris et des événements normalisés. Objectif de ce
sprint : connecter ce moteur à une implémentation native pour afficher de
vraies notifications système lorsque cela est possible, sans jamais faire
dépendre `NotificationService` d'une plateforme (Windows/Linux/macOS).
Le brief impose une méthode précise en cas d'absence de solution native
propre : ne jamais bricoler, créer uniquement une abstraction prête à
recevoir une future implémentation.

### Audit rapide (préalable, demandé par le brief)
- Tests : 1978 passants, 0 échouant.
- Couverture : ~97 %.
- Dette Ruff : 0 erreur.
- Dette mypy `motorsport_calendar/` : 39 erreurs (une seule famille
  documentée depuis le Sprint 26 — décalage stubs Flet 0.80/runtime
  0.85.3).
- Dette mypy `tests/` : 157 erreurs (inchangée après ce sprint).
- `git status --short` : dette héritée des sprints précédents, aucun
  commit tenté ce sprint non plus.

### Exploration préalable — vérifier, ne jamais supposer
Avant d'écrire la moindre ligne de code, recherche exhaustive dans le
paquet `flet==0.85.3` réellement installé dans l'environnement (jamais
la documentation en ligne, jamais une connaissance générale
potentiellement obsolète) :
- `.venv/lib/.../flet/controls/services/` — le dossier qui contient
  chaque "pont natif" officiel de Flet — listé intégralement :
  accelerometer, barometer, battery, browser_context_menu, clipboard,
  connectivity, file_picker, gyroscope, haptic_feedback, magnetometer,
  screen_brightness, semantics_service, shake_detector,
  shared_preferences, share, storage_paths, url_launcher,
  user_accelerometer, wakelock. 20 services, aucun pour les
  notifications système.
- `flet/controls/core/window.py` (`ft.Window`) — méthode par méthode :
  `wait_until_ready_to_show`/`destroy`/`center`/`close`/`to_front`/
  `start_dragging`/`start_resizing`. Aucune icône de zone de
  notification, aucun hook de notification native.
- `~/.pub-cache/hosted/pub.dev/flet-0.85.3/CHANGELOG.md` (le changelog
  Dart bundlé avec le paquet) — recherche de "notif" dans tout
  l'historique des releases : une seule occurrence, pour les
  notifications de **scroll** (`ScrollNotification`, un événement
  d'interface sans rapport), jamais pour une notification système.

Conclusion vérifiée : Flet ne fournit aucune capacité de notification
système sur aucune plateforme, à la version installée. Recherche
complémentaire : aucune bibliothèque de notification tierce (`plyer`,
`winotify`, `notify-py`, `notify2`) n'est déjà présente dans
l'environnement (`pip list`) ni dans `pyproject.toml`. Relecture de
`gui/notification_service.py` (confirmation que `Notification` est
"purement structuré, sans texte formaté" — le formatage est
explicitement délégué à un futur consommateur depuis le Sprint 46) et
de `gui/controller.py::check_for_update` (précédent exact à suivre pour
le court-circuit d'une préférence désactivée). Découverte en passant :
`utils/logging.py::get_logger` existe depuis le tout début du projet
mais n'est consommé nulle part dans le code applicatif réel — ce sprint
en devient le premier vrai utilisateur.

### Travail effectué

**Nouveau `gui/system_notifications.py`** — la seule couche du projet
autorisée à connaître l'existence d'une plateforme (voir ADR-047 pour
le raisonnement complet) :
- `SystemNotifier` (`Protocol`, 2 méthodes : `is_available()`/
  `notify(title, body)`) — la forme qu'une future implémentation devra
  remplir.
- `NullSystemNotifier` — la seule implémentation livrée ce sprint,
  toujours indisponible par construction (jamais un bug, jamais un
  contournement).
- `get_system_notifier()` — factory, toujours la null aujourd'hui ; le
  seul endroit où une détection de plateforme future prendrait place.
- `notify_all(notifications, *, notifier=None)` — point d'entrée
  unique. Ne lève jamais : un notifieur indisponible ou qui échoue
  dégrade toujours vers un no-op silencieux, journalisé (`_logger.debug`,
  via `utils.get_logger`) plutôt qu'affiché comme une erreur technique.
- `_format(notification)` — formate titre/corps ; 5 nouvelles chaînes
  `strings.py` pour les libellés `NotificationKind` (jamais dans
  `NotificationService`, qui reste sans texte formaté).

**`gui/controller.py::prepare_notifications()`** (nouveau) — même rôle
"le contrôleur relie la logique métier aux préférences" que
`check_for_update`. Court-circuite avant même de construire
`NotificationService()` si `notifications_enabled` est désactivé (la
préférence existante du Sprint 52, aucun nouveau réglage) ; sinon,
calcule via `compute_notifications()` inchangé puis délègue à
`notify_all()`.

**`main_view.py`** — `_prepare_system_notifications()` appelle
`prepare_notifications(year_events, favorite_ids=...)` une fois au
démarrage et à chaque rafraîchissement de `year_events` (changement
d'année), même déclencheur que les reconstructions d'index recherche/
circuits déjà en place juste au-dessus dans `_load_year_events`.
main_view.py n'importe jamais `system_notifications` directement, ni ne
lit la préférence lui-même — tout vit dans `controller.py`.

### Tests

- `tests/test_gui_system_notifications.py` (nouveau, 16 tests) —
  `TestNullSystemNotifier`/`TestGetSystemNotifier`/
  `TestNotifyAllUnavailable`/`TestNotifyAllAvailable`/
  `TestNotifyAllEmptyEngine`/`TestNotifyAllDegradation`, couvrant
  explicitement "notifications disponibles"/"indisponibles"/"moteur
  vide"/"absence de plateforme compatible" plus la dégradation d'un
  notifieur qui lève une exception sur `is_available()`/`notify()`.
- `tests/test_gui_controller.py` (+6 tests, `TestPrepareNotifications`)
  — couvre le scénario restant, "préférences désactivées" (prouvé en
  patchant `compute_notifications` pour échouer si jamais atteint,
  même technique que `TestCheckForUpdate`), plus le passage bout-en-bout
  réel (activé, session à venir réellement calculée, mais 0 notification
  effectivement affichée puisqu'aucune plateforme n'est encore
  compatible — vérifié en direct par le test, pas supposé), la
  propagation de `favorite_ids`, et le défaut de `now`.

### Fichiers modifiés / créés

| Fichier | Action |
|---|---|
| `motorsport_calendar/gui/system_notifications.py` | Créé |
| `motorsport_calendar/gui/controller.py` | Modifié — `prepare_notifications()` ajoutée |
| `motorsport_calendar/gui/main_view.py` | Modifié — `_prepare_system_notifications()`, câblage dans `_load_year_events` |
| `motorsport_calendar/gui/strings.py` | Modifié — 6 nouvelles chaînes de notification |
| `tests/test_gui_system_notifications.py` | Créé |
| `tests/test_gui_controller.py` | Modifié — `TestPrepareNotifications` ajoutée |
| `CHANGELOG.md` | Mis à jour |
| `docs/ROADMAP.md` | Mis à jour — v0.4.30 |
| `docs/AI_CONTEXT.md` | Mis à jour — entrée #56, nouvelle ligne de dette, nouvelle piste |
| `docs/TODO.md` | Mis à jour |
| `docs/DECISIONS.md` | ADR-047 ajouté |

`motorsport_calendar/gui/notification_service.py` **non modifié** —
vérifié explicitement en fin de session. Aucun nouveau provider, aucune
nouvelle dépendance, aucun nouveau réglage — conforme au brief.

### Tests exécutés
```
1978 passed → 2000 passed — 0 failed
```

Ruff : 0 erreur sur l'ensemble du dépôt (inchangé). mypy
`motorsport_calendar/` : 39 → 39 (inchangé — le nouveau module ne
construit aucun contrôle Flet, aucune signature de callback en jeu).
mypy `tests/` : 157 → 157 (inchangé).

`git status --short` confirmé en fin de session : **aucun commit
effectué**, conforme à la clôture de sprint demandée.

### Limites
- **Aucune notification système n'est jamais réellement affichée** —
  assumé et documenté, pas une régression cachée : `NullSystemNotifier`
  est la seule implémentation, en attendant qu'une solution native
  propre existe (Flet ou une dépendance tierce délibérément choisie).
- **L'audit de disponibilité est un instantané de Flet 0.85.3** — à
  revérifier de la même façon (grep exhaustif du paquet installé,
  jamais une supposition) avant toute Beta si une version majeure de
  Flet sort entretemps.
- **Aucune vérification sur un vrai poste multi-plateforme** — même
  limitation que chaque sprint GUI précédent ; de toute façon sans objet
  ici puisqu'aucune notification n'est actuellement affichable sur
  aucune plateforme.

### Réponses aux deux questions du brief

**1. Les notifications natives sont-elles réellement disponibles sur
les plateformes supportées ?**

Non — fait vérifié, pas une hypothèse. Flet 0.85.3 (la version
installée et utilisée par ce projet) ne fournit aucun service de
notification système sur aucune plateforme : ses 20 services officiels
(`flet.controls.services.*`) ne couvrent ni Windows, ni Linux, ni
macOS pour ce besoin ; `ft.Window` n'expose aucune icône de zone de
notification ; le changelog complet de Flet ne mentionne jamais les
notifications système dans son historique de releases. Ce n'est donc
pas une limitation de plateforme (Windows/macOS/Linux ont chacun une
vraie API de notification native) mais une lacune du framework
d'interface utilisé par ce projet.

**2. Si non, quelle est la meilleure stratégie retenue pour la Beta ?**

Livrer l'abstraction, pas un contournement. `gui/system_notifications.py`
définit la forme exacte qu'une future implémentation devra prendre
(`SystemNotifier`) et fournit la seule implémentation honnête
disponible aujourd'hui (`NullSystemNotifier`) — le moteur, les
préférences et l'orchestration sont entièrement prêts et testés, prêts
à afficher de vraies notifications le jour où `get_system_notifier()`
retourne autre chose que la null. Bricoler une solution avec une
bibliothèque tierce maintenant aurait été prématuré : le choix d'une
bibliothèque par plateforme, ses permissions (notamment macOS/Windows)
et son empreinte sur le packaging (`docs/PACKAGING.md`) sont des
décisions réelles qui méritent leur propre sprint dédié, pas un
sous-produit d'un sprint de connexion. Pour la Beta, la stratégie
retenue est donc : documenter clairement cette limite (elle l'est,
dans `docs/AI_CONTEXT.md`/`docs/TODO.md`, piste `-20`), et traiter
l'ajout d'un vrai `SystemNotifier` comme un sprint futur explicite,
déclenché soit par une release Flet qui comble ce manque, soit par une
décision produit assumée d'ajouter une dépendance tierce.

---

## Session 2026-07-13 — Sprint 55 : Recherche interactive

### Objectif
"Recherche" (Sprint 45) permet déjà de retrouver championnats/
événements/circuits, mais les résultats restent passifs — un clic ne
fait rien. Identifié comme dette au Sprint 54 (piste `-18`, hors
périmètre à l'époque). Objectif de ce sprint : permettre d'interagir
avec chaque résultat selon sa nature — championnat → meilleure
destination existante, événement → fiche événement existante
(Sprint 42), circuit → fiche Circuit existante (Sprint 47) — en
réutilisant exclusivement `SearchService`/`EventDetails`/
`CircuitService`/la navigation déjà existante, sans nouveau service,
sans nouvelle logique métier, sans duplication.

### Audit rapide (préalable, demandé par le brief)
- Tests : 1968 passants, 0 échouant.
- Couverture : ~97 %.
- Dette Ruff : 0 erreur.
- Dette mypy `motorsport_calendar/` : 39 erreurs (une seule famille
  documentée depuis le Sprint 26 — décalage stubs Flet 0.80/runtime
  0.85.3).
- Dette mypy `tests/` : 157 erreurs (inchangée après ce sprint).
- `git status --short` : dette héritée des sprints précédents, aucun
  commit tenté ce sprint non plus.

### Exploration préalable
Relecture de `gui/search_service.py` (`SearchResultItem`/
`SearchResults`/`SearchService.build_index`/`search` — Sprint 45,
aucune identité portée jusqu'ici, uniquement du texte déjà formaté) et
de `gui/views/search.py` (`_result_row` purement statique, aucun
`on_click`). Comparaison avec les deux résolutions "identité → vue
existante" déjà écrites ailleurs dans l'app : `main_view.py::
_on_event_row_click` (season explorer, Sprint 42 — cherche un `Event`
dans `year_events` par `championship_id`/`event_uid`, ouvre la fiche) et
le `on_circuit_click` interne à `_show_event_details_dialog` (Sprint 47
— résout un `circuit_key` via `CircuitService`, ouvre la fiche Circuit).
Vérification, en lisant `gui/event_display.py`/`gui/circuit_service.py`,
que `display.circuit_key` (déjà utilisé par `search_service.py` pour
dédupliquer les circuits) est bien le même format de clé que
`CircuitService.get_circuit()` attend (`normalize_key(circuit_display_
name(...))` des deux côtés) — confirmé avant d'écrire le moindre code
de câblage, pas supposé. Recherche d'une éventuelle page dédiée par
championnat pour le clic "championnat" : aucune n'existe ; "Mon
calendrier" retenue comme la destination existante la plus proche
(brief, verbatim : "la meilleure destination existante").

### Travail effectué

**`gui/search_service.py::SearchResultItem`** — 3 nouveaux champs
optionnels (`championship_id`/`event_uid`/`circuit_key`), jamais
rendus — même convention "identité portée à travers" que
`SeasonEventRow` (Sprint 42). `build_index()` les peuple en passant,
avec des valeurs déjà calculées pour d'autres besoins (`cid` de la
boucle, `event.event_uid`, `display.circuit_key`) — aucune nouvelle
logique de recherche/normalisation.

**`gui/views/search.py`** — `build_search_view()` gagne 3 callbacks
optionnels (`on_championship_click`/`on_event_click`/
`on_circuit_click`, tous `Callable[[SearchResultItem], None] | None`).
`_result_row`/`_result_section` câblent `card.on_click = lambda e:
on_click(item)` — attribution post-construction, même style que
`_championship_button`/`_season_event_row` (calendar.py), jamais
`ft.Container(on_click=...)` au constructeur (qui aurait ajouté à la
dette mypy Flet-stub).

**`main_view.py`** — deux résolutions extraites en fonctions partagées
au niveau de `build_main_view` (voir ADR-046) :
- `_open_event_details(championship_id, event_uid)` — ex-corps de
  `_on_event_row_click`, désormais aussi appelée par le clic résultat
  événement de "Recherche".
- `_open_circuit_details(circuit_key)` — ex-corps du `on_circuit_click`
  interne à `_show_event_details_dialog`, désormais aussi appelé par le
  clic résultat circuit.

Trois nouveaux handlers dans le bloc SEARCH CONTROLS :
`_on_search_championship_click` (navigue vers "Mon calendrier" via
`_navigate_to("calendar")`, sans jamais toucher `state.
selected_championships`), `_on_search_event_click`/
`_on_search_circuit_click` (délèguent directement aux deux fonctions
partagées ci-dessus). Les deux call sites de `build_search_view(...)`
(construction initiale + `_refresh_search_view`) passent désormais les
3 callbacks.

### Tests

- `tests/test_gui_search_service.py` (+4 tests, `TestSearchResultIdentity`)
  — championnat/événement/circuit portent la bonne identité, la clé
  circuit survit à la déduplication entre championnats.
- `tests/test_gui_views.py` (+6 tests, `TestSearchView`) — couvrant
  explicitement les 4 scénarios nommés par le brief : "clic
  championnat" (`test_clicking_a_championship_result_calls_on_
  championship_click`), "clic événement", "clic circuit", "absence de
  résultat" (2 variantes : callback non fourni → carte jamais
  cliquable ; résultats vides malgré des callbacks fournis → aucune
  carte cliquable) ; plus une garantie d'isolation entre sections
  (cliquer un résultat championnat ne déclenche jamais les callbacks
  événement/circuit).

### Fichiers modifiés / créés

| Fichier | Action |
|---|---|
| `motorsport_calendar/gui/search_service.py` | Modifié — `SearchResultItem` +3 champs d'identité |
| `motorsport_calendar/gui/views/search.py` | Modifié — 3 callbacks de clic, cartes cliquables |
| `motorsport_calendar/gui/main_view.py` | Modifié — `_open_event_details`/`_open_circuit_details` extraites, 3 nouveaux handlers de recherche |
| `tests/test_gui_search_service.py` | Modifié — `TestSearchResultIdentity` ajoutée |
| `tests/test_gui_views.py` | Modifié — 6 tests ajoutés à `TestSearchView` |
| `CHANGELOG.md` | Mis à jour |
| `docs/ROADMAP.md` | Mis à jour — v0.4.29 |
| `docs/AI_CONTEXT.md` | Mis à jour — entrée #55, dette résolue, nouvelle piste |
| `docs/TODO.md` | Mis à jour |
| `docs/DECISIONS.md` | ADR-046 ajouté |

Aucun service/provider/modèle créé, aucune nouvelle page — conforme au
brief.

### Tests exécutés
```
1968 passed → 1978 passed — 0 failed
```

Ruff : 0 erreur sur l'ensemble du dépôt (inchangé). mypy
`motorsport_calendar/` : 39 → 39 (inchangé — le câblage `on_click` en
attribut post-construction, jamais au constructeur, n'ajoute aucune
erreur à la famille Flet stub-version déjà documentée). mypy `tests/` :
157 → 157 (inchangé).

`git status --short` confirmé en fin de session : **aucun commit
effectué**, conforme à la clôture de sprint demandée.

### Limites
- **Aucune vérification visuelle réelle** des 3 nouveaux types de clic
  — poste avec affichage indisponible dans cet environnement, comme
  chaque sprint GUI précédent ; les 10 nouveaux tests verrouillent le
  câblage (bon callback, bon item, bonne isolation) mais jamais le rendu
  ou le clic pixel.
- **Aucune indication visuelle qu'une carte de résultat est cliquable**
  (curseur, effet au survol) — cohérent avec le choix déjà fait pour le
  lien circuit de la fiche événement (Sprint 47), jamais eu cette
  indication non plus ; documenté comme piste possible, non exploré.
- **Le clic championnat navigue sans présélectionner** le championnat
  sur "Mon calendrier" — choix délibéré (voir ADR-046) pour ne jamais
  muter silencieusement la sélection de génération de l'utilisateur,
  mais signifie que l'utilisateur doit encore chercher/déplier la bonne
  catégorie une fois arrivé sur la page.

---

## Session 2026-07-13 — Sprint 54 : Préparation Beta (Recette UX)

### Objectif
Motorsport Calendar possède désormais toutes les fonctionnalités
majeures prévues pour l'Alpha (Sprints 1-53). Avant de poursuivre le
développement, le brief demande une phase de recette utilisateur pure :
relire l'ensemble de l'interface (7 pages), auditer 8 axes de cohérence
nommés explicitement (espacements, icônes, titres, textes, boutons,
messages vides, dialogues, navigation), identifier les points faibles
(informations peu visibles, scrolls inutiles, actions difficiles à
trouver, doublons, incohérences de vocabulaire, textes trop techniques),
et corriger uniquement ce qui est "clairement identifié" — sans jamais
ajouter de fonctionnalité, provider, ou évolution des services/modèles.

### Audit rapide (préalable, demandé par le brief)
- Tests : 1961 passants, 0 échouant.
- Couverture : ~97 %.
- Dette Ruff : 0 erreur.
- Dette mypy `motorsport_calendar/` : 39 erreurs (une seule famille
  documentée depuis le Sprint 26 — décalage stubs Flet 0.80/runtime
  0.85.3).
- Dette mypy `tests/` : 157 erreurs (inchangée après ce sprint).
- `git status --short` : dette héritée des sprints précédents, aucun
  commit tenté ce sprint non plus.

### Audit UX
Lecture complète des 7 vues (`gui/views/dashboard.py`/`weekend.py`/
`calendar.py`/`search.py`/`favorites.py`/`preferences.py`/`about.py`),
de `gui/main_view.py` (1147 lignes — état, handlers, 4 boîtes de
dialogue), de `gui/theme.py` (Design System), et de `gui/strings.py`
(tout le texte utilisateur), plus les composants partagés
(`components/layout/*`, `championship_card.py`, `championship_selector.py`).
Recherches ciblées en complément de la lecture : `grep` de chaque valeur
`spacing=` littérale dans `gui/` pour détecter les bypasses du Design
System (invisible à la seule relecture — 8 trouvées) ; comparaison
systématique de chaque icône de `PageHeader` avec l'icône
`selected_icon` du `NavigationRailDestination` correspondant dans
`main_view.py` (2 incohérences trouvées) ; recherche de tout caractère
emoji dans du texte réellement rendu vs. dans des docstrings (1 trouvée,
dans la boîte de dialogue de succès) ; extraction de toutes les valeurs
de `strings.py` pour repérer les doublons/chaînes mortes (`nav_home`/
`nav_calendar`, jamais référencées) et les incohérences de ponctuation
des titres `EmptyState` (6 titres, moitié avec point moitié sans).
Vérification que `EmptyState.icon` (un paramètre optionnel existant
depuis le Sprint 31) n'est en réalité utilisé par aucun appelant — les
7 messages vides de l'app sont donc déjà cohérents entre eux sur ce
point précis (aucun n'a d'icône), rien à corriger là.

### Travail effectué

**Icônes** — 3 corrections :
- `views/favorites.py` : icône d'en-tête `STAR_BORDER` → `STAR`,
  rejoignant la convention déjà suivie par "Ce week-end"/"Mon
  calendrier"/"Recherche"/"Préférences" (icône de `PageHeader` = variante
  pleine du `selected_icon` du rail de navigation).
- `views/dashboard.py` : `_HEADER_ICON` `SPACE_DASHBOARD_OUTLINED` →
  `SPACE_DASHBOARD` — même correction.
- `main_view.py::_show_success_dialog` : le titre "✅ Calendrier créé
  avec succès" (emoji codé en dur dans une f-string) devient un
  `ft.Row([ft.Icon(CHECK_CIRCLE, color=Colors.SUCCESS), ft.Text(...)])`
  — cohérent avec le reste de l'app, qui n'affiche jamais d'emoji,
  uniquement des icônes Material.

**Espacements** — 8 occurrences d'un espacement codé en dur
(`spacing=2` ×6 dans `views/preferences.py`/`about.py`/`search.py`/
`calendar.py` ×3 ; `spacing=4` ×2 dans `main_view.py`, boîtes de
dialogue succès/mise à jour) remplacées par `theme.Spacing.XXS` — la
règle de `theme.py` ("no view should hardcode ... a raw padding int")
existait déjà depuis le Sprint 26 mais n'avait jamais été vérifiée par
un ratissage exhaustif.

**Messages vides** — ponctuation des titres `EmptyState` standardisée :
`weekend_empty_title`/`dashboard_weekend_championships_empty`/
`search_no_results` perdent leur point final pour rejoindre la majorité
déjà sans point ; `weekend_next_hint`/`search_empty_query` (phrases
instructives avec un verbe conjugué) gardent le leur — distinction
grammaticale, pas esthétique (voir ADR-045).

**Textes — "À propos"** : `about_version` devient un gabarit
(`"Version {version} — Alpha"`) au lieu d'un texte statique sans
numéro ; `build_about_view()` gagne un paramètre `version: str | None =
None` qui importe `motorsport_calendar.__version__` quand omis (import
local, même convention que `controller.py`/`cli.py`) — cohérent avec le
Dashboard, qui affiche déjà cette même valeur depuis le Sprint 53.

**Doublons** : `nav_home`/`nav_calendar` (chaînes "gardées pour
compatibilité" mais jamais référencées) supprimées de `strings.py`.

**Points identifiés, documentés, non corrigés** (hors périmètre du
sprint, pas oubliés) :
- Résultats de "Recherche" non cliquables — corriger nécessiterait
  d'ajouter `championship_id`/`event_uid` à `SearchResultItem`, une
  évolution de service explicitement hors périmètre ("Aucune évolution
  des services").
- "À propos" n'utilise pas de `PageHeader` classique — exception
  assumée et documentée depuis le Sprint 28 (l'app+version sert de
  titre), revalidée plutôt que "corrigée" : la changer aurait été une
  régression de choix éditorial, pas une correction d'incohérence.

### Tests

- `tests/test_gui_strings.py` (+3 tests) —
  `test_dead_backward_compat_nav_strings_removed`,
  `test_empty_state_titles_never_end_with_a_period` (6 clés vérifiées),
  `test_about_version_carries_a_version_placeholder`.
- `tests/test_gui_views.py` (+4 tests) — `TestAboutView::
  test_default_version_is_the_real_package_version`/
  `test_version_override_is_shown` ; `TestFavoritesView::
  test_header_icon_matches_the_nav_rails_filled_star` ;
  `TestDashboardView::
  test_header_icon_matches_the_nav_rails_filled_dashboard_glyph`.

### Fichiers modifiés / créés

| Fichier | Action |
|---|---|
| `motorsport_calendar/gui/strings.py` | Modifié — ponctuation EmptyState, `about_version` en gabarit, `nav_home`/`nav_calendar` retirées |
| `motorsport_calendar/gui/views/favorites.py` | Modifié — icône d'en-tête |
| `motorsport_calendar/gui/views/dashboard.py` | Modifié — icône d'en-tête |
| `motorsport_calendar/gui/views/about.py` | Modifié — version réelle, espacement |
| `motorsport_calendar/gui/views/preferences.py` | Modifié — espacement |
| `motorsport_calendar/gui/views/search.py` | Modifié — espacement |
| `motorsport_calendar/gui/views/calendar.py` | Modifié — espacements (×3) |
| `motorsport_calendar/gui/main_view.py` | Modifié — boîte de dialogue succès (icône + espacement), boîte de dialogue mise à jour (espacement), commentaire "5 destinations" corrigé |
| `motorsport_calendar/gui/components/layout/empty_state.py` | Modifié — docstring (exemple à jour) |
| `tests/test_gui_strings.py` | Modifié — 3 tests ajoutés |
| `tests/test_gui_views.py` | Modifié — 4 tests ajoutés |
| `CHANGELOG.md` | Mis à jour |
| `docs/ROADMAP.md` | Mis à jour — v0.4.28 |
| `docs/AI_CONTEXT.md` | Mis à jour — entrée #54, 6 lignes de dette résolues, 1 nouvelle piste |
| `docs/TODO.md` | Mis à jour |
| `docs/DECISIONS.md` | ADR-045 ajouté |

Aucun service/provider/modèle modifié, aucune nouvelle page, aucune
nouvelle fonctionnalité — conforme au brief.

### Tests exécutés
```
1961 passed → 1968 passed — 0 failed
```

Ruff : 0 erreur sur l'ensemble du dépôt (inchangé). mypy
`motorsport_calendar/` : 39 → 39 (inchangé — chaque correction est
visuelle/textuelle, aucune ne touche une signature de callback). mypy
`tests/` : 157 → 157 (inchangé).

`git status --short` confirmé en fin de session : **aucun commit
effectué**, conforme à la clôture de sprint demandée.

### Limites
- **Aucune vérification visuelle réelle** des corrections — poste avec
  affichage indisponible dans cet environnement, comme chaque sprint GUI
  précédent ; les 7 nouveaux tests verrouillent la structure (bonne
  icône, bon texte, bonne absence de chaîne morte) mais jamais le rendu
  pixel.
- **L'audit s'est appuyé sur la lecture de code + recherche textuelle,
  jamais sur un usage réel de l'app** — un audit UX mené face à
  l'interface rendue (poste avec affichage) pourrait révéler des points
  invisibles à la seule lecture (densité, alignement, contraste),
  documenté comme piste `-18bis`... en réalité regroupé avec la piste
  générale de vérification visuelle déjà répétée à chaque sprint GUI.
- **Résultats de "Recherche" non cliquables restent en l'état** —
  identifié, documenté (ADR-045, piste `-18`), volontairement non
  corrigé car la correction franchirait la limite "aucune évolution des
  services" du brief.

---

## Session 2026-07-13 — Sprint 53 : Nouveautés & Centre d'accueil

### Objectif
Motorsport Calendar est désormais une Alpha fonctionnelle — le moteur de
mise à jour (Sprint 51) et les préférences (Sprint 52) sont opérationnels.
Objectif : transformer le Dashboard (déjà la page d'accueil de facto
depuis le Sprint 39) en véritable point d'entrée du produit, en
réutilisant exclusivement les services déjà construits (`Dashboard`,
`UpdateService`, `FavoritesService`, `ProviderRegistry`), sans créer de
logique métier dans la vue, sans nouveau provider, sans évolution des
modèles métier. Trois nouvelles sections : "Nouveautés" (affiche
`UpdateService` s'il y a une mise à jour, rien sinon), "Accès rapides"
(navigation directe vers Ce week-end/Mon calendrier/Recherche/Favoris),
"État de Motorsport Calendar" (version, championnats actifs, fournisseurs
réellement fonctionnels, favoris — jamais de valeur codée en dur).

### Audit rapide (préalable, demandé par le brief)
- Tests : 1932 passants, 0 échouant.
- Couverture : ~97 %.
- Dette Ruff : 0 erreur.
- Dette mypy `motorsport_calendar/` : 38 erreurs (une seule famille
  documentée depuis le Sprint 26 — décalage stubs Flet 0.80/runtime
  0.85.3 ; voir ci-dessous pour le delta apporté par ce sprint).
- Dette mypy `tests/` : 157 erreurs (inchangée après ce sprint).
- `git status --short` : 177 chemins modifiés (dette héritée des sprints
  précédents, jamais commitée), aucun commit tenté ce sprint non plus,
  conforme à la contrainte du brief.

### Exploration préalable
Relecture de `gui/views/dashboard.py` (Sprint 39 : 3 états exacts —
chargement/pas de données/chargé — stats saison + "Ce week-end" +
"Prochain départ", zéro logique métier déjà) et de `gui/dashboard.py::
build_dashboard_data()` (module "compute" pur, sans Flet, séparé de
`controller.get_dashboard_data()` qui fait le fetch). Relecture de
`gui/update_service.py::UpdateCheckResult`/`UpdateManifest` (Sprint 51 :
`update_available`/`manifest`/`current_version`, jamais de raise) et de
`main_view.py::_show_update_dialog` (le bouton "Voir la version" existant
— fermeture inline `url_launcher.launch_url` + repli `subprocess.Popen`
en cas d'échec sur certaines plateformes). Relecture de
`FavoritesService.list()` et de `ProviderRegistry.enabled(config.
providers)` (déjà utilisé par `cli.py::providers` pour lister les
fournisseurs actifs). Confirmation par lecture de code qu'aucune
métadonnée "provider fonctionnel" n'existe nulle part dans le projet —
décision de la dériver des `entries` déjà récupérées par
`controller._fetch_weekend_entries()` plutôt que d'inventer un nouveau
champ sur `Provider` (voir ADR-044).

### Travail effectué

**`gui/strings.py`** — nouveau bloc de chaînes pour les 3 sections
(titres `dashboard_section_news`/`dashboard_section_quick_access`/
`dashboard_section_status`, 4 labels de statistique). Réutilise sans
duplication `update_new_version`/`update_view_btn` (Sprint 51) et
`nav_weekend`/`nav_my_calendar`/`nav_search`/`nav_favorites` (existants)
pour les nouvelles sections plutôt que d'introduire des doublons.

**`gui/dashboard.py`** — `DashboardData` gagne 5 champs passthrough
(`active_championships`, `favorite_count`, `current_version`, `update`)
et 1 champ réellement calculé ici (`functional_providers` — championnats
distincts ayant produit au moins une entrée parmi celles déjà
récupérées pour les 2 années fetchées ; voir ADR-044 pour le
raisonnement complet). `build_dashboard_data()` accepte les 4 valeurs
passthrough en paramètres nommés avec défauts, cohérent avec la
convention déjà établie par `favorite_ids`/`total_championships`.

**`gui/controller.py::get_dashboard_data()`** — récupère désormais les
entrées week-end (`_fetch_weekend_entries`) et la vérification de mise à
jour (`check_for_update`) en concurrence via `asyncio.gather()` (même
patron que les fetches provider concurrents du Sprint 50), résout
`active_championships = len(registry.enabled(ConfigService().providers))`
et transmet `favorite_count=len(favorite_ids)`,
`current_version=motorsport_calendar.__version__`.

**`gui/main_view.py`** — la fermeture inline de `_show_update_dialog`
extraite en fabrique nommée `_make_release_opener(url) ->
Callable[[ft.ControlEvent], Awaitable[None]]`, appelée par la boîte de
dialogue de démarrage ET par le chargement du Dashboard — une seule
implémentation de "ouvrir une URL de release", jamais dupliquée (voir
ADR-044). Nouvelle table `_quick_access_nav_index: dict[str, int]`
(clé → index `NavigationRail`) et fonction `_navigate_to(key)` qui met
à jour `nav_rail.selected_index`/`content_area.content`/`page.update()`
— seul endroit du projet qui connaît cette correspondance, la vue
Dashboard ne manipule jamais `NavigationRail` directement.
`_load_dashboard()` construit `on_view_release` conditionnellement (à
partir de `result.update.manifest.url` si présent) et passe
`on_navigate=_navigate_to` à `build_dashboard_view`.

**`gui/views/dashboard.py`** (réécrit) — `_news_section()` (nouveau,
seule fonction de section du Dashboard à pouvoir renvoyer `None` — voir
ADR-044), `_quick_access_section()` (4 `theme.card()`, chacune avec
`on_click = lambda e, k=key: on_navigate(k)`), `_status_section()`
(réutilise `_stat_card()` du Sprint 39 tel quel pour les 4 nouvelles
statistiques). `_loaded_state()` inclut toujours "Accès rapides" et
"État", "Nouveautés" seulement quand `_news_section()` ne renvoie pas
`None`.

### Tests

- `tests/test_gui_dashboard.py` (+12 tests) — `TestBuildDashboardData
  StatusFields` (passthrough/défauts des 4 nouveaux champs, y compris un
  test avec un vrai `UpdateManifest`) et `TestBuildDashboardData
  FunctionalProviders` (zéro si vide, championnats distincts comptés une
  fois même présents sur les deux années fetchées, un stub qui ne
  contribue jamais n'est jamais compté).
- `tests/test_gui_views.py` (+17 tests, 3 nouvelles classes) —
  `TestDashboardViewNews` (section absente sur `update=None`/
  `update_available=False`/`manifest=None`, présente avec version+résumé
  +bouton quand une mise à jour existe, handler du bouton vérifié comme
  étant exactement l'objet passé — jamais une seconde implémentation),
  `TestDashboardViewQuickAccess` (4 cartes présentes, chaque clic appelle
  `on_navigate` avec la bonne clé), `TestDashboardViewStatus` (les 4
  statistiques affichent des valeurs distinctes correctement mappées,
  jamais de valeur codée en dur). `TestDashboardView._make_data` promu
  en fonction module-level `_make_dashboard_data()`, réutilisée par les
  3 nouvelles classes. 3 assertions de comptage de cartes bordées
  préexistantes recalculées (6 → 14 — +8 pour les 2 sections toujours
  présentes, indépendant des données week-end/prochain départ).

### Fichiers modifiés / créés

| Fichier | Action |
|---|---|
| `motorsport_calendar/gui/strings.py` | Modifié — nouvelles chaînes des 3 sections |
| `motorsport_calendar/gui/dashboard.py` | Modifié — `DashboardData` +5 champs, `functional_providers` calculé |
| `motorsport_calendar/gui/controller.py` | Modifié — `get_dashboard_data` concurrent, résout les nouveaux champs |
| `motorsport_calendar/gui/main_view.py` | Modifié — `_make_release_opener`, `_navigate_to`, câblage Dashboard |
| `motorsport_calendar/gui/views/dashboard.py` | Réécrit — 3 nouvelles sections |
| `tests/test_gui_dashboard.py` | Modifié — 2 nouvelles classes |
| `tests/test_gui_views.py` | Modifié — 3 nouvelles classes, helper promu module-level |
| `CHANGELOG.md` | Mis à jour |
| `docs/ROADMAP.md` | Mis à jour — v0.4.27 |
| `docs/AI_CONTEXT.md` | Mis à jour — entrée #53, dette mypy +1, nouvelles pistes |
| `docs/TODO.md` | Mis à jour |
| `docs/DECISIONS.md` | ADR-044 ajouté |

Aucun provider modifié, aucun nouveau service, aucune évolution des
modèles métier — conforme au brief.

### Tests exécutés
```
1932 passed → 1961 passed — 0 failed
```

Ruff : 0 erreur sur l'ensemble du dépôt. mypy `motorsport_calendar/` :
38 → 39 erreurs — la seule nouvelle est dans la même famille déjà
documentée et acceptée (décalage stubs Flet 0.80/runtime 0.85.3 : le
nouveau `ft.Button(on_click=on_view_release)` de la carte "Nouveautés"),
pas une nouvelle catégorie. mypy `tests/` : 157 → 157 (inchangé, les 3
nouvelles classes de test n'introduisent que des notes
`annotation-unchecked` déjà courantes sur les fonctions de test non
typées, aucune nouvelle erreur).

`git status --short` confirmé en fin de session : **aucun commit
effectué**, conforme à la clôture de sprint demandée.

### Limites
- **Aucune vérification visuelle réelle** des 3 nouvelles sections —
  structure des contrôles + 29 tests nets vérifiés, poste avec affichage
  indisponible dans cet environnement (même limitation que chaque sprint
  GUI précédent).
- **`config.update.manifest_url` reste vide par défaut** (Sprint 51,
  volontaire) — la carte "Nouveautés" est fonctionnelle et testée mais
  reste un no-op silencieux en usage réel tant qu'aucun manifeste n'est
  publié ; ce manque se voit désormais à deux endroits (boîte de dialogue
  de démarrage + carte Dashboard) au lieu d'un seul.
- **`functional_providers` est un proxy, pas une mesure directe** — un
  provider qui répond mais ne produit exceptionnellement aucun événement
  pour les 2 années fetchées (cas non observé en pratique) serait compté
  comme non-fonctionnel à tort ; jugé acceptable plutôt que d'inventer
  une nouvelle métadonnée de capacité provider (voir ADR-044).

---

## Session 2026-07-12 — Sprint 52 : Préférences avancées

### Objectif
Motorsport Calendar possède désormais plusieurs services configurables
(Notifications, Mises à jour, Favoris, Génération ICS) mais la page
Préférences reste un placeholder statique depuis le Sprint 26 — aucune
ligne n'est reliée à rien de réel. Objectif : transformer cette page en
véritable centre de configuration, en réutilisant exclusivement les
services déjà construits (`FavoritesService`, `NotificationService`,
`UpdateService`), sans créer de logique métier dans la vue, et sans la
moindre évolution du Design System/Layout System/Components. La page doit
permettre de configurer : Notifications (activées/désactivées, favoris
uniquement, délai par défaut), Mises à jour (activer/désactiver la
vérification), Calendrier (année par défaut, rappel avant export si
pertinent) ; et préparer (sans forcément implémenter) : thème, langue,
format horaire.

### Audit rapide (préalable, demandé par le brief)
- Tests : 1923 passants, 0 échouant.
- Couverture : ~97 %.
- Dette Ruff : 0 erreur.
- Dette mypy `motorsport_calendar/` : 38 erreurs (une seule famille
  documentée depuis le Sprint 26 — décalage stubs Flet 0.80/runtime
  0.85.3 ; voir ci-dessous pour le delta apporté par ce sprint).
- Dette mypy `tests/` : 157 erreurs (inchangée après ce sprint).
- `git status --short` : 176 chemins modifiés, aucun commit.

### Exploration préalable
Relecture de `gui/views/preferences.py` (placeholder intégral, 6 rows
"Disponible prochainement" pointant vers un `PreferencesModel` jamais
lié à rien) et de `gui/models.py::PreferencesModel` (frozen dataclass
décorative depuis l'origine — `docs/AI_CONTEXT.md` documentait déjà
`favorite_championships` comme "superseded" par `FavoritesService`
depuis le Sprint 44, jamais nettoyé). Relecture complète de
`NotificationService` (Sprint 46 : `enabled`/`favorites_only`/
`default_lead_time`, chacun avec son `set_*`, déjà persistés dans
`gui/preferences.py` mais jamais exposés à une interface) et de
`gui/controller.py::check_for_update()` (Sprint 51 : lit déjà
`update_check_enabled` mais rien ne l'écrit). Comparaison des deux
patrons déjà établis pour une page interactive dans ce projet :
`views/favorites.py` (données pures + callables nommés) vs
`views/calendar.py::CalendarViewControls` (dataclass portant des
contrôles Flet déjà construits/câblés par main_view.py) — retenu le
second, plus direct pour 6 contrôles indépendants. Vérification par
introspection (`inspect.signature`) de la signature exacte de
`ft.Switch`/`ft.Dropdown` avant d'écrire le moindre handler — découverte
que `Dropdown` expose `on_select`, pas `on_change` (contrairement à
`Switch`), cohérent avec `year_dropdown` (Sprint 43) qui utilisait déjà
`on_select` sans que la raison n'ait jamais été explicitée jusqu'ici.

### Travail effectué

**`gui/preferences.py`** — deux nouvelles clés : `default_year` (défaut
`"current"`, une sentinelle plutôt qu'une année codée en dur — évite
qu'un défaut figé au moment de l'écriture du code devienne faux l'année
suivante) et `ics_alarm_minutes` (défaut `30`, identique à
`config.ics.alarm_minutes` pour un comportement inchangé tant que la page
n'est jamais ouverte). Docstring du module mis à jour avec le schéma
complet des deux nouvelles clés.

**`gui/models.py`** — nouveau `resolve_default_year(value, *,
current_year=None)` (pure, sans Flet) : décode `"current"` en
`date.today().year` à chaque appel (jamais figé), parse une valeur
littérale (`"2027"` → `2027`), retombe sur l'année courante pour toute
valeur corrompue sans jamais lever — une préférence hand-editée ne doit
jamais faire planter le démarrage de "Mon calendrier". `PreferencesModel`
repensé : les 6 champs hérités (`timezone`/`first_day_of_week`/
`favorite_championships`/`preferred_calendar`/`bapps_sync_enabled`, tous
décoratifs) retirés au profit des 3 seuls champs nommés par le brief pour
la section "Application" (`theme`/`language`/`time_format`) — repurposé
plutôt que supprimé, "ces préférences doivent être pensées pour évoluer"
justifie un modèle typé prêt, même inerte.

**`gui/controller.py::generate_calendar()`** — l'export ICS lit désormais
`load_preferences().get("ics_alarm_minutes", config.ics.alarm_minutes)`
avant de construire `IcsExporter` — repli sur la config si la préférence
n'a jamais été enregistrée. `cli.py::generate` volontairement inchangé :
la CLI n'a pas de fichier de préférences GUI, continue de ne lire que
`config.yaml`.

**`gui/strings.py`** — nouvelles chaînes pour les 4 sections (titres,
labels de contrôle, options de durée partagées entre le délai de
notification et le rappel d'export) ; 5 anciennes chaînes decoratives
(`prefs_timezone`/`prefs_first_day`/`prefs_favorites`/
`prefs_preferred_calendar`/`prefs_bapps_sync`) retirées avec les champs
`PreferencesModel` qu'elles décrivaient.

**`gui/views/preferences.py`** (réécriture complète) — nouveau
`PreferencesViewControls` (dataclass, patron `CalendarViewControls`) :
porte les 2 `ft.Switch`/3 `ft.Dropdown` déjà construits et câblés par
main_view.py, plus `favorite_count`/`application` (données pures). Deux
row-builders : `_control_row` (nouveau — icône, label, contrôle réel,
hint optionnel) pour les 6 réglages fonctionnels, `_pref_row` (inchangé
depuis le Sprint 31) pour les 3 rows "Disponible prochainement" de la
section Application. 4 `Section`/`SectionHeader` (patron déjà établi par
`search.py`) : Notifications, Mises à jour, Calendrier, Application.
Zéro logique métier — aucun `load_preferences()`, aucun service
construit dans ce module.

**`main_view.py`** — `notification_service = NotificationService()`
construit aux côtés de `favorites_service`/`search_service`/
`circuit_service`. Nouveau bloc "PRÉFÉRENCES PAGE" : 3 listes d'options
(délai de notification 15min-24h, rappel d'export 0-1h, année par
défaut — sentinelle + plage de `current_year - 5` à `current_year + 5`,
même convention que `year_dropdown`), `preferences_container`
(`ft.Container` mutable, même patron que `favorites_container`/
`weekend_container`), 6 handlers `_on_*_change` (3 délèguent à
`notification_service.set_*`, 3 lisent/écrivent directement
`load_preferences()`/`save_preferences()` — pas de service dédié pour ces
3 clés à une seule valeur, cf. ADR-043), `_build_preferences_controls()`
qui construit les 6 contrôles frais à chaque rafraîchissement (même
"reconstruire entièrement, jamais de mutation partielle" que
`_current_favorites_groups()`). `state = GenerateState(year=...)` seedé
via `resolve_default_year(prefs.get("default_year", DEFAULT_YEAR_SENTINEL))`
au lieu de `date.today().year` en dur. `all_views` : `preferences_container`
remplace l'appel direct `build_preferences_view(prefs_model)`.

### Tests

- `tests/test_gui_preferences_model.py` (réécriture complète, 15 tests) —
  mêmes classes (`Defaults`/`Frozen`/`CustomValues`/`Equality`/`Types`),
  nouveaux champs `theme`/`language`/`time_format`.
- `tests/test_gui_models.py` (+7 tests, `TestResolveDefaultYear`) —
  sentinelle, année littérale, valeur corrompue, override explicite de
  `current_year` pour chaque cas (déterministe, jamais dépendant de la
  date réelle du jour du test run sauf pour les 2 tests qui vérifient
  explicitement le comportement par défaut).
- `tests/test_gui_preferences.py` (+4 tests) — défauts `default_year`/
  `ics_alarm_minutes` au premier lancement, préservation aux côtés des
  autres clés (même patron que les tests `update_check_enabled` du
  Sprint 51).
- `tests/test_gui_controller.py` (+3 tests, `TestGenerateCalendarIcsAlarmMinutes`)
  — défaut (`TRIGGER:-PT30M`), override (`TRIGGER:-PT15M`, absence de
  l'ancien), désactivation totale (`ics_alarm_minutes=0` → aucun
  `BEGIN:VALARM`) — vérifiés sur le contenu réel du fichier `.ics`
  produit, pas seulement sur un paramètre interne.
- `tests/test_gui_views.py` (`TestPreferencesView` réécrite, 11 tests ;
  `TestAllViewsShareTheSameGrid._all_views()` adaptée) — compte de cartes
  bordées recalculé (6 lignes de contrôle réel = 1 carte chacune ; 3
  lignes Application = 2 cartes chacune, row + puce, comme avant) ;
  nouveau test vérifiant que les objets `Switch`/`Dropdown` passés sont
  bien les mêmes rendus (jamais reconstruits, ce qui perdrait leur
  câblage). Deux helpers de test mutualisés ajoutés au niveau module
  (`_flatten_controls`, `_collect_all_text`) — ce dernier remplace une
  fonction locale dupliquée dans `TestAboutView::
  test_app_title_and_version_shown_once`, un ménage mineur fait en
  passant plutôt qu'une troisième copie.

### Fichiers modifiés / créés

| Fichier | Action |
|---|---|
| `motorsport_calendar/gui/preferences.py` | Modifié — `default_year`, `ics_alarm_minutes` |
| `motorsport_calendar/gui/models.py` | Modifié — `resolve_default_year`, `PreferencesModel` repensé |
| `motorsport_calendar/gui/controller.py` | Modifié — `generate_calendar` lit `ics_alarm_minutes` |
| `motorsport_calendar/gui/strings.py` | Modifié — nouvelles chaînes, anciennes retirées |
| `motorsport_calendar/gui/views/preferences.py` | Réécrit — centre de configuration réel |
| `motorsport_calendar/gui/main_view.py` | Modifié — câblage complet de la page |
| `tests/test_gui_preferences_model.py` | Réécrit |
| `tests/test_gui_models.py` | Modifié — `TestResolveDefaultYear` ajoutée |
| `tests/test_gui_preferences.py` | Modifié — 4 tests ajoutés |
| `tests/test_gui_controller.py` | Modifié — 3 tests ajoutés |
| `tests/test_gui_views.py` | Modifié — `TestPreferencesView` réécrite, helpers mutualisés |
| `CHANGELOG.md` | Mis à jour |
| `docs/ROADMAP.md` | Mis à jour — v0.4.26 |
| `docs/AI_CONTEXT.md` | Mis à jour — 3 lignes de dette résolues |
| `docs/TODO.md` | Mis à jour |
| `docs/DECISIONS.md` | ADR-043 ajouté |

Aucun provider modifié, aucune nouvelle page — conforme au brief.

### Tests exécutés
```
1923 passed → 1932 passed — 0 failed
```

Couverture : `gui/models.py`, `gui/preferences.py`, `gui/views/
preferences.py` à 100 % ; `gui/controller.py` à 96 % (lignes manquantes
toutes pré-existantes, hors du nouveau code). Ruff : 0 erreur sur
l'ensemble du dépôt. mypy `motorsport_calendar/` : 26 → 38 erreurs — les
12 nouvelles sont dans la même famille déjà documentée et acceptée
(décalage stubs Flet 0.80/runtime 0.85.3 : les 2 `Switch`/3 `Dropdown` de
la nouvelle page, chacun à son site d'appel), pas une nouvelle catégorie.
mypy `tests/` : 157 → 157 (inchangé). `main_view.py` vérifié important
sans erreur avec `flet` réellement installé
(`python -c "import motorsport_calendar.gui.main_view"`).

`git status --short` confirmé en fin de session : **aucun commit
effectué**, conforme à la clôture de sprint demandée.

### Limites
- **Section "Application" reste inerte** — `theme`/`language`/
  `time_format` affichés "Disponible prochainement", aucune persistance
  ni lecture ailleurs dans l'app ; conforme au brief ("préparer, sans
  forcément implémenter").
- **Aucune vérification visuelle réelle** de la nouvelle page — premier
  usage de `ft.Switch`/plusieurs `ft.Dropdown` simultanés dans ce projet,
  structure vérifiée par les tests uniquement, poste avec affichage
  indisponible dans cet environnement (même limitation que chaque sprint
  GUI précédent).
- **`ics_alarm_minutes`/`default_year` n'ont pas de validation de bornes**
  au-delà des options offertes par leurs Dropdowns respectifs — non
  nécessaire aujourd'hui puisque ces clés ne peuvent être écrites que via
  la page elle-même, mais une préférence corrompue à la main resterait
  affichée sans option correspondante sélectionnée dans le Dropdown
  (`resolve_default_year` gère ce cas pour `default_year` spécifiquement
  en tombant sur l'année courante ; `ics_alarm_minutes` n'a pas
  d'équivalent).

---

## Session 2026-07-12 — Sprint 51 : Vérification des mises à jour

### Objectif
Motorsport Calendar est désormais une Alpha distribuable (Sprint 49). Les
utilisateurs doivent être informés lorsqu'une nouvelle version est
disponible — sans aucune mise à jour automatique, aucun téléchargement
automatique, aucune évolution des providers. Objectif : créer un système
léger de vérification des mises à jour, entièrement contenu dans un
nouveau `gui/update_service.py` totalement indépendant de Flet, capable de
récupérer un manifeste JSON distant, comparer les versions
numériquement (jamais lexicographiquement), déterminer si une mise à jour
est disponible, et retourner les informations à afficher. Interface :
au démarrage, si une version plus récente existe, afficher une boîte de
dialogue (version actuelle, nouvelle version, résumé, bouton "Voir la
version" ouvrant l'URL officielle). Contraintes explicites : ne pas
coupler la logique à GitHub, le manifeste doit pouvoir provenir de
n'importe quelle URL, prévoir la possibilité d'ignorer la vérification
(préférence future).

### Exploration préalable
Relecture des services GUI existants sans dépendance Flet
(`gui/favorites_service.py`, `gui/notification_service.py`,
`gui/search_service.py`) — le patron à suivre : classe simple, aucun
`import flet`, préférences lues/écrites via `gui/preferences.py`
(read-modify-write sur le fichier partagé), jamais d'état global caché
(paramètres explicites plutôt que lecture directe de l'horloge/du réseau
en interne). Relecture de `config/models.py`/`config/service.py`
(patron `XConfig` + propriété sur `ConfigService`, déjà utilisé pour
`CacheConfig`/`IcsConfig`/`ProvidersConfig`) comme mécanisme naturel pour
une URL configurable sans rien coder en dur. Relecture de
`gui/controller.py` (façade réseau de la GUI, aucune logique métier
propre — `generate_calendar`/`get_dashboard_data` déjà de bons patrons à
suivre) et de `main_view.py` (patron des boîtes de dialogue —
`_show_success_dialog` — et des tâches de fond au démarrage —
`page.weekend_load_task`/`page.dashboard_load_task`). Relecture de
`views/about.py::on_github_click` pour le patron d'ouverture d'URL
(`url_launcher.launch_url`, repli `subprocess.Popen` sous Windows en cas
d'échec).

### Travail effectué

**`config/models.py::UpdateConfig`** (nouveau) — `manifest_url: str = ""`,
frozen comme les autres sections de config. Ajouté à `AppConfig.update`.
`config/service.py::ConfigService.update` (nouvelle propriété) et
`config/__init__.py` (export) suivent exactement le patron déjà établi.
Décision explicite : aucune URL par défaut, même "neutre" en apparence —
la vérification reste un no-op silencieux tant que l'utilisateur n'a pas
renseigné une URL réelle dans `config.yaml`.

**`gui/preferences.py`** — nouvelle clé `update_check_enabled` (défaut
`True`, opt-out) ajoutée à `_DEFAULTS` et documentée dans le docstring du
module, même statut "fondations, aucune UI ne l'expose encore" que les
préférences de notifications (Sprint 46).

**`gui/update_service.py`** (nouveau, cœur du sprint) —
- `UpdateManifest` (dataclass frozen) : `version`, `release_date`,
  `title`, `summary`, `url`, `mandatory` (défaut `False`) — noms de champs
  identiques 1:1 au JSON du brief.
- `UpdateCheckResult` (dataclass frozen) : `update_available`,
  `current_version`, `manifest: UpdateManifest | None`,
  `error: str | None` — tout ce que `main_view.py` a besoin d'afficher,
  jamais le manifeste brut ni une exception.
- `parse_version(s) -> tuple[int, ...]` : parse une version pointée en
  tuple d'entiers, lève `ValueError` sur toute chaîne non conforme.
- `is_newer(current, candidate) -> bool` : compare les tuples parsés,
  jamais les chaînes — le piège nommé par le brief
  (`"0.4.9" > "0.4.10"` en comparaison lexicographique) vérifié en direct
  dans un test comme sanity-check, pas seulement affirmé dans un
  commentaire. Complète les tuples de longueurs différentes à zéro avant
  de comparer — un second piège découvert en réfléchissant à la
  comparaison de tuples Python natifs (`(0, 5) < (0, 5, 0)` nativement,
  aurait rendu `"0.5.0"` faussement plus récente que `"0.5"` sans ce
  complément).
- `_parse_manifest(data) -> UpdateManifest` : valide que `data` est un
  objet JSON et que les 5 champs requis (tout sauf `mandatory`) sont
  présents, lève `ValueError` avec la liste des champs manquants sinon.
- `UpdateService(manifest_url, current_version, *, client=None,
  timeout=5.0)` : `manifest_url`/`current_version` entièrement fournis
  par l'appelant, jamais lus en interne (même discipline que `now` dans
  `NotificationService.compute_notifications`) — le module n'a aucune
  connaissance de GitHub ni d'aucun hébergeur. `check_for_update()` ne
  lève jamais : URL vide, erreur réseau/HTTP (`httpx.HTTPError`), JSON
  invalide, manifeste incomplet, version illisible sont tous capturés et
  renvoyés via `UpdateCheckResult.error`. `client: httpx.AsyncClient |
  None` injectable pour les tests, même patron que les sources de
  providers (`OpenF1Source`, etc.).

**`gui/controller.py::check_for_update()`** (nouveau) — résout
`current_version` (`motorsport_calendar.__version__` par défaut) et
`manifest_url` (`ConfigService().update.manifest_url` par défaut),
respecte `update_check_enabled` (court-circuite avant tout appel réseau
si désactivé), puis délègue entièrement à `UpdateService`. Accepte des
overrides explicites (`current_version=`/`manifest_url=`) réservés aux
tests, même patron que `now: datetime | None = None` déjà utilisé par
`get_upcoming_weekend`/`get_dashboard_data`. Toute la logique métier
reste dans `update_service.py` — ce wrapper ne fait que la câbler à la
config/aux préférences, conformément à la consigne explicite du brief
("toute la logique doit rester dans ce service, la vue ne fait
qu'afficher le résultat").

**`main_view.py`** — `_show_update_dialog(result)` (nouvelle fonction,
même patron que `_show_success_dialog`) affiche titre, version
actuelle/nouvelle version, résumé, et un bouton "Voir la version"
(`url_launcher.launch_url`, repli `subprocess.Popen` Windows en cas
d'échec, même code que `views/about.py::on_github_click`) ; le champ
`mandatory` du manifeste est surfacé comme un simple badge textuel,
jamais comme un blocage du bouton Fermer — inventer un comportement
"forcé" à partir de ce champ aurait été une forme d'installation imposée
non demandée. `_check_for_update()` (nouvelle tâche de fond) suit
exactement le patron `_load_weekend`/`_load_dashboard` — lancée une fois
au démarrage (`page.update_check_task = asyncio.create_task(...)`),
n'affiche la boîte de dialogue que si `update_available` et un manifeste
sont bien présents, ne fait jamais planter le démarrage (son propre
`except Exception` n'est qu'un filet de sécurité, `UpdateService`
lui-même ne lève déjà jamais).

### Tests
- `tests/test_update_service.py` (nouveau, 45 tests) : `parse_version`
  (formats valides/invalides), `is_newer` (même version, bump patch —
  piège lexicographique explicitement vérifié —, bump mineur, bump
  majeur, version plus ancienne, complément à zéro pour longueurs
  différentes, versions invalides), `_parse_manifest` (manifeste valide,
  `mandatory` absent/présent, pas un objet JSON, champ(s) manquant(s)),
  `UpdateService.check_for_update` via `httpx.MockTransport` (jamais de
  vrai appel réseau) : mise à jour disponible (patch/mineure/majeure),
  `mandatory` transmis correctement, même version (aucune mise à jour),
  version courante en avance sur le manifeste (aucune mise à jour),
  manifeste invalide/incomplet, JSON malformé, version illisible,
  absence de réseau (`httpx.ConnectError`), timeout, erreurs HTTP
  404/500, aucune URL configurée, construction d'un client propre quand
  aucun n'est injecté, et un test explicite garantissant que
  `check_for_update()` ne lève jamais. Plus une classe
  `TestNoFletDependency` : vérifie par inspection de source qu'aucun
  `import flet` n'apparaît dans le module — le contrat d'indépendance du
  brief, vérifié, pas seulement documenté.
- `tests/test_config_service.py` (+7 tests) : défauts `UpdateConfig`,
  immutabilité (frozen), lecture depuis `config.yaml`, propriété
  `ConfigService.update`.
- `tests/test_gui_preferences.py` (+2 tests) : défaut `update_check_enabled
  = True` au premier lancement, préservation aux côtés des autres clés.
- `tests/test_gui_controller.py` (+5 tests) : URL vide court-circuite
  sans réseau, préférence désactivée court-circuite avant toute
  résolution d'URL (prouvé en patchant `UpdateService.check_for_update`
  pour lever une `AssertionError` s'il est appelé), délégation correcte à
  `UpdateService` quand tout est activé, résolution par défaut de
  `current_version`/`manifest_url` depuis `__version__`/`ConfigService`.

### Fichiers modifiés / créés

| Fichier | Action |
|---|---|
| `motorsport_calendar/gui/update_service.py` | Créé |
| `motorsport_calendar/config/models.py` | Modifié — `UpdateConfig` |
| `motorsport_calendar/config/service.py` | Modifié — propriété `update` |
| `motorsport_calendar/config/__init__.py` | Modifié — export `UpdateConfig` |
| `motorsport_calendar/gui/preferences.py` | Modifié — `update_check_enabled` |
| `motorsport_calendar/gui/controller.py` | Modifié — `check_for_update()` |
| `motorsport_calendar/gui/strings.py` | Modifié — chaînes de la boîte de dialogue |
| `motorsport_calendar/gui/main_view.py` | Modifié — dialogue + tâche de démarrage |
| `tests/test_update_service.py` | Créé — 45 tests |
| `tests/test_config_service.py` | Modifié — 7 tests ajoutés |
| `tests/test_gui_preferences.py` | Modifié — 2 tests ajoutés |
| `tests/test_gui_controller.py` | Modifié — 5 tests ajoutés |
| `CHANGELOG.md` | Mis à jour |
| `docs/ROADMAP.md` | Mis à jour — v0.4.25 |
| `docs/AI_CONTEXT.md` | Mis à jour |
| `docs/TODO.md` | Mis à jour |
| `docs/DECISIONS.md` | ADR-042 ajouté |

Aucun provider créé ou modifié — conforme à "aucune évolution des
providers" du brief.

### Tests exécutés
```
1865 passed → 1923 passed — 0 failed
```

Coverage : `gui/update_service.py` à 100 % (44 tests dédiés couvrant
chaque branche de `check_for_update`/`is_newer`/`_parse_manifest`).
`gui/controller.py` à 96 % (lignes manquantes toutes pré-existantes,
hors du nouveau `check_for_update()`). Ruff : 0 erreur sur l'ensemble du
dépôt après le sprint. mypy `motorsport_calendar/` : 23 → 26 erreurs — les
3 nouvelles sont dans la même famille déjà documentée et acceptée
(décalage stubs Flet 0.80/runtime 0.85.3 : `page.update_check_task` et
les deux boutons de la nouvelle boîte de dialogue), pas une nouvelle
catégorie de dette. mypy `tests/` : 157 → 157 (aucun nouveau fichier de
test n'a introduit de dette — un stale `# type: ignore` retiré dans
`test_config_service.py`, compensé). `main_view.py` vérifié important
sans erreur avec `flet` réellement installé dans l'environnement
(`python -c "import motorsport_calendar.gui.main_view"`).

`git status --short` confirmé en fin de session : **aucun commit
effectué**, conforme à la clôture de sprint demandée.

### Limites
- **Aucun manifeste réel n'est publié** — `config.update.manifest_url`
  reste vide par défaut ; la fonctionnalité est fonctionnelle et
  entièrement testée mais un no-op silencieux en usage réel tant que
  personne n'héberge un `manifest.json` et n'en renseigne l'URL dans
  `config.yaml`. Documenté comme piste `docs/TODO.md`, pas un défaut de
  ce sprint.
- **Aucune UI pour `update_check_enabled`** — la préférence existe et est
  lue mais rien ne permet à l'utilisateur de la changer depuis
  l'application ; même statut "fondations, pas d'interface" que les
  préférences de notifications au Sprint 46.
- **Aucune vérification visuelle réelle** de la boîte de dialogue — même
  limitation que chaque sprint GUI précédent, poste avec affichage
  indisponible dans cet environnement.

---

## Session 2026-07-12 — Sprint 50 : Audit & Consolidation

### Objectif
Motorsport Calendar a traversé 49 sprints de développement fonctionnel sans
jamais s'arrêter pour consolider. Ce sprint est explicitement non-fonctionnel :
aucune nouvelle fonctionnalité, aucun nouveau provider, aucune nouvelle page,
aucune évolution graphique. Objectif : réaliser un audit complet du projet
(duplications, fonctions/classes trop volumineuses, responsabilités mal
réparties, code mort, imports inutiles, constantes dupliquées, commentaires
obsolètes, TODO oubliés), vérifier les docstrings de toutes les fonctions
publiques, revoir la cohérence architecturale, réduire au maximum la dette
Ruff/mypy/duplication/complexité, nettoyer les tests (dédoublonnage,
factorisation de fixtures), identifier et appliquer les optimisations de
performance mesurables, produire un rapport d'audit complet
(`docs/AUDIT.md`) — le tout sans changer une seule ligne de comportement
utilisateur observable.

### Exploration préalable — établir une baseline fiable
Avant toute modification : `git stash` temporaire vers le dernier commit réel
(`3e8af0a`, plusieurs sprints en arrière — rien n'a été commité depuis) pour
mesurer la dette réellement pré-existante au projet, distincte de toute dette
qu'un sprint précédent aurait pu introduire sans jamais relancer un scan
complet. Résultat : 149 erreurs Ruff, 87 erreurs mypy sur
`motorsport_calendar/` (hors `gui/build/`, artefacts du build Flet Sprint 49
qui empêchaient purement et simplement mypy de s'exécuter — jamais exclus
jusqu'ici), 402 erreurs mypy sur `tests/`, 0 TODO/FIXME/XXX dans le code
source, 1863 tests passants à 97 % de couverture. `git stash pop` restaure
immédiatement l'état de travail avant de commencer.

### Travail effectué

**Ruff — 149 → 0 erreur.** Moitié corrigée mécaniquement
(`ruff check --fix`, imports non triés/inutilisés, `noqa` obsolètes,
`datetime.timezone.utc` → `datetime.UTC`). Reste revu un par un : 4
`pytest.raises(Exception)` sur des mutations de modèles Pydantic frozen
narrowés en `pydantic.ValidationError` (vérifié en direct via un script
Python que c'est bien l'exception réellement levée à l'exécution, jamais
supposé) ; 6 `lambda` assignées à un nom converties en `def` (2 fichiers de
tests registry) ; 5 `raise typer.Exit(...)` dans `cli.py` gagnent un
`from exc` pour préserver la chaîne d'exception à des fins de débogage ;
`gui/categories.py::Category(str, Enum)` aligné sur `enum.StrEnum` (déjà la
convention de `SessionType`/`EventStatus`/`ChampionshipCategory`, vérifié
avant de changer) ; `core/datasource/base.py::DataSource` (ABC marqueur
délibérément sans méthode abstraite) reçoit un `noqa` documenté plutôt
qu'une fausse méthode abstraite inventée pour satisfaire le linter ; deux
lignes de commentaire avec un caractère unicode ambigu (`×`, `ℹ`)
normalisées en ASCII.

**mypy `motorsport_calendar/` — 87 → 23 erreurs.** Signatures `dict`/`list`
sans paramètres génériques remplacées par `dict[str, Any]`/`list[Any]` dans
`cache/http_cache.py`, `cli.py`, `config/models.py`, `config/service.py`,
`core/datasource/json_source.py`, `providers/formula1/sources/{openf1,
jolpica}.py`, `providers/support_series/f1calendar_base.py`,
`providers/motogp_series/pulselive_base.py`,
`providers/formula2/sources/f1calendar.py`, `gui/preferences.py`,
`gui/strings.py`, `gui/controller.py`. Un cas non-mécanique dans
`jolpica.py::_get_json` : l'union `list[Any] | dict[str, Any]` héritée du
typage de `HttpCache.get_json` ne correspondait plus au comportement réel
de l'API Jolpica (jamais une liste à cet endpoint) — résolu par un
`cast(dict[str, Any], raw)` documentant explicitement cette connaissance
métier plutôt que de complexifier la fonction avec une vérification
d'exécution inutile. Deux packages de stubs manquants ajoutés aux
dépendances dev (`types-PyYAML`, `types-icalendar`, installés et vérifiés
dans le venv) plutôt que des suppressions locales — élimine 5 erreurs
d'un coup dans `config/service.py` et `exporters/ics.py`.

**Bug réel détecté et corrigé — `core/service.py::CalendarService`.**
`export_championship` passait un `Championship` entier à `Exporter.export()`
qui attend une liste d'`Event` — confusion entre métadonnées de championnat
et événements à exporter. Recherche exhaustive confirmant que cette classe,
bien qu'exportée depuis `core/__init__.py`, n'est appelée par **aucun** code
réel (ni `cli.py`, ni `gui/controller.py`) — coverage à 0 % sur le corps de
la méthode avant correction. Corrigée pour de bon : récupère désormais
réellement les événements via `provider.fetch_events(...)` avant de les
exporter. Zéro risque (rien n'exécute ce chemin en pratique) mais laisser un
bug connu dans le code source, même mort, contredirait l'objectif du sprint.
La classe reste volontairement non câblée nulle part (aucun brief ne l'a
demandé) — décision documentée dans `docs/TODO.md`/ADR-041.

**mypy `tests/` — 402 → 157 erreurs.** Diagnostic : la quasi-totalité des
402 erreurs provenait d'un seul phénomène — `unittest.mock.AsyncMock`
substitué à des attributs typés précisément, puis interrogé via
`mock.assert_awaited_once_with(...)` ou similaire, que mypy ne peut pas
résoudre statiquement bien que ce soit parfaitement valide à l'exécution
(confirmé : les 1863 tests passaient déjà tous avant tout changement).
`mypy.ini` (`[mypy-tests.*]`) ne relâchait jusqu'ici que
`disallow_untyped_defs`/`disallow_any_generics` — étendu à
`disallow_untyped_calls`/`check_untyped_defs`/`warn_return_any`, désactivés
pour les tests uniquement (pratique standard pour du code
`unittest.mock`-intensif), **`motorsport_calendar/` reste `strict = True`
intégral, aucune exception**. Effet : 402 → 210 sans modifier un seul
fichier de test. Complété par la suppression mécanique de 24
`# type: ignore` devenus inutiles (24 emplacements identifiés via mypy
lui-même, `unused-ignore`, retirés par script puis chaque suppression
reconfirmée par un nouveau passage mypy) et par une factorisation ciblée de
`test_aco_sports_event_base.py::TestSessionTypeForLabel` — 14 occurrences
du même pattern `_session_type_for_label(label)[0]` non-narrowed (14 erreurs
`[index]`, "tuple | None is not indexable") remplacées par un helper
`_type_for(label)` qui fait `assert result is not None` une seule fois —
double bénéfice, dette mypy ET duplication de test réduites par le même
changement. Compte final : 157, tous documentés dans `docs/AUDIT.md` §4
(deux familles : écho de la dette Flet stub-version dans les tests qui
construisent des contrôles, et bruit résiduel `unittest.mock` sans plugin
mypy dédié — aucune ne recouvre un vrai bug de test).

**Code mort — audité, quasiment rien trouvé.** `vulture` installé pour cet
audit (absent du projet jusqu'ici) : à 80 % de confiance, un seul résultat
(`cli.py:31`, faux positif — un paramètre Typer lu par introspection via
son `callback=`). À 60 % de confiance, dizaines de résultats mais tous des
faux positifs structurels attendus (enums comparés jamais "appelés",
attributs Pydantic/dataclass, attributs de contrôles Flet lus par le
framework) — confirmant qu'il n'y a pas de code mort caché. Un candidat
propre trouvé indépendamment via un script AST maison (classes publiques
référencées ≤ 2 fois dans tout le projet) : `gui/theme.py::BAppsColors`
(palette "écosystème BApps" jamais consommée par aucun token sémantique) —
examinée et conservée volontairement, c'est une classe de
documentation-as-code (traçabilité de la provenance du Brand Set), pas un
oubli de câblage.

**Docstrings publiques — triage systématique, pas d'ajout aveugle.** Script
AST maison : 367 fonctions/classes publiques du paquet, 103 signalées sans
docstring au premier passage. Chaque cas vérifié individuellement contre
son ABC parente avant toute décision : 76 sont des redéfinitions triviales
d'une méthode déjà pleinement documentée (`Provider.name`,
`Formula1Source.get_season`, etc. — vérifié en lisant chaque ABC concernée,
`providers/base.py`, `providers/formula1/source.py`, etc.) — convention
Python standard, **volontairement non dupliquées** (respect direct de la
consigne projet "pas de commentaire qui répète ce que le nom dit déjà"). Les
21 vrais manques comblés : `config/service.py` (4 propriétés), 
`exporters/ics.py` (0 — également des overrides ABC, exclues après lecture
d'`exporters/base.py`), `gui/favorites_service.py::is_favorite` (1),
`gui/notification_service.py` (6 propriétés/méthodes),
`gui/search_service.py::SearchResults` (2 propriétés),
`gui/theme.py::Spacing/Radius/IconSize/FontSize` (4 classes, alignées sur
`Colors`/`MotorsportColors` juste au-dessus qui avaient déjà la leur).

**Architecture — vérifiée, non modifiée.** Détection d'imports circulaires
par parcours de graphe AST (DFS sur chaque module de `motorsport_calendar`,
136 modules scannés) : aucun trouvé. Dépendances runtime déclarées (9 :
`typer`, `rich`, `pydantic`, `icalendar`, `httpx`, `pyyaml`,
`beautifulsoup4`, `lxml`, `tzdata`) toutes confirmées réellement consommées,
y compris les deux "invisibles" (`lxml` comme moteur de `BeautifulSoup`,
jamais `import`é directement ; `tzdata` pour `zoneinfo` sous Windows). 9
tables `_CIRCUIT_DATA` dupliquées entre providers (une par source de
données) examinées et volontairement non fusionnées — espaces de clés
différents par convention de chaque source, une fusion introduirait un
couplage artificiel entre des providers qui n'ont structurellement rien à
partager, pour un gain cosmétique seulement.

**Tests — une vraie duplication trouvée et factorisée.** Un helper
`_load(name: str) -> str` byte-identique (2 lignes) copié-collé dans 8
fichiers de test (`test_aco_sports_event_base.py`, `test_sro_timetable_base.py`,
`test_cli_generate_{elms,mlmc,igtc,gtwc_america,gtwc_asia,gtwc_europe}.py`),
chacun avec sa propre constante `_FIXTURES_DIR` identique
(`Path(__file__).parent / "fixtures" / "real"`) — factorisé en
`tests/conftest.py::load_real_fixture()`. Volontairement une fonction
simple, pas un `@pytest.fixture` : plusieurs de ces 8 fichiers l'appellent
au niveau module pour construire des constantes (`_RACE_BARCELONA =
_load(...)`), avant qu'un fixture pytest ne soit disponible. `tests/`
étant déjà un package (`__init__.py` présent), l'import
`from tests.conftest import load_real_fixture` fonctionne de façon fiable
dans les 8 fichiers. D'autres duplications structurelles examinées et
délibérément non touchées : les fixtures Championship/Circuit/Session/Event
répétées avec des valeurs différentes dans les 17 fichiers de test de
provider — chacune teste des données réellement distinctes (vrais noms de
circuits/fuseaux par championnat), factoriser romprait la lisibilité de
"quelle donnée ce test-là exerce" pour un gain de lignes cosmétique, à haut
risque de régression sur 17 fichiers pour un bénéfice faible.

**Performance — une optimisation réalisée, mesurée avant et après.**
Constat : `cli.py::generate` et `gui/controller.py::generate_calendar`
(l'agrégateur qui interroge tous les championnats activés) attendaient
chaque provider séquentiellement (`for cid, prov in provider_list: await
prov.fetch_events(...)`) alors que chacun interroge une API distante
totalement indépendante des 16 autres. Benchmark synthétique préalable (10
providers simulés, latence égale) : séquentiel 1.006 s, concurrent 0.101 s
— facteur ~10x, confirmant que l'optimisation vaut la peine avant de toucher
le vrai code. Fix : extraction du corps de boucle en une coroutine
`_fetch_one` par provider (gestion d'erreur par provider strictement
inchangée), puis `asyncio.gather(*(_fetch_one(...) for ...))` au lieu du
for/await — `asyncio.gather` préserve l'ordre de la liste d'entrée dans son
résultat, donc fichier ICS final et résumés affichés restent identiques.
Deux nouveaux tests de non-régression (`TestGenerateConcurrency` dans
`test_cli_generate.py`, `TestGenerateCalendarConcurrency` dans
`test_gui_controller.py`) mesurent le *spread* des timestamps de démarrage
de chaque appel provider mocké plutôt qu'un budget de temps total absolu
(le premier essai avec un seuil de temps total a échoué — `registry.
discover()`/`ConfigService()` ajoutent ~0.35-0.40s de coût fixe avant même
d'atteindre le fetch, sans rapport avec la concurrence elle-même ; le
spread des timestamps de démarrage est robuste à ce bruit). **Les deux
tests ont été vérifiés pour échouer contre l'ancienne implémentation
séquentielle** (spread mesuré de 0.659s et 0.151s respectivement,
largement au-dessus du seuil) avant d'être validés contre la nouvelle — la
preuve qu'ils testent réellement la régression qu'ils prétendent prévenir,
pas des tests qui passeraient de toute façon.

**`docs/AUDIT.md` (nouveau)** — rapport d'audit complet : audit rapide
(tableau avant/après), état général, points forts, points faibles/dette
corrigée, dette restante documentée par famille, vérifications
architecturales, 10 fichiers les plus volumineux, fonctions/classes les
plus volumineuses (`build_main_view` à 771 lignes identifiée comme seule
vraie anomalie), services les plus critiques, performance
(réalisé/reporté), recommandations pour les prochains sprints.

### Tests
- `tests/test_config_service.py`, `tests/test_imsa_provider.py`,
  `tests/test_wec_provider.py`, `tests/test_worldsbk_provider.py` :
  `pytest.raises(Exception)` narrowés en `pytest.raises(ValidationError)`
  (4 occurrences, comportement de test inchangé — même exception réellement
  levée, juste vérifiée précisément désormais).
- `tests/test_registry.py`, `tests/test_source_registry.py` : `lambda`
  assignées converties en `def` (6 occurrences, comportement identique).
- `tests/test_gui_categories.py`, `tests/test_gui_controller.py`,
  `tests/test_real_fixtures.py`, `tests/test_gui_views.py`,
  `tests/test_cli_generate_f1.py`, `tests/test_f1calendar_source.py`,
  `tests/test_http_cache.py`, `tests/test_jolpica_source.py` : corrections
  Ruff mécaniques ponctuelles (variable de boucle inutilisée renommée `_`,
  `dict()` → littéral, lignes trop longues reformatées, `with` imbriqués
  fusionnés) — comportement strictement inchangé, vérifié par leur suite
  existante intégralement verte.
- `tests/test_aco_sports_event_base.py` : nouveau helper `_type_for()`
  (14 sites d'appel migrés), `_event() -> object` corrigé en `-> Event`
  (2 occurrences) ; `_load()`/`_FIXTURES_DIR` locaux retirés au profit de
  `tests/conftest.py::load_real_fixture`.
- `tests/test_sro_timetable_base.py`,
  `tests/test_cli_generate_{elms,mlmc,igtc,gtwc_america,gtwc_asia,
  gtwc_europe}.py` : même retrait de `_load()`/`_FIXTURES_DIR` local au
  profit du helper partagé.
- `tests/conftest.py` : nouveau `load_real_fixture(name: str) -> str`
  (plain function, pas un fixture).
- `tests/test_cli_generate.py::TestGenerateConcurrency` (+1 test),
  `tests/test_gui_controller.py::TestGenerateCalendarConcurrency` (+1
  test) : nouveaux tests de non-régression performance, décrits ci-dessus.

### Fichiers modifiés / créés

| Fichier | Action |
|---|---|
| `mypy.ini` | Modifié — exclusion `gui/build/`, relâchement `[mypy-tests.*]` |
| `pyproject.toml` | Modifié — `types-PyYAML`, `types-icalendar` ajoutés aux deps dev |
| `motorsport_calendar/cache/http_cache.py` | Modifié — typage `dict[str, Any]`/`list[Any]` |
| `motorsport_calendar/cli.py` | Modifié — typage + `from exc` + fetch concurrent |
| `motorsport_calendar/config/models.py` | Modifié — typage |
| `motorsport_calendar/config/service.py` | Modifié — typage + docstrings + `ClassVar` |
| `motorsport_calendar/core/datasource/base.py` | Modifié — `noqa` B024 documenté |
| `motorsport_calendar/core/datasource/json_source.py` | Modifié — typage |
| `motorsport_calendar/core/service.py` | Modifié — bug corrigé |
| `motorsport_calendar/core/source_registry.py` | Modifié — `contextlib.suppress` |
| `motorsport_calendar/exporters/ics.py` | Non modifié (déjà propre, vérifié) |
| `motorsport_calendar/models/event.py` | Modifié — ligne trop longue reformatée |
| `motorsport_calendar/providers/*/​__init__.py` (17 fichiers) | Modifiés — annotations `_make_provider` |
| `motorsport_calendar/providers/formula1/sources/openf1.py` | Modifié — typage |
| `motorsport_calendar/providers/formula1/sources/jolpica.py` | Modifié — typage + `cast()` |
| `motorsport_calendar/providers/formula2/sources/f1calendar.py` | Modifié — typage |
| `motorsport_calendar/providers/support_series/f1calendar_base.py` | Modifié — typage |
| `motorsport_calendar/providers/motogp_series/pulselive_base.py` | Modifié — typage |
| `motorsport_calendar/gui/categories.py` | Modifié — `StrEnum` |
| `motorsport_calendar/gui/controller.py` | Modifié — typage + fetch concurrent |
| `motorsport_calendar/gui/favorites_service.py` | Modifié — docstring |
| `motorsport_calendar/gui/notification_service.py` | Modifié — docstrings |
| `motorsport_calendar/gui/preferences.py` | Modifié — typage |
| `motorsport_calendar/gui/search_service.py` | Modifié — docstrings |
| `motorsport_calendar/gui/strings.py` | Modifié — typage |
| `motorsport_calendar/gui/theme.py` | Modifié — docstrings |
| `motorsport_calendar/gui/main_view.py` | Modifié — annotation `ft.ControlEvent` manquante |
| `motorsport_calendar/gui/views/about.py` | Modifié — caractère unicode ambigu |
| `tests/conftest.py` | Modifié — `load_real_fixture()` |
| 8 fichiers `tests/test_*.py` | Modifiés — retrait `_load()` local |
| `tests/test_aco_sports_event_base.py` | Modifié — helper `_type_for()`, `Event` |
| `tests/test_cli_generate.py` | Modifié — nouveau test concurrence |
| `tests/test_gui_controller.py` | Modifié — nouveau test concurrence |
| ~15 autres fichiers `tests/*.py` | Modifiés — corrections Ruff ponctuelles |
| `docs/AUDIT.md` | Créé |
| `CHANGELOG.md` | Mis à jour |
| `docs/ROADMAP.md` | Mis à jour — v0.4.24 |
| `docs/AI_CONTEXT.md` | Mis à jour |
| `docs/TODO.md` | Mis à jour |
| `docs/DECISIONS.md` | ADR-041 ajouté |

Aucun provider, aucune vue, aucun service métier modifié dans sa **logique**
— uniquement typage, docstrings, un bug dans du code mort, une
optimisation de performance à comportement identique, et de la duplication
de test factorisée.

### Tests exécutés
```
1863 passed → 1865 passed — 0 failed
```

Ruff : 149 → 0 erreur (`ruff check .`). mypy `motorsport_calendar/` : 87 →
23 erreurs. mypy `tests/` : 402 → 157 erreurs. Les deux nouveaux tests de
concurrence ont été vérifiés manuellement pour échouer contre une version
temporairement re-séquentialisée de `cli.py::generate`/`gui/controller.py::
generate_calendar` (spread mesuré 0.659s/0.151s, bien au-dessus du seuil)
avant d'être validés contre l'implémentation finale — cette vérification a
ensuite été annulée (la version séquentielle n'a jamais été conservée).

`git status --short` confirmé en fin de session : **aucun commit
effectué**, conforme à la clôture de sprint demandée.

### Limites
- **Dette mypy Flet stub-version non corrigée** (23 erreurs source + une
  bonne part des 157 en tests) — décision assumée, documentée dans
  `docs/AUDIT.md` §4 et ADR-041 : la corriger risquerait une régression
  comportementale pour un gain de vérification statique seulement.
- **`build_main_view` (771 lignes) non découpée** — identifiée comme seule
  vraie anomalie de taille du projet, documentée comme recommandation
  prioritaire pour un futur sprint dédié avec vérification visuelle réelle
  (poste avec affichage, indisponible dans cet environnement).
- **Mutualisation des clients HTTP entre providers et virtualisation des
  listes GUI** — pistes de performance identifiées mais non mesurées,
  faute de réseau/affichage réel dans cet environnement de test.
- **`core/service.py::CalendarService` reste orpheline** — bug corrigé,
  mais la classe n'a toujours aucun appelant réel ; son avenir (câblage
  futur ou suppression) n'a pas été tranché, documenté comme piste ouverte.

---

## Session 2026-07-12 — Sprint 49 : Packaging Alpha

### Objectif
Motorsport Calendar dispose désormais d'une architecture fonctionnelle. Ce sprint n'ajoute
aucune fonctionnalité utilisateur : l'objectif est de produire une première Alpha
distribuable via la procédure officielle `flet build`, sous Linux et Windows, sans changer
le fonctionnement de l'application. Vérifier entièrement le packaging Flet (assets,
préférences, cache, exports ICS), corriger uniquement les problèmes liés au packaging, et
documenter précisément la procédure de build dans un nouveau `docs/PACKAGING.md`. Aucun
nouveau provider, aucune nouvelle page, aucune évolution métier, aucun changement de Design
System. Aucune installation automatique, aucun auto-update.

### Exploration préalable
Relecture de `pyproject.toml` (hatchling), `gui/app.py` (`assets_dir=` commenté depuis le
Sprint 23, jamais actif), `gui/preferences.py`, `cache/http_cache.py`, `config/service.py`,
`exporters/ics.py`, et de la structure `BApps-Studio/03-Products/Motorsport-Calendar/
Branding/` (les 6 fichiers officiels nommés par le brief). Deux décisions déléguées à
l'utilisateur en cours de sprint via question explicite : (1) tenter un vrai `flet build`
(télécharge le SDK Flutter, ~1-2 Go) plutôt qu'une validation structurelle seule — choix :
build réel ; (2) une fois le build bloqué sur des paquets système manquants et sans accès
sudo pour les installer moi-même, laisser l'utilisateur les installer lui-même plutôt que
me contenter de documenter la limitation — choix : l'utilisateur installe lui-même.

### Travail effectué

**`motorsport_calendar/utils/paths.py` (nouveau)** — `user_config_dir(app_name)` /
`user_cache_dir(app_name)` : convention XDG sous Linux (`$XDG_CONFIG_HOME`/
`$XDG_CACHE_HOME`, repli `~/.config`/`~/.cache`), `%APPDATA%`/`%LOCALAPPDATA%` sous
Windows — même patron `sys.platform == "win32"` déjà utilisé ailleurs dans la GUI, aucune
nouvelle dépendance (`platformdirs` écarté). Piège `Path("")` *truthy* évité en testant la
variable d'environnement brute avant de l'envelopper dans `Path(...)`.

**Trois emplacements par défaut corrigés** (même famille de bug — codé en dur Linux/macOS
ou relatif au CWD du process) :
- `cache/http_cache.py::HttpCache.__init__` : `Path(".cache")` → `_DEFAULT_CACHE_DIR =
  user_cache_dir("motorsport-calendar")`. Callers explicites (CLI/GUI via
  `config.cache.resolved_path`) inchangés — seul le repli implicite change d'emplacement.
- `config/models.py::CacheConfig.path` : même correction via `default_factory`.
- `gui/preferences.py::_PREFS_FILE` : `~/.config/motorsport-calendar/` codé en dur →
  `user_config_dir("motorsport-calendar") / "gui_prefs.json"`.
- `config/service.py::ConfigService._DEFAULT_PATHS` : seconde entrée (défaut niveau
  utilisateur) corrigée ; première entrée (`Path("config.yaml")`, relative au CWD)
  délibérément conservée — commodité de lecture explicite, pas un bug de packaging.

**`gui/app.py` — bug Flet réel découvert en lisant son propre source** : `assets_dir` passé
à `ft.run()` se résout via `flet/app.py::__get_assets_dir_path(assets_dir,
relative_to_cwd=True)` — relativement au CWD au lancement, jamais au fichier appelant.
`assets_dir=` était donc commenté depuis le Sprint 23 (aurait échoué silencieusement dès
qu'exécuté hors de la racine exacte du dépôt). Corrigé : `_ASSETS_DIR =
str(Path(__file__).parent / "assets")` — chemin absolu calculé à l'exécution, jamais un
littéral codé en dur.

**Assets officiels intégrés** — copie octet-identique depuis `BApps-Studio/03-Products/
Motorsport-Calendar/Branding/` vers `gui/assets/` : `favicon-16.png`, `favicon-32.png`,
`icon_windows.ico` (convention Flet pour l'icône Windows multi-résolution ; `icon.png`,
déjà présent, confirmé octet-identique à l'icône officielle par comparaison pixel),
`logo/mc-icon.svg`, `logo/logo-horizontal.svg`, `logo/logo-vertical.svg` (`.gitkeep`
retiré, devenu inutile). `page.window.icon = "icon.png"` câblé dans `main_view.py` (chrome
de fenêtre OS, jugé hors périmètre "vues"/"Design System"). Décision de périmètre
explicite : les 6 fichiers sont "intégrés au build" (présents, bundlés, adressables) sans
que `theme.logo_placeholder()` soit remplacé dans les vues — un chantier de Design System à
part entière, explicitement hors sprint, documenté dans `gui/assets/logo/README.md`.

**Export ICS vérifié, non modifié** — `exporters/ics.py::IcsExporter.export(events,
output_path)` déjà entièrement propre à la lecture : `output_path` fourni par l'appelant
sans défaut ni référence au dépôt. Propriété rendue explicite par de nouveaux tests.

**Build Linux tenté en direct, deux corrections de commande découvertes en cours de route** :
`flet build linux motorsport_calendar/gui --module-name app` — `python_app_path` doit
pointer sur le dossier contenant `app.py` (pas la racine du dépôt, dont `.` est le défaut) ;
`--module-name app` requis car l'entrée n'est pas `main.py`. Le SDK Flutter (3.41.7)
s'installe seul au premier lancement (~1-2 Go, confirmé). Le build atteint l'étape de
compilation native ("Building Linux application…") — confirmant que la configuration du
packaging (résolution du module, bundling des assets, `pyproject.toml`) est correcte de
bout en bout. Premier blocage : `clang`/`cmake`/`ninja-build`/`pkg-config`/`libgtk-3-dev`
manquants, aucun accès sudo pour les installer — question posée à l'utilisateur, qui a
choisi de les installer lui-même. Après recherche de la documentation officielle Flet
(WebFetch), la première liste donnée à l'utilisateur s'est révélée incomplète (manquait
`binutils`, `llvm`, et surtout `lld` — documenté par Flet comme critique, "sans lld le
build échoue avec une erreur de linker" — et `libunwind-dev`) : liste corrigée transmise
avant confirmation que l'utilisateur ait lancé la première commande.

### Tests
- `tests/test_utils_paths.py` (nouveau, 12 tests) : `user_config_dir`/`user_cache_dir` sous
  Linux et Windows (via `patch("sys.platform", ...)` + `patch.dict("os.environ", ...)`),
  repli par défaut, respect des variables XDG/`%APPDATA%`/`%LOCALAPPDATA%`, config et cache
  toujours distincts.
- `tests/test_http_cache.py` (+2 tests, `TestHttpCacheDefaultCacheDir`) : défaut inspecté
  via `inspect.signature(HttpCache.__init__).parameters["cache_dir"].default` — jamais
  instancié, pour ne pas créer un vrai répertoire sur la machine de développement.
- `tests/test_config_service.py` (+3 tests) : défaut `CacheConfig.path` et second
  `_DEFAULT_PATHS` alignés sur `user_cache_dir`/`user_config_dir` ; premier
  `_DEFAULT_PATHS` confirmé toujours CWD-relatif (intentionnel).
- `tests/test_gui_preferences.py` (+1 test, `TestDefaultPrefsFileLocation`) : vérifié par
  inspection de source (`inspect.getsource(preferences)`) plutôt que lecture de l'attribut
  live — le fixture autouse `_isolated_gui_prefs` (`conftest.py`, Sprint 44) l'écrase
  systématiquement pendant les tests, par design.
- `tests/test_ics_exporter.py` (+3 tests, `TestExportIsPackagingSafe`) : export loin de
  tout chemin du dépôt, indépendance au CWD (`monkeypatch.chdir`), acceptation d'un chemin
  absolu.
- `tests/test_packaging.py` (+5 tests) : `utils.paths` importable ; `gui.app` importable ;
  `_ASSETS_DIR` absolu ; les 6 fichiers officiels du brief présents dans `gui/assets/` ;
  résolution de `_ASSETS_DIR` indépendante du CWD (`monkeypatch.chdir` + `importlib.reload`).

### Fichiers modifiés / créés

| Fichier | Action |
|---|---|
| `motorsport_calendar/utils/paths.py` | Créé |
| `motorsport_calendar/utils/__init__.py` | Modifié — exports |
| `motorsport_calendar/cache/http_cache.py` | Modifié — défaut `cache_dir` |
| `motorsport_calendar/config/models.py` | Modifié — défaut `CacheConfig.path` |
| `motorsport_calendar/config/service.py` | Modifié — second `_DEFAULT_PATHS` |
| `motorsport_calendar/gui/preferences.py` | Modifié — `_PREFS_FILE` |
| `motorsport_calendar/gui/app.py` | Modifié — `_ASSETS_DIR`, `assets_dir=` activé |
| `motorsport_calendar/gui/main_view.py` | Modifié — `page.window.icon` |
| `motorsport_calendar/gui/assets/favicon-16.png` | Créé |
| `motorsport_calendar/gui/assets/favicon-32.png` | Créé |
| `motorsport_calendar/gui/assets/icon_windows.ico` | Créé |
| `motorsport_calendar/gui/assets/logo/mc-icon.svg` | Créé |
| `motorsport_calendar/gui/assets/logo/logo-horizontal.svg` | Créé |
| `motorsport_calendar/gui/assets/logo/logo-vertical.svg` | Créé |
| `motorsport_calendar/gui/assets/logo/.gitkeep` | Supprimé — devenu inutile |
| `motorsport_calendar/gui/assets/logo/README.md` | Réécrit — statut Brand Set v1.0 |
| `tests/test_utils_paths.py` | Créé — 12 tests |
| `tests/test_http_cache.py` | Modifié — 2 tests ajoutés |
| `tests/test_config_service.py` | Modifié — 3 tests ajoutés |
| `tests/test_gui_preferences.py` | Modifié — 1 test ajouté |
| `tests/test_ics_exporter.py` | Modifié — 3 tests ajoutés |
| `tests/test_packaging.py` | Modifié — 5 tests ajoutés, imports consolidés |
| `docs/PACKAGING.md` | Créé |
| `CHANGELOG.md` | Mis à jour |
| `docs/ROADMAP.md` | Mis à jour — v0.4.23 |
| `docs/AI_CONTEXT.md` | Mis à jour — entrée #49, dette résolue, nouvelles pistes |
| `docs/TODO.md` | Mis à jour — section Sprint 49 |
| `docs/DECISIONS.md` | ADR-040 ajouté |

`motorsport_calendar/providers/`, `motorsport_calendar/models/`, `motorsport_calendar/
gui/views/`, `motorsport_calendar/gui/components/` (hors `main_view.py`, une ligne) : **non
modifiés** — conforme à "ne pas modifier les providers", "ne pas modifier les services
métier", "ne pas modifier les vues autrement que pour résoudre un problème de packaging".

### Tests exécutés
```
1837 passed → 1863 passed — 0 failed
```

Vérification ruff/mypy sur les fichiers neufs/modifiés : import-sorting corrigé de façon
ciblée (`ruff check --fix --select I001`, jamais un `--fix` non scopé, pour ne pas
"nettoyer" silencieusement de la dette F401/RUF012/UP037/B017 préexistante — vérifié via
`git show HEAD:<file>` que chacun de ces éléments préexistait déjà avant ce sprint).
`utils/paths.py` passe à 0 erreur mypy.

Vérification manuelle additionnelle : smoke test direct de `user_config_dir`/
`user_cache_dir` confirmant une sortie strictement identique aux anciens chemins Linux
codés en dur, et le respect correct des variables d'environnement XDG en cas de
surcharge. `_ASSETS_DIR` vérifié identique quel que soit le CWD du process au lancement.

**Build Linux réellement exécuté sur cette machine** : `flet build linux
motorsport_calendar/gui --module-name app` — SDK Flutter téléchargé et installé,
dépendances Dart/Flutter résolues, module d'entrée et dossier `assets/` correctement
détectés, build atteint l'étape de compilation native. Bloqué à cette étape par
l'outillage système manquant sur cette machine de développement (`binutils clang cmake
llvm lld ninja-build pkg-config libgtk-3-dev libunwind-dev`) : commande d'installation
corrigée et complète transmise à l'utilisateur en fin de sprint
(`sudo apt update && sudo apt install -y binutils clang cmake llvm lld ninja-build
pkg-config libgtk-3-dev libunwind-dev`), aucun accès sudo disponible pour l'exécuter
moi-même. À la clôture de cette session, ces paquets **ne sont toujours pas installés**
sur cette machine (`dpkg -s` vérifié individuellement pour chacun) — le build Linux n'a
donc pas atteint un binaire compilé cette session, seulement la confirmation que la
configuration du packaging elle-même est correcte de bout en bout. Build Windows jamais
exécuté (aucune machine Windows disponible dans cet environnement, et Flet ne permet pas
la cross-compilation Windows depuis Linux/macOS) — procédure et prérequis transcrits
fidèlement depuis la documentation officielle Flet dans `docs/PACKAGING.md`, avec mention
honnête "non exécuté ce sprint".

`git status --short` confirmé en fin de session : 140 chemins modifiés/créés, **aucun
commit effectué**, conforme à la clôture de sprint demandée.

### Limites
- **Build Linux non mené jusqu'à un binaire compilé** — bloqué sur l'outillage système
  manquant, pas un bug projet ; à relancer une fois les paquets installés (voir
  `docs/PACKAGING.md` §2, `docs/TODO.md`). La checklist de validation complète du brief
  (démarre, charge les assets, ouvre toutes les pages, lit/écrit les préférences, crée le
  cache, génère un ICS, fonctionne sans le dépôt Git) n'a donc pas pu être exécutée contre
  un exécutable réel cette session — seulement validée structurellement (imports, chemins,
  tests unitaires).
- **Build Windows jamais exécuté** — aucune machine Windows disponible dans cet
  environnement ; procédure documentée mais non vérifiée en conditions réelles.
- **`theme.logo_placeholder()` non câblé sur les vraies images** — volontaire, chantier de
  Design System hors périmètre du brief Sprint 49.
- **CI/CD, installeur, auto-update, signature de code, build macOS** — explicitement hors
  périmètre du brief, non traités.

---

## Session 2026-07-12 — Sprint 48 : Finalisation des providers

### Objectif
Motorsport Calendar dispose désormais d'une architecture mature. Trois championnats
restent volontairement en mode "stub" : FIA WEC, IMSA WeatherTech, WorldSBK — l'objectif
est d'achever définitivement la couche de données en remplaçant les implémentations
temporaires par des providers fonctionnels. Travail attendu pour chacun : rechercher la
meilleure source de données disponible, privilégier une API officielle, à défaut une
source stable, le scraping en dernier recours. Conserver les abstractions existantes ;
créer une nouvelle famille de providers si elle apparaît naturellement ; ne jamais casser
les providers existants. Validation : chaque provider implémenté doit être vérifié sur une
saison complète (nombre d'événements, nombre de sessions, UID uniques, cohérence des
fuseaux horaires, intégration agrégateur/Dashboard/Ce week-end/Recherche). Tests complets,
zéro régression.

### Exploration préalable de l'architecture GUI
Relecture des trois stubs existants (`providers/wec/sources/official.py`,
`providers/imsa/sources/official.py`, `providers/worldsbk/sources/official.py`) : chacun
documente déjà en détail sa propre investigation passée (Sprints 29/36/38) — point de
départ, pas une conclusion à prendre pour acquise, puisque le brief demande explicitement
de "rechercher la meilleure source", pas de se contenter d'une documentation vieille de
plusieurs sprints. Relecture de `providers/aco_series/sports_event_base.py`
(`AcoSportsEventSource`, Sprint 35) et de `providers/elms/sources/aco_scraper.py`
(`AcoScraperSource`) comme patron de référence pour toute source basée sur le même CMS —
la piste explicitement documentée depuis le Sprint 35 pour WEC ("fiawec.com tourne
peut-être sur le même CMS qu'ELMS/MLMC, jamais vérifié sur une vraie manche") devient le
premier point d'investigation en direct.

### Travail effectué

**Recherche en direct — WEC : source trouvée**
`curl`/`httpx` directs (jamais un résumé IA à cette étape, cohérent avec la méthode déjà
établie aux Sprints 35/37/38) sur `fiawec.com/en/season/2026` puis sur les 8 pages course
réelles de la saison 2026 (pas seulement un Prologue, contrairement à l'inspection
partielle du Sprint 35) : structure JSON-LD `SportsEvent`/`subEvent` confirmée identique à
celle déjà exploitée pour ELMS/MLMC. Trois divergences réelles découvertes en comparant
les données, jamais supposées à l'avance : labels de session supplémentaires (Free
Practice 4, Hyperpole, Warm-up — absents chez ELMS/MLMC), page saison mélangeant l'année
demandée et la suivante dans le même DOM, et surtout un bug réel : l'`endDate` JSON-LD
top-level ne reflète jamais la durée réelle d'une course WEC (toujours minuit du dernier
jour annoncé) — silencieusement plausible-mais-fausse pour les 24 Heures du Mans
(~8h calculées au lieu de 24h réelles), détecté en comparant le résultat calculé à la durée
réelle connue de la course avant d'écrire le moindre test.

**Recherche en direct — IMSA : toujours aucune source (ré-investigué)**
`imsa.com` re-testé sur plusieurs routes, y compris `/robots.txt`/`/sitemap.xml` (jamais
testés au Sprint 36) : blocage Cloudflare HTTP 403 encore plus strict qu'au Sprint 36 (même
les fichiers habituellement exemptés d'une protection anti-bot standard sont bloqués).
Portail Al Kamel (`imsa.results.alkamelcloud.com`) re-vérifié : toujours une archive de
résultats post-course uniquement, confirmé en observant qu'aucun dossier de session
n'existe avant que la session ait eu lieu. Tableau "Schedule" de Wikipedia (API MediaWiki,
page "2026 IMSA SportsCar Championship") re-vérifié : toujours des dates de course
uniquement, jamais d'heures de session. Aucune source exploitable trouvée — même
conclusion que le Sprint 36, re-confirmée en direct plutôt que recopiée.

**Recherche en direct — WorldSBK : toujours aucune source (ré-investigué)**
Sondage de plusieurs variantes d'hôtes de la famille Pulselive au-delà de celles déjà
documentées au Sprint 38 : `api.pulselive.worldsbk.com` (réel, 404 applicatif sur toutes
les routes devinées), `wsbk-api-origin.gplat-prod.pulselive.com` (variante "-prod" du
candidat déjà connu "-test", injoignable), et deux hôtes jamais mentionnés auparavant
découverts en cherchant toute référence `*.pulselive.com` dans le HTML de la page
calendrier et son fichier de traductions — `api.wsbk.pulselive.com` (réel mais aucune
route valide) et `wsbk.pulselive.com` (s'avère être le CMS média du site public,
doublé d'un simple miroir SPA — pas une API). Aucun endpoint événements exploitable sans
automatisation navigateur pour intercepter les vrais appels XHR — même conclusion que le
Sprint 38, re-confirmée en direct avec deux nouvelles pistes explorées et écartées.

**`providers/aco_series/sports_event_base.py`** — étendu de façon purement additive
- `_EXCLUDED_SLUG_KEYWORDS` : `"prologue"` ajouté (le prologue pré-saison de WEC, jamais
  présent chez ELMS/MLMC).
- `_LABEL_RULES` : trois nouvelles entrées ("Free Practice 4" → `SessionType.FREE_PRACTICE`
  générique plutôt qu'un `FP4` non supporté par le modèle de domaine ; "Hyperpole" →
  `SessionType.HYPERPOLE`, déjà présent depuis les tout premiers sprints WEC ; "Warm-up" →
  `SessionType.TEST`, le type existant le plus proche — délibérément distinct de
  `FREE_PRACTICE` pour que le mécanisme de fusion multi-slots existant ne combine jamais
  les deux en une session absurde couvrant ~37 heures sur le week-end du Mans).
- Deux nouveaux points d'extension explicites, comportement par défaut strictement
  inchangé pour ELMS/MLMC : `_race_session_end(first_start, event_end, event_name) ->
  datetime | None` (défaut : logique de plausibilité déjà existante sur l'`endDate`) et
  `_race_url_belongs_to_season(url, year) -> bool` (défaut : `True` inconditionnel).
  Extraits plutôt que dupliqués — `OfficialWecSource` surcharge les deux, ELMS/MLMC n'y
  touchent pas.

**Nouveau `providers/wec/circuit_data.py`**
- `WEC_CIRCUIT_DATA` (nom de circuit → fuseau IANA, 8 entrées 2026) et
  `WEC_ADDRESS_COUNTRY_CODES` (code ISO 3166-1 alpha-3 → nom de pays anglais, 9 entrées) —
  le pays est résolu **dynamiquement** depuis le champ `location.address` du JSON-LD
  (`"{ville}, {code}"`, confirmé fiable sur les 8 manches 2026) plutôt qu'une table
  statique par circuit, même raisonnement "préférer la donnée en direct" déjà justifié
  pour `sro_series/circuit_data.py` (Sprint 37) ; la table statique ne sert que de repli.

**`providers/wec/sources/official.py`** — `OfficialWecSource` devient réelle
- `class OfficialWecSource(AcoSportsEventSource, WecSource)` — même patron exact que
  `AcoScraperSource` pour ELMS/MLMC. Nom de classe et clé d'enregistrement `"official"`
  conservés tels quels (jamais renommés en `"aco_scraper"`) : `ProvidersConfig.wec` a un
  défaut explicite `source="official"` — renommer aurait cassé silencieusement tout
  `config.yaml` s'appuyant sur ce défaut.
- `_series_key`/`_base_url`/`_event_name_prefix`/`_circuit_data`/`_make_championship` :
  les 5 propriétés/méthodes minimales requises par `AcoSportsEventSource`, même patron
  qu'ELMS/MLMC.
- `_race_url_belongs_to_season` : filtre par suffixe `-{year}` de l'URL.
- `_build_circuit` : surcharge complète pour la résolution de pays dynamique décrite
  ci-dessus (utilise `_circuit_data` uniquement comme repli fuseau/pays).
- `_race_session_end` : parse un motif `"X Hours"` (regex insensible à la casse) dans le
  nom brut de l'épreuve — couvre 6 des 8 manches 2026. Les 2 exceptions nommées
  différemment ("Lone Star Le Mans", "Qatar 1812km") ont des durées confirmées par
  recherche factuelle (fiawec.com/Wikipedia — 6h et 10h respectivement), jamais devinées.
  Repli générique à 6h (format WEC le plus courant) pour un nom futur non reconnu.

### Tests
- `tests/test_aco_sports_event_base.py` (+10 tests) : les 3 nouveaux labels de session
  (Free Practice 4 distinct de FP3, Hyperpole bare/numéroté, Warm-up), exclusion du
  prologue, comportement par défaut inchangé des deux nouveaux points d'extension
  (`_race_session_end` : endDate plausible utilisé/rejeté/absent ; `_race_url_belongs_to_season` :
  `True` par défaut).
- `tests/test_wec_provider.py` (+30 tests, -1 test stub obsolète retiré) : identité de
  `OfficialWecSource` (série/URL/préfixe, instance de `AcoSportsEventSource`) ; durée de
  course déduite du nom (6 manches "X Hours", 2 exceptions nommées, repli 6h générique,
  et surtout confirmation que l'`endDate` JSON-LD est totalement ignoré même quand il
  semble "plausible" — le bug Le Mans reproduit et vérifié corrigé) ; résolution de pays
  depuis l'adresse (code connu, code inconnu avec repli table statique, adresse absente,
  circuit totalement inconnu) ; filtrage par année de saison ; parsing de bout en bout sur
  les fixtures réelles Imola (6 sessions, Hyperpole fusionné, UID uniques) et Le Mans (8
  types de session distincts, Course à 24h exactement, FP4 et Warm-up jamais fusionnés
  malgré ~37h d'écart, Qualifying fusionné sur 2 jours × 2 classes) ; intégration
  `get_season()` de bout en bout avec la vraie page saison mockée (prologue et années
  2027 correctement exclus).
- `tests/test_cli_generate_wec.py` (-2 tests obsolètes retirés) : les deux tests
  "NotImplementedError sans mock" n'ont plus de sens réel (WEC ne lève plus cette
  exception) — retirés, le reste de la couverture (erreurs HTTP/timeout via mock explicite
  de `get_season`) reste valide et inchangé.
- `tests/test_cli_generate.py` (adapté, sans test net nouveau) : nouvelle entrée
  `OfficialWecSource` dans la fixture autouse `_isolate_support_series` — la fait échouer
  par défaut (`NotImplementedError`) sauf mock explicite, restaurant exactement le
  comportement dont dépendaient déjà 6 tests existants ("F1 réussit, WEC échoue", "tout
  échoue") sans devoir modifier le corps d'aucun d'eux.
- `tests/test_gui_controller.py` (adapté, sans test net nouveau) : WEC ajoutée à
  `_WEEKEND_SOURCE_PATHS` (désormais mockée comme toute autre source réelle, plus jamais
  laissée échouer naturellement) ; `TestGenerateCalendarWec` renommée
  `TestGenerateCalendarImsa` (IMSA, toujours un stub réel, reprend le rôle de "source non
  implémentée" de référence pour ces tests, même intention, même couverture) ; deux tests
  `test_wec_not_implemented_does_not_crash_the_whole_call` renommés/adaptés en
  `test_imsa_worldsbk_not_implemented_does_not_crash_the_whole_call`.

### Fichiers modifiés / créés

| Fichier | Action |
|---|---|
| `motorsport_calendar/providers/aco_series/sports_event_base.py` | Modifié — additif uniquement |
| `motorsport_calendar/providers/wec/circuit_data.py` | Créé |
| `motorsport_calendar/providers/wec/sources/official.py` | Réécrit — implémentation réelle |
| `tests/fixtures/real/wec_season_snippet.html` | Créé — extrait réel (prologue + 2026/2027) |
| `tests/fixtures/real/wec_race_imola.html` | Créé — JSON-LD réel, manche normale |
| `tests/fixtures/real/wec_race_le_mans.html` | Créé — JSON-LD réel, cas limite FP4/Warm-up |
| `tests/test_aco_sports_event_base.py` | Modifié — 10 tests ajoutés |
| `tests/test_wec_provider.py` | Modifié — 30 tests ajoutés, 1 retiré |
| `tests/test_cli_generate_wec.py` | Modifié — 2 tests obsolètes retirés |
| `tests/test_cli_generate.py` | Modifié — fixture autouse étendue |
| `tests/test_gui_controller.py` | Modifié — tests adaptés (IMSA reprend le rôle de WEC) |
| `CHANGELOG.md` | Mis à jour |
| `docs/ROADMAP.md` | Mis à jour — v0.4.22 |
| `docs/AI_CONTEXT.md` | Mis à jour |
| `docs/TODO.md` | Mis à jour |
| `docs/DECISIONS.md` | ADR-039 ajouté |
| `docs/DATA_SOURCES.md` | Sections WEC/IMSA/WorldSBK mises à jour |

`motorsport_calendar/providers/wec/provider.py`, `providers/wec/source.py`,
`providers/wec/__init__.py`, `providers/wec/sources/__init__.py` (non modifiés — clé
d'enregistrement `"official"` conservée telle quelle), `providers/elms/`, `providers/mlmc/`
(non modifiés — comportement strictement préservé, vérifié par leurs suites de tests
existantes), `providers/imsa/`, `providers/worldsbk/` (non modifiés — stubs inchangés,
aucune source exploitable trouvée), `gui/` (aucun fichier — WEC apparaît automatiquement
dans Dashboard/Ce week-end/Recherche sans aucun câblage supplémentaire, l'architecture
existante suffit) : **non modifiés**.

### Tests exécutés
```
1800 passed → 1837 passed — 0 failed
```

Vérification ruff sur les fichiers neufs/modifiés : 2 problèmes d'imports non triés
introduits (`aco_series/sports_event_base.py`, `wec/sources/official.py`) — corrigés
immédiatement avec `ruff check --fix`. Reste du code neuf entièrement propre. Les
problèmes ruff détectés lors d'un balayage plus large (imports non triés dans
`test_cli_generate.py`, `datetime.UTC` non utilisé, imports `pytest` inutilisés dans 2
fichiers) préexistent tous dans du code non touché par ce sprint (vérifié ligne par ligne
via `git diff`, aucune de ces lignes n'apparaît dans le diff de ce sprint).

Vérification mypy : `providers/aco_series/sports_event_base.py`,
`providers/wec/sources/official.py`, `providers/wec/circuit_data.py`,
`providers/wec/provider.py`, `providers/wec/source.py` passent tous à **0 erreur**.

Vérification manuelle additionnelle (vrais appels réseau, pas de mock) : `OfficialWecSource().get_season(2026)`
exécuté contre le vrai fiawec.com → 8 événements, 50 sessions, UID d'événement et de
session tous uniques (vérifié programmatiquement), fuseaux horaires corrects sur les 8
circuits. `motocal generate-wec 2026 out.ics` exécuté pour de vrai → "✓ 8 events, 50
sessions", fichier ICS valide. `motocal generate 2026 out.ics` (agrégateur complet, 17
providers) exécuté pour de vrai → WEC apparaît avec "✓ wec : 8 événements" aux côtés des
16 autres providers, IMSA/WorldSBK toujours "✗ ... : source non implémentée" proprement
géré, 179 événements/860 sessions au total. Intégration GUI vérifiée en direct sans mock :
`controller.list_championships()` inclut "wec" ; `controller.get_calendar_year_events(2026)["wec"]`
retourne les 8 événements réels ; `controller.get_dashboard_data()` et
`controller.get_upcoming_weekend()` incluent WEC dans leurs cartes de week-end réelles ;
`SearchService` retrouve "FIA WEC" par recherche "WEC", "24 Hours of Le Mans"/"Lone Star Le
Mans" par recherche "Le Mans" ; `CircuitService` (Sprint 47) fusionne automatiquement
"Spa-Francorchamps" de WEC avec 4 autres championnats sans aucune modification nécessaire.

### Limites
- **IMSA et WorldSBK restent des stubs** — aucune source structurée exploitable trouvée
  après ré-investigation en direct, conforme au brief ("rechercher la meilleure source
  disponible", pas "en trouver une à tout prix"). Pistes non explorées documentées dans
  `docs/DATA_SOURCES.md`/`docs/TODO.md` pour les deux : automatisation navigateur
  (Playwright, hors périmètre assumé de ce projet) et contact direct partenaire.
- **Aucune vérification visuelle réelle** de WEC dans le rendu Flet (Dashboard/Ce
  week-end) sur un poste avec affichage — pipeline de données entièrement revérifié en
  direct sans mock, mais aucun rendu pixel confirmé, même limitation que chaque sprint GUI
  précédent.
- Durée de course WEC pour un nom d'épreuve futur ne correspondant ni au motif "X Hours"
  ni à la table `_NAMED_RACE_DURATION_HOURS` se rabat sur 6h par défaut (correct pour la
  saison 2026, documenté comme approximation assumée dans `docs/AI_CONTEXT.md`).
- `WEC_CIRCUIT_DATA`/`WEC_ADDRESS_COUNTRY_CODES` couvrent uniquement les circuits observés
  sur le calendrier 2026 — non exhaustives par convention (même principe que toutes les
  autres tables `_CIRCUIT_DATA` du projet), à compléter au fil des saisons futures (ex.
  Silverstone, déjà au calendrier 2027).

---

## Session 2026-07-12 — Sprint 47 : Circuit Explorer

### Objectif
Les événements sont désormais consultables (fiche événement, Sprint 42) mais les
circuits restent de simples informations textuelles — jamais interrogeables,
jamais dédupliqués entre championnats. Ils doivent devenir des objets de premier
niveau : créer une véritable base de données des circuits à partir des données déjà
disponibles. Travail attendu : créer un `CircuitService` (aucun provider
supplémentaire, aucun appel réseau, construit uniquement à partir des événements déjà
chargés). Chaque circuit doit posséder : nom, pays, nombre de championnats, liste des
championnats, nombre total d'événements, première et dernière saisons disponibles.
Depuis la fiche événement, le nom du circuit devient cliquable ; au clic, ouvrir une
fiche Circuit affichant nom, pays, championnats, historique des événements, nombre
total de courses. Architecture : créer `gui/circuit_service.py`, toute la logique dans
ce service, aucune logique métier dans les vues. Tests complets, zéro régression.

### Exploration préalable de l'architecture GUI
Relecture de `motorsport_calendar/models/circuit.py` : `Circuit(id, name, city, country,
timezone)`, aucun champ optionnel — confirmant que `name`/`city` peuvent en pratique être
vides pour certains providers (déjà documenté depuis le Sprint 32 : le bug F2/F3 où
`Circuit.name` reprend le descriptif court de l'épreuve). Relecture de
`gui/event_display.py` (Sprint 32, ADR-023) : `_resolve_circuit_name` répond à "cette
ligne doit-elle s'afficher sous CET événement" (masque une valeur redondante avec le
titre d'une carte précise) — pas la question posée par une base de données de circuits
("comment ce circuit s'appelle-t-il, indépendamment de tout événement"). `_resolve_country`
en revanche convient tel quel : sa règle ("jamais 'Unknown' affiché tel quel") ne dépend
d'aucun événement précis. Relecture de `gui/search_service.py` (Sprint 45) : sa
normalisation privée `_normalize` (NFKD + accents + casse + alphanumérique uniquement)
dédupliquait déjà les circuits dans les résultats de recherche — exactement le besoin de
`CircuitService`, à plus grande échelle. Relecture de `gui/components/championship_card.py` :
le nom de circuit est un `ft.Text` nu, sans aucun point d'extension pour le rendre
cliquable — et le composant est partagé par "Ce week-end"/Dashboard/Favoris/fiche
événement, donc le rendre cliquable partout n'est ni demandé ni désirable. Relecture de
`main_view.py::_on_event_row_click`/`_show_event_details_dialog` (Sprint 42) : l'`Event`
domaine complet est déjà résolu au moment d'ouvrir la fiche événement — le point d'entrée
naturel pour résoudre aussi le circuit cliqué.

### Travail effectué

**`gui/event_display.py`** — trois fonctions promues/ajoutées publiques
- `normalize_key()` : déplacée depuis l'ancien `search_service._normalize` (Sprint 45)
  une fois la déduplication de circuits devenue un second consommateur réel de la même
  normalisation "compacte" — même principe de mutualisation-au-second-usage déjà
  appliqué à `session_type_label`/`championship_selector.py`. `search_service.py`
  importe désormais cette fonction publique au lieu de sa propre copie privée —
  comportement strictement inchangé, vérifié par ses 29 tests existants intégralement
  verts sans aucune modification après le déplacement.
- `circuit_display_name(circuit)` (nouvelle) : le nom propre d'un circuit — premier non
  vide entre `circuit.name`/`circuit.city` — sans jamais rien masquer pour cause de
  redondance avec un événement précis, contrairement à `_resolve_circuit_name`. Repli
  final sur une nouvelle chaîne `STRINGS.circuit_name_fallback` ("Circuit inconnu") dans
  le cas extrême (jamais observé sur les fixtures réelles du projet) où les deux valeurs
  sont vides.
- `resolve_country()` (renommée depuis `_resolve_country`, comportement identique) :
  publique car sa règle ne dépend d'aucun événement précis, réutilisable telle quelle
  pour le pays d'un circuit en tant qu'entité.
- `EventDisplayData` gagne `circuit_key: str | None`, calculé dans
  `normalize_event_display()` comme `normalize_key(circuit_name)` — **en lockstep avec
  `circuit_name`** : `None` exactement quand la ligne circuit est masquée pour cet
  événement précis. Décision explicite : jamais une identité de circuit "cliquable en
  théorie" sur une carte où il n'existe littéralement aucun texte affiché pour porter le
  clic.

**Nouveau `gui/circuit_service.py`** — `CircuitService`, mirroring `SearchService`
- `CircuitProfile` (frozen) : `circuit_key`, `name`, `country`, `championship_ids`/
  `championship_names` (tuples parallèles triés alphabétiquement), `championship_count`,
  `total_events`, `first_season`, `last_season`, `events: tuple[CircuitEventEntry, ...]`.
- `CircuitEventEntry` (frozen) : `event_name`, `championship_id`, `championship_name`,
  `season`, `event_uid` — identité portée, jamais interprétée (même patron "carry
  identity, never interpret" que `SeasonEventRow`, Sprint 42) : un futur clic sur une
  ligne d'historique pourra rouvrir la fiche événement correspondante sans que ce module
  ait besoin de le savoir.
- `build_index(year_events)` : agrège chaque circuit à travers tous les
  championnats/saisons déjà chargés. Déduplication par `normalize_key(circuit_display_name(...))`
  — validée en direct sur données réelles : "Spa-Francorchamps" fusionne automatiquement
  5 championnats (F1, ELMS, MLMC, GTWC Europe, IGTC) en une seule entité malgré des
  orthographes différentes selon le provider. Nom d'affichage : première occurrence
  gagne (même convention que la déduplication de circuits de `SearchService`, Sprint 45).
  Pays : "best available data" à travers les providers — tant qu'aucune valeur non-`None`
  n'a été trouvée pour un circuit, chaque nouvel événement est une nouvelle chance de la
  résoudre ; une fois trouvée, jamais écrasée par un "Unknown" rencontré ensuite (le
  défaut sévère des tables `_CIRCUIT_DATA` F2/F1 Academy, documenté depuis le Sprint 32,
  ne masque donc plus jamais un vrai pays qu'un autre championnat connaît pour le même
  circuit).
- `get_circuit(circuit_key)`/`list_circuits()` : interrogation de l'index construit,
  aucun accès réseau, aucune dépendance Flet.

**`gui/event_details.py`** — passe-plat, aucune logique propre
- `EventDetails` gagne `circuit_key: str | None`, transmis tel quel depuis
  `display.circuit_key` — même rôle que `date_label`, jamais interprété ici.

**`gui/components/championship_card.py`** — nouveau point d'extension
- `build_championship_card` gagne `on_circuit_click: Callable[[], None] | None = None` —
  exact même contrat que `footer` (Sprint 30) : `None` (partout ailleurs — Ce week-end,
  Dashboard, Favoris) laisse la ligne circuit strictement inchangée (texte simple,
  `theme.Colors.TEXT_MUTED`) ; wiré, elle devient un `ft.Container` cliquable
  (`theme.Colors.PRIMARY`, seul jeton sémantique déjà existant réutilisé, aucune
  nouvelle couleur). Rien à cliquer quand `circuit_name is None`, même avec le
  paramètre fourni — cohérent avec `circuit_key` en lockstep.

**`main_view.py`** — fiche Circuit et câblage du clic
- `circuit_service = CircuitService()` construit une fois ; `build_index()` appelé aux
  deux mêmes points que `search_service.build_index()` (démarrage avec `year_events or
  {}`, puis à chaque résolution d'année dans `_load_year_events`) — même rationale,
  l'index n'est jamais reconstruit depuis les providers.
- `_show_event_details_dialog` : nouveau `on_circuit_click()` interne, résolvant
  `circuit_service.get_circuit(details.circuit_key)` puis ouvrant
  `_show_circuit_details_dialog(profile)` — no-op silencieux si `circuit_key` est `None`
  ou si la clé est inconnue (index pas encore reconstruit), jamais un plantage.
- Nouveau `_show_circuit_details_dialog(profile)` : même patron exact que
  `_show_event_details_dialog`/`_show_success_dialog` (`ft.AlertDialog`/
  `page.show_dialog`/`page.pop_dialog`, largeur fixe 400px, colonne scrollable) — nom,
  pays, nombre de championnats + puces (`theme.chip`, même patron que la section
  "Championnats ce week-end" du Dashboard), historique chronologique des événements,
  nombre total de courses.

### Tests
- `tests/test_gui_circuit_service.py` (créé, 15 tests) : index vide, circuit unique
  (champs de base, entrée d'historique), pays masqué si "Unknown"/vide, déduplication
  cross-provider (insensible casse/séparateurs, fusion des championnats, première
  occurrence gagne pour le nom, meilleur pays disponible à travers les providers),
  plage de saisons (min/max), tri de l'historique (saison puis championnat puis
  événement), `list_circuits()` trié alphabétiquement, reconstruction de l'index
  (remplace, ne cumule jamais l'ancien contenu).
- `tests/test_gui_components_championship_card.py` (+5 tests,
  `TestCircuitClickExtensionPoint`) : texte simple par défaut, conteneur cliquable une
  fois wiré, le clic appelle le handler sans argument, rien à cliquer quand
  `circuit_name is None` même wiré, le nombre de sections ne change pas quand le
  paramètre est omis.
- `tests/test_gui_event_details.py` (+2 tests, `TestCircuitKey`) : `circuit_key` défini
  quand `circuit_name` est affiché, `circuit_key` à `None` quand la ligne est masquée
  (reproduction du bug F2/F3, Sprint 32).
- `tests/test_gui_event_display.py` (+13 tests) : `normalize_key` (casse/accents/
  séparateurs insensibles, noms différents produisent des clés différentes),
  `resolve_country` (résolution connue, sentinelle "Unknown"/vide masquées),
  `circuit_display_name` (préfère `name`, repli sur `city`, ne masque jamais pour
  redondance, repli générique si les deux sont vides), `circuit_key` sur
  `EventDisplayData` en lockstep avec `circuit_name`.

### Fichiers modifiés / créés

| Fichier | Action |
|---|---|
| `motorsport_calendar/gui/circuit_service.py` | Créé |
| `motorsport_calendar/gui/event_display.py` | Modifié — `normalize_key`/`circuit_display_name`/`resolve_country` publics, `circuit_key` |
| `motorsport_calendar/gui/event_details.py` | Modifié — `circuit_key` transmis |
| `motorsport_calendar/gui/search_service.py` | Modifié — réutilise `normalize_key` importé |
| `motorsport_calendar/gui/components/championship_card.py` | Modifié — `on_circuit_click` |
| `motorsport_calendar/gui/main_view.py` | Modifié — fiche Circuit + câblage du clic |
| `motorsport_calendar/gui/strings.py` | Modifié — bloc de chaînes Circuit Explorer |
| `tests/test_gui_circuit_service.py` | Créé — 15 tests |
| `tests/test_gui_components_championship_card.py` | Modifié — 5 tests ajoutés |
| `tests/test_gui_event_details.py` | Modifié — 2 tests ajoutés |
| `tests/test_gui_event_display.py` | Modifié — 13 tests ajoutés |
| `CHANGELOG.md` | Mis à jour |
| `docs/ROADMAP.md` | Mis à jour — v0.4.21 |
| `docs/AI_CONTEXT.md` | Mis à jour |
| `docs/TODO.md` | Mis à jour |
| `docs/DECISIONS.md` | ADR-038 ajouté |

`motorsport_calendar/core/`, `providers/`, `exporters/`, `models/` (domaine, non
modifié), `gui/favorites_service.py`, `gui/notification_service.py`,
`gui/calendar_selection.py`, `gui/season_explorer.py`, `gui/theme.py`,
`gui/components/layout/*`, `gui/components/championship_selector.py`,
`gui/categories.py`, `gui/preferences.py`, `gui/models.py`, `gui/controller.py`,
`gui/views/*` (aucune nouvelle page ce sprint, aucune destination de navigation ajoutée),
`docs/DATA_SOURCES.md` (aucune nouvelle source de données ce sprint) : **non modifiés**.

### Tests exécutés
```
1765 passed → 1800 passed — 0 failed
```

Vérification ruff sur les fichiers neufs/modifiés : 2 problèmes introduits — imports non
triés dans `event_display.py` (corrigé avec `ruff check --fix`) et 2 lignes trop longues
dans `main_view.py` (corrigées manuellement, découpage multi-lignes). Reste du code neuf
entièrement propre (`ruff check gui/circuit_service.py gui/event_display.py
gui/event_details.py gui/search_service.py gui/components/championship_card.py
tests/test_gui_circuit_service.py tests/test_gui_event_display.py
tests/test_gui_event_details.py tests/test_gui_components_championship_card.py` → "All
checks passed!"). Les problèmes ruff restants détectés lors d'un balayage plus large
(`noqa` non utilisés / `ANN001` / `UP037`) préexistent tous dans du code non touché par
ce sprint (vérifié ligne par ligne, mêmes lignes que les sprints précédents).

Vérification mypy : `gui/circuit_service.py`/`gui/event_display.py`/
`gui/event_details.py`/`gui/search_service.py`/`gui/components/championship_card.py`
passent tous à **0 erreur**. `main_view.py` passe de 19 à 20 erreurs — exactement +1,
la même famille déjà tolérée `Button.on_click` (le bouton de fermeture de la nouvelle
fiche Circuit, même famille que les fiches événement/succès existantes), pas une
nouvelle catégorie.

Vérification manuelle additionnelle (vrais appels réseau, pas de mock) : championnats et
événements réels de l'année 2026 récupérés, `CircuitService.build_index()` appelé sur
les 171 événements réels → 91 circuits indexés ; le profil "Spa-Francorchamps" confirmé
en direct : 5 championnats (`elms`, `formula1`, `gtwc-europe`, `igtc`, `mlmc`), 5
événements, pays "🇧🇪 Belgique" correctement résolu. Bout-en-bout complet simulé : un vrai
`Event` "Belgian Grand Prix" de Formula 1 passé à `build_event_details()` → `circuit_key
== "spafrancorchamps"` → `circuit_service.get_circuit(...)` résout le même profil Spa →
`build_championship_card(..., on_circuit_click=...)` rend un conteneur cliquable → le
clic simulé (`container.on_click(None)`) déclenche bien le handler avec le profil
attendu. Rendu du contenu de la fiche Circuit (nom, pays, puces de championnats,
historique, nombre total de courses) confirmé sans exception sur le vrai profil Spa (14
contrôles générés). `build_main_view()` exécuté de bout en bout avec une fausse `Page`
Flet et un fichier de préférences isolé — aucune erreur, `circuit_service` correctement
construit et indexé au démarrage et à chaque changement d'année.

### Limites
- **Aucune vérification visuelle réelle** (rendu Flet sur un poste avec affichage) —
  même limitation que chaque sprint GUI précédent.
- **Aucune page "Circuits" dédiée** — `list_circuits()` existe et est testé mais n'est
  exposé nulle part dans la navigation ; la fiche Circuit ne s'ouvre que depuis un clic
  dans la fiche événement. Non demandé par le brief, piste documentée dans
  `docs/TODO.md`.
- **Historique des événements de la fiche Circuit non cliquable** — chaque
  `CircuitEventEntry` porte déjà `championship_id`/`event_uid`, jamais interprétés à ce
  jour ; cliquer une ligne n'ouvre pas la fiche événement correspondante. Non demandé
  par le brief, identité déjà présente pour un futur sprint.
- Quand `circuit_name` est masqué pour un événement précis (redondance avec le titre —
  bug F2/F3 documenté depuis le Sprint 32), rien n'est cliquable sur cet événement-là,
  même si le circuit existe par ailleurs dans la base de données (visible via un autre
  événement du même circuit dont le nom n'est pas masqué). Comportement assumé et
  cohérent avec `circuit_key` en lockstep avec `circuit_name` — jamais un clic fantôme.

---

## Session 2026-07-12 — Sprint 46 : Moteur de notifications

### Objectif
Motorsport Calendar permet désormais d'explorer les saisons, de consulter les
événements, de rechercher (Sprint 45), et de gérer les favoris (Sprint 44). Le prochain
objectif : préparer un système de notifications fiable. Aucune notification système
(Windows/Linux/macOS) n'est attendue durant ce sprint — l'objectif est de construire les
fondations. Travail attendu : créer un `NotificationService` totalement indépendant de
l'interface, capable de calculer toutes les notifications à venir à partir des données
déjà chargées, sans aucun nouvel appel réseau. Le moteur doit produire 5 types de
notification (début du week-end, première session, qualifications, sprint, course), avec
des délais configurables (exemples : 24h, 12h, 1h, 15min avant), et doit pouvoir
fonctionner sur tous les championnats ou uniquement les favoris. Architecture : créer
`gui/notification_service.py`, toute la logique dans ce service, aucune logique métier
dans les vues, aucune dépendance Flet — le moteur doit pouvoir être utilisé plus tard par
Windows/Linux/macOS sans modification. Préférences à préparer (sans interface complète,
persistées) : notifications activées, délai par défaut, favoris uniquement. Validation :
aucune notification, une notification, plusieurs notifications, favoris uniquement,
changement de fuseau horaire, changement de saison. Tests complets, zéro régression.

### Exploration préalable de l'architecture GUI
Relecture de `gui/favorites_service.py` (Sprint 44) et `gui/search_service.py` (Sprint
45) comme précédents directs d'un "service à état" dans le paquet `gui/` — le patron
"lecture des préférences au constructeur, lecture-fusion-écriture à chaque sauvegarde,
aucun singleton partagé" est directement transposable. Relecture de
`motorsport_calendar/models/session.py` : `SessionType` (StrEnum) couvre déjà
`QUALIFYING`/`SPRINT`/`RACE` — correspondance directe et sans ambiguïté avec 3 des 5
types de notification demandés par le brief ; `Session.start_datetime`/`end_datetime`
sont déjà garantis timezone-aware par un validateur Pydantic (`_validate_datetimes`),
donc aucune conversion de fuseau à gérer manuellement dans le moteur — l'arithmétique
`datetime` tz-aware de Python gère déjà correctement les comparaisons entre fuseaux.
Relecture de `gui/season_explorer.py` : `_earliest_start(event)` (session la plus
précoce d'un événement, ancrage déjà utilisé pour le tri chronologique) — candidat direct
pour ancrer "début du week-end"/"première session", faute d'une notion de "début de
week-end" distincte dans le modèle de domaine. Relecture de `gui/upcoming_weekend.py` :
`find_upcoming_weekend(..., now: datetime)` — confirme la convention déjà établie depuis
le Sprint 29 de toujours recevoir `now` en paramètre requis, jamais lu sur l'horloge
système à l'intérieur d'un module de logique pure — reprise à l'identique pour
`compute_notifications`. Relecture de `gui/event_display.py`/`gui/display_names.py` :
`normalize_event_display`/`get_display_name` restent le point de passage obligé pour
tout nom de championnat/événement affiché, y compris dans une notification. Relecture de
`gui/preferences.py` : fichier JSON unique déjà partagé, confirmant qu'ajouter 3
nouvelles clés (`notifications_enabled`/`notifications_default_lead_time_minutes`/
`notifications_favorites_only`) suffit, sans nouveau fichier de configuration.

### Travail effectué

**Nouveau `gui/notification_service.py`** — `NotificationService`, mirroring
`FavoritesService`/`SearchService`
- `NotificationKind` (StrEnum, 5 valeurs) : `WEEKEND_START`/`FIRST_SESSION`/
  `QUALIFYING`/`SPRINT`/`RACE`. `QUALIFYING`/`SPRINT`/`RACE` s'ancrent chacun sur les
  sessions de l'événement dont le `SessionType` correspond exactement (0 ou 1, jamais
  supposé exactement 1) ; `WEEKEND_START`/`FIRST_SESSION` s'ancrent tous deux sur la
  session la plus précoce (même instant) — décision assumée et documentée en ADR-037,
  faute d'une notion de "début de week-end" distincte dans le modèle de domaine.
- `Notification` (dataclass frozen) : `kind`, `championship_id`, `championship_name`,
  `event_name`, `session_start`, `lead_time`, `trigger_at` — purement structuré, aucun
  message formaté (la mise en forme reste un souci de présentation pour un futur
  consommateur GUI ou système, jamais de ce service, cohérent avec "aucune dépendance
  Flet").
- `NotificationService.__init__` lit les 3 préférences depuis `gui/preferences.py`
  (`enabled`/`default_lead_time`/`favorites_only`, exposées en propriétés) ;
  `set_enabled`/`set_default_lead_time`/`set_favorites_only` les persistent en
  lecture-fusion-écriture, même discipline que `FavoritesService._save()`.
- `compute_notifications(year_events, *, now, lead_times=None, kinds=None,
  favorites_only=None, favorite_ids=frozenset())` : `now` requis (jamais lu sur
  l'horloge système, même convention que `find_upcoming_weekend`) ; `lead_times` accepte
  n'importe quelle combinaison de délais simultanément (les 4 exemples du brief
  fonctionnent en un seul appel) ; `kinds` (`None` = les 5 types) ajouté au-delà de ce
  que demandait littéralement le brief, nécessaire pour isoler un seul type dans les
  tests "une notification"/"plusieurs notifications" (un événement mono-session est
  structurellement toujours `WEEKEND_START` + `FIRST_SESSION` + son propre type
  spécifique, jamais un seul, sans un filtre) — voir ADR-037 ; `favorites_only`/
  `favorite_ids` restreint aux championnats favoris si demandé, sinon fonctionne sur
  tous les championnats de `year_events`. Seules les notifications dont l'instant de
  déclenchement (`session.start_datetime - lead_time`) est encore dans le futur
  (`trigger_at >= now`) sont retournées — jamais une notification déjà due. Résultat
  trié du plus proche au plus lointain, égalités départagées par nom de championnat puis
  d'événement puis type — sortie déterministe pour une entrée identique.
- Aucun index persistant à reconstruire (contrairement à `SearchService`) : chaque appel
  à `compute_notifications` est un calcul frais sur le `year_events` fourni — le
  scénario "changement de saison" ne peut structurellement pas faire fuiter l'ancienne
  saison, il n'y a rien à invalider entre deux appels.

**`gui/preferences.py`** — 3 nouvelles clés, sans nouveau fichier
- `_DEFAULTS["notifications_enabled"] = False`, `_DEFAULTS[
  "notifications_default_lead_time_minutes"] = 60`, `_DEFAULTS[
  "notifications_favorites_only"] = False` — persistance centralisée sur le fichier
  existant (`gui_prefs.json`), même fichier que `favorite_championships` (Sprint 44).

**Aucune interface construite** — conforme au brief
- Pas de `gui/views/notifications.py`, aucune destination de navigation ajoutée,
  `main_view.py` non modifié. Le service existe et est entièrement testé mais n'est
  câblé nulle part — décision directement dictée par le brief ("L'objectif est de
  construire les fondations"), documentée comme piste explicite dans `docs/TODO.md`.

### Tests
- `tests/test_gui_notification_service.py` (créé, 31 tests) : préférences par défaut
  (désactivé, délai 1h, pas favoris uniquement) et leur persistance (`set_enabled`/
  `set_default_lead_time`/`set_favorites_only`, fichier partagé, ne clobber jamais une
  clé sœur) ; aucune notification (`year_events` vide, événement sans session,
  notification déjà due, session entièrement passée) ; une notification (filtre `kinds`
  isolant un seul type, tous les champs de `Notification` vérifiés) ; plusieurs
  notifications (délais multiples produisant une notification chacun, événements
  multiples, tri du plus proche au plus lointain) ; les 5 types de notification un par
  un (`WEEKEND_START`/`FIRST_SESSION` co-ancrés sur la même session, `QUALIFYING`/
  `SPRINT`/`RACE` chacun sur son propre type de session, un événement sans sprint ne
  produit aucune notification Sprint, les 5 types calculés par défaut) ; favoris
  uniquement (toutes les championnats par défaut, restriction à un ensemble de favoris,
  aucun favori → aucun résultat, préférence persistée utilisée quand non explicitement
  outrepassée) ; changement de fuseau horaire (session construite avec `ZoneInfo("Asia/
  Tokyo")`, résultat identique à son équivalent UTC construit indépendamment ; `now`
  lui-même dans un fuseau non-UTC filtre toujours correctement ; une session proche mais
  hors délai reste exclue même loin de l'UTC — pas de double standard) ; changement de
  saison (même instance de service, deux appels avec des `year_events` différents,
  aucune fuite de l'ancienne saison).
- `tests/test_gui_preferences.py` (+2 tests) : les 3 clés `notifications_*` par défaut
  sur premier lancement, préservées aux côtés des autres clés.

### Fichiers modifiés / créés

| Fichier | Action |
|---|---|
| `motorsport_calendar/gui/notification_service.py` | Créé |
| `motorsport_calendar/gui/preferences.py` | Modifié — 3 clés `notifications_*` |
| `tests/test_gui_notification_service.py` | Créé — 31 tests |
| `tests/test_gui_preferences.py` | Modifié — 2 tests ajoutés |
| `CHANGELOG.md` | Mis à jour |
| `docs/ROADMAP.md` | Mis à jour — v0.4.20 |
| `docs/AI_CONTEXT.md` | Mis à jour |
| `docs/TODO.md` | Mis à jour |
| `docs/DECISIONS.md` | ADR-037 ajouté |

`motorsport_calendar/core/`, `providers/`, `exporters/`, `models/` (domaine, non
modifié — `SessionType` couvrait déjà tout le nécessaire), `gui/main_view.py` (aucune
interface câblée ce sprint, conforme au brief), `gui/strings.py` (aucune chaîne
utilisateur nécessaire, aucune vue construite), `gui/favorites_service.py`,
`gui/search_service.py`, `gui/calendar_selection.py`, `gui/season_explorer.py`,
`gui/event_details.py`, `gui/event_display.py`, `gui/display_names.py`,
`gui/components/*`, `gui/theme.py`, `gui/views/*`, `docs/DATA_SOURCES.md` (aucune
nouvelle source de données ce sprint) : **non modifiés**.

### Tests exécutés
```
1732 passed → 1765 passed — 0 failed
```

Vérification ruff sur les fichiers neufs/modifiés
(`gui/notification_service.py`/`gui/preferences.py`/
`tests/test_gui_notification_service.py`/`tests/test_gui_preferences.py`) : "All checks
passed!" du premier coup, aucune correction nécessaire.

Vérification mypy : `gui/notification_service.py` passe à **0 erreur**.
`gui/preferences.py` conserve ses 3 erreurs `dict` sans paramètres de type
(`type-arg`) déjà préexistantes avant ce sprint, comptage inchangé — seules 3 nouvelles
clés ont été ajoutées à `_DEFAULTS`, jamais leur typage.

Vérification manuelle additionnelle (vrais appels réseau, pas de mock) : championnats et
événements réels de l'année 2026 récupérés via `controller.list_championships()`/
`await controller.get_calendar_year_events(2026)` (17 championnats, 171 événements),
puis passés à `NotificationService.compute_notifications()` — appel par défaut (délai 1h,
les 5 types, tous les championnats) → 336 notifications à venir, la première
correspondant réellement à la prochaine course chronologique du jeu de données réel ;
appel avec 3 délais simultanés restreint à Qualifications+Course → 447 notifications ;
appel favoris uniquement (`formula1`, `motogp`) → 110 notifications, toutes bien
restreintes à ces deux championnats ; vérification finale que `trigger_at >= now` pour
chaque résultat du premier appel — aucune notification déjà due n'a fuité.

### Limites
- **Aucune interface construite** — ni page dédiée, ni destination de navigation, ni
  notification système réelle (Windows/Linux/macOS) : explicitement hors périmètre du
  brief de ce sprint ("construire les fondations" uniquement), piste documentée dans
  `docs/TODO.md` pour un futur sprint.
- `WEEKEND_START`/`FIRST_SESSION` s'ancrent actuellement sur le même instant (la session
  la plus précoce d'un événement) — le modèle de domaine n'a pas de notion de "début de
  week-end" distincte à ce jour ; décision assumée et documentée (ADR-037), pas une
  confusion entre les deux types.
- `kinds` (quels types de notification sont activés) reste un paramètre d'appel, pas
  encore une préférence persistée — seules les 3 préférences explicitement demandées par
  le brief (activées, délai par défaut, favoris uniquement) le sont.
- Aucune notification système réelle n'est envoyée — le moteur ne fait que calculer une
  liste structurée de `Notification`, jamais un appel `notify-send`/Toast/`osascript` ou
  équivalent. Conforme au brief, pas un oubli.

---

## Session 2026-07-12 — Sprint 45 : Recherche globale

### Objectif
Motorsport Calendar dispose désormais d'un Dashboard, d'un explorateur de saison, d'une
fiche événement, d'un système de favoris, et de 17 championnats intégrés. Le volume de
données justifie une recherche globale. Travail attendu : créer un `SearchService` dédié,
fonctionnant sans aucun appel réseau supplémentaire, exploitant uniquement les données
déjà chargées ; retrouver championnats, événements et circuits ; recherche sur nom
complet, nom partiel, insensible à la casse et aux accents (exemples explicites du
brief : spa/Spa/SPA/spa francorchamps ; Le Mans/lemans ; Moto/MotoGP ; Formula ; GT) ;
résultats regroupés par type, triés par pertinence puis alphabétiquement ; nouvelle page
"Recherche", destination de navigation au même titre que les 6 autres pages ; recherche
instantanée pendant la saisie ; `EmptyState` si aucun résultat ; index réutilisable,
jamais reconstruit depuis les providers à chaque frappe. Contraintes explicites : aucun
nouveau provider, aucune nouvelle source de données, aucune logique métier dans la vue,
réutiliser les modèles existants, aucune évolution graphique, aucun travail sur les
icônes. Validation : recherche vide, championnat, événement, circuit, partielle, casse
différente, accents, aucun résultat. Tests complets, zéro régression.

### Exploration préalable de l'architecture GUI
Relecture de `gui/event_display.py` (Sprint 32, ADR-023) : `normalize_event_display`
transforme déjà un `Event` domaine en `EventDisplayData` display-ready (nom d'épreuve,
circuit, pays), avec la même discipline "jamais de doublon, jamais de 'Unknown'" que le
reste de l'application — c'est le point de passage obligé pour indexer un événement,
jamais `event.name`/`circuit.name` lus directement. Relecture de `gui/display_names.py`
pour les noms de championnat. Relecture de `controller.py` : deux pipelines de fetch
distincts existent — `_fetch_weekend_entries` (17 championnats "Ce week-end", fenêtre de
2 ans) et `get_calendar_year_events(year)` (tous les championnats enregistrés, une année),
ce dernier alimentant déjà "Mon calendrier" depuis le Sprint 40 — candidat naturel pour la
recherche, car il couvre déjà l'intégralité des championnats, pas seulement les 17
"week-end". Relecture de `gui/favorites_service.py` (Sprint 44) comme précédent direct
d'un "service à état" dans le paquet `gui/` — patron transposable à un index de recherche.
Recherche du mot "Recherche" dans la suite de tests existante :
`test_gui_components_layout.py::TestLayoutSystemIntegration` contient déjà, depuis le
Sprint 31, une composition illustrative `PageHeader("Recherche", icon=ft.Icons.SEARCH,
subtitle="3 résultats")` + `Section`/`CardList` — confirmant l'icône et la composition à
suivre plutôt que d'en inventer une nouvelle. Vérification live avant d'écrire la moindre
ligne de logique de normalisation : test rapide en `python -c` comparant plusieurs
stratégies de normalisation contre les exemples exacts du brief ("Le Mans" vs "lemans",
"spa francorchamps" vs "Spa-Francorchamps") — une normalisation légère (accents/casse
seuls) échoue sur les deux ; seule une normalisation "compacte" (suppression de tout
caractère non alphanumérique) les satisfait toutes les deux.

### Travail effectué

**Nouveau `gui/search_service.py`** — `SearchService`, mirroring `FavoritesService`
- `_normalize(text)` : `unicodedata.normalize("NFKD", text)` + suppression des marques
  combinantes (accents) + `casefold()` + filtrage pour ne garder que les caractères
  alphanumériques — validé en direct contre les exemples exacts du brief avant d'écrire
  le reste du module (voir ADR-036).
- `SearchResultItem(title, subtitle)` / `SearchResults(championships, events, circuits)`
  (`total_count`, `is_empty`) — dataclasses frozen, display-ready, jamais un `Event`/
  `Championship`/`Circuit` domaine exposé au-delà de `build_index()`.
- `_IndexedItem(item, normalized)` / `_SearchIndex` (privés) : chaque entité indexée porte
  sa forme normalisée précalculée — un `search()` ne renormalise jamais tout le jeu de
  données à chaque frappe, seulement la requête.
- `_relevance(query, normalized)` : 0 = correspondance exacte, 1 = préfixe, 2 = sous-chaîne
  ailleurs — clé de tri primaire ; `_matches()` trie ensuite par `(pertinence,
  title.casefold())`, satisfaisant "trié par pertinence puis alphabétiquement".
- `SearchService.build_index(championship_ids, year_events)` : construit un nouvel
  `_SearchIndex` immuable à partir des championnats enregistrés (toujours cherchables,
  indépendamment de `year_events`) et des événements de l'année courante — réutilise
  `display_names.get_display_name`/`event_display.normalize_event_display`, jamais de
  seconde normalisation d'affichage inventée. Circuits dédupliqués par nom normalisé
  (premier occurrence conservée) — le même circuit accueille plusieurs
  événements/années, jamais affiché en double.
- `SearchService.search(query)` : requête vide (ou uniquement des espaces) → aucun
  résultat, jamais "tout afficher" (une sous-chaîne vide correspondrait trivialement à
  tout). Sinon, `_matches()` appliqué indépendamment à chaque groupe — purement
  O(taille de l'index), jamais un nouveau parcours des providers.

**Chaînes de `gui/strings.py`** — bloc dédié
- `nav_search` (destination de navigation), `search_hint`, `search_results_count`
  (pluralisation via `plural()`, même patron que `favorites_count`),
  `search_section_championships`/`_events`/`_circuits`, `search_empty_query`
  ("commencez à taper" — recherche vide) et `search_no_results` ("aucun résultat" —
  recherche sans correspondance), deux messages distincts pour deux scénarios de
  validation séparés du brief.

**Nouvelle `gui/views/search.py`** — pure mise en page
- `build_search_view(search_field, results, has_query)` : `PageHeader(STRINGS.nav_search,
  icon=ft.Icons.SEARCH, subtitle=...)` — sous-titre "N résultat(s)" affiché seulement
  quand une recherche a été saisie et a des résultats — puis, pour chaque groupe non vide,
  `Section(SectionHeader(label), CardList([...]))` ; `EmptyState` sinon, message dépendant
  de `has_query`. Le champ de recherche lui-même est injecté depuis `main_view.py` (même
  patron que `year_dropdown`/`output_field` sur "Mon calendrier") — cette vue ne construit
  aucun contrôle interactif, ne décide d'aucun tri/filtrage, se contente d'arranger ce que
  `SearchService` lui fournit déjà groupé/trié.
- Aucun nouveau composant créé : entièrement composé du Layout System existant
  (`PageContainer`/`PageHeader`/`Section`/`SectionHeader`/`CardList`/`EmptyState`) et de
  `theme.card()` pour chaque ligne de résultat (titre + sous-titre optionnel, même
  structure minimale qu'une ligne d'explorateur de saison).

**`main_view.py`** — recherche câblée, index reconstruit à deux points précis
- `search_service = SearchService()` construit une fois pour toute la session.
- `build_index()` appelé à deux endroits seulement : une fois au démarrage (avec
  `year_events or {}`, pour que les championnats soient cherchables immédiatement même
  avant que le fetch en arrière-plan ne résolve) et une seconde fois dans
  `_load_year_events(year)` à chaque résolution d'année — jamais à chaque frappe, jamais à
  chaque coche de championnat (qui ne modifie pas `year_events`). `_refresh_search_view()`
  appelé aux deux mêmes points pour qu'une recherche déjà affichée à l'écran ne reste
  jamais périmée après un changement d'année.
- Nouvelle section "SEARCH CONTROLS" : `search_container` (comme les autres conteneurs de
  page), `current_search_query` (état local, fermé dans les handlers),
  `_on_search_query_change(e)` déclenchant `_refresh_search_view()` à chaque frappe —
  recherche instantanée, aucun debounce nécessaire (recherche en mémoire, coût
  négligeable même sur le jeu de données complet).
- Nouvelle destination de navigation `nav_rail.destinations` : insérée entre "Mon
  calendrier" et "Mes favoris" (aucune position n'étant imposée par le brief) ;
  `search_container` inséré au même rang dans `all_views`.

### Tests
- `tests/test_gui_search_service.py` (créé, 29 tests) : recherche vide (index vide, index
  peuplé, requête blanche, avant tout `build_index()`) ; recherche championnat/
  événement/circuit ; déduplication des circuits entre événements ; recherche partielle,
  insensible à la casse (minuscule/majuscule), insensible aux accents ; aucun résultat
  (requête sans correspondance, tous les groupes vides) ; les exemples exacts du brief un
  par un (spa/Spa/SPA/spa francorchamps, Le Mans/lemans, Moto/MotoGP, Formula, GT — sur
  des fixtures réelles construites avec les vrais ids de championnat et noms d'affichage
  du projet) ; tri par pertinence (exact > préfixe > sous-chaîne) puis alphabétique ;
  reconstruction de l'index (remplace, ne cumule jamais l'ancien contenu).
- `tests/test_gui_views.py::TestSearchView` (créé, 17 tests) : import, retour `ft.Control`,
  `expand=True`, largeur de grille partagée, icône `ft.Icons.SEARCH` dans l'en-tête, champ
  de recherche en première position du corps, `EmptyState` "aucune saisie" vs "aucun
  résultat" (deux scénarios de validation distincts), sous-titre absent sans requête ou
  sans résultat, présent et pluralisé avec des résultats, chaque section (championnats/
  événements/circuits) affichée avec ses éléments et omise si vide, les trois sections
  simultanément.
- `TestAllViewsShareTheSameGrid._all_views()` : `build_search_view(ft.TextField(),
  SearchResults(), False)` ajouté à la liste — la nouvelle page respecte le même contrat
  de grille que les 6 autres, vérifié par les 5 tests déjà existants de cette classe sans
  aucune modification de leur corps.

### Fichiers modifiés / créés

| Fichier | Action |
|---|---|
| `motorsport_calendar/gui/search_service.py` | Créé |
| `motorsport_calendar/gui/views/search.py` | Créé |
| `motorsport_calendar/gui/strings.py` | Modifié — bloc de chaînes recherche |
| `motorsport_calendar/gui/main_view.py` | Modifié — index câblé, champ de recherche, navigation |
| `tests/test_gui_search_service.py` | Créé — 29 tests |
| `tests/test_gui_views.py` | Modifié — `TestSearchView` (17 tests) + `_all_views()` étendu |
| `CHANGELOG.md` | Mis à jour |
| `docs/ROADMAP.md` | Mis à jour — v0.4.19 |
| `docs/AI_CONTEXT.md` | Mis à jour |
| `docs/TODO.md` | Mis à jour |
| `docs/DECISIONS.md` | ADR-036 ajouté |

`motorsport_calendar/core/`, `providers/`, `exporters/`, `models/` (domaine),
`gui/calendar_selection.py`, `gui/season_explorer.py`, `gui/event_details.py`,
`gui/event_display.py`, `gui/display_names.py`, `gui/favorites_service.py`,
`gui/components/championship_card.py`, `gui/components/championship_selector.py`,
`gui/theme.py`, `gui/components/layout/*`, `gui/categories.py`, `gui/preferences.py`,
`gui/models.py`, `gui/controller.py`, `gui/views/dashboard.py`/`weekend.py`/`calendar.py`/
`favorites.py`/`preferences.py`/`about.py`, `docs/DATA_SOURCES.md` (aucune nouvelle
source de données ce sprint) : **non modifiés**.

### Tests exécutés
```
1686 passed → 1732 passed — 0 failed
```

Vérification ruff sur les fichiers neufs/modifiés : 2 problèmes d'imports non triés
introduits (`gui/search_service.py`, `tests/test_gui_search_service.py`) — corrigés
immédiatement avec `ruff check --fix`. Reste du code neuf entièrement propre (`ruff check
motorsport_calendar/gui/search_service.py motorsport_calendar/gui/views/search.py
tests/test_gui_search_service.py` → "All checks passed!"). Les problèmes ruff restants
détectés lors d'un balayage plus large (`noqa` non utilisés / `ANN001` / `UP037` /
`C408`) préexistent tous dans du code non touché par ce sprint (dialogue de succès,
`on_page_resize`, `Strings.from_dict`, `TestDashboardView` — vérifié ligne par ligne).

Vérification mypy : `gui/search_service.py` et `gui/views/search.py` passent tous deux à
**0 erreur**. `main_view.py` compte 19 erreurs au total (même famille tolérée depuis le
Sprint 26, signatures `on_click`/`on_change` Flet 0.80 code vs 0.85.3 installé) — 1 seule
nouvelle occurrence attribuable à ce sprint (`search_field.on_change=
_on_search_query_change`), pas une nouvelle catégorie, cohérente avec le traitement déjà
appliqué à ce type d'erreur aux Sprints 43/44.

Vérification manuelle additionnelle (vrais appels réseau, pas de mock) : import direct de
`SearchService`, `build_index()` avec les championnats réels
(`controller.list_championships()`) et les événements réels de l'année 2026
(`await controller.get_calendar_year_events(2026)`), puis chaque exemple explicite du
brief passé à `search()` un par un — `spa`/`Spa`/`SPA` → 13 résultats identiques (12
événements + le circuit "Spa-Francorchamps") ; `spa francorchamps` → 3 résultats (2
événements + le circuit) ; `Le Mans`/`lemans` → 4 résultats identiques (2 championnats :
"Michelin Le Mans Cup"/"European Le Mans Series" + 1 événement + 1 circuit) ; `Moto` → 4
résultats (MotoGP/Moto2/Moto3 + 1 circuit) ; `MotoGP` → exactement 1 (le championnat seul,
pas Moto2/Moto3) ; `Formula` → 4 championnats (Formula 1/2/3/E) ; `GT` → 6 résultats (les
4 championnats GT World Challenge/Intercontinental + 2 événements) ; requête vide et
requête absurde (`xyzxyz`) → 0 résultat dans les deux cas. Chaque jeu de résultats ensuite
passé à `build_search_view()` pour confirmer un rendu sans erreur (`isinstance(view,
ft.Control)`). `build_main_view()` exécuté de bout en bout avec une fausse `Page` Flet et
un fichier de préférences isolé dans un répertoire temporaire — aucune erreur, tâches de
fetch en arrière-plan démarrées normalement, `search_container` correctement inséré dans
`all_views` au même rang que la nouvelle destination de navigation.

### Limites
- **Aucune vérification visuelle réelle** (rendu Flet sur un poste avec affichage) —
  même limitation que chaque sprint GUI précédent.
- La recherche ne couvre que l'année actuellement parcourue sur "Mon calendrier"
  (`year_events`), jamais un historique multi-année — limite de périmètre assumée et
  documentée (voir ADR-036), cohérente avec "aucun appel réseau supplémentaire", pas un
  bug.
- Aucun clic-through depuis un résultat de recherche vers la fiche événement (Sprint 42)
  ou la page du championnat correspondant — résultats en lecture seule, non demandé par
  le brief ("aucune évolution graphique"), piste documentée dans `docs/TODO.md` pour un
  futur sprint.
- Aucun historique des recherches précédentes — piste documentée, pas construite par
  anticipation.

---

## Session 2026-07-12 — Sprint 44 : Favoris intelligents

### Objectif
"Mes favoris" était un placeholder depuis le Sprint 31. Ce sprint en fait une
fonctionnalité centrale : l'utilisateur définit ses championnats favoris, qui deviennent
une préférence globale de l'application. Travail attendu : créer un modèle persistant
des favoris (ajouter/retirer/retrouver au prochain lancement) ; intégrer automatiquement
partout — Dashboard (favoris en priorité, week-end favori en premier), Ce week-end
(cartes triées favoris d'abord), Mon calendrier (pré-sélection automatique), Mes favoris
(vraie page de gestion). Contraintes explicites : créer un `FavoritesService` dédié,
aucune logique métier dans les vues, ne pas dupliquer le code de sélection des
championnats, réutiliser les modèles existants, persistance centralisée, aucun nouveau
composant si ceux existants suffisent, aucune évolution graphique majeure, aucun nouveau
provider. Validation : aucun favori, un favori, plusieurs favoris, suppression,
persistance après redémarrage, Dashboard/Ce week-end/Mon calendrier mis à jour. Tests
complets, zéro régression.

### Exploration préalable de l'architecture GUI
Relecture de `gui/preferences.py` (fichier JSON unique déjà partagé pour
`selected_championships`/`last_output_dir`) et de `gui/models.py::PreferencesModel`
(champ `favorite_championships: tuple[str, ...] = ()` déjà anticipé depuis les tout
premiers sprints GUI, jamais branché à quoi que ce soit de réel — confirmant que ce
sprint complète une intention déjà présente dans l'architecture plutôt que d'en inventer
une nouvelle). Relecture de `gui/views/calendar.py` (Sprint 43) : la toute nouvelle
interface de sélection de championnats (accordéons par catégorie, boutons
sélectionnables) est structurellement identique à ce que "Mes favoris" a besoin —
signal fort pour une extraction plutôt qu'une reconstruction, cohérent avec la consigne
"ne pas dupliquer le code de sélection". Relecture de `gui/upcoming_weekend.py`/
`gui/dashboard.py`/`gui/controller.py` : `DashboardData.weekend` est littéralement un
`upcoming_weekend.WeekendResult` (même pipeline que "Ce week-end" depuis le Sprint 39,
ADR-030) — un seul point d'insertion pour "favoris en premier" suffit à satisfaire les
deux pages. Recherche d'un précédent "service à état" dans le projet :
`config/service.py::ConfigService` (construit frais, méthodes sémantiques plutôt que
manipulation de dict brut) — patron directement transposable à `FavoritesService`.
Vérification critique avant d'écrire le moindre test : un vrai fichier
`~/.config/motorsport-calendar/gui_prefs.json` existe sur cette machine de
développement (issu de l'usage réel du projet pendant les sprints précédents) — risque
de non-déterminisme des tests si `FavoritesService` (ou tout futur test) le lit sans
isolation explicite.

### Travail effectué

**Bug latent découvert et corrigé : `_save_prefs()` effaçait silencieusement d'autres
clés**
En traçant comment une nouvelle clé `favorite_championships` cohabiterait avec le
fichier de préférences existant, constat que `main_view.py::_save_prefs()` appelait
`save_preferences({"selected_championships": ..., "last_output_dir": ...})` — un
dictionnaire littéral neuf à chaque sauvegarde, qui écrase **toute** clé non listée.
N'importe quel favori sauvegardé aurait été silencieusement effacé au prochain
cochage/décochage d'un championnat sur "Mon calendrier". Corrigé en lecture-fusion-
écriture : `_save_prefs()` relit `load_preferences()` frais, ne remplace que les deux
clés qu'il possède, sauvegarde le dictionnaire complet. `FavoritesService._save()` suit
la même discipline pour sa propre clé. Cette règle est désormais documentée comme
contrat obligatoire dans le docstring de `gui/preferences.py`.

**`gui/preferences.py`** — nouvelle clé, sans nouveau fichier
- `_DEFAULTS["favorite_championships"] = []` — persistance centralisée sur le fichier
  existant (`gui_prefs.json`), jamais un second fichier de configuration.

**Nouveau `gui/favorites_service.py`** — `FavoritesService`, mirroring `ConfigService`
- Seul module `gui/*.py` de ce sprint à être une classe plutôt qu'une collection de
  fonctions : les favoris ont un état mutable qui doit survivre entre plusieurs appels
  (`add`/`remove`/`toggle`/`list`), contrairement aux modules "compute" purs établis
  depuis le Sprint 39 qui n'ont besoin que des données déjà fournies par l'appelant.
- `list()` (ordre d'insertion), `is_favorite()`, `add()`/`remove()` (no-op si déjà dans
  l'état visé), `toggle()`. Chaque mutation fait une lecture-fusion-écriture complète —
  jamais un littéral neuf, même règle que la correction de `_save_prefs()`.
- Construit frais partout où nécessaire (jamais un singleton partagé), comme
  `ConfigService()` — une lecture disque locale par utilisation, coût déjà accepté
  ailleurs dans le projet.

**Extraction `gui/components/championship_selector.py`** — deuxième composant du paquet
- `ChampionshipButtonData`/`ChampionshipCategoryData`/`build_championship_selector`
  (+ `_championship_button`/`_category_accordion` privés) déplacés depuis
  `gui/views/calendar.py` (Sprint 43) une fois "Mes favoris" devenu un second
  consommateur réel de l'accordéon-de-boutons-sélectionnables — même principe de
  mutualisation-au-second-usage que `_fetch_weekend_entries` (Sprint 39) ou
  `session_type_label` (Sprint 42).
- Le composant reste indifférent à ce que "sélectionné" signifie : "Mon calendrier"
  l'utilise pour "choisi pour cette génération", "Mes favoris" pour "favori" — aucune
  connaissance de `GenerateState` ni de `FavoritesService` dans le composant lui-même.
- `gui/views/calendar.py` importe désormais `build_championship_selector` au lieu de
  redéfinir `_championships_section` — comportement strictement inchangé, vérifié par la
  suite de tests existante intégralement verte après le déplacement.

**Nouveau `gui/views/favorites.py`** — vraie page, plus un placeholder
- `build_favorites_view(category_groups, favorite_count, on_favorite_click,
  on_category_toggle)` : `PageHeader` (sous-titre "N favoris", réutilise le slot déjà
  existant, aucun nouveau composant) + `build_championship_selector(...)` — rien
  d'autre, conforme à "aucun nouveau composant si ceux existants suffisent".
- Chaînes `favorites_empty`/`favorites_coming_soon` (placeholder) retirées, devenues
  mortes ; nouvelle chaîne `favorites_count`.

**Tri "favoris en premier" — `upcoming_weekend.py` + `dashboard.py`**
- `_group_entries_for_display(entries, favorite_ids)` : tri stable après le regroupement
  par catégorie existant — les favoris passent devant, leur ordre relatif (catégorie puis
  chronologique) est préservé entre eux, comme celui des non-favoris entre eux.
- `find_upcoming_weekend(..., favorite_ids=frozenset())` : nouveau paramètre optionnel,
  purement additif.
- `build_dashboard_data(..., favorite_ids=frozenset())` : transmis tel quel à
  `find_upcoming_weekend` — aucune logique de tri propre au Dashboard, une seule
  implémentation partagée par construction.

**`controller.py`** — `FavoritesService` construit en interne
- `get_upcoming_weekend()`/`get_dashboard_data()` construisent `FavoritesService()`
  (comme `ConfigService()` l'est déjà dans `_fetch_weekend_entries`) et lui passent
  `favorite_ids` — signature d'appel inchangée côté `main_view.py`.

**`main_view.py`** — favoris comme préférence globale
- `favorites_service = FavoritesService()` construit une fois pour toute la session.
- Pré-sélection "Mon calendrier" : `state.selected_championships` initialisé depuis
  `favorites_service.list()` s'il n'est pas vide, sinon repli sur l'ancien comportement
  mémorisé (`prefs.get("selected_championships", DEFAULT_SELECTED)`) — un seed initial au
  lancement, pas une synchronisation continue pendant la session (forcer la sélection
  active à chaque changement de favori aurait silencieusement écrasé une personnalisation
  en cours, non demandé par le brief).
- `favorites_container` (nouveau, comme `calendar_container`/`weekend_container`/
  `dashboard_container`) remplace l'appel statique `build_favorites_view()` d'avant ce
  sprint. `_current_favorites_groups()`/`_on_favorite_click()`/
  `_on_favorites_category_toggle()` : mêmes patrons que leurs équivalents "Mon
  calendrier" (`_current_category_groups`/`_on_championship_click`/
  `_on_category_toggle`), avec un tracker d'accordéons ouverts séparé
  (`favorites_expanded_categories`) — pages indépendantes, états indépendants.
- Basculer un favori (`_on_favorite_click`) déclenche `_load_weekend()`/
  `_load_dashboard()` de nouveau (mêmes fonctions que le chargement initial, cache HTTP
  existant absorbant le coût réseau) plutôt qu'un tri local des données déjà
  récupérées — garantit qu'il n'existe qu'une seule implémentation du tri favoris,
  jamais une variante "live" divergente de celle utilisée au chargement initial.

**Isolation des tests** — `tests/conftest.py`
- Nouvelle fixture `autouse` `_isolated_gui_prefs` : redirige
  `preferences._PREFS_FILE` vers un répertoire temporaire pour toute la suite —
  corrige un risque de non-déterminisme réel (le fichier de préférences de cette machine
  de développement contenait déjà des données de sessions précédentes) avant qu'il ne
  cause un test instable, sur cette machine ou une autre.

### Tests
- `tests/test_gui_favorites_service.py` (créé, 19 tests) : aucun favori par défaut,
  ajout (un, plusieurs, ordre d'insertion préservé, idempotent), suppression (un,
  préserve les autres, no-op sur un non-favori), toggle (ajoute/retire/aller-retour),
  persistance après redémarrage (nouvelle instance simulant un relancement de
  l'application) avec et sans favoris, persistance centralisée (même fichier que le
  reste des préférences, ne clobber jamais une clé sœur, résiste à une sauvegarde
  ultérieure d'une autre clé).
- `tests/test_gui_components_championship_selector.py` (créé, 15 tests) : déplacé depuis
  `test_gui_views.py::TestCalendarViewChampionships`, adapté aux nouveaux chemins
  d'import.
- `tests/test_gui_upcoming_weekend.py` (+5 tests) : aucun favori laisse l'ordre existant
  inchangé, un favori passe devant, plusieurs favoris gardent leur ordre relatif, tous
  favoris laisse l'ordre inchangé, un favori absent du week-end courant n'a aucun effet.
- `tests/test_gui_dashboard.py` (+3 tests) : `favorite_ids` transmis tel quel à
  `find_upcoming_weekend`, n'affecte ni les compteurs de saison ni "prochain départ".
- `tests/test_gui_controller.py` (+3 tests) : `get_upcoming_weekend`/`get_dashboard_data`
  reflètent un favori sauvegardé via `FavoritesService` sans plomberie supplémentaire au
  point d'appel (piège évité : WEC/IMSA/WorldSBK sont des stubs toujours en échec,
  non couverts par `patch_weekend_sources` — les tests utilisent Formula 1/Formula 2,
  deux championnats réellement mockables).
- `tests/test_gui_preferences.py` (+2 tests) : `favorite_championships` par défaut à
  liste vide, préservé aux côtés des autres clés.
- `tests/test_gui_views.py` : `TestFavoritesView` réécrite (page réelle, plus un
  placeholder), `TestAllViewsShareTheSameGrid._all_views()` adapté à la nouvelle
  signature de `build_favorites_view`.

### Fichiers modifiés / créés

| Fichier | Action |
|---|---|
| `motorsport_calendar/gui/favorites_service.py` | Créé |
| `motorsport_calendar/gui/components/championship_selector.py` | Créé — extrait de `views/calendar.py` |
| `motorsport_calendar/gui/preferences.py` | Modifié — clé `favorite_championships` |
| `motorsport_calendar/gui/views/calendar.py` | Modifié — réutilise le composant extrait |
| `motorsport_calendar/gui/views/favorites.py` | Réécrit — vraie page |
| `motorsport_calendar/gui/upcoming_weekend.py` | Modifié — tri favoris-en-premier |
| `motorsport_calendar/gui/dashboard.py` | Modifié — `favorite_ids` transmis |
| `motorsport_calendar/gui/controller.py` | Modifié — `FavoritesService` construit en interne |
| `motorsport_calendar/gui/main_view.py` | Modifié — favoris câblés partout, fix `_save_prefs` |
| `motorsport_calendar/gui/strings.py` | Modifié — chaînes placeholder retirées, `favorites_count` ajoutée |
| `tests/conftest.py` | Modifié — fixture `autouse` d'isolation des préférences |
| `tests/test_gui_favorites_service.py` | Créé — 19 tests |
| `tests/test_gui_components_championship_selector.py` | Créé — 15 tests (déplacés) |
| `tests/test_gui_upcoming_weekend.py` | Modifié — 5 tests ajoutés |
| `tests/test_gui_dashboard.py` | Modifié — 3 tests ajoutés |
| `tests/test_gui_controller.py` | Modifié — 3 tests ajoutés |
| `tests/test_gui_preferences.py` | Modifié — 2 tests ajoutés |
| `tests/test_gui_views.py` | Modifié — `TestFavoritesView` réécrite, `TestCalendarViewChampionships` retirée (déplacée) |
| `CHANGELOG.md` | Mis à jour |
| `docs/ROADMAP.md` | Mis à jour — v0.4.18 |
| `docs/AI_CONTEXT.md` | Mis à jour |
| `docs/TODO.md` | Mis à jour |
| `docs/DECISIONS.md` | ADR-035 ajouté |

`motorsport_calendar/core/`, `providers/`, `exporters/`, `models/` (domaine),
`gui/calendar_selection.py`, `gui/season_explorer.py`, `gui/event_details.py`,
`gui/event_display.py`, `gui/components/championship_card.py`, `gui/theme.py`,
`gui/components/layout/*`, `gui/categories.py`, `gui/display_names.py`, `gui/models.py`
(`PreferencesModel` non modifié — toujours décoratif, voir Limites),
`gui/views/dashboard.py`/`weekend.py`/`preferences.py`/`about.py`,
`docs/DATA_SOURCES.md` (aucune nouvelle source de données ce sprint) : **non modifiés**.

### Tests exécutés
```
1650 passed → 1686 passed — 0 failed
```

Vérification ruff : 2 lignes trop longues introduites dans le nouveau
`test_gui_components_championship_selector.py` — corrigées immédiatement. Reste du code
neuf entièrement propre. Vérification mypy : `gui/favorites_service.py`/
`gui/views/favorites.py`/`gui/components/championship_selector.py` zéro erreur nouvelle
(les 2 erreurs `ExpansionTile.on_change` de `championship_selector.py` sont les 2
mêmes déjà comptées dans `gui/views/calendar.py` avant l'extraction — `calendar.py`
passe d'ailleurs à 0 erreur, confirmant un déplacement, pas un ajout) ;
`gui/preferences.py` : 3 erreurs `dict` sans type-arg déjà présentes avant ce sprint,
inchangées (seule une nouvelle clé a été ajoutée à `_DEFAULTS`, pas son typage) ;
`main_view.py` passe de 15 à 17 erreurs — exactement +2, la même famille déjà tolérée
`Page.X_load_task` (`weekend_reload_task`/`dashboard_reload_task`), pas une nouvelle
catégorie.

Vérification manuelle additionnelle (vrais appels réseau, pas de mock, fichier de
préférences isolé dans un répertoire temporaire) — les 8 scénarios de validation du
brief, un par un : aucun favori (`FavoritesService().list() == []`) ; un favori
(`add("motogp")` → `["motogp"]`) ; plusieurs favoris (`add("formula1")`, `add("wec")` →
ordre d'insertion préservé) ; suppression (`remove("wec")` → favori retiré, les autres
intacts) ; persistance après redémarrage (nouvelle instance `FavoritesService()` voit
exactement l'état de la précédente) ; Dashboard mis à jour
(`get_dashboard_data().weekend.cards` commence par le favori) ; Ce week-end mis à jour
(même ordre, même pipeline) ; Mon calendrier pré-rempli (`state.selected_championships`
initialisé depuis la liste de favoris). `build_main_view()` exécuté de bout en bout avec
une fausse `Page` Flet et un fichier de préférences isolé — aucune erreur, tâches de
fetch en arrière-plan démarrées normalement, `favorites_container` correctement inséré
dans `all_views`.

### Limites
- **Aucune vérification visuelle réelle** (rendu Flet sur un poste avec affichage) —
  même limitation que chaque sprint GUI précédent. "Mes favoris" réutilise cependant
  l'accordéon déjà en place pour "Mon calendrier" (Sprint 43), déjà dans la même
  situation — risque jugé plus bas que celui du Sprint 43 lui-même.
- `PreferencesModel.favorite_championships` (anticipé depuis les tout premiers sprints
  GUI) reste non branché à `FavoritesService` — la page Préférences (toujours un
  placeholder) n'affiche pas les vrais favoris ; explicitement hors périmètre du brief
  de ce sprint, qui ne demandait que "Mes favoris".
- Basculer un favori déclenche un nouveau `_load_weekend()`/`_load_dashboard()` complet
  (cache HTTP existant, donc sans coût réseau réel) plutôt qu'un tri purement local des
  données déjà en mémoire — choix délibéré pour garantir une seule implémentation du tri
  (voir ADR-035), documenté comme optimisation possible dans `docs/TODO.md`.
- Aucun export ICS dédié "mes favoris uniquement", aucune notification/rappel favori —
  pistes documentées pour un futur sprint, pas construites par anticipation.

---

## Session 2026-07-11 — Sprint 43 : Refonte UX de "Mon calendrier"

### Objectif
Premier sprint purement ergonomique du projet — cadré explicitement par le brief : "Le
moteur de génération est désormais mature. Les fonctionnalités sont présentes. Le
principal point faible est maintenant l'expérience utilisateur." Réorganiser
complètement la page "Mon calendrier" pour réduire fortement le défilement et rendre la
sélection plus naturelle, en remplaçant l'assistant 4 étapes (saison/championnats/
destination/créer, Sprint 26) par une page unique construite autour de 7 exigences :
(1) les championnats deviennent le point d'entrée, affichés immédiatement sous le titre ;
(2) regroupés par catégorie dans des accordéons à un seul niveau ; (3) chaque championnat
un bouton sélectionnable (jamais de case à cocher, jamais de bouton radio, sélection
multiple conservée) ; (4) la saison devient un contrôle secondaire en haut à droite ;
(5) le résumé de sélection devient permanent (championnats/événements/sessions/période) ;
(6) l'explorateur de saison ne s'affiche que si ≥ 1 championnat est sélectionné, sinon un
`EmptyState` ; (7) "Créer mon calendrier" reste toujours visible sans jamais imposer de
défilement de la page entière — solution la plus simple à choisir. Contraintes
explicites, plus strictes que les sprints précédents : aucune nouvelle fonctionnalité
métier, aucun nouveau provider, aucune modification de la logique métier, aucune
modification des modèles, aucun changement graphique global, réutiliser un maximum de
composants existants. Tests adaptés + nouveaux, zéro régression.

### Exploration préalable de l'architecture GUI
Relecture complète de `gui/main_view.py` (section "CALENDAR WIZARD CONTROLS", ~250
lignes) et `gui/views/calendar.py` (assistant 4 étapes complet, ~435 lignes) pour
cartographier précisément ce qui devait disparaître (machinerie d'étapes) vs. rester
(logique de fetch/résumé/explorateur, Sprints 40-42, entièrement conservée). Vérification
de `categories.py::get_groups_for()` : regroupe déjà les championnats par catégorie
(Formula/Endurance/GT/Moto) exactement comme demandé par le brief — aucune nouvelle
logique de regroupement nécessaire, seulement une nouvelle présentation. Recherche d'un
composant Flet d'accordéon : `ft.ExpansionTile` (Material, titre + corps repliable)
convient exactement au "un seul niveau d'accordéon" demandé — pas de nesting possible
par construction si on ne l'utilise qu'une fois par catégorie. Relecture de `theme.py` :
`theme.card(..., selected: bool = False)` existe depuis le Sprint 26/30, documenté "used
for step indicators and chosen options in the calendar wizard" — recherche (`grep
selected=True`) confirmant qu'aucun appelant ne l'utilisait réellement avant ce sprint :
exactement le "bouton sélectionnable" demandé, jamais consommé jusqu'ici. Relecture du
Layout System (`gui/components/layout/page_container.py`/`page_header.py`) : ni l'un ni
l'autre ne permettent aujourd'hui (a) un contrôle secondaire à côté du titre, ni (b) une
zone fixe qui ne défile pas avec le reste — les deux besoins structurels du sprint.
Vérification de `tests/test_gui_views.py::TestAllViewsShareTheSameGrid` : verrouille que
les 5 vues partagent strictement la même grille (largeur/padding/alignement) — contrainte
à respecter absolument pour toute extension du Layout System.

### Travail effectué

**Portée de "aucune modification de logique métier / des modèles" clarifiée**
Le retrait complet de l'assistant est impossible sans toucher `GenerateState.current_step`
et consorts. Décision : les contraintes visent le moteur de génération (`core/`,
`providers/`, `exporters/`, `controller.py`) et les modèles de domaine Pydantic
(`models/`), jamais les dataclasses d'état GUI (`gui/models.py`), déjà considérées comme
de la présentation depuis toujours. `GenerateState` perd `current_step`/`STEP_COUNT`/
`step_valid`/`can_advance`/`can_go_back` (obsolètes, la notion d'étape n'existe plus) ;
`year`/`selected_championships`/`output_path`/`is_generating`/`is_ready()` inchangés.
Aucun fichier sous `core/`, `providers/`, `exporters/`, `models/` (domaine) touché.

**Extension du Layout System — `PageHeader.trailing` / `PageContainer.footer`**
- `PageHeader(title, *, icon=None, subtitle=None, trailing=None)` : `trailing` insère un
  second contrôle dans la ligne du titre (`ft.Row(alignment=SPACE_BETWEEN)`), sans
  toucher au sous-titre ni au séparateur. `trailing=None` (5 pages sur 6) laisse le titre
  exactement comme avant.
- `PageContainer(*, header=None, body=(), footer=None)` : `footer is None` emprunte
  exactement le même chemin de code qu'avant ce sprint (`theme.page_shell(*sections)`,
  zéro branche nouvelle). `footer` fourni bascule vers une structure à deux régions —
  en-tête+corps scrollables dans un `Container(expand=True)`, pied de page fixe en
  dehors — réutilisant exactement les mêmes tokens que `page_shell`
  (`MAX_CONTENT_WIDTH`, `page_padding()`, `Spacing.SM`, alignement `TOP_CENTER`, colonne
  `STRETCH`) : un découpage structurel, pas un nouveau style visuel.
- Ces deux extensions ont été vérifiées ne rien casser via `TestAllViewsShareTheSameGrid`,
  intégralement vert sans aucune modification de ce test.

**`gui/views/calendar.py` — réécriture complète**
- Toute la machinerie d'étapes retirée : `STEP_LABELS`, `_step_indicator`,
  `_STEP_BUILDERS`, `_step_season`/`_step_championships`/`_step_destination`/
  `_step_create`, les champs `back_btn`/`next_btn`/`current_step`/`on_step_click`/
  `championship_groups`/`recap_controls` de `CalendarViewControls`.
- Nouvelles dataclasses `ChampionshipButtonData` (championship_id/display_name/selected)
  et `ChampionshipCategoryData` (category_id/label/expanded/options) — display-ready,
  mirroring le style déjà établi par `SeasonEventRow`/`ChampionshipCardData` (Sprints
  30/41) : la vue ne connaît jamais `Category`/`get_display_name`, seulement ces données
  déjà résolues.
- `_championship_button(option, on_click)` : `theme.card(text, selected=option.selected)`
  + `.on_click` assigné après coup (même patron que `_season_event_row` depuis le
  Sprint 42) — aucun nouveau composant, aucune nouvelle primitive `theme.py`.
- `_category_accordion(group, on_championship_click, on_category_toggle)` :
  `ft.ExpansionTile(title=..., controls=[Row(boutons, wrap=True)], expanded=
  group.expanded, on_change=...)` — un seul niveau, jamais de nesting.
- `_championships_section(groups, ...)` : `Section(*accordions)`, un accordéon par
  catégorie dans l'ordre de `categories.get_groups_for` (inchangé).
- `_selection_summary_block(summary, selected_count)` : signature étendue d'un paramètre
  — `selected_count` (toujours connu instantanément) affiché dans les 3 états
  (chargement/vide/peuplé), jamais gated par le fetch dont dépend le reste du résumé.
- `_season_explorer_block`/`_season_event_row` : logique de rendu **inchangée** — la
  condition "≥ 1 championnat sélectionné" (exigence 6) est déjà satisfaite par le
  comportement existant de `build_season_explorer` (une sélection vide produit déjà un
  tuple vide, déjà rendu en `EmptyState`) ; seul le placement dans la page change (plus
  de gating par étape, juste une place fixe dans la page).
- `_generate_footer(c)` : destination + "Créer" + progress ring + erreur — fusion des
  anciennes étapes 3 et 4, qui n'ont plus de raison d'être séparées sans notion d'étape.
- `build_calendar_view(c)` : `PageContainer(header=PageHeader(titre, trailing=
  year_dropdown), body=[championships, résumé, explorateur], footer=footer)`.

**`main_view.py` — remplacement des handlers du wizard**
- Retiré : `checkboxes`, `_make_on_change`, `_build_championship_groups`, `_recap_row`,
  `_build_recap_controls`, `back_btn`/`next_btn`, `on_wizard_next`/`on_wizard_back`/
  `on_step_click`.
- Ajouté : `expanded_categories: set[str]` (état des accordéons, initialisé une fois avec
  les catégories contenant une présélection — ex. `formula1` par défaut — pour que le
  choix par défaut soit visible sans clic supplémentaire, un choix de confort lié à
  l'objectif "rendre la sélection plus naturelle") ; `_on_championship_click(cid)`
  (toggle dans `state.selected_championships`) ; `_on_category_toggle(category_id,
  expanded)` (persiste l'état ouvert/fermé à travers les reconstructions complètes de la
  vue) ; `_current_category_groups()` (résout `get_groups_for`/`get_display_name`,
  construit les nouvelles dataclasses).
- `_current_selection_summary()`/`_current_season_groups()` : nouveau cas particulier
  "aucun championnat sélectionné" → résultat immédiat (résumé à zéro / tuple vide) sans
  attendre `year_events`, puisqu'il n'y a rien de significatif à charger dans ce cas —
  évite un spinner de chargement inutile pour l'état vide.
- `year_dropdown` : largeur réduite (220 → 160) et `dense=True`, cohérent avec son
  nouveau rôle de contrôle secondaire compact dans l'en-tête.

**`strings.py`** : 11 chaînes `wizard_*` supprimées (devenues mortes) ; nouvelle chaîne
`calendar_summary_championships`.

### Tests
- `tests/test_gui_models.py` : `TestGenerateStateWizard` (15 tests) retirée, remplacée
  par un test unique verrouillant l'absence des attributs de l'assistant.
- `tests/test_gui_strings.py` : `test_wizard_step_labels_still_present`/
  `test_redundant_wizard_step_titles_removed` fusionnés en un seul test verrouillant
  l'absence de toutes les chaînes `wizard_*`.
- `tests/test_gui_components_layout.py` (+9 tests) : `PageContainer(footer=...)` — no-op
  quand omis, largeur/padding/alignement identiques, colonne externe non-scrollable,
  footer hors de la région scrollable ; `PageHeader(trailing=...)` — no-op quand omis,
  trailing dans la ligne du titre, n'affecte pas la position du séparateur.
- `tests/test_gui_views.py` : `TestCalendarView`/`TestCalendarViewSelectionSummary`/
  `TestCalendarViewSeasonExplorer` adaptées (nouvelle structure de contrôles, plus de
  boucle "pour chaque étape") ; nouvelle classe `TestCalendarViewChampionships` (14
  tests) — bouton affiche le nom, style `selected` réutilisé correctement (bordure/fond),
  clic transmet le bon id, aucun `ft.Radio` utilisé nulle part, accordéon = `ExpansionTile`
  à un seul niveau (vérifié par comptage récursif), état ouvert/fermé reflété
  correctement, toggle appelle le callback, sélection multiple préservée visuellement ;
  `TestAllViewsShareTheSameGrid._all_views()` adapté à la nouvelle signature de
  `CalendarViewControls`.

### Fichiers modifiés / créés

| Fichier | Action |
|---|---|
| `motorsport_calendar/gui/models.py` | Modifié — machinerie de l'assistant retirée de `GenerateState` |
| `motorsport_calendar/gui/strings.py` | Modifié — 11 chaînes `wizard_*` retirées, 1 ajoutée |
| `motorsport_calendar/gui/components/layout/page_header.py` | Modifié — paramètre `trailing` |
| `motorsport_calendar/gui/components/layout/page_container.py` | Modifié — paramètre `footer` |
| `motorsport_calendar/gui/views/calendar.py` | Réécrit — accordéons, boutons championnat, pied de page fixe |
| `motorsport_calendar/gui/main_view.py` | Modifié — handlers de l'assistant remplacés |
| `tests/test_gui_models.py` | Modifié — `TestGenerateStateWizard` retirée |
| `tests/test_gui_strings.py` | Modifié — tests wizard fusionnés |
| `tests/test_gui_components_layout.py` | Modifié — 9 tests ajoutés |
| `tests/test_gui_views.py` | Modifié — classes adaptées + `TestCalendarViewChampionships` (14 tests) |
| `CHANGELOG.md` | Mis à jour |
| `docs/ROADMAP.md` | Mis à jour — v0.4.17 |
| `docs/AI_CONTEXT.md` | Mis à jour |
| `docs/TODO.md` | Mis à jour |
| `docs/DECISIONS.md` | ADR-034 ajouté |

`motorsport_calendar/core/`, `providers/`, `exporters/`, `models/` (domaine),
`gui/calendar_selection.py`, `gui/season_explorer.py`, `gui/event_details.py`,
`gui/event_display.py`, `gui/upcoming_weekend.py`, `gui/dashboard.py`,
`gui/controller.py`, `gui/categories.py`, `gui/display_names.py`,
`gui/components/championship_card.py`, `theme.py`, les autres vues (`weekend.py`,
`dashboard.py`, `favorites.py`, `preferences.py`, `about.py`), `docs/DATA_SOURCES.md`
(aucune nouvelle source de données ce sprint) : **non modifiés**.

### Tests exécutés
```
1639 passed → 1650 passed — 0 failed
```

Vérification ruff : 1 import inutilisé (`SeasonMonthGroup`, laissé par un test réécrit)
et 3 lignes trop longues introduites dans le code neuf — corrigées immédiatement. Reste
du code neuf entièrement propre. Vérification mypy : `gui/views/calendar.py` reste à
exactement 2 erreurs (même famille de signature `Callable[[Event[BaseControl]], ...]`
déjà tolérée ailleurs — désormais dans `ft.ExpansionTile.on_change` plutôt que dans
l'ex-`_step_indicator`, supprimé avec le reste de l'assistant) ; `main_view.py` **baisse**
de 21 à 15 erreurs — le retrait de l'assistant (`back_btn`/`next_btn`/`on_wizard_next`/
`on_wizard_back`/`on_step_click`) a supprimé plus d'occurrences de ce schéma qu'il n'en a
ajouté (2 nouvelles dans `views/calendar.py`, 6 supprimées dans `main_view.py`).

Vérification manuelle additionnelle : `build_main_view()` exécuté de bout en bout avec
une fausse `Page` Flet (aucune erreur, tâches de fetch en arrière-plan démarrées
normalement) ; pipeline de données réel (`get_calendar_year_events` → `build_
selection_summary`/`build_season_explorer`) revérifié avec une sélection vide (résumé à
zéro, 0 groupe d'explorateur) et avec `formula1` sélectionné (résumé à 26 événements/126
sessions, 11 groupes mensuels) — comportement strictement identique à celui déjà
validé aux Sprints 40-41, confirmant qu'aucune régression n'a été introduite dans la
logique réutilisée. `categories.get_groups_for` confirmé retourner 4 groupes (Formula,
Endurance, GT, Moto) sur les championnats réellement enregistrés.

### Limites
- **Aucune vérification visuelle réelle** (rendu Flet sur un poste avec affichage) — la
  même limitation que chaque sprint GUI précédent, mais avec un enjeu plus élevé cette
  fois : c'est le changement de mise en page le plus visuellement significatif du projet
  à ce jour (page entièrement réorganisée, nouveau mécanisme de pied de page fixe, nouvel
  accordéon jamais utilisé auparavant dans l'application). Documenté avec une priorité
  plus haute que d'habitude dans `docs/TODO.md`/`docs/AI_CONTEXT.md`.
- L'état ouvert/fermé des accordéons n'est pas persisté dans les préférences utilisateur
  — remis à zéro (sauf la catégorie de la présélection) à chaque lancement de
  l'application ; comportement volontairement simple, piste documentée pour un futur
  sprint.
- Aucune indication visuelle du nombre de championnats sélectionnés directement sur le
  titre de chaque accordéon (ex. badge "(2)") — non demandé par le brief, piste
  documentée pour un futur sprint.

---

## Session 2026-07-10 — Sprint 42 : Fiche événement

### Objectif
Quatrième sprint "valeur" consécutif, dans la continuité directe de l'explorateur de
saison (Sprint 41) : rendre chaque événement de la liste sélectionnable, et au clic,
afficher une fiche contenant championnat, nom de l'épreuve, circuit, pays, date, et la
liste chronologique des sessions (essais, qualifications, sprint, warm-up, course) avec
heure et type. Contraintes explicites : créer un module dédié à la logique, aucune
logique métier dans la vue, réutiliser les **modèles** existants, aucun nouveau
provider, respecter intégralement Design System/Layout System/Components, aucune
évolution graphique, aucun travail sur les icônes. Validation attendue : événement vide,
événement Formula, événement GT, événement Moto, ordre chronologique des sessions. Tests
complets, zéro régression.

### Exploration préalable de l'architecture GUI
Relecture de `gui/components/championship_card.py` (Sprint 30) : `ChampionshipCardData`
(`championship_id`, `championship_name`, `event_name`, `circuit_name`, `country`,
`sessions: tuple[SessionRow, ...]`) correspond presque exactement à la forme demandée
par le brief — une lecture littérale de "réutiliser les modèles existants" suggère donc
de construire directement ce modèle plutôt que d'en inventer un nouveau. Vérification du
modèle domaine `models/session.py::SessionType` : `FP1`/`FP2`/`FP3`/`QUALIFYING`/
`SPRINT_QUALIFYING`/`SPRINT`/`RACE`/`FREE_PRACTICE`/`TEST`/`HYPERPOLE` — **aucun
`WARM_UP`**, alors que le brief liste "Warm-up" parmi les types à afficher. Aucun
provider du projet n'en produit non plus. Conformément à "aucun nouveau provider" et à
l'esprit "réutiliser les modèles existants" (ne pas en inventer), décision : ne pas
ajouter de type au domaine — la fiche affichera fidèlement les types réellement présents
dans les données, sans jamais inventer une session "Warm-up" absente de toute source.
Relecture de `main_view.py::_show_success_dialog` : patron de boîte de dialogue déjà
établi (`ft.AlertDialog` + `page.show_dialog()`/`page.pop_dialog()`), à mirroiter plutôt
qu'à réinventer. Constat : `upcoming_weekend.py` possède déjà, en privé, la table
`SessionType -> libellé FR` (`_SESSION_LABELS`) — un second consommateur réel (la fiche)
en ayant besoin, c'est le déclencheur exact déjà établi par le projet pour mutualiser
(Sprints 39-40).

### Travail effectué

**Extraction `event_display.session_type_label()`** — sans changement de comportement
- La table `_SESSION_LABELS`/fonction `_session_type_label` d'`upcoming_weekend.py` a été
  déplacée vers `gui/event_display.py` (déjà le module canonique "comment présenter un
  événement", Sprint 32) sous le nom public `session_type_label(session) -> str`.
  `upcoming_weekend.py` importe et réutilise cette même fonction — comportement
  strictement identique, vérifié par la suite de tests existante (`test_gui_
  upcoming_weekend.py`, `test_gui_event_display.py`, `test_gui_dashboard.py`, `test_gui_
  controller.py` — 101 tests) intégralement verte après le refactor, sans qu'aucun test
  n'ait dû être modifié pour cette partie.

**Nouveau `gui/event_details.py`** — logique pure, réutilisation littérale des modèles
- Aucun import Flet, aucune I/O — l'événement est déjà fetché (il vit dans `year_events`,
  Sprint 40) ; ce module ne fait que le transformer.
- `EventDetails` (frozen dataclass) : `card: ChampionshipCardData` (réutilisée telle
  quelle, jamais redéfinie) + `date_label: str | None` — le seul champ que le modèle de
  carte ne porte pas (un intitulé de date unique au niveau de l'événement, la carte ne
  montrant que l'heure de chaque session). `None` exactement quand l'événement n'a aucune
  session — même contrat "None = rien à montrer" que `SelectionSummary` (Sprint 40).
- `build_event_details(championship_id, event) -> EventDetails` : trie les sessions par
  `start_datetime` (jamais l'ordre fourni par le provider — même règle que
  `upcoming_weekend._build_card`), délègue nom/circuit/pays à
  `event_display.normalize_event_display` (Sprint 32, ADR-023) et chaque libellé de
  session à `event_display.session_type_label` (nouveau), calcule `date_label` depuis la
  session la plus précoce convertie dans le fuseau local du circuit (weekday + JJ/MM/AAAA
  — jamais UTC, contrairement à `season_explorer.py` qui groupe par mois et peut donc
  tolérer l'ancrage UTC ; une fiche affiche un jour précis à l'utilisateur, qui doit
  correspondre à l'heure locale réelle du circuit).
- `ChampionshipCardData`/`build_championship_card` (`gui/components/championship_card.py`)
  **non modifiés** — un nouveau champ `date` y aurait affecté tous ses consommateurs
  existants ("Ce week-end", Dashboard) pour un besoin propre à ce seul nouvel usage.

**Explorateur de saison cliquable (`gui/season_explorer.py`, `gui/views/calendar.py`)**
- `SeasonEventRow` (Sprint 41) gagne 2 champs : `championship_id`/`event_uid` —
  délibérément pas l'`Event` domaine lui-même (les dataclasses "display-ready" de ce
  paquet ne portent jamais d'objet domaine, seulement des identifiants stables), juste
  assez pour qu'un clic retrouve l'événement dans `year_events`.
- `_season_event_row(row, on_click)`/`_season_explorer_block(groups, on_event_click)` :
  le callback est transmis sans être interprété — aucune logique métier dans la vue,
  même principe que `on_step_click` depuis le Sprint 26. Mécaniquement : `theme.card(...)`
  retourne déjà un `ft.Container`, qui supporte nativement `on_click` — assigné après
  construction (`card.on_click = lambda e: on_click(row)`), sans modifier `theme.py` ni
  créer de nouveau composant.
- `CalendarViewControls.on_event_click` : nouveau champ, défaut no-op comme
  `on_step_click`.

**Intégration `main_view.py`**
- `_on_event_row_click(row)` : recherche l'`Event` dans `year_events[row.championship_id]`
  par `event_uid`, puis appelle `build_event_details` + `_show_event_details_dialog`.
  Aucune requête réseau supplémentaire — l'événement cliqué est toujours déjà en mémoire.
- `_show_event_details_dialog(details)` : nouvelle boîte de dialogue, mirroir exact du
  patron déjà établi par `_show_success_dialog` (`ft.AlertDialog`, contenu scrollable,
  un seul bouton "Fermer" réutilisant `STRINGS.close_btn` existant). Réutilise
  `build_championship_card(details.card)` tel quel comme corps principal, n'ajoutant que
  la ligne `date_label` au-dessus — le composant `ChampionshipCard` n'est jamais redessiné
  à la main.
- `strings.py` : une seule nouvelle chaîne, `event_details_title`.

### Tests
- `tests/test_gui_event_details.py` (créé, 16 tests) : événement vide (sessions vides →
  `card.sessions == ()` et `date_label is None`, reste de la carte quand même peuplé),
  événement Formula (règle du suffixe "Grand Prix", liste complète FP1→FP2→FP3→
  Qualifications→Course), événement GT (pas de suffixe GP, format double manche Sprint
  Cup — Essais Libres 1/Qualifications Sprint/Sprint/Qualifications/Course dans le bon
  ordre), événement Moto (champs normalisés, y compris le repli du pays non mappé
  "Thailand" — comportement hérité d'`event_display.py`, pas un bug de ce module), ordre
  chronologique (ordre d'entrée quelconque → sortie triée, deux sessions le même jour
  triées par instant exact), format heure de session (fuseau local du circuit, repli UTC
  sur fuseau invalide) — couvre explicitement les 5 scénarios de validation du brief.
- `tests/test_gui_season_explorer.py` (+1 test) : `championship_id`/`event_uid` bien
  portés par chaque `SeasonEventRow`.
- `tests/test_gui_views.py` (+3 tests) : clic sur une ligne appelle `on_event_click` avec
  la ligne cliquée, valeur par défaut no-op de `CalendarViewControls.on_event_click`,
  câblage de bout en bout à travers `build_calendar_view` (recherche ciblée de la carte
  contenant le nom de l'événement — le distinguer des pastilles cliquables de
  l'indicateur d'étapes, elles aussi des `ft.Container` avec `on_click`, présentes depuis
  le Sprint 26).
- `tests/test_gui_upcoming_weekend.py`/`test_gui_event_display.py`/`test_gui_dashboard.py`/
  `test_gui_controller.py` : aucune modification nécessaire, exécutés pour confirmer la
  non-régression du refactor `session_type_label`.

### Fichiers modifiés / créés

| Fichier | Action |
|---|---|
| `motorsport_calendar/gui/event_details.py` | Créé |
| `motorsport_calendar/gui/event_display.py` | Modifié — ajout `session_type_label` (extrait d'`upcoming_weekend.py`) |
| `motorsport_calendar/gui/upcoming_weekend.py` | Modifié — réutilise `event_display.session_type_label`, `_SESSION_LABELS` supprimée |
| `motorsport_calendar/gui/season_explorer.py` | Modifié — `SeasonEventRow` gagne `championship_id`/`event_uid` |
| `motorsport_calendar/gui/views/calendar.py` | Modifié — lignes cliquables (`on_event_click`), wizard inchangé |
| `motorsport_calendar/gui/main_view.py` | Modifié — `_on_event_row_click`, `_show_event_details_dialog` |
| `motorsport_calendar/gui/strings.py` | Modifié — 1 chaîne `event_details_title` |
| `tests/test_gui_event_details.py` | Créé — 16 tests |
| `tests/test_gui_season_explorer.py` | Modifié — 1 test ajouté |
| `tests/test_gui_views.py` | Modifié — 3 tests ajoutés |
| `CHANGELOG.md` | Mis à jour |
| `docs/ROADMAP.md` | Mis à jour — v0.4.16 |
| `docs/AI_CONTEXT.md` | Mis à jour |
| `docs/TODO.md` | Mis à jour |
| `docs/DECISIONS.md` | ADR-033 ajouté |

`gui/components/championship_card.py` (réutilisé tel quel, non modifié), `gui/theme.py`,
`gui/championship_assets.py`, `gui/components/layout/*`, `gui/calendar_selection.py`,
`gui/dashboard.py`, `gui/views/dashboard.py`, `gui/views/weekend.py`/`favorites.py`/
`preferences.py`/`about.py`, `gui/models.py`, `gui/preferences.py`, `gui/categories.py`,
`gui/display_names.py`, `controller.py` (réutilisé tel quel), tous les providers,
`docs/DATA_SOURCES.md` (aucune nouvelle source de données ce sprint) : **non modifiés**.

### Tests exécutés
```
1619 passed → 1639 passed — 0 failed
(+20 tests — gui/event_details.py à 100 %)
```

Vérification ruff : 1 import mal trié introduit dans `main_view.py` (nouvel import
`components.championship_card` placé après `controller` au lieu d'avant) — corrigé
immédiatement (`ruff check --fix --select I001`). Reste du code neuf
(`gui/event_details.py`, `gui/event_display.py::session_type_label`, câblage clic dans
`views/calendar.py`) entièrement propre, zéro avertissement. Vérification mypy :
`gui/event_details.py` zéro erreur ; `views/calendar.py` toujours exactement 2 erreurs,
toutes deux dans `_step_indicator` (non touchée ce sprint) ; `main_view.py` passe de 20 à
21 erreurs — exactement +1, la nouvelle occurrence de `ft.Button(on_click=on_close)` dans
`_show_event_details_dialog`, qui est la même famille d'erreur (signature `on_click` Flet
0.80 vs 0.85.3) déjà présente 4 fois ailleurs dans le fichier depuis le Sprint 26 — pas
une nouvelle catégorie de dette.

Vérification manuelle additionnelle (vrais appels réseau, pas de mock) :
`get_calendar_year_events(2026)` puis `build_event_details` sur les 3 disciplines
demandées par le brief — Formula 1 (Pre-Season Testing, 3 séances d'essais libres,
Bahreïn), GT World Challenge Europe (Circuit Paul Ricard, FP1/FP2/Qualifications/Course
dans le bon ordre chronologique), MotoGP (Thaïlande, FP1/FP2/FP3/Qualifications/Sprint/
Course) — les trois rendent une fiche cohérente sans erreur, sessions correctement
triées. Cas "événement vide" testé directement (événement sans nom ni sessions) :
`date_label=None`, `card.sessions=()`, `event_name` replié sur "TBD" (repli déjà prévu
par `event_display.py`, Sprint 32) — `build_championship_card()` rend la carte sans
crash, confirmant que le composant partagé gère nativement ce cas limite sans qu'aucune
modification n'ait été nécessaire.

### Limites
- **Aucune vérification visuelle réelle** (rendu Flet sur un poste avec affichage) —
  seule la structure des contrôles a pu être vérifiée dans ce bac à sable sans écran,
  exactement la même limitation que chaque sprint GUI précédent (Sprints 26-41).
  Attention particulière à porter lors d'une future vérification visuelle : la boîte de
  dialogue (largeur fixe 400px, Sprint 42) avec un événement à beaucoup de sessions (ex.
  week-end MotoGP à 6 sessions) doit rester lisible, et le scroll interne doit fonctionner
  réellement.
- "Warm-up" (cité dans le brief) reste absent de l'application — aucune source de données
  du projet n'en fournit ; documenté comme limite connue plutôt que masqué par une
  session inventée dans le domaine.
- La fiche reste volontairement simple (exactement les champs demandés par le brief) —
  pas d'export ICS par événement, pas de lien retour vers "Ce week-end", pas de favoris
  par événement ; pistes documentées pour un futur sprint, pas construites par
  anticipation.

---

## Session 2026-07-10 — Sprint 41 : Explorer une saison

### Objectif
Troisième sprint "valeur" consécutif, dans la continuité directe du résumé de sélection
(Sprint 40) : ajouter un explorateur de saison à "Mon calendrier". À partir de la
sélection actuelle (année + championnats), afficher la liste des événements — nom,
championnat, circuit, pays, date — triée chronologiquement et regroupée naturellement
par mois, mise à jour automatiquement lorsque la sélection change. Le wizard 4 étapes
existant doit rester intact. Contraintes explicites : créer un module dédié à la
logique, aucune logique métier dans la vue, réutiliser les composants existants,
respecter intégralement Design System/Layout System/Components, aucune évolution
graphique, aucun travail sur les icônes. Validation attendue : aucun événement, un
championnat, plusieurs championnats, changement d'année, tri chronologique. Tests
complets, zéro régression.

### Exploration préalable de l'architecture GUI
Relecture de `gui/calendar_selection.py` (Sprint 40) et de `gui/dashboard.py`/
`gui/upcoming_weekend.py` pour confirmer que le même patron "fetch" (controller) /
"compute" (module dédié) s'applique directement ici — avec une différence clé par
rapport aux trois précédents : la donnée brute nécessaire (`year_events`, tous les
championnats enregistrés pour l'année parcourue) est **déjà** récupérée par
`controller.get_calendar_year_events()` depuis le Sprint 40, donc aucun nouveau fetch
n'est nécessaire, seulement une nouvelle transformation locale. Vérification du modèle
domaine `Event` (`motorsport_calendar/models/event.py`) : pas de champ date propre —
seules les `sessions` portent des horodatages, confirmant qu'il faut ancrer le tri sur
la session la plus précoce de chaque événement, comme le fait déjà
`upcoming_weekend._entry_earliest_start`. Relecture de `gui/event_display.py`
(Sprint 32, ADR-023) : `normalize_event_display` est le point de passage obligé pour le
nom/circuit/pays d'un événement — jamais réimplémenté, réutilisé tel quel ici comme dans
`upcoming_weekend.py`.

### Travail effectué

**Nouveau `gui/season_explorer.py`** — logique pure, mirroring exact de
`calendar_selection.py`
- Aucun import Flet, aucune I/O — entièrement testable avec de simples fixtures
  `Event`/`Session` (les données vivent déjà dans `year_events`, récupéré par
  `controller.get_calendar_year_events`, Sprint 40).
- `SeasonEventRow` (frozen dataclass) : `event_name`, `championship_name`,
  `circuit_name: str | None`, `country: str | None`, `date_label: str` — dernier champ
  déjà formaté ("Dimanche 12/07"), même convention que `NextRaceStart.display`
  (Sprint 39) : le module de logique pure produit du texte prêt à afficher, la vue ne
  formate jamais de date elle-même.
- `SeasonMonthGroup` (frozen dataclass) : `month_label` ("Décembre 2025") + `rows` (tuple
  de `SeasonEventRow`, déjà triées).
- `build_season_explorer(year_events, selected_championships) -> tuple[SeasonMonthGroup,
  ...]` : agrège les événements des seuls championnats sélectionnés, calcule la session
  la plus précoce de chacun (`min(s.start_datetime for s in event.sessions)`), trie
  globalement par cet instant, puis regroupe par (année, mois) UTC — même convention que
  `upcoming_weekend._session_utc_date` (limitation déjà documentée pour les circuits loin
  de l'UTC, pas une nouvelle introduite ici). Un événement sans session (aucun horodatage
  à lui assigner) est exclu, jamais une erreur. Délibérément **pas** basé sur
  `Event.season` : l'anomalie Formula E déjà documentée au Sprint 40 (une manche "2026"
  datée du 6 décembre 2025, convention réelle du calendrier Formula E) doit apparaître
  sous "Décembre 2025", pas sous une étiquette "2026" trompeuse — verrouillé par
  `TestBuildSeasonExplorerYearBoundary`.

**`gui/views/calendar.py`** — nouveau bloc, wizard inchangé
- `CalendarViewControls` : nouveau champ `season_groups: tuple[SeasonMonthGroup, ...] |
  None` — même convention `None`/tuple-vide que `selection_summary` (Sprint 40) : `None`
  = fetch de l'année en cours toujours en vol, tuple vide = fetch résolu mais rien ne
  correspond à la sélection courante.
- Nouvelles fonctions pures `_season_event_row(row)` et `_season_explorer_block(groups)`
  — chaque événement est une carte à deux colonnes (nom/championnat/circuit/pays à
  gauche sur des lignes séparées — jamais combinées par "·", règle déjà posée pour
  `ChampionshipCard` au Sprint 30 — date à droite) ; chaque mois est une
  `Section(SectionHeader(month_label), CardList([...]))` du Layout System existant ;
  état de chargement (`ProgressRing` + message) et état vide (`EmptyState`) distincts,
  même trois états que `_selection_summary_block`. Aucun nouveau composant
  `gui/components/` créé — une ligne d'événement plate est structurellement trop
  différente d'une `ChampionshipCard` (détail de sessions d'un seul événement) pour
  justifier sa réutilisation, et aucun second consommateur réel n'est apparu pour en
  justifier un nouveau.
- `build_calendar_view` : `_season_explorer_block(c.season_groups)` inséré juste après
  `_selection_summary_block`, avant le corps spécifique à l'étape — visible sur les 4
  étapes, même placement/raisonnement que le résumé de sélection (Sprint 40).
  `_step_season`/`_step_championships`/`_step_destination`/`_step_create`/
  `_STEP_BUILDERS`/`_step_indicator` : **inchangés**.

**Intégration `main_view.py`** — aucun nouveau fetch, seulement une nouvelle dérivation
- `_current_season_groups()` : nouvelle fonction, mirroir exact de
  `_current_selection_summary()` — `None` tant que `year_events is None`, sinon
  `build_season_explorer(year_events, state.selected_championships)`.
- `_current_calendar_controls()` : `season_groups=_current_season_groups()` ajouté à la
  construction de `CalendarViewControls`.
- Aucune autre modification : `on_year_change`/`_make_on_change` appelaient déjà
  `_refresh_calendar_view()` (Sprint 26/40), qui reconstruit désormais aussi
  l'explorateur de saison à partir des mêmes `year_events`/`state.selected_championships`
  déjà en mémoire — "mis à jour automatiquement lorsque la sélection change" est donc
  satisfait sans aucun nouveau câblage d'événement ni nouvelle tâche asyncio.

**`strings.py`** : 3 nouvelles chaînes (`calendar_season_explorer_title`,
`calendar_season_explorer_empty`, `calendar_season_explorer_loading`).

### Tests
- `tests/test_gui_season_explorer.py` (créé, 16 tests) : sélection vide (aucun
  championnat coché, `year_events` vide, championnat coché mais jamais fetché, événement
  sans session exclu), un seul championnat (normalisation des champs via
  `event_display`, un seul groupe mensuel, groupes distincts par mois, événements du même
  mois regroupés), sélection multiple (fusion de plusieurs championnats dans les mêmes
  groupes, championnat non fetché ignoré sans crash), tri chronologique (ordre
  d'entrée quelconque → sortie triée, groupes mensuels eux-mêmes triés, deux événements le
  même jour triés par instant exact, un événement à cheval sur une frontière de mois
  classé sur sa session la plus précoce), frontière d'année (l'anomalie Formula E
  reproduite : décembre de l'année précédente et janvier de l'année sélectionnée en deux
  groupes distincts) — couvre explicitement les 5 scénarios de validation du brief.
- `tests/test_gui_views.py` (+7 tests, `TestCalendarViewSeasonExplorer`) : valeur par
  défaut `None` de `season_groups`, état de chargement, état vide (`EmptyState`), groupe
  peuplé (mois + tous les champs affichés), lignes circuit/pays omises quand `None`,
  plusieurs groupes mensuels tous rendus, présence du bloc sur les 4 étapes du wizard.
- `tests/test_gui_calendar_selection.py`/`test_gui_controller.py` : aucune modification
  nécessaire, exécutés pour confirmer la non-régression (aucun fetch/logique partagée
  modifié ce sprint).

### Fichiers modifiés / créés

| Fichier | Action |
|---|---|
| `motorsport_calendar/gui/season_explorer.py` | Créé |
| `motorsport_calendar/gui/views/calendar.py` | Modifié — bloc explorateur de saison (`season_groups`, `_season_explorer_block`), wizard inchangé |
| `motorsport_calendar/gui/main_view.py` | Modifié — `_current_season_groups()`, câblage dans `_current_calendar_controls()` |
| `motorsport_calendar/gui/strings.py` | Modifié — 3 chaînes `calendar_season_explorer_*` |
| `tests/test_gui_season_explorer.py` | Créé — 16 tests |
| `tests/test_gui_views.py` | Modifié — 7 tests ajoutés |
| `CHANGELOG.md` | Mis à jour |
| `docs/ROADMAP.md` | Mis à jour — v0.4.15 |
| `docs/AI_CONTEXT.md` | Mis à jour |
| `docs/TODO.md` | Mis à jour |
| `docs/DECISIONS.md` | ADR-032 ajouté |

`gui/theme.py`, `gui/championship_assets.py`, `gui/components/layout/*`,
`gui/components/championship_card.py`, `gui/calendar_selection.py`,
`gui/controller.py` (`get_calendar_year_events`, Sprint 40, réutilisée telle quelle),
`gui/dashboard.py`, `gui/views/dashboard.py`, `gui/views/weekend.py`/`favorites.py`/
`preferences.py`/`about.py`, `gui/models.py`, `gui/preferences.py`, `gui/categories.py`,
`gui/display_names.py`, `gui/event_display.py`, tous les providers, `docs/DATA_SOURCES.md`
(aucune nouvelle source de données ce sprint) : **non modifiés**.

### Tests exécutés
```
1596 passed → 1619 passed — 0 failed
(+23 tests — gui/season_explorer.py à 100 %)
```

Vérification ruff : 7 lignes trop longues (>100 caractères) introduites dans le code neuf
(`views/calendar.py::_season_event_row`, 6 lignes dans les fixtures de
`test_gui_season_explorer.py`) — corrigées immédiatement. Reste du code neuf
(`gui/season_explorer.py`, `_season_explorer_block`, `_current_season_groups`)
entièrement propre, zéro avertissement. Vérification mypy : `gui/season_explorer.py`
zéro erreur ; `views/calendar.py` toujours exactement 2 erreurs, toutes deux dans
`_step_indicator` (non touchée ce sprint) ; `main_view.py` toujours exactement 20
erreurs — nombre strictement identique à la fin du Sprint 40, confirmant qu'aucune
nouvelle dette n'a été introduite par `_current_season_groups()`/le champ
`season_groups`.

Vérification manuelle additionnelle (vrais appels réseau, pas de mock) :
`get_calendar_year_events(2026)` puis `build_season_explorer` sur les 5 scénarios de
validation du brief : sélection vide → `()` ; Formula 1 seul → 11 groupes mensuels
(Février à Décembre 2026), premier groupe "Février 2026" avec 2 événements ; Formula 1 +
MotoGP → toujours 11 groupes, 48 lignes au total ; toutes disciplines confondues → 13
groupes, 171 lignes (cohérent avec le total 171 événements déjà connu du Dashboard et du
résumé de sélection, Sprints 39-40) ; changement d'année (2025 vs 2026) → deux jeux de
groupes mensuels distincts et correctement étiquetés. Tri chronologique confirmé : les
groupes mensuels de la sélection complète apparaissent dans l'ordre Février → Décembre
2026 sans exception. Exemple de ligne normalisée vérifiée en direct : Formula E, Sao
Paulo ePrix, circuit "Sao Paulo", pays "🇧🇷 Brésil", date "Samedi 06/12" — confirmant que
l'anomalie de frontière d'année (documentée au Sprint 40) est bien classée sous
"Décembre 2025" et non sous une étiquette trompeuse.

### Limites
- **Aucune vérification visuelle réelle** (rendu Flet sur un poste avec affichage) —
  seule la structure des contrôles a pu être vérifiée dans ce bac à sable sans écran,
  exactement la même limitation que chaque sprint GUI précédent (Sprints 26-40). Attention
  particulière à porter lors d'une future vérification visuelle : une sélection large (17
  championnats, ~170 événements) produit une liste longue, jamais rendue réellement dans
  un navigateur — absorbée en théorie par le scroll de page déjà en place
  (`theme.page_shell`, Sprint 27), non confirmée en pratique.
- L'explorateur reste volontairement simple (les 5 champs demandés, rien de plus) — pas
  de lien vers `ChampionshipCard`, pas de filtre/recherche, pas de repli des mois passés ;
  pistes documentées pour un futur sprint, pas construites par anticipation.
- `year_events` n'est toujours pas mis en cache d'une année à l'autre dans la session GUI
  (limite déjà notée au Sprint 40) — bénéficierait aussi à l'explorateur de saison,
  puisqu'il consomme la même donnée.

---

## Session 2026-07-10 — Sprint 40 : Calendrier interactif

### Objectif
Deuxième sprint "valeur" du projet, dans la continuité du Dashboard (Sprint 39) :
transformer la page "Mon calendrier" d'un formulaire de génération ICS en un véritable
outil d'exploration. Le wizard 4 étapes existant (saison/championnats/destination/créer,
inchangé depuis le Sprint 26) doit être conservé intégralement — la génération ICS reste
l'aboutissement de la navigation, pas son unique objectif. Travail demandé : filtrer par
année et par championnat (déjà présent — étapes 1-2 du wizard existant), afficher le
nombre d'événements sélectionnés, le nombre de sessions sélectionnées, la période
couverte, et un résumé de la sélection avant génération. Contraintes explicites : aucune
logique métier dans la vue, réutiliser les composants existants, créer des composants
uniquement si une vraie réutilisation apparaît, respecter intégralement le Design System
et le Layout System, aucun travail sur les icônes. Validation attendue : sélection vide,
sélection d'un championnat, sélection multiple, toutes les disciplines, changement
d'année. Tests complets, zéro régression.

### Exploration préalable de l'architecture GUI
Avant d'écrire une ligne de code, relecture complète du wizard existant
(`gui/views/calendar.py`, `gui/models.py::GenerateState`, la section "CALENDAR WIZARD
CONTROLS" de `main_view.py`) pour confirmer l'interprétation du brief : le filtrage par
année et par championnat existe déjà (étapes 1-2), le vrai travail neuf est de rendre
l'**impact** de ce filtrage visible et vivant (compteurs, période) avant que l'utilisateur
n'atteigne l'étape finale — transformer "remplir un formulaire" en "explorer avant de
générer", sans toucher à la structure du wizard lui-même. Confirmation du patron
architectural déjà établi identiquement trois fois dans ce projet ("Ce week-end" Sprint
29, Dashboard Sprint 39) : un module de logique pure sans Flet ("compute", entièrement
testable avec de simples fixtures `Event`/`Session`) couplé à une fonction de contrôleur
sans Flet mais avec I/O ("fetch", registries/HttpCache/providers) — la vue ne reçoit que
des contrôles/dataclasses déjà construits.

### Travail effectué

**Nouveau `gui/calendar_selection.py`** — logique pure, mirroring exact de
`dashboard.py`/`upcoming_weekend.py`
- Aucun import Flet, aucune I/O — entièrement testable avec de simples fixtures
  `Event`/`Session` (le fetch vit dans `controller.get_calendar_year_events`, jamais dans
  ce module).
- `SelectionSummary` (frozen dataclass) : `event_count`, `session_count`,
  `period_start: date | None`, `period_end: date | None` — ces deux derniers sont `None`
  exactement quand `event_count == 0` (aucune sélection, ou une sélection dont les
  championnats n'ont aucun événement pour l'année parcourue), jamais un résumé à moitié
  rempli.
- `build_selection_summary(year_events, selected_championships) -> SelectionSummary` :
  agrège localement les événements des seuls championnats sélectionnés parmi ceux déjà
  récupérés — un championnat sélectionné mais absent de `year_events` (fetch échoué) est
  simplement ignoré, jamais une erreur.

**`controller.py`** — nouveau fetch + extraction partagée, comportement des fonctions
existantes strictement préservé
- Nouvelle fonction publique `get_calendar_year_events(year) -> dict[str, list[Event]]` :
  récupère en une seule passe les événements de **tous** les championnats enregistrés
  (`registry.list_all()`) pour l'année donnée — contrairement à `_fetch_weekend_entries`
  (Sprint 29/39), scopée à exactement une année (aucun lookahead sur l'année suivante,
  l'utilisateur l'a choisie délibérément) mais à l'intégralité des championnats, puisque
  les cases à cocher du wizard les listent déjà tous. Ne lève jamais — un championnat dont
  le fetch échoue (stub `NotImplementedError`, timeout…) est simplement absent du
  dictionnaire résultat.
- Résolution championnat→source→provider (config/opt-out/source par défaut, gestion
  d'échec silencieuse) extraite en
  `_resolve_source_and_provider_factories(cid, config)`, partagée entre
  `_fetch_weekend_entries` et `get_calendar_year_events` — comportement de
  `_fetch_weekend_entries` strictement préservé, vérifié par la suite de tests existante
  (`test_gui_controller.py`, `test_gui_upcoming_weekend.py`, `test_gui_dashboard.py` — 69
  tests) intégralement verte après le refactor, sans qu'aucun test n'ait dû être modifié
  pour cette partie. `generate_calendar()` délibérément **non** refactorisée dessus (ses
  tests verrouillent des messages d'erreur exacts par championnat que le retour
  `None`-générique de l'aide partagée aurait perdus).

**`gui/views/calendar.py`** — résumé persistant, wizard inchangé
- `CalendarViewControls` : nouveau champ `selection_summary: SelectionSummary | None`
  (`None` = fetch de l'année en cours toujours en vol, distinct d'un `SelectionSummary`
  résolu avec `event_count == 0`).
- Nouvelles fonctions pures `_summary_stat(value, label)` et
  `_selection_summary_block(summary)` — trois états rendus distinctement : chargement
  (`ProgressRing` + message), sélection vide (message dédié), résumé peuplé (compteurs
  pluralisés FR + période `dd/mm/yyyy - dd/mm/yyyy`, ou un tiret si aucune session n'a
  d'heure de début).
- `build_calendar_view` : `_selection_summary_block(c.selection_summary)` inséré juste
  après l'indicateur d'étapes, **avant** le corps spécifique à chaque étape — visible sur
  les 4 étapes sans dupliquer aucun contenu. À l'étape "Créer", ce bloc apparaît
  naturellement au-dessus du récapitulatif existant (`_build_recap_controls()`, non
  modifié) et du bouton de génération, satisfaisant "un résumé avant génération" sans
  toucher à cette logique déjà en place. `_step_season`/`_step_championships`/
  `_step_destination`/`_step_create`/`_STEP_BUILDERS`/`_step_indicator` : **inchangés**.

**Intégration `main_view.py`** — pattern de fetch en arrière-plan, mirroir exact de
`_load_weekend`/`_load_dashboard`
- `year_events: dict[str, list[Event]] | None` en closure de la section "CALENDAR WIZARD
  CONTROLS".
- `_load_year_events(year)` (async) : appelle `get_calendar_year_events(year)`, garde
  d'obsolescence (`if year != state.year: return` — ignore une réponse tardive pour une
  année que l'utilisateur a déjà quittée), assigne `year_events` puis reconstruit la vue.
- `on_year_change` : réinitialise `year_events = None` (affiche immédiatement l'état de
  chargement), reconstruit la vue, puis déclenche `page.calendar_year_load_task =
  asyncio.create_task(_load_year_events(state.year))`.
- Fetch initial déclenché une fois au lancement (année par défaut), dans la section
  "BUILD ALL VIEWS", juste après la première construction de `calendar_container`.
- `_current_calendar_controls()` : `selection_summary=_current_selection_summary()`
  ajouté — `None` tant que `year_events is None`, sinon
  `build_selection_summary(year_events, state.selected_championships)`.
- Le handler de case à cocher (`_make_on_change`) n'a nécessité **aucune** modification :
  il appelait déjà `_refresh_calendar_view()`, qui recalcule désormais le résumé à partir
  de `year_events`/`state.selected_championships` déjà en mémoire — zéro nouvelle requête
  réseau par coche, exactement l'objectif du sprint.

### Tests
- `tests/test_gui_calendar_selection.py` (créé, 9 tests) : sélection vide (aucun
  championnat coché, `year_events` vide, championnat coché mais jamais fetché), un seul
  championnat (comptages, période min/max, événement sans session), sélection multiple
  (agrégation croisée, championnat non fetché ignoré sans crash), toutes les disciplines
  (agrégation complète) — couvre explicitement les 5 scénarios de validation du brief
  (hors "changement d'année", couvert côté controller).
- `tests/test_gui_controller.py` (+8 tests, `TestGetCalendarYearEvents`) : aucune donnée
  nulle part (chaque championnat fetché avec succès obtient une liste vide, pas une
  absence de clé — distinct d'un échec de fetch), un seul an fetché (pas de lookahead sur
  l'année suivante, contrairement à `_fetch_weekend_entries`), clé = id championnat, stubs
  WEC/IMSA/WorldSBK tolérés (`NotImplementedError` ne casse jamais l'appel global),
  résilience à l'échec partiel d'un provider, couverture de tous les championnats
  enregistrés (pas seulement le sous-ensemble "Ce week-end"), championnat sans source /
  provider non enregistré ignoré proprement.
- `tests/test_gui_views.py` (+8 tests, `TestCalendarViewSelectionSummary`) : valeur par
  défaut `None` de `selection_summary`, état de chargement (`ProgressRing` + texte),
  sélection vide (message dédié), résumé peuplé (compteurs + période affichés), singulier/
  pluriel FR, résumé sans période (tiret), présence du bloc résumé sur les 4 étapes du
  wizard construites via `build_calendar_view`.
- `tests/test_gui_dashboard.py`/`test_gui_upcoming_weekend.py` : aucune modification
  nécessaire, exécutés pour confirmer la non-régression du refactor
  `_resolve_source_and_provider_factories`.

### Fichiers modifiés / créés

| Fichier | Action |
|---|---|
| `motorsport_calendar/gui/calendar_selection.py` | Créé |
| `motorsport_calendar/gui/controller.py` | Modifié — extraction `_resolve_source_and_provider_factories`, ajout `get_calendar_year_events` |
| `motorsport_calendar/gui/views/calendar.py` | Modifié — résumé persistant (`selection_summary`, `_selection_summary_block`), wizard inchangé |
| `motorsport_calendar/gui/main_view.py` | Modifié — fetch `year_events` en arrière-plan, câblage du résumé |
| `motorsport_calendar/gui/strings.py` | Modifié — 6 chaînes `calendar_summary_*` |
| `tests/test_gui_calendar_selection.py` | Créé — 9 tests |
| `tests/test_gui_controller.py` | Modifié — 8 tests ajoutés |
| `tests/test_gui_views.py` | Modifié — 8 tests ajoutés |
| `CHANGELOG.md` | Mis à jour |
| `docs/ROADMAP.md` | Mis à jour — v0.4.14 |
| `docs/AI_CONTEXT.md` | Mis à jour |
| `docs/TODO.md` | Mis à jour |
| `docs/DECISIONS.md` | ADR-031 ajouté |

`gui/theme.py`, `gui/championship_assets.py`, `gui/components/layout/*`,
`gui/components/championship_card.py`, `gui/dashboard.py`, `gui/views/dashboard.py`,
`gui/views/weekend.py`/`favorites.py`/`preferences.py`/`about.py`, `gui/models.py`
(`GenerateState` inchangée — le filtrage année/championnat existait déjà), `gui/
preferences.py`, `gui/categories.py`, `gui/display_names.py`, `gui/event_display.py`,
tous les providers, `docs/DATA_SOURCES.md` (aucune nouvelle source de données ce sprint) :
**non modifiés**.

### Tests exécutés
```
1571 passed → 1596 passed — 0 failed
(+25 tests — gui/calendar_selection.py à 100 %, controller.get_calendar_year_events et
_selection_summary_block couverts par tous les états)
```

Vérification ruff : 4 lignes trop longues (>100 caractères) introduites dans le code neuf
(`views/calendar.py::_summary_stat`, 2 tests) — corrigées immédiatement. Reste du code
neuf (`gui/calendar_selection.py`, `controller.get_calendar_year_events`,
`_resolve_source_and_provider_factories`, `_selection_summary_block`) entièrement propre,
zéro avertissement. Les avertissements ruff/mypy pré-existants ailleurs dans
`controller.py` (`generate_calendar`, non touchée), `strings.py` (`from_dict`, non
touchée) et `views/calendar.py` (`_step_indicator`, non touchée) sont strictement les
mêmes qu'avant ce sprint. Vérification mypy : le code neuf (`calendar_selection.py`,
`get_calendar_year_events`, `_resolve_source_and_provider_factories`,
`_selection_summary_block`, `_current_selection_summary`, `_load_year_events`) ne produit
aucune erreur ; les seules erreurs nouvellement visibles dans `main_view.py` sont 2
occurrences de `"Page" has no attribute "calendar_year_load_task"` — exactement la même
famille d'erreur déjà tolérée pour `weekend_load_task`/`dashboard_load_task` (attribution
dynamique d'attribut sur `ft.Page`, non modélisable par les stubs Flet actuels), pas une
nouvelle catégorie de dette.

Vérification manuelle additionnelle (vrais appels réseau, pas de mock) :
`get_calendar_year_events(2026)` en direct → 14 championnats avec événements (les stubs
WEC/IMSA/WorldSBK absents du résultat, comme attendu). `build_selection_summary` testé
sur les 5 scénarios de validation du brief : sélection vide → `(0, 0, None, None)` ;
Formula 1 seul → `(26, 126, 11/02/2026, 06/12/2026)` ; Formula 1 + MotoGP → `(48, 258,
mêmes bornes)` ; toutes disciplines confondues → `(171, 810, 06/12/2025, 06/12/2026)`
(cohérent avec les totaux 171/810 déjà connus du Dashboard, Sprint 39) ; sélection
incluant un championnat non fetché (`wec`) → ignoré proprement, comptages inchangés.
Période minimale 2025-12-06 sur la sélection complète tracée jusqu'à un événement
Formula E authentique (São Paulo ePrix, sessions FP2/QUALIFYING/RACE) — la saison "2026"
de Formula E démarre conventionnellement en décembre de l'année civile précédente,
confirmé non-bug.

### Limites
- **Aucune vérification visuelle réelle** (rendu Flet sur un poste avec affichage) —
  seule la structure des contrôles a pu être vérifiée dans ce bac à sable sans écran,
  exactement la même limitation que chaque sprint GUI précédent (Sprints 26-39).
  Documenté dans `docs/TODO.md` et `docs/AI_CONTEXT.md`.
- Le résumé reste volontairement simple (comptages + période, rien de plus) — pas de
  répartition par championnat, pas de fusion avec le récapitulatif de l'étape 4 ; pistes
  documentées pour un futur sprint, pas construites par anticipation.
- `year_events` n'est pas mis en cache d'une année à l'autre dans la session GUI — un
  aller-retour entre deux années déjà visitées redéclenche un fetch complet (absorbé par
  le TTL du `HttpCache` existant, donc sans coût réseau réel, mais recalcule quand même le
  résumé depuis zéro).

---

## Session 2026-07-10 — Sprint 39 : Dashboard Motorsport (page d'accueil)

### Objectif
Premier sprint "valeur" du projet après huit sprints consécutifs d'extension de
championnats (Sprints 33-38, 17 championnats intégrés au total) : construire la
première version d'un Tableau de bord exploitant le volume de données déjà disponible,
sans ajouter le moindre nouveau provider ni la moindre nouvelle source de données. Le
Dashboard devient la page d'accueil de l'application et doit afficher six informations :
le prochain week-end de course, le nombre de championnats disponibles, le nombre
d'événements de la saison, le nombre de sessions, les championnats présents ce week-end,
le prochain départ (date + heure). Contraintes explicites : créer une vue dédiée, ne
déplacer aucune logique métier dans la GUI, réutiliser les composants existants,
respecter intégralement le Design System et le Layout System, aucun travail sur les
icônes, les placeholders restent utilisés. Tests complets, zéro régression.

### Exploration préalable de l'architecture GUI
Avant d'écrire une ligne de code, relecture complète de la chaîne existante pour
identifier précisément où placer la nouvelle logique et la nouvelle vue sans dupliquer
ce qui existe déjà :
- `controller.get_upcoming_weekend()` — pipeline de fetch (registries, HttpCache, boucle
  sur les 17 championnats "Ce week-end" pour l'année courante + suivante) qui délègue
  ensuite tout le calcul à `upcoming_weekend.find_upcoming_weekend()`.
- `upcoming_weekend.py` — logique pure (sans Flet, sans HTTP), déjà découplée du fetch,
  déjà unitairement testable avec de simples fixtures `Event`/`Session`.
- `gui/views/weekend.py` — vue à 3 états (chargement/vide/trouvé), entièrement composée
  du Layout System, jamais de container/header/carte construits à la main.
- `gui/components/layout/section.py` — la docstring de `SectionHeader` anticipait
  littéralement "labelling one of several card groups on a future dashboard" : la
  structure du projet attendait déjà ce sprint.
- `gui/strings.py` — `nav_home: str = "Accueil"` existait déjà, commenté "Kept for
  backward compat — mapped to nav_weekend/nav_my_calendar", jamais branché : signe qu'une
  page d'accueil distincte avait déjà été anticipée à un moment antérieur du projet, sans
  jamais être construite. Conservé tel quel (hors périmètre, non modifié) ; une chaîne
  dédiée `nav_dashboard` a été ajoutée à la place pour nommer explicitement la nouvelle
  fonctionnalité.

Cette exploration a directement guidé la décision d'architecture : les six informations
demandées se dérivent presque entièrement de la même matière première que "Ce week-end"
récupère déjà, plutôt que d'un nouveau pipeline de fetch séparé.

### Travail effectué

**Refactor `controller.py`** — extraction sans changement de comportement
- La boucle de fetch de `get_upcoming_weekend()` (registries, HttpCache, itération sur
  `WEEKEND_CHAMPIONSHIP_IDS` pour 2 années) a été extraite en une nouvelle fonction privée
  `_fetch_weekend_entries(reference_now) -> list[WeekendEntry]`. `get_upcoming_weekend()`
  devient un simple appel à cette fonction suivi de `find_upcoming_weekend()` — comportement
  strictement identique, vérifié par la suite de tests existante (`test_gui_controller.py`,
  `test_gui_upcoming_weekend.py`) intégralement verte après le refactor, sans qu'aucun test
  n'ait dû être modifié pour cette partie.
- Nouvelle fonction publique `get_dashboard_data(*, now=None) -> DashboardData` : appelle
  `_fetch_weekend_entries()` une seule fois, récupère `len(registry.list_all())` pour le
  nombre de championnats disponibles, puis délègue tout le calcul à
  `gui/dashboard.py::build_dashboard_data()`.

**Nouveau `gui/dashboard.py`** — logique pure, mirroring exact de `upcoming_weekend.py`
- `NextRaceStart` (frozen dataclass) : nom du championnat + affichage déjà formaté.
- `DashboardData` (frozen dataclass) : `total_championships`, `total_events_season`,
  `total_sessions_season`, `weekend: WeekendResult` (réutilisé tel quel), `next_race:
  NextRaceStart | None`.
- `build_dashboard_data(entries, total_championships, now) -> DashboardData` : réutilise
  `find_upcoming_weekend(entries, now=now)` sans le réimplémenter (garantit que "Ce
  week-end" et le Dashboard s'accordent toujours, par construction) ; filtre `entries` sur
  `event.season == now.year` pour les compteurs de saison (les événements de l'année
  suivante, récupérés pour couvrir un week-end à cheval sur le nouvel an, ne polluent
  jamais ce compte) ; `_find_next_race()` cherche la plus proche session
  `SessionType.RACE` (exclusivement — jamais Sprint/Hyperpole) à partir de *now*, toutes
  classes confondues.

**`upcoming_weekend.py` — une seule addition**
- Nouvelle fonction publique `format_session_datetime(start, circuit_timezone) -> str`
  ("Dimanche 12/07 15:00", fuseau local du circuit) — réutilise `_circuit_zone()` et
  `_DAY_LABELS_FR` déjà existants (repli sûr sur UTC en cas de fuseau invalide, hérité de
  `_circuit_zone`) plutôt que de les dupliquer. Distincte du formatage `day_time` déjà
  utilisé à l'intérieur d'une `SessionRow` (jour + heure seulement) : le "prochain
  départ" est un stat isolé, pas contextualisé à un week-end déjà affiché à l'écran, donc
  a besoin de la date complète.

**Nouvelle vue `gui/views/dashboard.py`**
- 2 états (`build_dashboard_view(None)` = chargement, `build_dashboard_view(data)` =
  chargé), même patron que `views/weekend.py`.
- État chargé : `PageHeader` + 3 sections — une rangée de 4 stat cards (prochain
  week-end, championnats disponibles, événements de la saison, sessions), une section
  "Championnats ce week-end" (puces `theme.chip()` ou `EmptyState` si aucun week-end
  trouvé/aucune carte), une section "Prochain départ" (carte `theme.card()` avec nom du
  championnat + date/heure, ou `EmptyState` si aucune course à venir dans la fenêtre de
  recherche).
- Aucun nouveau composant, aucun nouveau token de Design System — uniquement
  `theme.card`/`theme.chip`/`theme.Spacing`/`theme.FontSize`/`theme.Colors` et le Layout
  System (`PageContainer`/`PageHeader`/`Section`/`SectionHeader`/`EmptyState`), déjà
  existants.

**Intégration page d'accueil (`main_view.py`)**
- Import de `get_dashboard_data`/`build_dashboard_view`.
- Nouveau `dashboard_container`, chargé en arrière-plan au lancement via
  `page.dashboard_load_task = asyncio.create_task(_load_dashboard())` — exact mirroir du
  pattern déjà établi pour `weekend_container`/`page.weekend_load_task` (Sprint 29).
- `all_views` : Dashboard inséré en première position, les 5 vues existantes décalées
  d'un cran (Ce week-end/Mon calendrier/Mes favoris/Préférences/À propos passent des
  index 0-4 aux index 1-5).
- `nav_rail.selected_index` : `1` → `0` (le Dashboard devient l'onglet par défaut au
  lancement). Nouvelle première destination `NavigationRailDestination` (icône
  `ft.Icons.SPACE_DASHBOARD_OUTLINED`/`SPACE_DASHBOARD`, déjà existante dans Flet — aucun
  travail d'icône, conforme à la consigne).
- `content_area` : `content=all_views[1]` (Mon calendrier) → `content=all_views[0]`
  (Tableau de bord).

**Nouvelles chaînes `strings.py`** : `nav_dashboard` + 8 chaînes dédiées au Dashboard
(`dashboard_stat_next_weekend`, `dashboard_stat_championships`, `dashboard_stat_events`,
`dashboard_stat_sessions`, `dashboard_next_weekend_none`,
`dashboard_section_weekend_championships`, `dashboard_weekend_championships_empty`,
`dashboard_section_next_race`, `dashboard_next_race_empty`). `nav_home`/`nav_calendar`
(chaînes historiques déjà présentes, jamais branchées) laissées inchangées, hors
périmètre.

### Tests
- `tests/test_gui_dashboard.py` — 12 tests : comptage championnats/événements/sessions
  (y compris exclusion des événements d'une autre saison), réutilisation de
  `find_upcoming_weekend` pour le week-end (trouvé/non trouvé), recherche du prochain
  départ (aucune entrée, sessions non-RACE ignorées, courses passées ignorées, la plus
  proche retenue en cas de plusieurs championnats, Sprint jamais compté comme un départ).
- `tests/test_gui_upcoming_weekend.py` — 4 nouveaux tests pour `format_session_datetime`
  (jour+date+heure, conversion vers le fuseau local du circuit, repli UTC sur fuseau
  invalide, changement de jour local possible par rapport à la date UTC).
- `tests/test_gui_controller.py` — 5 nouveaux tests pour `get_dashboard_data()` (aucune
  donnée nulle part, nombre de championnats aligné sur le registry, un événement ce
  week-end reflété à la fois dans `weekend` et `next_race`, résilience à l'échec partiel
  d'un provider — même garantie que "Ce week-end" puisque même pipeline partagé, `now`
  par défaut ne lève jamais).
- `tests/test_gui_views.py` — 11 nouveaux tests pour `build_dashboard_view` (import,
  types de contrôle retournés, largeur de page partagée, état de chargement encarté,
  présence du PageHeader, comptage exact de cartes bordées selon les combinaisons
  weekend/next_race trouvés ou vides, rendu complet sans crash).
- `tests/test_gui_strings.py` — aucune modification nécessaire (`test_all_required_keys_
  present` est une liste blanche fixe, jamais exhaustive).

### Fichiers modifiés / créés

| Fichier | Action |
|---|---|
| `motorsport_calendar/gui/dashboard.py` | Créé |
| `motorsport_calendar/gui/views/dashboard.py` | Créé |
| `motorsport_calendar/gui/controller.py` | Modifié — extraction `_fetch_weekend_entries`, ajout `get_dashboard_data` |
| `motorsport_calendar/gui/upcoming_weekend.py` | Modifié — ajout `format_session_datetime` |
| `motorsport_calendar/gui/main_view.py` | Modifié — Dashboard en page d'accueil |
| `motorsport_calendar/gui/strings.py` | Modifié — `nav_dashboard` + 8 chaînes Dashboard |
| `tests/test_gui_dashboard.py` | Créé — 12 tests |
| `tests/test_gui_upcoming_weekend.py` | Modifié — 4 tests ajoutés |
| `tests/test_gui_controller.py` | Modifié — 5 tests ajoutés |
| `tests/test_gui_views.py` | Modifié — 11 tests ajoutés |
| `CHANGELOG.md` | Mis à jour |
| `docs/ROADMAP.md` | Mis à jour — v0.4.13 |
| `docs/AI_CONTEXT.md` | Mis à jour |
| `docs/TODO.md` | Mis à jour |
| `docs/DECISIONS.md` | ADR-030 ajouté |

`gui/theme.py`, `gui/championship_assets.py`, `gui/components/layout/*`,
`gui/components/championship_card.py`, `gui/views/weekend.py`,
`gui/views/calendar.py`/`favorites.py`/`preferences.py`/`about.py`, `gui/models.py`,
`gui/preferences.py`, `gui/categories.py`, `gui/display_names.py`,
`gui/event_display.py`, tous les providers, `docs/DATA_SOURCES.md` (aucune nouvelle
source de données ce sprint) : **non modifiés**.

### Tests exécutés
```
1539 passed → 1571 passed — 0 failed — couverture ~96 %
(+32 tests — gui/dashboard.py et gui/views/dashboard.py à 100 %)
```

Vérification ruff/mypy (comparaison avant/après via `git stash`) : zéro nouvelle dette
introduite. `gui/dashboard.py`, `gui/views/dashboard.py` et `gui/upcoming_weekend.py`
entièrement propres (zéro avertissement ruff, zéro erreur mypy). Les seuls avertissements
restants dans `controller.py` (3 erreurs mypy, 2 ruff) et `main_view.py`/`strings.py`
(9 erreurs ruff) sont exactement les mêmes, aux mêmes lignes relatives, dans les zones
**non touchées** par ce sprint (`generate_calendar`, wizard, `on_page_resize`,
`from_dict`) — confirmé identique au baseline pré-sprint par comparaison directe.

Vérification manuelle additionnelle (vrais appels réseau, pas de mock) :
`get_dashboard_data()` en direct → 17 championnats disponibles, 171 événements/810
sessions pour la saison 2026 (cohérent avec l'agrégateur `generate` du Sprint 38), 4
championnats trouvés pour le week-end du 10-12 juillet 2026 (GT World Challenge Asia,
MotoGP, Moto2, Moto3), prochain départ = GT World Challenge Asia (Race 2, dimanche
11:35). `build_dashboard_view()` construit sans erreur avec ces données réelles comme
avec l'état de chargement (`None`). Structure de la vue confirmée : `PageHeader` + 3
sections dans le corps de page, cohérent avec le Layout System.

### Limites
- **Aucune vérification visuelle réelle** (rendu Flet sur un poste avec affichage) —
  seule la structure des contrôles a pu être vérifiée dans ce bac à sable sans écran,
  exactement la même limitation que chaque sprint GUI précédent (Sprints 26-38).
  Documenté dans `docs/TODO.md` et `docs/AI_CONTEXT.md`.
- Le Dashboard reste volontairement simple : exactement les 6 informations demandées,
  aucune stat card cliquable, aucun historique, aucun raccourci vers d'autres pages —
  pistes documentées pour un futur sprint, pas construites par anticipation.
- Aucun logo ne s'affiche sur les stat cards ni les puces de championnat du Dashboard
  (contrairement à `ChampionshipCard`) — choix délibéré pour rester compact/glaçable, non
  demandé par le brief.
- `nav_home`/`nav_calendar` (chaînes historiques déjà présentes, jamais branchées avant
  ce sprint) laissées inchangées — hors périmètre, la nouvelle page d'accueil utilise sa
  propre chaîne dédiée `nav_dashboard`.

---

## Session 2026-07-10 — Sprint 38 : Motorcycle Racing (MotoGP, Moto2, Moto3, WorldSBK)

### Objectif
Enrichir la discipline Moto en ajoutant quatre championnats : MotoGP, Moto2, Moto3 et
World Superbike (WorldSBK). Aucune évolution graphique, aucune nouvelle fonctionnalité
utilisateur. Consignes explicites : étudier les meilleures sources disponibles,
mutualiser uniquement lorsqu'une abstraction apparaît naturellement, ne jamais casser
l'architecture actuelle. Intégration automatique partout (Wizard, "Ce week-end",
génération ICS, catégories, noms lisibles, préférences), tests complets, zéro
régression, documentation complète puis `docs/JOURNAL.md` selon la procédure établie
(Sprint 34).

### Recherche de la source de données
Première étape : vérifier si le dataset `sportstimes/f1` (déjà utilisé pour F2/F3/F1
Academy/Formula E) couvrait tout ou partie du besoin. Confirmé : `_db/motogp/` existe,
mais ne couvre que la classe reine MotoGP (`config.json` révèle `"siteKey": "motogp"`,
`"url": "motogpcal.com"`) — aucune trace de Moto2/Moto3/WorldSBK dans l'écosystème
`sportstimes`.

Recherche menée directement sur motogp.com (fetch HTML réel, pas de résumé IA à cette
étape) : la page calendrier référence `api.pulselive.motogp.com`. Sondage direct de cette
API par `curl` (endpoints devinés puis affinés grâce aux messages d'erreur 400 explicites
du serveur, ex. `"Required request parameter 'seasonYear' for method parameter type
Integer is not present"`) révèle une **API REST officielle et non authentifiée
appartenant à Dorna Sports** : `GET /motogp/v1/events?seasonYear={year}` retourne en une
seule requête tous les événements de la saison (tests, présentations d'équipe/média, et
rounds réels distingués par `kind: "GP"`), et chaque round de Grand Prix embarque déjà un
tableau `broadcasts` avec **toutes les sessions des trois classes** (`category.acronym`:
`MGP`/`MT2`/`MT3`), chacune avec une vraie heure de début ET de fin
(`date_start`/`date_end`) pour la quasi-totalité des types de session — qualité de
données strictement supérieure au JSON-LD ACO (Sprint 35) et au scraping HTML SRO
(Sprint 37), sans qu'aucune page HTML n'ait besoin d'être parsée. Vérifié sur 22 rounds
réels de la saison 2026, y compris le tout dernier (Valence, novembre) : planning complet
disponible même pour le round le plus éloigné dans le calendrier.

Pour WorldSBK, organisé par Dorna Sports depuis 2022 (même groupe que MotoGP),
l'hypothèse d'une plateforme partagée était raisonnable mais non confirmée en pratique :
worldsbk.com tourne bien sur la même famille de plateforme "Pulse Live" (confirmé via un
fichier de traductions multi-tenant partagé,
`translations.gplat-prod.pulselive.com/wsbk/en.js`), mais son calendrier/planning est
**entièrement rendu côté client** — aucune donnée exploitable dans le HTML brut,
contrairement aux sites SRO GT du Sprint 37 qui étaient server-rendus. Un hôte API
candidat a été identifié dans le code source de la page
(`window.SD_DOMAIN = 'https://wsbk-api-origin.gplat-test.pulselive.com'`), mais il ne
répond pas aux requêtes externes (timeout de connexion sur les 3 IP résolues). Plusieurs
routes plausibles suivant la convention de nommage de l'API MotoGP (`/wsbk/v1/events`,
`/sbk/v1/events`, `/superbike/v1/events`, etc.) ont été testées directement sur
`api.pulselive.worldsbk.com` — toutes renvoient un vrai 404 applicatif du propre backend
du serveur (confirmant l'hôte actif, mais aucune route devinée correcte). L'API MotoGP
elle-même ne couvre pas WorldSBK (ses `circuit.timing_ids` n'exposent jamais de business
unit SBK). Résultats présentés à l'utilisateur (AskUserQuestion, 3 options : stub à la
WEC/IMSA / reporter WorldSBK entièrement / source suggérée par l'utilisateur) — option
retenue : **stub à la WEC/IMSA**.

### Travail effectué

**`motorsport_calendar/providers/motogp_series/`** — nouvelle abstraction partagée
- `pulselive_base.py::PulseliveGpSource(JsonDataSource, ABC)` : toute la logique
  HTTP/cache/filtrage de saison/classification de broadcasts/fusion de sessions vit ici.
  3 propriétés abstraites par sous-classe : `_series_key`, `_category_acronym`,
  `_race_duration_minutes`, plus `_make_championship()`.
- Aucune table de circuits à maintenir (contrairement à ACO Sprint 35 et SRO Sprint 37) :
  le pays, la ville et le fuseau horaire IANA (`time_zone`, ex. `"ASIA/BANGKOK"` →
  `.title()` → `"Asia/Bangkok"`) sont tous directement exposés par la source — vérifié
  valide via `zoneinfo.ZoneInfo` sur les 18 fuseaux distincts de la saison 2026.
- Deux subtilités de données gérées **génériquement** (pas par classe) :
  1. Chaque classe court 3 séances PRACTICE-kind par week-end, mais seules 2 portent un
     numéro explicite (`FP1`/`FP2`) — la 3ème s'appelle juste `PR` ("Practice") et tombe
     chronologiquement ENTRE les deux numérotées. Plutôt que de faire confiance au
     libellé, les 3 séances sont triées chronologiquement et assignées `FP1`/`FP2`/`FP3`
     par ordre de créneau — `Session.title` conserve le libellé réel de la source, donc
     l'écart entre "notre FP2" (le "PR" source) et "notre FP3" (le "FP2" source) n'est
     jamais caché.
  2. Qualifying tourne en deux segments (`Q1`, `Q2`) par classe, fusionnés en une seule
     session `QUALIFYING` allant du début de Q1 à la fin réelle de Q2 — contrairement à
     ACO/SRO, la source fournit déjà une vraie heure de fin, aucune durée n'est inventée
     pour cette fusion.
  3. Seules les sessions `RACE`/`SPRINT` (Sprint MotoGP uniquement) n'ont pas d'heure de
     fin réelle (`date_start == date_end` systématiquement côté source) — durée par
     défaut documentée par classe/format.

**`motorsport_calendar/providers/motogp/`**, **`moto2/`**, **`moto3/`**
- Patron Provider/Source identique aux championnats précédents. Source concrète
  (`sources/pulselive.py::PulseliveSource`) héritant de `PulseliveGpSource`, ne déclarant
  que la configuration spécifique à la classe (acronyme catégorie, durée de course par
  défaut).

**`motorsport_calendar/providers/worldsbk/`** — stub à la WEC/IMSA
- `source.py::WorldSbkSource(ABC)`, `provider.py::WorldSbkProvider`,
  `sources/official.py::OfficialWorldSbkSource` (`get_season` lève `NotImplementedError`)
  — mirroring exact de `providers/imsa/`, docstring documentant l'investigation complète
  pour éviter de la reproduire à l'avenir.

**`motorsport_calendar/cli.py`**
- `generate-motogp`, `generate-moto2`, `generate-moto3`, `generate-worldsbk`
  (`YEAR OUTPUT.ics`) ajoutées sur le helper `_run_generate_command()` (Sprint 34).
  `generate-worldsbk` inclut `not_implemented_message`, mirroring exact de
  `generate-wec`/`generate-imsa`.

**Intégration GUI — nouveau groupe, 4 lignes**
- `gui/categories.py` : nouveau groupe `ChampionshipGroup(category=Category.MOTO,
  label="Moto", emoji="🏍", championship_ids=("motogp", "moto2", "moto3", "worldsbk"))`.
  `Category.MOTO` existait déjà dans l'énumération depuis le Sprint 37 (la docstring du
  module anticipait explicitement ce scénario : "To add a new group (e.g. Moto): 1. Add
  MOTO...") — aucune modification d'énumération nécessaire, seulement l'ajout du groupe.
- `gui/display_names.py` : 4 entrées ajoutées.
- `gui/upcoming_weekend.py::WEEKEND_CHAMPIONSHIP_IDS` : 4 IDs ajoutés.
- `gui/event_display.py::_GP_SUFFIX_CHAMPIONSHIPS` : **aucun changement** — les noms
  d'événement MotoGP/Moto2/Moto3 sont déjà complets ("PT GRAND PRIX OF THAILAND"), donc
  ces IDs n'y figurent pas par défaut, comme WEC/ELMS/MLMC/FormulaE/IMSA/GT.
- Aucune ligne dans `main_view.py`/`calendar.py` — vérifié en confirmant que les 4
  championnats apparaissent automatiquement dans un nouveau groupe "🏍 Moto" sans code de
  vue supplémentaire.

**Bug réel détecté en vérification live (pas en test unitaire), corrigé avant
livraison :** la source rapporte chaque horodatage avec le décalage UTC local du circuit
(ex. `2026-02-27T10:45:00+0700`), jamais en UTC — contrairement à tous les autres
providers du projet, qui stockent systématiquement des horaires de session en UTC. En
conservant l'offset local tel quel, `IcsExporter` produisait un
`DTSTART;TZID="UTC+07:00"` synthétique dans l'ICS exporté, sans bloc `VTIMEZONE`
correspondant — détecté en inspectant le fichier `.ics` généré par une vérification live
réelle (`grep DTSTART`), pas par un test unitaire. Corrigé en normalisant chaque
horodatage vers UTC dans `_parse_datetime` (`.astimezone(UTC)`), rétablissant la
cohérence avec le reste du projet et un `DTSTART` simplement suffixé `Z`. Revérifié après
correction : les 22 rounds de la saison 2026 produisent des `DTSTART` tous `Z`-suffixés.

**Tests**
- `tests/test_pulselive_base.py` — 43 tests : classification de broadcasts (practice/
  qualifying/sprint/race/exclus), normalisation UTC des horodatages (décalages positifs
  et négatifs), résolution de circuit (pays/ville/fuseau depuis les champs source,
  fallback ville vide → nom circuit, normalisation casse IANA), construction de sessions
  sur 3 fixtures réelles (Thaïlande — format Sprint classique, USA — catégorie BWC
  supplémentaire à ignorer, Valence — dernier round de la saison), Moto2/Moto3 sans
  Sprint, `get_season()` bout-en-bout avec `fetch_json` mocké (filtrage kind GP,
  numérotation séquentielle des rounds, tri chronologique, unicité d'UID, propagation
  d'erreurs HTTP), résilience aux données malformées.
- `tests/test_motogp_provider.py`, `test_moto2_provider.py`, `test_moto3_provider.py` —
  13 tests chacun (39 total), patron identique aux providers précédents.
- `tests/test_worldsbk_provider.py` — 23 tests, mirroring exact de
  `test_imsa_provider.py`.
- `tests/test_cli_generate_motogp.py` (17 tests), `test_cli_generate_moto2.py`
  (16 tests), `test_cli_generate_moto3.py` (14 tests) — happy path, erreurs, contenu ICS,
  unicité d'UID, vérification que tous les `DTSTART` sont `Z`-suffixés (test de
  non-régression du bug UTC).
- `tests/test_cli_generate_worldsbk.py` (21 tests) — mirroring exact de
  `test_cli_generate_imsa.py`.
- `tests/fixtures/real/motogp_events_2026.json` — 1 nouveau fichier JSON, extrait réel
  non retouché (filtré aux clés effectivement consommées par le parser — id, name,
  shortname, kind, dates, time_zone, circuit, categories, broadcasts — jamais de valeur
  inventée), couvrant 1 événement TEST, 1 événement MEDIA et 3 rounds GP réels (Thaïlande,
  USA avec catégorie BWC, Valence dernier round).
- Tests existants corrigés pour isoler les trois nouveaux providers réels (sinon appels
  réseau non mockés) : `tests/test_cli_generate.py` (fixture autouse étendue + mocks
  d'échec explicites dans les 2 tests "tous les providers échouent"),
  `tests/test_gui_controller.py` (`_WEEKEND_SOURCE_PATHS` étendu à 14 entrées + le test
  de résilience partielle — WorldSBK exclu, son stub échoue naturellement comme WEC/IMSA),
  `tests/test_gui_upcoming_weekend.py` (13 → 17 championnats attendus).
  `tests/test_gui_categories.py` **n'a nécessité aucune modification** : `Category.MOTO`
  existait déjà depuis le Sprint 37, le nombre total de catégories reste à 6.

### Fichiers modifiés / créés

| Fichier | Action |
|---|---|
| `motorsport_calendar/providers/motogp_series/__init__.py` | Créé |
| `motorsport_calendar/providers/motogp_series/pulselive_base.py` | Créé |
| `motorsport_calendar/providers/motogp/*` (6 fichiers) | Créé |
| `motorsport_calendar/providers/moto2/*` (6 fichiers) | Créé |
| `motorsport_calendar/providers/moto3/*` (6 fichiers) | Créé |
| `motorsport_calendar/providers/worldsbk/*` (6 fichiers) | Créé |
| `motorsport_calendar/cli.py` | Modifié — 4 commandes `generate-*` |
| `motorsport_calendar/gui/categories.py` | Modifié — nouveau groupe "🏍 Moto" |
| `motorsport_calendar/gui/display_names.py` | Modifié — 4 lignes |
| `motorsport_calendar/gui/upcoming_weekend.py` | Modifié — 4 lignes |
| `tests/test_pulselive_base.py` | Créé — 43 tests |
| `tests/test_motogp_provider.py` | Créé — 13 tests |
| `tests/test_moto2_provider.py` | Créé — 13 tests |
| `tests/test_moto3_provider.py` | Créé — 13 tests |
| `tests/test_worldsbk_provider.py` | Créé — 23 tests |
| `tests/test_cli_generate_motogp.py` | Créé — 17 tests |
| `tests/test_cli_generate_moto2.py` | Créé — 16 tests |
| `tests/test_cli_generate_moto3.py` | Créé — 14 tests |
| `tests/test_cli_generate_worldsbk.py` | Créé — 21 tests |
| `tests/fixtures/real/motogp_events_2026.json` | Créé |
| `tests/test_cli_generate.py` | Modifié — isolation Moto (3 sources) |
| `tests/test_gui_controller.py` | Modifié — isolation Moto (3 sources) |
| `tests/test_gui_upcoming_weekend.py` | Modifié — 1 test mis à jour (13 → 17 championnats) |
| `CHANGELOG.md` | Mis à jour |
| `docs/ROADMAP.md` | Mis à jour — v0.4.12 |
| `docs/AI_CONTEXT.md` | Mis à jour |
| `docs/TODO.md` | Mis à jour |
| `docs/DECISIONS.md` | ADR-029 ajouté |
| `docs/DATA_SOURCES.md` | Mis à jour — nouvelles sections MotoGP/Moto2/Moto3 et WorldSBK |

`gui/event_display.py`, `gui/theme.py`, `gui/championship_assets.py`, `gui/main_view.py`,
`gui/views/calendar.py`, `core/registry.py`, `core/source_registry.py`, `config/models.py`,
`tests/test_gui_categories.py`, tous les providers existants (`f1`, `f2`, `f3`,
`f1-academy`, `formula-e`, `wec`, `elms`, `mlmc`, `imsa`, `gtwc-europe`, `gtwc-america`,
`gtwc-asia`, `igtc`), Design System : **non modifiés**.

### Tests exécutés
```
1373 passed → 1539 passed — 0 failed — couverture ~96 %
(+166 tests — motogp_series/ à 89 % (le corps réel de fetch_json, jamais mocké en
 unitaire, vérifié par les smoke tests live à la place), motogp/moto2/moto3/worldsbk à
 100 %)
```

Vérification ruff/mypy sur les fichiers touchés : zéro nouvelle dette introduite — les
seuls avertissements ruff restants correspondent exactement au motif déjà présent dans
WEC/ELMS/MLMC/IMSA/GT (`_make_provider(source)` sans annotation) et aux erreurs mypy déjà
acceptées dans `F1CalendarBaseSource` (`list | dict` sans paramètres génériques, imposé
par la signature abstraite `JsonDataSource.fetch_json`). mypy :
`Success: no issues found` sur l'ensemble des 22 nouveaux fichiers providers Moto (4
erreurs restantes, identiques au motif `F1CalendarBaseSource`).

Vérification manuelle additionnelle (vrais appels réseau, pas de mock) :
`motocal generate-motogp 2026 motogp.ics` → 22 événements, 132 sessions, tous les
`DTSTART` `Z`-suffixés après correction du bug UTC.
`motocal generate-moto2 2026 moto2.ics` → 22 événements, 110 sessions.
`motocal generate-moto3 2026 moto3.ics` → 22 événements, 110 sessions.
`motocal generate-worldsbk 2026 worldsbk.ics` → message d'erreur propre, exit code 1,
aucun fichier créé (identique à `generate-wec`/`generate-imsa`).
`motocal generate 2026 all2026.ics` (agrégateur, 17 providers) → 171 événements,
810 sessions ; MotoGP/Moto2/Moto3 réussissent, WEC/IMSA/WorldSBK échouent proprement
("source non implémentée"). UID uniques confirmés sur l'export complet pour les 3
nouveaux providers (4 doublons détectés dans l'export appartiennent tous à
`openf1-meeting-*` — un défaut préexistant du provider Formula 1, non lié à ce sprint,
non modifié). `get_upcoming_weekend()` en direct : cartes MotoGP/Moto2/Moto3 authentiques
trouvées pour le Grand Prix d'Allemagne (week-end réel du 10-12 juillet 2026), aux côtés
d'une carte GT World Challenge Asia, aucune erreur.
`registry.list_all()` / `categories.get_groups_for()` / `display_names.get_display_name()`
: les 4 championnats apparaissent correctement dans le nouveau groupe "🏍 Moto".

### Limites
- `OfficialWorldSbkSource` reste un stub `NotImplementedError` — **aucune source de
  données WorldSBK exploitable n'a été trouvée** après investigation (calendrier
  entièrement rendu côté client, hôte API candidat injoignable depuis l'extérieur). "Ce
  week-end" et `generate-worldsbk` n'afficheront jamais de données WorldSBK réelles tant
  qu'une source n'est pas trouvée — dette technique documentée dans
  `docs/DATA_SOURCES.md`, `docs/TODO.md` et ADR-029, décision explicitement confirmée
  avec l'utilisateur.
- Durée des sessions RACE/SPRINT (MotoGP/Moto2/Moto3) approximative — la source ne
  fournit jamais d'heure de fin réelle pour ces deux types de session (FP/Qualifying ont
  des heures réelles). Comportement documenté, cohérent avec les durées par défaut déjà
  utilisées par `JolpicaSource`/`OpenF1Source`/ACO/SRO.
- `PulseliveGpSource.get_season(year)` n'a pas été testé pour une saison passée (années
  antérieures à 2026) — hors périmètre demandé ce sprint.
- `motogp`/`moto2`/`moto3`/`worldsbk` absents de
  `championship_assets.py::_LOGO_FILENAMES` (conforme à la contrainte "aucun travail sur
  les icônes" de ce sprint).
- Bug préexistant identifié mais non corrigé (hors périmètre du sprint, provider non
  touché) : `openf1-meeting-*` génère occasionnellement des UID dupliqués dans
  l'agrégateur `generate` lorsqu'une saison F1 a 3+ séances d'essais libres pour un même
  meeting (fallback `SessionType.FREE_PRACTICE` réutilisé sans distinction FP1/FP2/FP3
  dans `providers/formula1/sources/openf1.py`). Documenté ici pour une correction future
  éventuelle du provider Formula 1.

---

## Session 2026-07-10 — Sprint 37 : GT Racing (GT World Challenge Europe/America/Asia, IGTC)

### Objectif
Enrichir la discipline GT en ajoutant quatre championnats organisés par SRO Motorsports
Group : GT World Challenge Europe, GT World Challenge America, GT World Challenge Asia et
l'Intercontinental GT Challenge (IGTC). Aucune évolution graphique, aucune nouvelle
fonctionnalité utilisateur. Consignes explicites : étudier les sources disponibles,
identifier les points communs entre les séries SRO, ne mutualiser que si justifié,
conserver l'architecture actuelle, intégration automatique partout (Wizard, "Ce week-end",
génération ICS, catégories, noms lisibles, préférences), tests complets, zéro régression,
documentation complète puis `docs/JOURNAL.md` selon la procédure établie (Sprint 34).

### Recherche de la source de données
Aucune des quatre séries n'a d'API publique documentée. Recherche menée par fetch direct du
HTML réel des quatre sites `.com` (pas de résumé IA à cette étape — le futur code de
parsing doit correspondre au HTML octet pour octet) :

- Les quatre sites (gt-world-challenge-europe.com, -america.com, -asia.com,
  intercontinentalgtchallenge.com) tournent sur un **CMS identique**, confirmé en
  comparant des pages réelles des quatre domaines : même schéma d'URL
  (`/event/{id}/{slug}`), mêmes classes CSS (`timetable__container`,
  `timetable__table`, `feature__heading`, `track-information`), même format de balise
  `<title>` ("{Nom}, {Pays}, {dates} | {Série}").
- **Aucun JSON-LD n'est présent nulle part** sur ces sites — contrairement à WEC/ELMS/MLMC
  (Sprint 35). Chaque page course expose uniquement un `<table class="timetable__table">`
  HTML classique par jour de week-end (colonnes Session / Local Time / GMT), et **aucune
  heure de fin de session** n'est jamais donnée. C'est la première extension de
  championnat de ce projet où le scraping HTML au sens littéral (sans donnée structurée
  intermédiaire) est réellement le dernier recours justifié, conformément à la consigne du
  sprint ("N'utiliser le scraping HTML qu'en dernier recours").
- La page calendrier (`/calendar`) de chaque site liste les rounds via un texte "Round N"
  (ou "Round N & M" chez GT World Challenge Asia, un même week-end comptant double dans son
  propre système de points) associé à un lien `/event/{id}/{slug}` — les entrées sans
  label "Round" (jours de tests officiels) sont naturellement exclues du même geste,
  suivant le précédent établi pour ACO au Sprint 35.
- Un href malformé a été repéré côté IGTC pour Indianapolis 8 Hour
  (`/event/153/Indianapolis 8 Hour` — espace brut et casse mixte, manifestement un bug côté
  SRO, pas corrigé côté source mais rendu robuste côté requête HTTP via encodage URL).

### Travail effectué

**`motorsport_calendar/providers/sro_series/`** — nouvelle abstraction partagée
- `timetable_base.py::SroTimetableSource(HtmlDataSource, ABC)` : toute la logique
  HTTP/cache/scraping HTML (liste des rounds)/parsing de tableaux/classification de
  sessions/inférence de durée vit ici. 2 propriétés abstraites par sous-classe :
  `_series_key`, `_base_url`, plus `_make_championship()`.
- `circuit_data.py::SRO_CIRCUIT_DATA` — table de circuits **partagée** entre les quatre
  séries, clé = slug d'URL (un même slug comme `crowdstrike-24-hours-of-spa` identifie la
  même venue réelle sur plusieurs domaines SRO, constaté empiriquement). Le pays n'y figure
  volontairement pas : la balise `<title>` de chaque page l'expose déjà de façon fiable.
- Trois subtilités de données gérées **génériquement** (pas par série) :
  1. **Format "Sprint Cup" à deux manches** (GTWC Europe/Asia) contre **format à une seule
     course** (Endurance Cup, GTWC America, IGTC) : plutôt que supposer un nombre de
     sessions fixe, chaque événement compte ses propres entrées "Race" — une seule →
     `QUALIFYING`/`RACE` classiques ; deux → la première chronologiquement devient
     `SPRINT_QUALIFYING`/`SPRINT` (même mécanisme que les week-ends Sprint F1), la seconde
     reste `QUALIFYING`/`RACE`. Les entrées Qualifying sont réparties selon la Race
     qu'elles précèdent chronologiquement.
  2. **Séances Free Practice en surnombre** (Bathurst 12 Hour : jusqu'à 6 séances
     numérotées, alors que le modèle n'a que 3 emplacements FP1/FP2/FP3) : les deux
     premières (par ordre chronologique) mappent normalement, tout ce qui suit la 3ème est
     fusionné dans une seule session FP3 (span étendu) plutôt que perdu.
  3. Sessions non compétitives (tests, parades, pit walks, warm-up, "pre-qualifying")
     exclues par mots-clés, cohérent avec le précédent d'exclusion des jours de tests ACO.
  4. "Superpole" (séance shootout à un tour, présente sur certains rounds Endurance
     Cup/IGTC) réutilise `SessionType.HYPERPOLE` — le terme "Superpole" est d'ailleurs
     l'origine historique du terme "Hyperpole" employé par le WEC.

**`motorsport_calendar/providers/gtwc_europe/`**, **`gtwc_america/`**, **`gtwc_asia/`**,
**`igtc/`**
- Patron Provider/Source identique aux championnats précédents. Source concrète
  (`sources/sro_scraper.py::SroScraperSource`) héritant de `SroTimetableSource`, ne
  déclarant que la configuration spécifique à la série.
- Chaque championnat re-numérote ses rounds séquentiellement lui-même (comme
  `AcoSportsEventSource`), plutôt que de reproduire le texte "Round N" du site —
  nécessaire de toute façon pour GT World Challenge Asia ("Round N & M").

**`motorsport_calendar/cli.py`**
- `generate-gtwc-europe`, `generate-gtwc-america`, `generate-gtwc-asia`, `generate-igtc`
  (`YEAR OUTPUT.ics`) ajoutées sur le helper `_run_generate_command()` (Sprint 34).

**Intégration GUI — nouvelle catégorie, 4 lignes**
- `gui/categories.py` : nouveau `Category.GT = "gt"`, nouveau groupe
  `ChampionshipGroup(category=Category.GT, label="GT", emoji="🚗", championship_ids=
  ("gtwc-europe", "gtwc-america", "gtwc-asia", "igtc"))`. Le groupe "Endurance" existant
  (WEC/ELMS/MLMC/IMSA) reste inchangé.
- `gui/display_names.py` : 4 entrées ajoutées.
- `gui/upcoming_weekend.py::WEEKEND_CHAMPIONSHIP_IDS` : 4 IDs ajoutés.
- `gui/event_display.py::_GP_SUFFIX_CHAMPIONSHIPS` : **aucun changement** — les 4 nouveaux
  IDs n'y figurent pas par défaut (comme WEC/ELMS/MLMC/FormulaE/IMSA), donc leurs noms
  d'événement ("Misano", "CrowdStrike 24 Hours of Spa"…) ne recevront jamais le suffixe
  "Grand Prix".
- Aucune ligne dans `main_view.py`/`calendar.py` — vérifié en confirmant que les 4
  championnats apparaissent automatiquement dans un nouveau groupe "🚗 GT" sans code de vue
  supplémentaire.

**Bug réel détecté en vérification live (pas en test unitaire), corrigé avant livraison :**
Combiner directement la date locale de la légende du tableau (ex. "Friday, 13 February")
avec l'heure de la colonne GMT produisait un jour UTC incorrect chaque fois que le décalage
horaire du circuit poussait une séance du petit matin local vers la veille en UTC — confirmé
sur Bathurst 12 Hour (Sydney, UTC+10/+11) : la première séance d'essais libres du vendredi
matin local (08:45 local) se retrouvait calculée sur le **vendredi UTC** au lieu du
**jeudi UTC** (22:45 GMT réel), ce qui cassait entièrement l'ordre chronologique des
sessions (FP1 se retrouvait après FP5/FP6 dans le tri). Corrigé en calculant le véritable
instant UTC à partir de l'écart entre les colonnes "Local Time" et "GMT" de chaque ligne du
tableau (`_resolve_utc_datetime()`) — aucune base de fuseaux horaires externe requise, la
source donne déjà les deux valeurs nécessaires sur chaque ligne.

**Nettoyage qualité (ruff) après première passe fonctionnelle**
- `ruff check --fix` a corrigé automatiquement le tri des imports et la conversion
  `timezone.utc` → `datetime.UTC` dans `timetable_base.py`.
- Deux lignes de construction de `Session(...)` dépassant 100 caractères reformatées
  manuellement (aucun changement de comportement).
- Docstring de module `igtc/sources/sro_scraper.py` raccourcie (dépassait 100 caractères).
- Comparaison avant/après confirmée : seuls 9 avertissements ruff pré-existants restent
  (motif `_make_provider(source)` sans annotation, identique aux 4 autres providers scrapés
  du projet ; `Category(str, Enum)` au lieu de `StrEnum`, préexistant avant ce sprint) —
  zéro nouvelle dette introduite.

**Tests**
- `tests/test_sro_timetable_base.py` — 74 tests : classification de labels (race/
  qualifying/practice/superpole/exclu), parsing d'heures (24h et 12h AM/PM), résolution
  UTC (décalage positif avec recul d'un jour, décalage négatif), extraction de rounds sur
  les 4 fixtures calendrier réelles (y compris l'ordre DOM non chronologique de GTWC
  America et le href malformé d'IGTC), construction de sessions sur 5 fixtures réelles
  (Sprint Cup Misano, Endurance Spa 24h, surnombre FP Bathurst, format simple COTA, Sprint
  Cup via Asia Sepang), résolution de circuit (slug connu + inconnu), extraction de pays,
  inférence de durée, `get_season()` bout-en-bout avec `fetch_html` mocké, résilience aux
  données malformées.
- `tests/test_gtwc_europe_provider.py`, `test_gtwc_america_provider.py`,
  `test_gtwc_asia_provider.py`, `test_igtc_provider.py` — 13 tests chacun (52 total),
  patron identique aux providers précédents.
- `tests/test_cli_generate_gtwc_europe.py` (18 tests), `test_cli_generate_gtwc_america.py`
  (15 tests), `test_cli_generate_gtwc_asia.py` (11 tests), `test_cli_generate_igtc.py`
  (15 tests) — happy path, erreurs, contenu ICS, unicité d'UID (avec dépliage RFC 5545 des
  lignes repliées — les UID basés sur des slugs plus longs que ceux d'ACO/ELMS peuvent
  dépasser la largeur de repli de 75 octets, contrairement aux suites CLI précédentes).
- `tests/fixtures/real/` — 9 nouveaux fichiers HTML, extraits réels non retouchés
  (calendrier + une page course par site, réduits à la balise `<title>`, l'en-tête
  `feature__heading` et les blocs `timetable__container` — même convention que les
  fixtures ACO).
- Tests existants corrigés pour isoler les quatre nouveaux providers réels (sinon appels
  réseau non mockés, provoquant un timeout complet de la suite) :
  `tests/test_cli_generate.py` (fixture autouse étendue + mocks d'échec explicites dans les
  2 tests "tous les providers échouent"), `tests/test_gui_controller.py`
  (`_WEEKEND_SOURCE_PATHS` étendu à 11 entrées + le test de résilience partielle),
  `tests/test_gui_upcoming_weekend.py` (9 → 13 championnats attendus),
  `tests/test_gui_categories.py` (5 → 6 catégories attendues suite à l'ajout de
  `Category.GT`).

### Fichiers modifiés / créés

| Fichier | Action |
|---|---|
| `motorsport_calendar/providers/sro_series/__init__.py` | Créé |
| `motorsport_calendar/providers/sro_series/timetable_base.py` | Créé |
| `motorsport_calendar/providers/sro_series/circuit_data.py` | Créé |
| `motorsport_calendar/providers/gtwc_europe/*` (6 fichiers) | Créé |
| `motorsport_calendar/providers/gtwc_america/*` (6 fichiers) | Créé |
| `motorsport_calendar/providers/gtwc_asia/*` (6 fichiers) | Créé |
| `motorsport_calendar/providers/igtc/*` (6 fichiers) | Créé |
| `motorsport_calendar/cli.py` | Modifié — 4 commandes `generate-*` |
| `motorsport_calendar/gui/categories.py` | Modifié — nouveau `Category.GT` + groupe |
| `motorsport_calendar/gui/display_names.py` | Modifié — 4 lignes |
| `motorsport_calendar/gui/upcoming_weekend.py` | Modifié — 4 lignes |
| `tests/test_sro_timetable_base.py` | Créé — 74 tests |
| `tests/test_gtwc_europe_provider.py` | Créé — 13 tests |
| `tests/test_gtwc_america_provider.py` | Créé — 13 tests |
| `tests/test_gtwc_asia_provider.py` | Créé — 13 tests |
| `tests/test_igtc_provider.py` | Créé — 13 tests |
| `tests/test_cli_generate_gtwc_europe.py` | Créé — 18 tests |
| `tests/test_cli_generate_gtwc_america.py` | Créé — 15 tests |
| `tests/test_cli_generate_gtwc_asia.py` | Créé — 11 tests |
| `tests/test_cli_generate_igtc.py` | Créé — 15 tests |
| `tests/fixtures/real/*.html` (9 fichiers) | Créé |
| `tests/test_cli_generate.py` | Modifié — isolation GT (4 sources) |
| `tests/test_gui_controller.py` | Modifié — isolation GT (4 sources) |
| `tests/test_gui_upcoming_weekend.py` | Modifié — 1 test mis à jour (9 → 13 championnats) |
| `tests/test_gui_categories.py` | Modifié — 2 tests mis à jour (5 → 6 catégories) |
| `CHANGELOG.md` | Mis à jour |
| `docs/ROADMAP.md` | Mis à jour — v0.4.11 |
| `docs/AI_CONTEXT.md` | Mis à jour |
| `docs/TODO.md` | Mis à jour |
| `docs/DECISIONS.md` | ADR-028 ajouté |
| `docs/DATA_SOURCES.md` | Mis à jour — nouvelle section GT Racing |

`gui/event_display.py`, `gui/theme.py`, `gui/championship_assets.py`, `gui/main_view.py`,
`gui/views/calendar.py`, `core/registry.py`, `core/source_registry.py`, `config/models.py`,
tous les providers existants (`f1`, `f2`, `f3`, `f1-academy`, `formula-e`, `wec`, `elms`,
`mlmc`, `imsa`), Design System : **non modifiés**.

### Tests exécutés
```
1189 passed → 1373 passed — 0 failed — couverture ~96 %
(+184 tests — sro_series/ à 92 % (le corps réel de fetch_html, jamais mocké en unitaire,
 vérifié par les smoke tests live à la place), gtwc_*/igtc à 100 %)
```

Vérification ruff/mypy (comparaison avant/après via `git stash`, sur les fichiers touchés) :
zéro nouvelle dette introduite — les seuls avertissements ruff restants correspondent
exactement au motif déjà présent dans WEC/ELMS/MLMC/IMSA (`_make_provider(source)` sans
annotation) et à `Category(str, Enum)` (préexistant, confirmé identique avant/après par
`git stash`). mypy : `Success: no issues found in 23 source files` sur l'ensemble des
nouveaux fichiers providers GT.

Vérification manuelle additionnelle (vrais appels réseau, pas de mock) :
`motocal generate-gtwc-europe 2026 gtwce.ics` → 10 événements, 45 sessions, 45 UID uniques
(vérifiés après dépliage RFC 5545).
`motocal generate-gtwc-america 2026 gtwca.ics` → 4 événements, 19 sessions (3 rounds sans
timetable publié correctement exclus), UID uniques.
`motocal generate-gtwc-asia 2026 gtwcasia.ics` → 4 événements, 20 sessions, UID uniques.
`motocal generate-igtc 2026 igtc.ics` → 3 événements, 12 sessions, UID uniques.
`motocal generate 2026 all2026.ics` (agrégateur, 13 providers) → 105 événements, 458
sessions ; les 4 providers GT réussissent, WEC et IMSA échouent proprement ("source non
implémentée", stubs inchangés). `get_upcoming_weekend()` en direct : une carte GT World
Challenge Asia authentique trouvée pour le week-end réel du 10-12 juillet 2026 (Fuji
International Speedway, 5 sessions), aucune erreur, aucune carte fantôme.
`registry.list_all()` / `categories.get_groups_for()` / `display_names.get_display_name()`
: les 4 championnats apparaissent correctement dans le nouveau groupe "🚗 GT".

### Limites
- Certains rounds éloignés dans le calendrier n'ont pas encore de tableau d'horaires publié
  par SRO au moment de ce sprint (ex. Indianapolis 8 Hour, GT World Challenge America 2026)
  — ces événements sont silencieusement exclus de la saison retournée par `get_season()`
  plutôt que d'apparaître avec zéro session ; ils apparaîtront automatiquement dès que SRO
  publie leur planning, sans changement de code.
- Durée de course inférée uniquement depuis un motif "N Hour(s)" dans le slug d'URL ; les
  formats sans motif horaire explicite (ex. `suzuka-1000km`) utilisent une durée par défaut
  approximative — comportement documenté, cohérent avec les durées par défaut déjà
  utilisées par `JolpicaSource`/`OpenF1Source`.
- `SroTimetableSource.get_season(year)` n'a pas été testé pour une saison passée — le
  comportement pour une année différente de la saison publiée courante est probablement le
  même qu'ACO (propagation de `HTTPStatusError`) mais non confirmé, hors périmètre demandé.
- `gtwc-europe`/`gtwc-america`/`gtwc-asia`/`igtc` absents de
  `championship_assets.py::_LOGO_FILENAMES` (conforme à la contrainte "aucun travail sur
  les icônes" de ce sprint).
- IGTC partage deux de ses cinq rounds (CrowdStrike 24 Hours of Spa, Indianapolis 8 Hour)
  avec GT World Challenge Europe/America respectivement — chaque site les identifie
  indépendamment, aucune déduplication inter-championnats n'est effectuée (cohérent avec le
  reste du projet, voir ADR-028).

---

## Session 2026-07-10 — Sprint 36 : Extension IMSA (sortie de l'écosystème ACO)

### Objectif
Valider que l'architecture Provider/Source de `motorsport-calendar` généralise à un
championnat majeur organisé par une entité **totalement extérieure à l'ACO**, après trois
sprints consécutifs (F1/F2/F3/F1A/FE sur `sportstimes/f1`, puis WEC/ELMS/MLMC sur le CMS
ACO) où les nouvelles séries partageaient toujours une infrastructure de données déjà
connue. Cible : IMSA WeatherTech SportsCar Championship. Consigne explicite : privilégier
une API officielle, à défaut une source stable et documentée, le scraping HTML en dernier
recours seulement. Contrainte architecturale stricte : ne modifier aucun provider
existant, créer un provider IMSA dédié, ne factoriser que si une abstraction commune
apparaît naturellement (jamais par anticipation), ne jamais casser l'architecture
actuelle. Intégration automatique requise dans le Wizard, "Ce week-end", la génération
ICS, les catégories, les noms lisibles et les préférences. Documentation complète en fin
de sprint, aucun commit.

### Recherche de la source de données
Contrairement aux sprints précédents, cette investigation n'a abouti à **aucune source
exploitable** — documentée ici en détail pour que la prochaine tentative ne reparte pas de
zéro (voir aussi `providers/imsa/sources/official.py`, `docs/DATA_SOURCES.md` et ADR-027).

- **Aucune API publique documentée** — recherche infructueuse (documentation développeur,
  portails partenaires).
- **imsa.com est bloqué au niveau infrastructure**, pas seulement hostile au scraping :
  `curl` avec en-têtes navigateur complets renvoie HTTP 403 avec l'en-tête
  `cf-mitigated: challenge` (Cloudflare, challenge actif) sur absolument toutes les routes
  testées — page d'accueil, page calendrier, articles de presse individuels, et même des
  PDF statiques sous `/wp-content/uploads/`. C'est un blocage dur, pas un problème d'en-tête
  manquant ; le contourner nécessiterait une automatisation de navigateur complète
  (Playwright) — une classe de dépendance bien plus lourde que tout ce qui existe déjà
  dans le projet, et plus proche d'un contournement actif d'anti-bot que d'un scraping
  raisonnable. Non tenté.
- **Le prestataire de chronométrage d'IMSA est Al Kamel Systems** — le même que
  WEC/ELMS/MLMC (confirmé : `imsa.results.alkamelcloud.com` est accessible, contrairement
  à imsa.com). Mais ce portail est une **archive de résultats post-course**, pas un
  calendrier prévisionnel : les dossiers de session (ex. `202606261125_Practice 1`)
  n'existent qu'*après* que la session ait eu lieu. Aucune donnée utilisable pour générer
  un calendrier à l'avance.
- **Wikipedia** expose un tableau de calendrier propre et stable via son API MediaWiki
  officielle (`en.wikipedia.org/w/api.php?action=parse&page=2026_IMSA_SportsCar_
  Championship&prop=wikitext&section=2`) : round, nom de course, circuit, ville, date
  (parfois une plage de dates) et durée de course — mais **aucun horaire de session**
  (pas de FP1/FP2/Qualifying/Race). Insuffisant pour construire un `Session` valide (le
  modèle exige un début ET une fin) sans inventer des horaires.
- **Sportscar365.com** (accessible, HTTP 200) publie des horaires de session détaillés,
  mais uniquement en **prose libre** à l'intérieur d'articles individuels de type
  "notebook" (confirmé via un extrait réel : "Practice 1 - WeatherTech Championship runs
  from 1:55 pm ET to 3:25 pm ET") — pas de données structurées. **51gt3.com**, un autre
  média spécialisé publiant parfois des horaires, a lui-même renvoyé HTTP 403 au test.
  Parser du texte en langage naturel de façon fiable sur ~11 rounds x plusieurs sessions
  serait fragile et ne correspond pas à une "source stable et documentée" au sens de ce
  projet.

Face à cette impasse, les résultats complets de l'investigation ont été présentés à
l'utilisateur (AskUserQuestion, 3 options : stub à la WEC / calendrier partiel basé sur
Wikipedia avec horaires inventés / autre source suggérée par l'utilisateur) plutôt que de
choisir silencieusement entre dégrader la qualité des données ou abandonner. L'utilisateur
a confirmé l'option **"Stub à la WEC"**.

### Travail effectué

**`motorsport_calendar/providers/imsa/`** — nouveau package, mirroring exact de
`providers/wec/`
- `source.py::ImsaSource(ABC)` — contrat abstrait, une seule méthode
  `async get_season(year: int) -> list[Event]`.
- `provider.py::ImsaProvider(Provider)` — `name="imsa"`, `supported_championships=
  ["imsa"]`, `fetch_championship()` construit un `Championship(id=f"imsa-{year}",
  name="IMSA WeatherTech SportsCar Championship", category=ChampionshipCategory.
  ENDURANCE)`, `fetch_events()` délègue à la source.
- `sources/official.py::OfficialImsaSource(ImsaSource)` — stub,
  `get_season()` lève `NotImplementedError`. Docstring de module détaillant
  l'investigation complète (voir ci-dessus) pour éviter de la reproduire à l'avenir.
- `__init__.py` — enregistre `_make_provider` dans `ProviderRegistry` sous `"imsa"`.
- `sources/__init__.py` — enregistre `OfficialImsaSource` dans `SourceRegistry` sous
  `("imsa", "official")`.
- Vérifié par exécution directe : `registry.discover()` détecte `"imsa"`,
  `source_registry.get("imsa", "official")` résout correctement.

**`motorsport_calendar/cli.py`**
- `generate-imsa YEAR OUTPUT.ics` ajoutée juste après `generate-wec`, sur le helper
  `_run_generate_command()` (Sprint 34) — `default_source="official"`,
  `not_implemented_message` calqué mot pour mot sur celui de WEC (juste "WEC" → "IMSA").

**Intégration GUI — 3 lignes, zéro fichier de vue touché**
- `gui/categories.py` : groupe "Endurance" devient `("wec", "elms", "mlmc", "imsa")`.
- `gui/display_names.py` : `"imsa": "IMSA WeatherTech SportsCar Championship"` ajouté.
- `gui/upcoming_weekend.py::WEEKEND_CHAMPIONSHIP_IDS` : `"imsa"` ajouté.
- `gui/event_display.py::_GP_SUFFIX_CHAMPIONSHIPS` : **aucun changement nécessaire** —
  IMSA n'y figure pas par défaut (comme WEC/ELMS/MLMC/FormulaE), donc ses noms d'événement
  ("Rolex 24 at Daytona", "12 Hours of Sebring"…) ne recevront jamais le suffixe erroné
  "Grand Prix" une fois la source réellement implémentée.

**Validation live du comportement du stub (identique à WEC point par point)**
- `motocal generate-imsa 2026 imsa.ics` → message "La source IMSA 'official' n'est pas
  encore implémentée…", exit code 1, aucun fichier créé.
- `motocal generate 2026 all.ics` (agrégateur, 9 providers désormais) → `✗ imsa : source
  non implémentée` affiché proprement aux côtés de `✗ wec`, exit code 0, 84 événements /
  362 sessions inchangés (les 7 autres providers réussissent normalement).
- `registry.list_all()` → `imsa` présent ; `categories.get_groups_for(ids)` → IMSA classé
  dans le groupe "🏁 Endurance" aux côtés de wec/elms/mlmc ; `get_display_name("imsa")` →
  "IMSA WeatherTech SportsCar Championship".
- `get_upcoming_weekend()` en direct : ne lève aucune exception, produit normalement les
  cartes F1/F2/F3 du week-end réel sans jamais inclure IMSA ni WEC (les deux stubs
  échouent silencieusement au niveau prévu, comme conçu depuis le Sprint 26).

### Tests
- `tests/test_imsa_provider.py` — 23 tests, mirroring exact de `test_wec_provider.py` :
  `FakeImsaSource` (test double), fixtures Daytona (Rolex 24, sessions FREE_PRACTICE/
  QUALIFYING/RACE), `TestImsaSourceABC`, `TestImsaProviderIdentity`, `TestFetchEvents`,
  `TestFetchChampionship`, `TestImsaSessionTypes`, `TestOfficialImsaSource`,
  `TestModelInteroperability` (interopérabilité avec `australian_gp` du conftest F1).
- `tests/test_cli_generate_imsa.py` — 16 tests, mirroring exact de
  `test_cli_generate_wec.py` : happy path (Daytona + Sebring, 3 sessions), erreurs
  (`NotImplementedError` sans mock nécessaire, `HTTPStatusError`, `TimeoutException`),
  `--refresh`. Un ajustement nécessaire par rapport au template WEC : l'assertion de
  localisation dans l'ICS vérifie `circuit.name` (`"Daytona International Speedway"`,
  `"Sebring International Raceway"`) plutôt que `circuit.city`, car `IcsExporter` compose
  la ligne `LOCATION` à partir de `circuit.name`/`circuit.country` (le test WEC original
  passait "par coïncidence" avec `circuit.city` puisque son `circuit.name` valait
  également "Sebring").
- `tests/test_gui_upcoming_weekend.py` : `TestWeekendChampionshipIds` mis à jour (8 → 9
  championnats attendus, `"imsa"` ajouté en fin de tuple).
- `tests/test_cli_generate.py`, `tests/test_gui_controller.py` : **aucune modification
  nécessaire** — IMSA suit exactement le même chemin que WEC (`OfficialImsaSource` échoue
  naturellement sans mock), les tests "tous les providers échouent" et
  `_WEEKEND_SOURCE_PATHS` n'avaient pas besoin d'entrée dédiée pour WEC et n'en ont donc
  pas besoin non plus pour IMSA. Vérifié en exécutant la suite complète après les
  modifications GUI — 65/65 tests passent sans changement.

### Fichiers modifiés / créés

| Fichier | Action |
|---|---|
| `motorsport_calendar/providers/imsa/__init__.py` | Créé |
| `motorsport_calendar/providers/imsa/provider.py` | Créé |
| `motorsport_calendar/providers/imsa/source.py` | Créé |
| `motorsport_calendar/providers/imsa/sources/__init__.py` | Créé |
| `motorsport_calendar/providers/imsa/sources/official.py` | Créé |
| `motorsport_calendar/cli.py` | Modifié — `generate-imsa` |
| `motorsport_calendar/gui/categories.py` | Modifié — 1 ligne |
| `motorsport_calendar/gui/display_names.py` | Modifié — 1 ligne |
| `motorsport_calendar/gui/upcoming_weekend.py` | Modifié — 1 ligne |
| `tests/test_imsa_provider.py` | Créé — 23 tests |
| `tests/test_cli_generate_imsa.py` | Créé — 16 tests |
| `tests/test_gui_upcoming_weekend.py` | Modifié — 1 test mis à jour (8 → 9 championnats) |
| `CHANGELOG.md` | Mis à jour |
| `docs/ROADMAP.md` | Mis à jour — v0.4.10 |
| `docs/AI_CONTEXT.md` | Mis à jour |
| `docs/TODO.md` | Mis à jour |
| `docs/DECISIONS.md` | ADR-027 ajouté |
| `docs/DATA_SOURCES.md` | Mis à jour — nouvelle section IMSA (investigation complète) |

`gui/event_display.py`, `gui/theme.py`, `gui/championship_assets.py`, `gui/main_view.py`,
`gui/views/calendar.py`, `core/registry.py`, `core/source_registry.py`, `config/models.py`,
tous les autres providers (`f1`, `f2`, `f3`, `f1-academy`, `formula-e`, `wec`, `elms`,
`mlmc`), Design System : **non modifiés**.

### Tests exécutés
```
1150 passed → 1189 passed — 0 failed — couverture ~96 %
(+39 tests — providers/imsa/ à 86-100 % selon fichier, le corps du stub
 OfficialImsaSource.get_season est trivial — une seule ligne `raise NotImplementedError`,
 entièrement couverte)
```

Vérification manuelle additionnelle (comportement réel, pas de mock) :
`motocal generate-imsa 2026 imsa.ics` → message d'erreur propre, exit code 1, aucun
fichier créé (identique à `generate-wec`).
`motocal generate 2026 all.ics` (agrégateur, 9 providers) → `✗ imsa : source non
implémentée` aux côtés de `✗ wec`, exit code 0, 84 événements / 362 sessions (inchangé —
IMSA n'ajoute aucun événement tant que le stub reste `NotImplementedError`).
`get_upcoming_weekend()` en direct : aucune exception, cartes F1/F2/F3 du week-end réel
affichées normalement, aucune carte IMSA ni WEC (comportement attendu du stub).
`registry.list_all()` / `categories.get_groups_for()` / `display_names.get_display_name()`
: IMSA apparaît correctement dans le groupe "🏁 Endurance" avec son nom complet.

### Limites
- `OfficialImsaSource` reste un stub `NotImplementedError` — **aucune source de données
  IMSA exploitable n'a été trouvée** après investigation exhaustive (imsa.com bloqué par
  Cloudflare, Al Kamel = résultats post-course uniquement, Wikipedia = pas d'horaires de
  session, Sportscar365/51gt3.com = données non structurées ou inaccessibles). "Ce
  week-end" et `generate-imsa` n'afficheront jamais de données IMSA réelles tant qu'une
  source n'est pas trouvée — dette technique documentée dans `docs/DATA_SOURCES.md`,
  `docs/TODO.md` et ADR-027, décision explicitement confirmée avec l'utilisateur plutôt
  que d'inventer des horaires de session non fiables.
- `imsa` absent de `championship_assets.py::_LOGO_FILENAMES` (aucun logo officiel
  disponible, hors périmètre de ce sprint).
- Objectif architectural du sprint néanmoins pleinement atteint : le provider IMSA
  s'intègre dans le registry, le Wizard, "Ce week-end", l'agrégateur, les catégories et
  les noms lisibles sans qu'aucun provider existant n'ait été modifié, confirmant que
  l'architecture Provider/Source généralise à un organisateur entièrement nouveau, même
  en l'absence de toute donnée réelle.

---

## Session 2026-07-10 — Sprint 35 : Extension Endurance (ELMS, Michelin Le Mans Cup)

### Objectif
Compléter la famille Endurance en ajoutant European Le Mans Series (ELMS) et Michelin Le
Mans Cup (MLMC), pour valider définitivement l'architecture multi-championnats. Aucune
nouvelle fonctionnalité utilisateur, aucune modification de la logique métier existante.
Factoriser avec WEC uniquement si une logique commune apparaît naturellement — ne jamais
factoriser par anticipation.

### Recherche de la source de données
Aucune des trois séries (WEC, ELMS, MLMC) n'a d'API publique documentée, et aucune n'est
dans le dataset `sportstimes/f1` utilisé par F2/F3/F1 Academy/Formula E (confirmé :
`_db/` ne contient que `extremee, f1-academy, f1, f2, f3, fe, indycar, motogp`). Recherche
menée par fetch direct du HTML réel (pas de résumé IA à cette étape — le futur code de
parsing doit correspondre au HTML octet pour octet) :

- `europeanlemansseries.com/en/season` et `lemanscup.com/en/season` : calendrier
  **rendu côté serveur** (contrairement à l'hypothèse de `docs/DATA_SOURCES.md`, jamais
  vérifiée avant ce sprint) — un simple `curl`/`httpx` suffit, aucun rendu JS requis pour
  le calendrier lui-même (seuls les tableaux de classement MLMC nécessitent du JS, hors
  scope).
- Chaque page course (`/en/race/{slug}-{year}`) embarque un bloc
  `<script type="application/ld+json">` schema.org `SportsEvent`, avec un tableau
  `subEvent` — un objet par session, horodatage ISO 8601 exact (offset UTC inclus).
  Confirmé identique sur les deux sites (mêmes clés, même vocabulaire de libellés de
  session : "Free Practice 1", "Bronze Driver Collective Test", "Qualifying...", "Race").
- `fiawec.com` (WEC) affiche la même navigation secondaire ("24H Le Mans, ELMS, MLMC,
  ALMS") et le même schéma JSON-LD sur la page inspectée — mais seul un Prologue a pu
  être vérifié (structure "Morning/Afternoon Session", différente de FP1/FP2/Qualifying/
  Hyperpole/Race). Une vraie manche de championnat n'a pas été confirmée : brancher WEC
  sur cette même abstraction est documenté comme piste (TODO.md, AI_CONTEXT.md) plutôt
  qu'implémenté ce sprint — hors périmètre demandé, et factoriser sans confirmation
  aurait été de la factorisation par anticipation.
- Les deux sites ne publient pas d'archive de saisons passées à une URL prévisible
  (`/en/season/{year}` répond 404 pour toute année ≠ année courante) — limitation
  assumée, propage `httpx.HTTPStatusError` comme le reste du projet.

### Travail effectué

**`motorsport_calendar/providers/aco_series/`** — nouvelle abstraction partagée
- `sports_event_base.py::AcoSportsEventSource(HtmlDataSource, ABC)` : toute la logique
  HTTP/cache/scraping HTML (liste des rounds)/parsing JSON-LD (sessions) vit ici. 4
  propriétés abstraites par sous-classe : `_series_key`, `_base_url`,
  `_event_name_prefix`, `_circuit_data`, plus `_make_championship()`.
- `circuit_data.py::ACO_CIRCUIT_DATA` — table de circuits **partagée** entre ELMS et
  MLMC (co-localisés sur les 6 mêmes circuits 2026 en 2026 : Barcelone, Le Castellet,
  Imola, Spa, Silverstone, Portimão + Le Mans pour Road to Le Mans) — factorisation
  justifiée par un fait constaté, pas anticipée.
- Deux subtilités de données gérées **génériquement** (dans la base partagée, jamais par
  série) :
  1. Qualifications multi-classes (ex. Barcelone ELMS : 4 créneaux de 25 min
     consécutifs, un par classe) mappent toutes vers `SessionType.QUALIFYING` —
     collision d'UID potentielle (`{event_uid}-{session.type}`). Fusionnées en une seule
     `Session` (premier créneau → dernier créneau + durée par défaut), plutôt que le
     contournement F1 Academy (ADR-016, relabelling vers un `SessionType` non lié) : plus
     honnête sémantiquement, et l'unicité d'UID est acquise sans artifice.
  2. Jours de tests pré-saison ("Official Tests"/"Collective Tests") exclus de la liste
     des rounds scrapés — pas des manches de championnat, et leur structure de sessions
     ("Morning/Afternoon Session" répétés sur plusieurs jours) recréerait le même
     problème de collision sans bénéfice utilisateur.

**`motorsport_calendar/providers/elms/`** et **`motorsport_calendar/providers/mlmc/`**
- Patron Provider/Source identique aux championnats précédents. Source concrète
  (`sources/aco_scraper.py::AcoScraperSource`) héritant de `AcoSportsEventSource`, ne
  déclarant que la configuration spécifique à la série.
- Road to Le Mans **n'a pas** de `championship_id` séparé — elle apparaît comme un round
  de plus dans `mlmc.get_season()`, fidèle à sa présentation sur le site officiel (une
  entrée de plus sur la même page saison). Confirmé en direct : round 3/6 en 2026.

**`motorsport_calendar/cli.py`**
- `generate-elms YEAR OUTPUT.ics` et `generate-mlmc YEAR OUTPUT.ics` ajoutées sur le
  helper `_run_generate_command()` (Sprint 34) — aucune nouvelle logique CLI.

**Intégration GUI — 3 lignes, zéro fichier de vue touché**
- `gui/categories.py` : groupe "Endurance" devient `("wec", "elms", "mlmc")`
- `gui/display_names.py` : `"mlmc": "Michelin Le Mans Cup"` ajouté (`"elms"` était déjà
  anticipée depuis un sprint antérieur)
- `gui/upcoming_weekend.py::WEEKEND_CHAMPIONSHIP_IDS` : `"elms"`, `"mlmc"` ajoutés
- Aucune ligne dans `main_view.py`/`calendar.py` — vérifié en confirmant qu'ELMS/MLMC
  apparaissent automatiquement dans le groupe "🏁 Endurance" sans code de vue
  supplémentaire.

**Deux bugs réels détectés en vérification live (pas en test unitaire), corrigés avant
livraison :**
1. **Durée de course "Road to Le Mans" à +61h au lieu de ~3h.** La règle "durée de course
   = `endDate` de l'événement top-level moins l'heure de départ de la course" fonctionne
   parfaitement pour les rounds ELMS/MLMC réguliers (`endDate` coïncide avec la fin de
   course, vérifié exact : 4h pour ELMS, 2h pour MLMC) — mais pour Road to Le Mans,
   `endDate` (2026-06-14T23:00) couvre toute la semaine des 24 Heures du Mans, pas
   seulement la course RTLM elle-même (2026-06-12T10:00 + quelques heures). Corrigé par
   un plafond de plausibilité (`_MAX_PLAUSIBLE_RACE_DURATION = timedelta(hours=26)`,
   couvre même Le Mans 24h) — au-delà, repli sur la durée par défaut documentée.
2. **Pollution de cache croisée entre tests, révélée par `test_cli_generate.py`.**
   `fetch_html` n'était initialement PAS transparent au cache (une méthode `_cached()`
   séparée l'enveloppait) — contrairement à `F1CalendarBaseSource.fetch_json`, qui
   encapsule sa propre logique de cache. Un mock posé sur `fetch_html` en test ne
   suffisait donc pas à contourner le vrai cache disque, provoquant des résultats
   incohérents entre tests utilisant la même année. Corrigé en déplaçant la logique de
   cache directement dans `fetch_html`, supprimant `_cached()` — aucun changement de
   comportement observable, juste une meilleure testabilité (même contrat que le module
   sœur). Un second symptôme du même problème a été trouvé **après** ce correctif, en
   conditions réellement live (`motocal generate-elms`/`generate-mlmc` en CLI réelle,
   pas en test) : une entrée de cache **périmée**, écrite par une version antérieure du
   code avant ce correctif, restait présente dans `~/.cache/motorsport-calendar/` (le
   vrai chemin de cache utilisé par la CLI via `ConfigService` — différent du `.cache/`
   local au dépôt utilisé par mes scripts de vérification ad hoc, d'où le fait que
   `rm -rf .cache` répété dans le dépôt ne suffisait pas à la faire disparaître).
   Diagnostiquée en décodant la clé de cache SHA256 et en inspectant le fichier JSON
   correspondant directement — supprimée, plus aucune trace du bug ensuite.

**Nouvelle dépendance**
- `beautifulsoup4>=4.12`, `lxml>=5.0` ajoutées à `pyproject.toml` — `core/datasource/
  html_source.py` anticipait déjà cette classe d'implémentation dans sa docstring
  ("typical implementations use httpx or playwright... and BeautifulSoup / lxml").

**Tests**
- `tests/test_aco_sports_event_base.py` — 43 tests : parsing JSON-LD, extraction des
  liens de rounds (avec filtrage des jours de tests), fusion des qualifications
  multi-classes, calcul de durée de course (cas normal + cas RTLM plafonné), résolution
  de circuit (connu + inconnu, repli propre), résilience aux données malformées
  (JSON-LD cassé, `startDate` absent, libellé de session non reconnu), `get_season()`
  bout-en-bout avec `fetch_html` mocké (succès, saison vide, propagation d'erreur HTTP)
- `tests/test_elms_provider.py`, `tests/test_mlmc_provider.py` — 13 et 14 tests, patron
  identique aux providers précédents
- `tests/test_cli_generate_elms.py`, `tests/test_cli_generate_mlmc.py` — 19 et 16 tests
  (happy path, erreurs, contenu ICS, unicité d'UID)
- `tests/fixtures/real/` — 4 nouveaux fichiers HTML, extraits réels non retouchés
  (bloc JSON-LD verbatim + HTML environnant trimmé) : `elms_race_barcelona.html`,
  `mlmc_race_barcelona.html`, `mlmc_race_road_to_le_mans.html` (le cas du bug de durée
  ci-dessus), `elms_season_snippet.html` (teste le filtrage des jours de tests)
- Tests existants corrigés pour isoler les deux nouveaux providers réels (sinon appels
  réseau non mockés) : `tests/test_cli_generate.py` (fixture autouse étendue + mocks
  d'échec explicites dans les 2 tests "tous les providers échouent"),
  `tests/test_gui_controller.py` (`_WEEKEND_SOURCE_PATHS` étendu, test de résilience
  partielle étendu), `tests/test_gui_upcoming_weekend.py` (6 → 8 championnats attendus)

### Fichiers modifiés / créés

| Fichier | Action |
|---|---|
| `motorsport_calendar/providers/aco_series/__init__.py` | Créé |
| `motorsport_calendar/providers/aco_series/sports_event_base.py` | Créé |
| `motorsport_calendar/providers/aco_series/circuit_data.py` | Créé |
| `motorsport_calendar/providers/elms/*` (6 fichiers) | Créé |
| `motorsport_calendar/providers/mlmc/*` (6 fichiers) | Créé |
| `motorsport_calendar/cli.py` | Modifié — `generate-elms`, `generate-mlmc` |
| `motorsport_calendar/gui/categories.py` | Modifié — 1 ligne |
| `motorsport_calendar/gui/display_names.py` | Modifié — 1 ligne |
| `motorsport_calendar/gui/upcoming_weekend.py` | Modifié — 2 lignes |
| `pyproject.toml` | Modifié — `beautifulsoup4`, `lxml` |
| `tests/test_aco_sports_event_base.py` | Créé — 43 tests |
| `tests/test_elms_provider.py` | Créé — 13 tests |
| `tests/test_mlmc_provider.py` | Créé — 14 tests |
| `tests/test_cli_generate_elms.py` | Créé — 19 tests |
| `tests/test_cli_generate_mlmc.py` | Créé — 16 tests |
| `tests/fixtures/real/*.html` (4 fichiers) | Créé |
| `tests/test_cli_generate.py` | Modifié — isolation ELMS/MLMC |
| `tests/test_gui_controller.py` | Modifié — isolation ELMS/MLMC |
| `tests/test_gui_upcoming_weekend.py` | Modifié — 1 test mis à jour (6 → 8 championnats) |
| `CHANGELOG.md` | Mis à jour |
| `docs/ROADMAP.md` | Mis à jour |
| `docs/AI_CONTEXT.md` | Mis à jour |
| `docs/TODO.md` | Mis à jour |
| `docs/DECISIONS.md` | ADR-026 ajouté |
| `docs/DATA_SOURCES.md` | Mis à jour — ELMS/MLMC/WEC passés de "scraping HTML hypothétique" à "JSON-LD confirmé" |

`gui/theme.py`, `gui/championship_assets.py`, `gui/main_view.py`, `gui/views/calendar.py`,
`core/registry.py`, `core/source_registry.py`, `config/models.py`, `providers/wec/`,
navigation, Design System : **non modifiés**.

### Tests exécutés
```
1045 passed → 1150 passed — 0 failed — couverture 96 %
(+105 tests — aco_series/ à 94 % (le corps réel de fetch_html, jamais mocké en
 unitaire, vérifié par les smoke tests live à la place), elms/ et mlmc/ à 100 %)
```

Vérification manuelle additionnelle (vrais appels réseau, pas de mock) :
`motocal generate-elms 2026 elms.ics` → 6 événements, 29 sessions, 29 UID uniques.
`motocal generate-mlmc 2026 mlmc.ics` → 6 événements, 29 sessions, 29 UID uniques.
`motocal generate 2026 all.ics` (agrégateur, 8 providers) → 84 événements, 362 sessions,
ELMS et MLMC réussissent, WEC échoue proprement ("source non implémentée", stub
inchangé). `get_upcoming_weekend()` en direct : aucune carte ELMS/MLMC ce week-end
précis (comportement correct — pas leur semaine de course), F1/F2/F3 affichés
normalement, aucune erreur.

### Limites
- `AcoSportsEventSource.get_season(year)` ne fonctionne que pour la saison courante —
  limitation du site source (pas d'archive par année), pas du code. Documentée dans
  AI_CONTEXT.md et DATA_SOURCES.md.
- `elms`/`mlmc` absents de `championship_assets.py::_LOGO_FILENAMES` (conforme à la
  contrainte "aucun travail sur les icônes" de ce sprint).
- WEC reste un stub `NotImplementedError` — la piste JSON-LD est documentée mais pas
  implémentée (hors périmètre demandé, structure non confirmée sur une vraie manche).
- Toujours aucun environnement graphique dans ce sandbox — vérifié par 1150 tests
  unitaires (94-100 % sur les nouveaux modules) + appels réseau réels multiples + script
  de simulation du regroupement wizard, pas par capture d'écran.

---

## Session 2026-07-10 — Sprint 34 : Extension Formula (Formula E)

### Objectif
Valider que l'architecture Provider/Source/Registry absorbe un nouveau championnat sans
duplication de code, en ajoutant Formula E. Aucune nouvelle fonctionnalité utilisateur,
comportement de l'application inchangé pour tout ce qui existe déjà.

### Constat préalable — le brief citait F1 Academy par erreur
Le brief indiquait "Motorsport Calendar possède aujourd'hui : F1, F2, F3, FIA WEC" et
demandait d'ajouter F1 Academy. Vérification faite avant tout développement : F1 Academy
existe déjà entièrement (`providers/f1_academy/`, wizard, "Ce week-end", CLI
`generate-f1-academy`) depuis le Sprint 29+. Confirmé avec l'utilisateur : le périmètre
réel du sprint est Formula E seule ; F1 Academy vérifié intégré partout (registre,
catégories, noms lisibles, `WEEKEND_CHAMPIONSHIP_IDS`) sans qu'aucune modification ne soit
nécessaire.

### Recherche de la source de données
Avant d'écrire une ligne de mapping : recherche du dataset `sportstimes/f1` (déjà utilisé
par F2/F3/F1 Academy via `F1CalendarBaseSource`) — confirmé qu'un dossier `_db/fe/` y
existe (Formula E). Structure vérifiée par fetch réel de plusieurs saisons (2023, 2024,
2025) : même format `{"races": [...]}` que les autres séries support
(`name`/`location`/`round`/`slug`/`sessions`). Différence structurelle notable par rapport
à F1 Academy : un week-end Formula E double-header (ex. Jeddah 2025, deux jours consécutifs)
est déjà représenté comme **deux rounds distincts** dans le dataset, chacun avec son propre
numéro de round et sa propre session `race` unique — pas un seul événement avec
race1/race2/race3 comme F1 Academy. Aucun contournement d'UID (SPRINT/FP3) n'est donc
nécessaire ici. Sessions observées : `practice1`, `practice2`, `practice3` (seconde
journée uniquement), `qualifying`, `race` — certains rounds omettent `qualifying` ou
`practice1`/`practice2` (ex. Tokyo round 8 2025), géré nativement par la boucle générique
de `F1CalendarBaseSource._build_event()`.

### Travail effectué

**`motorsport_calendar/providers/formula_e/`** — nouveau championnat, patron F1 Academy
- `provider.py` : `FormulaEProvider(Provider)` — `name="formula-e"`, délègue entièrement
  à la source injectée, `category=ChampionshipCategory.SINGLE_SEATER`
- `source.py` : `FormulaESource(ABC)` — contrat `get_season(year) -> list[Event]`
- `sources/f1calendar.py` : `F1CalendarSource(F1CalendarBaseSource, FormulaESource)` —
  **zéro logique HTTP/cache/mapping propre**, hérite tout de `F1CalendarBaseSource`.
  Seules 4 propriétés spécifiques : `_series_key="fe"`, `_SESSION_MAP` (5 clés,
  durées 30/30/30/60/45 min), `_CIRCUIT_DATA` (16 circuits couvrant 2023-2025 :
  Sao Paulo, Mexico City, Jeddah, Diriyah, Miami, Monaco, Tokyo, Shanghai, Jakarta,
  Berlin, Londres, Misano, Rome, Portland, Hyderabad, Cape Town), `_make_championship()`
- `sources/__init__.py` : enregistrement `source_registry.register("formula-e",
  "f1calendar", ...)` — patron identique à F2/F3/F1 Academy
- `__init__.py` : `registry.register("formula-e", _make_provider)`

**`motorsport_calendar/cli.py`** — factorisation
- Nouvelle fonction `_run_generate_command()` : corps partagé pour toute commande
  `generate-*` mono-championnat (résolution source/provider, fetch, gestion
  HTTPStatusError/TimeoutException/NotImplementedError optionnel, export ICS). Les 5
  commandes existantes (`generate-f1/f2/f3/f1-academy/wec`) — copiées-collées à chaque
  nouveau championnat depuis l'origine du projet — réduites à un wrapper Typer fin
  (conserve sa propre docstring/aide `--help`) qui appelle ce helper avec ses paramètres
  propres (`championship_id`, `fetch_label`, `default_source`, `error_prefix`,
  `not_implemented_message` optionnel pour le cas WEC). **Comportement/sorties console
  strictement identiques** — vérifié par les 116 tests CLI existants, passés sans aucune
  modification après le refactor.
- `generate-formula-e YEAR OUTPUT.ics` ajoutée sur ce même helper (≈10 lignes de code
  marginal au lieu de ≈75 en copiant-collant une 6ᵉ fois).
- Bénéfice mesuré : `cli.py` 355 → 182 lignes ; dette préexistante réduite en prime
  (13 → 5 erreurs mypy, 48 → 19 lignes non couvertes par les tests — comparé via
  `git stash` avant/après, aucune nouvelle dette introduite).

**Intégration GUI — 3 lignes, zéro fichier de vue touché**
- `gui/categories.py` : `"formula-e"` ajouté au groupe `Category.FORMULA`
- `gui/display_names.py` : `"formula-e": "Formula E"`
- `gui/upcoming_weekend.py::WEEKEND_CHAMPIONSHIP_IDS` : `"formula-e"` ajouté
- Aucune ligne dans `main_view.py`/`calendar.py` — le wizard et "Ce week-end" sont
  entièrement pilotés par `registry.list_all()` → `categories.get_groups_for()` →
  `display_names.get_display_name()`, vérifié en confirmant que Formula E apparaît
  automatiquement dans le groupe "🏎 Formula" sans code de vue supplémentaire.
- `gui/championship_assets.py` (logos) et Design System **non touchés**, conformément à
  la contrainte "aucun travail sur les icônes" — `get_championship_asset("formula-e")`
  renvoie `None` gracieusement (id absent de `_LOGO_FILENAMES`), comportement déjà
  générique depuis le Sprint 33, aucun changement requis.

**Tests**
- `tests/test_formula_e_provider.py` — 13 tests (identité, `fetch_championship`,
  `fetch_events`), patron `test_f1_academy_provider.py`
- `tests/test_cli_generate_formula_e.py` — 28 tests (happy path, erreurs, contenu ICS),
  y compris un cas "second jour" réel (practice3 seul, sans practice1/practice2)
- `tests/fixtures/real/formula-e.json` — extrait réel non retouché du dataset (2 rounds :
  Sao Paulo, Mexico City), conformément à la convention établie (`test_real_fixtures.py`)
- `tests/test_real_fixtures.py` — `TestFormulaERealFixture` (5 tests), même patron que
  F2/F3/F1 Academy
- Tests existants corrigés pour isoler le nouveau provider réel (sinon appels réseau non
  mockés dans les tests déjà en place) :
  - `tests/test_cli_generate.py` : fixture autouse `_isolate_support_series` étendue à
    `FormulaECalendarSource.fetch_json` ; 2 tests "tous les providers échouent" étendus
    avec un mock d'échec explicite pour Formula E (sinon elle "réussit" silencieusement
    avec 0 événement et fait échouer l'hypothèse du test)
  - `tests/test_gui_controller.py` : `_WEEKEND_SOURCE_PATHS` étendu avec l'entrée
    `"formula-e"`, un test de résilience partielle étendu pour la mocker explicitement
  - `tests/test_gui_upcoming_weekend.py` : `test_exactly_the_five_specified_championships`
    renommé/mis à jour pour les 6 championnats désormais attendus

### Fichiers modifiés / créés

| Fichier | Action |
|---|---|
| `motorsport_calendar/providers/formula_e/__init__.py` | Créé |
| `motorsport_calendar/providers/formula_e/provider.py` | Créé |
| `motorsport_calendar/providers/formula_e/source.py` | Créé |
| `motorsport_calendar/providers/formula_e/sources/__init__.py` | Créé |
| `motorsport_calendar/providers/formula_e/sources/f1calendar.py` | Créé |
| `motorsport_calendar/cli.py` | Modifié — `_run_generate_command()` + `generate-formula-e` |
| `motorsport_calendar/gui/categories.py` | Modifié — 1 ligne |
| `motorsport_calendar/gui/display_names.py` | Modifié — 1 ligne |
| `motorsport_calendar/gui/upcoming_weekend.py` | Modifié — 1 ligne |
| `tests/test_formula_e_provider.py` | Créé — 13 tests |
| `tests/test_cli_generate_formula_e.py` | Créé — 28 tests |
| `tests/fixtures/real/formula-e.json` | Créé |
| `tests/test_real_fixtures.py` | Modifié — `TestFormulaERealFixture`, 5 tests |
| `tests/test_cli_generate.py` | Modifié — isolation Formula E dans les tests existants |
| `tests/test_gui_controller.py` | Modifié — isolation Formula E dans les tests existants |
| `tests/test_gui_upcoming_weekend.py` | Modifié — 1 test mis à jour (5 → 6 championnats) |
| `CHANGELOG.md` | Mis à jour |
| `docs/ROADMAP.md` | Mis à jour |
| `docs/AI_CONTEXT.md` | Mis à jour |
| `docs/TODO.md` | Mis à jour |
| `docs/DECISIONS.md` | ADR-025 ajouté |

`gui/theme.py`, `gui/championship_assets.py`, `gui/main_view.py`, `gui/views/calendar.py`,
`core/registry.py`, `core/source_registry.py`, `config/models.py`, navigation, Design
System : **non modifiés**.

### Tests exécutés
```
999 passed → 1045 passed — 0 failed — couverture 96 %
(+46 tests — formula_e/ à 100 %, cli.py 86 %→90 % avec 173 lignes en moins)
```

Vérification manuelle additionnelle (vrai appel réseau, pas de mock) :
`motocal generate-formula-e 2025 fe.ics` → 16 événements, 56 sessions, 56 UID uniques,
`LOCATION` correctement résolu ("Sao Paulo ePrix, Brazil"), sessions `Free Practice 3`
présentes sur les rounds de seconde journée. Script direct confirmant que Formula E
apparaît automatiquement dans le groupe "🏎 Formula" via
`registry.list_all()`/`categories.get_groups_for()`/`display_names.get_display_name()`
sans aucun code de vue supplémentaire.

### Limites
- Aucun logo Formula E (conforme à la contrainte de ce sprint — voir ADR-024/Sprint 33) ;
  `formula-e` absent de `_LOGO_FILENAMES`, à ajouter séparément si un logo est fourni.
- Tables `_CIRCUIT_DATA`/pays incomplètes au-delà des 16 circuits 2023-2025 couverts —
  même limite déjà documentée et acceptée pour F2/F3/F1 Academy (repli propre, jamais
  "Unknown", juste incomplet).
- Toujours aucun environnement graphique dans ce sandbox — vérifié par 1045 tests
  unitaires (100 % sur `formula_e/`) + appel réseau réel + script de simulation du
  regroupement wizard, pas par capture d'écran.

---

## Session 2026-07-07 — Sprint 33 : Registre des identités visuelles de championnat

### Objectif
Utiliser les logos officiels des championnats pour renforcer l'identité visuelle des
`ChampionshipCard`, via un registre central (`championship_id` → ressources visuelles),
sans jamais coder de chemin de fichier dans une vue ni de `if championnat == ...` dans le
composant. Aucune modification de l'architecture existante (providers, Design System,
navigation), aucun commit.

### Constat préalable — aucun logo officiel présent dans le projet
Avant d'écrire le registre, recherche exhaustive dans `motorsport-calendar` et dans
`BApps-Studio` (où vit le Brand Set) : **aucun fichier logo de championnat (F1, F2, F3,
F1 Academy, WEC) n'existe nulle part** — seuls les assets de la marque *Motorsport
Calendar* elle-même sont présents dans `BApps-Studio/03-Products/Motorsport-Calendar/
Branding/` (`mc-icon`, `logo-horizontal/vertical`, favicons), pas encore copiés dans
`gui/assets/logo/` (toujours au stade placeholder depuis le Sprint 26). Le dossier
`BApps-Studio/02-Brand/Logos/` est vide. La prémisse du brief ("logos déjà présents")
ne correspondait donc à rien de concret — clarifié avec l'utilisateur avant de coder :
option retenue = construire le registre "prêt à recevoir" (même patron que
`gui/assets/logo/README.md` pour le logo de l'app), aucun fichier factice n'étant traité
comme un vrai logo officiel.

### Travail effectué

**`motorsport_calendar/gui/championship_assets.py`** — nouveau module, registre central
- `ChampionshipAsset(logo_src: str | None)` — frozen, extensible (couleur/icône futurs
  ajouteraient un champ, jamais un nouveau point d'entrée)
- `get_championship_asset(championship_id: str) -> ChampionshipAsset` — point d'entrée
  unique : résout un chemin Flet-relatif (`"championships/formula1.png"`) UNIQUEMENT si
  le fichier existe réellement sur disque ; sinon `logo_src=None`, que ce soit parce que
  l'id est inconnu ou parce que le fichier n'a simplement pas encore été livré — les deux
  cas ne sont jamais distingués par l'appelant, jamais d'exception.
- `_LOGO_FILENAMES` — mapping purement descriptif id → nom de fichier attendu ; ajouter un
  logo demain = déposer le fichier au bon nom, aucune ligne de code à changer ailleurs.

**`motorsport_calendar/gui/assets/championships/`** — nouveau dossier (`.gitkeep` +
`README.md` documentant les 5 fichiers attendus et la procédure d'intégration, même
patron que `gui/assets/logo/README.md`). Aucun fichier image livré.

**`motorsport_calendar/gui/components/championship_card.py`**
- `_header_title(data)` : construit le titre — `ft.Text` seul si `get_championship_asset`
  ne renvoie aucun logo (état réel de tous les championnats aujourd'hui, donc layout
  strictement identique à avant ce sprint), sinon `ft.Row([ft.Image(...), ft.Text(...)])`
  avec le logo en `theme.IconSize.LG` (24px, déjà un token existant) aligné verticalement
  au centre avec le titre.
- Aucun `if championship_id == ...` : la seule branche est "un logo a été résolu ou non",
  jamais un championnat en particulier.
- `ft.BoxFit.CONTAIN` (pas `ft.ImageFit` — n'existe plus dans Flet 0.85.3 installé,
  détecté immédiatement par les tests).

**Tests**
- `tests/test_gui_championship_assets.py` — 11 tests : dataclass frozen, les 5 ids connus
  sans fichier livré → `None` (état réel du dépôt), id inconnu et id vide → `None` sans
  exception, résolution correcte quand un fichier est simulé (`monkeypatch` sur
  `_ASSETS_DIR` + `tmp_path`), un seul id résolu parmi plusieurs, id inconnu toujours
  `None` même si le dossier contient des fichiers.
- `tests/test_gui_components_championship_card.py` — 5 tests ajoutés (`TestChampionshipLogo`) :
  aucun logo livré → titre `ft.Text` nu inchangé, id inconnu ne casse pas le rendu, logo
  simulé → `ft.Row([Image, Text])` dans le bon ordre, taille du logo = `IconSize.LG`, le
  reste de l'en-tête (circuit/pays/sessions) inchangé par l'ajout du logo.

### Fichiers modifiés / créés

| Fichier | Action |
|---|---|
| `motorsport_calendar/gui/championship_assets.py` | Créé — registre central |
| `motorsport_calendar/gui/assets/championships/.gitkeep` | Créé |
| `motorsport_calendar/gui/assets/championships/README.md` | Créé |
| `motorsport_calendar/gui/components/championship_card.py` | Modifié — logo dans l'en-tête |
| `tests/test_gui_championship_assets.py` | Créé — 11 tests |
| `tests/test_gui_components_championship_card.py` | Modifié — 5 tests ajoutés |
| `docs/JOURNAL.md` | Mis à jour |
| `docs/AI_CONTEXT.md` | Mis à jour |
| `docs/TODO.md` | Mis à jour |
| `docs/ROADMAP.md` | Mis à jour |
| `docs/DECISIONS.md` | ADR-024 ajouté |

`providers/`, `models/`, `theme.py`, `components/layout/`, navigation, `main_view.py`,
Design System : **non modifiés**.

### Tests exécutés
```
999 passed — 0 failed — couverture 95 %
(983 → 999 : +16 tests — championship_assets.py et championship_card.py tous à 100 %)
```

Vérification manuelle additionnelle : script direct instanciant `build_championship_card`
pour tous les championship_id connus + un id inconnu (`nascar`) + une chaîne vide — aucune
exception, titre rendu en `ft.Text` nu dans tous les cas (aucun logo livré dans le vrai
dépôt), confirmant que ce sprint est visuellement invisible tant qu'aucun fichier n'est
déposé — exactement le comportement voulu.

### Limites
- Aucun logo officiel livré : la fonctionnalité est architecturalement complète mais
  invisible en pratique tant que les fichiers PNG/SVG (F1, F2, F3, F1 Academy, WEC) ne
  sont pas déposés dans `gui/assets/championships/`.
- `assets_dir=` reste commenté dans `gui/app.py` (partagé avec le logo de l'app, hors
  périmètre de ce sprint) — même une fois un fichier déposé, `ft.Image(src=...)` ne se
  résoudra visuellement qu'après ce décommentage.
- Toujours aucun environnement graphique dans ce sandbox — vérifié par 999 tests unitaires
  (100 % sur les 2 fichiers concernés) + script de smoke-test direct, pas par capture
  d'écran.

---

## Session 2026-07-07 — Sprint 32 : Normalisation des métadonnées des événements

### Objectif
Nettoyer les incohérences observées dans les cartes de championnat ("Belgian / Belgian /
🇧🇪 Belgique", "Unknown") en définissant une règle d'affichage unique, appliquée par une
logique dédiée (`EventDisplayData`), en amont du composant `ChampionshipCard` qui ne
contient toujours aucune logique métier. Comprendre et documenter pourquoi F2/F3
n'affichent pas les mêmes informations que F1. Aucun changement aux providers, au Design
System ni à la navigation.

### Investigation — pourquoi F2/F3/F1 Academy affichent moins bien que F1

Données réelles capturées en interrogeant `get_upcoming_weekend()` pour le même week-end
(Grand Prix de Belgique) :

```
formula1 | event.name='Belgian Grand Prix' | circuit.name='Spa-Francorchamps'
         | circuit.city='Spa-Francorchamps' | circuit.country='Belgium'
formula2 | event.name='Belgian'             | circuit.name='Belgian'
         | circuit.city='Spa-Francorchamps' | circuit.country='Unknown'
formula3 | event.name='Australian'          | circuit.name='Australian'
         | circuit.city='Melbourne'         | circuit.country='Australia'
```

**Conclusion : deux causes indépendantes, ni un bug du modèle `Event`/`Circuit`, ni une
perte au parsing au sens strict — une vraie différence d'API, plus un choix de mapping
propre au code partagé F2/F3/F1 Academy.**

1. **Différence réelle d'API (externe, non corrigible sans toucher aux providers)** — F1
   utilise Jolpica/Ergast, qui fournit un `raceName` complet ("Belgian Grand Prix"), un
   `circuitName` réel et distinct ("Spa-Francorchamps"), une vraie localité et un vrai
   pays. F2/F3/F1 Academy utilisent tous les trois le dataset ouvert `sportstimes/f1`
   (f1calendar.com), confirmé nettement plus pauvre : chaque entrée n'a qu'un descriptif
   de manche court (`name`: "Belgian", "Australian" — jamais "Grand Prix"), un `location`
   (qui se rapproche en réalité plus d'un nom de circuit que d'une ville — "Spa-
   Francorchamps", "Yas Marina") et un `slug`. **Il n'existe tout simplement aucun champ
   "nom de circuit" ni "pays" dédié dans ce dataset.**
2. **Un choix de mapping dans notre propre code** (`providers/support_series/
   f1calendar_base.py::_build_circuit`, code PARTAGÉ par F2/F3/F1 Academy) —
   `Circuit.name` y est rempli avec exactement le même descriptif court que `Event.name`,
   ce qui explique le doublon "Belgian / Belgian". Le champ `location` (mappé sur
   `Circuit.city`) est en réalité un bien meilleur candidat pour le nom de circuit, mais
   n'est pas utilisé à cette fin. Ceci est corrigible (côté provider — hors périmètre de
   ce sprint), ce n'est pas une limite du modèle `Event`/`Circuit` (les champs existent et
   sont suffisants ; c'est le CODE de mapping qui n'a rien de mieux à y mettre depuis ce
   dataset pauvre). Écart secondaire, indépendant : les tables statiques `_CIRCUIT_DATA`
   (pays) de F2/F3/F1 Academy sont incomplètes chacune à des degrés différents (F3 couvre
   "Australian", F2 ne couvre pas "Belgian") — un défaut de couverture/maintenance, pas
   une limite du dataset externe (le pays pourrait y être ajouté).

Conséquence pour ce sprint : la normalisation compense entièrement côté présentation
(sans toucher au provider), car les valeurs utiles (`circuit.city`) sont déjà présentes
sur le modèle — seul le CHOIX d'affichage était mauvais.

### Travail effectué

**`motorsport_calendar/gui/event_display.py`** — nouveau module, logique dédiée
- `EventDisplayData(grand_prix_name: str, circuit_name: str | None, country: str | None)`
- `normalize_event_display(championship_id, event) -> EventDisplayData` — applique les 4
  règles :
  1. **Grand Prix == Circuit → une seule ligne** : `circuit_name` devient `None` si sa
     valeur (une fois résolue) est identique (insensible à la casse) au nom de Grand Prix
     affiché.
  2. **Circuit inconnu → ligne masquée** : tente `circuit.name`, puis `circuit.city` en
     repli (c'est ce qui résout "Belgian"→"Spa-Francorchamps" pour F2/F3/F1 Academy) ;
     `None` si aucun des deux candidats n'est utilisable.
  3. **Pays inconnu → ligne masquée** : le littéral `"Unknown"` (insensible à la casse) ou
     une valeur vide donne `country=None` — jamais affiché tel quel.
  4. **Nom du Grand Prix absent → stratégie documentée** : ajoute " Grand Prix" au nom brut
     pour F1/F2/F3/F1 Academy s'il ne le contient pas déjà (jamais pour WEC, dont les noms
     — "24 Hours of Le Mans" — sont déjà complets) ; si le nom est totalement absent,
     utilise le nom de circuit disponible comme titre, sinon un repli générique
     ("Événement", `STRINGS.event_name_fallback`).
- Limite assumée et documentée : "Canada" → "Canada Grand Prix" plutôt que "Canadian
  Grand Prix" (pas de table démonyme complète — jugé hors de proportion pour ce sprint).

**`motorsport_calendar/gui/components/championship_card.py`**
- `ChampionshipCardData.circuit_name`/`.country` deviennent `str | None`
- `build_championship_card` : les lignes circuit/pays ne sont ajoutées que si non `None` —
  aucune décision, uniquement une omission conditionnelle (le composant reste sans la
  moindre logique métier, comme exigé)

**`motorsport_calendar/gui/upcoming_weekend.py`**
- `_COUNTRY_LABELS`/`country_label()` déplacés vers `event_display.py` (la décision
  "quel pays afficher" y vit désormais entièrement)
- `_build_card()` appelle `normalize_event_display(...)` puis construit
  `ChampionshipCardData` à partir du résultat — ne contient plus aucune logique de
  normalisation elle-même

**`motorsport_calendar/gui/strings.py`** — `event_name_fallback = "Événement"`

**Tests**
- `tests/test_gui_event_display.py` — 23 tests : fixtures réelles F1/F2/F3 capturées en
  direct, jamais "Unknown" (sentinelle + variantes de casse + valeur vide), jamais de
  doublon (circuit==nom brut, circuit==nom normalisé, city aussi dupliqué, casse
  différente), stratégie du nom de Grand Prix (suffixe ajouté/déjà présent/jamais
  doublé/championnat non-GP/nom absent avec et sans circuit de repli/nom blanc)
- `tests/test_gui_components_championship_card.py` — 4 tests ajoutés (`circuit_name=None`
  masqué, `country=None` masqué, les deux masqués, rendu toujours valide)
- `tests/test_gui_upcoming_weekend.py` — test existant corrigé (sa propre fixture
  reproduisait involontairement le bug F2/F3 par duplication délibérée circuit==event ;
  helper `_entry()` étendu avec `circuit_name`/`circuit_city` optionnels) + 1 test
  d'intégration bout-en-bout reproduisant exactement le cas réel F2 ; 2 tests
  `country_label` déplacés vers `test_gui_event_display.py`

### Fichiers modifiés / créés

| Fichier | Action |
|---|---|
| `motorsport_calendar/gui/event_display.py` | Créé — normalisation dédiée |
| `motorsport_calendar/gui/components/championship_card.py` | Modifié — champs optionnels |
| `motorsport_calendar/gui/upcoming_weekend.py` | Modifié — délègue à `event_display.py` |
| `motorsport_calendar/gui/strings.py` | Modifié — `event_name_fallback` |
| `tests/test_gui_event_display.py` | Créé — 23 tests |
| `tests/test_gui_components_championship_card.py` | Modifié — 4 tests ajoutés |
| `tests/test_gui_upcoming_weekend.py` | Modifié — 1 test corrigé, 1 ajouté, 2 déplacés |
| `docs/JOURNAL.md` | Mis à jour |
| `docs/AI_CONTEXT.md` | Mis à jour |
| `docs/TODO.md` | Mis à jour |
| `docs/ROADMAP.md` | Mis à jour |
| `docs/DECISIONS.md` | ADR-023 ajouté |

`providers/`, `models/`, `theme.py`, `components/layout/`, navigation, `main_view.py` :
**non modifiés**.

### Tests exécutés
```
983 passed — 0 failed — couverture 95 %
(957 → 983 : +26 tests — event_display.py, upcoming_weekend.py et championship_card.py
 tous à 100 %)
```

Vérification manuelle additionnelle (vrais appels réseau) : `get_upcoming_weekend()` pour
le week-end réel du Grand Prix de Belgique — les 3 cartes (F3, F2, F1) affichent
désormais exactement "Belgian Grand Prix / Spa-Francorchamps / [pays ou masqué]", plus
aucun doublon ni "Unknown" ; `build_main_view()` piloté de bout en bout sans erreur.

### Limites
- "Canada Grand Prix" au lieu de "Canadian Grand Prix" (pas de table démonyme par pays —
  limitation cosmétique mineure, assumée).
- La couverture des tables de pays F2/F3/F1 Academy reste incomplète en amont (provider
  non modifié) — la ligne pays disparaît proprement pour les circuits non couverts plutôt
  que d'afficher "Unknown", mais elle n'apparaîtra pas non plus tant que ces tables ne
  seront pas complétées (hors périmètre de ce sprint).
- Toujours aucun environnement graphique dans ce sandbox — vérifié par 983 tests
  unitaires (100 % sur les 3 fichiers concernés) + appels réseau réels, pas par capture
  d'écran.

---

## Session 2026-07-07 — Sprint 31 : Mise en place du Layout System

### Objectif
Construire une base UI durable : un véritable Layout System utilisé par toute
l'application, pour que toute future page (Recherche, Tableau de bord, Favoris,
Notifications, Historique, Résultats, Paramètres, Synchronisation) se construise à partir
de composants réutilisables, sans jamais recréer marges, espacements, séparateurs,
largeurs ou cartes dans la vue elle-même. Aucune nouvelle fonctionnalité — uniquement
l'architecture de présentation. Design System, couleurs, icônes, `theme.py`, providers,
modèles, logique métier, navigation, fonctionnalités : non modifiés.

### Réflexion architecture (avant le code)

**Où vit le Layout System ?** `gui/components/layout/`, un sous-paquet de la bibliothèque
de composants créée au Sprint 30 (plutôt qu'un `gui/layout/` séparé) : un composant de
mise en page EST un composant, au même titre que `ChampionshipCard` — les deux partagent
la même philosophie ("connaître uniquement son modèle/ses props, jamais la logique
métier"). `championship_card.py` reste à sa place actuelle (aucun besoin de le déplacer
dans un sous-dossier pour "faire symétrique" — ç'aurait été du remaniement inutile).

**Une responsabilité par composant, strictement :**
- `PageContainer` — largeur max, padding, alignement. Rien d'autre. En interne, délègue
  entièrement à `theme.page_shell` (aucune réimplémentation, aucun nouveau token) ; expose
  juste une API `header=`/`body=` plus déclarative que l'ancienne liste `*sections` plate.
- `PageHeader` — icône, titre, sous-titre éventuel, séparateur. Un seul composant pour
  toutes les pages qui affichent un en-tête.
- `Section` — le seul job : l'espacement entre blocs liés. Ne connaît rien aux titres.
- `SectionHeader` — un intitulé plus discret *à l'intérieur* d'une Section (pas un
  substitut de `PageHeader`, qui reste le titre de la page). Aucun consommateur actuel,
  mais nécessaire dès qu'une page (Tableau de bord, Recherche) affichera plusieurs groupes
  de cartes distincts — construit maintenant plutôt que retardé, sans quoi il aurait fallu
  re-designer `Section` plus tard pour l'accueillir.
- `CardList` — empile une liste de cartes avec un espacement vertical uniforme. Les
  séparateurs entre cartes restent un point d'extension documenté, non construit (aucun
  appelant n'en a besoin aujourd'hui).
- `EmptyState` — le seul "rien ici pour l'instant", toujours encarté (règle héritée du
  Sprint 28, désormais centralisée).
- `PageSpacing` — un espace nommé et explicite pour le cas réellement ponctuel qu'aucun des
  composants ci-dessus ne couvre déjà (ex. avant la rangée d'actions du wizard).

**Changement architectural délibéré vis-à-vis du Sprint 28** : au Sprint 28, Favoris et
Ce week-end (vide) avaient leur titre de page absorbé À L'INTÉRIEUR de la carte, pour
éviter un doublon visuel (pas d'en-tête générique séparé à l'époque). Avec le Layout
System, CHAQUE page qui affiche un en-tête utilise désormais exactement le même
`PageHeader`, **séparé** du corps — cohérent avec Mon calendrier/Préférences, et surtout
généralisable : une future page "Recherche" aura un `PageHeader` + une barre de recherche
+ un `EmptyState` en cas d'absence de résultat, sans que ce dernier n'ait à porter le titre
de la page. Conséquence visible : le titre de "Ce week-end"/"Mes favoris" apparaît
désormais AU-DESSUS de la carte plutôt que dedans. Assumé et documenté ici — l'information
affichée est strictement identique, seule la structure change.
Autre conséquence, à Préférences : les lignes de réglages retrouvent leur bordure
individuelle (perdue au Sprint 28 pour éviter un double encadrement dans LA carte unique
englobante) — cette carte englobante n'existe plus (le `PageHeader` est séparé), donc
chaque ligne peut redevenir sa propre carte via `CardList`, sans double bordure.

**Nommage PascalCase** (`PageContainer`, `PageHeader`, ...) — délibérément aligné sur
l'exemple donné dans la demande plutôt que sur la convention `snake_case` du reste du
code (`build_championship_card`, `theme.card`) : signale clairement "ceci est un
composant/widget", à la manière Flet/Flutter. Ruff (`N802`, pep8-naming) aurait sinon
signalé chaque nom — ajout d'une exception `per-file-ignores` scoping strictement le
paquet `gui/components/layout/*.py` dans `ruff.toml`, avec commentaire explicite.

### Travail effectué

**`motorsport_calendar/gui/components/layout/`** — nouveau sous-paquet, 7 fichiers
- `page_container.py` → `PageContainer(*, header=None, body=())`
- `page_header.py` → `PageHeader(title, *, icon=None, subtitle=None)`
- `section.py` → `Section(*controls, spacing=Spacing.SM)` + `SectionHeader(title, *, icon=None)`
- `card_list.py` → `CardList(cards, *, spacing=Spacing.SM)`
- `empty_state.py` → `EmptyState(title, *, message=None, icon=None)`
- `spacing.py` → `PageSpacing(size=Spacing.MD)`
- `__init__.py` — ré-exporte les 7 composants

**Les 5 vues migrées** — chacune construite exclusivement à partir du Layout System :
- `weekend.py` : les 3 états (chargement/aucune course/trouvé) deviennent
  `PageContainer(header=PageHeader(...), body=[Section(...)])`, avec `EmptyState`/`CardList`
  pour le corps selon l'état
- `favorites.py` : réduite à un seul appel `PageContainer(header=..., body=[Section(EmptyState(...))])`
- `preferences.py` : `PageContainer(header=..., body=[Section(CardList(rows))])` — les
  lignes (`_pref_row`) redeviennent des `theme.card()` individuelles
- `about.py` : `PageContainer(body=[Section(...)])`, **sans** `header=` — conserve
  délibérément le bloc de marque compact du Sprint 28 (pas de `PageHeader` générique ici)
- `calendar.py` : `PageContainer(header=PageHeader(...), body=[...])` pour l'enveloppe ;
  le bandeau d'étapes, le corps d'étape et la rangée de navigation restent des contrôles
  bruts dans `body` (flux séquentiel du wizard, pas une "Section" générique) ; les deux
  espaceurs manuels de `_step_create` deviennent `PageSpacing(...)`

**`ruff.toml`** — exception `N802` scopée à `gui/components/layout/*.py`

**Tests**
- `tests/test_gui_components_layout.py` — 51 tests : chaque composant testé isolément
  (structure, valeurs par défaut, surcharge des paramètres, cas vides/limites) + 3 tests
  d'intégration prouvant la composition exacte de la demande + 1 test verrouillant qu'aucun
  spacing utilisé n'est étranger à l'échelle `theme.Spacing`
- `tests/test_gui_views.py` — 7 tests Sprint 28 adaptés à la nouvelle structure (en-tête
  désormais séparé de la carte) via un nouvel utilitaire `_bordered_cards()` qui parcourt
  récursivement l'arbre de contrôles plutôt que de supposer une profondeur d'imbrication
  fixe ; 3 nouveaux tests verrouillant la présence du `PageHeader` séparé (weekend,
  favorites, preferences) ; 1 test inversé (`test_pref_rows_now_carry_their_own_border`,
  documentant explicitement le changement Sprint 28 → 31)

### Fichiers modifiés / créés

| Fichier | Action |
|---|---|
| `motorsport_calendar/gui/components/layout/__init__.py` | Créé |
| `motorsport_calendar/gui/components/layout/page_container.py` | Créé |
| `motorsport_calendar/gui/components/layout/page_header.py` | Créé |
| `motorsport_calendar/gui/components/layout/section.py` | Créé |
| `motorsport_calendar/gui/components/layout/card_list.py` | Créé |
| `motorsport_calendar/gui/components/layout/empty_state.py` | Créé |
| `motorsport_calendar/gui/components/layout/spacing.py` | Créé |
| `motorsport_calendar/gui/views/weekend.py` | Modifié — Layout System |
| `motorsport_calendar/gui/views/favorites.py` | Modifié — Layout System |
| `motorsport_calendar/gui/views/preferences.py` | Modifié — Layout System, bordures restaurées |
| `motorsport_calendar/gui/views/about.py` | Modifié — Layout System (sans PageHeader) |
| `motorsport_calendar/gui/views/calendar.py` | Modifié — Layout System + PageSpacing |
| `ruff.toml` | Modifié — exception N802 scopée |
| `tests/test_gui_components_layout.py` | Créé — 51 tests |
| `tests/test_gui_views.py` | Modifié — 7 tests adaptés, 4 nouveaux |
| `docs/JOURNAL.md` | Mis à jour |
| `docs/AI_CONTEXT.md` | Mis à jour |
| `docs/TODO.md` | Mis à jour |
| `docs/ROADMAP.md` | Mis à jour |
| `docs/DECISIONS.md` | ADR-022 ajouté |

`theme.py`, `main_view.py`, `controller.py`, `upcoming_weekend.py`,
`components/championship_card.py`, providers, modèles métier, navigation, couleurs,
icônes : **non modifiés**.

### Compromis / choix assumés
1. **En-tête séparé de la carte** (Favoris, Ce week-end vide) — changement visuel par
   rapport au Sprint 28, expliqué ci-dessus. Assumé pour une généralisation réelle.
2. **Préférences : bordures des lignes restaurées** — changement visuel par rapport au
   Sprint 28, pour la même raison (plus de carte englobante unique).
3. **Nommage PascalCase** — déroge à la convention `snake_case` du reste du code Python,
   accepté explicitement pour signaler "composant" et matcher l'exemple de la demande ;
   compensé par une exception `ruff.toml` scopée et documentée plutôt que des `noqa`
   dispersés.
4. **`SectionHeader` sans consommateur actuel** — construit par anticipation explicite
   (demandé nommément dans le brief), pas par déduction spéculative — seul composant du
   sprint dans ce cas.
5. **`Section`/`PageContainer` semblent redondants sur les pages à un seul bloc** —
   c'est voulu : la charge cognitive de `body=[Section(...)]` est nulle aujourd'hui, mais
   évite une deuxième passe de refactoring le jour où une page aura plusieurs sections.

### Tests exécutés
```
957 passed — 0 failed — couverture 95 %
(906 → 957 : +51 tests — les 7 fichiers du Layout System à 100 %, les 5 vues migrées à
 100 % (about.py 76 % — écart préexistant, confirmé inchangé en valeur absolue))
```

Vérification manuelle additionnelle : `get_upcoming_weekend()` + `build_weekend_view()`
exécutés avec de vraies données réseau ; `build_main_view()` piloté de bout en bout via une
fausse `Page` — les 5 destinations de navigation, le fetch de "Ce week-end" et les 4 étapes
du wizard fonctionnent identiquement à travers le nouveau Layout System.

### Limites
- Toujours aucun environnement graphique dans ce sandbox — vérifié par 957 tests unitaires
  (couverture 100 % sur tout le Layout System) + appels réseau réels + simulation complète
  du wiring, pas par capture d'écran.
- `CardList` n'implémente pas de séparateur entre cartes (option documentée, non codée —
  aucun appelant actuel n'en a besoin).
- `SectionHeader` n'a encore aucun consommateur réel dans le code — prêt pour Tableau de
  bord/Recherche, verrouillé par tests, mais non exercé par une vraie page avant leur
  arrivée.

---

## Session 2026-07-07 — Sprint 30 : Création du composant ChampionshipCard

### Objectif
Démarrer la bibliothèque de composants réutilisables de Motorsport Calendar. Premier
composant : `ChampionshipCard`, extrait de "Ce week-end" pour être réutilisable tel quel
dans toute future vue (Favoris, Recherche, Tableau de bord, Calendrier, Notifications,
Historique) sans qu'aucune vue n'ait plus jamais à reconstruire ce layout. Aucune
régression, aucune modification du Design System, de la navigation, des providers ou de la
logique métier — uniquement une extraction/réutilisation.

### Réflexion architecture (avant le code)
Le composant ne doit connaître que son propre modèle de données, jamais un objet du domaine
(`Event`/`Session`/`Championship`/`Circuit`) ni le concept de "week-end". Il fallait donc :
1. Un nouveau paquet dédié `gui/components/` (bibliothèque de composants), distinct de
   `gui/views/` (une page = un module) et de `gui/theme.py` (tokens/primitives bas niveau).
2. Un modèle de données propre au composant (`ChampionshipCardData` + `SessionRow`),
   promu depuis `upcoming_weekend.WeekendCard`/`SessionRow` qui remplissaient déjà
   exactement ce rôle mais vivaient au mauvais endroit (couplés à "Ce week-end").
3. Une zone de pied de carte (`footer: ft.Control | None`) — non implémentée (Favori,
   Notifications, Export ICS, Partage, Résultats restent hors scope), mais le point
   d'extension existe dès maintenant sans rien devoir changer à l'appel du composant le
   jour où une vue voudra l'utiliser.

### Travail effectué

**`motorsport_calendar/gui/components/__init__.py`** — nouveau paquet, docstring décrivant
la philosophie de la bibliothèque (données déjà formatées en entrée, jamais de logique
métier/provider à l'intérieur d'un composant).

**`motorsport_calendar/gui/components/championship_card.py`** — nouveau, le composant
- `SessionRow(label, day_time)` et `ChampionshipCardData(championship_id,
  championship_name, event_name, circuit_name, country, sessions)` — dataclasses frozen,
  déplacées depuis `upcoming_weekend.py` (renommage `WeekendCard` → `ChampionshipCardData`,
  car le nom n'a plus de sens hors du contexte "week-end")
- `build_championship_card(data, *, footer=None) -> ft.Control` — en-tête dans l'ordre
  exact demandé (championnat, Grand Prix, circuit, pays sur 4 lignes distinctes — plus de
  "·" combinant circuit et pays comme dans l'ancien `_championship_card` de `weekend.py`),
  puis `Divider`, puis la grille de sessions
- Alignement des sessions : chaque ligne est une `ft.Row(alignment=SPACE_BETWEEN)` — libellé
  et heure ancrés chacun à une extrémité de la ligne, un vrai alignement en colonnes qui ne
  dépend jamais de la longueur du texte du libellé (contrairement à un simple `expand=True`
  sur le libellé, qui fonctionne mais est moins explicite)
- Construit entièrement à partir des primitives existantes de `theme.py`
  (`theme.card`, `Spacing`/`FontSize`/`Colors`) — **aucun nouveau token, aucune nouvelle
  couleur, aucun changement au Design System**
- `footer` : quand `None` (partout aujourd'hui), rien n'est ajouté après la grille de
  sessions — zéro changement visuel. Quand fourni, un `Divider` puis le contrôle passé sont
  ajoutés — le composant ne sait pas ce qu'il contient (bouton favori, icônes, etc.), il ne
  fait que le positionner

**`motorsport_calendar/gui/upcoming_weekend.py`** — migré
- Suppression de `SessionRow`/`WeekendCard` (déplacées) ; importe désormais
  `ChampionshipCardData`/`SessionRow` depuis `components.championship_card`
- `WeekendResult.cards: tuple[ChampionshipCardData, ...]` (renommage de type uniquement,
  aucun changement de champ ni de comportement)
- `_build_card` construit désormais un `ChampionshipCardData`

**`motorsport_calendar/gui/views/weekend.py`** — migré
- Suppression de `_championship_card`/`_session_row` (le layout vit maintenant dans le
  composant partagé)
- `_found_state` construit une liste de `build_championship_card(card)` — la vue ne
  connaît plus aucun détail de layout de carte, exactement comme demandé
  ("La vue 'Ce week-end' devra simplement construire une liste de ChampionshipCard")

**`tests/test_gui_components_championship_card.py`** — nouveau, 23 tests
- Modèle : immutabilité (`frozen=True`), champs
- Construction : type de retour, carte bordée via `theme.card`, ordre exact de l'en-tête,
  hiérarchie visuelle (nom du championnat = texte le plus proéminent), séparateur présent
- Grille de sessions : une ligne par session, ordre préservé (le tri reste la responsabilité
  de l'appelant), alignement `SPACE_BETWEEN` vérifié quel que soit la longueur du libellé,
  0 session ne plante pas
- Footer : absent par défaut (aucune section ajoutée), présent → `Divider` + contrôle ajoutés,
  accepte n'importe quel contrôle sans l'interpréter
- Réutilisabilité : rendu paramétré sur les 5 championnats cités dans la demande (F1, F2,
  F3, WEC, F1 Academy) + un événement de forme très différente ("24 Hours of Le Mans")

**`tests/test_gui_views.py`** — mis à jour (import `ChampionshipCardData`/`SessionRow`
depuis leur nouvel emplacement) ; aucun test perdu

### Fichiers modifiés / créés

| Fichier | Action |
|---|---|
| `motorsport_calendar/gui/components/__init__.py` | Créé |
| `motorsport_calendar/gui/components/championship_card.py` | Créé — le composant |
| `motorsport_calendar/gui/upcoming_weekend.py` | Modifié — utilise le modèle partagé |
| `motorsport_calendar/gui/views/weekend.py` | Modifié — construit une liste de cartes |
| `tests/test_gui_components_championship_card.py` | Créé — 23 tests |
| `tests/test_gui_views.py` | Modifié — import mis à jour |
| `docs/JOURNAL.md` | Mis à jour |
| `docs/AI_CONTEXT.md` | Mis à jour |
| `docs/TODO.md` | Mis à jour |
| `docs/ROADMAP.md` | Mis à jour |
| `docs/DECISIONS.md` | ADR-021 ajouté |

`theme.py`, `main_view.py`, `controller.py`, navigation, couleurs, espacements, providers,
modèles métier : **non modifiés**.

### Bugs rencontrés
Aucun — migration mécanique, verrouillée par les tests existants (aucun n'a dû changer de
comportement, seulement des imports).

### Tests exécutés
```
903 passed — 0 failed — couverture 95 %
(880 → 903 : +23 tests — championship_card.py, upcoming_weekend.py et views/weekend.py
 tous à 100 %)
```

Vérification manuelle additionnelle (vrais appels réseau) : `get_upcoming_weekend()` +
`build_weekend_view()` exécutés de bout en bout avec le nouveau composant — 3 cartes
(F3/F2/F1, week-end du Grand Prix de Belgique) rendues sans erreur.

### Limites
- Toujours aucun environnement graphique dans ce sandbox — vérifié par tests unitaires
  (100 % sur les 3 fichiers concernés) + appel réseau réel, pas par capture d'écran.
- Le footer reste un point d'extension vide : aucun bouton Favori/Notifications/Export/
  Partage/Résultats n'a été implémenté (explicitement hors scope de ce sprint).
- Le composant ne gère pas lui-même le tri/regroupement (Formula avant Endurance,
  chronologique) — c'est resté la responsabilité de `upcoming_weekend.py`, conforme à
  "aucune logique métier dans la vue/le composant".

---

## Session 2026-07-07 — Sprint 29 : Ce week-end (version fonctionnelle)

### Objectif
Transformer "Ce week-end" en première fonctionnalité réellement utile : trouver
automatiquement le prochain week-end de course (vendredi 00h00 → dimanche 23h59) à partir
des 5 championnats existants (F1, F2, F3, F1 Academy, WEC), afficher une carte par
championnat avec ses sessions, triées Formula puis Endurance puis chronologiquement.
Aucune nouvelle navigation, aucun changement graphique majeur, aucun nouveau provider —
uniquement le branchement de données réelles sur l'architecture existante (`registry` +
`source_registry` + `HttpCache`, exactement comme `generate_calendar`).

### Travail effectué

**`motorsport_calendar/gui/upcoming_weekend.py`** — nouveau module, logique pure (aucun
Flet, aucune I/O)
- `WEEKEND_CHAMPIONSHIP_IDS` — liste figée `(formula1, formula2, formula3, f1-academy, wec)`,
  indépendante de l'opt-out de `config.yaml` (cette page a son propre périmètre fixe)
- `WeekendEntry(championship_id, event)` — **découverte importante** : `Event.championship.id`
  tel que construit par chaque provider est suffixé par l'année (`"formula1-2026"`,
  `"f1-academy-2026"`), jamais l'id brut du registre (`"formula1"`). Le regroupement par
  catégorie (`categories.get_groups_for`) et les noms d'affichage (`display_names.
  get_display_name`) attendent l'id brut — `WeekendEntry` transporte donc explicitement
  l'id connu par l'appelant plutôt que de le déduire (fragile) de `event.championship.id`.
  Voir ADR-020.
- `find_next_weekend_entries(entries, now, max_weeks_ahead=104)` — avance semaine par
  semaine (vendredi→dimanche, dates UTC) jusqu'à trouver une fenêtre contenant au moins une
  session, conformément à l'énoncé ("le prochain week-end contenant au moins une
  compétition") ; retourne `None` si rien dans l'horizon (~2 ans, borné par les données
  réellement récupérées)
- `find_upcoming_weekend(entries, now)` — point d'entrée : recherche + regroupement
  (`_group_entries_for_display`, réutilise `categories.get_groups_for` tel quel — Formula
  puis Endurance, ordre chronologique préservé à l'intérieur) + mise en forme (`_build_card`)
  → `WeekendResult(found, friday, sunday, cards, next_hint_date)`
- Labels français présentation-only (même philosophie que `display_names.py`) :
  `_SESSION_LABELS` (SessionType → "Essais Libres 1"/"Qualifications"/"Course"/…),
  `_COUNTRY_LABELS` (~35 pays → emoji drapeau + nom FR, fallback sur le nom brut si absent),
  `_DAY_LABELS_FR`
- Heure affichée convertie dans le fuseau IANA du circuit (`Circuit.timezone`, déjà présent
  dans le modèle mais jusqu'ici jamais exploité) — fallback UTC si le fuseau est invalide

**`motorsport_calendar/gui/controller.py`** — `get_upcoming_weekend(now=None)`
- Mirroir exact du pipeline de `generate_calendar` : mêmes `registry`/`source_registry`,
  même `HttpCache`, **aucun nouveau provider**, `refresh=False` toujours — repose sur le TTL
  du cache existant pour ne jamais retaper le réseau à chaque ouverture de la page
- Boucle sur les 5 championnats fixes × 2 années (année courante + suivante, borne le
  scan sans appel réseau supplémentaire) ; échec d'un championnat/année → ignoré, les autres
  continuent (règle 8 de PROJECT_RULES.md)
- WEC : `OfficialWecSource.get_season()` lève `NotImplementedError` en conditions réelles —
  capturé comme n'importe quel autre échec, jamais un cas spécial

**`motorsport_calendar/gui/views/weekend.py`** — réécrit, 3 états exactement
- `build_weekend_view(result: WeekendResult | None = None)` :
  `None` → chargement ("Chargement..." dans une carte) ; `result.found is False` → carte
  unique "Aucune course ce week-end." + "Prochain week-end disponible le XX/XX." (si connu) ;
  `result.found is True` → en-tête de page + sous-titre (dates du week-end) + **une carte
  par championnat**, triées Formula puis Endurance puis chronologiquement (ordre déjà
  garanti par `find_upcoming_weekend`, la vue ne trie rien elle-même)
- Suppression du skeleton statique (`_race_preview_content`) et des chaînes qui n'allaient
  qu'avec lui (`weekend_coming_soon`, `weekend_section_*`, `weekend_layout_preview`)

**`motorsport_calendar/gui/main_view.py`**
- `weekend_container` (même pattern que `calendar_container`) : construit une fois avec
  l'état "chargement", puis `_load_weekend()` (tâche asyncio démarrée une seule fois au
  lancement de l'app, référencée sur `page.weekend_load_task` pour ne pas être ramassée par
  le GC en plein vol) appelle `get_upcoming_weekend()` et remplace `.content` une fois
  résolu — jamais retapé à chaque visite de l'onglet
- Docstring module mis à jour (2e exception à "vue construite une fois, swap sans rebuild")

**`motorsport_calendar/gui/strings.py`** — `weekend_loading`, `weekend_next_hint`
(gabarit `"Prochain week-end disponible le {date}."`) ; `weekend_empty_title` conservé
(désormais avec point final, conforme à l'énoncé) ; chaînes du skeleton statique retirées

### Fichiers modifiés / créés

| Fichier | Action |
|---|---|
| `motorsport_calendar/gui/upcoming_weekend.py` | Créé — logique pure |
| `motorsport_calendar/gui/controller.py` | Modifié — `get_upcoming_weekend()` |
| `motorsport_calendar/gui/views/weekend.py` | Réécrit — 3 états réels |
| `motorsport_calendar/gui/main_view.py` | Modifié — fetch en arrière-plan, une fois |
| `motorsport_calendar/gui/strings.py` | Modifié — nouvelles chaînes, anciennes retirées |
| `tests/test_gui_upcoming_weekend.py` | Créé — 21 tests |
| `tests/test_gui_controller.py` | Modifié — 8 tests `TestGetUpcomingWeekend` |
| `tests/test_gui_views.py` | Modifié — 5 tests des 3 états de la vue |
| `docs/JOURNAL.md` | Mis à jour |
| `docs/AI_CONTEXT.md` | Mis à jour |
| `docs/TODO.md` | Mis à jour |
| `docs/ROADMAP.md` | Mis à jour |
| `docs/DECISIONS.md` | ADR-020 ajouté |

`theme.py`, `models.py` (calendrier/wizard), `categories.py`, `display_names.py`,
`preferences.py`, providers existants, navigation : **non modifiés**.

### Bugs rencontrés

1. **`Event.championship.id` suffixé par l'année** — découvert en testant le contrôleur
   avec de vraies données : le regroupement Formula/Endurance échouait silencieusement
   (tout tombait dans le groupe "Autres" de secours) parce que `get_groups_for` cherchait
   `"formula1"` mais recevait `"formula1-2026"`. Corrigé en introduisant `WeekendEntry` qui
   transporte l'id du registre explicitement au lieu de le déduire de l'événement. Voir
   ADR-020 — aucun modèle ni provider modifié, la correction reste entièrement côté GUI.
2. **Source par défaut de "formula1" = openf1, pas jolpica** — `ProvidersConfig.formula1`
   a un défaut explicite `source="openf1"` (voir `config/models.py`) alors que jolpica est
   la source enregistrée en premier. Mes premiers tests mockaient jolpica et voyaient
   fuiter de vraies données réseau parce que le contrôleur, fidèle à `generate_calendar`,
   respecte ce défaut. Corrigé en mockant `OpenF1Source.get_season` à la place.

### Tests exécutés

```
880 passed — 0 failed — couverture 95 %
(846 → 880 : +34 tests — upcoming_weekend.py 100 %, views/weekend.py 100 %)
```

Vérification manuelle additionnelle (vrais appels réseau, hors suite de tests) :
- `get_upcoming_weekend()` exécuté en conditions réelles → a trouvé le week-end du Grand
  Prix de Belgique avec 3 cartes (F3, F2, F1) correctement triées chronologiquement à
  l'intérieur du groupe Formula.
- `build_main_view()` piloté de bout en bout via une fausse `Page` : `page.weekend_load_task`
  se résout sans lever, `page.update()` est appelé exactement une fois après résolution,
  confirmant que le conteneur "Ce week-end" passe bien de l'état chargement à l'état réel.

### Limites

- Le découpage vendredi-dimanche est calculé en **UTC**, pas dans le fuseau du circuit. Un
  essai libre du vendredi matin en Asie (ex. Suzuka, UTC+9) peut techniquement tomber un
  "jeudi" UTC si l'heure locale est très matinale — cas limite documenté, non corrigé dans
  cette version (l'heure *affichée* sur chaque session est, elle, correctement convertie
  dans le fuseau du circuit ; seule la fenêtre de *recherche* reste ancrée UTC).
- Table pays → drapeau/nom FR non exhaustive (~35 pays couvrant les circuits F1/F2/F3/F1A/
  WEC courants) — un pays absent s'affiche sans drapeau, avec son nom brut (souvent
  anglais) plutôt que de faire échouer l'affichage.
- Toujours aucun environnement graphique dans ce sandbox — vérifié par tests unitaires
  (100 % sur les 2 nouveaux modules) + appels réseau réels manuels + simulation complète du
  wiring, pas par capture d'écran.
- La tâche de fond (`page.weekend_load_task`) démarre au lancement de l'app, pas à la
  première visite de l'onglet "Ce week-end" — choix délibéré pour respecter "jamais
  d'appel réseau à chaque ouverture" au sens le plus strict (une seule fois par lancement,
  pas une fois par visite), mais cela signifie qu'un utilisateur qui ne visite jamais cet
  onglet aura quand même déclenché le fetch (atténué par le cache existant : TTL 24h par
  défaut, donc sans coût réseau réel au-delà de la première fois par jour).

---

## Session 2026-07-07 — Sprint 28 : Uniformisation finale de l'interface

### Objectif
Finaliser la structure visuelle avant les futures vraies fonctionnalités. Trois retouches
ciblées, purement UX/UI, sans logique métier ni nouvelle fonctionnalité : simplifier le
wizard (le bandeau d'étapes suffit, le titre par étape est redondant), donner de la
présence visuelle aux pages "vides" (Ce week-end, Mes favoris, Préférences) via une carte
centrale, et rendre la page À propos plus compacte. Aucun changement à la navigation, aux
couleurs, au Design System, au mécanisme `theme.page_shell`, aux modèles, providers,
préférences (données) ou à l'architecture.

### Travail effectué

**1. Wizard simplifié (`motorsport_calendar/gui/views/calendar.py`)**
- Suppression de `_step_header()` et de ses appels dans les 4 fonctions `_step_*` — plus de
  titre "Étape N — ..." ni de texte d'aide sous le bandeau de pastilles.
- Chaque étape commence directement par son contenu : `_step_season` retourne juste le
  `year_dropdown`, `_step_destination` juste la `Row` fichier+bouton, etc.
- `_step_championships`/`_step_destination` simplifiées en un seul niveau (l'ancien
  wrapper `Column` qui ne contenait plus que le header + un enfant est devenu inutile).
- `motorsport_calendar/gui/strings.py` : suppression des 8 constantes orphelines
  (`wizard_title_season/championships/destination/create`, `wizard_help_*`) —
  `wizard_step_*` (labels des pastilles) conservées intactes.
- Aucun changement à `build_calendar_view` au-delà du contenu des étapes : en-tête de page
  ("Mon calendrier" + icône), bandeau de pastilles, navigation Précédent/Suivant — tous
  inchangés, comme demandé ("Wizard (hors suppression du titre)").

**2. Cartes centrales pour les pages vides (`weekend.py`, `favorites.py`, `preferences.py`)**
- Les 3 vues passent maintenant **une seule section** à `theme.page_shell(...)` : un
  `theme.card(...)` contenant tout le contenu existant (en-tête `section_title` + `Divider`
  + le contenu propre à la page), au lieu de sections multiples posées à plat sur le fond
  de la page.
- `weekend.py` : le skeleton de prévisualisation (`_race_preview_content`) perd son propre
  encadrement `theme.card(...)` — il vit maintenant à l'intérieur de la carte centrale de
  la page, un double encadrement aurait été redondant.
- `preferences.py` : `_pref_row()` perd son bordure individuelle (`border=None` désormais)
  pour la même raison — les 6 lignes sont nested dans la carte centrale unique de la page.
- Aucune fonctionnalité, aucun bouton actif, aucun texte modifié — uniquement le conteneur.

**3. À propos compactée (`about.py`)**
- Suppression du header générique `section_title(nav_about, icon=INFO)` + `Divider` — le
  bloc "Motorsport Calendar / Version Alpha" (avec le placeholder logo) sert désormais
  lui-même de titre de page, sans label "À propos" redondant au-dessus.
- Suppression des `ft.Container(height=...)` espaceurs manuels entre les blocs — l'espacement
  inter-sections uniforme de `page_shell` (`Spacing.SM`) s'en charge, présentation plus
  compacte comme demandé.
- Mêmes informations conservées : titre, version, description, développeur, lien GitHub,
  licence — rien retiré, rien de nouveau. Pas de carte (contrairement aux 3 pages du point 2
  — la demande ne le mentionnait pas pour À propos).

### Fichiers modifiés

| Fichier | Action |
|---|---|
| `motorsport_calendar/gui/views/calendar.py` | Modifié — suppression `_step_header`, simplification des 4 fonctions `_step_*` |
| `motorsport_calendar/gui/strings.py` | Modifié — 8 constantes wizard orphelines supprimées |
| `motorsport_calendar/gui/views/weekend.py` | Modifié — carte centrale unique |
| `motorsport_calendar/gui/views/favorites.py` | Modifié — carte centrale unique |
| `motorsport_calendar/gui/views/preferences.py` | Modifié — carte centrale unique, lignes sans bordure propre |
| `motorsport_calendar/gui/views/about.py` | Modifié — présentation compactée, header générique retiré |
| `tests/test_gui_views.py` | Modifié — 9 tests (carte centrale ×3, absence de carte À propos, titre unique, step body sans en-tête) |
| `tests/test_gui_strings.py` | Modifié — 2 tests (labels pastilles conservés, strings orphelines absentes) |
| `docs/JOURNAL.md` | Mis à jour |
| `docs/AI_CONTEXT.md` | Mis à jour |
| `docs/TODO.md` | Mis à jour |

`theme.py`, `main_view.py`, `models.py`, `controller.py`, `categories.py`,
`display_names.py`, `preferences.py` (persistance) **non modifiés**. `docs/ROADMAP.md`
**non modifié** (explicitement demandé).

### Bugs rencontrés
Aucun.

### Tests exécutés
```
846 passed — 0 failed — couverture 94 %
(837 → 846 : +9 tests)
```

Vérification manuelle additionnelle (toujours aucun environnement graphique disponible) :
- Script pilotant `build_main_view()` de bout en bout confirme que le wizard, après
  simplification, conserve exactement le même comportement de gating (Suivant désactivé/
  activé en direct selon la sélection, retour arrière fonctionnel).
- Script appelant directement les 4 `build_*_view()` restants confirme que Ce week-end,
  Mes favoris et Préférences n'exposent plus qu'**une seule section** (la carte centrale,
  bordure confirmée) tandis qu'À propos n'a **aucune** section bordée parmi ses 5 sections.

### Limites
- Toujours aucune capture d'écran réelle possible dans ce sandbox (pas de serveur
  d'affichage). Vérifié uniquement par tests unitaires + inspection structurelle du wiring
  réel — recommandé de confirmer visuellement sur un poste avec affichage.
- Nested cards (Préférences) : la carte centrale contient les 6 lignes de réglages ; ces
  lignes n'ont plus leur propre bordure (pour éviter un double encadrement), mais gardent
  leur espacement (`spacing=XS`) — pas de séparateur visuel entre elles. À ajuster si le
  rendu final paraît trop dense.
- Interprétation retenue pour "carte centrale" : une carte qui remplit la largeur du
  gabarit partagé (comme toutes les autres cartes de l'app depuis le Sprint 27), pas une
  carte volontairement plus étroite et centrée dans l'espace restant — cohérent avec la
  règle d'uniformisation des largeurs de cartes déjà en place, mais à confirmer si
  l'intention était une carte visuellement plus petite/isolée.

---

## Session 2026-07-07 — Sprint 27 : Uniformisation du layout (UX)

### Objectif
Corriger une incohérence visuelle identifiée après validation du Design System (Sprint 26) :
Ce week-end / Mes favoris / À propos rendaient leur contenu entièrement centré au milieu de
l'écran, tandis que Mon calendrier et Préférences étaient alignés à gauche — donnant
l'impression de plusieurs applications cohabitant dans la même fenêtre. Objectif unique :
une seule grille de page, partagée par les 5 vues, avec un conteneur principal centré
(largeur max 900–1100 px) et un contenu systématiquement aligné à gauche à l'intérieur.
Aucune fonctionnalité, logique métier, provider, modèle, préférence, navigation ou logique
de wizard modifiée — changement strictement visuel.

### Travail effectué

**`motorsport_calendar/gui/theme.py`**
- `MAX_CONTENT_WIDTH = 1000` — constante unique (dans la fourchette 900–1100 px demandée)
- `page_shell(*sections)` — nouvelle fonction, LE gabarit partagé : un `Container` externe
  `expand=True` avec `alignment=TOP_CENTER` (centre uniquement le conteneur, jamais son
  contenu) et le `padding` standard ; à l'intérieur, un `Container` à largeur fixe
  (`width=MAX_CONTENT_WIDTH`) qui se réduit naturellement sur une fenêtre plus étroite
  (comportement standard de contrainte Flutter — un enfant à largeur fixe est bridé par les
  contraintes du parent, jamais en dépassement) ; à l'intérieur, une `Column` unique
  `horizontal_alignment=STRETCH` qui fait remplir la largeur du conteneur à toute carte/
  formulaire sans jamais les centrer — la fonction ne fait que positionner le bloc principal,
  jamais son contenu.
- Toutes les vues appellent désormais `theme.page_shell(...)` en lieu et place de leur
  propre `Container(padding=..., alignment=...)` ad hoc.

**`motorsport_calendar/gui/views/weekend.py`, `favorites.py`, `preferences.py`, `about.py`,
`calendar.py`** — migrés vers `theme.page_shell(...)`
- Weekend/Favoris/À propos : suppression de tout `alignment=ft.Alignment.TOP_CENTER`,
  `horizontal_alignment=ft.CrossAxisAlignment.CENTER` et `text_align=ft.TextAlign.CENTER` —
  le contenu (icône, titres, description, carte placeholder) est désormais empilé et aligné
  à gauche, comme Mon calendrier/Préférences l'étaient déjà.
- Les 5 pages utilisent maintenant un **en-tête identique** : `theme.section_title(label,
  icon=...)` suivi d'un `ft.Divider(height=Spacing.MD)` — y compris Mon calendrier, dont
  l'en-tête custom (logo + "Motorsport Calendar") est remplacé par
  `section_title(STRINGS.nav_my_calendar, icon=CALENDAR_MONTH)`, cohérent avec les autres
  pages qui affichent leur propre nom de section (pas le nom de l'app). Le placeholder logo
  (Sprint 26) reste en place sur la page À propos, son unique emplacement désormais.
- Carte placeholder "Ce week-end" : suppression de la largeur fixe (`width=320`) — elle
  remplit maintenant la largeur du gabarit comme toutes les autres cartes (Préférences,
  récapitulatif du wizard), via le même mécanisme `STRETCH`.
- Espacement inter-sections unifié : `Spacing.SM` partout (porté par `page_shell`), plus
  besoin de le redéfinir par vue.

**`tests/test_gui_theme.py`**
- `TestPageShell` — 8 tests : type de retour, `expand`, centrage de l'unique conteneur,
  largeur plafonnée à `MAX_CONTENT_WIDTH`, valeur dans la fourchette 900–1100, alignement
  `STRETCH` (jamais centré), ordre des sections préservé, padding = `page_padding()`.

**`tests/test_gui_views.py`**
- Un test `test_uses_shared_page_shell` ajouté à chacune des 5 classes de vue.
- `TestAllViewsShareTheSameGrid` — 5 tests transversaux qui construisent les 5 vues et
  vérifient qu'elles partagent *exactement* la même largeur max, le même centrage externe,
  le même alignement de contenu (`STRETCH`) et le même padding — verrou anti-régression
  direct sur l'exigence "même gabarit partout".

### Fichiers modifiés

| Fichier | Action |
|---|---|
| `motorsport_calendar/gui/theme.py` | Modifié — `MAX_CONTENT_WIDTH`, `page_shell()` |
| `motorsport_calendar/gui/views/weekend.py` | Modifié — gabarit partagé, contenu aligné à gauche |
| `motorsport_calendar/gui/views/favorites.py` | Modifié — gabarit partagé, contenu aligné à gauche |
| `motorsport_calendar/gui/views/preferences.py` | Modifié — gabarit partagé |
| `motorsport_calendar/gui/views/about.py` | Modifié — gabarit partagé, contenu aligné à gauche, en-tête uniformisé |
| `motorsport_calendar/gui/views/calendar.py` | Modifié — gabarit partagé, en-tête uniformisé (section_title au lieu du logo custom) |
| `tests/test_gui_theme.py` | Modifié — 8 tests `TestPageShell` |
| `tests/test_gui_views.py` | Modifié — 5 tests unitaires + `TestAllViewsShareTheSameGrid` (5 tests) |
| `docs/JOURNAL.md` | Mis à jour |
| `docs/AI_CONTEXT.md` | Mis à jour |
| `docs/TODO.md` | Mis à jour |
| `docs/ROADMAP.md` | Mis à jour |
| `docs/DECISIONS.md` | ADR-019 ajouté |

`main_view.py` et `models.py` **non modifiés** — la logique du wizard (état, gating,
navigation entre étapes) est restée intacte ; seule la fonction de rendu `build_calendar_view`
change de conteneur racine.

### Bugs rencontrés
Aucun. Point de vigilance documenté en Limites : le mécanisme de largeur maximale responsive
repose sur le comportement standard des contraintes Flutter (`BoxConstraints.enforce`) plutôt
que sur un recalcul manuel au resize — vérifié structurellement (tests + simulation), pas
visuellement (voir Limites).

### Tests exécutés
```
837 passed — 0 failed — couverture 94 %
(819 → 837 : +18 tests — 100 % sur theme.py, calendar.py, weekend.py, favorites.py,
 preferences.py, about.py)
```

Vérification manuelle additionnelle (toujours aucun environnement graphique disponible) :
script pilotant `build_main_view()` de bout en bout — confirme que la page "Mon calendrier"
produite par le wiring réel (pas seulement `build_calendar_view()` isolé) utilise bien
`page_shell` avec `width=1000`, `alignment=TOP_CENTER`, `horizontal_alignment=STRETCH`,
identique aux 4 autres vues.

### Limites
- Toujours pas de capture d'écran réelle possible (pas de serveur d'affichage dans ce
  sandbox). Le mécanisme de largeur max responsive (`ft.Container(width=1000)` sous un
  parent `alignment=TOP_CENTER`) repose sur le comportement documenté des contraintes
  Flutter — pas de recalcul dynamique au resize (`page.on_resize`) : ce n'était pas
  nécessaire pour obtenir le comportement demandé (rétrécit sur fenêtre étroite, plafonne
  à 1000 px sur fenêtre large), mais une vérification visuelle réelle reste recommandée
  avant merge, en particulier en redimensionnant la fenêtre au-delà de 1000 px.
- Interprétation retenue : "aucun changement... aucun wizard" (contraintes du sprint) lu
  comme "ne pas changer la logique/l'état du wizard" et non "ne pas toucher au rendu visuel
  de la page Mon calendrier" — celle-ci était explicitement listée dans "Pages concernées".
  `GenerateState`, `CalendarViewControls` et tous les handlers de `main_view.py` sont
  inchangés ; seul l'habillage visuel de `build_calendar_view` a changé.
- L'en-tête de Mon calendrier a perdu le placeholder logo qu'il affichait depuis le
  Sprint 26, au profit du même `section_title` que les autres pages — jugé nécessaire pour
  une uniformité réelle des titres (l'un des points explicitement demandés). Le placeholder
  logo reste présent sur la page À propos.

---

## Session 2026-07-07 — Sprint 26 : Release Alpha Phase 2 — UX & Design System

### Objectif
Transformer l'app desktop en logiciel utilisable par un utilisateur non développeur,
sans ajouter de fonctionnalité métier : design system centralisé, assistant guidé pour
"Mon calendrier", homogénéisation visuelle, emplacement prêt pour le futur logo. Aucun
changement au moteur (providers, export ICS, modèles métier) ni aux pages Ce week-end /
Mes favoris / Préférences au-delà du reskin visuel commun.

### Travail effectué

**`motorsport_calendar/gui/theme.py`** — nouveau module, design system
- `BAppsColors` (palette écosystème, source `BApps-Studio/02-Brand/BrandGuide.md`) et
  `MotorsportColors` (palette produit v1.0, source `BApps-Studio/03-Products/
  Motorsport-Calendar/Branding/Branding.md`)
- `Colors` — rôles sémantiques (PRIMARY, SURFACE, BORDER, TEXT_*, CTA, SUCCESS, ERROR…)
  consommés par les vues ; seule couche autorisée à référencer les palettes brutes
- `Spacing` (échelle 4px), `Radius`, `IconSize`, `FontSize` — échelles centralisées
- `page_padding()`, `section_title()` — layout de page standard
- `button_style(variant)` — "primary" / "cta" / "ghost"
- `card()`, `chip()` — composants réutilisables (cartes bordées, badges "prochainement")
- `logo_placeholder(kind, size)` — emplacement réservé au futur logo (voir plus bas)
- 100 % de couverture, 34 tests (`tests/test_gui_theme.py`)

**`motorsport_calendar/gui/assets/logo/README.md`** — nouveau
- Emplacement prévu pour les assets définitifs du Brand Set v1.0 (non livrés ce sprint —
  contrainte explicite : le logo ne bloque pas le développement)
- Documente les fichiers attendus (`mc-icon.svg`, `logo-horizontal.svg`, favicons, `.ico`)
  et les 3 étapes d'intégration future (copier les fichiers, décommenter `assets_dir` dans
  `app.py`, remplacer `theme.logo_placeholder(...)` par `ft.Image(...)`)

**`motorsport_calendar/gui/views/calendar.py`** — refonte complète en assistant 4 étapes
- `CalendarViewControls` étendue : `current_step`, `on_step_click`, `back_btn`, `next_btn`,
  `recap_controls` (en plus des contrôles existants)
- Étape 1 Saison → Étape 2 Championnats → Étape 3 Destination → Étape 4 Créer
- `_step_indicator()` — 4 puces cliquables (retour uniquement vers une étape déjà visitée ;
  la progression en avant passe obligatoirement par "Suivant", qui valide l'étape courante)
- Un seul step est rendu à la fois ; `back_btn`/`next_btn` sont les mêmes instances
  d'une étape à l'autre — seule leur visibilité change (layout pur, aucune mutation d'état)
- Toujours strictement layout : aucune logique/état, conforme à la règle existante du module

**`motorsport_calendar/gui/models.py`** — `GenerateState`
- Ajout `current_step: int = 0`, `STEP_COUNT = 4`
- `step_valid(step)` — règle de validité par étape (saison toujours valide ; championnats
  ⇔ sélection non vide ; destination ⇔ chemin renseigné ; créer ⇔ `is_ready()`)
- `can_advance()` / `can_go_back()` — dérivés purs, testables sans Flet

**`motorsport_calendar/gui/main_view.py`**
- État/handlers du wizard : `on_wizard_next`, `on_wizard_back`, `on_step_click`,
  `_refresh_calendar_view()` (reconstruit `calendar_container.content` à chaque
  changement d'étape — seule exception à la règle "vue construite une fois, swap sans
  rebuild", nécessaire car chaque étape affiche des contrôles différents)
- `_build_recap_controls()` — récapitulatif étape 4 avec lien "Modifier" par ligne
  (saison / championnats / destination), renvoie directement à l'étape concernée
- Remplacement de toutes les couleurs codées en dur (`ft.Colors.GREEN_700`, `WHITE60`…)
  par les tokens `theme.*` — nav rail, dialogue de succès, bouton "Créer"
- Correction incidente : `ft.Colors.WHITE12/30/38/54/60/70` (dépréciés dans Flet 0.85)
  → `WHITE_12/30/38/54/60/70` — corrigé une seule fois dans `theme.py`, plus de warning

**`motorsport_calendar/gui/views/weekend.py`, `favorites.py`, `preferences.py`, `about.py`**
- Reskin visuel uniquement via les tokens `theme.*` (couleurs, spacing, radius, cartes,
  chip) — **aucun changement de contenu, de texte ou de comportement** sur ces 3 pages
  explicitement hors scope (Ce week-end, Mes favoris, Préférences)
- `about.py` : ajout de `theme.logo_placeholder("icon")` à la place de l'icône générique
  Flet en en-tête — c'est le seul autre emplacement de logo préparé ce sprint (avec le
  wizard "Mon calendrier")
- Padding de page harmonisé : `theme.page_padding()` partout (vertical 24 / horizontal 32)

**`motorsport_calendar/gui/strings.py`**
- 23 nouvelles chaînes `wizard_*` (titres d'étape, aides, boutons Suivant/Précédent/
  Modifier, libellés du récapitulatif) — toujours centralisées, comme le reste de l'UI

### Fichiers modifiés / créés

| Fichier | Action |
|---|---|
| `motorsport_calendar/gui/theme.py` | Créé — design system |
| `motorsport_calendar/gui/assets/logo/README.md` | Créé — emplacement logo futur |
| `motorsport_calendar/gui/views/calendar.py` | Réécrit — assistant 4 étapes |
| `motorsport_calendar/gui/models.py` | Modifié — `current_step`, `step_valid`, `can_advance`, `can_go_back` |
| `motorsport_calendar/gui/main_view.py` | Modifié — wiring wizard + theme partout |
| `motorsport_calendar/gui/views/weekend.py` | Modifié — reskin theme uniquement |
| `motorsport_calendar/gui/views/favorites.py` | Modifié — reskin theme uniquement |
| `motorsport_calendar/gui/views/preferences.py` | Modifié — reskin theme uniquement |
| `motorsport_calendar/gui/views/about.py` | Modifié — reskin theme + logo placeholder |
| `motorsport_calendar/gui/strings.py` | Modifié — 23 chaînes wizard |
| `tests/test_gui_theme.py` | Créé — 34 tests |
| `tests/test_gui_models.py` | Modifié — 15 tests wizard state |
| `tests/test_gui_views.py` | Modifié — tests CalendarView adaptés au wizard (dataclass, gating nav, indicateur d'étapes) |
| `docs/JOURNAL.md` | Mis à jour |
| `docs/AI_CONTEXT.md` | Mis à jour |
| `docs/TODO.md` | Mis à jour |
| `docs/ROADMAP.md` | Mis à jour |
| `docs/DECISIONS.md` | ADR-018 ajouté |

### Bugs rencontrés

1. **Couleurs `ft.Colors.WHITE12/30/38/54/60/70` dépréciées** (Flet 0.85.3, code écrit
   contre `flet>=0.80`) — chaque usage émettait un `DeprecationWarning` à la construction.
   Corrigé une seule fois en dur dans `theme.Colors` (`WHITE_12` etc.) — bénéfice direct
   de la centralisation : plus aucun warning dans la suite de tests.
2. Aucun bug fonctionnel rencontré dans la logique du wizard — vérifié par simulation
   manuelle du parcours complet (voir Tests).

### Tests exécutés

```
819 passed — 0 failed — couverture 94 %
(764 → 819 : +55 tests — theme.py 100 %, calendar.py 100 %, models.py 100 %)
```

Vérification manuelle additionnelle (aucun environnement graphique disponible dans ce
sandbox pour lancer l'app desktop réelle) : script ad-hoc pilotant `build_main_view()`
avec une fausse `Page` pour simuler un parcours complet — sélection saison → coche/décoche
championnat (vérifie le blocage/déblocage en direct de "Suivant") → étape destination
(bloquée sans chemin) → retour arrière (l'état des étapes précédentes est préservé).
Tous les points de blocage se comportent comme attendu.

### Limites (voir aussi section dédiée du rapport)

- Pas de capture d'écran réelle possible : environnement sans serveur d'affichage
  (`flet build` / rendu Flutter nécessitent un display). Vérifié à la place par tests
  unitaires (100 % sur les 3 nouveaux modules) + simulation de parcours complet.
- Interprétation retenue pour "aucun changement" sur Ce week-end / Mes favoris /
  Préférences : appliquée au **contenu et au comportement**, pas au style visuel — sinon
  la tâche 3 (uniformisation) ne pourrait pas s'appliquer à ces pages. À confirmer avec
  le product owner si ce n'est pas l'intention.
- Dette mypy préexistante sur `main_view.py` (signatures `on_click` Flet 0.80 vs 0.85.3
  installé) : 21 erreurs sur `master` avant ce sprint, 26 après (+5 proportionnelles aux
  nouveaux handlers du wizard, même pattern que le code existant) — non corrigée, hors
  scope (nécessiterait un audit des stubs Flet sur tout le fichier).
- Logo définitif toujours non intégré (conforme à la contrainte) — emplacement prêt,
  voir `gui/assets/logo/README.md`.

---

## Session 2026-07-06 — Release Alpha : Branding v1.0

### Objectif
Produire les assets graphiques officiels du produit à partir du Brand Set validé (`BApps-Studio/03-Products/Motorsport-Calendar/Branding/Brand-Set-v1.0.png.png`) : logos, icône, favicons, `.ico`, visuels GitHub. Aucun redesign — déclinaison du Brand Set existant.

### Travail effectué

**Sources vectorielles** (recréation fidèle du Brand Set — palette, typographie et composition respectées ; pas un export direct du moodboard)
- `mc-icon.svg` — monogramme MC, dégradé BApps Blue → BApps Cyan, accent damier
- `logo-horizontal.svg` — monogramme + wordmark "Motorsport Calendar" (Variante A, texte blanc) + tagline "by BApps"
- `logo-vertical.svg` — monogramme centré au-dessus du wordmark, "Calendar" en dégradé

**Rendu** via un environnement de rendu isolé (Node + sharp/librsvg, polices Space Grotesk + Arial en substitut d'Inter — non commité, outillage local uniquement) :
- `mc-icon.png`, `logo-horizontal.png`, `logo-vertical.png` (fond transparent)
- `favicon-32.png`, `favicon-16.png`
- `icon.ico` — multi-résolution 16/24/32/48/64/128/256, tuile arrondie sur fond sombre
- `Cover-GitHub.png` (1200×630), `Banner.png` (1920×400)
- `Branding.md` — palette, typographie, principes d'usage, liste des livrables

**Diffusion**
- Livrables déposés dans `assets/branding/` (ce dépôt) et dans `BApps-Studio/03-Products/Motorsport-Calendar/Branding/` (référentiel central du studio)
- `motorsport_calendar/gui/assets/icon.png` peuplé (placeholder déjà prévu dans `app.py`, code non modifié — l'activation de `assets_dir`/`window.icon` reste à décider)
- `README.md` : ajout de la bannière en en-tête

### Fichiers modifiés / créés

| Fichier | Action |
|---|---|
| `assets/branding/*` | Créé — 12 fichiers (sources SVG + rendus + Branding.md) |
| `motorsport_calendar/gui/assets/icon.png` | Créé |
| `README.md` | Modifié — bannière en en-tête |
| `docs/JOURNAL.md` | Mis à jour |

### Tests exécutés
Non applicable — tâche de production d'assets graphiques, aucun code exécutable modifié.

### Bugs rencontrés
- La police variable Space Grotesk rendait en serif de repli avec `font-weight: 700` (Bold) via librsvg/Pango, mais correctement en sans-serif avec `font-weight: 600` — utilisé 600 (SemiBold), qui correspond de toute façon à la graisse spécifiée par la charte pour les titres.
- Les URLs `static/Inter-*.ttf` du dépôt `google/fonts` renvoyaient une page HTML 404 au lieu du fichier : substitution par Arial pour les textes secondaires en attendant une source Inter valide.

---

## Session 2026-07-05 — Sprint 12 : CLI generate (agrégateur multi-provider)

### Objectif
Ajouter la commande `motocal generate YEAR OUTPUT.ics` qui itère tous les providers activés, fusionne les événements en un seul ICS, et résiste à l'échec partiel.

### Travail effectué

**`docs/PROJECT_RULES.md`**
- Ajout règle 8 : résilience des commandes CLI agrégées — un provider qui échoue ne stoppe pas les autres.

**`motorsport_calendar/cli.py`** — nouvelle commande `generate`
- Lit `config.yaml` via `ConfigService`
- `registry.discover()` + `source_registry.discover()` — découverte automatique
- `registry.enabled(config.providers)` — liste des IDs activés (opt-out)
- Pour chaque provider : `source_registry.get(cid, source_name)(cache, refresh)` + `registry.get(cid)(source)`
- Fetch asynchrone groupé dans un seul `asyncio.run(_fetch_all())` — isolation d'erreur par provider
- Exceptions capturées individuellement : `NotImplementedError`, `httpx.HTTPStatusError`, `httpx.TimeoutException`, `Exception`
- Résumé `✓ provider : N événements` / `✗ provider : raison` affiché après fetch
- Tri chronologique par `min(s.start_datetime for s in e.sessions)` — events sans sessions triés en dernier
- Exit 0 si au moins un provider réussit, exit 1 si tous échouent
- Fallback source : `source_registry.list_for(cid)[0]` si `ProviderConfig.source == ""`

**`tests/test_cli_generate.py`** — 17 tests
- Happy path (9) : F1 seul exit 0, F1 seul crée fichier, F1 seul 3 VEVENTs, les deux exit 0, les deux 6 VEVENTs, VCALENDAR, ✓ dans output, ✗ dans output, saison vide exit 0
- Error path (5) : tous échouent exit 1, tous échouent pas de fichier, F1 HTTP 503 + WEC exit 0, F1 timeout + WEC exit 0, provider survivant exporté
- Refresh (2) : flag exit 0, flag crée fichier
- Tri (1) : WEC janvier avant F1 mars dans l'ICS

### Fichiers modifiés / créés

| Fichier | Action |
|---|---|
| `docs/PROJECT_RULES.md` | Modifié — règle 8 résilience |
| `motorsport_calendar/cli.py` | Modifié — ajout commande generate |
| `tests/test_cli_generate.py` | Créé — 17 tests |
| `docs/TODO.md` | Mis à jour |
| `docs/AI_CONTEXT.md` | Mis à jour |

### Tests exécutés
```
306 passed — 0 failed — couverture 92 %
```

---

## Session 2026-07-05 — Sprint 11 : CLI generate-wec

### Objectif
Ajouter la commande `motocal generate-wec YEAR OUTPUT.ics`, symétrique à `generate-f1`.

### Travail effectué

**`motorsport_calendar/cli.py`**
- Nouvelle commande `generate-wec` : même orchestration que `generate-f1`
- `source_registry.get("wec", source_name)` + `registry.get("wec")(source)`
- Gestion spécifique `NotImplementedError` : message clair "source non encore implémentée" → exit 1
- Flags : `YEAR`, `OUTPUT`, `--refresh`

**`tests/test_cli_generate_wec.py`** — 16 tests
- Happy path : exit 0, fichier créé, VCALENDAR, 3 VEVENTs (2 events, sessions mixtes), locations, saison vide
- Appel unique à `get_season` (vs 2 appels `_get_json` pour F1)
- Transmission du `year` correct au source
- Error path : `NotImplementedError` (stub réel — aucun mock), HTTP 503/404, timeout
- Flag `--refresh` : exit 0, fichier créé

### Fichiers modifiés / créés

| Fichier | Action |
|---|---|
| `motorsport_calendar/cli.py` | Modifié — ajout generate-wec |
| `tests/test_cli_generate_wec.py` | Créé — 16 tests |
| `docs/TODO.md` | Mis à jour |

### Bugs rencontrés
- `Circuit` a des champs requis supplémentaires (`id`, `city`, `timezone`) non documentés dans le résumé de session — corrigé dans les données de test.

### Tests exécutés
```
289 passed — 0 failed — couverture 92 %
```

---

## Session 2026-07-05 — Sprint 10 : Source Registry

### Objectif
Inverser la responsabilité de la sélection de source. Le provider ne connaît plus ses sources. Le `SourceRegistry` gère la correspondance `(championnat, nom_source) → factory`.

### Travail effectué

**`motorsport_calendar/core/source_registry.py`** — nouveau fichier
- `SourceRegistry` : `register()`, `get()`, `list_for()`, `list_all()`, `discover()`
- Clé composite `(championship_id, source_name)`
- `discover()` : importe `providers/X/sources/__init__.py` de chaque provider
- `source_registry` singleton
- Couverture 93 %

**`motorsport_calendar/providers/formula1/sources/__init__.py`**
- Ajout `source_registry.register("formula1", "openf1", lambda cache, refresh: OpenF1Source(...))`
- Les stubs (Ergast, Official, Cached) ne sont pas encore enregistrés

**`motorsport_calendar/providers/wec/sources/__init__.py`**
- Ajout `source_registry.register("wec", "official", lambda cache, refresh: OfficialWecSource())`

**`motorsport_calendar/providers/formula1/__init__.py`**
- Factory simplifiée : `_make_provider(source) → Formula1Provider(source)`
- Plus aucune référence à OpenF1Source, Ergast, etc.

**`motorsport_calendar/providers/wec/__init__.py`**
- Factory simplifiée : `_make_provider(source) → WecProvider(source)`

**`motorsport_calendar/cli.py`**
- `generate-f1` orchestre : `source_registry.get("formula1", source_name)(cache, refresh)` puis `registry.get("formula1")(source)`

### Fichiers modifiés / créés

| Fichier | Action |
|---|---|
| `motorsport_calendar/core/source_registry.py` | Créé |
| `motorsport_calendar/core/__init__.py` | Modifié — export SourceRegistry + source_registry |
| `motorsport_calendar/providers/formula1/__init__.py` | Modifié — factory simplifiée |
| `motorsport_calendar/providers/wec/__init__.py` | Modifié — factory simplifiée |
| `motorsport_calendar/providers/formula1/sources/__init__.py` | Modifié — enregistrement openf1 |
| `motorsport_calendar/providers/wec/sources/__init__.py` | Modifié — enregistrement official |
| `motorsport_calendar/cli.py` | Modifié — orchestration via source_registry |
| `tests/test_source_registry.py` | Créé — 24 tests |
| `tests/test_registry.py` | Modifié — factories mises à jour |
| `docs/DECISIONS.md` | ADR-012 ajouté |

### Bugs rencontrés
Aucun.

### Tests exécutés
```
273 passed — 0 failed — couverture 93 %
```

---

## Session 2026-07-05 — Sprint 9 : Provider Registry

### Objectif
Créer un `ProviderRegistry` central. Chaque provider s'enregistre automatiquement à l'import de son `__init__.py`. La CLI ne connaît plus aucun provider individuellement.

### Travail effectué

**`motorsport_calendar/core/registry.py`** — nouveau fichier
- `ProviderRegistry` : `register()`, `get()`, `list_all()`, `enabled()`, `discover()`
- `registry` singleton partagé par toute l'application
- `discover()` : `pkgutil.iter_modules` sur `providers/` → importe chaque sous-paquet
- `enabled(providers_config)` : logique opt-out (absent de la config = activé)
- Couverture 100 %

**`motorsport_calendar/config/models.py`**
- `ProviderConfig` : ajout `enabled: bool = True` et `source: str = ""` (source optionnelle)
- `ProvidersConfig` : ajout `extra="allow"` (Pydantic stocke les providers YAML hors nommés) + méthode `get(championship_id)` (cherche champs nommés puis extras)

**`motorsport_calendar/providers/formula1/__init__.py`**
- Ajout import `registry` + factory `_make_provider(cfg, cache, refresh)` → `Formula1Provider(OpenF1Source(...))`
- `registry.register("formula1", _make_provider)` à l'import

**`motorsport_calendar/providers/wec/__init__.py`**
- Ajout import `registry` + factory `_make_provider(cfg, cache, refresh)` → `WecProvider(OfficialWecSource())`
- `registry.register("wec", _make_provider)` à l'import

**`motorsport_calendar/cli.py`**
- `generate-f1` : remplace la logique `if source == "openf1"` par `registry.discover()` + `registry.get("formula1")`
- `providers` : mise à jour — affiche la liste depuis `registry.list_all()`

### Fichiers modifiés / créés

| Fichier | Action |
|---|---|
| `motorsport_calendar/core/registry.py` | Créé |
| `motorsport_calendar/core/__init__.py` | Modifié — export ProviderRegistry + registry |
| `motorsport_calendar/config/models.py` | Modifié — enabled + source optionnels + get() |
| `motorsport_calendar/providers/formula1/__init__.py` | Modifié — auto-enregistrement |
| `motorsport_calendar/providers/wec/__init__.py` | Modifié — auto-enregistrement |
| `motorsport_calendar/cli.py` | Modifié — registry-driven, providers cmd fonctionnelle |
| `config.example.yaml` | Modifié — champ enabled documenté |
| `tests/test_registry.py` | Créé — 25 tests |
| `tests/test_config_service.py` | Modifié — 7 tests ajoutés (enabled, get) |
| `docs/DECISIONS.md` | ADR-011 ajouté |

### Bugs rencontrés
Aucun.

### Tests exécutés
```
250 passed — 0 failed — couverture 93 %
```

---

## Session 2026-07-05 — Sprint 8 : Configuration centralisée

### Objectif
Supprimer tous les paramètres codés en dur. Créer un `ConfigService` qui lit `config.yaml` et alimente le cache, les providers et l'exporteur ICS.

### Travail effectué

**Module `motorsport_calendar/config/`**
- `AppConfig`, `CacheConfig`, `IcsConfig`, `ProviderConfig`, `ProvidersConfig` — tous Pydantic v2 `frozen=True`
- `ConfigService` : cherche `config.yaml` (CWD → `~/.config/…`) puis utilise les défauts
- Dépendance `pyyaml>=6.0` ajoutée à `pyproject.toml`

**IcsExporter**
- Ajout de `alarm_minutes: int = 0` au constructeur
- Si `alarm_minutes > 0` : VALARM `ACTION:DISPLAY`, `TRIGGER:-PTNm` dans chaque VEVENT

**CLI `generate-f1`**
- Lecture `ConfigService()` au démarrage de la commande
- Cache construit depuis `config.cache` (path + TTL)
- Source F1 sélectionnée depuis `config.providers.formula1.source`
- `IcsExporter(alarm_minutes=config.ics.alarm_minutes)` — plus de valeur codée en dur

**Fichiers**
- `config.example.yaml` — référence commentée de toutes les options
- `config.yaml` ajouté à `.gitignore`

### Fichiers modifiés / créés

| Fichier | Action |
|---|---|
| `motorsport_calendar/config/__init__.py` | Créé |
| `motorsport_calendar/config/models.py` | Créé — 5 modèles Pydantic |
| `motorsport_calendar/config/service.py` | Créé — ConfigService |
| `motorsport_calendar/exporters/ics.py` | Modifié — alarm_minutes + VALARM |
| `motorsport_calendar/cli.py` | Modifié — wiring ConfigService |
| `pyproject.toml` | Modifié — pyyaml>=6.0 |
| `tests/test_config_service.py` | Créé — 30 tests |
| `tests/test_ics_exporter.py` | Modifié — 7 tests VALARM |
| `config.example.yaml` | Créé — documentation utilisateur |
| `.gitignore` | Modifié — config.yaml exclu |
| `docs/DECISIONS.md` | ADR-009 + ADR-010 |

### Bugs rencontrés
Aucun.

### Tests exécutés
```
219 passed — 0 failed — couverture 91 %
```

---

## Session 2026-07-05 — Sprint 7 : Provider WEC

### Objectif
Créer l'architecture du provider WEC, symétrique à F1. Pas d'implémentation HTTP pour l'instant.

### Travail effectué

**Architecture `providers/wec/`**
- `WecSource` (ABC) — contrat identique à `Formula1Source`
- `WecProvider` — délègue à `WecSource`, retourne `Championship(category=ENDURANCE)`
- `OfficialWecSource` — stub `raise NotImplementedError`

**SessionTypes WEC**
- `FREE_PRACTICE`, `QUALIFYING`, `HYPERPOLE`, `RACE` — déjà présents dans le modèle `SessionType`
- Vérification explicite dans les tests

**Tests** (`test_wec_provider.py`)
- WecSource ABC non instanciable
- WecProvider identity (name="wec", supported_championships=["wec"])
- fetch_events : délégation, empty, passage year, non-mutation
- fetch_championship : id, name, category ENDURANCE, years différents
- SessionType WEC : les 4 types supportés
- OfficialWecSource : NotImplementedError, isinstance WecSource
- Interopérabilité modèles : Event, Circuit, Championship identiques F1/WEC

### Fichiers modifiés / créés

| Fichier | Action |
|---|---|
| `motorsport_calendar/providers/wec/__init__.py` | Créé |
| `motorsport_calendar/providers/wec/provider.py` | Créé |
| `motorsport_calendar/providers/wec/source.py` | Créé |
| `motorsport_calendar/providers/wec/sources/__init__.py` | Créé |
| `motorsport_calendar/providers/wec/sources/official.py` | Créé |
| `tests/test_wec_provider.py` | Créé — 24 tests |
| `docs/AI_CONTEXT.md` | Mis à jour |
| `docs/JOURNAL.md` | Mis à jour |
| `docs/TODO.md` | Mis à jour |

### Bugs rencontrés
Aucun.

### Tests exécutés
```
182 passed — 0 failed — couverture 90 %
```

---

## Session 2026-07-05 — Sprint 6 : Cache HTTP centralisé

### Objectif
Créer un cache HTTP mutualisé, indépendant de httpx, réutilisable par tous les futurs providers. Migrer OpenF1Source. Ajouter `--refresh` à la CLI.

### Travail effectué

**Module `motorsport_calendar/cache/`**
- `HttpCache` : cache disque JSON, TTL configurable (défaut 24h), clé SHA-256(url + params triés)
- API : `get_json(url, params, fetch, *, refresh)` / `invalidate()` / `clear()`
- Aucune dépendance httpx : le caller fournit la coroutine `fetch`
- Création automatique du dossier `.cache/`

**Migration OpenF1Source**
- Nouveaux paramètres : `cache: HttpCache | None`, `refresh: bool = False`
- Heuristique backward-compat : client injecté (tests) → cache désactivé par défaut → 45 tests existants non touchés
- `_get_json` : route via cache si présent, appel direct sinon

**CLI `generate-f1`**
- Ajout `--refresh` (boolean flag)
- Propagation `refresh=True` → `OpenF1Source(refresh=True)` → `HttpCache.get_json(refresh=True)`

**Tests**
- 24 tests unitaires `HttpCache` (miss, hit, expiry, refresh, corruption, invalidate, clear)
- 4 tests CLI `--refresh` (exit 0, fichier créé, flag propagé True/False)
- 45 tests OpenF1Source : aucune modification, tous passants

### Fichiers modifiés / créés

| Fichier | Action |
|---|---|
| `motorsport_calendar/cache/__init__.py` | Créé |
| `motorsport_calendar/cache/http_cache.py` | Créé |
| `motorsport_calendar/providers/formula1/sources/openf1.py` | Modifié — ajout cache + refresh |
| `motorsport_calendar/cli.py` | Modifié — ajout `--refresh` |
| `tests/test_http_cache.py` | Créé — 24 tests |
| `tests/test_cli_generate_f1.py` | Modifié — 4 tests --refresh |
| `.gitignore` | Modifié — ajout `.cache/` |
| `docs/AI_CONTEXT.md` | Mis à jour |
| `docs/JOURNAL.md` | Mis à jour |
| `docs/DECISIONS.md` | ADR-008 ajouté |
| `docs/TODO.md` | Mis à jour |

### Bugs rencontrés
Aucun. La heuristique "client injecté = cache désactivé" a permis d'éviter de toucher les 45 tests existants.

### Tests exécutés
```
158 passed — 0 failed — couverture 89 %
```

---

## Session 2026-07-05 — Phase 7 + documentation initiale

### Objectif
Finaliser le MVP Formula 1 : commande CLI `generate-f1` + tests d'intégration + documentation projet.

### Travail effectué

**Phase 7 — CLI `generate-f1`**
- Ajout de la commande `motocal generate-f1 YEAR OUTPUT.ics` dans `motorsport_calendar/cli.py`
- Wiring complet : `OpenF1Source` → `Formula1Provider` → `IcsExporter`
- Gestion d'erreur : `httpx.HTTPStatusError` (exit 1) et `httpx.TimeoutException` (exit 1)
- Imports lazy pour ne pas ralentir le démarrage CLI
- 11 tests d'intégration créés dans `tests/test_cli_generate_f1.py`
  - Happy path : exit 0, fichier créé, `BEGIN:VCALENDAR`, N VEVENTs, localisations, saison vide
  - Error path : HTTP 4xx/5xx et timeout → exit 1, pas de fichier créé

**Documentation**
- Création du dossier `docs/` avec 6 fichiers :
  - `PROJECT_RULES.md` — règles d'architecture
  - `DECISIONS.md` — 7 ADRs documentant les choix techniques
  - `ROADMAP.md` — vision v0.1 → v1.0
  - `TODO.md` — backlog priorisé
  - `AI_CONTEXT.md` — état projet pour reprise IA
  - `JOURNAL.md` — ce fichier

### Fichiers modifiés / créés

| Fichier | Action |
|---|---|
| `motorsport_calendar/cli.py` | Ajout commande `generate-f1` |
| `tests/test_cli_generate_f1.py` | Créé — 11 tests d'intégration |
| `docs/PROJECT_RULES.md` | Créé |
| `docs/DECISIONS.md` | Créé — 7 ADRs |
| `docs/ROADMAP.md` | Créé |
| `docs/TODO.md` | Créé |
| `docs/AI_CONTEXT.md` | Créé |
| `docs/JOURNAL.md` | Créé |

### Bugs rencontrés

1. **Test `test_event_summaries_contain_gp_names` échoue**
   - Cause : l'IcsExporter met `session.title` en SUMMARY (ex: "Race"), pas le nom du GP
   - Fix : remplacer l'assertion par un check sur le champ LOCATION (circuit name/city)

### Tests exécutés

```
130 passed — 0 failed — couverture 87 %
```

### Résultat du commit (à venir)
Voir section "Commit proposé" en bas de session.

---

## Session précédente (reconstituée depuis git)

### Phase 1 — Scaffold
- `pyproject.toml`, CI GitHub Actions, structure de packages, `motocal` entry point

### Phase 2 — Modèles métier
- `Championship`, `Circuit`, `Session`, `Event`, `SessionType`
- Pydantic v2, `frozen=True`, validator `end > start` sur `Session`

### Phase 3 — EventStatus + event_uid
- Ajout de `EventStatus(StrEnum)` et champ `event_uid` dans `Event`

### Phase 4 — IcsExporter
- `IcsExporter` avec `icalendar`, 1 VEVENT par Session, `METHOD:PUBLISH`

### Phase 5 — Architecture F1
- `Formula1Provider`, `Formula1Source` (ABC), 4 stubs (OpenF1, Ergast, Official, Cached)

### Phase 6 — OpenF1Source
- Implémentation complète : `_get_json`, mapping meetings/sessions, 25 circuits IANA
- 45 tests unitaires avec mock HTTP stdlib uniquement
