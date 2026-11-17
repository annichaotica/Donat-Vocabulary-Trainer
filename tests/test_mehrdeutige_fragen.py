"""Eine Frage muss sagen, welches Wort sie meint.

»eine, eines, mia, ena, enas, ta, to, die ganzen Artikel. Ich weiß sie,
aber anhand der Fragen weiß ich nie, welcher gemeint ist.«

Gemessen an ihrem Bestand, bevor hier etwas gebaut wurde: die Frage
lautete »ein« — richtig war ένας, μία oder ένα, je nach Geschlecht. Die
Frage »die« führte auf sieben verschiedene Wörter. Was dort stand, war
entweder nichts, oder ein Kürzel (»n«, »m«), oder dieser Satz:

    ihr: ihr (2. Person Plural, Subjekt); Sie: Sie (höflich) / ihr

Das ist keine Wissenslücke. Das ist eine unbeantwortbare Frage, und
FSRS hat daraus gelernt, dass sie die Wörter nicht kann.

ZWEI SEITEN, und sie müssen zusammenpassen:
  was die Frage SAGT      — `unterscheidung`
  was als Antwort GILT    — `nicht_unterschieden`
Was die Frage nicht sagt, darf die Wertung nicht verlangen.
"""

import pytest


def _sammlung(klient, eintraege):
    b = klient.post("/api/benutzer", json={"name": "Lernender 1"}).json()
    s = klient.post("/api/sammlungen", json={
        "besitzer_id": b["id"], "name": "Griechisch", "sprache": "el"}).json()
    klient.post(f"/api/sammlungen/{s['id']}/import/vokabeln",
                json={"eintraege": eintraege})
    return b, s


def _fragen(klient, b, s):
    """Alle Fragen »deutsch → fremd« dieser Sammlung, nach Lemma."""
    import datenbank as dbm
    import aufgaben
    db = dbm.verbindung()
    try:
        heraus = {}
        for z in dbm.zeilen(db, """
                SELECT a.id, l.lemma FROM aufgabe a
                  JOIN lexem l ON l.id = a.lexem_id
                 WHERE l.sammlung_id = ? AND a.typ = 'bedeutung_deutsch_fremd'
                   AND a.aktiv = 1""", (s["id"],)):
            f = aufgaben.frage(db, z["id"])
            _, auskunft = aufgaben.antwort_pruefen(db, z["id"], z["lemma"])
            heraus[z["lemma"]] = {"text": f["frage_text"],
                                  "zusatz": f["frage_zusatz"],
                                  "gilt": auskunft["erwartet"]}
        return heraus
    finally:
        db.close()


ARTIKEL = [
    {"lemma": "ένας", "wortart": "artikel",
     "merkmale": {"kasus": "nom", "numerus": "sg", "genus": "m"},
     "bedeutungen": [{"uebersetzungen": ["ein"]}]},
    {"lemma": "ένα", "wortart": "artikel",
     "merkmale": {"kasus": "nom", "numerus": "sg", "genus": "n"},
     "bedeutungen": [{"uebersetzungen": ["ein"]}]},
]


def test_die_frage_sagt_welcher_artikel_gemeint_ist(klient):
    """Der Kern. »ein« allein ist keine Frage."""
    b, s = _sammlung(klient, ARTIKEL)
    f = _fragen(klient, b, s)

    assert f["ένας"]["zusatz"] == "Nominativ Singular maskulin", f["ένας"]
    assert f["ένα"]["zusatz"] == "Nominativ Singular neutrum", f["ένα"]
    # Und weil die Frage es sagt, gilt auch nur das eine Wort.
    assert f["ένας"]["gilt"] == ["ένας"]
    assert f["ένα"]["gilt"] == ["ένα"]


def test_ohne_unterscheidende_merkmale_gelten_beide(klient):
    """μία und μια sind beide Nominativ Singular feminin.

    Dort hülfe eine Beschriftung nichts — sie täuschte Genauigkeit
    vor. Die Frage bleibt mehrdeutig, also gelten beide Antworten.
    Anders wäre es schlicht unwahr und verdürbe den Lernstand.
    """
    gleich = {"kasus": "nom", "numerus": "sg", "genus": "f"}
    b, s = _sammlung(klient, [
        {"lemma": "μία", "wortart": "artikel", "merkmale": gleich,
         "bedeutungen": [{"uebersetzungen": ["eine"]}]},
        {"lemma": "μια", "wortart": "artikel", "merkmale": gleich,
         "bedeutungen": [{"uebersetzungen": ["eine"]}]},
    ])
    f = _fragen(klient, b, s)
    assert set(f["μία"]["gilt"]) == {"μία", "μια"}, f["μία"]


