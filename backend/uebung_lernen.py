"""Übungssätze und Texte abfragen.

Dieselbe Rechnung wie bei den Vokabeln — FSRS, Wiedervorlage, sichtbare
Stabilität — aber an drei Stellen bewusst anders:

**Keine Zeitmessung.** Bei einer Vokabel ist die Zeit bis zum ersten
Tastendruck das Abrufmaß: entweder das Wort ist da oder nicht. Bei einem
Satz ist sie Lesezeit, und die Gesamtzeit ist zum größten Teil Tippzeit.
Beides sagt über das Können nichts. Bewertet wird darum allein nach der
Richtigkeit.

**Zwei Richtungen, zwei Lernstände.** »Χθες πήγα στο θέατρο« ins Deutsche
zu bringen ist leicht, wenn man die Wörter kennt; umgekehrt muss man sie
bilden können. Das sind zwei Fähigkeiten und darum zwei Aufgaben.

**Beim langen Text entscheidet der Mensch.** Der Vergleich läuft trotzdem
und wird gezeigt — er hilft beim Einschätzen. Aber eine freie Übersetzung
eines Absatzes stimmt selten wörtlich mit der Referenz überein, und ein
Trainer, der sie deshalb als falsch wertet, erzieht zum Auswendiglernen
der Musterlösung.

Abgefragt wird nur, was **freigegeben** ist — wie bei den Formen.
"""

from __future__ import annotations

import datetime as dt
import sqlite3

import bewertung as bewertungsmodul
import datenbank as dbm
import fsrs
import lernen as lernmodul
import satzpruefung
import sprachen
import uebungen


class UebungFehler(ValueError):
    pass


RICHTUNGSTEXT = {
    "uebersetzung_hin": "In die Grundsprache übersetzen",
    "uebersetzung_rueck": "In die Lernsprache übersetzen",
}


def _zustand_sichern(db: sqlite3.Connection, textaufgabe_id: int,
                     benutzer_id: int) -> dict:
    z = dbm.zeile(db, """SELECT * FROM textlernzustand
                          WHERE textaufgabe_id = ? AND benutzer_id = ?""",
                  (textaufgabe_id, benutzer_id))
    if z is None:
        db.execute("""INSERT INTO textlernzustand (textaufgabe_id, benutzer_id)
                      VALUES (?, ?)""", (textaufgabe_id, benutzer_id))
        z = dbm.zeile(db, """SELECT * FROM textlernzustand
                              WHERE textaufgabe_id = ? AND benutzer_id = ?""",
                      (textaufgabe_id, benutzer_id))
    return z


def _sprachen(db: sqlite3.Connection, a: dict) -> tuple[str, str]:
    """(Sprache der Frage, Sprache der Antwort)."""
    s = dbm.zeile(db, "SELECT * FROM sammlung WHERE id = ?", (a["sammlung_id"],))
    if a["typ"] == "uebersetzung_hin":
        return a["sprache"], s["grundsprache"]
    return s["grundsprache"], a["sprache"]


def _aufgabe(db: sqlite3.Connection, textaufgabe_id: int) -> dict:
    a = dbm.zeile(db, """
        SELECT x.*, t.sammlung_id, t.sprache, t.typ AS uebungstyp, t.titel,
               t.geprueft, t.lektion_id, k.nr AS lektion_nr,
               s.original, s.referenz, s.reihenfolge AS abschnitt_nr,
               s.varianten, s.referenz_varianten,
               (SELECT COUNT(*) FROM textabschnitt a2 WHERE a2.text_id = t.id)
                   AS abschnitte_gesamt
          FROM textaufgabe x
          JOIN text t ON t.id = x.text_id
          LEFT JOIN textabschnitt s ON s.id = x.abschnitt_id
          LEFT JOIN lektion k ON k.id = t.lektion_id
         WHERE x.id = ?""", (textaufgabe_id,))
    if a is None:
        raise UebungFehler(f"Übungsaufgabe {textaufgabe_id} gibt es nicht")
    return a


# ------------------------------------------------------------------ Stand

