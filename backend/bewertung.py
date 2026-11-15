"""Die Bewertung aus den Antworten ableiten statt zu fragen.

Selbsteinschätzung ist der schwächste Punkt der üblichen Wiederholungssysteme.
Wer gerade die Lösung gesehen hat, hält sie für leichter, als sie war — und
niemand bewertet sich über Monate gleichmäßig. Dabei liegen bessere Signale
schon vor:

1. **Richtigkeit.** Das offensichtliche, aber allein zu grob: richtig ist
   nicht gleich richtig.
2. **Die Fehlerart.** Ein fehlender Akzent ist etwas anderes als eine mit
   einer anderen Form verwechselte Antwort. Das erste ist Schreibung, das
   zweite ist Nichtwissen.
3. **Ob ein zweiter Versuch nötig war.**
4. **Die Denkzeit bis zum ersten Tastendruck.** Das ist das Abrufmaß. Die
   Gesamtzeit taugt dafür nicht: sie misst zu großen Teilen Tippgeschwindigkeit
   und Wortlänge mit.

Die Denkzeit wird nicht absolut gewertet, sondern gegen die **eigene** übliche
Zeit bei dieser Aufgabenart. Wer langsam tippt, wird dadurch nicht bestraft;
gemessen wird nur, ob es heute schneller oder zäher ging als sonst.

Solange zu wenige eigene Messwerte vorliegen, wirkt die Zeit nur bei
eindeutigen Ausschlägen. Und wer die Zeitmessung abschaltet — im
Legastheniemodus voreingestellt —, wird allein nach Richtigkeit bewertet.
"""

from __future__ import annotations

import sqlite3
import statistics

import datenbank as dbm
from fsrs import BEWERTUNGEN, GUT, LEICHT, NOCHMAL, SCHWER

# Ab so vielen eigenen Messwerten gilt die Bezugszeit als belastbar.
GENUG_MESSWERTE = 6

# Ab wann eine Denkzeit keine Denkzeit mehr ist.
#
# Aus dem Betrieb: »manchmal wird etwas als wacklig beurteilt, wo ich mir
# denke, nie im Leben habe ich so lange gebraucht«. Im Protokoll stand
# als Höchstwert 103 Sekunden. Das ist kein zähes Nachdenken, das ist
# eine Unterbrechung — das Telefon klingelt, jemand kommt zur Tür, die
# Seite liegt im Hintergrund.
#
# Beim Bilden des Bezugsmedians wurden solche Werte längst
# ausgeschlossen (BETWEEN 200 AND 60000). Für die EINZELNE Messung galt
# das nicht: sie wurde voll gegen die Schwelle gehalten und zog die
# Bewertung herunter. Dieselbe Spanne gilt jetzt für beides — was zum
# Median nicht taugt, taugt auch nicht zum Urteil.
MESSUNG_MIN_MS, MESSUNG_MAX_MS = 200, 60000


def messung_brauchbar(denkzeit_ms: int | None) -> bool:
    """Ist diese Zeitmessung überhaupt eine Aussage über das Können?"""
    return (denkzeit_ms is not None
            and MESSUNG_MIN_MS <= denkzeit_ms <= MESSUNG_MAX_MS)
MESSWERTE_FENSTER = 60

# Grenzen für das Verhältnis Denkzeit zu Bezugszeit.
SEHR_SCHNELL = 0.55
ZAEH = 2.0

# Ersatzbezug, solange eigene Werte fehlen: Grundzeit plus etwas je Zeichen
# der erwarteten Antwort.
GRUNDZEIT_MS = 1400
JE_ZEICHEN_MS = 45
BEZUG_MIN, BEZUG_MAX = 1200, 8000


def bezugszeit(db: sqlite3.Connection, benutzer_id: int, typ: str,
               zeichen: int = 8) -> tuple[float, int]:
    """Die übliche Denkzeit dieser Person bei dieser Aufgabenart.

    Der Median, nicht der Mittelwert — ein einzelnes Telefonat mitten in der
    Sitzung soll den Bezug nicht verschieben.
    """
    werte = [z["denkzeit_ms"] for z in dbm.zeilen(db, """
        SELECT w.denkzeit_ms
          FROM wiederholung w
          JOIN aufgabe a ON a.id = w.aufgabe_id
         WHERE w.benutzer_id = ? AND a.typ = ?
           AND w.urteil = 'richtig' AND w.denkzeit_ms IS NOT NULL
           AND w.denkzeit_ms BETWEEN 200 AND 60000
         ORDER BY w.zeitpunkt DESC
         LIMIT ?""", (benutzer_id, typ, MESSWERTE_FENSTER))]
    if len(werte) >= GENUG_MESSWERTE:
        return float(statistics.median(werte)), len(werte)
    ersatz = min(BEZUG_MAX, max(BEZUG_MIN, GRUNDZEIT_MS + JE_ZEICHEN_MS * zeichen))
    return float(ersatz), len(werte)


