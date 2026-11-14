"""Aufgaben: erzeugen, stellen, prüfen.

Aufgaben werden aus den Daten ERZEUGT und nicht von Hand gepflegt. Wer eine
Form einträgt, bekommt die zugehörigen Aufgaben; wer eine Form löscht, verliert
sie. Der Aufgabenschlüssel ist dabei absichtlich nicht an die Zeilennummer der
Form gebunden, sondern an ihr Merkmalsbündel: wird ein Tippfehler in einer Form
korrigiert, bleibt der Lernstand erhalten.
"""

from __future__ import annotations

import sqlite3

import datenbank as dbm
import merkmale as mk
import sprachen
from pruefung import Urteil, pruefen as text_pruefen

# Aufgabentypen. eingabeart steuert, was die Oberfläche anzeigt:
#   text      — Eingabefeld
#   merkmale  — Auswahlfelder für Person, Numerus, Zeit ...
#   auswahl   — Knöpfe mit vorgegebenen Antworten (Artikel)
TYPEN: dict[str, dict] = {
    "bedeutung_fremd_deutsch": {
        "name": "Bedeutung erkennen",
        "eingabeart": "text",
        "beschreibung": "Fremdsprachiges Wort, gesucht ist die Bedeutung.",
    },
    "bedeutung_deutsch_fremd": {
        "name": "Wort bilden",
        "eingabeart": "text",
        "beschreibung": "Deutsche Bedeutung, gesucht ist das fremdsprachige Wort.",
    },
    "form_bilden": {
        "name": "Form bilden",
        "eingabeart": "text",
        "beschreibung": "Grundform und Formangabe gegeben, gesucht ist die Form.",
    },
    "form_bestimmen": {
        "name": "Form bestimmen",
        "eingabeart": "merkmale",
        "beschreibung": "Form gegeben, gesucht ist, um welche Form es sich handelt.",
    },
    "genus": {
        "name": "Artikel",
        "eingabeart": "auswahl",
        "beschreibung": "Gesucht ist der Artikel beziehungsweise das Geschlecht.",
    },
}

TYPEN_STANDARD = ["bedeutung_fremd_deutsch", "bedeutung_deutsch_fremd",
                  "form_bilden", "genus"]


# ------------------------------------------------------------- Einstellungen

def sammlung_einstellungen(db: sqlite3.Connection, sammlung_id: int) -> dict:
    """Einstellungen einer Sammlung, mit den Vorgaben der Sprache aufgefüllt."""
    s = dbm.zeile(db, "SELECT * FROM sammlung WHERE id = ?", (sammlung_id,))
    if s is None:
        raise KeyError(f"Sammlung {sammlung_id} gibt es nicht")
    eigen = dbm.j_lesen(s["einstellungen"])
    return {
        "formgruppen": eigen.get("formgruppen")
                       or sprachen.formgruppen_standard(s["sprache"]),
        "typen": eigen.get("typen") or list(TYPEN_STANDARD),
        "ungeprueft_abfragen": bool(eigen.get("ungeprueft_abfragen", False)),
        "sprache": s["sprache"],
        "grundsprache": s["grundsprache"],
        "sammlung": s,
    }


def _gruppe_der_form(code: str, wortart: str, merkmale: dict) -> dict | None:
    """Zu welcher Formgruppe gehört diese Form? Die spezifischste gewinnt."""
    treffer = [g for g in sprachen.formgruppen(code, wortart)
               if all(merkmale.get(d) == w for d, w in g["merkmale"].items())]
    return max(treffer, key=lambda g: len(g["merkmale"])) if treffer else None


# ---------------------------------------------------------------- Erzeugen

def _schluessel(typ: str, lexem_id: int, ziel_art: str, kennzeichen: str) -> str:
    return f"{typ}:{lexem_id}:{ziel_art}:{kennzeichen}"


