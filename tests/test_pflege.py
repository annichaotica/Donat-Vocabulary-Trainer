"""Pflege über den MCP: berichtigen, auflisten, löschen.

Bisher konnte ein Agent nur anlegen. Das heißt: jeder Fehler aus einem
Probelauf blieb stehen, bis ein Mensch ihn von Hand nachzog. Umgekehrt darf
Löschen über die Schnittstelle nicht leicht sein — an jeder Form hängt ein
Lernstand, und eine verwechselte Kennung trifft lautlos das Falsche.
"""

import pytest

from test_mcp import person_mit_token, werkzeug


@pytest.fixture()
def mcp(klient):
    return person_mit_token(klient, "Verwalterin")


GRAFO = {
    "lemma": "γράφω", "wortart": "verb", "lektion_nr": 5,
    "merkmale": {"klasse": "Α-Konjugation"},
    "bedeutungen": [{"uebersetzungen": ["schreiben", "aufschreiben"]}],
    "formen": [{"text": "γράφω", "merkmale": {
        "modus": "indikativ", "tempus": "praesens",
        "person": "1", "numerus": "sg"}},
        {"text": "γράφεις", "merkmale": {
            "modus": "indikativ", "tempus": "praesens",
            "person": "2", "numerus": "sg"}}],
}


def _sammlung(mcp):
    return werkzeug(mcp, "sammlung_anlegen", name="Griechisch", sprache="el")


def _grafo(mcp, sammlung_id, **mehr):
    werkzeug(mcp, "vokabeln_importieren", sammlung_id=sammlung_id,
             eintraege=[{**GRAFO, **mehr}])
    return werkzeug(mcp, "vokabeln_auflisten",
                    sammlung_id=sammlung_id)["vokabeln"][0]


# ------------------------------------------------------- Sammlung anlegen

def test_sammlung_gehoert_der_sprechenden_person(mcp, klient):
    s = _sammlung(mcp)
    assert s["sprache"] == "el" and s["grundsprache"] == "de"
    meine = werkzeug(mcp, "sammlungen_auflisten")["sammlungen"]
    assert [x["id"] for x in meine] == [s["sammlung_id"]]
    # Und sie ist für andere nicht da.
    andere = person_mit_token(klient, "Fremde")
    assert werkzeug(andere, "sammlungen_auflisten")["sammlungen"] == []


def test_unbekannte_sprache_wird_abgewiesen(mcp):
    ergebnis = werkzeug(mcp, "sammlung_anlegen", name="X", sprache="kli")
    assert ergebnis.get("_werkzeugfehler")


# ------------------------------------------------------------- Auflisten

def test_auflisten_zeigt_den_pflegestand(mcp):
    s = _sammlung(mcp)
    werkzeug(mcp, "vokabeln_importieren", sammlung_id=s["sammlung_id"],
             eintraege=[GRAFO,
                        {"lemma": "το βιβλίο", "wortart": "substantiv",
                         "lektion_nr": 6, "merkmale": {"genus": "n"},
                         "bedeutungen": [{"uebersetzungen": ["das Buch",
                                                             "der Band"]}]}])
    alle = werkzeug(mcp, "vokabeln_auflisten", sammlung_id=s["sammlung_id"])
    assert alle["gesamt"] == 2
    verb = next(v for v in alle["vokabeln"] if v["wortart"] == "verb")
    assert verb["lemma"] == "γράφω"
    assert verb["bedeutung"] == "schreiben"
    assert verb["formen"] == 2 and verb["ungeprueft"] == 2

    nach_lektion = werkzeug(mcp, "vokabeln_auflisten",
                            sammlung_id=s["sammlung_id"], lektion_nr=6)
    assert [v["lemma"] for v in nach_lektion["vokabeln"]] == ["το βιβλίο"]
    nach_art = werkzeug(mcp, "vokabeln_auflisten",
                        sammlung_id=s["sammlung_id"], wortart="verb")
    assert [v["lemma"] for v in nach_art["vokabeln"]] == ["γράφω"]
    gesucht = werkzeug(mcp, "vokabeln_auflisten",
                       sammlung_id=s["sammlung_id"], suche="Buch")
    assert [v["lemma"] for v in gesucht["vokabeln"]] == ["το βιβλίο"]


def test_nur_ungepruefte(mcp, klient):
    s = _sammlung(mcp)
    lexem = _grafo(mcp, s["sammlung_id"])
    assert werkzeug(mcp, "vokabeln_auflisten", sammlung_id=s["sammlung_id"],
                    nur_ungepruefte=True)["gesamt"] == 1
    for f in klient.get(f"/api/lexeme/{lexem['lexem_id']}").json()["formen"]:
        klient.post(f"/api/formen/{f['id']}/bestaetigen")
    assert werkzeug(mcp, "vokabeln_auflisten", sammlung_id=s["sammlung_id"],
                    nur_ungepruefte=True)["gesamt"] == 0


