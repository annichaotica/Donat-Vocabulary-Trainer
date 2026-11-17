"""Zuspruch — jemandem, der lernt, etwas schicken.

»Auch möchte ich meiner Tochter Boosts schicken können zur
Motivation.«

Das Gegenstück zu `spiel`: dort wird alles aus dem Protokoll
gerechnet, hier steht das Einzige, was sich nirgends herleiten lässt,
weil es von einem Menschen kommt.

DREI ENTSCHEIDUNGEN, die den Zuschnitt bestimmen:

**Der Zuspruch ändert das Protokoll nicht.** Ein geschenkter
Verdoppler schreibt keine Punkte gut — er sagt nur, dass ein
bestimmter Tag doppelt gezählt wird. Ein geschenkter Joker schreibt
keinen Lerntag — er hebt die Zahl der Fehltage, die eine Strähne
trägt. Beides wird beim Auswerten angewandt, nicht beim Schreiben.
Sonst gäbe es zwei Wahrheiten über denselben Tag, und bei einem
Abbruch mitten im Vorgang wäre die falsche die haltbarere.

**Das Versprechen ist das Wichtigste und das Dümmste.** Die App
rechnet daran nichts aus und schenkt nichts; sie merkt sich einen Satz
(»Lernziel bis Freitag → Kino«) und sagt hinterher, dass er fällig
ist. Die Belohnung kommt nicht aus der App, und genau darum wirkt sie:
keine Punktzahl schlägt eine Mutter, die etwas eingelöst hat.

**Schicken darf nicht jeder an jeden.** Wer keine Sammlung mit jemandem
teilt, hat in dessen Trainer nichts zu melden. Und höchstens ein paar
am Tag: aus Zuspruch, der im Dutzend kommt, wird Hintergrundrauschen.
"""

from __future__ import annotations

import datetime as dt
import sqlite3

import datenbank as dbm
from zugang import NichtErlaubt


ARTEN = ("botschaft", "verdoppler", "joker", "versprechen")

# Wie viele ein Mensch am Tag an EINE Person schicken darf. Nicht als
# Schutz vor Angriffen gedacht — es ist die eigene Familie —, sondern
# gegen die gut gemeinte Flut. Ein Zuspruch wirkt, wenn er selten ist.
HOECHSTENS_JE_TAG = 5

# Wie lange einer stehen bleibt, wenn nichts anderes gesagt ist.
# Ein Versprechen bekommt keine Frist von selbst: es gilt bis zum
# Termin seines Lernziels oder bis es jemand abhakt.
GUELTIG_TAGE = {"botschaft": 7, "verdoppler": 30, "joker": 31,
                "versprechen": None}

HOECHSTLAENGE = 400


def _heute() -> dt.date:
    import lernen
    return lernen.heute()


def _jetzt() -> str:
    # Über `lernen`, damit eine in Tests vorgestellte Uhr auch hier gilt.
    import lernen
    return lernen._jetzt()


# ------------------------------------------------------------ Wer darf

def empfaenger(db: sqlite3.Connection, benutzer_id: int) -> list[dict]:
    """Wem diese Person Zuspruch schicken darf.

    Alle, mit denen sie eine Sammlung teilt — in welche Richtung die
    Freigabe läuft, ist gleich: wer gemeinsam an einem Wortschatz
    arbeitet, darf sich auch anfeuern. Verwalter dürfen an alle.

    Sich selbst nicht. Ein Versprechen an sich selbst ist ein Vorsatz,
    und dafür gibt es Lernziele.
    """
    ich = dbm.zeile(db, "SELECT * FROM benutzer WHERE id = ?", (benutzer_id,))
    if ich is None:
        raise KeyError(f"Benutzer {benutzer_id} gibt es nicht")
    if ich["verwalter"]:
        return [dict(z) for z in dbm.zeilen(db, """
            SELECT id, name, farbe FROM benutzer WHERE id != ? ORDER BY name""",
            (benutzer_id,))]
    return [dict(z) for z in dbm.zeilen(db, """
        SELECT DISTINCT b.id, b.name, b.farbe
          FROM benutzer b
         WHERE b.id != ?1
           AND (EXISTS (SELECT 1 FROM sammlung s
                          JOIN freigabe f ON f.sammlung_id = s.id
                         WHERE s.besitzer_id = ?1 AND f.benutzer_id = b.id)
             OR EXISTS (SELECT 1 FROM sammlung s
                          JOIN freigabe f ON f.sammlung_id = s.id
                         WHERE s.besitzer_id = b.id AND f.benutzer_id = ?1))
         ORDER BY b.name""", (benutzer_id,))]


