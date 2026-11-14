"""Freigabe in großen Mengen.

Mehrere tausend erzeugte Formen einzeln zu bestätigen ist nicht machbar, und
ungeprüft wird nichts abgefragt — ohne diesen Weg wäre der ganze
Sammelimport wertlos. Umgekehrt darf die Freigabe nicht zu leicht sein: sie
ist die einzige Stelle, an der ein Mensch die Einträge der KI ansieht.
"""


def _aufbau(klient, sprache="el"):
    b = klient.post("/api/benutzer", json={"name": "Prüferin"}).json()
    s = klient.post("/api/sammlungen", json={
        "besitzer_id": b["id"], "name": "Griechisch", "sprache": sprache}).json()
    return b, s


PERSONEN = [("1", "sg"), ("2", "sg"), ("3", "sg"),
            ("1", "pl"), ("2", "pl"), ("3", "pl")]


def _praesens(texte, **mehr):
    return [{"text": t, "merkmale": {"modus": "indikativ", "tempus": "praesens",
                                     "person": p, "numerus": n, **mehr}}
            for t, (p, n) in zip(texte, PERSONEN)]


GRAFO = {
    "lemma": "γράφω", "wortart": "verb", "lektion_nr": 5,
    "bedeutungen": [{"uebersetzungen": ["schreiben", "aufschreiben"]}],
    "formen": _praesens(["γράφω", "γράφεις", "γράφει",
                         "γράφουμε", "γράφετε", "γράφουν"]),
}
VIVLIO = {
    "lemma": "το βιβλίο", "wortart": "substantiv", "lektion_nr": 5,
    "merkmale": {"genus": "n"},
    "bedeutungen": [{"uebersetzungen": ["das Buch", "der Band"]}],
    "formen": [{"text": "βιβλίο", "merkmale": {"kasus": "nom", "numerus": "sg"}},
               {"text": "βιβλία", "merkmale": {"kasus": "nom", "numerus": "pl"}}],
}


def importieren(klient, sammlung_id, eintraege=None):
    return klient.post(f"/api/sammlungen/{sammlung_id}/import/vokabeln",
                       json={"eintraege": eintraege or [GRAFO, VIVLIO]}).json()


def ansicht(klient, sammlung_id, **frage):
    antwort = klient.get(f"/api/sammlungen/{sammlung_id}/freigabe", params=frage)
    assert antwort.status_code == 200, antwort.text
    return antwort.json()


def setzen(klient, sammlung_id, **daten):
    return klient.post(f"/api/sammlungen/{sammlung_id}/freigabe", json=daten)


# ------------------------------------------------------ Was ist offen?

def test_offene_lektionen_sind_der_einstieg(klient):
    _b, s = _aufbau(klient)
    importieren(klient, s["id"])
    uebersicht = klient.get(
        f"/api/sammlungen/{s['id']}/freigabe/lektionen").json()
    assert uebersicht["offen_gesamt"] == 8
    assert [k["nr"] for k in uebersicht["lektionen"]] == [5]
    assert uebersicht["lektionen"][0]["woerter"] == 2


def test_freigegebenes_verschwindet_aus_der_liste(klient):
    _b, s = _aufbau(klient)
    importieren(klient, s["id"])
    setzen(klient, s["id"], lektion_nr=5)
    uebersicht = klient.get(
        f"/api/sammlungen/{s['id']}/freigabe/lektionen").json()
    assert uebersicht["offen_gesamt"] == 0
    assert uebersicht["lektionen"] == []


def test_die_sammlungsliste_nennt_die_offenen_formen(klient):
    """Ohne diese Zahl auf dem Startbildschirm sucht man vergeblich nach den
    Wörtern, die die KI gerade eingetragen hat — abgefragt werden sie
    nämlich nicht."""
    b, s = _aufbau(klient)
    importieren(klient, s["id"])
    liste = klient.get("/api/sammlungen", params={"benutzer_id": b["id"]}).json()
    assert liste[0]["offene_formen"] == 8


# ------------------------------------------------------- Die Prüfansicht

def test_formen_stehen_als_paradigma_nach_zellen(klient):
    """Eine Liste in Eingabereihenfolge lässt sich nicht prüfen. Eine
    Tabelle nach den Zellen der Formgruppe schon."""
    _b, s = _aufbau(klient)
    importieren(klient, s["id"], [GRAFO])
    daten = ansicht(klient, s["id"], lektion_nr=5)
    wort = daten["woerter"][0]
    assert wort["lemma"] == "γράφω"
    gruppe = next(g for g in wort["gruppen"] if g["kennung"] == "enestotas")
    assert gruppe["belegt"] == 6 and gruppe["von"] == 6
    assert [z["formen"][0]["text"] for z in gruppe["zellen"]] == [
        "γράφω", "γράφεις", "γράφει", "γράφουμε", "γράφετε", "γράφουν"]
    assert "1. Person" in gruppe["zellen"][0]["beschriftung"]


