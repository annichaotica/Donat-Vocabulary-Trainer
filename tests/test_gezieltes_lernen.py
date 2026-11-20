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


def test_lernziel_fuer_jemand_anderen(klient):
    """»Kannst du es bitte zu Lernende 2 umhängen.«

    Der KI-Konnektor hängt an EINEM Profil, die Ziele sind aber meist
    für die Kinder. Deshalb darf ein Ziel gleich für jemand anderen
    angelegt und ein bestehendes umgehängt werden.
    """
    import sys
    sys.path.insert(0, "backend")
    import datenbank as dbm
    import mcp_dienst

    anni, s = _aufbau(klient, sprache="fr")          # erste Person = Verwalterin
    kathi = klient.post("/api/benutzer", json={"name": "Lernende 2"}).json()
    w = _wort(klient, s["id"], "le tandem")

    db = dbm.verbindung()
    try:
        person = dict(dbm.zeile(db, "SELECT * FROM benutzer WHERE id = ?",
                                (anni["id"],)))
        gleich = mcp_dienst.lernziel_anlegen(
            db, person, name="Vokabeltest", umfang={"lexeme": [w["id"]]},
            fuer="Lernende 2")
        assert gleich["benutzer_id"] == kathi["id"]

        # Und ein bestehendes umhängen.
        meins = mcp_dienst.lernziel_anlegen(
            db, person, name="Meins", umfang={"lexeme": [w["id"]]})
        assert meins["benutzer_id"] == anni["id"]
        db.commit()
        umgehaengt = mcp_dienst.lernziel_umhaengen(db, person, meins["id"],
                                                   "kathi")
        db.commit()
        assert umgehaengt["benutzer_id"] == kathi["id"]
    finally:
        db.close()

    # Bei Lernende 2 stehen jetzt beide, bei Annuschka keines.
    assert len(klient.get("/api/lernziele",
                          params={"benutzer_id": kathi["id"]}).json()) == 2
    assert klient.get("/api/lernziele",
                      params={"benutzer_id": anni["id"]}).json() == []


def test_nur_der_verwalter_darf_fremde_ziele_setzen(klient):
    """Sonst könnte jeder jedem Pflichten in den Plan schreiben.

    Der Test muss am EIGENEN Bestand ansetzen. Setzte er fremden
    Bestand ein, schlüge schon die Sammlungsprüfung zu — der Test
    bestünde dann auch ohne die Rechteprüfung, und zwar aus dem
    falschen Grund. Genau so war er zuerst gebaut, und die Gegenprobe
    hat es gezeigt.
    """
    import sys
    sys.path.insert(0, "backend")
    import datenbank as dbm
    import mcp_dienst
    import zugang

    _erste, _s = _aufbau(klient, sprache="fr")        # wird Verwalterin
    annuschka = klient.post("/api/benutzer",
                            json={"name": "Annuschka"}).json()
    kathi = klient.post("/api/benutzer", json={"name": "Lernende 2"}).json()
    ihre = klient.post("/api/sammlungen", json={
        "besitzer_id": kathi["id"], "name": "Lernende 2s Französisch",
        "sprache": "fr"}).json()
    ihr_wort = _wort(klient, ihre["id"], "le hasard")

    db = dbm.verbindung()
    try:
        kathi_person = dict(dbm.zeile(
            db, "SELECT * FROM benutzer WHERE id = ?", (kathi["id"],)))
        assert not kathi_person["verwalter"]

        # Ihr eigener Bestand, ihr eigenes Profil: erlaubt.
        eigenes = mcp_dienst.lernziel_anlegen(
            db, kathi_person, name="für mich",
            umfang={"lexeme": [ihr_wort["id"]]})
        assert eigenes["benutzer_id"] == kathi["id"]

        # Ihr eigener Bestand, FREMDES Profil: nicht erlaubt. Am
        # Umfang kann es hier nicht mehr scheitern.
        with pytest.raises(zugang.NichtErlaubt):
            mcp_dienst.lernziel_anlegen(
                db, kathi_person, name="für Mama",
                umfang={"lexeme": [ihr_wort["id"]]}, fuer="Annuschka")
        assert annuschka["id"] != kathi["id"]
    finally:
        db.close()


def test_das_umschalten_schickt_die_fertige_zeile_zurueck(klient):
    """Damit die Oberfläche nicht die ganze Liste neu holen muss.

    Sie tat genau das: nach jedem »ja/nein« eine Anfrage über bis zu
    200 Zeilen, jede mit zwei Unterabfragen — und die Seite sprang
    nach oben. Bei 1927 griechischen Wörtern ist das der Unterschied
    zwischen »ein Wort umgeschaltet« und »alles neu«.

    Die Zahl der aktiven Aufgaben steht erst fest, NACHDEM `erzeugen`
    gelaufen ist. Genau deshalb kann die Oberfläche sie nicht selbst
    ausrechnen, und genau deshalb gehört sie in die Antwort.
    """
    _b, s = _aufbau(klient)
    eins = _wort(klient, s["id"], "το σπίτι")
    zwei = _wort(klient, s["id"], "το μήλο")
    assert _aufgaben(klient, eins["id"])

    antwort = klient.put("/api/abfrage", json={
        "lexem_ids": [eins["id"]], "abfrage": False}).json()
    assert antwort["geaendert"] == 1
    zeile = antwort["woerter"][0]
    assert zeile["lexem_id"] == eins["id"]
    assert zeile["lemma"] == "το σπίτι"
    assert zeile["an"] is False
    assert zeile["aufgaben"] == 0          # nach dem Neuerzeugen, nicht davor
    assert zeile["bedeutung"] == "irgendwas"
    # Der Zähler unter den Filtern zählt die ganze Sammlung mit.
    assert antwort["stillgelegt"] == 1

    # Und wieder an: dieselbe Zeile, andere Zahlen.
    zurueck = klient.put("/api/abfrage", json={
        "lexem_ids": [eins["id"]], "abfrage": True}).json()
    assert zurueck["woerter"][0]["an"] is True
    assert zurueck["woerter"][0]["aufgaben"] > 0
    assert zurueck["stillgelegt"] == 0

    # Gesammelt genauso — eine Zeile je Wort, in einer Antwort.
    viele = klient.put("/api/abfrage", json={
        "lexem_ids": [eins["id"], zwei["id"]], "abfrage": False}).json()
    assert {w["lexem_id"] for w in viele["woerter"]} == {eins["id"], zwei["id"]}
    assert viele["stillgelegt"] == 2


def test_die_zurueckgeschickte_zeile_sieht_aus_wie_die_aus_der_liste(klient):
    """Zwei Beschreibungen derselben Zeile laufen auseinander.

    Die ausgetauschte Zeile steht zwischen Zeilen aus der Liste. Zeigt
    sie andere Felder, fällt es als Erstes dort auf — und zwar als
    »da fehlt was«, nicht als Fehler.
    """
    _b, s = _aufbau(klient)
    wort = _wort(klient, s["id"], "το σπίτι")

    aus_der_liste = klient.get(f"/api/sammlungen/{s['id']}/abfrage"
                               ).json()["woerter"][0]
    aus_dem_setzen = klient.put("/api/abfrage", json={
        "lexem_ids": [wort["id"]], "abfrage": True}).json()["woerter"][0]
    assert aus_der_liste.keys() == aus_dem_setzen.keys()
    assert aus_der_liste == aus_dem_setzen
