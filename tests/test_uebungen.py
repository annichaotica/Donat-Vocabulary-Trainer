"""Übungssätze, Texte und die Bewertung freier Übersetzungen.

Ein Satz und ein Text sind derselbe Gegenstand mit unterschiedlich vielen
Abschnitten — darum liegen beide in denselben Tabellen. Geprüft wird hier
vor allem, was dabei schiefgehen könnte: eine geratene Satzzuordnung, eine
richtige Übersetzung, die als falsch gilt, und eine Freigabe, die ein
Import stillschweigend überschreibt.
"""

import pytest


def _aufbau(klient, sprache="el"):
    b = klient.post("/api/benutzer", json={"name": "Übende"}).json()
    s = klient.post("/api/sammlungen", json={
        "besitzer_id": b["id"], "name": "Griechisch", "sprache": sprache}).json()
    return b, s


SATZ = {
    "typ": "satz", "lektion_nr": 39,
    "zielsprache": "Χθες πήγα στο θέατρο.",
    "grundsprache": "Gestern ging ich ins Theater.",
    "alternativen_zielsprache": ["Εχθές πήγα στο θέατρο."],
    "alternativen_grundsprache": ["Gestern bin ich ins Theater gegangen."],
    "richtungen": ["el-de", "de-el"],
    "quelle": {"art": "ki"},
}


def anlegen(klient, sammlung_id, eintrag=None):
    antwort = klient.post(f"/api/sammlungen/{sammlung_id}/uebungen",
                          json=eintrag or SATZ)
    assert antwort.status_code == 201, antwort.text
    return antwort.json()


def importieren(klient, sammlung_id, eintraege, **kw):
    antwort = klient.post(f"/api/sammlungen/{sammlung_id}/import/uebungen",
                          json={"eintraege": eintraege, **kw})
    assert antwort.status_code == 200, antwort.text
    return antwort.json()


def pruefen(klient, aufgabe_id, antwort_text):
    a = klient.post(f"/api/textaufgaben/{aufgabe_id}/pruefen",
                    json={"antwort": antwort_text})
    assert a.status_code == 200, a.text
    return a.json()


def richtung(uebung, typ):
    return next(a for a in uebung["aufgaben"] if a["typ"] == typ and a["aktiv"])


# --------------------------------------------------------------- Anlegen

def test_satz_mit_beiden_richtungen(klient):
    _b, s = _aufbau(klient)
    u = anlegen(klient, s["id"])
    assert u["typ"] == "satz"
    assert u["richtungen"] == ["hin", "rueck"]
    assert len(u["abschnitte"]) == 1
    assert u["lektion"]["nr"] == 39
    # Ungeprüft, bis ein Mensch freigibt — wie bei den Formen.
    assert u["geprueft"] is False
    assert {a["typ"] for a in u["aufgaben"]} == {"uebersetzung_hin",
                                                 "uebersetzung_rueck"}
    # Ein Satz wird verglichen, nicht selbst eingeschätzt.
    assert {a["bewertung_art"] for a in u["aufgaben"]} == {"genau"}


def test_titel_entsteht_von_selbst(klient):
    _b, s = _aufbau(klient)
    u = anlegen(klient, s["id"])
    assert u["titel"] == "Χθες πήγα στο θέατρο."


def test_nur_eine_richtung_erzeugt_nur_eine_aufgabe(klient):
    _b, s = _aufbau(klient)
    u = anlegen(klient, s["id"], {**SATZ, "richtungen": ["el-de"]})
    aktiv = [a for a in u["aufgaben"] if a["aktiv"]]
    assert len(aktiv) == 1 and aktiv[0]["typ"] == "uebersetzung_hin"


def test_fremde_richtung_wird_abgewiesen(klient):
    """"fr-de" in einer griechischen Sammlung ist ein Versehen, kein Wunsch."""
    _b, s = _aufbau(klient)
    antwort = klient.post(f"/api/sammlungen/{s['id']}/uebungen",
                          json={**SATZ, "richtungen": ["fr-de"]})
    assert antwort.status_code == 400
    assert "passt nicht zu dieser Sammlung" in antwort.json()["detail"]


# ------------------------------------------------------------- Bewerten

@pytest.mark.parametrize("antwort,erwartet", [
    ("Χθες πήγα στο θέατρο.", "richtig"),
    ("Εχθές πήγα στο θέατρο.", "richtig"),      # die Alternative
    ("εχθές πηγα στο θεατρο", "fast"),          # nur Akzente
    ("Χθες πήγα στο σπίτι.", "falsch"),
    ("", "falsch"),
])
def test_bewertung_der_rueckrichtung(klient, antwort, erwartet):
    _b, s = _aufbau(klient)
    u = anlegen(klient, s["id"])
    ergebnis = pruefen(klient, richtung(u, "uebersetzung_rueck")["id"], antwort)
    assert ergebnis["urteil"] == erwartet, ergebnis


