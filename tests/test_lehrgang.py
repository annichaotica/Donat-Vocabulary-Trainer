"""Keine Zeitform, die das Lehrwerk noch nicht eingeführt hat.

»Bei den Anfängerkapiteln, die ich mir gerade ansehe, habe ich noch gar
nicht alle Zeitformen gelernt.«

Gemessen am echten Bestand am 15.11.2026:

    Griechisch, 10751 aktive Aufgaben, davon 6971 Formenbilden
       Μέλλοντας (Futur)   970      Ενεστώτας (Präsens)   832
       Αόριστος (Aorist)   939      Passive zusammen      968

Rund 2900 Aufgaben lagen in Zeiten, die im Anfängerkapitel nicht
vorkommen — alle im selben Topf, aus dem die Tagesdosis zieht. Ihr
Lernziel stand auf Lektion 2, und die Abfrage bot Aorist an.

Die Schranke ist dreifach durchlässig, und jede Durchlässigkeit hat
hier ihren Test: ohne Buchstand gilt sie nicht, ohne Zuordnung gilt sie
nicht, und Bedeutungsaufgaben trifft sie nie.
"""

import pytest


@pytest.fixture()
def buch(klient):
    """Ein Lehrwerk mit drei Lektionen und zwei Zeiten."""
    b = klient.post("/api/benutzer", json={"name": "Lernender 1"}).json()
    klient.patch(f"/api/benutzer/{b['id']}", json={"fragen_je_tag": 0})
    s = klient.post("/api/sammlungen", json={
        "besitzer_id": b["id"], "name": "Griechisch", "sprache": "el"}).json()
    for nr, name in ((1, "Erste Wörter"), (2, "Verben im Präsens"),
                     (3, "Aorist I (Vergangenheit)")):
        klient.post(f"/api/sammlungen/{s['id']}/lektionen",
                    json={"nr": nr, "name": name})
    klient.post(f"/api/sammlungen/{s['id']}/import/vokabeln", json={
        "eintraege": [{
            "lemma": "γράφω", "wortart": "verb", "lektion_nr": 2,
            "bedeutungen": [{"uebersetzungen": ["schreiben"]}],
            "formen": [
                {"text": "γράφεις", "merkmale": {
                    "modus": "indikativ", "tempus": "praesens",
                    "person": "2", "numerus": "sg"}},
                {"text": "έγραψα", "merkmale": {
                    "modus": "indikativ", "tempus": "aorist",
                    "person": "1", "numerus": "sg"}},
            ]}]})
    klient.post(f"/api/sammlungen/{s['id']}/freigabe", json={"lektion_nr": 2})
    return b, s


def _gruppen(klient, b, s=None):
    """Welche Formgruppen bietet die Abfrage gerade an?"""
    frage = {"benutzer_id": b["id"], "anzahl": 50}
    if s:
        frage["sammlung_id"] = s["id"]
    liste = klient.get("/api/lernen/naechste", params=frage).json()
    import datenbank as dbm
    db = dbm.verbindung()
    try:
        return {dbm.wert(db, "SELECT formgruppe FROM aufgabe WHERE id = ?",
                         (a["aufgabe_id"],))
                for a in liste}
    finally:
        db.close()


def _lehrgang(klient, s, zuordnung):
    antwort = klient.put(f"/api/sammlungen/{s['id']}/lehrgang",
                         json={"zuordnung": zuordnung})
    assert antwort.status_code == 200, antwort.text


def _buchstand(klient, b, s, nr):
    antwort = klient.put(f"/api/sammlungen/{s['id']}/buchstand",
                         json={"benutzer_id": b["id"], "bis_lektion": nr})
    assert antwort.status_code == 200, antwort.text
    return antwort.json()


# ----------------------------------------------------- die Schranke selbst

def test_ohne_buchstand_gilt_alles(buch, klient):
    """Wer nichts einstellt, merkt nichts — das ist Absicht."""
    b, s = buch
    _lehrgang(klient, s, {"aoristos": 3})
    assert "aoristos" in _gruppen(klient, b)


def test_ohne_zuordnung_gilt_alles(buch, klient):
    """Über eine Gruppe, zu der niemand gesagt hat, wann sie drankommt,
    wird nicht stillschweigend entschieden."""
    b, s = buch
    _buchstand(klient, b, s, 2)
    assert "aoristos" in _gruppen(klient, b)


def test_die_spaetere_zeitform_bleibt_draussen(buch, klient):
    """Der gemessene Fall."""
    b, s = buch
    _lehrgang(klient, s, {"enestotas": 2, "aoristos": 3})
    _buchstand(klient, b, s, 2)
    gruppen = _gruppen(klient, b)
    assert "aoristos" not in gruppen, (
        f"Aorist kommt dran, obwohl Lektion 3 noch nicht erreicht ist: "
        f"{gruppen}")
    assert "enestotas" in gruppen, "das Präsens ist mit weggefallen"


