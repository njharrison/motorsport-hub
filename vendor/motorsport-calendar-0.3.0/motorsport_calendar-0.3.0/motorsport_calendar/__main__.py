"""Entry point for `python -m motorsport_calendar`.

Allows running the CLI when the Scripts directory is not on PATH:
    python -m motorsport_calendar --help
    python -m motorsport_calendar generate-f1 2026 f1.ics
"""

from motorsport_calendar.cli import app

app()
