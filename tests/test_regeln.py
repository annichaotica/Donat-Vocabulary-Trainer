"""Grammatikregeln — das »Warum ist das so?« an der Frage.

Der Wunsch kam aus dem Französischkurs von Duolingo: dort lässt sich zu
jeder Aufgabe nachlesen, welche Regel gerade greift.

Gefunden wird eine Regel über ihr MUSTER, nicht über eine Zuordnung zu
einzelnen Wörtern — sonst müsste jemand jede Regel an jedes Wort hängen,
und bei einem neuen Wort fehlte sie wieder. Diese Tests gehen den ganzen
Weg: eintragen, freigeben, und bei der richtigen Frage erscheinen.
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
            "formen": [
                {"text": "γράφω", "merkmale": {
                    "modus": "indikativ", "tempus": "praesens",
                    "person": "1", "numerus": "sg"}},
                {"text": "έγραψα", "merkmale": {
                    "modus": "indikativ", "tempus": "aorist",
                    "person": "1", "numerus": "sg"}},
            ]}]})
    klient.post(f"/api/sammlungen/{s['id']}/freigabe", json={"lektion_nr": 1})
    return b, s


def _regel(klient, s, **felder):
    felder.setdefault("titel", "Aorist: der einmalige Vorgang")
    felder.setdefault("text", "Der Aorist erzählt, was einmal geschah "
                              "und vorbei ist.")
    antwort = klient.post(f"/api/sammlungen/{s['id']}/regeln", json=felder)
    assert antwort.status_code == 201, antwort.text
    return antwort.json()


def _fragen(klient, b, s):
    return klient.get("/api/lernen/naechste", params={
        "benutzer_id": b["id"], "sammlung_id": s["id"], "anzahl": 20,
        "nur": "frei"}).json()


def _zu_form(fragen, text):
    for f in fragen:
        if f["typ"] == "form_bilden" and f.get("vorlesen") == text:
            return f
    for f in fragen:
        if f["typ"] == "form_bilden":
            return f
    raise AssertionError("keine Formaufgabe")


# ------------------------------------------------------ Eintragen

def test_eine_neue_regel_ist_ungeprueft(bestand, klient):
    """Wie eine eingetragene Vokabel: erst ansehen, dann zeigen."""
    b, s = bestand
    r = _regel(klient, s, muster={"merkmale": {"tempus": "aorist"}})
    assert r["geprueft"] is False


def test_die_kennung_berichtigt_statt_zu_verdoppeln(bestand, klient):
    b, s = bestand
    erst = _regel(klient, s, kennung="aorist", text="Erste Fassung.")
    wieder = _regel(klient, s, kennung="aorist", text="Zweite Fassung.")
    assert wieder["id"] == erst["id"]
    assert wieder["text"] == "Zweite Fassung."
    assert len(klient.get(f"/api/sammlungen/{s['id']}/regeln").json()) == 1


def test_ein_tippfehler_im_muster_wird_abgewiesen(bestand, klient):
    """Sonst wird die Regel angelegt, gilt als geprüft — und erscheint
    nie, ohne dass jemand erführe, warum."""
    b, s = bestand
    antwort = klient.post(f"/api/sammlungen/{s['id']}/regeln", json={
        "titel": "x", "text": "y", "muster": {"merkmale": {"tempuss": "aorist"}}})
    assert antwort.status_code == 400
    assert "tempuss" in antwort.json()["detail"]

    antwort = klient.post(f"/api/sammlungen/{s['id']}/regeln", json={
        "titel": "x", "text": "y", "muster": {"wortart": "verbb"}})
    assert antwort.status_code == 400


# ---------------------------------------------- Bei der Frage erscheinen

def test_ungepruefte_regeln_erscheinen_nicht(bestand, klient):
    b, s = bestand
    _regel(klient, s, muster={"merkmale": {"tempus": "aorist"}})
    for f in _fragen(klient, b, s):
        assert f.get("regeln") == [], f["typ"]


def test_die_freigegebene_regel_steht_an_der_passenden_frage(bestand, klient):
    b, s = bestand
    r = _regel(klient, s, muster={"merkmale": {"tempus": "aorist"}})
    klient.post(f"/api/regeln/{r['id']}/freigabe")

    fragen = _fragen(klient, b, s)
    mit = [f for f in fragen if f.get("regeln")]
    assert mit, "die Regel erscheint nirgends"
    for f in mit:
        assert f["regeln"][0]["titel"].startswith("Aorist")


def test_sie_steht_nicht_an_der_unpassenden_frage(bestand, klient):
    """Eine Aoristregel hat beim Präsens nichts zu suchen."""
    b, s = bestand
    r = _regel(klient, s, muster={"merkmale": {"tempus": "aorist"}})
    klient.post(f"/api/regeln/{r['id']}/freigabe")

    import datenbank as dbm
    db = dbm.verbindung()
    try:
        praesens = dbm.wert(db, """SELECT a.id FROM aufgabe a
                                     JOIN form f ON f.id = a.ziel_id
                                    WHERE a.ziel_art = 'form'
                                      AND f.text = 'γράφω'""")
        import regeln
        assert regeln.fuer_aufgabe(db, praesens) == []
        aorist = dbm.wert(db, """SELECT a.id FROM aufgabe a
                                   JOIN form f ON f.id = a.ziel_id
                                  WHERE a.ziel_art = 'form'
                                    AND f.text = 'έγραψα'""")
        assert len(regeln.fuer_aufgabe(db, aorist)) == 1
    finally:
        db.close()


def test_die_engste_regel_steht_vorn(bestand, klient):
    """Drei Regeln, von allgemein bis genau — die genaueste zuerst."""
    b, s = bestand
    for titel, muster in (
            ("Ganz allgemein", {}),
            ("Zu Verben", {"wortart": "verb"}),
            ("Zum Aorist", {"wortart": "verb",
                            "merkmale": {"tempus": "aorist"}})):
        r = _regel(klient, s, titel=titel, text=titel, muster=muster,
                   kennung=titel)
        klient.post(f"/api/regeln/{r['id']}/freigabe")

    import datenbank as dbm, regeln
    db = dbm.verbindung()
    try:
        aorist = dbm.wert(db, """SELECT a.id FROM aufgabe a
                                   JOIN form f ON f.id = a.ziel_id
                                  WHERE a.ziel_art = 'form'
                                    AND f.text = 'έγραψα'""")
        titel = [r["titel"] for r in regeln.fuer_aufgabe(db, aorist)]
    finally:
        db.close()
    assert titel == ["Zum Aorist", "Zu Verben", "Ganz allgemein"]


def test_eine_aktivregel_trifft_die_aktivform(bestand, klient):
    """Gespeichert wird eine Aktivform OHNE genus_verbi, eine Regel zum
    Aktiv nennt es aber. Ohne Normieren der Aufgabenmerkmale träfe sie
    nie — und niemand käme darauf, warum."""
    b, s = bestand
    r = _regel(klient, s, titel="Aktiv",
               muster={"wortart": "verb", "merkmale": {"genus_verbi": "aktiv"}})
    klient.post(f"/api/regeln/{r['id']}/freigabe")

    import datenbank as dbm, regeln
    db = dbm.verbindung()
    try:
        aorist = dbm.wert(db, """SELECT a.id FROM aufgabe a
                                   JOIN form f ON f.id = a.ziel_id
                                  WHERE a.ziel_art = 'form'
                                    AND f.text = 'έγραψα'""")
        assert [x["titel"] for x in regeln.fuer_aufgabe(db, aorist)] == ["Aktiv"]
    finally:
        db.close()


# --------------------------------------------------------- Änderungen

def test_eine_geaenderte_regel_muss_neu_freigegeben_werden(bestand, klient):
    b, s = bestand
    r = _regel(klient, s)
    klient.post(f"/api/regeln/{r['id']}/freigabe")
    assert klient.get(f"/api/regeln/{r['id']}").json()["geprueft"] is True

    klient.patch(f"/api/regeln/{r['id']}", json={"text": "Ganz anders."})
    assert klient.get(f"/api/regeln/{r['id']}").json()["geprueft"] is False


def test_die_reihenfolge_zu_verschieben_hebt_die_freigabe_nicht_auf(
        bestand, klient):
    """Sonst gäbe man dauernd dasselbe wieder frei."""
    b, s = bestand
    r = _regel(klient, s)
    klient.post(f"/api/regeln/{r['id']}/freigabe")
    klient.patch(f"/api/regeln/{r['id']}", json={"reihenfolge": 5})
    assert klient.get(f"/api/regeln/{r['id']}").json()["geprueft"] is True


def test_eine_regel_laesst_sich_loeschen(bestand, klient):
    b, s = bestand
    r = _regel(klient, s)
    assert klient.delete(f"/api/regeln/{r['id']}").status_code == 204
    assert klient.get(f"/api/regeln/{r['id']}").status_code == 404
