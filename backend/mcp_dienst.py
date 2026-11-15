"""MCP über HTTP — für Konnektoren in der Claude-App.

Ein Konnektor in claude.ai verlangt HTTPS auf Port 443 und kann feste
Kopfzeilen mitschicken. OAuth ist nicht nötig. Darum hier der
Streamable-HTTP-Transport unter /mcp, abgesichert über eine Kopfzeile.

**Es gibt nur diese eine Umsetzung.** Der stdio-Server unter mcp/ ist seit
dem Umbau eine dünne Brücke, die hierher weiterreicht — sonst müsste jede
neue Fähigkeit zweimal geschrieben und zweimal geprüft werden.

Die Werkzeuge rufen die Routenfunktionen aus app.py unmittelbar auf, nicht
über HTTP. Damit läuft die MCP-Schnittstelle durch dieselbe Prüfung und
dieselbe Geschäftslogik wie die Oberfläche — es gibt keinen zweiten Weg in
die Daten, der anders prüfen könnte.

**Jede Anfrage gehört zu einer Person.** Das Token ist an ein Profil
gebunden; alles, was über dieses Token geschieht, geschieht in deren Namen
und nur auf deren Bestand. Ein gemeinsames Geheimnis wäre hier falsch: man
könnte nicht sagen, wer etwas eingetragen hat, und es niemandem einzeln
entziehen.
"""

from __future__ import annotations

import sqlite3
from typing import Any, Callable

from fastapi import HTTPException

import logging

import datenbank as dbm
import lehrgang
import lesetexte
import zugang

VERSION = "0.2.0"
NAME = "vokabeltrainer"
PROTOKOLL = "2025-06-18"

ANLEITUNG = (
    "Vokabeltrainer im Heimnetz. Reihenfolge: sammlungen_auflisten, dann "
    "formgruppen_zeigen für die Sprache, dann eintragen. Vollständige "
    "Paradigmen liefern — der Trainer erzeugt daraus die Aufgaben und leitet "
    "den Wortstamm ab. Eingetragene Formen bleiben ungeprüft, bis ein Mensch "
    "sie freigibt — das geschieht in der Oberfläche unter "
    "»Freigabe«, nicht über diese Schnittstelle.\n\n"
    "Für Übungssätze und Texte: zuerst text_pruefen, damit der Text zur "
    "Stufe passt, dann uebungen_importieren. Fremde Texte werden verlinkt, "
    "nicht abgeschrieben."
)


class WerkzeugFehler(Exception):
    """Ein Werkzeug konnte nicht ausgeführt werden. Der Text geht an den
    Agenten zurück und soll ihm sagen, was zu tun ist."""


def _app():
    """Späte Einbindung, sonst gäbe es einen Ringschluss: app.py bindet
    dieses Modul ein, um die Route zu melden."""
    import app
    return app


def _fehler_wandeln(aufruf: Callable, *args, **kw):
    try:
        return aufruf(*args, **kw)
    except HTTPException as f:
        raise WerkzeugFehler(f"{f.status_code}: {f.detail}") from f
    except KeyError as f:
        raise WerkzeugFehler(str(f)) from f
    except ValueError as f:
        raise WerkzeugFehler(str(f)) from f


# ------------------------------------------------------------- Werkzeuge

def sammlungen_auflisten(db: sqlite3.Connection, person: dict):
    """Nur die eigenen und die freigegebenen Sammlungen — nicht fremde."""
    a = _app()
    return {
        "ich": {"id": person["id"], "name": person["name"],
                "verwalter": bool(person.get("verwalter"))},
        # Mit Namen, nicht nach Stellung: die Route hat einen Request-
        # Parameter, den nur FastAPI füllt, und der steht vorn.
        "sammlungen": _fehler_wandeln(a.sammlungen_liste, request=None,
                                      benutzer_id=person["id"], db=db),
        "hinweis": "Es werden nur Sammlungen gezeigt, die dir gehören oder "
                   "dir freigegeben sind. Alles Eintragen geschieht in "
                   "deinem Namen.",
    }


def formgruppen_zeigen(db: sqlite3.Connection, person: dict, sprache: str):
    a = _app()
    gruppen = _fehler_wandeln(a.formgruppen_liste, sprache)
    ausfuehrlich = {}
    for wortart, liste in gruppen["wortarten"].items():
        ausfuehrlich[wortart] = []
        for g in liste:
            zellen = _fehler_wandeln(a.formgruppe_zellen, sprache, g["kennung"])
            ausfuehrlich[wortart].append({
                "kennung": g["kennung"], "name": g["name"],
                "voreingestellt": g["kennung"] in gruppen["standard"],
                "zellen": [{"merkmale": z["merkmale"],
                            "beschriftung": z["beschriftung"]} for z in zellen],
            })
    return {"sprache": gruppen["sprache"], "stammformen": gruppen["stammformen"],
            "lexemmerkmale": gruppen["lexemmerkmale"], "wortarten": ausfuehrlich,
            "hinweis": "Jede Form braucht das Merkmalsbündel ihrer Zelle, genau "
                       "so wie es hier steht. Nicht voreingestellte Formgruppen "
                       "dürfen trotzdem befüllt werden — sie lassen sich später "
                       "zuschalten. Hat ein Wort eine ganze Gruppe nicht, gehört "
                       "das in die Lexemmerkmale (griechische Deponentien: "
                       "diathese = deponens) oder in luecken — nicht "
                       "unausgesprochen bleiben."}


def merkmale_zeigen(db: sqlite3.Connection, person: dict):
    return _fehler_wandeln(_app().merkmale_inventar)


def _bericht_kurz(bericht: dict) -> dict:
    return {
        "brauchbar": bericht["gut"],
        "aufgaben_entstanden": bericht["aufgaben_aktiv"],
        "ungepruefte_formen": bericht["ungeprueft"],
        "befunde": [{"schwere": b["schwere"], "art": b["art"], "text": b["text"],
                     **({"betrifft": b["betrifft"]} if b["betrifft"] else {}),
                     **({"rat": b["rat"]} if b["rat"] else {})}
                    for b in bericht["befunde"]],
    }


def vokabel_anlegen(db: sqlite3.Connection, person: dict, sammlung_id: int,
                    lemma: str, wortart: str, bedeutungen: list,
                    formen: list | None = None, merkmale: dict | None = None,
                    notiz: str | None = None, als_geprueft: bool = False):
    from modelle import LexemEingabe
    a = _app()
    zugang.sammlung_pruefen(db, person["id"], sammlung_id, schreiben=True)
    sauber_formen = []
    for f in list(formen or []):
        sauber_formen.append({**f, "quelle": f.get("quelle", "ki"),
                              "geprueft": f.get("geprueft", als_geprueft)})
    sauber_bedeutungen = []
    for b in bedeutungen:
        ue = b.get("uebersetzungen") or []
        sauber_bedeutungen.append({
            "uebersetzungen": [{"text": u, "quelle": "ki"} if isinstance(u, str)
                               else {**u, "quelle": u.get("quelle", "ki")}
                               for u in ue],
            "kontext": b.get("kontext"), "reihenfolge": b.get("reihenfolge", 0)})
    try:
        eingabe = LexemEingabe(sammlung_id=sammlung_id, lemma=lemma,
                               wortart=wortart, merkmale=merkmale or {},
                               notiz=notiz, formen=sauber_formen,
                               bedeutungen=sauber_bedeutungen)
    except Exception as f:
        raise WerkzeugFehler(f"Eingabe nicht gültig: {f}") from f
    lexem = _fehler_wandeln(a.lexem_anlegen, eingabe, None, db)
    bericht = _fehler_wandeln(a.lexem_pruefen, lexem["id"], db)
    return {
        "lexem_id": lexem["id"], "lemma": lexem["lemma"],
        "formen_angelegt": len(lexem["formen"]),
        "pruefung": _bericht_kurz(bericht),
        "hinweis": ("Die Formen sind als ungeprüft eingetragen und werden noch "
                    "nicht abgefragt. Das ist Absicht: eine erfundene Form, die "
                    "unbemerkt gepaukt wird, ist schlimmer als eine fehlende. "
                    "Die Freigabe geschieht in der Oberfläche, unter "
                    "»Freigabe« bei der Sammlung.") if not als_geprueft else None,
    }


def vokabeln_importieren(db: sqlite3.Connection, person: dict, sammlung_id: int,
                         eintraege: list, nur_pruefen: bool = False):
    """Viele Wörter in einem Aufruf — mit Probelauf und wiederholbar."""
    import sammelimport
    zugang.sammlung_pruefen(db, person["id"], sammlung_id, schreiben=True)
    try:
        return sammelimport.importieren(db, sammlung_id, eintraege, nur_pruefen)
    except Exception as f:
        raise WerkzeugFehler(str(f)) from f


# ------------------------------------------------------------- Pflege

def sammlung_anlegen(db: sqlite3.Connection, person: dict, name: str,
                     sprache: str, grundsprache: str = "de",
                     beschreibung: str | None = None):
    """Eine neue Sammlung — sie gehört der sprechenden Person."""
    from modelle import SammlungAnlegen
    ergebnis = _fehler_wandeln(
        _app().sammlung_anlegen,
        SammlungAnlegen(besitzer_id=person["id"], name=name, sprache=sprache,
                        grundsprache=grundsprache, beschreibung=beschreibung),
        None, db)
    return {"sammlung_id": ergebnis["id"], "name": ergebnis["name"],
            "sprache": ergebnis["sprache"],
            "grundsprache": ergebnis["grundsprache"],
            "hinweis": "Die Sammlung gehört dir. Als Nächstes "
                       "formgruppen_zeigen für diese Sprache."}


def vokabeln_auflisten(db: sqlite3.Connection, person: dict, sammlung_id: int,
                       lektion_nr: int | None = None,
                       wortart: str | None = None,
                       suche: str | None = None,
                       nur_ungepruefte: bool = False,
                       seite: int = 1, anzahl: int = 50):
    """Was steht schon im Bestand? Vor dem Berichtigen und vor dem Anlegen."""
    zugang.sammlung_pruefen(db, person["id"], sammlung_id)
    anzahl = max(1, min(int(anzahl), 200))
    ab = max(0, (max(1, int(seite)) - 1) * anzahl)
    ergebnis = _fehler_wandeln(_app().lexeme_liste, sammlung_id, suche, None,
                               lektion_nr, wortart, nur_ungepruefte, ab,
                               anzahl, db)
    return {
        "gesamt": ergebnis["gesamt"], "seite": max(1, int(seite)),
        "anzahl": ergebnis["anzahl"],
        "vokabeln": [{"lexem_id": z["id"], "lemma": z["lemma"],
                      "wortart": z["wortart"], "merkmale": z["merkmale"],
                      "bedeutung": z["erste_bedeutung"],
                      "formen": z["formen_anzahl"],
                      "ungeprueft": z["ungeprueft_anzahl"],
                      "aufgaben": z["aufgaben_anzahl"],
                      "kennung": z["kennung"],
                      "reihenfolge": z["reihenfolge"]}
                     for z in ergebnis["lexeme"]],
    }