def test_eine_richtige_uebersetzung_gilt_auch_als_alternative(klient):
    """"Gestern bin ich ins Theater gegangen" ist richtig. Dass es nicht die
    zuerst aufgeschriebene Fassung ist, darf nicht gegen sie zählen."""
    _b, s = _aufbau(klient)
    u = anlegen(klient, s["id"])
    ergebnis = pruefen(klient, richtung(u, "uebersetzung_hin")["id"],
                       "Gestern bin ich ins Theater gegangen.")
    assert ergebnis["urteil"] == "richtig"


def test_die_rueckmeldung_nennt_das_abweichende_wort(klient):
    """"falsch" ist keine Auskunft. Welches Wort es war, ist eine."""
    _b, s = _aufbau(klient)
    u = anlegen(klient, s["id"])
    ergebnis = pruefen(klient, richtung(u, "uebersetzung_rueck")["id"],
                       "Χθες πήγα στο σπίτι.")
    assert ergebnis["stellen"] == [{"art": "anders", "erwartet": "θέατρο",
                                    "bekommen": "σπίτι"}]
    assert "θέατρο" in ergebnis["hinweis"]
    assert ergebnis["woerter_richtig"] == 3
    assert ergebnis["woerter_gesamt"] == 4


def test_geprueft_wird_in_der_sprache_der_antwort(klient):
    """Eine deutsche Antwort darf nicht nach griechischen Akzentregeln
    beurteilt werden — und umgekehrt."""
    _b, s = _aufbau(klient)
    u = anlegen(klient, s["id"])
    assert pruefen(klient, richtung(u, "uebersetzung_hin")["id"],
                   "Gestern ging ich ins Theater.")["sprache"] == "de"
    assert pruefen(klient, richtung(u, "uebersetzung_rueck")["id"],
                   "Χθες πήγα στο θέατρο.")["sprache"] == "el"


def test_bei_laengerem_bleibt_die_einschaetzung_beim_menschen(klient):
    """Bei einem Textblock passt ein genauer Vergleich selten. Er findet
    trotzdem statt — aber er zählt nicht.

    Dieser Test stand hier mit einer WORTGLEICHEN Antwort als Beispiel
    und behauptete »zählt nicht« — also genau das, was sie später als
    Fehler gemeldet hat: »Wie kommt das? Es ist doch sogar wortgleich.«
    Er hat den Fehler nicht gefunden, er hat ihn festgeschrieben. Das
    Beispiel ist jetzt eine Antwort, die tatsächlich abweicht; dass
    Wortgleiches zählt, prüft
    test_wortgleich_zaehlt_auch_beim_text.
    """
    _b, s = _aufbau(klient)
    u = anlegen(klient, s["id"], {
        "typ": "text", "titel": "Στο θέατρο",
        "zielsprache": "Χθες πήγα στο θέατρο. Η παράσταση ήταν ωραία.",
        "grundsprache": "Gestern ging ich ins Theater. Die Vorstellung war schön.",
        "richtungen": ["el-de"]})
    assert len(u["abschnitte"]) == 2
    aufgabe = [a for a in u["aufgaben"] if a["aktiv"]][0]
    assert aufgabe["bewertung_art"] == "selbst"
    ergebnis = pruefen(klient, aufgabe["id"], "Gestern war ich im Theater.")
    assert ergebnis["wortgleich"] is False
    assert ergebnis["zaehlt"] is False


# ----------------------------------------------------------- Abschnitte

def test_text_wird_in_saetze_geteilt(klient):
    _b, s = _aufbau(klient)
    u = anlegen(klient, s["id"], {
        "typ": "text",
        "zielsprache": "Χθες πήγα στο θέατρο. Η παράσταση ήταν ωραία.",
        "grundsprache": "Gestern ging ich ins Theater. Die Vorstellung war schön.",
        "richtungen": ["el-de"]})
    assert [a["original"] for a in u["abschnitte"]] == [
        "Χθες πήγα στο θέατρο.", "Η παράσταση ήταν ωραία."]
    assert u["abschnitte"][1]["referenz"] == "Die Vorstellung war schön."


