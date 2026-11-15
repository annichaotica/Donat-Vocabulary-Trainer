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


# -------------------------------------------- Übersetzungsvorschlag

def test_eine_referenzuebersetzung_laesst_sich_hinterlegen(bestand, klient):
    """»Einen Übersetzungsvorschlag kann man sich vermutlich wieder nur
    von der angeschlossenen KI holen?«

    Ja — und bis hierher konnte sie es nicht einmal. Der Platz dafür
    stand im Schema, die Oberfläche zeigte ihn an, aber es gab keinen
    Weg, ihn zu füllen: kein Formular, kein Endpunkt, kein Werkzeug.
    Eine halbe Funktion, die aussah wie eine ganze.
    """
    b, s = bestand
    t = _text(klient, s)
    a = t["abschnitte"][0]
    antwort = klient.put(f"/api/texte/{t['id']}/referenz", json={
        "fassungen": {str(a["id"]): "Georg schreibt einen Brief."}})
    assert antwort.status_code == 200, antwort.text

    wieder = klient.get(f"/api/texte/{t['id']}",
                        params={"benutzer_id": b["id"]}).json()
    assert wieder["abschnitte"][0]["referenz"] == "Georg schreibt einen Brief."


def test_der_vorschlag_ueberschreibt_die_eigene_fassung_nicht(bestand, klient):
    """Zwei verschiedene Dinge: die Referenz gehört zum Text, der
    Versuch zur Person. Liefe das zusammen, löschte ein Vorschlag von
    außen die eigene Arbeit."""
    b, s = bestand
    t = _text(klient, s)
    a = t["abschnitte"][0]
    klient.put(f"/api/abschnitte/{a['id']}/fassung",
               json={"benutzer_id": b["id"], "fassung": "mein Versuch"})
    klient.put(f"/api/texte/{t['id']}/referenz",
               json={"fassungen": {str(a["id"]): "die Musterlösung"}})

    wieder = klient.get(f"/api/texte/{t['id']}",
                        params={"benutzer_id": b["id"]}).json()
    assert wieder["abschnitte"][0]["meine_fassung"] == "mein Versuch"
    assert wieder["abschnitte"][0]["referenz"] == "die Musterlösung"


def test_ein_fremder_abschnitt_wird_abgewiesen(bestand, klient):
    """Sonst schriebe ein Vorschlag in einen anderen Text."""
    b, s = bestand
    eins = _text(klient, s, titel="Eins")
    zwei = _text(klient, s, titel="Zwei")
    antwort = klient.put(f"/api/texte/{eins['id']}/referenz", json={
        "fassungen": {str(zwei["abschnitte"][0]["id"]): "falsch zugeordnet"}})
    assert antwort.status_code == 400, antwort.text


def test_die_deckung_bringt_die_bedeutungen_mit(bestand, klient):
    """Für die Wort-für-Wort-Hilfe — ohne sie bräuchte die Oberfläche
    je Wort einen eigenen Rundlauf."""
    b, s = bestand
    t = _text(klient, s)
    d = klient.get(f"/api/texte/{t['id']}/deckung",
                   params={"benutzer_id": b["id"]}).json()
    bekannt = [w for w in d["woerter"] if w["lexem_id"]]
    assert bekannt, "nichts erkannt — dann prüft der Test nichts"
    assert any(w.get("bedeutung") for w in bekannt), bekannt[:3]
    # Unbekannte haben keine, und das muss so sein: eine erfundene
    # Bedeutung wäre schlimmer als keine.
    assert all(w.get("bedeutung") is None
               for w in d["woerter"] if not w["lexem_id"])


# ------------------------------- alle Unbekannten auf einmal

