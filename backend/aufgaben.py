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
import legasthenie
import merkmale as mk
import sprachen
from pruefung import Urteil, artikel_trennen, pruefen as text_pruefen

# Aufgabentypen. eingabeart steuert, was die Oberfläche anzeigt:
#   text      — Eingabefeld
#   merkmale  — Auswahlfelder für Person, Numerus, Zeit ...
#   auswahl   — Knöpfe mit vorgegebenen Antworten (Artikel)
TYPEN: dict[str, dict] = {
    "bedeutung_fremd_deutsch": {
        "name": "Bedeutung erkennen",
        "eingabeart": "text",
        "beschreibung": "Fremdsprachiges Wort, gesucht ist die Bedeutung.",
        "beispiel": "το σπίτι → das Haus",
    },
    "bedeutung_deutsch_fremd": {
        "name": "Wort bilden",
        "eingabeart": "text",
        "beschreibung": "Deutsche Bedeutung, gesucht ist das fremdsprachige Wort.",
        "beispiel": "das Haus → το σπίτι",
    },
    "form_bilden": {
        "name": "Form bilden",
        "eingabeart": "text",
        "beschreibung": "Grundform und Formangabe gegeben, gesucht ist die Form.",
        "beispiel": "γράφω, »du« → γράφεις",
    },
    "form_bestimmen": {
        "name": "Form bestimmen",
        "eingabeart": "merkmale",
        "beschreibung": "Form gegeben, gesucht ist, um welche Form es sich "
                        "handelt.",
        "beispiel": "γράφεις → wer? du",
    },
    "genus": {
        "name": "Artikel",
        "eingabeart": "auswahl",
        "beschreibung": "Gesucht ist der Artikel beziehungsweise das Geschlecht.",
        "beispiel": "το σπίτι → το",
    },
    "formenreihe": {
        "name": "Ganze Reihe",
        "eingabeart": "reihe",
        "beschreibung": "Eine ganze Tabelle auf einmal: alle Personen einer "
                        "Zeit, alle Fälle eines Hauptworts.",
        "beispiel": "ich gehe, du gehst, er/sie/es geht …",
    },
    # Die Stammformen sind KEINE Formgruppe, sondern eine Auswahl aus
    # mehreren: je eine Form aus Infinitiv, Präteritum und Partizip. Als
    # Reihe abfragbar waren sie darum bisher nicht — jede dieser Gruppen
    # hat nur eine Zelle, und "eine Zelle ist keine Reihe". Dabei ist
    # gerade das die Reihe, die man auswendig lernt: aus ihr leitet sich
    # das ganze Paradigma ab, und im Mittelhochdeutschen hängt daran die
    # Ablautreihe.
    "stammformen": {
        "name": "Stammformen",
        "eingabeart": "reihe",
        "beschreibung": "Die Formen, aus denen sich alle anderen ableiten — "
                        "auf einmal.",
        "beispiel": "nëmen – nam – nâmen – genomen",
    },
    # Was für ein Wort ist das? Das Geschlecht hat dafür seine eigene
    # Aufgabe, weil es als Artikel gefragt wird. Alles andere, was eine
    # Sprache als Lexemmerkmal mit fester Werteliste kennt, ist hiermit
    # abfragbar: die Ablautreihe, die Deklinationsklasse, das Hilfsverb.
    "klasse": {
        "name": "Klasse bestimmen",
        "eingabeart": "auswahl",
        "beschreibung": "Gesucht ist, zu welcher Klasse das Wort gehört — "
                        "Ablautreihe, Deklinationsklasse, Hilfsverb.",
        "beispiel": "rîten → stark I",
    },
}

TYPEN_STANDARD = ["bedeutung_fremd_deutsch", "bedeutung_deutsch_fremd",
                  "form_bilden", "genus"]


# ------------------------------------------------------------- Einstellungen

# Was eine Abfragevorlage bedeuten kann. Heute nur das Anschalten und
# Abschalten — mehr wollte sie je Wort ausdrücklich nicht, und ein
# Feld, das niemand füllt, ist schlimmer als keines.
VORLAGEN_FELDER = ("an",)

# Vorlagen, die jede Sammlung kennt, ohne dass jemand sie anlegt.
# Eigene Vorlagen in den Sammlungseinstellungen überschreiben sie.
VORLAGEN_STANDARD = {
    "voll": {"an": True},
    # Im Wortschatz, aber nicht in der Abfrage. Zwei Fälle, und beide
    # kommen oft vor: Wörter, die gerade NICHT dran sind (»genau die
    # Vokabeln, die sie mir als Liste gegeben hat«), und solche, die
    # man nachschlagen können will, ohne sie je zu pauken —
    # Eigennamen, Abkürzungen, Zahlwörter.
    "nachschlagen": {"an": False},
}


def abfragevorlagen(db: sqlite3.Connection, sammlung_id: int) -> dict:
    """Die benannten Auswahlpakete dieser Sammlung."""
    s = dbm.zeile(db, "SELECT einstellungen FROM sammlung WHERE id = ?",
                  (sammlung_id,))
    eigen = (dbm.j_lesen(s["einstellungen"]) if s else {}).get(
        "abfragevorlagen") or {}
    return {**VORLAGEN_STANDARD, **eigen}


def abfrage_deuten(wert, vorlagen: dict) -> dict:
    """Macht aus dem, was jemand hinschreibt, eine Einstellung.

    Angenommen wird dreierlei, weil drei verschiedene Stellen das
    schreiben: ein Vorlagenname (»nachschlagen«, von der KI beim
    Anlegen), ein Wahrheitswert (der Schalter in der Oberfläche) oder
    ein Objekt. Zurück kommt immer ein Objekt — und `vorlage` bleibt
    darin stehen, damit man später sieht, WARUM ein Wort stillliegt.
    """
    if wert is None or wert == "":
        return {}
    if isinstance(wert, bool):
        return {"an": wert}
    if isinstance(wert, str):
        vorlage = vorlagen.get(wert)
        if vorlage is None:
            raise KeyError(f"Unbekannte Abfragevorlage {wert!r}. "
                           f"Bekannt: {', '.join(sorted(vorlagen))}")
        return {**vorlage, "vorlage": wert}
    if isinstance(wert, dict):
        name = wert.get("vorlage")
        grund = dict(vorlagen.get(name) or {}) if name else {}
        grund.update({k: v for k, v in wert.items()
                      if k in VORLAGEN_FELDER})
        if name:
            grund["vorlage"] = name
        return grund
    raise KeyError(f"Mit {wert!r} ist nichts anzufangen")


