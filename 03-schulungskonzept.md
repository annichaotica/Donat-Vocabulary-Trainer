# Schulungskonzept

*Stand 15.11.2026. Konzept, nicht der Schulungstext selbst. Hier steht,
was erklärt werden muss, in welcher Reihenfolge, in welcher Form und
warum gerade so.*

## Der Anlass

»*mir sind diese vier rundgänge zu kurz und zu oberflächlich. außerdem
fehlt völlig etwas zur rolle der ki, wie man verben eingibt und so
weiter*«

Beides trifft zu, und die beiden Hälften haben verschiedene Ursachen.

**Zu kurz** ist messbar: 15 Schritte für ein Werkzeug mit 14 Ansichten,
38 MCP-Werkzeugen und 23 Tabellen. Eine Blase hält drei Sätze; alles,
was mehr braucht, kann ein Rundgang nicht tragen. Das war beim Bau
Absicht (»eine Tour über fünfzehn Funktionen hat niemand zu Ende
gesehen«) und ist als Entscheidung richtig — nur fehlt daneben die
Form, die das Längere trägt.

**Zu oberflächlich** ist nicht die Länge, sondern die Ebene. Die
Rundgänge und die Anleitung erklären, *wo etwas steht* und *was ein
Knopf tut*. Sie erklären nicht, *wie der Trainer denkt*. Beispiel: der
Schritt »Die vier Zahlen« erklärt fällig, verlernt, neu, sitzt — aber
nicht, dass gezählt wird, was eine **Aufgabe** ist, und dass ein
griechisches Verb mit drei Zeiten siebzehn davon hat. Wer das nicht
weiß, hält die Zahl 6971 für einen Fehler.

Dieser Unterbau fehlt überall, und daran hängen die beiden genannten
Lücken: wer das Datenmodell nicht kennt, kann weder Verben eingeben
noch verstehen, was die Freigabe eigentlich freigibt — und damit auch
nicht, warum die KI sie nicht selbst machen darf.

## Was heute schon erklärt wird

| Ort | Umfang | Was er leistet |
|---|---|---|
| `fuehrung.js`, vier Rundgänge | 15 Schritte, angegeben 9 Minuten | Orientierung: wo liegt was, welcher Knopf tut was |
| `ansicht_hilfe.js`, Teil »Lernen« | 9 zugeklappte Abschnitte | Nachschlagewerk zu den Lernregeln, gut geschrieben |
| `ansicht_hilfe.js`, Teil »Chatprogramm« | 5 Abschnitte, 3 Schritte | Anschließen des Konnektors, die Kopfzeilenfalle |
| `beispielkurs.py` | 18 Wörter, 2 Sätze, 1 Text, 1 Regel, 5 Lektionen | Etwas zum Anfassen — aber ohne Anleitung, was man damit tun soll |
| Texte am Ort (Schalter, Marken) | verstreut | teils sehr gut, siehe unten |
| `00-konzept.md`, `01-format-…md` | 200 + 636 Zeilen | für Entwicklung und für die KI, nicht für die Benutzerin |

Zwei Befunde dazu:

**Die Anleitung ist ein Nachschlagewerk, das als Schulung gelesen
werden müsste.** Elf zugeklappte `details`-Abschnitte. Zugeklappt
öffnet man, wenn man ein Problem hat — nicht, bevor man eines hat.
Genau die Dinge, die man *vorher* wissen muss (fast richtig kostet
nichts, Weiß-ich-nicht ist keine Niederlage, der Rückstand ist keine
Mauer), stehen hinter einem Dreieck.

**Der Übungskurs ist gebaut, aber nicht benutzt.** Er bringt
ausdrücklich für jede Funktion etwas mit — Lektionsnamen für die
Schranke, `child/children` als echte Formaufgabe, `read/read/read` als
Fall für »das musst du wirklich wissen«. Nirgends steht, dass man ihn
dafür verwenden soll. Er ist vollständig freigegeben angelegt, was für
den ersten Eindruck richtig ist, aber bedeutet: **an ihm lässt sich die
Freigabe nicht üben**, und die Freigabe ist der Arbeitsgang, den die
Mutter am häufigsten braucht.

## Zwei Leserschaften

Die Trennung ist nicht Geschmack, sie steht im Datenmodell: `benutzer`
hat eine Spalte `verwalter`, und zwei MCP-Werkzeuge
(`sprachprofil_anpassen`, `sprache_einrichten`) werden nur Verwaltern
überhaupt angeboten.

| | Mutter (Verwalterin) | Kinder |
|---|---|---|
| Tut | pflegt Bestand, bindet den Chat an, gibt frei, setzt Buchstand und Ziele | lernt, liest Texte, fordert fehlende Wörter an |
| Muss verstehen | Datenmodell, Merkmalsbündel, Freigabe, Rolle der KI, Lehrgangsschranke | Abfrage, Bewertung, Tastatur, die vier Zahlen |
| Lernt wo | am Rechner, mit der Zeit es zu lesen | am Gerät, in der Minute vor dem Lernen |
| Erträgt | 10 Minuten je Kapitel | 2 Minuten, und keine zweite Chance |

