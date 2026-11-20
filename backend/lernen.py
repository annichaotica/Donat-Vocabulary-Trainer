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
import lernkern
import regeln as regelmodul
import merkmale as mk

# Reihenfolge, in der fällige Aufgaben genommen werden.
#   verlernt  — was zuletzt schiefging, zuerst
#   faellig   — überfällige vor knapp fälligen
#   neu       — Neues zuletzt, und mengenmäßig begrenzt
NEU_JE_SITZUNG = 20

# Wie viele Fragen ein Tag höchstens hat.
#
# Ohne Grenze ist die Tagesmenge einfach das, was der Terminplan ausspuckt
# — bei tausend Wörtern dreistellig, und nach ein paar Tagen Pause steht
# eine Mauer da, vor der man aufgibt. Mit Grenze ist der Tag immer
# schaffbar, und was darüber hinaus liegt, ist kein Vorwurf, sondern eine
# Zahl, die jeden Tag kleiner wird.
#
# Nichts geht dabei verloren: FSRS verträgt verspätete Wiederholungen,
# die Stabilität wird aus dem tatsächlichen Abstand gerechnet.
FRAGEN_JE_TAG = 80

# Das Tagesziel: wie viele Antworten einen Tag zu einem gelernten Tag
# machen. NICHT dasselbe wie die Tagesdosis darüber, auch wenn beides
# eine Zahl von Fragen am Tag ist:
#
#   Die Dosis ist eine OBERGRENZE — so viel serviert der Trainer
#   höchstens. Sie wird absichtlich hoch gesetzt, und der Lernzielhelfer
#   setzt sie noch höher, damit genug Neues durchkommt (bei einem Ziel
#   mit nahem Termin waren es schon 224).
#
#   Das Ziel ist eine LATTE — so viel nimmt man sich vor.
#
# Die Strähne an der Dosis zu messen war der erste Entwurf, und an den
# echten Daten fiel er sofort durch: bei einer Grenze von 120 stand die
# Strähne auf 0, obwohl an vier Tagen hintereinander 29 bis 123 Fragen
# beantwortet worden waren. Eine Latte, die niemand reißt, weil sie
# niemand erreicht, ist keine.
TAGESZIEL = 20

# Welcher Anteil des Tages dem Neuen offensteht.
#
# Ohne diese Reserve fräße ein Rückstand den ganzen Tag auf: Fälliges
# steht in der Reihenfolge vorn, also käme Neues erst, wenn der Rückstand
# abgearbeitet ist — bei vierhundert offenen Wiederholungen also wochenlang
# nicht. Dann wäre die Grenze genau das, was sie verhindern soll: ein
# Stillstand. Die Hälfte des Tages gehört darum dem Vorankommen.
NEU_ANTEIL = 0.5

# In welcher Folge Neues eingeführt wird: nach Lektion, dann nach der
# Lernreihenfolge innerhalb der Lektion, dann nach Eingabedatum. Wörter
# ohne Lektion kommen zuletzt — sie sind meist selbst nachgetragen.
# Die Lernreihenfolge des Lehrwerks: erst nach Lektion, darin nach der
# vorgegebenen Folge. Die Felder holt die Unterabfrage heraus, damit hier
# außen danach sortiert werden kann.
LERNREIHENFOLGE = ("lektion_nr IS NULL, lektion_nr, wort_folge, lexem_id, typ")

# Wie viele Aufgaben dieses Wortes schon einmal dran waren.
#
# Ohne diese Zahl bleibt ein Wort mit vierzig Formen für immer vorn: der
# Rang INNERHALB des Wortes zählt nur die übrigen Aufgaben, und die werden
# nach jeder Antwort neu durchnummeriert — es gibt also immer wieder eine
# mit Rang 1. Am echten Bestand sah man genau das: drei Wörter im Kreis,
# während 1.280 andere nie drankamen.
#
# Als eigene Teilabfrage und nicht als Unterabfrage je Zeile: über zehn-
# tausend Aufgaben müsste sie sonst zehntausendmal laufen, nur um zu
# sortieren.
SCHON_BEGONNEN = """
    LEFT JOIN (SELECT a2.lexem_id, COUNT(*) AS n
                 FROM aufgabe a2
                 JOIN lernzustand z2 ON z2.aufgabe_id = a2.id
                WHERE z2.benutzer_id = ? AND z2.zustand != 'neu'
                GROUP BY a2.lexem_id) begonnen ON begonnen.lexem_id = l.id"""


def heute() -> dt.date:
    return dt.date.today()


def _jetzt() -> str:
    return dt.datetime.now().isoformat(timespec="seconds")


def _selber_tag(zeitpunkt: str | None, jetzt: dt.datetime | None = None) -> bool:
    """Kam die vorige Antwort am selben KALENDERTAG?

    FSRS entschied das nach exakten 24 Stunden. Der Terminplan rechnet
    aber in Kalendertagen: `faellig` ist ein Datum. Wer abends um 20 Uhr
    lernt und morgens um 9 weitermacht, ist für den Plan einen Tag
    weiter, für die 24-Stunden-Regel aber noch am selben — und bekam die
    Selber-Tag-Formel, die kaum Stabilität zugesteht. Zwölf Minuten
    entschieden über Faktor drei.
    """
    if not zeitpunkt:
        return False                   # noch nie dran
    try:
        davor = dt.datetime.fromisoformat(zeitpunkt)
    except ValueError:
        return False
    return davor.date() == (jetzt or dt.datetime.now()).date()


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
    # 0 heißt ausdrücklich "ohne Grenze" — wer das will, soll es haben.
    dosis = e.get("fragen_je_tag")
    dosis = FRAGEN_JE_TAG if dosis is None else max(0, int(dosis))
    if lg["aktiv"] and lg.get("weniger_neues") and "fragen_je_tag" not in e:
        dosis = min(dosis, 40) if dosis else 40
    # Das Tagesziel kann die Dosis nicht überschreiten: mehr als serviert
    # wird, kann niemand beantworten. Wer seine Grenze auf zehn stellt,
    # hat damit auch sein Ziel auf zehn gestellt.
    ziel = max(1, int(e.get("tagesziel", TAGESZIEL)))
    if dosis:
        ziel = min(ziel, dosis)
    stil = e.get("beschriftung", "fach")
    return {
        "wunschretention": retention,
        "neu_je_sitzung": neu,
        # Die Tagesdosis in Fragen. 0 = ohne Grenze.
        "fragen_je_tag": dosis,
        # Die Latte für einen gelernten Tag — siehe TAGESZIEL oben.
        "tagesziel": ziel,
        "name": b["name"],
        "legasthenie": lg,
        # Neues durchgehend untermischen statt erst nach allem Fälligen?
        # Mehr Abwechslung, dafür rücken echte Wiederholungen nach hinten.
        "neues_einstreuen": bool(e.get("neues_einstreuen", False)),
        # Wie Formen benannt werden: fach | einfach | beides
        "beschriftung": stil if stil in mk.STILE else "fach",
        # Lateinische Tasten in die Zielschrift umsetzen, ohne das
        # Systemlayout umzuschalten. Voreingestellt an: wer wirklich
        # umgeschaltet hat, merkt nichts davon — Zeichen, die schon in
        # der Zielschrift ankommen, gehen unangetastet durch.
        "tastatur_umschrift": bool(e.get("tastatur_umschrift", True)),
        # Nach einer sauber richtigen Antwort von selbst weiterspringen.
        # Voreingestellt AUS: eine Seite, die sich von allein bewegt,
        # muss man wollen.
        "weiterspringen": bool(e.get("weiterspringen", False)),
    }


