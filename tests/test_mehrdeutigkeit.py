"""Mehrdeutigkeit, Gleichlauter, weitere Wortarten und der Lernstand.

Drei Dinge, die ein Trainer gern falsch macht:

Er wertet »κοντός« für die Frage »klein« als Fehler, obwohl es ein zweites
richtiges Wort ist. Er lehnt φορά ab, weil die Schreibung schon vergeben
ist, obwohl es wirklich zwei Wörter sind. Und er kennt zu Pronomen und
Artikeln keine Formen, obwohl αυτός/αυτή/αυτό ein Paradigma ist.
"""


def _aufbau(klient, sprache="el"):
    b = klient.post("/api/benutzer", json={"name": "Lernende"}).json()
    s = klient.post("/api/sammlungen", json={
        "besitzer_id": b["id"], "name": "Griechisch", "sprache": sprache}).json()
    return b, s


def importieren(klient, sammlung_id, eintraege):
    return klient.post(f"/api/sammlungen/{sammlung_id}/import/vokabeln",
                       json={"eintraege": eintraege}).json()


def arten(klient, lexem_id):
    bericht = klient.get(f"/api/lexeme/{lexem_id}/pruefung").json()
    return {b["art"] for b in bericht["befunde"]}


def _lexem(klient, sammlung_id, lemma):
    return next(l for l in klient.get(
        f"/api/sammlungen/{sammlung_id}/lexeme").json()["lexeme"]
        if l["lemma"] == lemma)


KLEIN = [
    {"lemma": "μικρός", "wortart": "adjektiv",
     "bedeutungen": [{"uebersetzungen": ["klein", "gering"]}],
     "formen": [{"text": "μικρός", "merkmale": {
         "genus": "m", "kasus": "nom", "numerus": "sg"}}]},
    {"lemma": "κοντός", "wortart": "adjektiv",
     "bedeutungen": [{"uebersetzungen": ["klein", "kurz"]}],
     "formen": [{"text": "κοντός", "merkmale": {
         "genus": "m", "kasus": "nom", "numerus": "sg"}}]},
]


def _bedeutungsaufgabe(klient, lexem_id):
    lexem = klient.get(f"/api/lexeme/{lexem_id}").json()
    return next(a for a in lexem["aufgaben"]
                if a["typ"] == "bedeutung_deutsch_fremd" and a["aktiv"])


def pruefen(klient, benutzer_id, aufgabe_id, eingabe):
    antwort = klient.post("/api/lernen/pruefen", json={
        "benutzer_id": benutzer_id, "aufgabe_id": aufgabe_id,
        "antwort": eingabe})
    assert antwort.status_code == 200, antwort.text
    return antwort.json()


# ------------------------------------------------- Mehrdeutigkeit (Punkt 8)

def test_das_andere_richtige_wort_gilt_auch(klient):
    """Wer bei »klein« κοντός schreibt, hat nicht geirrt — er hat das
    andere richtige Wort genannt."""
    b, s = _aufbau(klient)
    importieren(klient, s["id"], KLEIN)
    aufgabe = _bedeutungsaufgabe(klient, _lexem(klient, s["id"], "μικρός")["id"])
    ergebnis = pruefen(klient, b["id"], aufgabe["id"], "κοντός")
    assert ergebnis["urteil"]["urteil"] == "richtig"
    # Aber es wird gesagt, welches Wort gesucht war — sonst bleibt das
    # gesuchte ungelernt.
    assert ergebnis["aufloesung"]["gesucht_war"] == "μικρός"
    assert "κοντός" in ergebnis["aufloesung"]["auch_richtig"]


def test_ein_kontext_macht_die_frage_eindeutig(klient):
    """Steht »klein, Körpergröße« in der Frage, ist gesagt, welches Wort
    gemeint ist — dann gilt auch nur dieses."""
    b, s = _aufbau(klient)
    importieren(klient, s["id"], [
        {**KLEIN[0], "bedeutungen": [
            {"uebersetzungen": ["klein"], "kontext": "Größe einer Sache"}]},
        {**KLEIN[1], "bedeutungen": [
            {"uebersetzungen": ["klein"], "kontext": "Körpergröße"}]}])
    aufgabe = _bedeutungsaufgabe(klient, _lexem(klient, s["id"], "μικρός")["id"])
    assert pruefen(klient, b["id"], aufgabe["id"],
                   "κοντός")["urteil"]["urteil"] == "falsch"
    assert pruefen(klient, b["id"], aufgabe["id"],
                   "μικρός")["urteil"]["urteil"] == "richtig"