Einschränkung, die die Schulung aussprechen muss: **im Heimnetz gibt es
keine Schlösser.** Man wählt sein Profil aus einer Liste, ohne Passwort
(`identitaet.py`: »das ist Absicht und reicht dort völlig«). Ein Kind
kann also in das Profil der Mutter wechseln und dort freigeben.
Deshalb gehört in die Kinderspur ein Satz dazu, was die Freigabe ist
und warum man dort nicht aus Langeweile alles bestätigt — nicht als
Verbot, sondern als Erklärung.

## Inventar: was erklärt werden müsste

Spalten: **heute** — wo es heute erklärt wird (R = Rundgang, A =
Anleitung, O = am Ort in der Oberfläche, — = nirgends).
**Rang** — unverzichtbar / nützlich / Feinheit.
**Wem** — M = Mutter, K = Kinder.

### Das Weltbild (der fehlende Unterbau)

| Punkt | heute | Rang | Wem |
|---|---|---|---|
| Lexem – Formen – Bedeutungen als drei Ebenen | — (nur `00-konzept.md`) | unverzichtbar | M, K knapp |
| Eine Bedeutung hat mehrere gültige Übersetzungen | A (»eine von mehreren genügt«) | unverzichtbar | M, K |
| Die abfragbare Einheit ist die **Aufgabe**, nicht das Wort | — | unverzichtbar | M |
| Aufgaben werden **erzeugt**, nicht gepflegt | — | unverzichtbar | M |
| Darum zählt die Tagesdosis Wörter, nicht Aufgaben | — (steht im Repo-Gedächtnis) | nützlich | M |
| Eine Sammlung ist ein Wortschatz, meist ein Lehrbuch | R, A | unverzichtbar | M, K |
| Alles hängt an der Sammlungskarte — die Kopfzeile hat nur drei Knöpfe | R (nebenbei) | unverzichtbar | M, K |

### Lernen

| Punkt | heute | Rang | Wem |
|---|---|---|---|
| Ablauf: Frage, Enter, Wertung, Enter | A, R | unverzichtbar | K, M |
| Fast richtig kostet nichts (erst der zweite Versuch zählt) | A, R | unverzichtbar | K |
| Keine Selbsteinschätzung — der Trainer wertet und begründet | A | unverzichtbar | K, M |
| Wertung von Hand ändern (Tasten 1–4), wird als Eingriff vermerkt | A (halb), README | nützlich | K |
| »Weiß ich nicht« ist die ehrliche Auskunft, kein Aufgeben | A, R | unverzichtbar | K |
| Tipp in drei Stufen, deckelt die Wertung auf »Schwer« | R (halb) | nützlich | K |
| Aussetzen, zurücksetzen, Termin selbst setzen | R (nur »Aussetzen«) | Feinheit | M |
| Die sechs Aufgabenarten und was sie verlangen | A | unverzichtbar | K |
| Ganze Reihe: Enter springt ins Feld, geprüft wird am Ende | A | nützlich | K |
| Artikel und Pronomen darf man mitschreiben, falscher Artikel zählt | A | nützlich | K |
| Akzente sind Hinweis, nicht Fehler | A | unverzichtbar | K |
| Verwechslung statt Tippfehler (»das ist die 2. Person«) | — (README) | nützlich | K, M |
| Fehlerarten werden benannt (b/d, Reihenfolge, Doppelkonsonant) | — | nützlich | M |
| Stamm wird aus dem Paradigma abgeleitet: `γράφ\|ουμε` | — | Feinheit | M |
| »Warum kommt das jetzt?« aufklappen, FSRS einsehbar | R, A | nützlich | K, M |
| Tagespensum ist eine Zahl, Rückstand keine Mauer | A | unverzichtbar | K |
| Runde: erst jedes Wort einmal, dann das zweite Mal | A | nützlich | K |
| Tagesgrenze ist der Kalendertag | — | Feinheit | M |
| Fehler wiederholen / frei üben ohne Plan | R | nützlich | K |
| Gezielt üben: nur Verben, nur Aorist, mit Anzahl daneben | A | nützlich | K, M |
| Gezielt üben gilt nur für diese Sitzung | A | nützlich | K |
| Legastheniemodus: Abstände, Aufdecken, Fehler benennen | — | nützlich | M |

### Tastatur und Schrift

| Punkt | heute | Rang | Wem |
|---|---|---|---|
| Griechisch ohne Umschalten tippen (`grafo` → γράφω) | A, R | unverzichtbar | K |
| Akzent: Taste Ö, dann Vokal — oder Vokal halten, dann Ziffer | A (nur Ö-Weg) | unverzichtbar | K |
| Schluss-ς liegt auf W | A | nützlich | K |
| Zeichenleiste unter dem Antwortfeld | README | nützlich | K |
| Tastaturhilfe `#/tastatur/el`, auch während der Abfrage aufklappbar | A | nützlich | K |
| Eigenes Systemlayout wird erkannt, die Umschrift hält sich heraus | A | Feinheit | M |

### Planen