def erzeugen(db: sqlite3.Connection, lexem_id: int) -> dict:
    """Bringt die Aufgaben eines Lexems auf den Stand seiner Daten.

    Gibt zurück, was angelegt, wieder aktiviert und abgeschaltet wurde.
    Abgeschaltet statt gelöscht: so bleibt der Lernstand erhalten, wenn eine
    Formgruppe nur zeitweise abgewählt ist.
    """
    lexem = dbm.zeile(db, "SELECT * FROM lexem WHERE id = ?", (lexem_id,))
    if lexem is None:
        raise KeyError(f"Lexem {lexem_id} gibt es nicht")
    e = sammlung_einstellungen(db, lexem["sammlung_id"])
    code, wortart = e["sprache"], lexem["wortart"]
    lex_merkmale = dbm.j_lesen(lexem["merkmale"])

    formen = dbm.zeilen(db, "SELECT * FROM form WHERE lexem_id = ?", (lexem_id,))
    bedeutungen = dbm.zeilen(
        db, "SELECT * FROM bedeutung WHERE lexem_id = ? ORDER BY reihenfolge, id",
        (lexem_id,))

    gewuenscht: dict[str, tuple[str, str, int | None]] = {}

    # Bedeutung erkennen: eine Aufgabe je Lexem, nicht je Bedeutung. Wer
    # "aller" sieht, darf jede hinterlegte Bedeutung nennen.
    hat_uebersetzung = any(
        dbm.wert(db, """SELECT 1 FROM uebersetzung
                         WHERE bedeutung_id = ? AND sprache = ? LIMIT 1""",
                 (b["id"], e["grundsprache"]))
        for b in bedeutungen)
    if hat_uebersetzung and "bedeutung_fremd_deutsch" in e["typen"]:
        gewuenscht[_schluessel("bedeutung_fremd_deutsch", lexem_id, "lexem", "")] = \
            ("bedeutung_fremd_deutsch", "lexem", None)

    # Wort bilden: je Bedeutung, denn die Richtung Deutsch -> Fremdsprache
    # braucht die Bedeutung zur Unterscheidung.
    if "bedeutung_deutsch_fremd" in e["typen"]:
        for b in bedeutungen:
            if dbm.wert(db, """SELECT 1 FROM uebersetzung
                                WHERE bedeutung_id = ? AND sprache = ? LIMIT 1""",
                        (b["id"], e["grundsprache"])):
                sch = _schluessel("bedeutung_deutsch_fremd", lexem_id,
                                  "bedeutung", str(b["id"]))
                gewuenscht[sch] = ("bedeutung_deutsch_fremd", "bedeutung", b["id"])

    # Formaufgaben. Der Schlüssel nennt das Merkmalsbündel, nicht die Form-ID.
    for f in formen:
        if f["ist_grundform"]:
            continue
        if not f["geprueft"] and not e["ungeprueft_abfragen"]:
            continue
        fm = dbm.j_lesen(f["merkmale"])
        if not fm:
            continue
        gruppe = _gruppe_der_form(code, wortart, fm)
        if gruppe is not None and gruppe["kennung"] not in e["formgruppen"]:
            continue
        kennzeichen = mk.schluessel(fm)
        for typ in ("form_bilden", "form_bestimmen"):
            if typ in e["typen"]:
                gewuenscht[_schluessel(typ, lexem_id, "merkmale", kennzeichen)] = \
                    (typ, "form", f["id"])

    # Artikel: nur wo die Sprache überhaupt Artikel nach Geschlecht hat.
    artikel = sprachen.profil(code).get("artikel", {}).get("genus_artikel", {})
    if ("genus" in e["typen"] and wortart == "substantiv"
            and lex_merkmale.get("genus") in artikel):
        gewuenscht[_schluessel("genus", lexem_id, "lexem", "")] = \
            ("genus", "lexem", None)

    vorhanden = {a["schluessel"]: a for a in
                 dbm.zeilen(db, "SELECT * FROM aufgabe WHERE lexem_id = ?", (lexem_id,))}

    angelegt = reaktiviert = abgeschaltet = 0
    for sch, (typ, ziel_art, ziel_id) in gewuenscht.items():
        alt = vorhanden.get(sch)
        if alt is None:
            db.execute("""INSERT INTO aufgabe
                            (lexem_id, typ, ziel_art, ziel_id, schluessel, aktiv)
                          VALUES (?, ?, ?, ?, ?, 1)""",
                       (lexem_id, typ, ziel_art, ziel_id, sch))
            angelegt += 1
        else:
            if not alt["aktiv"]:
                reaktiviert += 1
            # ziel_id nachziehen: die Form kann neu angelegt worden sein
            db.execute("UPDATE aufgabe SET aktiv = 1, ziel_id = ? WHERE id = ?",
                       (ziel_id, alt["id"]))
    for sch, alt in vorhanden.items():
        if sch not in gewuenscht and alt["aktiv"]:
            db.execute("UPDATE aufgabe SET aktiv = 0 WHERE id = ?", (alt["id"],))
            abgeschaltet += 1

    return {"angelegt": angelegt, "reaktiviert": reaktiviert,
            "abgeschaltet": abgeschaltet, "gesamt": len(gewuenscht)}


