"""Vokabeln und Übungen müssen denselben Lernstand rechnen.

Der Einwand, der diese Datei gebracht hat: »das ist doch genau der Fall,
wo Code doppelt gepflegt werden muss, den ich gerne abschaffen möchte.«

Sie hatte recht, und die Durchsicht hatte es auch gefunden —
»uebung_lernen ist ein zweiter Lernkern und läuft schon auseinander«.
Ich habe es liegen lassen und stattdessen an einem Tag dreimal dasselbe
einzeln repariert:

  - `aussetzen(…, False)` setzte bei den Übungen stumpf »neu«, obwohl
    eine Stabilität dastand,
  - das Abstandhalten nach »Nochmal« fehlte dort,
  - die Runde »erst jedes Wort einmal« ebenso.

Jetzt rechnet beides über `lernkern`. Diese Tests prüfen nicht, DASS es
ein gemeinsames Modul gibt — das wäre eine Prüfung der Form —, sondern
dass beide Wege bei gleicher Vorgeschichte dasselbe ergeben. Liefe eines
der beiden wieder eigene Wege, fiele es hier auf.
"""

import sys

import pytest

sys.path.insert(0, "backend")

import fsrs
import lernkern


BEIDE = [lernkern.VOKABELN, lernkern.UEBUNGEN]


@pytest.fixture()
def bestand(klient):
    """Ein Wort und ein Satz, beide freigegeben und gleich alt."""
    b = klient.post("/api/benutzer", json={"name": "Übende"}).json()
    s = klient.post("/api/sammlungen", json={
        "besitzer_id": b["id"], "name": "S", "sprache": "el"}).json()
    klient.post(f"/api/sammlungen/{s['id']}/import/vokabeln", json={
        "eintraege": [{"lemma": "γράφω", "wortart": "verb", "lektion_nr": 1,
                       "bedeutungen": [{"uebersetzungen": ["schreiben"]}]}]})
    u = klient.post(f"/api/sammlungen/{s['id']}/uebungen", json={
        "typ": "satz", "zielsprache": "Γράφω.", "grundsprache": "Ich schreibe.",
        "lektion_nr": 1}).json()
    klient.post(f"/api/uebungen/{u['id']}/freigabe")
    klient.post(f"/api/sammlungen/{s['id']}/freigabe", json={"lektion_nr": 1})

    import datenbank as dbm
    db = dbm.verbindung()
    try:
        aufgabe = dbm.wert(db, "SELECT id FROM aufgabe LIMIT 1")
        textaufgabe = dbm.wert(db, "SELECT id FROM textaufgabe LIMIT 1")
    finally:
        db.close()
    return b["id"], {lernkern.VOKABELN: aufgabe, lernkern.UEBUNGEN: textaufgabe}


def _zustand(db, t, kennung, benutzer_id):
    import datenbank as dbm
    return dbm.zeile(db, f"""SELECT * FROM {t.zustand}
                              WHERE {t.kennung} = ? AND benutzer_id = ?""",
                     (kennung, benutzer_id))


def test_dieselbe_bewertung_ergibt_denselben_lernstand(bestand):
    """Der Kern der Sache: gleiche Eingabe, gleiche Rechnung."""
    import datenbank as dbm
    benutzer, kennungen = bestand
    db = dbm.verbindung()
    try:
        ergebnisse = []
        for t in BEIDE:
            ergebnisse.append(lernkern.fortschreiben(
                db, t, kennungen[t], benutzer, 3, 0.9, {}))
        a, b = ergebnisse
        # Die Saat ist die Kennung, die Streuung darf also abweichen —
        # alles andere nicht.
        assert a["zustand"] == b["zustand"]
        assert abs(a["stabilitaet"] - b["stabilitaet"]) < 1e-9
        assert abs(a["schwierigkeit"] - b["schwierigkeit"]) < 1e-9
    finally:
        db.close()


def test_aussetzen_und_zuruecknehmen_wirken_gleich(bestand):
    """Hier lief es auseinander: bei den Übungen wurde aus einem
    gelernten Eintrag beim Zurücknehmen wieder ein »neuer«."""
    import datenbank as dbm
    benutzer, kennungen = bestand
    db = dbm.verbindung()
    try:
        for t in BEIDE:
            lernkern.fortschreiben(db, t, kennungen[t], benutzer, 4, 0.9, {})
            lernkern.aussetzen(db, t, kennungen[t], benutzer, True)
            assert _zustand(db, t, kennungen[t], benutzer)["zustand"] \
                == "ausgesetzt"
            lernkern.aussetzen(db, t, kennungen[t], benutzer, False)
            z = _zustand(db, t, kennungen[t], benutzer)
            assert z["stabilitaet"] is not None
            assert z["zustand"] == "lernen", (
                f"{t.zustand}: war schon gelernt, gilt aber als {z['zustand']}")
    finally:
        db.close()