def stand(db: sqlite3.Connection, benutzer_id: int,
          sammlung_id: int | None = None) -> dict:
    """Was liegt an Übungen an?"""
    sammlungen = ([sammlung_id] if sammlung_id
                  else lernmodul._zugaengliche_sammlungen(db, benutzer_id))
    if not sammlungen:
        return {"faellig": 0, "neu": 0, "verlernt": 0, "reif": 0, "gesamt": 0,
                "ungeprueft": 0}
    platzhalter = ",".join("?" * len(sammlungen))
    heute_text = lernmodul.heute().isoformat()
    grund = f"""
        FROM textaufgabe x
        JOIN text t ON t.id = x.text_id
        LEFT JOIN textlernzustand z
               ON z.textaufgabe_id = x.id AND z.benutzer_id = ?
        WHERE x.aktiv = 1 AND t.geprueft = 1
          AND t.sammlung_id IN ({platzhalter})"""
    werte = (benutzer_id, *sammlungen)

    def zahl(bedingung, zusatz=()):
        return dbm.wert(db, f"SELECT COUNT(*) {grund} AND {bedingung}",
                        (*werte, *zusatz)) or 0

    return {
        "gesamt": dbm.wert(db, f"SELECT COUNT(*) {grund}", werte) or 0,
        "neu": zahl("(z.zustand IS NULL OR z.zustand = 'neu')"),
        "faellig": zahl("z.zustand IN ('lernen','reif') AND z.faellig <= ?",
                        (heute_text,)),
        "verlernt": zahl("z.zustand = 'verlernt'"),
        "reif": zahl("z.zustand = 'reif'"),
        # Nicht freigegebene Übungen werden nicht abgefragt. Die Zahl steht
        # hier, damit niemand vergeblich nach ihnen sucht.
        "ungeprueft": dbm.wert(db, f"""
            SELECT COUNT(*) FROM textaufgabe x JOIN text t ON t.id = x.text_id
             WHERE x.aktiv = 1 AND t.geprueft = 0
               AND t.sammlung_id IN ({platzhalter})""", sammlungen) or 0,
    }


# ----------------------------------------------------------- Was ist dran?

# Wie viele zuletzt gefragte Sätze gemieden werden, solange es Auswahl
# gibt. Gezählt wird der TEXT, nicht die einzelne Aufgabe: hin und
# zurück sind zwei Aufgaben zu demselben Satz, und zweimal denselben
# Satz hintereinander will auch niemand.
ZULETZT_MEIDEN = 2


def _rundenstand(db: sqlite3.Connection, benutzer_id: int) -> dict[int, int]:
    """Wie oft jeder TEXT heute schon dran war.

    Gezählt wird der Text, nicht die einzelne Aufgabe: hin und zurück
    sind zwei Aufgaben zu demselben Satz, und zweimal denselben Satz
    hintereinander will niemand.
    """
    heute = lernmodul.heute()
    morgen = (heute + dt.timedelta(days=1)).isoformat()
    return {z["text_id"]: z["n"] for z in dbm.zeilen(db, """
        SELECT x.text_id, COUNT(*) AS n
          FROM textbearbeitung b
          JOIN textaufgabe x ON x.id = b.textaufgabe_id
         WHERE b.benutzer_id = ? AND b.zeitpunkt >= ? AND b.zeitpunkt < ?
         GROUP BY x.text_id""", (benutzer_id, heute.isoformat(), morgen))}


def _zuletzt_gefragt(db: sqlite3.Connection, benutzer_id: int,
                     anzahl: int = ZULETZT_MEIDEN) -> list[int]:
    """Die Texte der zuletzt bearbeiteten Übungen dieser Person."""
    # Nach der Protokollnummer, nicht nach dem Zeitstempel: der hat
    # Sekundenauflösung, und wer zügig antwortet, erzeugt lauter
    # gleiche Werte — dann ist "zuletzt" nicht entscheidbar und die
    # Reihenfolge zufällig.
    return [z["text_id"] for z in dbm.zeilen(db, """
        SELECT x.text_id, MAX(b.id) AS zuletzt
          FROM textbearbeitung b
          JOIN textaufgabe x ON x.id = b.textaufgabe_id
         WHERE b.benutzer_id = ?
         GROUP BY x.text_id
         ORDER BY zuletzt DESC
         LIMIT ?""", (benutzer_id, anzahl))]