# Die Lektionsschranke: keine Formgruppe, die das Lehrwerk noch nicht
# eingeführt hat.
#
# Steht als SQL-Baustein da und nicht als Nachfilter in Python, weil das
# hier die wiederkehrende Fehlerquelle ist: die Abfrage holt ein Fenster
# der dringendsten Zeilen, und wer danach aussiebt, bekommt ein leeres
# Ergebnis, sobald die Ordnung genau das nach vorn stellt, was der
# Filter wegwirft. Die Bedingung gehört in die Abfrage.
#
# Dreimal durchlässig, und zwar mit Absicht:
#   - `a.formgruppe IS NULL`  — Bedeutungen und Genus haben keine Zeit
#   - keine Zuordnung         — über eine Gruppe, zu der niemand gesagt
#                               hat, wann sie drankommt, wird nicht
#                               stillschweigend entschieden
#   - kein Buchstand          — wer nichts eingestellt hat, bekommt alles
#
# Ein `?` für die benutzer_id.
LEKTIONSSCHRANKE_SQL = """(a.formgruppe IS NULL OR NOT EXISTS (
    SELECT 1 FROM formgruppe_lektion g
      JOIN buchstand b ON b.sammlung_id = g.sammlung_id
                      AND b.benutzer_id = ?
     WHERE g.sammlung_id = l.sammlung_id
       AND g.formgruppe = a.formgruppe
       AND g.ab_lektion > b.bis_lektion))"""


# Dieselbe Schranke, aber gegen eine GENANNTE Lektion statt gegen den
# persönlichen Buchstand.
#
# »Bei meinem Lernziel wird wieder der Aorist abgefragt, obwohl er gar
# nicht für diese Lektionen freigeschaltet wurde.« — Sie hatte recht,
# und zwar grundsätzlich: wer ein Ziel auf Lektion 2 und 3 schneidet,
# sagt damit schon, wie weit er ist. Eine zweite Zahl dafür zu
# verlangen wäre, dieselbe Auskunft zweimal zu fordern — und solange
# die zweite fehlt, passiert gar nichts. Genau so ist es passiert.
#
# Ein `?` für die Lektionsnummer, bis zu der gelernt wird.
LEKTIONSGRENZE_SQL = """(a.formgruppe IS NULL OR NOT EXISTS (
    SELECT 1 FROM formgruppe_lektion g
     WHERE g.sammlung_id = l.sammlung_id
       AND g.formgruppe = a.formgruppe
       AND g.ab_lektion > ?))"""


def sichtbare_sammlungen(db: sqlite3.Connection, benutzer_id: int) -> list[int]:
    """Eigene Sammlungen und die, die mir freigegeben wurden.

    Das ist die SICHTBARKEIT — wer darf hineinsehen und mitpflegen. Was
    abgefragt wird, sagt `lernsammlungen`; die beiden fallen
    auseinander, sobald jemand eine fremde Sammlung nur berichtigt.
    """
    return [z["id"] for z in dbm.zeilen(db, """
        SELECT s.id FROM sammlung s WHERE s.besitzer_id = ?
        UNION
        SELECT f.sammlung_id FROM freigabe f WHERE f.benutzer_id = ?""",
        (benutzer_id, benutzer_id))]


def lernsammlungen(db: sqlite3.Connection, benutzer_id: int) -> list[int]:
    """Woraus wird abgefragt, wenn keine Sammlung gewählt ist?

    »Wenn ich schon die Sammlungen der anderen sehe, würde ich gerne
    einstellen können, dass ich diese nicht aktiv lerne.« — Das traf
    zu: die Freigabe auf das fremde Französisch trug das Recht
    `schreiben`, also zum Mitpflegen, und trotzdem lagen die 36
    französischen Wörter im allgemeinen Lernen zwischen den
    griechischen.

    Vorgabe ist der Besitz, Abweichungen stehen in `lernwahl`. Die
    Bedingung gehört in die Abfrage und nicht hinterher davor — sonst
    wäre es wieder der Fehler, ein Fenster nachzusortieren.
    """
    return [z["id"] for z in dbm.zeilen(db, """
        SELECT s.id
          FROM sammlung s
          LEFT JOIN lernwahl w
                 ON w.sammlung_id = s.id AND w.benutzer_id = ?
         WHERE (s.besitzer_id = ?
                OR s.id IN (SELECT sammlung_id FROM freigabe
                             WHERE benutzer_id = ?))
           AND COALESCE(w.lernen, s.besitzer_id = ?) = 1""",
        (benutzer_id,) * 4)]


def lernwahl_setzen(db: sqlite3.Connection, benutzer_id: int,
                    sammlung_id: int, lernen: bool) -> None:
    """Trägt eine Abweichung ein — oder räumt sie weg, wenn sie der
    Vorgabe entspricht. So bleibt die Tabelle leer, solange niemand
    etwas umgestellt hat, und ein Besitzerwechsel zieht die Vorgabe
    einfach mit."""
    eigen = bool(dbm.wert(db, """SELECT besitzer_id = ? FROM sammlung
                                  WHERE id = ?""", (benutzer_id, sammlung_id)))
    if bool(lernen) == eigen:
        db.execute("""DELETE FROM lernwahl
                       WHERE benutzer_id = ? AND sammlung_id = ?""",
                   (benutzer_id, sammlung_id))
    else:
        db.execute("""INSERT INTO lernwahl (benutzer_id, sammlung_id, lernen)
                      VALUES (?, ?, ?)
                      ON CONFLICT (benutzer_id, sammlung_id)
                      DO UPDATE SET lernen = excluded.lernen""",
                   (benutzer_id, sammlung_id, int(bool(lernen))))


def _zustand_sichern(db: sqlite3.Connection, aufgabe_id: int,
                     benutzer_id: int) -> dict:
    """Legt den Lernzustand an, falls er noch fehlt."""
    return lernkern.zustand_sichern(db, lernkern.VOKABELN, aufgabe_id,
                                    benutzer_id)


