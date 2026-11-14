"""Import aus vorhandenen Dateien.

CSV, Tabulatorgetrenntes, Anki-Ausfuhr, Quizlet-Ausfuhr. Alles dasselbe
Problem: Zeilen mit Spalten, und niemand weiß vorher, welche Spalte was ist.

Darum zwei Schritte: erst **Vorschau** — die Datei wird gelesen, das
Trennzeichen erraten, die Spalten gedeutet und gezeigt, was dabei
herauskäme. Dann **Übernahme**, mit der Zuordnung, die der Mensch bestätigt
oder berichtigt hat. Ein Import, der ungefragt 800 Zeilen in den Bestand
kippt, ist schlimmer als keiner.

Was erkannt wird:

* Das Trennzeichen (Tabulator, Semikolon, Komma) — nach Häufigkeit und
  Gleichmäßigkeit über die Zeilen, nicht bloß nach dem ersten Vorkommen.
* Eine Kopfzeile, wenn sie bekannte Spaltennamen trägt.
* Welche Spalte das fremdsprachige Wort ist: die mit den meisten Zeichen,
  die in der Zielsprache vorkommen und in der Grundsprache nicht. Bei
  Griechisch und Mittelhochdeutsch ist das eindeutig; bei Französisch gegen
  Deutsch hilft die Kopfzeile oder die Reihenfolge.
* Mehrere Übersetzungen in einer Zelle, getrennt durch Komma, Schrägstrich
  oder Semikolon.
* Ein vorangestellter Artikel — daraus wird das Geschlecht abgeleitet.
"""

from __future__ import annotations

import csv
import io
import re
import sqlite3
import unicodedata

import aufgaben
import datenbank as dbm
import merkmale as mk
import sprachen

TRENNZEICHEN = ["\t", ";", "|", ","]
MEHRFACH = re.compile(r"\s*[,;/]\s*|\s+oder\s+")

# Spaltennamen, die in Ausfuhren vorkommen.
KOPFNAMEN = {
    "lemma": {"wort", "word", "front", "vorderseite", "begriff", "term",
              "fremdsprache", "vokabel", "lemma", "ausdruck"},
    "uebersetzung": {"bedeutung", "übersetzung", "uebersetzung", "back",
                     "rückseite", "rueckseite", "definition", "deutsch",
                     "meaning", "translation"},
    "wortart": {"wortart", "art", "pos", "typ", "part of speech"},
    "lektion": {"lektion", "kapitel", "unit", "lesson", "deck", "stapel",
                "kategorie", "tags"},
    "notiz": {"notiz", "note", "bemerkung", "kommentar", "beispiel"},
}


def _saeubern(text: str) -> str:
    return unicodedata.normalize("NFC", (text or "").strip()).strip('"').strip()


def trennzeichen_raten(text: str) -> str:
    """Welches Trennzeichen teilt die Zeilen am gleichmäßigsten?

    Nicht einfach das häufigste: ein Text voller Kommata in den Bedeutungen
    hat viele Kommata, aber ungleich verteilt. Gesucht ist das Zeichen, das
    in möglichst vielen Zeilen GLEICH OFT vorkommt.
    """
    zeilen = [z for z in text.splitlines() if z.strip()][:50]
    if not zeilen:
        return "\t"
    bestes, beste_güte = "\t", -1.0
    for zeichen in TRENNZEICHEN:
        anzahlen = [z.count(zeichen) for z in zeilen]
        if not any(anzahlen):
            continue
        haeufigste = max(set(anzahlen), key=anzahlen.count)
        if haeufigste == 0:
            continue
        einigkeit = anzahlen.count(haeufigste) / len(anzahlen)
        güte = einigkeit * min(haeufigste, 4)
        if güte > beste_güte:
            bestes, beste_güte = zeichen, güte
    return bestes


def _fremdheit(texte: list[str], code: str) -> float:
    """Wie fremd sieht diese Spalte aus? Anteil der Zeichen, die nicht zum
    deutschen Grundbestand gehören."""
    schrift = sprachen.profil(code).get("schrift", "latein")
    gesamt = fremd = 0
    for t in texte:
        for z in t:
            if not z.isalpha():
                continue
            gesamt += 1
            name = unicodedata.name(z, "")
            if schrift == "griechisch":
                if "GREEK" in name:
                    fremd += 1
            elif z.lower() not in "abcdefghijklmnopqrstuvwxyzäöüß":
                fremd += 1
    return fremd / gesamt if gesamt else 0.0