def naechste(db: sqlite3.Connection, benutzer_id: int,
             sammlung_id: int | None = None,
             lektion_nr: int | None = None,
             bis_lektion: int | None = None,
             typ: str | None = None,
             richtung: str | None = None,
             nur: str | None = None,
             anzahl: int = 1) -> list[dict]:
    """Die nächsten Übungsaufgaben.

    nur:  None       planmäßig: verlernt, dann fällig, dann neu
          "neu"      nur Neues
          "faellig"  nur Fälliges
          "frei"     alles, ohne Terminlogik
          "fehler"   was zuletzt schiefging
    """
    e = lernmodul.benutzer_einstellungen(db, benutzer_id)
    sammlungen = ([sammlung_id] if sammlung_id
                  else lernmodul._zugaengliche_sammlungen(db, benutzer_id))
    if not sammlungen:
        return []
    heute_text = lernmodul.heute().isoformat()

    bedingungen = ["x.aktiv = 1", "t.geprueft = 1",
                   f"t.sammlung_id IN ({','.join('?' * len(sammlungen))})"]
    werte: list = [benutzer_id, *sammlungen]
    if lektion_nr is not None:
        bedingungen.append("k.nr = ?"); werte.append(lektion_nr)
    if bis_lektion is not None:
        bedingungen.append("(k.nr IS NULL OR k.nr <= ?)")
        werte.append(bis_lektion)
    if typ:
        bedingungen.append("t.typ = ?"); werte.append(typ)
    if richtung:
        bedingungen.append("x.typ = ?")
        werte.append("uebersetzung_hin" if richtung == "hin"
                     else "uebersetzung_rueck")

    folge = "k.nr, t.reihenfolge, t.id, s.reihenfolge, x.typ"
    if nur == "neu":
        bedingungen.append("(z.zustand IS NULL OR z.zustand = 'neu')")
        ordnung = folge
    elif nur == "faellig":
        bedingungen.append(
            "z.zustand IN ('lernen','reif','verlernt') AND z.faellig <= ?")
        werte.append(heute_text)
        ordnung = "z.faellig, z.stabilitaet"
    elif nur == "fehler":
        bedingungen.append("z.anzahl_fehler > 0 AND z.zustand != 'ausgesetzt'")
        ordnung = "z.anzahl_fehler DESC, z.faellig"
    elif nur == "frei":
        bedingungen.append("(z.zustand IS NULL OR z.zustand != 'ausgesetzt')")
        ordnung = "RANDOM()"
    else:
        bedingungen.append("""(
            z.zustand IS NULL OR z.zustand = 'neu' OR z.zustand = 'verlernt'
            OR (z.zustand IN ('lernen','reif') AND z.faellig <= ?))""")
        werte.append(heute_text)
        ordnung = ("""CASE z.zustand WHEN 'verlernt' THEN 0
                                     WHEN 'lernen' THEN 1
                                     WHEN 'reif' THEN 1
                                     ELSE 3 END, z.faellig, """ + folge)

    # Abstand halten — dieselbe Regel wie bei den Vokabeln, wo sie schon
    # einmal aus dem Betrieb heraus nachgerüstet werden musste. Ohne sie
    # kommt nach »nochmal« sofort wieder derselbe Satz: die Bewertung
    # setzt ihn auf 'verlernt' und heute fällig, und 'verlernt' steht in
    # der Sortierung auf Rang 0. Daneben liegen unangetastete Sätze.
    #
    # Die Bedingung gehört in die ABFRAGE, nicht hinterher ins Sieb.
    # Nachgefiltert griff sie nicht: das Fenster enthält, nach Lektion
    # und Reihenfolge sortiert, überwiegend Aufgaben derselben ersten
    # Texte — also genau das, was gemieden werden soll, und dann bleibt
    # nichts übrig und der Rückfall nimmt doch wieder den alten Satz.
    meiden = ([] if nur in ("neu", "frei")
              else _zuletzt_gefragt(db, benutzer_id))
    # Erst jeden Satz einmal, dann den zweiten Durchgang — dieselbe Regel
    # wie bei den Vokabeln, und aus demselben Grund: »Nochmal« setzt den
    # Satz auf verlernt und heute fällig, und verlernt steht in der
    # Sortierung auf Rang 0. Gemessen waren es drei Sätze im Kreis,
    # sechzehn Fragen lang, während fünf unberührte danebenlagen.
    runde = ""
    if nur not in ("neu", "frei"):
        teile = " ".join(f"WHEN {int(t)} THEN {int(n)}"
                         for t, n in _rundenstand(db, benutzer_id).items())
        if teile:
            runde = f"CASE t.id {teile} ELSE 0 END, "
    rumpf = f"""
        SELECT x.id AS textaufgabe_id, t.id AS text_id
          FROM textaufgabe x
          JOIN text t ON t.id = x.text_id
          LEFT JOIN textabschnitt s ON s.id = x.abschnitt_id
          LEFT JOIN lektion k ON k.id = t.lektion_id
          LEFT JOIN textlernzustand z
                 ON z.textaufgabe_id = x.id AND z.benutzer_id = ?
         WHERE {' AND '.join(bedingungen)}"""
    reihe = []
    if meiden:
        reihe = dbm.zeilen(db, f"""{rumpf}
           AND t.id NOT IN ({','.join('?' * len(meiden))})
         ORDER BY {runde}{ordnung}
         LIMIT ?""", (*werte, *meiden, max(1, anzahl)))
    if not reihe:
        # Nichts anderes da — dann eben der zuletzt gefragte Satz. Mit
        # einer einzigen Übung ist jede Abfrage eine Wiederholung.
        reihe = dbm.zeilen(db, f"""{rumpf}
         ORDER BY {runde}{ordnung}
         LIMIT ?""", (*werte, max(1, anzahl)))

    ergebnis = []
    for r in reihe[:max(1, anzahl)]:
        _zustand_sichern(db, r["textaufgabe_id"], benutzer_id)
        ergebnis.append(ausbauen(db, r["textaufgabe_id"], benutzer_id,
                                 e["wunschretention"]))
    return ergebnis


