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

import zugang

VERSION = "0.2.0"
NAME = "vokabeltrainer"
PROTOKOLL = "2025-06-18"

ANLEITUNG = (
    "Vokabeltrainer im Heimnetz. Reihenfolge: sammlungen_auflisten, dann "
    "formgruppen_zeigen für die Sprache, dann eintragen. Vollständige "
    "Paradigmen liefern — der Trainer erzeugt daraus die Aufgaben und leitet "
    "den Wortstamm ab. Eingetragene Formen bleiben ungeprüft, bis ein Mensch "
    "sie freigibt."
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
        "sammlungen": _fehler_wandeln(a.sammlungen_liste, person["id"], db),
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
                       "zuschalten."}


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
                    "Freigabe durch einen Menschen in der Oberfläche oder mit "
                    "formen_bestaetigen.") if not als_geprueft else None,
    }


def vokabel_lesen(db: sqlite3.Connection, person: dict, lexem_id: int):
    zugang.lexem_pruefen(db, person["id"], lexem_id)
    lexem = _fehler_wandeln(_app().lexem_lesen, lexem_id, db)
    return {
        "lexem_id": lexem["id"], "lemma": lexem["lemma"],
        "wortart": lexem["wortart"], "merkmale": lexem["merkmale"],
        "sprache": lexem["sprache"],
        "formen": [{"id": f["id"], "text": f["text"], "merkmale": f["merkmale"],
                    "beschriftung": f["beschriftung"],
                    "geprueft": bool(f["geprueft"]), "quelle": f["quelle"],
                    "gruppe": f["gruppe"]} for f in lexem["formen"]],
        "bedeutungen": [{"id": b["id"], "kontext": b["kontext"],
                         "uebersetzungen": [u["text"] for u in b["uebersetzungen"]]}
                        for b in lexem["bedeutungen"]],
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


def formen_bestaetigen(db: sqlite3.Connection, person: dict, form_ids: list):
    a = _app()
    for form_id in form_ids:
        zugang.form_pruefen(db, person["id"], form_id)
        _fehler_wandeln(a.form_bestaetigen, form_id, db)
    return {"bestaetigt": len(form_ids)}


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

def _s(typ, beschreibung, **rest):
    return {"type": typ, "description": beschreibung, **rest}


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
                "erlaubt ist, sagt formgruppen_zeigen unter lexemmerkmale."),
            "notiz": _s("string", "freier Vermerk"),
            "als_geprueft": _s("boolean",
                "Nur auf ausdrücklichen Wunsch der Benutzerin auf true setzen. "
                "Sonst bleiben die Formen bis zur Freigabe unabgefragt."),
        }, "required": ["sammlung_id", "lemma", "wortart", "bedeutungen"]},
        "funktion": vokabel_anlegen,
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
                       "Form-Kennungen lesen. Die Kennungen braucht man für "
                       "formen_bestaetigen.",
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
        "name": "formen_bestaetigen",
        "description": "Formen als geprüft markieren — erst danach werden sie "
                       "abgefragt. NUR benutzen, wenn ein Mensch sie angesehen "
                       "hat oder die Benutzerin ausdrücklich darum bittet. "
                       "Nicht selbst die eigenen Einträge freigeben.",
        "inputSchema": {"type": "object", "properties": {
            "form_ids": _s("array", "Kennungen aus vokabel_lesen",
                           items={"type": "integer"})},
            "required": ["form_ids"]},
        "funktion": formen_bestaetigen,
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
            return antwort(fehler={"code": -32602,
                                   "message": f"Unbekanntes Werkzeug: {name}"})
        try:
            ergebnis = werkzeug["funktion"](db, person,
                                            **(parameter.get("arguments") or {}))
            return antwort(_text(ergebnis))
        except zugang.NichtErlaubt as f:
            return antwort(_text({"fehler": str(f), "art": "nicht_erlaubt"},
                                 fehler=True))
        except WerkzeugFehler as f:
            return antwort(_text({"fehler": str(f)}, fehler=True))
        except TypeError as f:
            return antwort(_text({"fehler": f"Falsche Angaben für {name}: {f}"},
                                 fehler=True))
        except Exception as f:                              # noqa: BLE001
            return antwort(_text({"fehler": f"{type(f).__name__}: {f}"},
                                 fehler=True))
    if kennung is not None:
        return antwort(fehler={"code": -32601,
                               "message": f"Unbekannte Methode: {methode}"})
    return None
