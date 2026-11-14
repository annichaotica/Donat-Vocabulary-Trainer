"""Der Tagesvorrat an Wörtern darf die Sitzung nicht vorzeitig beenden.

Aus einer Durchsicht am 14.11.2026, nachgemessen: eine frische Sammlung
gab genau `neu_je_sitzung` Fragen her und war dann leer — während die
Übersicht ein Vielfaches anzeigte.

Das ist zum dritten Mal derselbe Fehler, und darum steht er hier als
eigene Datei: **in einem kleinen Fenster nachträglich zu filtern geht
schief, wenn die Sortierung gerade das nach vorn holt, was der Filter
wegwirft.** Das Abrufen holt `anzahl * 4` Zeilen, bei einer Frage auf
einmal also vier. Die Sortierung stellt im Neuen die Wörter nach vorn,
von denen noch am wenigsten dran war; der Vorratsfilter lässt aber genau
die nicht mehr durch, sobald das Tagespensum an Wörtern voll ist. Dann
enthalten alle vier geholten Zeilen nur Verbotenes, und übrig bleibt
nichts — obwohl von den angefangenen Wörtern noch massenweise Formen
offen sind.

Die Lösung ist dieselbe wie beim Einstreuen und beim Vorzug: die
Bedingung gehört in die Abfrage, nicht hinterher ins Sieb.
"""

P = [("1", "sg"), ("2", "sg"), ("3", "sg")]
ENDUNGEN = ["ω", "εις", "ει"]
VERBEN = [("γράφ", "schreiben"), ("διαβάζ", "lesen"), ("παίζ", "spielen"),
          ("τρέχ", "laufen"), ("μιλ", "sprechen"), ("ακού", "hören")]


def _bestand(klient, verben=VERBEN, benutzer=None, name="Griechisch"):
    b = benutzer or klient.post("/api/benutzer",
                                json={"name": "Übende"}).json()
    s = klient.post("/api/sammlungen", json={
        "besitzer_id": b["id"], "name": name, "sprache": "el"}).json()
    klient.post(f"/api/sammlungen/{s['id']}/import/vokabeln", json={
        "eintraege": [{
            "lemma": stamm + "ω", "wortart": "verb", "lektion_nr": 1,
            "reihenfolge": i,
            "bedeutungen": [{"uebersetzungen": [bed]}],
            "formen": [{"text": stamm + e, "merkmale": {
                "modus": "indikativ", "tempus": "praesens",
                "person": p, "numerus": n}}
                for e, (p, n) in zip(ENDUNGEN, P)]}
            for i, (stamm, bed) in enumerate(verben)]})
    klient.post(f"/api/sammlungen/{s['id']}/freigabe", json={"lektion_nr": 1})
    return b, s


def _sitzung(klient, b, s, runden=60):
    gestellt = []
    for _ in range(runden):
        liste = klient.get("/api/lernen/naechste", params={
            "benutzer_id": b["id"], "sammlung_id": s["id"], "anzahl": 1}).json()
        if not liste:
            break
        a = liste[0]
        gestellt.append(a)
        klient.post("/api/lernen/bewerten", json={
            "benutzer_id": b["id"], "aufgabe_id": a["aufgabe_id"],
            "bewertung": 3})
    return gestellt


def test_die_angefangenen_woerter_werden_zu_ende_gefragt(klient):
    """Drei Wörter am Tag heißt drei WÖRTER, nicht drei Fragen."""
    b, s = _bestand(klient)
    klient.patch(f"/api/benutzer/{b['id']}",
                 json={"neu_je_sitzung": 3, "fragen_je_tag": 0})

    gestellt = _sitzung(klient, b, s)
    woerter = {a["lexem_id"] for a in gestellt}

    assert len(woerter) == 3, f"Tagesvorrat nicht eingehalten: {len(woerter)}"
    # Jedes Wort bringt vier Aufgaben mit (drei Formen, eine Bedeutung
    # je Richtung) — jedenfalls deutlich mehr als eine.
    assert len(gestellt) >= 9, (
        f"nur {len(gestellt)} Fragen aus {len(woerter)} Wörtern — "
        "die angefangenen Wörter wurden nicht zu Ende gefragt")


def test_die_uebersicht_verspricht_nicht_mehr_als_kommt(klient):
    """»heute_offen« und das, was wirklich kommt, müssen zusammenpassen."""
    b, s = _bestand(klient)
    klient.patch(f"/api/benutzer/{b['id']}",
                 json={"neu_je_sitzung": 3, "fragen_je_tag": 0})

    stand = klient.get("/api/lernen/stand", params={
        "benutzer_id": b["id"], "sammlung_id": s["id"]}).json()
    versprochen = stand["heute_offen"]

    gekommen = len(_sitzung(klient, b, s))
    assert gekommen == versprochen, (
        f"angekündigt {versprochen}, bekommen {gekommen}")


def test_der_vorrat_zaehlt_je_sammlung_wie_die_uebersicht(klient):
    """stand() zählt die heute begonnenen Wörter je Sammlung, naechste()
    zählte sie über alle — dann war die zweite Sammlung still leer."""
    b, s_a = _bestand(klient)
    _, s_b = _bestand(klient, benutzer=b, name="Zweite",
                      verben=[("κλεί", "schließen"), ("ανοίγ", "öffnen"),
                              ("τρώ", "essen")])
    klient.patch(f"/api/benutzer/{b['id']}",
                 json={"neu_je_sitzung": 3, "fragen_je_tag": 0})

    _sitzung(klient, b, s_a)          # Sammlung A leerlernen
    stand = klient.get("/api/lernen/stand", params={
        "benutzer_id": b["id"], "sammlung_id": s_b["id"]}).json()
    gekommen = len(_sitzung(klient, b, s_b))

    assert (stand["heute_offen"] > 0) == (gekommen > 0), (
        f"Übersicht sagt {stand['heute_offen']} offen, "
        f"geliefert wurden {gekommen}")
