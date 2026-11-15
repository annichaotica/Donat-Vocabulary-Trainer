"""Ein kleiner englischer Übungskurs — zum Ausprobieren, nicht zum Lernen.

»Dazu vielleicht auch tatsächlich für Englisch einen kleinen Übungskurs,
damit man alle Features zeigen und ausprobieren kann?«

Darum ist er so zugeschnitten, wie er ist: nicht nach Nützlichkeit für
das Englischlernen, sondern danach, dass jede Funktion des Trainers
darin etwas zu zeigen hat. Englisch, weil es jeder in der Familie genug
kann, um sich auf die Bedienung statt auf die Vokabel zu konzentrieren
— und weil niemand sich über eine falsche Wertung ärgert.

Was er mitbringt und warum
--------------------------
  Lektionen mit sprechenden Namen   damit die Lektionsschranke etwas
                                    vorzuschlagen hat
  Verben mit Simple past            damit es eine Zeitform gibt, die
                                    erst später »freigeschaltet« wird
  unregelmäßige Plurale             child/children ist eine Formaufgabe,
                                    die man wirklich wissen muss
  Adjektive mit Steigerung          eine dritte Formgruppe
  zwei Sätze                        für den Übungsweg
  ein Lesetext                      für Deckung und Wortwünsche
  eine Grammatikregel               für das »Warum ist das so?«

Er wird vollständig FREIGEGEBEN angelegt. Sonst stünde man nach dem
Anlegen vor einer leeren Abfrage und müsste erst die Freigabe suchen —
ein schlechter erster Eindruck, und für erfundene Beispieldaten ist die
Prüfung ohnehin sinnlos.
"""

from __future__ import annotations

import sqlite3

import aufgaben
import datenbank as dbm
import lehrgang
import lesetexte
import regeln
import sammelimport
import uebungen


NAME = "Englisch — kleiner Übungskurs"

LEKTIONEN = [
    (1, "Erste Wörter"),
    (2, "Verben im Präsens"),
    (3, "Plural"),
    (4, "Simple past"),
    (5, "Comparative und Superlative"),
]

# Die Formgruppen hängen an den Lektionsnamen — dieselbe Zuordnung, die
# die Lektionsschranke vorschlägt, hier gleich mitgeliefert. So lässt
# sich die Schranke sofort ausprobieren, ohne sie erst einzutragen.
LEHRGANG = {
    "present_3sg": 2,
    "pl": 3,
    "past": 4,
    "past_participle": 4,
    "komparativ": 5,
    "superlativ": 5,
}