def _kopfzeile_deuten(zeile: list[str]) -> dict[int, str]:
    zuordnung = {}
    for i, feld in enumerate(zeile):
        klein = _saeubern(feld).casefold()
        for rolle, namen in KOPFNAMEN.items():
            if klein in namen:
                zuordnung[i] = rolle
                break
    return zuordnung


def lesen(text: str, trenner: str | None = None) -> list[list[str]]:
    trenner = trenner or trennzeichen_raten(text)
    leser = csv.reader(io.StringIO(text), delimiter=trenner,
                       quotechar='"', skipinitialspace=True)
    return [[_saeubern(f) for f in zeile] for zeile in leser
            if any(f.strip() for f in zeile)]


def vorschau(db: sqlite3.Connection, sammlung_id: int, text: str,
             trenner: str | None = None, zuordnung: dict | None = None,
             hat_kopfzeile: bool | None = None, anzahl: int = 10) -> dict:
    """Liest die Datei und zeigt, was dabei herauskäme — ohne etwas zu ändern."""
    s = dbm.zeile(db, "SELECT * FROM sammlung WHERE id = ?", (sammlung_id,))
    if s is None:
        raise KeyError(f"Sammlung {sammlung_id} gibt es nicht")
    code = s["sprache"]

    trenner = trenner or trennzeichen_raten(text)
    zeilen = lesen(text, trenner)
    if not zeilen:
        return {"fehler": "Die Datei enthält keine lesbaren Zeilen.",
                "zeilen": 0}

    kopf_zuordnung = _kopfzeile_deuten(zeilen[0])
    if hat_kopfzeile is None:
        # Eine Kopfzeile erkennt man daran, dass sie bekannte Spaltennamen
        # trägt — nicht daran, dass sie die erste ist.
        hat_kopfzeile = len(kopf_zuordnung) >= 2
    daten = zeilen[1:] if hat_kopfzeile else zeilen
    if not daten:
        return {"fehler": "Außer der Kopfzeile steht nichts in der Datei.",
                "zeilen": 0}

    spalten = max(len(z) for z in daten)
    if zuordnung is None:
        zuordnung = dict(kopf_zuordnung) if hat_kopfzeile else {}
        if "lemma" not in zuordnung.values() or "uebersetzung" not in zuordnung.values():
            # Ohne Kopfzeile: die fremdeste Spalte ist das Lemma, die nächste
            # die Bedeutung.
            werte = {i: [z[i] for z in daten if i < len(z)] for i in range(spalten)}
            fremdheit = {i: _fremdheit(v, code) for i, v in werte.items()}
            lemma_spalte = max(fremdheit, key=fremdheit.get)
            if fremdheit[lemma_spalte] < 0.02 and spalten >= 2:
                lemma_spalte = 0          # keine fremde Schrift: erste Spalte
            zuordnung = {lemma_spalte: "lemma"}
            uebrig = [i for i in range(spalten) if i != lemma_spalte]
            if uebrig:
                zuordnung[uebrig[0]] = "uebersetzung"
    zuordnung = {int(k): v for k, v in zuordnung.items()}

    vorhandene = {z["lemma"] for z in dbm.zeilen(
        db, "SELECT lemma FROM lexem WHERE sammlung_id = ?", (sammlung_id,))}

    eintraege, uebersprungen = [], []
    for nr, zeile in enumerate(daten, start=2 if hat_kopfzeile else 1):
        eintrag = _zeile_deuten(zeile, zuordnung, code)
        if not eintrag["lemma"]:
            uebersprungen.append({"zeile": nr, "grund": "kein Wort in der Zeile"})
            continue
        if not eintrag["uebersetzungen"]:
            uebersprungen.append({"zeile": nr,
                                  "grund": f"keine Bedeutung zu »{eintrag['lemma']}«"})
            continue
        eintrag["schon_vorhanden"] = eintrag["lemma"] in vorhandene
        eintrag["zeile"] = nr
        eintraege.append(eintrag)

    return {
        "trenner": {"\t": "Tabulator", ";": "Semikolon", ",": "Komma",
                    "|": "Senkrechter Strich"}.get(trenner, trenner),
        "trenner_zeichen": trenner,
        "hat_kopfzeile": hat_kopfzeile,
        "spalten": spalten,
        "zuordnung": {str(k): v for k, v in zuordnung.items()},
        "moegliche_rollen": ["lemma", "uebersetzung", "wortart", "lektion",
                             "notiz", "ignorieren"],
        "zeilen": len(daten),
        "brauchbar": len(eintraege),
        "doppelt": sum(1 for e in eintraege if e["schon_vorhanden"]),
        "uebersprungen": uebersprungen[:20],
        "beispiel": eintraege[:anzahl],
    }


