"""Der MCP-Dienst über HTTP.

Seit dem Umbau gibt es nur eine Umsetzung: /mcp im Trainer selbst. Die
Werkzeuge rufen dieselben Routenfunktionen auf wie die Oberfläche — es gibt
also keinen zweiten Weg in die Daten, der anders prüfen könnte.
"""

import json

import pytest


class Zugang:
    """Ein Testklient, der als eine bestimmte Person spricht."""

    def __init__(self, klient, benutzer, token):
        self.klient = klient
        self.benutzer = benutzer
        self.token = token

    def post(self, *args, **kw):
        kopf = kw.setdefault("headers", {})
        kopf.setdefault("Authorization", f"Bearer {self.token}")
        return self.klient.post(*args, **kw)

    def get(self, *args, **kw):
        kopf = kw.setdefault("headers", {})
        kopf.setdefault("Authorization", f"Bearer {self.token}")
        return self.klient.get(*args, **kw)


def person_mit_token(klient, name):
    b = klient.post("/api/benutzer", json={"name": name}).json()
    t = klient.post(f"/api/benutzer/{b['id']}/mcp-token",
                    json={"name": f"Test {name}"}).json()
    return Zugang(klient, b, t["token"])


@pytest.fixture()
def mcp(klient):
    """Erste Person — bekommt die Verwalterrolle."""
    return person_mit_token(klient, "Verwalterin")


def ruf(mcp, methode, **parameter):
    return mcp.post("/mcp", json={"jsonrpc": "2.0", "id": 1, "method": methode,
                                  "params": parameter})


def werkzeug(mcp, _name, **argumente):
    antwort = ruf(mcp, "tools/call", name=_name, arguments=argumente)
    assert antwort.status_code == 200, antwort.text
    d = antwort.json()
    if "error" in d:
        return {"_protokollfehler": d["error"]["message"]}
    inhalt = json.loads(d["result"]["content"][0]["text"])
    if d["result"].get("isError"):
        inhalt["_werkzeugfehler"] = True
    return inhalt


def _aufbau(mcp, sprache="el", name="Griechisch"):
    """Eine Sammlung, die der sprechenden Person gehört."""
    s = mcp.klient.post("/api/sammlungen", json={
        "besitzer_id": mcp.benutzer["id"], "name": name,
        "sprache": sprache}).json()
    return mcp.benutzer, s


# ------------------------------------------------------------------ Zugang

def test_ohne_token_ist_die_schnittstelle_nicht_eingerichtet(klient):
    """Sie schaltet sich erst frei, wenn es ein Zugangsmerkmal gibt. Ohne
    eines kommt niemand hinein, auch nicht versehentlich."""
    antwort = klient.post("/mcp", json={"jsonrpc": "2.0", "id": 1,
                                        "method": "tools/list"})
    assert antwort.status_code == 503
    assert "noch nicht eingerichtet" in antwort.json()["detail"]


def test_falsches_token_wird_abgewiesen(mcp):
    antwort = mcp.klient.post("/mcp", headers={"Authorization": "Bearer falsch"},
                              json={"jsonrpc": "2.0", "id": 1,
                                    "method": "tools/list"})
    assert antwort.status_code == 401


def test_fehlende_kopfzeile_wird_abgewiesen(mcp):
    antwort = mcp.klient.post("/mcp", json={"jsonrpc": "2.0", "id": 1,
                                            "method": "tools/list"})
    assert antwort.status_code == 401


def test_zurueckgenommenes_token_gilt_nicht_mehr(mcp):
    liste = mcp.klient.get(
        f"/api/benutzer/{mcp.benutzer['id']}/mcp-token").json()
    assert len(liste) == 1 and liste[0]["aktiv"] == 1
    mcp.klient.delete(f"/api/mcp-token/{liste[0]['id']}")
    assert ruf(mcp, "tools/list").status_code in (401, 503)


def test_das_geheimnis_steht_nirgends_gespeichert(mcp):
    liste = mcp.klient.get(
        f"/api/benutzer/{mcp.benutzer['id']}/mcp-token").json()
    assert "streuwert" not in liste[0]
    assert "token" not in liste[0]
    # Nur die ersten Zeichen, zum Wiedererkennen
    assert liste[0]["anfang"].startswith("vok_")
    assert len(liste[0]["anfang"]) < 16


# --------------------------------------------------------------- Protokoll

