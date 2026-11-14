# Vokabeltrainer — Copyright (C) 2026 Annuschka Brenner
#
# Freie Software unter der GNU Affero General Public License, Fassung 3
# oder später. Herausgegeben in der Hoffnung, dass sie nützt, aber OHNE
# JEDE GEWÄHRLEISTUNG. Siehe die Datei LICENSE.
"""Der Lernstand — einmal, für Vokabeln UND Übungen.

Es gab diese Rechnung zweimal: `lernen.py` für die Wörter,
`uebung_lernen.py` für die Sätze. Die beiden Tabellenpaare sind laut
Schema »absichtlich deckungsgleich«, der Code nutzte das nur nicht —
und lief auseinander. An einem einzigen Tag kostete das drei Fehler:

- `aussetzen(…, False)` setzte bei den Übungen stumpf »neu«, auch wenn
  eine Stabilität dastand. Der Satz zählte danach wieder gegen den
  Tagesvorrat an Neuem, während FSRS mit S=15,7 weiterrechnete. Bei den
  Vokabeln stand dieselbe Zeile seit je richtig.
- Das Abstandhalten gegen »nach Nochmal sofort wieder dasselbe« gab es
  bei den Vokabeln, bei den Übungen nicht.
- Die Runde (erst jedes Wort einmal) ebenso.

Jedes Mal wurde einzeln repariert. Darum steht die Rechnung jetzt hier,
einmal, und die beiden Module geben nur ihre Tabellennamen mit.

**Was hier NICHT hingehört:** die Auswahl, welche Aufgabe als nächste
kommt. Die ist bei Wörtern und Sätzen wirklich verschieden — ein Wort
hat ein Paradigma und eine Formgruppe, ein Satz hat Richtungen. Was
gleich ist, ist der Gedächtniszustand und sein Fortschreiben.
"""

from __future__ import annotations

import datetime as dt
import sqlite3
from dataclasses import dataclass

import datenbank as dbm
import fsrs


@dataclass(frozen=True)
class Tabellen:
    """Welches Tabellenpaar gemeint ist.

    `gruppe` ist das, worüber die Runde zählt: bei Vokabeln das Lexem
    (ein Verbstamm ist EIN Wort, auch mit vierzig Formen), bei Übungen
    der Text (hin und zurück sind derselbe Satz).
    """
    zustand: str              # lernzustand | textlernzustand
    protokoll: str            # wiederholung | textbearbeitung
    kennung: str              # aufgabe_id | textaufgabe_id
    gruppe_sql: str           # wie man von der Aufgabe zur Gruppe kommt


VOKABELN = Tabellen(
    zustand="lernzustand", protokoll="wiederholung", kennung="aufgabe_id",
    gruppe_sql="""SELECT a.lexem_id AS gruppe, p.id AS protokoll_id,
                         p.zeitpunkt
                    FROM {protokoll} p
                    JOIN aufgabe a ON a.id = p.aufgabe_id""")

UEBUNGEN = Tabellen(
    zustand="textlernzustand", protokoll="textbearbeitung",
    kennung="textaufgabe_id",
    gruppe_sql="""SELECT x.text_id AS gruppe, p.id AS protokoll_id,
                         p.zeitpunkt
                    FROM {protokoll} p
                    JOIN textaufgabe x ON x.id = p.textaufgabe_id""")


# Die Uhr steht weiterhin in lernen.py — spät eingebunden, weil jenes
# Modul dieses hier benutzt. Das ist kein Schönheitsfehler, sondern
# Absicht: die Tests stellen die Uhr über `lernen.heute` (»zwei Wochen
# später«), und das muss auch für diesen Kern gelten. Gäbe es hier eine
# zweite Uhr, hätte man genau wieder zwei Wahrheiten — der Fehler, den
# dieses Modul abschafft.
def jetzt() -> str:
    import lernen
    return lernen._jetzt()


def heute() -> dt.date:
    import lernen
    return lernen.heute()


def tage_seit(zeitpunkt: str | None) -> float:
    if not zeitpunkt:
        return 0.0
    try:
        davor = dt.datetime.fromisoformat(zeitpunkt)
    except ValueError:
        return 0.0
    return max(0.0, (dt.datetime.now() - davor).total_seconds() / 86400.0)


def selber_tag(zeitpunkt: str | None,
               bezug: dt.datetime | None = None) -> bool:
    """Kam die vorige Antwort am selben KALENDERTAG?

    FSRS entschied das nach exakten 24 Stunden, der Terminplan rechnet
    aber in Kalendertagen. Wer abends um 20 Uhr lernt und morgens um 9
    weitermacht, ist für den Plan einen Tag weiter — zwölf Minuten
    entschieden über Faktor drei in der Stabilität.
    """
    if not zeitpunkt:
        return False
    try:
        davor = dt.datetime.fromisoformat(zeitpunkt)
    except ValueError:
        return False
    return davor.date() == (bezug or dt.datetime.now()).date()


