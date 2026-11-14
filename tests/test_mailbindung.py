"""Welche Mailadresse zu welchem Profil gehört.

Aus dem Betrieb: »anmeldung geht, aber mir wird mein konto nicht
zugewiesen«. Die erste Anmeldung über Cloudflare Access legte ein
zweites, leeres Profil an — der eigene Lernstand war dadurch unsichtbar.

Das Anlegen ist richtig so (wer durch Access kommt, ist eingeladen; ihn
dann noch um eine Anmeldung zu bitten, wäre eine Hürde ohne Gewinn).
Falsch war nur, dass es keine Möglichkeit gab, die Adresse vorher an das
richtige Profil zu binden.
"""


def test_adresse_binden_und_wieder_loesen(klient):
    b = klient.post("/api/benutzer", json={"name": "Annuschka"}).json()
    klient.patch(f"/api/benutzer/{b['id']}", json={"email": "Anni@Example.de"})
    gelesen = klient.get(f"/api/benutzer/{b['id']}").json()
    assert gelesen["email"] == "anni@example.de", "klein geschrieben gespeichert"
    assert klient.get("/api/benutzer").json()[0]["hat_mail"] == 1

    klient.patch(f"/api/benutzer/{b['id']}", json={"email": ""})
    assert klient.get(f"/api/benutzer/{b['id']}").json()["email"] is None


def test_unsinn_wird_abgelehnt(klient):
    b = klient.post("/api/benutzer", json={"name": "Annuschka"}).json()
    antwort = klient.patch(f"/api/benutzer/{b['id']}", json={"email": "kein-at"})
    assert antwort.status_code == 400


def test_ein_leeres_doppelprofil_wird_abgeraeumt(klient):
    """Genau der Fall aus dem Betrieb: Access hat schon eines angelegt."""
    echt = klient.post("/api/benutzer", json={"name": "Annuschka"}).json()
    versehen = klient.post("/api/benutzer", json={"name": "Brenner Anni"}).json()
    klient.patch(f"/api/benutzer/{versehen['id']}",
                 json={"email": "lernende@beispiel.invalid"})

    antwort = klient.patch(f"/api/benutzer/{echt['id']}",
                           json={"email": "lernende@beispiel.invalid"})
    assert antwort.status_code == 200
    assert antwort.json()["email"] == "lernende@beispiel.invalid"
    # Das leere Profil ist weg, nicht bloß die Adresse daran.
    assert klient.get(f"/api/benutzer/{versehen['id']}").status_code == 404
    namen = [p["name"] for p in klient.get("/api/benutzer").json()]
    assert namen == ["Annuschka"]


def test_ein_profil_mit_lernstand_wird_nicht_still_abgeraeumt(klient):
    """Zwei Bestände zusammenzuführen ist nichts fürs Vorbeigehen."""
    echt = klient.post("/api/benutzer", json={"name": "Annuschka"}).json()
    anderer = klient.post("/api/benutzer", json={"name": "Zweit"}).json()
    klient.patch(f"/api/benutzer/{anderer['id']}", json={"email": "a@b.de"})
    # Der andere hat etwas: eine eigene Sammlung.
    klient.post("/api/sammlungen", json={
        "besitzer_id": anderer["id"], "name": "Seins", "sprache": "el"})

    antwort = klient.patch(f"/api/benutzer/{echt['id']}", json={"email": "a@b.de"})
    assert antwort.status_code == 409
    assert "Sammlungen" in antwort.json()["detail"]
    # Und nichts wurde angefasst.
    assert klient.get(f"/api/benutzer/{anderer['id']}").json()["email"] == "a@b.de"
    assert klient.get(f"/api/benutzer/{echt['id']}").json()["email"] is None


def test_dieselbe_adresse_am_selben_profil_stoert_nicht(klient):
    b = klient.post("/api/benutzer", json={"name": "Annuschka"}).json()
    klient.patch(f"/api/benutzer/{b['id']}", json={"email": "a@b.de"})
    antwort = klient.patch(f"/api/benutzer/{b['id']}", json={"email": "a@b.de"})
    assert antwort.status_code == 200
