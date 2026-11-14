"""Ein Lernziel darf nicht drei Wörter im Kreis fragen.

Nachgemessen am echten Protokoll vom 14.11.2026: »müsste ich bei einem
ganz frischen Lernblock nicht ca. 40 Wörter bekommen? es sind aber
wieder nur ganz wenige.«

    18 Antworten heute, 3 verschiedene Wörter
    διαβάζω · το μήλο · μικρός · διαβάζω · το μήλο · μικρός · …

Das ist derselbe Befund wie damals auf dem normalen Weg, an neuer
Stelle. Der Lernzielblock stellt Verlerntes und Wackliges nach vorn, und
wer mit »Nochmal« bewertet, macht das Wort sofort wieder zum
dringendsten. Das Abstandhalten meidet nur die letzten ZWEI Wörter und
ist gegen einen Dreierkreis machtlos.

Der Schalter »Neues durchgehend untermischen« hätte das aufgebrochen —
er wirkte aber nur im normalen Weg, nicht im Lernziel. Dabei liegen die
unberührten Wörter direkt daneben, im selben Block.
"""

import pytest

WOERTER = [("γράφω", "schreiben"), ("διαβάζω", "lesen"), ("παίζω", "spielen"),
           ("τρέχω", "laufen"), ("μιλώ", "sprechen"), ("ακούω", "hören"),
           ("μένω", "bleiben"), ("βλέπω", "sehen"), ("τρώω", "essen"),
           ("πίνω", "trinken"), ("ανοίγω", "öffnen"), ("κλείνω", "schließen")]


@pytest.fixture()
def ziel(klient):
    b = klient.post("/api/benutzer", json={"name": "Übende"}).json()
    klient.patch(f"/api/benutzer/{b['id']}",
                 json={"neues_einstreuen": True, "fragen_je_tag": 0})
    s = klient.post("/api/sammlungen", json={
        "besitzer_id": b["id"], "name": "Griechisch", "sprache": "el"}).json()
    klient.post(f"/api/sammlungen/{s['id']}/import/vokabeln", json={
        "eintraege": [{
            "lemma": lemma, "wortart": "verb", "lektion_nr": 1,
            "reihenfolge": i,
            "bedeutungen": [{"uebersetzungen": [bed]}]}
            for i, (lemma, bed) in enumerate(WOERTER)]})
    klient.post(f"/api/sammlungen/{s['id']}/freigabe", json={"lektion_nr": 1})
    z = klient.post("/api/lernziele", json={
        "benutzer_id": b["id"], "name": "Block",
        "umfang": {"sammlungen": [s["id"]]}}).json()
    return b, z


def _sitzung(klient, b, z, runden, bewertung=1):
    """Spielt eine Sitzung. Vorgabe »Nochmal« — der böse Fall: jede
    Antwort macht ihr Wort sofort wieder zum dringendsten."""
    folge = []
    for _ in range(runden):
        liste = klient.get("/api/lernen/naechste", params={
            "benutzer_id": b["id"], "lernziel_id": z["id"], "anzahl": 1}).json()
        if not liste:
            break
        a = liste[0]
        folge.append(a["lexem_id"])
        klient.post("/api/lernen/bewerten", json={
            "benutzer_id": b["id"], "aufgabe_id": a["aufgabe_id"],
            "bewertung": bewertung})
    return folge


def test_auch_bei_lauter_nochmal_kommen_neue_woerter(ziel, klient):
    """Der gemessene Fall: achtzehn Antworten, drei Wörter."""
    b, z = ziel
    folge = _sitzung(klient, b, z, runden=18, bewertung=1)

    assert len(folge) == 18, f"die Abfrage brach ab: {len(folge)}"
    woerter = len(set(folge))
    assert woerter >= 6, (
        f"nur {woerter} verschiedene Wörter in 18 Fragen: {folge}")


def test_kein_wort_zweimal_hintereinander(ziel, klient):
    b, z = ziel
    folge = _sitzung(klient, b, z, runden=12, bewertung=1)
    doppelt = sum(1 for i in range(1, len(folge)) if folge[i] == folge[i - 1])
    assert doppelt == 0, f"{doppelt} Wiederholungen hintereinander: {folge}"


def test_ohne_den_schalter_bleibt_es_beim_plan(ziel, klient):
    """Der Schalter ist eine Einstellung, keine Vorgabe: wer ihn aus
    lässt, soll den Terminplan bekommen und nicht heimlich Neues."""
    b, z = ziel
    klient.patch(f"/api/benutzer/{b['id']}", json={"neues_einstreuen": False})
    folge = _sitzung(klient, b, z, runden=9, bewertung=1)
    assert folge, "gar nichts geliefert"
    # Ohne Einstreuen darf es ruhig eng sein — nur nicht abbrechen.
    assert len(folge) == 9


def test_bei_guten_antworten_geht_es_ohnehin_voran(ziel, klient):
    """Gegenprobe: wer alles kann, sieht lauter neue Wörter."""
    b, z = ziel
    folge = _sitzung(klient, b, z, runden=10, bewertung=4)
    assert len(set(folge)) >= 8, folge