WOERTER = [
    # --- Lektion 1: nackte Wörter, keine Formen
    {"lemma": "house", "wortart": "substantiv", "lektion_nr": 1,
     "bedeutungen": [{"uebersetzungen": ["das Haus", "Haus"]}],
     "formen": [{"text": "houses", "merkmale": {"numerus": "pl"}}]},
    {"lemma": "book", "wortart": "substantiv", "lektion_nr": 1,
     "bedeutungen": [{"uebersetzungen": ["das Buch"]}],
     "formen": [{"text": "books", "merkmale": {"numerus": "pl"}}]},
    {"lemma": "water", "wortart": "substantiv", "lektion_nr": 1,
     "bedeutungen": [{"uebersetzungen": ["das Wasser"]}]},
    {"lemma": "today", "wortart": "adverb", "lektion_nr": 1,
     "bedeutungen": [{"uebersetzungen": ["heute"]}]},

    # --- Lektion 2: Verben, mit 3. Person und Vergangenheit
    {"lemma": "to go", "wortart": "verb", "lektion_nr": 2,
     "merkmale": {"klasse": "unregelmäßig"},
     "bedeutungen": [{"uebersetzungen": ["gehen"]},
                     {"uebersetzungen": ["fahren"], "kontext": "mit Fahrzeug"}],
     "formen": [
         {"text": "goes", "merkmale": {"modus": "indikativ", "tempus": "praesens",
                                       "person": "3", "numerus": "sg"}},
         {"text": "went", "merkmale": {"modus": "indikativ", "tempus": "praeteritum"}},
         {"text": "gone", "merkmale": {"nonfinit": "partizip_perfekt"}},
     ]},
    {"lemma": "to read", "wortart": "verb", "lektion_nr": 2,
     "merkmale": {"klasse": "unregelmäßig"},
     "bedeutungen": [{"uebersetzungen": ["lesen"]}],
     "formen": [
         {"text": "reads", "merkmale": {"modus": "indikativ", "tempus": "praesens",
                                        "person": "3", "numerus": "sg"}},
         # Dieselbe Schreibweise, andere Aussprache — ein schöner Fall
         # für »das musst du wirklich wissen«.
         {"text": "read", "merkmale": {"modus": "indikativ", "tempus": "praeteritum"}},
         {"text": "read", "merkmale": {"nonfinit": "partizip_perfekt"}},
     ]},
    {"lemma": "to work", "wortart": "verb", "lektion_nr": 2,
     "merkmale": {"klasse": "regelmäßig"},
     "bedeutungen": [{"uebersetzungen": ["arbeiten"]},
                     {"uebersetzungen": ["funktionieren"],
                      "kontext": "Gerät"}],
     "formen": [
         {"text": "works", "merkmale": {"modus": "indikativ", "tempus": "praesens",
                                        "person": "3", "numerus": "sg"}},
         {"text": "worked", "merkmale": {"modus": "indikativ", "tempus": "praeteritum"}},
         {"text": "worked", "merkmale": {"nonfinit": "partizip_perfekt"}},
     ]},

    {"lemma": "to be", "wortart": "verb", "lektion_nr": 2,
     "merkmale": {"klasse": "unregelmäßig"},
     "bedeutungen": [{"uebersetzungen": ["sein"]}],
     "formen": [
         {"text": "is", "merkmale": {"modus": "indikativ",
                                     "tempus": "praesens",
                                     "person": "3", "numerus": "sg"}},
         {"text": "was", "merkmale": {"modus": "indikativ",
                                      "tempus": "praeteritum"}},
     ]},
    {"lemma": "to have", "wortart": "verb", "lektion_nr": 2,
     "merkmale": {"klasse": "unregelmäßig"},
     "bedeutungen": [{"uebersetzungen": ["haben"]}],
     "formen": [
         {"text": "has", "merkmale": {"modus": "indikativ",
                                      "tempus": "praesens",
                                      "person": "3", "numerus": "sg"}},
         {"text": "had", "merkmale": {"modus": "indikativ",
                                      "tempus": "praeteritum"}},
     ]},
    {"lemma": "a", "wortart": "artikel", "lektion_nr": 1,
     "bedeutungen": [{"uebersetzungen": ["ein", "eine"]}]},
    {"lemma": "the", "wortart": "artikel", "lektion_nr": 1,
     "bedeutungen": [{"uebersetzungen": ["der", "die", "das"]}]},
    {"lemma": "in", "wortart": "praeposition", "lektion_nr": 1,
     "bedeutungen": [{"uebersetzungen": ["in"]}]},
    {"lemma": "many", "wortart": "adjektiv", "lektion_nr": 3,
     "bedeutungen": [{"uebersetzungen": ["viele"]}]},

    # --- Lektion 3: unregelmäßige Plurale
    {"lemma": "child", "wortart": "substantiv", "lektion_nr": 3,
     "bedeutungen": [{"uebersetzungen": ["das Kind"]}],
     "formen": [{"text": "children", "merkmale": {"numerus": "pl"}}]},
    {"lemma": "man", "wortart": "substantiv", "lektion_nr": 3,
     "bedeutungen": [{"uebersetzungen": ["der Mann"]}],
     "formen": [{"text": "men", "merkmale": {"numerus": "pl"}}]},

    # --- Lektion 5: Steigerung
    {"lemma": "big", "wortart": "adjektiv", "lektion_nr": 5,
     "bedeutungen": [{"uebersetzungen": ["groß"]}],
     "formen": [{"text": "bigger", "merkmale": {"stufe": "komparativ"}},
                {"text": "biggest", "merkmale": {"stufe": "superlativ"}}]},
    {"lemma": "good", "wortart": "adjektiv", "lektion_nr": 5,
     "bedeutungen": [{"uebersetzungen": ["gut"]}],
     "formen": [{"text": "better", "merkmale": {"stufe": "komparativ"}},
                {"text": "best", "merkmale": {"stufe": "superlativ"}}]},
]

