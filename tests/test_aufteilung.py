"""Wie ein Text in Abschnitte zerfällt.

»Wir haben einen Segmentierungsfehler.«

Mittelhochdeutsche Verse kamen zeilenweise herein — aber durch
EINFACHE Zeilenumbrüche, also als ein Block ohne Leerzeilen. Damit
griff die Ersatzregel »an Satzenden trennen«, und im
Mittelhochdeutschen steht der Punkt mitten im Vers:

    11  dô truoc . unde noch sîn name treit .

wurde zu zwei Abschnitten. Gemessen am laufenden Bestand: 7684 Zeilen
im Original, 8906 gespeicherte Abschnitte — 1222 zu viel, bei 144 von
172 Texten.

Dazu kam, dass der Werkzeugtext etwas anderes versprach, als der Code
tat: »Absätze durch Leerzeilen trennen« — von Sätzen stand da nichts.

Der heikle Teil ist das Nachträgliche: an den Abschnittskennungen
hängen die Referenzübersetzungen und die eigenen Fassungen.
"""

import pytest

VERSE = ("11  dô truoc . unde noch sîn name treit .\n"
         "12  des habent die wârheit .\n"
         "13  sîne lantliute .")


@pytest.fixture()
def bestand(klient):
    b = klient.post("/api/benutzer", json={"name": "Lernender 1"}).json()
    s = klient.post("/api/sammlungen", json={
        "besitzer_id": b["id"], "name": "Mittelhochdeutsch",
        "sprache": "gmh"}).json()
    return b, s


def _abschnitte(klient, text_id):
    d = klient.get(f"/api/texte/{text_id}").json()
    return [a["original"] for a in d["abschnitte"]]


def test_der_fehler_ohne_angabe(klient, bestand):
    """Die Gegenprobe zum Befund — damit festgehalten ist, was ohne
    Angabe geschieht und warum es für Verse falsch ist."""
    b, s = bestand
    t = klient.post(f"/api/sammlungen/{s['id']}/texte", json={
        "titel": "Iwein", "inhalt": VERSE}).json()
    assert _abschnitte(klient, t["id"]) == [
        "11  dô truoc .", "unde noch sîn name treit .",
        "12  des habent die wârheit .", "13  sîne lantliute ."]


def test_zeilenweise_bleibt_der_vers_ganz(klient, bestand):
    b, s = bestand
    t = klient.post(f"/api/sammlungen/{s['id']}/texte", json={
        "titel": "Iwein", "inhalt": VERSE, "aufteilung": "zeilen"}).json()
    assert _abschnitte(klient, t["id"]) == [
        "11  dô truoc . unde noch sîn name treit .",
        "12  des habent die wârheit .",
        "13  sîne lantliute ."]
    assert klient.get(f"/api/texte/{t['id']}").json()["aufteilung"] == "zeilen"


def test_keine_laesst_den_text_in_einem_stueck(klient, bestand):
    b, s = bestand
    t = klient.post(f"/api/sammlungen/{s['id']}/texte", json={
        "titel": "Iwein", "inhalt": VERSE, "aufteilung": "keine"}).json()
    assert len(_abschnitte(klient, t["id"])) == 1


def test_absatz_trennt_nur_an_leerzeilen(klient, bestand):
    b, s = bestand
    t = klient.post(f"/api/sammlungen/{s['id']}/texte", json={
        "titel": "Prosa", "aufteilung": "absatz",
        "inhalt": "Erster Satz. Zweiter Satz.\n\nNeuer Absatz."}).json()
    assert _abschnitte(klient, t["id"]) == [
        "Erster Satz. Zweiter Satz.", "Neuer Absatz."]


# ------------------------------------------------- Nachträglich ändern

