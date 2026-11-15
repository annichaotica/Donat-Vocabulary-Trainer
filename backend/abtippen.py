"""Abtippen — sich mit den Wörtern vertraut machen.

»Alle Vokabeln zeigen, deutsch französisch und abtippen, erfolgreich
abgetippt, dann nächste. Sie muss sich erst mal mit den Wörtern
vertraut machen.«

Das ist ausdrücklich KEINE Abfrage, und darum liegt es neben dem
Lernkern statt darin:

  Die Abfrage fragt ab, was man schon kennt, und rechnet aus dem
  Ergebnis einen Termin. Wer ein Wort zum ersten Mal sieht, hat auf
  diese Frage keine Antwort — er rät, liegt daneben, und FSRS merkt
  sich einen Fehlschlag, der nichts über sein Gedächtnis sagt.

  Hier steht die Lösung von Anfang an da. Abgetippt wird, was man
  sieht. Das prüft nichts und soll nichts prüfen; es führt die Hand
  über das Wort, und genau darum geht es beim ersten Mal.

DREI FOLGERUNGEN, die den ganzen Zuschnitt bestimmen:

1. **Es wird kein Lernstand geschrieben.** Keine Bewertung, kein
   Termin, kein Eintrag im Protokoll der Wiederholungen. Eine
   abgeschriebene Vokabel als »gewusst« zu verbuchen würde den Plan
   verfälschen, und zwar genau für die Wörter, die noch niemand kann.

2. **Die Reihenfolge ist die des Lehrwerks**, nicht die der
   Fälligkeit: Lektion, dann die Folge innerhalb der Lektion. Wer sich
   vertraut macht, geht eine Liste durch.

3. **Geprüft wird trotzdem richtig** — mit dem Sprachprofil, also mit
   den Regeln für Akzente und Groß- und Kleinschreibung dieser
   Sprache. Ein »c'est« mit falschem Apostroph soll auffallen; dafür
   tippt man es ja ab.
"""

from __future__ import annotations

import sqlite3

import datenbank as dbm
import pruefung
import sprachen


def _karte(zeile: dict) -> dict:
    return {
        "lexem_id": zeile["id"],
        "fremd": zeile["lemma"],
        "deutsch": zeile["deutsch"] or "",
        # Getrennt mit 0x1F, dem Trennzeichen fuer Datenfelder: es
        # kommt in keiner Uebersetzung vor. Ein Komma taete es
        # nicht, "Hund, Ruede" waere dann zwei Eintraege. Als
        # Escape-Folge geschrieben und nicht als Zeichen selbst:
        # unsichtbare Steuerzeichen im Quelltext ueberlebt kein
        # Editor zuverlaessig.
        "weitere": [t for t in (zeile["weitere"] or "").split("\x1f")
                    if t],
        "ungeprueft": bool(zeile["ungeprueft"]),
        "wortart": zeile["wortart"],
        "lektion": zeile["lektion"],
        "lektion_nr": zeile["lektion_nr"],
    }