def stand(db: sqlite3.Connection, benutzer_id: int,
          sammlung_id: int | None = None) -> dict:
    """Was liegt an? Zahlen für die Übersicht."""
    sammlungen = ([sammlung_id] if sammlung_id
                  else lernsammlungen(db, benutzer_id))
    if not sammlungen:
        return {"faellig": 0, "neu": 0, "verlernt": 0, "reif": 0, "gesamt": 0,
                "heute_erledigt": 0, "heute_offen": 0, "heute_gesamt": 0,
                "tagesdosis": 0, "rueckstand": 0, "neue_woerter_frei": 0}
    platzhalter = ",".join("?" * len(sammlungen))
    heute_text = heute().isoformat()
    # Die Schranke zählt hier MIT. Liefe sie nur in der Abfrage, stünde
    # auf der Übersicht eine Zahl, die das Lernen nie einlöst — derselbe
    # Fehler wie damals »dein Tagespensum ist erledigt« über einem
    # Block, mit dem noch gar nichts gelernt war.
    grund = f"""
        FROM aufgabe a
        JOIN lexem l ON l.id = a.lexem_id
        LEFT JOIN lernzustand z
               ON z.aufgabe_id = a.id AND z.benutzer_id = ?
        WHERE a.aktiv = 1 AND l.sammlung_id IN ({platzhalter})
          AND {LEKTIONSSCHRANKE_SQL}"""
    werte = (benutzer_id, *sammlungen, benutzer_id)
    zahl = lambda bedingung, zusatz=(): dbm.wert(
        db, f"SELECT COUNT(*) {grund} AND {bedingung}", (*werte, *zusatz)) or 0
    e = benutzer_einstellungen(db, benutzer_id)
    morgen = (heute() + dt.timedelta(days=1)).isoformat()
    erledigt = dbm.wert(db, """
        SELECT COUNT(*) FROM wiederholung
         WHERE benutzer_id = ? AND zeitpunkt >= ? AND zeitpunkt < ?""",
        (benutzer_id, heute_text, morgen)) or 0
    # Wie viele WÖRTER heute schon angefangen wurden — der Tagesvorrat
    # zählt Wörter, nicht Aufgaben.
    begonnen = {z["lexem_id"] for z in dbm.zeilen(db, f"""
        SELECT DISTINCT a.lexem_id FROM wiederholung w
          JOIN aufgabe a ON a.id = w.aufgabe_id
          JOIN lexem l ON l.id = a.lexem_id
         WHERE w.benutzer_id = ? AND w.zeitpunkt >= ? AND w.zeitpunkt < ?
           AND w.stabilitaet_vor IS NULL
           AND l.sammlung_id IN ({platzhalter})""",
        (benutzer_id, heute_text, morgen, *sammlungen))}
    rest_woerter = max(0, e["neu_je_sitzung"] - len(begonnen))

    faellig = zahl("z.zustand IN ('lernen','reif') AND z.faellig <= ?",
                   (heute_text,))
    verlernt = zahl("z.zustand = 'verlernt'")
    # Was heute noch an NEUEM dazukommt: die Aufgaben der nächsten Wörter,
    # so weit der Vorrat reicht. Ohne diese Zahl weiß niemand, ob die
    # Abfrage in zehn Fragen zu Ende ist oder in dreihundert.
    neu_offen = 0
    if rest_woerter:
        for z in dbm.zeilen(db, f"""
                SELECT l.id, COUNT(*) AS aufgaben
                  FROM lexem l JOIN aufgabe a ON a.lexem_id = l.id AND a.aktiv = 1
                  LEFT JOIN lernzustand z
                         ON z.aufgabe_id = a.id AND z.benutzer_id = ?
                 WHERE l.sammlung_id IN ({platzhalter})
                   AND (z.zustand IS NULL OR z.zustand = 'neu')
                 GROUP BY l.id
                 ORDER BY (SELECT k.nr FROM lektion k WHERE k.id = l.lektion_id)
                            IS NULL,
                          (SELECT k.nr FROM lektion k WHERE k.id = l.lektion_id),
                          l.reihenfolge, l.id
                 LIMIT ?""",
                (benutzer_id, *sammlungen, rest_woerter + len(begonnen))):
            if z["id"] in begonnen:
                continue
            neu_offen += z["aufgaben"]
            rest_woerter -= 1
            if rest_woerter <= 0:
                break
    # Angefangene Wörter bringen ihre übrigen Aufgaben heute noch mit.
    if begonnen:
        neu_offen += dbm.wert(db, f"""
            SELECT COUNT(*) FROM aufgabe a
              JOIN lexem l ON l.id = a.lexem_id
              LEFT JOIN lernzustand z
                     ON z.aufgabe_id = a.id AND z.benutzer_id = ?
             WHERE a.aktiv = 1 AND l.id IN ({','.join('?' * len(begonnen))})
               AND (z.zustand IS NULL OR z.zustand = 'neu')""",
            (benutzer_id, *begonnen)) or 0

    offen = faellig + verlernt + neu_offen
    # Die Tagesdosis schneidet das Pensum zu. Angezeigt wird, was heute
    # wirklich drankommt; was darüber hinaus wartet, steht daneben als
    # Rückstand — eine Zahl, die kleiner wird, keine Mauer.
    dosis = e["fragen_je_tag"]
    heute_offen = offen
    rueckstand = 0
    if dosis:
        heute_offen = max(0, min(offen, dosis - erledigt))
        rueckstand = offen - heute_offen
    return {
        "gesamt": dbm.wert(db, f"SELECT COUNT(*) {grund}", werte) or 0,
        "neu": zahl("(z.zustand IS NULL OR z.zustand = 'neu')"),
        "faellig": faellig,
        "verlernt": verlernt,
        "reif": zahl("z.zustand = 'reif'"),
        "ausgesetzt": zahl("z.zustand = 'ausgesetzt'"),
        # Das Tagespensum: wie viel heute schon erledigt ist und wie viel
        # noch kommt. Eine Abfrage endet, wenn beides aufgeht.
        "heute_erledigt": erledigt,
        "heute_offen": heute_offen,
        "heute_gesamt": erledigt + heute_offen,
        # Die Grenze selbst (0 = ohne) und was heute nicht mehr drankommt.
        # Keine Schätzung, wie lange das Aufholen dauert: die hinge daran,
        # wie viel täglich neu fällig wird, und wäre erfunden.
        "tagesdosis": dosis,
        "rueckstand": rueckstand,
        "neue_woerter_frei": max(0, e["neu_je_sitzung"] - len(begonnen)),
    }


# Wie viele zuletzt gefragte Wörter gemieden werden, solange es Auswahl
# gibt. Zwei reichen hierfür: so entsteht weder eine unmittelbare
# Wiederholung noch ein Hin und Her zwischen genau zweien. Gegen einen
# Dreierkreis hilft nicht dieses Fenster, sondern die Runde darunter.
ZULETZT_MEIDEN = 2


def _rundenstand(db: sqlite3.Connection, benutzer_id: int) -> dict[int, int]:
    """Wie oft jedes Wort heute schon dran war."""
    return lernkern.rundenstand(db, lernkern.VOKABELN, benutzer_id)


def _runden_sql(stand: dict[int, int], spalte: str = "lexem_id") -> str:
    """Dieselbe Regel als Sortierausdruck für die Abfrage.

    Nachträglich zu sortieren genügt hier nicht: das Fenster holt nur
    `anzahl * 4` Zeilen, und darin stehen bei einer laufenden Sitzung
    überwiegend schon gesehene Wörter. Gemessen: die ersten zwölf Fragen
    brachten nur sieben verschiedene Wörter, obwohl zwölf bereitlagen.
    Zum dritten Mal dieselbe Lehre — die Bedingung gehört in die Abfrage.

    Die Werte stehen fest verdrahtet im Ausdruck, nicht als Platzhalter:
    es sind Zahlen aus der eigenen Datenbank, keine Eingaben, und `int()`
    lässt nichts anderes durch.
    """
    teile = " ".join(f"WHEN {int(lid)} THEN {int(n)}"
                     for lid, n in (stand or {}).items() if lid is not None)
    # Nicht "0" zurückgeben: eine nackte Zahl im ORDER BY ist in SQLite
    # eine SPALTENNUMMER, kein Wert. Lieber nichts.
    return lernkern.runden_sql(stand, spalte)


def _rundenweise(reihe: list[dict], stand: dict[int, int]) -> list[dict]:
    """Erst jedes Wort einmal, dann das zweite Mal.

    Der Einwand, der diese Regel gebracht hat: »wäre es denn nicht
    sinnvoller, erstmal die 40 Begriffe durchzurotieren und dann die
    schlecht beantworteten wieder zu bringen?«

    Vorher entschied allein die Dringlichkeit — und die ist nach einem
    »Nochmal« sofort wieder maximal. Drei Wörter genügten für einen
    Kreis, aus dem achtunddreißig unberührte Wörter nicht hineinkamen.
    Gegen so etwas hilft kein Meidefenster: man müsste es immer eins
    größer machen als den Kreis, den es gerade gibt.

    Sortiert wird STABIL, die bestehende Reihenfolge bleibt also
    innerhalb einer Runde erhalten. Die Dringlichkeit ordnet damit noch
    immer — nur nicht mehr über die Runde hinweg.
    """
    return lernkern.rundenweise(reihe, stand, "lexem_id")


def _schon_gefragt_heute(db: sqlite3.Connection, benutzer_id: int) -> int:
    """Wie viele Abfragen heute schon waren — als Zähler zum Abwechseln.

    Aus dem Protokoll statt aus einem Sitzungszustand: der Server hält
    keine Sitzung, und über Geräte hinweg soll es trotzdem stimmen.
    """
    return dbm.wert(db, """
        SELECT COUNT(*) FROM wiederholung
         WHERE benutzer_id = ? AND zeitpunkt >= ? AND zeitpunkt < ?""",
        (benutzer_id, heute().isoformat(),
         (heute() + dt.timedelta(days=1)).isoformat())) or 0


def _tagesstand(db: sqlite3.Connection, benutzer_id: int) -> dict:
    """Was heute schon gelaufen ist, getrennt nach Neuem und Wiederholung.

    `stabilitaet_vor IS NULL` kennzeichnet die erste Begegnung mit einer
    Aufgabe — daran hängt die Unterscheidung, und daran allein, denn der
    Server hält keine Sitzung.
    """
    z = dbm.zeile(db, """
        SELECT COUNT(*) AS gesamt,
               SUM(CASE WHEN stabilitaet_vor IS NULL THEN 1 ELSE 0 END) AS neu
          FROM wiederholung
         WHERE benutzer_id = ? AND zeitpunkt >= ? AND zeitpunkt < ?""",
        (benutzer_id, heute().isoformat(),
         (heute() + dt.timedelta(days=1)).isoformat()))
    gesamt = (z["gesamt"] if z else 0) or 0
    neu = (z["neu"] if z else 0) or 0
    return {"gesamt": gesamt, "neu": neu, "wiederholung": gesamt - neu}


