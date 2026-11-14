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


def test_wanderung_aus_einer_alten_datenbank():
    """Der Fall, der wirklich auftrat: alle Tests starten mit einer frischen
    Datenbank, deshalb fiel nie auf, dass ein Index im Schemaskript auf eine
    Spalte zeigte, die erst die Wanderung anlegt. In einer bestehenden
    Datenbank ist CREATE TABLE IF NOT EXISTS wirkungslos — der Index lief
    ins Leere und der Dienst startete nicht mehr.
    """
    import sqlite3
    import sys
    import tempfile
    sys.path.insert(0, str(WURZEL / "backend"))
    import datenbank as dbm

    pfad = pathlib.Path(tempfile.mkdtemp()) / "alt.db"
    alt = sqlite3.connect(pfad)
    # Eine Datenbank, wie sie vor den Erweiterungen aussah
    alt.executescript("""
        CREATE TABLE schema_stand (version INTEGER NOT NULL);
        INSERT INTO schema_stand VALUES (1);
        CREATE TABLE sprache (code TEXT PRIMARY KEY, name TEXT NOT NULL,
            schrift TEXT NOT NULL DEFAULT 'latein', stimme TEXT,
            profil TEXT NOT NULL DEFAULT '{}');
        CREATE TABLE benutzer (id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE,
            farbe TEXT NOT NULL DEFAULT '#6b7fd7',
            einstellungen TEXT NOT NULL DEFAULT '{}',
            angelegt TEXT NOT NULL DEFAULT (datetime('now')));
        CREATE TABLE sammlung (id INTEGER PRIMARY KEY, besitzer_id INTEGER NOT NULL,
            name TEXT NOT NULL, sprache TEXT NOT NULL,
            grundsprache TEXT NOT NULL DEFAULT 'de', beschreibung TEXT,
            angelegt TEXT NOT NULL DEFAULT (datetime('now')));
        CREATE TABLE lektion (id INTEGER PRIMARY KEY, sammlung_id INTEGER NOT NULL,
            name TEXT NOT NULL, reihenfolge INTEGER NOT NULL DEFAULT 0);
        CREATE TABLE lexem (id INTEGER PRIMARY KEY, sammlung_id INTEGER NOT NULL,
            lektion_id INTEGER, lemma TEXT NOT NULL, wortart TEXT NOT NULL,
            merkmale TEXT NOT NULL DEFAULT '{}', notiz TEXT,
            angelegt TEXT NOT NULL DEFAULT (datetime('now')),
            geaendert TEXT NOT NULL DEFAULT (datetime('now')));
        -- Die Texttabelle gab es schon, aber ohne die Übungsspalten. Genau
        -- so steht sie auf dem Familienserver — CREATE TABLE IF NOT EXISTS
        -- rührt sie nicht an, die Spalten müssen von der Wanderung kommen.
        CREATE TABLE text (id INTEGER PRIMARY KEY, sammlung_id INTEGER NOT NULL,
            lektion_id INTEGER, titel TEXT NOT NULL, sprache TEXT NOT NULL,
            inhalt TEXT NOT NULL, uebersetzung TEXT, niveau TEXT,
            quelle TEXT NOT NULL DEFAULT 'manuell', notiz TEXT,
            angelegt TEXT NOT NULL DEFAULT (datetime('now')));
        CREATE TABLE textabschnitt (id INTEGER PRIMARY KEY,
            text_id INTEGER NOT NULL, reihenfolge INTEGER NOT NULL DEFAULT 0,
            original TEXT NOT NULL, referenz TEXT, notiz TEXT);
        INSERT INTO text (sammlung_id, titel, sprache, inhalt)
            VALUES (1, 'Alter Text', 'el', 'Καλημέρα.');
        INSERT INTO benutzer (name) VALUES ('Alt');
        INSERT INTO sammlung (besitzer_id, name, sprache) VALUES (1, 'Alt', 'el');
        INSERT INTO lektion (sammlung_id, name) VALUES (1, 'Erste');
        INSERT INTO lexem (sammlung_id, lemma, wortart) VALUES (1, 'παλιό', 'adjektiv');
    """)
    alt.commit()
    alt.close()

    db = dbm.verbindung(pfad)
    dbm.einrichten(db)                        # darf nicht werfen
    assert dbm.wert(db, "SELECT version FROM schema_stand") == dbm.SCHEMA_VERSION
    # Die Daten sind noch da
    assert dbm.wert(db, "SELECT lemma FROM lexem") == "παλιό"
    assert dbm.wert(db, "SELECT name FROM benutzer") == "Alt"
    # Und die nachgerüsteten Spalten samt Index sind vorhanden
    assert {"nr", "beschreibung"} <= dbm.spalten(db, "lektion")
    assert {"reihenfolge", "kennung"} <= dbm.spalten(db, "lexem")
    indizes = {z[0] for z in db.execute(
        "SELECT name FROM sqlite_master WHERE type='index'")}
    assert "idx_lektion_nr" in indizes
    assert "idx_lexem_kennung" in indizes
    # Dasselbe für die Übungen: Spalten UND der Index auf einer von ihnen.
    assert {"typ", "richtungen", "geprueft", "kennung",
            "verweis_url"} <= dbm.spalten(db, "text")
    assert {"varianten", "referenz_varianten"} <= dbm.spalten(db, "textabschnitt")
    assert "idx_text_kennung" in indizes
    assert dbm.wert(db, "SELECT titel FROM text") == "Alter Text"
    assert dbm.wert(db, "SELECT typ FROM text") == "text"
    # Zweimal einrichten muss ebenfalls gehen
    dbm.einrichten(db)
    db.close()


