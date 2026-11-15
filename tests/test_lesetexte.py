"""Texte einwerfen, einschätzen, übersetzen, Lücken anfordern.

»Ich möchte eine Übersetzungsfunktion … wo analysiert wird, ob ich das
schon übersetzen können müsste … und Worte, die ich noch nicht kenne,
markieren kann. Die soll dann die angebundene KI über den MCP auslesen
können.«

Der Kern ist die Deckung, und ihr Wert steht und fällt damit, dass sie
nicht schmeichelt. Zwei Fehlerrichtungen sind möglich:

  zu freundlich   ein Wort gilt als bekannt, das nicht eingetragen ist
                  — dann heißt es »das müsstest du können«, und dann
                  sitzt man vor einem Text und kann es nicht
  zu streng      eine eingetragene Form wird nicht gefunden — dann
                  fordert man Vokabeln an, die man längst hat

Beide sind hier geprüft. Die erste Richtung ist die gefährlichere, weil
sie Vertrauen kostet.
"""

import pytest

TEXT = """Ο Γιώργος γράφει ένα γράμμα.

Το μήλο είναι κόκκινο και μικρό."""


@pytest.fixture()
def bestand(klient):
    b = klient.post("/api/benutzer", json={"name": "Übende"}).json()
    s = klient.post("/api/sammlungen", json={
        "besitzer_id": b["id"], "name": "Griechisch", "sprache": "el"}).json()
    klient.post(f"/api/sammlungen/{s['id']}/import/vokabeln", json={
        "eintraege": [
            {"lemma": "γράφω", "wortart": "verb", "lektion_nr": 1,
             "bedeutungen": [{"uebersetzungen": ["schreiben"]}],
             # Die Form im Text ist 3. Sg. — ohne sie wäre »γράφει«
             # unbekannt, obwohl das Wort gelernt ist.
             "formen": [{"text": "γράφει", "merkmale": {
                 "modus": "indikativ", "tempus": "praesens",
                 "person": "3", "numerus": "sg"}}]},
            {"lemma": "το μήλο", "wortart": "substantiv", "lektion_nr": 1,
             "bedeutungen": [{"uebersetzungen": ["der Apfel"]}]},
            {"lemma": "μικρός", "wortart": "adjektiv", "lektion_nr": 1,
             "bedeutungen": [{"uebersetzungen": ["klein"]}]},
        ]})
    klient.post(f"/api/sammlungen/{s['id']}/freigabe", json={"lektion_nr": 1})
    return b, s


def _text(klient, s, inhalt=TEXT, titel="Ein Absatz"):
    antwort = klient.post(f"/api/sammlungen/{s['id']}/texte",
                          json={"titel": titel, "inhalt": inhalt})
    assert antwort.status_code == 201, antwort.text
    return antwort.json()


# --------------------------------------------------------------- Einwerfen

def test_ein_eingefuegter_text_wird_gespeichert_und_zerlegt(bestand, klient):
    b, s = bestand
    t = _text(klient, s)
    assert t["titel"] == "Ein Absatz"
    # Zwei Absätze, also zwei Abschnitte — die Einheit zum Übersetzen.
    assert len(t["abschnitte"]) == 2
    assert t["abschnitte"][0]["original"].startswith("Ο Γιώργος")

    liste = klient.get(f"/api/sammlungen/{s['id']}/texte").json()
    assert [x["id"] for x in liste] == [t["id"]]
    assert liste[0]["abschnitte"] == 2


def test_ein_block_ohne_leerzeilen_wird_an_satzenden_getrennt(bestand, klient):
    """Sonst stünde der ganze Text in einem einzigen Feld."""
    b, s = bestand
    t = _text(klient, s, inhalt="Πρώτη πρόταση. Δεύτερη πρόταση. Τρίτη!")
    assert len(t["abschnitte"]) == 3


def test_ein_leerer_text_wird_abgewiesen(bestand, klient):
    b, s = bestand
    antwort = klient.post(f"/api/sammlungen/{s['id']}/texte",
                          json={"titel": "Nichts", "inhalt": "   \n  "})
    assert antwort.status_code == 400


