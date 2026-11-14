# Vokabeltrainer

Browserbasiert, eigene Datenbank, läuft im Heimnetz. Gebaut, weil die
üblichen Trainer eine Vokabel als *Paar aus zwei Zeichenketten* begreifen und
daran alles scheitert, was man eigentlich pauken muss — Formen, Zeiten,
Konjugationen.

Das Konzept samt Begründung der Entwurfsentscheidungen steht in
[`00-konzept.md`](00-konzept.md). Die Festlegung für die KI-gestützte
Befüllung in [`01-format-fuer-ki-befuellung.md`](01-format-fuer-ki-befuellung.md).

## Was ihn unterscheidet

| | |
|---|---|
| **Formen statt Paare** | Ein Lexem hat Formen (mit Merkmalen beschrieben) und Bedeutungen (mit beliebig vielen gültigen Übersetzungen). Daraus folgt freie Abfragerichtung von selbst. |
| **Aufgaben werden erzeugt** | Terminiert wird nicht „das Wort", sondern jede einzelne Aufgabe darüber. „Bedeutung weiß ich, Konjugation nicht" ist ein Zustand, den das Modell kennt. |
| **Verwechslung statt Tippfehler** | Wer bei der 1. Person *vas* schreibt, hat sich nicht vertippt. Der Trainer sagt: „Das ist die 2. Person Singular." |
| **Fehler werden benannt** | „b und d sehen sich ähnlich", „hier gehört mm hin", „die Reihenfolge stimmt nicht" — statt bloß „falsch". |
| **Keine Selbsteinschätzung** | Die Bewertung wird aus Richtigkeit, Fehlerart, Versuchen und Denkzeit abgeleitet — und begründet. |
| **Offene Rechnung** | FSRS-5, aber Stabilität, Schwierigkeit und Abrufwahrscheinlichkeit sind jederzeit einsehbar: „Warum kommt das jetzt?" |
| **Sprachen sind Daten** | Formgruppen, Prüfregeln und Artikel stehen im Sprachprofil, nicht im Code — und lassen sich über die Schnittstelle ändern. |

Mitgeliefert: Französisch, Spanisch, Englisch, Griechisch, Mittelhochdeutsch,
Deutsch. Weitere lassen sich ohne Codeänderung einrichten.

## Starten

### Auf dem Mac, zum Entwickeln

```sh
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python werkzeuge/beispieldaten.py        # Beispielbestand
.venv/bin/uvicorn app:app --app-dir backend --reload --port 8020
```

Dann <http://localhost:8020>. Tests: `.venv/bin/python -m pytest tests/ -q`

### Auf dem Familienserver

```sh
ssh familienserver
sudo mkdir -p /srv/vokabeltrainer && sudo chown "$USER" /srv/vokabeltrainer
# Projekt dorthin kopieren, dann:
cd /srv/vokabeltrainer && docker compose up -d --build
```

Erreichbar unter <http://familienserver:8020>, nur im Heimnetz. Port 8020,
weil 80 (Startseite), 2283 (Immich), 8010 (Paperless) und 9925 (Mealie)
belegt sind.

Auf dem iPhone oder iPad die Seite aufrufen und „Zum Home-Bildschirm" —
dann startet sie wie eine App.

### Sicherung

Die Datenbank liegt unter `/srv/vokabeltrainer/daten/` und wird damit von der
bestehenden `/srv`-Sicherung mitgenommen. **Aber:** sie läuft im WAL-Modus,
ein bloßes Kopieren der Datei während eines Schreibvorgangs ergibt einen
unvollständigen Stand. Darum vor dem Borg-Aufruf in
`/usr/local/sbin/familienserver-sichern` einhängen:

```sh
/srv/vokabeltrainer/werkzeuge/sicherung.sh
```

Das Skript legt einen in sich stimmigen Abzug unter `daten/abzug/` ab, prüft
ihn und behält die letzten sieben.

## Der MCP-Server

Damit kann Claude Vokabeln samt vollständigen Paradigmen unmittelbar
eintragen — ohne Dateien hin und her zu tragen. Nach jedem Anlegen läuft die
Qualitätsprüfung mit und ihr Ergebnis geht zurück: ob der Stamm ableitbar ist,
ob das Paradigma Lücken hat, ob eine Übersetzung fehlt.

Er braucht **keine Fremdpakete**, nur Python 3.

### In Claude Code einrichten

```sh
claude mcp add vokabeltrainer \
  --env VOKABEL_URL=http://familienserver:8020 \
  -- python3 /Users/annuschkabrenner/Projects/Vokabeltrainer/mcp/vokabeltrainer_mcp.py
```

