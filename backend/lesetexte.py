"""Texte lesen und übersetzen — und vorher wissen, ob man das kann.

»Ich möchte eine Übersetzungsfunktion, in dem Sinne, dass ich Texte
hochladen kann oder auch pasten, die gespeichert werden, und wo zum
einen analysiert wird, ob ich das schon übersetzen können müsste, eine
Unterstützung bei der Übersetzung, und als Allerletztes noch Worte, die
ich quasi noch nicht kenne, markieren kann. Die soll dann die
angebundene KI über den MCP auslesen können, um mir hier die
entsprechenden Datensätze einfügen zu können.«

Vier Dinge, und das erste trägt die anderen: die Deckung. Ohne sie ist
ein Text ein Text; mit ihr ist er eine Aussage über den eigenen Stand.

Wie gezählt wird
----------------
Jedes Wort des Textes wird in seine Vergleichsform gebracht — dieselbe,
mit der die Satzprüfung arbeitet, also mit den Schriftregeln der
Sprache (griechisches Schluss-Sigma, Apostrophe, Groß und Klein). Dann
wird es im Wortschatz der Sammlung gesucht, und zwar sowohl unter den
Grundformen als auch unter allen eingetragenen Formen. »γράφεις« findet
also »γράφω«, sofern die Form eingetragen ist.

Was dabei NICHT passiert, und das ist wichtig für das Vertrauen in die
Zahl: es wird nicht geraten. Keine Stammformenerkennung, keine
Endungsheuristik. Eine Form, die niemand eingetragen hat, gilt als
unbekannt — lieber eine zu vorsichtige Aussage als eine zu
freundliche. Wer die Lücke schließt, trägt die Form ein; dann stimmt
die Zahl dauerhaft, statt beim nächsten Text wieder geraten zu werden.

Die vier Töpfe
--------------
  sitzt      kenne ich, der Lernstand ist reif
  lernen     ist in Arbeit (fällig, verlernt, angefangen)
  neu        steht im Wortschatz, war aber noch nie dran
  unbekannt  steht nicht im Wortschatz

Nur der letzte Topf ist ein echtes Hindernis beim Übersetzen. »neu«
heißt: es ist eingetragen, du hast es nur noch nicht gelernt — beim
Nachschlagen findest du es.
"""

from __future__ import annotations

import json
import re
import sqlite3

import datenbank as dbm
import pruefung
import sprachen


# Zahlen und reine Satzzeichen zählen nicht mit. Sie als »unbekanntes
# Wort« zu führen wäre nicht falsch, aber unbrauchbar: die Deckung eines
# Textes mit Jahreszahlen sähe schlechter aus, als sie ist.
_NUR_ZIFFERN = re.compile(r"^[\d.,:/-]+$")

# Satzzeichen am Wortrand — dieselbe Liste wie in der Satzprüfung. Innen
# bleiben sie stehen: »σ' αγαπώ« ist ein Wort mit Apostroph.
_RAND = " \t\n\r.,;:!?¡¿\"»«“”„…()[]{}·'’—–-"
_TRENNER = re.compile(r"[\s ]+")


def woerter(inhalt: str, profil: dict) -> list[dict]:
    """Zerlegt einen Text in Wörter, mit Schreibweise UND Vergleichsform.

    Beides, weil beides gebraucht wird: angezeigt wird die Schreibweise
    aus dem Text, verglichen wird die normierte Fassung. Wer nur
    letztere behielte, zeigte der Leserin ein Wort, das so nicht
    dasteht.
    """
    gefunden = []
    for roh in _TRENNER.split(inhalt or ""):
        wort = roh.strip(_RAND)
        if not wort or _NUR_ZIFFERN.match(wort):
            continue
        gefunden.append({
            "wort": wort,
            "vergleichsform": pruefung._genau(wort, profil),
        })
    return gefunden


def _bedeutungen(db: sqlite3.Connection, sammlung_id: int) -> dict[int, str]:
    """lexem_id -> erste Übersetzung.

    Für die Wort-für-Wort-Hilfe. In EINER Abfrage, nicht je Wort: ein
    Absatz hat schnell vierzig Wörter, und vierzig Rundläufe für eine
    Lesehilfe wären keine Hilfe.
    """
    gefunden: dict[int, str] = {}
    for z in dbm.zeilen(db, """
            SELECT b.lexem_id, u.text
              FROM bedeutung b
              JOIN lexem l ON l.id = b.lexem_id
              JOIN uebersetzung u ON u.bedeutung_id = b.id
             WHERE l.sammlung_id = ?
             ORDER BY b.reihenfolge DESC, u.ist_haupt, u.id DESC""",
            (sammlung_id,)):
        gefunden[z["lexem_id"]] = z["text"]
    return gefunden


def _wortschatz(db: sqlite3.Connection, sammlung_id: int,
                profil: dict) -> dict[str, int]:
    """Vergleichsform -> lexem_id, über Grundformen UND Formen.

    Die Formen zählen ausdrücklich mit. Ohne sie wäre jeder flektierte
    Text »unbekannt«, obwohl das Wort längst gelernt ist — und genau
    das ist bei einer Flexionssprache die Regel und nicht die Ausnahme.

    Mehrwortige Einträge stehen hier als Ganzes drin: griechische
    Substantive werden mit Artikel gelernt (»το μήλο«), französische
    teils auch (»le pain«). Wer nur Einzelwörter abglich, fand beim
    ersten Text keines davon wieder und meldete lauter Lücken, die
    keine sind. Gesucht wird deshalb weiter unten mit dem längsten
    passenden Stück zuerst.
    """
    karte: dict[str, int] = {}
    # Erst die Formen, dann die Lemmata: bei gleicher Vergleichsform soll
    # das Lemma gewinnen, denn es ist der Eintrag, den man nachschlägt.
    for zeile in dbm.zeilen(db, """
            SELECT f.text, f.lexem_id FROM form f
              JOIN lexem l ON l.id = f.lexem_id
             WHERE l.sammlung_id = ?""", (sammlung_id,)):
        karte.setdefault(pruefung._genau(zeile["text"], profil),
                         zeile["lexem_id"])
    for zeile in dbm.zeilen(db, """
            SELECT id, lemma FROM lexem WHERE sammlung_id = ?""",
            (sammlung_id,)):
        karte[pruefung._genau(zeile["lemma"], profil)] = zeile["id"]
    return karte