def test_leere_zellen_bleiben_sichtbar(klient):
    """Dass hier nichts steht, IST die Auskunft. Eine weggelassene Zeile
    wäre keine."""
    _b, s = _aufbau(klient)
    importieren(klient, s["id"], [{**GRAFO, "formen": _praesens(["γράφω"])}])
    gruppe = next(g for g in ansicht(klient, s["id"])["woerter"][0]["gruppen"]
                  if g["kennung"] == "enestotas")
    assert gruppe["belegt"] == 1
    assert [bool(z["formen"]) for z in gruppe["zellen"]] == [
        True, False, False, False, False, False]
    assert all(not z["erklaerte_luecke"] for z in gruppe["zellen"])


def test_erklaerte_luecken_sind_als_solche_gekennzeichnet(klient):
    """πρέπει hat keine 1. Person. Das soll in der Tabelle nicht aussehen
    wie eine vergessene Form."""
    _b, s = _aufbau(klient)
    importieren(klient, s["id"], [{
        "lemma": "πρέπει", "wortart": "verb", "lektion_nr": 5,
        "luecken": [{"person": "1"}, {"person": "2"},
                    {"person": "3", "numerus": "pl"}],
        "bedeutungen": [{"uebersetzungen": ["müssen", "sollen"]}],
        "formen": [{"text": "πρέπει", "merkmale": {
            "modus": "indikativ", "tempus": "praesens",
            "person": "3", "numerus": "sg"}}]}])
    gruppe = next(g for g in ansicht(klient, s["id"])["woerter"][0]["gruppen"]
                  if g["kennung"] == "enestotas")
    erklaert = [z["beschriftung"] for z in gruppe["zellen"]
                if z["erklaerte_luecke"]]
    assert len(erklaert) == 5
    # Und sie zählen nicht gegen das Paradigma: πρέπει ist vollständig,
    # "1 von 6" wäre ein Vorwurf an ein fehlerfreies Wort.
    assert (gruppe["belegt"], gruppe["von"], gruppe["erklaert"]) == (1, 1, 5)


def test_befunde_stehen_am_wort(klient):
    """Wer weiß, dass das Paradigma lückig ist, liest die Tabelle anders.
    Notizen bleiben weg: "alles in Ordnung" soll man ohne Nachdenken
    drücken können."""
    _b, s = _aufbau(klient)
    importieren(klient, s["id"], [{**GRAFO, "formen": _praesens(["γράφω"])}])
    wort = ansicht(klient, s["id"])["woerter"][0]
    assert "paradigma_lueckig" in {b["art"] for b in wort["befunde"]}
    assert all(b["schwere"] != "notiz" for b in wort["befunde"])


def test_formen_ausserhalb_der_gruppen_werden_gezeigt(klient):
    """Sie erscheinen in keiner Tabelle und ließen sich sonst gar nicht
    ansehen."""
    _b, s = _aufbau(klient)
    importieren(klient, s["id"], [{
        **GRAFO, "formen": [{"text": "γράφοντας",
                             "merkmale": {"nonfinit": "infinitiv"}}]}])
    wort = ansicht(klient, s["id"])["woerter"][0]
    assert [f["text"] for f in wort["ausserhalb"]] == ["γράφοντας"]


def test_leere_formgruppen_erscheinen_nicht(klient):
    """Fünfzehn leere Tabellen je Wort wären keine Prüfansicht."""
    _b, s = _aufbau(klient)
    importieren(klient, s["id"], [GRAFO])
    kennungen = {g["kennung"] for g in ansicht(klient, s["id"])["woerter"][0]["gruppen"]}
    assert kennungen == {"enestotas"}


def test_nur_offene_woerter(klient):
    _b, s = _aufbau(klient)
    importieren(klient, s["id"])
    assert ansicht(klient, s["id"])["gesamt"] == 2
    setzen(klient, s["id"], lexem_ids=[
        ansicht(klient, s["id"])["woerter"][0]["lexem_id"]])
    assert ansicht(klient, s["id"])["gesamt"] == 1
    assert ansicht(klient, s["id"], nur_offene=False)["gesamt"] == 2


# ---------------------------------------------------------- Freigeben

