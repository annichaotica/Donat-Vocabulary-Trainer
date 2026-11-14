"""Statische Prüfungen der Oberfläche.

Ohne Bauschritt gibt es keinen Übersetzer, der einen Tippfehler im
Funktionsnamen bemerkt — `api.aufdecken(...)` aufzurufen, ohne es in api.js
einzutragen, fällt sonst erst beim Benutzen auf. Diese Tests ersetzen das,
soweit es sich mit einfachen Mitteln machen lässt.
"""

import json
import pathlib
import re
import subprocess

WURZEL = pathlib.Path(__file__).resolve().parents[1]
JS = sorted((WURZEL / "frontend" / "js").glob("*.js"))
CSS = WURZEL / "frontend" / "css"
HTML = WURZEL / "frontend" / "index.html"


def test_es_gibt_javascript_dateien():
    assert len(JS) >= 8


def test_jede_benutzte_schnittstellenfunktion_ist_auch_eingetragen():
    """Der Fall, der wirklich auftrat: api.aufdecken wurde an zwei Stellen
    gerufen und war nie eingetragen. »Weiß ich nicht« war damit kaputt."""
    api_text = (WURZEL / "frontend" / "js" / "api.js").read_text()
    # Die Schlüssel des exportierten Objekts
    eingetragen = set(re.findall(r"^\s{2}(\w+):", api_text, re.MULTILINE))
    assert "pruefen" in eingetragen, "Erkennung der Einträge misslungen"

    benutzt = set()
    for datei in JS:
        if datei.name == "api.js":
            continue
        benutzt |= set(re.findall(r"\bapi\.(\w+)\s*\(", datei.read_text()))
    fehlend = benutzt - eingetragen
    assert not fehlend, f"In api.js fehlen: {sorted(fehlend)}"


def test_keine_verwaisten_schnittstellenfunktionen():
    """Umgekehrt: was nie gerufen wird, ist vermutlich vergessener Ballast."""
    api_text = (WURZEL / "frontend" / "js" / "api.js").read_text()
    eingetragen = set(re.findall(r"^\s{2}(\w+):", api_text, re.MULTILINE))
    benutzt = set()
    for datei in JS:
        if datei.name == "api.js":
            continue
        benutzt |= set(re.findall(r"\bapi\.(\w+)\s*\(", datei.read_text()))
    unbenutzt = eingetragen - benutzt
    # Ein paar dürfen vorrätig sein, aber nicht die Hälfte.
    assert len(unbenutzt) < len(eingetragen) / 2, sorted(unbenutzt)


def test_alle_module_sind_syntaktisch_gueltig():
    """Braucht node; wo es fehlt, wird der Test übersprungen."""
    import shutil
    import pytest
    if not shutil.which("node"):
        pytest.skip("node nicht vorhanden")
    for datei in JS:
        ergebnis = subprocess.run(["node", "--check", str(datei)],
                                  capture_output=True, text=True)
        assert ergebnis.returncode == 0, f"{datei.name}: {ergebnis.stderr}"


def test_jede_vom_javascript_gesuchte_kennung_steht_im_html():
    html = HTML.read_text()
    vorhanden = set(re.findall(r'id="([^"]+)"', html))
    gesucht = set()
    for datei in JS:
        gesucht |= set(re.findall(r"getElementById\(['\"]([^'\"]+)['\"]\)",
                                  datei.read_text()))
    fehlend = gesucht - vorhanden
    assert not fehlend, f"Im HTML fehlen die Kennungen: {sorted(fehlend)}"


def test_die_variablen_des_legastheniemodus_wirken_im_stil():
    """darstellungSetzen in zustand.js schreibt diese Variablen. Wenn der
    Stil sie nicht benutzt, ändert der Modus nichts."""
    zustand = (WURZEL / "frontend" / "js" / "zustand.js").read_text()
    geschrieben = set(re.findall(r"setProperty\('(--[\w-]+)'", zustand))
    assert geschrieben, "keine Variablen gefunden"
    stil = "".join((CSS / name).read_text() for name in ("stil.css", "zusatz.css"))
    for name in geschrieben:
        # einmal gesetzt (:root) und mindestens einmal benutzt
        assert stil.count(f"var({name}") >= 1, f"{name} wird im Stil nicht benutzt"


def test_themenschalter_sind_vollstaendig():
    stil = (CSS / "stil.css").read_text()
    for grund in ("creme", "hell", "dunkel"):
        assert f'data-grund="{grund}"' in stil, grund
    assert "prefers-color-scheme: dark" in stil
    assert "prefers-reduced-motion" in stil


def test_keine_waagerechte_ueberlaufquelle_im_grundgeruest():
    """Der Seitenkörper darf nie seitlich scrollen."""
    stil = (CSS / "stil.css").read_text()
    assert "overflow-x" in stil, "keine Absicherung gegen waagerechten Überlauf"


