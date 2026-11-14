"""Die Lernsitzung: was ist dran, und was passiert mit der Bewertung.

Hier steckt die Antwort auf das dritte Ärgernis — "unverständlicher
Lernalgorithmus". Jede Aufgabe, die gestellt wird, kann begründen, warum
gerade sie dran ist, und jeder Bewertungsknopf zeigt vorher an, welchen
Termin er ergeben würde.
"""

from __future__ import annotations

import datetime as dt
import sqlite3

import aufgaben
import bewertung as bewertungsmodul
import datenbank as dbm
import fsrs
import legasthenie as legasthenie_modul

# Reihenfolge, in der fällige Aufgaben genommen werden.
#   verlernt  — was zuletzt schiefging, zuerst
#   faellig   — überfällige vor knapp fälligen
#   neu       — Neues zuletzt, und mengenmäßig begrenzt
NEU_JE_SITZUNG = 20

# In welcher Folge Neues eingeführt wird: nach Lektion, dann nach der
# Lernreihenfolge innerhalb der Lektion, dann nach Eingabedatum. Wörter
# ohne Lektion kommen zuletzt — sie sind meist selbst nachgetragen.
LERNREIHENFOLGE = ("(SELECT k.nr FROM lektion k WHERE k.id = l.lektion_id) "
                   "IS NULL, "
                   "(SELECT k.nr FROM lektion k WHERE k.id = l.lektion_id), "
                   "l.reihenfolge, l.id, a.typ")


def heute() -> dt.date:
    return dt.date.today()


def _jetzt() -> str:
    return dt.datetime.now().isoformat(timespec="seconds")


def _tage_seit(zeitpunkt: str | None) -> float:
    if not zeitpunkt:
        return 0.0
    try:
        davor = dt.datetime.fromisoformat(zeitpunkt)
    except ValueError:
        return 0.0
    return max(0.0, (dt.datetime.now() - davor).total_seconds() / 86400.0)


def benutzer_einstellungen(db: sqlite3.Connection, benutzer_id: int) -> dict:
    b = dbm.zeile(db, "SELECT * FROM benutzer WHERE id = ?", (benutzer_id,))
    if b is None:
        raise KeyError(f"Benutzer {benutzer_id} gibt es nicht")
    e = dbm.j_lesen(b["einstellungen"])
    lg = {**legasthenie_modul.VOREINSTELLUNG, **(e.get("legasthenie") or {})}

    retention = float(e.get("wunschretention", 0.9))
    neu = int(e.get("neu_je_sitzung", NEU_JE_SITZUNG))
    if lg["aktiv"]:
        # Häufiger wiederholen, dafür in kleineren Schritten, und weniger
        # Neues auf einmal — nicht weil weniger möglich wäre, sondern weil
        # die Last beim Abruf von Zeichenfolgen woanders liegt.
        if lg.get("mehr_wiederholungen") and "wunschretention" not in e:
            retention = 0.95
        if lg.get("weniger_neues") and "neu_je_sitzung" not in e:
            neu = 8
    return {
        "wunschretention": retention,
        "neu_je_sitzung": neu,
        "name": b["name"],
        "legasthenie": lg,
    }


def _zugaengliche_sammlungen(db: sqlite3.Connection, benutzer_id: int) -> list[int]:
    """Eigene Sammlungen und die, die mir freigegeben wurden."""
    return [z["id"] for z in dbm.zeilen(db, """
        SELECT s.id FROM sammlung s WHERE s.besitzer_id = ?
        UNION
        SELECT f.sammlung_id FROM freigabe f WHERE f.benutzer_id = ?""",
        (benutzer_id, benutzer_id))]


