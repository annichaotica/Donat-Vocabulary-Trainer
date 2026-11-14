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
        # Wörter mit gemeinsamem Geschlecht: ο/η γιατρός, ο/η δικηγόρος.
        # Die Form ist dieselbe, nur der Artikel richtet sich nach der
        # gemeinten Person. Beide Artikel gelten dann als richtig.
        "mf": ("maskulin oder feminin", "m/f"),
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


# Dieselben Merkmale in Alltagssprache.
#
# "Genitiv Singular" ist richtig und für die Hälfte der Lernenden eine
# Mauer. Wer in der Schule die vier Fälle über ihre Fragewörter gelernt
# hat — wer? wessen? wem? wen? —, kommt damit sofort zurecht; wer sie nie
# gelernt hat, mit "Genitiv" auch nicht.
#
# Nur dort hinterlegt, wo es hilft. Fehlt ein Eintrag, bleibt die
# Fachbezeichnung stehen; das ist besser als eine erfundene Umschreibung.
EINFACH: dict[str, dict[str, str]] = {
    "kasus": {
        "nom": "wer oder was?", "gen": "wessen?", "dat": "wem?",
        "akk": "wen oder was?", "vok": "Anrede", "abl": "womit?",
    },
    # Kein "dual": das Inventar kennt ihn nicht, und mk.pruefen() weist
    # ihn ab. Ein Eintrag, der nie greift, täuscht eine Fähigkeit vor.
    "numerus": {"sg": "Einzahl", "pl": "Mehrzahl"},
    "genus": {"m": "männlich", "f": "weiblich", "n": "sächlich",
              "mf": "männlich und weiblich"},
    "tempus": {
        "praesens": "jetzt", "imperfekt": "früher, immer wieder",
        "aorist": "früher, einmal", "praeteritum": "früher",
        "perfekt": "schon geschehen", "plusquamperfekt": "davor geschehen",
        "futur": "später", "futur_perfekt": "bis dann geschehen",
        "verlaufsform": "gerade dabei",
    },
    "modus": {
        "indikativ": "Aussage", "konjunktiv": "Möglichkeit oder Wunsch",
        "imperativ": "Aufforderung", "konditional": "Bedingung",
    },
    "genus_verbi": {"aktiv": "tut selbst", "passiv": "wird getan",
                    "medium": "an sich selbst"},
    "stufe": {"grund": "einfach", "komparativ": "mehr als",
              "superlativ": "am meisten"},
    "nonfinit": {
        "infinitiv": "Grundform", "partizip_praesens": "gerade dabei",
        "partizip_perfekt": "fertig, wie ein Eigenschaftswort",
        "gerundium": "beim Tun", "supinum": "um zu",
    },
    "aspekt": {"perfektiv": "einmalig", "imperfektiv": "andauernd"},
}

# Person und Zahl zusammen ergeben ein Wort, das jeder versteht. Einzeln
# gesagt ("1. Person", "Singular") muss man es erst zusammensetzen —
# genau daran scheitert man mitten in der Abfrage.
PERSONEN = {
    ("1", "sg"): "ich", ("2", "sg"): "du", ("3", "sg"): "er/sie/es",
    ("1", "pl"): "wir", ("2", "pl"): "ihr", ("3", "pl"): "sie",
}

STILE = ("fach", "einfach", "beides")

# Ein Beispiel sagt mehr als jede Umschreibung. "wen oder was?" ist schon
# besser als "Akkusativ", aber erst "ich sehe DEN Hund" macht es in einer
# Sekunde klar.
#
# Immer auf Deutsch und immer mit demselben Wort, damit man die Fälle
# nebeneinander vergleichen kann.
BEISPIELE: dict[str, dict[str, str]] = {
    "kasus": {
        "nom": "der Hund schläft", "gen": "das Fell des Hundes",
        "dat": "ich gebe dem Hund etwas", "akk": "ich sehe den Hund",
        "vok": "Hund, komm her!", "abl": "mit dem Hund",
    },
    "stufe": {"grund": "schön", "komparativ": "schöner",
              "superlativ": "am schönsten"},
    "nonfinit": {
        "infinitiv": "gehen", "partizip_praesens": "gehend",
        "partizip_perfekt": "gegangen", "gerundium": "beim Gehen",
        "supinum": "um zu gehen",
    },
    "modus": {
        "indikativ": "ich gehe", "konjunktiv": "dass ich gehe",
        "imperativ": "geh!", "konditional": "ich würde gehen",
    },
    "genus_verbi": {"aktiv": "ich sehe", "passiv": "ich werde gesehen",
                    "medium": "ich wasche mich"},
    "tempus": {
        "praesens": "ich gehe", "imperfekt": "ich ging immer wieder",
        "aorist": "ich ging (einmal)", "praeteritum": "ich ging",
        "perfekt": "ich bin gegangen", "plusquamperfekt": "ich war gegangen",
        "futur": "ich werde gehen", "futur_perfekt": "ich werde gegangen sein",
        "verlaufsform": "ich bin am Gehen",
    },
    "numerus": {"sg": "der Hund", "pl": "die Hunde"},
    "genus": {"m": "der Hund", "f": "die Katze", "n": "das Pferd",
              # ο/η γιατρός — dasselbe Wort für beide.
              "mf": "der oder die Angestellte"},
}

