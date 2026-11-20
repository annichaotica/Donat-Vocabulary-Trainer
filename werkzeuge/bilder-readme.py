#!/usr/bin/env python3
"""Nimmt die fünf Bildschirmfotos für die README auf.

    .venv/bin/python werkzeuge/bilder-readme.py

Getrennt von `bilder-aufnehmen.py`, obwohl das Gerüst dasselbe ist:
jenes fotografiert SEITEN, dieses fotografiert ZUSTÄNDE. Die fünf
Bilder sollen je eine Stärke zeigen, und vier davon entstehen erst,
nachdem etwas eingestellt oder bedient wurde — eine falsch getippte
Antwort, eine eingeschaltete Formgruppe, der Legastheniemodus, eine
eingeblendete Glosse.

Zwei Dinge macht dieses Skript deshalb mehr:

  einstellen   Vor jeder Aufnahme wird der Bestand über die
               Schnittstelle in den passenden Zustand gebracht. Nicht
               in der Datenbank herumgeschrieben: was die Oberfläche
               zeigt, soll durch dieselbe Tür gegangen sein wie alles
               andere.

  bedienen     Die Weiche führt nach dem Laden noch Schritte aus —
               tippen, klicken, warten. Chrome nimmt mit
               `--virtual-time-budget` erst danach auf.

EINDEUTIG MUSS ES SEIN. Welche Aufgabe die Abfrage als nächste
vorlegt, entscheidet der Planer. Für ein Bild ist das unbrauchbar:
der falsch getippte Buchstabe muss zu dem Wort passen, das zu sehen
ist. Darum wird vor jeder Abfrage-Aufnahme alles bis auf EIN Wort
stillgelegt — dann steht fest, was kommt.

Der Bestand ist der englische Übungskurs aus `beispielkurs.py`, in
einer eigenen Datenbank, die am Ende weggeworfen wird. Aus dem
Familienbestand darf auf diesen Bildern nichts zu sehen sein.
"""

from __future__ import annotations

import http.client
import json
import os
import pathlib
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.parse

WURZEL = pathlib.Path(__file__).resolve().parents[1]
ZIEL = WURZEL / "docs" / "screenshots"
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
BREITE = 1100


# Die Weiche setzt den Sitzungszustand und führt dann die Schritte aus.
#
# Sie muss vom SELBEN Ursprung kommen wie die Anwendung, sonst gehört
# ihr der localStorage nicht — darum liegt sie kurz in der Oberfläche
# und wird hinterher entfernt.
WEICHE = """<!doctype html><meta charset="utf-8"><title>Aufnahme</title>
<script>
// Setzt den Sitzungszustand und leitet weiter. Muss vom SELBEN
// Ursprung kommen wie die Anwendung, sonst gehört ihr der
// localStorage nicht.
const f = new URLSearchParams(location.search);
localStorage.setItem('vokabeltrainer.zustand', JSON.stringify({
  benutzerId: Number(f.get('p')), sammlungId: Number(f.get('s')),
  lektionId: null }));
// Die Rundgänge als gesehen markieren: ihre Willkommenskarte gehört
// nicht auf jedes Bild.
localStorage.setItem('vokabeltrainer.fuehrungen',
  '["erste-schritte","abfrage","planen","texte"]');
// Was nach dem Laden noch zu tun ist. Übersteht die Weiterleitung,
// gilt aber nur für diesen Reiter.
sessionStorage.setItem('aufnahme-schritte', f.get('t') || '');
location.replace('/' + (f.get('z') || '#/uebersicht'));
</script>
"""