def test_initialize_nennt_die_angemeldete_person(mcp):
    d = ruf(mcp, "initialize", protocolVersion="2025-06-18").json()
    r = d["result"]
    assert r["serverInfo"]["name"] == "vokabeltrainer"
    assert r["protocolVersion"] == "2025-06-18"
    assert r["capabilities"]["tools"] == {}
    assert "formgruppen_zeigen" in r["instructions"]
    assert "Verwalterin" in r["instructions"]


def test_initialize_uebernimmt_die_version_des_klienten(mcp):
    d = ruf(mcp, "initialize", protocolVersion="2024-11-05").json()
    assert d["result"]["protocolVersion"] == "2024-11-05"


def test_benachrichtigung_bekommt_keine_antwort(mcp):
    antwort = mcp.post("/mcp", json={"jsonrpc": "2.0",
                                     "method": "notifications/initialized"})
    assert antwort.status_code == 202
    assert not antwort.content


def test_stapelanfrage(mcp):
    antwort = mcp.post("/mcp",
                       json=[{"jsonrpc": "2.0", "id": 1, "method": "ping"},
                             {"jsonrpc": "2.0", "id": 2, "method": "tools/list"}])
    d = antwort.json()
    assert isinstance(d, list) and len(d) == 2
    assert {x["id"] for x in d} == {1, 2}


def test_werkzeugliste_ist_vollstaendig_beschrieben(mcp):
    werkzeuge = ruf(mcp, "tools/list").json()["result"]["tools"]
    assert len(werkzeuge) >= 13
    for w in werkzeuge:
        assert w["name"] and w["description"]
        assert w["inputSchema"]["type"] == "object"
        for pflicht in w["inputSchema"].get("required", []):
            assert pflicht in w["inputSchema"]["properties"], (w["name"], pflicht)


def test_unbekanntes_werkzeug(mcp):
    d = ruf(mcp, "tools/call", name="gibtsnicht", arguments={}).json()
    assert d["error"]["code"] == -32602


def test_unbekannte_methode(mcp):
    d = ruf(mcp, "quatsch").json()
    assert d["error"]["code"] == -32601


def test_kaputtes_json(mcp):
    antwort = mcp.post("/mcp", headers={"Content-Type": "application/json"},
                       content=b"{nicht json")
    assert antwort.status_code == 400
    assert antwort.json()["error"]["code"] == -32700


def test_get_wird_abgelehnt(mcp):
    assert mcp.get("/mcp").status_code == 405


# --------------------------------------------------------------- Werkzeuge

def test_formgruppen_zeigen_liefert_abschreibbare_merkmale(mcp):
    ergebnis = werkzeug(mcp, "formgruppen_zeigen", sprache="el")
    praesens = next(g for g in ergebnis["wortarten"]["verb"]
                    if g["kennung"] == "enestotas")
    assert len(praesens["zellen"]) == 6
    # genus_verbi steht ausdrücklich dabei, seit es Passivgruppen gibt
    assert praesens["zellen"][0]["merkmale"] == {
        "modus": "indikativ", "tempus": "praesens", "genus_verbi": "aktiv",
        "person": "1", "numerus": "sg"}
    assert praesens["zellen"][0]["beschriftung"].startswith("Ενεστώτας")
    assert praesens["voreingestellt"] is True


def test_vokabel_anlegen_prueft_gleich_mit(mcp):
    _b, s = _aufbau(mcp)
    ergebnis = werkzeug(
        mcp, "vokabel_anlegen", sammlung_id=s["id"], lemma="γράφω",
        wortart="verb", bedeutungen=[{"uebersetzungen": ["schreiben"]}],
        formen=[{"text": "γράφω", "merkmale": {"modus": "indikativ",
                                               "tempus": "praesens",
                                               "person": "1", "numerus": "sg"},
                 "ist_grundform": True},
                {"text": "γράφεις", "merkmale": {"modus": "indikativ",
                                                 "tempus": "praesens",
                                                 "person": "2", "numerus": "sg"}}])
    assert ergebnis["formen_angelegt"] == 2
    arten = {b["art"] for b in ergebnis["pruefung"]["befunde"]}
    assert "paradigma_lueckig" in arten
    assert "nur_eine_uebersetzung" in arten