def wird_abgefragt(lexem: dict) -> bool:
    """Soll dieses Wort überhaupt Aufgaben haben?"""
    return bool(dbm.j_lesen(lexem["abfrage"] or "{}").get("an", True))


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


def _klassenmerkmale(code: str, wortart: str) -> dict[str, list[str]]:
    """Lexemmerkmale mit fester Werteliste, die sich abfragen lassen.

    Ohne das Geschlecht: das hat seine eigene Aufgabe, weil es als
    ARTIKEL gefragt wird und nicht als Kürzel — »der« statt »m«. Zwei
    Aufgaben für dieselbe Auskunft wären eine zu viel.
    """
    erlaubt = sprachen.profil(code).get("lexemmerkmale", {}).get(wortart, {})
    return {d: list(w) for d, w in erlaubt.items()
            if d != "genus" and len(w) >= 2}


def _stammformgruppen(code: str, wortart: str) -> list[dict]:
    """Die Formgruppen, die in dieser Sprache die Stammformen bilden.

    Aus `stammformen` im Sprachprofil, in dessen Reihenfolge — die ist
    die gelernte (nëmen – nam – nâmen – genomen, nicht alphabetisch).
    Nur Gruppen DIESER Wortart: die Liste ist flach, aber Stammformen
    hat nur das Verb.
    """
    nach = {g["kennung"]: g for g in sprachen.formgruppen(code, wortart)}
    return [nach[k] for k in sprachen.profil(code).get("stammformen", [])
            if k in nach]


def _stammform_zellen(code: str, wortart: str) -> list[dict]:
    """Je Gruppe EINE Zelle — die erste.

    Bei einer einzelligen Gruppe (Infinitiv, Partizip) ist das die
    einzige. Bei einer Personenreihe ist es die 1. Person Singular, und
    genau so steht die Stammform auch im Lehrbuch: »ich ging«, nicht die
    ganze Präteritumstabelle. Wer die will, nimmt die ganze Reihe.
    """
    return [{"gruppe": g, "zelle": g["zellen"][0]}
            for g in _stammformgruppen(code, wortart) if g["zellen"]]