# Drei Einträge, die NICHT freigegeben werden — mit Absicht.
#
# Am Übungskurs ließ sich die Freigabe nicht üben: er war durchgehend
# freigegeben, und die Prüfansicht sagte »Alles freigegeben — es wartet
# nichts«. Ein Beispielkurs, an dem der wichtigste Handgriff nicht
# vorkommt, ist als Beispiel unvollständig.
#
# Einer davon ist absichtlich FALSCH: »goed« statt »went«. So etwas
# erfindet eine KI wirklich — sie wendet die regelmäßige Endung auf ein
# unregelmäßiges Verb an. Wer es durchwinkt, paukt es; wer hinsieht,
# hat verstanden, wozu die Freigabe da ist. Der Fehler steht hier und
# nicht in der Anleitung, weil man ihn einmal selbst finden muss.
UNGEPRUEFT = [
    {"lemma": "to drink", "wortart": "verb", "lektion_nr": 2,
     "bedeutungen": [{"uebersetzungen": ["trinken"]}],
     "formen": [
         {"text": "drinks", "merkmale": {"modus": "indikativ",
                                         "tempus": "praesens",
                                         "person": "3", "numerus": "sg"}},
         {"text": "drank", "merkmale": {"modus": "indikativ",
                                        "tempus": "praeteritum"}},
     ]},
    {"lemma": "to see", "wortart": "verb", "lektion_nr": 2,
     "bedeutungen": [{"uebersetzungen": ["sehen"]}],
     "formen": [
         {"text": "sees", "merkmale": {"modus": "indikativ",
                                       "tempus": "praesens",
                                       "person": "3", "numerus": "sg"}},
         {"text": "saw", "merkmale": {"modus": "indikativ",
                                      "tempus": "praeteritum"}},
     ]},
    {"lemma": "to walk", "wortart": "verb", "lektion_nr": 4,
     "bedeutungen": [{"uebersetzungen": ["gehen", "zu Fuß gehen"]}],
     "formen": [
         {"text": "walks", "merkmale": {"modus": "indikativ",
                                        "tempus": "praesens",
                                        "person": "3", "numerus": "sg"}},
         # Falsch: regelmäßige Endung an ein Verb, das sie nicht hat.
         # Richtig wäre »walked« — hier steht die Form, die eine KI
         # gern erfindet, wenn sie das Muster überträgt.
         {"text": "goed", "merkmale": {"modus": "indikativ",
                                       "tempus": "praeteritum"}},
     ]},
]

SAETZE = [
    {"typ": "satz", "lektion_nr": 2,
     "zielsprache": "The child reads a book.",
     "grundsprache": "Das Kind liest ein Buch."},
    {"typ": "satz", "lektion_nr": 4,
     "zielsprache": "Yesterday the men went home.",
     "grundsprache": "Gestern gingen die Männer nach Hause."},
]

TEXT_TITEL = "A day at home"
TEXT = """The man works today. The child reads a book in the house.

The water is good. The big house has many books."""

REGEL = {
    "titel": "Das -s in der 3. Person Singular",
    "text": "Im Präsens bekommt nur die 3. Person Singular ein -s: "
            "I work, you work, aber he works. Nach -ch, -sh, -s, -x und "
            "-o wird daraus -es: he goes, she watches.",
    "beispiele": [{"form": "he works", "bedeutung": "er arbeitet"},
                  {"form": "she goes", "bedeutung": "sie geht"}],
    "muster": {"wortart": "verb", "formgruppe": "present_3sg"},
}