def test_alle_unbekannten_auf_einmal(bestand, klient):
    """»Wenn ich einen ganz neuen Artikel hier rein poste, dann müsste
    ich alle Wörter markieren können, die ich nicht kenne. Wenn ich
    jetzt 260 mal klicke, macht das keinen Spaß.«

    Gemessen an einem echten Zeitungsartikel: 1145 verschiedene
    Wörter, 840 davon unbekannt.
    """
    b, s = bestand
    t = _text(klient, s)
    vorher = klient.get(f"/api/texte/{t['id']}/deckung",
                        params={"benutzer_id": b["id"]}).json()
    offen = vorher["zahlen"]["unbekannt"]
    assert offen > 0, "nichts unbekannt — dann prüft der Test nichts"

    antwort = klient.post(f"/api/texte/{t['id']}/wortwuensche/alle",
                          params={"benutzer_id": b["id"]})
    assert antwort.status_code == 201, antwort.text
    assert antwort.json()["angefordert"] == offen

    liste = klient.get("/api/wortwuensche",
                       params={"benutzer_id": b["id"]}).json()
    assert len(liste) == offen


def test_haeufiges_steht_oben(bestand, klient):
    """Bei achthundert Wörtern ist die Reihenfolge das Wichtigste: wer
    oben anfängt, hat auch dann etwas davon, wenn er nicht durchkommt."""
    b, s = bestand
    t = _text(klient, s, inhalt="ξένο ξένο ξένο. άλλο άλλο. drittes.")
    klient.post(f"/api/texte/{t['id']}/wortwuensche/alle",
                params={"benutzer_id": b["id"]})
    liste = klient.get("/api/wortwuensche",
                       params={"benutzer_id": b["id"]}).json()
    assert [w["wort"] for w in liste][:2] == ["ξένο", "άλλο"], liste
    assert liste[0]["vorkommen"] == 3


def test_schon_angefordertes_wird_nicht_verdoppelt(bestand, klient):
    b, s = bestand
    t = _text(klient, s)
    klient.post(f"/api/texte/{t['id']}/wortwuensche/alle",
                params={"benutzer_id": b["id"]})
    erst = len(klient.get("/api/wortwuensche",
                          params={"benutzer_id": b["id"]}).json())
    klient.post(f"/api/texte/{t['id']}/wortwuensche/alle",
                params={"benutzer_id": b["id"]})
    assert len(klient.get("/api/wortwuensche",
                          params={"benutzer_id": b["id"]}).json()) == erst


def test_alles_laesst_sich_zurueckziehen(bestand, klient):
    """Ein Knopf, der achthundert Einträge anlegt, braucht einen
    Gegenknopf — sonst traut sich niemand, ihn zu drücken."""
    b, s = bestand
    t = _text(klient, s)
    klient.post(f"/api/texte/{t['id']}/wortwuensche/alle",
                params={"benutzer_id": b["id"]})
    antwort = klient.delete(f"/api/texte/{t['id']}/wortwuensche/alle",
                            params={"benutzer_id": b["id"]})
    assert antwort.status_code == 200, antwort.text
    assert klient.get("/api/wortwuensche",
                      params={"benutzer_id": b["id"]}).json() == []


def test_erledigtes_bleibt_beim_zuruecknehmen_stehen(bestand, klient):
    """Was die KI schon eingetragen hat, ist der Beleg dafür, woher die
    Vokabel stammt."""
    b, s = bestand
    t = _text(klient, s)
    klient.post(f"/api/texte/{t['id']}/wortwuensche/alle",
                params={"benutzer_id": b["id"]})
    import datenbank as dbm
    db = dbm.verbindung()
    try:
        eine = dbm.wert(db, "SELECT id FROM wortwunsch LIMIT 1")
        db.execute("UPDATE wortwunsch SET erledigt = 1 WHERE id = ?", (eine,))
        db.commit()
    finally:
        db.close()
    klient.delete(f"/api/texte/{t['id']}/wortwuensche/alle",
                  params={"benutzer_id": b["id"]})
    alle = klient.get("/api/wortwuensche", params={
        "benutzer_id": b["id"], "offen": False}).json()
    assert len(alle) == 1


