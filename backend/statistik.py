"""Der eigene Lernfortschritt, aus dem Protokoll gerechnet.

»Und eine Statistik zu meinem Lernfortschritt, das braucht es natürlich
auch.«

Die Randbedingung, die den Zuschnitt bestimmt: sie muss nach ZWEI
Tagen etwas sagen. Beim Schreiben standen 108 Antworten an zwei Tagen
im Protokoll. Eine Statistik, die erst nach einem halben Jahr etwas
hergibt, sieht man sich einmal an und nie wieder — und bis dahin weiß
niemand, ob sie überhaupt stimmt.

Darum keine Jahresverläufe und keine gleitenden Mittel über Wochen.
Stattdessen vier Fragen, die sich auch mit wenig Daten beantworten
lassen:

  Wie viel habe ich getan?      Antworten je Tag, nach Urteil getrennt
  Wie gut lief es?              Trefferquote, und ob sie sich bewegt
  Wo steht mein Wortschatz?     neu / am Lernen / sitzt / verlernt
  Was kommt auf mich zu?        Fälligkeiten der nächsten Wochen

Die letzte halte ich für die nützlichste und habe sie nirgends sonst
gesehen: sie beantwortet »wie viel Arbeit habe ich mir eingehandelt«,
und zwar bevor die Arbeit da ist.

Alles wird aus `wiederholung` und `lernzustand` gerechnet, nichts
zusätzlich mitgeschrieben. Eine Statistik, für die man erst Daten
sammeln müsste, fängt bei null an; diese kennt die Vergangenheit.
"""

from __future__ import annotations

import datetime as dt
import sqlite3

import datenbank as dbm


# Wie weit zurück und wie weit voraus. Ein Monat ist der Bogen, den man
# noch im Kopf hat; ein Jahr wäre eine Tapete.
TAGE_ZURUECK = 30
TAGE_VORAUS = 30


def _heute() -> dt.date:
    # Über `lernen` importiert, damit Tests, die dort die Uhr
    # vorstellen, auch hier wirken — dieselbe Regel wie im Lernkern.
    import lernen
    return lernen.heute()


def _topf(db: sqlite3.Connection, benutzer_id: int,
          sammlung_id: int | None) -> tuple[str, tuple]:
    """Welche Aufgaben zählen — DERSELBE Topf wie in der Übersicht.

    Erster Entwurf zählte einfach alle aktiven Aufgaben: 11351 statt
    der 7389, die die Übersicht nennt. Darin lagen fremde Sammlungen,
    die nur zum Mitpflegen freigegeben sind, und Zeitformen, die die
    Lektionsschranke zurückhält. Zwei verschiedene Zahlen für
    dasselbe im selben Werkzeug sind schlimmer als eine unbequeme:
    man weiß dann bei keiner mehr, was sie bedeutet.

    Verlangt eine Abfrage über `aufgabe a` und `lexem l`.
    """
    import lernen as lernmodul
    sammlungen = ([sammlung_id] if sammlung_id
                  else lernmodul.lernsammlungen(db, benutzer_id))
    if not sammlungen:
        return " AND 0", ()
    platzhalter = ",".join("?" * len(sammlungen))
    bedingung = (f" AND l.sammlung_id IN ({platzhalter})"
                 f" AND {lernmodul.LEKTIONSSCHRANKE_SQL}")
    return bedingung, (*sammlungen, benutzer_id)


