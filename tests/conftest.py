import os
import pathlib
import sys
import tempfile

import pytest

WURZEL = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WURZEL / "backend"))


@pytest.fixture(autouse=True, scope="session")
def _ohne_beispieldaten():
    """Die Testläufe sehen die Umgebung nicht.

    `BEISPIELDATEN=1` legt beim Start einen Beispielbestand an. In einem
    Codespace steht die Variable dauerhaft da — und dann entsteht sie in
    JEDER Testdatenbank: das Demoprofil bekommt die 1, und vierzig Tests,
    die mit `benutzer_id=1` ihr eigenes Profil meinen, prüfen plötzlich
    fremde Rechte. Gemessen: 40 Fehlschläge mit der Variablen, 861 grün
    ohne sie.

    Der Fehler ist nicht die Variable, sondern die Annahme, die Umgebung
    sei leer. Ein Testlauf muss von sich aus gelten, auf jedem Rechner.

    Wer die Erstbefüllung selbst prüft, setzt sie ausdrücklich
    (`monkeypatch.setenv`) — das sticht diese Entfernung hier aus.
    """
    vorher = os.environ.pop("BEISPIELDATEN", None)
    yield
    if vorher is not None:
        os.environ["BEISPIELDATEN"] = vorher


@pytest.fixture()
def db(tmp_path, monkeypatch):
    """Frische Datenbank je Test."""
    import datenbank as dbm
    monkeypatch.setattr(dbm, "PFAD", tmp_path / "test.db")
    verbindung = dbm.verbindung()
    dbm.einrichten(verbindung)
    yield verbindung
    verbindung.close()


@pytest.fixture()
def klient(tmp_path, monkeypatch):
    """Testklient mit eigener Datenbank."""
    import datenbank as dbm
    monkeypatch.setattr(dbm, "PFAD", tmp_path / "api.db")
    from fastapi.testclient import TestClient
    import app as anwendung
    with TestClient(anwendung.app) as k:
        yield k