def _gruppe_der_form(code: str, wortart: str, merkmale: dict) -> dict | None:
    """Zu welcher Formgruppe gehört diese Form? Die spezifischste gewinnt."""
    voll = mk.normieren(merkmale, wortart)
    treffer = [g for g in sprachen.formgruppen(code, wortart)
               if all(voll.get(d) == w for d, w in g["merkmale"].items())]
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

    # Stillgelegt heißt: gar keine Aufgaben. Nicht gelöscht, nur
    # abgeschaltet — weiter unten wird abgeschaltet, was nicht
    # gewünscht ist, und damit bleibt der Lernstand erhalten, falls
    # das Wort später wieder dazukommt.
    if not wird_abgefragt(lexem):
        return _abgleichen(db, lexem_id, {})
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
            ("bedeutung_fremd_deutsch", "lexem", None, None)

    # Wort bilden: je Bedeutung, denn die Richtung Deutsch -> Fremdsprache
    # braucht die Bedeutung zur Unterscheidung.
    if "bedeutung_deutsch_fremd" in e["typen"]:
        for b in bedeutungen:
            if dbm.wert(db, """SELECT 1 FROM uebersetzung
                                WHERE bedeutung_id = ? AND sprache = ? LIMIT 1""",
                        (b["id"], e["grundsprache"])):
                sch = _schluessel("bedeutung_deutsch_fremd", lexem_id,
                                  "bedeutung", str(b["id"]))
                gewuenscht[sch] = ("bedeutung_deutsch_fremd", "bedeutung",
                                   b["id"], None)

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
        # NORMALFORM, nicht das rohe Bündel. Der Schlüssel ist dafür da,
        # dass eine Aufgabe dieselbe bleibt, wenn sich an den Daten etwas
        # ändert — nur so überlebt der Lernstand eine Berichtigung.
        # Roh genommen änderte er sich, sobald jemand ein unmarkiertes
        # Merkmal ausdrücklich nachtrug (genus_verbi: aktiv steht ohnehin
        # da, nur ungeschrieben). Die alte Aufgabe wurde abgeschaltet,
        # eine neue angelegt, und der Lernstand hing an der alten.
        # Drei Zeilen tiefer, bei der Formenreihe, stand es immer richtig.
        kennzeichen = mk.schluessel(mk.normieren(fm, wortart))
        for typ in ("form_bilden", "form_bestimmen"):
            if typ in e["typen"]:
                gewuenscht[_schluessel(typ, lexem_id, "merkmale", kennzeichen)] = \
                    (typ, "form", f["id"],
                     gruppe["kennung"] if gruppe else None)

    # Ganze Reihe: eine Aufgabe je FORMGRUPPE, nicht je Form. Das ist die
    # Art, wie man Konjugationen wirklich lernt — ich gehe, du gehst, er
    # geht —, und sie prüft etwas anderes als sechs Einzelabfragen: ob die
    # Reihe als Ganzes sitzt.
    if "formenreihe" in e["typen"]:
        for gruppe in sprachen.formgruppen(code, wortart):
            if len(gruppe["zellen"]) < 2:
                continue            # eine Zelle ist keine Reihe
            if gruppe["kennung"] not in e["formgruppen"]:
                continue
            belegt = [f for f in formen
                      if not f["ist_grundform"]
                      and (f["geprueft"] or e["ungeprueft_abfragen"])
                      and dbm.j_lesen(f["merkmale"])
                      and _gruppe_der_form(code, wortart,
                                           dbm.j_lesen(f["merkmale"]))
                          is not None
                      and _gruppe_der_form(code, wortart,
                                           dbm.j_lesen(f["merkmale"])
                                           )["kennung"] == gruppe["kennung"]]
            # Eine halbe Tabelle abzufragen wäre ärgerlich: man tippt in
            # Felder, zu denen es keine Antwort gibt. Erst ab vollständig
            # (abzüglich erklärter Lücken) lohnt die Reihe.
            luecken = dbm.j_lesen(lexem["luecken"], [])
            noetig = [z for z in gruppe["zellen"]
                      if not mk.ist_erklaerte_luecke(luecken, z)]
            vorhandene = {mk.schluessel(mk.normieren(dbm.j_lesen(f["merkmale"]),
                                                     wortart))
                          for f in belegt}
            if not noetig or any(
                    mk.schluessel(mk.normieren(z, wortart)) not in vorhandene
                    for z in noetig):
                continue
            gewuenscht[_schluessel("formenreihe", lexem_id, "gruppe",
                                   gruppe["kennung"])] = \
                ("formenreihe", "gruppe", None, gruppe["kennung"])

    # Stammformen: eine Aufgabe je Lexem, nicht je Gruppe — es ist ja
    # gerade die Reihe QUER durch die Gruppen.
    if "stammformen" in e["typen"]:
        zellen = _stammform_zellen(code, wortart)
        # Nur Gruppen, die diese Sammlung überhaupt abfragt — dieselbe
        # Regel wie bei der ganzen Reihe.
        if any(z["gruppe"]["kennung"] not in e["formgruppen"] for z in zellen):
            zellen = []
        luecken = dbm.j_lesen(lexem["luecken"], [])
        noetig = [z["zelle"] for z in zellen
                  if not mk.ist_erklaerte_luecke(luecken, z["zelle"])]
        # Dieselbe Regel wie bei der ganzen Reihe: eine halbe Tabelle
        # abzufragen heißt, in Felder zu tippen, zu denen es keine
        # Antwort gibt. Und unter zwei Formen ist es keine Reihe.
        vorhandene = {mk.schluessel(mk.normieren(dbm.j_lesen(f["merkmale"]),
                                                 wortart))
                      for f in formen
                      if (f["geprueft"] or e["ungeprueft_abfragen"])
                      and dbm.j_lesen(f["merkmale"])}
        if len(noetig) >= 2 and all(
                mk.schluessel(mk.normieren(z, wortart)) in vorhandene
                for z in noetig):
            # Welche Formgruppe in die Spalte kommt, entscheidet, WANN
            # die Reihe freigeschaltet ist: die Lektionsschranke prüft
            # genau diese eine. Leer zu lassen wäre bequem und falsch —
            # die Reihe enthält das Präteritum, und das käme dann, bevor
            # das Lehrwerk es eingeführt hat. Genau dieser Fehler ist
            # beim griechischen Aorist schon einmal passiert.
            #
            # Also die LETZTE der beteiligten Gruppen. Die Reihenfolge in
            # `stammformen` ist die gelernte, und das Partizip steht dort
            # am Ende, weil es im Lehrbuch zuletzt kommt. Die Reihe
            # wartet damit auf ihren spätesten Bestandteil. Eine
            # Annahme ist das trotzdem: sie hängt daran, dass die
            # Profilreihenfolge der Einführungsreihenfolge entspricht.
            # Im Zweifel wartet die Reihe zu lange — das ist die
            # harmlosere Richtung.
            letzte = zellen[-1]["gruppe"]["kennung"]
            gewuenscht[_schluessel("stammformen", lexem_id, "lexem", "")] = \
                ("stammformen", "lexem", None, letzte)

    # Klasse: je Lexemmerkmal mit fester Werteliste eine Aufgabe — aber
    # nur, wenn an diesem Wort auch wirklich etwas steht. Ein Verb ohne
    # eingetragene Ablautreihe ergäbe eine Frage ohne Antwort.
    if "klasse" in e["typen"]:
        for merkmal, werte in _klassenmerkmale(code, wortart).items():
            if lex_merkmale.get(merkmal) in werte:
                # Die Spalte `formgruppe` bleibt leer wie beim Artikel:
                # sie ist der SQL-Filter der Abfrage, und eine Klasse ist
                # keine Formgruppe. Welches Merkmal gemeint ist, steht im
                # Schlüssel.
                gewuenscht[_schluessel("klasse", lexem_id, "lexem", merkmal)] = \
                    ("klasse", "lexem", None, None)

    # Artikel: nur wo die Sprache überhaupt Artikel nach Geschlecht hat.
    artikel = sprachen.profil(code).get("artikel", {}).get("genus_artikel", {})
    # "mf" steht nicht in der Artikeltabelle — es bedeutet ja gerade, dass
    # zwei Artikel gelten. Die Aufgabe soll trotzdem entstehen.
    if ("genus" in e["typen"] and wortart == "substantiv"
            and (lex_merkmale.get("genus") in artikel
                 or (lex_merkmale.get("genus") == "mf" and artikel))):
        gewuenscht[_schluessel("genus", lexem_id, "lexem", "")] = \
            ("genus", "lexem", None, None)

    return _abgleichen(db, lexem_id, gewuenscht)


def _abgleichen(db: sqlite3.Connection, lexem_id: int,
                gewuenscht: dict) -> dict:
    """Bringt die Aufgaben eines Lexems auf die gewünschte Menge.

    Abgeschaltet statt gelöscht: so bleibt der Lernstand erhalten,
    wenn eine Formgruppe nur zeitweise abgewählt ist — oder wenn ein
    Wort stillgelegt und später wieder dazugenommen wird.
    """
    vorhanden = {a["schluessel"]: a for a in
                 dbm.zeilen(db, "SELECT * FROM aufgabe WHERE lexem_id = ?", (lexem_id,))}

    angelegt = reaktiviert = abgeschaltet = 0
    for sch, (typ, ziel_art, ziel_id, formgruppe) in gewuenscht.items():
        alt = vorhanden.get(sch)
        if alt is None:
            db.execute("""INSERT INTO aufgabe
                            (lexem_id, typ, ziel_art, ziel_id, schluessel,
                             formgruppe, aktiv)
                          VALUES (?, ?, ?, ?, ?, ?, 1)""",
                       (lexem_id, typ, ziel_art, ziel_id, sch, formgruppe))
            angelegt += 1
        else:
            if not alt["aktiv"]:
                reaktiviert += 1
            # ziel_id und Formgruppe nachziehen: die Form kann neu angelegt
            # worden sein, und die Gruppe wird hier mitgeführt, damit die
            # Abfrage danach in SQL aussieben kann statt hinterher in
            # Python. Ein Fenster nachzusortieren ist hier schon mehrfach
            # schiefgegangen.
            db.execute("""UPDATE aufgabe SET aktiv = 1, ziel_id = ?,
                                             formgruppe = ?
                           WHERE id = ?""", (ziel_id, formgruppe, alt["id"]))
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