def _zeile_deuten(zeile: list[str], zuordnung: dict[int, str],
                  code: str) -> dict:
    eintrag = {"lemma": "", "uebersetzungen": [], "wortart": None,
               "lektion": None, "notiz": None, "merkmale": {}}
    for i, rolle in zuordnung.items():
        if i >= len(zeile) or rolle == "ignorieren":
            continue
        wert = zeile[i]
        if not wert:
            continue
        if rolle == "lemma":
            eintrag["lemma"] = wert
        elif rolle == "uebersetzung":
            eintrag["uebersetzungen"] += [t for t in MEHRFACH.split(wert) if t]
        elif rolle == "wortart":
            eintrag["wortart"] = _wortart_deuten(wert)
        elif rolle == "lektion":
            eintrag["lektion"] = wert
        elif rolle == "notiz":
            eintrag["notiz"] = wert

    # Artikel vorweg? Dann steckt darin das Geschlecht.
    artikel = sprachen.profil(code).get("artikel", {}).get("genus_artikel", {})
    erstes = eintrag["lemma"].split(" ")[0].casefold() if eintrag["lemma"] else ""
    for genus, art in artikel.items():
        if erstes == art.casefold():
            eintrag["merkmale"]["genus"] = genus
            if not eintrag["wortart"]:
                eintrag["wortart"] = "substantiv"
            break
    if not eintrag["wortart"]:
        eintrag["wortart"] = "sonstiges"
    return eintrag


_WORTARTEN_SCHREIBWEISEN = {
    "substantiv": {"substantiv", "nomen", "noun", "n", "s", "subst"},
    "verb": {"verb", "v", "vb", "verbum"},
    "adjektiv": {"adjektiv", "adj", "adjective", "a"},
    "adverb": {"adverb", "adv"},
    "pronomen": {"pronomen", "pron"},
    "praeposition": {"präposition", "praeposition", "prep", "präp"},
    "konjunktion": {"konjunktion", "konj", "conj"},
    "numerale": {"zahlwort", "numerale", "num"},
    "wendung": {"wendung", "redewendung", "phrase", "ausdruck"},
}


def _wortart_deuten(wert: str) -> str | None:
    klein = _saeubern(wert).casefold().rstrip(".")
    for wortart, schreibweisen in _WORTARTEN_SCHREIBWEISEN.items():
        if klein in schreibweisen:
            return wortart
    return klein if klein in mk.WORTARTEN else None