def test_angelegte_formen_bleiben_ungeprueft(mcp):
    _b, s = _aufbau(mcp)
    ergebnis = werkzeug(
        mcp, "vokabel_anlegen", sammlung_id=s["id"], lemma="διαβάζω",
        wortart="verb", bedeutungen=[{"uebersetzungen": ["lesen"]}],
        formen=[{"text": "διαβάζεις", "merkmale": {"modus": "indikativ",
                                                   "tempus": "praesens",
                                                   "person": "2",
                                                   "numerus": "sg"}}])
    assert ergebnis["pruefung"]["ungepruefte_formen"] == 1
    assert "ungeprüft" in ergebnis["hinweis"]

    gelesen = werkzeug(mcp, "vokabel_lesen", lexem_id=ergebnis["lexem_id"])
    form = gelesen["formen"][0]
    assert form["geprueft"] is False and form["quelle"] == "ki"

    # form_id, nicht id: genau diese Zahl verlangen form_aendern,
    # form_loeschen und formen_bestaetigen.
    werkzeug(mcp, "formen_bestaetigen", form_ids=[form["form_id"]])
    danach = werkzeug(mcp, "vokabel_lesen", lexem_id=ergebnis["lexem_id"])
    assert danach["formen"][0]["geprueft"] is True


def test_nachschlagen_findet_ueber_jede_form(mcp):
    _b, s = _aufbau(mcp)
    werkzeug(mcp, "vokabel_anlegen", sammlung_id=s["id"], lemma="γράφω",
             wortart="verb", bedeutungen=[{"uebersetzungen": ["schreiben"]}],
             formen=[{"text": "έγραψαν", "merkmale": {
                 "modus": "indikativ", "tempus": "aorist",
                 "person": "3", "numerus": "pl"}}])
    ergebnis = werkzeug(mcp, "vokabel_nachschlagen",
                        sammlung_id=s["id"], suche="έγραψαν")
    assert ergebnis["gefunden"] == 1
    assert ergebnis["eintraege"][0]["lemma"] == "γράφω"
    assert any("Αόριστος" in f.get("beschriftung", "")
               for f in ergebnis["eintraege"][0]["gefunden_bei"])


def test_formen_ergaenzen(mcp):
    _b, s = _aufbau(mcp)
    angelegt = werkzeug(mcp, "vokabel_anlegen", sammlung_id=s["id"],
                        lemma="γράφω", wortart="verb",
                        bedeutungen=[{"uebersetzungen": ["schreiben",
                                                         "notieren"]}])
    ergebnis = werkzeug(mcp, "formen_ergaenzen", lexem_id=angelegt["lexem_id"],
                        formen=[{"text": "έγραψα", "merkmale": {
                            "modus": "indikativ", "tempus": "aorist",
                            "person": "1", "numerus": "sg"}}])
    assert ergebnis["angelegt"] == 1
    assert "befunde" in ergebnis["pruefung"]


def test_fehler_kommen_lesbar_zurueck(mcp):
    _b, s = _aufbau(mcp)
    ergebnis = werkzeug(mcp, "vokabel_anlegen", sammlung_id=s["id"], lemma="x",
                        wortart="verb", bedeutungen=[{"uebersetzungen": ["y"]}],
                        formen=[{"text": "z", "merkmale": {"tempus": "erfunden"}}])
    assert ergebnis.get("_werkzeugfehler")
    assert "erfunden" in ergebnis["fehler"]


def test_sprache_einrichten_und_sofort_benutzen(mcp):
    ergebnis = werkzeug(mcp, "sprache_einrichten", code="la", name="Latein",
                        profil={"formgruppen": {"substantiv": [
                            {"kennung": "nom_sg", "name": "Nominativ Singular",
                             "kurz": "Nom. Sg.",
                             "merkmale": {"kasus": "nom", "numerus": "sg"},
                             "zellen": [{"kasus": "nom", "numerus": "sg"}]}]},
                            "formgruppen_standard": {"substantiv": "alle"}})
    assert ergebnis["code"] == "la" and ergebnis["im_code_hinterlegt"] is False
    gruppen = werkzeug(mcp, "formgruppen_zeigen", sprache="la")
    assert len(gruppen["wortarten"]["substantiv"]) == 1


def test_unbrauchbares_sprachprofil_wird_abgelehnt(mcp):
    ergebnis = werkzeug(mcp, "sprachprofil_anpassen", sprache="fr",
                        profil={"farbe": "blau"})
    assert ergebnis.get("_werkzeugfehler")
    assert "Unbekannte Einträge" in ergebnis["fehler"]