def _bedeutungstext(db: sqlite3.Connection, lexem_id: int,
                    grundsprache: str) -> str | None:
    """Die deutsche Bedeutung eines Wortes, kurz — je Bedeutung die
    erste Übersetzung.

    »Beim Verben abfragen (Reihe) kannst du bitte die deutsche
    Übersetzung danebenschreiben, das ist dort ok.«

    »Dort ok« ist der entscheidende Teil. Bei einer Bedeutungsaufgabe
    wäre die Übersetzung die Lösung; bei einer Reihe ist sie es nicht —
    gefragt sind sechs Formen, und wer weiß, dass »aller« gehen heißt,
    hat davon keine einzige. Er weiß nur, wovon er redet, und das hilft
    beim Behalten.

    Je Bedeutung die ERSTE Übersetzung und nicht alle: »gehen, laufen,
    zu Fuß gehen, fahren« ist eine Liste, »gehen, fahren« eine
    Auskunft.
    """
    texte = []
    for b in _alle_bedeutungen(db, lexem_id, grundsprache):
        if b["uebersetzungen"]:
            texte.append(b["uebersetzungen"][0]["text"])
    return ", ".join(texte[:3]) or None


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


def gleichbedeutende(db: sqlite3.Connection, lexem: dict, bedeutung_id: int,
                     grundsprache: str) -> list[dict]:
    """Andere Wörter derselben Sammlung mit derselben Übersetzung.

    »klein« führt im Griechischen auf μικρός und κοντός, »arbeiten« auf
    δουλεύω und εργάζομαι. Wer bei der Frage »klein« κοντός schreibt, hat
    nicht geirrt — er hat das andere richtige Wort genannt. Es als falsch
    zu werten wäre schlicht unwahr und würde den Lernstand verderben.

    Verglichen wird über die kleingeschriebene Übersetzung: »Der Brief«
    und »der Brief« sind dasselbe Wort.
    """
    texte = [u["text"].casefold().strip() for u in
             dbm.zeilen(db, """SELECT text FROM uebersetzung
                                WHERE bedeutung_id = ? AND sprache = ?""",
                        (bedeutung_id, grundsprache))]
    if not texte:
        return []
    # Verglichen wird in Python, nicht in SQL.
    #
    # Hier stand `LOWER(TRIM(u.text)) IN (…)`. SQLites eingebautes LOWER
    # wirkt nur auf ASCII: lower('Öl') ist 'Öl', verglichen wurde aber
    # gegen das Python-seitige casefold 'öl'. Jede Übersetzung mit
    # Umlaut am Anfang — Öl, Übung, Äpfel, Ärmel — fiel damit durch, und
    # das zweite richtige Wort wurde als Nichtwissen protokolliert.
    # Genau das, was der Text oben ausschließen will.
    gesucht = set(texte)
    alle = dbm.zeilen(db, """
        SELECT DISTINCT l.id AS lexem_id, l.lemma, b.kontext, u.text
          FROM uebersetzung u
          JOIN bedeutung b ON b.id = u.bedeutung_id
          JOIN lexem l ON l.id = b.lexem_id
         WHERE l.sammlung_id = ? AND l.id != ?
           AND u.sprache = ?
         ORDER BY l.lemma""",
        (lexem["sammlung_id"], lexem["id"], grundsprache))
    gesehen, treffer = set(), []
    for z in alle:
        if z["text"].casefold().strip() not in gesucht:
            continue
        if z["lexem_id"] in gesehen:
            continue
        gesehen.add(z["lexem_id"])
        treffer.append({"lexem_id": z["lexem_id"], "lemma": z["lemma"],
                        "kontext": z["kontext"]})
    return treffer


def _merkmale(zeile: dict) -> dict:
    return dbm.j_lesen(zeile["merkmale"] or "{}") or {}


def nicht_unterschieden(db: sqlite3.Connection, lexem: dict,
                        bedeutung: dict, grundsprache: str) -> list[dict]:
    """Welche gleichbedeutenden Wörter die Frage NICHT ausschließt.

    Die Gegenseite zu `unterscheidung`: was dort nicht gesagt wird,
    darf die Wertung nicht verlangen.

    Der erste Entwurf fragte das in einem Zug — »unterscheiden die
    Merkmale von ALLEN, ja oder nein« —, und das war zu grob. Bei »die«
    stehen im griechischen Bestand sieben Wörter; τους hatte noch keine
    Merkmale eingetragen. Ein einziges unbestimmtes Wort machte damit
    die Frage für alle übrigen wieder mehrdeutig, obwohl »Nominativ
    Plural neutrum« η, την und τις sehr wohl ausschließt.

    Also je Wort einzeln: wen die Bestimmung trifft, der fällt weg;
    wen sie nicht erreicht, der bleibt eine gültige Antwort. Das ist
    auch der Weg, auf dem sich der Bestand von selbst verbessert —
    jedes nachgetragene Merkmalsbündel macht eine Frage schärfer, ohne
    dass die anderen fertig sein müssten.
    """
    andere = gleichbedeutende(db, lexem, bedeutung["id"], grundsprache)
    if not andere:
        return []
    fm = _merkmale(lexem)
    if not fm:
        # Ohne Merkmale entscheidet wie bisher der Kontext: steht einer
        # da, ist gesagt, welches Wort gemeint ist.
        return [] if (bedeutung["kontext"] or "").strip() else andere
    ids = [x["lexem_id"] for x in andere]
    platz = ",".join("?" * len(ids))
    fremde = {z["id"]: _merkmale(z) for z in dbm.zeilen(
        db, f"SELECT id, merkmale FROM lexem WHERE id IN ({platz})", ids)}
    return [x for x in andere
            if not _unterscheidet(fm, fremde.get(x["lexem_id"], {}))]


