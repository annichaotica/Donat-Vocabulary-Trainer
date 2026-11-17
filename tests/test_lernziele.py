"""Lernziele und dynamisch zusammengestellte Lernblöcke."""

import datetime as dt


def _wort(klient, sammlung_id, lemma, uebersetzung, lektion_id=None):
    return klient.post("/api/lexeme", json={
        "sammlung_id": sammlung_id, "lemma": lemma, "wortart": "verb",
        "lektion_id": lektion_id,
        "bedeutungen": [{"uebersetzungen": [{"text": uebersetzung}]}]}).json()


def _aufbau(klient, woerter=6):
    b = klient.post("/api/benutzer", json={"name": "Zieler"}).json()
    s = klient.post("/api/sammlungen", json={
        "besitzer_id": b["id"], "name": "Französisch", "sprache": "fr"}).json()
    lektionen = [klient.post(f"/api/sammlungen/{s['id']}/lektionen",
                             json={"name": f"Lektion {i}", "reihenfolge": i}).json()
                 for i in (1, 2)]
    for i in range(woerter):
        _wort(klient, s["id"], f"mot{i}", f"Wort {i}",
              lektionen[i % 2]["id"])
    return b, s, lektionen


def test_lernziel_anlegen_und_umfang_beschreiben(klient):
    b, s, lektionen = _aufbau(klient)
    ziel = klient.post("/api/lernziele", json={
        "benutzer_id": b["id"], "name": "Lektion 1 bis Freitag",
        "umfang": {"lektionen": [lektionen[0]["id"]]},
        "termin": (dt.date.today() + dt.timedelta(days=7)).isoformat()}).json()
    assert ziel["name"] == "Lektion 1 bis Freitag"
    gelesen = klient.get(f"/api/lernziele/{ziel['id']}").json()
    assert "Lektion" in gelesen["umfang_text"]


def test_fortschritt_rechnet_den_tagesbedarf(klient):
    b, s, lektionen = _aufbau(klient, woerter=10)
    ziel = klient.post("/api/lernziele", json={
        "benutzer_id": b["id"], "name": "Alles",
        "termin": (dt.date.today() + dt.timedelta(days=10)).isoformat()}).json()
    f = klient.get(f"/api/lernziele/{ziel['id']}/fortschritt",
                   params={"benutzer_id": b["id"]}).json()
    assert f["gesamt"] == 20          # je Wort zwei Bedeutungsaufgaben
    assert f["geschafft"] == 0 and f["neu"] == 20
    # 20 neue Aufgaben, 10 Tage minus 3 Tage Sicherheit = 7 Tage
    assert f["neu_taeglich_noetig"] == 3
    assert "noch 10 Tage" in f["lage"]
    assert f["schaffbar"] is True


def test_umfang_greift_ueber_lektionen_hinweg(klient):
    """Ein Ziel darf quer über Lektionen greifen — das ist der Sinn."""
    b, s, lektionen = _aufbau(klient, woerter=6)
    eng = klient.post("/api/lernziele", json={
        "benutzer_id": b["id"], "name": "Nur Lektion 1",
        "umfang": {"lektionen": [lektionen[0]["id"]]}}).json()
    weit = klient.post("/api/lernziele", json={
        "benutzer_id": b["id"], "name": "Beide Lektionen",
        "umfang": {"lektionen": [l["id"] for l in lektionen]}}).json()
    f_eng = klient.get(f"/api/lernziele/{eng['id']}/fortschritt",
                       params={"benutzer_id": b["id"]}).json()
    f_weit = klient.get(f"/api/lernziele/{weit['id']}/fortschritt",
                        params={"benutzer_id": b["id"]}).json()
    assert f_eng["gesamt"] == 6 and f_weit["gesamt"] == 12


def test_umfang_nach_aufgabentyp(klient):
    b, s, _l = _aufbau(klient, woerter=4)
    ziel = klient.post("/api/lernziele", json={
        "benutzer_id": b["id"], "name": "Nur Erkennen",
        "umfang": {"typen": ["bedeutung_fremd_deutsch"]}}).json()
    f = klient.get(f"/api/lernziele/{ziel['id']}/fortschritt",
                   params={"benutzer_id": b["id"]}).json()
    assert f["gesamt"] == 4