def _lernstaende(db: sqlite3.Connection, sammlung_id: int,
                 benutzer_id: int) -> dict[int, str]:
    """lexem_id -> sitzt | lernen | neu.

    Ein Wort hat mehrere Aufgaben (Bedeutung hin, Bedeutung zurück,
    Formen). Fürs Lesen zählt die GÜNSTIGSTE: wer »το μήλο« von
    Griechisch nach Deutsch sicher kann, kann den Text lesen, auch wenn
    die Gegenrichtung noch hakt. Beim Übersetzen in die Fremdsprache
    wäre es umgekehrt — darum steht die Richtung in der Aufgabe und
    nicht hier, und hier wird für das Lesen entschieden.
    """
    stand: dict[int, str] = {}
    for zeile in dbm.zeilen(db, """
            SELECT a.lexem_id,
                   MAX(CASE WHEN z.zustand = 'reif' THEN 2
                            WHEN z.zustand IS NOT NULL THEN 1
                            ELSE 0 END) AS beste
              FROM aufgabe a
              JOIN lexem l ON l.id = a.lexem_id
              LEFT JOIN lernzustand z
                     ON z.aufgabe_id = a.id AND z.benutzer_id = ?
             WHERE l.sammlung_id = ? AND a.aktiv = 1
             GROUP BY a.lexem_id""", (benutzer_id, sammlung_id)):
        stand[zeile["lexem_id"]] = {2: "sitzt", 1: "lernen"}.get(
            zeile["beste"], "neu")
    return stand


def _ohne_akzent_karte(karte: dict[str, int]) -> dict[str, int]:
    """Dieselbe Karte, akzentlos — für den Rückfall bei Großschreibung.

    Nur eindeutige Schlüssel: wo zwei verschiedene Wörter ohne Akzent
    gleich aussehen (»πότε« wann und »ποτέ« nie), wird nichts
    geraten. Ein falsch zugeordnetes Wort im Lesetext ist schlimmer
    als ein als unbekannt gemeldetes — das eine merkt man, das andere
    nicht.
    """
    zaehler: dict[str, set] = {}
    for form, lexem_id in karte.items():
        zaehler.setdefault(pruefung.ohne_diakritika(form), set()).add(lexem_id)
    return {form: next(iter(ids)) for form, ids in zaehler.items()
            if len(ids) == 1}


_AKZENTE = "άέήίόύώΐΰ"


def _ohne_zweitakzent(wort: str) -> str | None:
    """Enklise: ein zweiter Akzent, den ein angehängtes Wörtchen erzwingt.

    »το πελατολόγιό του«, »το πρόγραμμά τους«, »το νόημά της« — das
    Substantiv trägt dann zwei Akzente, im Wortschatz steht es mit
    einem. Gibt die Form ohne den LETZTEN Akzent zurück, sonst None.

    Nur bei genau zwei Akzenten: bei einem ist nichts zu tun, bei
    mehr als zweien ist es kein Enklisefall, sondern etwas anderes.
    """
    stellen = [i for i, z in enumerate(wort) if z in _AKZENTE]
    if len(stellen) != 2:
        return None
    i = stellen[-1]
    return wort[:i] + pruefung.ohne_diakritika(wort[i]) + wort[i + 1:]


def _gross_geschrieben(wort: str) -> bool:
    """Fängt das Wort mit einem Großbuchstaben an?"""
    for z in wort:
        if z.isalpha():
            return z.isupper()
    return False


def _zuordnen(folge: list[dict], karte: dict[str, int],
              ohne_akzent: dict[str, int] | None = None) -> list[dict]:
    """Legt den Wortschatz über die Wortfolge — längstes Stück zuerst.

    »Το μήλο είναι κόκκινο« soll als »το μήλο« + »είναι« + »κόκκινο«
    gelesen werden und nicht als vier Einzelwörter, von denen zwei
    unbekannt sind. Die Länge des längsten Eintrags bestimmt, wie weit
    vorausgeschaut wird; mehr als ein paar Wörter ist das nie.

    Gierig von links, ohne Rückzug: ein Eintrag, der zufällig in der
    Mitte eines längeren beginnt, wird erst gar nicht geprüft. Das
    genügt — die Einträge sind Lemmata, keine Satzteile.
    """
    laengste = max((e.count(" ") + 1 for e in karte), default=1)
    ergebnis: list[dict] = []
    i = 0
    while i < len(folge):
        for laenge in range(min(laengste, len(folge) - i), 0, -1):
            teile = folge[i:i + laenge]
            zusammen = " ".join(w["vergleichsform"] for w in teile)
            lexem_id = karte.get(zusammen)
            # GRIECHISCHE GROSSBUCHSTABEN TRAGEN KEINEN AKZENT.
            #
            # Zeitungen schreiben »Ηταν«, »Ελληνας«, »Οχι« — im
            # Wortschatz steht ήταν, Έλληνας, όχι. Das ist keine Lücke
            # im Bestand, sondern eine Rechtschreibregel, und sie
            # gehört darum in den Vergleich. Im Artikel waren es zwölf
            # von 47 verbliebenen »unbekannten« Wörtern.
            #
            # Nur für großgeschriebene Wörter, und nur wo die
            # akzentlose Form eindeutig ist: sonst fiele »ποτέ« (nie)
            # mit »πότε« (wann) zusammen, und zwar unbemerkt.
            if (lexem_id is None and ohne_akzent
                    and all(_gross_geschrieben(w["wort"]) for w in teile)):
                lexem_id = ohne_akzent.get(
                    pruefung.ohne_diakritika(zusammen))
            # Enklise: »πελατολόγιό« ist »πελατολόγιο« mit dem Akzent,
            # den das folgende »του« erzwingt. Hier wird nur EIN
            # Akzent entfernt, nicht alle — die Form bleibt also
            # unterscheidbar, und geraten wird nichts.
            # Auch über die Wortgruppe: griechische Substantive stehen
            # mit Artikel im Wortschatz (»το πελατολόγιο«), und der
            # Enklise-Akzent sitzt auf dem Substantiv. Über das
            # Einzelwort allein fände man den Eintrag nie.
            if lexem_id is None:
                einfach = _ohne_zweitakzent(zusammen)
                if einfach:
                    lexem_id = karte.get(einfach)
            if lexem_id or laenge == 1:
                ergebnis.append({
                    "wort": " ".join(w["wort"] for w in teile),
                    "vergleichsform": zusammen,
                    "lexem_id": lexem_id,
                })
                i += laenge
                break
    return ergebnis