def _unterscheidet(meine: dict, fremde: dict) -> bool:
    """Sagen diese Merkmale, welches der beiden Wörter gemeint ist?

    Verglichen werden NUR die Dimensionen, die beide tragen. Das ist der
    springende Punkt und war im ersten Entwurf falsch:

      το (Artikel) hat {Nominativ, Singular, neutrum},
      αυτό (Pronomen) hat {3. Person, Singular, neutrum}.

    Die Bündel sind verschieden — die Beschriftungen »Nominativ
    Singular neutrum« und »3. Person Singular neutrum« unterscheiden
    aber nichts, was jemand bei der Frage »es« entscheiden könnte.
    Gemeinsam haben sie Numerus und Genus, und darin stimmen sie
    überein. Also bleibt die Frage mehrdeutig, und beide Antworten
    gelten.

    Ohne gemeinsame Dimension lässt sich nichts entscheiden — dann
    ebenfalls nein.
    """
    gemeinsam = set(meine) & set(fremde)
    return bool(gemeinsam) and any(meine[d] != fremde[d] for d in gemeinsam)


def unterscheidung(db: sqlite3.Connection, lexem: dict, bedeutung: dict,
                   grundsprache: str, code: str,
                   stil: str = "fach") -> str | None:
    """Woran man erkennt, WELCHES Wort gefragt ist — oder None.

    »ich weiß sie, aber anhand der Fragen weiß ich nie, welcher gemeint
    ist.« Gemessen an ihrem Bestand: die Frage lautete »ein«, und
    richtig waren je nach Geschlecht ένας, μία oder ένα. »die« führte
    auf sechs verschiedene Artikel. Das ist keine Wissenslücke, das ist
    eine unbeantwortbare Frage.

    ZWEI QUELLEN, und die MERKMALE GEWINNEN:

      Die Merkmale des Lexems — »Nominativ Plural neutrum«, beschriftet
      wie überall sonst und im eingestellten Stil (»wer oder was?,
      Mehrzahl, sächlich«). Verlässlich, weil aus dem Paradigma und
      nicht von Hand getippt.

      Der Kontext der Bedeutung — »klein, Körpergröße«. Freitext von
      einem Menschen oder einem Agenten. Hilfreich, wo er gut ist; in
      ihrem Bestand stand dort aber auch »n«, »f, betont« und einmal
      »ihr: ihr (2. Person Plural, Subjekt); Sie: Sie (höflich) / ihr«.

    Beides nebeneinanderzustellen war der erste Entwurf und war falsch:
    aus »2. Person Plural« wurde dann »2. Person Plural · ihr: ihr
    (2. Person Plural, Subjekt); Sie: …«. Sagen die Merkmale es schon,
    ist der Freitext Lärm. Wo sie schweigen — bei »klein« etwa, das
    keine Merkmale hat, sondern eine Bedeutungsnuance —, bleibt der
    Kontext die einzige Quelle und wird gezeigt.

    NUR WENN ES ETWAS ZU VERWECHSELN GIBT. Bei »das Haus« wäre
    »neutrum« Lärm anderer Art — das steht im deutschen Artikel schon
    drin. Erst wenn ein zweites Wort derselben Sammlung dieselbe
    Übersetzung hat, muss die Frage sagen, welches gemeint ist.

    UND NUR, WENN DIE MERKMALE WIRKLICH UNTERSCHEIDEN (siehe
    `_unterscheidet`). μία und μια sind beide Nominativ Singular
    feminin; dort hülfe die Beschriftung nichts. Dann bleibt die Frage
    mehrdeutig — und `pruefen` lässt beide Antworten gelten.
    """
    fm = _merkmale(lexem)
    if fm and bedeutung and gleichbedeutende(db, lexem, bedeutung["id"],
                                             grundsprache):
        # `mk.beschriften` und NICHT `sprachen.beschriften_form`: das
        # sucht eine passende Formgruppe und stellt deren Namen voran.
        # Bei den griechischen Artikeln kam dabei »maskulin Nominativ
        # Singular« heraus — die Gruppe heißt »maskulin«, und der Rest
        # hing hinten dran. Hier geht es nicht um eine Formgruppe,
        # sondern um die Bestimmung des Wortes selbst.
        beschriftung = mk.beschriften(fm, stil=stil)
        if beschriftung:
            return beschriftung
    kontext = (bedeutung or {})["kontext"] if bedeutung else None
    return (kontext or "").strip() or None


def stamm_fuer_aufgabe(db: sqlite3.Connection, aufgabe_id: int) -> str:
    """Der Wortstamm für die Zerlegung — in dieser Reihenfolge:

    1. von Hand gesetzt (lexem.staemme je Formgruppe) — wo die Ableitung
       nicht trägt, etwa bei Suppletion
    2. abgeleitet aus den Geschwisterformen derselben Formgruppe,
       ohne Varianten und ohne vorangestellte Partikel
    """
    a = dbm.zeile(db, """SELECT lexem_id, ziel_art, ziel_id FROM aufgabe
                          WHERE id = ?""", (aufgabe_id,))
    if a is None:
        return ""
    lexem = dbm.zeile(db, "SELECT * FROM lexem WHERE id = ?", (a["lexem_id"],))
    if lexem is None:
        return ""
    sammlung = dbm.zeile(db, "SELECT sprache FROM sammlung WHERE id = ?",
                         (lexem["sammlung_id"],))
    code = sammlung["sprache"]
    teilchen = sprachen.partikeln(code)

    gruppe = None
    if a["ziel_art"] == "form" and a["ziel_id"]:
        f = dbm.zeile(db, "SELECT merkmale FROM form WHERE id = ?", (a["ziel_id"],))
        if f is not None:
            gruppe = _gruppe_der_form(code, lexem["wortart"],
                                      dbm.j_lesen(f["merkmale"]))

    von_hand = dbm.j_lesen(lexem["staemme"], {})
    if gruppe and von_hand.get(gruppe["kennung"]):
        return von_hand[gruppe["kennung"]]
    if von_hand.get("*"):
        return von_hand["*"]

    if a["ziel_art"] == "form" and a["ziel_id"]:
        geschwister = geschwisterformen(db, a["ziel_id"])
    else:
        geschwister = [z["text"] for z in dbm.zeilen(
            db, "SELECT text FROM form WHERE lexem_id = ? AND ist_variante = 0",
            (a["lexem_id"],))]
    return legasthenie.stamm(geschwister, teilchen)


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
    # Varianten bleiben draußen: μιλάω und μιλώ stehen in derselben Zelle,
    # ihr gemeinsamer Anfang wäre kürzer als der wirkliche Stamm.
    alle = dbm.zeilen(db, """SELECT * FROM form
                              WHERE lexem_id = ? AND ist_variante = 0""",
                      (f["lexem_id"],))
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
            if all(mk.normieren(dbm.j_lesen(z["merkmale"]),
                                lexem["wortart"]).get(d) == w
                   for d, w in gruppe["merkmale"].items())]


