# Mitarbeit

Dieses Projekt ist offen einsehbar und darf unter den Bedingungen der
[AGPL-3.0](LICENSE) benutzt, verändert und weitergegeben werden.

**Mitarbeit am Repo selbst ist auf Anfrage.** Das ist kein Misstrauen,
sondern hat zwei nüchterne Gründe: der Trainer wird von Kindern zum Lernen
benutzt, und jede Änderung am Lernalgorithmus oder an der Antwortprüfung
wirkt unmittelbar auf ihren Lernstand. Und das Projekt wird von einer
Person gepflegt, die nicht jeden eingereichten Vorschlag prüfen kann.

## Wenn du etwas beitragen möchtest

1. **Zuerst ein Issue aufmachen** und beschreiben, worum es geht. Auch bei
   kleinen Dingen — es erspart beiden Seiten vergebliche Arbeit.
2. Abwarten, ob und wie es hineinpasst. Antwort kann dauern.
3. Erst dann Code. Unaufgefordert eingereichte Pull Requests werden in der
   Regel ohne Prüfung geschlossen.

## Wenn du einen Fehler gefunden hast

Immer willkommen, auch ohne Rückfrage. Hilfreich ist:
was du getan hast, was passiert ist, was du erwartet hast. Bei Fehlern in
der Antwortprüfung bitte die Sprache, das Wort und die eingegebene Antwort
nennen — das reicht meist schon, um es nachzustellen.

## Wenn du es für dich selbst anpassen willst

Dafür brauchst du niemanden zu fragen: abspalten und loslegen. Beachte
dabei die AGPL — wer eine veränderte Fassung **über das Netz anbietet**,
muss seinen Quelltext veröffentlichen. Für den Betrieb zu Hause im eigenen
Netz gilt das nicht.

## Wenn doch Code eingereicht wird

- Deutsche Bezeichner im Fachcode (lexem, bedeutung, aufgabe), wie im
  Bestand.
- Kommentare erklären **warum**, nicht was.
- Tests dazu. `python -m pytest tests/ -q` muss durchlaufen.
- Keine neuen Abhängigkeiten ohne vorherige Absprache. Das Frontend hat
  bewusst keinen Bauschritt und soll keinen bekommen.

Mit dem Einreichen stellst du deinen Beitrag unter dieselbe Lizenz.