# Person und Zahl am Beispiel durchkonjugiert — genau die Reihe, die man
# beim Lernen aufsagt.
PERSONENBEISPIEL = {
    ("1", "sg"): "ich gehe", ("2", "sg"): "du gehst",
    ("3", "sg"): "er/sie/es geht", ("1", "pl"): "wir gehen",
    ("2", "pl"): "ihr geht", ("3", "pl"): "sie gehen",
}

# ---------------------------------------------------------------------
# »gehen« durch Person UND Zeit.
#
# Vorher gewann in der Beispielfolge die Person vor der Zeit, und das
# Beispiel zur 1. Person Singular lautet nun einmal »ich gehe«. Damit
# stand unter JEDER griechischen Zeit »wie bei: ich gehe« — auch unter
# dem Futur und dem Aorist, wo es schlicht falsch ist. Die Person allein
# erklärt die Form nicht, die Zeit allein auch nicht; gebraucht wird
# beides in einem Ausdruck.
#
# Zusammengesetzt statt achtundvierzig Einträge: die meisten deutschen
# Zeiten sind umschrieben, also genügt ein Hilfsverb und eine
# unveränderliche Form.
PRONOMEN_FOLGE = ("ich", "du", "er/sie/es", "wir", "ihr", "sie")
_STELLE = {("1", "sg"): 0, ("2", "sg"): 1, ("3", "sg"): 2,
           ("1", "pl"): 3, ("2", "pl"): 4, ("3", "pl"): 5}

# Einfache Zeiten: die Vollverbformen selbst.
_EINFACH = {
    "praesens": ("gehe", "gehst", "geht", "gehen", "geht", "gehen"),
    "praeteritum": ("ging", "gingst", "ging", "gingen", "gingt", "gingen"),
}
# Umschriebene Zeiten: Hilfsverb + unveränderlicher Teil.
_UMSCHRIEBEN = {
    "futur": (("werde", "wirst", "wird", "werden", "werdet", "werden"),
              "gehen"),
    "futur_perfekt": (("werde", "wirst", "wird", "werden", "werdet",
                       "werden"), "gegangen sein"),
    "perfekt": (("bin", "bist", "ist", "sind", "seid", "sind"), "gegangen"),
    "plusquamperfekt": (("war", "warst", "war", "waren", "wart", "waren"),
                        "gegangen"),
}
# Was der Aorist und der Paratatikos im Deutschen unterscheiden: beides
# ist Vergangenheit, der eine einmalig, der andere im Verlauf. Ohne den
# Zusatz wären die Beispiele gleich und erklärten nichts.
_ZUSATZ = {"aorist": " (einmal)", "imperfekt": " immer wieder"}
_WIE_PRAETERITUM = ("aorist", "imperfekt", "praeteritum")


def _verbbeispiel(merkmale: dict) -> str | None:
    """»du wirst gehen« statt »du gehst« — Person und Zeit zusammen."""
    stelle = _STELLE.get((str(merkmale.get("person")),
                          str(merkmale.get("numerus", "sg"))))
    if stelle is None:
        return None
    pron = PRONOMEN_FOLGE[stelle]
    tempus = merkmale.get("tempus")
    modus = merkmale.get("modus")

    # Der Konditional ist im Deutschen umschrieben und sticht die Zeit.
    if modus == "konditional":
        wuerde = ("würde", "würdest", "würde", "würden", "würdet", "würden")
        return f"{pron} {wuerde[stelle]} gehen"
    if merkmale.get("genus_verbi") == "passiv":
        # Nur Gegenwart und Vergangenheit — mehr braucht die Erklärung
        # nicht, und erfundene Formen helfen niemandem.
        if tempus in _WIE_PRAETERITUM:
            wurde = ("wurde", "wurdest", "wurde", "wurden", "wurdet", "wurden")
            return f"{pron} {wurde[stelle]} gesehen"
        werde = ("werde", "wirst", "wird", "werden", "werdet", "werden")
        return f"{pron} {werde[stelle]} gesehen"

    if tempus in _UMSCHRIEBEN:
        hilfs, rest = _UMSCHRIEBEN[tempus]
        satz = f"{pron} {hilfs[stelle]} {rest}"
    elif tempus in _WIE_PRAETERITUM:
        satz = f"{pron} {_EINFACH['praeteritum'][stelle]}"
    elif tempus in _EINFACH:
        satz = f"{pron} {_EINFACH[tempus][stelle]}"
    elif tempus is None:
        satz = f"{pron} {_EINFACH['praesens'][stelle]}"
    else:
        return None                  # unbekannte Zeit: lieber nichts sagen
    satz += _ZUSATZ.get(tempus, "")
    if modus == "konjunktiv":
        return f"dass {satz}"
    return satz

