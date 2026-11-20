# Vokabeltrainer — Copyright (C) 2026 Annuschka Brenner
#
# Freie Software unter der GNU Affero General Public License, Fassung 3
# oder später. Herausgegeben in der Hoffnung, dass sie nützt, aber OHNE
# JEDE GEWÄHRLEISTUNG. Siehe die Datei LICENSE.
"""Beispielbestand beim ersten Start — wenn man ihn ausdrücklich will.

Wer das Programm zum Ansehen startet, steht sonst vor einer leeren
Datenbank: kein Profil, keine Sammlung, nichts zu klicken. Das ist der
richtige Zustand für einen Betrieb und der falsche für einen Blick.

    BEISPIELDATEN=1

legt beim Start einen Beispielbestand an — aber NUR, wenn die Datenbank
leer ist. Das ist die ganze Vorsicht, die es braucht: ein laufender
Bestand wird nie angefasst, auch wenn die Variable versehentlich
stehenbleibt. Und es ist keine Rückfrage nötig, auf die beim
Containerstart ohnehin niemand antworten könnte.

Was entsteht und warum genau das — der Bestand soll die Stärken zeigen,
nicht die Menge:

    ein Profil             sonst landet man auf der Profilauswahl
    der Übungskurs         20 Wörter, fünf Lektionen, vollständige
                           Paradigmen (Präsens, Simple past, Plural,
                           Steigerung) — daran hängen Formaufgaben,
                           ganze Reihen und die Lektionsschranke
    ein Lesetext           jedes Wort darin steht im Kurs, also zeigt
                           die Deckung 100 % und die Einfärbung wirkt
    zwei Sätze             für den Übungsweg
    eine Grammatikregel    für »Warum ist das so?«
    ungeprüfte Einträge    als »von der KI« angelegt, damit die
                           Freigabe etwas zu zeigen hat
    ein Lernziel           mit Termin in einer Woche, damit der
                           Terminstreifen und die Tagesrechnung
                           etwas zu rechnen haben

Der Kurs selbst steht in `beispielkurs.py`; hier steht nur, WANN er
angelegt wird und was noch dazugehört.
"""

from __future__ import annotations

import datetime as dt
import logging
import os
import sqlite3

import beispielkurs
import datenbank as dbm
import lernziele

LOG = logging.getLogger("vokabeltrainer.beispieldaten")

# Was als »ja« gilt. Absichtlich großzügig: wer BEISPIELDATEN=true
# schreibt, meint dasselbe wie BEISPIELDATEN=1.
JA = {"1", "true", "yes", "ja", "on"}

PROFIL_VORGABE = "Zum Ausprobieren"
ZIEL_NAME = "Lektion 1 und 2 bis nächste Woche"
ZIEL_TAGE = 7


def gewuenscht() -> bool:
    return os.environ.get("BEISPIELDATEN", "").strip().lower() in JA


def _ist_leer(db: sqlite3.Connection) -> bool:
    """Leer heißt: noch kein Profil.

    Nicht »keine Tabellen« — die legt `einrichten` ja gerade an — und
    nicht »keine Wörter«: ein Profil ohne Sammlung ist schon ein
    angefangener Betrieb, und in den gehört nichts hineingeschüttet.
    """
    return dbm.wert(db, "SELECT COUNT(*) FROM benutzer") == 0


def vielleicht_befuellen(db: sqlite3.Connection) -> dict | None:
    """Beim Start aufgerufen. Gibt zurück, was angelegt wurde — oder None."""
    if not gewuenscht():
        return None
    if not _ist_leer(db):
        LOG.info("BEISPIELDATEN gesetzt, aber es gibt schon ein Profil — "
                 "nichts angelegt.")
        return None

    name = os.environ.get("BEISPIELDATEN_PROFIL", "").strip() or PROFIL_VORGABE
    cur = db.execute("INSERT INTO benutzer (name, farbe) VALUES (?, ?)",
                     (name, "#6b7fd7"))
    benutzer_id = cur.lastrowid

    kurs = beispielkurs.anlegen(db, benutzer_id)

    # Ein Lernziel mit Termin — ohne eines bleibt der Terminstreifen auf
    # der Übersicht leer, und gerade der ist neu.
    #
    # Umfang: die beiden ersten Lektionen. Nicht alles, denn ein Ziel,
    # das den ganzen Bestand umfasst, ist keines; und nicht eine
    # einzelne, denn dann rechnet die Tagesverteilung nichts aus.
    lektionen = [z["id"] for z in dbm.zeilen(
        db, """SELECT id FROM lektion WHERE sammlung_id = ?
                ORDER BY nr LIMIT 2""", (kurs["sammlung_id"],))]
    ziel = lernziele.anlegen(
        db, benutzer_id, ZIEL_NAME,
        {"sammlungen": [kurs["sammlung_id"]], "lektionen": lektionen},
        termin=(dt.date.today() + dt.timedelta(days=ZIEL_TAGE)).isoformat(),
        ziel="einmal_richtig",
        notiz="Beispielziel — zum Ansehen des Terminstreifens.")
    db.commit()

    bericht = {"profil": name, "benutzer_id": benutzer_id,
               "sammlung": kurs["name"], "woerter": kurs["woerter"],
               "ungeprueft": kurs["ungeprueft"], "lernziel": ziel["name"]}
    LOG.info("Beispielbestand angelegt: Profil %r, %d Wörter, "
             "%d warten auf Freigabe, Lernziel %r.",
             name, kurs["woerter"], kurs["ungeprueft"], ziel["name"])
    return bericht
