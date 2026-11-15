"""Wann führt das Lehrwerk welche Formgruppe ein?

»Bei den Anfängerkapiteln, die ich mir gerade ansehe, habe ich noch gar
nicht alle Zeitformen gelernt.«

Gemessen am griechischen Bestand: von 6971 Formaufgaben waren 832
Präsens und rund 2900 Aorist, Futur und Passiv — alles im selben Topf,
aus dem die Tagesdosis zieht. Ein Schalter je Lernziel hätte das nicht
geheilt, die allgemeine Abfrage zieht ja weiter alles.

Die Lektionsnamen sagen es selbst:

    14  Verben im Präsens I          39  Aorist I (Vergangenheit)
    10  Plural                       40  Konjunktiv und Futur (να / θα)
    13  Akkusativ                    45  Passiv Präsens
    17  Genitiv                      53  Komparativ und Superlativ

Darum wird die Schranke nicht von Hand gepflegt, sondern an den
Lehrgang gebunden: je Sammlung steht, ab welcher Lektion eine
Formgruppe gilt (`formgruppe_lektion`), und je Person, wo sie steht
(`buchstand`). Wer bei Lektion 20 ist, bekommt keinen Aorist; wer bei
39 ankommt, bekommt ihn von selbst, ohne etwas umzustellen.

Der Vorschlag
-------------
`vorschlag()` liest die Lektionsnamen und schlägt die Zuordnung vor.
Das ist ein Vorschlag und bleibt einer: er wird angezeigt, nicht
angewandt. Namensraten ist zu unsicher, um stillschweigend Stoff
wegzunehmen — und ein Lehrwerk, das seine Kapitel »Einheit 7« nennt,
gibt gar nichts her. Dann trägt es jemand ein, von Hand oder über den
MCP.
"""

from __future__ import annotations

import re
import sqlite3

import datenbank as dbm
import sprachen


# Wörter, die in fast jedem Lektionsnamen vorkommen und nichts
# unterscheiden. Ohne sie träfe »Verben im Präsens I« auf jede Gruppe,
# in deren Namen »Verb« steckt.
_FUELLWOERTER = {"und", "oder", "der", "die", "das", "den", "dem", "im",
                 "in", "mit", "von", "zum", "zur", "ein", "eine", "als",
                 "verben", "verb", "wörter", "wort", "formen", "form",
                 # Ein Lehrwerk führt den PLURAL ein, nie den Singular —
                 # der ist die Grundform, über die kein Kapitel handelt.
                 # Bliebe er drin, gälte »Genitiv Singular« als
                 # unauffindbar, obwohl Lektion 17 »Genitiv« genau das
                 # einführt.
                 "singular"}

_TEILER = re.compile(r"[^0-9A-Za-zÄÖÜäöüßΆ-ώ]+")


def _woerter(text: str) -> list[str]:
    return [w for w in _TEILER.split((text or "").casefold())
            if len(w) >= 4 and w not in _FUELLWOERTER]


_KLAMMER = re.compile(r"\(([^)]+)\)")


def _suchname(name: str) -> str:
    """»Ενεστώτας Παθητικής (Präsens Passiv)« -> »Präsens Passiv«.

    Die Formgruppen heißen in der Landessprache, die Lektionen auf
    Deutsch. Verglichen wird deshalb die deutsche Fassung in der
    Klammer, wenn es eine gibt — sonst sucht man griechische Wörter in
    deutschen Überschriften und findet nie etwas.
    """
    treffer = _KLAMMER.search(name or "")
    return treffer.group(1) if treffer else (name or "")


def zuordnung(db: sqlite3.Connection, sammlung_id: int) -> dict[str, int]:
    """Was ist eingetragen? Formgruppe -> ab welcher Lektionsnummer."""
    return {z["formgruppe"]: z["ab_lektion"] for z in dbm.zeilen(db, """
        SELECT formgruppe, ab_lektion FROM formgruppe_lektion
         WHERE sammlung_id = ?""", (sammlung_id,))}


