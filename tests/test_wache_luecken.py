"""Die Löcher in der Wache, die eine Durchsicht am 14.11.2026 fand.

Alle hier geprüften Wege gingen an der Wache vorbei. Gemeinsame Ursache
sind drei blinde Flecken, nicht drei Einzelfehler:

1. **Die Wache sieht nur den Pfad.** Steht die Kennung nicht im Pfad,
   sondern im Rumpf (`aufgabe_id`, `benutzer_id`) oder im Abfrageteil
   (`sammlung_id`), greift kein Muster — und wer `aufgabe_id` aufwärts
   zählt, liest den ganzen Bestand aller Personen.
2. **`MUSTER` ist eine Liste, die mitwachsen muss.** Übungen und
   Textaufgaben kamen später dazu und wurden nicht eingetragen.
3. **`OFFEN` wurde vor allem anderen geprüft** — auch vor der Regel, die
   Anfragen ohne geprüfte Identität von außen abweist. Unter
   `/api/sprachen` liegen aber nicht nur Stammdaten zum Lesen.

Der Angreifer ist überall derselbe: ein eingeladener Gast von außen, der
in der Access-Regel steht und ein eigenes, leeres Profil hat. Was er
hier versucht, muss 403 geben.
"""

import pytest


@pytest.fixture()
def mit_access(monkeypatch):
    import identitaet
    import wache
    monkeypatch.setattr(identitaet, "TEAM", "probe.cloudflareaccess.com")
    monkeypatch.setattr(wache.identitaet, "TEAM", "probe.cloudflareaccess.com")


def als(mail):
    return {"Cf-Access-Authenticated-User-Email": mail}


def ueber_cloudflare(**weitere):
    return {"Cf-Ray": "a5a8b240482509e5-IAD", **weitere}


CHEFIN, GAST = "chefin@example.de", "gast@example.de"


@pytest.fixture()
def bestand(klient, mit_access):
    """Eine Sammlung der Chefin mit einem Wort, einer Form und einer Übung."""
    chefin = klient.get("/api/ich", headers=als(CHEFIN)).json()["benutzer"]
    s = klient.post("/api/sammlungen", headers=als(CHEFIN),
                    json={"besitzer_id": chefin["id"], "name": "Privat",
                          "sprache": "fr"}).json()
    klient.post(f"/api/sammlungen/{s['id']}/import/vokabeln", headers=als(CHEFIN),
                json={"eintraege": [{
                    "lemma": "aller", "wortart": "verb", "lektion_nr": 1,
                    "bedeutungen": [{"uebersetzungen": ["gehen"]}],
                    "formen": [{"text": "vais", "merkmale": {
                        "modus": "indikativ", "tempus": "praesens",
                        "person": "1", "numerus": "sg"}}]}]})
    klient.post(f"/api/sammlungen/{s['id']}/freigabe", headers=als(CHEFIN),
                json={"lektion_nr": 1})
    aufgaben = klient.get("/api/lernen/naechste", headers=als(CHEFIN),
                          params={"benutzer_id": chefin["id"],
                                  "sammlung_id": s["id"], "anzahl": 5}).json()
    # Der Gast bekommt sein Profil, damit er nicht erst dabei entsteht.
    gast = klient.get("/api/ich", headers=als(GAST)).json()["benutzer"]
    return {"chefin": chefin, "gast": gast, "sammlung": s,
            "aufgaben": aufgaben}


# ------------------------------------- 1. Kennung im Rumpf, nicht im Pfad

def test_fremde_aufgabe_laesst_sich_nicht_aufdecken(klient, bestand):
    """Der bequemste Weg zum ganzen Wortschatz: aufgabe_id hochzählen."""
    a = bestand["aufgaben"][0]
    antwort = klient.post("/api/lernen/aufdecken", headers=als(GAST),
                          json={"benutzer_id": bestand["gast"]["id"],
                                "aufgabe_id": a["aufgabe_id"]})
    assert antwort.status_code == 403, antwort.text