def test_weiterkommen_oeffnet_sie_von_selbst(buch, klient):
    """Der eigentliche Gewinn gegenüber einem Schalter: nichts umstellen."""
    b, s = buch
    _lehrgang(klient, s, {"enestotas": 2, "aoristos": 3})
    _buchstand(klient, b, s, 2)
    assert "aoristos" not in _gruppen(klient, b)
    _buchstand(klient, b, s, 3)
    assert "aoristos" in _gruppen(klient, b)


def test_bedeutungsaufgaben_trifft_sie_nie(buch, klient):
    """Eine Vokabel kann man lernen, bevor man ihre Zeiten kennt."""
    b, s = buch
    _lehrgang(klient, s, {"enestotas": 99, "aoristos": 99})
    _buchstand(klient, b, s, 1)
    liste = klient.get("/api/lernen/naechste", params={
        "benutzer_id": b["id"], "anzahl": 50}).json()
    assert liste, "die Schranke hat auch die Bedeutungen erwischt"
    assert all(a["typ"].startswith("bedeutung") or a["typ"] == "genus"
               for a in liste), [a["typ"] for a in liste]


def test_die_schranke_laesst_sich_aufheben(buch, klient):
    """Wer für eine Prüfung über den ganzen Stoff übt, will alles."""
    b, s = buch
    _lehrgang(klient, s, {"aoristos": 3})
    _buchstand(klient, b, s, 1)
    assert "aoristos" not in _gruppen(klient, b)
    klient.put(f"/api/sammlungen/{s['id']}/buchstand",
               json={"benutzer_id": b["id"], "bis_lektion": None})
    assert "aoristos" in _gruppen(klient, b)


def test_sie_gilt_auch_bei_ausdruecklich_gewaehlter_sammlung(buch, klient):
    b, s = buch
    _lehrgang(klient, s, {"aoristos": 3})
    _buchstand(klient, b, s, 2)
    assert "aoristos" not in _gruppen(klient, b, s)


def test_die_uebersicht_zaehlt_dasselbe(buch, klient):
    """Sonst stünde dort eine Zahl, die das Lernen nie einlöst — der
    Fehler, den »dein Tagespensum ist erledigt« schon einmal hatte."""
    b, s = buch
    vorher = klient.get("/api/lernen/stand",
                        params={"benutzer_id": b["id"]}).json()["gesamt"]
    _lehrgang(klient, s, {"aoristos": 3})
    _buchstand(klient, b, s, 2)
    nachher = klient.get("/api/lernen/stand",
                         params={"benutzer_id": b["id"]}).json()["gesamt"]
    assert nachher < vorher, (
        f"die Übersicht zählt den ausgeblendeten Aorist weiter mit: "
        f"{vorher} -> {nachher}")
    liste = klient.get("/api/lernen/naechste", params={
        "benutzer_id": b["id"], "anzahl": 50}).json()
    assert nachher == len({a["aufgabe_id"] for a in liste})


def test_der_lernstand_bleibt_erhalten(buch, klient):
    """Ausblenden heißt warten, nicht wegwerfen."""
    b, s = buch
    alle = klient.get("/api/lernen/naechste", params={
        "benutzer_id": b["id"], "anzahl": 50}).json()
    import datenbank as dbm
    db = dbm.verbindung()
    try:
        aorist = next(a for a in alle
                      if dbm.wert(db, "SELECT formgruppe FROM aufgabe WHERE id = ?",
                                  (a["aufgabe_id"],)) == "aoristos")
    finally:
        db.close()
    klient.post("/api/lernen/bewerten", json={
        "benutzer_id": b["id"], "aufgabe_id": aorist["aufgabe_id"],
        "bewertung": 4})

    _lehrgang(klient, s, {"aoristos": 3})
    _buchstand(klient, b, s, 2)
    _buchstand(klient, b, s, 3)

    db = dbm.verbindung()
    try:
        z = dbm.zeile(db, """SELECT anzahl FROM lernzustand
                              WHERE aufgabe_id = ? AND benutzer_id = ?""",
                      (aorist["aufgabe_id"], b["id"]))
    finally:
        db.close()
    assert z is not None and z["anzahl"] == 1


def test_sie_gilt_je_person(buch, klient):
    """Zwei Leute lernen dasselbe Buch verschieden schnell."""
    b, s = buch
    zweite = klient.post("/api/benutzer", json={"name": "Lernender 2"}).json()
    klient.put(f"/api/sammlungen/{s['id']}/zugriff",
               json={"benutzer_id": zweite["id"], "recht": "lesen"})
    klient.put(f"/api/sammlungen/{s['id']}/lernwahl",
               json={"benutzer_id": zweite["id"], "lernen": True})
    _lehrgang(klient, s, {"aoristos": 3})
    _buchstand(klient, b, s, 2)
    assert "aoristos" not in _gruppen(klient, b)
    assert "aoristos" in _gruppen(klient, zweite)