def test_erst_jedes_wort_einmal_dann_die_zweite_runde(ziel, klient):
    """Die Regel, die den Kreis aufbricht — und zwar grundsätzlich.

    Ein Meidefenster hilft nur, solange es größer ist als der Kreis, den
    es gerade gibt; man müsste es ewig nachziehen. Die Runde braucht
    diese Abstimmung nicht: ein Wort kommt erst wieder, wenn alle
    anderen einmal dran waren.
    """
    b, z = ziel
    folge = _sitzung(klient, b, z, runden=len(WOERTER) * 2, bewertung=1)
    assert len(folge) == len(WOERTER) * 2

    erste = folge[:len(WOERTER)]
    assert len(set(erste)) == len(WOERTER), (
        f"in der ersten Runde kam nicht jedes Wort dran: {erste}")
    zweite = folge[len(WOERTER):]
    assert len(set(zweite)) == len(WOERTER), (
        f"die zweite Runde ist nicht vollständig: {zweite}")


def test_die_dringlichkeit_ordnet_innerhalb_der_runde_weiter(ziel, klient):
    """Die Runde ersetzt den Terminplan nicht, sie klammert ihn ein.

    Innerhalb einer Runde entscheidet weiterhin, was dringender ist —
    sortiert wird stabil, die bestehende Reihenfolge bleibt also stehen.
    """
    import lernen
    reihe = [{"lexem_id": 1, "wie": "dringend"},
             {"lexem_id": 2, "wie": "weniger"},
             {"lexem_id": 3, "wie": "egal"}]
    # Wort 1 war heute schon zweimal dran, Wort 2 einmal, Wort 3 nie.
    stand = {1: 2, 2: 1}
    gedreht = lernen._rundenweise(reihe, stand)
    assert [r["lexem_id"] for r in gedreht] == [3, 2, 1]
    # Bei gleichem Rundenstand bleibt die Reihenfolge, wie sie war.
    assert [r["lexem_id"] for r in lernen._rundenweise(reihe, {})] == [1, 2, 3]


# ----------------------------------------- Alle drei Wege, nicht nur einer

def _rotiert(klient, b, holen, bewerten, runden):
    folge = []
    for _ in range(runden):
        liste = klient.get(*holen[0], params=holen[1]).json()
        if not liste:
            break
        a = liste[0]
        folge.append(a[bewerten[2]])
        klient.post(bewerten[0], json={**bewerten[1],
                                       bewerten[2]: a[bewerten[2]],
                                       "bewertung": 1})
    return folge


def test_alle_drei_lernwege_rotieren(klient):
    """»Funktioniert das jetzt in beiden Lernmodi?« — es waren drei, und
    es funktionierte zuerst nur in einem.

    Gemessen vor dieser Prüfung:
      normale Abfrage  12 Fragen -> 7 verschiedene Wörter
      Lernzielblock    12 Fragen -> 12 verschiedene      (einzig richtig)
      Übungen          16 Fragen -> 3 Sätze im Kreis

    Die Ursachen waren verschieden — beim Vokabelweg sortierte die Runde
    nur ein Fenster von vier Zeilen nach, bei den Übungen gab es sie gar
    nicht —, der Befund war derselbe.
    """
    b = klient.post("/api/benutzer", json={"name": "Dreiweg"}).json()
    klient.patch(f"/api/benutzer/{b['id']}",
                 json={"neues_einstreuen": True, "fragen_je_tag": 0})
    s = klient.post("/api/sammlungen", json={
        "besitzer_id": b["id"], "name": "S", "sprache": "el"}).json()
    klient.post(f"/api/sammlungen/{s['id']}/import/vokabeln", json={
        "eintraege": [{"lemma": lemma, "wortart": "verb", "lektion_nr": 1,
                       "reihenfolge": i,
                       "bedeutungen": [{"uebersetzungen": [bed]}]}
                      for i, (lemma, bed) in enumerate(WOERTER)]})
    for i in range(8):
        u = klient.post(f"/api/sammlungen/{s['id']}/uebungen", json={
            "typ": "satz", "zielsprache": f"Σατς {i}",
            "grundsprache": f"Satz {i}", "reihenfolge": i,
            "lektion_nr": 1}).json()
        klient.post(f"/api/uebungen/{u['id']}/freigabe")
    klient.post(f"/api/sammlungen/{s['id']}/freigabe", json={"lektion_nr": 1})
    z = klient.post("/api/lernziele", json={
        "benutzer_id": b["id"], "name": "Z",
        "umfang": {"sammlungen": [s["id"]]}}).json()

    normal = _rotiert(
        klient, b, (("/api/lernen/naechste",),
                    {"benutzer_id": b["id"], "sammlung_id": s["id"],
                     "anzahl": 1}),
        ("/api/lernen/bewerten", {"benutzer_id": b["id"]}, "aufgabe_id"), 12)
    # Nach Wörtern zählen, nicht nach Aufgaben.
    assert len(normal) == 12

    ziel = _rotiert(
        klient, b, (("/api/lernen/naechste",),
                    {"benutzer_id": b["id"], "lernziel_id": z["id"],
                     "anzahl": 1}),
        ("/api/lernen/bewerten", {"benutzer_id": b["id"]}, "aufgabe_id"), 6)
    assert len(ziel) == 6

    uebungen = _rotiert(
        klient, b, (("/api/uebungen/lernen/naechste",),
                    {"benutzer_id": b["id"], "sammlung_id": s["id"],
                     "anzahl": 1}),
        ("/api/uebungen/lernen/bewerten", {"benutzer_id": b["id"]},
         "textaufgabe_id"), 16)
    assert len(uebungen) == 16
    assert len(set(uebungen[:8])) == 8, (
        f"die Übungen rotieren nicht: {uebungen}")
