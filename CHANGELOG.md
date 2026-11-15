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

### Akzente wieder durch Gedrückthalten

Zu merken war: »Da konnte man, wenn man länger auf einem Vokal blieb,
mit den Nummerntasten den Akzent wählen. Jetzt wird der Vokal mehrfach
ausgegeben.«

Beides stimmte, und beides kam von der Umschrift: sie fängt jede Taste
ab und setzt das Zeichen selbst. Jede Wiederholung beim Halten schrieb
dadurch ein weiteres Zeichen — und das Auswahlfenster des
Betriebssystems konnte gar nicht erscheinen, weil das Zeichen nie vom
System kam.

Jetzt macht die Umschrift die Auswahl selbst, mit derselben Bedienung:
Vokal halten, dann die Ziffer. Bei ι stehen ι, ί, ϊ und ΐ zur Wahl;
anklicken geht auch, weil es auf dem Telefon keine Zifferntasten gibt.
Und eine gehaltene Taste schreibt nur noch ein Zeichen.

### Übersetzungsvorschlag und »Wort für Wort«

Zu merken war die Frage: »Einen Übersetzungsvorschlag kann man sich
vermutlich wieder nur von der angeschlossenen KI holen?«

Für eine richtige Übersetzung ja — der Trainer hat keine
Übersetzungsmaschine und soll keine erfinden. Nur konnte die KI es
bisher auch nicht: der Platz dafür stand im Schema, die Oberfläche
zeigte ihn an, aber es gab keinen Weg, ihn zu füllen. Eine halbe
Funktion, die aussah wie eine ganze. Jetzt gibt es `text_lesen` und
`text_uebersetzen`; der Vorschlag erscheint unter dem Abschnitt als
»Übersetzungsvorschlag vergleichen« und lässt die eigene Fassung
unangetastet.

Ohne KI gibt es neu **Wort für Wort**: unter jedem Abschnitt die
Bedeutungen aus dem eigenen Wortschatz, aufklappbar. Das ist
ausdrücklich keine Übersetzung — es steht auch so da —, aber es
genügt, um beim Entziffern nicht an jedem zweiten Wort
hängenzubleiben.

### Rundgänge: ausblendbar, und mit einem Weg zurück

Drei Dinge aus dem ersten Durchlauf:

Die Karte auf der Übersicht lässt sich **ausblenden** — ein Knopf
darunter. Über die Anleitung holt man sie zurück.

Ein Rundgang **endet auf der Übersicht**, nicht dort, wo er gerade
war. Er führt ja in die Einstellungen oder in eine laufende Abfrage,
und von dort muss man sich sonst erst wieder zurechtfinden.

Und in der laufenden Abfrage steht jetzt **»Schluss für heute«**. Der
Weg hinaus führte bisher über den Pfeil in der Kopfzeile oder über das
Menü — beides sieht nicht nach Ausgang aus. Es geht dabei nichts
verloren: jede Antwort ist längst gespeichert.

### Geführte Rundgänge und ein englischer Übungskurs

Beim ersten Öffnen steht oben eine Karte mit vier kurzen Rundgängen —
**Erste Schritte**, **Eine Abfrage von innen**, **Planen: Ziele und
Lehrwerk**, **Texte lesen und übersetzen**. Jeder dauert zwei bis drei
Minuten und hört an einer Stelle auf, an der man etwas ausprobieren
kann. Die Anwendung bleibt währenddessen bedienbar; wer mitten im
Rundgang etwas antippen will, darf das. Über die Anleitung sind sie
jederzeit wieder erreichbar.

Vier statt einer, weil eine Tour über fünfzehn Funktionen niemand zu
Ende sieht. Die Karte verschwindet, sobald alle einmal gesehen sind —
ein Hinweis, der nach dem zwanzigsten Mal noch dasteht, wird zu
Hintergrundrauschen.

Dazu ein **kleiner englischer Übungskurs** auf Knopfdruck: 17 Wörter,
fünf Lektionen, Verben mit Simple past, unregelmäßige Plurale,
gesteigerte Adjektive, zwei Sätze, ein Lesetext und eine
Grammatikregel. Er ist nicht nach Nützlichkeit fürs Englischlernen
zusammengestellt, sondern danach, dass jede Funktion darin etwas zu
zeigen hat — auch die Lektionsschranke, deren Zuordnung gleich
mitkommt. Alles ist freigegeben, man kann sofort loslegen, und löschen
lässt er sich wie jede andere Sammlung.

### Ein Lernziel hält sich von selbst an seine Lektionen

Zu merken war: »bei meinem Lernziel wird wieder der Aorist abgefragt,
obwohl er gar nicht für diese Lektionen freigeschaltet wurde«.

Zu Recht. Die Zuordnung war eingetragen, die eigene Lektionsnummer
nicht — und ohne die tat die Schranke nichts. Dieselbe Auskunft
zweimal zu verlangen war der Fehler: ein Ziel auf Lektion 2 und 3 sagt
schon, wie weit jemand ist. Die höchste Lektion im Umfang gilt jetzt
als Grenze, ganz ohne zweite Eingabe. Dasselbe beim »mitlernen bis
Lektion N« im normalen Weg.

Wer eine Formgruppe ausdrücklich in den Umfang schreibt, bekommt sie
trotzdem — sonst wäre ein Ziel »nur Aorist, Lektion 1 bis 2« stumm
leer.

Und die Stelle zum Eintragen war nicht zu finden: sie lag zweieinhalb
Bildschirme tief hinter sechsundzwanzig Ankreuzfeldern. Sie steht
jetzt oben, und auf jeder Sammlungskarte steht eine Zeile »Lehrwerk: …
· Lektion eintragen«, die direkt dorthin springt. Eine gespeicherte
Zuordnung ohne eigene Lektion sagt außerdem, dass sie noch nichts tut.

