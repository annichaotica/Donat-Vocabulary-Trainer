# Schulungskonzept

*Stand 15.11.2026. Konzept, nicht der Schulungstext selbst. Hier steht,
was erklärt werden muss, in welcher Reihenfolge, in welcher Form und
warum gerade so. Gelesen wurde dafür der Code, nicht die Doku:
15 Ansichten, 116 HTTP-Routen, 38 MCP-Werkzeuge.*

## Der Anlass

»*mir sind diese vier rundgänge zu kurz und zu oberflächlich. außerdem
fehlt völlig etwas zur rolle der ki, wie man verben eingibt und so
weiter*«

Beides trifft zu, und die beiden Hälften haben verschiedene Ursachen.

**Zu kurz** ist messbar: 15 Schritte für 15 Ansichten, 38 MCP-Werkzeuge
und 23 Tabellen. Eine Blase hält drei Sätze; alles, was mehr braucht,
kann ein Rundgang nicht tragen. Das war beim Bau Absicht (»eine Tour
über fünfzehn Funktionen hat niemand zu Ende gesehen«) und ist als
Entscheidung richtig — nur fehlt daneben die Form, die das Längere
trägt.

**Zu oberflächlich** ist nicht die Länge, sondern die Ebene. Die
Rundgänge und die Anleitung erklären, *wo etwas steht* und *was ein
Knopf tut*. Sie erklären nicht, *wie der Trainer denkt*. Beispiel: der
Schritt »Die vier Zahlen« erklärt fällig, verlernt, neu, sitzt — aber
nicht, dass gezählt wird, was eine **Aufgabe** ist, und dass ein
griechisches Verb mit drei Zeiten siebzehn davon hat. Wer das nicht
weiß, hält die Zahl 6971 für einen Fehler.

Dieser Unterbau fehlt überall, und an ihm hängen die beiden genannten
Lücken: wer das Datenmodell nicht kennt, kann weder Verben eingeben
noch verstehen, was die Freigabe eigentlich freigibt — und damit auch
nicht, warum die KI sie nicht selbst machen darf.

## Was heute schon erklärt wird

| Ort | Umfang | Was er leistet |
|---|---|---|
| `fuehrung.js`, vier Rundgänge | 15 Schritte, angegeben 9 Minuten | Orientierung: wo liegt was, welcher Knopf tut was |
| `ansicht_hilfe.js`, Teil »Lernen« | 10 zugeklappte Abschnitte | Nachschlagewerk zu den Lernregeln, gut geschrieben |
| `ansicht_hilfe.js`, Teil »Chatprogramm« | 5 Abschnitte, 3 Schritte | Anschließen des Konnektors, die Kopfzeilenfalle |
| `tastatur.js` | eigene Seite `#/tastatur/el` | Belegung, Merkhinweise, Anleitung je Betriebssystem, Probefeld |
| `beispielkurs.py` | 18 Wörter, 2 Sätze, 1 Text, 1 Regel, 5 Lektionen | Etwas zum Anfassen — aber ohne Anleitung, was man damit tun soll |
| Texte am Ort | verstreut | teils vorbildlich, teils fehlend, siehe unten |
| `00-konzept.md`, `01-format-…md` | 200 + 636 Zeilen | für Entwicklung und für die KI, nicht für die Benutzerin |

Drei Befunde dazu:

**Die Anleitung ist ein Nachschlagewerk, das als Schulung gelesen
werden müsste.** Zehn zugeklappte `details`-Abschnitte. Zugeklappt
öffnet man, wenn man ein Problem hat — nicht, bevor man eines hat.
Genau die Dinge, die man *vorher* wissen muss (fast richtig kostet
nichts, Weiß-ich-nicht ist keine Niederlage, der Rückstand ist keine
Mauer), stehen hinter einem Dreieck.

**Der Übungskurs ist gebaut, aber nicht benutzt.** Er bringt
ausdrücklich für jede Funktion einen Fall mit — Lektionsnamen für die
Schranke, `child/children` als echte Formaufgabe, `read/read/read` als
Fall für »das musst du wirklich wissen«. Nirgends steht, dass man ihn
dafür verwenden soll. Er ist vollständig freigegeben angelegt, was für
den ersten Eindruck richtig ist, aber bedeutet: **an ihm lässt sich die
Freigabe nicht üben**, und die Freigabe ist der Arbeitsgang, den die
Mutter am häufigsten braucht.

**Die Tastaturseite ist der Maßstab.** Sie macht alles richtig, was
einer Schulung guttut: ein Bild, Suchfeld, Merkhinweise in einem Satz
(»Y und Z sind auf deutscher Tastatur vertauscht«), ein Probefeld, das
mitlernt, und je Betriebssystem eine eigene Anleitung, bei der die des
eigenen Geräts schon offen steht. Wo die neuen Kapitel sich an etwas
halten sollen, dann an dieser Seite.

## Zwei Leserschaften

Die Trennung ist nicht Geschmack, sie steht im Datenmodell: `benutzer`
hat eine Spalte `verwalter`, und zwei MCP-Werkzeuge
(`sprachprofil_anpassen`, `sprache_einrichten`) werden Nichtverwaltern
gar nicht angeboten.

| | Mutter (Verwalterin) | Kinder |
|---|---|---|
| Tut | pflegt Bestand, bindet den Chat an, gibt frei, setzt Buchstand und Ziele | lernt, liest Texte, fordert fehlende Wörter an |
| Muss verstehen | Datenmodell, Merkmalsbündel, Freigabe, Rolle der KI, Lehrgangsschranke | Abfrage, Bewertung, Tastatur, die vier Zahlen |
| Lernt wo | am Rechner, mit der Zeit, es zu lesen | am Gerät, in der Minute vor dem Lernen |
| Erträgt | 10 Minuten je Kapitel | 2 Minuten, und keine zweite Chance |

Zwei Einschränkungen, die die Schulung aussprechen muss:

**Im Heimnetz gibt es keine Schlösser.** Man wählt sein Profil aus
einer Liste, ohne Passwort (`identitaet.py`: »das ist Absicht und
reicht dort völlig«). Ein Kind kann also in das Profil der Mutter
wechseln und dort freigeben. Deshalb gehört in die Kinderspur ein Satz
dazu, was die Freigabe ist und warum man dort nicht aus Langeweile
alles bestätigt — nicht als Verbot, sondern als Erklärung.

**Die Grenze läuft nicht entlang der Ansichten.** Die Kinder brauchen
aus den Einstellungen das Tagespensum und den Legastheniemodus, aus den
Lernzielen den Knopf »Block starten«, aus dem Wortschatz das
Nachschlagen eines Wortes. Umgekehrt braucht die Mutter die Abfrage
selbst, um zu sehen, was ihre Einträge anrichten. Die Spuren teilen
also Themen, nicht Bildschirme.

