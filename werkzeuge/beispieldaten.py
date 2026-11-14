#!/usr/bin/env python3
"""Legt Beispieldaten an, damit sich der Trainer ansehen lässt.

    .venv/bin/python werkzeuge/beispieldaten.py [Profilname]

Löscht nichts. Besteht das Profil schon, wird es benutzt.
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "backend"))

import aufgaben                                             # noqa: E402
import datenbank as dbm                                     # noqa: E402

PERSONEN = [("1", "sg"), ("2", "sg"), ("3", "sg"),
            ("1", "pl"), ("2", "pl"), ("3", "pl")]


def reihe(worte, merkmale):
    """Sechs Personenformen zu einem Merkmalsbündel."""
    return [{"text": w, "merkmale": {**merkmale, "person": p, "numerus": n}}
            for w, (p, n) in zip(worte, PERSONEN) if w]


FRANZOESISCH = [
    {"lemma": "aller", "wortart": "verb",
     "merkmale": {"hilfsverb": "être", "klasse": "unregelmäßig"},
     "bedeutungen": [
         {"uebersetzungen": ["gehen", "laufen", "zu Fuß gehen"]},
         {"uebersetzungen": ["fahren"], "kontext": "mit Fahrzeug"}],
     "formen": [{"text": "aller", "merkmale": {"nonfinit": "infinitiv"},
                 "ist_grundform": True}]
     + reihe(["vais", "vas", "va", "allons", "allez", "vont"],
             {"modus": "indikativ", "tempus": "praesens"})
     + reihe(["allais", "allais", "allait", "allions", "alliez", "allaient"],
             {"modus": "indikativ", "tempus": "imperfekt"})
     + [{"text": "allé", "merkmale": {"nonfinit": "partizip_perfekt"}}]},

    {"lemma": "travailler", "wortart": "verb", "merkmale": {"klasse": "er"},
     "bedeutungen": [{"uebersetzungen": ["arbeiten"]}],
     "formen": [{"text": "travailler", "merkmale": {"nonfinit": "infinitiv"},
                 "ist_grundform": True}]
     + reihe(["travaille", "travailles", "travaille",
              "travaillons", "travaillez", "travaillent"],
             {"modus": "indikativ", "tempus": "praesens"})
     + reihe(["travaillais", "travaillais", "travaillait",
              "travaillions", "travailliez", "travaillaient"],
             {"modus": "indikativ", "tempus": "imperfekt"})
     + [{"text": "travaillé", "merkmale": {"nonfinit": "partizip_perfekt"}}]},

    {"lemma": "la table", "wortart": "substantiv", "merkmale": {"genus": "f"},
     "bedeutungen": [{"uebersetzungen": ["der Tisch", "die Tafel"]}],
     "formen": [{"text": "table", "merkmale": {"numerus": "sg"},
                 "ist_grundform": True},
                {"text": "tables", "merkmale": {"numerus": "pl"}}]},

    {"lemma": "l'élève", "wortart": "substantiv", "merkmale": {"genus": "m"},
     "bedeutungen": [{"uebersetzungen": ["der Schüler", "die Schülerin"]}],
     "formen": [{"text": "élève", "merkmale": {"numerus": "sg"},
                 "ist_grundform": True},
                {"text": "élèves", "merkmale": {"numerus": "pl"}}]},
]

GRIECHISCH = [
    {"lemma": "γράφω", "wortart": "verb", "merkmale": {"klasse": "Α-Konjugation"},
     "bedeutungen": [{"uebersetzungen": ["schreiben", "aufschreiben"]}],
     "formen": reihe(["γράφω", "γράφεις", "γράφει",
                      "γράφουμε", "γράφετε", "γράφουν"],
                     {"modus": "indikativ", "tempus": "praesens"})
     + reihe(["έγραψα", "έγραψες", "έγραψε",
              "γράψαμε", "γράψατε", "έγραψαν"],
             {"modus": "indikativ", "tempus": "aorist"})
     + reihe(["θα γράψω", "θα γράψεις", "θα γράψει",
              "θα γράψουμε", "θα γράψετε", "θα γράψουν"],
             {"modus": "indikativ", "tempus": "futur", "aspekt": "perfektiv"})},

    {"lemma": "το σπίτι", "wortart": "substantiv", "merkmale": {"genus": "n"},
     "bedeutungen": [{"uebersetzungen": ["das Haus", "die Wohnung"]}],
     "formen": [
         {"text": "σπίτι", "merkmale": {"kasus": "nom", "numerus": "sg"},
          "ist_grundform": True},
         {"text": "σπιτιού", "merkmale": {"kasus": "gen", "numerus": "sg"}},
         {"text": "σπίτι", "merkmale": {"kasus": "akk", "numerus": "sg"}},
         {"text": "σπίτια", "merkmale": {"kasus": "nom", "numerus": "pl"}},
         {"text": "σπιτιών", "merkmale": {"kasus": "gen", "numerus": "pl"}}]},
]

MITTELHOCHDEUTSCH = [
    # Die vier Stammformen sind das Pensum: nëmen – nam – nâmen – genomen
    {"lemma": "nëmen", "wortart": "verb", "merkmale": {"klasse": "stark IV"},
     "bedeutungen": [{"uebersetzungen": ["nehmen"]}],
     "formen": [
         {"text": "nëmen", "merkmale": {"nonfinit": "infinitiv"},
          "ist_grundform": True},
         {"text": "nam", "merkmale": {"modus": "indikativ", "tempus": "praeteritum",
                                      "person": "1", "numerus": "sg"}},
         {"text": "nâmen", "merkmale": {"modus": "indikativ", "tempus": "praeteritum",
                                        "person": "1", "numerus": "pl"}},
         {"text": "genomen", "merkmale": {"nonfinit": "partizip_perfekt"}}]},

    {"lemma": "rîten", "wortart": "verb", "merkmale": {"klasse": "stark I"},
     "bedeutungen": [{"uebersetzungen": ["reiten"]}],
     "formen": [
         {"text": "rîten", "merkmale": {"nonfinit": "infinitiv"},
          "ist_grundform": True},
         {"text": "reit", "merkmale": {"modus": "indikativ", "tempus": "praeteritum",
                                       "person": "1", "numerus": "sg"}},
         {"text": "riten", "merkmale": {"modus": "indikativ", "tempus": "praeteritum",
                                        "person": "1", "numerus": "pl"}},
         {"text": "geriten", "merkmale": {"nonfinit": "partizip_perfekt"}}]},

    {"lemma": "diu vrouwe", "wortart": "substantiv", "merkmale": {"genus": "f"},
     "bedeutungen": [{"uebersetzungen": ["die Dame", "die Herrin", "die Frau"]}],
     "formen": [
         {"text": "vrouwe", "merkmale": {"kasus": "nom", "numerus": "sg"},
          "ist_grundform": True},
         {"text": "vrouwen", "merkmale": {"kasus": "gen", "numerus": "sg"}},
         {"text": "vrouwen", "merkmale": {"kasus": "nom", "numerus": "pl"}}]},

    {"lemma": "diu âventiure", "wortart": "substantiv", "merkmale": {"genus": "f"},
     "bedeutungen": [{"uebersetzungen": ["die Erzählung", "das Wagnis",
                                         "das Abenteuer"]}],
     "formen": [
         {"text": "âventiure", "merkmale": {"kasus": "nom", "numerus": "sg"},
          "ist_grundform": True},
         {"text": "âventiuren", "merkmale": {"kasus": "nom", "numerus": "pl"}}]},
]

ENGLISCH = [
    {"lemma": "to go", "wortart": "verb", "merkmale": {"klasse": "unregelmäßig"},
     "bedeutungen": [{"uebersetzungen": ["gehen", "fahren"]}],
     "formen": [
         {"text": "go", "merkmale": {"nonfinit": "infinitiv"}, "ist_grundform": True},
         {"text": "goes", "merkmale": {"modus": "indikativ", "tempus": "praesens",
                                       "person": "3", "numerus": "sg"}},
         {"text": "went", "merkmale": {"modus": "indikativ",
                                       "tempus": "praeteritum"}},
         {"text": "gone", "merkmale": {"nonfinit": "partizip_perfekt"}},
         {"text": "going", "merkmale": {"nonfinit": "partizip_praesens"}}]},
]


def lexem_anlegen(db, sammlung_id, grundsprache, eintrag):
    merkmale = dbm.j_schreiben(eintrag.get("merkmale", {}))
    cur = db.execute("""INSERT INTO lexem (sammlung_id, lemma, wortart, merkmale)
                        VALUES (?, ?, ?, ?)""",
                     (sammlung_id, eintrag["lemma"], eintrag["wortart"], merkmale))
    lexem_id = cur.lastrowid
    for f in eintrag.get("formen", []):
        db.execute("""INSERT INTO form (lexem_id, text, merkmale, ist_grundform)
                      VALUES (?, ?, ?, ?)""",
                   (lexem_id, f["text"], dbm.j_schreiben(f["merkmale"]),
                    int(f.get("ist_grundform", False))))
    for i, b in enumerate(eintrag.get("bedeutungen", [])):
        cur = db.execute("""INSERT INTO bedeutung (lexem_id, reihenfolge, kontext)
                            VALUES (?, ?, ?)""",
                         (lexem_id, i, b.get("kontext")))
        for k, text in enumerate(b["uebersetzungen"]):
            db.execute("""INSERT INTO uebersetzung
                            (bedeutung_id, sprache, text, ist_haupt)
                          VALUES (?, ?, ?, ?)""",
                       (cur.lastrowid, grundsprache, text, int(k == 0)))
    return aufgaben.erzeugen(db, lexem_id)


def main():
    db = dbm.verbindung()
    dbm.einrichten(db)

    name = sys.argv[1] if len(sys.argv) > 1 else "Ich"
    person = dbm.zeile(db, "SELECT * FROM benutzer WHERE name = ?", (name,))
    if person is None:
        cur = db.execute("INSERT INTO benutzer (name, farbe) VALUES (?, ?)",
                         (name, "#6b7fd7"))
        benutzer_id = cur.lastrowid
        print(f"Profil »{name}« angelegt")
    else:
        benutzer_id = person["id"]
        print(f"Profil »{name}« vorhanden")

    bestand = [
        ("Französisch, Grundwortschatz", "fr", FRANZOESISCH),
        ("Griechisch, Grundwortschatz", "el", GRIECHISCH),
        ("Mittelhochdeutsch, Stammformen", "gmh", MITTELHOCHDEUTSCH),
        ("Englisch, unregelmäßige Verben", "en", ENGLISCH),
    ]
    gesamt = 0
    for name, sprache, eintraege in bestand:
        vorhanden = dbm.zeile(db, """SELECT * FROM sammlung
                                      WHERE besitzer_id = ? AND name = ?""",
                              (benutzer_id, name))
        if vorhanden:
            print(f"  {name}: schon da, übersprungen")
            continue
        cur = db.execute("""INSERT INTO sammlung
                              (besitzer_id, name, sprache, grundsprache)
                            VALUES (?, ?, ?, 'de')""",
                         (benutzer_id, name, sprache))
        sammlung_id = cur.lastrowid
        anzahl = 0
        for eintrag in eintraege:
            bilanz = lexem_anlegen(db, sammlung_id, "de", eintrag)
            anzahl += bilanz["angelegt"]
        gesamt += anzahl
        print(f"  {name}: {len(eintraege)} Wörter, {anzahl} Aufgaben")

    print(f"\nFertig. {gesamt} Aufgaben insgesamt.")
    print(f"Datenbank: {dbm.PFAD}")
    db.close()


if __name__ == "__main__":
    main()
