"""Nach »nochmal« darf nicht sofort derselbe Satz wiederkommen.

Auf der Vokabelseite war das schon einmal der Befund aus dem Betrieb
(»ich werde gefühlt ständig nur ein wort gefragt«) und ist dort mit
_zuletzt_gefragt / _abstand_halten / _abwechseln behoben. Die
Übungsseite ist eine zweite Umsetzung desselben Lernkerns — und die
Reparatur fehlte dort vollständig.

»Nochmal« setzt den Zustand auf 'verlernt' und den Termin auf heute;
die Sortierung stellt 'verlernt' auf Rang 0. Also stand derselbe Satz
sofort wieder vorn, beliebig oft, während unangetastete Sätze daneben
lagen.
"""

import pytest

SAETZE = [
    ("Je vais à Paris.", "Ich gehe nach Paris."),
    ("Il fait beau.", "Das Wetter ist schön."),
    ("Nous mangeons du pain.", "Wir essen Brot."),
    ("Elle lit un livre.", "Sie liest ein Buch."),
]


@pytest.fixture()
def bestand(klient):
    b = klient.post("/api/benutzer", json={"name": "Übende"}).json()
    s = klient.post("/api/sammlungen", json={
        "besitzer_id": b["id"], "name": "Französisch", "sprache": "fr"}).json()
    for i, (ziel, grund) in enumerate(SAETZE):
        a = klient.post(f"/api/sammlungen/{s['id']}/uebungen", json={
            "typ": "satz", "zielsprache": ziel, "grundsprache": grund,
            "reihenfolge": i, "lektion_nr": 1})
        assert a.status_code in (200, 201), a.text
        klient.post(f"/api/uebungen/{a.json()['id']}/freigabe")
    return b, s


def test_nach_nochmal_kommt_nicht_sofort_derselbe_satz(bestand, klient):
    """Acht Runden, jedes Mal »nochmal« — es dürfen nicht achtmal
    derselbe Satz sein."""
    b, s = bestand
    folge = []
    for _ in range(8):
        liste = klient.get("/api/uebungen/lernen/naechste", params={
            "benutzer_id": b["id"], "sammlung_id": s["id"], "anzahl": 1}).json()
        if not liste:
            break
        a = liste[0]
        folge.append(a["textaufgabe_id"])
        klient.post("/api/uebungen/lernen/bewerten", json={
            "benutzer_id": b["id"], "textaufgabe_id": a["textaufgabe_id"],
            "bewertung": 1})

    assert len(folge) == 8, f"Abfrage brach ab: {folge}"
    doppelt = sum(1 for i in range(1, len(folge)) if folge[i] == folge[i - 1])
    assert doppelt == 0, f"{doppelt} Wiederholungen hintereinander: {folge}"
    assert len(set(folge)) >= 3, f"nur {len(set(folge))} Sätze: {folge}"


def test_ausgesetzte_uebung_kommt_nicht_als_neu_zurueck(bestand, klient):
    """Wer schon gelernt hat, ist nicht wieder neu — sonst zählt die
    Übung gegen den Tagesvorrat an Neuem und FSRS rechnet daneben."""
    b, s = bestand
    a = klient.get("/api/uebungen/lernen/naechste", params={
        "benutzer_id": b["id"], "sammlung_id": s["id"], "anzahl": 1}).json()[0]
    kennung = a["textaufgabe_id"]
    klient.post("/api/uebungen/lernen/bewerten", json={
        "benutzer_id": b["id"], "textaufgabe_id": kennung, "bewertung": 4})

    # Es gibt dafür (noch) keinen Endpunkt — der erste Entwurf dieses
    # Tests rief einen an, der nicht existiert, und prüfte damit nichts.
    import datenbank as dbm
    import uebung_lernen
    db = dbm.verbindung()
    try:
        uebung_lernen.aussetzen(db, b["id"], kennung, True)
        uebung_lernen.aussetzen(db, b["id"], kennung, False)
        z = dbm.zeile(db, """SELECT zustand, stabilitaet FROM textlernzustand
                              WHERE textaufgabe_id = ? AND benutzer_id = ?""",
                      (kennung, b["id"]))
    finally:
        db.close()
    assert z["stabilitaet"] is not None
    assert z["zustand"] != "neu", (
        f"war schon gelernt (S={z['stabilitaet']:.1f}), gilt aber als neu")