def reihe(db: sqlite3.Connection, sammlung_id: int,
          lektion_id: int | None = None) -> dict:
    """Die Wörter einer Sammlung in Lehrwerksreihenfolge.

    Dieselbe Bedingung wie für eine Vokabelabfrage: eine Übersetzung
    in der Grundsprache. Mehr nicht.

    Der erste Entwurf wollte zusätzlich eine Freigabe verlangen — beim
    Abtippen steht die Lösung ja die ganze Zeit da, und eine erfundene
    Vokabel prägt sich dabei besonders gut ein. Das klang richtig und
    war es nicht, aus zwei Gründen:

      `uebersetzung.geprueft` gibt es zwar als Spalte, aber keine
      Stelle im ganzen Projekt setzt sie je auf 1. Ein Filter darauf
      ließ schlicht nichts durch.

      Und auf die Formen auszuweichen, half auch nicht: Wörter aus dem
      Sammelimport haben gar keine Form, nur Bedeutungen. Die Hürde
      hätte genau den Fall ausgesperrt, für den das hier gebaut wird —
      eine frisch eingelesene Vokabelliste.

    Entscheidend aber: `aufgaben.erzeugen` legt die Vokabelaufgaben
    allein danach an, ob eine Übersetzung da ist. Eine strengere Regel
    hier hieße, dass der Trainer ein Wort abfragt, das er zum Abtippen
    verschweigt. Zwei Maßstäbe für dieselbe Vokabel, und der
    unauffälligere gewinnt dann im Zweifel.

    Stattdessen wird Ungeprüftes MITGEZÄHLT und gemeldet, und die
    Oberfläche schreibt es hin. Hinweisen statt verstecken.
    """
    s = dbm.zeile(db, "SELECT * FROM sammlung WHERE id = ?", (sammlung_id,))
    if s is None:
        raise KeyError(f"Sammlung {sammlung_id} gibt es nicht")

    bedingungen = ["l.sammlung_id = ?"]
    werte: list = [s["grundsprache"], sammlung_id]
    if lektion_id is not None:
        bedingungen.append("l.lektion_id = ?")
        werte.append(lektion_id)

    zeilen = dbm.zeilen(db, f"""
        SELECT l.id, l.lemma, l.wortart, k.name AS lektion, k.nr AS lektion_nr,
               EXISTS (SELECT 1 FROM form f
                        WHERE f.lexem_id = l.id AND f.geprueft = 0)
                   AS ungeprueft,
               (SELECT u.text FROM bedeutung b
                  JOIN uebersetzung u ON u.bedeutung_id = b.id
                 WHERE b.lexem_id = l.id AND u.sprache = ?1
                 ORDER BY b.reihenfolge, b.id, u.ist_haupt DESC, u.id
                 LIMIT 1) AS deutsch,
               (SELECT group_concat(u.text, char(31)) FROM bedeutung b
                  JOIN uebersetzung u ON u.bedeutung_id = b.id
                 WHERE b.lexem_id = l.id AND u.sprache = ?1
               ) AS weitere
          FROM lexem l
          LEFT JOIN lektion k ON k.id = l.lektion_id
         WHERE {' AND '.join(bedingungen)}
         ORDER BY COALESCE(k.nr, 9999), COALESCE(k.reihenfolge, 0),
                  l.reihenfolge, l.id""", werte)

    karten = [_karte(z) for z in zeilen if z["deutsch"]]
    return {
        "sammlung_id": sammlung_id,
        "sammlung": s["name"],
        "sprache": s["sprache"],
        "grundsprache": s["grundsprache"],
        "karten": karten,
        # Ehrlich mitzählen statt stillschweigend weglassen: wer 84
        # Wörter erwartet und 71 bekommt, soll erfahren warum.
        "ohne_uebersetzung": sum(1 for z in zeilen if not z["deutsch"]),
        # Nicht ausgesiebt, nur gezählt — die Oberfläche sagt es dazu.
        # Beim Abschreiben prägt sich auch eine falsche Schreibung ein.
        "ungeprueft": sum(1 for z in zeilen if z["deutsch"] and z["ungeprueft"]),
    }


def pruefen(db: sqlite3.Connection, lexem_id: int, eingabe: str) -> dict:
    """Stimmt das Abgetippte?

    Mit demselben Maßstab wie die Abfrage — `pruefung.pruefen` und das
    Sprachprofil. Ein eigener, nachsichtigerer Vergleich wäre hier
    besonders verkehrt: beim Abtippen ist die Vorlage sichtbar, also
    ist jede Abweichung ein Vertipper und keine Wissenslücke, und
    gerade den soll man sehen.
    """
    l = dbm.zeile(db, """SELECT l.*, s.sprache FROM lexem l
                           JOIN sammlung s ON s.id = l.sammlung_id
                          WHERE l.id = ?""", (lexem_id,))
    if l is None:
        raise KeyError(f"Lexem {lexem_id} gibt es nicht")

    # Gültig ist das Lemma — das steht ja da. Dazu die Grundform, falls
    # sie anders geschrieben ist: bei »le chien« ist das »chien«, und
    # wer den Artikel wegläßt, hat das Wort trotzdem abgetippt.
    gueltig = [l["lemma"]]
    grund = dbm.wert(db, """SELECT text FROM form
                             WHERE lexem_id = ? AND ist_grundform = 1
                             LIMIT 1""", (lexem_id,))
    if grund and grund not in gueltig:
        gueltig.append(grund)

    urteil = pruefung.pruefen(eingabe, gueltig, sprachen.profil(l["sprache"]))
    return {
        "lexem_id": lexem_id,
        "urteil": urteil.urteil,
        "hinweis": urteil.hinweis,
        "fehlertext": getattr(urteil, "fehlertext", None),
        # Die Lösung mitzugeben ist hier kein Verrat — sie stand die
        # ganze Zeit auf der Karte.
        "erwartet": gueltig,
    }