def _dosis_rest(einstellungen: dict, tag: dict) -> dict | None:
    """Wie viel vom Tagespensum noch offen ist — None heißt: ohne Grenze.

    Die beiden Teilbeträge sind keine festen Fächer. Was das eine nicht
    braucht, darf das andere nehmen; begrenzt ist nur die Summe. Sonst
    endete ein Tag ohne neues Material vorzeitig, obwohl noch Luft wäre.
    """
    dosis = einstellungen["fragen_je_tag"]
    if not dosis:
        return None
    gesamt = max(0, dosis - tag["gesamt"])
    fuer_neu = round(dosis * NEU_ANTEIL)
    return {
        "gesamt": gesamt,
        "neu": min(gesamt, max(0, fuer_neu - tag["neu"])),
        "wiederholung": min(gesamt, max(0, dosis - fuer_neu
                                        - tag["wiederholung"])),
    }


def _vorzug(rest: dict | None) -> str | None:
    """Welcher Topf an der Reihe ist: "neu", "wiederholung" oder keiner.

    Hat das Fällige seinen Anteil verbraucht, kommt Neues dran, obwohl
    noch Wiederholungen offen sind — genau darum geht es: auch bei
    Rückstand jeden Tag ein Stück vorankommen.
    """
    if rest is None:
        return None
    if rest["neu"] <= 0 < rest["wiederholung"]:
        return "wiederholung"
    if rest["wiederholung"] <= 0 < rest["neu"]:
        return "neu"
    return None


def _nach_vorzug_waehlen(reihe: list[dict], vorzug: str | None) -> list[dict]:
    """Dasselbe als Sieb — für eine Reihe, die schon fertig gestellt ist.

    Taugt nur, wo die Auswahl ohnehin vollständig vorliegt (Lernzielblock).
    Beim Abruf aus der Datenbank wäre es falsch: dort umfasst das Fenster
    nur wenige Zeilen, und bei Rückstand stünde darin nie etwas Neues.
    """
    if vorzug is None:
        return reihe
    ist_neu = lambda r: r.get("zustand") in (None, "neu")
    passend = [r for r in reihe
               if ist_neu(r) == (vorzug == "neu")]
    return passend or reihe


def _zuletzt_gefragt(db: sqlite3.Connection, benutzer_id: int,
                     anzahl: int = ZULETZT_MEIDEN) -> list[int]:
    """Die zuletzt gefragten Wörter dieser Person.

    Gebraucht, weil die Oberfläche je EINE Aufgabe holt und der Block bei
    jedem Abruf neu gerechnet wird. Ohne dieses Gedächtnis stünde das
    soeben falsch beantwortete Wort sofort wieder vorn — es ist ja das
    dringendste —, und man bekäme dasselbe Wort ein Dutzend Mal
    hintereinander. Genau so fühlte es sich auch an.
    """
    gesehen: list[int] = []
    for z in dbm.zeilen(db, """
            SELECT a.lexem_id FROM wiederholung w
              JOIN aufgabe a ON a.id = w.aufgabe_id
             WHERE w.benutzer_id = ?
             ORDER BY w.zeitpunkt DESC, w.id DESC LIMIT 40""", (benutzer_id,)):
        if z["lexem_id"] not in gesehen:
            gesehen.append(z["lexem_id"])
        if len(gesehen) >= anzahl:
            break
    return gesehen


def _abstand_halten(reihe: list[dict], meiden: list[int],
                    anzahl: int) -> list[dict]:
    """Stellt die zuletzt gefragten Wörter hintan — aber nur, solange es
    etwas anderes gibt. Bleibt am Ende nur noch ein Wort übrig, wird es
    selbstverständlich gefragt."""
    if not meiden:
        return reihe
    frisch = [r for r in reihe if r["lexem_id"] not in meiden]
    spaeter = [r for r in reihe if r["lexem_id"] in meiden]
    return (frisch + spaeter) if len(frisch) >= min(anzahl, 1) else reihe


# Jede wievielte Frage ein neues Wort sein darf, wenn eingestreut wird.
# Drei zu eins: genug Abwechslung, ohne dass das Fällige liegenbleibt.
EINSTREUEN_JEDE = 3


def _ist_neu(r: dict) -> bool:
    return (r.get("zustand") or "neu") == "neu"


def _neues_einstreuen(reihe: list[dict], nachschub: list[dict],
                      zaehler: int, meiden: list[int] | None = None
                      ) -> list[dict]:
    """Holt gelegentlich etwas Neues nach vorn, auch wenn noch Fälliges da ist.

    Ohne das arbeitet man erst alles Fällige ab und sieht stundenlang
    dieselben Wörter; mit ihm kommt zwischendurch etwas Neues. Der Preis
    ist, dass echte Wiederholungen etwas nach hinten rücken — darum ist es
    eine Einstellung und keine Vorgabe.

    `nachschub` wird eigens geholt: bei großem Rückstand enthält das
    normale Abfragefenster überhaupt nichts Neues, das sich vorziehen
    ließe.
    """
    if zaehler % EINSTREUEN_JEDE != EINSTREUEN_JEDE - 1:
        return reihe
    schon = next((i for i, r in enumerate(reihe) if _ist_neu(r)), None)
    if schon is not None:
        return ([reihe[schon]] + [r for i, r in enumerate(reihe) if i != schon]
                if schon else reihe)
    if not nachschub:
        return reihe
    vorhanden = {r["aufgabe_id"] for r in reihe}
    frei = [r for r in nachschub if r["aufgabe_id"] not in vorhanden]
    # Am liebsten ein Wort, das gerade nicht dran war — sonst holt man
    # sich die Einseitigkeit durch die Hintertür wieder herein.
    neu = next((r for r in frei if r["lexem_id"] not in (meiden or [])),
               next(iter(frei), None))
    return [neu] + [r for r in reihe if r["aufgabe_id"] != neu["aufgabe_id"]] \
        if neu else reihe


def _dringlichkeitsstufe(r: dict) -> tuple:
    """Woran sich bemisst, ob zwei Aufgaben GLEICH dringend sind."""
    zustand = r.get("zustand") or "neu"
    rang = {"verlernt": 0, "lernen": 1, "reif": 1}.get(zustand, 3)
    return (rang, r.get("faellig") or "")


def _abwechseln(reihe: list[dict], saat: int) -> list[dict]:
    """Unter GLEICH dringenden Aufgaben nicht immer dieselbe zuerst.

    Die Oberfläche holt je eine Aufgabe und nimmt den Kopf der Liste.
    Sind drei Wörter gleich dringend, stand damit immer dasselbe vorn und
    es entstand ein starrer Dreierzyklus — γράφω, διαβάζω, παίζω, γράφω …
    Das ist kaum besser als dasselbe Wort zweimal.

    Gedreht wird nur innerhalb einer Stufe; die Rangfolge zwischen
    verlernt, fällig und neu bleibt unangetastet.
    """
    if len(reihe) <= 1:
        return reihe
    stufe = _dringlichkeitsstufe(reihe[0])
    gleich = [i for i, r in enumerate(reihe)
              if _dringlichkeitsstufe(r) == stufe]
    if len(gleich) <= 1:
        return reihe
    gewaehlt = gleich[saat % len(gleich)]
    return [reihe[gewaehlt]] + [r for i, r in enumerate(reihe)
                                if i != gewaehlt]