# --------------------------------- der Umfang eines Lernziels nach Gruppen

def test_ein_lernziel_laesst_sich_auf_eine_zeit_einschraenken(buch, klient):
    """Diese Auswahl gab es schon, geprüft war sie nie — und sie lief
    bis eben als Nachfilter in Python über ein Abfragefenster. Genau
    die Bauart, die hier mehrfach leere Ergebnisse erzeugt hat."""
    b, s = buch
    z = klient.post("/api/lernziele", json={
        "benutzer_id": b["id"], "name": "Nur Präsens",
        "umfang": {"sammlungen": [s["id"]], "formgruppen": ["enestotas"]}}).json()
    block = klient.get(f"/api/lernziele/{z['id']}/block", params={
        "benutzer_id": b["id"], "anzahl": 20}).json()
    assert block["aufgaben"], "der Block ist leer"

    import datenbank as dbm
    db = dbm.verbindung()
    try:
        gruppen = {dbm.wert(db, "SELECT formgruppe FROM aufgabe WHERE id = ?",
                            (a["aufgabe_id"],))
                   for a in block["aufgaben"]}
    finally:
        db.close()
    assert gruppen == {"enestotas"}, gruppen


def test_die_formgruppe_steht_an_der_aufgabe(buch, klient):
    """Sie wird beim Anlegen mitgeschrieben — sonst müsste die Abfrage
    hinterher aussieben."""
    import datenbank as dbm
    db = dbm.verbindung()
    try:
        offen = dbm.wert(db, """SELECT COUNT(*) FROM aufgabe
                                 WHERE formgruppe IS NULL
                                   AND ziel_art IN ('form', 'gruppe')""")
    finally:
        db.close()
    assert offen == 0, f"{offen} Formaufgaben ohne Gruppe"


# ----------------------------------------------------------- der Vorschlag

def test_der_vorschlag_liest_die_lektionsnamen(buch, klient):
    b, s = buch
    d = klient.get(f"/api/sammlungen/{s['id']}/lehrgang",
                   params={"benutzer_id": b["id"]}).json()
    nach_gruppe = {v["formgruppe"]: v for v in d["vorschlag"]}
    assert nach_gruppe["enestotas"]["ab_lektion"] == 2
    assert nach_gruppe["aoristos"]["ab_lektion"] == 3
    assert "Verben im Präsens" in nach_gruppe["enestotas"]["begruendung"]


def test_der_vorschlag_wird_nicht_von_selbst_angewandt(buch, klient):
    """Namensraten darf keinen Stoff wegnehmen."""
    b, s = buch
    d = klient.get(f"/api/sammlungen/{s['id']}/lehrgang",
                   params={"benutzer_id": b["id"]}).json()
    assert d["vorschlag"]
    assert d["zuordnung"] == {}
    assert "aoristos" in _gruppen(klient, b)


def test_eine_lektion_mit_allen_teilen_schlaegt_die_zusammengesetzte():
    """»Aorist Passiv« gehört zu Lektion 55 »Aorist Passiv«, nicht zu 45
    »Passiv Präsens« — obwohl beide »Passiv« enthalten."""
    import sys
    sys.path.insert(0, "backend")
    import lehrgang
    lektionen = [{"nr": 39, "name": "Aorist I"},
                 {"nr": 45, "name": "Passiv Präsens"},
                 {"nr": 55, "name": "Aorist Passiv"}]
    _l, nr, eindeutig = lehrgang._einfuehrung({"aorist", "passiv"}, lektionen)
    assert (nr, eindeutig) == (55, True)


def test_zusammengesetztes_braucht_die_spaetere_lektion():
    """»Genitiv Plural« kann man erst, wenn man Genitiv UND Plural hatte."""
    import sys
    sys.path.insert(0, "backend")
    import lehrgang
    lektionen = [{"nr": 10, "name": "Plural"}, {"nr": 17, "name": "Genitiv"}]
    _l, nr, eindeutig = lehrgang._einfuehrung({"genitiv", "plural"}, lektionen)
    assert (nr, eindeutig) == (17, True), (
        "die frühere Lektion genommen — die Schranke öffnete zu früh")


def test_ein_unbekannter_teil_wird_als_unsicher_gemeldet():
    """»Imperfekt Passiv«, wenn das Buch kein Imperfekt kennt."""
    import sys
    sys.path.insert(0, "backend")
    import lehrgang
    lektionen = [{"nr": 45, "name": "Passiv Präsens"}]
    _l, nr, eindeutig = lehrgang._einfuehrung({"imperfekt", "passiv"}, lektionen)
    assert nr == 45 and eindeutig is False