def test_ohne_etwas_zu_verwechseln_steht_keine_bestimmung_da(klient):
    """Bei »das Haus« wäre »neutrum« Lärm — das sagt der deutsche
    Artikel schon. Erst die Verwechslungsgefahr rechtfertigt die
    Beschriftung."""
    b, s = _sammlung(klient, [
        {"lemma": "το σπίτι", "wortart": "substantiv",
         "merkmale": {"genus": "n"},
         "bedeutungen": [{"uebersetzungen": ["das Haus"]}]},
    ])
    f = _fragen(klient, b, s)
    assert f["το σπίτι"]["zusatz"] is None, f["το σπίτι"]


def test_ein_wort_ohne_merkmale_macht_die_anderen_nicht_wieder_blind(klient):
    """Der Fehler des ersten Entwurfs.

    Dort wurde in EINEM Zug gefragt: unterscheiden die Merkmale von
    allen? Im echten Bestand stehen bei »die« sieben Wörter, und eines
    (τους) hatte noch keine Merkmale. Damit galt die Frage wieder als
    mehrdeutig — obwohl »Nominativ Plural neutrum« η und την sehr wohl
    ausschließt.

    Jetzt je Wort einzeln: wen die Bestimmung trifft, der fällt weg;
    wen sie nicht erreicht, der bleibt gültig. So verbessert sich der
    Bestand Stück für Stück, ohne dass er fertig sein muss.
    """
    b, s = _sammlung(klient, [
        {"lemma": "τα", "wortart": "artikel",
         "merkmale": {"kasus": "nom", "numerus": "pl", "genus": "n"},
         "bedeutungen": [{"uebersetzungen": ["die"]}]},
        {"lemma": "η", "wortart": "artikel",
         "merkmale": {"kasus": "nom", "numerus": "sg", "genus": "f"},
         "bedeutungen": [{"uebersetzungen": ["die"]}]},
        # Noch ungepflegt — wie τους im echten Bestand.
        {"lemma": "που", "wortart": "pronomen",
         "bedeutungen": [{"uebersetzungen": ["die"]}]},
    ])
    f = _fragen(klient, b, s)
    assert f["τα"]["zusatz"] == "Nominativ Plural neutrum"
    assert "η" not in f["τα"]["gilt"], "das Unterschiedene fällt weg"
    assert "που" in f["τα"]["gilt"], "das Unbestimmte bleibt gültig"


def test_merkmale_schlagen_den_freitext(klient):
    """Der Kontext ist Freitext und war im Bestand teils unlesbar.

    Beides nebeneinanderzustellen ergäbe »2. Person Plural · ihr: ihr
    (2. Person Plural, Subjekt); Sie: …«. Sagen die Merkmale es schon,
    ist der Freitext Lärm.
    """
    b, s = _sammlung(klient, [
        {"lemma": "εσείς", "wortart": "pronomen",
         "merkmale": {"person": "2", "numerus": "pl"},
         "bedeutungen": [{"uebersetzungen": ["ihr"],
                          "kontext": "ihr: ihr (2. Person Plural, Subjekt); "
                                     "Sie: Sie (höflich) / ihr"}]},
        {"lemma": "της", "wortart": "pronomen",
         "merkmale": {"person": "3", "numerus": "sg", "genus": "f"},
         "bedeutungen": [{"uebersetzungen": ["ihr"], "kontext": "f Sg."}]},
    ])
    f = _fragen(klient, b, s)
    assert f["εσείς"]["zusatz"] == "2. Person Plural", f["εσείς"]


def test_der_freitext_bleibt_wo_merkmale_nichts_sagen(klient):
    """»klein, Körpergröße« ist keine Formangabe, sondern eine
    Bedeutungsnuance. Dort ist der Kontext die einzige Quelle."""
    b, s = _sammlung(klient, [
        {"lemma": "μικρός", "wortart": "adjektiv",
         "bedeutungen": [{"uebersetzungen": ["klein"],
                          "kontext": "Körpergröße"}]},
        {"lemma": "κοντός", "wortart": "adjektiv",
         "bedeutungen": [{"uebersetzungen": ["klein"], "kontext": "Länge"}]},
    ])
    f = _fragen(klient, b, s)
    assert f["μικρός"]["zusatz"] == "Körpergröße"
    assert f["μικρός"]["gilt"] == ["μικρός"], "der Kontext bestimmt wie bisher"


def test_die_bestimmung_folgt_dem_eingestellten_stil(klient):
    """Wie überall: wer »einfach« eingestellt hat, bekommt
    »wer oder was?, Einzahl, männlich« statt des Fachworts."""
    import datenbank as dbm
    import aufgaben
    b, s = _sammlung(klient, ARTIKEL)
    db = dbm.verbindung()
    try:
        z = dbm.zeile(db, """SELECT a.id FROM aufgabe a
                               JOIN lexem l ON l.id = a.lexem_id
                              WHERE l.lemma = 'ένας'
                                AND a.typ = 'bedeutung_deutsch_fremd'""")
        einfach = aufgaben.frage(db, z["id"], stil="einfach")["frage_zusatz"]
    finally:
        db.close()
    assert "männlich" in einfach, einfach
    assert "maskulin" not in einfach, einfach
