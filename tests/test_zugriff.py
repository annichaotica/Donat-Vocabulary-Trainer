"""Wer darf eine Sammlung mitbenutzen.

Nicht zu verwechseln mit der Freigabe von FORMEN — hier geht es um
Menschen. Der entscheidende Punkt: der Lernstand hängt an der Person, nicht
an der Sammlung. Wer mitlernt, fängt mit seinem eigenen Fortschritt an, und
das ist der Sinn der Sache — die Mutter pflegt die Vokabeln, das Kind lernt
sie.
"""


def _aufbau(klient):
    mutter = klient.post("/api/benutzer", json={"name": "Lernender 1"}).json()
    kind = klient.post("/api/benutzer", json={"name": "Lernender 2"}).json()
    s = klient.post("/api/sammlungen", json={
        "besitzer_id": mutter["id"], "name": "Französisch",
        "sprache": "fr"}).json()
    klient.post(f"/api/sammlungen/{s['id']}/import/vokabeln", json={
        "eintraege": [{"lemma": "la maison", "wortart": "substantiv",
                       "merkmale": {"genus": "f"},
                       "bedeutungen": [{"uebersetzungen": ["das Haus",
                                                           "das Zuhause"]}]}]})
    return mutter, kind, s


def sammlungen(klient, benutzer_id):
    return klient.get("/api/sammlungen",
                      params={"benutzer_id": benutzer_id}).json()


def test_ohne_freigabe_sieht_das_kind_nichts(klient):
    _mutter, kind, _s = _aufbau(klient)
    assert sammlungen(klient, kind["id"]) == []


def test_mitlernen_freigeben(klient):
    mutter, kind, s = _aufbau(klient)
    z = klient.put(f"/api/sammlungen/{s['id']}/zugriff", json={
        "benutzer_id": kind["id"], "recht": "lesen"}).json()
    assert z["besitzer"]["name"] == "Lernender 1"
    assert [(m["name"], m["recht"]) for m in z["mitlernende"]] \
        == [("Lernender 2", "lesen")]

    meine = sammlungen(klient, kind["id"])
    assert [x["name"] for x in meine] == ["Französisch"]
    # Fremd, aber benutzbar.
    assert meine[0]["eigen"] == 0
    # Bei der Mutter steht sie weiter als eigene.
    assert sammlungen(klient, mutter["id"])[0]["eigen"] == 1


def test_der_lernstand_ist_je_person_eigen(klient):
    """Der eigentliche Grund, warum Mitlernen und nicht Kopieren: beide
    lernen dieselben Vokabeln, jede mit ihrem eigenen Fortschritt."""
    mutter, kind, s = _aufbau(klient)
    klient.put(f"/api/sammlungen/{s['id']}/zugriff",
               json={"benutzer_id": kind["id"], "recht": "lesen"})
    aufgabe = klient.get("/api/lernen/naechste", params={
        "benutzer_id": mutter["id"], "sammlung_id": s["id"],
        "anzahl": 1}).json()[0]
    klient.post("/api/lernen/bewerten", json={
        "benutzer_id": mutter["id"], "aufgabe_id": aufgabe["aufgabe_id"],
        "bewertung": 3})

    bei_mutter = klient.get("/api/lernen/stand", params={
        "benutzer_id": mutter["id"], "sammlung_id": s["id"]}).json()
    beim_kind = klient.get("/api/lernen/stand", params={
        "benutzer_id": kind["id"], "sammlung_id": s["id"]}).json()
    assert bei_mutter["heute_erledigt"] == 1
    assert beim_kind["heute_erledigt"] == 0
    assert beim_kind["neu"] == bei_mutter["gesamt"]


def test_besitz_uebertragen(klient):
    """»Das Französisch an Lernender 2 übertragen« — und trotzdem weiter
    pflegen können."""
    mutter, kind, s = _aufbau(klient)
    z = klient.post(f"/api/sammlungen/{s['id']}/besitz", json={
        "benutzer_id": kind["id"], "bisherige_behaelt_zugriff": True}).json()
    assert z["besitzer"]["name"] == "Lernender 2"
    assert [(m["name"], m["recht"]) for m in z["mitlernende"]] \
        == [("Lernender 1", "schreiben")]
    # Beide sehen sie weiterhin, mit vertauschten Rollen.
    assert sammlungen(klient, kind["id"])[0]["eigen"] == 1
    assert sammlungen(klient, mutter["id"])[0]["eigen"] == 0


def test_besitz_uebertragen_ohne_zugriff_zu_behalten(klient):
    mutter, kind, s = _aufbau(klient)
    klient.post(f"/api/sammlungen/{s['id']}/besitz", json={
        "benutzer_id": kind["id"], "bisherige_behaelt_zugriff": False})
    assert sammlungen(klient, mutter["id"]) == []


def test_zugriff_entziehen_laesst_den_lernstand_stehen(klient):
    """Falls man es sich anders überlegt, soll nicht alles verloren sein."""
    mutter, kind, s = _aufbau(klient)
    klient.put(f"/api/sammlungen/{s['id']}/zugriff",
               json={"benutzer_id": kind["id"], "recht": "lesen"})
    aufgabe = klient.get("/api/lernen/naechste", params={
        "benutzer_id": kind["id"], "sammlung_id": s["id"],
        "anzahl": 1}).json()[0]
    klient.post("/api/lernen/bewerten", json={
        "benutzer_id": kind["id"], "aufgabe_id": aufgabe["aufgabe_id"],
        "bewertung": 3})
    klient.put(f"/api/sammlungen/{s['id']}/zugriff",
               json={"benutzer_id": kind["id"], "recht": None})
    assert sammlungen(klient, kind["id"]) == []

    klient.put(f"/api/sammlungen/{s['id']}/zugriff",
               json={"benutzer_id": kind["id"], "recht": "lesen"})
    stand = klient.get("/api/lernen/stand", params={
        "benutzer_id": kind["id"], "sammlung_id": s["id"]}).json()
    assert stand["heute_erledigt"] == 1, "der Lernstand war weg"


def test_der_besitzerin_gibt_man_nichts_frei(klient):
    mutter, _kind, s = _aufbau(klient)
    antwort = klient.put(f"/api/sammlungen/{s['id']}/zugriff",
                         json={"benutzer_id": mutter["id"], "recht": "lesen"})
    assert antwort.status_code == 400
    assert "Besitzerin" in antwort.json()["detail"]
