"""Die Statistik muss nach ZWEI Tagen etwas sagen — und dasselbe wie
die Übersicht.

»Und eine Statistik zu meinem Lernfortschritt, das braucht es
natürlich auch.«

Zwei Anforderungen tragen diese Datei. Die erste ist der Zuschnitt:
beim Bauen standen 101 Antworten an zwei Tagen im Protokoll. Eine
Statistik, die erst nach einem halben Jahr aufwacht, sieht man einmal
an und nie wieder.

Die zweite ist die Übereinstimmung. Der erste Entwurf zählte einfach
alle aktiven Aufgaben und kam auf 11351 statt der 7389, die die
Übersicht nennt — darin lagen fremde Sammlungen und Zeitformen, die
die Lektionsschranke zurückhält. Zwei verschiedene Zahlen für dasselbe
im selben Werkzeug sind schlimmer als eine unbequeme: man weiß dann
bei keiner mehr, was sie bedeutet.
"""

import pytest


@pytest.fixture()
def gelernt(klient):
    b = klient.post("/api/benutzer", json={"name": "Lernender 1"}).json()
    klient.patch(f"/api/benutzer/{b['id']}", json={"fragen_je_tag": 0})
    s = klient.post("/api/sammlungen", json={
        "besitzer_id": b["id"], "name": "Griechisch", "sprache": "el"}).json()
    klient.post(f"/api/sammlungen/{s['id']}/import/vokabeln", json={
        "eintraege": [{"lemma": f"λέξη{i}", "wortart": "substantiv",
                       "lektion_nr": 1, "reihenfolge": i,
                       "bedeutungen": [{"uebersetzungen": [f"Wort {i}"]}]}
                      for i in range(8)]
        # Ein Verb mit Form, damit es überhaupt eine Formgruppe gibt.
        # Ohne sie übersprang sich der Test zur Lektionsschranke selbst
        # — und ein übersprungener Test schützt nichts.
        + [{"lemma": "γράφω", "wortart": "verb", "lektion_nr": 1,
            "bedeutungen": [{"uebersetzungen": ["schreiben"]}],
            "formen": [{"text": "γράφεις", "merkmale": {
                "modus": "indikativ", "tempus": "praesens",
                "person": "2", "numerus": "sg"}}]}]})
    klient.post(f"/api/sammlungen/{s['id']}/freigabe", json={"lektion_nr": 1})
    # Fünf Antworten, davon eine daneben.
    liste = klient.get("/api/lernen/naechste", params={
        "benutzer_id": b["id"], "sammlung_id": s["id"], "anzahl": 5}).json()
    for i, a in enumerate(liste):
        klient.post("/api/lernen/bewerten", json={
            "benutzer_id": b["id"], "aufgabe_id": a["aufgabe_id"],
            "bewertung": 1 if i == 0 else 4})
    return b, s


def _stat(klient, b, sammlung_id=None):
    frage = {"benutzer_id": b["id"]}
    if sammlung_id:
        frage["sammlung_id"] = sammlung_id
    antwort = klient.get("/api/statistik", params=frage)
    assert antwort.status_code == 200, antwort.text
    return antwort.json()


def test_nach_einem_tag_steht_schon_etwas_da(gelernt, klient):
    """Der Kern des Zuschnitts."""
    b, s = gelernt
    d = _stat(klient, b)
    assert d["gesamt"]["antworten"] == 5
    assert d["gesamt"]["aktive_tage"] == 1
    assert d["gesamt"]["straehne"] == 1
    assert d["gesamt"]["quote"] is not None


def test_ohne_antworten_wird_keine_quote_erfunden(klient):
    """0 % wäre gelogen — niemand hat etwas falsch gemacht."""
    b = klient.post("/api/benutzer", json={"name": "Neu"}).json()
    d = _stat(klient, b)
    assert d["gesamt"]["antworten"] == 0
    assert d["gesamt"]["quote"] is None


def test_die_summe_stimmt_mit_der_uebersicht_ueberein(gelernt, klient):
    """Der Fehler aus dem ersten Entwurf."""
    b, s = gelernt
    d = _stat(klient, b)
    stand = klient.get("/api/lernen/stand",
                       params={"benutzer_id": b["id"]}).json()
    assert sum(d["wortschatz"].values()) == stand["gesamt"]