def erzeugen_fuer_sammlung(db: sqlite3.Connection, sammlung_id: int) -> dict:
    """Nach einer Änderung der Einstellungen alle Lexeme neu durchrechnen."""
    summe = {"angelegt": 0, "reaktiviert": 0, "abgeschaltet": 0, "gesamt": 0}
    for z in dbm.zeilen(db, "SELECT id FROM lexem WHERE sammlung_id = ?",
                        (sammlung_id,)):
        for k, v in erzeugen(db, z["id"]).items():
            summe[k] += v
    return summe


# ------------------------------------------------------------- Aufgabe stellen

def _uebersetzungen(db: sqlite3.Connection, bedeutung_id: int,
                    sprache: str) -> list[dict]:
    return dbm.zeilen(db, """SELECT * FROM uebersetzung
                              WHERE bedeutung_id = ? AND sprache = ?
                              ORDER BY ist_haupt DESC, id""",
                      (bedeutung_id, sprache))


def _alle_bedeutungen(db: sqlite3.Connection, lexem_id: int,
                      sprache: str) -> list[dict]:
    ergebnis = []
    for b in dbm.zeilen(db, """SELECT * FROM bedeutung WHERE lexem_id = ?
                                ORDER BY reihenfolge, id""", (lexem_id,)):
        b["uebersetzungen"] = _uebersetzungen(db, b["id"], sprache)
        ergebnis.append(b)
    return ergebnis


def _verwechslungen(db: sqlite3.Connection, lexem: dict, code: str,
                    ausser_text: str | None) -> list[tuple[str, str]]:
    """Andere Formen desselben Wortes, mit Beschriftung.

    Damit wird aus einem vermeintlichen Tippfehler eine klare Auskunft:
    "Das ist die 2. Person Singular."
    """
    liste = []
    for f in dbm.zeilen(db, "SELECT * FROM form WHERE lexem_id = ?", (lexem["id"],)):
        if ausser_text is not None and f["text"] == ausser_text:
            continue
        fm = dbm.j_lesen(f["merkmale"])
        beschriftung = sprachen.beschriften_form(code, lexem["wortart"], fm)
        liste.append((f["text"], beschriftung))
    if lexem["lemma"] != ausser_text:
        liste.append((lexem["lemma"], "die Grundform"))
    return liste


def geschwisterformen(db: sqlite3.Connection, form_id: int) -> list[str]:
    """Die Formen derselben Formgruppe — also derselben Zeit beziehungsweise
    derselben Tabelle.

    Dafür da, den Wortstamm abzuleiten. Über ALLE Formen eines Wortes geht das
    nicht: griechisch "γράφω" und "έγραψα" und "θα γράψω" haben keinen
    gemeinsamen Anfang, weil Augment und Partikel davortreten. Innerhalb einer
    Zeit ist der Stamm dagegen konstant — γράφ|ω, γράφ|εις, γράφ|ουμε. Und das
    ist ohnehin die Zerlegung, die beim Lernen hilft.
    """
    f = dbm.zeile(db, "SELECT * FROM form WHERE id = ?", (form_id,))
    if f is None:
        return []
    lexem = dbm.zeile(db, "SELECT * FROM lexem WHERE id = ?", (f["lexem_id"],))
    s = dbm.zeile(db, "SELECT sprache FROM sammlung WHERE id = ?",
                  (lexem["sammlung_id"],))
    fm = dbm.j_lesen(f["merkmale"])
    gruppe = _gruppe_der_form(s["sprache"], lexem["wortart"], fm)
    alle = dbm.zeilen(db, "SELECT * FROM form WHERE lexem_id = ?", (f["lexem_id"],))
    if gruppe is None or len(gruppe["zellen"]) < 2:
        # Einzelform ohne Reihe: dann die ganze Zeitgruppe nach Zeit und Modus
        schluessel = {d: fm[d] for d in ("tempus", "modus", "aspekt", "kasus")
                      if d in fm}
        if not schluessel:
            return [z["text"] for z in alle]
        return [z["text"] for z in alle
                if all(dbm.j_lesen(z["merkmale"]).get(d) == w
                       for d, w in schluessel.items())]
    return [z["text"] for z in alle
            if all(dbm.j_lesen(z["merkmale"]).get(d) == w
                   for d, w in gruppe["merkmale"].items())]