def deckung(db: sqlite3.Connection, text_id: int, benutzer_id: int) -> dict:
    """Könnte ich diesen Text übersetzen?

    Gibt jedes Wort einzeln zurück UND die Zusammenfassung. Einzeln,
    weil die Oberfläche die unbekannten Wörter hervorheben soll — wer
    nur eine Prozentzahl bekommt, weiß nicht, woran es liegt.
    """
    t = dbm.zeile(db, "SELECT * FROM text WHERE id = ?", (text_id,))
    if t is None:
        raise KeyError(f"Text {text_id} gibt es nicht")
    profil = sprachen.profil(t["sprache"])
    karte = _wortschatz(db, t["sammlung_id"], profil)
    staende = _lernstaende(db, t["sammlung_id"], benutzer_id)
    gewuenscht = _wortwunsch_formen(db, benutzer_id, t["sammlung_id"])
    bedeutungen = _bedeutungen(db, t["sammlung_id"])

    treffer: list[dict] = []
    # Je Vergleichsform nur einmal zählen — ein Text, in dem »και«
    # zwanzigmal steht, ist nicht zu 95 % gedeckt, nur weil ein
    # Allerweltswort oft vorkommt.
    gesehen: dict[str, dict] = {}
    ohne_akzent = _ohne_akzent_karte(karte)
    for stueck in _zuordnen(woerter(t["inhalt"], profil), karte, ohne_akzent):
        lexem_id = stueck["lexem_id"]
        art = staende.get(lexem_id, "neu") if lexem_id else "unbekannt"
        eintrag = {**stueck, "art": art,
                   "bedeutung": bedeutungen.get(lexem_id),
                   "gewuenscht": stueck["vergleichsform"] in gewuenscht}
        treffer.append(eintrag)
        gesehen.setdefault(stueck["vergleichsform"], eintrag)

    zahlen = {"sitzt": 0, "lernen": 0, "neu": 0, "unbekannt": 0}
    for eintrag in gesehen.values():
        zahlen[eintrag["art"]] += 1
    verschieden = len(gesehen) or 1

    return {
        "text_id": text_id,
        "woerter": treffer,
        "verschiedene_woerter": len(gesehen),
        "woerter_gesamt": len(treffer),
        "zahlen": zahlen,
        # Was beim Lesen trägt: alles, was im Wortschatz steht. »neu«
        # zählt mit, denn nachschlagen kann man es.
        "abdeckung": round(100 * (verschieden - zahlen["unbekannt"])
                           / verschieden),
        "sicher": round(100 * zahlen["sitzt"] / verschieden),
        "urteil": _urteil(zahlen, verschieden),
    }


def _urteil(zahlen: dict, verschieden: int) -> str:
    """Ein Satz statt einer Zahl — die Zahl steht ja daneben."""
    unbekannt = zahlen["unbekannt"]
    sitzt_anteil = zahlen["sitzt"] / verschieden
    if unbekannt == 0 and sitzt_anteil >= 0.8:
        return ("Das müsstest du können — jedes Wort steht in deinem "
                "Wortschatz, das meiste sitzt.")
    if unbekannt == 0:
        return ("Jedes Wort steht in deinem Wortschatz. Gelernt ist noch "
                "nicht alles, nachschlagen kannst du aber alles.")
    if unbekannt <= 3:
        return (f"Fast — {unbekannt} Wörter fehlen dir noch. "
                "Die kannst du gleich hier anfordern.")
    if unbekannt / verschieden <= 0.15:
        return (f"Machbar mit Hilfe: {unbekannt} von {verschieden} Wörtern "
                "stehen noch nicht in deinem Wortschatz.")
    return (f"Das ist noch zu früh: {unbekannt} von {verschieden} Wörtern "
            "kennst du nicht. Lieber erst einen leichteren Text.")


# --------------------------------------------------------------- Wortwünsche

def _wortwunsch_formen(db: sqlite3.Connection, benutzer_id: int,
                       sammlung_id: int) -> set[str]:
    return {z["vergleichsform"] for z in dbm.zeilen(db, """
        SELECT vergleichsform FROM wortwunsch
         WHERE benutzer_id = ? AND sammlung_id = ? AND erledigt = 0""",
        (benutzer_id, sammlung_id))}