def test_block_begruendet_seinen_zuschnitt(klient):
    b, s, _l = _aufbau(klient, woerter=8)
    ziel = klient.post("/api/lernziele", json={
        "benutzer_id": b["id"], "name": "Alles",
        "termin": (dt.date.today() + dt.timedelta(days=30)).isoformat()}).json()
    block = klient.get(f"/api/lernziele/{ziel['id']}/block",
                       params={"benutzer_id": b["id"], "anzahl": 10}).json()
    assert block["anzahl"] > 0
    assert "neu" in block["begruendung"]
    assert block["zusammensetzung"]["neu"] == block["anzahl"]


def test_block_verschraenkt_die_woerter(klient):
    """Aufeinanderfolgende Aufgaben sollen nicht zum selben Wort gehören.
    Wer sechs Formen desselben Verbs am Stück bekommt, merkt sich die
    Reihenfolge statt der Formen."""
    b, s, _l = _aufbau(klient, woerter=6)
    ziel = klient.post("/api/lernziele", json={
        "benutzer_id": b["id"], "name": "Alles"}).json()
    block = klient.get(f"/api/lernziele/{ziel['id']}/block",
                       params={"benutzer_id": b["id"], "anzahl": 12}).json()
    lexeme = [a["lexem_id"] for a in block["aufgaben"]]
    nacheinander = sum(1 for i in range(len(lexeme) - 1)
                       if lexeme[i] == lexeme[i + 1])
    assert nacheinander == 0, f"{nacheinander} Wiederholungen hintereinander"


def test_block_nimmt_faelliges_zuerst(klient):
    b, s, _l = _aufbau(klient, woerter=6)
    ziel = klient.post("/api/lernziele", json={
        "benutzer_id": b["id"], "name": "Alles"}).json()
    # Zwei Aufgaben lernen und auf heute zurückdatieren
    erste = klient.get(f"/api/lernziele/{ziel['id']}/block",
                       params={"benutzer_id": b["id"], "anzahl": 2}).json()
    for a in erste["aufgaben"]:
        klient.post("/api/lernen/bewerten", json={
            "benutzer_id": b["id"], "aufgabe_id": a["aufgabe_id"],
            "urteil": "richtig", "denkzeit_ms": 1000})
        klient.post("/api/lernen/termin", json={
            "benutzer_id": b["id"], "aufgabe_id": a["aufgabe_id"],
            "datum": dt.date.today().isoformat()})
    zweite = klient.get(f"/api/lernziele/{ziel['id']}/block",
                        params={"benutzer_id": b["id"], "anzahl": 10}).json()
    assert zweite["zusammensetzung"]["faellig"] == 2
    assert "fällig" in zweite["begruendung"]


def test_lernen_kann_aus_einem_lernziel_ziehen(klient):
    b, s, lektionen = _aufbau(klient, woerter=4)
    ziel = klient.post("/api/lernziele", json={
        "benutzer_id": b["id"], "name": "Nur Lektion 2",
        "umfang": {"lektionen": [lektionen[1]["id"]]}}).json()
    reihe = klient.get("/api/lernen/naechste", params={
        "benutzer_id": b["id"], "lernziel_id": ziel["id"], "anzahl": 3}).json()
    assert len(reihe) == 3
    for a in reihe:
        assert a["lernziel"]["name"] == "Nur Lektion 2"
        assert a["herkunft"] in ("neu", "faellig", "wacklig")
        assert a["frage_text"]            # vollständig ausgebaut
        assert a["vorschau"]["3"]["text"]


def test_leeres_lernziel_liefert_einen_leeren_block(klient):
    b, _s, _l = _aufbau(klient, woerter=2)
    ziel = klient.post("/api/lernziele", json={
        "benutzer_id": b["id"], "name": "Nichts",
        "umfang": {"lexeme": [999999]}}).json()
    block = klient.get(f"/api/lernziele/{ziel['id']}/block",
                       params={"benutzer_id": b["id"]}).json()
    assert block["anzahl"] == 0
    assert "nichts zu tun" in block["begruendung"]
    f = klient.get(f"/api/lernziele/{ziel['id']}/fortschritt",
                   params={"benutzer_id": b["id"]}).json()
    assert f["gesamt"] == 0 and f["anteil"] == 0.0


