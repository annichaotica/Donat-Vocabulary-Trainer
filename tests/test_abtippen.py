"""Abtippen — sich mit den Wörtern vertraut machen.

»Alle Vokabeln zeigen, deutsch französisch und abtippen, erfolgreich
abgetippt, dann nächste. Sie muss sich erst mal mit den Wörtern
vertraut machen.«

Der Kern dieser Betriebsart ist, was sie NICHT tut: sie schreibt
keinen Lernstand. Eine abgeschriebene Vokabel als »gewusst« zu
verbuchen würde den Plan verfälschen, und zwar genau für die Wörter,
die noch niemand kann. Darauf zielen die meisten Prüfungen hier.
"""


def _aufbau(klient):
    b = klient.post("/api/benutzer", json={"name": "Tochter"}).json()
    s = klient.post("/api/sammlungen", json={
        "besitzer_id": b["id"], "name": "Französisch", "sprache": "fr"}).json()
    return b, s


def _lektion(klient, sammlung_id, nr, name):
    return klient.post(f"/api/sammlungen/{sammlung_id}/lektionen",
                       json={"nr": nr, "name": name}).json()


def _wort(klient, sammlung_id, lemma, deutsch, lektion_nr=None,
          reihenfolge=0, formen=None):
    """Die Lektion wird über ihre NUMMER zugeordnet, nicht über die
    Kennung — so nimmt es der Sammelimport entgegen."""
    eintrag = {"lemma": lemma, "wortart": "substantiv",
               "reihenfolge": reihenfolge,
               "bedeutungen": [{"uebersetzungen": [deutsch]}]}
    if lektion_nr is not None:
        eintrag["lektion_nr"] = lektion_nr
    if formen:
        eintrag["formen"] = formen
    a = klient.post(f"/api/sammlungen/{sammlung_id}/import/vokabeln",
                    json={"eintraege": [eintrag]})
    assert a.status_code < 300, a.text
    return klient.get(f"/api/sammlungen/{sammlung_id}/lexeme",
                      params={"suche": lemma}).json()["lexeme"][0]


def _reihe(klient, sammlung_id, **frage):
    a = klient.get(f"/api/sammlungen/{sammlung_id}/abtippen", params=frage)
    assert a.status_code == 200, a.text
    return a.json()


def _pruefen(klient, lexem_id, eingabe):
    a = klient.post("/api/abtippen/pruefen",
                    json={"lexem_id": lexem_id, "eingabe": eingabe})
    assert a.status_code == 200, a.text
    return a.json()


# --------------------------------------------------------- Die Reihenfolge

def test_alle_woerter_in_der_reihenfolge_des_lehrwerks(klient):
    """Nicht nach Fälligkeit wie die Abfrage: wer sich vertraut macht,
    geht eine Liste durch — Lektion für Lektion."""
    _b, s = _aufbau(klient)
    _lektion(klient, s["id"], 2, "Au marché")
    _lektion(klient, s["id"], 1, "Bonjour")
    _wort(klient, s["id"], "le pain", "das Brot", 2, 0)
    _wort(klient, s["id"], "bonjour", "guten Tag", 1, 0)
    _wort(klient, s["id"], "merci", "danke", 1, 1)

    d = _reihe(klient, s["id"])
    assert [k["fremd"] for k in d["karten"]] == ["bonjour", "merci", "le pain"]
    assert d["karten"][0]["deutsch"] == "guten Tag"
    assert d["sprache"] == "fr"


def test_eine_einzelne_lektion(klient):
    _b, s = _aufbau(klient)
    eins = _lektion(klient, s["id"], 1, "Bonjour")
    _lektion(klient, s["id"], 2, "Au marché")
    _wort(klient, s["id"], "bonjour", "guten Tag", 1)
    _wort(klient, s["id"], "le pain", "das Brot", 2)
    d = _reihe(klient, s["id"], lektion_id=eins["id"])
    assert [k["fremd"] for k in d["karten"]] == ["bonjour"]


def test_ungepruefte_werden_gemeldet_aber_nicht_versteckt(klient):
    """Beim Abschreiben prägt sich auch eine falsche Schreibung ein —
    also soll man wissen, was noch niemand angesehen hat.

    Weggelassen werden sie aber NICHT. Der Trainer legt die
    Vokabelabfrage allein danach an, ob eine Übersetzung da ist; eine
    strengere Regel hier hieße, dass er ein Wort abfragt, das er zum
    Abtippen verschweigt."""
    _b, s = _aufbau(klient)
    _wort(klient, s["id"], "bonjour", "guten Tag")
    _wort(klient, s["id"], "soi-disant", "angeblich",
          formen=[{"text": "soi-disant", "merkmale": {}, "geprueft": False}])
    d = _reihe(klient, s["id"])
    assert [k["fremd"] for k in d["karten"]] == ["bonjour", "soi-disant"]
    assert d["ungeprueft"] == 1
    assert [k["ungeprueft"] for k in d["karten"]] == [False, True]