def naechste(db: sqlite3.Connection, benutzer_id: int,
             sammlung_id: int | None = None,
             lektion_id: int | None = None,
             typen: list[str] | None = None,
             wortarten: list[str] | None = None,
             formgruppen: list[str] | None = None,
             nur: str | None = None,
             anzahl: int = 1,
             lernziel_id: int | None = None,
             bis_lektion: int | None = None,
             ohne_grenze: bool = False,
             _ohne_vorzug: bool = False) -> list[dict]:
    """Die nächsten Aufgaben.

    nur:  None       — planmäßig: verlernt, dann fällig, dann neu
          "neu"      — nur Neues
          "faellig"  — nur Fälliges, kein Neues
          "frei"     — freies Üben: alles, ohne Terminlogik
          "fehler"   — was zuletzt schiefging

    Die Tagesdosis begrenzt nur die planmäßige Abfrage (nur=None) und den
    Lernzielblock. Wer ausdrücklich "nur Fälliges" oder "freies Üben"
    wählt, hat sich schon entschieden; dem redet die Grenze nicht herein.
    `ohne_grenze` ist der Knopf "trotzdem weitermachen" am Tagesende.
    """
    # Ein Lernziel schneidet den Bestand zu — und zwar quer über Lektionen
    # und Sammlungen. Der Block entscheidet dann über die Reihenfolge.
    if lernziel_id is not None:
        import lernziele
        # Der Block wird in brauchbarer Größe gerechnet, auch wenn nur eine
        # Aufgabe abgeholt wird: bei Blockgröße 1 kann die Verschränkung
        # nichts verschränken und der Zuschnitt verliert seinen Sinn.
        e = benutzer_einstellungen(db, benutzer_id)
        rest = None if ohne_grenze else _dosis_rest(
            e, _tagesstand(db, benutzer_id))
        if rest is not None and rest["gesamt"] <= 0:
            return []          # Tagespensum voll. Was fehlt, sagt stand().
        plan = lernziele.block(db, benutzer_id, lernziel_id, max(anzahl, 20))
        ergebnis = []
        gewaehlt = _nach_vorzug_waehlen(plan["aufgaben"], _vorzug(rest))
        gewaehlt = _abwechseln(gewaehlt,
                               _schon_gefragt_heute(db, benutzer_id))
        meiden = _zuletzt_gefragt(db, benutzer_id)
        gewaehlt = _rundenweise(gewaehlt, _rundenstand(db, benutzer_id))
        gewaehlt = _abstand_halten(gewaehlt, meiden, anzahl)
        # Auch hier Neues einstreuen, wenn der Schalter an ist.
        #
        # Er wirkte nur im normalen Weg — im Lernziel nicht, und genau
        # dort fällt es auf: der Block stellt Verlerntes und Wackliges
        # nach vorn, und wer eine Antwort mit »Nochmal« bewertet, macht
        # das Wort sofort wieder zum dringendsten. Gemessen am
        # Protokoll: 18 Antworten, drei Wörter, im Kreis — während
        # achtunddreißig unberührte danebenlagen. Das Abstandhalten
        # meidet nur die letzten zwei und ist gegen einen Dreierkreis
        # machtlos.
        if e["neues_einstreuen"]:
            nachschub = [a for a in plan["aufgaben"]
                         if a.get("zustand") in (None, "neu")]
            if rest is not None and rest["neu"] <= 0:
                nachschub = []          # Tagesanteil fürs Neue ist voll
            if nachschub:
                gewaehlt = _neues_einstreuen(
                    gewaehlt, nachschub, _schon_gefragt_heute(db, benutzer_id),
                    meiden)
        for eintrag in gewaehlt[:anzahl]:
            z = _zustand_sichern(db, eintrag["aufgabe_id"], benutzer_id)
            ergebnis.append({
                **_aufgabe_ausbauen(db, {**dict(z),
                                         "aufgabe_id": eintrag["aufgabe_id"],
                                         "typ": eintrag["typ"]},
                                    e["wunschretention"], e["legasthenie"],
                                    e["beschriftung"]),
                "herkunft": eintrag["herkunft"],
                # Der Stand des ZIELS, nicht des Tages.
                #
                # »Warum steht beim Lernziel 70 von 120 heute und in
                # der Übersicht 0 von 28?« — Weil der Balken in der
                # Abfrage das Tagespensum misst, über alle Sammlungen
                # und Ziele zusammen. Das ist richtig und steht an der
                # falschen Stelle: wer gerade ein Ziel abfragt, will
                # dessen Fortschritt sehen. Gerechnet ist er ohnehin,
                # der Block braucht ihn selbst.
                "lernziel": {"id": lernziel_id, "name": plan["name"],
                             "begruendung": plan["begruendung"],
                             "ziel": plan["fortschritt"]["ziel"],
                             "gesamt": plan["fortschritt"]["gesamt"],
                             "geschafft": plan["fortschritt"]["geschafft"],
                             "angefangen": plan["fortschritt"]["angefangen"],
                             "lage": plan["fortschritt"]["lage"]},
            })
        return ergebnis

    sammlungen = ([sammlung_id] if sammlung_id
                  else lernsammlungen(db, benutzer_id))
    if not sammlungen:
        return []
    e = benutzer_einstellungen(db, benutzer_id)
    rest = None
    if nur is None and not ohne_grenze:
        rest = _dosis_rest(e, _tagesstand(db, benutzer_id))
        if rest is not None and rest["gesamt"] <= 0:
            return []          # Tagespensum voll. Was fehlt, sagt stand().
    vorzug = None if _ohne_vorzug else _vorzug(rest)
    heute_text = heute().isoformat()

    # Welche Wörter heute schon angefangen wurden, und wie viele noch
    # dürfen. Muss VOR der Abfrage feststehen: der Vorrat gehört in die
    # Bedingung, nicht hinterher ins Sieb (siehe tests/test_wortvorrat.py).
    # Und je Sammlung gezählt, genau wie in stand() — sonst meldet die
    # Übersicht für die zweite Sammlung offene Fragen, die nie kommen.
    rundenstand = _rundenstand(db, benutzer_id)
    heute_begonnen: set[int] = set()
    rest_neu = e["neu_je_sitzung"]
    if nur is None:
        morgen = (heute() + dt.timedelta(days=1)).isoformat()
        # Tagesgrenzen statt date() auf der Spalte: so greift der Index
        # idx_wiederholung_zeit. Mit date() wird bei jedem Aufgabenabruf das
        # ganze Protokoll des Benutzers gelesen, und das wird nie geleert.
        heute_begonnen = {z["lexem_id"] for z in dbm.zeilen(db, f"""
            SELECT DISTINCT a.lexem_id FROM wiederholung w
              JOIN aufgabe a ON a.id = w.aufgabe_id
              JOIN lexem l ON l.id = a.lexem_id
             WHERE w.benutzer_id = ?
               AND w.zeitpunkt >= ? AND w.zeitpunkt < ?
               AND w.stabilitaet_vor IS NULL
               AND l.sammlung_id IN ({','.join('?' * len(sammlungen))})""",
            (benutzer_id, heute_text, morgen, *sammlungen))}
        rest_neu = max(0, e["neu_je_sitzung"] - len(heute_begonnen))

    bedingungen = [f"l.sammlung_id IN ({','.join('?' * len(sammlungen))})",
                   "a.aktiv = 1", LEKTIONSSCHRANKE_SQL]
    werte: list = [benutzer_id, *sammlungen, benutzer_id]
    # Die Lernmodi: »nur Verben«, »nur eine Zeitform«, »nur Adjektive«.
    #
    # Dieselben Begriffe, die der Umfang eines Lernziels kennt — und
    # dieselben Spalten. Ein Modus ist kein eigener Mechanismus,
    # sondern ein Ausschnitt; ein zweiter Weg daneben liefe früher oder
    # später auseinander, wie es `uebung_lernen` schon einmal tat.
    for auswahl, spalte in ((wortarten, "l.wortart"),
                            (formgruppen, "a.formgruppe")):
        if auswahl:
            bedingungen.append(
                f"{spalte} IN ({','.join('?' * len(auswahl))})")
            werte += list(auswahl)
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
        # Und dieselbe Grenze gilt für die FORMEN. Wer bis Lektion 12
        # mitlernt, hat den Aorist aus Lektion 39 nicht gehabt — die
        # Wörter von Lektion 12 bringen ihre Aoristformen aber mit.
        bedingungen.append(LEKTIONSGRENZE_SQL)
        # Zweimal: einmal für die Lektionsgrenze der Wörter, einmal für
        # die der Formen.
        werte += [bis_lektion, bis_lektion]
    if typen:
        bedingungen.append(f"a.typ IN ({','.join('?' * len(typen))})")
        werte += list(typen)
    # Der Ausschnitt OHNE die Bedingung zum Lernstand — gebraucht, um für
    # das Einstreuen eigens Neues zu holen.
    grundbedingungen = list(bedingungen)
    grundwerte = list(werte[1:])

    # Die Sortierung ist die eigentliche Entscheidung. Sie steht hier
    # vollständig und ist in der Oberfläche als "Warum jetzt?" nachlesbar.
    if nur == "neu":
        bedingungen.append("(z.zustand IS NULL OR z.zustand = 'neu')")
        ordnung = f"schon_begonnen, rang_im_wort, {LERNREIHENFOLGE}"
    elif nur == "faellig":
        bedingungen.append(
            "z.zustand IN ('lernen','reif','verlernt') AND z.faellig <= ?")
        werte.append(heute_text)
        ordnung = "faellig, stabilitaet"
    elif nur == "fehler":
        bedingungen.append("z.anzahl_fehler > 0 AND z.zustand != 'ausgesetzt'")
        ordnung = "anzahl_fehler DESC, faellig"
    elif nur == "frei":
        bedingungen.append("(z.zustand IS NULL OR z.zustand != 'ausgesetzt')")
        ordnung = "RANDOM()"
    else:
        if vorzug == "neu":
            # Der Tagesanteil fürs Fällige ist verbraucht; jetzt gehört
            # der Rest dem Vorankommen.
            bedingungen.append("(z.zustand IS NULL OR z.zustand = 'neu')")
        elif vorzug == "wiederholung":
            bedingungen.append("""(
                z.zustand = 'verlernt'
                OR (z.zustand IN ('lernen','reif') AND z.faellig <= ?)
            )""")
            werte.append(heute_text)
        else:
            # Ist der Tagesvorrat an WÖRTERN aufgebraucht, darf Neues nur
            # noch von den heute angefangenen Wörtern kommen. Stünde das
            # erst im Sieb hinter der Abfrage, holte das Fenster
            # (anzahl * 4 Zeilen) ausschließlich Verbotenes: die
            # Sortierung stellt ja gerade die noch unberührten Wörter
            # nach vorn. Übrig bliebe nichts, und die Sitzung endete nach
            # genau `neu_je_sitzung` Fragen.
            if rest_neu <= 0 and heute_begonnen:
                neu_zweig = (f"""((z.zustand IS NULL OR z.zustand = 'neu')
                                  AND l.id IN
                                  ({','.join('?' * len(heute_begonnen))}))""")
                neu_werte = list(heute_begonnen)
            elif rest_neu <= 0:
                neu_zweig, neu_werte = "0", []     # heute nichts Neues mehr
            else:
                neu_zweig, neu_werte = "(z.zustand IS NULL OR z.zustand = 'neu')", []
            bedingungen.append(f"""(
                {neu_zweig}
                OR (z.zustand = 'verlernt')
                OR (z.zustand IN ('lernen','reif') AND z.faellig <= ?)
            )""")
            werte += neu_werte
            werte.append(heute_text)
        # verlernt zuerst, dann nach Fälligkeit, Neues zuletzt — und
        # innerhalb des Neuen von jedem Wort erst die erste Aufgabe.
        # Erst Verlerntes und Fälliges, dann Neues — und innerhalb des
        # Neuen die Wörter zuerst, von denen noch am wenigsten dran war.
        ordnung = """
            CASE zustand WHEN 'verlernt' THEN 0
                         WHEN 'lernen' THEN 1
                         WHEN 'reif' THEN 1
                         ELSE 3 END,
            faellig,
            schon_begonnen,
            rang_im_wort,
            """ + LERNREIHENFOLGE

    # rang_im_wort nummeriert die Aufgaben INNERHALB eines Wortes. Wird
    # danach zuerst sortiert, kommt von jedem Wort erst die erste Aufgabe,
    # dann von jedem die zweite — statt vierzig Formen desselben Verbs
    # hintereinander. Blockweises Üben fühlt sich leichter an und behält
    # schlechter; verschränktes ist mühsamer und sitzt.
    # Die Runde steht VOR allem anderen: erst jedes Wort einmal, dann
    # das zweite Mal. Die Dringlichkeit ordnet innerhalb der Runde.
    runde = _runden_sql(rundenstand)
    if runde:
        ordnung = f"{runde}, {ordnung}"
    sql = f"""
        SELECT * FROM (
          SELECT a.id AS aufgabe_id, a.typ, l.id AS lexem_id, l.lemma,
                 l.sammlung_id, z.zustand, z.stabilitaet, z.schwierigkeit,
                 z.faellig, z.letzte_wiederholung, z.anzahl, z.anzahl_fehler,
                 l.reihenfolge AS wort_folge,
                 COALESCE(begonnen.n, 0) AS schon_begonnen,
                 (SELECT k.nr FROM lektion k WHERE k.id = l.lektion_id)
                     AS lektion_nr,
                 ROW_NUMBER() OVER (PARTITION BY l.id
                                    ORDER BY a.typ, a.id) AS rang_im_wort
            FROM aufgabe a
            JOIN lexem l ON l.id = a.lexem_id
            LEFT JOIN lernzustand z
                   ON z.aufgabe_id = a.id AND z.benutzer_id = ?
            {SCHON_BEGONNEN}
           WHERE {' AND '.join(bedingungen)}
        )
         ORDER BY {ordnung}
         LIMIT ?"""
    # Die Platzhalter in der Reihenfolge, in der sie im SQL stehen:
    # erst der Lernzustand-Verbund, dann der Begonnen-Verbund, dann die
    # Bedingungen, zuletzt die Grenze.
    reihe = dbm.zeilen(db, sql,
                       (werte[0], benutzer_id, *werte[1:], anzahl * 4))

    # Neue begrenzen, sonst überschwemmt ein frischer Import die Sitzung.
    #
    # Gezählt werden WÖRTER, nicht Aufgaben. Ein griechisches Verb bringt
    # vierzig Formen mit; zählte jede einzeln, wäre ein Tagesvorrat von
    # zwanzig nach einem halben Verb aufgebraucht — und man übte einen
    # Tag lang nichts als dessen Präsens. Ein Verbstamm ist ein Wort,
    # auch wenn viel daran hängt.
    if nur is None:
        # Deckelt, wie viele VERSCHIEDENE neue Wörter ein Abruf anfängt.
        # Die Abfrage oben hat schon ausgeschlossen, was gar nicht mehr
        # darf; hier wird nur noch gezählt.
        gefiltert, dazu = [], set()
        for r in reihe:
            if r["zustand"] in (None, "neu"):
                bekannt = (r["lexem_id"] in heute_begonnen
                           or r["lexem_id"] in dazu)
                if not bekannt:
                    if len(dazu) >= rest_neu:
                        continue      # das Tagespensum an Wörtern ist voll
                    dazu.add(r["lexem_id"])
            gefiltert.append(r)
        reihe = gefiltert

    # Erst zum Schluss: die Auswahl steht, nur die Reihenfolge wird noch
    # so gedreht, dass nicht dasselbe Wort zweimal hintereinander kommt
    # und unter gleich Dringendem abgewechselt wird.
    # Erst abwechseln, DANN Abstand halten: andersherum holte das
    # Abwechseln die eben zurückgestellten Wörter wieder nach vorn.
    if not reihe and vorzug is not None:
        # Der bevorzugte Topf ist leer — dann eben der andere. Eine halb
        # ungenutzte Tagesdosis hilft niemandem.
        return naechste(db, benutzer_id, sammlung_id=sammlung_id,
                        lektion_id=lektion_id, typen=typen,
                        wortarten=wortarten, formgruppen=formgruppen,
                        nur=nur, anzahl=anzahl, lernziel_id=lernziel_id,
                        bis_lektion=bis_lektion, ohne_grenze=ohne_grenze,
                        _ohne_vorzug=True)
    zaehler = _schon_gefragt_heute(db, benutzer_id)
    nachschub = None
    if (nur is None and e["neues_einstreuen"]
            and (rest is None or rest["neu"] > 0)):
        # Eigene Abfrage nur für Neues — im normalen Fenster steht bei
        # großem Rückstand keines.
        nachschub = dbm.zeilen(db, f"""
            SELECT * FROM (
              SELECT a.id AS aufgabe_id, a.typ, l.id AS lexem_id, l.lemma,
                     l.sammlung_id, z.zustand, z.stabilitaet, z.schwierigkeit,
                     z.faellig, z.letzte_wiederholung, z.anzahl,
                     z.anzahl_fehler, l.reihenfolge AS wort_folge,
                     COALESCE(begonnen.n, 0) AS schon_begonnen,
                     (SELECT k.nr FROM lektion k WHERE k.id = l.lektion_id)
                         AS lektion_nr,
                     ROW_NUMBER() OVER (PARTITION BY l.id
                                        ORDER BY a.typ, a.id) AS rang_im_wort
                FROM aufgabe a
                JOIN lexem l ON l.id = a.lexem_id
                LEFT JOIN lernzustand z
                       ON z.aufgabe_id = a.id AND z.benutzer_id = ?
                {SCHON_BEGONNEN}
               WHERE {' AND '.join(grundbedingungen)}
                 AND (z.zustand IS NULL OR z.zustand = 'neu')
            )
             ORDER BY {runde + ", " if runde else ""}schon_begonnen,
                      rang_im_wort, {LERNREIHENFOLGE}
             LIMIT 12""", (benutzer_id, benutzer_id, *grundwerte))
        nachschub = [r for r in nachschub
                     if r["lexem_id"] in dazu or len(dazu) < rest_neu]
    zuletzt = _zuletzt_gefragt(db, benutzer_id)
    reihe = _rundenweise(reihe, rundenstand)
    reihe = _abwechseln(reihe, zaehler)
    reihe = _abstand_halten(reihe, zuletzt, anzahl)
    # Zuletzt, nicht zuerst: sonst schiebt das Abstandhalten das eben
    # vorgezogene Neue wieder nach hinten — bei wenigen Wörtern ist ja
    # jedes "kürzlich dran gewesen".
    if nachschub is not None:
        reihe = _neues_einstreuen(reihe, nachschub, zaehler, zuletzt)

    ergebnis = []
    for r in reihe[:anzahl]:
        _zustand_sichern(db, r["aufgabe_id"], benutzer_id)
        ergebnis.append(_aufgabe_ausbauen(db, r, e["wunschretention"],
                                          e["legasthenie"], e["beschriftung"]))
    return ergebnis