def vokabel_aendern(db: sqlite3.Connection, person: dict, lexem_id: int,
                    lektion_nr: int | None = None, **aenderung):
    """Ein Wort berichtigen. Nur das Genannte ändert sich."""
    import sammelimport
    from modelle import LexemAendern
    zugang.lexem_pruefen(db, person["id"], lexem_id, schreiben=True)
    lexem = dbm.zeile(db, "SELECT * FROM lexem WHERE id = ?", (lexem_id,))
    if lektion_nr is not None:
        aenderung["lektion_id"] = sammelimport.lektion_sichern(
            db, lexem["sammlung_id"], lektion_nr)
    if not aenderung:
        raise WerkzeugFehler("Nichts zu ändern angegeben")
    try:
        eingabe = LexemAendern(**aenderung)
    except Exception as f:
        raise WerkzeugFehler(f"Unbrauchbare Angaben: {f}") from f
    ergebnis = _fehler_wandeln(_app().lexem_aendern, lexem_id, eingabe, db)
    return {"lexem_id": ergebnis["id"], "lemma": ergebnis["lemma"],
            "wortart": ergebnis["wortart"], "merkmale": ergebnis["merkmale"],
            "bedeutungen": [[u["text"] for u in b["uebersetzungen"]]
                            for b in ergebnis["bedeutungen"]],
            "formen": len(ergebnis["formen"])}


def form_aendern(db: sqlite3.Connection, person: dict, form_id: int,
                 **aenderung):
    """Eine Form berichtigen. Geänderter Inhalt fällt auf ungeprüft zurück."""
    from modelle import FormAendern
    zugang.form_pruefen(db, person["id"], form_id, schreiben=True)
    if not aenderung:
        raise WerkzeugFehler("Nichts zu ändern angegeben")
    # Die Freigabe ist dem Agenten nicht zugänglich: sie gehört dem
    # Menschen, und eine geänderte Form ist nicht mehr die freigegebene.
    aenderung.pop("geprueft", None)
    try:
        eingabe = FormAendern(**aenderung)
    except Exception as f:
        raise WerkzeugFehler(f"Unbrauchbare Angaben: {f}") from f
    ergebnis = _fehler_wandeln(_app().form_teil_aendern, form_id, eingabe, db)
    return {"form_id": ergebnis["id"], "text": ergebnis["text"],
            "merkmale": dbm.j_lesen(ergebnis["merkmale"]),
            "geprueft": bool(ergebnis["geprueft"]),
            "hinweis": None if ergebnis["geprueft"] else
                       "Die Form ist jetzt ungeprüft und wird erst nach "
                       "Freigabe durch einen Menschen abgefragt."}


def form_loeschen(db: sqlite3.Connection, person: dict, form_id: int,
                  text: str):
    """Eine Form entfernen. `text` muss die vorhandene Form nennen.

    Die Bestätigung ist kein Formalismus: an einer Form hängt ein
    Lernstand, und eine verwechselte Kennung löschte stillschweigend die
    falsche.
    """
    zugang.form_pruefen(db, person["id"], form_id, schreiben=True)
    f = dbm.zeile(db, "SELECT * FROM form WHERE id = ?", (form_id,))
    if f is None:
        raise WerkzeugFehler(f"Form {form_id} gibt es nicht")
    if (text or "").strip() != f["text"]:
        raise WerkzeugFehler(
            f"Form {form_id} lautet {f['text']!r}, nicht {text!r}. "
            f"Zum Löschen muss der vorhandene Text genannt werden.")
    _fehler_wandeln(_app().form_loeschen, form_id, db)
    return {"geloescht": f["text"], "lexem_id": f["lexem_id"]}


def vokabel_loeschen(db: sqlite3.Connection, person: dict, lexem_id: int,
                     lemma: str):
    """Ein ganzes Wort entfernen. `lemma` muss das vorhandene nennen.

    Mit dem Wort gehen seine Formen, Bedeutungen und der Lernstand dazu.
    Darum die Bestätigung — und darum sagt die Antwort, was dabei
    verlorenging.
    """
    zugang.lexem_pruefen(db, person["id"], lexem_id, schreiben=True)
    lexem = dbm.zeile(db, "SELECT * FROM lexem WHERE id = ?", (lexem_id,))
    if lexem is None:
        raise WerkzeugFehler(f"Wort {lexem_id} gibt es nicht")
    if (lemma or "").strip() != lexem["lemma"]:
        raise WerkzeugFehler(
            f"Wort {lexem_id} lautet {lexem['lemma']!r}, nicht {lemma!r}. "
            f"Zum Löschen muss das vorhandene Lemma genannt werden.")
    bestand = {
        "formen": dbm.wert(db, "SELECT COUNT(*) FROM form WHERE lexem_id = ?",
                           (lexem_id,)),
        "aufgaben": dbm.wert(db, "SELECT COUNT(*) FROM aufgabe WHERE lexem_id = ?",
                             (lexem_id,)),
        "wiederholungen": dbm.wert(db, """SELECT COUNT(*) FROM wiederholung w
                                            JOIN aufgabe a ON a.id = w.aufgabe_id
                                           WHERE a.lexem_id = ?""", (lexem_id,)),
    }
    _fehler_wandeln(_app().lexem_loeschen, lexem_id, db)
    return {"geloescht": lexem["lemma"], **bestand,
            "hinweis": (f"Mit dem Wort sind {bestand['wiederholungen']} "
                        f"Wiederholungen verlorengegangen."
                        if bestand["wiederholungen"] else None)}


def lernstand_lesen(db: sqlite3.Connection, person: dict, sammlung_id: int,
                    anzahl: int = 40):
    """Was sitzt, und woran hakt es — für diese Person."""
    zugang.sammlung_pruefen(db, person["id"], sammlung_id)
    return _fehler_wandeln(_app().lernstand_lesen, sammlung_id, person["id"],
                           max(1, min(int(anzahl), 200)), db)


# ----------------------------------------------------- Grammatikregeln

def regel_anlegen(db: sqlite3.Connection, person: dict, sammlung_id: int,
                  titel: str, text: str, muster: dict | None = None,
                  beispiele: list | None = None, kennung: str | None = None,
                  reihenfolge: int = 0):
    """Eine Grammatikregel anlegen oder berichtigen."""
    import regeln
    zugang.sammlung_pruefen(db, person["id"], sammlung_id, schreiben=True)
    sammlung = dbm.zeile(db, "SELECT sprache FROM sammlung WHERE id = ?",
                         (sammlung_id,))
    if sammlung is None:
        raise WerkzeugFehler(f"Sammlung {sammlung_id} gibt es nicht")
    try:
        r = regeln.anlegen(db, sammlung_id, titel, text, sammlung["sprache"],
                           muster, beispiele, kennung, quelle="ki",
                           reihenfolge=reihenfolge)
    except Exception as f:
        raise WerkzeugFehler(str(f)) from f
    return {"regel_id": r["id"], "titel": r["titel"], "muster": r["muster"],
            "hinweis": "Die Regel bleibt ungeprüft und wird nicht gezeigt, "
                       "bis ein Mensch sie freigibt — wie eine eingetragene "
                       "Vokabel."}


def regeln_auflisten(db: sqlite3.Connection, person: dict, sammlung_id: int,
                     nur_ungepruefte: bool = False):
    """Welche Regeln es schon gibt — damit nichts doppelt geschrieben wird."""
    import regeln
    zugang.sammlung_pruefen(db, person["id"], sammlung_id, schreiben=False)
    liste = regeln.auflisten(db, sammlung_id, nur_ungepruefte)
    return {"anzahl": len(liste),
            "regeln": [{"id": r["id"], "kennung": r["kennung"],
                        "titel": r["titel"], "muster": r["muster"],
                        "geprueft": r["geprueft"]} for r in liste]}


# ------------------------------------------------------- Sätze und Texte

def uebung_anlegen(db: sqlite3.Connection, person: dict, sammlung_id: int,
                   **eintrag):
    """Einen Übungssatz oder Text anlegen."""
    import uebungen
    zugang.sammlung_pruefen(db, person["id"], sammlung_id, schreiben=True)
    try:
        ergebnis = uebungen.anlegen(db, sammlung_id, eintrag)
    except Exception as f:
        raise WerkzeugFehler(str(f)) from f
    return {"uebung_id": ergebnis["id"], "typ": ergebnis["typ"],
            "titel": ergebnis["titel"],
            "abschnitte": len(ergebnis["abschnitte"]),
            "aufgaben": [{"id": a["id"], "typ": a["typ"],
                          "bewertung_art": a["bewertung_art"]}
                         for a in ergebnis["aufgaben"] if a["aktiv"]],
            "hinweis": "Die Übung bleibt ungeprüft, bis ein Mensch sie "
                       "freigibt — wie eine eingetragene Form."}


def uebungen_importieren(db: sqlite3.Connection, person: dict, sammlung_id: int,
                         eintraege: list, nur_pruefen: bool = False):
    """Viele Übungen in einem Aufruf — mit Probelauf und wiederholbar."""
    import uebungen
    zugang.sammlung_pruefen(db, person["id"], sammlung_id, schreiben=True)
    try:
        return uebungen.importieren(db, sammlung_id, eintraege, nur_pruefen)
    except Exception as f:
        raise WerkzeugFehler(str(f)) from f


def uebungen_auflisten(db: sqlite3.Connection, person: dict, sammlung_id: int,
                       lektion_nr: int | None = None,
                       bis_lektion: int | None = None,
                       typ: str | None = None,
                       nur_ungepruefte: bool = False,
                       seite: int = 1, anzahl: int = 50):
    import uebungen
    zugang.sammlung_pruefen(db, person["id"], sammlung_id)
    anzahl = max(1, min(int(anzahl), 200))
    ab = max(0, (max(1, int(seite)) - 1) * anzahl)
    try:
        return uebungen.auflisten(db, sammlung_id, lektion_nr, typ,
                                  bis_lektion, nur_ungepruefte, ab, anzahl)
    except Exception as f:
        raise WerkzeugFehler(str(f)) from f


