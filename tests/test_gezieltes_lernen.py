"""Wort für Wort festlegen, ob es abgefragt wird.

»Wir brauchen einen Modus für gezieltes Lernen, dort soll Wort für
Wort auswählbar sein, was abgefragt wird. Da das auch bei der Anlage
über den MCP vorbelegbar sein sollte, z.B. mit Sammlungskeywords oder
so, muss das auch mitberücksichtigt werden.«

Der Anlass steckt in Kapitel 101: unter 621 Einträgen sind 45
Eigennamen und 10 Abkürzungen. Die gehören in den Wortschatz, damit
der Lesetext gedeckt ist — abgefragt werden will sie niemand.
"""

import pytest


def _aufbau(klient, sprache="el"):
    b = klient.post("/api/benutzer", json={"name": "Lernende"}).json()
    s = klient.post("/api/sammlungen", json={
        "besitzer_id": b["id"], "name": "Griechisch", "sprache": sprache}).json()
    return b, s


def _wort(klient, sammlung_id, lemma, **rest):
    eintrag = {"lemma": lemma, "wortart": "substantiv",
               "bedeutungen": [{"uebersetzungen": ["irgendwas"]}], **rest}
    a = klient.post(f"/api/sammlungen/{sammlung_id}/import/vokabeln",
                    json={"eintraege": [eintrag]})
    assert a.status_code < 300, a.text
    return klient.get(f"/api/sammlungen/{sammlung_id}/lexeme",
                      params={"suche": lemma}).json()["lexeme"][0]


def _aufgaben(klient, lexem_id):
    return [a for a in klient.get(f"/api/lexeme/{lexem_id}").json()["aufgaben"]
            if a["aktiv"]]


# --------------------------------------------------------- Stilllegen

def test_stillgelegt_erzeugt_keine_aufgaben(klient):
    _b, s = _aufbau(klient)
    w = _wort(klient, s["id"], "Μέρκελ")
    assert _aufgaben(klient, w["id"]), "Vorbedingung: es gibt Aufgaben"

    a = klient.put("/api/abfrage", json={"lexem_ids": [w["id"]],
                                         "abfrage": False})
    assert a.status_code == 200, a.text
    assert not _aufgaben(klient, w["id"])


def test_wieder_dazunehmen_holt_den_lernstand_zurueck(klient):
    """Abgeschaltet, nicht gelöscht. Wer ein Wort zeitweise stilllegt,
    soll beim Wiedereinschalten nicht von vorn anfangen — das ist
    dieselbe Zusage wie bei einer abgewählten Formgruppe."""
    import sys
    sys.path.insert(0, "backend")
    import datenbank as dbm

    b, s = _aufbau(klient)
    w = _wort(klient, s["id"], "το σπίτι")
    vorher = {a["id"] for a in _aufgaben(klient, w["id"])}
    aufgabe_id = next(iter(vorher))

    db = dbm.verbindung()
    try:
        db.execute("""INSERT INTO lernzustand
                        (benutzer_id, aufgabe_id, zustand, stabilitaet,
                         schwierigkeit, faellig)
                      VALUES (?, ?, 'reif', 12.0, 5.0, '2099-01-01')""",
                   (b["id"], aufgabe_id))
        db.commit()
    finally:
        db.close()

    klient.put("/api/abfrage", json={"lexem_ids": [w["id"]], "abfrage": False})
    assert not _aufgaben(klient, w["id"])
    klient.put("/api/abfrage", json={"lexem_ids": [w["id"]], "abfrage": True})
    assert {a["id"] for a in _aufgaben(klient, w["id"])} == vorher

    db = dbm.verbindung()
    try:
        assert dbm.wert(db, """SELECT stabilitaet FROM lernzustand
                                WHERE aufgabe_id = ?""", (aufgabe_id,)) == 12.0
    finally:
        db.close()


def test_viele_auf_einmal(klient):
    """Nach einem Zeitungsartikel sind es fünfundvierzig Eigennamen."""
    _b, s = _aufbau(klient)
    ids = [_wort(klient, s["id"], n)["id"]
           for n in ("Μέρκελ", "Βερολίνο", "Ρόμπερτ")]
    d = klient.put("/api/abfrage",
                   json={"lexem_ids": ids, "abfrage": "nachschlagen"}).json()
    assert d["geaendert"] == 3
    for i in ids:
        assert not _aufgaben(klient, i)


# ----------------------------------------------------------- Vorlagen

def test_vorlage_nachschlagen_gibt_es_ohne_zutun(klient):
    """Zwei Namen kennt jede Sammlung, ohne dass jemand sie anlegt —
    sie benennen die Fälle, die beim Eintragen aus Texten dauernd
    vorkommen."""
    _b, s = _aufbau(klient)
    d = klient.get(f"/api/sammlungen/{s['id']}/abfrage").json()
    assert d["vorlagen"]["nachschlagen"] == {"an": False}
    assert d["vorlagen"]["voll"] == {"an": True}