# Der Bediener, der in der Seite selbst läuft.
#
# Ein Rahmen (iframe) wäre eleganter gewesen — und wird von Chrome im
# Kopflosbetrieb nicht mitfotografiert: das Bild blieb weiß. Also wird
# diese Datei für die Dauer der Aufnahme in die Oberfläche gelegt und
# aus index.html geladen; hinterher verschwindet beides wieder. Dieselbe
# Vorgehensweise wie bei der Weiche, und derselbe Grund: aufgenommen
# werden soll die echte Seite, nicht eine nachgebaute.
BEDIENER = """
const schlaf = (ms) => new Promise((r) => setTimeout(r, ms));
async function warte(wahl, bis = 10000) {
  const ende = Date.now() + bis;
  while (Date.now() < ende) {
    const e = document.querySelector(wahl);
    if (e) return e;
    await schlaf(100);
  }
  throw new Error('nicht gefunden: ' + wahl);
}
function knopf(text) {
  return [...document.querySelectorAll('button')]
    .find((b) => b.textContent.trim().startsWith(text));
}
async function klick(text, bis = 10000) {
  const ende = Date.now() + bis;
  while (Date.now() < ende) {
    const k = knopf(text);
    if (k) { k.click(); return k; }
    await schlaf(100);
  }
  throw new Error('kein Knopf: ' + text);
}
(async () => {
  const schritte = sessionStorage.getItem('aufnahme-schritte') || '';
  if (!schritte) return;
  await schlaf(1200);                     // die erste Zeichnung abwarten
  try {
    await new Function('schlaf', 'warte', 'klick', 'knopf',
      '"use strict"; return (async () => {' + schritte + '})();'
    )(schlaf, warte, klick, knopf);
  } catch (fehler) {
    // Sichtbar scheitern: ein Bild, das stillschweigend die falsche
    // Seite zeigt, ist schlimmer als keines.
    const balken = document.createElement('pre');
    balken.textContent = 'AUFNAHME GESCHEITERT: ' + fehler.message;
    balken.style.cssText = 'position:fixed;inset:0;margin:0;padding:2rem;'
      + 'background:#c00;color:#fff;font:16px monospace;z-index:99';
    document.body.append(balken);
  }
})();
"""


def freier_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class Dienst:
    """Ein winziger Client für die eigene Schnittstelle."""

    def __init__(self, port: int):
        self.port = port

    def ruf(self, verfahren: str, pfad: str, daten=None):
        v = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        leib = json.dumps(daten) if daten is not None else None
        v.request(verfahren, pfad, body=leib,
                  headers={"Content-Type": "application/json"})
        a = v.getresponse()
        roh = a.read()
        if a.status >= 400:
            raise RuntimeError(f"{verfahren} {pfad} → {a.status}: {roh[:200]!r}")
        return json.loads(roh) if roh else None

    def wartet(self, sekunden: float = 25) -> bool:
        ende = time.time() + sekunden
        while time.time() < ende:
            try:
                self.ruf("GET", "/api/zustand")
                return True
            except OSError:
                time.sleep(0.3)
            except RuntimeError:
                return True
        return False


def nur_dieses_wort(d: Dienst, sammlung_id: int, lemma: str) -> None:
    """Alles stilllegen außer einem Wort.

    Damit steht fest, welche Aufgabe die Abfrage vorlegt — sonst
    passte der absichtliche Tippfehler im Bild nicht zum Wort.
    """
    alle = d.ruf("GET", f"/api/sammlungen/{sammlung_id}/lexeme?anzahl=500")["lexeme"]
    treffer = [l for l in alle if l["lemma"] == lemma]
    if not treffer:
        raise RuntimeError(f"{lemma!r} steht nicht im Kurs")
    andere = [l["id"] for l in alle if l["lemma"] != lemma]
    d.ruf("PUT", "/api/abfrage", {"lexem_ids": andere, "abfrage": False})
    d.ruf("PUT", "/api/abfrage", {"lexem_ids": [treffer[0]["id"]], "abfrage": True})


def alle_wieder_an(d: Dienst, sammlung_id: int) -> None:
    alle = d.ruf("GET", f"/api/sammlungen/{sammlung_id}/lexeme?anzahl=500")["lexeme"]
    d.ruf("PUT", "/api/abfrage",
          {"lexem_ids": [l["id"] for l in alle], "abfrage": True})


def _franzoesisch_anlegen(db) -> int:
    """Eine zweite Sammlung mit einem vollständig konjugierten Verb.

    Genommen aus `werkzeuge/beispieldaten.py` — dort steht `aller` mit
    Präsens und Imparfait, beides sechszellig. Die Sammlung lebt nur in
    der Aufnahmedatenbank und wird am Ende mitsamt ihr weggeworfen; in
    den ausgelieferten Beispielbestand gehört sie nicht.
    """
    import importlib.util
    import aufgaben
    import datenbank as dbm

    pfad = WURZEL / "werkzeuge" / "beispieldaten.py"
    spec = importlib.util.spec_from_file_location("beispieldaten", pfad)
    bd = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(bd)

    cur = db.execute(
        """INSERT INTO sammlung (besitzer_id, name, sprache, grundsprache)
           VALUES (1, ?, 'fr', 'de')""", ("Französisch — Beispiel",))
    sammlung_id = cur.lastrowid
    for eintrag in bd.FRANZOESISCH:
        if eintrag["wortart"] == "verb":
            bd.lexem_anlegen(db, sammlung_id, "de", eintrag)
    db.execute("""UPDATE form SET geprueft = 1
                   WHERE lexem_id IN (SELECT id FROM lexem
                                       WHERE sammlung_id = ?)""",
               (sammlung_id,))
    aufgaben.erzeugen_fuer_sammlung(db, sammlung_id)
    return sammlung_id


