"""Übungssätze abfragen — dieselbe Rechnung wie bei den Vokabeln.

Drei Dinge sind hier anders als bei einer Vokabel, und jedes aus einem
Grund: die Denkzeit geht nicht in die Bewertung ein (sie misst bei einem
Satz Lesen und Tippen), die beiden Richtungen haben getrennte Lernstände
(es sind zwei Fähigkeiten), und bei langen Texten entscheidet der Mensch.
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
    "alternativen_grundsprache": ["Gestern bin ich ins Theater gegangen."],
    "richtungen": ["el-de", "de-el"],
}


def anlegen(klient, sammlung_id, eintrag=None, freigeben=True):
    u = klient.post(f"/api/sammlungen/{sammlung_id}/uebungen",
                    json=eintrag or SATZ).json()
    if freigeben:
        klient.post(f"/api/uebungen/{u['id']}/freigabe")
    return u


def stand(klient, benutzer_id, sammlung_id=None):
    # sammlung_id weglassen statt leer schicken: ein leeres "sammlung_id="
    # ist für FastAPI keine gültige Ganzzahl und gibt 422.
    frage = {"benutzer_id": benutzer_id}
    if sammlung_id is not None:
        frage["sammlung_id"] = sammlung_id
    return klient.get("/api/uebungen/lernen/stand", params=frage).json()


def naechste(klient, benutzer_id, **frage):
    antwort = klient.get("/api/uebungen/lernen/naechste",
                         params={"benutzer_id": benutzer_id, **frage})
    assert antwort.status_code == 200, antwort.text
    return antwort.json()


def pruefen(klient, benutzer_id, textaufgabe_id, antwort):
    a = klient.post("/api/uebungen/lernen/pruefen", json={
        "benutzer_id": benutzer_id, "textaufgabe_id": textaufgabe_id,
        "antwort": antwort})
    assert a.status_code == 200, a.text
    return a.json()


def bewerten(klient, benutzer_id, textaufgabe_id, **daten):
    a = klient.post("/api/uebungen/lernen/bewerten", json={
        "benutzer_id": benutzer_id, "textaufgabe_id": textaufgabe_id, **daten})
    assert a.status_code == 200, a.text
    return a.json()


# ------------------------------------------------------ Nur Freigegebenes

def test_ungepruefte_uebungen_werden_nicht_abgefragt(klient):
    """Wie bei den Formen. Die Zahl steht trotzdem im Stand, damit niemand
    vergeblich nach ihnen sucht."""
    b, s = _aufbau(klient)
    anlegen(klient, s["id"], freigeben=False)
    z = stand(klient, b["id"], s["id"])
    assert z["gesamt"] == 0 and z["ungeprueft"] == 2
    assert naechste(klient, b["id"], sammlung_id=s["id"]) == []


def test_nach_der_freigabe_ist_sie_dran(klient):
    b, s = _aufbau(klient)
    u = anlegen(klient, s["id"], freigeben=False)
    klient.post(f"/api/uebungen/{u['id']}/freigabe")
    z = stand(klient, b["id"], s["id"])
    assert (z["gesamt"], z["neu"], z["ungeprueft"]) == (2, 2, 0)
    assert len(naechste(klient, b["id"], sammlung_id=s["id"], anzahl=5)) == 2


# ------------------------------------------------------------- Die Aufgabe

def test_die_aufgabe_nennt_richtung_und_sprachen(klient):
    b, s = _aufbau(klient)
    anlegen(klient, s["id"])
    hin = next(a for a in naechste(klient, b["id"], sammlung_id=s["id"],
                                   anzahl=5)
               if a["typ"] == "uebersetzung_hin")
    assert hin["frage_text"] == "Χθες πήγα στο θέατρο."
    assert (hin["frage_sprache"], hin["antwort_sprache"]) == ("el", "de")
    assert hin["aufgabe_text"] == "In die Grundsprache übersetzen"
    assert hin["lektion_nr"] == 39
    # Vorgelesen wird nur, was in der Lernsprache steht.
    assert hin["vorlesen"] == "Χθες πήγα στο θέατρο."

    zurueck = next(a for a in naechste(klient, b["id"], sammlung_id=s["id"],
                                       anzahl=5)
                   if a["typ"] == "uebersetzung_rueck")
    assert zurueck["frage_text"] == "Gestern ging ich ins Theater."
    assert (zurueck["frage_sprache"], zurueck["antwort_sprache"]) == ("de", "el")
    assert zurueck["vorlesen"] is None


def test_die_aufgabe_verraet_die_loesung_nicht(klient):
    b, s = _aufbau(klient)
    anlegen(klient, s["id"])
    aufgabe = naechste(klient, b["id"], sammlung_id=s["id"])[0]
    inhalt = str(aufgabe)
    assert "erwartet" not in aufgabe
    assert "loesung" not in aufgabe
    if aufgabe["typ"] == "uebersetzung_hin":
        assert "Gestern ging ich" not in inhalt


def test_eine_richtung_laesst_sich_waehlen(klient):
    b, s = _aufbau(klient)
    anlegen(klient, s["id"])
    nur_hin = naechste(klient, b["id"], sammlung_id=s["id"],
                       richtung="hin", anzahl=5)
    assert [a["typ"] for a in nur_hin] == ["uebersetzung_hin"]


# ------------------------------------------------------------ Bewerten

@pytest.mark.parametrize("antwort,erwartet", [
    ("Gestern ging ich ins Theater.", "richtig"),
    ("Gestern bin ich ins Theater gegangen.", "richtig"),
    ("Gestern ging ich ins Kino.", "falsch"),
])
def test_vergleich_wort_fuer_wort(klient, antwort, erwartet):
    b, s = _aufbau(klient)
    anlegen(klient, s["id"])
    hin = next(a for a in naechste(klient, b["id"], sammlung_id=s["id"],
                                   anzahl=5) if a["typ"] == "uebersetzung_hin")
    ergebnis = pruefen(klient, b["id"], hin["textaufgabe_id"], antwort)
    assert ergebnis["urteil"]["urteil"] == erwartet
    assert ergebnis["zaehlt"] is True
    assert ergebnis["loesung"]["haupt"] == "Gestern ging ich ins Theater."
    # Das Gegenstück gehört dazu: wer die Lösung liest, will den Satz ganz
    # sehen und nicht nur die Hälfte.
    assert ergebnis["loesung"]["gegenstueck"] == "Χθες πήγα στο θέατρο."


def test_richtig_setzt_einen_termin(klient):
    b, s = _aufbau(klient)
    anlegen(klient, s["id"])
    aufgabe = naechste(klient, b["id"], sammlung_id=s["id"])[0]
    ergebnis = bewerten(klient, b["id"], aufgabe["textaufgabe_id"],
                        urteil="richtig", antwort="…")
    assert ergebnis["bewertung"] >= 3
    assert ergebnis["bewertung_quelle"] == "automatisch"
    assert ergebnis["intervall_tage"] > 0
    assert ergebnis["stabilitaet"] > 0
    # Und sie ist heute nicht mehr dran.
    offen = [a["textaufgabe_id"] for a in
             naechste(klient, b["id"], sammlung_id=s["id"], anzahl=5)]
    assert aufgabe["textaufgabe_id"] not in offen


def test_falsch_kommt_gleich_wieder(klient):
    b, s = _aufbau(klient)
    anlegen(klient, s["id"])
    aufgabe = naechste(klient, b["id"], sammlung_id=s["id"])[0]
    ergebnis = bewerten(klient, b["id"], aufgabe["textaufgabe_id"],
                        urteil="falsch", antwort="Quatsch")
    assert ergebnis["bewertung"] == 1
    offen = [a["textaufgabe_id"] for a in
             naechste(klient, b["id"], sammlung_id=s["id"], anzahl=5)]
    assert aufgabe["textaufgabe_id"] in offen
    # Nach dem ERSTEN Fehler heißt der Zustand "lernen", nicht "verlernt" —
    # verlernt wird nur, was schon einmal saß. Fällig ist sie trotzdem.
    assert ergebnis["zustand"] == "lernen"
    assert ergebnis["termin_text"] == "gleich noch einmal"
    assert stand(klient, b["id"], s["id"])["faellig"] >= 1


def test_die_beiden_richtungen_haben_getrennte_lernstaende(klient):
    """»Χθες πήγα στο θέατρο« zu verstehen ist leicht; es zu bilden nicht.
    Zwei Fähigkeiten, zwei Lernstände."""
    b, s = _aufbau(klient)
    anlegen(klient, s["id"])
    alle = naechste(klient, b["id"], sammlung_id=s["id"], anzahl=5)
    hin = next(a for a in alle if a["typ"] == "uebersetzung_hin")
    bewerten(klient, b["id"], hin["textaufgabe_id"], urteil="richtig")
    uebrig = naechste(klient, b["id"], sammlung_id=s["id"], anzahl=5)
    assert [a["typ"] for a in uebrig] == ["uebersetzung_rueck"]


def test_bei_langem_text_entscheidet_der_mensch(klient):
    """Eine freie Übersetzung eines Absatzes stimmt selten wörtlich. Der
    Vergleich läuft trotzdem — aber er zählt nicht."""
    b, s = _aufbau(klient)
    anlegen(klient, s["id"], {
        "typ": "text", "titel": "Στο θέατρο",
        "zielsprache": "Χθες πήγα στο θέατρο. Η παράσταση ήταν ωραία.",
        "grundsprache": "Gestern ging ich ins Theater. Die Vorstellung war schön.",
        "richtungen": ["el-de"]})
    aufgabe = naechste(klient, b["id"], sammlung_id=s["id"])[0]
    assert aufgabe["selbsteinschaetzung"] is True
    ergebnis = pruefen(klient, b["id"], aufgabe["textaufgabe_id"],
                       "Gestern war ich im Theater.")
    assert ergebnis["zaehlt"] is False
    # Die Einschätzung kommt dann von der Person und wird als solche
    # protokolliert.
    bewertet = bewerten(klient, b["id"], aufgabe["textaufgabe_id"],
                        urteil="richtig", antwort="Gestern war ich im Theater.")
    assert bewertet["bewertung_quelle"] == "selbsteinschaetzung"


def test_wortgleich_zaehlt_auch_beim_text(klient):
    """»Wie kommt das? Es ist doch sogar wortgleich.«

    Neben »Richtig — 9 von 9 Wörtern« stand »zählt nicht«, und sie
    musste darunter noch einmal von Hand bestätigen, dass es richtig
    war. Die Begründung für die Selbsteinschätzung — eine freie
    Übersetzung trifft die Referenz selten wörtlich — gilt hier nicht,
    denn sie hat sie wörtlich getroffen. Dann gibt es nichts mehr
    einzuschätzen.
    """
    b, s = _aufbau(klient)
    anlegen(klient, s["id"], {
        "typ": "text", "titel": "Στο θέατρο",
        "zielsprache": "Χθες πήγα στο θέατρο. Η παράσταση ήταν ωραία.",
        "grundsprache": "Gestern ging ich ins Theater. Die Vorstellung war schön.",
        "richtungen": ["el-de"]})
    aufgabe = naechste(klient, b["id"], sammlung_id=s["id"])[0]
    wort_fuer_wort = "Gestern ging ich ins Theater."

    ergebnis = pruefen(klient, b["id"], aufgabe["textaufgabe_id"], wort_fuer_wort)
    assert ergebnis["urteil"]["wortgleich"] is True
    assert ergebnis["zaehlt"] is True
    assert ergebnis["selbsteinschaetzung"] is False

    # Und im Protokoll steht dann auch nicht, sie habe sich selbst
    # eingeschätzt — gefragt wurde sie ja gar nicht.
    bewertet = bewerten(klient, b["id"], aufgabe["textaufgabe_id"],
                        urteil="richtig", antwort=wort_fuer_wort)
    assert bewertet["bewertung_quelle"] == "automatisch"


def test_nur_die_gleichheit_oeffnet_die_tuer(klient):
    """Eine Tür in eine Richtung. Wer NICHT wörtlich trifft, kann
    trotzdem völlig richtig übersetzt haben — deswegen gibt es die
    Selbsteinschätzung überhaupt. Auch »fast« bleibt bei ihr: dort
    weicht etwas ab, und ob das ein Fehler ist, weiß nur sie."""
    b, s = _aufbau(klient)
    anlegen(klient, s["id"], {
        "typ": "text", "titel": "Στο θέατρο",
        "zielsprache": "Χθες πήγα στο θέατρο. Η παράσταση ήταν ωραία.",
        "grundsprache": "Gestern ging ich ins Theater. Die Vorstellung war schön.",
        "richtungen": ["el-de"]})
    aufgabe = naechste(klient, b["id"], sammlung_id=s["id"])[0]

    for antwort in ("Gestern war ich im Theater.",      # richtig, aber anders
                    "Gestern ging ich ins Theatr.",     # Tippfehler -> fast
                    "Heute koche ich Suppe."):          # falsch
        ergebnis = pruefen(klient, b["id"], aufgabe["textaufgabe_id"], antwort)
        assert ergebnis["urteil"]["wortgleich"] is False, antwort
        assert ergebnis["zaehlt"] is False, antwort
        assert ergebnis["selbsteinschaetzung"] is True, antwort


def test_aufdecken_zeigt_die_loesung(klient):
    b, s = _aufbau(klient)
    anlegen(klient, s["id"])
    aufgabe = naechste(klient, b["id"], sammlung_id=s["id"])[0]
    a = klient.post("/api/uebungen/lernen/aufdecken", json={
        "benutzer_id": b["id"], "textaufgabe_id": aufgabe["textaufgabe_id"]})
    assert a.status_code == 200, a.text
    assert a.json()["loesung"]["haupt"]
    ergebnis = bewerten(klient, b["id"], aufgabe["textaufgabe_id"],
                        urteil="falsch", aufgedeckt=True)
    assert ergebnis["bewertung"] == 1


def test_die_denkzeit_geht_nicht_in_die_bewertung_ein(klient):
    """Bei einem Satz misst sie Lesen und Tippen, nicht das Können. Zwei
    gleiche Antworten müssen gleich bewertet werden."""
    b, s = _aufbau(klient)
    anlegen(klient, s["id"])
    anlegen(klient, s["id"], {**SATZ, "zielsprache": "Σήμερα διαβάζω.",
                              "grundsprache": "Heute lese ich.",
                              "alternativen_grundsprache": []})
    beide = naechste(klient, b["id"], sammlung_id=s["id"], anzahl=9)
    schnell = bewerten(klient, b["id"], beide[0]["textaufgabe_id"],
                       urteil="richtig", dauer_ms=800)
    langsam = bewerten(klient, b["id"], beide[1]["textaufgabe_id"],
                       urteil="richtig", dauer_ms=45000)
    assert schnell["bewertung"] == langsam["bewertung"]


# ----------------------------------------------------------- Eingrenzen

def test_nach_lektion_und_bis_lektion(klient):
    b, s = _aufbau(klient)
    anlegen(klient, s["id"])                                   # Lektion 39
    anlegen(klient, s["id"], {**SATZ, "lektion_nr": 12,
                              "zielsprache": "Σήμερα διαβάζω.",
                              "grundsprache": "Heute lese ich.",
                              "alternativen_grundsprache": []})
    nur12 = naechste(klient, b["id"], sammlung_id=s["id"], lektion_nr=12,
                     anzahl=9)
    assert {a["lektion_nr"] for a in nur12} == {12}
    bis20 = naechste(klient, b["id"], sammlung_id=s["id"], bis_lektion=20,
                     anzahl=9)
    assert {a["lektion_nr"] for a in bis20} == {12}
    alles = naechste(klient, b["id"], sammlung_id=s["id"], anzahl=9)
    assert {a["lektion_nr"] for a in alles} == {12, 39}


def test_eine_fremde_sammlung_liefert_nichts(klient):
    b1, s1 = _aufbau(klient)
    anlegen(klient, s1["id"])
    b2 = klient.post("/api/benutzer", json={"name": "Andere"}).json()
    assert naechste(klient, b2["id"]) == []
    assert stand(klient, b2["id"])["gesamt"] == 0