| Punkt | heute | Rang | Wem |
|---|---|---|---|
| Lernziel = Ausschnitt mit Termin | R, A | nützlich | M, K |
| Der Trainer rechnet das Tagessoll und sagt, wenn das Pensum nicht reicht | A | nützlich | M |
| »Was käme dran?« mit Begründung, »Neu würfeln« | R, A | nützlich | M |
| Lehrgangsschranke: ab welcher Lektion welche Formgruppe | R, A | unverzichtbar | M |
| Der Vorschlag aus den Lektionsnamen bleibt ein Vorschlag | — | nützlich | M |
| Buchstand ist je Person, Zuordnung je Sammlung | — | nützlich | M |
| Ausgeblendet heißt wartet, nicht gelöscht | A | unverzichtbar | M, K |
| Bedeutungen sind von der Schranke nie betroffen | A | nützlich | M |

### Eingeben und pflegen (siehe eigenes Kapitel unten)

| Punkt | heute | Rang | Wem |
|---|---|---|---|
| Vier Wege hinein: Maske, Chat, Import, Beispielkurs | — | unverzichtbar | M |
| Merkmalsbündel statt Spaltennamen | — (nur `01-format`) | unverzichtbar | M |
| Formgruppe = die Tabelle, die zusammen gelernt wird | O (Einstellungen) | unverzichtbar | M |
| Standardgruppen gegen zuschaltbare | O | nützlich | M |
| Genau eine Grundform, für sie entsteht keine Formaufgabe | — | unverzichtbar | M |
| Die Eingabemaske baut sich aus den Formgruppen der Sprache | — | unverzichtbar | M |
| Handeintrag gilt sofort als geprüft, KI-Eintrag nicht | — | unverzichtbar | M |
| Lexemmerkmale: `klasse`, `genus`, griechisches `diathese = deponens` | — | Feinheit | M |
| Bedeutung gegen Übersetzung, `kontext` als Trennschärfe | — (nur `01-format`) | unverzichtbar | M |
| Gleiche Übersetzung auf zwei Wörtern — beide gelten | — | nützlich | M |
| Paradigmentafel im Wortschatz, ungeprüfte Zeilen anders dargestellt | O | unverzichtbar | M |
| Qualitätsprüfung und ihre Befunde | — | nützlich | M |
| Berichtigen ist besser als Löschen, der Lernstand hängt an der Form | — | unverzichtbar | M |
| Jede inhaltliche Änderung setzt die Freigabe zurück | — | unverzichtbar | M |

### Freigabe

| Punkt | heute | Rang | Wem |
|---|---|---|---|
| Ungeprüft wird nicht abgefragt — und warum | A, O | unverzichtbar | M, K |
| Die Freigabeansicht: je Lektion, Tafel, Zellen abwählbar | — | unverzichtbar | M |
| Übungssätze und Regeln warten mit | — | nützlich | M |
| Auf der Übersicht steht, was wartet | O | nützlich | M |
| Der Schalter »Ungeprüfte mitabfragen« hebt die Sperre auf | O | nützlich | M |
| Freigabe ist ein Arbeitsgang, keine Einstellung | — | unverzichtbar | M |

### Texte

| Punkt | heute | Rang | Wem |
|---|---|---|---|
| Text einwerfen oder hochladen, Leerzeilen trennen Abschnitte | R, A | nützlich | M, K |
| Deckung: vier Töpfe, und es wird nicht geraten | A | unverzichtbar | K, M |
| Jedes Wort anklickbar, zeigt den eigenen Eintrag samt Form | A | nützlich | K |
| »Wort für Wort« ist keine Übersetzung | — (CHANGELOG) | nützlich | K |
| Eigene Fassung sichert sich beim Tippen, kein Abschicken | A | nützlich | K |
| Übersetzungsvorschlag kommt nur über den Chat | — | nützlich | M |
| Beim langen Text entscheidet der Mensch, der Vergleich hilft nur | — | nützlich | K |
| Fehlende Wörter »für die KI merken«, Liste wartet, bis jemand fragt | A | unverzichtbar | K, M |

### Profile und Freigabe an Personen

| Punkt | heute | Rang | Wem |
|---|---|---|---|
| Profil ohne Passwort, Wechsel oben rechts | — | unverzichtbar | K, M |
| Lernstand ist immer persönlich, auch bei geteiltem Bestand | A (halb) | unverzichtbar | M |
| Sammlung freigeben mit Lese- oder Schreibrecht | — | nützlich | M |
| Freigegeben heißt nicht mitgelernt — das Häkchen je Karte | R, A | unverzichtbar | M, K |
| Verwalterin darf mehr (Sprachprofile) | — | Feinheit | M |

### Zugang und Anlage (nicht in die Schulung, aber irgendwohin)

| Punkt | heute | Rang | Wem |
|---|---|---|---|
| Token anlegen, wird einmal gezeigt, zurücknehmbar | A | unverzichtbar | M |
| Kopfzeile anklicken statt eintippen | A, Gedächtnis | unverzichtbar | M |
| Sperre nach acht Fehlversuchen | — | Feinheit | M |
| Zugang von außen, Cloudflare Access, Mailbindung | `BETRIEB-PRIVAT.md` | Feinheit | M |
| Als App auf den Startbildschirm | README | nützlich | K |
| Sicherung (WAL, `werkzeuge/sicherung.sh`) | README | unverzichtbar für den Betrieb | M |

## Lücke 1: Die Rolle der KI