## Was man von selbst nicht findet

Das ist der Teil, der die Schulung rechtfertigt. Jede Stelle hier ist
eine, an der die Oberfläche richtig arbeitet, aber stillschweigend —
und wo das Missverständnis vorhersehbar ist.

1. **Ungeprüftes wird nicht abgefragt.** Alles, was Chat oder Import
   einträgt — Formen, Übungssätze, Grammatikregeln —, ist stumm, bis es
   bestätigt wurde. Wer das nicht weiß, sucht die gerade eingetragene
   Lektion vergeblich. Es verrät nur eine Warnmarke auf der
   Sammlungskarte.
2. **Freigegeben heißt nicht mitgelernt.** Das Häkchen »Wird allgemein
   mitgelernt« steckt klein auf der Karte. Ohne es kommt die Sammlung
   nur über den Knopf »Lernen« derselben Karte dran, nicht in der
   allgemeinen Abfrage.
3. **Die Lehrgangszuordnung tut ohne die eigene Lektionsnummer
   nichts.** Man kann einundzwanzig Zeilen »Aorist ab Lektion 14«
   eintragen; solange »Ich bin bei Lektion« leer ist, kommt in der
   allgemeinen Abfrage weiter alles dran. Lernziele mit Lektionsauswahl
   halten sich auch ohne die Zahl daran — dieselbe Angabe wirkt also an
   zwei Stellen verschieden.
4. **Das Tagespensum zählt über alle Sammlungen und Ziele zusammen.**
   Darum steht »Für heute ist Schluss«, obwohl man in *dieser* Sammlung
   noch nichts getan hat. »Trotzdem weitermachen« hebt es auf — die
   Grenze ist ein Vorschlag, kein Schloss.
5. **»Gezielt üben« ist in keinem Menü**, nur ein Knopf auf jeder
   Sammlungskarte. Es übt ohne Tagespensum, gilt nur für diese Sitzung,
   und der Lernstand zählt trotzdem mit.
6. **Fast richtig kostet nichts, ein Tipp aber etwas.** Ein einzelnes
   danebenliegendes Zeichen darf man nachtippen; ein genommener Tipp
   deckelt die Wertung dauerhaft auf »Schwer«. Und `Enter` nach der
   Rückmeldung übernimmt die automatische Wertung — die Ziffern 1 bis 4
   sind ein protokollierter Eingriff, kein Normalweg.
7. **Im griechischen Antwortfeld muss man nichts umschalten**, und die
   Betonung liegt auf einer Taste, die allein nichts schreibt (`Ö`).
   Dass ein gehaltener Buchstabe eine Akzentauswahl mit Zifferntasten
   öffnet, steht nirgends. Im mehrzeiligen Übungsfeld schickt nur
   `Umschalt+Enter` ab.
8. **Dinge, die sich von selbst oder gar nicht speichern.** Die
   Textübersetzung sichert sich 800 ms nach dem Tippen, es gibt kein
   Abschicken. Das MCP-Zugangsmerkmal ist nur einmal sichtbar. Die
   Legasthenie-Regler wirken sofort, sind aber erst nach »Speichern«
   dauerhaft — und wer unter »Lernverhalten« einen abgeleiteten Wert
   anfasst, friert ihn für immer fest (`ansicht_einstellungen.js`
   schickt darum nur wirklich bewegte Werte).
9. **Eine Mailadresse muss vor der ersten Anmeldung von außen
   eingetragen sein.** Sonst entsteht ein zweites, leeres Profil, und
   der Lernstand sieht verloren aus. Das ist die unangenehmste Stelle
   der Liste, weil sie sich nicht zurücknehmen lässt, ohne Profile zu
   verschmelzen.
10. **Die Willkommenskarte verschwindet.** Nach dem ersten Durchlauf
    ist sie weg; wiederzufinden nur über die Anleitung, Knopf »Karte
    wieder einblenden«.

## Inventar: was erklärt werden müsste

Spalten: **heute** — wo es erklärt wird (R = Rundgang, A = Anleitung,
T = Tastaturseite, O = am Ort in der Oberfläche, — = nirgends).
**Rang** — unverzichtbar / nützlich / Feinheit.
**Wem** — M = Mutter, K = Kinder.

### Das Weltbild (der fehlende Unterbau)

| Punkt | heute | Rang | Wem |
|---|---|---|---|
| Lexem – Formen – Bedeutungen als drei Ebenen | — (nur `00-konzept.md`) | unverzichtbar | M; K knapp |
| Eine Bedeutung hat mehrere gültige Übersetzungen | A | unverzichtbar | M, K |
| Die abfragbare Einheit ist die **Aufgabe**, nicht das Wort | — | unverzichtbar | M |
| Aufgaben werden **erzeugt**, nicht gepflegt | — | unverzichtbar | M |
| Darum zählt die Tagesdosis Wörter, nicht Aufgaben | — | nützlich | M |
| Eine Sammlung ist ein Wortschatz, meist ein Lehrbuch | R, A | unverzichtbar | M, K |
| Alles hängt an der Sammlungskarte — die Kopfzeile hat nur drei Reiter | R (nebenbei) | unverzichtbar | M, K |
| Profil, Sammlung und Lektion merkt sich der Browser; der Lernmodus nicht | — | Feinheit | M |

### Lernen