def ausbauen(db: sqlite3.Connection, textaufgabe_id: int, benutzer_id: int,
             wunschretention: float = 0.9) -> dict:
    """Die Aufgabe, wie sie die Oberfläche braucht — ohne die Lösung."""
    a = _aufgabe(db, textaufgabe_id)
    z = _zustand_sichern(db, textaufgabe_id, benutzer_id)
    frage_sprache, antwort_sprache = _sprachen(db, a)
    hin = a["typ"] == "uebersetzung_hin"
    frage = a["original"] if hin else a["referenz"]
    vorher = fsrs.Zustand(z["stabilitaet"], z["schwierigkeit"])
    verstrichen = lernmodul._tage_seit(z["letzte_wiederholung"])

    return {
        "textaufgabe_id": textaufgabe_id,
        "uebung_id": a["text_id"],
        "typ": a["typ"],
        "uebungstyp": a["uebungstyp"],
        "titel": a["titel"],
        "aufgabe_text": RICHTUNGSTEXT.get(a["typ"], a["typ"]),
        "bewertung_art": a["bewertung_art"],
        # Beim Satz zählt das Urteil, beim langen Text schätzt der Mensch
        # selbst ein. Die Oberfläche muss das vorher wissen.
        "selbsteinschaetzung": a["bewertung_art"] != "genau",
        "frage_text": frage,
        "frage_sprache": frage_sprache,
        "antwort_sprache": antwort_sprache,
        "lektion_nr": a["lektion_nr"],
        "abschnitt": (a["abschnitt_nr"] or 0) + 1,
        "abschnitte_gesamt": a["abschnitte_gesamt"],
        "vorlesen": frage if frage_sprache == a["sprache"] else None,
        "zustand": z["zustand"],
        "stabilitaet": z["stabilitaet"],
        "schwierigkeit": z["schwierigkeit"],
        "anzahl": z["anzahl"],
        "anzahl_fehler": z["anzahl_fehler"],
        "begruendung": lernmodul._begruendung(z) if hasattr(
            lernmodul, "_begruendung") else None,
        "vorschau": {str(b): fsrs.tage_in_text(
            fsrs.vorschau(vorher, verstrichen, wunschretention,
                          saat=textaufgabe_id,
                          selber_tag=lernmodul._selber_tag(
                              z["letzte_wiederholung"]))[b])
            for b in fsrs.BEWERTUNGEN},
    }