def test_eine_grosse_liste_verdeckt_keine_kleine(klient):
    """»Die 89 neuen mittelhochdeutschen Wörter werden mir noch nicht
    angezeigt.«

    Sie waren da. Nur steht die Liste nach Häufigkeit, und zwar quer
    über alle Sammlungen: aus 825 griechischen und 89
    mittelhochdeutschen Wünschen bestand das Häppchen von 40 aus
    vierzig griechischen. Die KI sah nach, fand kein einziges
    mittelhochdeutsches Wort und schloss daraus, es gebe keines.

    Darum nennt die Antwort jetzt immer, WELCHE Sammlungen etwas offen
    haben — auch die, aus denen gerade nichts im Häppchen ist.
    """
    import sys
    sys.path.insert(0, "backend")
    import datenbank as dbm
    import mcp_dienst

    b = klient.post("/api/benutzer", json={"name": "Lesende"}).json()
    gross = klient.post("/api/sammlungen", json={
        "besitzer_id": b["id"], "name": "Griechisch", "sprache": "el"}).json()
    klein = klient.post("/api/sammlungen", json={
        "besitzer_id": b["id"], "name": "Mittelhochdeutsch",
        "sprache": "gmh"}).json()

    db = dbm.verbindung()
    try:
        # Viele häufige Wünsche in der einen, wenige in der anderen.
        for i in range(45):
            db.execute("""INSERT INTO wortwunsch
                            (benutzer_id, sammlung_id, wort, vergleichsform,
                             vorkommen)
                          VALUES (?, ?, ?, ?, ?)""",
                       (b["id"], gross["id"], f"g{i}", f"g{i}", 99))
        for i in range(3):
            db.execute("""INSERT INTO wortwunsch
                            (benutzer_id, sammlung_id, wort, vergleichsform,
                             vorkommen)
                          VALUES (?, ?, ?, ?, ?)""",
                       (b["id"], klein["id"], f"m{i}", f"m{i}", 1))
        db.commit()
        person = dict(dbm.zeile(db, "SELECT * FROM benutzer WHERE id = ?",
                                (b["id"],)))
        d = mcp_dienst.offene_woerter_lesen(db, person)
    finally:
        db.close()

    # Im Häppchen steht nichts Mittelhochdeutsches …
    assert all(w["sammlung"] == "Griechisch" for w in d["woerter"])
    # … aber die Antwort verschweigt es trotzdem nicht.
    assert d["offen_nach_sammlung"]["Mittelhochdeutsch"] == 3
    assert d["offen_nach_sammlung"]["Griechisch"] == 45
    assert "Mittelhochdeutsch (3)" in d["hinweis"]
    assert "sammlung_id" in d["hinweis"]


def test_wuensche_anderer_aus_eigener_schreibsammlung(klient):
    """»Der Konnektor im ChatGPT war für Max gedacht, der nutzt den
    gleichen Zugang. Das heißt, der müsste dann auch Anforderungen von
    Max abholen.«

    In einer Familie hängt der Zugang an EINEM Profil, die Wünsche
    entstehen aber an allen. Die Regel ist deshalb nicht »meine
    Wünsche«, sondern: **was ich erfüllen darf, soll ich auch sehen.**
    Wer in Max' Sammlung schreiben darf, kann Max' Wünsche erfüllen.
    """
    import sys
    sys.path.insert(0, "backend")
    import datenbank as dbm
    import mcp_dienst

    anni = klient.post("/api/benutzer", json={"name": "Annuschka"}).json()
    max_ = klient.post("/api/benutzer", json={"name": "Max"}).json()
    seine = klient.post("/api/sammlungen", json={
        "besitzer_id": max_["id"], "name": "Mittelhochdeutsch",
        "sprache": "gmh"}).json()
    fremd = klient.post("/api/sammlungen", json={
        "besitzer_id": max_["id"], "name": "Nur zum Lesen",
        "sprache": "en"}).json()
    klient.put(f"/api/sammlungen/{seine['id']}/zugriff", json={
        "benutzer_id": anni["id"], "recht": "schreiben"})
    klient.put(f"/api/sammlungen/{fremd['id']}/zugriff", json={
        "benutzer_id": anni["id"], "recht": "lesen"})

    db = dbm.verbindung()
    try:
        for sid, wort in ((seine["id"], "ouwê"), (fremd["id"], "yonder")):
            db.execute("""INSERT INTO wortwunsch
                            (benutzer_id, sammlung_id, wort, vergleichsform,
                             vorkommen)
                          VALUES (?, ?, ?, ?, 1)""",
                       (max_["id"], sid, wort, wort))
        db.commit()
        person = dict(dbm.zeile(db, "SELECT * FROM benutzer WHERE id = ?",
                                (anni["id"],)))
        d = mcp_dienst.offene_woerter_lesen(db, person)
        woerter = {w["wort"]: w for w in d["woerter"]}
    finally:
        db.close()

    # Aus der Schreibsammlung: ja — und mit dem Namen dessen, der ihn
    # gestellt hat, denn das ist nicht die Person am Zugang.
    assert "ouwê" in woerter
    assert woerter["ouwê"]["angefordert_von"] == "Max"
    assert woerter["ouwê"]["von_mir"] is False
    # Aus der Nur-Lese-Sammlung: nein. Sehen, was man nicht erfüllen
    # kann, wäre eine Liste, die nie kürzer wird.
    assert "yonder" not in woerter