| Punkt | heute | Rang | Wem |
|---|---|---|---|
| Ablauf: Frage, Enter, Wertung, Enter | A, R | unverzichtbar | K, M |
| Der Balken misst am Tagespensum, nicht an einer erfundenen Marke | — | nützlich | K |
| Vier Eingabearten: Feld, Auswahlknöpfe, Merkmalslisten, ganze Reihe | A (nur Reihe) | nützlich | K |
| Fast richtig kostet nichts, erst der zweite Versuch zählt | A, R | unverzichtbar | K |
| Keine Selbsteinschätzung — der Trainer wertet und begründet | A | unverzichtbar | K, M |
| »Wonach wurde gewertet?« (Urteil, Versuche, Denkzeit) | — | nützlich | K |
| Wertung von Hand ändern (1–4), wird als Eingriff vermerkt | A halb, README | nützlich | K |
| Tipp in drei Stufen, deckelt die Wertung auf »Schwer« | R halb | unverzichtbar | K |
| »Weiß ich nicht« ist die ehrliche Auskunft, kein Aufgeben | A, R | unverzichtbar | K |
| Aussetzen; Termin selbst setzen; auf »neu« zurücksetzen | R (nur Aussetzen) | Feinheit | M |
| »Wort ansehen« und »Schluss für heute«, ohne die Sitzung zu verlieren | — | nützlich | K |
| Die Aufgabenarten und was sie verlangen | A | unverzichtbar | K |
| Ganze Reihe: Enter springt ins Feld, geprüft wird am Ende | A | nützlich | K |
| Artikel und Pronomen darf man mitschreiben, falscher Artikel zählt | A | nützlich | K |
| Akzente sind Hinweis, nicht Fehler | A | unverzichtbar | K |
| Verwechslung statt Tippfehler (»das ist die 2. Person Singular«) | — (README) | nützlich | K, M |
| Fehlerarten werden benannt (b/d, Reihenfolge, Doppelkonsonant) | — | nützlich | M |
| Stamm wird aus dem Paradigma abgeleitet: `γράφ\|ουμε` | — | Feinheit | M |
| Merktafel und Zeichenleiste unter dem Antwortfeld | A, README | nützlich | K |
| »Warum kommt das jetzt?« — Stabilität, Schwierigkeit, Abruf | R, A | nützlich | K, M |
| »Warum ist das so?« — die greifende Grammatikregel | — | nützlich | K |
| Terminvorschau bei jeder der vier Noten | — | nützlich | K |
| Tagespensum ist eine Zahl, Rückstand keine Mauer, »Trotzdem weitermachen« | A halb | unverzichtbar | K |
| Runde: erst jedes Wort einmal, dann das zweite Mal | A | nützlich | K |
| Tagesgrenze ist der Kalendertag | — | Feinheit | M |
| Denkzeit nur bis zum ersten Tastendruck, verworfen bei Unterbrechung | — | Feinheit | M |
| Frei üben / Fehler wiederholen | R | nützlich | K |
| Gezielt üben: Wortart oder einzelne Zeit, mit Anzahl daneben | A | nützlich | K, M |
| Gezielt üben gilt nur für diese Sitzung | A | nützlich | K |
| Legastheniemodus: Lesbarkeit live, Einprägen vor dem ersten Mal, Gerüst | — | nützlich | M |

### Tastatur und Schrift

| Punkt | heute | Rang | Wem |
|---|---|---|---|
| Griechisch ohne Umschalten tippen (`grafo` → γράφω) | A, T | unverzichtbar | K |
| Akzent: tote Taste `Ö` — **oder** Vokal halten, dann Ziffer | A, T (Haltenweg fehlt) | unverzichtbar | K |
| Schluss-ς auf `W`, Fragezeichen auf `Q`, Y und Z vertauscht | T | nützlich | K |
| Das Probefeld lernt die wirkliche Belegung mit | T | Feinheit | M |
| Eigenes Systemlayout umschalten, die Umschrift hält sich heraus | A, T | nützlich | K |
| Im Übungsfeld schickt `Umschalt+Enter` ab | O (Hinweis) | nützlich | K |

### Planen

| Punkt | heute | Rang | Wem |
|---|---|---|---|
| Lernziel = Ausschnitt mit Termin | R, A | nützlich | M, K |
| Umfang wählen: Lektionen, Zeiten, Wortarten, Abfragearten (nichts = alles) | — | nützlich | M |
| Der Trainer rechnet das Tagessoll und sagt, wenn das Pensum nicht reicht | A | nützlich | M |
| »So reicht die Zeit nicht« setzt das Pensum für **alle** Sammlungen | — | unverzichtbar | M |
| »Was käme dran?« mit Begründung; »Neu würfeln« wird am Ziel vermerkt | R, A | nützlich | M |
| Ziel löschen lässt den Lernstand stehen | O | nützlich | M |
| Lehrgangsschranke: ab welcher Lektion welche Formgruppe | R, A | unverzichtbar | M |
| Sie wirkt erst mit »Ich bin bei Lektion« (siehe oben, Punkt 3) | O (Warnkasten) | unverzichtbar | M |
| Der Vorschlag aus den Lektionsnamen bleibt ein Vorschlag | O halb | nützlich | M |
| Buchstand ist je Person, Zuordnung je Sammlung | — | nützlich | M |
| Ausgeblendet heißt wartet, nicht gelöscht | A | unverzichtbar | M, K |
| Bedeutungen sind von der Schranke nie betroffen | A | nützlich | M |

### Eingeben und pflegen

| Punkt | heute | Rang | Wem |
|---|---|---|---|
| Vier Wege hinein: Maske, Chat, Datei, Übungskurs | — | unverzichtbar | M |
| Merkmalsbündel statt Spaltennamen | — (nur `01-format`) | unverzichtbar | M |
| Formgruppe = die Tabelle, die zusammen gelernt wird | O (Einstellungen) | unverzichtbar | M |
| Standardgruppen gegen zuschaltbare; Abwählen schaltet ab, löscht nicht | O | nützlich | M |
| Die Eingabemaske zeigt nur die Felder, die diese Sammlung abfragt | — | unverzichtbar | M |
| Genau eine Grundform, für sie entsteht keine Formaufgabe | — | unverzichtbar | M |
| Handeintrag gilt sofort als geprüft, Chateintrag nicht | — | unverzichtbar | M |
| Lexemmerkmale: `klasse`, `genus`, griechisch `diathese = deponens` | — | Feinheit | M |
| Bedeutung gegen Übersetzung, `kontext` als Trennschärfe | — (nur `01-format`) | unverzichtbar | M |
| Gleiche Übersetzung auf zwei Wörtern — beide gelten | — | nützlich | M |
| Paradigmentafel im Wortschatz, ungeprüfte Zeilen anders dargestellt | O | unverzichtbar | M |
| Durchsichtleiste »3 von 28 ungeprüft« mit `Enter`, `→`, `←` | O (Hinweis) | unverzichtbar | M |
| Qualitätsprüfung und ihre Befunde (»Paradigma lückig«) | — | nützlich | M |
| Nachschlagen findet über **alle** Formen, nicht nur Lemmata | — | nützlich | M, K |
| Berichtigen ist besser als Löschen, der Lernstand hängt an der Form | — | unverzichtbar | M |
| Jede inhaltliche Änderung setzt die Freigabe zurück | — | unverzichtbar | M |
| Datei einlesen: zwei Wege (Bündel-JSON, Tabelle mit Spaltendeutung) | — | nützlich | M |
| Der Import ist wiederholbar und überschreibt Freigegebenes nicht | — | nützlich | M |
| Probelauf schreibt nichts | A (nur für den Chat) | unverzichtbar | M |

### Freigabe