Die Anleitung erklärt heute, *wie* man den Chat anschließt, und in
einem Abschnitt, *was er darf*. Was fehlt, ist das Bild davor — und
das ist der Teil, der Vertrauen trägt oder nicht.

### Was gesagt werden muss, in dieser Reihenfolge

**1. Der Trainer ruft nirgends an.** Keine Adresse, kein Schlüssel,
keine Kosten; `requirements.txt` kennt drei Pakete. Wo im Datensatz
`quelle = 'ki'` steht, ist das ein **Herkunftsvermerk** — wer hat das
eingetragen —, kein Aufruf. Das ist der eine Satz, den die Kinder von
diesem Kapitel behalten sollen, und der Grund, warum es ihn überhaupt
gibt (`02-geplant-ki-adapter.md`).

**2. Die Richtung ist umgekehrt, als man denkt.** Nicht der Trainer
fragt die KI, sondern das Chatprogramm klopft beim Trainer an. Es
verbindet sich mit `/mcp`, bekommt eine Liste von 38 Werkzeugen und
benutzt sie. Die Rechnung zahlt das bestehende Abonnement; jeder
Schritt wird von einem Menschen ausgelöst.

**3. Es arbeitet in deinem Namen.** Das Zugangsmerkmal hängt an einem
Profil. Alles, was darüber geschieht, geschieht auf dem Bestand dieser
Person und ist ihr zugeordnet. Daraus folgt der praktische Rat:
**genau ein Token, bei der Mutter.** Kinder brauchen keines, und die
Weitergabe des Merkmals ist dasselbe wie das Verleihen des Profils.

**4. Es sieht mehr, als man vermutet.** Nicht nur Vokabeln:
`lernstand_lesen` gibt zurück, was sitzt und woran es hakt — je Wort,
für diese Person. Wer ein Kinderprofil anbindet, schickt also auch
Leistungsdaten zum Anbieter des Chatprogramms. Für den geplanten
KI-Adapter ist »keine Lerndaten« eine der nicht verhandelbaren Regeln
(`02-geplant-ki-adapter.md`); über den MCP gilt sie **nicht
automatisch**. Das steht heute nirgends und gehört in die Schulung —
nicht als Warnung, sondern als Entscheidungsgrundlage.

**5. Freigeben kann es nicht — mit zwei Sternchen.** Das Werkzeug
`formen_bestaetigen` wurde absichtlich entfernt: »eine Bitte ist keine
Sperre«. Zwei Wege daneben sind aber offen, und die Schulung darf sie
nicht verschweigen, weil die Mutter sonst ein falsches Bild hat:

- `vokabel_anlegen` und `formen_ergaenzen` haben einen Schalter
  `als_geprueft`. In der Werkzeugbeschreibung steht »nur auf
  ausdrücklichen Wunsch der Benutzerin« — also genau die Bitte, die an
  anderer Stelle als untauglich verworfen wurde.
- Je Sammlung gibt es die Einstellung **»Ungeprüfte Formen
  mitabfragen«**. Ist sie an, ist die ganze Prüfung aus.

Richtig ist der Satz also: *Freigeben ist nichts, was im Vorbeigehen
passiert — es braucht entweder einen Menschen in der Freigabeansicht
oder eine ausdrückliche Anweisung von dir.* Besser wäre, den Schalter
`als_geprueft` zu entfernen; das ist eine Codeänderung und gehört nicht
in dieses Dokument (siehe Befunde am Ende).

**6. Warum ein Mensch prüfen muss.** Nicht »weil KI unzuverlässig
ist«, sondern konkret: eine **erfundene Form, die unbemerkt gepaukt
wird, ist schlimmer als eine fehlende** — man lernt sie, sie klingt
plausibel, und sie steht dann gegen das, was im Unterricht gilt. Bei
Grammatikregeln ist es schlimmer als bei Formen: eine falsche Regel
erklärt scheinbar und wird darum behalten.

**7. Wie man sie anweist.** Das ist der Teil, der heute nur als drei
Beispielsätze in der Anleitung steht. Er sollte als Muster aufgebaut
sein, nicht als Liste von Zaubersprüchen:

| Will man | sagt man | weil |
|---|---|---|
| eine Lektion eintragen | »Trag Lektion 5 ein, mit allen Formen. Mach zuerst einen Probelauf.« | Probelauf schreibt nichts, zeigt aber, was herauskäme |
| in einer neuen Sprache anfangen | »Sieh zuerst nach, welche Formgruppen diese Sammlung verlangt.« | sonst kommen Merkmale, die der Trainer mit 422 abweist |
| Übungssätze | »Prüf den Text vorher gegen meinen Wortschatz bis Lektion 20.« | ein Text mit dreißig unbekannten Wörtern ist keine Übung |
| die angeforderten Wörter | »Schau nach, welche Wörter ich angefordert habe, und trag sie ein.« | sie kommen mit dem Satz, in dem sie standen |
| etwas berichtigen | »Die Form `έγραψε` ist falsch beschriftet, stell sie richtig.« | Ändern erhält den Lernstand, Löschen vernichtet ihn |

Und was man **nicht** sagt: »lösch alles aus Lektion 3« — Löschen
verlangt die Nennung des Lemmas und meldet zurück, wie viele
Wiederholungen verlorengehen; steht dort eine Zahl über null, erst
hinsehen.