def taetigkeit(db: sqlite3.Connection, benutzer_id: int,
               sammlung_id: int | None = None) -> list[dict]:
    """Antworten je Tag, nach Urteil getrennt.

    Lückenlos: Tage ohne Antwort stehen mit Null da. Ohne sie zöge ein
    Balkenbild die Pausen zusammen, und drei Tage Arbeit mit einer
    Woche Pause dazwischen sähen aus wie drei Tage am Stück.
    """
    zusatz, werte = _topf(db, benutzer_id, sammlung_id)
    ab = (_heute() - dt.timedelta(days=TAGE_ZURUECK - 1)).isoformat()
    roh = {z["tag"]: z for z in dbm.zeilen(db, f"""
        SELECT substr(w.zeitpunkt, 1, 10) AS tag,
               COUNT(*) AS gesamt,
               SUM(w.urteil = 'richtig') AS richtig,
               SUM(w.urteil = 'fast') AS fast,
               SUM(w.urteil IN ('falsch', 'aufgedeckt')) AS falsch
          FROM wiederholung w
          JOIN aufgabe a ON a.id = w.aufgabe_id
          JOIN lexem l ON l.id = a.lexem_id
         WHERE w.benutzer_id = ? AND w.zeitpunkt >= ?{zusatz}
         GROUP BY tag""", (benutzer_id, ab, *werte))}

    tage = []
    for i in range(TAGE_ZURUECK):
        tag = (_heute() - dt.timedelta(days=TAGE_ZURUECK - 1 - i)).isoformat()
        z = roh.get(tag)
        tage.append({"tag": tag,
                     "gesamt": z["gesamt"] if z else 0,
                     "richtig": (z["richtig"] or 0) if z else 0,
                     "fast": (z["fast"] or 0) if z else 0,
                     "falsch": (z["falsch"] or 0) if z else 0})
    return tage


def vorschau(db: sqlite3.Connection, benutzer_id: int,
             sammlung_id: int | None = None) -> list[dict]:
    """Was in den nächsten Wochen fällig wird.

    »Überfällig« kommt als erster Eintrag, nicht als Balken in der
    Vergangenheit: es ist keine Vorhersage, sondern Rückstand, und es
    kommt heute dran.
    """
    zusatz, werte = _topf(db, benutzer_id, sammlung_id)
    heute = _heute()
    bis = (heute + dt.timedelta(days=TAGE_VORAUS)).isoformat()
    roh = {z["faellig"]: z["n"] for z in dbm.zeilen(db, f"""
        SELECT z.faellig, COUNT(*) AS n
          FROM lernzustand z
          JOIN aufgabe a ON a.id = z.aufgabe_id
          JOIN lexem l ON l.id = a.lexem_id
         WHERE z.benutzer_id = ? AND a.aktiv = 1
           AND z.faellig IS NOT NULL AND z.faellig <= ?
           AND z.zustand != 'ausgesetzt'{zusatz}
         GROUP BY z.faellig""", (benutzer_id, bis, *werte))}

    ueberfaellig = sum(n for tag, n in roh.items() if tag < heute.isoformat())
    reihe = [{"tag": None, "beschriftung": "überfällig", "n": ueberfaellig}]
    for i in range(TAGE_VORAUS + 1):
        tag = (heute + dt.timedelta(days=i)).isoformat()
        reihe.append({"tag": tag,
                      "beschriftung": "heute" if i == 0 else tag[5:],
                      "n": roh.get(tag, 0)})
    return reihe


def wortschatz(db: sqlite3.Connection, benutzer_id: int,
               sammlung_id: int | None = None) -> dict:
    """Wo steht der Bestand — gezählt in AUFGABEN, wie überall sonst.

    Nicht in Wörtern: ein Verb mit vierzig Formen wäre dann ein
    Eintrag wie »heute«, und die Zahl hätte mit der Arbeit nichts mehr
    zu tun. Die Übersicht zählt ebenso; zwei verschiedene Zählweisen
    im selben Werkzeug wären schlimmer als eine ungewohnte.
    """
    zusatz, werte = _topf(db, benutzer_id, sammlung_id)
    zahlen = {"neu": 0, "lernen": 0, "reif": 0, "verlernt": 0,
              "ausgesetzt": 0}
    for z in dbm.zeilen(db, f"""
            SELECT COALESCE(z.zustand, 'neu') AS zustand, COUNT(*) AS n
              FROM aufgabe a
              JOIN lexem l ON l.id = a.lexem_id
              LEFT JOIN lernzustand z
                     ON z.aufgabe_id = a.id AND z.benutzer_id = ?
             WHERE a.aktiv = 1{zusatz}
             GROUP BY COALESCE(z.zustand, 'neu')""",
            (benutzer_id, *werte)):
        zahlen[z["zustand"]] = z["n"]
    return zahlen