def test_fremden_wunsch_darf_man_auch_abhaken(klient):
    """Sonst sähe man ihn bei jedem Abruf wieder — eine Liste, die sich
    nicht abarbeiten lässt, ist schlimmer als keine."""
    import sys
    sys.path.insert(0, "backend")
    import datenbank as dbm
    import mcp_dienst

    anni = klient.post("/api/benutzer", json={"name": "Annuschka"}).json()
    max_ = klient.post("/api/benutzer", json={"name": "Max"}).json()
    s = klient.post("/api/sammlungen", json={
        "besitzer_id": max_["id"], "name": "Mhd", "sprache": "gmh"}).json()
    klient.put(f"/api/sammlungen/{s['id']}/zugriff", json={
        "benutzer_id": anni["id"], "recht": "schreiben"})

    db = dbm.verbindung()
    try:
        cur = db.execute("""INSERT INTO wortwunsch
                              (benutzer_id, sammlung_id, wort, vergleichsform,
                               vorkommen)
                            VALUES (?, ?, 'ouwê', 'ouwê', 1)""",
                         (max_["id"], s["id"]))
        db.commit()
        person = dict(dbm.zeile(db, "SELECT * FROM benutzer WHERE id = ?",
                                (anni["id"],)))
        mcp_dienst.offenes_wort_erledigen(db, person, cur.lastrowid)
        db.commit()
        assert dbm.wert(db, "SELECT erledigt FROM wortwunsch WHERE id = ?",
                        (cur.lastrowid,)) == 1
    finally:
        db.close()


def test_sammelabhaken(klient):
    """»Über die Schnittstelle geht nur einer pro Aufruf, das wären
    über 800 Aufrufe.«

    Bei einem Zeitungsartikel mit 840 unbekannten Wörtern ist das kein
    Komfortproblem: einzeln abzuhaken dauerte länger als das Eintragen.
    """
    import sys
    sys.path.insert(0, "backend")
    import datenbank as dbm

    b = klient.post("/api/benutzer", json={"name": "Lesende"}).json()
    s = klient.post("/api/sammlungen", json={
        "besitzer_id": b["id"], "name": "Griechisch", "sprache": "el"}).json()
    klient.post(f"/api/sammlungen/{s['id']}/import/vokabeln", json={
        "eintraege": [{"lemma": "το κόμμα", "wortart": "substantiv",
                       "kennung": "el-k",
                       "merkmale": {"genus": "n"},
                       "bedeutungen": [{"uebersetzungen": ["Partei"]}]}]})
    lexem = klient.get(f"/api/sammlungen/{s['id']}/lexeme",
                       params={"suche": "κόμμα"}).json()["lexeme"][0]

    db = dbm.verbindung()
    try:
        for wort in ("κόμμα", "κόμματος", "ξένο"):
            db.execute("""INSERT INTO wortwunsch
                            (benutzer_id, sammlung_id, wort, vergleichsform,
                             vorkommen)
                          VALUES (?, ?, ?, ?, 1)""",
                       (b["id"], s["id"], wort, wort))
        db.commit()
    finally:
        db.close()

    antwort = klient.post("/api/wortwuensche/abhaken",
                          params={"benutzer_id": b["id"]},
                          json={"zuordnungen": [
                              {"wort": "κόμμα", "lexem_id": lexem["id"]},
                              {"wort": "κόμματος", "lexem_id": lexem["id"]},
                              # Bewusst ohne Vokabel — ein Eigenname etwa.
                              {"wort": "ξένο"},
                              {"wort": "gibtsnicht", "lexem_id": lexem["id"]}]})
    assert antwort.status_code == 200, antwort.text
    d = antwort.json()
    assert d["abgehakt"] == 3
    assert d["nicht_gefunden"] == 1
    assert d["noch_offen"] == 0
    # Die Zuordnung ist festgehalten — sie ist der Beleg, woher die
    # Vokabel stammt.
    offen = klient.get("/api/wortwuensche",
                       params={"benutzer_id": b["id"], "offen": False}).json()
    nach_wort = {w["wort"]: w for w in offen}
    assert nach_wort["κόμμα"]["lexem_id"] == lexem["id"]
    assert nach_wort["ξένο"]["lexem_id"] is None