def test_jede_ansicht_ist_im_wegweiser_eingetragen():
    """Eine Ansichtsdatei, die niemand aufruft, ist toter Code — und eine
    Route, die auf eine fehlende Funktion zeigt, ist eine leere Seite.
    Beides fällt ohne Bauschritt erst beim Benutzen auf.
    """
    app = (WURZEL / "frontend" / "js" / "app.js").read_text()
    for datei in JS:
        if not datei.name.startswith("ansicht_"):
            continue
        assert f"'./{datei.name}'" in app, f"{datei.name} wird nirgends eingebunden"
        # Jede eingebundene Ansicht muss auch von einer Route gerufen werden.
        kuerzel = re.search(
            rf"import \* as (\w+) from '\./{datei.name}'", app)
        assert kuerzel, f"{datei.name} ist nicht als Modul eingebunden"
        assert f"{kuerzel.group(1)}." in app.split("import *")[-1], \
            f"{datei.name} wird eingebunden, aber nie aufgerufen"


def test_der_wegweiser_gibt_jeder_ansicht_einen_frischen_bereich():
    """Der Fall, der wirklich auftrat: beim schnellen Wechseln schrieb die
    überholte Ansicht nach ihren await-Stellen weiter in denselben Bereich,
    und es standen zwei Seiten untereinander. Über eine schnelle Leitung
    war das kaum zu sehen, über eine langsame regelmäßig.
    """
    app = (WURZEL / "frontend" / "js" / "app.js").read_text()
    assert "function frischerInhalt()" in app
    assert "const inhalt = frischerInhalt();" in app
    # Kein Bereich mehr auf Modulebene — sonst teilten sich zwei Durchläufe
    # wieder denselben.
    assert "const inhalt = document.getElementById('inhalt');" not in app


def test_der_import_laeuft_immer_zuerst_als_probelauf():
    """Ein Import, der ungefragt tausend Zeilen in den Bestand kippt, ist
    schlimmer als keiner."""
    quelle = (WURZEL / "frontend" / "js" / "ansicht_import.js").read_text()
    assert "nur_pruefen: nurPruefen" in quelle
    assert "await lauf(true)" in quelle, "Der Probelauf muss von selbst anlaufen"
    # Große Dateien gestückelt: ein einziger Aufruf mit zehntausend Formen
    # läuft in die Zeitgrenze.
    assert "PAECKCHEN" in quelle


def test_die_tastaturbelegung_ist_auffindbar():
    """Eine Nachschlagetafel nützt nur, wenn man sie findet, ohne die
    Adresse zu kennen."""
    quelle = (WURZEL / "frontend" / "js").glob("*.js")
    verweise = [d.name for d in quelle if "#/tastatur" in d.read_text()]
    assert "ansicht_einstellungen.js" in verweise
    assert "tastatur.js" in verweise


def test_die_belegung_lernt_nur_zeichen_der_richtigen_schrift():
    """Ohne diese Prüfung schriebe ein Tippversuch mit deutscher Tastatur
    lauter lateinische Buchstaben in die Abbildung — und die wäre hinterher
    falsch statt hilfreich."""
    quelle = (WURZEL / "frontend" / "js" / "tastatur.js").read_text()
    assert "schrift:" in quelle
    assert "b.schrift.test(zeichen)" in quelle
    # Und die deutsche Beschriftung, nicht die amerikanische: auf einer
    # deutschen Tastatur sind Y und Z vertauscht.
    assert "['KeyY', 'Z']" in quelle and "['KeyZ', 'Y']" in quelle