def test_je_wort(klient):
    _b, s = _aufbau(klient)
    importieren(klient, s["id"])
    wort = next(w for w in ansicht(klient, s["id"])["woerter"]
                if w["lemma"] == "γράφω")
    ergebnis = setzen(klient, s["id"], lexem_ids=[wort["lexem_id"]]).json()
    assert ergebnis["gesetzt"] == 6 and ergebnis["lexeme"] == 1
    assert ansicht(klient, s["id"])["offen_gesamt"] == 2


def test_je_lektion_mit_abgewaehlten_zellen(klient):
    """Der eigentliche Weg: eine Lektion ansehen, die zwei falschen Formen
    abhaken, den Rest freigeben."""
    _b, s = _aufbau(klient)
    importieren(klient, s["id"])
    daten = ansicht(klient, s["id"], lektion_nr=5)
    alle = [f["form_id"] for w in daten["woerter"] for g in w["gruppen"]
            for z in g["zellen"] for f in z["formen"]]
    assert len(alle) == 8
    ergebnis = setzen(klient, s["id"], lektion_nr=5, ausser=alle[:2]).json()
    assert ergebnis["gesetzt"] == 6
    uebrig = ansicht(klient, s["id"], lektion_nr=5)
    assert uebrig["offen_gesamt"] == 2


def test_eine_ganze_sammlung_auf_einmal_geht_nicht(klient):
    """Das wäre keine Prüfung, sondern ein Haken."""
    _b, s = _aufbau(klient)
    importieren(klient, s["id"])
    antwort = setzen(klient, s["id"])
    assert antwort.status_code == 400
    assert "keine Prüfung" in antwort.json()["detail"]
    assert ansicht(klient, s["id"])["offen_gesamt"] == 8


def test_fremde_formen_lassen_sich_nicht_mitfreigeben(klient):
    """Eine fremde Kennung im Stapel darf nicht auf einem Bestand wirken,
    der jemand anderem gehört."""
    _b1, s1 = _aufbau(klient)
    b2 = klient.post("/api/benutzer", json={"name": "Andere"}).json()
    s2 = klient.post("/api/sammlungen", json={
        "besitzer_id": b2["id"], "name": "Fremd", "sprache": "el"}).json()
    importieren(klient, s1["id"], [GRAFO])
    importieren(klient, s2["id"], [VIVLIO])
    fremd = [f["form_id"] for w in ansicht(klient, s2["id"])["woerter"]
             for g in w["gruppen"] for z in g["zellen"] for f in z["formen"]]
    eigen = [f["form_id"] for w in ansicht(klient, s1["id"])["woerter"]
             for g in w["gruppen"] for z in g["zellen"] for f in z["formen"]]
    ergebnis = setzen(klient, s1["id"], form_ids=eigen + fremd).json()
    assert ergebnis["gesetzt"] == len(eigen)
    assert ansicht(klient, s2["id"])["offen_gesamt"] == 2


def test_freigabe_schaltet_die_aufgaben_frei(klient):
    """Das ist der ganze Zweck: ungeprüft wird nicht abgefragt."""
    _b, s = _aufbau(klient)
    importieren(klient, s["id"], [GRAFO])
    lexem_id = ansicht(klient, s["id"])["woerter"][0]["lexem_id"]
    vorher = klient.get(f"/api/lexeme/{lexem_id}").json()["aufgaben"]
    setzen(klient, s["id"], lexem_ids=[lexem_id])
    nachher = klient.get(f"/api/lexeme/{lexem_id}").json()["aufgaben"]
    assert sum(1 for a in nachher if a["aktiv"]) > sum(1 for a in vorher if a["aktiv"])


def test_freigabe_laesst_sich_zuruecknehmen(klient):
    _b, s = _aufbau(klient)
    importieren(klient, s["id"], [GRAFO])
    lexem_id = ansicht(klient, s["id"])["woerter"][0]["lexem_id"]
    setzen(klient, s["id"], lexem_ids=[lexem_id])
    assert ansicht(klient, s["id"])["offen_gesamt"] == 0
    setzen(klient, s["id"], lexem_ids=[lexem_id], geprueft=False)
    assert ansicht(klient, s["id"])["offen_gesamt"] == 6


# ------------------------------------------------------------- Grenze

def test_die_ki_kann_nicht_im_stapel_freigeben(klient):
    """Die Freigabe ist die einzige Stelle, an der ein Mensch die Einträge
    der KI ansieht. Ein Werkzeug dafür hätte sie abgeschafft, nicht
    erledigt — darum gibt es keines."""
    import sys
    sys.path.insert(0, "backend")
    import mcp_dienst
    namen = {w["name"] for w in mcp_dienst.WERKZEUGE}
    assert "formen_bestaetigen" not in namen
    assert not any("freigab" in n or "bestaetig" in n for n in namen), namen