def test_neu_aufteilen_nimmt_die_uebersetzungen_mit(klient, bestand):
    """Der heikle Teil.

    Zwei zerschnittene Hälften eines Verses haben je eine Übersetzung.
    Werden sie zu einem Abschnitt zusammengeführt, müssen beide
    Übersetzungen mit — in der richtigen Reihenfolge.
    """
    b, s = bestand
    t = klient.post(f"/api/sammlungen/{s['id']}/texte", json={
        "titel": "Iwein", "inhalt": VERSE}).json()
    ids = [a["id"] for a in t["abschnitte"]]
    klient.put(f"/api/texte/{t['id']}/referenz", json={"fassungen": {
        str(ids[0]): "da trug er",
        str(ids[1]): "und noch trägt seinen Namen",
        str(ids[2]): "das bezeugen"}})

    a = klient.put(f"/api/texte/{t['id']}/aufteilung",
                   json={"aufteilung": "zeilen"})
    assert a.status_code == 200, a.text
    bericht = a.json()
    assert bericht["abschnitte_vorher"] == 4
    assert bericht["abschnitte_nachher"] == 3
    assert bericht["zusammengefuegt"] == 1

    d = klient.get(f"/api/texte/{t['id']}").json()
    assert d["abschnitte"][0]["referenz"] == "da trug er und noch trägt seinen Namen"
    assert d["abschnitte"][1]["referenz"] == "das bezeugen"
    assert d["abschnitte"][2]["referenz"] is None


def test_neu_aufteilen_nimmt_die_eigene_fassung_mit(klient, bestand):
    """Die eigene Fassung gehört der Person und ist oft eine halbe
    Stunde Arbeit. Sie darf beim Umsortieren nicht verschwinden."""
    b, s = bestand
    t = klient.post(f"/api/sammlungen/{s['id']}/texte", json={
        "titel": "Iwein", "inhalt": VERSE}).json()
    ids = [a["id"] for a in t["abschnitte"]]
    for kennung, fassung in ((ids[0], "da trug er"),
                             (ids[1], "und trägt noch seinen Namen")):
        klient.put(f"/api/abschnitte/{kennung}/fassung",
                   json={"benutzer_id": b["id"], "fassung": fassung})

    klient.put(f"/api/texte/{t['id']}/aufteilung",
               json={"aufteilung": "zeilen"})

    d = klient.get(f"/api/texte/{t['id']}",
                   params={"benutzer_id": b["id"]}).json()
    assert d["abschnitte"][0]["meine_fassung"] == \
        "da trug er und trägt noch seinen Namen"


def test_nur_pruefen_schreibt_nichts(klient, bestand):
    """Bei 173 Texten mit Übersetzungen daran will man das vorher
    sehen."""
    b, s = bestand
    t = klient.post(f"/api/sammlungen/{s['id']}/texte", json={
        "titel": "Iwein", "inhalt": VERSE}).json()
    vorher = _abschnitte(klient, t["id"])

    bericht = klient.put(f"/api/texte/{t['id']}/aufteilung",
                         json={"aufteilung": "zeilen",
                               "nur_pruefen": True}).json()
    assert bericht["geschrieben"] is False
    assert bericht["abschnitte_nachher"] == 3
    assert bericht["beispiel"][0]["original"].startswith("11  dô truoc")
    assert _abschnitte(klient, t["id"]) == vorher, "nichts angefasst"


def test_dieselbe_aufteilung_fasst_nichts_an(klient, bestand):
    """Sonst verlöre jemand seine Kennungen, nur weil er die Funktion
    zweimal aufgerufen hat."""
    b, s = bestand
    t = klient.post(f"/api/sammlungen/{s['id']}/texte", json={
        "titel": "Iwein", "inhalt": VERSE, "aufteilung": "zeilen"}).json()
    vorher = [a["id"] for a in klient.get(f"/api/texte/{t['id']}").json()["abschnitte"]]

    bericht = klient.put(f"/api/texte/{t['id']}/aufteilung",
                         json={"aufteilung": "zeilen"}).json()
    assert bericht["geaendert"] is False
    nachher = [a["id"] for a in klient.get(f"/api/texte/{t['id']}").json()["abschnitte"]]
    assert nachher == vorher, "dieselben Kennungen"


def test_eine_unbekannte_aufteilung_wird_abgewiesen(klient, bestand):
    b, s = bestand
    a = klient.post(f"/api/sammlungen/{s['id']}/texte", json={
        "titel": "Iwein", "inhalt": VERSE, "aufteilung": "verse"})
    assert a.status_code == 422, a.text