# ------------------------------------------------------------- Bearbeiten

def pruefen(db: sqlite3.Connection, benutzer_id: int, textaufgabe_id: int,
            antwort: str) -> dict:
    """Vergleicht die Antwort. Schreibt noch nichts fort."""
    a = _aufgabe(db, textaufgabe_id)
    _frage_sprache, antwort_sprache = _sprachen(db, a)
    urteil = satzpruefung.pruefen(antwort, dbm.j_lesen(a["erwartet"]) or [],
                                  sprachen.profil(antwort_sprache))
    return {
        "textaufgabe_id": textaufgabe_id,
        "bewertung_art": a["bewertung_art"],
        # Beim langen Text ist der Vergleich Hilfestellung, kein Urteil.
        "zaehlt": a["bewertung_art"] == "genau",
        "selbsteinschaetzung": a["bewertung_art"] != "genau",
        "sprache": antwort_sprache,
        "urteil": urteil.als_dict(),
        "loesung": _loesung(a),
    }


def aufdecken(db: sqlite3.Connection, benutzer_id: int,
              textaufgabe_id: int) -> dict:
    """»Weiß ich nicht«. Zeigt die Lösung, ohne schon zu bewerten."""
    a = _aufgabe(db, textaufgabe_id)
    _zustand_sichern(db, textaufgabe_id, benutzer_id)
    return {"textaufgabe_id": textaufgabe_id, "loesung": _loesung(a),
            "hinweis": "Aufgedeckt zählt wie »nochmal« — die Übung kommt "
                       "gleich wieder."}


def _loesung(a: dict) -> dict:
    gueltig = dbm.j_lesen(a["erwartet"]) or []
    return {"haupt": gueltig[0] if gueltig else None,
            "weitere": gueltig[1:],
            # Die andere Seite dazu: wer die Lösung liest, will den Satz im
            # Ganzen sehen, nicht nur die Hälfte, die er suchen sollte.
            "gegenstueck": (a["referenz"] if a["typ"] == "uebersetzung_rueck"
                            else a["original"])}