def wort_merken(db: sqlite3.Connection, benutzer_id: int, text_id: int,
                wort: str, zusammenhang: str | None = None) -> dict:
    """»Das kenne ich nicht« — auf die Liste damit.

    Zweimal dasselbe Wort ergibt einen Eintrag, nicht zwei: verglichen
    wird die normierte Fassung. Sonst stünde »Και« vom Satzanfang neben
    »και« aus der Satzmitte, und die KI legte zwei Vokabeln an.
    """
    t = dbm.zeile(db, "SELECT * FROM text WHERE id = ?", (text_id,))
    if t is None:
        raise KeyError(f"Text {text_id} gibt es nicht")
    profil = sprachen.profil(t["sprache"])
    vergleichsform = pruefung._genau(wort.strip(_RAND), profil)
    if not vergleichsform:
        raise ValueError("Das ist kein Wort.")

    db.execute("""INSERT INTO wortwunsch (benutzer_id, sammlung_id, wort,
                                          vergleichsform, zusammenhang, text_id)
                  VALUES (?, ?, ?, ?, ?, ?)
                  ON CONFLICT (benutzer_id, sammlung_id, vergleichsform)
                  DO UPDATE SET erledigt = 0,
                                zusammenhang = COALESCE(excluded.zusammenhang,
                                                        wortwunsch.zusammenhang)""",
               (benutzer_id, t["sammlung_id"], wort.strip(_RAND),
                vergleichsform, zusammenhang, text_id))
    return dbm.zeile(db, """SELECT * FROM wortwunsch
                             WHERE benutzer_id = ? AND sammlung_id = ?
                               AND vergleichsform = ?""",
                     (benutzer_id, t["sammlung_id"], vergleichsform))


def alle_unbekannten_merken(db: sqlite3.Connection, benutzer_id: int,
                            text_id: int) -> dict:
    """Alle unbekannten Wörter eines Textes auf einmal anfordern.

    »Wenn ich einen ganz neuen Artikel hier rein poste, dann müsste
    ich alle Wörter markieren können, die ich nicht kenne. Wenn ich
    jetzt 260 mal klicke, macht das keinen Spaß.« — Gemessen an einem
    echten Zeitungsartikel waren es 840 von 1145.

    Die Auswahl trifft der Server, nicht die Oberfläche: er hat die
    Deckung gerade gerechnet und weiß, welche Wörter fehlen. Eine
    Liste von 840 Wörtern durch die Leitung zu schicken, nur damit er
    sie wieder nachschlägt, wäre doppelte Arbeit mit doppelter
    Gelegenheit, sich zu unterscheiden.

    Je Wort wird mitgeschrieben, wie oft es im Text vorkam und in
    welchem Satz es zuerst stand. Ohne das stünde die KI vor einem
    Haufen ohne Reihenfolge.
    """
    d = deckung(db, text_id, benutzer_id)
    t = dbm.zeile(db, "SELECT * FROM text WHERE id = ?", (text_id,))
    abschnitte = dbm.zeilen(db, """SELECT original FROM textabschnitt
                                    WHERE text_id = ? ORDER BY reihenfolge""",
                            (text_id,))

    gezaehlt: dict[str, dict] = {}
    for w in d["woerter"]:
        if w["lexem_id"] or w["gewuenscht"]:
            continue
        eintrag = gezaehlt.setdefault(
            w["vergleichsform"], {"wort": w["wort"], "n": 0})
        eintrag["n"] += 1

    def zusammenhang(wort: str) -> str | None:
        for a in abschnitte:
            if wort in a["original"]:
                return a["original"][:400]
        return None

    neu = 0
    for form, e in gezaehlt.items():
        db.execute("""INSERT INTO wortwunsch (benutzer_id, sammlung_id, wort,
                                              vergleichsform, zusammenhang,
                                              text_id, vorkommen)
                      VALUES (?, ?, ?, ?, ?, ?, ?)
                      ON CONFLICT (benutzer_id, sammlung_id, vergleichsform)
                      DO UPDATE SET erledigt = 0,
                                    vorkommen = MAX(wortwunsch.vorkommen,
                                                    excluded.vorkommen)""",
                   (benutzer_id, t["sammlung_id"], e["wort"], form,
                    zusammenhang(e["wort"]), text_id, e["n"]))
        neu += 1
    return {"text_id": text_id, "angefordert": neu}


def alle_zuruecknehmen(db: sqlite3.Connection, benutzer_id: int,
                       text_id: int) -> dict:
    """Alles, was aus DIESEM Text angefordert wurde, wieder weg.

    Nur die offenen: was die KI schon eingetragen hat, ist erledigt
    und bleibt als Beleg stehen.
    """
    t = dbm.zeile(db, "SELECT * FROM text WHERE id = ?", (text_id,))
    if t is None:
        raise KeyError(f"Text {text_id} gibt es nicht")
    cur = db.execute("""DELETE FROM wortwunsch
                         WHERE benutzer_id = ? AND text_id = ? AND erledigt = 0""",
                     (benutzer_id, text_id))
    return {"text_id": text_id, "entfernt": cur.rowcount}


def wort_vergessen(db: sqlite3.Connection, benutzer_id: int, text_id: int,
                   wort: str) -> None:
    """Doch gekannt — wieder herunter von der Liste."""
    t = dbm.zeile(db, "SELECT * FROM text WHERE id = ?", (text_id,))
    if t is None:
        raise KeyError(f"Text {text_id} gibt es nicht")
    vergleichsform = pruefung._genau(wort.strip(_RAND),
                                     sprachen.profil(t["sprache"]))
    db.execute("""DELETE FROM wortwunsch
                   WHERE benutzer_id = ? AND sammlung_id = ?
                     AND vergleichsform = ?""",
               (benutzer_id, t["sammlung_id"], vergleichsform))


