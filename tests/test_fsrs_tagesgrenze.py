"""Zwei Stellen, an denen FSRS und der Terminplan aneinander vorbeirechnen.

**Die Tagesgrenze.** `faellig` ist ein KALENDERDATUM. FSRS entschied
aber nach exakten 24 Stunden, ob eine Antwort »am selben Tag« kam. Wer
abends um 20 Uhr lernt und am nächsten Morgen um 9 weitermacht, liegt
13 Stunden später — für den Terminplan ein neuer Tag, für FSRS derselbe.
Gemessen: 23,9 h ergaben Stabilität 1,41, 24,1 h ergaben 4,03. Zwölf
Minuten entschieden über Faktor drei. Bei reifen Karten wirkt es
umgekehrt: die Selber-Tag-Formel bläht sie auf (23,5 h → 14,08 gegen
24,5 h → 12,58).

**Die Vorschau.** Jeder Bewertungsknopf zeigt an, welchen Termin er
ergäbe — das ist eines der erklärten Versprechen des Moduls. Die Rechnung
dahinter streute den Termin aber um ±5 %, die Vorschau nicht. Der Knopf
sagte »in 3,0 Monaten«, gesetzt wurden 2,9.
"""

import datetime as dt
import sys

sys.path.insert(0, "backend")

import fsrs


# ------------------------------------------------------- Tagesgrenze

def test_am_naechsten_morgen_ist_ein_neuer_tag():
    """13 Stunden später, aber ein Kalendertag weiter: das zählt."""
    z = fsrs.Zustand(1.0, 5.0)
    kurz = fsrs.bewerten(z, 3, 13 / 24, 0.9, selber_tag=False)
    lang = fsrs.bewerten(z, 3, 25 / 24, 0.9)
    # Nicht gleich — 13 Stunden sind weniger als 25 —, aber in derselben
    # Größenordnung, nicht um Faktor drei daneben.
    assert kurz.stabilitaet > 2.0, kurz.stabilitaet
    assert kurz.stabilitaet < lang.stabilitaet


def test_zweimal_am_selben_tag_bleibt_selber_tag():
    """Wer eine Karte in derselben Sitzung noch einmal sieht, soll dafür
    keine Stabilität geschenkt bekommen."""
    z = fsrs.Zustand(1.0, 5.0)
    e = fsrs.bewerten(z, 3, 2 / 24, 0.9, selber_tag=True)
    assert e.stabilitaet < 2.0, e.stabilitaet


def test_ohne_angabe_bleibt_es_bei_den_24_stunden():
    """`selber_tag` ist freigestellt; ohne die Angabe rechnet FSRS wie
    bisher. Sonst bräuchte jeder Aufrufer eine Uhrzeit."""
    z = fsrs.Zustand(1.0, 5.0)
    a = fsrs.bewerten(z, 3, 0.5, 0.9)
    b = fsrs.bewerten(z, 3, 0.5, 0.9, selber_tag=True)
    assert a.stabilitaet == b.stabilitaet


def test_die_grenze_richtet_sich_nach_dem_datum_nicht_nach_der_uhr():
    """Der Weg durch lernen.bewerten: gestern Abend beantwortet, heute
    früh wieder — das muss als neuer Tag gelten."""
    import lernen
    gestern_abend = (dt.datetime.combine(lernen.heute() - dt.timedelta(days=1),
                                         dt.time(20, 0)))
    heute_frueh = dt.datetime.combine(lernen.heute(), dt.time(9, 0))
    assert lernen._selber_tag(gestern_abend.isoformat(timespec="seconds"),
                              heute_frueh) is False
    heute_abends = dt.datetime.combine(lernen.heute(), dt.time(22, 0))
    assert lernen._selber_tag(heute_frueh.isoformat(timespec="seconds"),
                              heute_abends) is True
    assert lernen._selber_tag(None, heute_abends) is False


# ---------------------------------------------------------- Vorschau

def test_die_vorschau_nennt_den_termin_der_wirklich_gesetzt_wird():
    """Sonst ist das Versprechen des Moduls gebrochen: »jeder
    Bewertungsknopf zeigt vorher an, welchen Termin er ergeben würde«."""
    z = fsrs.Zustand(10.0, 5.0)
    saat = 4711
    v = fsrs.vorschau(z, 12.0, 0.9, saat=saat)
    for note in (1, 2, 3, 4):
        gesetzt = fsrs.bewerten(z, note, 12.0, 0.9, saat=saat).intervall_tage
        assert abs(v[note] - gesetzt) < 1e-9, (note, v[note], gesetzt)


def test_ohne_saat_streut_auch_die_vorschau_nicht():
    """Gleichstand: ohne Streuung sind beide Seiten ungestreut."""
    z = fsrs.Zustand(10.0, 5.0)
    v = fsrs.vorschau(z, 12.0, 0.9)
    for note in (1, 2, 3, 4):
        gesetzt = fsrs.bewerten(z, note, 12.0, 0.9).intervall_tage
        assert abs(v[note] - gesetzt) < 1e-9
