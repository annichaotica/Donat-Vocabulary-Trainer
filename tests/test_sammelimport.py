"""Sammelimport: viele Wörter in einem Aufruf.

Die drei Eigenschaften, auf die es ankommt: Probelauf ohne Folgen,
Wiederholbarkeit ohne Doppelte, und dass Geprüftes nie überschrieben wird.
"""


def _aufbau(klient, sprache="el"):
    b = klient.post("/api/benutzer", json={"name": "Importeurin"}).json()
    s = klient.post("/api/sammlungen", json={
        "besitzer_id": b["id"], "name": "Griechisch", "sprache": sprache}).json()
    return b, s


def _reihe(worte, merkmale):
    personen = [("1", "sg"), ("2", "sg"), ("3", "sg"),
                ("1", "pl"), ("2", "pl"), ("3", "pl")]
    return [{"text": w, "merkmale": {**merkmale, "person": p, "numerus": n}}
            for w, (p, n) in zip(worte, personen)]


GRAFO = {
    "lemma": "γράφω", "wortart": "verb", "lektion_nr": 3,
    "lektion_titel": "Im Büro", "reihenfolge": 1,
    "merkmale": {"klasse": "Α-Konjugation"},
    "bedeutungen": [{"uebersetzungen": ["schreiben", "aufschreiben"]}],
    "formen": _reihe(["γράφω", "γράφεις", "γράφει",
                      "γράφουμε", "γράφετε", "γράφουν"],
                     {"modus": "indikativ", "tempus": "praesens"}),
}
SPITI = {
    "lemma": "το σπίτι", "wortart": "substantiv", "lektion_nr": 3,
    "reihenfolge": 2, "merkmale": {"genus": "n"},
    "bedeutungen": [{"uebersetzungen": ["das Haus", "die Wohnung"]}],
}


def importieren(klient, sammlung_id, eintraege, **kw):
    return klient.post(f"/api/sammlungen/{sammlung_id}/import/vokabeln",
                       json={"eintraege": eintraege, **kw}).json()


# ----------------------------------------------------------- Probelauf

def test_probelauf_schreibt_nichts_meldet_aber_alles(klient):
    _b, s = _aufbau(klient)
    ergebnis = importieren(klient, s["id"], [GRAFO, SPITI], nur_pruefen=True)
    assert ergebnis["nur_pruefen"] is True
    assert ergebnis["angelegt"] == 2
    # ... aber im Bestand steht nichts
    assert klient.get(f"/api/sammlungen/{s['id']}/lexeme").json()["gesamt"] == 0
    assert klient.get(f"/api/sammlungen/{s['id']}/lektionen").json() == []


def test_probelauf_meldet_befunde(klient):
    _b, s = _aufbau(klient)
    lueckig = {**GRAFO, "formen": GRAFO["formen"][:2]}
    ergebnis = importieren(klient, s["id"], [lueckig], nur_pruefen=True)
    arten = {b["art"] for e in ergebnis["eintraege"] for b in e.get("befunde", [])}
    assert "paradigma_lueckig" in arten


# --------------------------------------------------------- Wiederholbar

def test_zweiter_lauf_verdoppelt_nicht(klient):
    _b, s = _aufbau(klient)
    importieren(klient, s["id"], [GRAFO, SPITI])
    zweiter = importieren(klient, s["id"], [GRAFO, SPITI])
    assert zweiter["angelegt"] == 0 and zweiter["aktualisiert"] == 2
    assert klient.get(f"/api/sammlungen/{s['id']}/lexeme").json()["gesamt"] == 2


def test_zweiter_lauf_bessert_nach(klient):
    _b, s = _aufbau(klient)
    importieren(klient, s["id"], [{**GRAFO, "formen": GRAFO["formen"][:3]}])
    importieren(klient, s["id"], [GRAFO])          # jetzt vollständig
    liste = klient.get(f"/api/sammlungen/{s['id']}/lexeme").json()["lexeme"]
    lexem = klient.get(f"/api/lexeme/{liste[0]['id']}").json()
    assert len(lexem["formen"]) == 6