**8. Wenn es nicht geht.** Die drei Hürden stehen schon in der
Anleitung (Kopfzeile anklicken, neue Unterhaltung für neue Werkzeuge,
ungeprüft wird nicht abgefragt). Sie bleiben dort; in der Schulung
genügt ein Verweis.

### Form

Dieses Kapitel ist **Lesetext**, kein Rundgang: es gibt kaum etwas zu
zeigen, und der wichtigste Satz ist eine Verneinung. Länge etwa eine
Bildschirmseite. Für die Kinder davon genau zwei Sätze, in der
Kinderspur: der Trainer schickt nichts aus dem Haus, und wenn du
Wörter anforderst, wartet die Liste, bis jemand sie abholt.

## Lücke 2: Vokabeln eingeben, besonders Verben

Der schwierigste Teil, und er hat genau eine Hürde: man muss aufhören,
in Spalten zu denken.

### Der Aufbau des Kapitels

**1. Ein Wort ist ein Datensatz mit allem darin.** Nicht vierzig
Einzelkarten. `γράφω` mit Präsens, Aorist und Futur ist *ein* Eintrag
mit 18 Formen und zwei Übersetzungen.

**2. Eine Form ist Text plus Merkmalsbündel.** Hier steht der
Vergleich, auf den alles hinausläuft:

```
nicht:   praesens_1sg = "γράφω"
sondern: "γράφω" + {modus: indikativ, tempus: praesens,
                    person: 1, numerus: sg}
```

Der Grund ist kein Geschmack: Englisch braucht kein Genus, Griechisch
braucht Aspekt, Latein bräuchte den Ablativ. Mit Spalten wäre jede neue
Sprache eine Datenbankänderung; mit Bündeln ist sie ein Sprachprofil,
also Daten.

**3. Was daraus entsteht: Aufgaben.** Das ist der Satz, der die Mutter
von der Pflege zur Abfrage verbindet. 18 Formen ergeben 17
Formaufgaben — die Grundform zählt nicht mit —, dazu Bedeutung in beide
Richtungen. Wer ein Verb einträgt, legt keine Karten an; er legt
Material hin, aus dem der Trainer die Karten macht. Umgekehrt: eine
fehlende Zelle ist eine fehlende Aufgabe, und ein lückenhaftes
Paradigma verdirbt zusätzlich die Stammerkennung, aus der
`γράφ|ουμε` entsteht.

**4. Die Formgruppe ist die Tabelle, nicht die Zelle.** Eine
Formgruppe ist das, was zusammen gelernt wird: eine Zeit mit ihren
sechs Personen, oder eine Einzelform wie das Partizip. Griechisch hat
15 Verbgruppen, davon sechs voreingestellt. Der Trainer baut die
**Eingabemaske aus eben diesen Gruppen** — man füllt also nicht
Merkmale aus, sondern Felder, die schon beschriftet sind. Das ist die
gute Nachricht dieses Kapitels und sie steht heute nirgends.

**5. Dieselbe Sache von Hand, über den Chat, aus einer Datei.** Mit
dem einen Unterschied, der zählt: **von Hand eingetragene Formen
gelten sofort als geprüft, über den Chat eingetragene nicht.** Nicht
weil Handarbeit besser wäre, sondern weil beim Eintippen schon
jemand hingesehen hat.

**6. Die Fallen, in dieser Reihenfolge:**

- Genau **eine** Form trägt »Grundform«. Das ist die Zitierform, und
  für sie gibt es absichtlich keine eigene Formaufgabe — »bilde die
  Grundform von γράφω« wäre keine Frage.
- **Bedeutung gegen Übersetzung.** »schreiben« und »aufschreiben« sind
  zwei Übersetzungen *derselben* Bedeutung. »Bank« als Geldhaus und als
  Sitzbank sind zwei Bedeutungen, jede mit eigenem `kontext`. Falsch
  einsortiert heißt: der Trainer lässt die falsche Antwort gelten.
- **Mehrere gültige Übersetzungen sind der Normalfall.** Alle angeben,
  nicht die beste auswählen.
- **Zwei Wörter mit derselben Übersetzung.** »klein« führt auf μικρός
  *und* κοντός; beide gelten dann als richtig. Wer das nicht will,
  setzt `kontext` (»klein, Körpergröße«) — dann ist die Frage
  eindeutig und beide werden wirklich geübt.
- **Unbekannte Merkmale werden abgewiesen**, nicht stillschweigend
  gespeichert. Ein `tempuss` ergibt einen Fehler statt einer Form, die
  nie abgefragt wird. Eigenes geht mit dem Vorsatz `x_`.
- Beim Verb gibt es Merkmale des **Wortes**, nicht der Form: `klasse`
  (Konjugationsklasse, Ablautreihe) und für griechische Deponentien
  `diathese = deponens` — sonst meldet die Qualitätsprüfung
  Aktivformen als fehlend, die es bei θυμάμαι gar nicht gibt.