def test_ungleiche_satzzahl_wird_nicht_geraten(klient):
    """Eine falsch zugeordnete Referenzübersetzung ist schlimmer als ein
    ungeteilter Text: die Rückmeldung verglich dann mit dem falschen Satz."""
    _b, s = _aufbau(klient)
    bericht = importieren(klient, s["id"], [{
        "typ": "text",
        "zielsprache": "Χθες πήγα στο θέατρο. Η παράσταση ήταν ωραία.",
        "grundsprache": "Gestern war ich im Theater und die Vorstellung "
                        "war schön.",
        "richtungen": ["el-de"]}])
    eintrag = bericht["eintraege"][0]
    assert eintrag["abschnitte"] == 1
    assert any("Nicht in Sätze geteilt" in b for b in eintrag["befunde"])


def test_abschnitte_ausdruecklich_angeben(klient):
    _b, s = _aufbau(klient)
    u = anlegen(klient, s["id"], {
        "typ": "dialog", "titel": "Στο ταμείο",
        "abschnitte": [
            {"zielsprache": "Καλημέρα!", "grundsprache": "Guten Morgen!",
             "alternativen_grundsprache": ["Guten Tag!"]},
            {"zielsprache": "Τι θα πάρετε;", "grundsprache": "Was nehmen Sie?"}],
        "richtungen": ["el-de"]})
    assert len(u["abschnitte"]) == 2
    assert u["abschnitte"][0]["referenz_varianten"] == ["Guten Tag!"]
    erste = [a for a in u["aufgaben"]
             if a["abschnitt_id"] == u["abschnitte"][0]["id"]][0]
    assert pruefen(klient, erste["id"], "Guten Tag!")["urteil"] == "richtig"


# ----------------------------------------------------------- Mengenimport

def test_import_ist_wiederholbar(klient):
    _b, s = _aufbau(klient)
    erster = importieren(klient, s["id"], [SATZ])
    assert erster["angelegt"] == 1
    zweiter = importieren(klient, s["id"], [SATZ])
    assert (zweiter["angelegt"], zweiter["aktualisiert"]) == (0, 1)
    assert klient.get(f"/api/sammlungen/{s['id']}/uebungen").json()["gesamt"] == 1


def test_probelauf_schreibt_nichts(klient):
    _b, s = _aufbau(klient)
    bericht = importieren(klient, s["id"], [SATZ], nur_pruefen=True)
    assert bericht["angelegt"] == 1
    assert klient.get(f"/api/sammlungen/{s['id']}/uebungen").json()["gesamt"] == 0


def test_freigegebene_uebung_wird_nicht_ueberschrieben(klient):
    """Wie bei den Formen: hat ein Mensch freigegeben, meldet ein Import die
    Abweichung und entscheidet nicht selbst."""
    _b, s = _aufbau(klient)
    u = anlegen(klient, s["id"])
    # Ohne Kennung ist der Zieltext der Schlüssel — ein geänderter Zieltext
    # wäre dann ein anderer Eintrag. Erst die Kennung macht ihn wiederfindbar.
    klient.patch(f"/api/uebungen/{u['id']}", json={"kennung": "L39-1"})
    klient.post(f"/api/uebungen/{u['id']}/freigabe")
    bericht = importieren(klient, s["id"], [
        {**SATZ, "kennung": "L39-1", "zielsprache": "Χθες πήγα στο σινεμά."}])
    eintrag = bericht["eintraege"][0]
    assert eintrag["zustand"] == "aktualisiert"
    assert eintrag["abweichungen"][0]["steht"] == "Χθες πήγα στο θέατρο."
    assert "freigegeben" in eintrag["abweichungen"][0]["grund"]
    gelesen = klient.get(f"/api/uebungen/{u['id']}").json()
    assert gelesen["abschnitte"][0]["original"] == "Χθες πήγα στο θέατρο."


def test_fehlerhafte_eintraege_halten_den_lauf_nicht_auf(klient):
    _b, s = _aufbau(klient)
    bericht = importieren(klient, s["id"], [
        SATZ,
        {"typ": "quatsch", "zielsprache": "x"},
        {"typ": "satz", "grundsprache": "ohne Zielsprache"}])
    assert (bericht["angelegt"], bericht["abgelehnt"]) == (1, 2)
    gruende = " ".join(f for e in bericht["eintraege"] for f in e.get("fehler", []))
    assert "Unbekannter Typ" in gruende
    assert "Keine Zielsprache" in gruende


# ---------------------------------------------------------------- Ändern