def test_lernziel_aendern_und_loeschen(klient):
    b, _s, _l = _aufbau(klient, woerter=2)
    ziel = klient.post("/api/lernziele", json={
        "benutzer_id": b["id"], "name": "Alt"}).json()
    geaendert = klient.patch(f"/api/lernziele/{ziel['id']}",
                             json={"name": "Neu", "ziel": "einmal_richtig"}).json()
    assert geaendert["name"] == "Neu" and geaendert["ziel"] == "einmal_richtig"
    assert klient.delete(f"/api/lernziele/{ziel['id']}").status_code == 204
    assert klient.get(f"/api/lernziele/{ziel['id']}").status_code == 404


def test_ziel_einmal_richtig_zaehlt_anders_als_reif(klient):
    b, _s, _l = _aufbau(klient, woerter=3)
    locker = klient.post("/api/lernziele", json={
        "benutzer_id": b["id"], "name": "Einmal gekonnt",
        "ziel": "einmal_richtig"}).json()
    streng = klient.post("/api/lernziele", json={
        "benutzer_id": b["id"], "name": "Sitzt dauerhaft", "ziel": "reif"}).json()
    block = klient.get(f"/api/lernziele/{locker['id']}/block",
                       params={"benutzer_id": b["id"], "anzahl": 3}).json()
    for a in block["aufgaben"]:
        klient.post("/api/lernen/bewerten", json={
            "benutzer_id": b["id"], "aufgabe_id": a["aufgabe_id"],
            "urteil": "richtig", "denkzeit_ms": 800})
    f_locker = klient.get(f"/api/lernziele/{locker['id']}/fortschritt",
                          params={"benutzer_id": b["id"]}).json()
    f_streng = klient.get(f"/api/lernziele/{streng['id']}/fortschritt",
                          params={"benutzer_id": b["id"]}).json()
    assert f_locker["geschafft"] == 3
    assert f_streng["geschafft"] < f_locker["geschafft"]


def test_wackliges_kommt_auch_bei_rueckstand_dran(klient):
    """Der Wacklig-Anteil wird vor dem Neuen reserviert. Sonst bliebe er
    gerade dann leer, wenn er am wichtigsten ist: bei Rückstand braucht man
    viel Neues, und genau dann schleppt man die Lücken mit."""
    import datetime as dt
    b, s, _l = _aufbau(klient, woerter=40)
    ziel = klient.post("/api/lernziele", json={
        "benutzer_id": b["id"], "name": "Viel vor",
        "termin": (dt.date.today() + dt.timedelta(days=5)).isoformat()}).json()

    # Ein paar Aufgaben wacklig machen: gelernt, aber mehrfach daneben,
    # und auf einen Termin in der Zukunft gesetzt.
    erste = klient.get(f"/api/lernziele/{ziel['id']}/block",
                       params={"benutzer_id": b["id"], "anzahl": 4}).json()
    for a in erste["aufgaben"]:
        for _ in range(3):
            klient.post("/api/lernen/bewerten", json={
                "benutzer_id": b["id"], "aufgabe_id": a["aufgabe_id"],
                "urteil": "falsch"})
        klient.post("/api/lernen/bewerten", json={
            "benutzer_id": b["id"], "aufgabe_id": a["aufgabe_id"],
            "urteil": "richtig", "denkzeit_ms": 900})
        klient.post("/api/lernen/termin", json={
            "benutzer_id": b["id"], "aufgabe_id": a["aufgabe_id"],
            "datum": (dt.date.today() + dt.timedelta(days=20)).isoformat()})

    block = klient.get(f"/api/lernziele/{ziel['id']}/block",
                       params={"benutzer_id": b["id"], "anzahl": 20}).json()
    assert block["zusammensetzung"]["wacklig"] > 0, block["zusammensetzung"]
    assert block["zusammensetzung"]["neu"] > 0
    assert "wacklig" in block["begruendung"]