def _pruefen(db: sqlite3.Connection, von_id: int, an_id: int) -> None:
    if not any(e["id"] == an_id for e in empfaenger(db, von_id)):
        raise NichtErlaubt(
            "Zuspruch geht nur an Leute, mit denen du eine Sammlung teilst.")
    heute = _heute().isoformat()
    schon = dbm.wert(db, """
        SELECT COUNT(*) FROM zuspruch
         WHERE von_id = ? AND an_id = ? AND substr(angelegt, 1, 10) = ?""",
        (von_id, an_id, heute)) or 0
    if schon >= HOECHSTENS_JE_TAG:
        raise NichtErlaubt(
            f"Heute schon {schon} verschickt — mehr als {HOECHSTENS_JE_TAG} "
            "am Tag sind keine Ermutigung mehr.")


# ------------------------------------------------------------ Schicken

def schicken(db: sqlite3.Connection, von_id: int, an_id: int, art: str,
             text: str | None = None, belohnung: str | None = None,
             lernziel_id: int | None = None,
             gueltig_tage: int | None = None) -> dict:
    """Einen Zuspruch abschicken."""
    if art not in ARTEN:
        raise ValueError(f"Art muss eins von {', '.join(ARTEN)} sein")
    _pruefen(db, von_id, an_id)

    text = (text or "").strip() or None
    belohnung = (belohnung or "").strip() or None
    for feld, wert in (("text", text), ("belohnung", belohnung)):
        if wert and len(wert) > HOECHSTLAENGE:
            raise ValueError(f"{feld} ist zu lang (höchstens "
                             f"{HOECHSTLAENGE} Zeichen)")
    if art == "botschaft" and not text:
        raise ValueError("Eine Botschaft ohne Text ist keine")
    if art == "versprechen" and not belohnung:
        raise ValueError("Ein Versprechen ohne Belohnung ist keines")

    # Das Lernziel wird als TEXT mitgenommen, nicht nur als Verweis.
    # Wird es gelöscht, soll das Versprechen lesbar bleiben.
    ziel_text = None
    frist = None
    if lernziel_id is not None:
        z = dbm.zeile(db, "SELECT * FROM lernziel WHERE id = ?", (lernziel_id,))
        if z is None:
            raise KeyError(f"Lernziel {lernziel_id} gibt es nicht")
        if z["benutzer_id"] != an_id:
            raise NichtErlaubt(
                "Das Lernziel gehört nicht der Person, die den Zuspruch "
                "bekommt.")
        ziel_text = z["name"]
        frist = z["termin"]

    if gueltig_tage is None:
        tage = GUELTIG_TAGE[art]
        if tage is not None:
            frist = (_heute() + dt.timedelta(days=tage)).isoformat()
    else:
        frist = (_heute() + dt.timedelta(days=gueltig_tage)).isoformat()

    cur = db.execute("""INSERT INTO zuspruch
                          (von_id, an_id, art, text, belohnung, ziel_text,
                           lernziel_id, gueltig_bis)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                     (von_id, an_id, art, text, belohnung, ziel_text,
                      lernziel_id, frist))
    return lesen(db, cur.lastrowid)


def lesen(db: sqlite3.Connection, zuspruch_id: int) -> dict:
    z = dbm.zeile(db, """
        SELECT z.*, v.name AS von_name, v.farbe AS von_farbe,
               a.name AS an_name
          FROM zuspruch z
          JOIN benutzer v ON v.id = z.von_id
          JOIN benutzer a ON a.id = z.an_id
         WHERE z.id = ?""", (zuspruch_id,))
    if z is None:
        raise KeyError(f"Zuspruch {zuspruch_id} gibt es nicht")
    return dict(z)


# ------------------------------------------------------------- Ansehen

def _offen_bedingung() -> str:
    """Was noch zählt: nicht abgehakt und nicht abgelaufen.

    Die Bedingung gehört in die Abfrage und nicht hinterher in eine
    Schleife — dieselbe Lehre wie an einem halben Dutzend anderer
    Stellen in diesem Projekt.
    """
    return ("z.erledigt IS NULL"
            " AND (z.gueltig_bis IS NULL OR z.gueltig_bis >= ?)")


def fuer_mich(db: sqlite3.Connection, benutzer_id: int,
              alle: bool = False) -> list[dict]:
    """Was mir geschickt wurde und noch gilt."""
    heute = _heute().isoformat()
    bedingung = "z.an_id = ?" if alle else f"z.an_id = ? AND {_offen_bedingung()}"
    werte = (benutzer_id,) if alle else (benutzer_id, heute)
    return [dict(z) for z in dbm.zeilen(db, f"""
        SELECT z.*, v.name AS von_name, v.farbe AS von_farbe
          FROM zuspruch z JOIN benutzer v ON v.id = z.von_id
         WHERE {bedingung}
         ORDER BY z.angelegt DESC""", werte)]


def von_mir(db: sqlite3.Connection, benutzer_id: int) -> list[dict]:
    """Was ich verschickt habe — und was daraus geworden ist."""
    return [dict(z) for z in dbm.zeilen(db, """
        SELECT z.*, a.name AS an_name
          FROM zuspruch z JOIN benutzer a ON a.id = z.an_id
         WHERE z.von_id = ?
         ORDER BY z.angelegt DESC LIMIT 50""", (benutzer_id,))]


# ------------------------------------------------------------- Anfassen

def _meiner(db: sqlite3.Connection, zuspruch_id: int, benutzer_id: int,
            als: str) -> dict:
    z = lesen(db, zuspruch_id)
    if z["an_id" if als == "empfaenger" else "von_id"] != benutzer_id:
        raise NichtErlaubt("Das ist nicht dein Zuspruch.")
    return z


def gesehen(db: sqlite3.Connection, zuspruch_id: int,
            benutzer_id: int) -> dict:
    """Zur Kenntnis genommen. Botschaften verschwinden danach."""
    _meiner(db, zuspruch_id, benutzer_id, "empfaenger")
    db.execute("UPDATE zuspruch SET gesehen = COALESCE(gesehen, ?) "
               "WHERE id = ?", (_jetzt(), zuspruch_id))
    # Eine Botschaft ist mit dem Lesen erledigt — sie will nicht
    # abgearbeitet werden, sie will gelesen werden.
    db.execute("UPDATE zuspruch SET erledigt = ? "
               "WHERE id = ? AND art = 'botschaft'",
               (_jetzt(), zuspruch_id))
    return lesen(db, zuspruch_id)


def einloesen(db: sqlite3.Connection, zuspruch_id: int,
              benutzer_id: int) -> dict:
    """Jetzt soll er wirken.

    Beim Verdoppler ist das eine echte Entscheidung: er gilt für DIESEN
    Tag. Wer ihn für einen großen Tag aufhebt, hat mehr davon — und
    deshalb löst ihn der Empfänger ein und nicht die App.
    """
    z = _meiner(db, zuspruch_id, benutzer_id, "empfaenger")
    if z["art"] != "verdoppler":
        raise ValueError("Nur ein Verdoppler wird eingelöst.")
    if z["eingeloest"]:
        raise ValueError("Der läuft schon.")
    db.execute("UPDATE zuspruch SET eingeloest = ?, gesehen = COALESCE(gesehen, ?) "
               "WHERE id = ?",
               (_heute().isoformat(), _jetzt(), zuspruch_id))
    return lesen(db, zuspruch_id)


def erledigen(db: sqlite3.Connection, zuspruch_id: int,
              benutzer_id: int) -> dict:
    """Abgehakt — eingelöst, abgegolten, vorbei.

    Beim Versprechen darf das NUR die Person, die es gegeben hat. Wer
    sich selbst bescheinigen könnte, das Kino sei abgegolten, bräuchte
    kein Versprechen.
    """
    z = lesen(db, zuspruch_id)
    if z["art"] == "versprechen":
        if z["von_id"] != benutzer_id:
            raise NichtErlaubt(
                "Ein Versprechen hakt ab, wer es gegeben hat.")
    elif benutzer_id not in (z["an_id"], z["von_id"]):
        raise NichtErlaubt("Das ist nicht dein Zuspruch.")
    db.execute("UPDATE zuspruch SET erledigt = COALESCE(erledigt, ?) "
               "WHERE id = ?", (_jetzt(), zuspruch_id))
    return lesen(db, zuspruch_id)


def zuruecknehmen(db: sqlite3.Connection, zuspruch_id: int,
                  benutzer_id: int) -> None:
    """Weg damit — nur, solange er nicht gesehen wurde.

    Danach nicht mehr: was jemand gelesen hat, kann man ihm nicht
    wieder wegnehmen, und ein Versprechen schon gar nicht.
    """
    z = _meiner(db, zuspruch_id, benutzer_id, "sender")
    if z["gesehen"]:
        raise NichtErlaubt(
            "Schon gelesen — das lässt sich nicht mehr zurücknehmen.")
    db.execute("DELETE FROM zuspruch WHERE id = ?", (zuspruch_id,))


# ------------------------------------------------- Wirkung auf das Spiel

def verdopplungstage(db: sqlite3.Connection, benutzer_id: int) -> set[str]:
    """Tage, an denen ein eingelöster Verdoppler lief."""
    return {z["eingeloest"] for z in dbm.zeilen(db, """
        SELECT eingeloest FROM zuspruch
         WHERE an_id = ? AND art = 'verdoppler' AND eingeloest IS NOT NULL""",
        (benutzer_id,))}


def geschenkte_joker(db: sqlite3.Connection,
                     benutzer_id: int) -> dict[str, int]:
    """Zusätzliche Fehltage je Kalendermonat.

    Ein geschenkter Joker gilt für den Monat, in dem er geschickt
    wurde. Nicht »bis er gebraucht wird«: ein Vorrat, der sich
    anhäuft, hebelt die Regel aus, und dann trägt die Strähne
    irgendwann alles.
    """
    je_monat: dict[str, int] = {}
    for z in dbm.zeilen(db, """
            SELECT substr(angelegt, 1, 7) AS monat, COUNT(*) AS n
              FROM zuspruch
             WHERE an_id = ? AND art = 'joker'
             GROUP BY monat""", (benutzer_id,)):
        je_monat[z["monat"]] = z["n"]
    return je_monat
