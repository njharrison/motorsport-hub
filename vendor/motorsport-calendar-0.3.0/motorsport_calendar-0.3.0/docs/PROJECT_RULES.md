# PROJECT_RULES.md

> Ces règles gouvernent l'architecture du projet. Ne jamais les modifier sans demander confirmation explicite.

---

## 1. Modèles métier

- Tous les modèles sont des `pydantic.BaseModel` avec `frozen=True`.
- Les champs de collection utilisent `tuple[T, ...]` (pas `list`) pour garantir l'immuabilité réelle.
- Aucun modèle ne contient de logique I/O (pas d'appel HTTP, pas de lecture de fichier).
- Les enums héritent de `StrEnum`.
- Validation des invariants dans un `@model_validator(mode="after")`.

## 2. Providers

- Tout provider hérite de `Provider` (ABC dans `providers/base.py`).
- Un provider ne contient **aucune logique de parsing** : il délègue à une `Source`.
- La `Source` est injectée au constructeur (dependency injection).
- Un provider Formula 1 hérite de `Formula1Provider` et reçoit une `Formula1Source`.
- Les sources HTTP utilisent `httpx.AsyncClient` injecté optionnellement.

## 3. Exporteurs

- Tout exporteur hérite de `Exporter` (ABC dans `exporters/base.py`).
- Les exporteurs ne contiennent **aucune logique métier** : ils reçoivent des `Event` prêts.
- Méthodes obligatoires : `export(events, output_path)` et `export_to_string(events)`.

## 4. CLI

- La CLI ne contient **aucune logique métier**.
- Les imports lourds (providers, exporters) sont **lazy** (à l'intérieur de chaque commande).
- La gestion d'erreur CLI se limite aux exceptions HTTP et aux erreurs de chemin.
- `asyncio.run()` est le seul pont sync→async autorisé dans la CLI.
- Aucun `print()` direct : utiliser `Console` (Rich).

## 5. Tests

- Toute classe publique doit avoir des tests unitaires.
- Les appels HTTP sont toujours mockés (`unittest.mock`, jamais de hit réseau en CI).
- Le pattern de mock HTTP : `AsyncMock` sur `_get_json` ou client injecté.
- Aucune dépendance de test externe au-delà de `pytest`, `pytest-asyncio`, `pytest-cov`.
- `asyncio_mode = "auto"` : pas de décorateur `@pytest.mark.asyncio`.

## 6. Qualité

- Linter : `ruff` (voir `ruff.toml`).
- Type checker : `mypy` (voir `mypy.ini`).
- Pre-commit hooks actifs.
- Couverture cible : ≥ 85 % (actuellement ~97 % — voir `docs/AI_CONTEXT.md`).

## 7. Git

- Format des commits : `type(scope): message` (Conventional Commits).
- Branche principale : `master`.
- Pas de merge sans tests verts.

## 8. Résilience des commandes CLI agrégées

Une commande CLI qui orchestre plusieurs providers ne doit **jamais** échouer
à cause d'un provider individuel. Le comportement attendu est :

1. Journaliser l'erreur (résumé affiché à l'utilisateur avec `✗ provider : raison`).
2. Continuer avec les providers restants.
3. Produire le meilleur résultat possible (exporter ce qui a réussi).
4. Retourner exit code 0 si au moins un provider a réussi, 1 si tous ont échoué.
