"""Die Bewertung wird aus den Antworten abgeleitet, nicht erfragt."""

import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "backend"))

import bewertung
from fsrs import GUT, LEICHT, NOCHMAL, SCHWER


def e(**kw):
    vorgabe = dict(urteil="richtig", fehlerart=None, denkzeit_ms=2000,
                   versuche=1, aufgedeckt=False, bezug_ms=2000, messwerte=20,
                   zeitmessung=True)
    return bewertung.einschaetzen(**{**vorgabe, **kw})


# ------------------------------------------------------------ Richtigkeit

def test_falsch_heisst_nochmal():
    assert e(urteil="falsch")["bewertung"] == NOCHMAL


def test_aufgedeckt_heisst_nochmal():
    urteil = e(urteil="falsch", aufgedeckt=True)
    assert urteil["bewertung"] == NOCHMAL
    assert "Aufgedeckt" in urteil["begruendung"]


def test_verwechslung_wird_benannt():
    assert "verwechselt" in e(urteil="falsch", fehlerart="verwechslung")["begruendung"]


def test_auf_anhieb_richtig_in_gewohnter_zeit_ist_gut():
    assert e(denkzeit_ms=2000)["bewertung"] == GUT


def test_zweiter_anlauf_ist_schwer():
    assert e(urteil="fast", versuche=2, fehlerart="tippfehler")["bewertung"] == SCHWER


def test_akzentfehler_wird_als_schreibung_benannt():
    urteil = e(urteil="fast", versuche=2, fehlerart="diakritika")
    assert urteil["bewertung"] == SCHWER
    assert "Zeichen" in urteil["begruendung"]


# ------------------------------------------------------------------- Zeit

def test_sofort_da_ist_leicht():
    assert e(denkzeit_ms=800, bezug_ms=2500)["bewertung"] == LEICHT


def test_lange_gesucht_ist_schwer_trotz_richtig():
    urteil = e(denkzeit_ms=7000, bezug_ms=2500)
    assert urteil["bewertung"] == SCHWER
    assert "lange gesucht" in urteil["begruendung"]


def test_die_zeit_wird_gegen_die_eigene_gewohnheit_gemessen():
    """Wer langsam tippt, soll nicht bestraft werden. Gemessen wird nur, ob es
    heute zäher ging als sonst."""
    # Dieselbe absolute Zeit, verschiedene Gewohnheiten.
    schnelle_person = e(denkzeit_ms=4000, bezug_ms=1500)
    langsame_person = e(denkzeit_ms=4000, bezug_ms=5000)
    assert schnelle_person["bewertung"] == SCHWER
    assert langsame_person["bewertung"] == GUT


def test_ohne_genug_messwerte_wirkt_die_zeit_nur_bei_ausschlaegen():
    # Leicht erhöhte Zeit, kaum eigene Werte: keine Abwertung.
    assert e(denkzeit_ms=5200, bezug_ms=2000, messwerte=1)["bewertung"] == GUT
    # Deutlicher Ausschlag: doch.
    assert e(denkzeit_ms=9000, bezug_ms=2000, messwerte=1)["bewertung"] == SCHWER


def test_abgeschaltete_zeitmessung_wertet_nur_die_richtigkeit():
    """Im Legastheniemodus voreingestellt. Zeitdruck verschlechtert gerade
    dort das Ergebnis."""
    assert e(denkzeit_ms=12000, zeitmessung=False)["bewertung"] == GUT
    assert e(denkzeit_ms=300, zeitmessung=False)["bewertung"] == GUT


def test_begruendung_ist_immer_lesbar():
    for fall in ({}, {"urteil": "falsch"}, {"urteil": "fast", "versuche": 2},
                 {"denkzeit_ms": None}, {"zeitmessung": False}):
        urteil = e(**fall)
        assert urteil["begruendung"].endswith(".")
        assert urteil["begruendung"][0].isupper()


def test_signale_werden_mitgeliefert():
    """Wer nicht selbst bewertet, muss sehen können, wonach bewertet wurde."""
    s = e(denkzeit_ms=800, bezug_ms=2500)["signale"]
    assert s["zeitwert"] == 0.32 and s["zeit_gewertet"] is True
    assert s["bezugszeit_ms"] == 2500
