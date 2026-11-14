"""SQLite-Anbindung.

Eine Datei, kein Serverdienst. Sie liegt auf dem Familienserver unter
/srv/vokabeltrainer/ und wird damit von der bestehenden /srv-Sicherung
mitgenommen, ohne dass irgendwo ein Datenbankabzug eingerichtet werden muss.

WAL-Modus, damit Lesen und Schreiben sich nicht gegenseitig blockieren,
wenn gleichzeitig jemand am iPad lernt und jemand am Mac Vokabeln einträgt.
"""

from __future__ import annotations

import json
import os
import pathlib
import sqlite3
from typing import Any, Iterable

import sprachen

SCHEMA_VERSION = 8

_WURZEL = pathlib.Path(__file__).resolve().parent.parent
PFAD = pathlib.Path(os.environ.get("VOKABEL_DB", _WURZEL / "daten" / "vokabeltrainer.db"))


def verbindung(pfad: pathlib.Path | str | None = None) -> sqlite3.Connection:
    ziel = pathlib.Path(pfad or PFAD)
    ziel.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(ziel, isolation_level=None, check_same_thread=False)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    db.execute("PRAGMA journal_mode = WAL")
    db.execute("PRAGMA synchronous = NORMAL")
    db.execute("PRAGMA busy_timeout = 5000")
    return db


def einrichten(db: sqlite3.Connection) -> None:
    """Legt das Schema an, falls es fehlt, und pflegt die Sprachliste."""
    schema = (pathlib.Path(__file__).resolve().parent / "schema.sql").read_text()
    db.executescript(schema)
    stand = db.execute("SELECT version FROM schema_stand").fetchone()
    if stand is None:
        db.execute("INSERT INTO schema_stand (version) VALUES (?)", (SCHEMA_VERSION,))
    # Die Wanderung läuft IMMER, nicht nur bei abweichendem Stand. Sie legt
    # auch die Indizes an, die auf nachgerüsteten Spalten liegen — die
    # dürfen nicht im Schemaskript stehen, weil sie dort zu früh kämen.
    wandern(db, stand["version"] if stand else SCHEMA_VERSION)
    sprachen_pflegen(db)
    sprachprofile_laden(db)


def spalten(db: sqlite3.Connection, tabelle: str) -> set[str]:
    return {z[1] for z in db.execute(f"PRAGMA table_info({tabelle})")}


# Nachgerüstete Spalten. CREATE TABLE IF NOT EXISTS legt eine bestehende
# Tabelle nicht neu an — fehlende Spalten müssen also einzeln dazu.
NACHRUESTEN: dict[str, dict[str, str]] = {
    "wiederholung": {
        "denkzeit_ms": "INTEGER",
        "versuche": "INTEGER NOT NULL DEFAULT 1",
        "bewertung_quelle": "TEXT NOT NULL DEFAULT 'automatisch'",
    },
    "sammlung": {
        "einstellungen": "TEXT NOT NULL DEFAULT '{}'",
    },
    "lektion": {
        "nr": "INTEGER",
        "beschreibung": "TEXT",
    },
    "lexem": {
        "reihenfolge": "INTEGER NOT NULL DEFAULT 0",
        "kennung": "TEXT",
        "luecken": "TEXT NOT NULL DEFAULT '[]'",
        "staemme": "TEXT NOT NULL DEFAULT '{}'",
    },
    "form": {
        "ist_variante": "INTEGER NOT NULL DEFAULT 0",
    },
    "text": {
        "typ": "TEXT NOT NULL DEFAULT 'text'",
        "richtungen": "TEXT NOT NULL DEFAULT '[]'",
        # Getrennt von `quelle`: die sagt, wer es geschrieben hat, dies,
        # worauf es sich stützt. Ein fremder Artikel wird verlinkt, nicht
        # abgeschrieben.
        "verweis_titel": "TEXT",
        "verweis_url": "TEXT",
        "geprueft": "INTEGER NOT NULL DEFAULT 0",
        "kennung": "TEXT",
        "reihenfolge": "INTEGER NOT NULL DEFAULT 0",
        "geaendert": "TEXT",
    },
    "textabschnitt": {
        "varianten": "TEXT NOT NULL DEFAULT '[]'",
        "referenz_varianten": "TEXT NOT NULL DEFAULT '[]'",
    },
    "benutzer": {
        # Ohne UNIQUE: ALTER TABLE kann in SQLite keine eindeutige Spalte
        # nachrüsten. Der eindeutige Index steht darum eine Zeile tiefer.
        "email": "TEXT",
        "verwalter": "INTEGER NOT NULL DEFAULT 0",
    },
}


