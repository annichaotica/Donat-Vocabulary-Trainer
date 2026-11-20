# Vokabeltrainer — Copyright (C) 2026 Annuschka Brenner
#
# Freie Software unter der GNU Affero General Public License, Fassung 3
# oder später. Herausgegeben in der Hoffnung, dass sie nützt, aber OHNE
# JEDE GEWÄHRLEISTUNG. Siehe die Datei LICENSE.
"""Der Name des Programms — an EINER Stelle.

»Arbeitsname des Projekts: Donat. In README, Image-Namen und
Oberfläche als eine zentrale Einstellung führen, damit er sich später
an einer Stelle ändern lässt.«

Donat nach Aelius Donatus, dessen *Ars minor* das Lateinlehrbuch des
Mittelalters war — über tausend Jahre lang, und »Donat« wurde im
Deutschen zum Gattungswort für das Schulbuch selbst.

ÄNDERN: hier, und nur hier. Alles andere liest von hier:

    backend      `marke.NAME` (FastAPI-Titel, MCP-Auskunft, Startseite)
    Oberfläche   `GET /api/zustand` liefert den Namen mit; index.html
                 und das Webmanifest tragen ihn als Anfangswert, bis
                 die Anwendung geladen ist
    Abbild       `IMAGE_NAME` in der GitHub-Action und in der
                 docker-compose.yml
    README       in der Überschrift

Das Verzeichnis, das Paket und die Modulnamen heißen weiter
»vokabeltrainer«: ein Umbenennen des Repositoriums ist ausdrücklich
nicht beauftragt, und ein halb umbenanntes Projekt ist schlimmer als
ein durchgehend altmodisches.

Über die Umgebung übersteuerbar, damit sich ein anderer Name
ausprobieren lässt, ohne den Quelltext anzufassen.
"""

from __future__ import annotations

import os

# Der Arbeitsname. Eine Zeile, die den Namen überall ändert.
NAME = os.environ.get("VOKABEL_NAME", "Donat").strip() or "Donat"

# Was unter dem Namen steht — in der Startseite und in der Auskunft der
# Schnittstelle. Bewusst ein Satz und kein Werbespruch.
UNTERTITEL = os.environ.get(
    "VOKABEL_UNTERTITEL",
    "Vokabeln lernen mit Formen, Fehleranalyse und eigenen Texten").strip()

# Die Fassung. Stand hier einmal im FastAPI-Aufruf und einmal im
# CHANGELOG; zwei Orte für dieselbe Zahl laufen auseinander.
VERSION = "0.1.0"

# Der Name des Abbilds auf ghcr.io, klein geschrieben.
ABBILD = NAME.lower()
