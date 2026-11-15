"""Der Übungskurs muss alles können, was er zeigen soll.

»Dazu vielleicht auch tatsächlich für Englisch einen kleinen
Übungskurs, damit man alle Features zeigen und ausprobieren kann?«

Ein Beispielkurs, bei dem die Hälfte der Knöpfe ins Leere führt, ist
schlimmer als keiner — man hielte den Trainer für kaputt. Diese Tests
gehen deshalb nicht die Daten durch, sondern die Funktionen: lässt
sich damit abfragen, üben, lesen, planen und die Lektionsschranke
vorführen?
"""

import pytest


@pytest.fixture()
def kurs(klient):
    b = klient.post("/api/benutzer", json={"name": "Neugierig"}).json()
    antwort = klient.post("/api/beispielkurs", params={"benutzer_id": b["id"]})
    assert antwort.status_code == 201, antwort.text
    return b, antwort.json()


def test_er_entsteht_vollstaendig(kurs, klient):
    b, d = kurs
    assert d["neu"] is True
    assert d["aufgaben"] > 20, d


def test_zweimal_anlegen_gibt_einen_kurs(kurs, klient):
    """Sonst verteilt sich der Lernstand auf zwei."""
    b, d = kurs
    nochmal = klient.post("/api/beispielkurs",
                          params={"benutzer_id": b["id"]}).json()
    assert nochmal["neu"] is False
    assert nochmal["sammlung_id"] == d["sammlung_id"]
    liste = klient.get("/api/sammlungen",
                       params={"benutzer_id": b["id"]}).json()
    assert len(liste) == 1


def test_man_kann_sofort_abfragen(kurs, klient):
    """Nichts muss erst freigegeben werden."""
    b, d = kurs
    liste = klient.get("/api/lernen/naechste", params={
        "benutzer_id": b["id"], "sammlung_id": d["sammlung_id"],
        "anzahl": 10}).json()
    assert len(liste) == 10, liste


def test_es_gibt_formaufgaben_nicht_nur_bedeutungen(kurs, klient):
    """Sonst liefe »Form bilden« im Kurs ins Leere."""
    b, d = kurs
    import datenbank as dbm
    db = dbm.verbindung()
    try:
        gruppen = {z["formgruppe"] for z in dbm.zeilen(db, """
            SELECT DISTINCT a.formgruppe FROM aufgabe a
              JOIN lexem l ON l.id = a.lexem_id
             WHERE l.sammlung_id = ? AND a.aktiv = 1
               AND a.formgruppe IS NOT NULL""", (d["sammlung_id"],))}
    finally:
        db.close()
    assert {"present_3sg", "past", "pl"} <= gruppen, gruppen


def test_die_saetze_lassen_sich_ueben(kurs, klient):
    b, d = kurs
    liste = klient.get("/api/uebungen/lernen/naechste", params={
        "benutzer_id": b["id"], "sammlung_id": d["sammlung_id"],
        "anzahl": 5}).json()
    assert liste, "keine Satzübung — der Knopf »Sätze« führt ins Leere"


def test_der_text_ist_da_und_vollstaendig_gedeckt(kurs, klient):
    """Der Beispieltext soll zeigen, wie die Deckung aussieht, wenn man
    alles kann — und nicht zufällig Lücken haben."""
    b, d = kurs
    texte = klient.get(f"/api/sammlungen/{d['sammlung_id']}/texte").json()
    assert len(texte) == 1, texte
    deckung = klient.get(f"/api/texte/{texte[0]['id']}/deckung",
                         params={"benutzer_id": b["id"]}).json()
    fehlt = sorted({w["wort"] for w in deckung["woerter"] if not w["lexem_id"]})
    assert deckung["abdeckung"] >= 60, (
        f"der Beispieltext hat zu viele Lücken: {fehlt}")


def test_die_grammatikregel_erscheint_an_der_aufgabe(kurs, klient):
    """Das »Warum ist das so?« — ohne Regel bliebe das Feld leer."""
    b, d = kurs
    # Freies Üben: der Planweg deckelt die neuen Wörter je Sitzung, und
    # dann kann die Formaufgabe zum Präsens zufällig fehlen. Die erste
    # Fassung dieses Tests lief deshalb ins Leere, ohne dass an der
    # Regel etwas falsch war.
    liste = klient.get("/api/lernen/naechste", params={
        "benutzer_id": b["id"], "sammlung_id": d["sammlung_id"],
        "nur": "frei", "anzahl": 50}).json()
    mit = [a for a in liste if a.get("regeln")]
    assert mit, "keine Aufgabe bringt die Grammatikregel mit"
    assert any("3. Person" in r["titel"] for a in mit for r in a["regeln"])


