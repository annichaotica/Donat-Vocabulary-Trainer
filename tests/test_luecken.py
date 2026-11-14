"""Erklärte Lücken, Varianten, gemeinsames Genus, überschriebener Stamm.

Griechische Paradigmen sind von Natur aus oft unvollständig oder doppelt
besetzt. Ohne diese vier Dinge meldete der Trainer bei jedem dritten Wort
einen Mangel, den es nicht gibt.
"""


def _aufbau(klient, sprache="el"):
    b = klient.post("/api/benutzer", json={"name": "Lückentester"}).json()
    s = klient.post("/api/sammlungen", json={
        "besitzer_id": b["id"], "name": "Griechisch", "sprache": sprache}).json()
    return b, s


def importieren(klient, sammlung_id, eintraege, **kw):
    return klient.post(f"/api/sammlungen/{sammlung_id}/import/vokabeln",
                       json={"eintraege": eintraege, **kw}).json()


def befunde(ergebnis, nr=0):
    if not ergebnis["eintraege"]:
        return set()
    return {b["art"] for b in ergebnis["eintraege"][nr].get("befunde", [])}


# ----------------------------------------------------- Unpersönliche Verben

def test_unpersoenliches_verb_meldet_keine_fehlenden_personen(klient):
    """πρέπει gibt es nur in der 3. Person. Das ist eine Eigenschaft des
    Wortes, kein Mangel."""
    _b, s = _aufbau(klient)
    ohne = importieren(klient, s["id"], [{
        "lemma": "πρέπει", "wortart": "verb",
        "bedeutungen": [{"uebersetzungen": ["müssen", "sollen"]}],
        "formen": [{"text": "πρέπει", "merkmale": {
            "modus": "indikativ", "tempus": "praesens",
            "person": "3", "numerus": "sg"}}]}])
    assert "paradigma_lueckig" in befunde(ohne)

    mit = importieren(klient, s["id"], [{
        "lemma": "πρέπει", "wortart": "verb",
        "luecken": [{"person": "1"}, {"person": "2"},
                    {"person": "3", "numerus": "pl"}],
        "bedeutungen": [{"uebersetzungen": ["müssen", "sollen"]}],
        "formen": [{"text": "πρέπει", "merkmale": {
            "modus": "indikativ", "tempus": "praesens",
            "person": "3", "numerus": "sg"}}]}])
    assert "paradigma_lueckig" not in befunde(mit)


def test_verb_ohne_aorist(klient):
    """είμαι hat keinen Aorist — seine Vergangenheit steht im Imperfekt."""
    _b, s = _aufbau(klient)
    ergebnis = importieren(klient, s["id"], [{
        "lemma": "είμαι", "wortart": "verb",
        "luecken": [{"tempus": "aorist"}],
        "bedeutungen": [{"uebersetzungen": ["sein"]}],
        "formen": [{"text": t, "merkmale": {
            "modus": "indikativ", "tempus": "praesens",
            "person": p, "numerus": n}}
            for t, (p, n) in zip(["είμαι", "είσαι", "είναι",
                                  "είμαστε", "είστε", "είναι"],
                                 [("1", "sg"), ("2", "sg"), ("3", "sg"),
                                  ("1", "pl"), ("2", "pl"), ("3", "pl")])]}])
    # Der Aorist steht nicht in der Standardauswahl, aber auch sonst nirgends
    # als Mangel
    assert "paradigma_lueckig" not in befunde(ergebnis)


def test_nur_im_plural(klient):
    """τα μεσάνυχτα gibt es nicht im Singular."""
    _b, s = _aufbau(klient)
    ergebnis = importieren(klient, s["id"], [{
        "lemma": "τα μεσάνυχτα", "wortart": "substantiv",
        "merkmale": {"genus": "n"},
        "luecken": [{"numerus": "sg"}],
        "bedeutungen": [{"uebersetzungen": ["Mitternacht"]}],
        "formen": [{"text": "μεσάνυχτα", "merkmale": {"kasus": "nom",
                                                      "numerus": "pl"}},
                   {"text": "μεσανύχτων", "merkmale": {"kasus": "gen",
                                                       "numerus": "pl"}},
                   {"text": "μεσάνυχτα", "merkmale": {"kasus": "akk",
                                                      "numerus": "pl"}}]}])
    assert "paradigma_lueckig" not in befunde(ergebnis)


def test_unveraenderliches_wort(klient):
    """το ταξί und μπλε haben überhaupt keine Formen. Das leere Muster
    sagt genau das."""
    _b, s = _aufbau(klient)
    ergebnis = importieren(klient, s["id"], [{
        "lemma": "το ταξί", "wortart": "substantiv",
        "merkmale": {"genus": "n"}, "luecken": [{}],
        "bedeutungen": [{"uebersetzungen": ["das Taxi"]}]}])
    assert "ohne_formen" not in befunde(ergebnis)
    assert "paradigma_lueckig" not in befunde(ergebnis)


def test_unbrauchbares_lueckenmuster_wird_abgewiesen(klient):
    _b, s = _aufbau(klient)
    ergebnis = importieren(klient, s["id"], [{
        "lemma": "x", "wortart": "verb",
        "luecken": [{"tempus": "erfunden"}],
        "bedeutungen": [{"uebersetzungen": ["y"]}]}])
    assert ergebnis["abgelehnt"] == 1
    assert "luecken" in " ".join(ergebnis["eintraege"][0]["befunde"])


# -------------------------------------------------------------- Varianten