def wortwuensche(db: sqlite3.Connection, benutzer_id: int,
                 sammlung_id: int | None = None,
                 offen: bool = True,
                 auch_aus_sammlungen: list[int] | None = None) -> list[dict]:
    """Die Liste, die die KI über den MCP abholt.

    `auch_aus_sammlungen` nimmt die Wünsche ANDERER Leute aus diesen
    Sammlungen mit. Das ist kein Zusatz, sondern der Normalfall in
    einer Familie: der Konnektor hängt an einem Profil, die Wünsche
    entstehen aber an allen. Max markiert Wörter in seinem
    mittelhochdeutschen Text, und die KI, die über ihr Zugang
    spricht, sah sie nicht — obwohl Annuschka in Max' Sammlung
    schreiben darf und die Wünsche also erfüllen KANN.

    Die Regel ist genau diese: was ich erfüllen darf, soll ich auch
    sehen. Dafür steht `zugang.beschreibbare_sammlungen`.
    """
    wer = ["w.benutzer_id = ?"]
    werte: list = [benutzer_id]
    if auch_aus_sammlungen:
        platz = ",".join("?" * len(auch_aus_sammlungen))
        wer.append(f"w.sammlung_id IN ({platz})")
        werte += list(auch_aus_sammlungen)
    bedingungen = ["(" + " OR ".join(wer) + ")"]
    if sammlung_id:
        bedingungen.append("w.sammlung_id = ?")
        werte.append(sammlung_id)
    if offen:
        bedingungen.append("w.erledigt = 0")
    return dbm.zeilen(db, f"""
        SELECT w.*, s.name AS sammlung, s.sprache, t.titel AS text,
               b.name AS wunsch_von, (w.benutzer_id = {int(benutzer_id)})
                   AS von_mir
          FROM wortwunsch w
          JOIN sammlung s ON s.id = w.sammlung_id
          JOIN benutzer b ON b.id = w.benutzer_id
          LEFT JOIN text t ON t.id = w.text_id
         WHERE {' AND '.join(bedingungen)}
         -- Häufigstes zuerst: wer eine Liste von achthundert Wörtern
         -- abarbeitet, soll oben anfangen können und etwas davon
         -- haben, auch wenn er nicht zu Ende kommt.
         ORDER BY w.vorkommen DESC, w.angelegt""", tuple(werte))


def wortwunsch_erledigen(db: sqlite3.Connection, wunsch_id: int,
                         lexem_id: int | None = None) -> dict:
    """Die KI hat die Vokabel angelegt — Haken dran.

    Der Eintrag wird NICHT gelöscht: er ist der Beleg, woher die Vokabel
    stammt, und er verhindert, dass dasselbe Wort beim nächsten Text
    erneut angefordert wird, bevor es freigegeben ist.
    """
    w = dbm.zeile(db, "SELECT * FROM wortwunsch WHERE id = ?", (wunsch_id,))
    if w is None:
        raise KeyError(f"Wortwunsch {wunsch_id} gibt es nicht")
    db.execute("UPDATE wortwunsch SET erledigt = 1, lexem_id = ? WHERE id = ?",
               (lexem_id, wunsch_id))
    return dbm.zeile(db, "SELECT * FROM wortwunsch WHERE id = ?", (wunsch_id,))


def wuensche_abhaken(db: sqlite3.Connection, benutzer_id: int,
                     zuordnungen: list[dict],
                     erlaubte_sammlungen: list[int] | None = None) -> dict:
    """Viele Wünsche auf einmal abhaken.

    »Über die Schnittstelle geht nur einer pro Aufruf, das wären über
    800 Aufrufe.«

    Je Zuordnung entweder `wunsch_id` oder `wort` — beim Wort wird über
    die Vergleichsform gesucht, denn so steht es in der Liste. Dazu die
    `lexem_id` des Eintrags, der das Wort jetzt abdeckt; sie darf
    fehlen, wenn das Wort bewusst ohne Vokabel abgehakt wird (ein
    Eigenname, eine Zahl, eine flektierte Form eines vorhandenen
    Wortes).

    Abgehakt wird nur, was diese Person auch erledigen DARF: eigene
    Wünsche und solche aus Sammlungen, in die sie schreiben kann —
    dieselbe Regel wie beim Lesen der Liste.

    DIE SUCHE ÜBER DAS WORT BLEIBT IN EINER SAMMLUNG. Beim ersten Lauf
    tat sie das nicht, und das Ergebnis war lehrreich: in einem
    griechischen Zeitungsartikel stehen deutsche Zitate, also stand
    »ich« auf der griechischen Wunschliste — und hakte prompt das
    gleichlautende »ich« in Max' mittelhochdeutscher Liste mit ab, 89
    Wünsche auf einen Schlag. Die Sammlung ergibt sich aus der
    `lexem_id`; ohne sie kann `sammlung_id` mitgegeben werden. Fehlt
    beides, bleibt es bei der sammlungsübergreifenden Suche — dann
    aber nur, wenn das Wort eindeutig ist.
    """
    import pruefung
    import sprachen

    wo = ["w.benutzer_id = ?"]
    werte: list = [benutzer_id]
    if erlaubte_sammlungen:
        platz = ",".join("?" * len(erlaubte_sammlungen))
        wo.append(f"w.sammlung_id IN ({platz})")
        werte += list(erlaubte_sammlungen)
    erlaubt = f"({' OR '.join(wo)})"

    # Einmal alle offenen holen statt je Zuordnung zu suchen: bei 777
    # Zuordnungen wären das 777 Abfragen, und die Vergleichsform muss
    # ohnehin nach den Regeln der Sprache gebildet werden.
    offen = dbm.zeilen(db, f"""
        SELECT w.*, s.sprache FROM wortwunsch w
          JOIN sammlung s ON s.id = w.sammlung_id
         WHERE w.erledigt = 0 AND {erlaubt}""", tuple(werte))
    nach_id = {w["id"]: w for w in offen}
    nach_form: dict[tuple, dict] = {}
    for w in offen:
        nach_form.setdefault((w["sammlung_id"], w["vergleichsform"]), w)
        # Zusätzlich die Schreibung selbst, falls die Zuordnung sie nennt.
        nach_form.setdefault((w["sammlung_id"], w["wort"]), w)

    # Zu welcher Sammlung gehört ein Lexem? Einmal nachschlagen statt
    # je Zuordnung.
    sammlung_von_lexem = {
        z["id"]: z["sammlung_id"] for z in dbm.zeilen(
            db, "SELECT id, sammlung_id FROM lexem")}

    abgehakt, unbekannt, schon, mehrdeutig = 0, [], 0, []
    for z in zuordnungen:
        w = None
        if z.get("wunsch_id"):
            w = nach_id.get(int(z["wunsch_id"]))
        else:
            wort = (z.get("wort") or "").strip()
            if not wort:
                continue
            # Die Sammlung eingrenzen, sobald sie bekannt ist.
            grenze = z.get("sammlung_id") or sammlung_von_lexem.get(
                z.get("lexem_id"))
            infrage = [k for k in offen
                       if grenze is None or k["sammlung_id"] == grenze]
            treffer = [k for k in infrage
                       if wort in (k["vergleichsform"], k["wort"])]
            if not treffer:
                # Noch einmal über die Vergleichsform der Sprache — so
                # findet »Έλληνας« auch den Wunsch »έλληνας«.
                treffer = [k for k in infrage
                           if pruefung.normalisieren(
                               wort, sprachen.profil(k["sprache"]))
                           == k["vergleichsform"]]
            if len(treffer) > 1:
                # Ohne Sammlung und mit mehreren Treffern wird NICHT
                # geraten: lieber stehenlassen und melden.
                mehrdeutig.append(wort)
                continue
            w = treffer[0] if treffer else None
        if w is None:
            unbekannt.append(z.get("wort") or z.get("wunsch_id"))
            continue
        if w["erledigt"]:
            schon += 1
            continue
        db.execute("UPDATE wortwunsch SET erledigt = 1, lexem_id = ? "
                   "WHERE id = ?", (z.get("lexem_id"), w["id"]))
        w["erledigt"] = 1
        abgehakt += 1
    return {"abgehakt": abgehakt, "schon_erledigt": schon,
            "nicht_gefunden": len(unbekannt),
            "beispiele_nicht_gefunden": unbekannt[:20],
            # Mehrdeutig heißt: dasselbe Wort steht in mehreren
            # Sammlungen offen und es wurde keine genannt. Dann wird
            # nichts abgehakt — raten wäre hier teuer.
            "mehrdeutig": len(mehrdeutig),
            "beispiele_mehrdeutig": mehrdeutig[:20],
            "noch_offen": dbm.wert(db, f"""SELECT COUNT(*) FROM wortwunsch w
                                            WHERE w.erledigt = 0 AND {erlaubt}""",
                                   tuple(werte))}