# -------------------------------------------------------------- Ändern

def test_vokabel_aendern_laesst_das_uebrige_stehen(mcp):
    s = _sammlung(mcp)
    lexem = _grafo(mcp, s["sammlung_id"])
    ergebnis = werkzeug(mcp, "vokabel_aendern", lexem_id=lexem["lexem_id"],
                        notiz="Β-Konjugation prüfen")
    assert ergebnis["lemma"] == "γράφω"
    assert ergebnis["merkmale"] == {"klasse": "Α-Konjugation"}
    assert ergebnis["formen"] == 2


def test_bedeutungen_werden_ersetzt_nicht_ergaenzt(mcp):
    s = _sammlung(mcp)
    lexem = _grafo(mcp, s["sammlung_id"])
    ergebnis = werkzeug(mcp, "vokabel_aendern", lexem_id=lexem["lexem_id"],
                        bedeutungen=[{"uebersetzungen": ["schreiben",
                                                         "verfassen"]}])
    assert ergebnis["bedeutungen"] == [["schreiben", "verfassen"]]


def test_vokabel_ohne_bedeutung_wird_abgewiesen(mcp):
    """Ohne Bedeutung entsteht keine Bedeutungsaufgabe — das Wort wäre
    stumm im Bestand."""
    s = _sammlung(mcp)
    lexem = _grafo(mcp, s["sammlung_id"])
    ergebnis = werkzeug(mcp, "vokabel_aendern", lexem_id=lexem["lexem_id"],
                        bedeutungen=[])
    assert ergebnis.get("_werkzeugfehler")


def test_lektion_wird_ueber_die_nummer_gesetzt(mcp):
    s = _sammlung(mcp)
    lexem = _grafo(mcp, s["sammlung_id"])
    werkzeug(mcp, "vokabel_aendern", lexem_id=lexem["lexem_id"], lektion_nr=12)
    liste = werkzeug(mcp, "vokabeln_auflisten", sammlung_id=s["sammlung_id"],
                     lektion_nr=12)
    assert liste["gesamt"] == 1
    assert 12 in [k["nr"] for k in
                  werkzeug(mcp, "lektionen_auflisten",
                           sammlung_id=s["sammlung_id"])["lektionen"]]


def test_geaenderte_form_faellt_auf_ungepruefte_zurueck(mcp, klient):
    """Was geändert wurde, ist nicht mehr das, was ein Mensch freigegeben
    hat. Sonst könnte ein Agent eine Freigabe für einen anderen Inhalt
    weiterbenutzen."""
    s = _sammlung(mcp)
    lexem = _grafo(mcp, s["sammlung_id"])
    form = werkzeug(mcp, "vokabel_lesen",
                    lexem_id=lexem["lexem_id"])["formen"][0]
    klient.post(f"/api/formen/{form['form_id']}/bestaetigen")
    assert klient.get(f"/api/lexeme/{lexem['lexem_id']}").json(
        )["formen"][0]["geprueft"] == 1

    ergebnis = werkzeug(mcp, "form_aendern", form_id=form["form_id"],
                        text="γράφω!")
    assert ergebnis["text"] == "γράφω!"
    assert ergebnis["geprueft"] is False
    assert "Freigabe" in ergebnis["hinweis"]


def test_eine_unveraenderte_freigabe_bleibt(mcp, klient):
    """Nur INHALTLICHE Änderungen nehmen die Freigabe zurück. Eine Notiz
    dazuzuschreiben darf das Wort nicht aus der Abfrage nehmen."""
    s = _sammlung(mcp)
    lexem = _grafo(mcp, s["sammlung_id"])
    form = werkzeug(mcp, "vokabel_lesen",
                    lexem_id=lexem["lexem_id"])["formen"][0]
    klient.post(f"/api/formen/{form['form_id']}/bestaetigen")
    ergebnis = werkzeug(mcp, "form_aendern", form_id=form["form_id"],
                        notiz="Betonung auf der zweiten Silbe")
    assert ergebnis["geprueft"] is True


