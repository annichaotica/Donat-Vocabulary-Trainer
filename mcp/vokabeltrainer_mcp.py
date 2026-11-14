#!/usr/bin/env python3
# Vokabeltrainer — Copyright (C) 2026 Annuschka Brenner
#
# Freie Software unter der GNU Affero General Public License, Fassung 3
# oder später. Herausgegeben in der Hoffnung, dass sie nützt, aber OHNE
# JEDE GEWÄHRLEISTUNG. Siehe die Datei LICENSE.
"""Brücke von stdio zum MCP-Dienst des Vokabeltrainers.

Seit dem Umbau auf HTTPS gibt es nur noch EINE Umsetzung der Werkzeuge:
sie steht im Trainer selbst unter /mcp (backend/mcp_dienst.py). Dieses
Skript reicht nur durch — für Clients, die MCP über stdio sprechen
(Claude Code, Claude Desktop ohne Konnektor).

Sonst müsste jede neue Fähigkeit zweimal geschrieben und zweimal geprüft
werden, und die beiden Fassungen liefen auseinander.

    VOKABEL_URL=http://dein-server:8030 \
    VOKABEL_MCP_TOKEN=... \
    python3 vokabeltrainer_mcp.py

Keine Fremdpakete, nur die Standardbibliothek.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request

ADRESSE = os.environ.get("VOKABEL_URL", "http://localhost:8030").rstrip("/")
GEHEIMNIS = os.environ.get("VOKABEL_MCP_TOKEN", "").strip()
ZEITGRENZE = 60


def _antwort(kennung, ergebnis=None, fehler=None) -> None:
    nachricht = {"jsonrpc": "2.0", "id": kennung}
    if fehler is not None:
        nachricht["error"] = fehler
    else:
        nachricht["result"] = ergebnis
    sys.stdout.write(json.dumps(nachricht, ensure_ascii=False) + "\n")
    sys.stdout.flush()


def _durchreichen(nachricht: dict) -> dict | None:
    """Schickt die Nachricht an /mcp und gibt die Antwort zurück."""
    kopfzeilen = {"Content-Type": "application/json",
                  "Accept": "application/json"}
    if GEHEIMNIS:
        kopfzeilen["Authorization"] = f"Bearer {GEHEIMNIS}"
    anfrage = urllib.request.Request(
        f"{ADRESSE}/mcp", data=json.dumps(nachricht).encode(),
        method="POST", headers=kopfzeilen)
    with urllib.request.urlopen(anfrage, timeout=ZEITGRENZE) as antwort:
        if antwort.status == 202:
            return None                     # Benachrichtigung, keine Antwort
        roh = antwort.read().decode()
        return json.loads(roh) if roh.strip() else None


def behandeln(nachricht: dict) -> None:
    kennung = nachricht.get("id")
    try:
        antwort = _durchreichen(nachricht)
    except urllib.error.HTTPError as fehler:
        text = fehler.read().decode()
        try:
            einzelheit = json.loads(text).get("detail") or text
        except json.JSONDecodeError:
            einzelheit = text
        if kennung is not None:
            hinweis = {
                401: "Zugang abgelehnt. Stimmt VOKABEL_MCP_TOKEN?",
                503: "Die MCP-Schnittstelle ist im Trainer abgeschaltet. "
                     "Dort VOKABEL_MCP_TOKEN setzen.",
            }.get(fehler.code, "")
            _antwort(kennung, fehler={
                "code": -32000,
                "message": f"{fehler.code}: {einzelheit}"
                           + (f" — {hinweis}" if hinweis else "")})
        return
    except urllib.error.URLError as fehler:
        if kennung is not None:
            _antwort(kennung, fehler={
                "code": -32000,
                "message": f"Der Trainer ist unter {ADRESSE} nicht erreichbar "
                           f"({fehler.reason}). Läuft er? Stimmt VOKABEL_URL?"})
        return
    except Exception as fehler:                              # noqa: BLE001
        if kennung is not None:
            _antwort(kennung, fehler={"code": -32603, "message": str(fehler)})
        return

    if antwort is not None:
        sys.stdout.write(json.dumps(antwort, ensure_ascii=False) + "\n")
        sys.stdout.flush()


def main() -> None:
    for zeile in sys.stdin:
        zeile = zeile.strip()
        if not zeile:
            continue
        try:
            nachricht = json.loads(zeile)
        except json.JSONDecodeError:
            continue
        behandeln(nachricht)


if __name__ == "__main__":
    main()