def test_block_bleibt_bei_grossem_bestand_schnell(klient):
    """Der Zuschnitt darf nicht quadratisch sein — bei fünfzehn Zeiten je
    französischem Verb sind einige tausend Aufgaben schnell erreicht."""
    import time
    b, s, _l = _aufbau(klient, woerter=250)        # 500 Aufgaben
    ziel = klient.post("/api/lernziele", json={
        "benutzer_id": b["id"], "name": "Alles"}).json()
    begonnen = time.perf_counter()
    for _ in range(5):
        klient.get(f"/api/lernziele/{ziel['id']}/block",
                   params={"benutzer_id": b["id"], "anzahl": 20})
    dauer = (time.perf_counter() - begonnen) / 5
    assert dauer < 0.5, f"{dauer * 1000:.0f} ms je Block"


def test_ungueltiger_termin_wird_abgelehnt(klient):
    """Das Muster allein lässt 2026-13-45 durch — ein solches Ziel wäre
    danach dauerhaft unbenutzbar."""
    b, _s, _l = _aufbau(klient, woerter=1)
    assert klient.post("/api/lernziele", json={
        "benutzer_id": b["id"], "name": "Kaputt",
        "termin": "2026-13-45"}).status_code == 422
    ziel = klient.post("/api/lernziele", json={
        "benutzer_id": b["id"], "name": "Gut"}).json()
    assert klient.patch(f"/api/lernziele/{ziel['id']}",
                        json={"termin": "2026-02-30"}).status_code == 422
    # und das Ziel ist danach weiterhin benutzbar
    assert klient.get(f"/api/lernziele/{ziel['id']}/fortschritt",
                      params={"benutzer_id": b["id"]}).status_code == 200


def test_ein_verbstamm_zaehlt_als_ein_wort(klient):
    """Der Einwand aus dem Betrieb: ein griechisches Verb bringt vierzig
    Formen mit. Zählte jede als eigenes »neues Wort«, wäre ein Tagesvorrat
    von zwanzig nach einem halben Verb aufgebraucht — und man übte einen
    Tag lang nichts als dessen Präsens.
    """
    b = klient.post("/api/benutzer", json={"name": "Vielformige"}).json()
    s = klient.post("/api/sammlungen", json={
        "besitzer_id": b["id"], "name": "Griechisch", "sprache": "el"}).json()
    P = [("1", "sg"), ("2", "sg"), ("3", "sg"),
         ("1", "pl"), ("2", "pl"), ("3", "pl")]

    def verb(stamm, b1, b2):
        formen = []
        for zeit, endungen in (("praesens", ["ω", "εις", "ει", "ουμε", "ετε", "ουν"]),
                               ("aorist", ["α", "ες", "ε", "αμε", "ατε", "αν"])):
            for e, (pp, nn) in zip(endungen, P):
                formen.append({"text": stamm + e, "merkmale": {
                    "modus": "indikativ", "tempus": zeit,
                    "person": pp, "numerus": nn}})
        return {"lemma": stamm + "ω", "wortart": "verb", "lektion_nr": 1,
                "bedeutungen": [{"uebersetzungen": [b1, b2]}],
                "formen": formen}

    klient.post(f"/api/sammlungen/{s['id']}/import/vokabeln", json={
        "eintraege": [verb("γράφ", "schreiben", "aufschreiben"),
                      verb("διαβάζ", "lesen", "vorlesen"),
                      verb("παίζ", "spielen", "aufführen")]})
    klient.post(f"/api/sammlungen/{s['id']}/freigabe", json={"lektion_nr": 1})

    # Zwölf Formen je Verb, drei Verben — aber nur drei WÖRTER.
    aufgaben = klient.get("/api/lernen/naechste", params={
        "benutzer_id": b["id"], "sammlung_id": s["id"], "anzahl": 12}).json()
    assert len(aufgaben) == 12
    woerter = [a["lexem_id"] for a in aufgaben]
    # Alle drei Verben kommen vor, und nicht zwölfmal dasselbe.
    assert len(set(woerter)) == 3, woerter
    # Und zwei aufeinanderfolgende Aufgaben gehören selten zum selben Wort.
    gleich = sum(1 for i in range(1, len(woerter))
                 if woerter[i] == woerter[i - 1])
    assert gleich <= 2, woerter