| Punkt | heute | Rang | Wem |
|---|---|---|---|
| Ungeprüft wird nicht abgefragt — und warum | A, O | unverzichtbar | M, K |
| Zwei Wege: Wortschatz-Durchsicht (ein Wort) und Freigabeansicht (ganze Lektion) | — | unverzichtbar | M |
| Die Tafel zeigt leere Zellen als »—« bzw. »erklärte Lücke« | O | nützlich | M |
| Zellen einzeln abwählbar; `Enter`, `j`, `k` zum Durchgehen | O (Hinweis) | nützlich | M |
| Übungssätze und Grammatikregeln warten mit, Regeln stehen oben | — | nützlich | M |
| Auf der Übersicht steht, was wartet | O | nützlich | M |
| Der Schalter »Ungeprüfte mitabfragen« hebt die Sperre ganz auf | O (vorbildlich) | nützlich | M |
| Freigabe ist ein Arbeitsgang, keine Einstellung | — | unverzichtbar | M |

### Sätze und Texte

| Punkt | heute | Rang | Wem |
|---|---|---|---|
| Sätze üben: eigene Abfrage, eigene Lernstände je Richtung | — | nützlich | K |
| Rückmeldung Wort für Wort (`σπίτι → θέατρο`, `fehlt: στο`) | A | nützlich | K |
| Beim langen Text urteilt der Mensch, der Vergleich hilft nur | — | unverzichtbar | K |
| Text einwerfen oder hochladen, Leerzeilen trennen Abschnitte | R, A | nützlich | M, K |
| Deckung: vier Töpfe, Prozentangabe, und es wird nicht geraten | A | unverzichtbar | K, M |
| Jedes Wort anklickbar, zeigt den eigenen Eintrag samt Form | A | nützlich | K |
| »Wort für Wort« ist ausdrücklich keine Übersetzung | — (CHANGELOG) | nützlich | K |
| Eigene Fassung sichert sich beim Tippen, kein Abschicken | A | nützlich | K |
| Übersetzungsvorschlag kommt nur über den Chat | — | nützlich | M |
| Fehlende Wörter »für die KI merken«; die Liste wartet, bis jemand fragt | A | unverzichtbar | K, M |
| Einen Text löschen nimmt die eigene Übersetzung mit | O (Warnung) | nützlich | K |

### Dein Fortschritt

Am 15.11.2026 dazugekommen (`ansicht_statistik.js`), nach der Durchsicht
dieses Konzepts. Der Zuschnitt ist der einer guten Schulung — vier
Zahlen, die man ohne Diagramm versteht, und wo nichts auszusagen ist,
steht ein Satz statt eines leeren Gerüsts. Entsprechend braucht die
Ansicht selbst fast keine Erklärung; drei Punkte doch:

| Punkt | heute | Rang | Wem |
|---|---|---|---|
| Der Knopf steht auf der Übersicht neben »Fehler wiederholen« | O | nützlich | K, M |
| »Was auf dich zukommt« ist Planung, nicht Rückblick — Fälligkeiten der nächsten Wochen | O (Kacheltitel) | nützlich | M |
| Die Zahlen stimmen mit der Übersicht überein: nur mitgelernte Sammlungen, nur Zeitformen vor der Schranke | — (nur CHANGELOG) | nützlich | M |

Der dritte Punkt ist der einzige, der wirklich erklärt werden muss, und
er gehört nicht in ein Kapitel, sondern als Zeile unter die Kacheln:
wer die Lektionsschranke gesetzt hat, sieht hier weniger, als im
Bestand steht, und soll das nicht für einen Fehler halten.

Als Abschluss der Kinderspur ist die Ansicht gut geeignet: »Was du
getan hast« nach zwei Tagen Lernen ist der beste Grund, am dritten
weiterzumachen.

### Profile und Freigabe an Personen

| Punkt | heute | Rang | Wem |
|---|---|---|---|
| Profil ohne Passwort, Wechsel oben rechts | — | unverzichtbar | K, M |
| Lernstand ist immer persönlich, auch bei geteiltem Bestand | A halb | unverzichtbar | M |
| Sammlung freigeben: mitlernen / mitlernen und pflegen / entziehen | — | nützlich | M |
| Recht entziehen lässt den Lernstand stehen | — | Feinheit | M |
| Besitz übertragen, bisherige Besitzerin behält Schreibrecht | — | Feinheit | M |
| Verwalterin darf mehr (Sprachprofile) | — | Feinheit | M |

### Einstellungen, Zugang, Anlage

| Punkt | heute | Rang | Wem |
|---|---|---|---|
| Wunschretention 80–97 %: »wie sicher soll etwas sitzen« | O | nützlich | M |
| Neue Wörter je Tag; Fragen je Tag (0 = ohne Grenze) | O | unverzichtbar | M |
| Die Hälfte des Pensums ist fürs Neue reserviert | — | nützlich | M |
| »Neues durchgehend untermischen« | O | Feinheit | M |
| Formbenennung in drei Fassungen (»Genitiv Singular« … »wessen?, Einzahl«) | O | nützlich | M |
| Speichern schickt nur bewegte Werte — sonst friert eine Ableitung ein | O (Hinweis) | unverzichtbar | M |
| Token anlegen, nur einmal sichtbar, zurücknehmbar | A | unverzichtbar | M |
| Kopfzeile anklicken statt eintippen | A | unverzichtbar | M |
| Sperre nach acht Fehlversuchen | — | Feinheit | M |
| Mailadresse **vor** der ersten Anmeldung von außen eintragen | O halb | unverzichtbar | M |
| Als App auf den Startbildschirm | README | nützlich | K |
| Sicherung (WAL, `werkzeuge/sicherung.sh`) | README | unverzichtbar für den Betrieb | M |

Die letzte Zeilengruppe gehört **nicht** in eine Schulung: einmalige
Einrichtung, bei der jemand daneben sitzt. Sie steht richtig in
`README.md` und `BETRIEB-PRIVAT.md`. Ausnahme ist die Mailbindung —
sie ist einmalig, aber unumkehrbar, und muss darum irgendwo stehen, wo
man sie vorher liest.

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
Schritt wird von einem Menschen ausgelöst. Und es gibt keinen zweiten
Datenweg: die Werkzeuge rufen dieselben Funktionen auf wie die
Oberfläche, also gilt dieselbe Prüfung.

**3. Es arbeitet in deinem Namen.** Das Zugangsmerkmal hängt an einem
Profil. Alles, was darüber geschieht, geschieht auf dem Bestand dieser
Person und ist ihr zugeordnet. Daraus folgt der praktische Rat: **genau
ein Token, bei der Mutter.** Kinder brauchen keines, und das Merkmal
weiterzugeben ist dasselbe wie das Profil zu verleihen.