def test_aenderung_nimmt_die_freigabe_zurueck(klient):
    _b, s = _aufbau(klient)
    u = anlegen(klient, s["id"])
    klient.post(f"/api/uebungen/{u['id']}/freigabe")
    assert klient.get(f"/api/uebungen/{u['id']}").json()["geprueft"] is True
    geaendert = klient.patch(f"/api/uebungen/{u['id']}",
                             json={"zielsprache": "Χθες πήγα στο σινεμά."}).json()
    assert geaendert["geprueft"] is False
    assert geaendert["abschnitte"][0]["original"] == "Χθες πήγα στο σινεμά."


def test_teilaenderung_laesst_das_uebrige_stehen(klient):
    _b, s = _aufbau(klient)
    u = anlegen(klient, s["id"])
    geaendert = klient.patch(f"/api/uebungen/{u['id']}",
                             json={"niveau": "A2"}).json()
    assert geaendert["niveau"] == "A2"
    assert geaendert["abschnitte"][0]["original"] == "Χθες πήγα στο θέατρο."
    assert geaendert["abschnitte"][0]["varianten"] == ["Εχθές πήγα στο θέατρο."]
    assert geaendert["richtungen"] == ["hin", "rueck"]


def test_eine_abgewaehlte_richtung_verliert_nicht_den_lernstand(klient):
    """Die Aufgabe wird stillgelegt, nicht gelöscht — sonst wäre der
    Lernstand weg, wenn jemand versehentlich abwählt und zurücknimmt."""
    _b, s = _aufbau(klient)
    u = anlegen(klient, s["id"])
    vorher = richtung(u, "uebersetzung_hin")["id"]
    geaendert = klient.patch(f"/api/uebungen/{u['id']}",
                             json={"richtungen": ["de-el"]}).json()
    hin = next(a for a in geaendert["aufgaben"] if a["id"] == vorher)
    assert hin["aktiv"] == 0
    zurueck = klient.patch(f"/api/uebungen/{u['id']}",
                           json={"richtungen": ["el-de", "de-el"]}).json()
    assert next(a for a in zurueck["aufgaben"] if a["id"] == vorher)["aktiv"] == 1


# ------------------------------------------------------ Quelle und Verweis

def test_fremder_text_wird_verlinkt(klient):
    _b, s = _aufbau(klient)
    u = anlegen(klient, s["id"], {
        "typ": "zeitungsstil", "titel": "Στην Αθήνα",
        "zielsprache": "Η Αθήνα είναι η πρωτεύουσα.",
        "grundsprache": "Athen ist die Hauptstadt.",
        "richtungen": ["el-de"],
        "quelle": {"art": "verweis", "titel": "Καθημερινή",
                   "url": "https://www.kathimerini.gr/beispiel"}})
    assert u["quelle"]["art"] == "verweis"
    assert u["quelle"]["url"] == "https://www.kathimerini.gr/beispiel"


def test_verweis_ohne_angabe_wird_abgewiesen(klient):
    _b, s = _aufbau(klient)
    antwort = klient.post(f"/api/sammlungen/{s['id']}/uebungen",
                          json={**SATZ, "quelle": {"art": "verweis"}})
    assert antwort.status_code == 400
    assert "verweis" in antwort.json()["detail"]


# -------------------------------------------------------- Deckung prüfen

def _wortschatz(klient, sammlung_id):
    klient.post(f"/api/sammlungen/{sammlung_id}/import/vokabeln", json={
        "eintraege": [
            {"lemma": "γράφω", "wortart": "verb", "lektion_nr": 5,
             "bedeutungen": [{"uebersetzungen": ["schreiben", "aufschreiben"]}],
             "formen": [{"text": t, "merkmale": {
                 "modus": "indikativ", "tempus": "aorist",
                 "person": p, "numerus": n}}
                 for t, (p, n) in zip(
                     ["έγραψα", "έγραψες", "έγραψε",
                      "γράψαμε", "γράψατε", "έγραψαν"],
                     [("1", "sg"), ("2", "sg"), ("3", "sg"),
                      ("1", "pl"), ("2", "pl"), ("3", "pl")])]},
            {"lemma": "το γράμμα", "wortart": "substantiv", "lektion_nr": 5,
             "bedeutungen": [{"uebersetzungen": ["der Brief", "das Schreiben"]}],
             "formen": [{"text": "γράμμα",
                         "merkmale": {"kasus": "akk", "numerus": "sg"}}]},
            {"lemma": "χθες", "wortart": "adverb", "lektion_nr": 40,
             "bedeutungen": [{"uebersetzungen": ["gestern", "neulich"]}]}]})


def deckung(klient, sammlung_id, text, **kw):
    antwort = klient.post(f"/api/sammlungen/{sammlung_id}/text/pruefen",
                          json={"text": text, **kw})
    assert antwort.status_code == 200, antwort.text
    return antwort.json()