def test_fremde_wuensche_nur_mit_schreibrecht_abhaken(klient):
    """Dieselbe Grenze wie beim Lesen der Liste."""
    import sys
    sys.path.insert(0, "backend")
    import datenbank as dbm

    anni = klient.post("/api/benutzer", json={"name": "Annuschka"}).json()
    max_ = klient.post("/api/benutzer", json={"name": "Max"}).json()
    seine = klient.post("/api/sammlungen", json={
        "besitzer_id": max_["id"], "name": "Mhd", "sprache": "gmh"}).json()
    db = dbm.verbindung()
    try:
        db.execute("""INSERT INTO wortwunsch
                        (benutzer_id, sammlung_id, wort, vergleichsform,
                         vorkommen)
                      VALUES (?, ?, 'ouwê', 'ouwê', 1)""",
                   (max_["id"], seine["id"]))
        db.commit()
    finally:
        db.close()

    # Ohne Freigabe: nicht gefunden, nicht abgehakt.
    d = klient.post("/api/wortwuensche/abhaken",
                    params={"benutzer_id": anni["id"]},
                    json={"zuordnungen": [{"wort": "ouwê"}]}).json()
    assert d["abgehakt"] == 0 and d["nicht_gefunden"] == 1

    klient.put(f"/api/sammlungen/{seine['id']}/zugriff", json={
        "benutzer_id": anni["id"], "recht": "schreiben"})
    d = klient.post("/api/wortwuensche/abhaken",
                    params={"benutzer_id": anni["id"]},
                    json={"zuordnungen": [{"wort": "ouwê"}]}).json()
    assert d["abgehakt"] == 1


def test_abhaken_greift_nicht_in_fremde_sammlungen(klient):
    """Beim ersten Lauf an echten Daten passierte genau das.

    In einem griechischen Zeitungsartikel stehen deutsche Zitate, also
    stand »ich« auf der griechischen Wunschliste. Das Abhaken suchte
    über alle Sammlungen und erwischte das gleichlautende »ich« in der
    mittelhochdeutschen Liste gleich mit — 89 fremde Wünsche auf einen
    Schlag als erledigt markiert, obwohl niemand sie angelegt hatte.

    Die Sammlung ergibt sich aus der lexem_id. Ist sie nicht zu
    ermitteln und das Wort steht in mehreren Sammlungen offen, wird
    NICHTS abgehakt und das gemeldet.
    """
    import sys
    sys.path.insert(0, "backend")
    import datenbank as dbm

    b = klient.post("/api/benutzer", json={"name": "Lesende"}).json()
    el = klient.post("/api/sammlungen", json={
        "besitzer_id": b["id"], "name": "Griechisch", "sprache": "el"}).json()
    gmh = klient.post("/api/sammlungen", json={
        "besitzer_id": b["id"], "name": "Mhd", "sprache": "gmh"}).json()
    klient.post(f"/api/sammlungen/{el['id']}/import/vokabeln", json={
        "eintraege": [{"lemma": "ich", "wortart": "sonstiges",
                       "bedeutungen": [{"uebersetzungen": ["ich (deutsch)"]}]}]})
    lexem = klient.get(f"/api/sammlungen/{el['id']}/lexeme",
                       params={"suche": "ich"}).json()["lexeme"][0]

    db = dbm.verbindung()
    try:
        for sid in (el["id"], gmh["id"]):
            db.execute("""INSERT INTO wortwunsch
                            (benutzer_id, sammlung_id, wort, vergleichsform,
                             vorkommen)
                          VALUES (?, ?, 'ich', 'ich', 1)""", (b["id"], sid))
        db.commit()
    finally:
        db.close()

    d = klient.post("/api/wortwuensche/abhaken",
                    params={"benutzer_id": b["id"]},
                    json={"zuordnungen": [
                        {"wort": "ich", "lexem_id": lexem["id"]}]}).json()
    assert d["abgehakt"] == 1

    offen = klient.get("/api/wortwuensche",
                       params={"benutzer_id": b["id"]}).json()
    # Der mittelhochdeutsche steht NOCH offen.
    assert [w["sammlung_id"] for w in offen] == [gmh["id"]]