def test_die_lektionsschranke_laesst_sich_vorfuehren(kurs, klient):
    """Der Kurs bringt die Zuordnung mit — sonst müsste man sie erst
    eintragen, um die Funktion überhaupt zu sehen."""
    b, d = kurs
    lg = klient.get(f"/api/sammlungen/{d['sammlung_id']}/lehrgang",
                    params={"benutzer_id": b["id"]}).json()
    assert lg["zuordnung"].get("past") == 4

    klient.put(f"/api/sammlungen/{d['sammlung_id']}/buchstand",
               json={"benutzer_id": b["id"], "bis_lektion": 2})
    # Freies Üben: der Planweg deckelt die neuen Wörter je Sitzung, und
    # dann fehlt die gesuchte Formgruppe womöglich nur deshalb. Seit der
    # Kurs drei ungeprüfte Wörter mehr hat, ist das eingetreten.
    liste = klient.get("/api/lernen/naechste", params={
        "benutzer_id": b["id"], "sammlung_id": d["sammlung_id"],
        "nur": "frei", "anzahl": 50}).json()
    import datenbank as dbm
    db = dbm.verbindung()
    try:
        gruppen = {dbm.wert(db, "SELECT formgruppe FROM aufgabe WHERE id = ?",
                            (a["aufgabe_id"],)) for a in liste}
    finally:
        db.close()
    assert "past" not in gruppen, gruppen
    assert "present_3sg" in gruppen, "das Präsens ist mit weggefallen"


def test_er_laesst_sich_wieder_loeschen(kurs, klient):
    """Er soll ein Angebot sein, kein Anhängsel."""
    b, d = kurs
    antwort = klient.delete(f"/api/sammlungen/{d['sammlung_id']}")
    assert antwort.status_code in (200, 204), antwort.text
    assert klient.get("/api/sammlungen",
                      params={"benutzer_id": b["id"]}).json() == []


def test_an_ihm_laesst_sich_die_freigabe_ueben(kurs, klient):
    """Der Kurs war durchgehend freigegeben — und damit ließ sich der
    wichtigste Handgriff an ihm nicht zeigen. Die Prüfansicht sagte
    »Alles freigegeben, es wartet nichts«; das Bildschirmfoto für den
    Lehrgang bewies es.
    """
    b, d = kurs
    offen = klient.get(
        f"/api/sammlungen/{d['sammlung_id']}/freigabe/lektionen").json()
    assert offen["offen_gesamt"] > 0, "nichts zu prüfen"


def test_ein_eintrag_ist_absichtlich_falsch(kurs, klient):
    """»goed« statt »walked« — so etwas erfindet eine KI wirklich: sie
    überträgt die regelmäßige Endung auf ein Verb, das sie nicht hat.
    Wer es durchwinkt, paukt es. Der Fehler muss drinbleiben, sonst
    übt man die Freigabe an lauter richtigen Einträgen und lernt, sie
    durchzuklicken."""
    b, d = kurs
    import datenbank as dbm
    db = dbm.verbindung()
    try:
        falsch = dbm.zeile(db, """SELECT f.text, f.geprueft
                                    FROM form f JOIN lexem l ON l.id = f.lexem_id
                                   WHERE l.sammlung_id = ? AND f.text = 'goed'""",
                           (d["sammlung_id"],))
    finally:
        db.close()
    assert falsch is not None, "der absichtliche Fehler fehlt"
    assert falsch["geprueft"] == 0, "er ist freigegeben — dann fällt er nie auf"


def test_das_ungepruefte_wird_nicht_abgefragt(kurs, klient):
    """Die Zusage, auf der alles ruht."""
    b, d = kurs
    liste = klient.get("/api/lernen/naechste", params={
        "benutzer_id": b["id"], "sammlung_id": d["sammlung_id"],
        "nur": "frei", "anzahl": 50}).json()
    import datenbank as dbm
    db = dbm.verbindung()
    try:
        ziele = {dbm.wert(db, """SELECT f.text FROM aufgabe a
                                   JOIN form f ON f.id = a.ziel_id
                                  WHERE a.id = ? AND a.ziel_art = 'form'""",
                          (a["aufgabe_id"],)) for a in liste}
    finally:
        db.close()
    assert "goed" not in ziele, "der ungeprüfte Fehler wird abgefragt"