def test_der_mcp_geht_durch_dieselbe_pruefung_wie_die_oberflaeche(mcp):
    """Es darf keinen zweiten Weg in die Daten geben, der anders prüft."""
    klient = mcp.klient
    _b, s = _aufbau(mcp)
    ueber_mcp = werkzeug(mcp, "vokabel_anlegen", sammlung_id=s["id"],
                         lemma="test1", wortart="substantiv",
                         merkmale={"ablautreihe": "IV"},
                         bedeutungen=[{"uebersetzungen": ["x"]}])
    ueber_http = klient.post("/api/lexeme", json={
        "sammlung_id": s["id"], "lemma": "test2", "wortart": "substantiv",
        "merkmale": {"ablautreihe": "IV"},
        "bedeutungen": [{"uebersetzungen": [{"text": "x"}]}]})
    assert ueber_mcp.get("_werkzeugfehler")
    assert ueber_http.status_code == 400
    assert "Lexemmerkmal" in ueber_mcp["fehler"]
    assert "Lexemmerkmal" in ueber_http.json()["detail"]


# ------------------------------------------------- Trennung der Personen

def test_fremde_sammlungen_sind_unsichtbar(mcp):
    """Wer eingeladen wird, soll nicht den Lernstand der anderen sehen."""
    _b, eigene = _aufbau(mcp, name="Meine Sammlung")
    gast = person_mit_token(mcp.klient, "Gast")
    _gb, gasts = _aufbau(gast, name="Gastsammlung")

    meine = werkzeug(mcp, "sammlungen_auflisten")
    namen = {s["name"] for s in meine["sammlungen"]}
    assert "Meine Sammlung" in namen and "Gastsammlung" not in namen

    gasts_sicht = werkzeug(gast, "sammlungen_auflisten")
    assert {s["name"] for s in gasts_sicht["sammlungen"]} == {"Gastsammlung"}


def test_in_fremde_sammlungen_laesst_sich_nicht_schreiben(mcp):
    """Unsichtbar genügt nicht — es muss auch unerreichbar sein, wenn jemand
    die Kennung errät."""
    _b, eigene = _aufbau(mcp, name="Meine Sammlung")
    gast = person_mit_token(mcp.klient, "Gast")
    ergebnis = werkzeug(gast, "vokabel_anlegen", sammlung_id=eigene["id"],
                        lemma="eindringling", wortart="verb",
                        bedeutungen=[{"uebersetzungen": ["x"]}])
    assert ergebnis.get("_werkzeugfehler")
    assert ergebnis["art"] == "nicht_erlaubt"
    assert "gehört dir nicht" in ergebnis["fehler"]


def test_fremde_eintraege_lassen_sich_nicht_lesen(mcp):
    _b, eigene = _aufbau(mcp)
    lexem = werkzeug(mcp, "vokabel_anlegen", sammlung_id=eigene["id"],
                     lemma="γράφω", wortart="verb",
                     bedeutungen=[{"uebersetzungen": ["schreiben"]}])
    gast = person_mit_token(mcp.klient, "Gast")
    ergebnis = werkzeug(gast, "vokabel_lesen", lexem_id=lexem["lexem_id"])
    assert ergebnis.get("_werkzeugfehler")
    assert ergebnis["art"] == "nicht_erlaubt"


def test_freigegebene_sammlung_ist_erreichbar(mcp):
    """Was ausdrücklich freigegeben wurde, muss gehen."""
    import datenbank as dbm
    _b, eigene = _aufbau(mcp, name="Geteilt")
    gast = person_mit_token(mcp.klient, "Gast")
    # Freigabe (noch gibt es keine Route dafür, darum unmittelbar)
    db = dbm.verbindung()
    db.execute("INSERT INTO freigabe (sammlung_id, benutzer_id, recht) "
               "VALUES (?, ?, 'schreiben')", (eigene["id"], gast.benutzer["id"]))
    db.close()
    sicht = werkzeug(gast, "sammlungen_auflisten")
    assert any(s["name"] == "Geteilt" for s in sicht["sammlungen"])
    ergebnis = werkzeug(gast, "vokabel_anlegen", sammlung_id=eigene["id"],
                        lemma="δίνω", wortart="verb",
                        bedeutungen=[{"uebersetzungen": ["geben"]}])
    assert not ergebnis.get("_werkzeugfehler"), ergebnis


def test_nur_verwalter_duerfen_sprachprofile_aendern(mcp):
    """Das wirkt auf alle Sammlungen dieser Sprache, auch auf fremde."""
    gast = person_mit_token(mcp.klient, "Gast")
    werkzeuge_gast = {w["name"] for w in
                      ruf(gast, "tools/list").json()["result"]["tools"]}
    werkzeuge_chefin = {w["name"] for w in
                        ruf(mcp, "tools/list").json()["result"]["tools"]}
    # Was man nicht darf, wird gar nicht erst angeboten
    assert "sprachprofil_anpassen" not in werkzeuge_gast
    assert "sprachprofil_anpassen" in werkzeuge_chefin

    # Und wenn der Agent es doch versucht:
    ergebnis = werkzeug(gast, "sprachprofil_anpassen", sprache="fr",
                        profil={"pruefung": {"diakritika": "streng"}})
    assert ergebnis.get("_werkzeugfehler")
    assert ergebnis["art"] == "nicht_erlaubt"
    assert "Verwalter" in ergebnis["fehler"]


