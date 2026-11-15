"""Die zwei Fragen, nach denen eine Mediävistikklausur wirklich fragt.

»Kann man auch Grammatik für Mittelhochdeutsch abfragen? Keine Ahnung,
wie man so was machen sollte.«

Die Grammatik war im Sprachprofil längst modelliert — die vier
Stammformen, die sieben Ablautreihen, die Deklinationsklassen. Nur
abfragen ließ sich beides nicht:

  Die STAMMFORMEN sind keine Formgruppe, sondern eine Auswahl quer
  durch mehrere, und jede davon hat nur eine Zelle. »Eine Zelle ist
  keine Reihe« — also fiel die Reihe durch das Raster, die man
  eigentlich auswendig lernt.

  Die ABLAUTREIHE steht als Lexemmerkmal am Verb, mit fester
  Werteliste. Abfragbar war davon nur das Geschlecht, und das fest
  verdrahtet als Artikel.
"""

import pytest

# nëmen – nam – nâmen – genomen, Ablautreihe IV.
STAMMFORMEN = [
    ("nëmen", {"nonfinit": "infinitiv"}),
    ("nam", {"modus": "indikativ", "tempus": "praeteritum",
             "person": "1", "numerus": "sg"}),
    ("nâmen", {"modus": "indikativ", "tempus": "praeteritum",
               "person": "1", "numerus": "pl"}),
    ("genomen", {"nonfinit": "partizip_perfekt"}),
]


def _aufbau(klient, typen, formen=STAMMFORMEN, merkmale=None):
    b = klient.post("/api/benutzer", json={"name": "Mediävistin"}).json()
    s = klient.post("/api/sammlungen", json={
        "besitzer_id": b["id"], "name": "Mittelhochdeutsch",
        "sprache": "gmh"}).json()
    klient.put(f"/api/sammlungen/{s['id']}/einstellungen", json={"typen": typen})
    a = klient.post(f"/api/sammlungen/{s['id']}/import/vokabeln", json={
        "eintraege": [{
            "lemma": "nëmen", "wortart": "verb",
            "merkmale": {"klasse": "stark IV"} if merkmale is None else merkmale,
            "bedeutungen": [{"uebersetzungen": ["nehmen"]}],
            "formen": [{"text": t, "merkmale": m} for t, m in formen]}]})
    assert a.status_code < 300, a.text
    klient.post(f"/api/sammlungen/{s['id']}/freigabe", json={"lexem_ids": [1]})
    return b, s


def _aufgabe(klient, b, s, typ):
    alle = klient.get("/api/lernen/naechste", params={
        "benutzer_id": b["id"], "sammlung_id": s["id"],
        "nur": "frei", "anzahl": 30}).json()
    return next((a for a in alle if a["typ"] == typ), None)


def pruefen(klient, b, aufgabe, antwort):
    a = klient.post("/api/lernen/pruefen", json={
        "benutzer_id": b["id"], "aufgabe_id": aufgabe["aufgabe_id"],
        "antwort": antwort})
    assert a.status_code == 200, a.text
    return a.json()


# --------------------------------------------------------- Stammformen

def test_die_vier_stammformen_sind_eine_aufgabe(klient):
    b, s = _aufbau(klient, ["stammformen"])
    a = _aufgabe(klient, b, s, "stammformen")
    assert a is not None, "die Stammformenreihe entsteht nicht"
    assert a["frage_text"] == "nëmen"
    assert a["eingabeart"] == "reihe"
    # Beschriftet mit dem Gruppennamen, nicht mit den Merkmalen der
    # Zelle: »1. Person Singular« stünde sonst zweimal da.
    assert [z["beschriftung"] for z in a["zellen"]] == [
        "Infinitiv", "Prät. Sg.", "Prät. Pl.", "Part. Prät."]


def test_die_reihe_sitzt_als_ganzes(klient):
    b, s = _aufbau(klient, ["stammformen"])
    a = _aufgabe(klient, b, s, "stammformen")
    zellen = [z["zelle"] for z in a["zellen"]]

    ganz = pruefen(klient, b, a, dict(zip(zellen, ["nëmen", "nam", "nâmen",
                                                   "genomen"])))
    assert ganz["urteil"]["urteil"] == "richtig"

    # Drei von vier ist die Reihe nicht. Das ist der Sinn der Reihe.
    # Geprüft wird hier nur verglichen, nicht fortgeschrieben — dieselbe
    # Aufgabe darf also ein zweites Mal beantwortet werden.
    teil = pruefen(klient, b, a, dict(zip(zellen, ["nëmen", "nam", "nâmen",
                                                   "gestolen"])))
    assert teil["urteil"]["urteil"] == "falsch"
    assert "3 von 4" in (teil["urteil"]["hinweis"] or "")


