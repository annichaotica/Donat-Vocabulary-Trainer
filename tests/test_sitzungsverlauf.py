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


# ------------------------------------------------- Tagespensum und Ende

def test_der_stand_sagt_wie_viel_heute_noch_kommt(klient):
    """»Hat die irgendwann ein Ende?« — ohne diese Zahl weiß das niemand,
    und der Balken war nach 25 Fragen voll, gleich ob noch dreißig oder
    dreihundert kamen."""
    b, s = _bestand(klient)
    stand = klient.get("/api/lernen/stand", params={
        "benutzer_id": b["id"], "sammlung_id": s["id"]}).json()
    assert stand["heute_erledigt"] == 0
    assert stand["heute_offen"] > 0
    assert stand["heute_gesamt"] == stand["heute_offen"]
    # Nicht der ganze Bestand: der Tagesvorrat an Wörtern begrenzt ihn.
    assert stand["heute_offen"] <= stand["gesamt"]
    assert stand["neue_woerter_frei"] > 0


def test_das_pensum_waechst_mit_dem_erledigten_mit(klient):
    b, s = _bestand(klient)
    vorher = klient.get("/api/lernen/stand", params={
        "benutzer_id": b["id"], "sammlung_id": s["id"]}).json()
    _sitzung(klient, b, s, runden=5)
    nachher = klient.get("/api/lernen/stand", params={
        "benutzer_id": b["id"], "sammlung_id": s["id"]}).json()
    assert nachher["heute_erledigt"] == 5
    assert nachher["heute_erledigt"] + nachher["heute_offen"] \
        == nachher["heute_gesamt"]
    assert nachher["neue_woerter_frei"] < vorher["neue_woerter_frei"]


def test_die_abfrage_endet_wenn_das_pensum_abgearbeitet_ist(klient):
    """Sie läuft nicht endlos: ist alles Fällige getan und der Tagesvorrat
    aufgebraucht, kommt nichts mehr."""
    b = klient.post("/api/benutzer", json={"name": "Fleissige"}).json()
    klient.patch(f"/api/benutzer/{b['id']}", json={"neu_je_sitzung": 1})
    s = klient.post("/api/sammlungen", json={
        "besitzer_id": b["id"], "name": "Griechisch", "sprache": "el"}).json()
    klient.post(f"/api/sammlungen/{s['id']}/import/vokabeln", json={
        "eintraege": [{"lemma": stamm + "ω", "wortart": "verb",
                       "bedeutungen": [{"uebersetzungen": [b1, b2]}]}
                      for stamm, b1, b2 in VERBEN[:3]]})
    klient.post(f"/api/sammlungen/{s['id']}/freigabe",
                json={"lexem_ids": [1, 2, 3]})
    folge = []
    for _ in range(30):
        liste = klient.get("/api/lernen/naechste", params={
            "benutzer_id": b["id"], "sammlung_id": s["id"], "anzahl": 1}).json()
        if not liste:
            break
        folge.append(liste[0]["lexem_id"])
        klient.post("/api/lernen/bewerten", json={
            "benutzer_id": b["id"], "aufgabe_id": liste[0]["aufgabe_id"],
            "bewertung": 3})
    assert len(folge) < 30, "die Abfrage muss ein Ende haben"
    assert len(set(folge)) == 1, "ein Wort am Tag heißt ein Wort"