def wandern(db: sqlite3.Connection, von: int) -> None:
    """Bringt eine bestehende Datenbank auf den neuen Stand.

    Nur ergänzend: es werden Spalten hinzugefügt, nie welche entfernt oder
    umgedeutet. Ein Lernstand darf durch eine Aktualisierung nicht verloren
    gehen.
    """
    for tabelle, felder in NACHRUESTEN.items():
        if not db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
                          (tabelle,)).fetchone():
            continue
        vorhanden = spalten(db, tabelle)
        for name, art in felder.items():
            if name not in vorhanden:
                db.execute(f"ALTER TABLE {tabelle} ADD COLUMN {name} {art}")
    db.execute("""CREATE UNIQUE INDEX IF NOT EXISTS idx_benutzer_email
                    ON benutzer(email) WHERE email IS NOT NULL""")
    db.execute("""CREATE UNIQUE INDEX IF NOT EXISTS idx_lektion_nr
                    ON lektion(sammlung_id, nr) WHERE nr IS NOT NULL""")
    db.execute("""CREATE UNIQUE INDEX IF NOT EXISTS idx_lexem_kennung
                    ON lexem(sammlung_id, kennung) WHERE kennung IS NOT NULL""")
    db.execute("""CREATE INDEX IF NOT EXISTS idx_lexem_folge
                    ON lexem(sammlung_id, lektion_id, reihenfolge)""")
    db.execute("""CREATE UNIQUE INDEX IF NOT EXISTS idx_text_kennung
                    ON text(sammlung_id, kennung) WHERE kennung IS NOT NULL""")
    db.execute("""CREATE INDEX IF NOT EXISTS idx_text_folge
                    ON text(sammlung_id, lektion_id, reihenfolge)""")
    # Gibt es noch keinen Verwalter, wird es die erste angelegte Person.
    # Ohne das stünde ein bestehender Bestand nach der Aktualisierung ohne
    # jemanden da, der Sprachprofile pflegen darf.
    if not db.execute("SELECT 1 FROM benutzer WHERE verwalter = 1").fetchone():
        db.execute("""UPDATE benutzer SET verwalter = 1
                       WHERE id = (SELECT MIN(id) FROM benutzer)""")
    if von != SCHEMA_VERSION:
        db.execute("UPDATE schema_stand SET version = ?", (SCHEMA_VERSION,))


def sprachen_pflegen(db: sqlite3.Connection) -> None:
    """Trägt die im Code hinterlegten Sprachprofile ein.

    In der Tabelle stehen nur Name, Schrift und Stimme — das eigentliche
    Profil (Formgruppen, Prüfregeln) steht in sprachen.py und wird nicht
    verdoppelt. Die Spalte `profil` ist für selbst angelegte Sprachen da,
    die kein Profil im Code haben.
    """
    for code, p in sprachen.PROFILE.items():
        db.execute(
            """INSERT INTO sprache (code, name, schrift, stimme, profil)
                 VALUES (?, ?, ?, ?, '{}')
               ON CONFLICT(code) DO UPDATE SET
                 name = excluded.name,
                 schrift = excluded.schrift,
                 stimme = excluded.stimme""",
            (code, p["name"], p["schrift"], p.get("stimme")),
        )


def sprachprofile_laden(db: sqlite3.Connection) -> None:
    """Lädt die Profilüberschreibungen aus der Datenbank in sprachen.py.

    Wird bei jeder Anfrage aufgerufen. Das ist ein winziges SELECT über eine
    Handvoll Zeilen und dafür immer aktuell — anders als ein Zwischenspeicher,
    der veraltet, sobald ein Agent am MCP ein Profil ändert.
    """
    eintraege = {}
    for z in db.execute("SELECT code, profil FROM sprache"):
        eigen = j_lesen(z["profil"])
        if eigen:
            eintraege[z["code"]] = eigen
    sprachen.uebernehmen(eintraege)


def profil_fuer(db: sqlite3.Connection, code: str) -> dict:
    """Sprachprofil für die Antwortprüfung.

    Aus dem Code, bei selbst angelegten Sprachen aus der Tabelle. Einträge in
    der Tabelle überschreiben einzelne Teile des Codeprofils — so lassen sich
    etwa die Akzentregeln für eine Sprache nachjustieren, ohne Codeänderung.
    """
    sprachprofile_laden(db)
    grund = dict(sprachen.profil(code))
    zeile = db.execute("SELECT name, schrift, stimme FROM sprache WHERE code = ?",
                       (code,)).fetchone()
    if zeile is not None:
        grund["name"] = zeile["name"]
        grund["schrift"] = zeile["schrift"]
        grund["stimme"] = zeile["stimme"]
    return grund


# ------------------------------------------------------------------- Hilfen

def zeile(db: sqlite3.Connection, sql: str, werte: Iterable = ()) -> dict | None:
    z = db.execute(sql, tuple(werte)).fetchone()
    return dict(z) if z else None


def zeilen(db: sqlite3.Connection, sql: str, werte: Iterable = ()) -> list[dict]:
    return [dict(z) for z in db.execute(sql, tuple(werte)).fetchall()]


def wert(db: sqlite3.Connection, sql: str, werte: Iterable = ()) -> Any:
    z = db.execute(sql, tuple(werte)).fetchone()
    return z[0] if z else None


def j_lesen(text: str | None, standard: Any = None) -> Any:
    if not text:
        return {} if standard is None else standard
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {} if standard is None else standard


def j_schreiben(daten: Any) -> str:
    return json.dumps(daten, sort_keys=True, ensure_ascii=False)