def test_die_erste_person_wird_verwalterin(klient):
    erste = klient.post("/api/benutzer", json={"name": "Erste"}).json()
    zweite = klient.post("/api/benutzer", json={"name": "Zweite"}).json()
    leute = {b["name"]: b for b in klient.get("/api/benutzer").json()}
    assert leute["Erste"]["verwalter"] == 1
    assert leute["Zweite"]["verwalter"] == 0


# ------------------------------------------- Kopfzeilen und Sperre

def test_das_merkmal_geht_auch_in_x_account_key(mcp):
    """Der Konnektor in claude.ai lässt nur eine feste Liste von
    Headernamen zu. Weder Authorization noch ein eigener Name stehen
    darauf — x-account-key schon."""
    antwort = mcp.klient.post("/mcp", headers={"x-account-key": mcp.token},
                              json={"jsonrpc": "2.0", "id": 1,
                                    "method": "tools/list"})
    assert antwort.status_code == 200
    assert len(antwort.json()["result"]["tools"]) >= 13


def test_vorangestelltes_bearer_wird_vertragen(mcp):
    """Falls es jemand aus Gewohnheit mitschreibt."""
    antwort = mcp.klient.post("/mcp",
                              headers={"x-account-key": f"Bearer {mcp.token}"},
                              json={"jsonrpc": "2.0", "id": 1,
                                    "method": "tools/list"})
    assert antwort.status_code == 200


def test_durchprobieren_wird_gesperrt(mcp):
    import drossel
    drossel.zuruecksetzen()
    try:
        letzte = None
        for i in range(drossel.GRENZE + 2):
            letzte = mcp.klient.post(
                "/mcp", headers={"Authorization": f"Bearer falsch{i}",
                                 "CF-Connecting-IP": "198.51.100.7"},
                json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
        assert letzte.status_code == 429
        assert "Fehlversuche" in letzte.json()["detail"]
        assert letzte.headers.get("Retry-After")

        # Das richtige Merkmal von einer ANDEREN Adresse geht weiter
        gut = mcp.klient.post("/mcp",
                              headers={"Authorization": f"Bearer {mcp.token}",
                                       "CF-Connecting-IP": "203.0.113.1"},
                              json={"jsonrpc": "2.0", "id": 1,
                                    "method": "tools/list"})
        assert gut.status_code == 200
    finally:
        drossel.zuruecksetzen()


# --------------------------------------------------- Fremde Herkunft (CORS)

def test_vorabanfrage_wird_beantwortet(klient):
    """Ein Konnektor läuft im Browser und schickt vor dem Aufruf eine
    Vorabanfrage. Misslingt die, kommt die eigentliche Anfrage nie
    zustande — der Client meldet nur »nicht erreichbar«, ohne Grund."""
    antwort = klient.options("/mcp", headers={
        "Origin": "https://claude.ai",
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "content-type,x-account-key"})
    assert antwort.status_code == 204
    assert antwort.headers["access-control-allow-origin"] == "*"
    erlaubt = antwort.headers["access-control-allow-headers"].lower()
    assert "x-account-key" in erlaubt
    assert "authorization" in erlaubt
    assert "POST" in antwort.headers["access-control-allow-methods"]


def test_vorabanfrage_braucht_keine_anmeldung(klient):
    """Sie trägt nie Anmeldedaten mit — sie darf nicht an der Prüfung
    scheitern."""
    assert klient.options("/mcp").status_code == 204


def test_antworten_tragen_die_cors_angaben(mcp):
    antwort = ruf(mcp, "tools/list")
    assert antwort.headers["access-control-allow-origin"] == "*"


def test_die_api_bleibt_ohne_cors(klient):
    """Im Heimnetz gibt es dort keine Anmeldung. Mit CORS könnte eine
    beliebige Webseite den Vokabelbestand auslesen, sobald jemand im
    Heimnetz sie öffnet."""
    antwort = klient.get("/api/sprachen", headers={"Origin": "https://boese.example"})
    assert "access-control-allow-origin" not in antwort.headers
