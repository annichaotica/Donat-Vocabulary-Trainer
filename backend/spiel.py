"""Tagesziel und Strähne — was das Durchhalten sichtbar macht.

»Wir brauchen auf jeden Fall einen Streak, XP, Leistungslevels und
Motivationsbringer.«

Hier steht der erste Teil davon: das Tagesziel als Zahl, die aufgeht,
und die Strähne als Zahl, die wächst. Beides wird GERECHNET, nicht
mitgeschrieben — aus `wiederholung`, das nie geleert wird. Drei Folgen,
und alle drei sind der Grund für diesen Zuschnitt:

  Niemand fängt bei null an. Die 66 Antworten aus der Zeit davor zählen
  vom ersten Tag
  an mit, statt dass eine leere Anzeige behauptet, sie hätte noch nie
  etwas getan.

  Es kann nicht auseinanderlaufen. Ein Zähler, der neben dem Protokoll
  mitläuft, ist eine zweite Wahrheit; bei einem Abbruch mitten in der
  Sitzung wäre sie die falsche.

  Ein gelöschtes Lernziel nimmt auch hier nichts mit.

DIE EINE REGEL, die den ganzen Entwurf bestimmt: **belohnt wird
Erscheinen, nicht Trefferquote.** Gezählt werden bearbeitete Aufgaben,
gleich wie sie ausgingen. Dieser Trainer verlässt sich an einer Stelle
ausdrücklich auf Ehrlichkeit — bei längeren Antworten bleibt die
Einschätzung beim Menschen. Hinge daran ein Punktestand, entstünde
genau dort ein Anreiz zu schummeln, und der Schaden wäre nicht der
verlorene Punkt, sondern ein verdorbener Terminplan: FSRS legt
großzügig bewertete Wörter weit weg, und vor der Arbeit ist nichts
mehr da. Die Trefferquote wird gezeigt — im Fortschritt —, aber sie
wird nicht bepunktet.

ÜBER ALLE SAMMLUNGEN ZUSAMMEN, wie die Tagesdosis selbst. Eine Strähne
je Sammlung wäre eine zweite Zahl für dasselbe, und man wüsste bei
keiner mehr, was sie bedeutet.
"""

from __future__ import annotations

import datetime as dt
import sqlite3

import datenbank as dbm


# Fehltage, die eine laufende Strähne überspringt — zwei je Kalendermonat.
#
# Ohne sie reißt eine Strähne beim ersten Grippetag, und das ist der
# bekannte Weg, auf dem Strähnen aufhören zu motivieren und anfangen zu
# nerven: wer 23 Tage verloren hat, fängt nicht wieder bei eins an, er
# hört auf. Mit ihnen bleibt die Zahl trotzdem ehrlich — der dritte
# Fehltag im Monat reißt sie, und der Joker heißt Joker und nicht
# »gelernt«.
TAGE_JOKER = 2


def _heute() -> dt.date:
    # Über `lernen`, damit Tests, die dort die Uhr vorstellen, auch hier
    # wirken — dieselbe Regel wie im Lernkern und in der Statistik.
    import lernen
    return lernen.heute()


def _ziel_je_tag(einstellungen: dict) -> int:
    """Wie viele Antworten einen Tag zu einem gelernten Tag machen.

    Das Tagesziel, nicht die Tagesdosis. Der erste Entwurf nahm die
    Dosis — sie stand ja schon da, und eine zweite Zahl wollte ich
    vermeiden. An den echten Daten fiel das sofort durch: die Dosis ist
    eine Obergrenze und wird absichtlich hoch gesetzt, vom
    Lernzielhelfer noch höher. Bei 120 stand die Strähne auf 0, obwohl
    an vier Tagen hintereinander 29 bis 123 Fragen beantwortet worden
    waren.

    Zwei Zahlen sind hier also richtig, weil es zwei Dinge sind: wie
    viel der Trainer höchstens serviert, und wie viel man sich vornimmt.
    Die Begrenzung auf die Dosis steckt in `benutzer_einstellungen`.
    """
    return einstellungen["tagesziel"]


