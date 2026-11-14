"""Der Aufgabenschlüssel muss die Normalform benutzen, sonst geht Lernstand weg.

Der Schlüssel ist ausdrücklich dafür da, dass eine Aufgabe dieselbe
bleibt, wenn sich an den Daten etwas ändert — nur so überlebt der
Lernstand eine Berichtigung. Er nennt deshalb das Merkmalsbündel und
nicht die Form-ID.

Er nannte es aber ROH. `mk.normieren()` ergänzt die unmarkierten
Merkmale: eine Aktivform wird ohne `genus_verbi` gespeichert, ist aber
`genus_verbi: aktiv`. Schrieb jemand das später ausdrücklich dazu — von
Hand, über den MCP oder durch einen zweiten Import —, änderte sich der
Schlüssel, obwohl sich an der Form nichts geändert hatte. Die alte
Aufgabe wurde abgeschaltet, eine neue angelegt, und der Lernstand hing
an der alten.

Drei Zeilen tiefer, bei der Formenreihe, stand `mk.schluessel(
mk.normieren(...))` — dieselbe Entscheidung, einmal richtig und einmal
falsch. Genau die Fehlerfamilie, die beim Import schon einmal 36
Dubletten erzeugt hätte.
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
            # Ohne genus_verbi — so kommt es aus jeder normalen Quelle.
            "formen": [{"text": "γράφεις", "merkmale": {
                "modus": "indikativ", "tempus": "praesens",
                "person": "2", "numerus": "sg"}}]}]})
    klient.post(f"/api/sammlungen/{s['id']}/freigabe", json={"lektion_nr": 1})
    return b, s


def _form_und_aufgabe(klient, s):
    import datenbank as dbm
    db = dbm.verbindung()
    try:
        f = dbm.zeile(db, "SELECT * FROM form WHERE text = 'γράφεις'")
        a = dbm.zeile(db, """SELECT * FROM aufgabe
                              WHERE typ = 'form_bilden' AND ziel_id = ?""",
                      (f["id"],))
        return dict(f), (dict(a) if a else None)
    finally:
        db.close()


def test_der_schluessel_ueberlebt_ein_nachgetragenes_merkmal(bestand, klient):
    """Das Kernversprechen: dieselbe Form, dieselbe Aufgabe."""
    b, s = bestand
    form, aufgabe = _form_und_aufgabe(klient, s)
    assert aufgabe is not None, "keine Formaufgabe entstanden"
    vorher = aufgabe["schluessel"]

    # Jemand trägt nach, was ohnehin gilt: Aktivform.
    antwort = klient.patch(f"/api/formen/{form['id']}", json={
        "text": form["text"],
        "merkmale": {"modus": "indikativ", "tempus": "praesens",
                     "person": "2", "numerus": "sg", "genus_verbi": "aktiv"}})
    assert antwort.status_code == 200, antwort.text
    # Eine geänderte Form ist ungeprüft — erst die erneute Freigabe
    # bringt sie zurück in die Abfrage. Das ist der echte Ablauf: ein
    # Agent berichtigt, ein Mensch sieht nach, die Aufgaben entstehen neu.
    klient.post(f"/api/sammlungen/{s['id']}/freigabe", json={"lektion_nr": 1})

    _form, nachher = _form_und_aufgabe(klient, s)
    assert nachher is not None, "die Aufgabe ist ganz verschwunden"
    assert nachher["schluessel"] == vorher, (
        "der Schlüssel hat sich geändert, obwohl sich an der Form nichts "
        "geändert hat — der Lernstand hinge jetzt an einer abgeschalteten "
        "Aufgabe")
    assert nachher["id"] == aufgabe["id"]
    assert nachher["aktiv"] == 1


def test_der_lernstand_bleibt_dabei_erhalten(bestand, klient):
    """Der eigentliche Schaden, in der Währung, die zählt."""
    b, s = bestand
    form, aufgabe = _form_und_aufgabe(klient, s)
    klient.post("/api/lernen/bewerten", json={
        "benutzer_id": b["id"], "aufgabe_id": aufgabe["id"], "bewertung": 4})

    import datenbank as dbm
    db = dbm.verbindung()
    try:
        vorher = dbm.zeile(db, """SELECT stabilitaet, anzahl FROM lernzustand
                                   WHERE aufgabe_id = ? AND benutzer_id = ?""",
                           (aufgabe["id"], b["id"]))
        assert vorher["anzahl"] == 1
    finally:
        db.close()

    klient.patch(f"/api/formen/{form['id']}", json={
        "text": form["text"],
        "merkmale": {"modus": "indikativ", "tempus": "praesens",
                     "person": "2", "numerus": "sg", "genus_verbi": "aktiv"}})
    klient.post(f"/api/sammlungen/{s['id']}/freigabe", json={"lektion_nr": 1})

    _f, nachher = _form_und_aufgabe(klient, s)
    db = dbm.verbindung()
    try:
        z = dbm.zeile(db, """SELECT stabilitaet, anzahl FROM lernzustand
                              WHERE aufgabe_id = ? AND benutzer_id = ?""",
                      (nachher["id"], b["id"]))
    finally:
        db.close()
    assert z is not None, "der Lernstand hängt an einer anderen Aufgabe"
    assert z["anzahl"] == 1
    assert abs(z["stabilitaet"] - vorher["stabilitaet"]) < 1e-9


def test_beide_schreibweisen_ergeben_denselben_schluessel():
    """Unmittelbar an der Stelle geprüft, ohne Umweg über die Datenbank."""
    import aufgaben, merkmale as mk
    roh = {"modus": "indikativ", "tempus": "praesens",
           "person": "2", "numerus": "sg"}
    ausdruecklich = {**roh, "genus_verbi": "aktiv"}
    assert (mk.schluessel(mk.normieren(roh, "verb"))
            == mk.schluessel(mk.normieren(ausdruecklich, "verb")))


def test_die_wanderung_zieht_bestehende_schluessel_nach(tmp_path, monkeypatch):
    """Ohne sie würde der erste Lauf nach der Berichtigung alle
    Formaufgaben abschalten und neu anlegen — der Lernstand hinge an den
    abgeschalteten. Genau das, was der Schlüssel verhindern soll.
    """
    import datenbank as dbm
    monkeypatch.setattr(dbm, "PFAD", tmp_path / "alt.db")
    db = dbm.verbindung()
    dbm.einrichten(db)
    db.execute("""INSERT INTO benutzer (id, name) VALUES (1, 'A')""")
    db.execute("""INSERT INTO sammlung (besitzer_id, name, sprache)
                  VALUES (1, 'S', 'el')""")
    db.execute("""INSERT INTO lexem (sammlung_id, lemma, wortart)
                  VALUES (1, 'γράφω', 'verb')""")
    db.execute("""INSERT INTO form (lexem_id, text, merkmale, geprueft)
                  VALUES (1, 'γράφεις',
                          '{"modus":"indikativ","tempus":"praesens","person":"2","numerus":"sg"}',
                          1)""")
    # Eine Aufgabe mit dem ALTEN, rohen Schlüssel — so sah der Bestand aus.
    alt = ("form_bilden:1:merkmale:"
           "modus=indikativ,numerus=sg,person=2,tempus=praesens")
    db.execute("""INSERT INTO aufgabe (lexem_id, typ, ziel_art, ziel_id, schluessel)
                  VALUES (1, 'form_bilden', 'form', 1, ?)""", (alt,))
    aufgabe_id = db.execute("SELECT id FROM aufgabe").fetchone()[0]
    db.execute("""INSERT INTO lernzustand (aufgabe_id, benutzer_id, zustand,
                                           stabilitaet, anzahl)
                  VALUES (?, 1, 'reif', 42.0, 7)""", (aufgabe_id,))

    dbm._aufgabenschluessel_normieren(db)

    neu = db.execute("SELECT schluessel, aktiv FROM aufgabe WHERE id = ?",
                     (aufgabe_id,)).fetchone()
    assert "genus_verbi=aktiv" in neu["schluessel"], \
        "der Schlüssel wurde nicht nachgezogen"
    assert neu["aktiv"] == 1
    z = db.execute("""SELECT stabilitaet, anzahl FROM lernzustand
                       WHERE aufgabe_id = ?""", (aufgabe_id,)).fetchone()
    assert (z["stabilitaet"], z["anzahl"]) == (42.0, 7), \
        "der Lernstand hängt noch an derselben Aufgabe"
    db.close()