def zuordnung_setzen(db: sqlite3.Connection, sammlung_id: int,
                     neu: dict[str, int]) -> dict[str, int]:
    """Ersetzt die Zuordnung als Ganzes.

    Als Ganzes und nicht Feld für Feld: die Oberfläche zeigt sie
    vollständig, also ist das Weglassen einer Gruppe eine Aussage
    (»gilt von Anfang an«) und kein Versehen.
    """
    if dbm.zeile(db, "SELECT 1 FROM sammlung WHERE id = ?",
                 (sammlung_id,)) is None:
        raise KeyError(f"Sammlung {sammlung_id} gibt es nicht")
    db.execute("DELETE FROM formgruppe_lektion WHERE sammlung_id = ?",
               (sammlung_id,))
    for gruppe, nr in (neu or {}).items():
        if nr is None:
            continue
        db.execute("""INSERT INTO formgruppe_lektion
                          (sammlung_id, formgruppe, ab_lektion)
                      VALUES (?, ?, ?)""", (sammlung_id, str(gruppe), int(nr)))
    return zuordnung(db, sammlung_id)


def vorschlag(db: sqlite3.Connection, sammlung_id: int) -> list[dict]:
    """Welche Lektion führt welche Formgruppe ein — geraten aus den Namen.

    Gibt zu jeder Gruppe die Lektion mit, an der der Vorschlag hängt.
    Ohne diese Begründung müsste man dem Raten glauben; mit ihr sieht
    man auf einen Blick, dass »39 Aorist I« gemeint ist und nicht
    irgendeine Zahl.
    """
    s = dbm.zeile(db, "SELECT * FROM sammlung WHERE id = ?", (sammlung_id,))
    if s is None:
        raise KeyError(f"Sammlung {sammlung_id} gibt es nicht")
    lektionen = [z for z in dbm.zeilen(db, """
        SELECT nr, name FROM lektion
         WHERE sammlung_id = ? AND nr IS NOT NULL
         ORDER BY nr""", (sammlung_id,))]

    gefunden = []
    for gruppe, wortart in _alle_gruppen(s["sprache"]):
        marken = set(_woerter(_suchname(gruppe["name"])))
        # Die Lektion mit den MEISTEN Treffern gewinnt, bei Gleichstand
        # die frühere. Nur »die erste, die irgendein Wort enthält« war
        # falsch: »Ενεστώτας Παθητικής (Präsens Passiv)« landete damit
        # auf Lektion 14 »Verben im Präsens I« statt auf 45 »Passiv
        # Präsens« — die spezifischere Lektion stand weiter hinten.
        treffer, ab, eindeutig = _einfuehrung(marken, lektionen)
        gefunden.append({
            "formgruppe": gruppe["kennung"],
            "name": gruppe["name"],
            "wortart": wortart,
            "ab_lektion": ab,
            "eindeutig": eindeutig,
            "begruendung": (f"Lektion {treffer['nr']}: {treffer['name']}"
                            + ("" if eindeutig else " — ein Teil des Namens "
                                                    "kommt in keiner Lektion "
                                                    "vor, bitte nachsehen")
                            if treffer else
                            "Keine Lektion nennt sie — vermutlich von "
                            "Anfang an dabei."),
        })
    return gefunden


def _einfuehrung(marken: set[str], lektionen: list) -> tuple:
    """Ab welcher Lektion gilt eine Gruppe? (Lektion, Nummer, eindeutig)

    Zwei Wege, und beide braucht es:

    1. Nennt EINE Lektion alle Bestandteile, ist sie es — die früheste
       solche. »Aorist Passiv« steht wörtlich in Lektion 55, und die
       ist gemeint, nicht Lektion 45 »Passiv Präsens«, die zufällig
       auch »Passiv« enthält.

    2. Sonst muss man alle Bestandteile beisammen haben, und das ist
       man erst bei der SPÄTESTEN von ihnen. »Genitiv Plural« kann
       man, wenn man Genitiv (17) und Plural (10) hatte — also ab 17,
       nicht ab 10. Die frühere zu nehmen wäre der Fehler, der die
       Schranke zu früh öffnet.

    Eindeutig ist der Vorschlag nur, wenn JEDER Bestandteil irgendwo
    vorkommt. »Imperfekt Passiv« findet nur »Passiv« — das Buch führt
    das Imperfekt gar nicht ein, und darüber darf nicht stillschweigend
    entschieden werden.
    """
    if not marken:
        return None, None, False

    for l in lektionen:
        if marken <= set(_woerter(l["name"])):
            return l, l["nr"], True

    je_marke = {}
    for marke in marken:
        for l in lektionen:
            if marke in _woerter(l["name"]):
                je_marke[marke] = l
                break
    if not je_marke:
        return None, None, False
    spaeteste = max(je_marke.values(), key=lambda l: l["nr"])
    return spaeteste, spaeteste["nr"], len(je_marke) == len(marken)