### Die KI kann die Lektionszuordnung übernehmen

Zwei neue Werkzeuge für das angebundene Chatprogramm:
`lehrgang_lesen` und `lehrgang_zuordnen`. Der Namensvorschlag des
Trainers ist reine Wortsuche; ein Chat versteht dagegen, dass
»Konjunktiv und Futur (να / θα)« zwei Formgruppen auf einmal einführt.

Was dabei NICHT hilft und wovor die Werkzeugbeschreibung ausdrücklich
warnt: die Formen der Vokabeln. Nachgemessen erschien jede Formgruppe
ab Lektion 1, weil zu fast jedem Wort das volle Paradigma eingetragen
ist.

### Die Anleitung kennt den Trainer wieder

Sie hatte zwei Abschnitte — wie eine Abfrage abläuft und wie man sein
Chatprogramm anschließt — und das war schon länger nicht mehr alles.
Weder Lernziele noch Tagespensum standen darin, von den Sachen von
heute ganz zu schweigen. Eine Funktion, die niemand findet, gibt es
nicht.

Sechs Abschnitte dazu: was heute drankommt (Pensum, Rückstand, die
Runde), Lernziele und Blöcke samt »Neu würfeln«, gezielt üben, »nur
das, was ihr schon hattet«, welche Sammlungen mitgelernt werden, und
Texte lesen und übersetzen. Dazu im Teil über das Chatprogramm ein
Absatz darüber, dass es die angeforderten Wörter abrufen und selbst
Texte hinlegen kann.

### Gezielt üben: Verben, Adjektive, eine einzelne Zeitform

Zu merken war: »dann brauchen wir noch ein paar mehr Lernmodi: Verben
lernen, Zeiten lernen, bestimmte Worttypen, k.A. Adjektive oder so«.

Auf jeder Sammlungskarte gibt es den Knopf **Gezielt üben**. Dahinter
stehen alle Wortarten, die wirklich in der Sammlung vorkommen — mit
Zahlen daneben, damit man sieht, ob sich ein Ausschnitt lohnt — und
darunter jede Zeit und jede Formentabelle einzeln.

Das ist freies Üben: keine Tagesdosis, es geht, solange man mag. Mit
dem Terminplan kam sonst »Nichts zu tun«, sobald die Tagesdosis an
neuen Wörtern verbraucht war und zufällig nichts aus dem gewählten
Ausschnitt fällig stand — gemessen: 737 Adjektivaufgaben, und die
Abfrage lieferte null. Der Lernstand zählt ganz normal mit.

Der Modus gilt für die Sitzung und wird nicht gespeichert: wer heute
nur Verben übt, soll morgen nicht unbemerkt darin hängen.

Dieselben Ausschnitte gibt es jetzt auch als Lernziel — die Wortarten
fehlten dort, obwohl der Umfang sie längst konnte.

### Keine Zeitform, die das Lehrwerk noch nicht eingeführt hat

Zu merken war: »bei den Anfängerkapiteln, die ich mir gerade ansehe,
habe ich noch gar nicht alle Zeitformen gelernt«. Die Abfrage bot
Aorist an, obwohl das Lernziel auf Lektion 2 stand.

Nachgemessen im griechischen Bestand: von 10751 Aufgaben waren 6971
Formenbilden, davon nur 832 Präsens — rund 2900 lagen in Aorist, Futur
und den Passiven. Alles im selben Topf, aus dem die Tagesdosis zieht.

Unter **Einstellungen** einer Sammlung steht jetzt »Wo stehst du im
Lehrwerk?«. Dort trägt man ein, ab welcher Lektion eine Zeitform gilt —
vorgeschlagen aus den Lektionsnamen, denn die sagen es selbst (»39
Aorist I«, »45 Passiv Präsens«) — und darunter die eigene Lektion. Was
später kommt, bleibt draußen, bis man dort ankommt; dann kommt es von
selbst, ohne dass man etwas umstellt.

Drei Dinge dabei mit Absicht:

- Der Vorschlag wird **nicht** von selbst angewandt. Namensraten darf
  keinen Stoff wegnehmen; wo ein Teil des Namens in keiner Lektion
  vorkommt, steht das daneben.
- Ohne eigene Lektionsangabe ändert sich **nichts**. Wer nichts
  einstellt, bekommt alles wie bisher.
- Bedeutungs- und Genusaufgaben trifft die Schranke nie — eine Vokabel
  kann man lernen, bevor man ihre Zeiten kennt.

Der Lernstand bleibt in jedem Fall erhalten; Ausblenden heißt warten.

### Lernziel bearbeiten: jetzt auch Lektionen, Zeiten und Abfragearten

Zu merken war: »bei den Lernzielen sollte man auch einstellen können,
welche Tempi und welche Abfragen dort erfolgen«.

Das Formular zum ANLEGEN konnte das längst, das zum Bearbeiten nicht.
Wer sich vertat oder weiterkam, musste das Ziel wegwerfen und neu
anlegen. Jetzt stehen die drei Mehrfachwahlen auch dort, mit dem
vorgewählt, was gerade gilt.

### Die Leiste bei der Freigabe wurde von den Formzeilen durchkreuzt

Zu merken war: unten über den Knöpfen »Weitere laden« und »Lektion
freigeben« lagen Teile der Formtabelle, der linke Knopf war halb
verdeckt.

Die erste Tabellenspalte klebt beim seitlichen Rollen (damit das Wort
stehen bleibt) und hat dafür eine Lage über dem Fluss. Die Leiste hatte
gar keine Angabe und lag damit darunter. Sie liegt jetzt dazwischen:
über der Tabelle, unter der Kopfzeile.

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