def uebung_aendern(db: sqlite3.Connection, person: dict, uebung_id: int,
                   **aenderung):
    """Eine Übung berichtigen. Geänderter Inhalt fällt auf ungeprüft zurück."""
    import uebungen
    t = dbm.zeile(db, "SELECT sammlung_id FROM text WHERE id = ?", (uebung_id,))
    if t is None:
        raise WerkzeugFehler(f"Übung {uebung_id} gibt es nicht")
    zugang.sammlung_pruefen(db, person["id"], t["sammlung_id"], schreiben=True)
    if not aenderung:
        raise WerkzeugFehler("Nichts zu ändern angegeben")
    try:
        ergebnis = uebungen.aendern(db, uebung_id, aenderung)
    except Exception as f:
        raise WerkzeugFehler(str(f)) from f
    return {"uebung_id": ergebnis["id"], "titel": ergebnis["titel"],
            "geprueft": ergebnis["geprueft"],
            "abschnitte": len(ergebnis["abschnitte"])}


def text_pruefen(db: sqlite3.Connection, person: dict, sammlung_id: int,
                 text: str, bis_lektion: int | None = None):
    """Welche Wörter des Textes stehen bis zu dieser Lektion noch nicht da?"""
    import uebungen
    zugang.sammlung_pruefen(db, person["id"], sammlung_id)
    try:
        return uebungen.text_pruefen(db, sammlung_id, text, bis_lektion)
    except Exception as f:
        raise WerkzeugFehler(str(f)) from f


def lektion_anlegen(db: sqlite3.Connection, person: dict, sammlung_id: int,
                    nr: int, titel: str | None = None,
                    beschreibung: str | None = None):
    """Legt eine Lektion an oder zieht die vorhandene mit dieser Nummer nach."""
    import sammelimport
    zugang.sammlung_pruefen(db, person["id"], sammlung_id, schreiben=True)
    kennung = sammelimport.lektion_sichern(db, sammlung_id, nr, titel,
                                           beschreibung)
    return dbm.zeile(db, "SELECT * FROM lektion WHERE id = ?", (kennung,))


def lektionen_auflisten(db: sqlite3.Connection, person: dict, sammlung_id: int):
    """Welche Lektionen gibt es, und wie viele Wörter hängen daran?"""
    import sammelimport
    zugang.sammlung_pruefen(db, person["id"], sammlung_id)
    return {"lektionen": sammelimport.lektionen(db, sammlung_id)}


def vokabel_lesen(db: sqlite3.Connection, person: dict, lexem_id: int):
    zugang.lexem_pruefen(db, person["id"], lexem_id)
    lexem = _fehler_wandeln(_app().lexem_lesen, lexem_id, db)
    return {
        "lexem_id": lexem["id"], "lemma": lexem["lemma"],
        "wortart": lexem["wortart"], "merkmale": lexem["merkmale"],
        "sprache": lexem["sprache"],
        # form_id, nicht id: genau diese Zahl verlangen form_aendern und
        # form_loeschen, und sie soll nicht erst übersetzt werden müssen.
        "formen": [{"form_id": f["id"], "text": f["text"],
                    "merkmale": f["merkmale"],
                    "beschriftung": f["beschriftung"],
                    "geprueft": bool(f["geprueft"]), "quelle": f["quelle"],
                    "gruppe": f["gruppe"]} for f in lexem["formen"]],
        "bedeutungen": [{"id": b["id"], "kontext": b["kontext"],
                         "erklaerung": b["notiz"],
                         "uebersetzungen": [u["text"] for u in b["uebersetzungen"]]}
                        for b in lexem["bedeutungen"]],
        # Mit, damit beispiele_setzen nicht blind ersetzt: es tauscht
        # die Liste als Ganzes aus, und wer sie nicht kennt, wirft weg,
        # was schon dasteht.
        "beispiele": [{"satz": b["satz"], "uebersetzung": b["uebersetzung"],
                       "bedeutung_id": b["bedeutung_id"]}
                      for b in lexem["beispiele"]],
        "aufgaben_aktiv": len([x for x in lexem["aufgaben"] if x["aktiv"]]),
    }


def vokabel_nachschlagen(db: sqlite3.Connection, person: dict, sammlung_id: int,
                         suche: str, anzahl: int = 10):
    zugang.sammlung_pruefen(db, person["id"], sammlung_id)
    ergebnis = _fehler_wandeln(_app().woerterbuch, sammlung_id, suche, anzahl, db)
    return {"suche": ergebnis["suche"], "gefunden": ergebnis["gefunden"],
            "eintraege": [{"lexem_id": e["id"], "lemma": e["lemma"],
                           "wortart": e["wortart"],
                           "bedeutungen": [", ".join(u["text"]
                                                     for u in b["uebersetzungen"])
                                           for b in e["bedeutungen"]],
                           "gefunden_bei": e["fundstellen"]}
                          for e in ergebnis["eintraege"]]}


def formen_ergaenzen(db: sqlite3.Connection, person: dict, lexem_id: int,
                     formen: list, als_geprueft: bool = False):
    from modelle import FormEingabe
    a = _app()
    zugang.lexem_pruefen(db, person["id"], lexem_id, schreiben=True)
    angelegt = []
    for f in formen:
        try:
            eingabe = FormEingabe(**{**f, "quelle": f.get("quelle", "ki"),
                                     "geprueft": f.get("geprueft", als_geprueft)})
        except Exception as fehler:
            raise WerkzeugFehler(f"Form nicht gültig: {fehler}") from fehler
        angelegt.append(_fehler_wandeln(a.form_anlegen, lexem_id, eingabe, db)["id"])
    return {"angelegt": len(angelegt), "form_ids": angelegt,
            "pruefung": _bericht_kurz(_fehler_wandeln(a.lexem_pruefen, lexem_id, db))}


# Ein Werkzeug zum STAPELWEISEN Freigeben gibt es hier absichtlich nicht.
# Es hieß formen_bestaetigen und nahm eine Liste von Kennungen; die
# Beschreibung bat darum, die eigenen Einträge nicht selbst freizugeben.
# Eine Bitte ist keine Sperre, und ein Agent, der im Stapel freigibt,
# hätte die Prüfung abgeschafft, nicht erledigt.
#
# EHRLICHERWEISE ist damit nicht alles zu: `als_geprueft` an
# vokabel_anlegen und formen_ergaenzen und ein `geprueft` im Eintrag von
# uebung_anlegen lassen dasselbe im Kleinen zu. Das ist so entschieden
# worden — die Abkürzung ist bequem, wenn man den Eintrag ohnehin
# beurteilen kann —, aber es ist eine Entscheidung und keine Sperre, und
# der Kommentar hat jahrelang das Gegenteil behauptet. Wer das ändern
# will: den Parameter streichen, dann stimmt die alte Zusage wieder.


def beispiele_setzen(db: sqlite3.Connection, person: dict, lexem_id: int,
                     beispiele: list):
    """Beispielsätze zu einem Wort — wie im Wörterbuch."""
    zugang.lexem_pruefen(db, person["id"], lexem_id, schreiben=True)
    from modelle import BeispieleSetzen
    eingabe = BeispieleSetzen(beispiele=beispiele or [])
    d = _fehler_wandeln(_app().beispiele_setzen, lexem_id, eingabe, None, db)
    return {**d, "hinweis": "Beispielsätze werden nicht abgefragt und "
                            "brauchen keine Freigabe — sie stehen beim Wort "
                            "und helfen beim Verstehen."}


def erklaerung_setzen(db: sqlite3.Connection, person: dict, bedeutung_id: int,
                      erklaerung: str):
    """Der Erklärsatz zu einer Bedeutung."""
    lexem_id = dbm.wert(db, "SELECT lexem_id FROM bedeutung WHERE id = ?",
                        (bedeutung_id,))
    if lexem_id is None:
        raise KeyError(f"Bedeutung {bedeutung_id} gibt es nicht")
    zugang.lexem_pruefen(db, person["id"], lexem_id, schreiben=True)
    from modelle import ErklaerungSetzen
    return _fehler_wandeln(_app().erklaerung_setzen, bedeutung_id,
                           ErklaerungSetzen(erklaerung=erklaerung), None, db)


def eintrag_pruefen(db: sqlite3.Connection, person: dict, lexem_id: int):
    zugang.lexem_pruefen(db, person["id"], lexem_id)
    return _bericht_kurz(_fehler_wandeln(_app().lexem_pruefen, lexem_id, db))


def sammlung_pruefen(db: sqlite3.Connection, person: dict, sammlung_id: int,
                     nur_mangelhafte: bool = True):
    zugang.sammlung_pruefen(db, person["id"], sammlung_id)
    bericht = _fehler_wandeln(_app().sammlung_pruefen, sammlung_id,
                              nur_mangelhafte, db)
    return {"geprueft": bericht["geprueft"], "zaehler": bericht["zaehler"],
            "eintraege": [{"lexem_id": e["lexem_id"], "lemma": e["lemma"],
                           **_bericht_kurz(e)} for e in bericht["eintraege"]]}


def sprachprofil_lesen(db: sqlite3.Connection, person: dict, sprache: str):
    return _fehler_wandeln(_app().sprachprofil_lesen, sprache, db)


def sprachprofil_anpassen(db: sqlite3.Connection, person: dict, sprache: str,
                          profil: dict):
    from modelle import SprachprofilSetzen
    zugang.verwalter_pruefen(person)
    return _fehler_wandeln(_app().sprachprofil_setzen, sprache,
                           SprachprofilSetzen(profil=profil, neu_rechnen=True),
                           None, db)


def sprache_einrichten(db: sqlite3.Connection, person: dict, code: str,
                       name: str, profil: dict, schrift: str = "latein",
                       stimme: str | None = None):
    from modelle import SpracheAnlegen
    zugang.verwalter_pruefen(person)
    try:
        eingabe = SpracheAnlegen(code=code, name=name, schrift=schrift,
                                 stimme=stimme, profil=profil)
    except Exception as f:
        raise WerkzeugFehler(f"Eingabe nicht gültig: {f}") from f
    return _fehler_wandeln(_app().sprache_anlegen, eingabe, None, db)


# ------------------------------------------- Beschreibung der Werkzeuge

