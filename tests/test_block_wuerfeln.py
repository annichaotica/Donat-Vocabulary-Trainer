"""»Können wir bei ›Was kommt dran‹ eine Art ›neu würfeln‹ einfügen?«

Die Falle dabei ist nicht das Würfeln, sondern wo das Ergebnis liegt.
Vorschau und Abfrage rechnen durch dieselbe Funktion — `lernen.naechste`
ruft `lernziele.block`. Ein Wurf, der nur in der Ansicht lebte, zeigte
einen Block, den die Abfrage danach nicht liefert. Darum steht der
Würfelzähler am Lernziel.

Was der Wurf NICHT tun darf:

  - den Terminplan verwürfeln. Was länger überfällig ist, bleibt vorn;
    gemischt wird nur, was gleichauf liegt.
  - die Lernreihenfolge des Neuen aufheben. Neues wird in seiner Folge
    eingeführt, das steht so im Schema. Beim Neuen wird deshalb nicht
    gemischt, sondern weitergeblättert.
  - den Zuschnitt ändern. Wie viel fällig, wacklig und neu ist,
    entscheidet der Termin, nicht der Würfel.
"""

import pytest

WOERTER = [(f"λέξη{i}", f"Wort {i}") for i in range(40)]


@pytest.fixture()
def ziel(klient):
    b = klient.post("/api/benutzer", json={"name": "Übende"}).json()
    klient.patch(f"/api/benutzer/{b['id']}", json={"fragen_je_tag": 0})
    s = klient.post("/api/sammlungen", json={
        "besitzer_id": b["id"], "name": "Griechisch", "sprache": "el"}).json()
    klient.post(f"/api/sammlungen/{s['id']}/import/vokabeln", json={
        "eintraege": [{"lemma": lemma, "wortart": "substantiv",
                       "lektion_nr": 1, "reihenfolge": i,
                       "bedeutungen": [{"uebersetzungen": [bed]}]}
                      for i, (lemma, bed) in enumerate(WOERTER)]})
    klient.post(f"/api/sammlungen/{s['id']}/freigabe", json={"lektion_nr": 1})
    z = klient.post("/api/lernziele", json={
        "benutzer_id": b["id"], "name": "Block",
        "umfang": {"sammlungen": [s["id"]]}}).json()
    return b, s, z


def _block(klient, b, z, anzahl=10):
    return klient.get(f"/api/lernziele/{z['id']}/block", params={
        "benutzer_id": b["id"], "anzahl": anzahl}).json()


def _wuerfeln(klient, b, z, anzahl=10):
    antwort = klient.post(f"/api/lernziele/{z['id']}/wuerfeln", params={
        "benutzer_id": b["id"], "anzahl": anzahl})
    assert antwort.status_code == 200, antwort.text
    return antwort.json()


def test_ohne_wurf_bleibt_alles_wie_bisher(ziel, klient):
    """Die Vorgabe darf sich nicht verändert haben — sonst hätte ich
    nebenbei die Zusammenstellung umgebaut."""
    b, s, z = ziel
    erst = _block(klient, b, z)
    nochmal = _block(klient, b, z)
    assert erst["wurf"] == 0
    assert ([a["aufgabe_id"] for a in erst["aufgaben"]]
            == [a["aufgabe_id"] for a in nochmal["aufgaben"]])


def test_ein_wurf_liefert_andere_woerter(ziel, klient):
    b, s, z = ziel
    vorher = {a["lemma"] for a in _block(klient, b, z)["aufgaben"]}
    nachher = _wuerfeln(klient, b, z)
    assert nachher["wurf"] == 1
    jetzt = {a["lemma"] for a in nachher["aufgaben"]}
    assert jetzt != vorher, f"derselbe Block nach dem Wurf: {sorted(jetzt)}"


def test_der_wurf_bleibt_stehen(ziel, klient):
    """Sonst zeigte der nächste Blick wieder den alten Block."""
    b, s, z = ziel
    gewuerfelt = _wuerfeln(klient, b, z)
    wieder = _block(klient, b, z)
    assert wieder["wurf"] == 1
    assert ([a["aufgabe_id"] for a in wieder["aufgaben"]]
            == [a["aufgabe_id"] for a in gewuerfelt["aufgaben"]])


def test_die_abfrage_liefert_was_die_vorschau_zeigte(ziel, klient):
    """Der Kern der Sache. »Was käme dran?« ist ein Versprechen.

    Verglichen wird die MENGE, nicht die Folge. Die Vorschau sagt zu,
    welche Wörter kommen; in welcher Folge, entscheidet danach die
    Abfrage (Runde, Abstand halten) — sie steht so auch in der
    Begründung: »verschränkt gemischt«. Die erste Fassung dieses Tests
    verglich geordnete Listen. Sie lief im Testbestand grün und wäre
    an echten Daten gefallen, ohne dass etwas kaputt gewesen wäre: ein
    Test, der mehr verspricht als die Sache selbst.
    """
    b, s, z = ziel
    gewuerfelt = _wuerfeln(klient, b, z)
    versprochen = {a["aufgabe_id"] for a in gewuerfelt["aufgaben"]}

    geliefert = klient.get("/api/lernen/naechste", params={
        "benutzer_id": b["id"], "lernziel_id": z["id"], "anzahl": 10}).json()
    bekommen = {a["aufgabe_id"] for a in geliefert}
    assert bekommen == versprochen, (
        "die Abfrage liefert andere Wörter, als die Vorschau zeigte: "
        f"zu viel {bekommen - versprochen}, zu wenig {versprochen - bekommen}")