def _zustand_sichern(db: sqlite3.Connection, aufgabe_id: int,
                     benutzer_id: int) -> dict:
    """Legt den Lernzustand an, falls er noch fehlt."""
    z = dbm.zeile(db, """SELECT * FROM lernzustand
                          WHERE aufgabe_id = ? AND benutzer_id = ?""",
                  (aufgabe_id, benutzer_id))
    if z is None:
        db.execute("""INSERT INTO lernzustand (aufgabe_id, benutzer_id, zustand)
                      VALUES (?, ?, 'neu')""", (aufgabe_id, benutzer_id))
        z = dbm.zeile(db, """SELECT * FROM lernzustand
                              WHERE aufgabe_id = ? AND benutzer_id = ?""",
                      (aufgabe_id, benutzer_id))
    return z


def stand(db: sqlite3.Connection, benutzer_id: int,
          sammlung_id: int | None = None) -> dict:
    """Was liegt an? Zahlen für die Übersicht."""
    sammlungen = ([sammlung_id] if sammlung_id
                  else _zugaengliche_sammlungen(db, benutzer_id))
    if not sammlungen:
        return {"faellig": 0, "neu": 0, "verlernt": 0, "reif": 0, "gesamt": 0}
    platzhalter = ",".join("?" * len(sammlungen))
    heute_text = heute().isoformat()
    grund = f"""
        FROM aufgabe a
        JOIN lexem l ON l.id = a.lexem_id
        LEFT JOIN lernzustand z
               ON z.aufgabe_id = a.id AND z.benutzer_id = ?
        WHERE a.aktiv = 1 AND l.sammlung_id IN ({platzhalter})"""
    werte = (benutzer_id, *sammlungen)
    zahl = lambda bedingung, zusatz=(): dbm.wert(
        db, f"SELECT COUNT(*) {grund} AND {bedingung}", (*werte, *zusatz)) or 0
    return {
        "gesamt": dbm.wert(db, f"SELECT COUNT(*) {grund}", werte) or 0,
        "neu": zahl("(z.zustand IS NULL OR z.zustand = 'neu')"),
        "faellig": zahl("z.zustand IN ('lernen','reif') AND z.faellig <= ?",
                        (heute_text,)),
        "verlernt": zahl("z.zustand = 'verlernt'"),
        "reif": zahl("z.zustand = 'reif'"),
        "ausgesetzt": zahl("z.zustand = 'ausgesetzt'"),
    }


