"""Import aus CSV, Anki- und Quizlet-Ausfuhren."""


def _aufbau(klient, sprache="fr"):
    b = klient.post("/api/benutzer", json={"name": "Importeur"}).json()
    s = klient.post("/api/sammlungen", json={
        "besitzer_id": b["id"], "name": "Probe", "sprache": sprache}).json()
    return b, s


ANKI = "\n".join([
    "aller\tgehen, laufen",
    "travailler\tarbeiten",
    "la table\tder Tisch; die Tafel",
])

MIT_KOPF = "\n".join([
    "Wort;Bedeutung;Wortart;Lektion",
    "aller;gehen, laufen;Verb;Lektion 1",
    "la table;der Tisch;Substantiv;Lektion 1",
    "travailler;arbeiten;v;Lektion 2",
])


# ------------------------------------------------------------- Erkennung

def test_tabulator_wird_erkannt(klient):
    _b, s = _aufbau(klient)
    schau = klient.post(f"/api/sammlungen/{s['id']}/import/vorschau",
                        json={"text": ANKI}).json()
    assert schau["trenner"] == "Tabulator"
    assert schau["hat_kopfzeile"] is False
    assert schau["brauchbar"] == 3


def test_kopfzeile_wird_erkannt_und_gedeutet(klient):
    _b, s = _aufbau(klient)
    schau = klient.post(f"/api/sammlungen/{s['id']}/import/vorschau",
                        json={"text": MIT_KOPF}).json()
    assert schau["trenner"] == "Semikolon"
    assert schau["hat_kopfzeile"] is True
    assert schau["zuordnung"] == {"0": "lemma", "1": "uebersetzung",
                                  "2": "wortart", "3": "lektion"}


def test_mehrere_bedeutungen_in_einer_zelle(klient):
    _b, s = _aufbau(klient)
    schau = klient.post(f"/api/sammlungen/{s['id']}/import/vorschau",
                        json={"text": ANKI}).json()
    erstes = schau["beispiel"][0]
    assert erstes["uebersetzungen"] == ["gehen", "laufen"]
    tisch = schau["beispiel"][2]
    assert tisch["uebersetzungen"] == ["der Tisch", "die Tafel"]


def test_artikel_verraet_das_geschlecht(klient):
    _b, s = _aufbau(klient)
    schau = klient.post(f"/api/sammlungen/{s['id']}/import/vorschau",
                        json={"text": ANKI}).json()
    tisch = schau["beispiel"][2]
    assert tisch["merkmale"] == {"genus": "f"}      # la table
    assert tisch["wortart"] == "substantiv"


def test_wortart_in_jeder_schreibweise(klient):
    _b, s = _aufbau(klient)
    schau = klient.post(f"/api/sammlungen/{s['id']}/import/vorschau",
                        json={"text": MIT_KOPF}).json()
    arten = [e["wortart"] for e in schau["beispiel"]]
    assert arten == ["verb", "substantiv", "verb"]   # "Verb", "Substantiv", "v"


def test_griechische_spalte_wird_als_lemma_erkannt(klient):
    """Ohne Kopfzeile entscheidet die Schrift: die griechische Spalte ist
    das Lemma, auch wenn sie hinten steht."""
    _b, s = _aufbau(klient, "el")
    schau = klient.post(f"/api/sammlungen/{s['id']}/import/vorschau",
                        json={"text": "schreiben\tγράφω\nlesen\tδιαβάζω"}).json()
    assert schau["zuordnung"]["1"] == "lemma"
    assert schau["beispiel"][0]["lemma"] == "γράφω"
    assert schau["beispiel"][0]["uebersetzungen"] == ["schreiben"]


def test_unbrauchbare_zeilen_werden_benannt_nicht_verschluckt(klient):
    _b, s = _aufbau(klient)
    schau = klient.post(f"/api/sammlungen/{s['id']}/import/vorschau", json={
        "text": "aller\tgehen\nparler\t\n\tnur Bedeutung"}).json()
    assert schau["brauchbar"] == 1
    gruende = [u["grund"] for u in schau["uebersprungen"]]
    assert any("parler" in g for g in gruende)