**4. Es sieht mehr, als man vermutet.** Nicht nur Vokabeln:
`lernstand_lesen` gibt zurück, was sitzt und woran es hakt — je Wort,
für diese Person, mit der Angabe, was »schwach« ist. Wer ein
Kinderprofil anbindet, schickt also auch Leistungsdaten an den
Anbieter des Chatprogramms. Für den geplanten KI-Adapter ist »keine
Lerndaten« eine der nicht verhandelbaren Regeln
(`02-geplant-ki-adapter.md`); über den MCP gilt sie **nicht
automatisch**. Das steht heute nirgends und gehört in die Schulung —
nicht als Warnung, sondern als Entscheidungsgrundlage.

Gegenstück und gute Nachricht: Sammlungen an Personen freigeben, Besitz
übertragen und Token verwalten kann über den MCP **niemand**. Diese
Fähigkeiten gibt es nur in der Oberfläche.

**5. Freigeben soll es nicht — und kann es doch.** Das Werkzeug
`formen_bestaetigen` wurde absichtlich entfernt, mit der Begründung im
Quelltext: »eine Bitte ist keine Sperre«. Drei Türen daneben stehen
aber offen, und die Schulung darf sie nicht verschweigen, weil die
Mutter sonst ein falsches Bild hat:

- `vokabel_anlegen` und `formen_ergaenzen` haben den Schalter
  `als_geprueft`. Die Beschreibung bittet, ihn »nur auf ausdrücklichen
  Wunsch der Benutzerin« zu setzen — also genau die Bitte, die an
  anderer Stelle als untauglich verworfen wurde.
- `uebung_anlegen` und `uebungen_importieren` reichen den Eintrag
  unverändert weiter; ein `"geprueft": true` darin erzeugt eine sofort
  freigegebene Übung. Im `inputSchema` ist das Feld nicht einmal
  genannt.
- Je Sammlung gibt es die Einstellung **»Ungeprüfte Formen
  mitabfragen«**. Ist sie an, ist die Prüfung ganz aus.

Sauber zu ist nur `form_aendern`: es entfernt `geprueft` aktiv aus der
Eingabe.

Richtig ist der Satz also nicht »freigeben kann es nicht«, sondern:
*freigeben passiert nicht im Vorbeigehen — es braucht einen Menschen in
der Freigabeansicht oder eine ausdrückliche Anweisung von dir.* Besser
wäre, die Türen zu schließen; das ist eine Codeänderung und steht
unten bei den Befunden.

**6. Warum ein Mensch prüfen muss.** Nicht »weil KI unzuverlässig
ist«, sondern konkret: eine **erfundene Form, die unbemerkt gepaukt
wird, ist schlimmer als eine fehlende** — man lernt sie, sie klingt
plausibel, und sie steht dann gegen das, was im Unterricht gilt. Bei
Grammatikregeln ist es schlimmer als bei Formen: eine falsche Regel
erklärt scheinbar und wird deshalb behalten.

**7. Wie man sie anweist.** Das steht heute nur als drei Beispielsätze
in der Anleitung. Es sollte als Muster aufgebaut sein, nicht als Liste
von Zaubersprüchen — mit dem Grund daneben, damit man eigene Sätze
bilden kann:

| Will man | sagt man | weil |
|---|---|---|
| eine Lektion eintragen | »Trag Lektion 5 ein, mit allen Formen. Mach zuerst einen Probelauf.« | der Probelauf schreibt nichts, zeigt aber, was herauskäme |
| in einer neuen Sprache anfangen | »Sieh zuerst nach, welche Formgruppen diese Sammlung verlangt.« | sonst kommen Merkmale, die der Trainer mit 422 abweist |
| Übungssätze | »Prüf den Text vorher gegen meinen Wortschatz bis Lektion 20.« | ein Text mit dreißig unbekannten Wörtern ist keine Übung |
| die angeforderten Wörter | »Schau nach, welche Wörter ich angefordert habe, trag sie ein und hak sie ab.« | ohne Abhaken bleiben sie auf der Liste; sie kommen mit dem Satz, in dem sie standen |
| eine Formangabe berichtigen | »Die Form `έγραψε` ist falsch beschriftet, stell sie richtig.« | Ändern erhält den Lernstand, Löschen vernichtet ihn |
| wissen, woran es hakt | »Was in meinem Wortschatz sitzt noch nicht?« | daraus macht man Übungssätze, die sich lohnen |

Und was man **nicht** sagt: »lösch alles aus Lektion 3«. Löschen
verlangt die Nennung des Lemmas und meldet zurück, wie viele
Wiederholungen verlorengehen; steht dort eine Zahl über null, erst
hinsehen.

**8. Wenn es nicht geht.** Die drei Hürden stehen schon in der
Anleitung (Kopfzeile aus der Liste anklicken, neue Unterhaltung für
neue Werkzeuge, ungeprüft wird nicht abgefragt). Sie bleiben dort; in
der Schulung genügt ein Verweis.

### Form

Dieses Kapitel ist **Lesetext**, kein Rundgang: es gibt kaum etwas zu
zeigen, und der wichtigste Satz ist eine Verneinung. Länge etwa eine
Bildschirmseite. Für die Kinder davon genau zwei Sätze, an passender
Stelle in der Kinderspur: der Trainer schickt nichts aus dem Haus, und
wenn du Wörter anforderst, wartet die Liste, bis jemand sie abholt.

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

**3. Was daraus entsteht: Aufgaben.** Das ist der Satz, der die Pflege
mit der Abfrage verbindet. 18 Formen ergeben 17 Formaufgaben — die
Grundform zählt nicht mit —, dazu Bedeutung in beide Richtungen. Wer
ein Verb einträgt, legt keine Karten an; er legt Material hin, aus dem
der Trainer die Karten macht. Umgekehrt: eine fehlende Zelle ist eine
fehlende Aufgabe, und ein lückenhaftes Paradigma verdirbt zusätzlich
die Stammerkennung, aus der `γράφ|ουμε` entsteht.

**4. Die Formgruppe ist die Tabelle, nicht die Zelle.** Eine
Formgruppe ist das, was zusammen gelernt wird: eine Zeit mit ihren
sechs Personen, oder eine Einzelform wie das Partizip. Griechisch hat
fünfzehn Verbgruppen, davon sechs voreingestellt. Der Trainer baut die
**Eingabemaske aus eben diesen Gruppen** — man füllt also keine
Merkmale aus, sondern Felder, die schon beschriftet sind, und zwar nur
die, die diese Sammlung wirklich abfragt. Das ist die gute Nachricht
dieses Kapitels, und sie steht heute nirgends.