### In der Claude-App einrichten

In `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "vokabeltrainer": {
      "command": "python3",
      "args": ["/Users/annuschkabrenner/Projects/Vokabeltrainer/mcp/vokabeltrainer_mcp.py"],
      "env": { "VOKABEL_URL": "http://familienserver:8020" }
    }
  }
}
```

### Die Werkzeuge

| Werkzeug | wofür |
|---|---|
| `sammlungen_auflisten` | Der erste Aufruf — ohne `sammlung_id` geht nichts |
| `formgruppen_zeigen` | **Vor** dem ersten Eintragen in einer Sprache: welche Merkmalsbündel die Formen tragen müssen |
| `vokabel_anlegen` | Ein ganzes Wort mit allen Formen und Bedeutungen in einem Zug |
| `vokabel_nachschlagen` | Über Lemma, **alle Formen** und alle Übersetzungen |
| `formen_ergaenzen` | Einem bestehenden Eintrag eine weitere Zeit anfügen |
| `eintrag_pruefen`, `sammlung_pruefen` | Taugt das für die Fähigkeiten des Trainers? |
| `formen_bestaetigen` | Freigabe — erst danach wird abgefragt |
| `sprachprofil_lesen`, `sprachprofil_anpassen`, `sprache_einrichten` | Eine Sprache zum Laufen bringen, ohne Codeänderung |

**Eingetragene Formen bleiben ungeprüft**, bis ein Mensch sie freigibt. Das
ist Absicht: eine erfundene Form, die unbemerkt gepaukt wird, ist schlimmer
als eine fehlende.

## Aufbau

```
backend/
  schema.sql        Datenbank. 20 Tabellen, mit Kommentaren
  merkmale.py       Grammatische Merkmale, deutsche Beschriftungen
  sprachen.py       Sprachprofile: Formgruppen, Prüfregeln, Artikel
  pruefung.py       Antwortprüfung in Schichten
  legasthenie.py    Fehlerarten benennen, Stamm ableiten, Silben
  fsrs.py           Lernalgorithmus, nachvollziehbar
  bewertung.py      Note aus Richtigkeit, Fehlerart und Denkzeit
  aufgaben.py       Aufgaben erzeugen, stellen, prüfen
  lernen.py         Die Sitzung
  lernziele.py      Ziele und dynamische Lernblöcke
  qualitaet.py      Prüft Einträge auf das, was der Trainer braucht
  datenbank.py      SQLite, Wanderungen
  app.py            HTTP-Schnittstelle
frontend/           HTML, CSS, ES-Module. Kein Bauschritt, kein npm
mcp/                MCP-Server, nur Standardbibliothek
werkzeuge/          Beispieldaten, Sicherung
tests/              159 Tests
```

Warum kein Bauschritt im Frontend: ein Vokabeltrainer soll in fünf Jahren noch
starten, ohne dass sich ein Paketbaum von 2026 neu auflösen lässt.

## Tastatur

| | |
|---|---|
| <kbd>Enter</kbd> | prüfen; danach weiter mit der automatischen Wertung |
| <kbd>1</kbd>–<kbd>4</kbd> | von Hand anders werten |
| <kbd>l</kbd> / <kbd>w</kbd> / <kbd>u</kbd> | lernen, Wortschatz, Übersicht |

Für Akzente gibt es eine Zeichenleiste unter dem Antwortfeld. Für Sprachen
mit eigener Schrift — Griechisch — lohnt ein richtiges Tastaturlayout; die
Anleitung dazu steht unter `#/tastatur`.

## Stand

**Fertig:** Datenmodell, Antwortprüfung, FSRS mit automatischer Bewertung,
Abfrage für fünf Aufgabentypen, Wortschatzverwaltung mit Eingabemaske,
Sprachprofile als Daten, Qualitätsprüfung, Wörterbuchsuche über alle Formen,
Lernziele mit dynamischen Blöcken, Legastheniemodus, MCP-Server, Docker.

**Als Nächstes:** Import aus CSV und Anki, Paradigma-Generator,
Wiktionary-Anbindung, Diktat und Aussprache, Paradigmentabellen als
Aufgabentyp, Lückensätze, Statistik.

**Später (Tabellen stehen schon):** Textverständnis — Texte mit Abschnitten
und Referenzübersetzungen, Übersetzen in beide Richtungen,
Verständnisfragen, Bewertung über den MCP-Server.