def _reihe_zellen(db: sqlite3.Connection, a: dict, lexem: dict, code: str,
                  stil: str = "fach") -> tuple[dict | None, list[dict]]:
    """Gruppe und Zellen einer Reihenaufgabe, mit den gültigen Antworten.

    Die Gruppenkennung steht im Schlüssel — eine Reihe hängt an keiner
    einzelnen Form, sondern an der Tabelle.
    """
    kennung = a["schluessel"].rsplit(":", 1)[-1]
    gruppe = next((g for g in sprachen.formgruppen(code, lexem["wortart"])
                   if g["kennung"] == kennung), None)
    if gruppe is None:
        return None, []
    formen = dbm.zeilen(db, "SELECT * FROM form WHERE lexem_id = ?",
                        (lexem["id"],))
    nach_zelle: dict[str, list[str]] = {}
    for f in formen:
        fm = dbm.j_lesen(f["merkmale"])
        if not fm:
            continue
        nach_zelle.setdefault(
            mk.schluessel(mk.normieren(fm, lexem["wortart"])), []).append(f["text"])
    luecken = dbm.j_lesen(lexem["luecken"], [])
    zellen = []
    for zelle in gruppe["zellen"]:
        if mk.ist_erklaerte_luecke(luecken, zelle):
            continue
        schl = mk.schluessel(mk.normieren(zelle, lexem["wortart"]))
        eigen = {d: w for d, w in zelle.items() if d not in gruppe["merkmale"]}
        zellen.append({
            "zelle": schl,
            "merkmale": zelle,
            # Nur, was diese Zeile von ihren Geschwistern unterscheidet —
            # der Gruppenname steht als Überschrift darüber.
            "beschriftung": (mk.beschriften(eigen, stil=stil) if eigen
                             else sprachen.beschriften_form(
                                 code, lexem["wortart"], zelle, stil=stil)),
            "beispiel": mk.beispiel(zelle),
            "pronomen": sprachen.personalpronomen(code, zelle),
            "erwartet": nach_zelle.get(schl, []),
        })
    return gruppe, zellen


def _stammform_reihe(db: sqlite3.Connection, lexem: dict,
                     code: str) -> list[dict]:
    """Die Zellen der Stammformenreihe, in derselben Gestalt wie bei der
    ganzen Reihe — damit Oberfläche und Prüfung nichts unterscheiden
    müssen.

    Beschriftet wird mit dem KURZNAMEN der Gruppe (»Prät. Sg.«), nicht
    mit den Merkmalen der Zelle. Bei einer Reihe quer durch die Gruppen
    ist der Gruppenname das Unterscheidende; »1. Person Singular« stünde
    sonst zweimal da und sagte nichts.
    """
    nach_zelle: dict[str, list[str]] = {}
    for f in dbm.zeilen(db, "SELECT * FROM form WHERE lexem_id = ?",
                        (lexem["id"],)):
        fm = dbm.j_lesen(f["merkmale"])
        if fm:
            nach_zelle.setdefault(
                mk.schluessel(mk.normieren(fm, lexem["wortart"])),
                []).append(f["text"])
    luecken = dbm.j_lesen(lexem["luecken"], [])
    zellen = []
    for eintrag in _stammform_zellen(code, lexem["wortart"]):
        zelle, gruppe = eintrag["zelle"], eintrag["gruppe"]
        if mk.ist_erklaerte_luecke(luecken, zelle):
            continue
        schl = mk.schluessel(mk.normieren(zelle, lexem["wortart"]))
        zellen.append({
            "zelle": schl,
            "merkmale": zelle,
            "beschriftung": gruppe.get("kurz") or gruppe["name"],
            "beispiel": mk.beispiel(zelle),
            "pronomen": sprachen.personalpronomen(code, zelle),
            "erwartet": nach_zelle.get(schl, []),
        })
    return zellen


