#!/usr/bin/env python3
"""Nimmt die Bildschirmfotos für den Lehrgang auf.

    .venv/bin/python werkzeuge/bilder-aufnehmen.py

Warum ein Skript und nicht von Hand: Bildschirmfotos veralten. Jede
Änderung an der Oberfläche macht sie ein Stück falscher, und ein Bild,
das etwas anderes zeigt als das Werkzeug, ist schlimmer als keines.
Mit diesem Skript kostet das Erneuern einen Aufruf.

Und warum eine EIGENE Instanz mit eigener Datenbank, statt den
laufenden Trainer zu fotografieren: die Bilder landen in einem
öffentlichen Repo. Aus dem Familienbestand dürfte nichts darauf zu
sehen sein — keine Vokabel, kein Lernstand, kein Name. Hier entsteht
ein leeres Profil namens »Beispiel« mit dem englischen Übungskurs, und
die Datenbank wird am Ende weggeworfen.

Gebraucht wird Google Chrome (für `--headless --screenshot`) und ein
freier Port. Beides wird geprüft, bevor etwas passiert.
"""

from __future__ import annotations

import http.client
import os
import pathlib
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.parse

WURZEL = pathlib.Path(__file__).resolve().parents[1]
ZIEL = WURZEL / "frontend" / "bilder" / "lehrgang"
CHROME = ("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")

# Was aufgenommen wird. Die Höhe ist je Bild verschieden — ein Ausschnitt
# soll zeigen, worum es geht, und nicht eine halbe leere Seite.
AUFNAHMEN = [
    ("abfrage", "#/lernen", 1100, 500),
    ("uebersicht", "#/uebersicht", 1100, 860),
    ("wortschatz", "#/wortschatz", 1100, 700),
    ("freigabe", "#/freigabe", 1100, 330),
    ("texte", "#/texte", 1100, 430),
    ("fortschritt", "#/statistik", 1100, 900),
    ("lehrgang-einstellung", "#/einstellungen/lehrgang", 1100, 620),
]

# Eine Seite, die den Sitzungszustand setzt und dann weiterleitet.
# Muss vom SELBEN Ursprung kommen wie die Anwendung, sonst gehört ihr
# der localStorage nicht. Darum wird sie in die Oberfläche gelegt und
# hinterher wieder entfernt.
WEICHE = """<!doctype html><meta charset="utf-8"><title>Aufnahme</title>
<script>
  const f = new URLSearchParams(location.search);
  localStorage.setItem('vokabeltrainer.zustand', JSON.stringify({
    benutzerId: Number(f.get('p')), sammlungId: Number(f.get('s')),
    lektionId: null }));
  // Die Rundgänge als gesehen markieren: ihre Willkommenskarte gehört
  // nicht auf jedes Bild.
  localStorage.setItem('vokabeltrainer.fuehrungen',
    '["erste-schritte","abfrage","planen","texte"]');
  location.replace('/' + (f.get('z') || '#/uebersicht'));
</script>
"""


def freier_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def wartet_auf(port: int, sekunden: float = 20) -> bool:
    ende = time.time() + sekunden
    while time.time() < ende:
        try:
            v = http.client.HTTPConnection("127.0.0.1", port, timeout=1)
            v.request("GET", "/api/zustand")
            if v.getresponse().status < 500:
                return True
        except OSError:
            time.sleep(0.3)
    return False


def main() -> int:
    if not pathlib.Path(CHROME).exists():
        print(f"Chrome nicht gefunden: {CHROME}", file=sys.stderr)
        return 1

    sys.path.insert(0, str(WURZEL / "backend"))
    ordner = pathlib.Path(tempfile.mkdtemp(prefix="bilder-"))
    datenbank = ordner / "aufnahme.db"

    import datenbank as dbm                                  # noqa: E402
    dbm.PFAD = datenbank
    db = dbm.verbindung()
    dbm.einrichten(db)
    db.execute("INSERT INTO benutzer (id, name, verwalter) VALUES (1, ?, 1)",
               ("Beispiel",))
    import beispielkurs                                      # noqa: E402
    kurs = beispielkurs.anlegen(db, 1)

    # Ein paar Antworten, damit »Fortschritt« nicht leer aussieht. Ohne
    # sie zeigte das Bild nur den Satz »noch keine Antwort« — richtig,
    # aber als Beispiel wertlos.
    import lernen as lernmodul                               # noqa: E402
    for i, a in enumerate(lernmodul.naechste(db, 1, anzahl=12)):
        lernmodul.bewerten(db, 1, a["aufgabe_id"], 1 if i % 4 == 3 else 4)
    db.commit()
    db.close()

    weiche = WURZEL / "frontend" / "_aufnahme.html"
    weiche.write_text(WEICHE)
    port = freier_port()
    umgebung = {**os.environ, "VOKABEL_DB": str(datenbank)}
    dienst = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app:app",
         "--host", "127.0.0.1", "--port", str(port), "--log-level", "warning"],
        cwd=WURZEL / "backend", env=umgebung,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        if not wartet_auf(port):
            print("Der Dienst ist nicht hochgekommen.", file=sys.stderr)
            return 1
        ZIEL.mkdir(parents=True, exist_ok=True)
        for name, ziel, breite, hoehe in AUFNAHMEN:
            # Der Anker MUSS verschlüsselt werden: roh angehängt
            # beginnt mit »#« der Fragmentteil der Weiche, `z` bleibt
            # leer, und jedes Bild zeigt die Übersicht. Genau so ist
            # es beim ersten Lauf passiert.
            adresse = (f"http://127.0.0.1:{port}/_aufnahme.html"
                       f"?p=1&s={kurs['sammlung_id']}"
                       f"&z={urllib.parse.quote(ziel, safe='')}")
            pfad = ZIEL / f"{name}.png"
            lauf = subprocess.run(
                [CHROME, "--headless", "--disable-gpu", "--hide-scrollbars",
                 f"--screenshot={pfad}", f"--window-size={breite},{hoehe}",
                 "--virtual-time-budget=8000",
                 f"--user-data-dir={ordner / 'chrome'}", adresse],
                capture_output=True, text=True)
            gut = pfad.exists() and pfad.stat().st_size > 3000
            print(f"  {'ok ' if gut else 'LEER'} {name:22} "
                  f"{pfad.stat().st_size if pfad.exists() else 0:7} Byte")
            if not gut and lauf.stderr:
                print("      " + lauf.stderr.strip().splitlines()[-1])
    finally:
        dienst.terminate()
        dienst.wait(timeout=10)
        weiche.unlink(missing_ok=True)
        shutil.rmtree(ordner, ignore_errors=True)
    print(f"\nBilder in {ZIEL.relative_to(WURZEL)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
