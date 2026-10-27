"""GUI components — reusable widgets shared across every view.

Unlike ``gui/views/*`` (one module per navigation destination, each owning
its own page), a component here knows nothing about *where* it is used.
It takes a plain, already-formatted data model and returns an ``ft.Control``
— nothing else. Views build the data (from providers, preferences, search
results, ...) and hand it to the component; the component never reaches
back into business logic, providers, or domain models.

First component: ``championship_card`` — the one race-card layout reused by
Ce week-end today, and eventually Favoris, Recherche, Tableau de bord,
Calendrier, Notifications, Historique.
"""