def zustand_sichern(db: sqlite3.Connection, t: Tabellen, kennung: int,
                    benutzer_id: int) -> dict:
    """Legt den Lernzustand an, falls er noch fehlt."""
    hole = (f"SELECT * FROM {t.zustand} "
            f"WHERE {t.kennung} = ? AND benutzer_id = ?")
    z = dbm.zeile(db, hole, (kennung, benutzer_id))
    if z is None:
        db.execute(f"""INSERT INTO {t.zustand} ({t.kennung}, benutzer_id,
                                                zustand)
                       VALUES (?, ?, 'neu')""", (kennung, benutzer_id))
        z = dbm.zeile(db, hole, (kennung, benutzer_id))
    return z


def rundenstand(db: sqlite3.Connection, t: Tabellen,
                benutzer_id: int) -> dict[int, int]:
    """Wie oft jede Gruppe heute schon dran war.

    Grundlage der Regel »erst jedes Wort einmal, dann das zweite Mal«.
    """
    morgen = (heute() + dt.timedelta(days=1)).isoformat()
    quelle = t.gruppe_sql.format(protokoll=t.protokoll)
    return {z["gruppe"]: z["n"] for z in dbm.zeilen(db, f"""
        SELECT gruppe, COUNT(*) AS n FROM ({quelle})
         WHERE zeitpunkt >= ? AND zeitpunkt < ?
           AND protokoll_id IN (SELECT id FROM {t.protokoll}
                                 WHERE benutzer_id = ?)
         GROUP BY gruppe""", (heute().isoformat(), morgen, benutzer_id))}


def zuletzt_gefragt(db: sqlite3.Connection, t: Tabellen, benutzer_id: int,
                    anzahl: int = 2) -> list[int]:
    """Die zuletzt bearbeiteten Gruppen.

    Nach der Protokollnummer, nicht nach dem Zeitstempel: der hat
    Sekundenauflösung, und wer zügig antwortet, erzeugt lauter gleiche
    Werte — dann ist »zuletzt« nicht entscheidbar.
    """
    quelle = t.gruppe_sql.format(protokoll=t.protokoll)
    return [z["gruppe"] for z in dbm.zeilen(db, f"""
        SELECT gruppe, MAX(protokoll_id) AS zuletzt FROM ({quelle})
         WHERE protokoll_id IN (SELECT id FROM {t.protokoll}
                                 WHERE benutzer_id = ?)
         GROUP BY gruppe
         ORDER BY zuletzt DESC
         LIMIT ?""", (benutzer_id, anzahl))]


def runden_sql(stand: dict[int, int], spalte: str) -> str:
    """Die Runde als Sortierausdruck für die Abfrage.

    Nachträglich zu sortieren genügt nicht: das Abrufen holt nur ein
    kleines Fenster, und darin stehen während einer Sitzung überwiegend
    schon gesehene Einträge.

    Gibt einen LEEREN Ausdruck zurück, wenn nichts zu ordnen ist — eine
    nackte »0« im ORDER BY ist in SQLite eine Spaltennummer, kein Wert.
    """
    teile = " ".join(f"WHEN {int(g)} THEN {int(n)}"
                     for g, n in (stand or {}).items() if g is not None)
    return f"CASE {spalte} {teile} ELSE 0 END" if teile else ""


def rundenweise(reihe: list[dict], stand: dict[int, int],
                feld: str) -> list[dict]:
    """Erst jede Gruppe einmal, dann die zweite Runde.

    Stabil sortiert: innerhalb einer Runde bleibt die bestehende
    Reihenfolge, die Dringlichkeit ordnet also weiter — nur nicht mehr
    über die Runde hinweg.
    """
    return sorted(reihe, key=lambda r: stand.get(r.get(feld), 0))


def abstand_halten(reihe: list[dict], meiden: list[int], anzahl: int,
                   feld: str) -> list[dict]:
    """Stellt die zuletzt Gefragten hintan — solange es Auswahl gibt."""
    if not meiden:
        return reihe
    frisch = [r for r in reihe if r.get(feld) not in meiden]
    spaeter = [r for r in reihe if r.get(feld) in meiden]
    return (frisch + spaeter) if len(frisch) >= min(anzahl, 1) else reihe