def test_der_tagesvorrat_zaehlt_woerter_nicht_formen(klient):
    """»20 neue Wörter am Tag« heißt 20 Wörter, auch wenn eines davon
    vierzig Formen hat."""
    b = klient.post("/api/benutzer", json={"name": "Zählerin"}).json()
    klient.patch(f"/api/benutzer/{b['id']}", json={"neu_je_sitzung": 2})
    s = klient.post("/api/sammlungen", json={
        "besitzer_id": b["id"], "name": "Griechisch", "sprache": "el"}).json()
    P = [("1", "sg"), ("2", "sg"), ("3", "sg"),
         ("1", "pl"), ("2", "pl"), ("3", "pl")]
    eintraege = []
    for stamm, b1, b2 in (("γράφ", "schreiben", "aufschreiben"),
                          ("διαβάζ", "lesen", "vorlesen"),
                          ("παίζ", "spielen", "aufführen")):
        eintraege.append({
            "lemma": stamm + "ω", "wortart": "verb", "lektion_nr": 1,
            "bedeutungen": [{"uebersetzungen": [b1, b2]}],
            "formen": [{"text": stamm + e, "merkmale": {
                "modus": "indikativ", "tempus": "praesens",
                "person": pp, "numerus": nn}}
                for e, (pp, nn) in zip(
                    ["ω", "εις", "ει", "ουμε", "ετε", "ουν"], P)]})
    klient.post(f"/api/sammlungen/{s['id']}/import/vokabeln",
                json={"eintraege": eintraege})
    klient.post(f"/api/sammlungen/{s['id']}/freigabe", json={"lektion_nr": 1})

    aufgaben = klient.get("/api/lernen/naechste", params={
        "benutzer_id": b["id"], "sammlung_id": s["id"], "anzahl": 40}).json()
    woerter = {a["lexem_id"] for a in aufgaben}
    # Zwei Wörter, aber deren sämtliche Aufgaben — nicht zwei Aufgaben.
    assert len(woerter) == 2, woerter
    assert len(aufgaben) > 2, len(aufgaben)


def test_ein_geloeschtes_lernziel_nimmt_keinen_lernstand_mit(klient):
    """»Wenn ich die mal lösche, sind sie ja quasi weg.«

    Sind sie nicht. Der Fortschritt eines Lernziels ist nirgends
    gespeichert — er wird bei jedem Aufruf aus dem Lernstand
    gerechnet. Gelöscht wird nur das Ziel selbst: Name, Ausschnitt,
    Termin. Jede beantwortete Aufgabe bleibt.
    """
    import sys
    sys.path.insert(0, "backend")
    import datenbank as dbm

    b = klient.post("/api/benutzer", json={"name": "Lernende"}).json()
    s = klient.post("/api/sammlungen", json={
        "besitzer_id": b["id"], "name": "Griechisch", "sprache": "el"}).json()
    klient.post(f"/api/sammlungen/{s['id']}/import/vokabeln", json={
        "eintraege": [{"lemma": "το σπίτι", "wortart": "substantiv",
                       "merkmale": {"genus": "n"},
                       "bedeutungen": [{"uebersetzungen": ["das Haus"]}]}]})
    ziel = klient.post("/api/lernziele", json={
        "benutzer_id": b["id"], "name": "Test",
        "umfang": {"sammlungen": [s["id"]]}}).json()

    aufgabe = klient.get("/api/lernen/naechste", params={
        "benutzer_id": b["id"], "anzahl": 1}).json()[0]
    klient.post("/api/lernen/bewerten", json={
        "benutzer_id": b["id"], "aufgabe_id": aufgabe["aufgabe_id"],
        "bewertung": 4})

    db = dbm.verbindung()
    try:
        vorher = {t: dbm.wert(db, f"SELECT COUNT(*) FROM {t}")
                  for t in ("lernzustand", "wiederholung", "aufgabe", "lexem")}
    finally:
        db.close()

    assert klient.delete(f"/api/lernziele/{ziel['id']}").status_code == 204

    db = dbm.verbindung()
    try:
        nachher = {t: dbm.wert(db, f"SELECT COUNT(*) FROM {t}")
                   for t in ("lernzustand", "wiederholung", "aufgabe", "lexem")}
        assert dbm.wert(db, "SELECT COUNT(*) FROM lernziel") == 0
    finally:
        db.close()
    assert nachher == vorher, "das Löschen hat Lernstand mitgenommen"

    # Und die allgemeine Statistik weiß weiterhin davon.
    stat = klient.get("/api/statistik", params={"benutzer_id": b["id"]}).json()
    assert stat["gesamt"]["antworten"] >= 1