# -------------------------------------------------------------- Texte selbst

def anlegen(db: sqlite3.Connection, sammlung_id: int, titel: str,
            inhalt: str, **rest) -> dict:
    """Einen Text einwerfen. Mehr braucht es nicht: Titel und Inhalt.

    Die Abschnitte entstehen gleich mit, denn ohne sie gäbe es keine
    Einheit zum Übersetzen. Zerlegt wird an Leerzeilen (Absätze) und
    sonst an Satzenden — ein Absatz ist die natürliche Einheit, ein
    einzelner Satz die kleinere Ausweichmöglichkeit, wenn kein Absatz
    erkennbar ist.
    """
    s = dbm.zeile(db, "SELECT * FROM sammlung WHERE id = ?", (sammlung_id,))
    if s is None:
        raise KeyError(f"Sammlung {sammlung_id} gibt es nicht")
    if not (inhalt or "").strip():
        raise ValueError("Der Text ist leer.")

    cur = db.execute("""INSERT INTO text (sammlung_id, titel, sprache, inhalt,
                                          uebersetzung, niveau, quelle, notiz,
                                          typ, geprueft)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'lesetext', 1)""",
                     (sammlung_id, titel.strip() or "Ohne Titel",
                      rest.get("sprache") or s["sprache"], inhalt.strip(),
                      rest.get("uebersetzung"), rest.get("niveau"),
                      rest.get("quelle", "manuell"), rest.get("notiz")))
    text_id = cur.lastrowid
    _abschnitte_schreiben(db, text_id, inhalt)
    return lesen(db, text_id)


def _abschnitte_schreiben(db: sqlite3.Connection, text_id: int,
                          inhalt: str) -> None:
    db.execute("DELETE FROM textabschnitt WHERE text_id = ?", (text_id,))
    for i, stueck in enumerate(abschnitte_zerlegen(inhalt)):
        db.execute("""INSERT INTO textabschnitt (text_id, reihenfolge, original)
                      VALUES (?, ?, ?)""", (text_id, i, stueck))


def abschnitte_zerlegen(inhalt: str) -> list[str]:
    """Absätze, und nur ersatzweise Sätze.

    Ein Absatz ist die Einheit, in der man übersetzt — Satz für Satz
    zerreißt den Zusammenhang, auf den es beim Übersetzen gerade
    ankommt. Nur wenn jemand einen Block ohne Leerzeilen einwirft, wird
    an Satzenden getrennt, sonst stünde der ganze Text in einem Feld.
    """
    roh = (inhalt or "").strip()
    absaetze = [a.strip() for a in re.split(r"\n\s*\n", roh) if a.strip()]
    if len(absaetze) > 1:
        return absaetze
    # Ein Block: an Satzenden trennen, das Satzzeichen bleibt dabei stehen.
    saetze = [s.strip() for s in re.split(r"(?<=[.!?;·])\s+", roh) if s.strip()]
    return saetze or [roh]