**5. Dieselbe Sache von Hand, über den Chat, aus einer Datei.** Mit
dem einen Unterschied, der zählt: **von Hand eingetragene Formen gelten
sofort als geprüft, über den Chat eingetragene nicht.** Nicht weil
Handarbeit besser wäre, sondern weil beim Eintippen schon jemand
hingesehen hat. Beim Dateiweg gibt es zwei Fälle, die man
auseinanderhalten muss: eine JSON-Datei mit vollständigen Paradigmen
(Merkmalsbündel wie oben) und eine Tabelle aus Anki oder Quizlet, bei
der man nur Wort, Bedeutung, Wortart und Lektion zuordnet — Formen
bringt sie keine.

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
  setzt `kontext` (»klein, Körpergröße«) — dann ist die Frage eindeutig
  und beide werden wirklich geübt.
- **Unbekannte Merkmale werden abgewiesen**, nicht stillschweigend
  gespeichert. Ein `tempuss` ergibt einen Fehler statt einer Form, die
  nie abgefragt wird. Eigenes geht mit dem Vorsatz `x_`.
- Beim Verb gibt es Merkmale des **Wortes**, nicht der Form: `klasse`
  (Konjugationsklasse, Ablautreihe) und für griechische Deponentien
  `diathese = deponens` — sonst meldet die Qualitätsprüfung
  Aktivformen als fehlend, die es bei θυμάμαι gar nicht gibt.

**7. Ansehen und freigeben.** Die Paradigmentafel zeigt die Formen so,
wie sie im Buch stehen, Zelle für Zelle, ungeprüfte anders dargestellt
— eine leere oder doppelt besetzte Zelle sieht man auf einen Blick,
eine Liste in Eingabereihenfolge kann man nicht prüfen. Dafür gibt es
**zwei Wege, und die Schulung muss beide nennen**: die Durchsicht im
Wortschatz (ein Wort nach dem anderen, `Enter` bestätigt und blättert
weiter) und die Freigabeansicht (ganze Lektion, Zellen abwählbar,
Befunde daneben, `Enter` / `j` / `k`). Der erste Weg ist für fünf
Wörter, der zweite für eine Lektion.

**8. Berichtigen statt löschen.** An jeder Form hängt ein Lernstand.
Eine falsch beschriftete Form stellt man richtig; die Aufgaben hängen
am Merkmalsbündel, nicht an der Zeile, und der Lernstand bleibt.
Umgekehrt: jede inhaltliche Änderung nimmt die Freigabe zurück, weil
das Geänderte nicht mehr das ist, was jemand angesehen hat.

**9. Und wenn es zu viel wird:** die Lehrgangsschranke. Hier gehört
die echte Zahl hin, weil sie das Problem erklärt: im griechischen
Bestand stehen 6971 Formaufgaben, davon 832 Präsens und rund 2900
Aorist, Futur und Passiv. Wer bei Lektion 20 ist, hat den Aorist noch
nicht gehabt — er kommt in Lektion 39. Die Schranke nimmt ihn heraus,
bis man dort ankommt. **Und sie wirkt nur mit der eigenen
Lektionsnummer** — der häufigste Leerlauf des ganzen Werkzeugs.

### Form

Dieses Kapitel ist **Übung am Beispiel**, nicht Lesetext. Es braucht
etwas, woran man es tut, und es braucht einen Fall mit ungeprüften
Formen. Dafür müsste der Übungskurs einen zweiten Teil bekommen, siehe
unten.

## Empfehlung zur Form

Kurz: **die vier Rundgänge bleiben, bekommen aber eine engere Aufgabe
und zwei Geschwister; daneben entsteht ein Lehrgang aus Kapiteln in der
Anleitung, jedes mit einer Handlung am Übungskurs. Kein Video.**

### Warum nicht einfach längere Rundgänge

Die Blase trägt drei Sätze. Das ist keine Einstellung, sondern eine
Eigenschaft der Form: sie liegt über der Anwendung, verdeckt also
gerade das, was sie erklärt, und sie wird mit jedem Satz schwerer zu
platzieren — die Kommentare in `fuehrung.js` erzählen genau diese
Geschichte (Blase mitten auf dem erklärten Element, Knöpfe außerhalb
des Bildschirms, Rundgang nicht mehr verlassbar).

Ein Rundgang kann außerdem nur zeigen, was **da** ist. Er kann nicht
sagen, was eine Aufgabe ist — das steht nirgends auf dem Bildschirm.

**Also:** Rundgänge sind Orientierung. Höchstens sechs Schritte, jeder
Text unter 300 Zeichen, jeder zeigt auf ein Ding, keiner erklärt ein
Konzept. Zwei fehlen heute und wären je zwei Minuten: **Formen
eintragen** (durch die Maske) und **Freigabe** (durch die
Freigabeansicht) — in beiden Fällen ist das Erklärte wirklich auf dem
Bildschirm, und beides sind Mutterwege, die heute gar nicht vorkommen.

### Warum Kapitel in der Anleitung und nicht ein neues Werkzeug

Der Ort ist schon da (`#/hilfe`), er ist aus der Fußzeile und den
Einstellungen verlinkt, und er ist Text — also wartbar ohne Bauschritt
und durchsuchbar. Die Änderung ist nicht der Ort, sondern die **Form
des Ortes**: heute zehn zugeklappte Abschnitte gleichberechtigt
untereinander. Daraus würde:

- **oben zwei Spuren** (»Ich will lernen« / »Ich pflege den Bestand«),
  je eine numerierte Kapitelliste mit Dauer;
- **jedes Kapitel eine eigene Seite** (`#/hilfe/pflege-2`), nicht ein
  Ausklapper. Ein Kapitel, das offen ist, soll die anderen nicht
  daneben zeigen;
- **am Ende jedes Kapitels genau eine Handlung** am Übungskurs, mit
  Knopf dorthin;
- **Fortschritt gemerkt**, mit derselben Mechanik wie die Rundgänge
  (`localStorage`, eine Liste gesehener Kennungen) — damit auf der
  Übersicht »Kapitel 3 von 6« stehen kann statt nur »Anleitung«.

Die bestehenden Abschnitte werden dabei nicht weggeworfen; sie sind gut
und werden die Kapitelkörper. Was fehlt, ist das Gerüst und die drei
neuen Kapitel (Weltbild, Formen eintragen, Rolle der KI).

### Warum der Übungskurs der Hebel ist

Er ist schon gebaut, er ist Englisch (»damit man sich auf die Bedienung
statt auf die Vokabel konzentriert«), und er bringt für jede Funktion
einen Fall mit. Er ist aber **durchgehend freigegeben**, und damit
fehlt genau der Gegenstand, an dem die Pflegespur üben müsste.