# ---------------------------------------------------------------- Deckung

def test_eine_eingetragene_form_gilt_als_bekannt(bestand, klient):
    """Die strenge Richtung: »γράφει« steht als Form da, das Lemma ist
    »γράφω«. Würde nur das Lemma verglichen, hielte die Analyse ein
    gelerntes Wort für unbekannt."""
    b, s = bestand
    t = _text(klient, s)
    d = klient.get(f"/api/texte/{t['id']}/deckung",
                   params={"benutzer_id": b["id"]}).json()
    nach_wort = {w["vergleichsform"]: w for w in d["woerter"]}
    assert nach_wort["γράφει"]["art"] != "unbekannt", (
        "die eingetragene Form wurde nicht gefunden")
    assert nach_wort["γράφει"]["lexem_id"]


def test_ein_nicht_eingetragenes_wort_gilt_als_unbekannt(bestand, klient):
    """Die gefährliche Richtung: hier darf nicht geraten werden.

    »κόκκινο« ist nicht eingetragen. Eine Endungsheuristik könnte es
    für eine Form von »μικρός« halten — und dann stünde »das müsstest
    du können« über einem Text, den man nicht lesen kann.
    """
    b, s = bestand
    t = _text(klient, s)
    d = klient.get(f"/api/texte/{t['id']}/deckung",
                   params={"benutzer_id": b["id"]}).json()
    nach_wort = {w["vergleichsform"]: w for w in d["woerter"]}
    assert nach_wort["κόκκινο"]["art"] == "unbekannt"
    assert nach_wort["κόκκινο"]["lexem_id"] is None


def test_die_flexionsform_eines_fehlenden_wortes_wird_nicht_erraten(bestand, klient):
    """Dieselbe Zusage, ausdrücklich geprüft: »μικρό« ist der Neutrum
    des eingetragenen »μικρός«, aber als FORM nicht eingetragen. Sie
    darf nicht stillschweigend als bekannt durchgehen."""
    b, s = bestand
    t = _text(klient, s)
    d = klient.get(f"/api/texte/{t['id']}/deckung",
                   params={"benutzer_id": b["id"]}).json()
    nach_wort = {w["vergleichsform"]: w for w in d["woerter"]}
    assert nach_wort["μικρό"]["art"] == "unbekannt", (
        "eine nicht eingetragene Form wurde als bekannt gezählt — die "
        "Deckungszahl schmeichelt")


def test_jedes_wort_zaehlt_nur_einmal(bestand, klient):
    """Ein Text mit zwanzigmal »και« ist nicht zu 95 % gedeckt."""
    b, s = bestand
    t = _text(klient, s, inhalt="το μήλο το μήλο το μήλο ξένο")
    d = klient.get(f"/api/texte/{t['id']}/deckung",
                   params={"benutzer_id": b["id"]}).json()
    # »το μήλο« ist EIN Eintrag, nicht zwei Wörter — dazu »ξένο«.
    assert d["verschiedene_woerter"] == 2
    assert d["woerter_gesamt"] == 4
    assert [w["wort"] for w in d["woerter"]][:2] == ["το μήλο", "το μήλο"]


def test_zahlen_und_satzzeichen_zaehlen_nicht_mit(bestand, klient):
    b, s = bestand
    t = _text(klient, s, inhalt="Το μήλο 1821, μικρός — ναι!")
    d = klient.get(f"/api/texte/{t['id']}/deckung",
                   params={"benutzer_id": b["id"]}).json()
    formen = {w["vergleichsform"] for w in d["woerter"]}
    assert "1821" not in formen
    assert "—" not in formen
    # Vergleichsform, nicht Schreibweise: das griechische Schluss-Sigma
    # ist derselbe Buchstabe wie σ.
    assert "μικρόσ" in formen
    assert "μικρός" in {w["wort"] for w in d["woerter"]}


