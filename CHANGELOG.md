# Änderungen

Was sich geändert hat, in Alltagssprache — nicht als Liste von Commits.
Wer hier liest, will wissen, was jetzt anders ist und warum, nicht
welche Datei angefasst wurde. Neues steht oben.

Geführt ab dem 15.11.2026. Was davor war, steht in der Versionsgeschichte
(`git log`); die Commit-Nachrichten dort sind ausführlich.

**Regel für Einträge:** eine Überschrift mit Datum, darunter Absätze zu
den einzelnen Änderungen. Bei einem behobenen Fehler gehört dazu, was
man als Benutzerin gemerkt hat — das ist der Anker, an dem man einen
Eintrag wiederfindet.

---

## 15.11.2026

### Die Abfrage war kaputt — behoben

Zu merken war: die Frage erschien kurz und wurde dann überblendet,
Eingeben ging nicht mehr, und die Umschrift auf die griechische
Tastatur fehlte.

Beides kam von einer einzigen Zeile. Beim Umbau des Ausklappers
»Mehr dazu« griff `zeichenleiste()` auf eine Variable zu, die es dort
nicht gibt (sie heißt nur in einer anderen Funktion derselben Datei
so). Jedes Zeichnen der Abfrage brach damit mittendrin ab, nachdem die
Frage schon im Baum hing — daher das kurze Aufblitzen. Und weil
derselbe Aufruf die Umschrift-Tastatur anlegt, war die gleich mit tot.

`werkzeuge/js-pruefen.sh` konnte das nicht finden: die Syntax war
korrekt, ein nie ausgeführter Variablenname fällt erst zur Laufzeit
auf. Seitdem gilt: nach jedem Ausliefern der Oberfläche die Seite im
Browser laden und die Konsole lesen, bevor »fertig« gesagt wird.

Dabei fiel noch auf: die Oberfläche steckt im Docker-Abbild. Ein
`docker compose restart` ändert gar nichts, es braucht `up -d --build`.

### Zeitmessung: eine Unterbrechung ist keine schlechte Antwort

Zu merken war: »manchmal wird etwas als wacklig beurteilt, wo ich mir
denke, nie im Leben habe ich so lange gebraucht«.

Im Protokoll stand als Höchstwert eine Antwort nach 103 Sekunden. Das
ist kein zähes Nachdenken, das ist das Telefon oder ein Reiter im
Hintergrund. Beim Bilden des Bezugsmedians waren solche Ausreißer
längst ausgeschlossen (200 bis 60 000 ms) — für die einzelne Messung
galt das nicht, sie wurde voll gegen die Schwelle gehalten und zog die
Note herunter. Der Median war also klüger als das Urteil, das er
stützen sollte. Jetzt gilt dieselbe Spanne für beides.

Dazu: war die Seite zwischendurch im Hintergrund, wird die Messung
verworfen statt gewertet.

Gemessen am echten Bestand verschob die Zeit vorher 23 % aller
richtigen Antworten.

### Fremde Sammlungen werden nicht mehr ungefragt mitgelernt

Zu merken war: in der allgemeinen Abfrage konnten Wörter aus
Sammlungen auftauchen, die einem nur zum Mitpflegen freigegeben sind.

Die Freigabe beantwortete zwei Fragen zugleich — »wer darf
hineinsehen« und »wer lernt das«. Das sind zwei Dinge. Auf jeder
Sammlungskarte steht jetzt ein Häkchen dafür; voreingestellt sind die
eigenen Sammlungen an und die fremden aus. Über den Knopf »Lernen« auf
der Karte kommt man weiterhin in jede Sammlung hinein — das Häkchen
betrifft nur die Abfrage ohne gewählte Sammlung. Der Lernstand bleibt
unangetastet.

### Neu: Texte lesen und übersetzen

Auf jeder Sammlungskarte gibt es den Knopf **Texte**. Dort lässt sich
ein Text einfügen oder als Datei hochladen; Leerzeilen werden zu
Abschnitten.

Vorweg sagt eine Analyse, ob man den Text schon übersetzen könnte: jedes
Wort wird gegen den eigenen Wortschatz gehalten, Grundformen und
eingetragene Formen, mehrwortige Einträge als Einheit. Dabei wird
ausdrücklich **nicht geraten** — eine Form, die niemand eingetragen hat,
gilt als unbekannt, auch wenn die Grundform längst dasteht. Lieber eine
zu vorsichtige Aussage als eine Zusage, vor der man dann sitzt.

Beim Übersetzen ist jedes Wort anklickbar und schlägt den eigenen
Eintrag auf, mitsamt der Form, die im Text steht. Die eigene Fassung
sichert sich beim Tippen; es gibt kein Abschicken. Zwei Leute können
denselben Text übersetzen, ohne sich zu überschreiben.

Was fehlt, lässt sich antippen und für die angebundene KI merken — mit
dem Satz als Zusammenhang. Die liest die Liste über den MCP, legt die
Vokabeln an und hakt ab. Fünf neue Werkzeuge dafür:
`offene_woerter_lesen`, `offenes_wort_erledigen`, `texte_auflisten`,
`text_anlegen`, `text_deckung_lesen`.

### »Neu würfeln« bei »Was käme dran?«

Der Block lässt sich neu zusammenstellen. Der Zuschnitt bleibt dabei
gleich — wie viel fällig, wacklig und neu, das entscheidet der Termin,
nicht der Würfel. Gewürfelt wird nur, welche Wörter es innerhalb jeder
Gruppe werden; was länger überfällig ist, bleibt vorn. Beim Neuen wird
nicht gemischt, sondern weitergeblättert: Neues wird in seiner
Lernreihenfolge eingeführt, und daran ändert ein Würfel nichts.

Der Wurf wird am Lernziel vermerkt, nicht in der Ansicht. Vorschau und
Abfrage rechnen durch dieselbe Funktion; bliebe der Wurf in der
Ansicht, zeigte »Was käme dran?« einen Block, den »Los« danach nicht
liefert.

### Lernziel bearbeiten — jetzt auch aus der Blockvorschau

Zu merken war: »beim Block kann ich immer noch nichts ändern, also
z.B. ein Lernziel ohne Datum nicht mit Datum versehen«.

Bearbeiten gab es, aber nur auf der Lernzielkarte, eine Ansicht weiter
oben. Der Knopf steht jetzt auch in der Blockvorschau.