def _aufgabe_ausbauen(db: sqlite3.Connection, r: dict, wunschretention: float,
                      legasthenie: dict | None = None,
                      stil: str = "fach") -> dict:
    """Aufgabe plus Begründung plus Terminvorschau.

    Im Legastheniemodus kommt das Schreibgerüst gleich mit: ins leere Feld zu
    tippen ist genau der Teil, der schwerfällt. Es wird hier erzeugt und nicht
    in der Oberfläche, weil nur hier die erwartete Antwort bekannt ist.
    """
    f = aufgaben.frage(db, r["aufgabe_id"], stil)
    lg = legasthenie or {}
    if (lg.get("aktiv") and lg.get("maske_stufe") is not None
            and f.get("eingabeart") == "text"):
        _u, aufloesung = aufgaben.antwort_pruefen(db, r["aufgabe_id"], "",
                                                  fehler_benennen=False)
        ziel = next(iter(aufloesung.get("erwartet") or []), None)
        if ziel:
            f["maske"] = legasthenie_modul.maske(ziel, int(lg["maske_stufe"]))
    # Das »Warum ist das so?« — nur die freigegebenen Regeln, die zu
    # dieser Frage passen, höchstens drei. Fehlt eine, fehlt sie still:
    # eine Abfrage darf nicht daran scheitern, dass die Grammatik noch
    # nicht geschrieben ist.
    try:
        f["regeln"] = regelmodul.fuer_aufgabe(db, r["aufgabe_id"])
    except Exception:
        f["regeln"] = []
    z = fsrs.Zustand(r["stabilitaet"], r["schwierigkeit"])
    verstrichen = _tage_seit(r["letzte_wiederholung"])
    # Mit denselben Angaben wie das spätere Bewerten — sonst zeigt der
    # Knopf einen anderen Termin an, als er setzt.
    vorschau = fsrs.vorschau(z, verstrichen, wunschretention,
                             saat=r["aufgabe_id"],
                             selber_tag=_selber_tag(r["letzte_wiederholung"]))
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
            aufgedeckt: bool = False, tipps: int = 0) -> dict:
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
    # Bei einer Reihe gilt dieselbe Regel JE ZELLE.
    #
    # »Man kann bei ihnen nicht noch mal schreiben, das wäre schon
    # gut.« — Eine Reihe sitzt als Ganzes oder nicht, und dabei bleibt
    # es: steht in einem Feld etwas Falsches, ist die Reihe falsch.
    # Aber ein Akzent, der verrutscht ist, ist auch in einer Reihe nur
    # ein Akzent. Beim einzelnen Wort gibt es dafür den zweiten
    # Versuch; in der Reihe gab es ihn praktisch nie, weil schon ein
    # einziges leeres Feld das Urteil auf "falsch" zieht.
    #
    # Offen ist danach NUR, was "fast" war. Wer eine Form nicht wusste,
    # bekommt keinen zweiten Rateversuch — das wäre mehr, als das
    # einzelne Wort bietet.
    if not nochmal and versuche == 1 and not aufgedeckt:
        nochmal = any(z["urteil"] == "fast"
                      for z in (aufloesung.get("zellen") or []))
    erwartet = next(iter(aufloesung.get("erwartet") or []), None)
    gewertet = bewertungsmodul.fuer_aufgabe(
        db, benutzer_id, aufgabe_id,
        urteil=urteil.urteil,
        fehlerart=(urteil.fehlerart
                   or ("diakritika" if "diakritika" in urteil.abweichungen
                       else ("verwechslung" if "verwechslung" in urteil.abweichungen
                             else None))),
        denkzeit_ms=denkzeit_ms, versuche=versuche, aufgedeckt=aufgedeckt,
        tipps=tipps,
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


# Wie viele Stufen ein Tipp hat. Mehr wären keine Hilfe mehr, sondern
# die Lösung auf Umwegen — dafür gibt es »Weiß ich nicht«.
TIPPSTUFEN = 3


def tipp(db: sqlite3.Connection, benutzer_id: int, aufgabe_id: int,
         stufe: int = 1) -> dict:
    """Ein Tipp — weniger als die Lösung, und in der Abfrage bleibend.

    Bisher gab es nur »Weiß ich nicht« (deckt alles auf und wertet als
    Nochmal) und »Wort ansehen« (führte aus der Abfrage heraus, und
    zurück kam man nicht). Dazwischen fehlte das Naheliegende: ein
    Anstoß, nach dem man selbst weiterkommt.

    Die Stufen bauen aufeinander auf:
      1  Wie viele Buchstaben, und der erste. Bei Formaufgaben der Stamm.
      2  Dazu der letzte Buchstabe.
      3  Dazu die Mitlaute — die Selbstlaute bleiben die Arbeit.

    Die Lösung steht nirgends in der Antwort: was der Browser nicht
    bekommt, kann er auch nicht verraten.
    """
    stufe = max(1, min(int(stufe), TIPPSTUFEN))
    _urteil, aufloesung = aufgaben.antwort_pruefen(db, aufgabe_id, "",
                                                   fehler_benennen=False)

    # Eine Reihe braucht einen Tipp JE ZELLE.
    #
    # »Bei den Reihen funktioniert der Tipp nicht.« — Er tat etwas
    # Schlimmeres als nichts: `erwartet` ist bei einer Reihe die flache
    # Liste aller Formen, und `next(iter(...))` nahm davon die erste.
    # Es stand also ein Gerüst da, ohne zu sagen, zu welchem der sechs
    # Felder es gehört. Wer es auf das Feld bezog, in dem er gerade
    # steckte, bekam Unsinn.
    zellen = aufloesung.get("zellen")
    if zellen:
        antwort = {
            "stufe": stufe,
            "hoechste_stufe": TIPPSTUFEN,
            "zellen": [{"zelle": z["zelle"],
                        "beschriftung": z["beschriftung"],
                        "maske": legasthenie_modul.maske(z["erwartet"][0], stufe),
                        "buchstaben": len([c for c in z["erwartet"][0]
                                           if c.isalpha()])}
                       for z in zellen if z.get("erwartet")],
        }
        if stufe == 1:
            # Der Stamm gilt für die ganze Reihe — sie teilen ihn sich,
            # das ist ja der Witz an einer Formgruppe.
            stamm = aufgaben.stamm_fuer_aufgabe(db, aufgabe_id)
            if stamm:
                antwort["stamm"] = stamm
        if not antwort["zellen"]:
            return {"stufe": stufe, "hoechste_stufe": TIPPSTUFEN,
                    "maske": None, "hinweis": "Dazu gibt es keinen Tipp."}
        return antwort

    erwartet = next(iter(aufloesung.get("erwartet") or []), None)
    if not erwartet:
        return {"stufe": stufe, "hoechste_stufe": TIPPSTUFEN,
                "maske": None, "hinweis": "Dazu gibt es keinen Tipp."}
    antwort = {
        "stufe": stufe,
        "hoechste_stufe": TIPPSTUFEN,
        "maske": legasthenie_modul.maske(erwartet, stufe),
        "buchstaben": len([z for z in erwartet if z.isalpha()]),
        "woerter": len(erwartet.split()),
    }
    if stufe == 1:
        stamm = aufgaben.stamm_fuer_aufgabe(db, aufgabe_id)
        # Der Stamm nur, wenn er wirklich kürzer ist als die Antwort —
        # sonst wäre der »Tipp« das Wort selbst.
        if stamm and len(stamm) < len(erwartet):
            antwort["stamm"] = stamm
    return antwort


def bewerten(db: sqlite3.Connection, benutzer_id: int, aufgabe_id: int,
             bewertung: int | None = None, antwort: str | None = None,
             urteil: str | None = None, dauer_ms: int | None = None,
             denkzeit_ms: int | None = None, versuche: int = 1,
             aufgedeckt: bool = False, fehlerart: str | None = None,
             tipps: int = 0) -> dict:
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
        tipps=tipps,
            erwartet=antwort, zeitmessung=_zeitmessung(e))
        bewertung = einschaetzung["bewertung"]
        quelle = "automatisch"
    if bewertung not in fsrs.BEWERTUNGEN:
        raise ValueError("Bewertung muss 1 bis 4 sein")
    ergebnis = lernkern.fortschreiben(
        db, lernkern.VOKABELN, aufgabe_id, benutzer_id, bewertung,
        e["wunschretention"],
        {"antwort": antwort, "urteil": urteil, "dauer_ms": dauer_ms,
         "denkzeit_ms": denkzeit_ms, "versuche": versuche,
         "bewertung_quelle": quelle})

    return {**ergebnis, "bewertung_quelle": quelle,
            "einschaetzung": einschaetzung}