def test_der_lernstand_schlaegt_in_den_toepfen_durch(bestand, klient):
    """Vorher »neu«, nach einer guten Antwort nicht mehr."""
    b, s = bestand
    t = _text(klient, s, inhalt="Το μήλο.")
    vorher = klient.get(f"/api/texte/{t['id']}/deckung",
                        params={"benutzer_id": b["id"]}).json()
    assert vorher["zahlen"]["neu"] >= 1
    assert vorher["zahlen"]["lernen"] == 0

    # Ausdrücklich eine Aufgabe ZU DIESEM Wort — sonst prüft der Test
    # nur, dass irgendwo etwas gelernt wurde.
    lexem_id = vorher["woerter"][0]["lexem_id"]
    alle = klient.get("/api/lernen/naechste", params={
        "benutzer_id": b["id"], "sammlung_id": s["id"], "anzahl": 50}).json()
    a = next(x for x in alle if x["lexem_id"] == lexem_id)
    klient.post("/api/lernen/bewerten", json={
        "benutzer_id": b["id"], "aufgabe_id": a["aufgabe_id"], "bewertung": 3})

    nachher = klient.get(f"/api/texte/{t['id']}/deckung",
                         params={"benutzer_id": b["id"]}).json()
    assert nachher["zahlen"]["lernen"] + nachher["zahlen"]["sitzt"] >= 1, (
        f"der Lernstand kommt in der Deckung nicht an: {nachher['zahlen']}")


def test_das_urteil_sagt_nicht_koennen_wenn_woerter_fehlen(bestand, klient):
    """Der Satz über den Zahlen ist das, was gelesen wird. Er darf nicht
    freundlicher sein als die Zahlen darunter."""
    b, s = bestand
    t = _text(klient, s)
    d = klient.get(f"/api/texte/{t['id']}/deckung",
                   params={"benutzer_id": b["id"]}).json()
    assert d["zahlen"]["unbekannt"] > 0
    assert "müsstest du können" not in d["urteil"], d["urteil"]


def test_wer_alles_hat_bekommt_die_zusage(bestand, klient):
    b, s = bestand
    t = _text(klient, s, inhalt="Το μήλο. Μικρός.")
    d = klient.get(f"/api/texte/{t['id']}/deckung",
                   params={"benutzer_id": b["id"]}).json()
    assert d["zahlen"]["unbekannt"] == 0, d["woerter"]
    assert d["abdeckung"] == 100


# ------------------------------------------------------ Unterstützung

def test_nachschlagen_liefert_den_eigenen_eintrag(bestand, klient):
    """Keine Maschinenübersetzung — der eigene Wortschatz."""
    b, s = bestand
    t = _text(klient, s)
    d = klient.get(f"/api/texte/{t['id']}/nachschlagen",
                   params={"wort": "γράφει"}).json()
    assert d["gefunden"] is True
    assert d["lemma"] == "γράφω"
    assert "schreiben" in d["bedeutungen"][0]["uebersetzungen"]
    # Welche Form ist es? Beim Übersetzen die halbe Miete.
    assert d["merkmale"]["person"] == "3"


def test_nachschlagen_sagt_ehrlich_wenn_nichts_dasteht(bestand, klient):
    b, s = bestand
    t = _text(klient, s)
    d = klient.get(f"/api/texte/{t['id']}/nachschlagen",
                   params={"wort": "κόκκινο"}).json()
    assert d["gefunden"] is False
    assert d["bedeutungen"] == []


def test_meine_fassung_wird_gesichert_und_kommt_wieder(bestand, klient):
    b, s = bestand
    t = _text(klient, s)
    a = t["abschnitte"][0]
    antwort = klient.put(f"/api/abschnitte/{a['id']}/fassung", json={
        "benutzer_id": b["id"], "fassung": "Georg schreibt einen Brief."})
    assert antwort.status_code == 200, antwort.text

    wieder = klient.get(f"/api/texte/{t['id']}",
                        params={"benutzer_id": b["id"]}).json()
    assert wieder["abschnitte"][0]["meine_fassung"] \
        == "Georg schreibt einen Brief."
    assert wieder["abschnitte"][1]["meine_fassung"] == ""