# Wie eine Dimension auf Deutsch heißt. Stand zweimal in aufgaben.py,
# mit verschiedenem Inhalt: einmal mit `genus_verbi: "Form"`, einmal
# ohne — das Auswahlfeld hieß also »Form«, und die Rückmeldung bei
# falscher Antwort sagte »genus_verbi stimmt nicht«.
NAMEN: dict[str, str] = {
    "person": "Person", "numerus": "Zahl", "genus": "Geschlecht",
    "kasus": "Fall", "stufe": "Steigerung", "tempus": "Zeit",
    "modus": "Modus", "nonfinit": "Nennform", "genus_verbi": "Form",
    "aspekt": "Aspekt", "flexion": "Beugung", "diathese": "Diathese",
}


def name_der_dimension(dimension: str) -> str:
    return NAMEN.get(dimension, dimension)


# In dieser Reihenfolge wird nach einem Beispiel gesucht. Erklärt wird
# EINE Sache, nicht alle: "ich sehe den Hund, der Hund" wäre keine Hilfe.
BEISPIELFOLGE = ("kasus", "nonfinit", "stufe", "person", "modus",
                 "genus_verbi", "tempus", "genus")

# Der Normalfall sagt nichts. Dass eine Form im Indikativ steht und aktiv
# ist, unterscheidet sie von nichts — das tun die ZEIT und alles, was vom
# Normalfall abweicht. Darum erklären diese Werte nur, wenn sonst nichts
# da ist.
UNMARKIERT = {"modus": "indikativ", "genus_verbi": "aktiv", "stufe": "grund",
              "numerus": "sg"}


def beispiel(merkmale: dict) -> str | None:
    """Ein deutscher Beispielausdruck für das, was hier verlangt ist."""
    # Beim Imperativ ist der Modus der Punkt und nicht die Person: "geh!"
    # erklärt die Form, "du gehst" wäre schlicht etwas anderes.
    if merkmale.get("modus") == "imperativ":
        return "geh!" if merkmale.get("numerus") != "pl" else "geht!"
    # Steht das Geschlecht im Nominativ dabei, IST es der Punkt — bei
    # einem Adjektiv unterscheidet es die drei Formen voneinander, der
    # Fall tut es nicht.
    if merkmale.get("genus") and merkmale.get("kasus") in (None, "nom"):
        b = BEISPIELE["genus"].get(merkmale["genus"])
        if b:
            return b
    # Zwei Durchgänge: erst das Markierte, dann der Rest. Sonst erklärte
    # jede griechische Zeit mit "ich gehe", weil der Indikativ vorne steht.
    folge = [d for d in BEISPIELFOLGE
             if d in merkmale and UNMARKIERT.get(d) != merkmale[d]]
    folge += [d for d in BEISPIELFOLGE if d in merkmale and d not in folge]
    for dimension in folge:
        if dimension == "person":
            # Person UND Zeit, nicht nur die Person: sonst stand unter
            # jeder griechischen Zeit »ich gehe«, auch unter dem Futur.
            b = _verbbeispiel(merkmale)
            if b:
                return b
            b = PERSONENBEISPIEL.get((str(merkmale.get("person")),
                                      str(merkmale.get("numerus", "sg"))))
            if b:
                return b
            continue
        b = BEISPIELE.get(dimension, {}).get(merkmale[dimension])
        if b:
            # Beim Fall sagt die Zahl mit, ob einer oder mehrere gemeint
            # sind — "ich sehe den Hund" gegen "ich sehe die Hunde".
            if dimension == "kasus" and merkmale.get("numerus") == "pl":
                b = (b.replace("der Hund schläft", "die Hunde schlafen")
                      .replace("den Hund", "die Hunde")
                      .replace("des Hundes", "der Hunde")
                      .replace("dem Hund", "den Hunden")
                      .replace("Hund, komm her!", "Hunde, kommt her!"))
            return b
    return None