def test_der_agent_kann_die_freigabe_nicht_selbst_setzen(mcp, klient):
    """Die Freigabe gehört dem Menschen. Ein mitgeschicktes geprueft=true
    wird stillschweigend verworfen, nicht befolgt."""
    s = _sammlung(mcp)
    lexem = _grafo(mcp, s["sammlung_id"])
    form = werkzeug(mcp, "vokabel_lesen",
                    lexem_id=lexem["lexem_id"])["formen"][0]
    ergebnis = werkzeug(mcp, "form_aendern", form_id=form["form_id"],
                        text="γράφω", geprueft=True)
    assert ergebnis["geprueft"] is False


def test_unbrauchbare_merkmale_werden_abgewiesen(mcp):
    s = _sammlung(mcp)
    lexem = _grafo(mcp, s["sammlung_id"])
    form = werkzeug(mcp, "vokabel_lesen",
                    lexem_id=lexem["lexem_id"])["formen"][0]
    ergebnis = werkzeug(mcp, "form_aendern", form_id=form["form_id"],
                        merkmale={"tempus": "übermorgen"})
    assert ergebnis.get("_werkzeugfehler")


# -------------------------------------------------------------- Löschen

def test_form_loeschen_verlangt_den_vorhandenen_text(mcp):
    """Die Bestätigung ist kein Formalismus: eine verwechselte Kennung
    träfe lautlos die falsche Form."""
    s = _sammlung(mcp)
    lexem = _grafo(mcp, s["sammlung_id"])
    formen = werkzeug(mcp, "vokabel_lesen", lexem_id=lexem["lexem_id"])["formen"]
    falsch = werkzeug(mcp, "form_loeschen", form_id=formen[0]["form_id"],
                      text="irgendwas")
    assert falsch.get("_werkzeugfehler")
    assert werkzeug(mcp, "vokabel_lesen",
                    lexem_id=lexem["lexem_id"])["formen"] != []

    ziel = formen[0]
    richtig = werkzeug(mcp, "form_loeschen", form_id=ziel["form_id"],
                       text=ziel["text"])
    assert richtig["geloescht"] == ziel["text"]
    uebrig = werkzeug(mcp, "vokabel_lesen", lexem_id=lexem["lexem_id"])["formen"]
    assert ziel["text"] not in [f["text"] for f in uebrig]


def test_vokabel_loeschen_verlangt_das_lemma_und_sagt_was_weg_ist(mcp):
    s = _sammlung(mcp)
    lexem = _grafo(mcp, s["sammlung_id"])
    falsch = werkzeug(mcp, "vokabel_loeschen", lexem_id=lexem["lexem_id"],
                      lemma="γράφει")
    assert falsch.get("_werkzeugfehler")
    assert werkzeug(mcp, "vokabeln_auflisten",
                    sammlung_id=s["sammlung_id"])["gesamt"] == 1

    ergebnis = werkzeug(mcp, "vokabel_loeschen", lexem_id=lexem["lexem_id"],
                        lemma="γράφω")
    assert ergebnis["geloescht"] == "γράφω"
    assert ergebnis["formen"] == 2
    assert ergebnis["wiederholungen"] == 0
    assert werkzeug(mcp, "vokabeln_auflisten",
                    sammlung_id=s["sammlung_id"])["gesamt"] == 0


def test_verlorener_lernstand_wird_benannt(mcp, klient):
    """Ein gelerntes Wort zu löschen, soll nicht wie ein leeres aussehen."""
    s = _sammlung(mcp)
    lexem = _grafo(mcp, s["sammlung_id"])
    aufgaben = klient.get(f"/api/lexeme/{lexem['lexem_id']}").json()["aufgaben"]
    klient.post("/api/lernen/bewerten", json={
        "benutzer_id": mcp.benutzer["id"], "aufgabe_id": aufgaben[0]["id"],
        "bewertung": 3})
    ergebnis = werkzeug(mcp, "vokabel_loeschen", lexem_id=lexem["lexem_id"],
                        lemma="γράφω")
    assert ergebnis["wiederholungen"] == 1
    assert "Wiederholungen verlorengegangen" in ergebnis["hinweis"]


# --------------------------------------------------------------- Zugang

def test_fremdes_wort_ist_nicht_aenderbar(mcp, klient):
    s = _sammlung(mcp)
    lexem = _grafo(mcp, s["sammlung_id"])
    andere = person_mit_token(klient, "Fremde")
    for name, args in (
            ("vokabel_aendern", {"lexem_id": lexem["lexem_id"], "notiz": "x"}),
            ("vokabel_loeschen", {"lexem_id": lexem["lexem_id"],
                                  "lemma": "γράφω"}),
            ("vokabeln_auflisten", {"sammlung_id": s["sammlung_id"]})):
        assert werkzeug(andere, name, **args).get("_werkzeugfehler"), name
