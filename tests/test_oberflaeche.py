"""Statische Prüfungen der Oberfläche.

Ohne Bauschritt gibt es keinen Übersetzer, der einen Tippfehler im
Funktionsnamen bemerkt — `api.aufdecken(...)` aufzurufen, ohne es in api.js
einzutragen, fällt sonst erst beim Benutzen auf. Diese Tests ersetzen das,
soweit es sich mit einfachen Mitteln machen lässt.
"""

import json
import pathlib
import re
import subprocess

WURZEL = pathlib.Path(__file__).resolve().parents[1]
JS = sorted((WURZEL / "frontend" / "js").glob("*.js"))
CSS = WURZEL / "frontend" / "css"
HTML = WURZEL / "frontend" / "index.html"


def test_es_gibt_javascript_dateien():
    assert len(JS) >= 8


def test_jede_benutzte_schnittstellenfunktion_ist_auch_eingetragen():
    """Der Fall, der wirklich auftrat: api.aufdecken wurde an zwei Stellen
    gerufen und war nie eingetragen. »Weiß ich nicht« war damit kaputt."""
    api_text = (WURZEL / "frontend" / "js" / "api.js").read_text()
    # Die Schlüssel des exportierten Objekts
    eingetragen = set(re.findall(r"^\s{2}(\w+):", api_text, re.MULTILINE))
    assert "pruefen" in eingetragen, "Erkennung der Einträge misslungen"

    benutzt = set()
    for datei in JS:
        if datei.name == "api.js":
            continue
        benutzt |= set(re.findall(r"\bapi\.(\w+)\s*\(", datei.read_text()))
    fehlend = benutzt - eingetragen
    assert not fehlend, f"In api.js fehlen: {sorted(fehlend)}"


def test_keine_verwaisten_schnittstellenfunktionen():
    """Umgekehrt: was nie gerufen wird, ist vermutlich vergessener Ballast."""
    api_text = (WURZEL / "frontend" / "js" / "api.js").read_text()
    eingetragen = set(re.findall(r"^\s{2}(\w+):", api_text, re.MULTILINE))
    benutzt = set()
    for datei in JS:
        if datei.name == "api.js":
            continue
        benutzt |= set(re.findall(r"\bapi\.(\w+)\s*\(", datei.read_text()))
    unbenutzt = eingetragen - benutzt
    # Ein paar dürfen vorrätig sein, aber nicht die Hälfte.
    assert len(unbenutzt) < len(eingetragen) / 2, sorted(unbenutzt)


def test_alle_module_sind_syntaktisch_gueltig():
    """Braucht node; wo es fehlt, wird der Test übersprungen."""
    import shutil
    import pytest
    if not shutil.which("node"):
        pytest.skip("node nicht vorhanden")
    for datei in JS:
        ergebnis = subprocess.run(["node", "--check", str(datei)],
                                  capture_output=True, text=True)
        assert ergebnis.returncode == 0, f"{datei.name}: {ergebnis.stderr}"


def test_jede_vom_javascript_gesuchte_kennung_steht_im_html():
    html = HTML.read_text()
    vorhanden = set(re.findall(r'id="([^"]+)"', html))
    gesucht = set()
    for datei in JS:
        gesucht |= set(re.findall(r"getElementById\(['\"]([^'\"]+)['\"]\)",
                                  datei.read_text()))
    fehlend = gesucht - vorhanden
    assert not fehlend, f"Im HTML fehlen die Kennungen: {sorted(fehlend)}"


def test_die_variablen_des_legastheniemodus_wirken_im_stil():
    """darstellungSetzen in zustand.js schreibt diese Variablen. Wenn der
    Stil sie nicht benutzt, ändert der Modus nichts."""
    zustand = (WURZEL / "frontend" / "js" / "zustand.js").read_text()
    geschrieben = set(re.findall(r"setProperty\('(--[\w-]+)'", zustand))
    assert geschrieben, "keine Variablen gefunden"
    stil = "".join((CSS / name).read_text() for name in ("stil.css", "zusatz.css"))
    for name in geschrieben:
        # einmal gesetzt (:root) und mindestens einmal benutzt
        assert stil.count(f"var({name}") >= 1, f"{name} wird im Stil nicht benutzt"


def test_themenschalter_sind_vollstaendig():
    stil = (CSS / "stil.css").read_text()
    for grund in ("creme", "hell", "dunkel"):
        assert f'data-grund="{grund}"' in stil, grund
    assert "prefers-color-scheme: dark" in stil
    assert "prefers-reduced-motion" in stil


def test_keine_waagerechte_ueberlaufquelle_im_grundgeruest():
    """Der Seitenkörper darf nie seitlich scrollen."""
    stil = (CSS / "stil.css").read_text()
    assert "overflow-x" in stil, "keine Absicherung gegen waagerechten Überlauf"


def test_kein_aufruf_einer_unbekannten_stammdatenfunktion():
    stammdaten = (WURZEL / "frontend" / "js" / "stammdaten.js").read_text()
    eingetragen = set(re.findall(r"^\s{2}(\w+):", stammdaten, re.MULTILINE))
    eingetragen |= set(re.findall(r"^\s{2}async (\w+)\(", stammdaten, re.MULTILINE))
    benutzt = set()
    for datei in JS:
        if datei.name == "stammdaten.js":
            continue
        benutzt |= set(re.findall(r"\bstammdaten\.(\w+)\s*\(", datei.read_text()))
    assert not (benutzt - eingetragen), sorted(benutzt - eingetragen)


def test_oberflaechendateien_werden_gegengeprueft():
    """Ohne das hält der Browser die ES-Module fest und zeigt nach einer
    Aktualisierung tagelang die alte Fassung — ohne jeden Hinweis."""
    import pathlib, sys
    sys.path.insert(0, str(WURZEL / "backend"))
    import tempfile
    import datenbank as dbm
    dbm.PFAD = pathlib.Path(tempfile.mkdtemp()) / "t.db"
    from fastapi.testclient import TestClient
    import app as anwendung
    with TestClient(anwendung.app) as k:
        for pfad in ("/", "/js/app.js", "/css/stil.css"):
            antwort = k.get(pfad)
            assert antwort.status_code == 200, pfad
            assert antwort.headers.get("cache-control") == "no-cache", pfad
        # Die Schnittstelle ist davon nicht betroffen
        assert k.get("/api/zustand").headers.get("cache-control") is None