def test_der_zuschnitt_bleibt_gleich(ziel, klient):
    """Wie viel fällig, wacklig und neu — das entscheidet der Termin,
    nicht der Würfel."""
    b, s, z = ziel
    vorher = _block(klient, b, z)["zusammensetzung"]
    for _ in range(3):
        nachher = _wuerfeln(klient, b, z)["zusammensetzung"]
        assert nachher == vorher, f"{vorher} -> {nachher}"


def test_faelliges_bleibt_vor_neuem(ziel, klient):
    """Der Würfel darf den Terminplan nicht aufheben."""
    b, s, z = ziel
    # Drei Wörter einmal falsch beantworten: sie werden fällig.
    liste = klient.get("/api/lernen/naechste", params={
        "benutzer_id": b["id"], "lernziel_id": z["id"], "anzahl": 3}).json()
    for a in liste:
        klient.post("/api/lernen/bewerten", json={
            "benutzer_id": b["id"], "aufgabe_id": a["aufgabe_id"],
            "bewertung": 1})

    for _ in range(5):
        block = _wuerfeln(klient, b, z)
        herkuenfte = [a["herkunft"] for a in block["aufgaben"]]
        assert "faellig" in herkuenfte, (
            f"nach dem Wurf ist nichts Fälliges mehr dabei: {herkuenfte}")


def test_das_neue_bleibt_in_seiner_lernreihenfolge(ziel, klient):
    """Nicht gemischt, sondern weitergeblättert: die gezeigten neuen
    Wörter stehen untereinander weiterhin in der Reihenfolge, in der
    sie eingeführt werden sollen.

    `verschraenken` mischt die Aufgaben am Ende noch durch, damit nicht
    zwei zum selben Wort nebeneinander liegen — geprüft wird deshalb
    die Auswahl, nicht ihre Anzeigefolge: die gewählten Wörter müssen
    ein zusammenhängendes Stück der Lernreihenfolge sein.
    """
    b, s, z = ziel
    nummern = []
    for a in _wuerfeln(klient, b, z)["aufgaben"]:
        if a["herkunft"] == "neu":
            nummern.append(int(a["lemma"].removeprefix("λέξη")))
    assert nummern, "keine neuen Wörter im Block"
    gespanne = max(nummern) - min(nummern) + 1
    assert gespanne <= len(set(nummern)) * 2, (
        f"die neuen Wörter sind quer aus dem Bestand gegriffen: "
        f"{sorted(set(nummern))}")


def test_mehrere_wuerfe_ergeben_mehrere_bloecke(ziel, klient):
    """Zweimal würfeln soll nicht zweimal dasselbe ergeben."""
    b, s, z = ziel
    gesehen = []
    for _ in range(4):
        gesehen.append(tuple(sorted(a["lemma"]
                                    for a in _wuerfeln(klient, b, z)["aufgaben"])))
    assert len(set(gesehen)) >= 3, (
        f"vier Würfe, nur {len(set(gesehen))} verschiedene Blöcke")


def test_ein_fremdes_ziel_laesst_sich_nicht_wuerfeln(ziel, klient):
    b, s, z = ziel
    fremde = klient.post("/api/benutzer", json={"name": "Fremde"}).json()
    antwort = klient.post(f"/api/lernziele/{z['id']}/wuerfeln",
                          params={"benutzer_id": fremde["id"]})
    assert antwort.status_code == 403, antwort.text


def test_jedes_neue_wort_ist_erreichbar(ziel, klient):
    """Der Mangel, der beim Schreiben dieser Datei auffiel.

    Erst schob ein Wurf das Fenster um eine feste Schrittweite weiter.
    Bei vierzig Wörtern und Schritt zwanzig bekam man abwechselnd die
    Wörter 0–9 und 20–29 — die dazwischen waren unerreichbar, und zwar
    dauerhaft, nicht nur selten. Der Ansatzpunkt wird deshalb gewürfelt
    und ist kein Vielfaches.
    """
    b, s, z = ziel
    gesehen = set()
    for _ in range(25):
        for a in _wuerfeln(klient, b, z)["aufgaben"]:
            gesehen.add(a["lemma"])
    fehlen = {lemma for lemma, _bed in WOERTER} - gesehen
    assert not fehlen, (
        f"nach 25 Würfen nie gezeigt: {sorted(fehlen)} — ein Teil des "
        "Bestands ist unerreichbar")


def test_das_fenster_laeuft_nicht_ueber_das_ende(ziel, klient):
    """Sonst stünde das letzte Wort der Lektion neben dem ersten."""
    import sys
    sys.path.insert(0, "backend")
    import lernziele
    reihe = [{"n": i} for i in range(100)]
    for saat in range(1, 30):
        geschoben = lernziele._fenster_schieben(reihe, saat)
        fenster = [r["n"] for r in geschoben[:lernziele.FENSTER_BEIM_BLAETTERN]]
        assert fenster == sorted(fenster), (
            f"Wurf {saat} springt im Fenster zurück: {fenster}")