def fortschreiben(db: sqlite3.Connection, t: Tabellen, kennung: int,
                  benutzer_id: int, bewertung: int, wunschretention: float,
                  protokoll_felder: dict) -> dict:
    """Rechnet den neuen Gedächtniszustand und schreibt ihn fort.

    Zustand und Protokoll gehen in EINER Transaktion hinaus. Vorher
    waren es zwei Schreibvorgänge im Autocommit: scheiterte der zweite
    (SQLITE_BUSY, volle Platte), stand der Lernstand fortgeschrieben da
    und der Protokolleintrag fehlte — und an dem hängen die Tagesgrenze,
    der Wortvorrat und die späteren FSRS-Parameter.
    """
    if bewertung not in fsrs.BEWERTUNGEN:
        raise ValueError("Bewertung muss 1 bis 4 sein")
    z = zustand_sichern(db, t, kennung, benutzer_id)
    vorher = fsrs.Zustand(z["stabilitaet"], z["schwierigkeit"])
    verstrichen = tage_seit(z["letzte_wiederholung"])
    ergebnis = fsrs.bewerten(vorher, bewertung, verstrichen, wunschretention,
                             saat=kennung,
                             selber_tag=selber_tag(z["letzte_wiederholung"]))
    faellig = (heute().isoformat() if bewertung == fsrs.NOCHMAL
               else (heute() + dt.timedelta(
                   days=round(ergebnis.intervall_tage))).isoformat())

    felder = {
        t.kennung: kennung, "benutzer_id": benutzer_id, "zeitpunkt": jetzt(),
        "bewertung": bewertung,
        "stabilitaet_vor": vorher.stabilitaet,
        "stabilitaet_nach": ergebnis.stabilitaet,
        "schwierigkeit_vor": vorher.schwierigkeit,
        "schwierigkeit_nach": ergebnis.schwierigkeit,
        "intervall_tage": ergebnis.intervall_tage,
        "verstrichen_tage": round(verstrichen, 4),
        **protokoll_felder,
    }
    namen = ", ".join(felder)
    platz = ", ".join("?" * len(felder))

    db.execute("BEGIN")
    try:
        db.execute(f"""UPDATE {t.zustand}
                         SET zustand = ?, stabilitaet = ?, schwierigkeit = ?,
                             letzte_wiederholung = ?, faellig = ?,
                             anzahl = anzahl + 1,
                             anzahl_fehler = anzahl_fehler + ?
                       WHERE {t.kennung} = ? AND benutzer_id = ?""",
                   (ergebnis.zustand, ergebnis.stabilitaet,
                    ergebnis.schwierigkeit, jetzt(), faellig,
                    1 if bewertung == fsrs.NOCHMAL else 0,
                    kennung, benutzer_id))
        db.execute(f"INSERT INTO {t.protokoll} ({namen}) VALUES ({platz})",
                   tuple(felder.values()))
        db.execute("COMMIT")
    except Exception:
        db.execute("ROLLBACK")
        raise

    return {
        "bewertung": bewertung,
        "zustand": ergebnis.zustand,
        "stabilitaet": ergebnis.stabilitaet,
        "schwierigkeit": ergebnis.schwierigkeit,
        "intervall_tage": ergebnis.intervall_tage,
        "faellig": faellig,
        "termin_text": fsrs.tage_in_text(ergebnis.intervall_tage),
    }


def aussetzen(db: sqlite3.Connection, t: Tabellen, kennung: int,
              benutzer_id: int, aussetzen_: bool = True) -> None:
    """Aus der Abfrage nehmen — und wieder hinein.

    Beim Zurücknehmen NICHT stumpf »neu«: wer schon geübt hat, hat eine
    Stabilität, und die rechnet FSRS weiter. Als »neu« zählte der
    Eintrag gegen den Tagesvorrat an Neuem und würde noch einmal
    eingeführt. Bei den Übungen stand hier bis heute die stumpfe
    Fassung — genau der Schaden, den ein zweiter Lernkern anrichtet.
    """
    zustand_sichern(db, t, kennung, benutzer_id)
    if aussetzen_:
        db.execute(f"""UPDATE {t.zustand} SET zustand = 'ausgesetzt'
                        WHERE {t.kennung} = ? AND benutzer_id = ?""",
                   (kennung, benutzer_id))
        return
    db.execute(f"""UPDATE {t.zustand}
                     SET zustand = CASE WHEN stabilitaet IS NULL
                                        THEN 'neu' ELSE 'lernen' END
                   WHERE {t.kennung} = ? AND benutzer_id = ?""",
               (kennung, benutzer_id))


def zuruecksetzen(db: sqlite3.Connection, t: Tabellen, kennung: int,
                  benutzer_id: int) -> None:
    """Von vorn: Gedächtniszustand weg, Protokoll bleibt.

    Das Protokoll bleibt mit Absicht — es ist die Grundlage für die
    spätere Optimierung der FSRS-Parameter und wird nie geleert.
    """
    zustand_sichern(db, t, kennung, benutzer_id)
    db.execute(f"""UPDATE {t.zustand}
                     SET zustand = 'neu', stabilitaet = NULL,
                         schwierigkeit = NULL, letzte_wiederholung = NULL,
                         faellig = NULL, anzahl = 0, anzahl_fehler = 0
                   WHERE {t.kennung} = ? AND benutzer_id = ?""",
               (kennung, benutzer_id))