def frage(db: sqlite3.Connection, aufgabe_id: int) -> dict:
    """Baut die Aufgabe für die Oberfläche."""
    a = dbm.zeile(db, "SELECT * FROM aufgabe WHERE id = ?", (aufgabe_id,))
    if a is None:
        raise KeyError(f"Aufgabe {aufgabe_id} gibt es nicht")
    lexem = dbm.zeile(db, "SELECT * FROM lexem WHERE id = ?", (a["lexem_id"],))
    e = sammlung_einstellungen(db, lexem["sammlung_id"])
    code, grund = e["sprache"], e["grundsprache"]
    typ = a["typ"]
    lex_merkmale = dbm.j_lesen(lexem["merkmale"])

    kopf = {
        "aufgabe_id": a["id"],
        "typ": typ,
        "typ_name": TYPEN[typ]["name"],
        "eingabeart": TYPEN[typ]["eingabeart"],
        "lexem_id": lexem["id"],
        "wortart": lexem["wortart"],
        "wortart_name": mk.WORTARTEN.get(lexem["wortart"], lexem["wortart"]),
        "sprache": code,
        "grundsprache": grund,
    }

    if typ == "bedeutung_fremd_deutsch":
        bedeutungen = _alle_bedeutungen(db, lexem["id"], grund)
        return {**kopf,
                "frage_text": lexem["lemma"],
                "frage_sprache": code,
                "frage_zusatz": None,
                "antwort_sprache": grund,
                "anzahl_bedeutungen": len(bedeutungen),
                "vorlesen": lexem["lemma"]}

    if typ == "bedeutung_deutsch_fremd":
        b = dbm.zeile(db, "SELECT * FROM bedeutung WHERE id = ?", (a["ziel_id"],))
        ue = _uebersetzungen(db, b["id"], grund)
        return {**kopf,
                "frage_text": ue[0]["text"] if ue else "(keine Übersetzung)",
                "frage_sprache": grund,
                "frage_zusatz": b["kontext"],
                "antwort_sprache": code,
                "vorlesen": None}

    if typ == "form_bilden":
        f = dbm.zeile(db, "SELECT * FROM form WHERE id = ?", (a["ziel_id"],))
        fm = dbm.j_lesen(f["merkmale"])
        return {**kopf,
                "frage_text": lexem["lemma"],
                "frage_sprache": code,
                "frage_zusatz": sprachen.beschriften_form(code, lexem["wortart"], fm),
                "antwort_sprache": code,
                "vorlesen": lexem["lemma"]}

    if typ == "form_bestimmen":
        f = dbm.zeile(db, "SELECT * FROM form WHERE id = ?", (a["ziel_id"],))
        return {**kopf,
                "frage_text": f["text"],
                "frage_sprache": code,
                "frage_zusatz": f"von {lexem['lemma']}",
                "antwort_sprache": None,
                "dimensionen": _dimensionen(code, lexem["wortart"]),
                "vorlesen": f["text"]}

    if typ == "genus":
        artikel = sprachen.profil(code)["artikel"]["genus_artikel"]
        return {**kopf,
                "frage_text": lexem["lemma"],
                "frage_sprache": code,
                "frage_zusatz": "Welcher Artikel?",
                "antwort_sprache": code,
                "auswahl": [{"wert": g, "text": t} for g, t in artikel.items()],
                "vorlesen": lexem["lemma"]}

    raise ValueError(f"Unbekannter Aufgabentyp {typ!r}")