def test_eigene_kennung_trennt_gleichlauter(klient):
    """φορά heißt »Mal« und »er trägt« — ohne Kennung wären das ein Eintrag."""
    _b, s = _aufbau(klient)
    importieren(klient, s["id"], [
        {"lemma": "φορά", "wortart": "substantiv", "kennung": "fora-mal",
         "merkmale": {"genus": "f"},
         "bedeutungen": [{"uebersetzungen": ["das Mal"]}]},
        {"lemma": "φορά", "wortart": "substantiv", "kennung": "fora-traegt",
         "merkmale": {"genus": "f"},
         "bedeutungen": [{"uebersetzungen": ["Wendung"]}]},
    ])
    assert klient.get(f"/api/sammlungen/{s['id']}/lexeme").json()["gesamt"] == 2


# ------------------------------------------------- Geprüftes ist geschützt

def test_gepruefte_form_wird_nicht_ueberschrieben(klient):
    """Sonst könnte ein fehlerhafter Durchlauf stillschweigend wegräumen,
    was jemand mühsam richtiggestellt hat."""
    _b, s = _aufbau(klient)
    importieren(klient, s["id"], [GRAFO])
    liste = klient.get(f"/api/sammlungen/{s['id']}/lexeme").json()["lexeme"]
    lexem = klient.get(f"/api/lexeme/{liste[0]['id']}").json()
    erste = next(f for f in lexem["formen"] if f["text"] == "γράφεις")
    klient.post(f"/api/formen/{erste['id']}/bestaetigen")

    # Jetzt ein Import mit abweichender Form an derselben Stelle
    kaputt = {**GRAFO, "formen": [
        {**f, "text": "FALSCH"} if f["text"] == "γράφεις" else f
        for f in GRAFO["formen"]]}
    ergebnis = importieren(klient, s["id"], [kaputt])

    eintrag = ergebnis["eintraege"][0]
    assert "abweichungen" in eintrag
    assert "γράφεις ist geprüft" in eintrag["abweichungen"][0]
    nachher = klient.get(f"/api/lexeme/{liste[0]['id']}").json()
    assert any(f["text"] == "γράφεις" for f in nachher["formen"])
    assert not any(f["text"] == "FALSCH" for f in nachher["formen"])


def test_ungepruefte_form_wird_nachgezogen(klient):
    _b, s = _aufbau(klient)
    importieren(klient, s["id"], [GRAFO])
    berichtigt = {**GRAFO, "formen": [
        {**f, "text": "γράφετε!"} if f["text"] == "γράφετε" else f
        for f in GRAFO["formen"]]}
    ergebnis = importieren(klient, s["id"], [berichtigt])
    assert ergebnis["formen_geaendert"] == 1


# ------------------------------------------------------------- Lektionen

def test_lektionen_entstehen_beim_import(klient):
    _b, s = _aufbau(klient)
    ergebnis = importieren(klient, s["id"], [GRAFO, SPITI])
    assert ergebnis["lektionen_neu"] == [3]
    lektionen = klient.get(f"/api/sammlungen/{s['id']}/lektionen").json()
    assert len(lektionen) == 1
    assert lektionen[0]["nr"] == 3 and lektionen[0]["name"] == "Im Büro"
    assert lektionen[0]["lexeme"] == 2


def test_die_nummer_ist_der_schluessel_nicht_der_name(klient):
    """Lehrwerke benennen Lektionen um, nummerieren sie aber nicht neu."""
    _b, s = _aufbau(klient)
    importieren(klient, s["id"], [GRAFO])
    importieren(klient, s["id"], [{**SPITI, "lektion_nr": 3,
                                   "lektion_titel": "Im Büro (neu)"}])
    lektionen = klient.get(f"/api/sammlungen/{s['id']}/lektionen").json()
    assert len(lektionen) == 1
    assert lektionen[0]["name"] == "Im Büro (neu)"