def _alle_gruppen(sprache: str) -> list[tuple[dict, str]]:
    """Jede Gruppe mit ihrer Wortart.

    Die Wortart gehört dazu, weil die Namen sich wiederholen:
    »maskulin Nominativ Singular« gibt es bei Adjektiv, Pronomen,
    Artikel und Zahlwort. In einer Liste ohne Wortart stünde es
    viermal gleich da, und man wüsste nicht, was man anhakt.
    """
    gesehen, alle = set(), []
    for wortart in sprachen.profil(sprache).get("formgruppen", {}):
        for g in sprachen.formgruppen(sprache, wortart):
            if g["kennung"] in gesehen:
                continue
            gesehen.add(g["kennung"])
            alle.append((g, wortart))
    return alle


# ------------------------------------------------------------- Buchstand

def buchstand(db: sqlite3.Connection, benutzer_id: int,
              sammlung_id: int | None = None) -> dict[int, int]:
    """Wo steht diese Person — je Sammlung eine Lektionsnummer."""
    bedingung, werte = "benutzer_id = ?", [benutzer_id]
    if sammlung_id:
        bedingung += " AND sammlung_id = ?"
        werte.append(sammlung_id)
    return {z["sammlung_id"]: z["bis_lektion"] for z in dbm.zeilen(db, f"""
        SELECT sammlung_id, bis_lektion FROM buchstand
         WHERE {bedingung}""", tuple(werte))}


def buchstand_setzen(db: sqlite3.Connection, benutzer_id: int,
                     sammlung_id: int, bis_lektion: int | None) -> None:
    """`None` hebt die Schranke auf — dann gilt wieder alles.

    Das muss ausdrücklich gehen: wer sich auf eine Prüfung über den
    ganzen Stoff vorbereitet, will nicht bei Lektion 20 festhängen,
    nur weil er dort einmal stand.
    """
    if bis_lektion is None:
        db.execute("""DELETE FROM buchstand
                       WHERE benutzer_id = ? AND sammlung_id = ?""",
                   (benutzer_id, sammlung_id))
        return
    db.execute("""INSERT INTO buchstand (benutzer_id, sammlung_id, bis_lektion)
                  VALUES (?, ?, ?)
                  ON CONFLICT (benutzer_id, sammlung_id)
                  DO UPDATE SET bis_lektion = excluded.bis_lektion""",
               (benutzer_id, sammlung_id, int(bis_lektion)))


def ausgeblendet(db: sqlite3.Connection, benutzer_id: int,
                 sammlung_id: int) -> list[dict]:
    """Was die Schranke gerade zurückhält, mit Zahlen.

    Damit die Einstellung nicht im Blindflug geschieht: wer eine Zahl
    setzt, soll sehen, wie viele Aufgaben das betrifft — und dass der
    Lernstand dabei nicht verloren geht, sondern nur wartet.
    """
    stand = buchstand(db, benutzer_id, sammlung_id).get(sammlung_id)
    if stand is None:
        return []
    return dbm.zeilen(db, """
        SELECT g.formgruppe, g.ab_lektion, COUNT(a.id) AS aufgaben
          FROM formgruppe_lektion g
          JOIN aufgabe a ON a.formgruppe = g.formgruppe AND a.aktiv = 1
          JOIN lexem l ON l.id = a.lexem_id AND l.sammlung_id = g.sammlung_id
         WHERE g.sammlung_id = ? AND g.ab_lektion > ?
         GROUP BY g.formgruppe, g.ab_lektion
         ORDER BY g.ab_lektion""", (sammlung_id, stand))