def test_eigene_vorlage_der_sammlung(klient):
    _b, s = _aufbau(klient)
    klient.put(f"/api/sammlungen/{s['id']}/einstellungen", json={
        "abfragevorlagen": {"zitat": {"an": False}}})
    w = _wort(klient, s["id"], "Wir schaffen das", abfrage="zitat")
    assert not _aufgaben(klient, w["id"])
    d = klient.get(f"/api/sammlungen/{s['id']}/abfrage").json()
    eintrag = next(x for x in d["woerter"] if x["lexem_id"] == w["id"])
    # Die Vorlage bleibt stehen — man sieht später, WARUM es stillliegt.
    assert eintrag["vorlage"] == "zitat"
    assert eintrag["an"] is False


def test_unbekannte_vorlage_wird_abgelehnt(klient):
    """Still übergehen wäre das Schlimmste: das Wort stünde abfragbar
    da, obwohl es ausdrücklich nicht sollte."""
    _b, s = _aufbau(klient)
    a = klient.post(f"/api/sammlungen/{s['id']}/import/vokabeln", json={
        "eintraege": [{"lemma": "AfD", "wortart": "sonstiges",
                       "abfrage": "gibtsnicht",
                       "bedeutungen": [{"uebersetzungen": ["AfD"]}]}]})
    d = a.json()
    assert d["abgelehnt"] == 1
    assert "gibtsnicht" in str(d["eintraege"][0]["befunde"])


# ------------------------------------------------------------ Übersicht

def test_uebersicht_zeigt_und_filtert(klient):
    _b, s = _aufbau(klient)
    an = _wort(klient, s["id"], "το σπίτι")
    aus = _wort(klient, s["id"], "Μέρκελ", abfrage="nachschlagen")

    d = klient.get(f"/api/sammlungen/{s['id']}/abfrage").json()
    assert d["gesamt"] == 2 and d["stillgelegt"] == 1
    nach_id = {w["lexem_id"]: w for w in d["woerter"]}
    assert nach_id[an["id"]]["an"] is True
    assert nach_id[an["id"]]["aufgaben"] > 0
    assert nach_id[aus["id"]]["an"] is False
    assert nach_id[aus["id"]]["aufgaben"] == 0

    nur = klient.get(f"/api/sammlungen/{s['id']}/abfrage",
                     params={"nur_aus": True}).json()
    assert [w["lexem_id"] for w in nur["woerter"]] == [aus["id"]]


# ------------------------------------------------- Lernziel über Wörter

def test_lernziel_ueber_genau_diese_woerter(klient):
    """»Könnte ich das dem Claude geben, um eine Sammlung aus genau den
    Wörtern zu erstellen, die in den zwei Fotos meiner Tochter sind?«

    Eine eigene Sammlung wäre der Umweg: sie verdoppelt die Wörter und
    teilt den Lernstand. Ein Lernziel nimmt `umfang.lexeme` — genau
    diese Wörter, aus der Sammlung, die es schon gibt.
    """
    import sys
    sys.path.insert(0, "backend")
    import datenbank as dbm
    import mcp_dienst

    b, s = _aufbau(klient, sprache="fr")
    ids = [_wort(klient, s["id"], w)["id"]
           for w in ("le tandem", "s'inscrire", "sans cesse", "le hasard")]
    liste = ids[:3]          # die zwei Fotos ergeben drei Wörter

    db = dbm.verbindung()
    try:
        person = dict(dbm.zeile(db, "SELECT * FROM benutzer WHERE id = ?",
                                (b["id"],)))
        ziel = mcp_dienst.lernziel_anlegen(
            db, person, name="Vokabeltest Freitag",
            umfang={"lexeme": liste}, termin="2099-01-15",
            ziel="einmal_richtig")
        db.commit()
        offen = mcp_dienst.lernziele_auflisten(db, person)
    finally:
        db.close()

    assert ziel["name"] == "Vokabeltest Freitag"
    eintrag = offen["lernziele"][0]
    assert eintrag["umfang_text"] == "3 ausgewählte Wörter"
    # Der Fortschritt zählt NUR diese drei, nicht das vierte Wort.
    assert eintrag["fortschritt"]["gesamt"] > 0
    d = klient.get(f"/api/lernziele/{ziel['id']}/fortschritt",
                   params={"benutzer_id": b["id"]}).json()
    assert d["gesamt"] == eintrag["fortschritt"]["gesamt"]


def test_lernziel_nicht_ueber_fremden_bestand(klient):
    """Ohne diese Prüfung ließe sich ein Ziel über Wörter legen, die
    einen nichts angehen — und die Abfrage zeigte sie dann."""
    import sys
    sys.path.insert(0, "backend")
    import datenbank as dbm
    import mcp_dienst
    import zugang

    a, _ = _aufbau(klient)
    fremd_b = klient.post("/api/benutzer", json={"name": "Max"}).json()
    fremd_s = klient.post("/api/sammlungen", json={
        "besitzer_id": fremd_b["id"], "name": "Max", "sprache": "gmh"}).json()
    fremdes_wort = _wort(klient, fremd_s["id"], "ouwê")

    db = dbm.verbindung()
    try:
        person = dict(dbm.zeile(db, "SELECT * FROM benutzer WHERE id = ?",
                                (a["id"],)))
        with pytest.raises(zugang.NichtErlaubt):
            mcp_dienst.lernziel_anlegen(
                db, person, name="geht nicht",
                umfang={"lexeme": [fremdes_wort["id"]]})
    finally:
        db.close()