def uebernehmen(db: sqlite3.Connection, sammlung_id: int, text: str,
                trenner: str | None = None, zuordnung: dict | None = None,
                hat_kopfzeile: bool | None = None,
                doppelte: str = "ueberspringen",
                als_geprueft: bool = True) -> dict:
    """Übernimmt die Datei in den Bestand.

    doppelte: "ueberspringen" | "ergaenzen" (Bedeutungen zum vorhandenen
    Eintrag dazu) | "trotzdem" (zweiter Eintrag).
    """
    s = dbm.zeile(db, "SELECT * FROM sammlung WHERE id = ?", (sammlung_id,))
    if s is None:
        raise KeyError(f"Sammlung {sammlung_id} gibt es nicht")
    schau = vorschau(db, sammlung_id, text, trenner, zuordnung, hat_kopfzeile,
                     anzahl=0)
    if "fehler" in schau:
        return schau

    # Alle brauchbaren Zeilen, nicht nur das Beispiel
    alle = vorschau(db, sammlung_id, text, schau["trenner_zeichen"],
                    {int(k): v for k, v in schau["zuordnung"].items()},
                    schau["hat_kopfzeile"], anzahl=10 ** 6)["beispiel"]

    lektionen = {z["name"]: z["id"] for z in dbm.zeilen(
        db, "SELECT id, name FROM lektion WHERE sammlung_id = ?", (sammlung_id,))}
    vorhandene = {z["lemma"]: z["id"] for z in dbm.zeilen(
        db, "SELECT id, lemma FROM lexem WHERE sammlung_id = ?", (sammlung_id,))}

    angelegt = ergaenzt = uebersprungen = 0
    aufgaben_gesamt = 0
    db.execute("BEGIN")
    try:
        for e in alle:
            lektion_id = None
            if e["lektion"]:
                if e["lektion"] not in lektionen:
                    cur = db.execute("""INSERT INTO lektion
                                          (sammlung_id, name, reihenfolge)
                                        VALUES (?, ?, ?)""",
                                     (sammlung_id, e["lektion"], len(lektionen)))
                    lektionen[e["lektion"]] = cur.lastrowid
                lektion_id = lektionen[e["lektion"]]

            if e["lemma"] in vorhandene:
                if doppelte == "ueberspringen":
                    uebersprungen += 1
                    continue
                if doppelte == "ergaenzen":
                    _bedeutung_dazu(db, vorhandene[e["lemma"]], e,
                                    s["grundsprache"])
                    aufgaben_gesamt += aufgaben.erzeugen(
                        db, vorhandene[e["lemma"]])["angelegt"]
                    ergaenzt += 1
                    continue

            merkmale = sprachen.pruefen_lexemmerkmale(
                s["sprache"], e["wortart"], e["merkmale"])
            cur = db.execute("""INSERT INTO lexem
                                  (sammlung_id, lektion_id, lemma, wortart,
                                   merkmale, notiz)
                                VALUES (?, ?, ?, ?, ?, ?)""",
                             (sammlung_id, lektion_id, e["lemma"], e["wortart"],
                              dbm.j_schreiben(merkmale), e["notiz"]))
            lexem_id = cur.lastrowid
            vorhandene[e["lemma"]] = lexem_id
            # Das Lemma selbst als Grundform, damit es eine gibt.
            db.execute("""INSERT INTO form
                            (lexem_id, text, merkmale, ist_grundform, quelle,
                             geprueft)
                          VALUES (?, ?, '{}', 1, 'import', ?)""",
                       (lexem_id, e["lemma"], int(als_geprueft)))
            _bedeutung_dazu(db, lexem_id, e, s["grundsprache"])
            aufgaben_gesamt += aufgaben.erzeugen(db, lexem_id)["angelegt"]
            angelegt += 1
        db.execute("COMMIT")
    except Exception:
        db.execute("ROLLBACK")
        raise

    return {"angelegt": angelegt, "ergaenzt": ergaenzt,
            "uebersprungen": uebersprungen,
            "nicht_lesbar": len(schau["uebersprungen"]),
            "aufgaben": aufgaben_gesamt,
            "lektionen_neu": [n for n in lektionen if n],
            "zuordnung": schau["zuordnung"],
            "trenner": schau["trenner"]}


def _bedeutung_dazu(db: sqlite3.Connection, lexem_id: int, eintrag: dict,
                    grundsprache: str) -> None:
    anzahl = dbm.wert(db, "SELECT COUNT(*) FROM bedeutung WHERE lexem_id = ?",
                      (lexem_id,)) or 0
    cur = db.execute("""INSERT INTO bedeutung (lexem_id, reihenfolge)
                        VALUES (?, ?)""", (lexem_id, anzahl))
    for i, text in enumerate(eintrag["uebersetzungen"]):
        db.execute("""INSERT INTO uebersetzung
                        (bedeutung_id, sprache, text, ist_haupt, quelle)
                      VALUES (?, ?, ?, ?, 'import')""",
                   (cur.lastrowid, grundsprache, text, int(i == 0)))