def vorhanden(db: sqlite3.Connection, benutzer_id: int) -> int | None:
    """Gibt es den Kurs für diese Person schon? Dann seine Kennung."""
    return dbm.wert(db, """SELECT id FROM sammlung
                            WHERE besitzer_id = ? AND name = ?""",
                    (benutzer_id, NAME))


def anlegen(db: sqlite3.Connection, benutzer_id: int) -> dict:
    """Legt den Kurs an — einmal je Person.

    Beim zweiten Aufruf passiert nichts; zurückgegeben wird die
    bestehende Sammlung. Sonst entstünden beim zweimaligen Tippen zwei
    Kurse, und der Lernstand verteilte sich auf beide.
    """
    if dbm.zeile(db, "SELECT 1 FROM benutzer WHERE id = ?",
                 (benutzer_id,)) is None:
        raise KeyError(f"Profil {benutzer_id} gibt es nicht")
    schon = vorhanden(db, benutzer_id)
    if schon:
        return {"sammlung_id": schon, "neu": False,
                "hinweis": "Der Übungskurs war schon da."}

    cur = db.execute("""INSERT INTO sammlung (besitzer_id, name, sprache,
                                              grundsprache, beschreibung)
                        VALUES (?, ?, 'en', 'de', ?)""",
                     (benutzer_id, NAME,
                      "Zum Ausprobieren: ein paar Wörter, Sätze, ein Text "
                      "und eine Grammatikregel. Löschen, wann du magst."))
    sammlung_id = cur.lastrowid

    for nr, name in LEKTIONEN:
        db.execute("""INSERT INTO lektion (sammlung_id, nr, name)
                      VALUES (?, ?, ?)""", (sammlung_id, nr, name))

    sammelimport.importieren(db, sammlung_id, WOERTER, quelle="manuell")
    uebungen.importieren(db, sammlung_id, SAETZE)
    lesetexte.anlegen(db, sammlung_id, TEXT_TITEL, TEXT,
                      niveau="A1",
                      notiz="Beispieltext — jedes Wort darin steht im Kurs.")
    regeln.anlegen(db, sammlung_id, REGEL["titel"], REGEL["text"], "en",
                   REGEL["muster"], REGEL["beispiele"],
                   kennung="beispiel-3sg", quelle="manuell")
    lehrgang.zuordnung_setzen(db, sammlung_id, LEHRGANG)

    # Alles freigeben: Wörter, Formen, Sätze und die Regel. Ein
    # Beispielkurs, der erst durch die Prüfung muss, ist kein Beispiel,
    # sondern eine Hürde.
    db.execute("""UPDATE form SET geprueft = 1
                   WHERE lexem_id IN (SELECT id FROM lexem
                                       WHERE sammlung_id = ?)""",
               (sammlung_id,))
    db.execute("""UPDATE text SET geprueft = 1 WHERE sammlung_id = ?""",
               (sammlung_id,))
    db.execute("""UPDATE regel SET geprueft = 1 WHERE sammlung_id = ?""",
               (sammlung_id,))
    aufgaben.erzeugen_fuer_sammlung(db, sammlung_id)

    # Erst JETZT die ungeprüften — sonst hätte sie die Freigabe oben
    # mit erwischt, und die Prüfansicht wäre wieder leer.
    sammelimport.importieren(db, sammlung_id, UNGEPRUEFT, quelle="ki")
    aufgaben.erzeugen_fuer_sammlung(db, sammlung_id)

    return {
        "sammlung_id": sammlung_id,
        "neu": True,
        "name": NAME,
        "woerter": len(WOERTER) + len(UNGEPRUEFT),
        "ungeprueft": len(UNGEPRUEFT),
        "saetze": len(SAETZE),
        "lektionen": len(LEKTIONEN),
        "aufgaben": dbm.wert(db, """SELECT COUNT(*) FROM aufgabe a
                                      JOIN lexem l ON l.id = a.lexem_id
                                     WHERE l.sammlung_id = ? AND a.aktiv = 1""",
                             (sammlung_id,)) or 0,
    }