def _einfach(merkmale: dict) -> str:
    """Dasselbe Bündel in Alltagssprache."""
    teile: list[str] = []
    person = merkmale.get("person")
    numerus = merkmale.get("numerus")
    zusammen = PERSONEN.get((str(person), str(numerus))) if person else None
    for dimension in REIHENFOLGE:
        if dimension not in merkmale:
            continue
        if zusammen and dimension in ("person", "numerus"):
            if dimension == "person":
                teile.append(zusammen)
            continue
        wert = merkmale[dimension]
        ersatz = EINFACH.get(dimension, {}).get(wert)
        if ersatz:
            teile.append(ersatz)
            continue
        eintrag = INVENTAR.get(dimension, {}).get(wert)
        teile.append(eintrag[0] if eintrag else str(wert))
    return ", ".join(teile)


def beschriften(merkmale: dict, profil: dict | None = None, kurz: bool = False,
                stil: str = "fach") -> str:
    """Macht aus einem Merkmalsbündel eine lesbare Beschriftung.

    {"person":"1","numerus":"sg","tempus":"praesens","modus":"indikativ"}
    -> "1. Person Singular Präsens Indikativ"

    Mit `stil="einfach"` dasselbe in Alltagssprache ("ich, jetzt, Aussage"),
    mit `stil="beides"` beides nebeneinander. Das Sprachprofil darf
    Beschriftungen überschreiben, damit Französisch "Passé composé" sagt,
    wo das allgemeine Inventar "Perfekt" sagt.
    """
    if stil == "einfach":
        schlicht = _einfach(merkmale)
        if schlicht:
            return schlicht
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
    fach = " ".join(teile)
    if stil == "beides":
        schlicht = _einfach(merkmale)
        # Nur anhängen, wenn es etwas anderes sagt — "Grundform
        # (Grundform)" hilft niemandem.
        if schlicht and schlicht.replace(", ", " ").casefold() != fach.casefold():
            return f"{fach} ({schlicht})"
    return fach


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


# ----------------------------------------------- Stillschweigende Vorgaben

def normieren(merkmale: dict, wortart: str) -> dict:
    """Ergänzt, was ungesagt gilt.

    Eine Verbform ohne Angabe zum Genus verbi ist **aktiv**. Das muss
    ausgesprochen werden, sobald es auch Passivgruppen gibt: sonst passte
    eine Passivform auch auf die Aktivzelle, weil die das Merkmal gar nicht
    verlangt — und ein Deponens sähe aus, als hätte es ein vollständiges
    Aktivparadigma.

    Nur zum VERGLEICHEN gedacht, nicht zum Speichern: die Datensätze
    bleiben, wie sie eingetragen wurden.
    """
    if (wortart == "verb" and "genus_verbi" not in merkmale
            and any(d in merkmale for d in ("tempus", "modus", "nonfinit"))):
        return {**merkmale, "genus_verbi": "aktiv"}
    return dict(merkmale)


# --------------------------------------------------------- Erklärte Lücken

def passt_muster(muster: dict, zelle: dict) -> bool:
    """Ist das Muster in dieser Zelle enthalten?

    Das LEERE Muster passt überall — damit lässt sich "dieses Wort hat
    überhaupt keine Formen" ausdrücken (το ταξί, μπλε).
    """
    return all(str(zelle.get(d)) == str(w) for d, w in (muster or {}).items())


def ist_erklaerte_luecke(luecken, zelle: dict) -> bool:
    """Wurde für diese Zelle erklärt, dass es sie nicht gibt?

    Unpersönliche Verben haben keine 1. und 2. Person, είμαι hat keinen
    Aorist, τα μεσάνυχτα keinen Singular. Das sind keine Mängel, sondern
    Eigenschaften des Wortes — und sie dürfen weder als Fehler gemeldet
    werden noch die Stammerkennung stören.
    """
    if not luecken:
        return False
    return any(passt_muster(m, zelle) for m in luecken if isinstance(m, dict))


def luecken_pruefen(luecken) -> list[dict]:
    """Prüft die Lückenmuster gegen das Inventar."""
    if luecken is None:
        return []
    if not isinstance(luecken, list):
        raise MerkmalFehler("luecken muss eine Liste von Merkmalsmustern sein")
    sauber = []
    for muster in luecken:
        if not isinstance(muster, dict):
            raise MerkmalFehler("Jedes Lückenmuster muss ein Objekt sein; das "
                                "leere Objekt {} bedeutet: gar keine Formen")
        sauber.append(pruefen(muster))
    return sauber