def test_abfrage_bis_zu_einer_lektion(klient):
    """Der übliche Schnitt beim Mitlernen mit einem Lehrwerk."""
    b, s = _aufbau(klient)
    importieren(klient, s["id"], [
        {**GRAFO, "lektion_nr": 1},
        {**SPITI, "lektion_nr": 1},
        {"lemma": "αργότερα", "wortart": "adverb", "lektion_nr": 40,
         "bedeutungen": [{"uebersetzungen": ["später"]}]},
    ])
    alle = klient.get("/api/lernen/naechste", params={
        "benutzer_id": b["id"], "sammlung_id": s["id"], "anzahl": 50}).json()
    frueh = klient.get("/api/lernen/naechste", params={
        "benutzer_id": b["id"], "sammlung_id": s["id"], "anzahl": 50,
        "bis_lektion": 5}).json()
    lemmata_alle = {a["lexem_id"] for a in alle}
    lemmata_frueh = {a["lexem_id"] for a in frueh}
    assert len(lemmata_alle) == 3
    assert len(lemmata_frueh) == 2


def test_neues_kommt_in_lernreihenfolge(klient):
    b, s = _aufbau(klient)
    importieren(klient, s["id"], [
        {"lemma": "zweites", "wortart": "adverb", "lektion_nr": 2,
         "reihenfolge": 1, "bedeutungen": [{"uebersetzungen": ["zwei"]}]},
        {"lemma": "erstes", "wortart": "adverb", "lektion_nr": 1,
         "reihenfolge": 1, "bedeutungen": [{"uebersetzungen": ["eins"]}]},
    ])
    reihe = klient.get("/api/lernen/naechste", params={
        "benutzer_id": b["id"], "sammlung_id": s["id"], "anzahl": 1,
        "nur": "neu"}).json()
    # Lektion 1 kommt vor Lektion 2, nicht die Eingabereihenfolge
    assert reihe[0]["lexem_id"] == klient.get(
        f"/api/sammlungen/{s['id']}/lexeme",
        params={"suche": "erstes"}).json()["lexeme"][0]["id"]


# ----------------------------------------------------------- Abweisung

def test_unbrauchbare_eintraege_werden_einzeln_abgewiesen(klient):
    """Ein schlechter Eintrag darf nicht den ganzen Lauf verwerfen."""
    _b, s = _aufbau(klient)
    ergebnis = importieren(klient, s["id"], [
        GRAFO,
        {"lemma": "", "wortart": "verb"},
        {"lemma": "x", "wortart": "quatsch"},
        {"lemma": "y", "wortart": "verb",
         "formen": [{"text": "z", "merkmale": {"tempus": "erfunden"}}]},
        SPITI,
    ])
    assert ergebnis["angelegt"] == 2
    assert ergebnis["abgelehnt"] == 3
    gruende = " ".join(b for e in ergebnis["eintraege"]
                       for b in e.get("befunde", []) if isinstance(b, str))
    assert "lemma fehlt" in gruende
    assert "quatsch" in gruende
    assert "erfunden" in gruende


def test_bericht_bleibt_kurz(klient):
    """Bei sechzehnhundert Wörtern will niemand sechzehnhundert Zeilen lesen."""
    _b, s = _aufbau(klient)
    viele = [{"lemma": f"wort{i}", "wortart": "adverb",
              "bedeutungen": [{"uebersetzungen": [f"Wort {i}", f"Dingsda {i}"]}]}
             for i in range(60)]
    ergebnis = importieren(klient, s["id"], viele)
    assert ergebnis["angelegt"] == 60
    # Nur Einträge mit Befunden erscheinen; diese haben keine.
    assert ergebnis["mit_befunden"] == 0
    assert ergebnis["eintraege"] == []