def offene_woerter_lesen(db: sqlite3.Connection, person: dict,
                         sammlung_id: int | None = None,
                         anzahl: int = 40):
    """Welche Wörter hat sie beim Lesen markiert und braucht sie noch?

    Mit Grenze, und die ist nicht Zierde: aus einem Zeitungsartikel
    kamen in einem Zug 840 Wörter auf die Liste. Die alle in eine
    Antwort zu packen hieße, dass die KI den Anfang vergessen hat,
    bevor sie am Ende ist.
    """
    if sammlung_id:
        zugang.sammlung_pruefen(db, person["id"], sammlung_id)
    offen = lesetexte.wortwuensche(db, person["id"], sammlung_id, offen=True)
    grenze = max(1, min(int(anzahl), 200))
    gezeigt = offen[:grenze]

    # WELCHE Sammlungen überhaupt etwas offen haben, immer mitgeben.
    #
    # Ohne das verdeckt eine große Liste jede kleinere: die Reihenfolge
    # ist die Häufigkeit, und die zählt quer über alle Sammlungen. Aus
    # 825 griechischen und 89 mittelhochdeutschen Wünschen kamen im
    # Häppchen von 40 vierzig griechische — die KI sah nach, fand kein
    # einziges mittelhochdeutsches Wort und schloss daraus, es gebe
    # keines. Genau so ist es passiert.
    alle = (offen if not sammlung_id
            else lesetexte.wortwuensche(db, person["id"], None, offen=True))
    nach_sammlung: dict[str, int] = {}
    for w in alle:
        name = w["sammlung"] or "ohne Sammlung"
        nach_sammlung[name] = nach_sammlung.get(name, 0) + 1

    weitere = ""
    if len(nach_sammlung) > 1:
        weitere = (" Offen nach Sammlung: "
                   + ", ".join(f"{n} ({z})" for n, z in
                               sorted(nach_sammlung.items(),
                                      key=lambda x: -x[1]))
                   + ". Die Reihenfolge ist die Häufigkeit und gilt über "
                     "ALLE Sammlungen — eine große verdeckt sonst eine "
                     "kleine. Für eine bestimmte sammlung_id mitgeben.")

    return {
        "anzahl": len(gezeigt),
        "offen_gesamt": len(offen),
        "offen_nach_sammlung": nach_sammlung,
        "hinweis": ("Nach Häufigkeit im Text geordnet, Häufigstes zuerst. "
                    + (f"Es warten noch {len(offen) - len(gezeigt)} weitere — "
                       "diese hier erledigen, dann erneut abrufen."
                       if len(offen) > len(gezeigt) else "")
                    + weitere),
        "woerter": [{"wunsch_id": w["id"], "wort": w["wort"],
                     "vorkommen": w["vorkommen"],
                     "sammlung_id": w["sammlung_id"],
                     "sammlung": w["sammlung"], "sprache": w["sprache"],
                     "zusammenhang": w["zusammenhang"],
                     "aus_text": w["text"]}
                    for w in gezeigt],
    }


def offenes_wort_erledigen(db: sqlite3.Connection, person: dict,
                           wunsch_id: int, lexem_id: int | None = None):
    """Haken dran, nachdem die Vokabel angelegt ist."""
    w = dbm.zeile(db, "SELECT * FROM wortwunsch WHERE id = ?", (wunsch_id,))
    if w is None:
        raise KeyError(f"Wortwunsch {wunsch_id} gibt es nicht")
    if w["benutzer_id"] != person["id"]:
        raise PermissionError("Dieser Wortwunsch gehört dir nicht.")
    return dict(_fehler_wandeln(lesetexte.wortwunsch_erledigen, db,
                                wunsch_id, lexem_id))


def texte_auflisten(db: sqlite3.Connection, person: dict, sammlung_id: int):
    """Welche Lesetexte liegen in dieser Sammlung?"""
    zugang.sammlung_pruefen(db, person["id"], sammlung_id)
    return {"texte": [dict(t) for t in lesetexte.auflisten(db, sammlung_id)]}


def text_anlegen(db: sqlite3.Connection, person: dict, sammlung_id: int,
                 titel: str, inhalt: str, niveau: str | None = None,
                 notiz: str | None = None):
    """Einen Text hinterlegen, den sie dann lesen und übersetzen kann."""
    zugang.sammlung_pruefen(db, person["id"], sammlung_id, schreiben=True)
    t = _fehler_wandeln(lesetexte.anlegen, db, sammlung_id, titel, inhalt,
                        niveau=niveau, notiz=notiz, quelle="ki")
    return {"text_id": t["id"], "titel": t["titel"],
            "abschnitte": len(t["abschnitte"])}


def text_lesen(db: sqlite3.Connection, person: dict, text_id: int):
    """Den Text mit seinen Abschnitten — zum Übersetzen."""
    t = dbm.zeile(db, "SELECT sammlung_id FROM text WHERE id = ?", (text_id,))
    if t is None:
        raise KeyError(f"Text {text_id} gibt es nicht")
    zugang.sammlung_pruefen(db, person["id"], t["sammlung_id"])
    d = _fehler_wandeln(lesetexte.lesen, db, text_id)
    return {"titel": d["titel"], "sprache": d["sprache"],
            "abschnitte": [{"abschnitt_id": a["id"], "original": a["original"],
                            "referenz": a["referenz"]}
                           for a in d["abschnitte"]]}


def text_uebersetzen(db: sqlite3.Connection, person: dict, text_id: int,
                     fassungen: dict):
    """Hinterlegt je Abschnitt eine Referenzübersetzung."""
    t = dbm.zeile(db, "SELECT sammlung_id FROM text WHERE id = ?", (text_id,))
    if t is None:
        raise KeyError(f"Text {text_id} gibt es nicht")
    zugang.sammlung_pruefen(db, person["id"], t["sammlung_id"], schreiben=True)
    sauber = {int(k): str(v) for k, v in (fassungen or {}).items()}
    d = _fehler_wandeln(lesetexte.referenz_setzen, db, text_id, sauber)
    return {**d, "hinweis": "Sie erscheint im Text als aufklappbare "
                            "Referenzübersetzung. Die eigene Fassung der "
                            "Lernenden bleibt davon unberührt."}


def text_deckung_lesen(db: sqlite3.Connection, person: dict, text_id: int):
    """Welche Wörter des Textes fehlen ihr noch?

    Der nützlichste Aufruf vor dem Anlegen von Vokabeln: er nennt die
    Lücken, ohne dass sie jedes Wort einzeln markieren muss.
    """
    t = dbm.zeile(db, "SELECT sammlung_id FROM text WHERE id = ?", (text_id,))
    if t is None:
        raise KeyError(f"Text {text_id} gibt es nicht")
    zugang.sammlung_pruefen(db, person["id"], t["sammlung_id"])
    d = _fehler_wandeln(lesetexte.deckung, db, text_id, person["id"])
    fehlend = sorted({w["wort"] for w in d["woerter"] if not w["lexem_id"]})
    return {"abdeckung": d["abdeckung"], "zahlen": d["zahlen"],
            "urteil": d["urteil"], "fehlende_woerter": fehlend}


def lehrgang_lesen(db: sqlite3.Connection, person: dict, sammlung_id: int):
    """Lektionen, Formgruppen und die bisherige Zuordnung — zum Ordnen."""
    zugang.sammlung_pruefen(db, person["id"], sammlung_id)
    lektionen = [{"nr": z["nr"], "name": z["name"], "woerter": z["woerter"]}
                 for z in dbm.zeilen(db, """
        SELECT l.nr, l.name,
               (SELECT COUNT(*) FROM lexem x WHERE x.lektion_id = l.id)
                 AS woerter
          FROM lektion l WHERE l.sammlung_id = ? AND l.nr IS NOT NULL
         ORDER BY l.nr""", (sammlung_id,))]
    vorhanden = lehrgang.zuordnung(db, sammlung_id)
    gruppen = []
    for v in _fehler_wandeln(lehrgang.vorschlag, db, sammlung_id):
        gruppen.append({
            "formgruppe": v["formgruppe"], "name": v["name"],
            "wortart": v["wortart"],
            "ab_lektion": vorhanden.get(v["formgruppe"]),
            "namensvorschlag": v["ab_lektion"],
            "namensvorschlag_eindeutig": v["eindeutig"],
            "aufgaben": dbm.wert(db, """
                SELECT COUNT(*) FROM aufgabe a JOIN lexem l ON l.id = a.lexem_id
                 WHERE l.sammlung_id = ? AND a.formgruppe = ? AND a.aktiv = 1""",
                (sammlung_id, v["formgruppe"])) or 0,
        })
    return {"lektionen": lektionen, "formgruppen": gruppen,
            "hinweis": "Geh nach den Lektionsnamen und nach dem, was du über "
                       "den Aufbau dieser Sprache weißt. Die Formen der "
                       "Vokabeln helfen NICHT: zu den meisten Wörtern steht "
                       "das volle Paradigma, unabhängig von der Lektion — "
                       "nachgemessen erschien jede Formgruppe ab Lektion 1."}


def lehrgang_zuordnen(db: sqlite3.Connection, person: dict, sammlung_id: int,
                      zuordnung: dict):
    """Trägt ein, ab welcher Lektion welche Formgruppe gilt."""
    zugang.sammlung_pruefen(db, person["id"], sammlung_id, schreiben=True)
    sauber = {k: int(v) for k, v in (zuordnung or {}).items() if v is not None}
    neu = _fehler_wandeln(lehrgang.zuordnung_setzen, db, sammlung_id, sauber)
    return {"zuordnung": neu, "anzahl": len(neu),
            "hinweis": "Wirkt erst, wenn jemand unter Einstellungen seine "
                       "eigene Lektion einträgt. Der Lernstand bleibt in "
                       "jedem Fall erhalten."}


def _s(typ, beschreibung, **rest):
    return {"type": typ, "description": beschreibung, **rest}


_TYPEN = ("satz", "text", "dialog", "brief", "zeitungsstil")

MERKMALSHINWEIS = (
    "Formen tragen Merkmalsbündel, keine Spaltennamen: "
    '{"modus":"indikativ","tempus":"praesens","person":"1","numerus":"sg"}. '
    "Die Person ist eine Zeichenkette. Welche Bündel eine Sprache kennt, sagt "
    "formgruppen_zeigen — das ist vor dem ersten Eintragen aufzurufen."
)

