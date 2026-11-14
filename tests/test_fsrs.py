import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "backend"))

import pytest
import fsrs
from fsrs import Zustand, bewerten, NOCHMAL, SCHWER, GUT, LEICHT


def test_bei_neunzig_prozent_ist_das_intervall_die_stabilitaet():
    # Die Stabilität ist als "Tage bis 90 % Erinnerung" definiert. Bei einer
    # Wunschretention von 90 % müssen Intervall und Stabilität zusammenfallen.
    assert fsrs.intervall(10.0, 0.9) == pytest.approx(10.0, rel=1e-6)


def test_abrufwahrscheinlichkeit_faellt_monoton():
    s = 10.0
    werte = [fsrs.abrufwahrscheinlichkeit(t, s) for t in (0, 1, 5, 10, 30, 100)]
    assert werte == sorted(werte, reverse=True)
    assert werte[0] == pytest.approx(1.0)
    assert fsrs.abrufwahrscheinlichkeit(10.0, 10.0) == pytest.approx(0.9, abs=1e-6)


def test_hoehere_wunschretention_kuerzt_das_intervall():
    assert fsrs.intervall(10.0, 0.95) < fsrs.intervall(10.0, 0.9) < fsrs.intervall(10.0, 0.8)


def test_erste_bewertung_je_besser_desto_laenger():
    neu = Zustand()
    tage = [bewerten(neu, b).intervall_tage for b in (NOCHMAL, SCHWER, GUT, LEICHT)]
    assert tage[0] == 0.0                       # "Nochmal" bleibt in der Sitzung
    assert tage[1] < tage[2] < tage[3]


def test_erste_bewertung_je_besser_desto_leichter():
    neu = Zustand()
    d = [bewerten(neu, b).schwierigkeit for b in (NOCHMAL, SCHWER, GUT, LEICHT)]
    assert d == sorted(d, reverse=True)
    assert all(1.0 <= x <= 10.0 for x in d)


def test_erfolg_steigert_die_stabilitaet():
    z = Zustand(stabilitaet=10.0, schwierigkeit=5.0)
    assert bewerten(z, GUT, verstrichen_tage=10.0).stabilitaet > 10.0


def test_vergessen_senkt_die_stabilitaet_aber_nicht_auf_null():
    z = Zustand(stabilitaet=50.0, schwierigkeit=5.0)
    e = bewerten(z, NOCHMAL, verstrichen_tage=60.0)
    assert 0 < e.stabilitaet < 50.0
    assert e.zustand == "verlernt"


def test_spaeter_wiederholen_bringt_mehr():
    # Der Kern des verteilten Lernens: eine Wiederholung kurz vor dem
    # Vergessen festigt stärker als eine gleich hinterher.
    z = Zustand(stabilitaet=10.0, schwierigkeit=5.0)
    frueh = bewerten(z, GUT, verstrichen_tage=2.0).stabilitaet
    spaet = bewerten(z, GUT, verstrichen_tage=10.0).stabilitaet
    assert spaet > frueh


def test_wiederholung_am_selben_tag_bewegt_kaum():
    z = Zustand(stabilitaet=20.0, schwierigkeit=5.0)
    e = bewerten(z, GUT, verstrichen_tage=0.0)
    assert 15.0 < e.stabilitaet < 30.0


def test_schwer_gibt_kuerzeres_intervall_als_gut():
    z = Zustand(stabilitaet=10.0, schwierigkeit=5.0)
    assert (bewerten(z, SCHWER, 10.0).intervall_tage
            < bewerten(z, GUT, 10.0).intervall_tage
            < bewerten(z, LEICHT, 10.0).intervall_tage)


def test_schwieriges_wissen_waechst_langsamer():
    leicht = Zustand(stabilitaet=10.0, schwierigkeit=2.0)
    zaeh = Zustand(stabilitaet=10.0, schwierigkeit=9.0)
    assert bewerten(leicht, GUT, 10.0).stabilitaet > bewerten(zaeh, GUT, 10.0).stabilitaet


def test_reif_ab_drei_wochen():
    z = Zustand(stabilitaet=40.0, schwierigkeit=5.0)
    assert bewerten(z, GUT, 40.0).zustand == "reif"
    assert bewerten(Zustand(), GUT).zustand == "lernen"


def test_vorschau_nennt_alle_vier_termine():
    v = fsrs.vorschau(Zustand(stabilitaet=10.0, schwierigkeit=5.0), 10.0)
    assert set(v) == {1, 2, 3, 4}
    assert v[1] == 0.0 and v[4] > v[3] > v[2]


def test_streuung_ist_pro_aufgabe_stabil():
    a = fsrs.streuen(100.0, saat=42)
    b = fsrs.streuen(100.0, saat=42)
    c = fsrs.streuen(100.0, saat=43)
    assert a == b and a != c
    assert 90 < a < 110


def test_kurze_intervalle_werden_nicht_gestreut():
    assert fsrs.streuen(2.0, saat=1) == 2.0


def test_ungueltige_bewertung():
    with pytest.raises(ValueError):
        bewerten(Zustand(), 7)


def test_erklaerung_fuer_neue_aufgabe():
    assert fsrs.erklaeren(Zustand(), 0.0)["neu"] is True


def test_erklaerung_nennt_prozent_und_lage():
    e = fsrs.erklaeren(Zustand(stabilitaet=10.0, schwierigkeit=5.0), 15.0)
    assert e["abrufwahrscheinlichkeit"] < 0.9
    assert "fällig seit" in e["text"]


def test_termintext():
    assert fsrs.tage_in_text(0) == "gleich noch einmal"
    assert fsrs.tage_in_text(1.2) == "morgen"
    assert fsrs.tage_in_text(14) == "in 14 Tagen"
    assert "Monaten" in fsrs.tage_in_text(90)
    assert "Jahren" in fsrs.tage_in_text(800)


def test_stabilitaet_bleibt_in_grenzen():
    z = Zustand(stabilitaet=36000.0, schwierigkeit=1.0)
    assert bewerten(z, LEICHT, 36000.0).stabilitaet <= fsrs.S_MAX