def _tage(db: sqlite3.Connection, benutzer_id: int) -> dict[str, int]:
    """Antworten je Kalendertag, über die ganze Vergangenheit.

    Ohne Sammlungsfilter — die Tagesdosis zählt auch über alle
    zusammen. `substr` statt `date()`: dieselbe Schreibweise wie in der
    Statistik, und sie kommt ohne Zeitzonenrechnung aus.
    """
    return {z["tag"]: z["n"] for z in dbm.zeilen(db, """
        SELECT substr(zeitpunkt, 1, 10) AS tag, COUNT(*) AS n
          FROM wiederholung WHERE benutzer_id = ?
         GROUP BY tag""", (benutzer_id,))}


def tagesziel(db: sqlite3.Connection, benutzer_id: int,
              stand: dict | None = None) -> dict:
    """Wie weit das Tagespensum heute aufgegangen ist.

    `stand` darf mitgegeben werden, wenn der Aufrufer ihn schon hat —
    die Übersicht holt ihn ohnehin. Sonst wird er geholt, denn eine
    Zahl brauchen wir daraus: ob überhaupt noch etwas offen ist. Davon
    hängt ab, ob ein kurzer Tag als geschafft gilt.
    """
    import lernen as lernmodul
    e = lernmodul.benutzer_einstellungen(db, benutzer_id)
    if stand is None:
        stand = lernmodul.stand(db, benutzer_id)
    ziel = _ziel_je_tag(e)
    erledigt = stand["heute_erledigt"]
    offen = stand["heute_offen"]
    return {
        "erledigt": erledigt,
        "ziel": ziel,
        # Die Dosis selbst, damit die Oberfläche »ohne Grenze« von
        # »genau eine Frage« unterscheiden kann.
        "dosis": e["fragen_je_tag"],
        "offen": offen,
        "geschafft": _erfuellt(erledigt, ziel, offen),
        # Warum der Tag als geschafft gilt, obwohl die Dosis nicht voll
        # ist: weil nichts mehr da war. Das soll die Oberfläche sagen
        # können, sonst sieht es nach einem Rechenfehler aus.
        "nichts_mehr_faellig": bool(erledigt and not offen
                                    and erledigt < ziel),
    }


def _erfuellt(erledigt: int, ziel: int, offen: int | None = None) -> bool:
    """Gilt der Tag als gelernt?

    Die Dosis erfüllt — oder gelernt, bis nichts mehr da war. Der
    zweite Fall ist wichtig: an einem Tag, an dem nur drei Aufgaben
    fällig sind, darf die Strähne nicht reißen. Sonst erzieht die App
    dazu, gegen den eigenen Terminplan zu arbeiten, nur damit eine Zahl
    stehen bleibt.

    Dieser Fall ist allerdings nur für HEUTE zu haben: was an einem
    vergangenen Tag fällig war, steht nirgends — `lernzustand.faellig`
    kennt nur den jetzigen Termin, und aus dem Protokoll ließe es sich
    bloß durch ein Nachspiel aller Termine rekonstruieren. Dafür ist
    eine Strähne nicht wichtig genug. Vergangene knappe Tage fängt
    stattdessen der Joker auf, und das ist auch der ehrlichere Weg:
    lieber eine klare Regel mit zwei Freitagen als eine
    nachgerechnete, die niemand prüfen kann.
    """
    if erledigt >= ziel:
        return True
    return bool(offen is not None and offen == 0 and erledigt > 0)