def test_laengenzeichen_sind_hinweis_kein_fehler(klient):
    """nam gegen nâmen ist Singular gegen Plural und damit bedeutsam —
    aber die Ausgaben setzen die Zeichen verschieden, und auf der
    Tastatur sind sie nicht. Darum Hinweis, keine Strafe. Das steht so
    im Sprachprofil und soll auch in der Reihe gelten."""
    b, s = _aufbau(klient, ["stammformen"])
    a = _aufgabe(klient, b, s, "stammformen")
    zellen = [z["zelle"] for z in a["zellen"]]
    e = pruefen(klient, b, a, dict(zip(zellen, ["nemen", "nam", "namen",
                                                "genomen"])))
    assert e["urteil"]["urteil"] == "fast", e["urteil"]


def test_ohne_vollstaendige_formen_keine_reihe(klient):
    """Eine halbe Tabelle abzufragen hieße, in Felder zu tippen, zu
    denen es keine Antwort gibt."""
    b, s = _aufbau(klient, ["stammformen"], formen=STAMMFORMEN[:2])
    assert _aufgabe(klient, b, s, "stammformen") is None


def test_die_reihe_wartet_auf_ihren_spaetesten_teil(klient):
    """Die Reihe enthält das Präteritum. Hinge sie an keiner Formgruppe,
    käme sie, bevor das Lehrwerk das Präteritum eingeführt hat — genau
    der Fehler, der beim griechischen Aorist schon passiert ist. Sie
    hängt darum an der LETZTEN beteiligten Gruppe."""
    import datenbank as dbm
    b, s = _aufbau(klient, ["stammformen"])
    db = dbm.verbindung()
    try:
        gruppe = dbm.wert(db, """SELECT formgruppe FROM aufgabe
                                  WHERE typ = 'stammformen'""")
    finally:
        db.close()
    assert gruppe == "partizip_praet", gruppe


# -------------------------------------------------------------- Klasse

def test_die_ablautreihe_laesst_sich_abfragen(klient):
    b, s = _aufbau(klient, ["klasse"])
    a = _aufgabe(klient, b, s, "klasse")
    assert a is not None, "die Klassenabfrage entsteht nicht"
    assert a["frage_text"] == "nëmen"
    assert a["eingabeart"] == "auswahl"
    # Nicht »Welche Klasse?«: in der Klausur heißt die Frage anders,
    # und wer sie nicht liest, sucht in der Auswahl nach etwas anderem.
    assert a["frage_zusatz"] == "Welche Ablautreihe?"
    werte = [w["wert"] for w in a["auswahl"]]
    assert "stark IV" in werte and "Präteritopräsens" in werte

    assert pruefen(klient, b, a, "stark IV")["urteil"]["urteil"] == "richtig"


def test_falsche_reihe_nennt_die_richtige(klient):
    b, s = _aufbau(klient, ["klasse"])
    a = _aufgabe(klient, b, s, "klasse")
    e = pruefen(klient, b, a, "stark II")
    assert e["urteil"]["urteil"] == "falsch"
    assert "stark IV" in (e["urteil"]["hinweis"] or "")


def test_ohne_eingetragene_klasse_keine_frage(klient):
    """Ein Verb ohne Ablautreihe ergäbe eine Frage ohne Antwort."""
    b, s = _aufbau(klient, ["klasse"], merkmale={})
    assert _aufgabe(klient, b, s, "klasse") is None


def test_das_geschlecht_bleibt_beim_artikel(klient):
    """Das Geschlecht hat seine eigene Aufgabe, weil es als ARTIKEL
    gefragt wird — »diu«, nicht »f«. Zwei Aufgaben für dieselbe Auskunft
    wären eine zu viel."""
    b = klient.post("/api/benutzer", json={"name": "Mediävistin"}).json()
    s = klient.post("/api/sammlungen", json={
        "besitzer_id": b["id"], "name": "Mittelhochdeutsch",
        "sprache": "gmh"}).json()
    klient.put(f"/api/sammlungen/{s['id']}/einstellungen",
               json={"typen": ["klasse", "genus"]})
    klient.post(f"/api/sammlungen/{s['id']}/import/vokabeln", json={
        "eintraege": [{
            "lemma": "vrouwe", "wortart": "substantiv",
            "merkmale": {"genus": "f", "klasse": "schwach n"},
            "bedeutungen": [{"uebersetzungen": ["Frau", "Herrin"]}]}]})
    klient.post(f"/api/sammlungen/{s['id']}/freigabe", json={"lexem_ids": [1]})
    alle = klient.get("/api/lernen/naechste", params={
        "benutzer_id": b["id"], "sammlung_id": s["id"],
        "nur": "frei", "anzahl": 30}).json()
    typen = [a["typ"] for a in alle]
    assert typen.count("genus") == 1
    assert typen.count("klasse") == 1
    klasse = next(a for a in alle if a["typ"] == "klasse")
    assert klasse["frage_zusatz"] == "Welche Deklinationsklasse?"
    assert "schwach n" in [w["wert"] for w in klasse["auswahl"]]
    # und das Geschlecht ist NICHT unter den Klassenwerten
    assert "f" not in [w["wert"] for w in klasse["auswahl"]]