def test_kein_aufruf_einer_unbekannten_stammdatenfunktion():
    stammdaten = (WURZEL / "frontend" / "js" / "stammdaten.js").read_text()
    eingetragen = set(re.findall(r"^\s{2}(\w+):", stammdaten, re.MULTILINE))
    eingetragen |= set(re.findall(r"^\s{2}async (\w+)\(", stammdaten, re.MULTILINE))
    benutzt = set()
    for datei in JS:
        if datei.name == "stammdaten.js":
            continue
        benutzt |= set(re.findall(r"\bstammdaten\.(\w+)\s*\(", datei.read_text()))
    assert not (benutzt - eingetragen), sorted(benutzt - eingetragen)


def test_oberflaechendateien_werden_gegengeprueft():
    """Ohne das hält der Browser die ES-Module fest und zeigt nach einer
    Aktualisierung tagelang die alte Fassung — ohne jeden Hinweis."""
    import pathlib, sys
    sys.path.insert(0, str(WURZEL / "backend"))
    import tempfile
    import datenbank as dbm
    dbm.PFAD = pathlib.Path(tempfile.mkdtemp()) / "t.db"
    from fastapi.testclient import TestClient
    import app as anwendung
    with TestClient(anwendung.app) as k:
        for pfad in ("/", "/js/app.js", "/css/stil.css"):
            antwort = k.get(pfad)
            assert antwort.status_code == 200, pfad
            assert antwort.headers.get("cache-control") == "no-cache", pfad
        # Die Schnittstelle ist davon nicht betroffen
        assert k.get("/api/zustand").headers.get("cache-control") is None


def test_wanderung_aus_einer_alten_datenbank():
    """Der Fall, der wirklich auftrat: alle Tests starten mit einer frischen
    Datenbank, deshalb fiel nie auf, dass ein Index im Schemaskript auf eine
    Spalte zeigte, die erst die Wanderung anlegt. In einer bestehenden
    Datenbank ist CREATE TABLE IF NOT EXISTS wirkungslos — der Index lief
    ins Leere und der Dienst startete nicht mehr.
    """
    import sqlite3
    import sys
    import tempfile
    sys.path.insert(0, str(WURZEL / "backend"))
    import datenbank as dbm

    pfad = pathlib.Path(tempfile.mkdtemp()) / "alt.db"
    alt = sqlite3.connect(pfad)
    # Eine Datenbank, wie sie vor den Erweiterungen aussah
    alt.executescript("""
        CREATE TABLE schema_stand (version INTEGER NOT NULL);
        INSERT INTO schema_stand VALUES (1);
        CREATE TABLE sprache (code TEXT PRIMARY KEY, name TEXT NOT NULL,
            schrift TEXT NOT NULL DEFAULT 'latein', stimme TEXT,
            profil TEXT NOT NULL DEFAULT '{}');
        CREATE TABLE benutzer (id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE,
            farbe TEXT NOT NULL DEFAULT '#6b7fd7',
            einstellungen TEXT NOT NULL DEFAULT '{}',
            angelegt TEXT NOT NULL DEFAULT (datetime('now')));
        CREATE TABLE sammlung (id INTEGER PRIMARY KEY, besitzer_id INTEGER NOT NULL,
            name TEXT NOT NULL, sprache TEXT NOT NULL,
            grundsprache TEXT NOT NULL DEFAULT 'de', beschreibung TEXT,
            angelegt TEXT NOT NULL DEFAULT (datetime('now')));
        CREATE TABLE lektion (id INTEGER PRIMARY KEY, sammlung_id INTEGER NOT NULL,
            name TEXT NOT NULL, reihenfolge INTEGER NOT NULL DEFAULT 0);
        CREATE TABLE lexem (id INTEGER PRIMARY KEY, sammlung_id INTEGER NOT NULL,
            lektion_id INTEGER, lemma TEXT NOT NULL, wortart TEXT NOT NULL,
            merkmale TEXT NOT NULL DEFAULT '{}', notiz TEXT,
            angelegt TEXT NOT NULL DEFAULT (datetime('now')),
            geaendert TEXT NOT NULL DEFAULT (datetime('now')));
        INSERT INTO benutzer (name) VALUES ('Alt');
        INSERT INTO sammlung (besitzer_id, name, sprache) VALUES (1, 'Alt', 'el');
        INSERT INTO lektion (sammlung_id, name) VALUES (1, 'Erste');
        INSERT INTO lexem (sammlung_id, lemma, wortart) VALUES (1, 'παλιό', 'adjektiv');
    """)
    alt.commit()
    alt.close()

    db = dbm.verbindung(pfad)
    dbm.einrichten(db)                        # darf nicht werfen
    assert dbm.wert(db, "SELECT version FROM schema_stand") == dbm.SCHEMA_VERSION
    # Die Daten sind noch da
    assert dbm.wert(db, "SELECT lemma FROM lexem") == "παλιό"
    assert dbm.wert(db, "SELECT name FROM benutzer") == "Alt"
    # Und die nachgerüsteten Spalten samt Index sind vorhanden
    assert {"nr", "beschreibung"} <= dbm.spalten(db, "lektion")
    assert {"reihenfolge", "kennung"} <= dbm.spalten(db, "lexem")
    indizes = {z[0] for z in db.execute(
        "SELECT name FROM sqlite_master WHERE type='index'")}
    assert "idx_lektion_nr" in indizes
    assert "idx_lexem_kennung" in indizes
    # Zweimal einrichten muss ebenfalls gehen
    dbm.einrichten(db)
    db.close()
