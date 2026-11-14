"""Grammatische Merkmale.

Formen werden nicht in festen Spalten gespeichert, sondern als Merkmalsbündel
beschrieben: {"person": "1", "numerus": "sg", "tempus": "praesens"}.

Hier steht das allgemeine Inventar mit deutschen Beschriftungen. Welche
Dimensionen und Werte eine Sprache tatsächlich benutzt — und wie sie sie
nennt ("Passé composé" statt "Perfekt") — steht im Sprachprofil, siehe
sprachen.py. Dieses Modul kennt keine einzelne Sprache.
"""

from __future__ import annotations

import json
import unicodedata

# Reihenfolge der Dimensionen in der Beschriftung. Sie folgt dem deutschen
# Sprachgebrauch: beim Verb "1. Person Singular Präsens Indikativ",
# beim Substantiv "Genitiv Singular".
REIHENFOLGE = (
    "nonfinit",
    "person",
    "kasus",
    "numerus",
    "genus",
    "stufe",
    "tempus",
    "aspekt",
    "modus",
    "genus_verbi",
    "flexion",
)

# Dimension -> Wert -> (lange Beschriftung, kurze Beschriftung)
INVENTAR: dict[str, dict[str, tuple[str, str]]] = {
    "nonfinit": {
        "infinitiv": ("Infinitiv", "Inf."),
        "partizip_praesens": ("Partizip Präsens", "Part. Präs."),
        "partizip_perfekt": ("Partizip Perfekt", "Part. Perf."),
        "gerundium": ("Gerundium", "Ger."),
        "supinum": ("Supinum", "Sup."),
    },
    "person": {
        "1": ("1. Person", "1."),
        "2": ("2. Person", "2."),
        "3": ("3. Person", "3."),
    },
    "numerus": {
        "sg": ("Singular", "Sg."),
        "pl": ("Plural", "Pl."),
    },
    "genus": {
        "m": ("maskulin", "m"),
        "f": ("feminin", "f"),
        "n": ("neutrum", "n"),
    },
    "kasus": {
        "nom": ("Nominativ", "Nom."),
        "gen": ("Genitiv", "Gen."),
        "dat": ("Dativ", "Dat."),
        "akk": ("Akkusativ", "Akk."),
        "vok": ("Vokativ", "Vok."),
        "abl": ("Ablativ", "Abl."),
    },
    "stufe": {
        "grund": ("Grundstufe", "Grundst."),
        "komparativ": ("Komparativ", "Komp."),
        "superlativ": ("Superlativ", "Sup."),
    },
    "tempus": {
        "praesens": ("Präsens", "Präs."),
        "imperfekt": ("Imperfekt", "Imperf."),
        "praeteritum": ("Präteritum", "Prät."),
        "aorist": ("Aorist", "Aor."),
        "perfekt": ("Perfekt", "Perf."),
        "plusquamperfekt": ("Plusquamperfekt", "Plusq."),
        "futur": ("Futur", "Fut."),
        "futur_perfekt": ("Futur II", "Fut. II"),
        "verlaufsform": ("Verlaufsform", "Verlaufsf."),
    },
    "aspekt": {
        # Im Neugriechischen bedeutungstragend: θα γράψω (einmalig) gegen
        # θα γράφω (fortgesetzt). Auch für slawische Sprachen gebraucht.
        "perfektiv": ("punktuell", "pkt."),
        "imperfektiv": ("fortgesetzt", "fortg."),
    },
    "modus": {
        "indikativ": ("Indikativ", "Ind."),
        "konjunktiv": ("Konjunktiv", "Konj."),
        "imperativ": ("Imperativ", "Imp."),
        "konditional": ("Konditional", "Kond."),
    },
    "flexion": {
        "stark": ("starke Flexion", "st."),
        "schwach": ("schwache Flexion", "schw."),
    },
    "genus_verbi": {
        "aktiv": ("Aktiv", "Akt."),
        "passiv": ("Passiv", "Pass."),
        "medium": ("Medium", "Med."),
    },
}

WORTARTEN: dict[str, str] = {
    "substantiv": "Substantiv",
    "verb": "Verb",
    "adjektiv": "Adjektiv",
    "adverb": "Adverb",
    "pronomen": "Pronomen",
    "artikel": "Artikel",
    "praeposition": "Präposition",
    "konjunktion": "Konjunktion",
    "numerale": "Zahlwort",
    "interjektion": "Interjektion",
    "wendung": "Wendung",
    "sonstiges": "Sonstiges",
}