def test_fremde_aufgabe_laesst_sich_nicht_pruefen(klient, bestand):
    """Auch Raten gibt die Lösung preis: die Antwort nennt den Treffer."""
    a = bestand["aufgaben"][0]
    antwort = klient.post("/api/lernen/pruefen", headers=als(GAST),
                          json={"benutzer_id": bestand["gast"]["id"],
                                "aufgabe_id": a["aufgabe_id"],
                                "antwort": "irgendwas"})
    assert antwort.status_code == 403, antwort.text


def test_fremde_sammlung_laesst_sich_nicht_abfragen(klient, bestand):
    """sammlung_id im Abfrageteil wurde nie gegen den Zugang gehalten."""
    antwort = klient.get("/api/lernen/naechste", headers=als(GAST),
                         params={"benutzer_id": bestand["gast"]["id"],
                                 "sammlung_id": bestand["sammlung"]["id"],
                                 "nur": "frei", "anzahl": 50})
    assert antwort.status_code == 403, antwort.text


def test_fremder_lernstand_ist_nicht_einsehbar(klient, bestand):
    antwort = klient.get("/api/lernen/stand", headers=als(GAST),
                         params={"benutzer_id": bestand["gast"]["id"],
                                 "sammlung_id": bestand["sammlung"]["id"]})
    assert antwort.status_code == 403, antwort.text


# --------------------------------- 2. Handeln im fremden Namen (Rumpf)

@pytest.mark.parametrize("pfad,zusatz", [
    ("/api/lernen/bewerten", {"bewertung": 1}),
    ("/api/lernen/aussetzen", {}),
    ("/api/lernen/zuruecksetzen", {}),
    ("/api/lernen/termin", {"datum": "2030-01-01"}),
])
def test_niemand_greift_in_fremden_lernstand_ein(klient, bestand, pfad, zusatz):
    """Fremde Zähler hochsetzen, ein Wort bis 2030 aus dem Verkehr ziehen,
    einen Lernstand wegwerfen — alles ging."""
    a = bestand["aufgaben"][0]
    antwort = klient.post(pfad, headers=als(GAST),
                          json={"benutzer_id": bestand["chefin"]["id"],
                                "aufgabe_id": a["aufgabe_id"], **zusatz})
    assert antwort.status_code == 403, f"{pfad}: {antwort.text}"


def test_kein_lernziel_in_fremdem_namen(klient, bestand):
    antwort = klient.post("/api/lernziele", headers=als(GAST),
                          json={"benutzer_id": bestand["chefin"]["id"],
                                "name": "fremdes Ziel",
                                "umfang": {"sammlung_id": bestand["sammlung"]["id"]}})
    assert antwort.status_code == 403, antwort.text


# ------------------------------------------- 3. Übungen fehlen in MUSTER

@pytest.fixture()
def uebung(klient, bestand):
    antwort = klient.post(f"/api/sammlungen/{bestand['sammlung']['id']}/uebungen",
                          headers=als(CHEFIN),
                          json={"typ": "satz", "titel": "Probe",
                                "zielsprache": "Je vais à Paris.",
                                "grundsprache": "Ich gehe nach Paris."})
    assert antwort.status_code in (200, 201), antwort.text
    return antwort.json()


def test_fremde_uebung_ist_nicht_lesbar(klient, uebung):
    assert klient.get(f"/api/uebungen/{uebung['id']}",
                      headers=als(GAST)).status_code == 403


def test_fremde_uebung_ist_nicht_aenderbar(klient, uebung):
    antwort = klient.patch(f"/api/uebungen/{uebung['id']}", headers=als(GAST),
                           json={"titel": "GEKAPERT"})
    assert antwort.status_code == 403, antwort.text


def test_fremde_uebung_ist_nicht_loeschbar(klient, uebung):
    assert klient.delete(f"/api/uebungen/{uebung['id']}",
                         headers=als(GAST)).status_code == 403


def test_niemand_gibt_fremde_uebungen_frei(klient, uebung):
    """Die Freigabe ist die eine Stelle, die bewusst beim Menschen bleibt."""
    antwort = klient.post(f"/api/uebungen/{uebung['id']}/freigabe",
                          headers=als(GAST))
    assert antwort.status_code == 403, antwort.text