def test_leere_datei(klient):
    _b, s = _aufbau(klient)
    schau = klient.post(f"/api/sammlungen/{s['id']}/import/vorschau",
                        json={"text": "   \n  \n"}).json()
    assert "fehler" in schau


# ------------------------------------------------------------- Übernahme

def test_uebernahme_legt_woerter_und_aufgaben_an(klient):
    _b, s = _aufbau(klient)
    ergebnis = klient.post(f"/api/sammlungen/{s['id']}/import",
                           json={"text": MIT_KOPF}).json()
    assert ergebnis["angelegt"] == 3
    assert ergebnis["aufgaben"] > 0
    liste = klient.get(f"/api/sammlungen/{s['id']}/lexeme").json()
    assert liste["gesamt"] == 3


def test_lektionen_entstehen_mit(klient):
    _b, s = _aufbau(klient)
    klient.post(f"/api/sammlungen/{s['id']}/import", json={"text": MIT_KOPF})
    lektionen = klient.get(f"/api/sammlungen/{s['id']}/lektionen").json()
    assert {l["name"] for l in lektionen} == {"Lektion 1", "Lektion 2"}
    assert sum(l["lexeme"] for l in lektionen) == 3


def test_doppelte_werden_standardmaessig_uebersprungen(klient):
    _b, s = _aufbau(klient)
    klient.post(f"/api/sammlungen/{s['id']}/import", json={"text": ANKI})
    zweites = klient.post(f"/api/sammlungen/{s['id']}/import",
                          json={"text": ANKI}).json()
    assert zweites["angelegt"] == 0 and zweites["uebersprungen"] == 3


def test_doppelte_koennen_bedeutungen_ergaenzen(klient):
    _b, s = _aufbau(klient)
    klient.post(f"/api/sammlungen/{s['id']}/import",
                json={"text": "aller\tgehen"})
    klient.post(f"/api/sammlungen/{s['id']}/import",
                json={"text": "aller\tfahren", "doppelte": "ergaenzen"})
    liste = klient.get(f"/api/sammlungen/{s['id']}/lexeme").json()
    assert liste["gesamt"] == 1
    lexem = klient.get(f"/api/lexeme/{liste['lexeme'][0]['id']}").json()
    assert len(lexem["bedeutungen"]) == 2


def test_eigene_zuordnung_schlaegt_die_erratene(klient):
    _b, s = _aufbau(klient)
    # Spalten vertauscht, und die Erkennung soll übersteuert werden
    ergebnis = klient.post(f"/api/sammlungen/{s['id']}/import", json={
        "text": "gehen\taller\narbeiten\ttravailler",
        "zuordnung": {"0": "uebersetzung", "1": "lemma"}}).json()
    assert ergebnis["angelegt"] == 2
    liste = klient.get(f"/api/sammlungen/{s['id']}/lexeme").json()
    assert {l["lemma"] for l in liste["lexeme"]} == {"aller", "travailler"}


def test_importiertes_wort_ist_sofort_abfragbar(klient):
    b, s = _aufbau(klient)
    klient.post(f"/api/sammlungen/{s['id']}/import", json={"text": ANKI})
    reihe = klient.get("/api/lernen/naechste", params={
        "benutzer_id": b["id"], "sammlung_id": s["id"], "anzahl": 1}).json()
    assert len(reihe) == 1
    aufgabe = reihe[0]
    ergebnis = klient.post("/api/lernen/pruefen", json={
        "benutzer_id": b["id"], "aufgabe_id": aufgabe["aufgabe_id"],
        "antwort": "gehen" if aufgabe["typ"] == "bedeutung_fremd_deutsch"
                   else "aller"}).json()
    assert ergebnis["urteil"]["urteil"] in ("richtig", "fast", "falsch")


def test_herkunft_import_wird_vermerkt(klient):
    _b, s = _aufbau(klient)
    klient.post(f"/api/sammlungen/{s['id']}/import", json={"text": ANKI})
    liste = klient.get(f"/api/sammlungen/{s['id']}/lexeme").json()
    lexem = klient.get(f"/api/lexeme/{liste['lexeme'][0]['id']}").json()
    assert lexem["formen"][0]["quelle"] == "import"
    assert lexem["bedeutungen"][0]["uebersetzungen"][0]["quelle"] == "import"
