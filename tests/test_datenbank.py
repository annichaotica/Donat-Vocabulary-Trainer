

def test_keine_tabelle_steht_zweimal_in_nachruesten():
    """Ein doppelter Schlüssel im Wörterbuch ist kein Fehler — der
    spätere gewinnt, und der frühere verschwindet lautlos.

    Genau das ist passiert: »lexem« stand zweimal darin, die neu
    eingetragene Spalte `abfrage` fiel weg, und auf einer bestehenden
    Datenbank meldete der Server »no such column«. Auf einer frischen
    Testdatenbank war nichts zu sehen, weil die Spalte dort aus
    schema.sql kommt.
    """
    import ast
    import pathlib
    quelle = (pathlib.Path(__file__).resolve().parents[1]
              / "backend" / "datenbank.py").read_text()
    baum = ast.parse(quelle)
    for knoten in ast.walk(baum):
        if (isinstance(knoten, ast.AnnAssign)
                and getattr(knoten.target, "id", "") == "NACHRUESTEN"):
            namen = [k.value for k in knoten.value.keys]
            assert len(namen) == len(set(namen)), \
                f"doppelt in NACHRUESTEN: {sorted(n for n in namen if namen.count(n) > 1)}"
            return
    raise AssertionError("NACHRUESTEN nicht gefunden")


def test_abfrage_wird_nachgeruestet(tmp_path, monkeypatch):
    """Eine bestehende Datenbank ohne die Spalte bekommt sie beim Start.

    Nachgestellt, indem die Spalte aus einer fertigen Datenbank wieder
    entfernt wird — denn genau so sah ihr Bestand aus: das
    Schemaskript legt sie bei einer NEUEN Datenbank an, eine
    bestehende ändert es nicht.
    """
    import datenbank as dbm
    monkeypatch.setattr(dbm, "PFAD", tmp_path / "bestand.db")
    v = dbm.verbindung()
    try:
        dbm.einrichten(v)
        assert "abfrage" in dbm.spalten(v, "lexem")
        v.execute("ALTER TABLE lexem DROP COLUMN abfrage")
        v.commit()
        assert "abfrage" not in dbm.spalten(v, "lexem")

        dbm.wandern(v, dbm.SCHEMA_VERSION)
        assert "abfrage" in dbm.spalten(v, "lexem"), \
            "die Nachrüstung hat die Spalte nicht angelegt"
    finally:
        v.close()