# ------------------------- 4. OFFEN stand vor der Cloudflare-Prüfung

def test_sprachprofil_braucht_eine_identitaet(klient, mit_access):
    """Ohne Mailadresse über Cloudflare: abweisen, auch unter OFFEN.

    `/api/sprachen` ist als Stammdatenpfad offen — darunter liegen aber
    zwei schreibende Routen, und die trafen auf eine Verwalterprüfung,
    die ohne Identität wortlos durchwinkt.
    """
    antwort = klient.put("/api/sprachen/fr/profil", headers=ueber_cloudflare(),
                         json={"profil": {"pruefung": {"diakritika": "ignorieren"}},
                               "neu_rechnen": False})
    assert antwort.status_code == 403, antwort.text


def test_neue_sprache_braucht_eine_identitaet(klient, mit_access):
    antwort = klient.post("/api/sprachen", headers=ueber_cloudflare(),
                          json={"code": "xx", "name": "Erfunden"})
    assert antwort.status_code == 403, antwort.text


def test_stammdaten_lesen_bleibt_offen(klient, mit_access):
    """Nur Schreiben wird enger. Lesen muss gehen, sonst kommt die
    Anmeldeseite nicht einmal so weit zu fragen, wer man ist."""
    for pfad in ("/api/sprachen", "/api/merkmale", "/api/zustand", "/api/ich"):
        antwort = klient.get(pfad, headers=ueber_cloudflare())
        assert antwort.status_code == 200, pfad


# --------------------------------------------- 5. Auflistungen von außen

def test_die_sammlungsliste_zeigt_von_aussen_nicht_alles(klient, bestand):
    """Ohne benutzer_id lautete die Abfrage schlicht 'alle Sammlungen'."""
    antwort = klient.get("/api/sammlungen", headers=als(GAST))
    assert antwort.status_code == 200
    namen = [s["name"] for s in antwort.json()]
    assert "Privat" not in namen, f"fremde Sammlung sichtbar: {namen}"


def test_von_aussen_entstehen_keine_fremden_profile(klient, mit_access):
    """Mit Identität fehlte die Prüfung, ohne war sie da."""
    klient.get("/api/ich", headers=als(GAST))
    antwort = klient.post("/api/benutzer", headers=als(GAST),
                          json={"name": "Eingeschmuggelt"})
    assert antwort.status_code == 403, antwort.text


# ------------------------------------------------------- Gegenproben

def test_die_eigene_arbeit_geht_weiter(klient, bestand):
    """Alles oben darf die Chefin bei sich selbst weiterhin tun."""
    a = bestand["aufgaben"][0]
    assert klient.post("/api/lernen/aufdecken", headers=als(CHEFIN),
                       json={"benutzer_id": bestand["chefin"]["id"],
                             "aufgabe_id": a["aufgabe_id"]}).status_code == 200
    assert klient.get("/api/lernen/naechste", headers=als(CHEFIN),
                      params={"benutzer_id": bestand["chefin"]["id"],
                              "sammlung_id": bestand["sammlung"]["id"],
                              "anzahl": 1}).status_code == 200
    assert klient.post("/api/lernen/bewerten", headers=als(CHEFIN),
                       json={"benutzer_id": bestand["chefin"]["id"],
                             "aufgabe_id": a["aufgabe_id"],
                             "bewertung": 3}).status_code == 200


def test_im_heimnetz_bleibt_alles_wie_es_war(klient):
    """Ohne Access-Kopfzeile ist es das Heimnetz. Dort wird nichts enger —
    sonst wäre der Profilwähler kaputt."""
    a = klient.post("/api/benutzer", json={"name": "A"}).json()
    s = klient.post("/api/sammlungen", json={
        "besitzer_id": a["id"], "name": "As", "sprache": "fr"}).json()
    b = klient.post("/api/benutzer", json={"name": "B"}).json()
    assert klient.get("/api/sammlungen").status_code == 200
    assert klient.get("/api/lernen/stand",
                      params={"benutzer_id": b["id"],
                              "sammlung_id": s["id"]}).status_code == 200