def test_mehrdeutigkeit_wird_als_notiz_gemeldet(klient):
    """Als Notiz, nicht als Mangel: es ist die Sprache, kein Fehler."""
    _b, s = _aufbau(klient)
    bericht = importieren(klient, s["id"], KLEIN)
    assert bericht["angelegt"] == 2
    lexem = _lexem(klient, s["id"], "κοντός")
    befunde = klient.get(f"/api/lexeme/{lexem['id']}/pruefung").json()["befunde"]
    notiz = next(b for b in befunde if b["art"] == "uebersetzung_mehrdeutig")
    assert notiz["schwere"] == "notiz"
    assert "μικρός" in notiz["text"]
    assert "kontext" in notiz["rat"]
    # Und der Eintrag bleibt in Ordnung.
    assert klient.get(f"/api/lexeme/{lexem['id']}/pruefung").json()["gut"]


def test_ein_eindeutiges_wort_bekommt_keine_notiz(klient):
    _b, s = _aufbau(klient)
    importieren(klient, s["id"], [KLEIN[0]])
    lexem = _lexem(klient, s["id"], "μικρός")
    assert "uebersetzung_mehrdeutig" not in arten(klient, lexem["id"])


# ---------------------------------------------------- Gleichlauter (Punkt 9)

def test_gleichlautende_formen_werden_gemeldet_nicht_abgelehnt(klient):
    """φορά ist »das Mal« und »er trägt«. Beide Wörter bleiben bestehen."""
    _b, s = _aufbau(klient)
    bericht = importieren(klient, s["id"], [
        {"lemma": "η φορά", "wortart": "substantiv", "merkmale": {"genus": "f"},
         "bedeutungen": [{"uebersetzungen": ["das Mal", "die Wendung"]}],
         "formen": [{"text": "φορά", "merkmale": {
             "kasus": "nom", "numerus": "sg"}}]},
        {"lemma": "φοράω", "wortart": "verb",
         "bedeutungen": [{"uebersetzungen": ["tragen", "anziehen"]}],
         "formen": [{"text": "φορά", "merkmale": {
             "modus": "indikativ", "tempus": "praesens",
             "person": "3", "numerus": "sg"}}]}])
    assert bericht["angelegt"] == 2 and bericht["abgelehnt"] == 0
    lexem = _lexem(klient, s["id"], "φοράω")
    befunde = klient.get(f"/api/lexeme/{lexem['id']}/pruefung").json()["befunde"]
    notiz = next(b for b in befunde if b["art"] == "gleichlauter")
    assert notiz["schwere"] == "notiz"
    assert "φορά" in notiz["text"]
    # Beide bleiben abfragbar und beide werden gefunden.
    gefunden = klient.get(f"/api/sammlungen/{s['id']}/woerterbuch",
                          params={"suche": "φορά"}).json()
    assert {e["lemma"] for e in gefunden["eintraege"]} == {"η φορά", "φοράω"}


# ------------------------------------------- Weitere Wortarten (Punkt 9)

def test_pronomen_artikel_und_zahlwoerter_haben_formen(klient):
    """αυτός/αυτή/αυτό, ο/η/το, ένας/μία/ένα sind Paradigmen. Ohne eigene
    Gruppen fielen sie in keine Tabelle."""
    _b, s = _aufbau(klient)
    bericht = importieren(klient, s["id"], [
        {"lemma": "αυτός", "wortart": "pronomen",
         "bedeutungen": [{"uebersetzungen": ["dieser", "er"]}],
         "formen": [{"text": t, "merkmale": {
             "genus": g, "kasus": "nom", "numerus": "sg"}}
             for t, g in (("αυτός", "m"), ("αυτή", "f"), ("αυτό", "n"))]},
        {"lemma": "ένας", "wortart": "numerale",
         "bedeutungen": [{"uebersetzungen": ["eins", "ein"]}],
         "formen": [{"text": t, "merkmale": {
             "genus": g, "kasus": "nom", "numerus": "sg"}}
             for t, g in (("ένας", "m"), ("μία", "f"), ("ένα", "n"))]}])
    assert bericht["angelegt"] == 2
    for lemma in ("αυτός", "ένας"):
        lexem = _lexem(klient, s["id"], lemma)
        assert "ausserhalb_der_formgruppen" not in arten(klient, lexem["id"])
        voll = klient.get(f"/api/lexeme/{lexem['id']}").json()
        # Jede Form sitzt in einer Formgruppe — das ist der Punkt.
        assert all(f["gruppe"] for f in voll["formen"]), lemma
        assert {f["gruppe"] for f in voll["formen"]} == {
            f"{'pron' if lemma == 'αυτός' else 'num'}_{g}"
            for g in ("m", "f", "n")}
        # Abgefragt werden sie nach der Freigabe, wie alle Formen.
        klient.post(f"/api/sammlungen/{s['id']}/freigabe",
                    json={"lexem_ids": [lexem["id"]]})
        danach = klient.get(f"/api/lexeme/{lexem['id']}").json()
        assert sum(1 for a in danach["aufgaben"] if a["aktiv"]) > sum(
            1 for a in voll["aufgaben"] if a["aktiv"]), lemma


