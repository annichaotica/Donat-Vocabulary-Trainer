

def test_nur_wiederholen_bringt_nichts_neues(klient):
    """»Haben wir eigentlich auch eine Art Wiederholungsmodus?«

    Der Unterschied zum planmäßigen Lernen ist nicht kosmetisch: dort
    kommt Neues dazu, sobald Platz ist. Wer vor einer Arbeit steht
    oder wenig Zeit hat, will genau das nicht — er will festigen, was
    schon angefangen ist.
    """
    b = klient.post("/api/benutzer", json={"name": "Wiederholende"}).json()
    s = klient.post("/api/sammlungen", json={
        "besitzer_id": b["id"], "name": "Griechisch", "sprache": "el"}).json()
    klient.post(f"/api/sammlungen/{s['id']}/import/vokabeln", json={
        "eintraege": [{"lemma": f"wort{i}", "wortart": "substantiv",
                       "bedeutungen": [{"uebersetzungen": [f"Wort {i}"]}]}
                      for i in range(6)]})

    # Eine Aufgabe anfangen, damit es überhaupt etwas Fälliges gibt.
    erste = klient.get("/api/lernen/naechste", params={
        "benutzer_id": b["id"], "sammlung_id": s["id"], "anzahl": 1}).json()[0]
    klient.post("/api/lernen/bewerten", json={
        "benutzer_id": b["id"], "aufgabe_id": erste["aufgabe_id"],
        "bewertung": 1})          # »nochmal« — gleich wieder fällig

    planmaessig = klient.get("/api/lernen/naechste", params={
        "benutzer_id": b["id"], "sammlung_id": s["id"], "anzahl": 10}).json()
    wiederholen = klient.get("/api/lernen/naechste", params={
        "benutzer_id": b["id"], "sammlung_id": s["id"],
        "nur": "faellig", "anzahl": 10}).json()

    zustand = lambda a: (a["lernstand"] or {}).get("zustand")
    assert any(zustand(a) in (None, "neu") for a in planmaessig), \
        "planmäßig soll Neues mitbringen"
    assert wiederholen, "etwas Fälliges muss da sein"
    assert all(zustand(a) not in (None, "neu") for a in wiederholen), \
        f"Wiederholen brachte Neues mit: {[zustand(a) for a in wiederholen]}"
