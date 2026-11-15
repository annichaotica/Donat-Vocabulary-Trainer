"""Eine Freigabe ist keine Lernentscheidung.

»Wenn ich schon die Sammlungen der anderen sehe, würde ich
gerne einstellen können, dass ich diese nicht aktiv lerne, weil das
allgemeine Lernen ohne Lernziel mutmaßlich auf alle Quellen zugreift?«

Sie griff. Im echten Bestand:

    An Lernender 1 freigegeben: das Französisch von Lernender 2 (36
    Wörter, Recht »schreiben«) und das Mittelhochdeutsch von Lernender
    3 (4). Lernstand hatte sie auf keiner von beiden — die fremden
    Wörter wären ihr also irgendwann unvermittelt zwischen den
    griechischen begegnet.

Die Ursache war eine Bedeutungsvermischung in EINER Tabelle: `freigabe`
beantwortete »wer darf hineinsehen« und »wer lernt das« zugleich. Jetzt
beantwortet sie nur noch die erste Frage.
"""

import pytest


@pytest.fixture()
def zwei_leute(klient):
    """Zwei Profile — und die Sammlung des zweiten ist mir zum Pflegen
    freigegeben, nicht zum Lernen."""
    ich = klient.post("/api/benutzer", json={"name": "Lernender 1"}).json()
    andere = klient.post("/api/benutzer", json={"name": "Lernender 2"}).json()

    meine = klient.post("/api/sammlungen", json={
        "besitzer_id": ich["id"], "name": "Griechisch", "sprache": "el"}).json()
    klient.post(f"/api/sammlungen/{meine['id']}/import/vokabeln", json={
        "eintraege": [{"lemma": "γράφω", "wortart": "verb", "lektion_nr": 1,
                       "bedeutungen": [{"uebersetzungen": ["schreiben"]}]}]})
    klient.post(f"/api/sammlungen/{meine['id']}/freigabe", json={"lektion_nr": 1})

    ihre = klient.post("/api/sammlungen", json={
        "besitzer_id": andere["id"], "name": "Französisch",
        "sprache": "fr"}).json()
    klient.post(f"/api/sammlungen/{ihre['id']}/import/vokabeln", json={
        "eintraege": [{"lemma": "le pain", "wortart": "substantiv",
                       "lektion_nr": 1,
                       "bedeutungen": [{"uebersetzungen": ["das Brot"]}]}]})
    klient.post(f"/api/sammlungen/{ihre['id']}/freigabe", json={"lektion_nr": 1})
    klient.put(f"/api/sammlungen/{ihre['id']}/zugriff", json={
        "benutzer_id": ich["id"], "recht": "schreiben"})
    return ich, andere, meine, ihre


def _lemmata(klient, benutzer_id, anzahl=20):
    """Was bekäme ich in der allgemeinen Abfrage zu sehen?"""
    liste = klient.get("/api/lernen/naechste", params={
        "benutzer_id": benutzer_id, "anzahl": anzahl}).json()
    return {a["frage_text"] for a in liste} | {
        a.get("antwort_text") for a in liste}


def test_eine_fremde_sammlung_wird_nicht_ungefragt_mitgelernt(zwei_leute, klient):
    """Der gemessene Fall."""
    ich, _andere, _meine, ihre = zwei_leute
    liste = klient.get("/api/lernen/naechste", params={
        "benutzer_id": ich["id"], "anzahl": 20}).json()
    assert liste, "gar nichts geliefert — dann prüft der Test nichts"
    fremde = [a for a in liste if a["sprache"] == "fr"]
    assert not fremde, (
        "Das fremde Französisch liegt in meiner allgemeinen Abfrage, obwohl "
        f"ich es nur mitpflege: {[a['frage_text'] for a in fremde]}")