def lesen(db: sqlite3.Connection, text_id: int,
          benutzer_id: int | None = None) -> dict:
    t = dbm.zeile(db, "SELECT * FROM text WHERE id = ?", (text_id,))
    if t is None:
        raise KeyError(f"Text {text_id} gibt es nicht")
    ergebnis = dict(t)
    ergebnis["abschnitte"] = [dict(a) for a in dbm.zeilen(db, """
        SELECT * FROM textabschnitt WHERE text_id = ?
         ORDER BY reihenfolge""", (text_id,))]
    if benutzer_id:
        eigene = {z["abschnitt_id"]: z["fassung"] for z in dbm.zeilen(db, """
            SELECT v.abschnitt_id, v.fassung FROM uebersetzungsversuch v
              JOIN textabschnitt a ON a.id = v.abschnitt_id
             WHERE a.text_id = ? AND v.benutzer_id = ?""",
            (text_id, benutzer_id))}
        for a in ergebnis["abschnitte"]:
            a["meine_fassung"] = eigene.get(a["id"], "")
    return ergebnis


def auflisten(db: sqlite3.Connection, sammlung_id: int) -> list[dict]:
    """Die Lesetexte einer Sammlung — mit dem Stand der Übersetzung.

    `uebersetzt` steht hier, weil sonst niemand weiß, wo er aufgehört
    hat. Beim mittelhochdeutschen Bestand sind es 173 Texte mit 8912
    Abschnitten; wer die übersetzt, tut es über Tage und braucht beim
    nächsten Mal die Antwort auf »welcher ist dran«. Ohne die Zahl
    bliebe nur, jeden Text einzeln zu öffnen und nachzusehen — oder
    Arbeit doppelt zu machen.

    Leerer Text zählt als nicht übersetzt: ein Abschnitt mit '' ist
    nicht übersetzt, er sieht nur so aus.

    GEORDNET NACH KAPITEL, darin in der Reihenfolge des Werks. Vorher
    stand hier `ORDER BY t.angelegt DESC` — das Neueste oben, richtig
    für eine Ablage, falsch für ein Buch: der Iwein liegt in 173
    Stücken vor (»Verse 1–38«, »Verse 39–86«, …), und die las man dann
    von hinten. Nach dem Titel zu ordnen wäre noch schlechter, da käme
    »Verse 135–182« vor »Verse 39–86«.

    Wer gerade einen Text eingeworfen hat, findet ihn trotzdem: das
    Einwerfen öffnet ihn sofort.
    """
    return dbm.zeilen(db, """
        SELECT t.id, t.titel, t.sprache, t.niveau, t.angelegt, t.notiz,
               t.lektion_id, k.nr AS lektion_nr, k.name AS lektion_name,
               t.buch_id, t.kapitel, b.titel AS buch_titel,
               LENGTH(t.inhalt) AS zeichen,
               (SELECT COUNT(*) FROM textabschnitt a WHERE a.text_id = t.id)
                 AS abschnitte,
               (SELECT COUNT(*) FROM textabschnitt a
                 WHERE a.text_id = t.id
                   AND a.referenz IS NOT NULL AND TRIM(a.referenz) != '')
                 AS uebersetzt
          FROM text t
          LEFT JOIN lektion k ON k.id = t.lektion_id
          LEFT JOIN buch b ON b.id = t.buch_id
         WHERE t.sammlung_id = ? AND t.typ = 'lesetext'
         ORDER BY k.nr IS NULL, k.nr, t.reihenfolge, t.angelegt, t.id""",
        (sammlung_id,))


def kapitel_setzen(db: sqlite3.Connection, sammlung_id: int,
                   text_ids: list[int], lektion_id: int | None) -> dict:
    """Texte in ein Kapitel hängen — oder wieder heraus.

    »Die Texte müssten wir noch zusammenfassbar machen, also Text –
    Kapitel. So ist das schwer für jemand, der damit lernt.«

    Bei den Wörtern entscheidet das Kapitel über die Lektionsschranke;
    hier entscheidet es gar nichts — es ordnet. Ein Text wird nicht
    früher oder später fällig, weil er in einem Kapitel steht. Darum
    ist das hier harmloser als beim Wortschatz, und darum steht keine
    Warnung dabei.

    Fremde Texte werden abgewiesen statt still übergangen: still
    übergangen sähe aus, als wäre umgehängt worden.
    """
    if not text_ids:
        return {"verschoben": 0, "lektion_id": lektion_id}
    platz = ",".join("?" * len(text_ids))
    eigene = {z["id"] for z in dbm.zeilen(
        db, f"SELECT id FROM text WHERE sammlung_id = ? AND id IN ({platz})",
        (sammlung_id, *text_ids))}
    fremd = [i for i in text_ids if i not in eigene]
    if fremd:
        raise ValueError(
            f"{len(fremd)} der Texte liegen nicht in dieser Sammlung.")
    db.execute(f"""UPDATE text SET lektion_id = ?,
                          geaendert = datetime('now')
                    WHERE id IN ({platz})""", (lektion_id, *text_ids))
    return {"verschoben": len(text_ids), "lektion_id": lektion_id}


def alle_fuer(db: sqlite3.Connection, benutzer_id: int) -> list[dict]:
    """Alle Lesetexte, die diese Person erreichen kann.

    Ohne Sammlungskennung — dasselbe Argument wie bei den Büchern: wer
    drei Sprachen lernt, hat ein Regal und nicht drei. Die Sammlung
    steht an jedem Text dabei, sie ist eine Eigenschaft und kein
    Eingang.

    Was in einem Buch steht, kommt zuerst; Loses zuletzt. `b.id IS
    NULL` muss dafür ausdrücklich davorstehen: SQLite sortiert NULL
    nach vorn, und ohne diese Zeile stand der eine unsortierte Text
    über dem ganzen Iwein.
    """
    import buecher
    sammlungen = buecher._zugaenglich(db, benutzer_id)
    if not sammlungen:
        return []
    platz = ",".join("?" * len(sammlungen))
    return dbm.zeilen(db, f"""
        SELECT t.id, t.titel, t.sprache, t.niveau, t.angelegt,
               t.sammlung_id, s.name AS sammlung,
               t.buch_id, t.kapitel, b.titel AS buch_titel,
               LENGTH(t.inhalt) AS zeichen,
               (SELECT COUNT(*) FROM textabschnitt a WHERE a.text_id = t.id)
                 AS abschnitte,
               (SELECT COUNT(*) FROM textabschnitt a
                 WHERE a.text_id = t.id
                   AND a.referenz IS NOT NULL AND TRIM(a.referenz) != '')
                 AS uebersetzt
          FROM text t
          JOIN sammlung s ON s.id = t.sammlung_id
          LEFT JOIN buch b ON b.id = t.buch_id
         WHERE t.sammlung_id IN ({platz}) AND t.typ = 'lesetext'
         ORDER BY b.id IS NULL, b.reihenfolge, b.titel,
                  t.reihenfolge, t.angelegt, t.id""",
        sammlungen)