def aussetzen(db: sqlite3.Connection, benutzer_id: int, aufgabe_id: int,
              aussetzen_: bool = True) -> None:
    """Aus der Abfrage nehmen — und wieder hinein."""
    lernkern.aussetzen(db, lernkern.VOKABELN, aufgabe_id, benutzer_id,
                       aussetzen_)


def zuruecksetzen(db: sqlite3.Connection, benutzer_id: int,
                  aufgabe_id: int) -> None:
    """Von vorn: Gedächtniszustand weg, Protokoll bleibt."""
    lernkern.zuruecksetzen(db, lernkern.VOKABELN, aufgabe_id, benutzer_id)


def termin_setzen(db: sqlite3.Connection, benutzer_id: int, aufgabe_id: int,
                  datum: str) -> None:
    """Termin selbst in die Hand nehmen."""
    # Nicht nur fromisoformat: das nimmt seit Python 3.11 auch
    # "20261114" und "2026-W47-1" an. Gespeichert würde der Rohtext, und
    # der Vergleich `faellig <= '2026-11-14'` wäre dann dauerhaft
    # unwahr — die Aufgabe verschwände still aus dem Terminplan.
    geprueft = dt.date.fromisoformat(datum)
    if datum != geprueft.isoformat():
        raise ValueError("datum muss JJJJ-MM-TT sein")
    _zustand_sichern(db, aufgabe_id, benutzer_id)
    db.execute("""UPDATE lernzustand SET faellig = ?,
                         zustand = CASE WHEN zustand = 'neu' THEN 'lernen'
                                        ELSE zustand END
                   WHERE aufgabe_id = ? AND benutzer_id = ?""",
               (datum, aufgabe_id, benutzer_id))