WERKZEUGE: list[dict] = [
    {
        "name": "sammlungen_auflisten",
        "description": "Wer du bist und welche Sammlungen dir gehören oder dir "
                       "freigegeben sind. Der erste Aufruf in jeder Sitzung — "
                       "ohne sammlung_id geht nichts. Fremde Sammlungen "
                       "erscheinen nicht und sind auch nicht erreichbar.",
        "inputSchema": {"type": "object", "properties": {}},
        "funktion": sammlungen_auflisten,
    },
    {
        "name": "formgruppen_zeigen",
        "description": "Welche Formgruppen (Zeiten, Tabellen) eine Sprache hat "
                       "und welche Merkmale ihre Zellen tragen. VOR dem ersten "
                       "Eintragen in einer Sprache aufrufen. Liefert für jede "
                       "Zelle das genaue Merkmalsbündel zum Abschreiben.",
        "inputSchema": {"type": "object", "properties": {
            "sprache": _s("string", "Sprachkennung, z.B. el, fr, gmh")},
            "required": ["sprache"]},
        "funktion": formgruppen_zeigen,
    },
    {
        "name": "merkmale_zeigen",
        "description": "Das vollständige erlaubte Merkmalsvokabular. Alles "
                       "andere wird beim Eintragen abgelehnt.",
        "inputSchema": {"type": "object", "properties": {}},
        "funktion": merkmale_zeigen,
    },
    {
        "name": "vokabel_anlegen",
        "description":
            "Ein vollständiges Wort anlegen — Lemma, alle Formen, alle "
            "Bedeutungen in EINEM Aufruf, nicht in vierzig Einzelschritten.\n\n"
            + MERKMALSHINWEIS + "\n\n"
            "Vollständige Paradigmen liefern: der Trainer ERZEUGT daraus die "
            "Aufgaben, und aus dem gemeinsamen Anfang der Formen einer Zeit "
            "leitet er den Wortstamm ab. Fehlende Zellen heißen fehlende "
            "Aufgaben und verdorbene Stammerkennung.\n\n"
            "Mehrere gültige Übersetzungen sind der Normalfall — alle angeben, "
            "nicht die beste auswählen. Verschiedene BEDEUTUNGEN (Bank als "
            "Geldinstitut gegen Sitzbank) sind getrennte Einträge in "
            "bedeutungen, jeder mit kontext.\n\n"
            "Die Formen werden als ungeprüft eingetragen und noch nicht "
            "abgefragt, bis ein Mensch sie freigibt. Die Antwort enthält die "
            "Qualitätsprüfung — ihre Befunde bitte lesen und nachbessern.",
        "inputSchema": {"type": "object", "properties": {
            "sammlung_id": _s("integer", "aus sammlungen_auflisten"),
            "lemma": _s("string", "Zitierform, wie im Wörterbuch"),
            "wortart": _s("string", "verb, substantiv, adjektiv, adverb, "
                                    "pronomen, wendung …"),
            "bedeutungen": _s("array",
                "Je Bedeutung ein Objekt mit uebersetzungen (Liste von "
                'Zeichenketten) und wahlweise kontext. Beispiel: '
                '[{"uebersetzungen":["schreiben","aufschreiben"]}]',
                items={"type": "object"}),
            "formen": _s("array",
                'Je Form {"text": "...", "merkmale": {...}}. Genau eine Form '
                'darf "ist_grundform": true tragen.', items={"type": "object"}),
            "merkmale": _s("object",
                "Merkmale des WORTES, nicht einer Form: genus beim Substantiv, "
                "klasse (Ablautreihe, Konjugationsklasse) beim Verb. Was "
                "erlaubt ist, sagt formgruppen_zeigen unter lexemmerkmale. "
                "Griechische Deponentien (θυμάμαι, έρχομαι) brauchen hier "
                "diathese = deponens: dann zählen die Aktivgruppen, die es "
                "bei ihnen gar nicht gibt, nicht als fehlend."),
            "notiz": _s("string", "freier Vermerk"),
            "als_geprueft": _s("boolean",
                "Nur auf ausdrücklichen Wunsch der Benutzerin auf true setzen. "
                "Sonst bleiben die Formen bis zur Freigabe unabgefragt."),
        }, "required": ["sammlung_id", "lemma", "wortart", "bedeutungen"]},
        "funktion": vokabel_anlegen,
    },
    {
        "name": "vokabeln_importieren",
        "description":
            "Viele Wörter in EINEM Aufruf. Für größere Bestände der richtige "
            "Weg — vokabel_anlegen ist für einzelne Wörter.\n\n"
            "Drei Eigenschaften, auf die es ankommt:\n"
            "• **Probelauf**: nur_pruefen=true schreibt nichts und meldet "
            "trotzdem alle Befunde. Immer zuerst so laufen lassen.\n"
            "• **Wiederholbar**: derselbe Eintrag landet nicht zweimal im "
            "Bestand. Schlüssel ist die mitgegebene kennung, sonst lemma + "
            "wortart. Ein zweiter Lauf mit berichtigten Daten bessert nach.\n"
            "• **Geprüftes bleibt unangetastet**: hat ein Mensch eine Form "
            "bestätigt, wird sie nie überschrieben — die Abweichung wird "
            "gemeldet.\n\n"
            "Je Eintrag dasselbe Format wie bei vokabel_anlegen, dazu "
            "wahlweise lektion_nr, lektion_titel, reihenfolge und kennung. "
            "Berichtet wird knapp: nur Einträge, zu denen es etwas zu sagen "
            "gibt.\n\n" + MERKMALSHINWEIS,
        "inputSchema": {"type": "object", "properties": {
            "sammlung_id": _s("integer", "aus sammlungen_auflisten"),
            "eintraege": _s("array",
                "Liste von Wörtern. Je Eintrag: lemma, wortart, bedeutungen, "
                "formen, merkmale — dazu lektion_nr (Nummer im Lehrwerk), "
                "lektion_titel, reihenfolge (Lernreihenfolge innerhalb der "
                "Lektion) und kennung (eigener Schlüssel; nötig bei "
                "Gleichlautern wie φορά »Mal« und »er trägt«).",
                items={"type": "object"}),
            "nur_pruefen": _s("boolean",
                "true: nichts schreiben, nur berichten. Zuerst immer so.")},
            "required": ["sammlung_id", "eintraege"]},
        "funktion": vokabeln_importieren,
    },
    {
        "name": "sammlung_anlegen",
        "description": "Eine neue Sammlung anlegen. Sie gehört dir; niemand "
                       "sonst sieht sie, bis du sie freigibst. Danach "
                       "formgruppen_zeigen für die Sprache aufrufen.",
        "inputSchema": {"type": "object", "properties": {
            "name": _s("string", "wie die Sammlung heißen soll"),
            "sprache": _s("string",
                "Code der Lernsprache: de, en, fr, es, el, gmh. Eine andere "
                "braucht erst sprache_einrichten."),
            "grundsprache": _s("string", "Sprache der Übersetzungen, meist de"),
            "beschreibung": _s("string", "wahlweise"),
        }, "required": ["name", "sprache"]},
        "funktion": sammlung_anlegen,
    },
    {
        "name": "vokabeln_auflisten",
        "description":
            "Was steht schon im Bestand? Vor dem Anlegen und vor dem "
            "Berichtigen aufzurufen — sonst entstehen Doppelte.\n\n"
            "Je Wort kommen lexem_id, Lemma, Wortart, die erste Bedeutung "
            "und die Zahl der Formen, der ungeprüften und der Aufgaben "
            "zurück. Mit nur_ungepruefte lässt sich sehen, wo noch eine "
            "Freigabe fehlt.",
        "inputSchema": {"type": "object", "properties": {
            "sammlung_id": _s("integer", "aus sammlungen_auflisten"),
            "lektion_nr": _s("integer", "nur diese Lektion"),
            "wortart": _s("string", "nur diese Wortart"),
            "suche": _s("string", "Teil des Lemmas oder einer Übersetzung"),
            "nur_ungepruefte": _s("boolean",
                "nur Wörter mit noch nicht freigegebenen Formen"),
            "seite": _s("integer", "ab 1"),
            "anzahl": _s("integer", "je Seite, höchstens 200"),
        }, "required": ["sammlung_id"]},
        "funktion": vokabeln_auflisten,
    },
    {
        "name": "vokabel_aendern",
        "description":
            "Ein Wort berichtigen. Nur die genannten Felder ändern sich.\n\n"
            "`bedeutungen` ERSETZT alle Bedeutungen — welche einzelne "
            "Übersetzung sonst gemeint wäre, ließe sich nicht ausdrücken. "
            "Für die Formen gibt es form_aendern und formen_ergaenzen.",
        "inputSchema": {"type": "object", "properties": {
            "lexem_id": _s("integer", "aus vokabeln_auflisten"),
            "lemma": _s("string", "die Zitierform"),
            "wortart": _s("string", ""),
            "merkmale": _s("object",
                "Merkmale des WORTES (genus, klasse, diathese), nicht einer "
                "Form. Ersetzt die bisherigen."),
            "bedeutungen": _s("array",
                'ERSETZT alle: [{"uebersetzungen":["schreiben"],'
                '"kontext":"…"}]', items={"type": "object"}),
            "lektion_nr": _s("integer", "Nummer im Lehrwerk"),
            "reihenfolge": _s("integer", "Lernreihenfolge in der Lektion"),
            "kennung": _s("string", "eigener Schlüssel"),
            "notiz": _s("string", "freier Vermerk"),
        }, "required": ["lexem_id"]},
        "funktion": vokabel_aendern,
    },
    {
        "name": "form_aendern",
        "description":
            "Eine einzelne Form berichtigen. Nur das Genannte ändert sich.\n\n"
            "Ändert sich Text oder Merkmalsbündel, fällt die Form auf "
            "**ungeprüft** zurück und wird bis zur Freigabe nicht abgefragt "
            "— was geändert wurde, ist nicht mehr das, was ein Mensch "
            "freigegeben hat. Die Freigabe selbst kann dieses Werkzeug "
            "nicht setzen.\n\n" + MERKMALSHINWEIS,
        "inputSchema": {"type": "object", "properties": {
            "form_id": _s("integer", "aus vokabel_lesen"),
            "text": _s("string", "die berichtigte Form"),
            "merkmale": _s("object", "ersetzt das Bündel vollständig"),
            "ist_grundform": _s("boolean", "die Zitierform; nur eine je Wort"),
            "ist_variante": _s("boolean",
                "eine weitere gültige Form derselben Zelle (μιλώ neben "
                "μιλάω). Varianten zählen als richtig, werden aber nicht "
                "eigens abgefragt."),
            "aussprache": _s("string", "wahlweise"),
            "notiz": _s("string", "wahlweise"),
        }, "required": ["form_id"]},
        "funktion": form_aendern,
    },
    {
        "name": "form_loeschen",
        "description":
            "Eine Form entfernen. `text` muss die vorhandene Form nennen — "
            "an einer Form hängt ein Lernstand, und eine verwechselte "
            "Kennung löschte sonst stillschweigend die falsche.\n\n"
            "Eine falsch beschriftete Form lässt sich meist mit form_aendern "
            "richtigstellen; das ist der schonendere Weg.",
        "inputSchema": {"type": "object", "properties": {
            "form_id": _s("integer", "aus vokabel_lesen"),
            "text": _s("string", "die vorhandene Form, zur Bestätigung"),
        }, "required": ["form_id", "text"]},
        "funktion": form_loeschen,
    },
    {
        "name": "vokabel_loeschen",
        "description":
            "Ein ganzes Wort entfernen, mit allen Formen, Bedeutungen und "
            "dem Lernstand dazu. `lemma` muss das vorhandene nennen.\n\n"
            "Die Antwort sagt, wie viele Wiederholungen dabei verlorengehen. "
            "Steht dort eine Zahl über null, ist das Wort schon gelernt "
            "worden — dann vorher mit der Benutzerin abstimmen.",
        "inputSchema": {"type": "object", "properties": {
            "lexem_id": _s("integer", "aus vokabeln_auflisten"),
            "lemma": _s("string", "das vorhandene Lemma, zur Bestätigung"),
        }, "required": ["lexem_id", "lemma"]},
        "funktion": vokabel_loeschen,
    },
    {
        "name": "regeln_auflisten",
        "description":
            "Welche Grammatikregeln diese Sammlung schon hat. Vor dem "
            "Schreiben ansehen, sonst entstehen Dubletten.",
        "inputSchema": {"type": "object", "properties": {
            "sammlung_id": _s("integer", "aus sammlungen_auflisten"),
            "nur_ungepruefte": _s("boolean", "nur die noch nicht "
                                             "freigegebenen"),
        }, "required": ["sammlung_id"]},
        "funktion": regeln_auflisten,
    },
    {
        "name": "regel_anlegen",
        "description":
            "Eine Grammatikregel hinterlegen — das \"Warum ist das so?\", "
            "das beim Üben neben der Frage steht.\n\n"
            "Gefunden wird eine Regel über ihr MUSTER, nicht über eine "
            "Zuordnung zu einzelnen Wörtern: {\"wortart\": \"verb\", "
            "\"merkmale\": {\"tempus\": \"aorist\"}} greift bei jeder "
            "Aoristform jedes Verbs — auch bei denen, die es noch gar nicht "
            "gibt. Ein leeres Muster gilt überall.\n\n"
            "Je enger das Muster, desto eher wird die Regel gezeigt; es "
            "erscheinen höchstens drei je Frage. Also lieber mehrere enge "
            "Regeln als eine lange allgemeine.\n\n"
            "**Schreib für jemanden, der mitten in einer Abfrage sitzt** und "
            "eine Frage hat — zwei, drei Sätze, kein Grammatikbuchabschnitt. "
            "Beispiele helfen mehr als Begriffe.\n\n"
            "Mit `kennung` findest du dieselbe Regel wieder und berichtigst "
            "sie, statt eine zweite anzulegen. Jede Änderung setzt die "
            "Freigabe zurück.",
        "inputSchema": {"type": "object", "properties": {
            "sammlung_id": _s("integer", "aus sammlungen_auflisten"),
            "titel": _s("string", "kurz, z. B. \"Aorist: der einmalige "
                                  "Vorgang\""),
            "text": _s("string", "die Erklärung selbst"),
            "muster": _s("object",
                "worauf die Regel zutrifft; alle Felder freigestellt. "
                "wortart, formgruppe (Kennung aus formgruppen_zeigen), "
                "merkmale (Merkmalsbündel wie bei den Formen)"),
            "beispiele": _s("array",
                "[{\"form\": \"έγραψα\", \"bedeutung\": \"ich schrieb\"}]",
                items={"type": "object"}),
            "kennung": _s("string", "stabile Kennung zum Wiederfinden"),
            "reihenfolge": _s("integer", "unter gleich engen Regeln"),
        }, "required": ["sammlung_id", "titel", "text"]},
        "funktion": regel_anlegen,
    },
    {
        "name": "uebung_anlegen",
        "description":
            "Einen Übungssatz oder Text anlegen. Satz und Text sind dasselbe "
            "mit unterschiedlich vielen Abschnitten.\n\n"
            "Aus `richtungen` entstehen die Aufgaben: \"el-de\" heißt aus der "
            "Lernsprache in die Grundsprache, \"de-el\" umgekehrt. Bei typ "
            "\"satz\" wird Wort für Wort gegen alle angegebenen Fassungen "
            "verglichen und bewertet; bei allem Längeren bleibt die "
            "Einschätzung beim Menschen und der Vergleich ist nur Hilfe.\n\n"
            "Alternativen großzügig angeben — eine richtige Übersetzung darf "
            "nicht daran scheitern, dass sie nicht die zuerst aufgeschriebene "
            "ist.\n\n"
            "**Fremde Texte werden verlinkt, nicht abgeschrieben.** Für einen "
            "Zeitungsartikel quelle = {\"art\": \"verweis\", \"titel\": …, "
            "\"url\": …} und eine eigene Fassung als Übung.\n\n"
            "Ein Eintrag darf `geprueft: true` tragen und ist dann sofort "
            "abfragbar, ohne dass ein Mensch ihn angesehen hat. Das war "
            "bisher undokumentiert und ist damit die unangenehmste Art "
            "einer Hintertür: nur auf ausdrücklichen Wunsch setzen.",
        "inputSchema": {"type": "object", "properties": {
            "sammlung_id": _s("integer", "aus sammlungen_auflisten"),
            "typ": _s("string", "satz | text | dialog | brief | zeitungsstil",
                      enum=list(_TYPEN)),
            "titel": _s("string", "wahlweise; bei einem Satz unnötig"),
            "zielsprache": _s("string", "der Satz oder Text in der Lernsprache"),
            "grundsprache": _s("string", "die Referenzübersetzung"),
            "alternativen_zielsprache": _s("array",
                "weitere gültige Fassungen in der Lernsprache",
                items={"type": "string"}),
            "alternativen_grundsprache": _s("array",
                "weitere gültige Fassungen in der Grundsprache",
                items={"type": "string"}),
            "abschnitte": _s("array",
                "Bei mehreren Sätzen genauer als zielsprache/grundsprache: "
                "je Abschnitt {zielsprache, grundsprache, "
                "alternativen_zielsprache, alternativen_grundsprache}. Ohne "
                "diese Liste wird nur geteilt, wenn beide Sprachen auf "
                "gleich viele Sätze kommen.", items={"type": "object"}),
            "richtungen": _s("array",
                '["el-de", "de-el"] oder ["hin", "rueck"]. Ohne Angabe beide.',
                items={"type": "string"}),
            "lektion_nr": _s("integer", "Nummer im Lehrwerk"),
            "lektion_titel": _s("string", "wahlweise"),
            "reihenfolge": _s("integer", "Lernreihenfolge innerhalb der Lektion"),
            "niveau": _s("string", "A1 … C2, frei"),
            "kennung": _s("string",
                "eigener Schlüssel; damit ein zweiter Lauf aktualisiert "
                "statt zu verdoppeln"),
            "notiz": _s("string", "freier Vermerk"),
            "quelle": _s("object",
                '{"art": "ki" | "eigen" | "verweis", "titel": …, "url": …}. '
                "Bei \"verweis\" ist Titel oder Adresse nötig."),
        }, "required": ["sammlung_id", "zielsprache"]},
        "funktion": uebung_anlegen,
    },
    {
        "name": "uebungen_importieren",
        "description":
            "Viele Übungen in EINEM Aufruf. Dieselben drei Zusagen wie bei "
            "vokabeln_importieren: Probelauf mit nur_pruefen, wiederholbar "
            "über kennung (sonst über den Zieltext selbst), und eine "
            "freigegebene Übung wird nie überschrieben — die Abweichung wird "
            "gemeldet.\n\n"
            "Berichtet wird knapp: nur Einträge, zu denen es etwas zu sagen "
            "gibt. Vor dem Schreiben lohnt text_pruefen, damit die Sätze zur "
            "Stufe passen.",
        "inputSchema": {"type": "object", "properties": {
            "sammlung_id": _s("integer", "aus sammlungen_auflisten"),
            "eintraege": _s("array",
                "Liste von Übungen, je Eintrag im Format von uebung_anlegen "
                "(ohne sammlung_id).", items={"type": "object"}),
            "nur_pruefen": _s("boolean",
                "true: nichts schreiben, nur berichten. Zuerst immer so."),
        }, "required": ["sammlung_id", "eintraege"]},
        "funktion": uebungen_importieren,
    },
    {
        "name": "uebungen_auflisten",
        "description": "Welche Übungen gibt es? Nach Lektion, bis zu einer "
                       "Lektion, nach Typ, wahlweise nur die noch nicht "
                       "freigegebenen.",
        "inputSchema": {"type": "object", "properties": {
            "sammlung_id": _s("integer", ""),
            "lektion_nr": _s("integer", "genau diese Lektion"),
            "bis_lektion": _s("integer", "alles bis einschließlich dieser"),
            "typ": _s("string", "satz | text | dialog | brief | zeitungsstil",
                      enum=list(_TYPEN)),
            "nur_ungepruefte": _s("boolean", "nur noch nicht freigegebene"),
            "seite": _s("integer", "ab 1"),
            "anzahl": _s("integer", "je Seite, höchstens 200"),
        }, "required": ["sammlung_id"]},
        "funktion": uebungen_auflisten,
    },
    {
        "name": "uebung_aendern",
        "description": "Eine Übung berichtigen. Nur die genannten Felder "
                       "ändern sich. Ändert sich der Inhalt, fällt die Übung "
                       "auf ungeprüft zurück — wie eine geänderte Form. Die "
                       "Freigabe nimmt dieses Werkzeug niemandem ab.",
        "inputSchema": {"type": "object", "properties": {
            "uebung_id": _s("integer", "aus uebungen_auflisten"),
            "typ": _s("string", "", enum=list(_TYPEN)),
            "titel": _s("string", ""),
            "zielsprache": _s("string", ""),
            "grundsprache": _s("string", ""),
            "alternativen_zielsprache": _s("array", "", items={"type": "string"}),
            "alternativen_grundsprache": _s("array", "", items={"type": "string"}),
            "abschnitte": _s("array", "", items={"type": "object"}),
            "richtungen": _s("array", "", items={"type": "string"}),
            "lektion_nr": _s("integer", ""),
            "reihenfolge": _s("integer", ""),
            "niveau": _s("string", ""),
            "kennung": _s("string", ""),
            "notiz": _s("string", ""),
        }, "required": ["uebung_id"]},
        "funktion": uebung_aendern,
    },
    {
        "name": "lernstand_lesen",
        "description":
            "Was sitzt, und woran hakt es? Je WORT, nicht je Aufgabe — zum "
            "Schreiben eines Satzes wird das Wort gebraucht, nicht die "
            "Auskunft, dass daran die Aorist-Aufgabe hakt.\n\n"
            "»schwach« sind Wörter, die mindestens dreimal geübt wurden und "
            "trotzdem in einem Drittel der Fälle danebengingen. Genau sie "
            "gehören in neue Übungssätze — das ist der Schritt von "
            "»Vokabeln abfragen« zu »üben, was nötig ist«.\n\n"
            "Die Zahlen gelten für dich, nicht für alle: ein Lernstand ist "
            "an die Person gebunden.",
        "inputSchema": {"type": "object", "properties": {
            "sammlung_id": _s("integer", "aus sammlungen_auflisten"),
            "anzahl": _s("integer", "wie viele je Liste, höchstens 200"),
        }, "required": ["sammlung_id"]},
        "funktion": lernstand_lesen,
    },
    {
        "name": "text_pruefen",
        "description":
            "Welche Wörter eines Textes stehen im Bestand noch nicht da? "
            "**Vor** dem Schreiben eines Übungstextes aufzurufen — damit er "
            "zur Stufe passt, statt hinterher verworfen zu werden.\n\n"
            "Nachgeschlagen wird über ALLE Formen, nicht nur die Lemmata: "
            "wer έγραψαν liest, hat γράφω vor sich. Drei Listen kommen "
            "zurück: bekannt, zu_spaet (steht da, kommt aber erst nach "
            "dieser Lektion) und unbekannt (steht gar nicht da). Partikeln "
            "der Sprache (θα, να, δεν) zählen nicht als unbekannt.",
        "inputSchema": {"type": "object", "properties": {
            "sammlung_id": _s("integer", ""),
            "text": _s("string", "der Text, noch nicht eingetragen"),
            "bis_lektion": _s("integer",
                "Stufe, auf die der Text passen soll. Ohne Angabe gilt der "
                "ganze Bestand als bekannt."),
        }, "required": ["sammlung_id", "text"]},
        "funktion": text_pruefen,
    },
    {
        "name": "lektion_anlegen",
        "description": "Eine Lektion anlegen oder die vorhandene mit dieser "
                       "Nummer nachziehen. Die NUMMER ist der Schlüssel, "
                       "nicht der Name — Lehrwerke benennen um, nummerieren "
                       "aber nicht neu. Beim Import entstehen Lektionen auch "
                       "von selbst, wenn lektion_nr mitgegeben wird.",
        "inputSchema": {"type": "object", "properties": {
            "sammlung_id": _s("integer", ""),
            "nr": _s("integer", "Nummer im Lehrwerk"),
            "titel": _s("string", "Überschrift der Lektion"),
            "beschreibung": _s("string", "wahlweise")},
            "required": ["sammlung_id", "nr"]},
        "funktion": lektion_anlegen,
    },
    {
        "name": "lektionen_auflisten",
        "description": "Welche Lektionen gibt es in dieser Sammlung, und wie "
                       "viele Wörter hängen daran?",
        "inputSchema": {"type": "object", "properties": {
            "sammlung_id": _s("integer", "")}, "required": ["sammlung_id"]},
        "funktion": lektionen_auflisten,
    },
    {
        "name": "vokabel_nachschlagen",
        "description": "Im Bestand nachschlagen — über Lemma, ALLE Formen und "
                       "alle Übersetzungen. Vor dem Anlegen benutzen, um "
                       "Doppelte zu vermeiden. Sagt auch, an welcher Stelle "
                       "ein Eintrag gefunden wurde und welche Form das ist.",
        "inputSchema": {"type": "object", "properties": {
            "sammlung_id": _s("integer", ""),
            "suche": _s("string", "Wort, Form oder Übersetzung"),
            "anzahl": _s("integer", "höchstens so viele Treffer")},
            "required": ["sammlung_id", "suche"]},
        "funktion": vokabel_nachschlagen,
    },
    {
        "name": "vokabel_lesen",
        "description": "Einen Eintrag mit allen Formen, Bedeutungen und "
                       "Form-Kennungen lesen — etwa um eine Form zu "
                       "berichtigen (form_aendern) oder eine fehlende "
                       "nachzutragen (formen_ergaenzen).",
        "inputSchema": {"type": "object", "properties": {
            "lexem_id": _s("integer", "")}, "required": ["lexem_id"]},
        "funktion": vokabel_lesen,
    },
    {
        "name": "formen_ergaenzen",
        "description": "Einem bestehenden Eintrag Formen hinzufügen, etwa eine "
                       "weitere Zeit. " + MERKMALSHINWEIS,
        "inputSchema": {"type": "object", "properties": {
            "lexem_id": _s("integer", ""),
            "formen": _s("array", "wie bei vokabel_anlegen",
                         items={"type": "object"}),
            "als_geprueft": _s("boolean", "nur auf ausdrücklichen Wunsch")},
            "required": ["lexem_id", "formen"]},
        "funktion": formen_ergaenzen,
    },
    {
        "name": "eintrag_pruefen",
        "description": "Prüft, ob ein Eintrag die Fähigkeiten des Trainers "
                       "nutzen kann: Übersetzung da? Paradigma vollständig? "
                       "Stamm ableitbar? Formen in einer Formgruppe?",
        "inputSchema": {"type": "object", "properties": {
            "lexem_id": _s("integer", "")}, "required": ["lexem_id"]},
        "funktion": eintrag_pruefen,
    },
    {
        "name": "sammlung_pruefen",
        "description": "Alle Einträge einer Sammlung auf einmal prüfen. Gut "
                       "nach einem größeren Eintragen.",
        "inputSchema": {"type": "object", "properties": {
            "sammlung_id": _s("integer", ""),
            "nur_mangelhafte": _s("boolean", "nur auffällige Einträge zeigen")},
            "required": ["sammlung_id"]},
        "funktion": sammlung_pruefen,
    },
    {
        "name": "sprachprofil_lesen",
        "description": "Das wirksame Sprachprofil ansehen: Prüfregeln, Artikel, "
                       "Formgruppen, erlaubte Lexemmerkmale.",
        "inputSchema": {"type": "object", "properties": {
            "sprache": _s("string", "")}, "required": ["sprache"]},
        "funktion": sprachprofil_lesen,
    },
    {
        "name": "sprachprofil_anpassen",
        "description":
            "Ein Sprachprofil ändern, damit die Sprache abfragbar wird — ohne "
            "Codeänderung. Formgruppen werden je Wortart gemischt: gleiche "
            "Kennung ersetzt, neue kommen hinzu. Nur Übergebenes ändert sich.\n\n"
            "Eine Formgruppe braucht kennung, name, kurz, merkmale (was alle "
            "Zellen gemeinsam haben) und zellen (die einzelnen Bündel). Jede "
            "Zelle MUSS die gemeinsamen Merkmale tragen.\n\n"
            "Vor einer Änderung sprachprofil_lesen aufrufen. Änderungen wirken "
            "sofort und auf den ganzen Bestand dieser Sprache — bei einer "
            "Sprache, in der schon gelernt wird, vorher mit der Benutzerin "
            "abstimmen.",
        "inputSchema": {"type": "object", "properties": {
            "sprache": _s("string", ""),
            "profil": _s("object", "zu überschreibende Teile: pruefung, "
                                   "artikel, formgruppen, formgruppen_standard, "
                                   "stammformen, lexemmerkmale, name, stimme")},
            "required": ["sprache", "profil"]},
        "nur_verwalter": True,
        "funktion": sprachprofil_anpassen,
    },
    {
        "name": "sprache_einrichten",
        "description": "Eine Sprache anlegen, die es im Code noch nicht gibt. "
                       "Profilaufbau wie bei sprachprofil_anpassen.",
        "inputSchema": {"type": "object", "properties": {
            "code": _s("string", "ISO-Kennung, z.B. mn, la, ru"),
            "name": _s("string", "deutscher Name"),
            "schrift": _s("string", "latein, griechisch, kyrillisch …"),
            "stimme": _s("string", "BCP47 für die Sprachsynthese, z.B. ru-RU. "
                                   "Für tote Sprachen weglassen — eine falsche "
                                   "Stimme ist irreführender als gar keine."),
            "profil": _s("object", "wie bei sprachprofil_anpassen")},
            "required": ["code", "name", "profil"]},
        "nur_verwalter": True,
        "funktion": sprache_einrichten,
    },
    {
        "name": "offene_woerter_lesen",
        "description": "Wörter, die sie beim Lesen eines Textes als »kenne "
                       "ich nicht« markiert hat und eingetragen haben "
                       "möchte. Mit Zusammenhang, also dem Satz, in dem das "
                       "Wort stand — daran hängt, welche Bedeutung gemeint "
                       "ist. Nach dem Anlegen offenes_wort_erledigen "
                       "aufrufen, sonst steht das Wort weiter auf der "
                       "Liste.\n\n"
                       "Geordnet nach Häufigkeit im Text. Bei einem ganzen "
                       "Artikel stehen schnell hunderte darauf, und dann "
                       "ist die Reihenfolge das Wichtigste: oben anfangen "
                       "lohnt sich auch, wenn man nicht durchkommt.\n\n"
                       "FLEKTIERTE FORMEN brauchen keine neue Vokabel: "
                       "steht das Lemma schon im Bestand, gehört die Form "
                       "dorthin ergänzt (formen_ergaenzen) und nicht als "
                       "zweites Lemma angelegt. Mit offenes_wort_erledigen "
                       "abhaken und kurz sagen, wohin sie ergänzt "
                       "wurde.\n\n"
                       "EIGENNAMEN in der Schrift der Lernsprache gehören "
                       "SEHR WOHL angelegt — ein griechischer Nachname oder "
                       "Ortsname ist für jemanden, der die Schrift erst "
                       "lernt, genauso unlesbar wie jedes andere Wort. "
                       "»Die weiß ich ja auch nicht.« Als Bedeutung die "
                       "Umschrift und wofür der Name steht "
                       "(»Μπουτάκογλου — Butakoglou, Nachname«; "
                       "»Θεσσαλονίκη — Thessaloniki, Stadt in "
                       "Nordgriechenland«), als Wortart das Substantiv, und "
                       "beim Ortsnamen das Genus dazu, denn das trägt er. "
                       "Nicht anzulegen sind nur Namen, die ohnehin "
                       "lateinisch dastehen (»AfD«, »Deutschland«) — die "
                       "sind schon lesbar und sagen ihr nichts Neues.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "sammlung_id": _s("integer", "nur diese Sammlung; ohne "
                                             "Angabe alle"),
                "anzahl": _s("integer", "wie viele auf einmal, "
                                        "Vorgabe 40, höchstens 200")},
        },
        "funktion": offene_woerter_lesen,
    },
    {
        "name": "offenes_wort_erledigen",
        "description": "Haken an einen Wortwunsch, nachdem die Vokabel "
                       "angelegt ist. lexem_id mitgeben, damit sie "
                       "nachvollziehen kann, woher der Eintrag stammt.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "wunsch_id": _s("integer", "aus offene_woerter_lesen"),
                "lexem_id": _s("integer", "die angelegte Vokabel")},
            "required": ["wunsch_id"],
        },
        "funktion": offenes_wort_erledigen,
    },
    {
        "name": "texte_auflisten",
        "description": "Welche Lesetexte liegen in einer Sammlung?",
        "inputSchema": {
            "type": "object",
            "properties": {
                "sammlung_id": _s("integer", "aus sammlungen_auflisten")},
            "required": ["sammlung_id"],
        },
        "funktion": texte_auflisten,
    },
    {
        "name": "text_anlegen",
        "description": "Einen Lesetext hinterlegen. Absätze durch Leerzeilen "
                       "trennen — daran entstehen die Abschnitte, in denen "
                       "übersetzt wird. Danach text_deckung_lesen aufrufen: "
                       "es sagt, welche Wörter ihr dafür noch fehlen.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "sammlung_id": _s("integer", "aus sammlungen_auflisten"),
                "titel": _s("string", "kurz, zum Wiederfinden"),
                "inhalt": _s("string", "der Text in der Lernsprache"),
                "niveau": _s("string", "A1 … C2, frei"),
                "notiz": _s("string", "woher er stammt, worum es geht")},
            "required": ["sammlung_id", "titel", "inhalt"],
        },
        "funktion": text_anlegen,
    },
    {
        "name": "text_deckung_lesen",
        "description": "Welche Wörter eines Textes stehen noch nicht in "
                       "ihrem Wortschatz? Nennt die Lücken namentlich. "
                       "Achtung: eine nicht eingetragene FORM gilt als "
                       "Lücke, auch wenn das Lemma längst da ist — dann "
                       "gehört die Form ergänzt (formen_ergaenzen), nicht "
                       "eine zweite Vokabel angelegt.",
        "inputSchema": {
            "type": "object",
            "properties": {"text_id": _s("integer", "aus texte_auflisten")},
            "required": ["text_id"],
        },
        "funktion": text_deckung_lesen,
    },
    {
        "name": "lehrgang_lesen",
        "description": "Die Lektionen einer Sammlung und ihre Formgruppen "
                       "(Zeiten, Fall-Tabellen), um zuzuordnen, ab welcher "
                       "Lektion das Lehrwerk welche Form einführt. Wer das "
                       "eingetragen hat, bekommt keine Zeitform abgefragt, "
                       "die im Buch noch nicht vorkam. Enthält einen "
                       "groben Namensvorschlag des Trainers — der ist "
                       "reine Wortsuche und oft daneben, besonders bei "
                       "Lektionen, die zwei Dinge auf einmal einführen.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "sammlung_id": _s("integer", "aus sammlungen_auflisten")},
            "required": ["sammlung_id"],
        },
        "funktion": lehrgang_lesen,
    },
    {
        "name": "lehrgang_zuordnen",
        "description": "Trägt ein, ab welcher Lektion welche Formgruppe "
                       "gilt. Die Zuordnung wird als GANZES ersetzt — also "
                       "vorher lehrgang_lesen und alles mitschicken, was "
                       "bleiben soll. Eine weggelassene Gruppe heißt »gilt "
                       "von Anfang an«.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "sammlung_id": _s("integer", "aus sammlungen_auflisten"),
                "zuordnung": _s("object",
                                "Formgruppen-Kennung -> Lektionsnummer, "
                                'z.B. {"aoristos": 39, "enestotas": 14}')},
            "required": ["sammlung_id", "zuordnung"],
        },
        "funktion": lehrgang_zuordnen,
    },
    {
        "name": "text_lesen",
        "description": "Einen Lesetext mit seinen Abschnitten. Jeder "
                       "Abschnitt hat eine Kennung — die braucht "
                       "text_uebersetzen.",
        "inputSchema": {
            "type": "object",
            "properties": {"text_id": _s("integer", "aus texte_auflisten")},
            "required": ["text_id"],
        },
        "funktion": text_lesen,
    },
    {
        "name": "text_uebersetzen",
        "description": "Hinterlegt je Abschnitt eine Referenzübersetzung. "
                       "Sie erscheint im Text als aufklappbarer Vorschlag "
                       "— zum Vergleichen, NACHDEM man selbst übersetzt "
                       "hat. Die eigene Fassung wird dabei nicht "
                       "angerührt. Übersetze so, wie es im Unterricht "
                       "gälte: nah am Original, aber in gutem Deutsch.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "text_id": _s("integer", "aus texte_auflisten"),
                "fassungen": _s("object",
                                "Abschnitts-Kennung -> Übersetzung, "
                                'z.B. {"12": "Das Kind liest ein Buch."}')},
            "required": ["text_id", "fassungen"],
        },
        "funktion": text_uebersetzen,
    },
    {
        "name": "beispiele_setzen",
        "description": "Beispielsätze zu einem Wort, wie in einem "
                       "Wörterbuch: ein Satz, der zeigt, wie das Wort "
                       "benutzt wird, mit Übersetzung. Gehört ein Satz zu "
                       "einer bestimmten Bedeutung, `bedeutung_id` "
                       "mitgeben — bei »to go« gehört der Satz mit dem Auto "
                       "zu »fahren«, nicht zu »gehen«; die Kennungen kommen "
                       "aus vokabel_lesen.\n\n"
                       "Die Liste wird als GANZES ersetzt: vorher "
                       "vokabel_lesen, sonst wirfst du weg, was schon "
                       "dasteht. Kurze, alltägliche Sätze, die nur Wörter "
                       "aus dem schon gelernten Umfeld benutzen — ein "
                       "Beispielsatz, den man selbst nicht lesen kann, "
                       "erklärt nichts.\n\n"
                       "Beispielsätze werden nicht abgefragt und brauchen "
                       "keine Freigabe.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "lexem_id": _s("integer", "aus vokabeln_auflisten"),
                "beispiele": _s("array",
                                '[{"satz": …, "uebersetzung": …, '
                                '"bedeutung_id": …}]',
                                items={"type": "object"})},
            "required": ["lexem_id", "beispiele"],
        },
        "funktion": beispiele_setzen,
    },
    {
        "name": "erklaerung_setzen",
        "description": "Ein Erklärsatz zu EINER Bedeutung — was sie "
                       "bedeutet, in eigenen Worten, wie die Zeile im "
                       "Duden. Nicht zu verwechseln mit `kontext`: der "
                       "unterscheidet zwei Bedeutungen voneinander (»mit "
                       "Fahrzeug«), die Erklärung sagt, was die Bedeutung "
                       "IST. Leerer Text löscht sie.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "bedeutung_id": _s("integer", "aus vokabel_lesen"),
                "erklaerung": _s("string", "ein bis zwei Sätze")},
            "required": ["bedeutung_id", "erklaerung"],
        },
        "funktion": erklaerung_setzen,
    },
]