def loeschen(db: sqlite3.Connection, text_id: int) -> None:
    if dbm.zeile(db, "SELECT 1 FROM text WHERE id = ?", (text_id,)) is None:
        raise KeyError(f"Text {text_id} gibt es nicht")
    db.execute("DELETE FROM text WHERE id = ?", (text_id,))


def fassung_sichern(db: sqlite3.Connection, abschnitt_id: int,
                    benutzer_id: int, fassung: str) -> dict:
    """Meine Übersetzung eines Abschnitts."""
    if dbm.zeile(db, "SELECT 1 FROM textabschnitt WHERE id = ?",
                 (abschnitt_id,)) is None:
        raise KeyError(f"Abschnitt {abschnitt_id} gibt es nicht")
    db.execute("""INSERT INTO uebersetzungsversuch
                      (abschnitt_id, benutzer_id, fassung, geaendert)
                  VALUES (?, ?, ?, datetime('now'))
                  ON CONFLICT (abschnitt_id, benutzer_id)
                  DO UPDATE SET fassung = excluded.fassung,
                                geaendert = datetime('now')""",
               (abschnitt_id, benutzer_id, fassung))
    return {"abschnitt_id": abschnitt_id, "fassung": fassung}


def nachschlagen(db: sqlite3.Connection, text_id: int, wort: str) -> dict:
    """Was weiß der Wortschatz über dieses Wort?

    Die Unterstützung beim Übersetzen, in ihrer einfachsten und
    ehrlichsten Form: nicht eine Maschinenübersetzung, sondern der
    eigene Eintrag. Steht er nicht da, sagt die Antwort das — und
    genau dann ist der Knopf »anfordern« richtig.
    """
    t = dbm.zeile(db, "SELECT * FROM text WHERE id = ?", (text_id,))
    if t is None:
        raise KeyError(f"Text {text_id} gibt es nicht")
    profil = sprachen.profil(t["sprache"])
    vergleichsform = pruefung._genau(wort.strip(_RAND), profil)
    lexem_id = _wortschatz(db, t["sammlung_id"], profil).get(vergleichsform)
    if not lexem_id:
        return {"wort": wort, "gefunden": False, "bedeutungen": []}

    lexem = dbm.zeile(db, "SELECT * FROM lexem WHERE id = ?", (lexem_id,))
    bedeutungen = []
    for b in dbm.zeilen(db, """SELECT * FROM bedeutung WHERE lexem_id = ?
                                ORDER BY reihenfolge""", (lexem_id,)):
        bedeutungen.append({
            "kontext": b["kontext"],
            "notiz": b["notiz"],
            "uebersetzungen": [u["text"] for u in dbm.zeilen(db, """
                SELECT text FROM uebersetzung WHERE bedeutung_id = ?
                 ORDER BY ist_haupt DESC, id""", (b["id"],))],
        })
    # Welche Form ist es denn? Das ist beim Übersetzen die halbe Miete:
    # »έγραψα« ist nicht »γράφω«, sondern dessen Aorist.
    form = dbm.zeile(db, """SELECT * FROM form
                             WHERE lexem_id = ? AND text = ?""",
                     (lexem_id, wort.strip(_RAND)))
    return {
        "wort": wort,
        "gefunden": True,
        "lexem_id": lexem_id,
        "lemma": lexem["lemma"],
        "wortart": lexem["wortart"],
        "bedeutungen": bedeutungen,
        "merkmale": json.loads(form["merkmale"]) if form else None,
    }


def referenz_setzen(db: sqlite3.Connection, text_id: int,
                    fassungen: dict[int, str]) -> dict:
    """Die Referenzübersetzung je Abschnitt — der Vorschlag von außen.

    Sie wird angezeigt, seit es Abschnitte gibt, war aber nirgends zu
    setzen: kein Formular, kein Endpunkt, kein Werkzeug. Die
    angebundene KI konnte also gar keinen Vorschlag hinterlegen,
    obwohl der Platz dafür dastand.

    Sie überschreibt NICHT die eigene Fassung. Das sind zwei Dinge:
    die Referenz gehört zum Text, der Versuch gehört zur Person —
    sonst hätte ein Vorschlag von außen die eigene Arbeit gelöscht.
    """
    if dbm.zeile(db, "SELECT 1 FROM text WHERE id = ?", (text_id,)) is None:
        raise KeyError(f"Text {text_id} gibt es nicht")
    eigene = {z["id"] for z in dbm.zeilen(db, """
        SELECT id FROM textabschnitt WHERE text_id = ?""", (text_id,))}
    fremd = set(map(int, fassungen or {})) - eigene
    if fremd:
        raise ValueError(f"Diese Abschnitte gehören nicht zum Text: "
                         f"{sorted(fremd)}")
    for abschnitt_id, fassung in (fassungen or {}).items():
        db.execute("UPDATE textabschnitt SET referenz = ? WHERE id = ?",
                   (fassung or None, int(abschnitt_id)))
    return {"text_id": text_id, "abschnitte": len(fassungen or {})}