def naechste(db: sqlite3.Connection, benutzer_id: int,
             sammlung_id: int | None = None,
             lektion_id: int | None = None,
             typen: list[str] | None = None,
             nur: str | None = None,
             anzahl: int = 1,
             lernziel_id: int | None = None,
             bis_lektion: int | None = None) -> list[dict]:
    """Die nächsten Aufgaben.

    nur:  None       — planmäßig: verlernt, dann fällig, dann neu
          "neu"      — nur Neues
          "faellig"  — nur Fälliges, kein Neues
          "frei"     — freies Üben: alles, ohne Terminlogik
          "fehler"   — was zuletzt schiefging
    """
    # Ein Lernziel schneidet den Bestand zu — und zwar quer über Lektionen
    # und Sammlungen. Der Block entscheidet dann über die Reihenfolge.
    if lernziel_id is not None:
        import lernziele
        # Der Block wird in brauchbarer Größe gerechnet, auch wenn nur eine
        # Aufgabe abgeholt wird: bei Blockgröße 1 kann die Verschränkung
        # nichts verschränken und der Zuschnitt verliert seinen Sinn.
        plan = lernziele.block(db, benutzer_id, lernziel_id, max(anzahl, 20))
        e = benutzer_einstellungen(db, benutzer_id)
        ergebnis = []
        for eintrag in plan["aufgaben"][:anzahl]:
            z = _zustand_sichern(db, eintrag["aufgabe_id"], benutzer_id)
            ergebnis.append({
                **_aufgabe_ausbauen(db, {**dict(z),
                                         "aufgabe_id": eintrag["aufgabe_id"],
                                         "typ": eintrag["typ"]},
                                    e["wunschretention"], e["legasthenie"]),
                "herkunft": eintrag["herkunft"],
                "lernziel": {"id": lernziel_id, "name": plan["name"],
                             "begruendung": plan["begruendung"]},
            })
        return ergebnis

    sammlungen = ([sammlung_id] if sammlung_id
                  else _zugaengliche_sammlungen(db, benutzer_id))
    if not sammlungen:
        return []
    e = benutzer_einstellungen(db, benutzer_id)
    heute_text = heute().isoformat()

    bedingungen = [f"l.sammlung_id IN ({','.join('?' * len(sammlungen))})",
                   "a.aktiv = 1"]
    werte: list = [benutzer_id, *sammlungen]
    if lektion_id is not None:
        bedingungen.append("l.lektion_id = ?")
        werte.append(lektion_id)
    if bis_lektion is not None:
        # Der übliche Schnitt beim Mitlernen: alles bis zur Lektion, die man
        # im Unterricht hat. Wörter ohne Lektion zählen mit — sie sind meist
        # selbst nachgetragen und nicht an das Lehrwerk gebunden.
        bedingungen.append("""(l.lektion_id IS NULL OR EXISTS (
            SELECT 1 FROM lektion k WHERE k.id = l.lektion_id
              AND (k.nr IS NULL OR k.nr <= ?)))""")
        werte.append(bis_lektion)
    if typen:
        bedingungen.append(f"a.typ IN ({','.join('?' * len(typen))})")
        werte += list(typen)

    # Die Sortierung ist die eigentliche Entscheidung. Sie steht hier
    # vollständig und ist in der Oberfläche als "Warum jetzt?" nachlesbar.
    if nur == "neu":
        bedingungen.append("(z.zustand IS NULL OR z.zustand = 'neu')")
        ordnung = LERNREIHENFOLGE
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
            z.zustand IS NULL
            OR z.zustand = 'neu'
            OR (z.zustand = 'verlernt')
            OR (z.zustand IN ('lernen','reif') AND z.faellig <= ?)
        )""")
        werte.append(heute_text)
        # verlernt zuerst, dann nach Fälligkeit, Neues zuletzt
        ordnung = """
            CASE z.zustand WHEN 'verlernt' THEN 0
                           WHEN 'lernen' THEN 1
                           WHEN 'reif' THEN 1
                           ELSE 3 END,
            z.faellig,
            """ + LERNREIHENFOLGE

    sql = f"""
        SELECT a.id AS aufgabe_id, a.typ, l.id AS lexem_id, l.lemma,
               l.sammlung_id, z.zustand, z.stabilitaet, z.schwierigkeit,
               z.faellig, z.letzte_wiederholung, z.anzahl, z.anzahl_fehler
          FROM aufgabe a
          JOIN lexem l ON l.id = a.lexem_id
          LEFT JOIN lernzustand z
                 ON z.aufgabe_id = a.id AND z.benutzer_id = ?
         WHERE {' AND '.join(bedingungen)}
         ORDER BY {ordnung}
         LIMIT ?"""
    reihe = dbm.zeilen(db, sql, (*werte, anzahl * 4))

    # Neue begrenzen, sonst überschwemmt ein frischer Import die Sitzung.
    if nur is None:
        # Tagesgrenzen statt date() auf der Spalte: so greift der Index
        # idx_wiederholung_zeit. Mit date() wird bei jedem Aufgabenabruf das
        # ganze Protokoll des Benutzers gelesen, und das wird nie geleert.
        schon_neu = dbm.wert(db, """
            SELECT COUNT(DISTINCT w.aufgabe_id) FROM wiederholung w
             WHERE w.benutzer_id = ?
               AND w.zeitpunkt >= ? AND w.zeitpunkt < ?
               AND w.stabilitaet_vor IS NULL""",
            (benutzer_id, heute_text, (heute() + dt.timedelta(days=1)).isoformat())) or 0
        rest_neu = max(0, e["neu_je_sitzung"] - schon_neu)
        gefiltert, genommen_neu = [], 0
        for r in reihe:
            ist_neu = r["zustand"] in (None, "neu")
            if ist_neu:
                if genommen_neu >= rest_neu:
                    continue
                genommen_neu += 1
            gefiltert.append(r)
        reihe = gefiltert

    ergebnis = []
    for r in reihe[:anzahl]:
        _zustand_sichern(db, r["aufgabe_id"], benutzer_id)
        ergebnis.append(_aufgabe_ausbauen(db, r, e["wunschretention"],
                                          e["legasthenie"]))
    return ergebnis


def _aufgabe_ausbauen(db: sqlite3.Connection, r: dict, wunschretention: float,
                      legasthenie: dict | None = None) -> dict:
    """Aufgabe plus Begründung plus Terminvorschau.

    Im Legastheniemodus kommt das Schreibgerüst gleich mit: ins leere Feld zu
    tippen ist genau der Teil, der schwerfällt. Es wird hier erzeugt und nicht
    in der Oberfläche, weil nur hier die erwartete Antwort bekannt ist.
    """
    f = aufgaben.frage(db, r["aufgabe_id"])
    lg = legasthenie or {}
    if (lg.get("aktiv") and lg.get("maske_stufe") is not None
            and f.get("eingabeart") == "text"):
        _u, aufloesung = aufgaben.antwort_pruefen(db, r["aufgabe_id"], "",
                                                  fehler_benennen=False)
        ziel = next(iter(aufloesung.get("erwartet") or []), None)
        if ziel:
            f["maske"] = legasthenie_modul.maske(ziel, int(lg["maske_stufe"]))
    z = fsrs.Zustand(r["stabilitaet"], r["schwierigkeit"])
    verstrichen = _tage_seit(r["letzte_wiederholung"])
    vorschau = fsrs.vorschau(z, verstrichen, wunschretention)
    return {
        **f,
        "lernstand": {
            "zustand": r["zustand"] or "neu",
            "stabilitaet": r["stabilitaet"],
            "schwierigkeit": r["schwierigkeit"],
            "faellig": r["faellig"],
            "anzahl": r["anzahl"],
            "anzahl_fehler": r["anzahl_fehler"],
            "verstrichen_tage": round(verstrichen, 2),
        },
        "warum": fsrs.erklaeren(z, verstrichen, wunschretention),
        "vorschau": {str(b): {"tage": t, "text": fsrs.tage_in_text(t)}
                     for b, t in vorschau.items()},
    }


def pruefen(db: sqlite3.Connection, benutzer_id: int, aufgabe_id: int,
            eingabe, denkzeit_ms: int | None = None, versuche: int = 1,
            aufgedeckt: bool = False) -> dict:
    """Prüft die Antwort — ohne den Lernstand zu ändern.

    Getrennt vom Bewerten, damit "fast richtig" möglich ist: dann wird noch
    einmal getippt, und erst die endgültige Antwort zählt.

    Die Bewertung wird hier schon mitgerechnet und mitgeliefert, damit die
    Oberfläche zeigen kann, wie gewertet wird — und wonach.
    """
    e = benutzer_einstellungen(db, benutzer_id)
    urteil, aufloesung = aufgaben.antwort_pruefen(
        db, aufgabe_id, eingabe,
        fehler_benennen=bool(e["legasthenie"].get("fehler_benennen", True)))

    # "Fast richtig" wird noch nicht gewertet — es wird noch einmal getippt.
    nochmal = urteil.urteil == "fast" and versuche == 1 and not aufgedeckt
    erwartet = next(iter(aufloesung.get("erwartet") or []), None)
    gewertet = bewertungsmodul.fuer_aufgabe(
        db, benutzer_id, aufgabe_id,
        urteil=urteil.urteil,
        fehlerart=(urteil.fehlerart
                   or ("diakritika" if "diakritika" in urteil.abweichungen
                       else ("verwechslung" if "verwechslung" in urteil.abweichungen
                             else None))),
        denkzeit_ms=denkzeit_ms, versuche=versuche, aufgedeckt=aufgedeckt,
        erwartet=erwartet,
        zeitmessung=_zeitmessung(e),
    )
    return {
        "urteil": urteil.als_dict(),
        "aufloesung": aufloesung,
        "zerlegung": _zerlegung(db, aufgabe_id, urteil, aufloesung, e),
        "bewertung": gewertet,
        "bewertung_vorschlag": gewertet["bewertung"],
        "nochmal_tippen": nochmal,
    }


def _zerlegung(db: sqlite3.Connection, aufgabe_id: int, urteil, aufloesung: dict,
               einstellungen: dict) -> dict | None:
    """Zerlegt die richtige Antwort in Stamm und Endung beziehungsweise Silben.

    Nur wenn verlangt und nur wenn es etwas zu zerlegen gibt. Der Stamm wird
    aus den anderen Formen desselben Wortes abgeleitet, nicht geraten.
    """
    lg = einstellungen["legasthenie"]
    if not lg.get("aktiv") or urteil.urteil == "richtig":
        return None
    # Nur bei Texteingaben. Bei "Form bestimmen" ist die Antwort ein
    # Merkmalsbündel, beim Artikel ein einzelnes Wörtchen — da wäre die
    # Zerlegung in Stamm und Silben sinnlos bis irreführend.
    a0 = dbm.zeile(db, "SELECT typ FROM aufgabe WHERE id = ?", (aufgabe_id,))
    if a0 is None or aufgaben.TYPEN[a0["typ"]]["eingabeart"] != "text":
        return None
    # Ohne Treffer — also bei klar falscher Antwort — die erwartete Lösung
    # zerlegen. Gerade dann ist die Hilfe am nötigsten.
    ziel = urteil.treffer or next(iter(aufloesung.get("erwartet") or []), None)
    if not ziel:
        return None
    st = aufgaben.stamm_fuer_aufgabe(db, aufgabe_id)
    ergebnis: dict = {}
    if lg.get("stamm_hervorheben") and st:
        ergebnis["stamm"] = st
        ergebnis["teile"] = legasthenie_modul.teilen(ziel, st, _partikeln(db, aufgabe_id))
    if lg.get("silben_faerben"):
        ergebnis["silben"] = legasthenie_modul.silben(ziel)
    if lg.get("maske_stufe") is not None:
        ergebnis["maske"] = legasthenie_modul.maske(ziel, int(lg["maske_stufe"]))
    return ergebnis or None


def _zeitmessung(einstellungen: dict) -> bool:
    """Wird die Denkzeit gewertet?

    Die Legasthenie-Voreinstellungen stehen immer im Datensatz, gelten aber
    nur bei eingeschaltetem Modus. Ohne diese Unterscheidung wäre die
    Zeitwertung für alle abgeschaltet gewesen — die Voreinstellung sagt dort
    ja "nicht messen".
    """
    lg = einstellungen["legasthenie"]
    return not (lg.get("aktiv") and lg.get("keine_zeitmessung", True))


def _partikeln(db: sqlite3.Connection, aufgabe_id: int) -> list[str]:
    """Vorangestellte Wörtchen der Sprache dieser Aufgabe."""
    import sprachen
    code = dbm.wert(db, """SELECT s.sprache FROM aufgabe a
                            JOIN lexem l ON l.id = a.lexem_id
                            JOIN sammlung s ON s.id = l.sammlung_id
                           WHERE a.id = ?""", (aufgabe_id,))
    return sprachen.partikeln(code) if code else []


def _stammformen(db: sqlite3.Connection, aufgabe_id: int) -> list[str]:
    """Die Formen, aus denen der Stamm abgeleitet wird.

    Bei einer Formaufgabe die Geschwister derselben Zeit — nur dort ist der
    Stamm konstant. Sonst alle Formen des Wortes.
    """
    a = dbm.zeile(db, "SELECT lexem_id, ziel_art, ziel_id FROM aufgabe WHERE id = ?",
                  (aufgabe_id,))
    if a is None:
        return []
    if a["ziel_art"] == "form" and a["ziel_id"]:
        geschwister = aufgaben.geschwisterformen(db, a["ziel_id"])
        if len(geschwister) >= 2:
            return geschwister
    return [z["text"] for z in
            dbm.zeilen(db, "SELECT text FROM form WHERE lexem_id = ?",
                       (a["lexem_id"],))]


def aufdecken(db: sqlite3.Connection, benutzer_id: int, aufgabe_id: int) -> dict:
    """Die Lösung zeigen, ohne zu bewerten.

    Zwei Zwecke. Erstens "ich weiß es nicht" — ehrlicher als zu raten.
    Zweitens das Einprägen vor dem Schreiben im Legastheniemodus: beim
    ERSTEN Zusammentreffen mit einem Wort ins Leere tippen zu müssen,
    erzeugt nur einen Fehler, den man sich dann mitmerkt. Also zuerst
    ansehen, zerlegt und wenn möglich gehört — dann schreiben.
    """
    e = benutzer_einstellungen(db, benutzer_id)
    _urteil, aufloesung = aufgaben.antwort_pruefen(db, aufgabe_id, "",
                                                   fehler_benennen=False)
    erwartet = list(aufloesung.get("erwartet") or [])
    ziel = erwartet[0] if erwartet else None
    a0 = dbm.zeile(db, "SELECT typ FROM aufgabe WHERE id = ?", (aufgabe_id,))
    nur_text = a0 is not None and aufgaben.TYPEN[a0["typ"]]["eingabeart"] == "text"
    zerlegung = None
    if ziel and nur_text:
        lg = e["legasthenie"]
        st = aufgaben.stamm_fuer_aufgabe(db, aufgabe_id)
        zerlegung = {
            "silben": legasthenie_modul.silben(ziel),
            "stamm": st or None,
            "teile": (legasthenie_modul.teilen(ziel, st, _partikeln(db, aufgabe_id))
                      if st else [ziel]),
            "maske": legasthenie_modul.maske(ziel, int(lg.get("maske_stufe", 2))),
        }
    return {"erwartet": erwartet, "aufloesung": aufloesung,
            "zerlegung": zerlegung}


def bewerten(db: sqlite3.Connection, benutzer_id: int, aufgabe_id: int,
             bewertung: int | None = None, antwort: str | None = None,
             urteil: str | None = None, dauer_ms: int | None = None,
             denkzeit_ms: int | None = None, versuche: int = 1,
             aufgedeckt: bool = False, fehlerart: str | None = None) -> dict:
    """Schreibt die Bewertung fort: Lernzustand neu rechnen, protokollieren.

    Ohne `bewertung` wird sie aus den Antwortsignalen abgeleitet — das ist der
    Normalfall. Eine mitgegebene Bewertung ist ein Eingriff von Hand und wird
    als solcher protokolliert, damit später nachvollziehbar bleibt, welcher
    Teil des Lernstands auf automatischer Wertung beruht.
    """
    e = benutzer_einstellungen(db, benutzer_id)
    quelle = "von_hand"
    einschaetzung = None
    if bewertung is None:
        if urteil is None:
            raise ValueError("Ohne Bewertung wird das Urteil gebraucht")
        einschaetzung = bewertungsmodul.fuer_aufgabe(
            db, benutzer_id, aufgabe_id, urteil=urteil, fehlerart=fehlerart,
            denkzeit_ms=denkzeit_ms, versuche=versuche, aufgedeckt=aufgedeckt,
            erwartet=antwort, zeitmessung=_zeitmessung(e))
        bewertung = einschaetzung["bewertung"]
        quelle = "automatisch"
    if bewertung not in fsrs.BEWERTUNGEN:
        raise ValueError("Bewertung muss 1 bis 4 sein")
    z = _zustand_sichern(db, aufgabe_id, benutzer_id)
    vorher = fsrs.Zustand(z["stabilitaet"], z["schwierigkeit"])
    verstrichen = _tage_seit(z["letzte_wiederholung"])

    ergebnis = fsrs.bewerten(vorher, bewertung, verstrichen,
                             e["wunschretention"], saat=aufgabe_id)

    if bewertung == fsrs.NOCHMAL:
        faellig = heute().isoformat()          # bleibt heute dran
    else:
        faellig = (heute() + dt.timedelta(days=round(ergebnis.intervall_tage))
                   ).isoformat()

    db.execute("""UPDATE lernzustand
                     SET zustand = ?, stabilitaet = ?, schwierigkeit = ?,
                         letzte_wiederholung = ?, faellig = ?,
                         anzahl = anzahl + 1,
                         anzahl_fehler = anzahl_fehler + ?
                   WHERE aufgabe_id = ? AND benutzer_id = ?""",
               (ergebnis.zustand, ergebnis.stabilitaet, ergebnis.schwierigkeit,
                _jetzt(), faellig, 1 if bewertung == fsrs.NOCHMAL else 0,
                aufgabe_id, benutzer_id))

    db.execute("""INSERT INTO wiederholung
                    (aufgabe_id, benutzer_id, zeitpunkt, bewertung, antwort,
                     urteil, dauer_ms, denkzeit_ms, versuche, bewertung_quelle,
                     stabilitaet_vor, stabilitaet_nach,
                     schwierigkeit_vor, schwierigkeit_nach, intervall_tage,
                     verstrichen_tage)
                  VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
               (aufgabe_id, benutzer_id, _jetzt(), bewertung, antwort, urteil,
                dauer_ms, denkzeit_ms, versuche, quelle,
                vorher.stabilitaet, ergebnis.stabilitaet,
                vorher.schwierigkeit, ergebnis.schwierigkeit,
                ergebnis.intervall_tage, round(verstrichen, 4)))

    return {
        "bewertung": bewertung,
        "bewertung_quelle": quelle,
        "einschaetzung": einschaetzung,
        "zustand": ergebnis.zustand,
        "stabilitaet": ergebnis.stabilitaet,
        "schwierigkeit": ergebnis.schwierigkeit,
        "intervall_tage": ergebnis.intervall_tage,
        "faellig": faellig,
        "termin_text": fsrs.tage_in_text(ergebnis.intervall_tage),
    }