NACH_NAME = {w["name"]: w for w in WERKZEUGE}


# ------------------------------------------------- Protokollabwicklung

def _text(inhalt: Any, fehler: bool = False) -> dict:
    import json
    antwort = {"content": [{"type": "text",
                            "text": json.dumps(inhalt, ensure_ascii=False,
                                               indent=2)}]}
    if fehler:
        antwort["isError"] = True
    return antwort


# Mitschreiben, WELCHES Werkzeug gerufen wurde und ob es geklappt hat.
#
# Der Anlass: ChatGPT meldete »ich verbessere gerade die bestehenden
# Einträge«, machte 43 Aufrufe in siebzig Sekunden — und in der
# Datenbank änderte sich keine einzige Zeile. Im Zugriffsprotokoll
# stand nur »POST /mcp 200«, denn ein GESCHEITERTER Werkzeugaufruf
# kommt bei MCP ebenfalls mit 200 zurück; der Fehler steckt im Rumpf.
# Damit ließ sich nicht unterscheiden, ob die KI liest, ob sie
# schreiben will und abgewiesen wird, oder ob sie etwas erzählt, was
# sie gar nicht tut.
#
# Mitgeschrieben wird der Name des Werkzeugs, wer es gerufen hat und
# das Ergebnis — bei einem Fehler dessen Text. NICHT die Argumente:
# die enthalten ganze Vokabeleinträge, das Protokoll wäre nach einer
# Sitzung unlesbar und bei den Texten stünde halbe Privatlektüre
# darin.
protokoll = logging.getLogger("vokabeltrainer.mcp")


