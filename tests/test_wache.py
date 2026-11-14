"""Zugriffsprüfung der Web-Schnittstelle.

Dass die Oberfläche nur die eigenen Sammlungen anzeigt, ist keine
Absicherung. Diese Tests prüfen, dass es auch durchgesetzt wird — sobald
jemand von außen über Cloudflare Access hereinkommt.
"""

import pytest


@pytest.fixture()
def mit_access(monkeypatch):
    """Tut so, als stünde Cloudflare Access davor."""
    import identitaet
    import wache
    monkeypatch.setattr(identitaet, "TEAM", "probe.cloudflareaccess.com")
    monkeypatch.setattr(wache.identitaet, "TEAM", "probe.cloudflareaccess.com")


def als(mail):
    return {"Cf-Access-Authenticated-User-Email": mail}


def test_im_heimnetz_greift_die_wache_nicht(klient):
    """Ohne geprüfte Identität bleibt alles wie bisher — dort wählt man sein
    Profil aus einer Liste, und das ist gewollt."""
    a = klient.post("/api/benutzer", json={"name": "A"}).json()
    s = klient.post("/api/sammlungen", json={
        "besitzer_id": a["id"], "name": "As Sammlung", "sprache": "fr"}).json()
    b = klient.post("/api/benutzer", json={"name": "B"}).json()
    # B darf im Heimnetz auf As Sammlung — so war es immer.
    assert klient.get(f"/api/sammlungen/{s['id']}/lexeme").status_code == 200
    assert klient.get("/api/lernen/stand",
                      params={"benutzer_id": b["id"]}).status_code == 200


def test_profil_entsteht_bei_der_ersten_anfrage(klient, mit_access):
    antwort = klient.get("/api/ich", headers=als("maxi.brenner@example.de"))
    d = antwort.json()
    assert d["gebunden"] is True
    assert d["email"] == "maxi.brenner@example.de"
    assert d["benutzer"]["name"] == "Maxi Brenner"
    # Beim zweiten Mal dasselbe Profil, nicht ein neues
    zweite = klient.get("/api/ich", headers=als("maxi.brenner@example.de")).json()
    assert zweite["benutzer"]["id"] == d["benutzer"]["id"]


def test_eine_einladung_zieht_kein_bestehendes_profil_an_sich(klient, mit_access):
    """Sonst könnte eine Einladung an anna@... das Familienprofil »Anna«
    übernehmen."""
    familie = klient.post("/api/benutzer", json={"name": "Anna"}).json()
    neu = klient.get("/api/ich", headers=als("anna@example.de")).json()
    assert neu["benutzer"]["id"] != familie["id"]
    assert neu["benutzer"]["name"] != "Anna"


def test_fremde_sammlung_ist_nicht_lesbar(klient, mit_access):
    chefin = klient.get("/api/ich", headers=als("chefin@example.de")).json()["benutzer"]
    s = klient.post("/api/sammlungen",
                    headers=als("chefin@example.de"),
                    json={"besitzer_id": chefin["id"], "name": "Privat",
                          "sprache": "fr"}).json()
    # Der Gast kennt die Kennung — er kommt trotzdem nicht dran.
    antwort = klient.get(f"/api/sammlungen/{s['id']}/lexeme",
                         headers=als("gast@example.de"))
    assert antwort.status_code == 403
    assert "gehört dir nicht" in antwort.json()["detail"]


def test_fremdes_lexem_ist_nicht_lesbar(klient, mit_access):
    chefin = klient.get("/api/ich", headers=als("chefin@example.de")).json()["benutzer"]
    s = klient.post("/api/sammlungen", headers=als("chefin@example.de"),
                    json={"besitzer_id": chefin["id"], "name": "Privat",
                          "sprache": "fr"}).json()
    lexem = klient.post("/api/lexeme", headers=als("chefin@example.de"),
                        json={"sammlung_id": s["id"], "lemma": "aller",
                              "wortart": "verb",
                              "bedeutungen": [{"uebersetzungen": [{"text": "gehen"}]}]}).json()
    assert klient.get(f"/api/lexeme/{lexem['id']}",
                      headers=als("gast@example.de")).status_code == 403
    assert klient.delete(f"/api/lexeme/{lexem['id']}",
                         headers=als("gast@example.de")).status_code == 403