def test_neues_einstreuen_holt_neues_vor_das_faellige(klient):
    """Der Schalter: mehr Abwechslung gegen etwas später wiederholte
    Vokabeln. Das ist eine Entscheidung über das eigene Lernen, darum eine
    Einstellung und keine Vorgabe.

    Geprüft wird, was er wirklich tut: ausgeschaltet kommt erst alles
    Fällige, eingeschaltet schiebt sich Neues dazwischen.
    """
    b, s = _bestand(klient)

    # Einen echten Rückstand aufbauen: zehn VERSCHIEDENE Aufgaben einmal
    # falsch. Danach liegt Fälliges vor allem Neuen.
    offen = klient.get("/api/lernen/naechste", params={
        "benutzer_id": b["id"], "sammlung_id": s["id"], "anzahl": 10}).json()
    assert len(offen) >= 8
    for a in offen:
        klient.post("/api/lernen/bewerten", json={
            "benutzer_id": b["id"], "aufgabe_id": a["aufgabe_id"],
            "bewertung": 1})

    def zustaende(runden=6):
        """Eine Frage nach der anderen, wie es die Oberfläche tut — der
        Schalter wirkt bei jeder dritten, nicht auf einen Schlag."""
        gesehen = []
        for _ in range(runden):
            liste = klient.get("/api/lernen/naechste", params={
                "benutzer_id": b["id"], "sammlung_id": s["id"],
                "anzahl": 1}).json()
            if not liste:
                break
            gesehen.append(liste[0]["lernstand"]["zustand"] or "neu")
            klient.post("/api/lernen/bewerten", json={
                "benutzer_id": b["id"], "aufgabe_id": liste[0]["aufgabe_id"],
                "bewertung": 1})          # fällig halten, sonst leert sich der Berg
        return gesehen

    aus = zustaende()
    assert "neu" not in aus, f"ohne Schalter kommt erst Fälliges: {aus}"

    klient.patch(f"/api/benutzer/{b['id']}", json={"neues_einstreuen": True})
    an = zustaende()
    assert "neu" in an, f"mit Schalter muss Neues dazwischenkommen: {an}"
    # Aber nicht überhandnehmen — das Fällige bleibt in der Mehrzahl.
    assert an.count("neu") <= len(an) // 2, an


def test_ein_wort_mit_vielen_formen_bleibt_nicht_fuer_immer_vorn(klient):
    """Der Fehler, der im Betrieb auffiel und den ich selbst eingebaut
    hatte: der Rang INNERHALB eines Wortes zählt nur die übrigen Aufgaben.
    Nach jeder Antwort werden sie neu durchnummeriert — es gibt also
    immer wieder eine mit Rang 1, und ein Verb mit vierzig Formen stand
    für immer vorn. Im echten Protokoll kreisten drei Wörter, während
    1.280 andere nie drankamen.

    Jetzt zählt, wie viel von einem Wort schon dran WAR.
    """
    b = klient.post("/api/benutzer", json={"name": "Kreisende"}).json()
    s = klient.post("/api/sammlungen", json={
        "besitzer_id": b["id"], "name": "Griechisch", "sprache": "el"}).json()
    # Ein Verb mit vielen Formen und zehn magere Wörter daneben.
    eintraege = [{
        "lemma": "γράφω", "wortart": "verb", "lektion_nr": 1, "reihenfolge": 0,
        "bedeutungen": [{"uebersetzungen": ["schreiben", "aufschreiben"]}],
        "formen": [{"text": "γράφ" + e, "merkmale": {
            "modus": "indikativ", "tempus": zeit, "person": p, "numerus": n}}
            for zeit, endungen in (("praesens", ["ω", "εις", "ει", "ουμε",
                                                 "ετε", "ουν"]),
                                   ("imperfekt", ["α", "ες", "ε", "αμε",
                                                  "ατε", "αν"]))
            for e, (p, n) in zip(endungen, P)]}]
    eintraege += [{"lemma": f"λέξη{i}", "wortart": "substantiv",
                   "lektion_nr": 1, "reihenfolge": i + 1,
                   "merkmale": {"genus": "f"},
                   "bedeutungen": [{"uebersetzungen": [f"Wort {i}",
                                                       f"Begriff {i}"]}]}
                  for i in range(1, 11)]
    klient.post(f"/api/sammlungen/{s['id']}/import/vokabeln",
                json={"eintraege": eintraege})
    klient.post(f"/api/sammlungen/{s['id']}/freigabe", json={"lektion_nr": 1})

    folge = []
    for _ in range(20):
        liste = klient.get("/api/lernen/naechste", params={
            "benutzer_id": b["id"], "sammlung_id": s["id"], "anzahl": 1}).json()
        if not liste:
            break
        folge.append(liste[0]["lexem_id"])
        klient.post("/api/lernen/bewerten", json={
            "benutzer_id": b["id"], "aufgabe_id": liste[0]["aufgabe_id"],
            "bewertung": 3})
    # Vorher kamen hier zwei, drei Wörter heraus — das Verb blieb vorn.
    assert len(set(folge)) >= 8, f"nur {len(set(folge))} Wörter: {folge}"
    # Und das vielformige Verb nimmt nicht überhand.
    haeufigstes = max(folge.count(x) for x in set(folge))
    assert haeufigstes <= 4, f"ein Wort kam {haeufigstes}× in 20 Fragen"