def test_mitpflegen_bleibt_trotzdem_moeglich(zwei_leute, klient):
    """Die Freigabe darf dabei nichts von ihrer Wirkung verlieren —
    sonst hätte ich das eine Problem gegen ein anderes getauscht."""
    ich, _andere, _meine, ihre = zwei_leute
    liste = klient.get("/api/sammlungen",
                       params={"benutzer_id": ich["id"]}).json()
    ids = {s["id"] for s in liste}
    assert ihre["id"] in ids, "die freigegebene Sammlung ist verschwunden"
    eintrag = next(s for s in liste if s["id"] == ihre["id"])
    assert eintrag["lerne_ich"] == 0

    # Und schreiben geht auch noch.
    antwort = klient.post(f"/api/sammlungen/{ihre['id']}/import/vokabeln", json={
        "eintraege": [{"lemma": "le vin", "wortart": "substantiv",
                       "lektion_nr": 1,
                       "bedeutungen": [{"uebersetzungen": ["der Wein"]}]}]})
    assert antwort.status_code == 200, antwort.text


def test_wer_mitlernen_will_schaltet_es_ein(zwei_leute, klient):
    """Die Gegenrichtung: gemeinsam lernen soll weiter gehen, nur eben
    gesagt und nicht stillschweigend."""
    ich, _andere, _meine, ihre = zwei_leute
    antwort = klient.put(f"/api/sammlungen/{ihre['id']}/lernwahl", json={
        "benutzer_id": ich["id"], "lernen": True})
    assert antwort.status_code == 200, antwort.text

    liste = klient.get("/api/lernen/naechste", params={
        "benutzer_id": ich["id"], "anzahl": 20}).json()
    assert any(a["sprache"] == "fr" for a in liste), (
        "eingeschaltet, kommt aber immer noch nicht")


def test_die_eigene_sammlung_laesst_sich_pausieren(zwei_leute, klient):
    """Auch die eigene — wer sich auf Griechisch sammelt, will das
    Englische nicht dazwischen haben."""
    ich, _andere, meine, _ihre = zwei_leute
    klient.put(f"/api/sammlungen/{meine['id']}/lernwahl", json={
        "benutzer_id": ich["id"], "lernen": False})
    liste = klient.get("/api/lernen/naechste", params={
        "benutzer_id": ich["id"], "anzahl": 20}).json()
    assert not liste, f"abgeschaltet, kommt aber: {liste}"


def test_ausdruecklich_aufgerufen_wird_sie_trotzdem_abgefragt(zwei_leute, klient):
    """Die Abschaltung gilt der allgemeinen Abfrage, nicht der Sammlung.

    Sonst wäre der Knopf »Lernen« auf der Karte einer abgeschalteten
    Sammlung eine Sackgasse — und genau solche stillen Sackgassen sind
    hier schon zweimal aufgefallen.
    """
    ich, _andere, _meine, ihre = zwei_leute
    liste = klient.get("/api/lernen/naechste", params={
        "benutzer_id": ich["id"], "sammlung_id": ihre["id"],
        "anzahl": 5}).json()
    assert liste, "ausdrücklich aufgerufen und trotzdem leer"
    assert all(a["sprache"] == "fr" for a in liste)


def test_die_zahlen_der_uebersicht_zaehlen_dasselbe(zwei_leute, klient):
    """Die Übersicht las bisher denselben Topf. Liefe sie auseinander,
    stünde dort eine Zahl, die die Abfrage nie einlöst — der Fehler, den
    »dein Tagespensum ist erledigt« ohne gelernten Block schon einmal
    hatte."""
    ich, _andere, _meine, _ihre = zwei_leute
    stand = klient.get("/api/lernen/stand",
                       params={"benutzer_id": ich["id"]}).json()
    liste = klient.get("/api/lernen/naechste", params={
        "benutzer_id": ich["id"], "anzahl": 50}).json()
    assert liste, "nichts zu lernen — dann prüft der Test nichts"
    # Das Französische darf in keiner der beiden Zahlen stecken: eine
    # Vokabel, also höchstens deren Aufgaben.
    meine_aufgaben = len({a["aufgabe_id"] for a in liste})
    assert stand["gesamt"] == meine_aufgaben, (
        f"Übersicht {stand['gesamt']}, Abfrage {meine_aufgaben} — "
        f"sie zählen verschiedene Töpfe: {stand}")


