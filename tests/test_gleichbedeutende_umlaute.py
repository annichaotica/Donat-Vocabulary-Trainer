"""Das andere richtige Wort — auch wenn es mit Umlaut anfängt.

»klein« führt im Griechischen auf μικρός und κοντός. Wer bei der Frage
»klein« κοντός schreibt, hat nicht geirrt. Das war gebaut und
funktionierte — solange die Übersetzung aus ASCII bestand.

Verglichen wurde nämlich in SQL mit `LOWER(TRIM(u.text))`, und SQLites
eingebautes LOWER wirkt nur auf ASCII: lower('Öl') ist 'Öl'. Die
Python-Seite hatte vorher casefold angewandt und suchte nach 'öl'. Jede
Übersetzung mit Umlaut am Wortanfang fiel damit durch — und das zweite
richtige Wort wurde als Nichtwissen protokolliert, mit Bewertung 1.
"""

import pytest


@pytest.fixture()
def bestand(klient):
    b = klient.post("/api/benutzer", json={"name": "Übende"}).json()
    s = klient.post("/api/sammlungen", json={
        "besitzer_id": b["id"], "name": "Griechisch", "sprache": "el"}).json()
    klient.post(f"/api/sammlungen/{s['id']}/import/vokabeln", json={
        "eintraege": [
            # Zwei Wörter, eine Bedeutung — der ASCII-Fall, der ging.
            {"lemma": "μικρός", "wortart": "adjektiv", "lektion_nr": 1,
             "bedeutungen": [{"uebersetzungen": ["klein"]}]},
            {"lemma": "κοντός", "wortart": "adjektiv", "lektion_nr": 1,
             "bedeutungen": [{"uebersetzungen": ["klein"]}]},
            # Und derselbe Fall mit Umlaut am Anfang.
            {"lemma": "λάδι", "wortart": "substantiv", "lektion_nr": 1,
             "merkmale": {"genus": "n"},
             "bedeutungen": [{"uebersetzungen": ["Öl"]}]},
            {"lemma": "ελαιόλαδο", "wortart": "substantiv", "lektion_nr": 1,
             "merkmale": {"genus": "n"},
             "bedeutungen": [{"uebersetzungen": ["Öl"]}]},
        ]})
    klient.post(f"/api/sammlungen/{s['id']}/freigabe", json={"lektion_nr": 1})
    aufgaben = klient.get("/api/lernen/naechste", params={
        "benutzer_id": b["id"], "sammlung_id": s["id"], "anzahl": 30,
        "nur": "frei"}).json()
    antwort = klient.get(f"/api/sammlungen/{s['id']}/lexeme").json()
    liste = antwort["lexeme"] if isinstance(antwort, dict) else antwort
    lexeme = {z["lemma"]: z["id"] for z in liste}
    return b, aufgaben, lexeme


def _frage(aufgaben, lexeme, lemma):
    """Die Aufgabe, deren GESUCHTES Wort dieses ist.

    Nach dem Fragetext zu suchen reicht nicht: zwei Wörter mit derselben
    Übersetzung ergeben zwei Aufgaben mit demselben Fragetext. Der erste
    Treffer war dann womöglich genau der, dessen Lemma man antwortet —
    und der Test bestand auch mit dem Fehler.
    """
    for a in aufgaben:
        if (a["typ"] == "bedeutung_deutsch_fremd"
                and a["lexem_id"] == lexeme[lemma]):
            return a
    raise AssertionError(f"keine Aufgabe zu {lemma!r}")


def _urteil(klient, b, aufgabe, antwort):
    d = klient.post("/api/lernen/pruefen", json={
        "benutzer_id": b["id"], "aufgabe_id": aufgabe["aufgabe_id"],
        "antwort": antwort}).json()
    return d.get("urteil", d)


def test_das_andere_wort_gilt_auch_bei_ascii(bestand, klient):
    """Die Gegenprobe: dieser Fall ging schon immer."""
    b, aufgaben, lexeme = bestand
    urteil = _urteil(klient, b, _frage(aufgaben, lexeme, "μικρός"), "κοντός")
    assert urteil["urteil"] == "richtig", urteil


def test_das_andere_wort_gilt_auch_mit_umlaut(bestand, klient):
    """Gefragt ist λάδι, geantwortet wird ελαιόλαδο — beides heißt Öl."""
    b, aufgaben, lexeme = bestand
    urteil = _urteil(klient, b, _frage(aufgaben, lexeme, "λάδι"), "ελαιόλαδο")
    assert urteil["urteil"] == "richtig", urteil


def test_ein_wirklich_falsches_wort_bleibt_falsch(bestand, klient):
    b, aufgaben, lexeme = bestand
    urteil = _urteil(klient, b, _frage(aufgaben, lexeme, "λάδι"), "κοντός")
    assert urteil["urteil"] == "falsch", urteil