**7. Ansehen und freigeben.** Die Paradigmentafel im Wortschatz zeigt
die Formen so, wie sie im Buch stehen, Zelle für Zelle, ungeprüfte
anders dargestellt — eine leere oder doppelt besetzte Zelle sieht man
auf einen Blick, eine Liste in Eingabereihenfolge kann man nicht
prüfen. Die Freigabeansicht macht dasselbe je Lektion, mit abwählbaren
Zellen und den Befunden der Qualitätsprüfung daneben.

**8. Berichtigen statt löschen.** An jeder Form hängt ein Lernstand.
Eine falsch beschriftete Form stellt man richtig; die Aufgaben hängen
am Merkmalsbündel, nicht an der Zeile, und der Lernstand bleibt.
Umgekehrt: jede inhaltliche Änderung nimmt die Freigabe zurück, weil
das Geänderte nicht mehr das ist, was jemand angesehen hat.

**9. Und wenn es zu viel wird:** die Lehrgangsschranke. Hier gehört
die echte Zahl hin, weil sie das Problem erklärt: im griechischen
Bestand stehen 6971 Formaufgaben, davon 832 Präsens und rund 2900
Aorist, Futur und Passiv. Wer bei Lektion 20 ist, hat den Aorist noch
nicht gehabt — er kommt aus Lektion 39. Die Schranke nimmt ihn heraus,
bis man dort ankommt.

### Form

Dieses Kapitel ist **Übung am Beispiel**, nicht Lesetext. Es braucht
etwas, woran man es tut, und es braucht einen Fall mit ungeprüften
Formen. Dafür müsste der Übungskurs einen zweiten Teil bekommen (siehe
Empfehlung).

## Empfehlung zur Form

Kurz: **die vier Rundgänge bleiben, bekommen aber eine engere Aufgabe,
und daneben entsteht ein Lehrgang aus Kapiteln in der Anleitung, jedes
mit einer Handlung am Übungskurs. Kein Video.**

### Warum nicht einfach längere Rundgänge

Die Blase trägt drei Sätze. Das ist keine Einstellung, sondern eine
Eigenschaft der Form: sie liegt über der Anwendung, verdeckt also
gerade das, was sie erklärt, und sie wird mit jedem Satz schwerer zu
platzieren — die Kommentare in `fuehrung.js` erzählen genau diese
Geschichte (Blase mitten auf dem erklärten Element, Knöpfe außerhalb
des Bildschirms, Rundgang nicht mehr verlassbar). Was dort nicht
hineinpasst, darf man nicht hineinzwingen.

Ein Rundgang kann außerdem nur zeigen, was **da** ist. Er kann nicht
sagen, was eine Aufgabe ist — das steht nirgends auf dem Bildschirm.

**Also:** Rundgänge sind Orientierung. Höchstens sechs Schritte, jeder
Text unter 300 Zeichen, jeder zeigt auf ein Ding. Kein Rundgang
erklärt ein Konzept. Zwei fehlen heute und wären je zwei Minuten:
*Formen eintragen* (durch die Maske) und *Freigabe* (durch die
Freigabeansicht) — in beiden Fällen ist das Erklärte wirklich auf dem
Bildschirm.

### Warum Kapitel in der Anleitung und nicht ein neues Werkzeug

Der Ort ist schon da (`#/hilfe`), er ist aus der Fußzeile und den
Einstellungen verlinkt, und er ist Text — also wartbar ohne Bauschritt
und durchsuchbar mit Strg+F. Die Änderung ist nicht der Ort, sondern
die **Form des Ortes**: heute elf zugeklappte Abschnitte
gleichberechtigt untereinander. Daraus würde:

- **oben eine Spur**, zwei Stück (»Ich will lernen« / »Ich pflege den
  Bestand«), je als numerierte Kapitelliste mit Dauer;
- **jedes Kapitel eine eigene Seite** (`#/hilfe/lernen-2`), nicht ein
  Ausklapper. Ein Kapitel, das man offen hat, soll die anderen nicht
  daneben zeigen;
- **am Ende jedes Kapitels genau eine Handlung** am Übungskurs, mit
  Knopf dorthin;
- **Fortschritt gemerkt**, mit derselben Mechanik wie die Rundgänge
  (`localStorage`, eine Liste gesehener Kennungen) — damit auf der
  Übersicht »Kapitel 3 von 6« stehen kann und nicht nur »Anleitung«.

Die bestehenden Abschnitte werden dabei nicht weggeworfen; sie sind
gut und werden die Kapitelkörper. Was fehlt, ist das Gerüst und die
drei neuen Kapitel (Weltbild, KI, Formen eintragen).

### Warum der Übungskurs der Hebel ist

Er ist schon gebaut, er ist Englisch (»damit man sich auf die Bedienung
statt auf die Vokabel konzentriert«), und er bringt für jede Funktion
einen Fall mit. Er ist aber **durchgehend freigegeben**, und damit
fehlt genau der Gegenstand, an dem die Pflege-Spur üben müsste.

Empfehlung: ein **zweiter Teil im Kurs**, zwei oder drei Wörter, als
`quelle = 'ki'` und ungeprüft angelegt, davon eines mit einem
absichtlichen Fehler — etwa `to go` mit `goed` als Präteritum. Dann
hat das Kapitel »Freigabe« etwas zu tun, das Kapitel »Berichtigen
statt löschen« einen echten Fall, und die Qualitätsprüfung zeigt ihren
Befund an etwas, das wirklich falsch ist. Das ist eine kleine
Ergänzung an `beispielkurs.py` und ersetzt drei Absätze Erklärung.