def test_auch_die_saetze_folgen_der_lernwahl(zwei_leute, klient):
    """Derselbe Griff gab es viermal; drei davon sind Vokabeln, einer
    sind die Übungen. Genau an so einer Stelle ist es schon einmal
    auseinandergelaufen."""
    ich, _andere, _meine, ihre = zwei_leute
    u = klient.post(f"/api/sammlungen/{ihre['id']}/uebungen", json={
        "typ": "satz", "zielsprache": "Le pain est bon.",
        "grundsprache": "Das Brot ist gut.", "lektion_nr": 1}).json()
    klient.post(f"/api/uebungen/{u['id']}/freigabe")

    liste = klient.get("/api/uebungen/lernen/naechste", params={
        "benutzer_id": ich["id"], "anzahl": 10}).json()
    assert not liste, f"fremde Sätze in der allgemeinen Übung: {liste}"

    klient.put(f"/api/sammlungen/{ihre['id']}/lernwahl", json={
        "benutzer_id": ich["id"], "lernen": True})
    liste = klient.get("/api/uebungen/lernen/naechste", params={
        "benutzer_id": ich["id"], "anzahl": 10}).json()
    assert liste, "eingeschaltet, aber die Sätze kommen nicht"


def test_abschalten_wirft_den_lernstand_nicht_weg(zwei_leute, klient):
    """Sonst wäre der Schalter gefährlich statt nützlich."""
    ich, _andere, meine, _ihre = zwei_leute
    a = klient.get("/api/lernen/naechste", params={
        "benutzer_id": ich["id"], "anzahl": 1}).json()[0]
    klient.post("/api/lernen/bewerten", json={
        "benutzer_id": ich["id"], "aufgabe_id": a["aufgabe_id"],
        "bewertung": 4})

    klient.put(f"/api/sammlungen/{meine['id']}/lernwahl", json={
        "benutzer_id": ich["id"], "lernen": False})
    klient.put(f"/api/sammlungen/{meine['id']}/lernwahl", json={
        "benutzer_id": ich["id"], "lernen": True})

    import datenbank as dbm
    db = dbm.verbindung()
    try:
        z = dbm.zeile(db, """SELECT anzahl FROM lernzustand
                              WHERE aufgabe_id = ? AND benutzer_id = ?""",
                      (a["aufgabe_id"], ich["id"]))
    finally:
        db.close()
    assert z is not None and z["anzahl"] == 1


def test_die_vorgabe_braucht_keine_zeile(zwei_leute, klient):
    """Nur Abweichungen werden gespeichert. Sonst bräuchte jede neue
    Sammlung und jede neue Freigabe einen Begleiteintrag — und der kann
    ausbleiben."""
    ich, _andere, meine, _ihre = zwei_leute
    import datenbank as dbm
    db = dbm.verbindung()
    try:
        assert dbm.wert(db, "SELECT COUNT(*) FROM lernwahl") == 0

        klient.put(f"/api/sammlungen/{meine['id']}/lernwahl", json={
            "benutzer_id": ich["id"], "lernen": False})
        assert dbm.wert(db, "SELECT COUNT(*) FROM lernwahl") == 1

        # Zurück auf die Vorgabe: die Zeile verschwindet wieder.
        klient.put(f"/api/sammlungen/{meine['id']}/lernwahl", json={
            "benutzer_id": ich["id"], "lernen": True})
        assert dbm.wert(db, "SELECT COUNT(*) FROM lernwahl") == 0
    finally:
        db.close()


def test_fremde_sammlung_laesst_sich_nicht_fuer_mich_umstellen(zwei_leute, klient):
    """Eine Sammlung, die ich gar nicht sehe, darf ich auch nicht in
    meine Abfrage holen."""
    ich, andere, meine, _ihre = zwei_leute
    unsichtbar = klient.post("/api/sammlungen", json={
        "besitzer_id": andere["id"], "name": "Geheim", "sprache": "fr"}).json()
    antwort = klient.put(f"/api/sammlungen/{unsichtbar['id']}/lernwahl", json={
        "benutzer_id": ich["id"], "lernen": True})
    assert antwort.status_code == 403, antwort.text