def test_in_fremde_sammlung_laesst_sich_nicht_schreiben(klient, mit_access):
    chefin = klient.get("/api/ich", headers=als("chefin@example.de")).json()["benutzer"]
    s = klient.post("/api/sammlungen", headers=als("chefin@example.de"),
                    json={"besitzer_id": chefin["id"], "name": "Privat",
                          "sprache": "fr"}).json()
    antwort = klient.post("/api/lexeme", headers=als("gast@example.de"),
                          json={"sammlung_id": s["id"], "lemma": "x",
                                "wortart": "verb", "bedeutungen": []})
    assert antwort.status_code == 403


def test_niemand_handelt_in_fremdem_namen(klient, mit_access):
    chefin = klient.get("/api/ich", headers=als("chefin@example.de")).json()["benutzer"]
    antwort = klient.get("/api/lernen/stand", headers=als("gast@example.de"),
                         params={"benutzer_id": chefin["id"]})
    assert antwort.status_code == 403
    assert "eigenen Namen" in antwort.json()["detail"]


def test_fremdes_profil_ist_nicht_aenderbar(klient, mit_access):
    chefin = klient.get("/api/ich", headers=als("chefin@example.de")).json()["benutzer"]
    assert klient.patch(f"/api/benutzer/{chefin['id']}",
                        headers=als("gast@example.de"),
                        json={"name": "Gekapert"}).status_code == 403


def test_fremde_zugangsmerkmale_sind_unerreichbar(klient, mit_access):
    chefin = klient.get("/api/ich", headers=als("chefin@example.de")).json()["benutzer"]
    token = klient.post(f"/api/benutzer/{chefin['id']}/mcp-token",
                        headers=als("chefin@example.de"),
                        json={"name": "iPad"}).json()
    assert klient.delete(f"/api/mcp-token/{token['id']}",
                         headers=als("gast@example.de")).status_code == 403
    assert klient.delete(f"/api/mcp-token/{token['id']}",
                         headers=als("chefin@example.de")).status_code == 204


def test_nur_verwalter_duerfen_sprachprofile_aendern(klient, mit_access):
    # Die erste Person ist Verwalterin
    klient.get("/api/ich", headers=als("chefin@example.de"))
    klient.get("/api/ich", headers=als("gast@example.de"))
    gut = klient.put("/api/sprachen/fr/profil", headers=als("chefin@example.de"),
                     json={"profil": {"pruefung": {"diakritika": "streng"}}})
    schlecht = klient.put("/api/sprachen/fr/profil", headers=als("gast@example.de"),
                          json={"profil": {"pruefung": {"diakritika": "hinweis"}}})
    assert gut.status_code == 200
    assert schlecht.status_code == 403
    assert "Verwalter" in schlecht.json()["detail"]


def test_stammdaten_bleiben_fuer_alle_offen(klient, mit_access):
    """Sprachen und Merkmale sind kein Geheimnis."""
    for pfad in ("/api/sprachen", "/api/merkmale", "/api/aufgabentypen",
                 "/api/sprachen/fr/formgruppen"):
        assert klient.get(pfad, headers=als("gast@example.de")).status_code == 200


def test_eigenes_bleibt_erreichbar(klient, mit_access):
    """Die Wache darf nicht den eigenen Bestand sperren."""
    ich = klient.get("/api/ich", headers=als("ich@example.de")).json()["benutzer"]
    kopf = als("ich@example.de")
    s = klient.post("/api/sammlungen", headers=kopf,
                    json={"besitzer_id": ich["id"], "name": "Meins",
                          "sprache": "fr"}).json()
    lexem = klient.post("/api/lexeme", headers=kopf,
                        json={"sammlung_id": s["id"], "lemma": "aller",
                              "wortart": "verb",
                              "bedeutungen": [{"uebersetzungen": [{"text": "gehen"}]}]})
    assert lexem.status_code == 201
    assert klient.get(f"/api/sammlungen/{s['id']}/lexeme",
                      headers=kopf).status_code == 200
    assert klient.get("/api/lernen/stand", headers=kopf,
                      params={"benutzer_id": ich["id"]}).status_code == 200
    assert klient.get(f"/api/lexeme/{lexem.json()['id']}",
                      headers=kopf).status_code == 200


def test_ohne_teamkennung_wird_die_kopfzeile_ignoriert(klient):
    """Nicht gesetzt heißt: gar nicht erst ansehen. Sonst könnte im Heimnetz
    jemand die Kopfzeile selbst mitschicken und sich ausgeben."""
    d = klient.get("/api/ich", headers=als("fremd@example.de")).json()
    assert d["gebunden"] is False and d["benutzer"] is None