def behandeln(nachricht: dict, db: sqlite3.Connection,
              person: dict) -> dict | None:
    """Beantwortet eine JSON-RPC-Nachricht. None heißt: keine Antwort nötig
    (das ist bei Benachrichtigungen so)."""
    methode = nachricht.get("method")
    kennung = nachricht.get("id")
    parameter = nachricht.get("params") or {}

    def antwort(ergebnis=None, fehler=None):
        n = {"jsonrpc": "2.0", "id": kennung}
        if fehler is not None:
            n["error"] = fehler
        else:
            n["result"] = ergebnis
        return n

    if methode == "initialize":
        return antwort({
            "protocolVersion": parameter.get("protocolVersion") or PROTOKOLL,
            "capabilities": {"tools": {}},
            "serverInfo": {"name": NAME, "version": VERSION},
            "instructions": ANLEITUNG + (
                f" Angemeldet als {person['name']}; alles geschieht in "
                f"diesem Namen und nur auf diesem Bestand."),
        })
    if methode and methode.startswith("notifications/"):
        return None
    if methode == "ping":
        return antwort({})
    if methode == "tools/list":
        # Was die Person nicht darf, wird gar nicht erst angeboten — sonst
        # probiert der Agent es und bekommt eine Absage, die er nicht
        # einordnen kann.
        verwalter = bool(person.get("verwalter"))
        return antwort({"tools": [{k: w[k] for k in
                                   ("name", "description", "inputSchema")}
                                  for w in WERKZEUGE
                                  if verwalter or not w.get("nur_verwalter")]})
    if methode == "tools/call":
        name = parameter.get("name")
        werkzeug = NACH_NAME.get(name)
        if werkzeug is None:
            # Auch das gehört ins Protokoll: ein Agent, der ein Werkzeug
            # ruft, das es nicht gibt, hat eine falsche Vorstellung vom
            # Server — und das sieht man sonst nirgends.
            protokoll.warning("%s · %s · UNBEKANNTES WERKZEUG",
                              person.get("name", "?"), name)
            return antwort(fehler={"code": -32602,
                                   "message": f"Unbekanntes Werkzeug: {name}"})
        wer = person.get("name", "?")
        try:
            ergebnis = werkzeug["funktion"](db, person,
                                            **(parameter.get("arguments") or {}))
            protokoll.info("%s · %s · ok", wer, name)
            return antwort(_text(ergebnis))
        except zugang.NichtErlaubt as f:
            protokoll.warning("%s · %s · NICHT ERLAUBT: %s", wer, name, f)
            return antwort(_text({"fehler": str(f), "art": "nicht_erlaubt"},
                                 fehler=True))
        except WerkzeugFehler as f:
            protokoll.warning("%s · %s · abgelehnt: %s", wer, name, f)
            return antwort(_text({"fehler": str(f)}, fehler=True))
        except TypeError as f:
            protokoll.warning("%s · %s · falsche Angaben: %s", wer, name, f)
            return antwort(_text({"fehler": f"Falsche Angaben für {name}: {f}"},
                                 fehler=True))
        except Exception as f:                              # noqa: BLE001
            protokoll.exception("%s · %s · FEHLER", wer, name)
            return antwort(_text({"fehler": f"{type(f).__name__}: {f}"},
                                 fehler=True))
    if kennung is not None:
        return antwort(fehler={"code": -32601,
                               "message": f"Unbekannte Methode: {methode}"})
    return None