def test_wendungen_und_adverbien_melden_keine_fehlenden_formen(klient):
    """Für sie gibt es keine Formgruppen — »ohne Formen« wäre kein Mangel,
    sondern die Wahrheit."""
    _b, s = _aufbau(klient)
    importieren(klient, s["id"], [
        {"lemma": "καλημέρα", "wortart": "wendung",
         "bedeutungen": [{"uebersetzungen": ["guten Morgen", "guten Tag"]}]},
        {"lemma": "αύριο", "wortart": "adverb",
         "bedeutungen": [{"uebersetzungen": ["morgen", "künftig"]}]}])
    for lemma in ("καλημέρα", "αύριο"):
        lexem = _lexem(klient, s["id"], lemma)
        assert "ohne_formen" not in arten(klient, lexem["id"]), lemma


# ------------------------------------------------------ Lernstand (Punkt 10)

def test_lernstand_nennt_die_schwachen_woerter(klient):
    """Daraus kann die KI gezielt Sätze mit genau diesen Wörtern schreiben."""
    b, s = _aufbau(klient)
    importieren(klient, s["id"], KLEIN)
    schwach = _lexem(klient, s["id"], "κοντός")
    aufgabe = _bedeutungsaufgabe(klient, schwach["id"])
    for _ in range(4):
        klient.post("/api/lernen/bewerten", json={
            "benutzer_id": b["id"], "aufgabe_id": aufgabe["id"],
            "bewertung": 1})

    stand = klient.get(f"/api/sammlungen/{s['id']}/lernstand",
                       params={"benutzer_id": b["id"]}).json()
    assert stand["woerter_gesamt"] == 2
    assert stand["geuebt"] == 1 and stand["nie_geuebt"] == 1
    assert [w["lemma"] for w in stand["schwach"]] == ["κοντός"]
    assert stand["schwach"][0]["fehleranteil"] == 1.0
    assert stand["schwach"][0]["versuche"] == 4


def test_ein_einzelner_fehler_macht_noch_kein_schwaches_wort(klient):
    """Sonst stünde nach dem ersten Lerntag der halbe Bestand auf der
    Liste, und die Liste wäre wertlos."""
    b, s = _aufbau(klient)
    importieren(klient, s["id"], KLEIN)
    aufgabe = _bedeutungsaufgabe(
        klient, _lexem(klient, s["id"], "κοντός")["id"])
    klient.post("/api/lernen/bewerten", json={
        "benutzer_id": b["id"], "aufgabe_id": aufgabe["id"], "bewertung": 1})
    stand = klient.get(f"/api/sammlungen/{s['id']}/lernstand",
                       params={"benutzer_id": b["id"]}).json()
    assert stand["schwach"] == []


def test_lernstand_ueber_den_mcp_gilt_der_sprechenden_person(klient):
    """Ein Lernstand ist an die Person gebunden — der eines anderen geht
    niemanden etwas an."""
    from test_mcp import person_mit_token, werkzeug
    mcp = person_mit_token(klient, "Verwalterin")
    s = klient.post("/api/sammlungen", json={
        "besitzer_id": mcp.benutzer["id"], "name": "Griechisch",
        "sprache": "el"}).json()
    importieren(klient, s["id"], KLEIN)
    stand = werkzeug(mcp, "lernstand_lesen", sammlung_id=s["id"])
    assert stand["benutzer_id"] == mcp.benutzer["id"]
    assert stand["woerter_gesamt"] == 2 and stand["nie_geuebt"] == 2

    andere = person_mit_token(klient, "Fremde")
    assert werkzeug(andere, "lernstand_lesen",
                    sammlung_id=s["id"]).get("_werkzeugfehler")
