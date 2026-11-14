"""Den Artikel mitzuschreiben darf nie ein Fehler sein.

Der Wunsch aus dem Betrieb: »bei mehrzahl und ähnlichen fragen möchte
ich schon auch den artikel mitgeben dürfen … es ist eher so, dass es
halt kein fehler ist, wenn man es nicht mit schreibt, es aber eigentlich
schon sollte.«

Gebaut war das für die Formaufgaben. Für die beiden Bedeutungsaufgaben
war es das Gegenteil: sie geben nie an, welcher Artikel dazugehört, und
die Prüfung las »nichts angegeben« als »hier gehört keiner hin«. Wer
»das Haus« schrieb, bekam »fast« mit dem Hinweis, hier gehöre kein
Artikel davor — für den richtigen Artikel wie für den falschen.

None heißt jetzt »dazu ist nichts bekannt«, und nur das ausdrückliche
KEIN_ARTIKEL (Vokativ) macht einen mitgeschriebenen zum Fehler.
"""

import pytest


@pytest.fixture()
def bestand(klient):
    b = klient.post("/api/benutzer", json={"name": "Übende"}).json()
    s = klient.post("/api/sammlungen", json={
        "besitzer_id": b["id"], "name": "Griechisch", "sprache": "el"}).json()
    klient.post(f"/api/sammlungen/{s['id']}/import/vokabeln", json={
        "eintraege": [{
            "lemma": "σπίτι", "wortart": "substantiv", "lektion_nr": 1,
            "merkmale": {"genus": "n"},
            "bedeutungen": [{"uebersetzungen": ["Haus"]}],
            "formen": [
                {"text": "σπίτι", "merkmale": {"kasus": "nom", "numerus": "sg"}},
                {"text": "σπίτια", "merkmale": {"kasus": "nom", "numerus": "pl"}},
            ]}]})
    klient.post(f"/api/sammlungen/{s['id']}/freigabe", json={"lektion_nr": 1})
    aufgaben = klient.get("/api/lernen/naechste", params={
        "benutzer_id": b["id"], "sammlung_id": s["id"], "anzahl": 20,
        "nur": "frei"}).json()
    return b, {a["typ"]: a for a in aufgaben}


def _urteil(klient, b, aufgabe, antwort):
    antwort_d = klient.post("/api/lernen/pruefen", json={
        "benutzer_id": b["id"], "aufgabe_id": aufgabe["aufgabe_id"],
        "antwort": antwort}).json()
    # Die Route verpackt das Urteil noch einmal.
    return antwort_d.get("urteil", antwort_d)


def test_der_richtige_artikel_ist_richtig(bestand, klient):
    """το σπίτι muss so gut sein wie σπίτι."""
    b, nach_typ = bestand
    a = nach_typ.get("bedeutung_deutsch_fremd")
    assert a is not None, "Aufgabentyp fehlt"
    ohne = _urteil(klient, b, a, "σπίτι")
    mit = _urteil(klient, b, a, "το σπίτι")
    assert ohne["urteil"] == "richtig"
    assert mit["urteil"] == "richtig", mit


def test_der_deutsche_artikel_ist_auch_richtig(bestand, klient):
    """In der anderen Richtung genauso: »das Haus« ist kein Fehler."""
    b, nach_typ = bestand
    a = nach_typ.get("bedeutung_fremd_deutsch")
    assert a is not None, "Aufgabentyp fehlt"
    assert _urteil(klient, b, a, "Haus")["urteil"] == "richtig"
    mit = _urteil(klient, b, a, "das Haus")
    assert mit["urteil"] == "richtig", mit


def test_der_falsche_artikel_bleibt_ein_fehler(bestand, klient):
    """Nur die Form wird milde behandelt, nicht der Inhalt."""
    b, nach_typ = bestand
    a = nach_typ.get("form_bilden")
    if a is None:
        pytest.skip("keine Formaufgabe erzeugt")
    falsch = _urteil(klient, b, a, "η σπίτι")
    assert falsch["urteil"] != "richtig"


def test_im_vokativ_gehoert_wirklich_keiner_davor():
    """Die einzige Stelle, an der ein mitgeschriebener Artikel zählt."""
    import pruefung, sprachen
    assert sprachen.artikel_fuer(
        "el", {"genus": "n"}, {"kasus": "vok"}) == pruefung.KEIN_ARTIKEL
    urteil = pruefung.pruefen("το σπίτι", ["σπίτι"], sprachen.profil("el"),
                              artikel_verlangt=pruefung.KEIN_ARTIKEL)
    assert "artikel_ueberfluessig" in urteil.abweichungen


def test_ohne_angabe_sagt_die_pruefung_nichts_dazu():
    """None heißt »unbekannt«, nicht »keiner«."""
    import pruefung, sprachen
    urteil = pruefung.pruefen("το σπίτι", ["σπίτι"], sprachen.profil("el"))
    assert urteil.urteil == "richtig", urteil
    assert "artikel_ueberfluessig" not in urteil.abweichungen