def test_ohne_sammlung_und_mehrdeutig_wird_nichts_abgehakt(klient):
    """Raten wäre hier teuer: ein falsch abgehakter Wunsch verschwindet
    aus der Liste und kommt nie wieder."""
    import sys
    sys.path.insert(0, "backend")
    import datenbank as dbm

    b = klient.post("/api/benutzer", json={"name": "Lesende"}).json()
    a = klient.post("/api/sammlungen", json={
        "besitzer_id": b["id"], "name": "A", "sprache": "el"}).json()
    c = klient.post("/api/sammlungen", json={
        "besitzer_id": b["id"], "name": "B", "sprache": "gmh"}).json()
    db = dbm.verbindung()
    try:
        for sid in (a["id"], c["id"]):
            db.execute("""INSERT INTO wortwunsch
                            (benutzer_id, sammlung_id, wort, vergleichsform,
                             vorkommen)
                          VALUES (?, ?, 'ich', 'ich', 1)""", (b["id"], sid))
        db.commit()
    finally:
        db.close()

    d = klient.post("/api/wortwuensche/abhaken",
                    params={"benutzer_id": b["id"]},
                    json={"zuordnungen": [{"wort": "ich"}]}).json()
    assert d["abgehakt"] == 0
    assert d["mehrdeutig"] == 1
    assert len(klient.get("/api/wortwuensche",
                          params={"benutzer_id": b["id"]}).json()) == 2


def test_grossbuchstaben_ohne_akzent_gelten_als_bekannt(klient):
    """Griechische Großbuchstaben tragen keinen Akzent.

    Zeitungen schreiben »Ηταν«, »Ελληνας«, »Οχι«; im Wortschatz steht
    ήταν, Έλληνας, όχι. Das ist keine Lücke im Bestand, sondern eine
    Rechtschreibregel — und sie gehört in den Vergleich. In einem
    echten Artikel waren das zwölf von 47 verbliebenen »unbekannten«
    Wörtern.
    """
    b = klient.post("/api/benutzer", json={"name": "Lesende"}).json()
    s = klient.post("/api/sammlungen", json={
        "besitzer_id": b["id"], "name": "Griechisch", "sprache": "el"}).json()
    klient.post(f"/api/sammlungen/{s['id']}/import/vokabeln", json={
        "eintraege": [
            {"lemma": "ήταν", "wortart": "verb",
             "bedeutungen": [{"uebersetzungen": ["war"]}]},
            {"lemma": "όχι", "wortart": "adverb",
             "bedeutungen": [{"uebersetzungen": ["nein"]}]}]})
    t = klient.post(f"/api/sammlungen/{s['id']}/texte", json={
        "titel": "Zeitung", "inhalt": "Ηταν καλά. Οχι."}).json()
    d = klient.get(f"/api/texte/{t['id']}/deckung",
                   params={"benutzer_id": b["id"]}).json()
    nach_wort = {w["wort"]: w for w in d["woerter"]}
    assert nach_wort["Ηταν"]["lexem_id"], "Ηταν wurde nicht erkannt"
    assert nach_wort["Οχι"]["lexem_id"], "Οχι wurde nicht erkannt"


