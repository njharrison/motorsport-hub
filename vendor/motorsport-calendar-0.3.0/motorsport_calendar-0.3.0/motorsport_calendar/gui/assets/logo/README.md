# Logos — Brand Set v1.0 (livrés Sprint 49)

Ce dossier contient les assets définitifs du Brand Set Motorsport Calendar
v1.0 (validé, voir `BApps-Studio/03-Products/Motorsport-Calendar/Branding/Branding.md`
et sa copie locale `assets/branding/` à la racine du dépôt — copies
identiques, vérifié bit à bit).

Servis par Flet via `assets_dir` (`gui/app.py`) — accessibles à l'exécution
sous le chemin relatif `logo/{fichier}`.

**Sprint 49 (Packaging Alpha) intègre les fichiers au build uniquement** —
conformément à la consigne du sprint ("aucune évolution du Design System",
"ne pas modifier les vues autrement que pour résoudre un problème de
packaging"), l'app continue d'afficher le **placeholder**
(`theme.logo_placeholder()` dans `gui/theme.py`) partout où le logo
apparaîtra à terme. Remplacer les appels par de vraies images reste une
tâche de polish visuel distincte, pas un problème de packaging.

## Fichiers présents

| Fichier | Rôle | Consommateur prévu (pas encore câblé) |
|---|---|---|
| `mc-icon.svg` | Monogramme MC seul, fond transparent | Nav rail, en-tête "À propos", en-tête "Mon calendrier" |
| `logo-horizontal.svg` | Monogramme + wordmark, texte blanc | En-tête large / bannière |
| `logo-vertical.svg` | Monogramme au-dessus du wordmark | Espaces restreints (menus latéraux, mobile) |

L'icône application (fenêtre/barre des tâches) est **déjà câblée** :
`gui/assets/icon.png` (`page.window.icon`, `main_view.py`) et
`gui/assets/icon_windows.ico` (icône `.exe` Windows, convention Flet
`icon_windows.ico` — voir `docs/PACKAGING.md`). Le favicon
(`gui/assets/favicon-16.png`/`favicon-32.png`) est présent et servi mais
n'a pas de consommateur actif : l'app ne cible que `ft.AppView.FLET_APP`
(desktop natif) aujourd'hui, pas `WEB_BROWSER`.

## Intégration future (remplacement des placeholders)

1. Remplacer les appels à `theme.logo_placeholder(...)` par
   `ft.Image(src="logo/mc-icon.svg", ...)` (ou `logo-horizontal.svg`) aux
   emplacements listés ci-dessus.

Aucune autre modification de layout n'est nécessaire : les emplacements ont
été dimensionnés pour accueillir le logo définitif tel quel.