def test_fremde_sammlungen_zaehlen_nicht_mit(gelernt, klient):
    """Eine Sammlung, die man nur mitpflegt, gehört nicht in den
    eigenen Fortschritt."""
    b, s = gelernt
    andere = klient.post("/api/benutzer", json={"name": "Lernender 2"}).json()
    fremd = klient.post("/api/sammlungen", json={
        "besitzer_id": andere["id"], "name": "Französisch",
        "sprache": "fr"}).json()
    klient.post(f"/api/sammlungen/{fremd['id']}/import/vokabeln", json={
        "eintraege": [{"lemma": "le pain", "wortart": "substantiv",
                       "lektion_nr": 1,
                       "bedeutungen": [{"uebersetzungen": ["das Brot"]}]}]})
    klient.post(f"/api/sammlungen/{fremd['id']}/freigabe", json={"lektion_nr": 1})
    klient.put(f"/api/sammlungen/{fremd['id']}/zugriff", json={
        "benutzer_id": b["id"], "recht": "schreiben"})

    d = _stat(klient, b)
    stand = klient.get("/api/lernen/stand",
                       params={"benutzer_id": b["id"]}).json()
    assert sum(d["wortschatz"].values()) == stand["gesamt"]


def test_die_lektionsschranke_gilt_auch_hier(gelernt, klient):
    """Sonst stünde im Fortschritt eine Zahl, die das Lernen nie
    einlöst — derselbe Fehler wie damals beim Tagespensum."""
    b, s = gelernt
    vorher = sum(_stat(klient, b)["wortschatz"].values())
    import datenbank as dbm
    db = dbm.verbindung()
    try:
        gruppe = dbm.wert(db, """SELECT formgruppe FROM aufgabe
                                  WHERE formgruppe IS NOT NULL LIMIT 1""")
    finally:
        db.close()
    assert gruppe is not None, "die Vorrichtung bringt keine Formaufgabe mit"
    klient.put(f"/api/sammlungen/{s['id']}/lehrgang",
               json={"zuordnung": {gruppe: 99}})
    klient.put(f"/api/sammlungen/{s['id']}/buchstand",
               json={"benutzer_id": b["id"], "bis_lektion": 1})
    nachher = sum(_stat(klient, b)["wortschatz"].values())
    assert nachher < vorher


def test_die_taetigkeit_hat_keine_luecken(gelernt, klient):
    """Tage ohne Antwort stehen mit Null da. Ohne sie zöge ein
    Balkenbild die Pausen zusammen, und drei Tage Arbeit mit einer
    Woche Pause sähen aus wie drei Tage am Stück."""
    b, s = gelernt
    d = _stat(klient, b)
    assert len(d["taetigkeit"]) == d["gesamt"]["tage_betrachtet"]
    tage = [t["tag"] for t in d["taetigkeit"]]
    assert tage == sorted(tage)
    import datetime as dt
    erster = dt.date.fromisoformat(tage[0])
    letzter = dt.date.fromisoformat(tage[-1])
    assert (letzter - erster).days == len(tage) - 1


def test_die_vorschau_trennt_ueberfaelliges_von_der_zukunft(gelernt, klient):
    """Überfälliges ist Rückstand, keine Vorhersage — es kommt heute."""
    b, s = gelernt
    d = _stat(klient, b)
    assert d["vorschau"][0]["beschriftung"] == "überfällig"
    assert d["vorschau"][0]["tag"] is None
    assert d["vorschau"][1]["beschriftung"] == "heute"
    assert sum(v["n"] for v in d["vorschau"]) > 0, "nichts terminiert"


def test_das_tempo_schliesst_ausreisser_aus(gelernt, klient):
    """Dieselbe Spanne wie bei der Bewertung — was dort nicht zählt,
    darf hier den Median nicht verschieben."""
    b, s = gelernt
    import datenbank as dbm
    db = dbm.verbindung()
    try:
        db.execute("""UPDATE wiederholung SET denkzeit_ms = 999999
                       WHERE benutzer_id = ?""", (b["id"],))
        db.commit()
    finally:
        db.close()
    d = _stat(klient, b)
    assert d["tempo"] == [], (
        "ein Ausreißer von 999 Sekunden steht im Tempo-Bild")


def test_eine_einzelne_sammlung_laesst_sich_ansehen(gelernt, klient):
    b, s = gelernt
    d = _stat(klient, b, s["id"])
    assert d["gesamt"]["antworten"] == 5