def tempo(db: sqlite3.Connection, benutzer_id: int,
          sammlung_id: int | None = None) -> list[dict]:
    """Wie lange bis zur Antwort, je Aufgabenart — der Median.

    Der Median, nicht der Mittelwert: eine Antwort nach 103 Sekunden
    (das Telefon klingelt) zieht jeden Mittelwert in den Unsinn. Aus
    demselben Grund steht hier dieselbe Spanne wie bei der Bewertung.
    """
    import bewertung
    zusatz, werte = _topf(db, benutzer_id, sammlung_id)
    reihe = []
    for z in dbm.zeilen(db, f"""
            SELECT a.typ, COUNT(*) AS n
              FROM wiederholung w
              JOIN aufgabe a ON a.id = w.aufgabe_id
              JOIN lexem l ON l.id = a.lexem_id
             WHERE w.benutzer_id = ?
               AND w.denkzeit_ms BETWEEN ? AND ?{zusatz}
             GROUP BY a.typ ORDER BY n DESC""",
            (benutzer_id, bewertung.MESSUNG_MIN_MS,
             bewertung.MESSUNG_MAX_MS, *werte)):
        zeiten = [x["denkzeit_ms"] for x in dbm.zeilen(db, f"""
            SELECT w.denkzeit_ms FROM wiederholung w
              JOIN aufgabe a ON a.id = w.aufgabe_id
              JOIN lexem l ON l.id = a.lexem_id
             WHERE w.benutzer_id = ? AND a.typ = ?
               AND w.denkzeit_ms BETWEEN ? AND ?{zusatz}
             ORDER BY w.denkzeit_ms""",
            (benutzer_id, z["typ"], bewertung.MESSUNG_MIN_MS,
             bewertung.MESSUNG_MAX_MS, *werte))]
        if not zeiten:
            continue
        reihe.append({"typ": z["typ"], "anzahl": len(zeiten),
                      "median_ms": zeiten[len(zeiten) // 2]})
    return reihe


def alles(db: sqlite3.Connection, benutzer_id: int,
          sammlung_id: int | None = None) -> dict:
    """Ein Aufruf für die ganze Seite.

    Fünf Rundläufe für fünf Kacheln wären fünf Gelegenheiten, dass
    eine fehlt und die Seite halb dasteht.
    """
    tage = taetigkeit(db, benutzer_id, sammlung_id)
    gesamt = sum(t["gesamt"] for t in tage)
    richtig = sum(t["richtig"] for t in tage)
    fast = sum(t["fast"] for t in tage)
    aktive_tage = sum(1 for t in tage if t["gesamt"])

    # Die Strähne kommt aus `spiel` und wird hier NICHT noch einmal
    # gerechnet. Sie stand früher an dieser Stelle und zählte Tage mit
    # mindestens einer Antwort innerhalb des Monatsfensters — damit
    # genügte eine einzige Karte für einen gelernten Tag, und über 30
    # konnte die Zahl nie hinaus. Dieselbe Zahl zweimal verschieden zu
    # rechnen wäre der schlimmere Fehler: in der Kopfzeile stünde
    # »Strähne 12« und im Fortschritt »Strähne 30«, und man wüsste bei
    # keiner mehr, was sie bedeutet.
    #
    # Sie gilt für die PERSON, auch wenn diese Seite auf eine Sammlung
    # eingeschränkt ist — so wie die Tagesdosis, an der sie hängt.
    import spiel
    folge = spiel.straehne(db, benutzer_id)

    return {
        "taetigkeit": tage,
        "vorschau": vorschau(db, benutzer_id, sammlung_id),
        "wortschatz": wortschatz(db, benutzer_id, sammlung_id),
        "tempo": tempo(db, benutzer_id, sammlung_id),
        "gesamt": {
            "antworten": gesamt,
            "richtig": richtig,
            "fast": fast,
            # Ohne Antworten keine Quote. 0 % wäre gelogen.
            "quote": round(100 * richtig / gesamt) if gesamt else None,
            "aktive_tage": aktive_tage,
            "straehne": folge["laufend"],
            "straehne_laengste": folge["laengste"],
            "straehne_ziel": folge["ziel"],
            "straehne_joker": folge["joker_benutzt"],
            "tage_betrachtet": TAGE_ZURUECK,
        },
    }