### Warum kein Video

Nicht wegen des Aufwands, sondern wegen der Haltbarkeit. Der
CHANGELOG führt für den 15.11.2026 allein sieben Änderungen an der
Oberfläche, darunter zwei an den Rundgängen selbst. Ein Film zeigt
Knöpfe, die es in drei Wochen anders gibt, und niemand schneidet ihn
nach. Text in `ansicht_hilfe.js` wird beim Ändern der Oberfläche
mitgeändert, weil er daneben liegt; eine Videodatei wird es nicht. Für
genau einen Zweck wäre bewegtes Bild überlegen — das Tippen mit der
Umschrift (`grafo` → γράφω) und die Akzentwahl durch Halten. Dafür
genügt eine kleine Schleife ohne Ton auf der Tastaturseite, kein
Video mit Erzähler.

### Reihenfolge, und warum sie zwingend ist

```
Weltbild (Lexem/Formen/Bedeutungen → Aufgaben)
   ├─→ Lernen: Abfrage, Bewertung, Tipp          (Kinder beginnen hier)
   │      └─→ Tastatur                 └─→ Was heute drankommt
   │                                          └─→ Ziele, Lehrgangsschranke
   └─→ Pflege: Merkmale und Formgruppen
          ├─→ Eintragen von Hand
          │      └─→ Freigabe ──→ Berichtigen und Löschen
          └─→ Die Rolle der KI ──→ Chat anschließen ──→ Texte und Wortwünsche
```

Zwei Abhängigkeiten sind hart: **Freigabe setzt Merkmale voraus** (man
kann eine Tafel nicht prüfen, deren Zellen man nicht liest), und **die
KI-Kapitel setzen die Freigabe voraus** (sonst ist »sie darf nicht
freigeben« eine Regel ohne Gegenstand). Alles andere ist tauschbar.

Die Kinder brauchen das Weltbild nur als einen Absatz: *ein Wort hat
Formen, und jede Form ist eine eigene Frage — darum sind es so viele.*

### Länge

Gemessen daran, was hier schon beobachtet wurde (»eine Tour über
fünfzehn Funktionen hat niemand zu Ende gesehen«):

| Form | Obergrenze | Abbruchstelle |
|---|---|---|
| Rundgangsschritt | 300 Zeichen | — |
| Rundgang | 6 Schritte, 2 Minuten | nach Schritt 7 |
| Kapitel Kinderspur | 1 Bildschirmseite, 3 Minuten | beim zweiten Bildlauf |
| Kapitel Pflegespur | 2 Bildschirmseiten, 8 Minuten | wenn kein Knopf vorkommt |
| Spur gesamt | 3 bzw. 6 Kapitel | — |

Eine Regel, die sich aus den Rundgängen übertragen lässt und die
wichtigste ist: **jedes Stück endet an einer Stelle, an der man etwas
tun will.** Nicht mit einer Zusammenfassung.

## Kapitelplan

### Spur »Ich will lernen« (Kinder, drei Kapitel, zusammen 8 Minuten)

| | Kapitel | Inhalt | endet mit |
|---|---|---|---|
| 1 | Wie der Trainer fragt | Weltbild in einem Absatz; Ablauf; fast richtig; Weiß-ich-nicht; Tipp | »Lernen« im Übungskurs, fünf Fragen |
| 2 | Tippen und Antworten | Umschrift, Akzent durch Halten, ς auf W, Zeichenleiste, Artikel mitschreiben | fünf Fragen auf Griechisch |
| 3 | Was heute drankommt | die vier Zahlen, Pensum und Rückstand, Runde, »warum kommt das jetzt« | Aufklapper in der Abfrage öffnen |

Dazu, nicht als Kapitel, sondern als zwei Sätze an passender Stelle:
der Trainer schickt nichts aus dem Haus; die angeforderten Wörter
warten, bis jemand sie abholt.

### Spur »Ich pflege den Bestand« (Mutter, sechs Kapitel, zusammen 45 Minuten)

| | Kapitel | Inhalt | endet mit |
|---|---|---|---|
| 1 | Wie der Trainer die Vokabeln sieht | drei Ebenen; Aufgaben werden erzeugt; die Rechnung 18 Formen → 17 Aufgaben | Paradigmentafel von `to go` ansehen |
| 2 | Merkmale und Formgruppen | Bündel gegen Spalten; Formgruppe als Tabelle; Standard gegen zuschaltbar; die Maske kommt daraus | `to drink` von Hand eintragen |
| 3 | Freigabe | ungeprüft wird nicht abgefragt; die Ansicht je Lektion; Befunde; der Schalter, der alles aufhebt | den ungeprüften Teil des Kurses durchgehen |
| 4 | Berichtigen und löschen | Lernstand hängt an der Form; Änderung nimmt die Freigabe zurück; Löschen verlangt den Namen | `goed` richtigstellen |
| 5 | Die Rolle der KI | die acht Punkte oben | Probelauf im Chat, ohne zu schreiben |
| 6 | Ziele und das Lehrwerk | Lernziel mit Termin; Buchstand; Vorschlag aus Lektionsnamen; ausgeblendet heißt wartet | Buchstand im Kurs auf 3 setzen und sehen, was wegfällt |

