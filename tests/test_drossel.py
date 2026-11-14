"""Sperre gegen Durchprobieren.

Nötig geworden, weil vor der MCP-Schnittstelle kein Cloudflare Access mehr
stehen kann: der Konnektor in claude.ai lässt nur eine feste Liste von
Headernamen zu, und die Access-Kopfzeilen sind nicht dabei. Damit trägt das
Zugangsmerkmal die Last allein.
"""

import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "backend"))

import pytest

import drossel


@pytest.fixture(autouse=True)
def leer():
    drossel.zuruecksetzen()
    yield
    drossel.zuruecksetzen()


def test_einzelne_fehlversuche_sperren_nicht():
    for _ in range(drossel.GRENZE - 1):
        assert drossel.fehlversuch("1.2.3.4") == 0.0
    assert drossel.gesperrt("1.2.3.4") == 0.0


def test_ab_der_grenze_wird_gesperrt():
    for _ in range(drossel.GRENZE):
        dauer = drossel.fehlversuch("1.2.3.4")
    assert dauer > 0
    assert drossel.gesperrt("1.2.3.4") > 0


def test_die_sperre_trifft_nur_den_verursacher():
    for _ in range(drossel.GRENZE):
        drossel.fehlversuch("1.2.3.4")
    assert drossel.gesperrt("1.2.3.4") > 0
    assert drossel.gesperrt("5.6.7.8") == 0.0


def test_gelungener_zugang_setzt_den_zaehler_zurueck():
    for _ in range(drossel.GRENZE - 1):
        drossel.fehlversuch("1.2.3.4")
    drossel.geschafft("1.2.3.4")
    # Jetzt wieder von vorn: ein einzelner Fehlversuch sperrt nicht
    assert drossel.fehlversuch("1.2.3.4") == 0.0


def test_die_ablage_waechst_nicht_unbegrenzt():
    for i in range(drossel.HOECHSTENS + 500):
        drossel.fehlversuch(f"10.0.{i // 256}.{i % 256}")
    assert len(drossel._versuche) <= drossel.HOECHSTENS


def test_kennung_kommt_aus_der_cloudflare_kopfzeile():
    """Hinter dem Tunnel wäre request.client immer derselbe."""
    class Anfrage:
        headers = {"cf-connecting-ip": "203.0.113.9"}
        client = type("C", (), {"host": "172.21.0.1"})()
    assert drossel.kennung_aus_anfrage(Anfrage()) == "203.0.113.9"


def test_kennung_faellt_auf_die_verbindung_zurueck():
    class Anfrage:
        headers = {}
        client = type("C", (), {"host": "192.0.2.5"})()
    assert drossel.kennung_aus_anfrage(Anfrage()) == "192.0.2.5"