def aussetzen(db: sqlite3.Connection, benutzer_id: int, aufgabe_id: int,
              aussetzen_: bool = True) -> None:
    """Von Hand aus dem Verkehr ziehen oder zurückholen."""
    _zustand_sichern(db, aufgabe_id, benutzer_id)
    if aussetzen_:
        db.execute("""UPDATE lernzustand SET zustand = 'ausgesetzt'
                       WHERE aufgabe_id = ? AND benutzer_id = ?""",
                   (aufgabe_id, benutzer_id))
    else:
        db.execute("""UPDATE lernzustand
                         SET zustand = CASE WHEN stabilitaet IS NULL THEN 'neu'
                                            ELSE 'lernen' END
                       WHERE aufgabe_id = ? AND benutzer_id = ?""",
                   (aufgabe_id, benutzer_id))


def zuruecksetzen(db: sqlite3.Connection, benutzer_id: int,
                  aufgabe_id: int) -> None:
    """Lernstand verwerfen, Aufgabe gilt wieder als neu.
    Das Protokoll bleibt stehen."""
    db.execute("""UPDATE lernzustand
                     SET zustand = 'neu', stabilitaet = NULL,
                         schwierigkeit = NULL, letzte_wiederholung = NULL,
                         faellig = NULL, anzahl = 0, anzahl_fehler = 0
                   WHERE aufgabe_id = ? AND benutzer_id = ?""",
               (aufgabe_id, benutzer_id))


def termin_setzen(db: sqlite3.Connection, benutzer_id: int, aufgabe_id: int,
                  datum: str) -> None:
    """Termin selbst in die Hand nehmen."""
    dt.date.fromisoformat(datum)               # prüft das Format
    _zustand_sichern(db, aufgabe_id, benutzer_id)
    db.execute("""UPDATE lernzustand SET faellig = ?,
                         zustand = CASE WHEN zustand = 'neu' THEN 'lernen'
                                        ELSE zustand END
                   WHERE aufgabe_id = ? AND benutzer_id = ?""",
               (datum, aufgabe_id, benutzer_id))