def _dimensionen(code: str, wortart: str) -> list[dict]:
    """Welche Auswahlfelder braucht "Form bestimmen"?

    Abgeleitet aus den Formgruppen der Sprache: nur Dimensionen, die dort
    überhaupt vorkommen, und nur mit den dort vorkommenden Werten.
    """
    verwendet: dict[str, list[str]] = {}
    for g in sprachen.formgruppen(code, wortart):
        for zelle in g["zellen"]:
            for d, w in zelle.items():
                verwendet.setdefault(d, [])
                if w not in verwendet[d]:
                    verwendet[d].append(w)
    ergebnis = []
    for d in mk.REIHENFOLGE:
        if d not in verwendet:
            continue
        werte = sorted(verwendet[d], key=lambda w: list(mk.INVENTAR[d]).index(w)
                       if w in mk.INVENTAR.get(d, {}) else 99)
        ergebnis.append({
            "dimension": d,
            "name": {"person": "Person", "numerus": "Zahl", "genus": "Geschlecht",
                     "kasus": "Fall", "stufe": "Steigerung", "tempus": "Zeit",
                     "modus": "Modus", "nonfinit": "Nennform",
                     "genus_verbi": "Form"}.get(d, d),
            "werte": [{"wert": w, "text": mk.INVENTAR[d][w][0]} for w in werte
                      if w in mk.INVENTAR.get(d, {})],
        })
    return ergebnis


# -------------------------------------------------------------- Antwort prüfen

def antwort_pruefen(db: sqlite3.Connection, aufgabe_id: int, eingabe,
                    fehler_benennen: bool = True) -> tuple[Urteil, dict]:
    """Prüft eine Antwort. Gibt Urteil und Auflösung zurück."""
    a = dbm.zeile(db, "SELECT * FROM aufgabe WHERE id = ?", (aufgabe_id,))
    if a is None:
        raise KeyError(f"Aufgabe {aufgabe_id} gibt es nicht")
    lexem = dbm.zeile(db, "SELECT * FROM lexem WHERE id = ?", (a["lexem_id"],))
    e = sammlung_einstellungen(db, lexem["sammlung_id"])
    code, grund = e["sprache"], e["grundsprache"]
    typ = a["typ"]
    p_code = dbm.profil_fuer(db, code)
    p_grund = dbm.profil_fuer(db, grund)

    if typ == "bedeutung_fremd_deutsch":
        bedeutungen = _alle_bedeutungen(db, lexem["id"], grund)
        gueltig = [u["text"] for b in bedeutungen for u in b["uebersetzungen"]]
        urteil = text_pruefen(str(eingabe), gueltig, p_grund,
                              fehler_benennen=fehler_benennen)
        return urteil, {"erwartet": gueltig, "bedeutungen": bedeutungen}

    if typ == "bedeutung_deutsch_fremd":
        gueltig = [lexem["lemma"]]
        vw = _verwechslungen(db, lexem, code, ausser_text=lexem["lemma"])
        urteil = text_pruefen(str(eingabe), gueltig, p_code, verwechslungen=vw,
                              fehler_benennen=fehler_benennen)
        return urteil, {"erwartet": gueltig}

    if typ == "form_bilden":
        f = dbm.zeile(db, "SELECT * FROM form WHERE id = ?", (a["ziel_id"],))
        fm = dbm.j_lesen(f["merkmale"])
        # Alle Formen des Lexems mit genau diesem Merkmalsbündel gelten —
        # es gibt Wörter mit zwei zulässigen Formen in derselben Zelle.
        gueltig = [z["text"] for z in
                   dbm.zeilen(db, "SELECT * FROM form WHERE lexem_id = ?",
                              (lexem["id"],))
                   if dbm.j_lesen(z["merkmale"]) == fm]
        vw = [(t, b) for t, b in _verwechslungen(db, lexem, code, None)
              if t not in gueltig]
        urteil = text_pruefen(str(eingabe), gueltig, p_code, verwechslungen=vw,
                              fehler_benennen=fehler_benennen)
        return urteil, {"erwartet": gueltig,
                        "beschriftung": sprachen.beschriften_form(
                            code, lexem["wortart"], fm)}

    if typ == "form_bestimmen":
        f = dbm.zeile(db, "SELECT * FROM form WHERE id = ?", (a["ziel_id"],))
        return _merkmale_pruefen(db, lexem, f, eingabe, code)

    if typ == "genus":
        artikel = sprachen.profil(code)["artikel"]["genus_artikel"]
        soll_genus = dbm.j_lesen(lexem["merkmale"]).get("genus")
        soll_artikel = artikel.get(soll_genus)
        if soll_artikel is None:
            # Das Geschlecht wurde nachträglich entfernt. Dann ist die Aufgabe
            # nicht beantwortbar — das soll dastehen und nicht "Richtig ist None".
            return Urteil("falsch", None,
                          "Zu diesem Wort ist kein Geschlecht hinterlegt. "
                          "Die Aufgabe wird beim nächsten Durchrechnen "
                          "abgeschaltet.", ["unbeantwortbar"]), {"erwartet": []}
        gegeben = str(eingabe).strip()
        # Sowohl das Kürzel ("f") als auch der Artikel selbst ("la") gelten.
        richtig = gegeben == soll_genus or gegeben.casefold() == soll_artikel.casefold()
        urteil = (Urteil("richtig", soll_artikel) if richtig
                  else Urteil("falsch", soll_artikel,
                              f"Richtig ist {soll_artikel}.", ["genus"]))
        return urteil, {"erwartet": [soll_artikel], "genus": soll_genus}

    raise ValueError(f"Unbekannter Aufgabentyp {typ!r}")


