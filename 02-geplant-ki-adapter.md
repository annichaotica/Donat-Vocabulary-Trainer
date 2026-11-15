# Geplant: ein Adapter für eine angebundene KI

*Stand 15.11.2026. Entwurf, nicht gebaut. Bewusst nicht gebaut — die
Begründung steht weiter unten und ist der eigentliche Inhalt dieses
Dokuments.*

## Worum es geht

Der Trainer ruft heute **nirgends nach außen**. Kein Schlüssel, keine
Netzabhängigkeit, keine Kosten; `requirements.txt` kennt drei Pakete.
Wo „KI" im Quelltext steht, ist das ein Herkunftsvermerk — *wer hat das
eingetragen* —, kein Aufruf.

Alles, was eine KI hier tut, tut sie über den **MCP-Server**: das
Chatprogramm der Benutzerin verbindet sich, liest, trägt ein. Die
Rechnung zahlt ihr bestehendes Abonnement, die Entscheidung über jeden
Schritt trifft ein Mensch, und abgefragt wird erst nach Freigabe.

Die Frage, die zu diesem Dokument geführt hat: *»Möglicherweise wäre es
opportun, eine Art allgemeiner KI anzubinden, falls es dafür eine
gibt. Die Hetzner-KI, die ich angebunden hatte für die Tests, ist
abgekündigt.«*

## Was es brächte — und was nicht

Nichts, was heute nicht geht. Der Unterschied ist **unbeaufsichtigte
Arbeit**:

| heute | mit Adapter |
|---|---|
| Text einfügen, Chat bitten zu übersetzen | Text einfügen, Übersetzung liegt da |
| Chat bitten, die Formen zu ergänzen | Lücke erkannt, Formen vorgeschlagen |
| Chat bitten, die angeforderten Wörter einzutragen | läuft nachts durch |

Das ist Bequemlichkeit, kein Können. Bezahlt wird sie mit einem
Schlüssel auf dem Server, ausgehendem Verkehr mit den Lerndaten von
Kindern, laufenden Kosten und einer Abhängigkeit, die abgekündigt
werden kann — wie gerade geschehen.

## Warum nicht jetzt

1. **Der Gewinn ist klein.** Das Chatprogramm kann alles davon schon,
   und es ist besser als alles, was sich selbst betreiben ließe.
2. **Der Preis ist nicht nur Geld.** Heute lässt sich über dieses
   Werkzeug in einem Satz sagen: es telefoniert nicht nach Hause. Das
   ist bei einem Familienwerkzeug mehr wert als eine Nachtschicht
   Formenergänzung.
3. **Die Hardware trägt es nicht.** Der Familienserver ist ein Dell
   OptiPlex 3080 Micro: i5-10500T, 16 GB, **keine Grafikkarte**, und
   Immich, Paperless und Mealie laufen schon darauf. Ein quantisiertes
   7–8B-Modell schafft dort wenige Token je Sekunde. Für einen kurzen
   Satz reicht das; für griechische Formentabellen wäre die Qualität
   deutlich schlechter als die des Chats — und eine falsche Form, die
   unbemerkt gepaukt wird, ist schlimmer als eine fehlende.
4. **Die Lage ändert sich.** Dieses Dokument nennt bewusst keine
   Preise und keine Modellnamen. Wer es umsetzt, sieht zuerst nach,
   was es dann gibt.

## Wie es gebaut würde

### Anbieterneutral, weil es nichts kostet

Fast alle in Frage kommenden Dienste sprechen dieselbe
OpenAI-kompatible HTTP-Schnittstelle — auch ein lokales Ollama oder
llama.cpp. Es braucht also keine Festlegung auf einen Anbieter,
sondern **eine einstellbare Adresse**. Drei Klassen kämen in Frage:

- **lokal** auf dem Familienserver (Ollama, llama.cpp): kostet nichts,
  nichts verlässt das Haus, Qualität und Tempo siehe oben;
- **europäisch gehostet** (Mistral, Aleph Alpha, IONOS, OVHcloud,
  Scaleway): Cent-Beträge bei Familienumfang;
- **die großen** (Anthropic, OpenAI, Google): beste Qualität, Daten
  verlassen das Haus und meist die EU.

Im öffentlichen Quelltext steht keiner davon. Was eingetragen wird,
steht in der `.env` und gehört zur Anlage, nicht zum Programm —
dieselbe Regel wie bei der MCP-Adresse.

### Skizze

```
backend/ki.py
    verfuegbar() -> bool          liest KI_ADRESSE, KI_SCHLUESSEL, KI_MODELL
    fragen(auftrag, text) -> str  ein Aufruf, OpenAI-kompatibel,
                                  mit Zeitgrenze und ohne Wiederholung
```

Drei Umgebungsvariablen, **Vorgabe leer = aus**. Ist nichts gesetzt,
verhält sich der Trainer exakt wie heute; kein Knopf erscheint, keine
Verbindung wird aufgebaut.

Genau zwei Aufrufstellen zu Beginn:

| Stelle | Auftrag | ohne Adapter |
|---|---|---|
| `lesetexte` | Abschnitte übersetzen → `textabschnitt.referenz` | der Chat über `text_uebersetzen` |
| `aufgaben` | fehlende Formen vorschlagen | der Chat über `formen_ergaenzen` |

Beide bleiben **ohne** Adapter vollständig benutzbar. Das ist die
Bedingung, unter der das überhaupt hineingehört: keine Funktion darf
davon abhängen.

### Regeln, die nicht verhandelbar sind

- **Nichts wird freigegeben.** Was der Adapter liefert, ist
  `geprueft = 0` und `quelle = 'ki'` — wie beim MCP-Server. Ein
  Programm, das seine eigenen Einträge freigibt, hat die Prüfung
  abgeschafft, nicht erledigt.
- **Jeder Aufruf ist sichtbar.** Wer ihn ausgelöst hat, wann, wie
  viele Zeichen hinausgingen. Ohne Protokoll ist „es telefoniert nicht
  nach Hause" nicht mehr prüfbar, sondern nur noch behauptet.
- **Nur auf Anforderung, nie im Hintergrund** — jedenfalls in der
  ersten Fassung. Ein nächtlicher Lauf ist der ganze Reiz, aber er
  gehört erst dazu, wenn das Protokoll steht und jemand es gelesen hat.
- **Keine Lerndaten.** Hinaus gehen Wörter und Texte, nicht wer wie
  gut ist. Die Lernstände haben außerhalb des Hauses nichts verloren.
- **Abschaltbar bleibt der Normalfall.** Die `.env` leeren, neu
  starten, fertig.

### Aufwand

Etwa ein halber Tag für Adapter, die zwei Stellen, Protokoll und
Tests. Der Adapter selbst ist klein; die Arbeit steckt darin, dass
beide Wege — mit und ohne — weiter funktionieren und geprüft sind.

## Wenn es jemand umsetzt

Zuerst nachsehen, was es dann gibt: Anbieter, Preise und
Datenschutzbedingungen ändern sich schneller, als ein Dokument
nachkommt. Die Entscheidung, die dieses Dokument trifft, ist nicht
„Anbieter X", sondern: **einstellbar, aus als Vorgabe, und keine
Funktion, die davon abhängt.**