def einschaetzen(urteil: str, fehlerart: str | None = None,
                 denkzeit_ms: int | None = None, versuche: int = 1,
                 aufgedeckt: bool = False, bezug_ms: float | None = None,
                 messwerte: int = 0, zeitmessung: bool = True,
                 tipps: int = 0) -> dict:
    """Leitet die Bewertung 1 bis 4 ab und begründet sie in Klartext.

    Die Begründung ist kein Beiwerk: wer nicht selbst bewertet, muss sehen
    können, wonach bewertet wurde. Sonst wird aus dem Fortschritt wieder eine
    Blackbox, und genau das soll dieser Trainer nicht sein.
    """
    gruende: list[str] = []

    # ---- Grundlage: was ist herausgekommen?
    if aufgedeckt:
        note = NOCHMAL
        gruende.append("Aufgedeckt statt geraten")
    elif urteil == "falsch":
        note = NOCHMAL
        gruende.append("Nicht gewusst"
                       if fehlerart != "verwechslung"
                       else "Mit einer anderen Form verwechselt")
    elif urteil == "fast" or versuche > 1:
        note = SCHWER
        if fehlerart == "diakritika":
            gruende.append("Richtig, aber die Zeichen saßen nicht")
        elif fehlerart in ("doppelung_zuwenig", "doppelung_zuviel"):
            gruende.append("Richtig, aber die Schreibung wackelte")
        elif fehlerart:
            gruende.append("Erst im zweiten Anlauf richtig")
        else:
            gruende.append("Fast richtig, dann richtig")
    elif tipps:
        # Mit Tipp gewusst ist nicht »auf Anhieb«, aber auch nicht
        # »nicht gewusst«: die Antwort kam ja selbst. Darum Schwer.
        note = SCHWER
        gruende.append("Richtig, aber mit Tipp"
                       if tipps == 1 else f"Richtig, aber mit {tipps} Tipps")
    else:
        note = GUT
        gruende.append("Auf Anhieb richtig")

    # ---- Verfeinerung: wie zäh ging es?
    zeitwert = None
    if zeitmessung and bezug_ms and messung_brauchbar(denkzeit_ms):
        zeitwert = denkzeit_ms / bezug_ms
        belastbar = messwerte >= GENUG_MESSWERTE
        # Ohne genug eigene Messwerte nur bei deutlichen Ausschlägen eingreifen.
        schnell = SEHR_SCHNELL if belastbar else SEHR_SCHNELL * 0.7
        zaeh = ZAEH if belastbar else ZAEH * 1.6

        if note == GUT and zeitwert <= schnell:
            note = LEICHT
            gruende.append(f"und sofort da ({denkzeit_ms / 1000:.1f} s)"
                           .replace(".", ","))
        elif note == GUT and zeitwert >= zaeh:
            note = SCHWER
            gruende.append(f"aber lange gesucht ({denkzeit_ms / 1000:.1f} s "
                           f"statt sonst {bezug_ms / 1000:.1f} s)"
                           .replace(".", ","))
        elif note == SCHWER and zeitwert >= zaeh and urteil != "richtig":
            gruende.append("und lange gesucht")
        elif note == GUT:
            gruende.append(f"in gewohnter Zeit ({denkzeit_ms / 1000:.1f} s)"
                           .replace(".", ","))

    begruendung = ", ".join(gruende) + "."
    return {
        "bewertung": note,
        "name": BEWERTUNGEN[note],
        "begruendung": begruendung[0].upper() + begruendung[1:],
        "automatisch": True,
        "signale": {
            "urteil": urteil,
            "fehlerart": fehlerart,
            "versuche": versuche,
            "aufgedeckt": aufgedeckt,
            "denkzeit_ms": denkzeit_ms,
            "bezugszeit_ms": round(bezug_ms) if bezug_ms else None,
            "zeitwert": round(zeitwert, 2) if zeitwert else None,
            "eigene_messwerte": messwerte,
            # Dieselbe Bedingung wie oben beim Urteil, nicht eine
            # ähnliche. Sie stand hier als »zeitmessung and denkzeit_ms
            # and bezug_ms« und meldete damit `true`, nachdem die
            # Messung als unbrauchbar verworfen worden war — die
            # Begründung, die sie aufklappt, behauptete also, die Zeit
            # habe gezählt. Eine Begründung, die nicht stimmt, ist
            # schlimmer als keine.
            "zeit_gewertet": bool(zeitmessung and bezug_ms
                                  and messung_brauchbar(denkzeit_ms)),
        },
    }


def fuer_aufgabe(db: sqlite3.Connection, benutzer_id: int, aufgabe_id: int,
                 urteil: str, fehlerart: str | None = None,
                 denkzeit_ms: int | None = None, versuche: int = 1,
                 aufgedeckt: bool = False, erwartet: str | None = None,
                 zeitmessung: bool = True, tipps: int = 0) -> dict:
    """Bewertung für eine bestimmte Aufgabe, mit dem passenden Zeitbezug."""
    a = dbm.zeile(db, "SELECT typ FROM aufgabe WHERE id = ?", (aufgabe_id,))
    typ = a["typ"] if a else "bedeutung_fremd_deutsch"
    bezug, messwerte = bezugszeit(db, benutzer_id, typ, len(erwartet or "") or 8)
    return einschaetzen(urteil, fehlerart, denkzeit_ms, versuche, aufgedeckt,
                        bezug, messwerte, zeitmessung, tipps)