def test_zuruecksetzen_wirkt_gleich(bestand):
    import datenbank as dbm
    benutzer, kennungen = bestand
    db = dbm.verbindung()
    try:
        for t in BEIDE:
            lernkern.fortschreiben(db, t, kennungen[t], benutzer, 4, 0.9, {})
            lernkern.zuruecksetzen(db, t, kennungen[t], benutzer)
            z = _zustand(db, t, kennungen[t], benutzer)
            assert (z["zustand"], z["stabilitaet"], z["anzahl"]) \
                == ("neu", None, 0), t.zustand
            # Das Protokoll bleibt — es trägt die spätere Optimierung.
            uebrig = dbm.wert(db, f"""SELECT COUNT(*) FROM {t.protokoll}
                                       WHERE {t.kennung} = ?""",
                              (kennungen[t],))
            assert uebrig >= 1, t.protokoll
    finally:
        db.close()


def test_zustand_und_protokoll_gehen_zusammen_hinaus(bestand):
    """Beides in EINER Transaktion. Vorher waren es zwei Schreibvorgänge
    im Autocommit: scheiterte der zweite, stand der Lernstand
    fortgeschrieben da und der Protokolleintrag fehlte — und daran
    hängen die Tagesgrenze, der Wortvorrat und die FSRS-Parameter."""
    import datenbank as dbm
    benutzer, kennungen = bestand
    db = dbm.verbindung()
    try:
        t = lernkern.VOKABELN
        # Ein Feld, das es im Protokoll nicht gibt: der INSERT scheitert.
        with pytest.raises(Exception):
            lernkern.fortschreiben(db, t, kennungen[t], benutzer, 3, 0.9,
                                   {"gibtsnicht": 1})
        z = _zustand(db, t, kennungen[t], benutzer)
        assert z is None or z["anzahl"] == 0, (
            "der Lernstand wurde fortgeschrieben, obwohl das Protokoll "
            "scheiterte")
    finally:
        db.close()


def test_beide_tabellenpaare_sind_wirklich_deckungsgleich(klient):
    """Das Schema sagt »absichtlich deckungsgleich«. Wenn das einmal
    nicht mehr stimmt, kann der gemeinsame Kern nicht mehr beides —
    und dann soll es hier auffallen und nicht im Betrieb."""
    import datenbank as dbm
    db = dbm.verbindung()
    try:
        for feld, a, b in (("zustand", lernkern.VOKABELN.zustand,
                            lernkern.UEBUNGEN.zustand),
                           ("protokoll", lernkern.VOKABELN.protokoll,
                            lernkern.UEBUNGEN.protokoll)):
            sa = dbm.spalten(db, a) - {lernkern.VOKABELN.kennung}
            sb = dbm.spalten(db, b) - {lernkern.UEBUNGEN.kennung}
            fehlt = sa - sb
            assert not fehlt, f"{b} fehlen gegenüber {a}: {sorted(fehlt)}"
    finally:
        db.close()


def test_alle_module_fragen_dieselbe_uhr(monkeypatch):
    """`lernziele` hatte eine eigene `_heute()` mit `dt.date.today()`.

    Wer die Uhr für einen Test vorstellt, stellte damit nur die eine —
    die Lernzielrechnung blieb im echten Heute stehen, und zwei Module
    waren verschiedener Meinung darüber, welcher Tag ist.
    """
    import datetime as dt
    import lernen, lernziele, lernkern
    spaeter = dt.date.today() + dt.timedelta(days=30)
    monkeypatch.setattr(lernen, "heute", lambda: spaeter)
    assert lernziele._heute() == spaeter
    assert lernkern.heute() == spaeter


def test_ein_fehlender_termin_gilt_nirgends_als_faellig():
    """In SQL ist `faellig <= heute` für NULL unwahr. In Python stand
    `(r["faellig"] or "") <= heute` — und das ist für NULL WAHR. Damit
    waren Lernzielblock und Abfrage verschiedener Meinung darüber, was
    heute dran ist."""
    import pathlib
    quelle = (pathlib.Path(__file__).resolve().parents[1]
              / "backend" / "lernziele.py").read_text()
    assert '(r["faellig"] or "")' not in quelle
