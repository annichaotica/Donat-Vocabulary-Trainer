"""Der MCP-Server.

Geprüft wird beides: das Protokoll (damit Claude ihn überhaupt anfassen kann)
und die Werkzeuge (damit sie das Richtige tun). Die HTTP-Aufrufe des Servers
werden dabei auf den Testklienten umgeleitet — so braucht es keinen laufenden
Dienst, und die Tests laufen in Millisekunden.
"""

import importlib.util
import io
import json
import pathlib
import sys

import pytest

WURZEL = pathlib.Path(__file__).resolve().parents[1]


@pytest.fixture()
def mcp(klient, monkeypatch):
    """Lädt den MCP-Server und leitet seine HTTP-Aufrufe um."""
    spec = importlib.util.spec_from_file_location(
        "vokabeltrainer_mcp", WURZEL / "mcp" / "vokabeltrainer_mcp.py")
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)

    def ruf(pfad, methode="GET", daten=None, frage=None):
        sauber = {k: v for k, v in (frage or {}).items() if v is not None}
        antwort = klient.request(methode, "/api" + pfad, json=daten, params=sauber)
        if antwort.status_code >= 400:
            einzelheit = antwort.json().get("detail")
            raise modul.TrainerFehler(f"{antwort.status_code}: {einzelheit}")
        return antwort.json() if antwort.content else None

    monkeypatch.setattr(modul, "ruf", ruf)
    return modul


def ruf_werkzeug(mcp, _werkzeug, **argumente):
    """Ein Werkzeug über den Protokollweg aufrufen, wie Claude es täte.

    Der Werkzeugname heißt hier _werkzeug und nicht name, weil `name` ein
    gültiger Parameter der Werkzeuge selbst ist (sprache_einrichten).
    """
    ausgabe = io.StringIO()
    altes = sys.stdout
    sys.stdout = ausgabe
    try:
        mcp.behandeln({"jsonrpc": "2.0", "id": 99, "method": "tools/call",
                       "params": {"name": _werkzeug, "arguments": argumente}})
    finally:
        sys.stdout = altes
    antwort = json.loads(ausgabe.getvalue())
    if "error" in antwort:
        return {"_protokollfehler": antwort["error"]["message"]}
    inhalt = json.loads(antwort["result"]["content"][0]["text"])
    if antwort["result"].get("isError"):
        inhalt["_werkzeugfehler"] = True
    return inhalt


def _aufbau(klient):
    b = klient.post("/api/benutzer", json={"name": "MCP"}).json()
    s = klient.post("/api/sammlungen", json={
        "besitzer_id": b["id"], "name": "Griechisch", "sprache": "el"}).json()
    return b, s


# ------------------------------------------------------------- Protokoll

def _antwort(mcp, nachricht):
    ausgabe = io.StringIO()
    altes = sys.stdout
    sys.stdout = ausgabe
    try:
        mcp.behandeln(nachricht)
    finally:
        sys.stdout = altes
    text = ausgabe.getvalue()
    return json.loads(text) if text.strip() else None


def test_initialize_nennt_sich_und_gibt_eine_anleitung(mcp):
    a = _antwort(mcp, {"jsonrpc": "2.0", "id": 1, "method": "initialize",
                       "params": {"protocolVersion": "2025-06-18"}})
    r = a["result"]
    assert r["serverInfo"]["name"] == "vokabeltrainer"
    assert r["protocolVersion"] == "2025-06-18"
    assert r["capabilities"]["tools"] == {}
    # Die Anleitung sagt die Reihenfolge — ohne sie rät der Agent.
    assert "formgruppen_zeigen" in r["instructions"]


def test_initialize_uebernimmt_die_version_des_klienten(mcp):
    a = _antwort(mcp, {"jsonrpc": "2.0", "id": 1, "method": "initialize",
                       "params": {"protocolVersion": "2024-11-05"}})
    assert a["result"]["protocolVersion"] == "2024-11-05"


