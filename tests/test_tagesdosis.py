"""Der Tag hat ein Ende.

Der Einwand aus dem Betrieb: »die Mauer klingt bedrohlich, man möchte ja
vorankommen«. Angezeigt waren 445 Fragen für einen Tag — entstanden, weil
nur der Nachschub an neuen Wörtern gedeckelt war, die Wiederholungen aber
nicht. Nach ein paar Tagen Pause wächst daraus eine Zahl, vor der man
aufgibt.

Zwei Eigenschaften muss die Grenze haben, und die zweite ist die
schwierigere: der Tag muss ein Ende haben, UND es muss trotz Rückstand
jeden Tag vorangehen. Eine Grenze ohne Reserve fürs Neue wäre Stillstand
— Fälliges steht in der Reihenfolge vorn und käme bei vierhundert offenen
Wiederholungen wochenlang nicht ans Neue heran.
"""

import datetime as dt

P = [("1", "sg"), ("2", "sg"), ("3", "sg"), ("1", "pl"), ("2", "pl"), ("3", "pl")]
ENDUNGEN = ["ω", "εις", "ει", "ουμε", "ετε", "ουν"]
VERBEN = [("γράφ", "schreiben"), ("διαβάζ", "lesen"), ("παίζ", "spielen"),
          ("τρέχ", "laufen"), ("μιλ", "sprechen"), ("ακού", "hören"),
          ("μέν", "bleiben"), ("βλέπ", "sehen")]


def _bestand(klient):
    b = klient.post("/api/benutzer", json={"name": "Übende"}).json()
    s = klient.post("/api/sammlungen", json={
        "besitzer_id": b["id"], "name": "Griechisch", "sprache": "el"}).json()
    klient.post(f"/api/sammlungen/{s['id']}/import/vokabeln", json={
        "eintraege": [{
            "lemma": stamm + "ω", "wortart": "verb", "lektion_nr": 1,
            "reihenfolge": i,
            "bedeutungen": [{"uebersetzungen": [bed]}],
            "formen": [{"text": stamm + e, "merkmale": {
                "modus": "indikativ", "tempus": "praesens",
                "person": p, "numerus": n}}
                for e, (p, n) in zip(ENDUNGEN, P)]}
            for i, (stamm, bed) in enumerate(VERBEN)]})
    klient.post(f"/api/sammlungen/{s['id']}/freigabe", json={"lektion_nr": 1})
    return b, s


def _dosis(klient, b, wieviel):
    antwort = klient.patch(f"/api/benutzer/{b['id']}",
                           json={"fragen_je_tag": wieviel})
    assert antwort.status_code == 200, antwort.text


def _runde(klient, b, s, runden, **zusatz):
    """Spielt eine Sitzung, wie ein Mensch sie geht."""
    gestellt = []
    for _ in range(runden):
        liste = klient.get("/api/lernen/naechste", params={
            "benutzer_id": b["id"], "sammlung_id": s["id"], "anzahl": 1,
            **zusatz}).json()
        if not liste:
            break
        a = liste[0]
        gestellt.append(a)
        klient.post("/api/lernen/bewerten", json={
            "benutzer_id": b["id"], "aufgabe_id": a["aufgabe_id"],
            "bewertung": 3})
    return gestellt


def test_der_tag_hoert_bei_der_dosis_auf(klient):
    b, s = _bestand(klient)
    _dosis(klient, b, 12)
    assert len(_runde(klient, b, s, 40)) == 12


def test_ohne_grenze_geht_weiter_wer_will(klient):
    """Die Grenze ist ein Vorschlag, kein Schloss."""
    b, s = _bestand(klient)
    _dosis(klient, b, 12)
    _runde(klient, b, s, 40)
    weiter = _runde(klient, b, s, 10, ohne_grenze=True)
    assert len(weiter) == 10


def test_null_heisst_ohne_grenze(klient):
    b, s = _bestand(klient)
    _dosis(klient, b, 0)
    assert len(_runde(klient, b, s, 30)) == 30


def test_freies_ueben_kennt_keine_grenze(klient):
    """Wer ausdrücklich freies Üben wählt, hat sich schon entschieden."""
    b, s = _bestand(klient)
    _dosis(klient, b, 5)
    _runde(klient, b, s, 20)
    assert len(_runde(klient, b, s, 8, nur="frei")) == 8


def test_bei_rueckstand_kommt_trotzdem_neues(klient, monkeypatch):
    """Der eigentliche Punkt: vorankommen trotz Rückstand.

    Erst ein Tag Lernen, dann vierzig Tage Pause — alles Gelernte ist
    überfällig und stünde in der Reihenfolge vor jedem neuen Wort. Ohne
    die Reserve käme an diesem Tag ausschließlich Rückstand.
    """
    import lernen
    b, s = _bestand(klient)
    _dosis(klient, b, 20)
    _runde(klient, b, s, 20)                      # Tag 1: zwanzig Fragen

    spaeter = dt.date.today() + dt.timedelta(days=40)
    monkeypatch.setattr(lernen, "heute", lambda: spaeter)
    monkeypatch.setattr(lernen, "_jetzt",
                        lambda: dt.datetime.combine(
                            spaeter, dt.time(9, 0)).isoformat(timespec="seconds"))

    stand = klient.get("/api/lernen/stand", params={
        "benutzer_id": b["id"], "sammlung_id": s["id"]}).json()
    assert stand["faellig"] >= 15, "der Rückstand muss echt sein"

    gestellt = _runde(klient, b, s, 20)
    assert len(gestellt) == 20
    neu = [a for a in gestellt if a["lernstand"]["zustand"] == "neu"]
    assert neu, "trotz Rückstand muss Neues drankommen"
    assert len(neu) >= 6, f"zu wenig Neues: {len(neu)} von 20"
    assert len(neu) <= 14, f"der Rückstand kommt zu kurz: {len(neu)} von 20"


def test_stand_zeigt_das_pensum_und_den_rueckstand_getrennt(klient,
                                                            monkeypatch):
    """Angezeigt wird, was heute drankommt — der Rest steht daneben."""
    import lernen
    b, s = _bestand(klient)
    _dosis(klient, b, 10)
    _runde(klient, b, s, 10)
    spaeter = dt.date.today() + dt.timedelta(days=40)
    monkeypatch.setattr(lernen, "heute", lambda: spaeter)

    stand = klient.get("/api/lernen/stand", params={
        "benutzer_id": b["id"], "sammlung_id": s["id"]}).json()
    assert stand["tagesdosis"] == 10
    assert stand["heute_gesamt"] == 10
    assert stand["heute_offen"] == 10
    assert stand["rueckstand"] > 0, "der Rest darf nicht verschwinden"