def test_zwei_leute_ueberschreiben_sich_nicht(bestand, klient):
    """Die Fassung gehört mir, die Referenz gehört zum Text."""
    b, s = bestand
    zweite = klient.post("/api/benutzer", json={"name": "Zweite"}).json()
    t = _text(klient, s)
    a = t["abschnitte"][0]
    klient.put(f"/api/abschnitte/{a['id']}/fassung",
               json={"benutzer_id": b["id"], "fassung": "meine"})
    klient.put(f"/api/abschnitte/{a['id']}/fassung",
               json={"benutzer_id": zweite["id"], "fassung": "ihre"})
    meins = klient.get(f"/api/texte/{t['id']}",
                       params={"benutzer_id": b["id"]}).json()
    assert meins["abschnitte"][0]["meine_fassung"] == "meine"


# ------------------------------------------------- Wortwünsche für die KI

def test_ein_markiertes_wort_landet_auf_der_liste(bestand, klient):
    b, s = bestand
    t = _text(klient, s)
    antwort = klient.post(f"/api/texte/{t['id']}/wortwunsch", json={
        "benutzer_id": b["id"], "wort": "κόκκινο",
        "zusammenhang": "Το μήλο είναι κόκκινο και μικρό."})
    assert antwort.status_code == 201, antwort.text

    liste = klient.get("/api/wortwuensche",
                       params={"benutzer_id": b["id"]}).json()
    assert [w["wort"] for w in liste] == ["κόκκινο"]
    assert liste[0]["zusammenhang"].startswith("Το μήλο")
    assert liste[0]["sprache"] == "el"


def test_dasselbe_wort_zweimal_ergibt_einen_eintrag(bestand, klient):
    """Einmal am Satzanfang groß, einmal klein — ein Wort, nicht zwei.
    Sonst legt die KI zwei Vokabeln an."""
    b, s = bestand
    t = _text(klient, s)
    klient.post(f"/api/texte/{t['id']}/wortwunsch",
                json={"benutzer_id": b["id"], "wort": "Κόκκινο"})
    klient.post(f"/api/texte/{t['id']}/wortwunsch",
                json={"benutzer_id": b["id"], "wort": "κόκκινο"})
    liste = klient.get("/api/wortwuensche",
                       params={"benutzer_id": b["id"]}).json()
    assert len(liste) == 1, liste


def test_ein_markiertes_wort_laesst_sich_zuruecknehmen(bestand, klient):
    b, s = bestand
    t = _text(klient, s)
    klient.post(f"/api/texte/{t['id']}/wortwunsch",
                json={"benutzer_id": b["id"], "wort": "κόκκινο"})
    klient.delete(f"/api/texte/{t['id']}/wortwunsch", params={
        "benutzer_id": b["id"], "wort": "κόκκινο"})
    assert klient.get("/api/wortwuensche",
                      params={"benutzer_id": b["id"]}).json() == []


def test_die_deckung_zeigt_was_schon_angefordert_ist(bestand, klient):
    """Sonst markiert man beim zweiten Durchgang dasselbe noch einmal."""
    b, s = bestand
    t = _text(klient, s)
    klient.post(f"/api/texte/{t['id']}/wortwunsch",
                json={"benutzer_id": b["id"], "wort": "κόκκινο"})
    d = klient.get(f"/api/texte/{t['id']}/deckung",
                   params={"benutzer_id": b["id"]}).json()
    nach_wort = {w["vergleichsform"]: w for w in d["woerter"]}
    assert nach_wort["κόκκινο"]["gewuenscht"] is True
    assert nach_wort["μικρό"]["gewuenscht"] is False


def test_die_wortwuensche_sind_persoenlich(bestand, klient):
    b, s = bestand
    zweite = klient.post("/api/benutzer", json={"name": "Zweite"}).json()
    t = _text(klient, s)
    klient.post(f"/api/texte/{t['id']}/wortwunsch",
                json={"benutzer_id": b["id"], "wort": "κόκκινο"})
    assert klient.get("/api/wortwuensche",
                      params={"benutzer_id": zweite["id"]}).json() == []