# ------------------------------------------- Ein leeres Ziel sagt warum

def _franzoesisch(klient, typen=None):
    b = klient.post("/api/benutzer", json={"name": "Lernende 1"}).json()
    s = klient.post("/api/sammlungen", json={
        "besitzer_id": b["id"], "name": "Französisch", "sprache": "fr"}).json()
    if typen is not None:
        klient.put(f"/api/sammlungen/{s['id']}/einstellungen",
                   json={"typen": typen})
    klient.post(f"/api/sammlungen/{s['id']}/import/vokabeln", json={
        "eintraege": [{"lemma": "travailler", "wortart": "verb",
                       "bedeutungen": [{"uebersetzungen": ["arbeiten"]}],
                       "formen": [{"text": "travaille", "merkmale": {
                           "modus": "indikativ", "tempus": "praesens",
                           "person": "1", "numerus": "sg"}}]}]})
    return b, s


def test_ein_lernziel_das_nichts_trifft_sagt_warum(klient):
    """»Es kommen aber keine Übungen, obwohl eigentlich 19 Verben da
    sein sollten.«

    Das Ziel stand mit »0 von 0« da und sagte kein Wort dazu. Der Grund
    war, dass die Sammlung die verlangte Aufgabenart gar nicht erzeugt:
    sie war auf Vokabeln beschränkt, »Ganze Reihe« stand nicht darin.

    Das ist die Eigenschaft, über die man stolpert — ein Lernziel
    SCHRÄNKT EIN, es erzeugt nicht. Ein Ausschnitt aus nichts bleibt
    nichts, und das muss dastehen.
    """
    b, s = _franzoesisch(klient, typen=["bedeutung_fremd_deutsch",
                                        "bedeutung_deutsch_fremd"])
    ziel = klient.post("/api/lernziele", json={
        "benutzer_id": b["id"], "name": "verben",
        "umfang": {"sammlungen": [s["id"]], "wortarten": ["verb"],
                   "typen": ["formenreihe"]}}).json()
    f = klient.get(f"/api/lernziele/{ziel['id']}/fortschritt",
                   params={"benutzer_id": b["id"]}).json()

    assert f["gesamt"] == 0
    assert f["warum_leer"], "ein leeres Ziel muss sagen, warum"
    grund = " ".join(f["warum_leer"])
    assert "Ganze Reihe" in grund, grund
    assert "schränkt" in grund or "erzeugt" in grund, grund


def test_ein_ziel_mit_inhalt_erklaert_nichts(klient):
    """Keine Erklärung, wo es nichts zu erklären gibt — und keine vier
    Abfragen dafür."""
    b, s = _franzoesisch(klient)
    ziel = klient.post("/api/lernziele", json={
        "benutzer_id": b["id"], "name": "alles",
        "umfang": {"sammlungen": [s["id"]]}}).json()
    f = klient.get(f"/api/lernziele/{ziel['id']}/fortschritt",
                   params={"benutzer_id": b["id"]}).json()
    assert f["gesamt"] > 0
    assert f["warum_leer"] == []


def test_ein_ausschnitt_ohne_wort_sagt_das_zuerst(klient):
    """Der äußere Grund gewinnt: wo kein Wort ist, nützt die Auskunft
    über Aufgabenarten nichts."""
    b, s = _franzoesisch(klient)
    ziel = klient.post("/api/lernziele", json={
        "benutzer_id": b["id"], "name": "Hauptwörter",
        "umfang": {"sammlungen": [s["id"]], "wortarten": ["substantiv"],
                   "typen": ["formenreihe"]}}).json()
    f = klient.get(f"/api/lernziele/{ziel['id']}/fortschritt",
                   params={"benutzer_id": b["id"]}).json()
    assert "Kein Wort" in " ".join(f["warum_leer"]), f["warum_leer"]