def aufnehmen(name: str, ziel: str, hoehe: int, schritte: str,
              port: int, sammlung_id: int, ordner: pathlib.Path,
              profil: int = 1) -> bool:
    adresse = (f"http://127.0.0.1:{port}/_aufnahme.html"
               f"?p={profil}&s={sammlung_id}"
               f"&z={urllib.parse.quote(ziel, safe='')}"
               f"&t={urllib.parse.quote(schritte, safe='')}")
    pfad = ZIEL / f"{name}.png"
    lauf = subprocess.run(
        [CHROME, "--headless", "--disable-gpu", "--hide-scrollbars",
         f"--screenshot={pfad}", f"--window-size={BREITE},{hoehe}",
         "--virtual-time-budget=15000",
         f"--user-data-dir={ordner / 'chrome'}", adresse],
        capture_output=True, text=True)
    gut = pfad.exists() and pfad.stat().st_size > 5000
    groesse = pfad.stat().st_size if pfad.exists() else 0
    print(f"  {'ok  ' if gut else 'LEER'} {name:16} {groesse:8} Byte")
    if not gut and lauf.stderr:
        print("       " + lauf.stderr.strip().splitlines()[-1][:120])
    return gut


def main() -> int:
    if not pathlib.Path(CHROME).exists():
        print(f"Chrome nicht gefunden: {CHROME}", file=sys.stderr)
        return 1

    ordner = pathlib.Path(tempfile.mkdtemp(prefix="readme-bilder-"))
    datenbank = ordner / "aufnahme.db"
    sys.path.insert(0, str(WURZEL / "backend"))

    import datenbank as dbm                                  # noqa: E402
    dbm.PFAD = datenbank
    db = dbm.verbindung()
    dbm.einrichten(db)
    db.execute("INSERT INTO benutzer (id, name, verwalter) VALUES (1, ?, 1)",
               ("Beispiel",))
    import beispielkurs                                      # noqa: E402
    kurs = beispielkurs.anlegen(db, 1)

    # Für »Ganze Reihe« braucht es eine Sprache, die eine hat.
    #
    # Das englische Sprachprofil ist sprachlich richtig und für dieses
    # Bild unbrauchbar: JEDE englische Formgruppe hat genau eine Zelle
    # (Infinitiv, 3. Person Singular, Simple past …), und eine Zelle ist
    # keine Reihe. Es entsteht deshalb gar keine formenreihe-Aufgabe.
    # Französisch hat sechs Zellen je Zeit — das ist der Fall, den die
    # Abfrage zeigen soll.
    franz = _franzoesisch_anlegen(db)
    db.commit()
    db.close()
    sammlung = kurs["sammlung_id"]

    # Weiche, Bediener und der Verweis darauf — alle drei nur für die
    # Dauer der Aufnahme. Die index.html wird dafür angefasst und im
    # finally-Zweig wortgleich wiederhergestellt.
    weiche = WURZEL / "frontend" / "_aufnahme.html"
    bediener = WURZEL / "frontend" / "_aufnahme.js"
    index = WURZEL / "frontend" / "index.html"
    index_vorher = index.read_text()
    weiche.write_text(WEICHE)
    bediener.write_text(BEDIENER)
    index.write_text(index_vorher.replace(
        "</body>", '<script type="module" src="/_aufnahme.js"></script>\n</body>'))
    port = freier_port()
    dienst = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app:app",
         "--host", "127.0.0.1", "--port", str(port), "--log-level", "warning"],
        cwd=WURZEL / "backend",
        env={**os.environ, "VOKABEL_DB": str(datenbank)},
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    d = Dienst(port)
    gut = True
    try:
        if not d.wartet():
            print("Der Dienst ist nicht hochgekommen.", file=sys.stderr)
            return 1
        ZIEL.mkdir(parents=True, exist_ok=True)

        # ---------------------------------------------------- Freigabe
        # Keine Einstellung nötig: der Übungskurs bringt drei ungeprüfte
        # Einträge mit, darunter die erfundene Form »goed«.
        # Eine Ebene tiefer: die Kapitelliste allein zeigt nur Zahlen.
        # Worum es geht, steht in den Wörtern — dort steht »goed« als
        # Simple past von »to walk«, und man sieht, wozu die Freigabe da
        # ist.
        print("Freigabe")
        gut &= aufnehmen("freigabe", "#/freigabe", 820,
                         "const e = await warte('.eintrag');"
                         "e.click(); await schlaf(900);", port, sammlung, ordner)

        # ------------------------------------------------- Textdeckung
        # Die Glosse ist ein Schalter in der Seite, kein gespeicherter
        # Zustand — also klicken.
        print("Textdeckung")
        texte = d.ruf("GET", f"/api/texte?benutzer_id=1")
        text_id = (texte[0] if isinstance(texte, list) else texte["texte"][0])["id"]
        gut &= aufnehmen("textdeckung", f"#/texte/{text_id}", 760,
                         "await klick('Wort für Wort einblenden');"
                         "await schlaf(400);", port, sammlung, ordner)

        # ----------------------------------------------- Fehleranalyse
        # »water« mit vertauschten Buchstaben: der Trainer soll nicht
        # »falsch« sagen, sondern »die Reihenfolge stimmt nicht«.
        print("Fehleranalyse")
        d.ruf("PUT", f"/api/sammlungen/{sammlung}/einstellungen",
              {"typen": ["bedeutung_deutsch_fremd"]})
        nur_dieses_wort(d, sammlung, "water")
        gut &= aufnehmen("fehleranalyse", "#/lernen", 700,
                         "const feld = await warte('.antwortfeld input');"
                         "feld.value = 'wtaer';"
                         "feld.dispatchEvent(new Event('input', {bubbles:true}));"
                         "await klick('Prüfen');"
                         "await warte('.rueckmeldung');"
                         "await schlaf(600);", port, sammlung, ordner)

        # --------------------------------------------------- Paradigma
        # In der FRANZÖSISCHEN Sammlung: sechs Personen des Présent.
        print("Paradigma")
        d.ruf("PUT", f"/api/sammlungen/{franz}/einstellungen",
              {"typen": ["formenreihe"], "formgruppen": ["praesens"]})
        gut &= aufnehmen("paradigma", "#/lernen/frei", 820,
                         "await warte('.reihe input');"
                         "await schlaf(600);", port, franz, ordner)

        # ------------------------------------------------- Legasthenie
        # Alle Posten an, die man SIEHT: Zeichenabstand, größere Schrift,
        # ruhiger Grund, gefärbte Silben, hervorgehobener Stamm und das
        # Schreibgerüst. Die stillen (keine Zeitmessung, weniger Neues)
        # gehören dazu, zeigen sich aber nicht.
        print("Legasthenie")
        # »water« ist von der Fehleranalyse schon beantwortet und darum
        # nicht mehr fällig — ein anderes Wort, und über »frei üben«,
        # das den Terminplan nicht fragt.
        d.ruf("PUT", f"/api/sammlungen/{sammlung}/einstellungen",
              {"typen": ["bedeutung_deutsch_fremd"]})
        nur_dieses_wort(d, sammlung, "house")
        d.ruf("PUT", "/api/benutzer/1/legasthenie",
              {"aktiv": True, "zeichenabstand": 0.12, "zeilenhoehe": 1.9,
               "schriftgroesse": 1.25, "hintergrund": "creme",
               "silben_faerben": True, "stamm_hervorheben": True,
               "maske_stufe": 2, "fehler_benennen": True})
        # Im Legastheniemodus kann eine Einprägephase davorstehen
        # (»Ansehen, hören, dann selbst schreiben«) — dann gibt es noch
        # kein Antwortfeld, sondern einen Knopf. Beides abfangen.
        gut &= aufnehmen("legasthenie", "#/lernen/frei", 760,
                         "await warte('.abfrage');"
                         "const k = knopf('Jetzt schreiben') || knopf('Weiter');"
                         "if (k) { k.click(); await schlaf(700); }"
                         "await warte('.antwortfeld input');"
                         "await schlaf(700);", port, sammlung, ordner)

        alle_wieder_an(d, sammlung)
    finally:
        dienst.terminate()
        dienst.wait(timeout=10)
        weiche.unlink(missing_ok=True)
        bediener.unlink(missing_ok=True)
        index.write_text(index_vorher)
        shutil.rmtree(ordner, ignore_errors=True)

    print(f"\nBilder in {ZIEL.relative_to(WURZEL)}")
    return 0 if gut else 1


if __name__ == "__main__":
    raise SystemExit(main())
