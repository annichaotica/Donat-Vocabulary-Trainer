"""Den Artikel mitzuschreiben ist die bessere Gewohnheit.

Die Haltung dahinter, und sie ist nicht selbstverständlich: wer ihn
weglässt, hat nichts falsch gemacht — aber eigentlich sollte man ihn
mitschreiben. Also gilt beides als richtig, und wer ihn weglässt, bekommt
ihn wenigstens zu sehen. Ein FALSCHER Artikel ist dagegen ein echter
Fehler: genau den soll man beim Üben loswerden.
"""


def _aufbau(klient):
    b = klient.post("/api/benutzer", json={"name": "Artikelnde"}).json()
    s = klient.post("/api/sammlungen", json={
        "besitzer_id": b["id"], "name": "Griechisch", "sprache": "el"}).json()
    klient.post(f"/api/sammlungen/{s['id']}/import/vokabeln", json={
        "eintraege": [{
            "lemma": "το καρότο", "wortart": "substantiv",
            "merkmale": {"genus": "n"},
            "bedeutungen": [{"uebersetzungen": ["die Karotte", "die Möhre"]}],
            "formen": [
                {"text": "καρότο", "merkmale": {"kasus": "nom",
                                                "numerus": "sg"}},
                {"text": "καρότου", "merkmale": {"kasus": "gen",
                                                 "numerus": "sg"}},
                {"text": "καρότα", "merkmale": {"kasus": "nom",
                                                "numerus": "pl"}}]}]})
    klient.post(f"/api/sammlungen/{s['id']}/freigabe", json={"lexem_ids": [1]})
    return b, s


def _form(klient, b, s, teil):
    aufgaben = klient.get("/api/lernen/naechste", params={
        "benutzer_id": b["id"], "sammlung_id": s["id"],
        "nur": "frei", "anzahl": 30}).json()
    return next(a for a in aufgaben
                if a["typ"] == "form_bilden" and teil in a["frage_zusatz"])


def pruefen(klient, b, aufgabe, antwort):
    return klient.post("/api/lernen/pruefen", json={
        "benutzer_id": b["id"], "aufgabe_id": aufgabe["aufgabe_id"],
        "antwort": antwort}).json()


def test_mit_artikel_ist_richtig(klient):
    """»τα καρότα« für den Nominativ Plural — vorher hieß es »Hier gehört
    kein Artikel davor«, obwohl er genau dorthin gehört."""
    b, s = _aufbau(klient)
    plural = _form(klient, b, s, "Plural")
    e = pruefen(klient, b, plural, "τα καρότα")
    assert e["urteil"]["urteil"] == "richtig"
    assert not e["urteil"]["abweichungen"]


def test_ohne_artikel_ist_auch_richtig_aber_er_wird_gezeigt(klient):
    b, s = _aufbau(klient)
    plural = _form(klient, b, s, "Plural")
    e = pruefen(klient, b, plural, "καρότα")
    assert e["urteil"]["urteil"] == "richtig"
    assert e["urteil"]["hinweis"] == "Mit Artikel: τα καρότα"


def test_falscher_artikel_ist_ein_fehler(klient):
    """Den soll man beim Üben ja gerade loswerden."""
    b, s = _aufbau(klient)
    plural = _form(klient, b, s, "Plural")
    e = pruefen(klient, b, plural, "το καρότα")
    assert e["urteil"]["urteil"] == "falsch"
    assert "τα" in e["urteil"]["hinweis"]


def test_auch_im_genitiv_und_nicht_nur_im_nominativ(klient):
    """Vorher kannte die Artikelliste nur ο, η, το, οι, τα — »του« galt
    als Teil des Wortes und damit als Tippfehler."""
    b, s = _aufbau(klient)
    genitiv = _form(klient, b, s, "Genitiv")
    assert pruefen(klient, b, genitiv,
                   "του καρότου")["urteil"]["urteil"] == "richtig"
    e = pruefen(klient, b, genitiv, "καρότου")
    assert e["urteil"]["urteil"] == "richtig"
    assert e["urteil"]["hinweis"] == "Mit Artikel: του καρότου"


def test_im_vokativ_steht_keiner(klient):
    import sys
    sys.path.insert(0, "backend")
    import sprachen
    assert sprachen.artikel_fuer("el", {"genus": "n"},
                                 {"kasus": "vok", "numerus": "sg"}) is None


def test_gemeinsames_geschlecht_zeigt_einen(klient):
    """ο/η γιατρός — irgendeiner muss gezeigt werden, sonst gar keiner."""
    import sys
    sys.path.insert(0, "backend")
    import sprachen
    assert sprachen.artikel_fuer("el", {"genus": "mf"},
                                 {"kasus": "nom", "numerus": "sg"}) == "ο"


def test_franzoesisch_beugt_den_artikel_nur_nach_zahl(klient):
    import sys
    sys.path.insert(0, "backend")
    import sprachen
    assert sprachen.artikel_fuer("fr", {"genus": "f"}, {"numerus": "sg"}) == "la"
    assert sprachen.artikel_fuer("fr", {"genus": "f"}, {"numerus": "pl"}) == "les"
