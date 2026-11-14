import pathlib
import sys
import tempfile

import pytest

WURZEL = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WURZEL / "backend"))


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