class MerkmalFehler(ValueError):
    """Unbekannte Dimension oder unbekannter Wert."""


def pruefen(merkmale: dict) -> dict[str, str]:
    """Prüft ein Merkmalsbündel gegen das Inventar und gibt es normiert zurück.

    Werte werden als Zeichenketten geführt, damit {"person": 1} und
    {"person": "1"} denselben Aufgabenschlüssel ergeben.
    """
    if not isinstance(merkmale, dict):
        raise MerkmalFehler("Merkmale müssen ein Objekt sein")
    sauber: dict[str, str] = {}
    for dimension, wert in merkmale.items():
        if dimension not in INVENTAR:
            # Freie Zusatzmerkmale sind erlaubt, wenn sie als solche
            # gekennzeichnet sind: "x_" voran. So bleibt Raum für Sprachen,
            # die etwas brauchen, das hier noch nicht steht.
            if dimension.startswith("x_"):
                sauber[dimension] = str(wert)
                continue
            raise MerkmalFehler(f"Unbekannte Dimension: {dimension!r}")
        wert = str(wert)
        if wert not in INVENTAR[dimension]:
            erlaubt = ", ".join(sorted(INVENTAR[dimension]))
            raise MerkmalFehler(
                f"Unbekannter Wert {wert!r} für {dimension!r}. Erlaubt: {erlaubt}"
            )
        sauber[dimension] = wert
    return sauber


def schluessel(merkmale: dict) -> str:
    """Kanonische Zeichenkette eines Merkmalsbündels.

    Reihenfolgeunabhängig, damit Aufgabenschlüssel stabil bleiben.
    """
    teile = [f"{d}={merkmale[d]}" for d in sorted(merkmale)]
    return ",".join(teile)


def als_json(merkmale: dict) -> str:
    return json.dumps(merkmale, sort_keys=True, ensure_ascii=False)


def beschriften(merkmale: dict, profil: dict | None = None, kurz: bool = False) -> str:
    """Macht aus einem Merkmalsbündel eine lesbare Beschriftung.

    {"person":"1","numerus":"sg","tempus":"praesens","modus":"indikativ"}
    -> "1. Person Singular Präsens Indikativ"

    Das Sprachprofil darf Beschriftungen überschreiben, damit Französisch
    "Passé composé" sagt, wo das allgemeine Inventar "Perfekt" sagt.
    """
    eigene = (profil or {}).get("beschriftungen", {})
    teile: list[str] = []
    for dimension in REIHENFOLGE:
        if dimension not in merkmale:
            continue
        wert = merkmale[dimension]
        ersatz = eigene.get(dimension, {}).get(wert)
        if ersatz is not None:
            teile.append(ersatz if isinstance(ersatz, str) else ersatz[1 if kurz else 0])
            continue
        eintrag = INVENTAR.get(dimension, {}).get(wert)
        teile.append(eintrag[1 if kurz else 0] if eintrag else wert)
    # Zusatzmerkmale hinten anhängen, damit sie nicht verschwinden
    for dimension in sorted(merkmale):
        if dimension.startswith("x_"):
            teile.append(str(merkmale[dimension]))
    if not teile:
        return "Grundform"
    return " ".join(teile)


def sortierbar(merkmale: dict) -> tuple:
    """Sortierschlüssel, damit Formen in einer sinnvollen Reihenfolge stehen
    (1. Person vor 2. Person, Singular vor Plural)."""
    schluesselteile: list[int] = []
    for dimension in REIHENFOLGE:
        werte = list(INVENTAR.get(dimension, {}))
        wert = merkmale.get(dimension)
        if wert is None:
            schluesselteile.append(-1)
        elif wert in werte:
            schluesselteile.append(werte.index(wert))
        else:
            schluesselteile.append(len(werte))
    return tuple(schluesselteile)


def vergleichbar(text: str) -> str:
    """NFC-Normalform. Eingaben aus verschiedenen Tastaturen und
    Betriebssystemen sehen gleich aus, sind aber byteweise verschieden
    (é als ein Zeichen oder als e + Akzent). Ohne das scheitert jeder
    Vergleich auf dem Mac gegen Daten aus dem Netz."""
    return unicodedata.normalize("NFC", text)
