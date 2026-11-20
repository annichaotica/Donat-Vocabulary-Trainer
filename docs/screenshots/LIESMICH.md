# Bildschirmfotos für die README

Fünf Bilder, je eines für eine Stärke. Sie entstehen mit einem
Aufruf:

    .venv/bin/python werkzeuge/bilder-readme.py

Nicht von Hand aufnehmen. Bildschirmfotos veralten, und ein Bild, das
etwas anderes zeigt als das Werkzeug, ist schlimmer als keines — mit
dem Skript kostet das Erneuern einen Aufruf. Es baut dafür eine eigene
Datenbank mit dem englischen Übungskurs auf und wirft sie hinterher
weg; aus dem Familienbestand darf auf diesen Bildern nichts zu sehen
sein.

| Datei | Was darauf zu sehen sein soll | Wo in der Oberfläche |
|---|---|---|
| `fehleranalyse.png` | Die Rückmeldung nach einer falschen Antwort, mit der benannten Fehlerart — nicht »falsch«, sondern »b und d sehen sich ähnlich« oder »das ist die 2. Person Singular«. | Abfrage → eine Form absichtlich mit vertauschten Buchstaben eingeben → die Zeile **»Was passiert ist«** |
| `paradigma.png` | Eine ganze Reihe: sechs Personen einer Zeit, mit Beschriftung und Beispiel je Zeile. | Einstellungen → Aufgabenarten → **Ganze Reihe** einschalten → Abfrage, bis eine Reihe kommt |
| `textdeckung.png` | Ein Lesetext mit eingefärbten Wörtern und der Deckungszahl darüber, am besten mit eingeblendeter Glosse. | Bücher und Texte → einen Text öffnen → **»Wort für Wort einblenden«** |
| `legasthenie.png` | Die Abfrage im Legastheniemodus: größere Schrift, Zeichenabstand, gefärbte Silben, Schreibgerüst. | Einstellungen → Legastheniemodus → *aktiv* → Abfrage |
| `freigabe.png` | Die Freigabe mit wartenden KI-Einträgen, darunter ein erkennbar falscher. | Freigabe (im Beispielbestand warten drei Wörter, eines davon mit der erfundenen Form *goed*) |

## Zwei Dinge, die beim Bauen des Skripts herauskamen

**Englisch kann keine »Ganze Reihe« zeigen.** Jede englische
Formgruppe hat genau eine Zelle — Infinitiv, 3. Person Singular,
Simple past —, und eine Zelle ist keine Reihe. Das ist sprachlich
richtig und heißt: aus dem englischen Übungskurs entsteht gar keine
`formenreihe`-Aufgabe. `paradigma.png` kommt deshalb aus einer
französischen Sammlung, die das Skript für sich selbst anlegt
(`aller`, sechs Personen im Présent, aus
`werkzeuge/beispieldaten.py`).

**Die Aufnahmen teilen eine Datenbank.** Wer in einem Bild eine
Aufgabe beantwortet, nimmt sie dem nächsten weg — sie ist dann nicht
mehr fällig. Die späteren Aufnahmen gehen darum über »frei üben«, das
den Terminplan nicht fragt.

Scheitert ein Schritt, wird das Bild **knallrot** mit der Ursache
darauf. Ein Bild, das stillschweigend die falsche Seite zeigt, wäre
schlimmer als keines.