def straehne(db: sqlite3.Connection, benutzer_id: int,
             stand: dict | None = None) -> dict:
    """Die laufende Strähne, die längste, und was die Joker tun.

    Rückwärts von heute. Heute reißt nie: der Tag ist noch nicht
    vorbei, und eine Strähne, die morgens auf null steht, ist eine
    Drohung und kein Anreiz.
    """
    import lernen as lernmodul
    import zuspruch as zuspruchmodul
    e = lernmodul.benutzer_einstellungen(db, benutzer_id)
    ziel = _ziel_je_tag(e)
    tage = _tage(db, benutzer_id)
    heute = _heute()
    heute_text = heute.isoformat()

    # Geschenkte Joker heben die Zahl der Fehltage, die eine Strähne
    # trägt — für den Monat, in dem sie geschickt wurden. Sie schreiben
    # KEINEN Lerntag ins Protokoll: der Zuspruch ändert nicht, was
    # geschehen ist, nur wie es gezählt wird.
    geschenkt = zuspruchmodul.geschenkte_joker(db, benutzer_id)

    def erlaubt(monat: str) -> int:
        return TAGE_JOKER + geschenkt.get(monat, 0)

    if not tage:
        return {"laufend": 0, "laengste": 0, "ziel": ziel,
                "joker_frei": erlaubt(heute_text[:7]),
                "joker_geschenkt": geschenkt.get(heute_text[:7], 0),
                "joker_benutzt": [], "heute_geschafft": False}

    # Nur für heute ist bekannt, ob überhaupt noch etwas offen war.
    if stand is None:
        stand = lernmodul.stand(db, benutzer_id)
    heute_offen = stand["heute_offen"]

    def erfuellt(tag: str) -> bool:
        return _erfuellt(tage.get(tag, 0), ziel,
                         heute_offen if tag == heute_text else None)

    erster = dt.date.fromisoformat(min(tage))

    # --- rückwärts: die laufende Strähne
    laufend = 0
    joker: dict[str, int] = {}
    geschuetzt: list[str] = []
    tag = heute
    while tag >= erster:
        text = tag.isoformat()
        if erfuellt(text):
            laufend += 1
        elif text == heute_text:
            pass                      # der Tag läuft noch
        else:
            monat = text[:7]
            # Kein Joker, solange die Strähne noch nicht angefangen hat:
            # sonst verbrennt ein Rückblick auf zwei faule Tage die
            # Freitage für eine Strähne, die es gar nicht gibt.
            if laufend and joker.get(monat, 0) < erlaubt(monat):
                joker[monat] = joker.get(monat, 0) + 1
                geschuetzt.append(text)
            else:
                break
        tag -= dt.timedelta(days=1)

    # --- vorwärts: die längste, mit derselben Regel
    #
    # Die Joker werden je Kalendermonat UND je Strähne gezählt und beim
    # Reißen zurückgesetzt. Sonst widersprächen sich die beiden
    # Durchläufe: Fehltage aus einer längst gerissenen Strähne hätten
    # die Freitage des laufenden Monats schon verbraucht, und rückwärts
    # käme eine andere Zahl heraus als vorwärts. Zwei verschiedene
    # Zahlen für dieselbe Strähne wären schlimmer als eine milde Regel.
    laengste = 0
    lauf = 0
    joker_lauf: dict[str, int] = {}
    tag = erster
    while tag <= heute:
        text = tag.isoformat()
        if erfuellt(text):
            lauf += 1
            laengste = max(laengste, lauf)
        elif text != heute_text:
            monat = text[:7]
            if lauf and joker_lauf.get(monat, 0) < erlaubt(monat):
                joker_lauf[monat] = joker_lauf.get(monat, 0) + 1
            else:
                lauf = 0
                joker_lauf = {}
        tag += dt.timedelta(days=1)

    return {
        "laufend": laufend,
        "laengste": max(laengste, laufend),
        "ziel": ziel,
        "joker_frei": max(0, erlaubt(heute_text[:7])
                            - joker.get(heute_text[:7], 0)),
        "joker_geschenkt": geschenkt.get(heute_text[:7], 0),
        # Welche Tage der Joker getragen hat — damit die Anzeige nicht
        # behaupten muss, an diesen Tagen wäre gelernt worden.
        "joker_benutzt": sorted(geschuetzt),
        "heute_geschafft": erfuellt(heute_text),
    }


