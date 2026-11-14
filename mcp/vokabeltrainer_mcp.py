#!/usr/bin/env python3
"""MCP-Server für den Vokabeltrainer.

Spricht über die HTTP-Schnittstelle mit dem Trainer. Keine Fremdpakete, nur
die Standardbibliothek — damit er in fünf Jahren noch startet.

    VOKABEL_URL=http://familienserver:8020 python3 vokabeltrainer_mcp.py

Der Server tut mehr, als Daten durchzureichen: nach jedem Anlegen läuft die
Qualitätsprüfung mit und ihr Ergebnis geht in die Antwort zurück. Der Agent
erfährt also unmittelbar, ob sein Eintrag die Fähigkeiten des Trainers
überhaupt nutzen kann — ob der Stamm ableitbar ist, ob das Paradigma Lücken
hat, ob eine Übersetzung fehlt. Ohne das entstünden formal gültige und
inhaltlich nutzlose Einträge.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

ADRESSE = os.environ.get("VOKABEL_URL", "http://localhost:8020").rstrip("/")
NAME = "vokabeltrainer"
VERSION = "0.1.0"
PROTOKOLL = "2025-06-18"


# ------------------------------------------------------------------- HTTP

class TrainerFehler(Exception):
    pass


def ruf(pfad: str, methode: str = "GET", daten=None, frage=None):
    adresse = f"{ADRESSE}/api{pfad}"
    if frage:
        sauber = {k: v for k, v in frage.items() if v is not None}
        if sauber:
            adresse += "?" + urllib.parse.urlencode(sauber, doseq=True)
    leib = json.dumps(daten).encode() if daten is not None else None
    anfrage = urllib.request.Request(
        adresse, data=leib, method=methode,
        headers={"Content-Type": "application/json"} if leib else {})
    try:
        with urllib.request.urlopen(anfrage, timeout=30) as antwort:
            inhalt = antwort.read().decode()
            return json.loads(inhalt) if inhalt else None
    except urllib.error.HTTPError as fehler:
        text = fehler.read().decode()
        try:
            einzelheit = json.loads(text).get("detail")
        except json.JSONDecodeError:
            einzelheit = text
        if isinstance(einzelheit, list):
            einzelheit = "; ".join(
                f"{' → '.join(str(t) for t in f.get('loc', []) if t != 'body')}: {f.get('msg')}"
                for f in einzelheit)
        raise TrainerFehler(f"{fehler.code}: {einzelheit}") from fehler
    except urllib.error.URLError as fehler:
        raise TrainerFehler(
            f"Der Trainer ist unter {ADRESSE} nicht erreichbar ({fehler.reason}). "
            f"Läuft er? Stimmt VOKABEL_URL?") from fehler


# ------------------------------------------------------------- Werkzeuge

def _bericht_kurz(bericht: dict) -> dict:
    """Die Qualitätsprüfung in der Form, in der sie dem Agenten nützt."""
    return {
        "brauchbar": bericht["gut"],
        "aufgaben_entstanden": bericht["aufgaben_aktiv"],
        "ungepruefte_formen": bericht["ungeprueft"],
        "befunde": [
            {"schwere": b["schwere"], "art": b["art"], "text": b["text"],
             **({"betrifft": b["betrifft"]} if b["betrifft"] else {}),
             **({"rat": b["rat"]} if b["rat"] else {})}
            for b in bericht["befunde"]
        ],
    }


def sammlungen_auflisten(benutzer_id: int | None = None):
    """Welche Sammlungen gibt es, und wie heißen ihre Kennungen?"""
    leute = ruf("/benutzer")
    if benutzer_id is None:
        if not leute:
            return {"hinweis": "Es gibt noch kein Profil. Erst eines in der "
                               "Oberfläche anlegen.", "benutzer": []}
        benutzer_id = leute[0]["id"]
    return {
        "benutzer": leute,
        "benutzer_id": benutzer_id,
        "sammlungen": ruf("/sammlungen", frage={"benutzer_id": benutzer_id}),
    }


def formgruppen_zeigen(sprache: str):
    """Welche Formgruppen hat diese Sprache, und welche Merkmale tragen sie?

    IMMER vor dem ersten Eintragen in einer Sprache aufrufen — daraus ergibt
    sich, welche Merkmalsbündel die Formen tragen müssen.
    """
    gruppen = ruf(f"/sprachen/{sprache}/formgruppen")
    ausfuehrlich = {}
    for wortart, liste in gruppen["wortarten"].items():
        ausfuehrlich[wortart] = []
        for g in liste:
            zellen = ruf(f"/sprachen/{sprache}/formgruppen/"
                         f"{urllib.parse.quote(g['kennung'])}/zellen")
            ausfuehrlich[wortart].append({
                "kennung": g["kennung"], "name": g["name"],
                "voreingestellt": g["kennung"] in gruppen["standard"],
                "zellen": [{"merkmale": z["merkmale"],
                            "beschriftung": z["beschriftung"]} for z in zellen],
            })
    return {
        "sprache": gruppen["sprache"],
        "stammformen": gruppen["stammformen"],
        "lexemmerkmale": gruppen["lexemmerkmale"],
        "wortarten": ausfuehrlich,
        "hinweis": "Jede Form braucht das Merkmalsbündel ihrer Zelle, genau so "
                   "wie es hier steht. Nicht voreingestellte Formgruppen dürfen "
                   "trotzdem befüllt werden — sie lassen sich später zuschalten.",
    }


def merkmale_zeigen():
    """Das erlaubte Merkmalsvokabular. Alles andere wird abgelehnt."""
    return ruf("/merkmale")


def vokabel_anlegen(sammlung_id: int, lemma: str, wortart: str,
                    bedeutungen: list, formen: list | None = None,
                    merkmale: dict | None = None, notiz: str | None = None,
                    als_geprueft: bool = False):
    """Ein vollständiges Wort anlegen und sofort prüfen lassen."""
    formen = list(formen or [])
    for f in formen:
        f.setdefault("quelle", "ki")
        f.setdefault("geprueft", als_geprueft)
    sauber_bedeutungen = []
    for b in bedeutungen:
        ue = b.get("uebersetzungen") or []
        sauber_bedeutungen.append({
            "uebersetzungen": [
                {"text": u, "quelle": "ki"} if isinstance(u, str)
                else {**u, "quelle": u.get("quelle", "ki")} for u in ue],
            "kontext": b.get("kontext"),
            "reihenfolge": b.get("reihenfolge", 0),
        })
    lexem = ruf("/lexeme", "POST", {
        "sammlung_id": sammlung_id, "lemma": lemma, "wortart": wortart,
        "merkmale": merkmale or {}, "notiz": notiz,
        "formen": formen, "bedeutungen": sauber_bedeutungen,
    })
    bericht = ruf(f"/lexeme/{lexem['id']}/pruefung")
    return {
        "lexem_id": lexem["id"],
        "lemma": lexem["lemma"],
        "formen_angelegt": len(lexem["formen"]),
        "pruefung": _bericht_kurz(bericht),
        "hinweis": ("Die Formen sind als ungeprüft eingetragen und werden noch "
                    "nicht abgefragt. Das ist Absicht: eine erfundene Form, die "
                    "unbemerkt gepaukt wird, ist schlimmer als eine fehlende. "
                    "Freigabe durch einen Menschen in der Oberfläche oder mit "
                    "formen_bestaetigen.") if not als_geprueft else None,
    }


def vokabel_lesen(lexem_id: int):
    """Einen Eintrag mit allen Formen und Bedeutungen lesen."""
    lexem = ruf(f"/lexeme/{lexem_id}")
    return {
        "lexem_id": lexem["id"], "lemma": lexem["lemma"],
        "wortart": lexem["wortart"], "merkmale": lexem["merkmale"],
        "sprache": lexem["sprache"],
        "formen": [{"id": f["id"], "text": f["text"], "merkmale": f["merkmale"],
                    "beschriftung": f["beschriftung"], "geprueft": bool(f["geprueft"]),
                    "quelle": f["quelle"], "gruppe": f["gruppe"]}
                   for f in lexem["formen"]],
        "bedeutungen": [{"id": b["id"], "kontext": b["kontext"],
                         "uebersetzungen": [u["text"] for u in b["uebersetzungen"]]}
                        for b in lexem["bedeutungen"]],
        "aufgaben_aktiv": len([a for a in lexem["aufgaben"] if a["aktiv"]]),
    }


def vokabel_nachschlagen(sammlung_id: int, suche: str, anzahl: int = 10):
    """Im Bestand nachschlagen — über Lemma, alle Formen und alle Übersetzungen."""
    ergebnis = ruf(f"/sammlungen/{sammlung_id}/woerterbuch",
                   frage={"suche": suche, "anzahl": anzahl})
    return {
        "suche": ergebnis["suche"], "gefunden": ergebnis["gefunden"],
        "eintraege": [{
            "lexem_id": e["id"], "lemma": e["lemma"], "wortart": e["wortart"],
            "bedeutungen": [", ".join(u["text"] for u in b["uebersetzungen"])
                            for b in e["bedeutungen"]],
            "gefunden_bei": e["fundstellen"],
        } for e in ergebnis["eintraege"]],
    }


def formen_ergaenzen(lexem_id: int, formen: list, als_geprueft: bool = False):
    """Einem bestehenden Eintrag Formen hinzufügen."""
    angelegt = []
    for f in formen:
        eintrag = {**f, "quelle": f.get("quelle", "ki"),
                   "geprueft": f.get("geprueft", als_geprueft)}
        angelegt.append(ruf(f"/lexeme/{lexem_id}/formen", "POST", eintrag)["id"])
    return {"angelegt": len(angelegt), "form_ids": angelegt,
            "pruefung": _bericht_kurz(ruf(f"/lexeme/{lexem_id}/pruefung"))}


def formen_bestaetigen(form_ids: list):
    """Formen als geprüft markieren — erst danach werden sie abgefragt.

    Nur benutzen, wenn ein Mensch sie wirklich angesehen hat oder wenn die
    Benutzerin ausdrücklich darum gebeten hat.
    """
    for form_id in form_ids:
        ruf(f"/formen/{form_id}/bestaetigen", "POST")
    return {"bestaetigt": len(form_ids)}


def eintrag_pruefen(lexem_id: int):
    """Taugt dieser Eintrag für das, was der Trainer kann?"""
    return _bericht_kurz(ruf(f"/lexeme/{lexem_id}/pruefung"))


def sammlung_pruefen(sammlung_id: int, nur_mangelhafte: bool = True):
    """Alle Einträge einer Sammlung auf einmal prüfen."""
    bericht = ruf(f"/sammlungen/{sammlung_id}/pruefung",
                  frage={"nur_mangelhafte": str(nur_mangelhafte).lower()})
    return {
        "geprueft": bericht["geprueft"], "zaehler": bericht["zaehler"],
        "eintraege": [{"lexem_id": e["lexem_id"], "lemma": e["lemma"],
                       **_bericht_kurz(e)} for e in bericht["eintraege"]],
    }


def sprachprofil_lesen(sprache: str):
    """Das wirksame Sprachprofil ansehen — Code plus eigene Überschreibungen."""
    return ruf(f"/sprachen/{sprache}/profil")


def sprachprofil_anpassen(sprache: str, profil: dict):
    """Ein Sprachprofil anpassen, damit die Sprache abfragbar wird.

    Damit lässt sich eine Sprache einrichten, ohne dass jemand Code ändert:
    Formgruppen anfügen, Prüfregeln justieren, Artikel eintragen. Nur was
    übergeben wird, ändert sich.
    """
    return ruf(f"/sprachen/{sprache}/profil", "PUT",
               {"profil": profil, "neu_rechnen": True})


def sprache_einrichten(code: str, name: str, profil: dict,
                       schrift: str = "latein", stimme: str | None = None):
    """Eine neue Sprache anlegen, die es im Code noch nicht gibt."""
    return ruf("/sprachen", "POST", {
        "code": code, "name": name, "schrift": schrift,
        "stimme": stimme, "profil": profil})


# --------------------------------------------------- Beschreibung der Werkzeuge

def _s(typ, beschreibung, **rest):
    return {"type": typ, "description": beschreibung, **rest}


MERKMALSHINWEIS = (
    "Formen tragen Merkmalsbündel, keine Spaltennamen: "
    '{"modus":"indikativ","tempus":"praesens","person":"1","numerus":"sg"}. '
    "Die Person ist eine Zeichenkette. Welche Bündel eine Sprache kennt, sagt "
    "formgruppen_zeigen — das ist vor dem ersten Eintragen aufzurufen."
)

WERKZEUGE = [
    {
        "name": "sammlungen_auflisten",
        "description": "Profile und Sammlungen mit ihren Kennungen. Der erste "
                       "Aufruf in jeder Sitzung — ohne sammlung_id geht nichts.",
        "inputSchema": {"type": "object", "properties": {
            "benutzer_id": _s("integer", "Profil; ohne Angabe das erste")}},
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
        "funktion": sprache_einrichten,
    },
]

NACH_NAME = {w["name"]: w for w in WERKZEUGE}


# ----------------------------------------------------------- JSON-RPC über stdio

def _antwort(kennung, ergebnis=None, fehler=None):
    nachricht = {"jsonrpc": "2.0", "id": kennung}
    if fehler is not None:
        nachricht["error"] = fehler
    else:
        nachricht["result"] = ergebnis
    sys.stdout.write(json.dumps(nachricht, ensure_ascii=False) + "\n")
    sys.stdout.flush()


def _text(inhalt) -> dict:
    return {"content": [{"type": "text",
                         "text": json.dumps(inhalt, ensure_ascii=False, indent=2)}]}


def behandeln(nachricht: dict) -> None:
    methode = nachricht.get("method")
    kennung = nachricht.get("id")
    parameter = nachricht.get("params") or {}

    if methode == "initialize":
        gewuenscht = parameter.get("protocolVersion") or PROTOKOLL
        _antwort(kennung, {
            "protocolVersion": gewuenscht,
            "capabilities": {"tools": {}},
            "serverInfo": {"name": NAME, "version": VERSION},
            "instructions":
                "Vokabeltrainer im Heimnetz. Reihenfolge: sammlungen_auflisten, "
                "dann formgruppen_zeigen für die Sprache, dann eintragen. "
                "Vollständige Paradigmen liefern — der Trainer erzeugt daraus "
                "die Aufgaben und leitet den Wortstamm ab. Eingetragene Formen "
                "bleiben ungeprüft, bis ein Mensch sie freigibt.",
        })
    elif methode in ("notifications/initialized", "notifications/cancelled"):
        pass                                    # Benachrichtigung, keine Antwort
    elif methode == "ping":
        _antwort(kennung, {})
    elif methode == "tools/list":
        _antwort(kennung, {"tools": [
            {k: w[k] for k in ("name", "description", "inputSchema")}
            for w in WERKZEUGE]})
    elif methode == "tools/call":
        name = parameter.get("name")
        werkzeug = NACH_NAME.get(name)
        if werkzeug is None:
            _antwort(kennung, fehler={"code": -32602,
                                      "message": f"Unbekanntes Werkzeug: {name}"})
            return
        try:
            ergebnis = werkzeug["funktion"](**(parameter.get("arguments") or {}))
            _antwort(kennung, _text(ergebnis))
        except TrainerFehler as fehler:
            _antwort(kennung, {**_text({"fehler": str(fehler)}), "isError": True})
        except TypeError as fehler:
            _antwort(kennung, {**_text(
                {"fehler": f"Falsche Angaben für {name}: {fehler}"}),
                "isError": True})
        except Exception as fehler:                       # noqa: BLE001
            _antwort(kennung, {**_text(
                {"fehler": f"{type(fehler).__name__}: {fehler}"}), "isError": True})
    elif kennung is not None:
        _antwort(kennung, fehler={"code": -32601,
                                  "message": f"Unbekannte Methode: {methode}"})


def main() -> None:
    for zeile in sys.stdin:
        zeile = zeile.strip()
        if not zeile:
            continue
        try:
            nachricht = json.loads(zeile)
        except json.JSONDecodeError:
            continue
        try:
            behandeln(nachricht)
        except Exception as fehler:                       # noqa: BLE001
            if nachricht.get("id") is not None:
                _antwort(nachricht["id"],
                         fehler={"code": -32603, "message": str(fehler)})


if __name__ == "__main__":
    main()
