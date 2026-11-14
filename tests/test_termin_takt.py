"""Ein Lernziel mit Termin gibt den Takt vor — und sagt, wenn es nicht reicht.

Aus dem Betrieb: »oder es vielleicht wenn man ein gewisses ziel hat, weil
z.B. eine probe zu schreiben ist, anders einstellen, also, tagesziel wäre
dann wenn alles sitzt?«

Der Code tat bisher so, als beantworte er das: `schaffbar` verglich gegen
eine fest eingebaute 40. Drei Fehler auf einmal —

1. die 40 hatte mit niemandes Einstellung etwas zu tun,
2. sie verglich Aufgaben mit Wörtern (ein griechisches Verb mit vierzig
   Formen ist EIN Wort, aber vierzig Aufgaben),
3. die Tagesdosis kam gar nicht vor: ein Ziel konnte »schaffbar« melden,
   während die Grenze es still unmöglich machte.

Jetzt wird in den eigenen Einheiten gerechnet, und wo es nicht reicht,
steht im Klartext, woran es liegt und welches Pensum nötig wäre.
"""

import datetime as dt

import pytest

P = [("1", "sg"), ("2", "sg"), ("3", "sg"), ("1", "pl"), ("2", "pl"), ("3", "pl")]
ENDUNGEN = ["ω", "εις", "ει", "ουμε", "ετε", "ουν"]
VERBEN = [("γράφ", "schreiben"), ("διαβάζ", "lesen"), ("παίζ", "spielen"),
          ("τρέχ", "laufen"), ("μιλ", "sprechen"), ("ακού", "hören"),
          ("μέν", "bleiben"), ("βλέπ", "sehen")]


@pytest.fixture()
def bestand(klient):
    """Acht Verben à sechs Formen — also wenige WÖRTER, viele AUFGABEN."""
    b = klient.post("/api/benutzer", json={"name": "Übende"}).json()
    s = klient.post("/api/sammlungen", json={
        "besitzer_id": b["id"], "name": "Griechisch", "sprache": "el"}).json()
    klient.post(f"/api/sammlungen/{s['id']}/import/vokabeln", json={
        "eintraege": [{
            "lemma": stamm + "ω", "wortart": "verb", "lektion_nr": 1,
            "reihenfolge": i,
            "bedeutungen": [{"uebersetzungen": [bed]}],
            "formen": [{"text": stamm + e, "merkmale": {
                "modus": "indikativ", "tempus": "praesens",
                "person": p, "numerus": n}}
                for e, (p, n) in zip(ENDUNGEN, P)]}
            for i, (stamm, bed) in enumerate(VERBEN)]})
    klient.post(f"/api/sammlungen/{s['id']}/freigabe", json={"lektion_nr": 1})
    return b, s


def _ziel(klient, b, s, tage=None):
    termin = ((dt.date.today() + dt.timedelta(days=tage)).isoformat()
              if tage is not None else None)
    antwort = klient.post("/api/lernziele", json={
        "benutzer_id": b["id"], "name": "Probe", "termin": termin,
        "umfang": {"sammlungen": [s["id"]]}})
    assert antwort.status_code == 201, antwort.text
    return antwort.json()


def _fortschritt(klient, b, ziel):
    return klient.get(f"/api/lernziele/{ziel['id']}/fortschritt",
                      params={"benutzer_id": b["id"]}).json()


def test_ohne_termin_steht_nichts_im_weg(bestand, klient):
    b, s = bestand
    f = _fortschritt(klient, b, _ziel(klient, b, s))
    assert f["schaffbar"] is True
    assert f["huerden"] == []
    assert f["neu_taeglich_noetig"] is None


def test_mit_reichlich_zeit_geht_es_sich_aus(bestand, klient):
    b, s = bestand
    f = _fortschritt(klient, b, _ziel(klient, b, s, tage=90))
    assert f["schaffbar"] is True, f["huerden"]


def test_zu_knapper_termin_sagt_woran_es_liegt(bestand, klient):
    """Nicht bloß »nicht schaffbar«, sondern in welcher Einheit es klemmt."""
    b, s = bestand
    klient.patch(f"/api/benutzer/{b['id']}",
                 json={"fragen_je_tag": 10, "neu_je_sitzung": 2})
    f = _fortschritt(klient, b, _ziel(klient, b, s, tage=5))

    assert f["schaffbar"] is False
    assert f["huerden"], "es muss dastehen, woran es scheitert"
    text = " ".join(f["huerden"])
    assert "Wörter" in text and "Aufgaben" in text, text
    assert f["pensum_jetzt"] == 10
    assert f["pensum_noetig"] > 10


