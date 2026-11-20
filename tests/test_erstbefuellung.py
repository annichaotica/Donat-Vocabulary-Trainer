"""Beispielbestand beim ersten Start — nur auf Wunsch und nur einmal.

Wer das Programm zum Ansehen startet, steht sonst vor einer leeren
Datenbank. Wer es betreibt, will auf keinen Fall, dass ihm etwas
hineingeschüttet wird — auch dann nicht, wenn die Umgebungsvariable
versehentlich stehenbleibt.
"""

import pytest


@pytest.fixture
def leer(tmp_path, monkeypatch):
    """Eine frische Datenbank, wie beim allerersten Start."""
    import datenbank as dbm
    monkeypatch.setattr(dbm, "PFAD", tmp_path / "neu.db")
    # Über dbm.verbindung, nicht über sqlite3.connect: der Import setzt
    # eigene Transaktionen ab, und das geht nur mit isolation_level=None.
    db = dbm.verbindung()
    dbm.einrichten(db)
    yield db
    db.close()


def _befuellen(db, monkeypatch, **umgebung):
    import erstbefuellung
    for k, v in umgebung.items():
        monkeypatch.setenv(k, v)
    return erstbefuellung.vielleicht_befuellen(db)


def test_ohne_schalter_passiert_nichts(leer, monkeypatch):
    monkeypatch.delenv("BEISPIELDATEN", raising=False)
    import erstbefuellung
    assert erstbefuellung.vielleicht_befuellen(leer) is None
    assert leer.execute("SELECT COUNT(*) FROM benutzer").fetchone()[0] == 0


def test_mit_schalter_entsteht_ein_vollstaendiger_bestand(leer, monkeypatch):
    bericht = _befuellen(leer, monkeypatch, BEISPIELDATEN="1")
    assert bericht is not None

    def zahl(sql):
        return leer.execute(sql).fetchone()[0]

    assert zahl("SELECT COUNT(*) FROM benutzer") == 1
    assert zahl("SELECT COUNT(*) FROM sammlung") == 1
    # Die Stärken sollen zu sehen sein, nicht nur ein paar Wörter:
    assert zahl("SELECT COUNT(*) FROM lexem") >= 20
    assert zahl("SELECT COUNT(*) FROM lektion") >= 5
    # Vollständige Paradigmen — daran hängen Formaufgaben und Reihen.
    assert zahl("SELECT COUNT(*) FROM form") > zahl("SELECT COUNT(*) FROM lexem")
    # Ein Lesetext mit Deckung.
    assert zahl("SELECT COUNT(*) FROM text") >= 1
    # Ungeprüfte Einträge, als »von der KI« — sonst ist die Freigabe leer.
    assert zahl("SELECT COUNT(*) FROM form WHERE geprueft = 0 "
                "AND quelle = 'ki'") >= 1
    # Ein Lernziel MIT Termin, sonst bleibt der Terminstreifen leer.
    assert zahl("SELECT COUNT(*) FROM lernziel WHERE termin IS NOT NULL") == 1
    # Und abfragbar ist es auch schon.
    assert zahl("SELECT COUNT(*) FROM aufgabe WHERE aktiv = 1") > 0


@pytest.mark.parametrize("wert", ["1", "true", "ja", "YES", "on"])
def test_der_schalter_versteht_die_ueblichen_schreibweisen(leer, monkeypatch, wert):
    assert _befuellen(leer, monkeypatch, BEISPIELDATEN=wert) is not None


@pytest.mark.parametrize("wert", ["", "0", "nein", "false"])
def test_alles_andere_heisst_nein(leer, monkeypatch, wert):
    assert _befuellen(leer, monkeypatch, BEISPIELDATEN=wert) is None


def test_ein_bestehender_bestand_wird_nie_angefasst(leer, monkeypatch):
    """Die wichtigste Zusage dieses Moduls.

    Wer die Variable im Container stehen lässt und morgen neu startet,
    darf nicht plötzlich einen Übungskurs zwischen seinen Sammlungen
    finden — und schon gar nicht ein zweites Mal.
    """
    leer.execute("INSERT INTO benutzer (name) VALUES ('Jemand')")
    leer.commit()
    assert _befuellen(leer, monkeypatch, BEISPIELDATEN="1") is None
    assert leer.execute("SELECT COUNT(*) FROM sammlung").fetchone()[0] == 0
    assert leer.execute("SELECT COUNT(*) FROM benutzer").fetchone()[0] == 1


def test_zweimal_befuellen_legt_nichts_doppelt_an(leer, monkeypatch):
    _befuellen(leer, monkeypatch, BEISPIELDATEN="1")
    vorher = leer.execute("SELECT COUNT(*) FROM lexem").fetchone()[0]
    assert _befuellen(leer, monkeypatch, BEISPIELDATEN="1") is None
    assert leer.execute("SELECT COUNT(*) FROM lexem").fetchone()[0] == vorher


def test_der_profilname_laesst_sich_setzen(leer, monkeypatch):
    bericht = _befuellen(leer, monkeypatch, BEISPIELDATEN="1",
                         BEISPIELDATEN_PROFIL="Gast")
    assert bericht["profil"] == "Gast"
    assert leer.execute("SELECT name FROM benutzer").fetchone()[0] == "Gast"