def test_ohne_uebersetzung_keine_karte(klient):
    """Ohne deutsche Seite gibt es nichts zu zeigen — und das wird
    gesagt statt stillschweigend weggelassen."""
    _b, s = _aufbau(klient)
    _wort(klient, s["id"], "bonjour", "guten Tag")
    klient.post(f"/api/sammlungen/{s['id']}/import/vokabeln", json={
        "eintraege": [{"lemma": "zut", "wortart": "interjektion",
                       "bedeutungen": []}]})
    d = _reihe(klient, s["id"])
    assert [k["fremd"] for k in d["karten"]] == ["bonjour"]
    assert d["ohne_uebersetzung"] == 1


# ------------------------------------------------------------- Das Prüfen

def test_richtig_abgetippt(klient):
    _b, s = _aufbau(klient)
    w = _wort(klient, s["id"], "bonjour", "guten Tag")
    assert _pruefen(klient, w["id"], "bonjour")["urteil"] == "richtig"


def test_vertipper_faellt_auf(klient):
    """Beim Abtippen ist die Vorlage sichtbar. Jede Abweichung ist also
    ein Vertipper und keine Wissenslücke — und gerade den soll man
    sehen. Ein nachsichtigerer Maßstab als in der Abfrage wäre hier
    besonders verkehrt."""
    _b, s = _aufbau(klient)
    w = _wort(klient, s["id"], "bonjour", "guten Tag")
    assert _pruefen(klient, w["id"], "bonjur")["urteil"] != "richtig"


def test_der_artikel_darf_fehlen(klient):
    """»le chien« abgetippt als »chien« ist das Wort — der Artikel ist
    die Zugabe des Wörterbuchs, nicht das Wort selbst."""
    _b, s = _aufbau(klient)
    w = _wort(klient, s["id"], "le chien", "der Hund")
    assert _pruefen(klient, w["id"], "le chien")["urteil"] == "richtig"
    assert _pruefen(klient, w["id"], "chien")["urteil"] == "richtig"


def test_akzente_werden_nach_dem_sprachprofil_beurteilt(klient):
    """Französisch, nicht irgendeine allgemeine Regel: was ein fehlender
    Akzent bedeutet, entscheidet die Sprache."""
    _b, s = _aufbau(klient)
    w = _wort(klient, s["id"], "l'été", "der Sommer")
    assert _pruefen(klient, w["id"], "l'été")["urteil"] == "richtig"
    assert _pruefen(klient, w["id"], "l'ete")["urteil"] != "richtig"


# ---------------------------------------------- Und was es NICHT tut

def test_abtippen_schreibt_keinen_lernstand(klient):
    """Der Kern der ganzen Betriebsart.

    Die Abfrage rechnet aus dem Ergebnis einen Termin. Wer ein Wort zum
    ersten Mal sieht, hat darauf keine Antwort — er rät. Ein
    abgeschriebenes Wort als »gewusst« zu verbuchen, verfälscht den
    Plan genau für die Wörter, die noch niemand kann.
    """
    b, s = _aufbau(klient)
    w = _wort(klient, s["id"], "bonjour", "guten Tag")

    vorher = klient.get("/api/lernen/stand",
                        params={"benutzer_id": b["id"],
                                "sammlung_id": s["id"]}).json()
    for _ in range(5):
        assert _pruefen(klient, w["id"], "bonjour")["urteil"] == "richtig"
    nachher = klient.get("/api/lernen/stand",
                         params={"benutzer_id": b["id"],
                                 "sammlung_id": s["id"]}).json()
    assert nachher == vorher, "Abtippen hat den Lernstand verändert"

    # Und das Wort ist danach immer noch »neu«, nicht etwa terminiert.
    import datenbank as dbm
    db = dbm.verbindung()
    try:
        assert dbm.wert(db, "SELECT COUNT(*) FROM lernzustand") == 0
        assert dbm.wert(db, "SELECT COUNT(*) FROM wiederholung") == 0
    finally:
        db.close()


def test_unbekanntes_wort_gibt_404(klient):
    _aufbau(klient)
    a = klient.post("/api/abtippen/pruefen",
                    json={"lexem_id": 9999, "eingabe": "x"})
    assert a.status_code == 404
