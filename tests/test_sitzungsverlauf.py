"""Wie sich eine Sitzung anfühlt.

Der Einwand aus dem Betrieb: »ich werde gefühlt ständig nur ein Wort
gefragt«. Nachgemessen am echten Protokoll stimmte es — 36 von 51
Übergängen blieben beim selben Wort.

Zwei Ursachen, beide nicht offensichtlich:

Die Oberfläche holt je EINE Aufgabe, und der Block wird bei jedem Abruf
neu gerechnet. Wer »nochmal« bekommt, ist sofort wieder der dringendste
und steht wieder ganz vorn — also kam dasselbe Wort ein Dutzend Mal.

Und wenn mehrere Wörter gleich dringend sind, stand immer dasselbe vorn:
ein starrer Zyklus γράφω, διαβάζω, παίζω, γράφω — kaum besser.
"""

import random

P = [("1", "sg"), ("2", "sg"), ("3", "sg"),
     ("1", "pl"), ("2", "pl"), ("3", "pl")]
ENDUNGEN = ["ω", "εις", "ει", "ουμε", "ετε", "ουν"]
VERBEN = [("γράφ", "schreiben", "aufschreiben"),
          ("διαβάζ", "lesen", "vorlesen"),
          ("παίζ", "spielen", "aufführen"),
          ("τρέχ", "laufen", "rennen"),
          ("μιλ", "sprechen", "reden"),
          ("ακού", "hören", "zuhören")]


def _bestand(klient):
    b = klient.post("/api/benutzer", json={"name": "Übende"}).json()
    s = klient.post("/api/sammlungen", json={
        "besitzer_id": b["id"], "name": "Griechisch", "sprache": "el"}).json()
    klient.post(f"/api/sammlungen/{s['id']}/import/vokabeln", json={
        "eintraege": [{
            "lemma": stamm + "ω", "wortart": "verb", "lektion_nr": 1,
            "reihenfolge": i,
            "bedeutungen": [{"uebersetzungen": [b1, b2]}],
            "formen": [{"text": stamm + e, "merkmale": {
                "modus": "indikativ", "tempus": "praesens",
                "person": p, "numerus": n}}
                for e, (p, n) in zip(ENDUNGEN, P)]}
            for i, (stamm, b1, b2) in enumerate(VERBEN)]})
    klient.post(f"/api/sammlungen/{s['id']}/freigabe", json={"lektion_nr": 1})
    return b, s


def _sitzung(klient, b, s, runden=40, saat=7):
    """Spielt eine Sitzung durch, wie ein Mensch sie geht: eine Aufgabe
    holen, beantworten, nächste holen."""
    wuerfel = random.Random(saat)
    folge = []
    for _ in range(runden):
        liste = klient.get("/api/lernen/naechste", params={
            "benutzer_id": b["id"], "sammlung_id": s["id"], "anzahl": 1}).json()
        if not liste:
            break
        a = liste[0]
        folge.append(a["lexem_id"])
        klient.post("/api/lernen/bewerten", json={
            "benutzer_id": b["id"], "aufgabe_id": a["aufgabe_id"],
            "bewertung": wuerfel.choices([1, 2, 3, 4],
                                         weights=[12, 20, 48, 20])[0]})
    return folge


def test_nicht_zweimal_dasselbe_wort_hintereinander(klient):
    b, s = _bestand(klient)
    folge = _sitzung(klient, b, s)
    assert len(folge) >= 30
    gleich = [i for i in range(1, len(folge)) if folge[i] == folge[i - 1]]
    assert not gleich, (f"{len(gleich)} Wiederholungen direkt hintereinander "
                        f"bei {len(folge)} Abfragen")


def test_die_sitzung_kreist_nicht_in_einem_starren_zyklus(klient):
    """Drei Wörter immer in derselben Reihenfolge sind kaum besser als
    eines. Geprüft am Abstand: er darf nicht immer gleich sein."""
    b, s = _bestand(klient)
    folge = _sitzung(klient, b, s)
    abstaende = set()
    zuletzt = {}
    for i, wort in enumerate(folge):
        if wort in zuletzt:
            abstaende.add(i - zuletzt[wort])
        zuletzt[wort] = i
    assert len(abstaende) >= 3, f"immer derselbe Abstand: {abstaende}"


def test_auch_falsch_beantwortete_kommen_nicht_sofort_wieder(klient):
    """Sie sollen wiederkommen — nur nicht als die allernächste Frage.
    Genau das machte die Sitzung einseitig."""
    b, s = _bestand(klient)
    erste = klient.get("/api/lernen/naechste", params={
        "benutzer_id": b["id"], "sammlung_id": s["id"], "anzahl": 1}).json()[0]
    klient.post("/api/lernen/bewerten", json={
        "benutzer_id": b["id"], "aufgabe_id": erste["aufgabe_id"],
        "bewertung": 1})
    zweite = klient.get("/api/lernen/naechste", params={
        "benutzer_id": b["id"], "sammlung_id": s["id"], "anzahl": 1}).json()[0]
    assert zweite["lexem_id"] != erste["lexem_id"]


def test_bleibt_nur_ein_wort_uebrig_wird_es_trotzdem_gefragt(klient):
    """Der Abstand ist ein Wunsch, keine Sperre — sonst bliebe am Ende
    einer Lektion die letzte Vokabel ungefragt liegen."""
    b = klient.post("/api/benutzer", json={"name": "Einzelne"}).json()
    s = klient.post("/api/sammlungen", json={
        "besitzer_id": b["id"], "name": "Griechisch", "sprache": "el"}).json()
    klient.post(f"/api/sammlungen/{s['id']}/import/vokabeln", json={
        "eintraege": [{
            "lemma": "γράφω", "wortart": "verb",
            "bedeutungen": [{"uebersetzungen": ["schreiben", "reden"]}]}]})
    klient.post(f"/api/sammlungen/{s['id']}/freigabe", json={"lexem_ids": [1]})
    # Immer "nochmal", damit es fällig bleibt — sonst endet die Sitzung
    # ganz regulär, weil das Wort nur zwei Aufgaben hat.
    folge = []
    for _ in range(5):
        liste = klient.get("/api/lernen/naechste", params={
            "benutzer_id": b["id"], "sammlung_id": s["id"],
            "anzahl": 1}).json()
        if not liste:
            break
        folge.append(liste[0]["lexem_id"])
        klient.post("/api/lernen/bewerten", json={
            "benutzer_id": b["id"], "aufgabe_id": liste[0]["aufgabe_id"],
            "bewertung": 1})
    assert len(folge) == 5, "das einzige Wort muss weiter gefragt werden"
    assert set(folge) == {1}
