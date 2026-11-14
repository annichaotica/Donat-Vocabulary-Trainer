# Vokabeltrainer — Konzept und Architektur

Stand 2026-11-14. Eigenbau, weil die üblichen Trainer eine Vokabel als *Paar
aus zwei Zeichenketten* begreifen. Genau daraus folgen alle Ärgernisse: starre
Abfragerichtung, dummes Richtig/Falsch, undurchschaubare Intervalle — und vor
allem die Unfähigkeit, **Formen** abzufragen, also das, was wirklich gepaukt
werden muss.

## Der Kern: das Datenmodell

Nicht ein Paar, sondern drei getrennte Ebenen.

```
LEXEM  (das Wort als Eintrag: "aller", Verb, Französisch)
  │
  ├── FORMEN      — jede mit Merkmalen beschrieben
  │     "vais"    {person:1, numerus:sg, tempus:präsens, modus:indikativ}
  │     "allions" {person:1, numerus:pl, tempus:imperfekt, modus:indikativ}
  │     "allé"    {form:partizip-perfekt}
  │
  └── BEDEUTUNGEN — jede mit beliebig vielen gültigen Übersetzungen
        1. "gehen" | "laufen" | "zu Fuß gehen"
        2. "fahren" (mit Fahrzeug)
```

Daraus folgt alles Weitere von selbst:

- **Abfragerichtung ist frei**, weil keine Richtung im Datensatz eingebacken
  ist. Jede Richtung und jede Mischung ist nur eine Auswahl über denselben Daten.
- **Mehrere gültige Übersetzungen sind der Normalfall**, nicht der Sonderfall.
- **Bedeutung und Form sind getrennt planbar.** „Bedeutung weiß ich, aber die
  Konjugation nicht" ist ein Zustand, den das Modell kennt und abbilden kann.

### Merkmale statt Spalten

Formen werden nicht in festen Spalten gespeichert (`praesens_1sg`,
`praesens_2sg`, …), sondern als **Merkmalsbündel**. Jede Sprache bringt ihren
eigenen Merkmalsraum mit, als Daten, nicht als Code. Englisch braucht kein
Genus, Griechisch braucht Kasus und Aspekt, Latein bräuchte Ablativ. Neue
Sprache heißt neues Sprachprofil, nicht neue Datenbankspalten.

## Die abfragbare Einheit ist die Aufgabe, nicht die Vokabel

Terminiert wird nicht „das Wort *aller*", sondern jede einzelne **Aufgabe**
darüber. Das ist der zweite entscheidende Unterschied zu allen bekannten
Trainern.

| Typ | Frage | Erwartet |
|---|---|---|
| `bedeutung_fremd_deutsch` | *aller* | gehen |
| `bedeutung_deutsch_fremd` | gehen | aller |
| `form_bilden` | 1. Pers. Sg. Präsens von *aller* | vais |
| `form_bestimmen` | Welche Form ist *allions*? | 1. Pers. Pl. Imperfekt |
| `paradigma` | *aller* im Präsens konjugieren | alle sechs Formen |
| `stammformen` | go — ? — ? | went, gone |
| `genus` | ___ table | la |
| `luecke` | Hier *(aller)* je ___ à Paris. | vais |
| `diktat` | 🔊 anhören | geschriebene Form |
| `aussprache` | *aller* vorlesen | Selbsteinschätzung |

Aufgaben werden **erzeugt**, nicht gepflegt. Wer eine Form einträgt, bekommt
die zugehörigen Aufgaben automatisch; niemand legt Karten von Hand an.

## Antwortprüfung in Schichten

Keine Zeichenkettengleichheit. Von außen nach innen:

1. **Normalisierung** pro Sprache — Unicode NFC, Leerraum, Satzzeichen.
2. **Schrift- und Diakritikaregeln** pro Sprache, dreistufig einstellbar:
   streng / als Hinweis / ignorieren. Griechisch braucht Sonderbehandlung
   (Schluss-Sigma ς↔σ, Tonos, Dialytika), Französisch und Spanisch die Akzente.
3. **Alternativen** — mehrere gültige Übersetzungen, Klammerteile als optional
   (`(sich) waschen`), Artikel je Sprache verlangt oder freigestellt.
4. **Tippfehlertoleranz** per Editierabstand, an die Wortlänge gekoppelt.
   Ergebnis ist dann nicht „falsch", sondern **„fast richtig, bitte nochmal"** —
   ohne Strafe für den Lernstand.
5. **Teilrichtig** bei Paradigmen: fünf von sechs Formen richtig ist kein
   Fehlschlag, sondern wird je Zelle bewertet.

## Lernalgorithmus: FSRS, aber einsehbar

FSRS (Nachfolger von SM-2, wie im heutigen Anki) — aber mit offener Rechnung.
Zu jeder Aufgabe ist jederzeit sichtbar:

- **Stabilität** (wie lange das Gedächtnis hält), **Schwierigkeit**,
  **Abrufwahrscheinlichkeit** heute
- **Warum kommt das jetzt?** — und was die nächsten Termine wären, je nachdem
  wie du bewertest
- Eingriff von Hand: aussetzen, zurücksetzen, Termin selbst setzen

Dazu **freies Üben** ohne Terminlogik: nur Lektion 3, nur Verbformen, nur was
letzte Woche schiefging. Das Protokoll aller Wiederholungen wird nie gelöscht —
damit lassen sich die FSRS-Parameter später auf dein eigenes Lernverhalten
optimieren.

## Befüllung — die eigentliche Arbeit

Vierzig Formen pro Verb tippt niemand. Vier Wege, kombinierbar:

1. **Import** aus CSV, Excel, Anki- und Quizlet-Export.
2. **Paradigma-Generator**: Konjugationsmuster als Daten je Sprache. Das
   Muster schlägt die Formen vor, sie werden als *generiert, ungeprüft*
   markiert und in der Oberfläche sichtbar anders dargestellt, bis du sie
   bestätigt oder korrigiert hast.
3. **Offene Quellen** (Wiktionary) zum Nachladen von Formen und Übersetzungen.
4. **KI über einen eigenen MCP-Server** — `mcp__vokabeltrainer__*`. Damit kann
   Claude direkt Lexeme mit vollständigen Paradigmen anlegen, Formen ergänzen
   und Beispielsätze einpflegen. Genau für Verb- und Zeitformen der schnellste
   Weg. Jeder so entstandene Eintrag trägt seine Herkunft im Datensatz.

Jede Form weiß, **woher sie kommt** (manuell, generiert, Wiktionary, KI) und
**ob sie geprüft ist**. Ungeprüfte Formen werden nicht abgefragt, solange du
das nicht erlaubst.

## Mehrere Benutzer

Profile ohne Passwort (reines Heimnetz). Jeder hat **eigene Sammlungen** und
**eigene Lernstände**; Sammlungen lassen sich an andere Profile freigeben, mit
Lese- oder Schreibrecht. Der Lernstand bleibt immer persönlich, auch bei
geteiltem Bestand — zwei Leute mit demselben Schulbuch, aber getrennten
Intervallen.

## Technik

| | |
|---|---|
| Läuft auf | Familienserver, Docker, Port **8030** |
| Erreichbar | `http://familienserver:8030` im Heimnetz, von Mac, iPad, Handy |
| Backend | Python, FastAPI |
| Datenbank | **SQLite** in `/srv/vokabeltrainer/` — eine Datei, wird von der bestehenden `/srv`-Sicherung automatisch mitgenommen, kein zusätzlicher Postgres-Container |
| Frontend | HTML, CSS und ES-Module ohne Bauschritt. Kein npm, keine Übersetzungsstufe, in fünf Jahren noch wartbar. Als PWA auf den Startbildschirm legbar |
| Audio | Sprachsynthese im Browser (Web Speech API) für Englisch, Französisch, Spanisch, Griechisch; Audiofeld je Form für eigene Aufnahmen |
| MCP | eigener Server, spricht über die HTTP-Schnittstelle mit dem Trainer |

Warum kein Bauschritt im Frontend: ein Vokabeltrainer soll in fünf Jahren noch
starten, ohne dass ein Paketbaum von 2026 sich neu auflösen lässt.

## Textverständnis — die Stufe nach dem Pauken

Vokabeln zu wissen ist nicht dasselbe wie einen Text zu verstehen. Darum eine
zweite Ebene über dem Wortschatz, im Datenmodell schon angelegt:

```
TEXT ── ABSCHNITTE (meist Sätze; die Einheit, an der gearbeitet wird)
  │        └── Referenzübersetzung je Abschnitt
  │
  ├── TEXT_LEXEM — welche Vokabeln kommen darin vor
  └── TEXTAUFGABEN — übersetzen hin, übersetzen zurück,
                     Verständnisfragen, Lückentext
```

Die Verknüpfung `text_lexem` ist der eigentliche Gewinn: sie macht Text und
Wortschatz **miteinander verrechenbar**. Damit lässt sich beides beantworten —
„übe die Vokabeln zu diesem Text" und, umgekehrt, „welchen Text kann ich mit
meinem Wortschatz schon lesen".

**Das Bewertungsproblem.** Eine freie Übersetzung lässt sich nicht per
Zeichenkettenvergleich prüfen. Es gibt genau drei brauchbare Wege, und jede
Textaufgabe trägt im Datensatz, welcher für sie gilt:

| | |
|---|---|
| `genau` | prüfbare Antwort — Lückentext, Auswahlfrage. Geht mit der vorhandenen Antwortprüfung. |
| `selbst` | Referenzübersetzung aufdecken, selbst einschätzen. Wie bei Anki, ehrlich und ohne Technik. |
| `ki` | echte Rückmeldung über den MCP-Server: was fehlt, was ist falsch verstanden, was ist nur anders formuliert. |

Der dritte Weg ist der interessante und der Grund, warum der MCP-Server nicht
nur zum Befüllen taugt: über ihn kommen ganze Texte mit Abschnitten und
Referenzübersetzungen herein, und über ihn kommt auch die Bewertung zurück.
Die Rückmeldung wird mitprotokolliert, damit nachvollziehbar bleibt, woran es
lag.

## Reihenfolge der Umsetzung

**Stufe 1 — das Fundament.** Datenbankschema, Sprachprofile, Backend-API für
Lexeme, Formen und Bedeutungen. Antwortprüfung mit allen Schichten. FSRS.
Abfrageoberfläche für die Typen Bedeutung (beide Richtungen), Formbilden,
Formbestimmen. Docker-Aufbau, läuft auf dem Server.

**Stufe 2 — Befüllung.** Eingabemaske, Paradigma-Generator mit Mustern für
Französisch, Spanisch, Englisch, Griechisch. Import. MCP-Server.

**Stufe 3 — Ausbau.** Audio und Diktat, Paradigmentabellen als Aufgabentyp,
Lückensätze, Statistik und Einsicht in den Algorithmus, freies Üben,
Wiktionary-Anbindung, Freigabe von Sammlungen.

**Stufe 4 — Textverständnis.** Texte mit Abschnitten und
Referenzübersetzungen, Übersetzen in beide Richtungen, Verständnisfragen,
Bewertung über den MCP-Server. Die Tabellen dafür stehen bereits im Schema.