# ------------------------------------------------------------- Lernstand

def lernstand(db: sqlite3.Connection, benutzer_id: int, sammlung_id: int,
              anzahl: int = 40) -> dict:
    """Was sitzt, und woran hakt es?

    Gedacht für die KI am MCP: aus »diese zwölf Wörter gehen immer wieder
    schief« lassen sich gezielt Sätze schreiben, in denen genau sie
    vorkommen. Das ist der Schritt von »Vokabeln abfragen« zu »üben, was
    nötig ist«.

    Gemessen wird je WORT, nicht je Aufgabe: dass an γράφω die
    Aorist-Aufgabe hakt und die Bedeutungsaufgabe sitzt, ist für das
    Schreiben eines Satzes zweitrangig — gebraucht wird das Wort.
    """
    s = dbm.zeile(db, "SELECT * FROM sammlung WHERE id = ?", (sammlung_id,))
    if s is None:
        raise KeyError(f"Sammlung {sammlung_id} gibt es nicht")

    zeilen = dbm.zeilen(db, """
        SELECT l.id AS lexem_id, l.lemma, l.wortart, k.nr AS lektion_nr,
               COUNT(a.id) AS aufgaben,
               SUM(CASE WHEN z.zustand = 'reif' THEN 1 ELSE 0 END) AS reif,
               SUM(CASE WHEN z.zustand = 'verlernt' THEN 1 ELSE 0 END) AS verlernt,
               SUM(CASE WHEN z.aufgabe_id IS NULL OR z.zustand = 'neu'
                        THEN 1 ELSE 0 END) AS neu,
               SUM(COALESCE(z.anzahl, 0)) AS versuche,
               SUM(COALESCE(z.anzahl_fehler, 0)) AS fehler,
               AVG(z.stabilitaet) AS stabilitaet,
               MIN(z.faellig) AS naechste_faelligkeit
          FROM lexem l
          JOIN aufgabe a ON a.lexem_id = l.id AND a.aktiv = 1
          LEFT JOIN lernzustand z
                 ON z.aufgabe_id = a.id AND z.benutzer_id = ?
          LEFT JOIN lektion k ON k.id = l.lektion_id
         WHERE l.sammlung_id = ?
         GROUP BY l.id""", (benutzer_id, sammlung_id))

    def anteil(z):
        return (z["fehler"] / z["versuche"]) if z["versuche"] else 0.0

    woerter = []
    for z in zeilen:
        woerter.append({**z, "fehleranteil": round(anteil(z), 3),
                        "stabilitaet": round(z["stabilitaet"], 1)
                        if z["stabilitaet"] is not None else None})

    geuebt = [w for w in woerter if w["versuche"]]
    # "Schwach" heißt: schon geübt UND trotzdem oft daneben. Ein Wort mit
    # einem einzigen Fehlversuch gehört nicht dazu — sonst stünde nach dem
    # ersten Lerntag der halbe Bestand auf der Liste.
    schwach = sorted(
        [w for w in geuebt if w["versuche"] >= 3 and w["fehleranteil"] >= 0.34],
        key=lambda w: (-w["fehleranteil"], -w["versuche"]))[:anzahl]
    sitzt = sorted([w for w in geuebt if w["reif"] and not w["verlernt"]
                    and w["fehleranteil"] < 0.2],
                   key=lambda w: -(w["stabilitaet"] or 0))[:anzahl]

    return {
        "sammlung_id": sammlung_id, "benutzer_id": benutzer_id,
        "woerter_gesamt": len(woerter),
        "geuebt": len(geuebt),
        "nie_geuebt": len(woerter) - len(geuebt),
        "aufgaben": sum(w["aufgaben"] for w in woerter),
        "reif": sum(w["reif"] or 0 for w in woerter),
        "verlernt": sum(w["verlernt"] or 0 for w in woerter),
        "schwach": schwach,
        "sitzt": sitzt,
        "hinweis": "»schwach« sind Wörter, die mindestens dreimal geübt "
                   "wurden und trotzdem in einem Drittel der Fälle "
                   "danebengingen. Genau sie gehören in neue Übungssätze. "
                   "Die Zahlen gelten für diese eine Person.",
    }