# ------------------------- die Lektionsgrenze des Ziels selbst

def test_ein_lernziel_auf_fruehen_lektionen_bekommt_keine_spaete_zeitform(
        buch, klient):
    """»Bei meinem Lernziel wird wieder der Aorist abgefragt, obwohl er
    gar nicht für diese Lektionen freigeschaltet wurde.«

    Der Fall aus dem Betrieb, und er war berechtigt. Die Zuordnung war
    eingetragen (21 Zeilen), der persönliche Buchstand nicht — also tat
    die Schranke nichts. Dieselbe Auskunft zweimal zu verlangen war der
    Entwurfsfehler: ein Ziel auf Lektion 2 und 3 sagt schon, wie weit
    jemand ist.
    """
    b, s = buch
    _lehrgang(klient, s, {"enestotas": 2, "aoristos": 3})
    # KEIN Buchstand — genau ihre Lage.
    lektionen = klient.get(f"/api/sammlungen/{s['id']}/lektionen").json()
    bis_zwei = [l["id"] for l in lektionen if l["nr"] in (1, 2)]
    z = klient.post("/api/lernziele", json={
        "benutzer_id": b["id"], "name": "Lektion 1 und 2",
        "umfang": {"sammlungen": [s["id"]], "lektionen": bis_zwei}}).json()

    block = klient.get(f"/api/lernziele/{z['id']}/block", params={
        "benutzer_id": b["id"], "anzahl": 30}).json()
    assert block["aufgaben"], "der Block ist leer"

    import datenbank as dbm
    db = dbm.verbindung()
    try:
        gruppen = {dbm.wert(db, "SELECT formgruppe FROM aufgabe WHERE id = ?",
                            (a["aufgabe_id"],))
                   for a in block["aufgaben"]}
    finally:
        db.close()
    assert "aoristos" not in gruppen, (
        f"Aorist im Block, obwohl das Ziel nur bis Lektion 2 reicht: {gruppen}")
    assert "enestotas" in gruppen, "das Präsens fehlt jetzt auch"


def test_ein_ziel_ohne_lektionsauswahl_bekommt_weiter_alles(buch, klient):
    """Keine Lektionsgrenze heißt keine Grenze — sonst nähme ein Ziel
    über den ganzen Stoff plötzlich Stoff weg."""
    b, s = buch
    _lehrgang(klient, s, {"aoristos": 3})
    z = klient.post("/api/lernziele", json={
        "benutzer_id": b["id"], "name": "Alles",
        "umfang": {"sammlungen": [s["id"]]}}).json()
    block = klient.get(f"/api/lernziele/{z['id']}/block", params={
        "benutzer_id": b["id"], "anzahl": 30}).json()
    import datenbank as dbm
    db = dbm.verbindung()
    try:
        gruppen = {dbm.wert(db, "SELECT formgruppe FROM aufgabe WHERE id = ?",
                            (a["aufgabe_id"],)) for a in block["aufgaben"]}
    finally:
        db.close()
    assert "aoristos" in gruppen


def test_eine_ausdruecklich_gewaehlte_formgruppe_schlaegt_die_grenze(buch, klient):
    """Wer »nur Aorist, Lektion 1 bis 2« einstellt, meint das — sonst
    wäre das Ziel stumm leer und niemand wüsste, warum."""
    b, s = buch
    _lehrgang(klient, s, {"aoristos": 3})
    lektionen = klient.get(f"/api/sammlungen/{s['id']}/lektionen").json()
    bis_zwei = [l["id"] for l in lektionen if l["nr"] in (1, 2)]
    z = klient.post("/api/lernziele", json={
        "benutzer_id": b["id"], "name": "Aorist üben",
        "umfang": {"sammlungen": [s["id"]], "lektionen": bis_zwei,
                   "formgruppen": ["aoristos"]}}).json()
    block = klient.get(f"/api/lernziele/{z['id']}/block", params={
        "benutzer_id": b["id"], "anzahl": 30}).json()
    assert block["aufgaben"], "ausdrücklich gewählt und trotzdem leer"


def test_bis_lektion_greift_auch_auf_die_formen(buch, klient):
    """Derselbe Gedanke im normalen Lernweg: »mitlernen bis Lektion N«."""
    b, s = buch
    _lehrgang(klient, s, {"aoristos": 3})
    liste = klient.get("/api/lernen/naechste", params={
        "benutzer_id": b["id"], "sammlung_id": s["id"],
        "bis_lektion": 2, "anzahl": 30}).json()
    import datenbank as dbm
    db = dbm.verbindung()
    try:
        gruppen = {dbm.wert(db, "SELECT formgruppe FROM aufgabe WHERE id = ?",
                            (a["aufgabe_id"],)) for a in liste}
    finally:
        db.close()
    assert "aoristos" not in gruppen, gruppen