def frage(db: sqlite3.Connection, aufgabe_id: int, stil: str = "fach") -> dict:
    """Baut die Aufgabe für die Oberfläche.

    `stil` bestimmt, wie die Form benannt wird: "Genitiv Singular",
    "wessen?, Einzahl" oder beides. Die Wahl trifft die lernende Person —
    an der Fachbezeichnung scheitert man mitten in der Abfrage, und dann
    ist nicht die Vokabel schuld.
    """
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
                # Nicht mehr bloß der Kontext: auch die Merkmale, wenn
                # es ohne sie mehrdeutig wäre. »ein« allein ist keine
                # Frage, »ein (Nominativ Singular neutrum)« schon.
                "frage_zusatz": unterscheidung(db, lexem, b, grund, code,
                                               stil=stil),
                "antwort_sprache": code,
                "vorlesen": None}

    if typ == "form_bilden":
        f = dbm.zeile(db, "SELECT * FROM form WHERE id = ?", (a["ziel_id"],))
        fm = dbm.j_lesen(f["merkmale"])
        return {**kopf,
                "frage_text": lexem["lemma"],
                "frage_sprache": code,
                "frage_zusatz": sprachen.beschriften_form(
                    code, lexem["wortart"], fm, stil=stil),
                # Ein Beispiel auf Deutsch. "wen oder was?" ist schon
                # besser als "Akkusativ", aber erst "ich sehe DEN Hund"
                # macht es in einer Sekunde klar.
                "frage_hilfe": mk.beispiel(fm),
                # Wer gemeint ist, in der Sprache selbst. Im Griechischen
                # in Klammern: dort sagt die Endung es schon, aber sehen
                # will man es trotzdem.
                "pronomen": sprachen.personalpronomen(code, fm),
                "pronomen_pflicht": sprachen.pronomen_pflicht(code),
                "antwort_sprache": code,
                "vorlesen": lexem["lemma"]}

    if typ == "formenreihe":
        gruppe, zellen = _reihe_zellen(db, a, lexem, code, stil)
        return {**kopf,
                "frage_text": lexem["lemma"],
                "frage_sprache": code,
                "frage_zusatz": gruppe["name"] if gruppe else "",
                # Die Bedeutung darf hier mitstehen — sie ist nicht die
                # Lösung. Gefragt sind die Formen.
                "bedeutung": _bedeutungstext(db, lexem["id"], grund),
                "antwort_sprache": code,
                # Ohne die erwarteten Antworten — die Lösung gehört nicht
                # in die Frage.
                "zellen": [{k: v for k, v in z.items() if k != "erwartet"}
                           for z in zellen],
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

    if typ == "stammformen":
        zellen = _stammform_reihe(db, lexem, code)
        return {**kopf,
                "frage_text": lexem["lemma"],
                "frage_sprache": code,
                "frage_zusatz": "Stammformen",
                # Wie bei der Reihe: die Bedeutung verrät hier nichts.
                # Bei »nëmen – nam – nâmen – genomen« hilft es sogar
                # besonders, weil man das Wort beim Üben sonst nur als
                # Lautfolge behandelt.
                "bedeutung": _bedeutungstext(db, lexem["id"], grund),
                "antwort_sprache": code,
                "zellen": [{k: v for k, v in z.items() if k != "erwartet"}
                           for z in zellen],
                "vorlesen": lexem["lemma"]}

    if typ == "klasse":
        merkmal = a["schluessel"].rsplit(":", 1)[-1]
        werte = _klassenmerkmale(code, lexem["wortart"]).get(merkmal, [])
        return {**kopf,
                "frage_text": lexem["lemma"],
                "frage_sprache": code,
                "frage_zusatz": sprachen.klassenfrage(code, lexem["wortart"],
                                                      merkmal),
                "antwort_sprache": None,
                "auswahl": [{"wert": w, "text": w} for w in werte],
                "vorlesen": lexem["lemma"]}

    if typ == "genus":
        artikel = sprachen.profil(code)["artikel"]["genus_artikel"]
        gemeinsam = dbm.j_lesen(lexem["merkmale"]).get("genus") == "mf"
        # OHNE den Artikel. Er steht im Lemma (»το αγόρι«) — und er IST
        # die Antwort. Gemessen am laufenden Bestand: 909 von 928
        # Artikelaufgaben zeigten sie an, also praktisch alle. Wer hier
        # richtig lag, hat nichts bewiesen, und FSRS hat daraus
        # geschlossen, das Wort sitze.
        ohne = artikel_trennen(lexem["lemma"],
                               dbm.profil_fuer(db, code))[1]
        return {**kopf,
                "frage_text": ohne or lexem["lemma"],
                "frage_sprache": code,
                "frage_zusatz": ("Welcher Artikel? (gemeinsames Geschlecht — "
                                 "beide gelten)" if gemeinsam
                                 else "Welcher Artikel?"),
                "antwort_sprache": code,
                "auswahl": [{"wert": g, "text": t} for g, t in artikel.items()],
                # Vorgelesen wird das Wort OHNE Artikel, aus demselben
                # Grund: »το αγόρι« zu hören beantwortet die Frage.
                "vorlesen": ohne or lexem["lemma"]}

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
            "name": mk.name_der_dimension(d),
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
        b = dbm.zeile(db, "SELECT * FROM bedeutung WHERE id = ?", (a["ziel_id"],))
        # Steht in der Frage eine Unterscheidung — ein Kontext wie
        # »klein, Körpergröße« oder die Merkmale wie »Nominativ Plural
        # neutrum« —, ist gesagt, welches Wort gemeint ist; dann gilt
        # nur dieses. Fehlt sie, ist die Frage mehrdeutig, und jedes
        # Wort mit derselben Übersetzung ist eine richtige Antwort.
        #
        # DIESELBE Funktion wie in der Frage, und das ist der Punkt:
        # was die Frage nicht sagt, darf die Wertung nicht verlangen.
        auch = nicht_unterschieden(db, lexem, b, grund) if b else []
        gueltig += [x["lemma"] for x in auch]
        vw = [(t, bs) for t, bs in
              _verwechslungen(db, lexem, code, ausser_text=lexem["lemma"])
              if t not in gueltig]
        urteil = text_pruefen(str(eingabe), gueltig, p_code, verwechslungen=vw,
                              fehler_benennen=fehler_benennen)
        auskunft = {"erwartet": gueltig}
        if auch and urteil.treffer and urteil.treffer != lexem["lemma"]:
            # Sagen, dass beides geht — sonst wirkt das richtige Urteil
            # wie ein Zufall, und das gesuchte Wort bleibt ungelernt.
            auskunft["auch_richtig"] = [x["lemma"] for x in auch]
            auskunft["gesucht_war"] = lexem["lemma"]
        return urteil, auskunft

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
        # Den Artikel darf man mitschreiben — bei einem Hauptwort gehört
        # er sogar dazu. Welcher es ist, weiß die Sprache aus Geschlecht,
        # Fall und Zahl.
        urteil = text_pruefen(str(eingabe), gueltig, p_code, verwechslungen=vw,
                              fehler_benennen=fehler_benennen,
                              vorsilben=sprachen.personalpronomen(code, fm),
                              artikel_verlangt=sprachen.artikel_fuer(
                                  code, dbm.j_lesen(lexem["merkmale"]), fm))
        return urteil, {"erwartet": gueltig,
                        "beschriftung": sprachen.beschriften_form(
                            code, lexem["wortart"], fm)}

    if typ == "formenreihe":
        gruppe, zellen = _reihe_zellen(db, a, lexem, code)
        return _reihe_pruefen(db, lexem, code, zellen, eingabe,
                              fehler_benennen, p_code,
                              gruppe["name"] if gruppe else "")

    if typ == "stammformen":
        return _reihe_pruefen(db, lexem, code, _stammform_reihe(db, lexem, code),
                              eingabe, fehler_benennen, p_code, "Stammformen")

    if typ == "klasse":
        merkmal = a["schluessel"].rsplit(":", 1)[-1]
        soll = dbm.j_lesen(lexem["merkmale"]).get(merkmal)
        if soll is None:
            # Das Merkmal wurde nachträglich entfernt. Dann ist die
            # Aufgabe nicht beantwortbar, und das soll dastehen —
            # dieselbe Lage wie beim Geschlecht.
            return Urteil("falsch", None,
                          "Zu diesem Wort ist keine Klasse hinterlegt. Die "
                          "Aufgabe wird beim nächsten Durchrechnen "
                          "abgeschaltet.", ["unbeantwortbar"]), {"erwartet": []}
        gegeben = str(eingabe).strip()
        urteil = (Urteil("richtig", soll) if gegeben == soll
                  else Urteil("falsch", soll, f"Richtig ist {soll}.",
                              ["klasse"]))
        return urteil, {"erwartet": [soll], "klasse": soll}

    if typ == "form_bestimmen":
        f = dbm.zeile(db, "SELECT * FROM form WHERE id = ?", (a["ziel_id"],))
        return _merkmale_pruefen(db, lexem, f, eingabe, code)

    if typ == "genus":
        artikel = sprachen.profil(code)["artikel"]["genus_artikel"]
        soll_genus = dbm.j_lesen(lexem["merkmale"]).get("genus")
        if soll_genus == "mf":
            # Gemeinsames Geschlecht: ο/η γιατρός. Beide Artikel gelten,
            # je nachdem, wen man meint.
            moeglich = [artikel[g] for g in ("m", "f") if g in artikel]
            gegeben = str(eingabe).strip()
            richtig = (gegeben in ("m", "f", "mf")
                       or any(gegeben.casefold() == a.casefold()
                              for a in moeglich))
            text = " oder ".join(moeglich)
            urteil = (Urteil("richtig", text) if richtig
                      else Urteil("falsch", text,
                                  f"Dieses Wort hat gemeinsames Geschlecht — "
                                  f"richtig ist {text}.", ["genus"]))
            return urteil, {"erwartet": moeglich, "genus": "mf"}
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


def _reihe_pruefen(db: sqlite3.Connection, lexem: dict, code: str,
                   zellen: list[dict], eingabe, fehler_benennen: bool,
                   p_code: str, gruppenname: str) -> tuple[Urteil, dict]:
    """Eine ganze Reihe auf einmal bewerten.

    Gemeinsam für die Formgruppenreihe und die Stammformen: sie
    unterscheiden sich darin, WELCHE Zellen in der Reihe stehen, und in
    nichts sonst. Zwei Maßstäbe für dieselbe Eingabeart wären ein
    Versprechen, das irgendwann bricht.
    """
    eingaben = eingabe if isinstance(eingabe, dict) else {}
    ergebnisse = []
    for z in zellen:
        text = str(eingaben.get(z["zelle"], "") or "")
        # Die Geschwisterformen DERSELBEN Reihe sind hier keine
        # Verwechslung, sondern die Nachbarfelder — sie als solche zu
        # melden wäre irreführend.
        einzel = text_pruefen(text, z["erwartet"], p_code,
                              fehler_benennen=fehler_benennen,
                              vorsilben=z.get("pronomen"),
                              artikel_verlangt=sprachen.artikel_fuer(
                                  code, dbm.j_lesen(lexem["merkmale"]),
                                  z["merkmale"]))
        ergebnisse.append({
            "zelle": z["zelle"], "beschriftung": z["beschriftung"],
            "urteil": einzel.urteil, "erwartet": z["erwartet"],
            "eingabe": text, "hinweis": einzel.hinweis,
            "fehlertext": einzel.fehlertext,
        })
    richtig = sum(1 for r in ergebnisse if r["urteil"] == "richtig")
    fast = sum(1 for r in ergebnisse if r["urteil"] == "fast")
    gesamt = len(ergebnisse)
    # Eine Reihe sitzt als GANZES oder nicht. Wer fünf von sechs Formen
    # kann, kann die Tabelle noch nicht — aber es ist auch kein glatter
    # Fehlschlag, darum "fast", wenn nur Kleinigkeiten fehlen.
    if gesamt and richtig == gesamt:
        urteil = Urteil("richtig")
    elif gesamt and richtig + fast == gesamt:
        urteil = Urteil("fast", hinweis="Bis auf Kleinigkeiten richtig.")
    else:
        teile = [f"{richtig} von {gesamt} Formen sitzen"]
        if fast:
            teile.append(f"{fast} fast")
        offen = gesamt - richtig - fast
        if offen:
            teile.append(f"{offen} noch nicht")
        urteil = Urteil("falsch", hinweis=", ".join(teile) + ".")
    return urteil, {"zellen": ergebnisse, "gruppe": gruppenname,
                    "richtig": richtig, "gesamt": gesamt,
                    "erwartet": [t for z in zellen for t in z["erwartet"]]}


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
    if falsch and treffer_zahl > 0:
        fehlend = ", ".join(mk.name_der_dimension(d) for d in falsch)
        return Urteil("falsch", " / ".join(beschriftungen),
                      f"Nicht ganz — {fehlend} stimmt nicht. "
                      f"Richtig: {' oder '.join(beschriftungen)}.",
                      ["merkmale"]), auflösung
    return Urteil("falsch", " / ".join(beschriftungen),
                  f"Richtig: {' oder '.join(beschriftungen)}.",
                  ["merkmale"]), auflösung