Empfehlung: ein **zweiter Teil im Kurs**, zwei oder drei Wörter, als
`quelle = 'ki'` und ungeprüft angelegt, davon eines mit einem
absichtlichen Fehler — etwa `to go` mit `goed` als Präteritum. Dann hat
das Kapitel »Freigabe« etwas zu tun, das Kapitel »Berichtigen statt
löschen« einen echten Fall, und die Qualitätsprüfung zeigt ihren Befund
an etwas, das wirklich falsch ist. Das ist eine kleine Ergänzung an
`beispielkurs.py` und ersetzt drei Absätze Erklärung.

Zweite Empfehlung dazu: der Kurs sollte ein **zweites Profil**
anlegen können (»Übungskind«), damit die Mutter die Freigabe an
Personen und das Häkchen »Wird mitgelernt« einmal gefahrlos ausprobiert
hat, bevor sie es mit den Lernständen ihrer Kinder tut. Ob das ohne
Verwirrung in der Profilliste geht, habe ich nicht geprüft.

### Warum kein Video

Nicht wegen des Aufwands, sondern wegen der Haltbarkeit. Der CHANGELOG
führt für den 15.11.2026 allein sieben Änderungen an der Oberfläche,
darunter zwei an den Rundgängen selbst. Ein Film zeigt Knöpfe, die es
in drei Wochen anders gibt, und niemand schneidet ihn nach. Text in
`ansicht_hilfe.js` wird beim Ändern der Oberfläche mitgeändert, weil er
daneben liegt; eine Videodatei wird es nicht.

Für genau einen Zweck wäre bewegtes Bild überlegen: das Tippen mit der
Umschrift (`grafo` → γράφω) und die Akzentwahl durch Halten. Beides ist
in Worten umständlich und in zwei Sekunden Bild klar. Dafür genügt eine
kleine Schleife ohne Ton auf der Tastaturseite — kein Video mit
Erzähler, und dort steht sie neben dem Probefeld, in dem man es gleich
nachmacht.

### Reihenfolge, und warum sie zwingend ist

```
Weltbild (Lexem/Formen/Bedeutungen → Aufgaben)
   ├─→ Lernen: Abfrage, Bewertung, Tipp          (Kinder beginnen hier)
   │      ├─→ Tastatur
   │      └─→ Was heute drankommt
   │             └─→ Ziele, Lehrgangsschranke
   └─→ Pflege: Merkmale und Formgruppen
          ├─→ Eintragen von Hand
          │      └─→ Freigabe ──→ Berichtigen und Löschen
          └─→ Die Rolle der KI ──→ Chat anschließen
                 └─→ Texte, Deckung, Wortwünsche
```

Zwei Abhängigkeiten sind hart: **Freigabe setzt Merkmale voraus** (man
kann eine Tafel nicht prüfen, deren Zellen man nicht liest), und **die
KI-Kapitel setzen die Freigabe voraus** (sonst ist »sie darf nicht
freigeben« eine Regel ohne Gegenstand). Alles andere ist tauschbar.

Die Kinder brauchen das Weltbild nur als einen Absatz: *ein Wort hat
Formen, und jede Form ist eine eigene Frage — darum sind es so viele.*

### Länge

Gemessen an dem, was hier schon beobachtet wurde (»eine Tour über
fünfzehn Funktionen hat niemand zu Ende gesehen«):

| Form | Obergrenze | wo abgebrochen wird |
|---|---|---|
| Rundgangsschritt | 300 Zeichen | — |
| Rundgang | 6 Schritte, 2 Minuten | nach Schritt 7 |
| Kapitel Kinderspur | 1 Bildschirmseite, 3 Minuten | beim zweiten Bildlauf |
| Kapitel Pflegespur | 2 Bildschirmseiten, 8 Minuten | wenn kein Knopf vorkommt |
| Spur gesamt | 3 bzw. 6 Kapitel | — |

Die wichtigste Regel ist von den Rundgängen übertragbar: **jedes Stück
endet an einer Stelle, an der man etwas tun will.** Nicht mit einer
Zusammenfassung.

## Kapitelplan

### Spur »Ich will lernen« (Kinder, drei Kapitel, zusammen 8 Minuten)

| | Kapitel | Inhalt | endet mit |
|---|---|---|---|
| 1 | Wie der Trainer fragt | Weltbild in einem Absatz; Ablauf; fast richtig; Weiß-ich-nicht; Tipp und was er kostet | »Lernen« im Übungskurs, fünf Fragen |
| 2 | Tippen und antworten | Umschrift, Akzent durch Halten, ς auf W, Zeichenleiste, Merktafel, Artikel mitschreiben, `Umschalt+Enter` beim Satz | fünf Fragen auf Griechisch |
| 3 | Was heute drankommt | die vier Zahlen, Pensum und Rückstand, »Trotzdem weitermachen«, Runde, »Warum kommt das jetzt« | »Warum kommt das jetzt« in der Abfrage aufklappen, dann »Fortschritt« ansehen |

Dazu, nicht als Kapitel, sondern als zwei Sätze an passender Stelle:
der Trainer schickt nichts aus dem Haus; die angeforderten Wörter
warten, bis jemand sie abholt.

### Spur »Ich pflege den Bestand« (Mutter, sechs Kapitel, zusammen 45 Minuten)

| | Kapitel | Inhalt | endet mit |
|---|---|---|---|
| 1 | Wie der Trainer die Vokabeln sieht | drei Ebenen; Aufgaben werden erzeugt; die Rechnung 18 Formen → 17 Aufgaben; Bedeutung gegen Übersetzung | Paradigmentafel von `to go` ansehen |
| 2 | Merkmale und Formgruppen | Bündel gegen Spalten; Formgruppe als Tabelle; Standard gegen zuschaltbar; die Maske kommt daraus | `to drink` von Hand eintragen |
| 3 | Freigabe | ungeprüft wird nicht abgefragt; die zwei Wege; Befunde; der Schalter, der alles aufhebt | den ungeprüften Teil des Kurses durchgehen |
| 4 | Berichtigen und löschen | Lernstand hängt an der Form; Änderung nimmt die Freigabe zurück; Löschen verlangt den Namen und nennt den Verlust | `goed` richtigstellen |
| 5 | Die Rolle der KI | die acht Punkte oben, mit der Tabelle »was man sagt« | Probelauf im Chat, ohne zu schreiben |
| 6 | Ziele und das Lehrwerk | Lernziel mit Termin; Buchstand; dass die Schranke ohne ihn nichts tut; Vorschlag aus Lektionsnamen; ausgeblendet heißt wartet | Buchstand im Kurs auf 3 setzen und sehen, was wegfällt |

