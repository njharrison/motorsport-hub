# Logos de championnats — à compléter

Ce dossier reçoit les logos officiels par championnat, consommés
exclusivement via `gui/championship_assets.py::get_championship_asset()`.
Aucune vue ni composant ne référence un chemin de fichier directement.

Aucun logo officiel n'a été livré ni copié ici pour ce sprint —
`ChampionshipCard` s'affiche donc sans logo pour tous les championnats
aujourd'hui (comportement de repli explicitement prévu et testé, pas un
bug).

## Fichiers attendus (non livrés)

| Fichier | championship_id |
|---|---|
| `formula1.png` | `formula1` |
| `formula2.png` | `formula2` |
| `formula3.png` | `formula3` |
| `f1-academy.png` | `f1-academy` |
| `wec.png` | `wec` |

## Intégration future

1. Copier le fichier officiel dans ce dossier, au nom exact listé ci-dessus.
2. Décommenter `assets_dir=` dans `motorsport_calendar/gui/app.py`
   (partagé avec `gui/assets/logo/README.md` — un seul dossier `assets/`
   servi par Flet pour toute l'app).

Aucune autre modification n'est nécessaire : `get_championship_asset()`
détecte la présence du fichier à l'exécution et `ChampionshipCard`
affiche le logo automatiquement dès qu'il est présent.