Die Kapitel 1 bis 4 sind die Pflicht. 5 braucht man erst, wenn der
Chat angebunden wird; 6 erst, wenn eine echte Sammlung mit Lektionen
da ist. Diese Staffelung sollte dastehen — sonst liest man sechs
Kapitel, von denen zwei gerade nicht gebraucht werden, und bricht in
der Mitte ab.

## Erklärung am Ort statt in der Schulung

Die Regel: **was man genau dann wissen muss, wenn man vor dem Knopf
steht, gehört an den Knopf.** Eine Schulung, die es vorwegnimmt, wird
vergessen; eine Erklärung am Ort wirkt beim zehnten Mal noch. Was heute
am Ort steht, ist teils vorbildlich (der Schalter »Ungeprüfte Formen
mitabfragen« nennt in zwei Sätzen Wirkung und Grund). Es fehlt an sechs
Stellen:

| Stelle | ein Satz, der dort fehlt |
|---|---|
| Eingabemaske, über den Formfeldern | »Diese Felder kommen aus den Formgruppen deiner Sprache. Leer lassen ist erlaubt — nur die ausgefüllten werden abgefragt.« |
| Die Marke »ungeprüft« in der Tafel | beim Antippen: warum sie da ist und wo man freigibt |
| »Für die KI merken« | »Es wird nichts verschickt. Das Wort steht auf einer Liste, bis dein Chatprogramm danach fragt.« |
| Lehrgangsschranke, nach dem Eintragen | »Damit bleiben gerade N Formaufgaben draußen« — die Wirkung in Zahlen, nicht als Versprechen |
| Löschknopf bei Wort und Form | die Zahl der Wiederholungen, die verlorengehen, **vor** der Bestätigung |
| Profilwechsel | »Lernstände sind je Profil. Wenn du hier das falsche wählst, landet deine Antwort bei jemand anderem.« |

Umgekehrt gehört **nichts** davon in die Schulung, was nur einmal
geschieht und bei dem jemand daneben sitzt: Tunnel, Access,
Sicherungsskript, Sprachprofile anlegen. Das steht richtig in
`README.md` und `BETRIEB-PRIVAT.md`.

## Befunde am Rand

Beim Lesen des Bestands aufgefallen; keine Schulungsfragen, aber sie
beeinflussen, was die Schulung behaupten darf. Nichts davon ist
geändert.

1. **`als_geprueft` ist eine Bitte, keine Sperre.**
   `vokabel_anlegen` und `formen_ergaenzen` nehmen den Schalter an.
   Damit kann ein Agent seine eigenen Einträge freigeben — genau das,
   wofür `formen_bestaetigen` entfernt wurde. Solange er existiert, ist
   »freigeben kann es nicht« in der Anleitung zu stark formuliert.
2. **`formen_bestaetigen` wird noch dreimal genannt**, obwohl es das
   Werkzeug nicht mehr gibt: in `README.md` (Werkzeugtabelle), im
   Hinweistext von `vokabel_anlegen` und in der Beschreibung von
   `vokabel_lesen` (»die Kennungen braucht man für
   formen_bestaetigen«). Die KI liest diese Texte und sucht dann etwas,
   das es nicht gibt.
3. **Der Lernstand geht über den MCP hinaus.** `lernstand_lesen` ist
   richtig und nützlich, aber für ein Kinderprofil bedeutet die
   Anbindung, dass Leistungsdaten das Haus verlassen. Für den geplanten
   Adapter ist das ausdrücklich verboten; für den MCP steht es nirgends.
4. **Der Übungskurs kann die Freigabe nicht zeigen**, weil er
   vollständig freigegeben angelegt wird. Siehe Empfehlung oben.

## Was ich nicht geprüft habe

- **Ob die Kinder die Rundgänge überhaupt angesehen haben** und woran
  sie hängengeblieben sind. Dieses Konzept schließt aus dem Code auf
  die Lücken, nicht aus Beobachtung. Eine halbe Stunde Zusehen beim
  ersten Lernen wiegt mehr als die Hälfte dieses Dokuments.
- **Den echten Bestand.** Die Zahlen zum Griechischen (6971
  Formaufgaben, 832 Präsens, Aorist ab Lektion 39) stammen aus dem
  Kommentar in `lehrgang.py` und dem Projektgedächtnis; die Datenbank
  in `daten/` ist der Beispielbestand mit vier Sammlungen und 73
  Formen.
- **Die Oberfläche im Betrieb.** Ich habe den Code gelesen, nicht den
  Trainer bedient. Wo ich schreibe, etwas »stehe nirgends«, heißt das:
  ich habe es in `ansicht_hilfe.js`, `fuehrung.js` und den
  Beschriftungen der Ansichten nicht gefunden. Ein Hinweis, der nur in
  einem `title`-Attribut steht, kann mir entgangen sein.
- **Wie lange die Kapitel wirklich brauchen.** Die Minutenangaben sind
  geschätzt, nach Textlänge, nicht gemessen.