Die Kapitel 1 bis 4 sind die Pflicht. 5 braucht man erst, wenn der Chat
angebunden wird; 6 erst, wenn eine echte Sammlung mit Lektionen da ist.
Diese Staffelung sollte dastehen — sonst liest man sechs Kapitel, von
denen zwei gerade nicht gebraucht werden, und bricht in der Mitte ab.

Was in **keiner** Spur vorkommt, aber irgendwo stehen muss: Import aus
Dateien (eigene Seite, zur Hand, wenn es gebraucht wird),
Sammlungsfreigabe an Personen, Mailbindung, Sicherung. Das sind
Nachschlagestücke, nicht Lehrstoff.

## Erklärung am Ort statt in der Schulung

Die Regel: **was man genau dann wissen muss, wenn man vor dem Knopf
steht, gehört an den Knopf.** Eine Schulung, die es vorwegnimmt, wird
vergessen; eine Erklärung am Ort wirkt beim zehnten Mal noch. Was
heute am Ort steht, ist teils vorbildlich — der Schalter »Ungeprüfte
Formen mitabfragen« nennt in zwei Sätzen Wirkung und Grund, und der
Warnkasten beim Lehrgang sagt, dass die Zuordnung ohne die eigene
Lektion nichts tut. Es fehlt an sieben Stellen:

| Stelle | ein Satz, der dort fehlt |
|---|---|
| Eingabemaske, über den Formfeldern | »Diese Felder kommen aus den Formgruppen deiner Sprache. Leer lassen ist erlaubt — nur die gefüllten werden abgefragt.« |
| Die Marke »ungeprüft« in der Tafel | beim Antippen: warum sie da ist und wo man freigibt |
| »Für die KI merken« | »Es wird nichts verschickt. Das Wort steht auf einer Liste, bis dein Chatprogramm danach fragt.« |
| Lehrgangsschranke, nach dem Speichern | die Wirkung in Zahlen: »damit bleiben gerade N Formaufgaben draußen« |
| Löschknopf bei Wort und Form | die Zahl der Wiederholungen, die verlorengehen, **vor** der Bestätigung |
| Profilwechsel | »Lernstände sind je Profil. Wenn du hier das falsche wählst, landet deine Antwort bei jemand anderem.« |
| Mailadressfeld | »Am besten eintragen, **bevor** sich die Person das erste Mal von außen anmeldet — sonst entsteht ein zweites, leeres Profil.« |
| Unter den Fortschrittskacheln | »Gezählt wird, was du wirklich lernst: fremde Sammlungen ohne Häkchen und Zeitformen hinter deiner Lektion sind nicht dabei.« |

Umgekehrt gehört nichts davon in eine Schulung, was nur einmal
geschieht und bei dem jemand daneben sitzt: Tunnel, Access,
Sicherungsskript, Sprachprofile anlegen.

## Befunde am Rand

Beim Lesen aufgefallen; keine Schulungsfragen, aber sie beeinflussen,
was die Schulung behaupten darf. Nichts davon ist geändert.

1. **Die Freigabe ist über Nutzlastfelder erreichbar.**
   `als_geprueft` an `vokabel_anlegen` und `formen_ergaenzen`; ein
   undokumentiertes `geprueft: true` an `uebung_anlegen` und
   `uebungen_importieren`; `geprueft` je Form bei
   `vokabeln_importieren`. Damit kann ein Agent seine eigenen Einträge
   freigeben — genau das, wofür `formen_bestaetigen` entfernt wurde.
   Sauber zu ist nur `form_aendern`. Solange das so ist, ist
   »freigeben kann es nicht« in der Anleitung zu stark.
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
   vollständig freigegeben angelegt wird.
5. **Die Lehrgangsschranke wirkt an zwei Stellen verschieden.** Die
   allgemeine Abfrage braucht den Buchstand; ein Lernziel mit
   Lektionsauswahl hält sich auch ohne ihn daran. Das ist vermutlich so
   gewollt, aber es ist die Art Asymmetrie, die eine Schulung nicht
   geradebiegen kann — sie muss sie nennen.
6. **`app.py` definiert den Namen `text_deckung` zweimal** (Zeile 998
   und 1095). Beide Routen arbeiten, aber `app.text_deckung` zeigt nur
   noch auf die zweite. Da `mcp_dienst.py` Routenfunktionen über den
   Modulnamen aufruft, ist das eine Falle für den Nächsten; derzeit
   ruft es niemand so auf.

## Was ich nicht geprüft habe

- **Ob die Kinder die Rundgänge überhaupt angesehen haben** und woran
  sie hängengeblieben sind. Dieses Konzept schließt aus dem Code auf
  die Lücken, nicht aus Beobachtung. Eine halbe Stunde Zusehen beim
  ersten Lernen wiegt mehr als die Hälfte dieses Dokuments — und wenn
  sie dem widerspricht, hat sie recht.
- **Den echten Bestand.** Die Zahlen zum Griechischen (6971
  Formaufgaben, 832 Präsens, Aorist ab Lektion 39) stammen aus dem
  Kommentar in `lehrgang.py` und dem Projektgedächtnis; die Datenbank
  in `daten/` ist der Beispielbestand mit vier Sammlungen und 73
  Formen.
- **Die Oberfläche im Betrieb.** Ich habe den Code gelesen, nicht den
  Trainer bedient. Wo hier steht, etwas »stehe nirgends«, heißt das:
  nicht gefunden in `ansicht_hilfe.js`, `fuehrung.js`, `tastatur.js`
  und den Beschriftungen der Ansichten. Ein Hinweis, der nur in einem
  `title`-Attribut steht, kann mir entgangen sein.
- **Wie lange die Kapitel wirklich brauchen.** Die Minutenangaben sind
  nach Textlänge geschätzt, nicht gemessen.
- **Ob ein zweites Übungsprofil in der Profilliste mehr verwirrt, als
  es nützt.** Vorschlag ohne Beleg.
- **»Dein Fortschritt« nur überflogen.** Die Ansicht entstand während
  der Arbeit an diesem Konzept (`backend/statistik.py`,
  `frontend/js/ansicht_statistik.js`, Stand 15.11. nachmittags). Was
  hier dazu steht, beruht auf den Kopfkommentaren, dem CHANGELOG und
  den Kachelüberschriften, nicht auf einem vollständigen Durchgang.
  Sollte die Ansicht noch Bedienelemente haben, die eine Erklärung
  brauchen — etwa die Sammlungsauswahl —, fehlen sie im Inventar.
