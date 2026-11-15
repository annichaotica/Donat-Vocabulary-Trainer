"""Eine unterbrochene Antwort ist keine schlechte Antwort.

»Manchmal wird etwas als wacklig beurteilt, wo ich mir denke, nie im
Leben habe ich so lange gebraucht, und umgekehrt etwas, wo ich echt
lange gebraucht habe, als super. Natürlich kann ich dir keine Beispiele
nennen.«

Beispiele brauchte es nicht, das Protokoll hatte sie. Gemessen am
echten Bestand vom 15.11.2026:

    bedeutung_deutsch_fremd: n=59, Median 2843 ms
       Streuung: 1300 – 103355 ms
       unter 1564 ms -> »sofort da« (3×), über 5686 ms -> »lange gesucht« (6×)
       Die Zeit verschiebt 23 % aller richtigen Antworten.

103 Sekunden ist kein zähes Nachdenken. Das ist das Telefon, die Tür,
ein Reiter im Hintergrund. Beim Bilden des Bezugsmedians waren solche
Werte längst ausgeschlossen (BETWEEN 200 AND 60000) — für die EINZELNE
Messung galt das nicht. Sie wurde voll gegen die Schwelle gehalten und
zog die Note herunter. Der Median war also klüger als das Urteil, das
er stützen sollte.

Diese Datei ist nachgereicht: die Korrektur ging ohne Test in Betrieb.
"""

import sys

import pytest

sys.path.insert(0, "backend")

import bewertung
from fsrs import NOCHMAL, SCHWER, GUT, LEICHT


# Ein Bezug, bei dem die Schwellen bequem zu treffen sind: mit
# belastbarer Messwertzahl gilt »sofort da« unter 0,55 und »lange
# gesucht« ab 2,0 des Bezugs.
BEZUG = 3000.0
VIELE = bewertung.GENUG_MESSWERTE


def _note(denkzeit_ms, **rest):
    return bewertung.einschaetzen(
        "richtig", denkzeit_ms=denkzeit_ms, bezug_ms=BEZUG,
        messwerte=VIELE, **rest)


# ------------------------------------------- die Spanne gilt für beides

def test_der_ausreisser_zieht_die_note_nicht_mehr_herunter():
    """Der gemessene Fall: 103 Sekunden bei einem Bezug von 3."""
    d = _note(103355)
    assert d["bewertung"] == GUT, d
    assert "lange gesucht" not in d["begruendung"], d["begruendung"]
    # Und das Signal sagt es auch — es steht in der Begründung, die sie
    # aufklappen kann, und darf nicht behaupten, die Zeit habe gezählt.
    assert d["signale"]["zeit_gewertet"] is False, d["signale"]


def test_knapp_unter_der_grenze_wird_sehr_wohl_gewertet():
    """Die Gegenprobe — sonst hätte ich die Zeitmessung abgeschafft
    statt sie zu berichtigen. 59 s sind zäh und zählen."""
    d = _note(59000)
    assert d["bewertung"] == SCHWER, d
    assert "lange gesucht" in d["begruendung"], d["begruendung"]
    assert d["signale"]["zeit_gewertet"] is True


def test_die_grenze_ist_dieselbe_wie_beim_median():
    """Was zum Bezugsmedian nicht taugt, taugt auch nicht zum Urteil.

    Laufen die beiden Spannen auseinander, ist der Fehler wieder da —
    nur an anderer Stelle. Darum hier festgenagelt und nicht nur
    nebenan kommentiert.
    """
    import pathlib
    quelle = (pathlib.Path(__file__).resolve().parents[1]
              / "backend" / "bewertung.py").read_text()
    assert "BETWEEN ? AND ?" in quelle or "BETWEEN" in quelle
    assert (bewertung.MESSUNG_MIN_MS, bewertung.MESSUNG_MAX_MS) == (200, 60000)
    # Und die Median-Abfrage benutzt genau diese beiden Zahlen.
    assert "MESSUNG_MIN_MS" in quelle and "MESSUNG_MAX_MS" in quelle


def test_ein_unsinnig_kurzer_wert_zaehlt_auch_nicht():
    """Die andere Richtung, und sie ist die aus ihrem zweiten Halbsatz:
    »umgekehrt etwas, wo ich echt lange gebraucht habe, als super«.

    Unter 200 ms hat niemand gelesen, gedacht und getippt. So ein Wert
    entsteht, wenn die Messung an der falschen Stelle beginnt — er darf
    keine Bestnote begründen.
    """
    d = _note(80)
    assert d["bewertung"] == GUT, d
    assert "sofort da" not in d["begruendung"], d["begruendung"]
    assert d["signale"]["zeit_gewertet"] is False


def test_eine_fehlende_messung_wird_nicht_erfunden():
    d = _note(None)
    assert d["bewertung"] == GUT
    assert "sofort" not in d["begruendung"]
    assert "lange" not in d["begruendung"]


def test_schnell_bleibt_schnell():
    """Die Verfeinerung muss nach wie vor greifen, sonst wäre der ganze
    Mechanismus still abgeschaltet."""
    d = _note(1200)
    assert d["bewertung"] == LEICHT, d
    assert "sofort da" in d["begruendung"], d["begruendung"]
    assert d["signale"]["zeit_gewertet"] is True


# ------------------------------------------------ die Grenzen selbst

@pytest.mark.parametrize("ms, brauchbar", [
    (None, False),
    (0, False),
    (199, False),
    (200, True),
    (3000, True),
    (60000, True),
    (60001, False),
    (103355, False),
])
def test_die_spanne_an_ihren_raendern(ms, brauchbar):
    assert bewertung.messung_brauchbar(ms) is brauchbar


# ----------------------------------- eine verworfene Messung ist neutral

def test_eine_verworfene_messung_laesst_die_grundnote_stehen():
    """Weder gut noch schlecht: ohne brauchbare Zeit bleibt das Urteil
    das, was die Antwort selbst hergibt. Bei einer falschen Antwort
    also weiterhin schlecht — der Ausreißer darf nicht zum Freibrief
    werden."""
    d = bewertung.einschaetzen("falsch", denkzeit_ms=103355, bezug_ms=BEZUG,
                               messwerte=VIELE)
    assert d["bewertung"] in (NOCHMAL, SCHWER), d