# ----------------------------------------------------------------- XP
#
# Was Punkte gibt — und warum GENAU das.
#
# XP_TAG  ist der Kern: eine Aufgabe, an einem Tag bearbeitet. EINMAL je
#         Aufgabe und Tag, und darin steckt der ganze Schutz vor dem
#         Schinden von Punkten. Wer dieselbe Karte fünfzigmal
#         durchklickt, bekommt zehn Punkte. Mehr holt nur, wer mehr
#         verschiedene Aufgaben anfasst — und davon gibt es nur so viele,
#         wie der Bestand hergibt. Ein Tagesdeckel erübrigt sich damit;
#         er wäre eine zweite Regel für dieselbe Sache.
#
#         Es zählt NICHT, ob die Antwort stimmte. Das ist die Grundregel
#         dieses Moduls: belohnt wird Erscheinen. Gäbe es Punkte für
#         »richtig«, entstünde ein Anreiz, sich großzügig zu bewerten —
#         und der Schaden wäre ein verdorbener Terminplan.
#
# XP_NEU  für die erste Begegnung mit einer Aufgabe. Klein gehalten:
#         Neues anfangen ist leicht, Neues behalten ist die Arbeit.
#
# XP_REIF für den Sprung auf »sitzt dauerhaft«. Das ist der einzige
#         Posten, den man nicht an einem Nachmittag holen kann — dorthin
#         führt nur ein Intervall von drei Wochen, und das vergeht in
#         drei Wochen. Darum ist er der größte.
#
# XP_ZIEL fürs erreichte Tagesziel. Belohnt das Zuendemachen.
XP_TAG = 10
XP_NEU = 5
XP_REIF = 25
XP_ZIEL = 50

# Die Stufen. Die Abstände wachsen, damit die ersten schnell kommen und
# die späteren etwas bedeuten. Die Namen sind eine Leiter durchs Lesen —
# gemeint als Vorschlag: wer sich eigene ausdenkt, hat mehr davon.
#
# Nach oben offen: über der letzten Schwelle bleibt die Stufe stehen und
# die Punkte zählen weiter. Eine Stufe »Meister«, hinter der nichts mehr
# kommt, wäre ein Schlusspunkt, und Lernen hat keinen.
STUFEN = [
    (0, "Buchstaben"),
    (250, "Wörter"),
    (750, "Sätze"),
    (1750, "Absätze"),
    (3500, "Seiten"),
    (7000, "Kapitel"),
    (14000, "Bücher"),
    (28000, "Regal"),
    (56000, "Bibliothek"),
]


def _xp_je_tag(db: sqlite3.Connection, benutzer_id: int) -> dict[str, int]:
    """Die Punkte, nach Tagen aufgeschlüsselt.

    Nach Tagen und nicht als eine Summe, weil ein geschenkter
    Verdoppler (siehe `zuspruch`) an einem TAG hängt. Außerdem lässt
    sich so zeigen, wann etwas verdient wurde.

    Alles aus `wiederholung` gerechnet. Der Übergang auf »sitzt
    dauerhaft« steht dort nicht als Wort, aber als Zahl: `intervall_tage`
    ist genau dann über der Reifegrenze, wenn der Lernkern »reif«
    gesetzt hat (`fsrs.bewerten` entscheidet an derselben Zahl). Mit
    LAG wird verglichen, was bei derselben Aufgabe davor galt — ein
    Sprung zählt, ein Verbleiben nicht.
    """
    import fsrs
    tage: dict[str, int] = {}

    def dazu(tag: str, wert: int) -> None:
        tage[tag] = tage.get(tag, 0) + wert

    # Eine Aufgabe, an einem Tag angefasst.
    for z in dbm.zeilen(db, """
            SELECT tag, COUNT(*) AS n FROM (
                SELECT DISTINCT aufgabe_id, substr(zeitpunkt, 1, 10) AS tag
                  FROM wiederholung WHERE benutzer_id = ?)
             GROUP BY tag""", (benutzer_id,)):
        dazu(z["tag"], XP_TAG * z["n"])

    # Erste Begegnung.
    for z in dbm.zeilen(db, """
            SELECT substr(zeitpunkt, 1, 10) AS tag, COUNT(*) AS n
              FROM wiederholung
             WHERE benutzer_id = ? AND stabilitaet_vor IS NULL
             GROUP BY tag""", (benutzer_id,)):
        dazu(z["tag"], XP_NEU * z["n"])

    # Der Sprung auf »sitzt dauerhaft«. Ein Rückfall und ein erneutes
    # Erreichen zählen wieder — es ist dieselbe Arbeit noch einmal.
    for z in dbm.zeilen(db, """
            SELECT tag, COUNT(*) AS n FROM (
                SELECT substr(zeitpunkt, 1, 10) AS tag,
                       bewertung > 1 AND intervall_tage >= ?2 AS reif,
                       LAG(bewertung > 1 AND intervall_tage >= ?2) OVER (
                           PARTITION BY aufgabe_id ORDER BY zeitpunkt, id
                       ) AS reif_davor
                  FROM wiederholung WHERE benutzer_id = ?1)
             WHERE reif = 1 AND COALESCE(reif_davor, 0) = 0
             GROUP BY tag""", (benutzer_id, fsrs.REIF_AB_TAGEN)):
        dazu(z["tag"], XP_REIF * z["n"])

    # Das erreichte Tagesziel.
    import lernen as lernmodul
    ziel = _ziel_je_tag(lernmodul.benutzer_einstellungen(db, benutzer_id))
    for tag, anzahl in _tage(db, benutzer_id).items():
        if anzahl >= ziel:
            dazu(tag, XP_ZIEL)

    return tage