def test_benachrichtigungen_bekommen_keine_antwort(mcp):
    assert _antwort(mcp, {"jsonrpc": "2.0",
                          "method": "notifications/initialized"}) is None


def test_werkzeugliste_ist_vollstaendig_beschrieben(mcp):
    a = _antwort(mcp, {"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
    werkzeuge = a["result"]["tools"]
    assert len(werkzeuge) >= 13
    for w in werkzeuge:
        assert w["name"] and w["description"]
        assert w["inputSchema"]["type"] == "object"
        # Pflichtfelder müssen im Schema auch vorkommen
        for pflicht in w["inputSchema"].get("required", []):
            assert pflicht in w["inputSchema"]["properties"], (w["name"], pflicht)


def test_unbekanntes_werkzeug_ergibt_einen_protokollfehler(mcp):
    a = _antwort(mcp, {"jsonrpc": "2.0", "id": 3, "method": "tools/call",
                       "params": {"name": "gibtsnicht", "arguments": {}}})
    assert a["error"]["code"] == -32602


def test_unbekannte_methode(mcp):
    a = _antwort(mcp, {"jsonrpc": "2.0", "id": 4, "method": "quatsch"})
    assert a["error"]["code"] == -32601


def test_falsche_angaben_ergeben_eine_lesbare_meldung(mcp, klient):
    ergebnis = ruf_werkzeug(mcp, "vokabel_lesen")      # lexem_id fehlt
    assert ergebnis.get("_werkzeugfehler")
    assert "vokabel_lesen" in ergebnis["fehler"]


# ------------------------------------------------------------- Werkzeuge

def test_formgruppen_zeigen_liefert_abschreibbare_merkmale(mcp, klient):
    """Der Agent muss die Merkmalsbündel abschreiben können — sonst rät er."""
    ergebnis = ruf_werkzeug(mcp, "formgruppen_zeigen", sprache="el")
    verben = ergebnis["wortarten"]["verb"]
    praesens = next(g for g in verben if g["kennung"] == "enestotas")
    assert len(praesens["zellen"]) == 6
    zelle = praesens["zellen"][0]
    assert zelle["merkmale"] == {"modus": "indikativ", "tempus": "praesens",
                                 "person": "1", "numerus": "sg"}
    assert zelle["beschriftung"].startswith("Ενεστώτας")
    assert praesens["voreingestellt"] is True


def test_vokabel_anlegen_prueft_gleich_mit(mcp, klient):
    """Nach dem Anlegen bekommt der Agent sofort zu hören, was fehlt."""
    _b, s = _aufbau(klient)
    ergebnis = ruf_werkzeug(
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
    assert "paradigma_lueckig" in arten        # 2 von 6
    assert "nur_eine_uebersetzung" in arten


def test_angelegte_formen_bleiben_ungeprueft(mcp, klient):
    """Eine erfundene Form, die unbemerkt gepaukt wird, ist schlimmer als
    eine fehlende."""
    _b, s = _aufbau(klient)
    ergebnis = ruf_werkzeug(
        mcp, "vokabel_anlegen", sammlung_id=s["id"], lemma="διαβάζω",
        wortart="verb", bedeutungen=[{"uebersetzungen": ["lesen"]}],
        formen=[{"text": "διαβάζεις", "merkmale": {"modus": "indikativ",
                                                   "tempus": "praesens",
                                                   "person": "2", "numerus": "sg"}}])
    assert ergebnis["pruefung"]["ungepruefte_formen"] == 1
    assert "ungeprüft" in ergebnis["hinweis"]

    gelesen = ruf_werkzeug(mcp, "vokabel_lesen", lexem_id=ergebnis["lexem_id"])
    form = gelesen["formen"][0]
    assert form["geprueft"] is False and form["quelle"] == "ki"

    ruf_werkzeug(mcp, "formen_bestaetigen", form_ids=[form["id"]])
    danach = ruf_werkzeug(mcp, "vokabel_lesen", lexem_id=ergebnis["lexem_id"])
    assert danach["formen"][0]["geprueft"] is True


def test_nachschlagen_findet_ueber_jede_form(mcp, klient):
    _b, s = _aufbau(klient)
    ruf_werkzeug(mcp, "vokabel_anlegen", sammlung_id=s["id"], lemma="γράφω",
                 wortart="verb", bedeutungen=[{"uebersetzungen": ["schreiben"]}],
                 formen=[{"text": "έγραψαν", "merkmale": {
                     "modus": "indikativ", "tempus": "aorist",
                     "person": "3", "numerus": "pl"}}])
    ergebnis = ruf_werkzeug(mcp, "vokabel_nachschlagen",
                            sammlung_id=s["id"], suche="έγραψαν")
    assert ergebnis["gefunden"] == 1
    eintrag = ergebnis["eintraege"][0]
    assert eintrag["lemma"] == "γράφω"
    assert any("Αόριστος" in f.get("beschriftung", "")
               for f in eintrag["gefunden_bei"])


def test_formen_ergaenzen_meldet_den_neuen_stand(mcp, klient):
    _b, s = _aufbau(klient)
    angelegt = ruf_werkzeug(
        mcp, "vokabel_anlegen", sammlung_id=s["id"], lemma="γράφω",
        wortart="verb", bedeutungen=[{"uebersetzungen": ["schreiben", "notieren"]}])
    ergebnis = ruf_werkzeug(mcp, "formen_ergaenzen",
                            lexem_id=angelegt["lexem_id"],
                            formen=[{"text": "έγραψα", "merkmale": {
                                "modus": "indikativ", "tempus": "aorist",
                                "person": "1", "numerus": "sg"}}])
    assert ergebnis["angelegt"] == 1
    assert "befunde" in ergebnis["pruefung"]


def test_fehler_aus_dem_trainer_kommen_lesbar_zurueck(mcp, klient):
    _b, s = _aufbau(klient)
    ergebnis = ruf_werkzeug(
        mcp, "vokabel_anlegen", sammlung_id=s["id"], lemma="x",
        wortart="verb", bedeutungen=[{"uebersetzungen": ["y"]}],
        formen=[{"text": "z", "merkmale": {"tempus": "erfunden"}}])
    assert ergebnis.get("_werkzeugfehler")
    assert "erfunden" in ergebnis["fehler"]


def test_sprache_einrichten_und_sofort_benutzen(mcp, klient):
    """Ein Agent muss eine Sprache zum Laufen bringen können, ohne dass
    jemand Code ändert."""
    ergebnis = ruf_werkzeug(mcp, "sprache_einrichten", code="la", name="Latein",
                            profil={"formgruppen": {"substantiv": [
                                {"kennung": "nom_sg", "name": "Nominativ Singular",
                                 "kurz": "Nom. Sg.",
                                 "merkmale": {"kasus": "nom", "numerus": "sg"},
                                 "zellen": [{"kasus": "nom", "numerus": "sg"}]},
                                {"kennung": "gen_sg", "name": "Genitiv Singular",
                                 "kurz": "Gen. Sg.",
                                 "merkmale": {"kasus": "gen", "numerus": "sg"},
                                 "zellen": [{"kasus": "gen", "numerus": "sg"}]}]},
                                "formgruppen_standard": {"substantiv": "alle"}})
    assert ergebnis["code"] == "la"
    assert ergebnis["im_code_hinterlegt"] is False

    gruppen = ruf_werkzeug(mcp, "formgruppen_zeigen", sprache="la")
    assert len(gruppen["wortarten"]["substantiv"]) == 2


def test_unbrauchbares_sprachprofil_wird_abgelehnt(mcp, klient):
    ergebnis = ruf_werkzeug(mcp, "sprachprofil_anpassen", sprache="fr",
                            profil={"farbe": "blau"})
    assert ergebnis.get("_werkzeugfehler")
    assert "Unbekannte Einträge" in ergebnis["fehler"]