def test_deckung_findet_ueber_jede_form(klient):
    """Wer έγραψαν liest, hat γράφω vor sich. Ohne die Formentabelle wäre
    jede gebeugte Form unbekannt."""
    _b, s = _aufbau(klient)
    _wortschatz(klient, s["id"])
    b = deckung(klient, s["id"], "Έγραψαν ένα γράμμα.")
    bekannt = {e["wort"]: e["lemma"] for e in b["bekannt"]}
    assert bekannt["Έγραψαν"] == "γράφω"
    assert bekannt["γράμμα"] == "το γράμμα"
    assert [e["wort"] for e in b["unbekannt"]] == ["ένα"]


def test_deckung_trennt_zu_spaet_von_unbekannt(klient):
    """Beides muss der Schreibende wissen, aber es ist nicht dasselbe:
    "zu spät" lässt sich vorziehen, "unbekannt" muss erst eingetragen
    werden."""
    _b, s = _aufbau(klient)
    _wortschatz(klient, s["id"])
    b = deckung(klient, s["id"], "Χθες έγραψαν ένα γράμμα.", bis_lektion=12)
    assert [e["wort"] for e in b["zu_spaet"]] == ["Χθες"]
    assert b["zu_spaet"][0]["lektion_nr"] == 40
    assert [e["wort"] for e in b["unbekannt"]] == ["ένα"]
    assert b["deckung"] == 0.5


def test_partikeln_gelten_nicht_als_unbekannt(klient):
    """θα ist Teil der Futurform, kein eigener Eintrag. Es als fehlende
    Vokabel zu melden, wäre eine Dauerstörung."""
    _b, s = _aufbau(klient)
    _wortschatz(klient, s["id"])
    b = deckung(klient, s["id"], "Θα γράψατε δεν να ας μην.")
    assert [e["wort"] for e in b["unbekannt"]] == []


def test_haeufigkeit_steht_vorn(klient):
    _b, s = _aufbau(klient)
    _wortschatz(klient, s["id"])
    b = deckung(klient, s["id"], "ένα και ένα και ένα, και τι;")
    assert b["unbekannt"][0]["wort"] == "ένα"
    assert b["unbekannt"][0]["anzahl"] == 3


# ------------------------------------------------------------------- MCP

def test_uebungen_ueber_den_mcp(klient):
    """Der ganze Weg, wie ein Agent ihn geht: erst prüfen, dann schreiben."""
    from test_mcp import person_mit_token, werkzeug
    mcp = person_mit_token(klient, "Verwalterin")
    s = klient.post("/api/sammlungen", json={
        "besitzer_id": mcp.benutzer["id"], "name": "Griechisch",
        "sprache": "el"}).json()
    _wortschatz(klient, s["id"])

    b = werkzeug(mcp, "text_pruefen", sammlung_id=s["id"],
                 text="Χθες έγραψαν ένα γράμμα.", bis_lektion=12)
    assert [e["wort"] for e in b["unbekannt"]] == ["ένα"]

    bericht = werkzeug(mcp, "uebungen_importieren", sammlung_id=s["id"],
                       eintraege=[SATZ], nur_pruefen=True)
    assert bericht["angelegt"] == 1
    assert werkzeug(mcp, "uebungen_auflisten",
                    sammlung_id=s["id"])["gesamt"] == 0

    angelegt = werkzeug(mcp, "uebung_anlegen", sammlung_id=s["id"], **SATZ)
    assert len(angelegt["aufgaben"]) == 2
    assert "ungeprüft" in angelegt["hinweis"]

    liste = werkzeug(mcp, "uebungen_auflisten", sammlung_id=s["id"],
                     nur_ungepruefte=True)
    assert liste["gesamt"] == 1 and liste["uebungen"][0]["lektion_nr"] == 39

    geaendert = werkzeug(mcp, "uebung_aendern",
                         uebung_id=angelegt["uebung_id"], niveau="A2")
    assert geaendert["uebung_id"] == angelegt["uebung_id"]


def test_fremde_sammlung_bleibt_dicht(klient):
    from test_mcp import person_mit_token, werkzeug
    eine = person_mit_token(klient, "Verwalterin")
    andere = person_mit_token(klient, "Fremde")
    s = klient.post("/api/sammlungen", json={
        "besitzer_id": eine.benutzer["id"], "name": "Privat",
        "sprache": "el"}).json()
    ergebnis = werkzeug(andere, "uebung_anlegen", sammlung_id=s["id"], **SATZ)
    assert ergebnis.get("_werkzeugfehler")
