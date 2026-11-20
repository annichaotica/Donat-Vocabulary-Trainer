# Bildschirmfotos für die README

Fünf Bilder, je eines für eine Stärke. Sie fehlen noch; solange sie
fehlen, zeigt die englische README gebrochene Bilder — das ist
beabsichtigt und sichtbarer als eine Zeile in einer Aufgabenliste.

| Datei | Was darauf zu sehen sein soll | Wo in der Oberfläche |
|---|---|---|
| `fehleranalyse.png` | Die Rückmeldung nach einer falschen Antwort, mit der benannten Fehlerart — nicht »falsch«, sondern »b und d sehen sich ähnlich« oder »das ist die 2. Person Singular«. | Abfrage → eine Form absichtlich mit vertauschten Buchstaben eingeben → die Zeile **»Was passiert ist«** |
| `paradigma.png` | Eine ganze Reihe: sechs Personen einer Zeit, mit Beschriftung und Beispiel je Zeile. | Einstellungen → Aufgabenarten → **Ganze Reihe** einschalten → Abfrage, bis eine Reihe kommt |
| `textdeckung.png` | Ein Lesetext mit eingefärbten Wörtern und der Deckungszahl darüber, am besten mit eingeblendeter Glosse. | Bücher und Texte → einen Text öffnen → **»Wort für Wort einblenden«** |
| `legasthenie.png` | Die Abfrage im Legastheniemodus: größere Schrift, Zeichenabstand, gefärbte Silben, Schreibgerüst. | Einstellungen → Legastheniemodus → *aktiv* → Abfrage |
| `freigabe.png` | Die Freigabe mit wartenden KI-Einträgen, darunter ein erkennbar falscher. | Freigabe (im Beispielbestand warten drei Wörter, eines davon mit der erfundenen Form *goed*) |

## Aufnehmen

Der Beispielbestand reicht für alle fünf:

```sh
BEISPIELDATEN=1 .venv/bin/uvicorn app:app --app-dir backend --port 8030
```

Es gibt ein Werkzeug, das die Bilder des eingebauten Lehrgangs aufnimmt
— `werkzeuge/bilder-aufnehmen.py`. Für diese fünf ist es nicht
eingerichtet; von Hand aufnehmen ist schneller als es zu erweitern.

**Breite 1100 px**, heller Grund, und vorher nachsehen, dass kein
echter Name und keine echte Sammlung im Bild steht. Im Beispielbestand
heißt das Profil »Zum Ausprobieren«.