def bewerten(db: sqlite3.Connection, benutzer_id: int, textaufgabe_id: int,
             urteil: str | None = None, bewertung: int | None = None,
             antwort: str | None = None, dauer_ms: int | None = None,
             aufgedeckt: bool = False, versuche: int = 1,
             rueckmeldung: str | None = None) -> dict:
    """Schreibt den Lernstand fort und protokolliert.

    Ohne `bewertung` wird sie aus dem Urteil abgeleitet. Die Denkzeit geht
    hier bewusst NICHT ein: bei einem Satz misst sie Lesen und Tippen, nicht
    das Können.
    """
    a = _aufgabe(db, textaufgabe_id)
    e = lernmodul.benutzer_einstellungen(db, benutzer_id)
    quelle = "von_hand"
    einschaetzung = None
    if bewertung is None:
        if urteil is None:
            raise UebungFehler("Ohne Bewertung wird das Urteil gebraucht")
        einschaetzung = bewertungsmodul.einschaetzen(
            urteil, denkzeit_ms=None, versuche=versuche, aufgedeckt=aufgedeckt,
            zeitmessung=False)
        bewertung = einschaetzung["bewertung"]
        quelle = ("automatisch" if a["bewertung_art"] == "genau"
                  else "selbsteinschaetzung")
    if bewertung not in fsrs.BEWERTUNGEN:
        raise UebungFehler("Bewertung muss 1 bis 4 sein")

    z = _zustand_sichern(db, textaufgabe_id, benutzer_id)
    vorher = fsrs.Zustand(z["stabilitaet"], z["schwierigkeit"])
    verstrichen = lernmodul._tage_seit(z["letzte_wiederholung"])
    ergebnis = fsrs.bewerten(
        vorher, bewertung, verstrichen, e["wunschretention"],
        saat=textaufgabe_id,
        selber_tag=lernmodul._selber_tag(z["letzte_wiederholung"]))
    faellig = (lernmodul.heute().isoformat() if bewertung == fsrs.NOCHMAL
               else (lernmodul.heute()
                     + dt.timedelta(days=round(ergebnis.intervall_tage))
                     ).isoformat())

    db.execute("""UPDATE textlernzustand
                     SET zustand = ?, stabilitaet = ?, schwierigkeit = ?,
                         letzte_wiederholung = ?, faellig = ?,
                         anzahl = anzahl + 1,
                         anzahl_fehler = anzahl_fehler + ?
                   WHERE textaufgabe_id = ? AND benutzer_id = ?""",
               (ergebnis.zustand, ergebnis.stabilitaet, ergebnis.schwierigkeit,
                lernmodul._jetzt(), faellig,
                1 if bewertung == fsrs.NOCHMAL else 0,
                textaufgabe_id, benutzer_id))
    db.execute("""INSERT INTO textbearbeitung
                    (textaufgabe_id, benutzer_id, zeitpunkt, antwort,
                     bewertung, rueckmeldung, dauer_ms, urteil, versuche,
                     bewertung_quelle, aufgedeckt, stabilitaet_vor,
                     stabilitaet_nach, schwierigkeit_vor, schwierigkeit_nach,
                     intervall_tage, verstrichen_tage)
                  VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
               (textaufgabe_id, benutzer_id, lernmodul._jetzt(), antwort,
                bewertung, rueckmeldung, dauer_ms, urteil, versuche, quelle,
                int(bool(aufgedeckt)), vorher.stabilitaet, ergebnis.stabilitaet,
                vorher.schwierigkeit, ergebnis.schwierigkeit,
                ergebnis.intervall_tage, round(verstrichen, 4)))

    return {
        "bewertung": bewertung, "bewertung_quelle": quelle,
        "einschaetzung": einschaetzung, "zustand": ergebnis.zustand,
        "stabilitaet": ergebnis.stabilitaet,
        "schwierigkeit": ergebnis.schwierigkeit,
        "intervall_tage": ergebnis.intervall_tage, "faellig": faellig,
        "termin_text": fsrs.tage_in_text(ergebnis.intervall_tage),
    }


def zuruecksetzen(db: sqlite3.Connection, benutzer_id: int,
                  textaufgabe_id: int) -> None:
    db.execute("""UPDATE textlernzustand
                     SET zustand = 'neu', stabilitaet = NULL,
                         schwierigkeit = NULL, letzte_wiederholung = NULL,
                         faellig = NULL, anzahl = 0, anzahl_fehler = 0
                   WHERE textaufgabe_id = ? AND benutzer_id = ?""",
               (textaufgabe_id, benutzer_id))


def aussetzen(db: sqlite3.Connection, benutzer_id: int, textaufgabe_id: int,
              aussetzen_: bool = True) -> None:
    _zustand_sichern(db, textaufgabe_id, benutzer_id)
    if aussetzen_:
        db.execute("""UPDATE textlernzustand SET zustand = 'ausgesetzt'
                       WHERE textaufgabe_id = ? AND benutzer_id = ?""",
                   (textaufgabe_id, benutzer_id))
        return
    # Zurück in den Verkehr — aber nicht als »neu«: wer schon geübt hat,
    # hat eine Stabilität, und die rechnet FSRS weiter. Als »neu« zählte
    # der Satz gegen den Tagesvorrat an Neuem und würde noch einmal
    # eingeführt. Die Vokabelseite macht es seit je richtig.
    db.execute("""UPDATE textlernzustand
                     SET zustand = CASE WHEN stabilitaet IS NULL
                                        THEN 'neu' ELSE 'lernen' END
                   WHERE textaufgabe_id = ? AND benutzer_id = ?""",
               (textaufgabe_id, benutzer_id))