def test_nebenformen_gelten_beide(klient):
    """μιλάω und μιλώ sind dieselbe Zelle, beide richtig."""
    b, s = _aufbau(klient)
    importieren(klient, s["id"], [{
        "lemma": "μιλάω", "wortart": "verb",
        "bedeutungen": [{"uebersetzungen": ["sprechen"]}],
        "formen": [{"text": "μιλάω", "varianten": ["μιλώ"],
                    "merkmale": {"modus": "indikativ", "tempus": "praesens",
                                 "person": "1", "numerus": "sg"},
                    "geprueft": True}]}])
    lex = klient.get(f"/api/sammlungen/{s['id']}/lexeme").json()["lexeme"][0]
    voll = klient.get(f"/api/lexeme/{lex['id']}").json()
    assert len(voll["formen"]) == 2
    aufgabe = next(a for a in voll["aufgaben"]
                   if a["typ"] == "form_bilden" and a["aktiv"])
    for antwort in ("μιλάω", "μιλώ"):
        ergebnis = klient.post("/api/lernen/pruefen", json={
            "benutzer_id": b["id"], "aufgabe_id": aufgabe["id"],
            "antwort": antwort}).json()
        assert ergebnis["urteil"]["urteil"] == "richtig", antwort


def test_varianten_verderben_den_stamm_nicht(klient):
    """μιλάω und μιλώ hätten gemeinsam nur »μιλ« — der wirkliche Stamm
    der Präsensreihe ist länger."""
    b, s = _aufbau(klient)
    klient.put(f"/api/benutzer/{b['id']}/legasthenie", json={"aktiv": True})
    P = [("1", "sg"), ("2", "sg"), ("3", "sg"), ("1", "pl"), ("2", "pl"), ("3", "pl")]
    importieren(klient, s["id"], [{
        "lemma": "μιλάω", "wortart": "verb",
        "bedeutungen": [{"uebersetzungen": ["sprechen"]}],
        "formen": [{"text": t, "geprueft": True,
                    "varianten": (["μιλώ"] if t == "μιλάω" else []),
                    "merkmale": {"modus": "indikativ", "tempus": "praesens",
                                 "person": p, "numerus": n}}
                   for t, (p, n) in zip(["μιλάω", "μιλάς", "μιλάει",
                                         "μιλάμε", "μιλάτε", "μιλάνε"], P)]}])
    lex = klient.get(f"/api/sammlungen/{s['id']}/lexeme").json()["lexeme"][0]
    voll = klient.get(f"/api/lexeme/{lex['id']}").json()
    form = next(f for f in voll["formen"] if f["text"] == "μιλάτε")
    aufgabe = next(a for a in voll["aufgaben"]
                   if a["typ"] == "form_bilden" and a["ziel_id"] == form["id"])
    gezeigt = klient.post("/api/lernen/aufdecken", json={
        "benutzer_id": b["id"], "aufgabe_id": aufgabe["id"]}).json()
    assert gezeigt["zerlegung"]["stamm"] == "μιλά"


# ------------------------------------------------------- Gemeinsames Genus

def test_gemeinsames_genus_nimmt_beide_artikel(klient):
    """ο/η γιατρός — welcher Artikel richtig ist, hängt davon ab, wen man
    meint. Beide gelten."""
    b, s = _aufbau(klient)
    importieren(klient, s["id"], [{
        "lemma": "γιατρός", "wortart": "substantiv",
        "merkmale": {"genus": "mf"},
        "bedeutungen": [{"uebersetzungen": ["Arzt", "Ärztin"]}]}])
    lex = klient.get(f"/api/sammlungen/{s['id']}/lexeme").json()["lexeme"][0]
    voll = klient.get(f"/api/lexeme/{lex['id']}").json()
    aufgabe = next(a for a in voll["aufgaben"] if a["typ"] == "genus")
    for antwort in ("ο", "η"):
        ergebnis = klient.post("/api/lernen/pruefen", json={
            "benutzer_id": b["id"], "aufgabe_id": aufgabe["id"],
            "antwort": antwort}).json()
        assert ergebnis["urteil"]["urteil"] == "richtig", antwort
    falsch = klient.post("/api/lernen/pruefen", json={
        "benutzer_id": b["id"], "aufgabe_id": aufgabe["id"],
        "antwort": "το"}).json()
    assert falsch["urteil"]["urteil"] == "falsch"
    assert "gemeinsames Geschlecht" in falsch["urteil"]["hinweis"]


# --------------------------------------------------------- Stamm von Hand

def test_stamm_laesst_sich_ueberschreiben(klient):
    """Wo die Ableitung nicht trägt, setzt man ihn selbst."""
    b, s = _aufbau(klient)
    klient.put(f"/api/benutzer/{b['id']}/legasthenie", json={"aktiv": True})
    importieren(klient, s["id"], [{
        "lemma": "τρώω", "wortart": "verb",
        "staemme": {"*": "ΗANDGESETZT"},
        "bedeutungen": [{"uebersetzungen": ["essen"]}],
        "formen": [{"text": "τρώω", "geprueft": True,
                    "merkmale": {"modus": "indikativ", "tempus": "praesens",
                                 "person": "1", "numerus": "sg"}},
                   {"text": "τρως", "geprueft": True,
                    "merkmale": {"modus": "indikativ", "tempus": "praesens",
                                 "person": "2", "numerus": "sg"}}]}])
    lex = klient.get(f"/api/sammlungen/{s['id']}/lexeme").json()["lexeme"][0]
    voll = klient.get(f"/api/lexeme/{lex['id']}").json()
    aufgabe = next(a for a in voll["aufgaben"]
                   if a["typ"] == "form_bilden" and a["aktiv"])
    gezeigt = klient.post("/api/lernen/aufdecken", json={
        "benutzer_id": b["id"], "aufgabe_id": aufgabe["id"]}).json()
    assert gezeigt["zerlegung"]["stamm"] == "ΗANDGESETZT"