def _merkmale_pruefen(db: sqlite3.Connection, lexem: dict, form: dict,
                      eingabe, code: str) -> tuple[Urteil, dict]:
    """"Form bestimmen": die Antwort ist ein Merkmalsbündel.

    Mehrdeutige Formen sind der Normalfall — französisch "parle" ist
    1. und 3. Person Singular und Imperativ. Jede zutreffende Lesart gilt.
    """
    # Die Lesarten immer ermitteln — auch ohne Eingabe. Sonst liefert
    # "Lösung zeigen" bei dieser Aufgabenart nichts.
    lesarten_alle = [dbm.j_lesen(z["merkmale"]) for z in
                     dbm.zeilen(db, """SELECT * FROM form
                                        WHERE lexem_id = ? AND text = ?""",
                                (lexem["id"], form["text"]))]
    beschriftungen_alle = [sprachen.beschriften_form(code, lexem["wortart"], l)
                           for l in lesarten_alle]
    auflösung_leer = {"lesarten": lesarten_alle,
                      "beschriftungen": beschriftungen_alle,
                      "erwartet": beschriftungen_alle}

    if not isinstance(eingabe, dict) or not eingabe:
        return (Urteil("falsch", " / ".join(beschriftungen_alle),
                       "Keine Auswahl getroffen.", ["keine_auswahl"]),
                auflösung_leer)
    try:
        gegeben = mk.pruefen(eingabe)
    except mk.MerkmalFehler as fehler:
        return Urteil("falsch", hinweis=str(fehler)), auflösung_leer
    gegeben = {d: w for d, w in gegeben.items() if w}

    lesarten, beschriftungen = lesarten_alle, beschriftungen_alle
    auflösung = dict(auflösung_leer)

    if gegeben in lesarten:
        return Urteil("richtig", " / ".join(beschriftungen)), auflösung

    # Teilweise richtig: die Lesart mit den meisten Übereinstimmungen suchen.
    beste, treffer_zahl = None, -1
    for lesart in lesarten:
        gleich = sum(1 for d, w in lesart.items() if gegeben.get(d) == w)
        if gleich > treffer_zahl:
            beste, treffer_zahl = lesart, gleich
    falsch = [d for d, w in (beste or {}).items() if gegeben.get(d) != w]
    namen = {"person": "Person", "numerus": "Zahl", "tempus": "Zeit",
             "modus": "Modus", "kasus": "Fall", "genus": "Geschlecht",
             "stufe": "Steigerung", "nonfinit": "Nennform"}
    if falsch and treffer_zahl > 0:
        fehlend = ", ".join(namen.get(d, d) for d in falsch)
        return Urteil("falsch", " / ".join(beschriftungen),
                      f"Nicht ganz — {fehlend} stimmt nicht. "
                      f"Richtig: {' oder '.join(beschriftungen)}.",
                      ["merkmale"]), auflösung
    return Urteil("falsch", " / ".join(beschriftungen),
                  f"Richtig: {' oder '.join(beschriftungen)}.",
                  ["merkmale"]), auflösung
