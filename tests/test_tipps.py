"""Ein Tipp — weniger als die Lösung, und die Abfrage läuft weiter.

Aus dem Betrieb: »wenn ich ein Wort ansehe, weil ich es nicht weiß, dann
komme ich nicht wieder zurück zur Abfrage, also muss das eher eine
eigene Tipp-Anzeige sein.«

Zwei Sachen in einer Beobachtung. »Wort ansehen« sprang auf eine andere
Seite und beendete dabei die Sitzung. Und zwischen »Weiß ich nicht«
(deckt alles auf, wertet als Nochmal) und gar nichts lag nichts: wer nur
einen Anstoß brauchte, hatte keine Wahl.
"""

import pytest


@pytest.fixture()
def bestand(klient):
    b = klient.post("/api/benutzer", json={"name": "Übende"}).json()
    s = klient.post("/api/sammlungen", json={
        "besitzer_id": b["id"], "name": "Griechisch", "sprache": "el"}).json()
    klient.post(f"/api/sammlungen/{s['id']}/import/vokabeln", json={
        "eintraege": [{
            "lemma": "γράφω", "wortart": "verb", "lektion_nr": 1,
            "bedeutungen": [{"uebersetzungen": ["schreiben"]}],
            "formen": [{"text": "γράφεις", "merkmale": {
                "modus": "indikativ", "tempus": "praesens",
                "person": "2", "numerus": "sg"}}]}]})
    klient.post(f"/api/sammlungen/{s['id']}/freigabe", json={"lektion_nr": 1})
    aufgaben = klient.get("/api/lernen/naechste", params={
        "benutzer_id": b["id"], "sammlung_id": s["id"], "anzahl": 10,
        "nur": "frei"}).json()
    return b, s, aufgaben


def _tipp(klient, b, aufgabe, stufe):
    return klient.get("/api/lernen/tipp", params={
        "benutzer_id": b["id"], "aufgabe_id": aufgabe["aufgabe_id"],
        "stufe": stufe}).json()


def test_der_tipp_verraet_die_loesung_nicht(bestand, klient):
    """Was der Browser nicht bekommt, kann er auch nicht verraten."""
    b, s, aufgaben = bestand
    a = next(x for x in aufgaben if x["typ"] == "form_bilden")
    for stufe in (1, 2, 3):
        t = _tipp(klient, b, a, stufe)
        roh = str(t)
        assert "γράφεις" not in roh, f"Stufe {stufe} enthält die Antwort: {t}"


def test_die_stufen_werden_schrittweise_deutlicher(bestand, klient):
    b, s, aufgaben = bestand
    a = next(x for x in aufgaben if x["typ"] == "form_bilden")
    masken = [_tipp(klient, b, a, st)["maske"] for st in (1, 2, 3)]
    verdeckt = [m.count("_") for m in masken]
    assert verdeckt[0] > verdeckt[1] > verdeckt[2], masken
    # Und auch auf der höchsten Stufe bleibt etwas zu tun.
    assert verdeckt[2] > 0, masken


def test_bei_griechisch_bleiben_die_selbstlaute_verdeckt(bestand, klient):
    """`VOKALE` war rein lateinisch — damit zeigte Stufe 3 bei
    griechischer Schrift das ganze Wort, und der Tipp war die Lösung."""
    import legasthenie
    assert "_" in legasthenie.maske("γράφεις", 3), legasthenie.maske("γράφεις", 3)
    assert "_" in legasthenie.maske("άνθρωπος", 3)


def test_ein_tipp_deckelt_die_bewertung(bestand, klient):
    """Mit Tipp gewusst ist nicht »auf Anhieb«, aber auch nicht
    »nicht gewusst«: die Antwort kam ja selbst."""
    b, s, aufgaben = bestand
    a = next(x for x in aufgaben if x["typ"] == "form_bilden")
    ohne = klient.post("/api/lernen/bewerten", json={
        "benutzer_id": b["id"], "aufgabe_id": a["aufgabe_id"],
        "urteil": "richtig"}).json()
    assert ohne["bewertung"] >= 3

    mit = klient.post("/api/lernen/bewerten", json={
        "benutzer_id": b["id"], "aufgabe_id": a["aufgabe_id"],
        "urteil": "richtig", "tipps": 1}).json()
    assert mit["bewertung"] == 2, mit
    assert "Tipp" in (mit.get("einschaetzung") or {}).get("begruendung", ""), mit


def test_der_stamm_kommt_nur_wenn_er_kuerzer_ist(bestand, klient):
    """Sonst wäre der »Tipp« das gesuchte Wort selbst."""
    b, s, aufgaben = bestand
    a = next(x for x in aufgaben if x["typ"] == "form_bilden")
    t = _tipp(klient, b, a, 1)
    if "stamm" in t:
        assert len(t["stamm"]) < len("γράφεις")


def test_die_abfrage_bleibt_bestehen():
    """Der eigentliche Punkt: »Wort ansehen« darf nicht mehr
    weg-navigieren, sonst ist die Sitzung hin."""
    import pathlib
    quelle = (pathlib.Path(__file__).resolve().parents[1]
              / "frontend" / "js" / "ansicht_lernen.js").read_text()
    assert "location.hash = `#/wort/" not in quelle
    assert "wortZeigen()" in quelle