def stufe(punkte: int) -> dict:
    """Welche Stufe, und wie weit bis zur nächsten."""
    nummer, name, ab = 1, STUFEN[0][1], 0
    for i, (schwelle, bezeichnung) in enumerate(STUFEN):
        if punkte >= schwelle:
            nummer, name, ab = i + 1, bezeichnung, schwelle
        else:
            break
    naechste = next((s for s, _ in STUFEN if s > punkte), None)
    return {
        "nummer": nummer,
        "name": name,
        "ab": ab,
        "naechste": naechste,
        # Wie weit zwischen dieser und der nächsten Stufe — für den
        # Balken. Auf der letzten Stufe gibt es keinen, und dann soll
        # auch keiner gezeichnet werden: ein Balken, der nie voll wird,
        # ist eine Enttäuschung mit Ansage.
        "anteil": (None if naechste is None
                   else round((punkte - ab) / (naechste - ab), 3)),
    }


def punkte(db: sqlite3.Connection, benutzer_id: int,
           verdoppelt: set[str] | None = None) -> dict:
    """Punkte insgesamt, heute, und die Stufe dazu.

    `verdoppelt` sind Tage, an denen ein geschenkter Verdoppler lief.
    Sie werden doppelt gezählt — der Zuspruch ändert nicht das
    Protokoll, sondern nur, wie es ausgewertet wird. Dasselbe Prinzip
    wie überall hier: nichts Zusätzliches mitschreiben.
    """
    je_tag = _xp_je_tag(db, benutzer_id)
    verdoppelt = verdoppelt or set()
    gesamt = sum(wert * (2 if tag in verdoppelt else 1)
                 for tag, wert in je_tag.items())
    heute = _heute().isoformat()
    return {
        "gesamt": gesamt,
        "heute": je_tag.get(heute, 0) * (2 if heute in verdoppelt else 1),
        "heute_verdoppelt": heute in verdoppelt,
        "stufe": stufe(gesamt),
    }


def stand(db: sqlite3.Connection, benutzer_id: int) -> dict:
    """Alles in einem Aufruf — die Kopfzeile fragt bei jedem Wechsel.

    Der Lernstand wird EINMAL geholt und weitergereicht. Sonst stünde er
    dreimal in derselben Antwort, mit allen Zählabfragen dreifach.
    """
    import lernen as lernmodul
    import zuspruch as zuspruchmodul
    roh = lernmodul.stand(db, benutzer_id)
    return {
        "tagesziel": tagesziel(db, benutzer_id, roh),
        "straehne": straehne(db, benutzer_id, roh),
        "punkte": punkte(db, benutzer_id,
                         zuspruchmodul.verdopplungstage(db, benutzer_id)),
    }