def test_jede_javascript_datei_ist_syntaktisch_heil():
    """Ohne Bauschritt bemerkt niemand eine kaputte Klammer, bis die Seite
    weiß bleibt. `node --check` ist in zwei Sekunden durch; fehlt node,
    wird der Test übersprungen statt grün zu lügen."""
    import shutil
    node = shutil.which("node")
    if not node:
        import pytest
        pytest.skip("node ist nicht da")
    for datei in JS:
        ergebnis = subprocess.run([node, "--check", str(datei)],
                                  capture_output=True, text=True)
        assert ergebnis.returncode == 0, f"{datei.name}: {ergebnis.stderr}"


def test_die_merktafel_stiehlt_dem_antwortfeld_nicht_den_fokus():
    """Der Fall, auf den es hier ankommt: ein Klick auf die Tafel mitten in
    der Eingabe darf die Einfügemarke nicht verlieren — sonst schreibt man
    nach dem Nachsehen an der falschen Stelle weiter."""
    quelle = (WURZEL / "frontend" / "js" / "tastatur.js").read_text()
    # Sowohl der Aufklappknopf als auch die Tasten selbst.
    assert quelle.count("onmousedown: (e) => e.preventDefault()") >= 3
    # Und sie merkt sich, ob sie offen war — sonst klappt man sie bei
    # jeder Vokabel neu auf.
    assert "merktafelMerken" in quelle


def test_die_freigabe_laesst_sich_ohne_maus_durchgehen():
    """Beim Prüfen von dreißig Wörtern ist Scrollen der falsche Weg: nach
    dem Freigeben muss die nächste Karte an dieselbe Stelle nachrücken,
    und die Tastatur muss reichen."""
    quelle = (WURZEL / "frontend" / "js" / "ansicht_freigabe.js").read_text()
    assert "function hervorheben" in quelle
    assert "scrollIntoView" in quelle
    assert "'Enter'" in quelle and "ArrowDown" in quelle
    # Der Behandler muss sich abmelden, wenn die Seite gewechselt wird —
    # sonst reagiert er noch in der Abfrage auf Enter.
    assert "el.isConnected" in quelle
    assert "removeEventListener('keydown', aufTaste)" in quelle


def test_die_wortdurchsicht_hat_ein_weiter():
    """Der eigentliche Weg beim Prüfen gepflegter Wörter: Wort ansehen,
    bestätigen, nächstes. Ohne »weiter« heißt das jedes Mal zurück zur
    Liste und scrollen."""
    quelle = (WURZEL / "frontend" / "js" / "ansicht_wortschatz.js").read_text()
    assert "async function warteschlange" in quelle
    assert "nur_ungepruefte: true" in quelle
    assert "bestaetigenUndWeiter" in quelle
    assert "ArrowRight" in quelle and "ArrowLeft" in quelle
    # Die Ansicht zeichnet sich auch ohne Seitenwechsel neu — dann darf
    # kein zweiter Behandler hängenbleiben, sonst löst Enter doppelt aus.
    assert "let tastenbehandler = null;" in quelle
    assert "removeEventListener('keydown', tastenbehandler)" in quelle


def test_die_anleitung_nennt_keine_feste_adresse():
    """Das Repo ist öffentlich. Die Adresse der Schnittstelle gehört zur
    Anlage, kommt aus der Umgebung und darf nirgends im Quelltext stehen —
    auch nicht in einem Test, der sie verbieten soll."""
    quelle = (WURZEL / "frontend" / "js" / "ansicht_hilfe.js").read_text()
    assert "stand.mcp_url" in quelle
    for datei in list(JS) + [HTML]:
        text = datei.read_text()
        fremde = [
            u for u in re.findall(r"https?://[\w.:-]+", text)
            if "localhost" not in u and "127.0.0.1" not in u
            and "github.com" not in u and "gnu.org" not in u
        ]
        assert not fremde, f"{datei.name}: {fremde}"


def test_die_anleitung_ist_von_ueberall_erreichbar():
    """Eine Anleitung, die man suchen muss, liest niemand."""
    assert 'href="#/hilfe"' in HTML.read_text()
    app = (WURZEL / "frontend" / "js" / "app.js").read_text()
    assert "case 'hilfe':" in app


def test_meldung_versteht_auch_die_art_statt_der_dauer():
    """`meldung(text, 'fehler')` ergab setTimeout(fn, NaN) — geklemmt auf
    0, also war die Meldung ausgerechnet im Fehlerfall unsichtbar.

    Vier Aufrufstellen schrieben es so, in der Annahme, dort stünde die
    Art. Statt sie zu berichtigen und auf die fünfte zu hoffen, versteht
    die Funktion beides.
    """
    quelle = (WURZEL / "frontend" / "js" / "hilfen.js").read_text()
    assert "MELDUNG_FEHLER" in quelle
    assert "Number.isFinite" in quelle, "die Dauer muss geprüft werden"