def test_das_noetige_pensum_laesst_das_noetige_neue_durch(bestand, klient):
    """`pensum_noetig` ist keine Schätzung, sondern die Umkehrung der
    Reservierung: von der Dosis ist die Hälfte fürs Neue da."""
    import lernen
    b, s = bestand
    klient.patch(f"/api/benutzer/{b['id']}",
                 json={"fragen_je_tag": 10, "neu_je_sitzung": 50})
    f = _fortschritt(klient, b, _ziel(klient, b, s, tage=5))

    noetig = f["neu_taeglich_noetig"]
    assert round(f["pensum_noetig"] * lernen.NEU_ANTEIL) >= noetig


def test_mit_angepasstem_pensum_geht_es_dann(bestand, klient):
    """Der Knopf »Pensum anpassen« muss auch wirklich helfen."""
    b, s = bestand
    klient.patch(f"/api/benutzer/{b['id']}",
                 json={"fragen_je_tag": 10, "neu_je_sitzung": 2})
    ziel = _ziel(klient, b, s, tage=5)
    f = _fortschritt(klient, b, ziel)
    assert f["schaffbar"] is False

    klient.patch(f"/api/benutzer/{b['id']}", json={
        "fragen_je_tag": f["pensum_noetig"],
        "neu_je_sitzung": f["woerter_taeglich_noetig"]})
    assert _fortschritt(klient, b, ziel)["schaffbar"] is True


def test_ohne_grenze_steht_das_pensum_nie_im_weg(bestand, klient):
    """0 heißt ausdrücklich »ohne Grenze« — dann kann sie nichts blockieren."""
    b, s = bestand
    klient.patch(f"/api/benutzer/{b['id']}",
                 json={"fragen_je_tag": 0, "neu_je_sitzung": 200})
    f = _fortschritt(klient, b, _ziel(klient, b, s, tage=3))
    assert f["schaffbar"] is True, f["huerden"]


def test_woerter_und_aufgaben_werden_nicht_verwechselt(bestand, klient):
    """Acht Verben à sechs Formen: deutlich mehr Aufgaben als Wörter."""
    b, s = bestand
    f = _fortschritt(klient, b, _ziel(klient, b, s, tage=10))
    assert f["neue_woerter"] == len(VERBEN)
    assert f["neu"] > f["neue_woerter"] * 2, (f["neu"], f["neue_woerter"])
    assert f["woerter_taeglich_noetig"] < f["neu_taeglich_noetig"]


def test_ein_termin_laesst_sich_auch_wieder_entfernen(bestand, klient):
    """`null` heißt bei einer Teiländerung »unverändert« — sonst löschte
    jede Teiländerung alles andere mit. Zum Leeren gibt es den leeren
    String. Ohne ihn bliebe ein Ziel für immer unter Zeitdruck."""
    b, s = bestand
    ziel = _ziel(klient, b, s, tage=5)
    assert _fortschritt(klient, b, ziel)["termin"] is not None

    klient.patch(f"/api/lernziele/{ziel['id']}",
                 json={"benutzer_id": b["id"], "termin": None})
    assert _fortschritt(klient, b, ziel)["termin"] is not None, \
        "null darf nicht löschen"

    klient.patch(f"/api/lernziele/{ziel['id']}",
                 json={"benutzer_id": b["id"], "termin": ""})
    f = _fortschritt(klient, b, ziel)
    assert f["termin"] is None
    assert f["lage"] == "ohne Termin"
    assert f["schaffbar"] is True


def test_ein_termin_in_fremdem_format_wird_abgewiesen(bestand, klient):
    """`dt.date.fromisoformat` nimmt seit Python 3.11 auch "20261114".
    Gespeichert würde der Rohtext — und `faellig <= '2026-11-14'` wäre
    damit dauerhaft unwahr: die Aufgabe verschwände still aus dem
    Terminplan, ohne dass jemand erführe, warum."""
    b, s = bestand
    aufgaben = klient.get("/api/lernen/naechste", params={
        "benutzer_id": b["id"], "sammlung_id": s["id"], "anzahl": 1}).json()
    kennung = aufgaben[0]["aufgabe_id"]
    for falsch in ("20301231", "2030-W47-1"):
        antwort = klient.post("/api/lernen/termin", json={
            "benutzer_id": b["id"], "aufgabe_id": kennung, "datum": falsch})
        assert antwort.status_code == 400, f"{falsch}: {antwort.text}"
    gut = klient.post("/api/lernen/termin", json={
        "benutzer_id": b["id"], "aufgabe_id": kennung, "datum": "2030-12-31"})
    assert gut.status_code == 200