def test_kleingeschriebenes_bleibt_streng(klient):
    """Der Rückfall gilt NUR für großgeschriebene Wörter. Sonst fiele
    »ποτέ« (nie) mit »πότε« (wann) zusammen — und zwar unbemerkt, denn
    ein falsch zugeordnetes Wort meldet sich nie."""
    b = klient.post("/api/benutzer", json={"name": "Lesende"}).json()
    s = klient.post("/api/sammlungen", json={
        "besitzer_id": b["id"], "name": "Griechisch", "sprache": "el"}).json()
    klient.post(f"/api/sammlungen/{s['id']}/import/vokabeln", json={
        "eintraege": [{"lemma": "πότε", "wortart": "adverb",
                       "bedeutungen": [{"uebersetzungen": ["wann"]}]}]})
    t = klient.post(f"/api/sammlungen/{s['id']}/texte", json={
        "titel": "Satz", "inhalt": "ποτε δεν."}).json()
    d = klient.get(f"/api/texte/{t['id']}/deckung",
                   params={"benutzer_id": b["id"]}).json()
    nach_wort = {w["wort"]: w for w in d["woerter"]}
    assert not nach_wort["ποτε"]["lexem_id"], \
        "kleingeschrieben darf der Akzent nicht wegfallen"


def test_mehrdeutiges_wird_auch_gross_nicht_geraten(klient):
    """Zwei Wörter, die sich nur im Akzent unterscheiden: dann wird
    auch bei Großschreibung nichts zugeordnet."""
    b = klient.post("/api/benutzer", json={"name": "Lesende"}).json()
    s = klient.post("/api/sammlungen", json={
        "besitzer_id": b["id"], "name": "Griechisch", "sprache": "el"}).json()
    klient.post(f"/api/sammlungen/{s['id']}/import/vokabeln", json={
        "eintraege": [
            {"lemma": "πότε", "wortart": "adverb",
             "bedeutungen": [{"uebersetzungen": ["wann"]}]},
            {"lemma": "ποτέ", "wortart": "adverb",
             "bedeutungen": [{"uebersetzungen": ["nie"]}]}]})
    t = klient.post(f"/api/sammlungen/{s['id']}/texte", json={
        "titel": "Satz", "inhalt": "Ποτε ήρθε;"}).json()
    d = klient.get(f"/api/texte/{t['id']}/deckung",
                   params={"benutzer_id": b["id"]}).json()
    nach_wort = {w["wort"]: w for w in d["woerter"]}
    assert not nach_wort["Ποτε"]["lexem_id"], "hier darf nicht geraten werden"


def test_enklise_akzent_wird_erkannt(klient):
    """»το πελατολόγιό του« — das Substantiv trägt einen zweiten
    Akzent, den das angehängte Wörtchen erzwingt. Im Wortschatz steht
    es mit einem.

    Entfernt wird nur der LETZTE der beiden Akzente, nicht alle: die
    Form bleibt damit unterscheidbar und es wird nichts geraten.
    """
    b = klient.post("/api/benutzer", json={"name": "Lesende"}).json()
    s = klient.post("/api/sammlungen", json={
        "besitzer_id": b["id"], "name": "Griechisch", "sprache": "el"}).json()
    klient.post(f"/api/sammlungen/{s['id']}/import/vokabeln", json={
        "eintraege": [{"lemma": "το πελατολόγιο", "wortart": "substantiv",
                       "merkmale": {"genus": "n"},
                       "bedeutungen": [{"uebersetzungen": ["Kundenstamm"]}]}]})
    t = klient.post(f"/api/sammlungen/{s['id']}/texte", json={
        "titel": "Satz", "inhalt": "το πελατολόγιό του μεγάλωνε."}).json()
    d = klient.get(f"/api/texte/{t['id']}/deckung",
                   params={"benutzer_id": b["id"]}).json()
    nach = {w["wort"]: w for w in d["woerter"]}
    assert any(w["lexem_id"] for k, w in nach.items() if "πελατολόγι" in k), \
        f"nicht erkannt: {list(nach)}"


def test_ein_einzelner_akzent_wird_nicht_angetastet(klient):
    """Nur bei GENAU zwei Akzenten wird einer entfernt. Sonst wäre es
    kein Enklisefall, sondern ein anderes Wort."""
    import sys
    sys.path.insert(0, "backend")
    import lesetexte
    assert lesetexte._ohne_zweitakzent("ποτέ") is None
    assert lesetexte._ohne_zweitakzent("πελατολόγιό") == "πελατολόγιο"
    assert lesetexte._ohne_zweitakzent("καλημέρα") is None
