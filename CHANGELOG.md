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

## 18.11.2026

### Die Artikelfrage zeigte die Antwort

»Artikel wird bereits angezeigt.«

Die Frage lautete **»το αγόρι — Welcher Artikel?«**, und darüber stand
το. Nachgezählt am laufenden Bestand: **909 von 928 Artikelaufgaben
waren so** — praktisch alle, denn ein griechisches Hauptwort steht im
Lehrwerk mit seinem Artikel.

Wer da richtig lag, hat nichts bewiesen. Und der Lernplan hat daraus
geschlossen, das Wort sitze.

Jetzt steht in der Frage das Wort ohne Artikel — und vorgelesen wird
es auch ohne, denn »το αγόρι« zu *hören* beantwortet die Frage
genauso. Abgetrennt wird nur ein echter Artikel: »τοίχος« fängt zwar
mit »το« an, ist aber keine Fügung.

### Wenn der Kontext eine Form desselben Wortes nennt

»Falscher Wortstamm? Hat mich jedenfalls verwirrt.«

Die Frage lautete »gegessen — *Partizip φαγωμένος*«, erwartet war
**τρώω**. Sie hat φαγωμένο getippt, also das, was in der Frage stand,
und bekam »Nicht richtig«.

Jedes Stück für sich ist in Ordnung: Deutsch → Griechisch fragt nach
der Grundform, und ein Kontext soll erläutern. Zusammen zeigt die
Frage ein griechisches Wort und verlangt ein anderes.

Dahinter steckt meist eine Verwechslung beim Eintragen: »gegessen« ist
keine Bedeutung von τρώω, sondern die Übersetzung einer **Form** — und
die steht schon im Paradigma. Im Bestand sind **116 Bedeutungen** so.

Die Eintragsprüfung meldet das jetzt. Als Notiz und nicht als Fehler:
manchmal ist es gewollt (»ο έτερος = der andere«), nämlich wenn der
Kontext ein Beispiel zeigt und nicht die Antwort. Das kann nur ein
Mensch unterscheiden — die Prüfung sagt, wo er hinsehen soll.

### Ein Regal: Buch – Kapitel – Text

»Es gibt noch keine Bücher, das wäre noch gut. Und tatsächlich würde
ich behaupten, die Texte gehören dem Konto und nicht der Sammlung,
also können sie auch außerhalb der Sammlungskarte dargestellt werden,
als eigene Karte.«

Sie hat recht, und zwar in der Ordnung der Dinge: **der Iwein gehört
nicht zu »Mittelhochdeutsch, Stammformen«.** Er ist Literatur, die man
*mit* diesem Wortschatz liest. Vorher musste man erst eine Sammlung
wählen, und bei drei Sammlungen stand der Knopf »Texte« dreimal auf
der Übersicht, jedes Mal mit einem anderen Ausschnitt dahinter.

Jetzt gibt es **Bücher und Texte** als eigene Karte auf der Übersicht,
und dahinter ein Regal mit drei Ebenen: Buch → Kapitel → Text. Bücher
sind zugeklappt, bis man sie öffnet — bei fünf Büchern mit je 173
Stücken wäre die Seite sonst ein Band.

Zuordnen geht wie überall sonst: anhaken, Buch wählen, Kapitel
eintippen, zuordnen. Vorhandene Kapitelnamen werden vorgeschlagen,
damit aus einem Tippfehler nicht zwei Kapitel werden.

**Die Sammlung bleibt am Buch** — aber als Eigenschaft, nicht als
Besitz. An ihr hängt die Deckung (»kann ich das schon lesen?«), und
ohne einen Wortschatz, gegen den gerechnet wird, gibt es diese
Auskunft nicht. Ein Text aus einem anderen Wortschatz darf darum nicht
ins Buch: die Antwort wäre sonst erfunden.

**Ein Buch aufzulösen löscht keine Texte.** Es ist eine Klammer, kein
Behälter; danach stehen sie unter »Ohne Buch«.

Über den MCP geht alles auch: `buch_anlegen`, `buecher_auflisten`,
`buch_lesen`, `texte_zuordnen`. 173 Stücke von Hand einzusortieren
wäre eine Strafe.

## 17.11.2026

### Texte haben jetzt Kapitel

»Die Texte müssten wir noch zusammenfassbar machen, also Text –
Kapitel. So ist das schwer für jemand, der damit lernt.«

Der Iwein liegt in **173 Stücken** vor. Als flache Liste ist das keine
Bedienung, sondern ein Stapel.

Die Liste gliedert sich jetzt nach Kapiteln, mit Überschrift, und
darüber steht eine Auswahl — nur mit den Kapiteln, in denen auch
wirklich ein Text liegt. Umhängen geht wie beim Wortschatz: anhaken,
Kapitel wählen, umhängen. Eine neue Nummer legt ein Kapitel an.

Die Spalte dafür gab es längst. Gefüllt ist sie allerdings nur beim
Übungsmaterial — die 352 griechischen Übungssätze hängen alle an ihrer
Lektion, aber die stehen gar nicht in dieser Liste. Von den
**Lesetexten hat bisher keiner ein Kapitel**: zwei auf Griechisch, 173
auf Mittelhochdeutsch. Dort wäre ein Kapitel »Iwein« der erste Griff.

(Im ersten Entwurf dieses Eintrags stand »390 von 392 hängen schon an
ihrer Lektion«. Das war gezählt über alle Zeilen der Texttabelle,
Übungssätze eingeschlossen — und damit über etwas anderes, als diese
Liste zeigt.)

Anders als beim Wortschatz entscheidet das Kapitel hier über nichts —
ein Text wird nicht früher oder später fällig. Es ordnet nur.

**Die Reihenfolge stimmt jetzt auch.** Vorher stand das Neueste oben —
richtig für eine Ablage, falsch für ein Buch: der Iwein las sich von
hinten. Jetzt nach Kapitel und darin in der Reihenfolge des Werks.
(Nach dem Titel zu ordnen wäre noch schlechter gewesen: da käme »Verse
135–182« vor »Verse 39–86«.)

### Die Übersetzung daneben

»Für die Texte brauchen wir noch eine Option, Referenzübersetzungen
daneben zu stellen. Gerade bei den mittelhochdeutschen ist das nämlich
wichtig.«

Über jedem Text steht jetzt der Schalter **Übersetzung daneben**.
Angeschaltet stehen Original und Übersetzung nebeneinander — so sind
mittelhochdeutsche Ausgaben gedruckt, und der Iwein steht ohnehin Vers
für Vers da, ein Abschnitt je Vers. Eingeklappt unter jedem Vers nützt
die Übersetzung beim Lesen nichts; niemand öffnet achtundvierzig
Klappen.

Ausgeschaltet bleibt alles wie bisher: eigenes Feld, Übersetzung
eingeklappt darunter, zum Vergleichen *nachdem* man selbst übersetzt
hat. Die Wahl wird gemerkt — sie ist eine Lesegewohnheit.

Auf dem schmalen Gerät stehen die beiden untereinander, mit einer
Kante dazwischen.

**Abschnitte ohne Übersetzung bleiben als Spalte stehen** und sagen
»noch nicht übersetzt«. Die Lücke ist die Auskunft. Und über dem Text
steht, wie viel überhaupt da ist — beim Iwein derzeit nichts, und das
soll nicht nach einem Anzeigefehler aussehen.

### Der Wortschatz zeigt die Kapitel — und man kann Wörter umhängen

»Bei Wortschatz müsste man auch die Kapitel sehen können, aktuell
scheint das nur eine ganze Liste zu sein. Und man müsste auch die
Vokabeln verschieben können in andere Kapitel.«

Die Liste ist jetzt nach **Kapiteln gegliedert**, mit Überschrift und
in der Reihenfolge des Lehrwerks — wie ein Glossar. Darüber steht eine
Auswahl: *alle Kapitel*, jedes einzelne mit seiner Wortzahl, und *ohne
Kapitel*.

Das war nicht nur Schönheit. Die Liste holt höchstens 200 Wörter, im
griechischen Bestand stehen 1927 — darüber stand bisher »1927 Wörter«,
und man suchte den Rest. Jetzt sagt sie, dass sie abgeschnitten ist,
und das Kapitel ist der Weg zum Rest.

**Verschieben** geht über die Kästchen links: anhaken, Kapitel wählen,
verschieben. Auch in ein Kapitel, das es noch nicht gibt — Nummer
eintippen, es wird angelegt. Und wieder heraus, »ohne Kapitel« ist ein
gültiges Ziel.

Dabei steht ein Hinweis, der kein Kleingedrucktes ist: **das Kapitel
entscheidet mit, wann ein Wort drankommt.** An ihm hängt die
Lektionsschranke. Darum sagt die Meldung hinterher auch, wie viele
Aufgaben sich dadurch geändert haben.

### Ein leeres Lernziel sagt jetzt, warum

»Da ist ein neues Lernziel, nur Verben, Reihen — es kommen aber keine
Übungen, obwohl eigentlich 19 Verben da sein sollten.«

Das Ziel stand mit **»0 von 0«** da und schwieg. Jetzt steht die
Begründung daneben, und sie geht von außen nach innen: kein Wort im
Ausschnitt? Die Sammlung erzeugt diese Aufgabenart gar nicht? Die
Aufgaben sind da, aber abgeschaltet? Oder hält sie die
Lektionsschranke zurück?

Der Satz, über den man stolpert: **ein Lernziel schränkt ein, es
erzeugt nicht.** Ein Ausschnitt aus nichts bleibt nichts — und wer
»Ganze Reihe« verlangt, bekommt nichts, solange die Sammlung diese
Aufgabenart nicht anhakt.

### »Ein« ist keine Frage

»Eine, eines, mia, ena, enas, ta, to — die ganzen Artikel. Ich weiß
sie, aber anhand der Fragen weiß ich nie, welcher gemeint ist.«

Nachgesehen: sie hat recht, und es lag nicht an ihr. Die Frage lautete
wörtlich **»ein«** — richtig war je nach Geschlecht ένας, μία oder
ένα. **»die«** führte auf sieben verschiedene Wörter. Was zur
Unterscheidung dastand, war entweder nichts, oder ein Kürzel (»n«,
»m«), oder dieser Satz:

> ihr: ihr (2. Person Plural, Subjekt); Sie: Sie (höflich) / ihr

Das ist keine Wissenslücke, das ist eine unbeantwortbare Frage — und
der Lernplan hat daraus gelernt, dass sie die Wörter nicht kann.

Jetzt steht die **Bestimmung in der Frage**: »ein *(Nominativ Singular
neutrum)*«, »die *(Nominativ Plural neutrum)*«, »ihr *(2. Person
Plural)*«. Sie kommt aus den Merkmalen des Wortes, wird beschriftet wie
überall sonst und folgt dem eingestellten Stil — wer »einfach«
eingestellt hat, liest »wer oder was?, Mehrzahl, sächlich«.

Drei Regeln dahinter:

- **Nur wenn es etwas zu verwechseln gibt.** Bei »das Haus« wäre
  »neutrum« Lärm; das sagt der deutsche Artikel schon.
- **Die Merkmale schlagen den Freitext.** Sagen sie es, verschwindet
  der Kontext aus der Frage — sonst stünde beides nebeneinander.
- **Was die Frage nicht sagt, darf die Wertung nicht verlangen.** μία
  und μια sind beide Nominativ Singular feminin; dort gelten weiterhin
  beide Antworten. Und ein Wort, bei dem die Merkmale noch fehlen,
  bleibt gültig — es macht die Frage für die anderen aber nicht wieder
  blind.

Dazu sind die Merkmale für die griechischen Artikel und Pronomen
nachgetragen: 41 Wörter, das ganze Paradigma.

### Punkte und Stufen

Punkte gibt es **fürs Drankommen, nicht fürs Richtigliegen**: je
Aufgabe und Tag einmal, gleich wie es ausging. Das ist die wichtigste
Entscheidung an der ganzen Sache. Hingen sie am »richtig«, lohnte es
sich, sich selbst großzügig zu bewerten — und der Schaden wäre nicht
der erschlichene Punkt, sondern ein verdorbener Terminplan.

Dieselbe Karte fünfzigmal durchzuklicken bringt deshalb genau zehn
Punkte. Einen Tagesdeckel braucht es dafür nicht; die Form der Vergabe
ist schon die Grenze.

Am meisten bringt, was **dauerhaft sitzt** (25) — der einzige Posten,
den kein Nachmittag holt, weil dorthin nur ein Intervall von drei
Wochen führt. Dazu 5 fürs erste Mal und 50 fürs erreichte Tagesziel.

Neun Stufen, benannt nach dem Weg durchs Lesen: *Buchstaben, Wörter,
Sätze, Absätze, Seiten, Kapitel, Bücher, Regal, Bibliothek.* Die Stufe
**fällt nie** — ein Rang, der sinkt, weil man krank war, ist eine
Strafe mit Konfetti. Wie es wirklich steht, sagt weiterhin der
Wortschatz im Fortschritt, und der geht in beide Richtungen.

Gerechnet aus dem Protokoll, nichts mitgeschrieben. Darum fängt
niemand bei null an.

### Zuspruch — jemandem etwas schicken

»Auch möchte ich meiner Tochter Boosts schicken können.«

Unter **Zuspruch schicken** auf der Übersicht. Vier Arten:

- **Botschaft** — ein Satz, der beim nächsten Öffnen oben steht.
- **Doppelte Punkte** — für einen Tag, den sie sich selbst aussucht.
  Wer ihn für einen großen Tag aufhebt, hat mehr davon.
- **Joker** — ein Fehltag mehr, den die Strähne diesen Monat mitträgt.
- **Versprechen** — »Lernziel bis Freitag → Kino«.

Das Versprechen ist das Stärkste und zugleich das Dümmste: die App
rechnet daran nichts aus und schenkt nichts. Sie merkt sich den Satz
und sagt hinterher, dass er fällig ist. **Die Belohnung kommt nicht aus
der App** — genau darum wirkt sie. Abhaken kann nur, wer sie gegeben
hat.

Beim Empfänger steht alles ganz oben auf der Übersicht, vor den
fälligen Aufgaben: ein Satz von der Mutter ist wichtiger als eine Zahl.

Schicken darf, wer eine Sammlung mit der Person teilt, und höchstens
fünfmal am Tag an dieselbe — aus Zuspruch im Dutzend wird
Hintergrundrauschen. Zurückziehen geht, solange es niemand gelesen hat;
danach nicht mehr.

Auch **über den MCP**: »Schick Lernende 2 einen Boost für morgen« genügt.
In fremde Postfächer sehen darf dabei nur, wer verwalten darf — »schick
Lernende 2 etwas« soll nicht heißen »lies, was Lernende 2 bekommen hat«.

Weder Verdoppler noch Joker schreiben etwas ins Protokoll. Sie ändern
nur, wie es ausgewertet wird. Es darf nie zwei Wahrheiten über
denselben Tag geben.

### Von außen 30 Tage angemeldet bleiben

Die Cloudflare-Sitzung stand auf 24 Stunden — wer von außen kam,
brauchte täglich einen neuen Mailcode. Jetzt 30 Tage, wie bei einer
Mailbestätigung üblich. Betrifft nur den Vokabeltrainer; Fotos und
Rezepte stehen weiter auf 24 Stunden.

### Ein Ring für den Tag, eine Zahl für die Tage

»Wir brauchen auf jeden Fall einen Streak.«

Oben in der Kopfzeile steht jetzt ein **Ring**: dein Tagesziel. Er
füllt sich mit jeder Antwort und bekommt einen Haken, wenn das Pensum
aufgegangen ist. Daneben die **Strähne** — wie viele Tage in Folge du
sie geschafft hast.

Die Tagesdosis war längst eingestellt und stand nirgends; man erfuhr
erst am Ende der Abfrage, dass man sie erreicht hatte. Der Ring steht
oben und nicht in der Übersicht, weil die Übersicht während der
Abfrage gar nicht zu sehen ist — und gerade dann zählt er hoch.

### Die Strähne zählt jetzt etwas anderes

Es gab schon eine, im Fortschritt. Sie zählte Tage mit **mindestens
einer Antwort**, innerhalb eines Fensters von dreißig Tagen. Beides
war falsch: eine einzige Karte genügte für einen gelernten Tag, und
über 30 kam die Zahl nie hinaus — nach zwei Monaten Disziplin stand da
dasselbe wie nach einem.

Jetzt zählt ein Tag, wenn das **Tagesziel aufgeht** — eine neue
Einstellung, vorbelegt mit 20 Antworten. Das ist ausdrücklich **nicht**
die »Fragen je Tag höchstens«, die es schon gab: die ist eine
Obergrenze und steht absichtlich hoch (bei einem Lernziel mit nahem
Termin setzt der Helfer sie noch höher, bei Lernende 2 auf 224). Der erste
Entwurf hat die Strähne daran gemessen und fiel an den echten Daten
sofort durch: Strähne 0, obwohl an vier Tagen hintereinander 29 bis 123
Fragen beantwortet worden waren. Eine Latte, die niemand erreicht, ist
keine. Oder wenn nichts
mehr fällig war: an einem Tag mit drei fälligen Aufgaben darf die
Strähne nicht reißen, sonst erzieht der Trainer dazu, gegen den
eigenen Terminplan zu arbeiten.

Und **zwei Fehltage im Monat trägt sie mit**. Ohne das reißt eine
Strähne beim ersten Grippetag, und wer 23 Tage verloren hat, fängt
nicht wieder bei eins an — er hört auf. Der dritte Fehltag reißt sie
trotzdem, sonst wäre die Zahl geschenkt. Überbrückte Tage werden
genannt und nicht verschwiegen.

Gerechnet wird alles aus dem Protokoll, nichts wird mitgeschrieben.
Darum fängt niemand bei null an: wer schon gelernt hat, hat auch schon
eine Strähne.

### Am Ende der Runde steht, was sich geändert hat

Bisher stand dort, wie viel getippt wurde — 24 Aufgaben, so und so
viele richtig. Das ist eine Leistungsmessung, kein Grund
weiterzumachen, und morgen steht dieselbe Zahl da.

Jetzt kommt dazu: was **dauerhaft sitzt**, was **neu angefangen** ist,
was aus dem Verlernten **zurückgeholt** wurde — und wie die Strähne
steht. Ist nichts davon passiert, steht auch nichts da; eine Zeile,
die »0 Aufgaben sitzen jetzt dauerhaft« schreibt, erzieht dazu, die
Stelle zu überlesen, an der später etwas Gutes steht.

Der nützlichste Satz ist der letzte: *»Noch 6 Fragen bis zum
Tagesziel — dann steht die Strähne bei 6 Tagen.«*

### Keine Punkte für richtige Antworten

Eine Entscheidung, die man nicht sieht, die aber alles Weitere
bestimmt: **belohnt wird Erscheinen, nicht Trefferquote.** Gezählt
werden bearbeitete Aufgaben, gleich wie sie ausgingen.

Der Grund: bei längeren Antworten bleibt die Einschätzung beim
Menschen. Hinge daran ein Punktestand, entstünde genau dort ein Anreiz
zu schummeln — und der Schaden wäre nicht der erschlichene Punkt,
sondern ein verdorbener Terminplan. Großzügig bewertete Wörter legt
der Trainer weit weg, und vor der Arbeit ist nichts mehr da. Die
Trefferquote wird gezeigt, aber nicht bepunktet.

### Wiederholen, ohne dass Neues dazukommt

»Haben wir eigentlich auch eine Art Wiederholungsmodus?«

Halb: **Frei üben** und **Fehler wiederholen** standen schon in der
Übersicht, und der Lernkern konnte zusätzlich »nur Fälliges, nichts
Neues« — nur führte dorthin kein Knopf. Jetzt gibt es
**Wiederholen**, mit der Zahl daneben.

Der Unterschied zu »Lernen« ist nicht kosmetisch: planmäßig kommt
Neues dazu, sobald Platz in der Tagesdosis ist. Wer vor einer Arbeit
steht oder wenig Zeit hat, will genau das nicht — er will festigen,
was schon angefangen ist.

### Gelöschte Lernziele nehmen nichts mit

»Wenn ich die mal lösche, sind sie ja quasi weg.«

Sind sie nicht. Der Fortschritt eines Lernziels ist **nirgends
gespeichert** — er wird bei jedem Aufruf aus dem Lernstand gerechnet.
Gelöscht wird nur das Ziel selbst: Name, Ausschnitt, Termin. Keine
Tabelle verweist darauf, kein Lernstand hängt daran. Ein Test hält
das fest: er zählt vor und nach dem Löschen und verlangt, dass sich
nichts rührt.

Allgemeine Statistiken gibt es übrigens auch schon — **Fortschritt**
in der Übersicht, neben »Lernen«. Antworten je Tag, Trefferquote,
Strähne, wo der Wortschatz steht, was in den nächsten Wochen fällig
wird und wie schnell man antwortet.


### Die KI kann jetzt Lernziele anlegen

»Könnte ich das dem angeschlossenen Claude geben, um eine Sammlung
aus genau den Wörtern zu erstellen, die in den zwei Fotos meiner
Tochter enthalten sind, aus denen sie dann ein Lernziel machen kann?«

Die Antwort ist: ja — aber **ohne neue Sammlung**. Ein Lernziel nimmt
im `umfang` das Feld `lexeme`, also genau diese Wörter. Eine eigene
Sammlung dafür wäre der Umweg: sie verdoppelt die Wörter und teilt
den Lernstand, und beim nächsten Test ginge es wieder von vorn los.

Gefehlt hat nur das Werkzeug. Die KI konnte Wörter anlegen und
suchen, aber kein Ziel daraus machen — das hätte von Hand gebaut
werden müssen, mit Lexem-Kennungen, die in der Oberfläche nirgends
stehen. Neu sind `lernziel_anlegen` und `lernziele_auflisten`.

Ein Ziel über fremden Bestand wird abgelehnt: ohne diese Prüfung
ließe sich eines über Wörter legen, die einen nichts angehen, und die
Abfrage zeigte sie dann.


### Gezielt lernen: Wort für Wort an und aus

»Meine Tochter muss genau die Vokabeln lernen, die sie mir als Liste
gegeben hat.«

Eine Sammlung wächst mit der Zeit; die Liste für die nächste Arbeit
ist ein Ausschnitt daraus. Bisher blieb nur, den Rest zu löschen oder
eine zweite Sammlung anzulegen — beides wirft weg, was schon gelernt
ist.

Neu in der Übersicht der Knopf **Auswahl**. Dort steht die Sammlung
Wort für Wort, mit Filtern nach Lektion, Wortart und »nur die
ausgeschalteten«, dazu Kästchen zum Stapelweise-Umschalten. Was
ausgeschaltet ist, bleibt im Wortschatz und deckt die Lesetexte
weiter ab — es wird nur nicht mehr abgefragt, und **der Lernstand
bleibt stehen**. Dieselbe Zusage wie bei einer abgewählten Zeitform.

Beim Anlegen kann die KI es gleich mitgeben: je Eintrag ein Feld
`abfrage` mit dem Namen einer **Abfragevorlage**. Zwei kennt jede
Sammlung von sich aus — `voll` und `nachschlagen` —, eigene lassen
sich in den Sammlungseinstellungen hinterlegen. Der Sinn der Namen
ist die spätere Änderung: wer die Bedeutung eines Namens ändert,
ändert alle Wörter mit, ohne eines anzufassen.

### Ein doppelter Schlüssel, der nichts sagte

Die neue Spalte kam auf einer bestehenden Datenbank nicht an: »no
such column«. In der Nachrüstliste stand `lexem` **zweimal**, und bei
einem doppelten Schlüssel im Wörterbuch gewinnt lautlos der spätere.
Auf einer frischen Testdatenbank war nichts zu sehen, weil die Spalte
dort aus dem Schemaskript kommt — der Fehler konnte nur im Betrieb
auffallen.

Zusammengeführt, und ein Test liest die Liste jetzt im Quelltext
nach: keine Tabelle darf zweimal darin stehen.

## 16.11.2026

### »wie geht es euch« galt als falsch

Zu merken war: bei »πώς είστε« getippt, abgewiesen — und darunter
stand als richtige Lösung »wie geht es Ihnen / euch?«.

Die Pflege war schuld, nicht die Prüfung. Der Eintrag hatte **eine**
Übersetzung, in der zwei Varianten mit einem Schrägstrich
zusammengefasst waren. Der Trainer nimmt jede hinterlegte Übersetzung
als richtig an — aber nur als Ganzes. Wer eine der beiden Varianten
tippt, bekommt ein »falsch« für eine Antwort, die stimmt.

Im ganzen Bestand waren es sechs solche Einträge, alle aus einem
frühen KI-Import (`πώς είστε`, `γεια σας`, `γεια σου`, `στο`, `στον`,
`που`). Sie sind in getrennte Übersetzungen zerlegt; »wie geht es
euch« und »wie geht es Ihnen« zählen jetzt beide, »wie geht es dir«
weiterhin nicht.

Damit es nicht wiederkommt — die KI legt ja laufend Einträge an —
meldet die Qualitätsprüfung einen Schrägstrich in der Übersetzung
jetzt als Hinweis.


### Kapitel 101 eingespielt — und drei Dinge dabei gelernt

Das Paket aus `kapitel101.zip`: **550 neue Wörter mit 7.216 Formen**,
dazu 123 Formen für 55 Wörter, die es schon gab, und 767 abgehakte
Wortwünsche. Die Deckung des Artikels ist damit von 27 % auf **98 %**
gestiegen — von 840 unbekannten Wörtern sind 24 übrig.

Vor dem ersten Schreibzugriff ein Abzug nach
`daten/abzug/vor-kapitel101-…`; er hat sich noch am selben Abend
bezahlt gemacht, siehe unten.

### Wortwünsche: ein Sammelwerkzeug zum Abhaken

Einzeln abzuhaken wären bei einem Zeitungsartikel über achthundert
Aufrufe gewesen — länger als das Eintragen selbst. `POST
/api/wortwuensche/abhaken` und das MCP-Werkzeug
`offene_woerter_abhaken` nehmen jetzt eine ganze Liste.

**Beim ersten Lauf an echten Daten ging es schief**, und der Grund ist
lehrreich: im griechischen Artikel stehen deutsche Zitate, also stand
»ich« auf der griechischen Wunschliste — und hakte das gleichlautende
»ich« in Max' mittelhochdeutscher Liste gleich mit ab. 89 fremde
Wünsche auf einen Schlag. Aus dem Abzug wiederhergestellt und gegen
ihn geprüft; der Abgleich bleibt jetzt in einer Sammlung, und wo das
Wort in mehreren offen steht, wird nichts geraten, sondern gemeldet.

### Großbuchstaben und Enklise im Textabgleich

Zwei Rechtschreibregeln, die bisher als Wissenslücke gezählt wurden:

**Griechische Großbuchstaben tragen keinen Akzent.** Zeitungen
schreiben »Ηταν«, »Ελληνας«, »Οχι«; im Wortschatz steht ήταν,
Έλληνας, όχι. Das waren zwölf der verbliebenen Unbekannten.

**Enklise.** »το πελατολόγιό του« — das Substantiv trägt einen
zweiten Akzent, den das angehängte Wörtchen erzwingt.

Beides gilt nur dort, wo es eindeutig ist: wo zwei Wörter sich allein
im Akzent unterscheiden (»πότε« wann, »ποτέ« nie), wird nichts
zugeordnet. Ein falsch erkanntes Wort im Lesetext ist schlimmer als
ein als unbekannt gemeldetes — das eine merkt man, das andere nicht.

## 15.11.2026

### Die KI sieht jetzt auch die Wünsche der anderen

»Der Konnektor im ChatGPT war für Max gedacht, der nutzt den gleichen
Zugang. Das heißt, der müsste dann auch Anforderungen von Max
abholen.«

Bisher zeigte die Wunschliste nur die eigenen. In einer Familie hängt
der Zugang aber an **einem** Profil, während die Wünsche an **allen**
entstehen: Max markiert Wörter in seinem mittelhochdeutschen Text,
und die KI, die über ihr Zugang spricht, sah davon nichts —
obwohl Annuschka in Max' Sammlung schreiben darf und die Wünsche also
erfüllen *kann*.

Die Regel heißt deshalb jetzt nicht mehr »meine Wünsche«, sondern:
**was ich erfüllen darf, soll ich auch sehen.** Mitgenommen werden
Wünsche anderer aus Sammlungen mit Schreibrecht — bei bloßem
Leserecht nicht, denn eine Liste, die man nicht abarbeiten kann, wird
nie kürzer.

Bei jedem Eintrag steht, wer ihn gestellt hat (`angefordert_von`),
damit die KI weiß, für wen sie arbeitet. Und abhaken darf man fremde
Wünsche ebenfalls — sonst kämen sie bei jedem Abruf wieder.


### Eine große Wunschliste verdeckte eine kleine

»Die 89 neuen mittelhochdeutschen Wörter werden mir noch nicht
angezeigt.«

Sie waren da. Die Liste steht aber nach Häufigkeit, und zwar **quer
über alle Sammlungen**: bei 825 griechischen und 89
mittelhochdeutschen Wünschen bestand das Häppchen von 40 aus vierzig
griechischen. Die KI sah nach, fand kein mittelhochdeutsches Wort und
schloss daraus, es gebe keines.

Die Häppchen waren richtig — 840 Wörter in einer Antwort hieße, dass
die KI den Anfang vergessen hat, bevor sie am Ende ist. Falsch war,
dass die Antwort nichts über das sagte, was sie **nicht** zeigt. Jetzt
nennt sie immer, welche Sammlungen etwas offen haben, auch die ohne
Eintrag im Häppchen:

```
offen_nach_sammlung: {"Griechisch": 825, "Mittelhochdeutsch": 89}
```

Dazu der Satz, dass die Reihenfolge über alle Sammlungen gilt und man
für eine bestimmte die `sammlung_id` mitgeben soll.


### Abtippen: kein Überspringen mehr, außer man hat es versucht

»Lernende 2 möchte für den Abtippen-Modus, dass sie gezwungen wird, die
Wörter zu tippen, auch wenn sie diese schon kennt.«

Der Knopf **Überspringen** ist weg — und erscheint erst, wenn bei
dieser Karte einmal getippt wurde und es nicht gestimmt hat. Wer die
Vokabel kennt, kommt also nicht daran vorbei; wer an einem Eintrag
mit unttippbaren Zeichen hängt, schon.

Ganz ohne Ausweg wäre es keine Strenge, sondern eine Falle: eine
Übung, aus der man nur durch Schließen des Reiters herauskommt, macht
niemand ein zweites Mal.


### Das Protokoll sagt jetzt, was die KI tut

»Er verbessert gerade die bestehenden Einträge« — 43 Aufrufe in
siebzig Sekunden, und in der Datenbank änderte sich **keine einzige
Zeile**. Im Zugriffsprotokoll stand nur `POST /mcp 200`, denn ein
**gescheiterter** Werkzeugaufruf kommt bei MCP ebenfalls mit 200
zurück; der Fehler steckt in der Antwort. Damit ließ sich nicht
unterscheiden, ob die KI liest, ob sie schreiben will und abgewiesen
wird, oder ob sie etwas erzählt, was sie gar nicht tut.

Jetzt wird jeder Werkzeugaufruf mitgeschrieben: wer, welches Werkzeug,
und ob es geklappt hat — bei einem Fehler dessen Text. Auch ein
Werkzeug, das es gar nicht gibt: ein Agent mit falscher Vorstellung
vom Server fiel sonst nirgends auf.

**Nicht** mitgeschrieben werden die Argumente. Die enthalten ganze
Vokabeleinträge und bei den Lesetexten halbe Privatlektüre; das
gehört nicht ins Serverprotokoll. Ein Test hält das fest.

Beim ersten Lauf blieb das Protokoll trotzdem leer: ohne gesetzten
Pegel verwirft Python alles unterhalb von WARNING, und die Aufrufe
sind INFO. Auch das ist behoben — und im Container nachgemessen,
nicht nur im Test.


### Die openid-Adresse antwortet — verspricht aber nichts

Jeder ChatGPT-Durchlauf endete gleich, über mehr als eine Stunde
hinweg:

```
GET /.well-known/oauth-protected-resource     200
GET /.well-known/oauth-authorization-server   200
GET /.well-known/openid-configuration         404   ← und dann Schluss
```

Das ausgegebene Token blieb dabei unbenutzt. Damit war die Adresse
der einzige verbliebene Verdacht.

Der Trainer spricht **kein OpenID Connect**: er gibt keine
Identitätstoken aus, hat keinen Schlüsselsatz und weiß vom Menschen
nur die Mailadresse, die Cloudflare Access geprüft hat. Trotzdem
antwortet er dort jetzt — mit genau denselben Angaben wie im
OAuth-Blatt und mit **keiner einzigen** darüber hinaus. Die Felder,
die OpenID Connect verlangt und die hier gelogen wären (`jwks_uri`,
`id_token_signing_alg_values_supported`, `subject_types_supported`),
fehlen bewusst. Wer echtes OpenID Connect braucht, sieht das und
scheitert sichtbar, statt auf ein Identitätstoken zu warten, das nie
kommt. Ein Test hält fest, dass diese Felder nicht hineinwandern.


### Anmeldung geglückt, Werkzeugliste gescheitert

Der ganze OAuth-Ablauf lief durch — Weiterleitung, Access-Anmeldung,
Einwilligung, Token:

```
GET  /mcp/oauth/authorize    302
GET  /oauth/authorize        200     Einwilligungsseite
POST /oauth/authorize        303     »Erlauben« gedrückt
POST /mcp/oauth/token        200     Token ausgegeben
```

Danach meldete ChatGPT »authentication successful, action discovery
failed«, und im Protokoll stand sofort der Grund:

```
GET /.well-known/oauth-protected-resource   404   ← die hatte ich entfernt
```

In der Autorisierungsanfrage stand auch, warum es gerade diese Stelle
abfragt: `resource=https://mcp.<domain>` — **ohne** `/mcp`. ChatGPT
hält den ganzen Namen für die Ressource, nicht den Pfad.

Diese Stelle gab es einmal und ich hatte sie entfernt, weil darin eine
Ressource mit Pfad stand und ein Blatt, dessen Inhalt nicht zu seiner
Adresse passt, schlimmer ist als keines. Die Lehre war richtig, die
Folgerung falsch: gebraucht wurden nicht weniger Blätter, sondern je
Adresse das passende. Beide Lesarten sind zutreffend — der Trainer ist
über diesen Namen erreichbar, und sein MCP-Endpunkt liegt unter
`/mcp`. Jetzt nennt jedes Blatt die Ressource, die zu seiner eigenen
Adresse gehört.


### Die Einwilligungsseite nannte das Falsche

Vor dem ersten echten Durchlauf habe ich die Seite probeweise geladen.
Dort stand:

```
Dein Profil        ChatGPT Max      ← das ist der Konnektor, nicht sie
```

An der Aufrufstelle standen zwei Wörterbücher mit je einem Feld
`name` in der falschen Reihenfolge. Auf der einen Seite, deren
ganzer Zweck es ist zu zeigen, **wer** auf **wessen** Daten zugreifen
darf, ist das der schlimmstmögliche Fehler: eine Einwilligung, die
das Falsche nennt, ist keine.

Berichtigt, und die Argumente lassen sich jetzt nur noch **benannt**
übergeben — damit dieselbe Verwechslung nicht wiederkommt. Ein Test
hält fest, dass das Profil den Menschen nennt und der Name den
Konnektor; mit vertauschten Argumenten fällt er.

Nebenbei zeigte das Protokoll, dass die Berichtigung am Kennblatt
gewirkt hat: ChatGPT läuft die Suche nicht mehr in der Schleife,
sondern einmal durch und bleibt dann stehen.


### Warum ChatGPT das Kennblatt holte und trotzdem weitersuchte

Im Serverprotokoll stand die Antwort, zweimal dieselbe Schleife im
Abstand von fünf Sekunden:

```
POST /mcp                                        401   wie vorgesehen
GET  /mcp/.well-known/oauth-protected-resource   200   folgt der Kopfzeile
GET  /.well-known/oauth-authorization-server/mcp 200   findet das Blatt
GET  …/openid-configuration  (drei Schreibweisen) 404
→ und von vorn
```

Es **bekam** das Blatt und suchte danach trotzdem weiter. Also hat es
das Blatt verworfen, und dafür gab es zwei Gründe — beide von mir:

**Der Herausgeber passte nicht zur Adresse.** RFC 8414 verlangt, dass
der im Blatt genannte Herausgeber genau zu der Stelle passt, an der es
liegt. Unter `/.well-known/oauth-authorization-server` heißt der
Herausgeber `https://mcp.…`, im Blatt stand aber `https://mcp.…/mcp`.
Dass ich den Pfad hineingeschrieben hatte, war ein Umweg um das
Tunnelproblem — auf Kosten der Richtigkeit, und es hat sich gerächt.
Seit die Tunnelroute steht, braucht es den Umweg nicht mehr.

**Der Autorisierungsendpunkt lag auf einem anderen Namen** als der
Herausgeber. Erlaubt, aber ungewöhnlich. Er liegt jetzt auf
demselben Namen und leitet von dort dorthin weiter, wo Cloudflare
Access die Anmeldung macht — am Ablauf ändert das nichts, am Blatt
schon.

Ein Blatt an der falschen Stelle ist schlimmer als keines: es wird
geholt, geprüft, verworfen, und die Suche beginnt von vorn. Darum
liegen die Blätter jetzt nur noch dort, wo sie hingehören, und die
früher zusätzlich bedienten Stellen antworten wieder mit 404.


### Die Anmeldeangaben stehen jetzt an allen drei Stellen

Nachdem der Tunnel `/.well-known` durchlässt, wurde eine dritte
Schreibweise sichtbar, die vorher unter Cloudflares leerem 404
verborgen war: hat der Herausgeber einen Pfad — hier `/mcp` —, schiebt
RFC 8414 ihn **hinter** den `.well-known`-Teil
(`/.well-known/oauth-authorization-server/mcp`). Dasselbe tut RFC 9728
für die Ressource. Genau das ist bei dieser Anlage die eigentlich
vorgeschriebene Stelle, und sie fehlte.

Alle drei Schreibweisen antworten jetzt, für beide Blätter. Das kostet
sechs Zeilen und erspart die Suche nach dem Grund, warum ein Konnektor
ablehnt, ohne den Server je zu fragen.

Von außen nachgemessen: sechsmal 200. Und `/api` über diesen Namen
weiterhin 0 Byte — die neue Tunnelroute öffnet nichts außer
`.well-known`.


### ChatGPT lehnte die Einrichtung ab — zwei Ursachen

**»Ich glaube, die Callback-URL wird nicht gespeichert.«** Sie wurde,
sogar zweimal. Das war ein Fehler meiner Oberfläche: sie leerte das
Feld nach dem Anlegen und zeichnete die Liste nicht neu, also sah es
aus, als sei nichts passiert. Jetzt bleibt das Feld stehen, der Knopf
schaltet auf »Angelegt«, und im Bestätigungskasten steht, was
gespeichert wurde — Name und Rückadresse im Klartext.

**»Einige App-Einstellungen wurden abgelehnt.«** Im Serverprotokoll
stand keine einzige Anfrage von ChatGPT: es kam nie bis hierher. Der
Grund ist der Tunnel. Ein Konnektor sucht die Anmeldeangaben an vier
vorgeschriebenen Stellen unter `/.well-known/…`, und die sind auf dem
Namen der Schnittstelle alle gesperrt — nur `/mcp` kommt durch.
Nachgemessen:

```
404  /.well-known/oauth-protected-resource/mcp      0 Byte  ← Cloudflare
404  /.well-known/oauth-authorization-server        0 Byte  ← Cloudflare
200  /mcp/.well-known/oauth-authorization-server  405 Byte  ← der Server
```

Dafür gibt es einen vorgesehenen Ausweg, den ich nicht gebaut hatte:
die Kopfzeile **`WWW-Authenticate`** auf der Abweisung. Mit ihr sagt
der Server selbst, wo seine Angaben stehen, statt den Client raten zu
lassen. RFC 9728 sieht sie vor, die MCP-Spezifikation verlangt sie —
und hier ist sie der einzige Weg. Dazu nennt sich die Schnittstelle
jetzt **mit Pfad** als Herausgeber, damit auch der zweite Suchweg
(`<Herausgeber>/.well-known/…`) auf der erreichbaren Stelle landet.

Die ganze Kette liegt damit innerhalb von `/mcp` und kommt ohne
Änderung bei Cloudflare aus. Ein Client, der auf der dritten
vorgeschriebenen Schreibweise besteht, braucht sie trotzdem — wie das
geht, steht in `deploy/cloudflared/LIESMICH.md`, samt der Warnung,
die Pfadbeschränkung nicht einfach zu entfernen: dahinter liegt
`/api`, und das hat keine Anmeldung.


### Abtippen — ein Modus zum Vertrautmachen

»Alle Vokabeln zeigen, deutsch französisch und abtippen, erfolgreich
abgetippt, dann nächste. Sie muss sich erst mal mit den Wörtern
vertraut machen.«

Neben **Lernen** steht jetzt **Abtippen**. Es geht alle Wörter einer
Sammlung durch, in der Reihenfolge des Lehrwerks: deutsche Seite oben,
das fremde Wort groß darunter — sichtbar, es ist eine Vorlage und kein
Rätsel. Richtig abgetippt springt es von selbst weiter; die
Eingabetaste genügt, man muss die Hände nicht von der Tastatur nehmen.
Falsch abgetippt passiert fast nichts: es steht da, was abweicht
(»Ein t fehlt«), und man tippt weiter. Kein Fehlerzähler.

**Es wird dabei kein Lernstand geschrieben** — keine Note, kein
Termin, kein Eintrag im Protokoll. Das ist der Kern und nicht eine
Auslassung: die Abfrage fragt ab, was man kennt, und rechnet daraus
einen Termin. Wer ein Wort zum ersten Mal sieht, hat darauf keine
Antwort, und eine abgeschriebene Vokabel als »gewusst« zu verbuchen
würde den Plan genau für die Wörter verfälschen, die noch niemand
kann. Es steht auch auf der Seite, damit niemand sich täuscht.

Geprüft wird trotzdem genau, mit dem Sprachprofil: `l'ete` statt
`l'été` gilt nicht. Beim Abtippen ist die Vorlage ja sichtbar, also
ist jede Abweichung ein Vertipper — und gerade den soll man sehen. Die
Akzentleiste steht darunter wie in der Abfrage.

Wörter, die noch niemand durchgesehen hat, werden **gekennzeichnet,
aber nicht weggelassen**. Der erste Entwurf wollte sie aussperren —
beim Abschreiben prägt sich auch eine falsche Schreibung ein. Das
hätte aber bedeutet, dass der Trainer ein Wort abfragt, das er zum
Abtippen verschweigt: die Vokabelabfrage entsteht allein daraus, dass
eine Übersetzung da ist. Zwei Maßstäbe für dieselbe Vokabel wären
schlimmer als ein Hinweis.


### OAuth — damit auch ChatGPT angebunden werden kann

Der Dialog »Benutzerdefinierten MCP-Server hinzufügen« in ChatGPT
kennt unter Authentifizierung nur **OAuth**, **keine
Authentifizierung** oder beides. Kein Feld für einen Schlüssel, und
auch keines für eine eigene Kopfzeile. Damit ging der Weg, den
claude.ai nimmt, dort nicht.

Die Alternative wäre gewesen, das Zugangsmerkmal in die Adresse zu
schreiben. Adressen landen in Protokollen — bei Cloudflare, auf dem
Server, im Verlauf. Also OAuth.

**Die Anmeldung des Menschen baut der Trainer dabei nicht selbst.** Das
ist der Kniff, der es klein hält: der Einwilligungsschritt liegt auf
der Adresse, hinter der Cloudflare Access steht. Access fragt
Mailadresse und Einmalcode, wie im Browser auch, und sagt dem Trainer,
wer gekommen ist. Keine Passwörter, keine Sitzungen. Und was am Ende
herauskommt, ist ein ganz gewöhnliches Zugangsmerkmal — die Prüfung an
der Schnittstelle blieb unverändert.

Eingerichtet wird es in den Einstellungen unter **Zugang für ChatGPT
(OAuth)**: Name und Callback-URL aus dem ChatGPT-Dialog eintragen,
Client-ID und Schlüssel zurückbekommen, beides dort einsetzen. Für
Claude braucht man das nicht — dort bleibt der einfachere Weg.

Absichtlich eng: PKCE ist Pflicht und nur S256, die Rückadresse muss
zeichengenau stimmen, der Code gilt zwei Minuten und einmal. Wird er
ein zweites Mal vorgelegt, hat ihn jemand mitgelesen — dann werden die
damit ausgegebenen Zugänge zurückgenommen. Sechzehn Tests, die
meisten davon für Dinge, die **nicht** gehen dürfen.

Dabei kam noch etwas heraus, das nirgends aufgeschrieben war: der
Tunnel lässt auf dem Namen der Schnittstelle nur den Pfad `/mcp`
durch, alles andere beantwortet Cloudflare selbst mit einem leeren
404. Die OAuth-Endpunkte hängen deshalb zusätzlich unter `/mcp` und
sind damit ohne jede Änderung bei Cloudflare erreichbar. Notiert in
`deploy/cloudflared/LIESMICH.md`, samt der Messung.


### Fehler von mir: die `.env` auf dem Server gelöscht

Beim Ausliefern habe ich `rsync --delete` von Hand benutzt und dabei
nur `daten` ausgenommen. Die `.env` auf dem Server steht
richtigerweise **nicht** im Repo — also sah rsync eine Datei, die es
hier nicht mehr gibt, und hat sie entfernt.

Folge: `VOKABEL_ACCESS_TEAM` war leer. Damit sieht der Trainer die von
Cloudflare Access geprüfte Mailadresse gar nicht erst an (so ist es
gebaut: ohne Team-Kennung wird die Kopfzeile ignoriert, weil sie sich
im Heimnetz fälschen ließe). Wer von außen kam, landete darum auf der
Profilliste statt in seinem eigenen Profil. Bestand und Lernstände
waren nie betroffen — `daten` war ausgenommen.

Wiederhergestellt. Beide Werte waren eindeutig rekonstruierbar: die
Team-Kennung steht in der Weiterleitung, die Access selbst schickt,
und die MCP-Adresse in der Anleitung.

Damit das nicht wiederkommt, gibt es jetzt
`werkzeuge/ausliefern.sh`: feste Ausnahmeliste für alles, was nur auf
dem Server lebt (`daten`, `.env`, `ZUGANGSDATEN*`), ein Probelauf, der
**vor** der Übertragung zeigt, was gelöscht würde und dann nachfragt,
und am Ende die Kontrolle, ob die Anlagewerte im Container noch
gesetzt sind.


### Ein Knopf zum Berichtigen

»Wir müssen die Datensätze natürlich auch mal überarbeiten können.
Dafür fehlt ein Knopf!«

Es gab **Löschen** und **Bestätigen**, aber kein **Ändern**. Ein
Tippfehler in einer Form war nur zu beheben, indem man sie löscht und
neu anlegt — und dabei war der Lernstand weg. Bei einem Bestand, den
zum großen Teil die KI gefüllt hat, ist das die falsche Richtung:
berichtigen wird häufiger gebraucht als wegwerfen.

Drei Stellen haben jetzt einen:

- **Oben beim Wort** — Lemma und die Merkmale, die am Wort hängen.
  Beschriftet mit ihrem richtigen Namen: »Ablautreihe«,
  »Deklinationsklasse«, »Geschlecht« statt `klasse` und `genus`.
- **Bei jeder Bedeutung** — Übersetzungen ergänzen und entfernen, dazu
  der Erklärsatz. Die letzte Übersetzung lässt sich nicht entfernen:
  ohne sie gäbe es keine Abfrage mehr.
- **Bei jeder Form** — Schreibung und Bestimmung, aufklappend in der
  Zeile selbst. Eine falsch eingeordnete Form (»zweimal Genitiv
  Singular«) gehört umgehängt, nicht gelöscht.

Was dabei mit dem Lernstand passiert, steht jetzt auch dort, weil es
zwei verschiedene Dinge sind: eine berichtigte **Schreibung** behält
ihn — der Aufgabenschlüssel nennt das Merkmalsbündel, nicht die Form.
Eine andere **Bestimmung** nicht: der Lernstand gehört der Zelle. Was
man unter »du schreibst« gelernt hat, hat man nicht unter »er
schreibt« gelernt, und war die Zuordnung falsch, war auch das Gelernte
falsch. Die alte Zelle bleibt dabei stehen, falls man es zurücknimmt.

Beides setzt die Form auf **ungeprüft** zurück. Was geändert wurde,
ist nicht mehr das, was jemand freigegeben hat.


### Zwei neue Abfragen: Stammformen und Klasse bestimmen

»Kann man auch Grammatik für Mittelhochdeutsch abfragen? Keine
Ahnung, wie man so was machen sollte.«

Die mittelhochdeutsche Grammatik stand längst im Sprachprofil — die
vier Stammformen, die sieben Ablautreihen, die Deklinationsklassen,
die Artikeltabelle mit `der/diu/daz`. Abfragen ließ sich davon aber
ausgerechnet das nicht, wonach eine Klausur fragt.

**Stammformen.** `nëmen – nam – nâmen – genomen` ist keine Formgruppe,
sondern eine Auswahl quer durch vier, und jede davon hat nur eine
Zelle. Die »Ganze Reihe« verlangt mindestens zwei Zellen je Gruppe —
also fiel ausgerechnet die Reihe durch, die man auswendig lernt. Es
gibt sie jetzt als eigene Abfrage: alle vier Formen auf einmal,
beschriftet mit den Gruppennamen. Sie gilt auch für Englisch,
Französisch, Spanisch und Deutsch, die ihre Stammformen ebenso im
Profil stehen haben — die unregelmäßigen Verben also als Tabelle statt
einzeln.

Die Reihe hängt an der **letzten** beteiligten Formgruppe, nicht an
keiner. Das klingt nebensächlich und ist es nicht: sie enthält das
Präteritum, und ohne diese Bindung käme sie, bevor das Lehrwerk das
Präteritum eingeführt hat — genau der Fehler, den du beim
griechischen Aorist hattest.

**Klasse bestimmen.** Die Ablautreihe steht als Merkmal am Verb, mit
fester Werteliste — genau das, was eine Auswahlfrage braucht. Fragen
ließ sich bisher nur das Geschlecht, und das fest verdrahtet als
Artikel. Jetzt ist jedes Lexemmerkmal mit fester Werteliste abfragbar;
das Geschlecht behält seine eigene Abfrage, weil es als »diu« gefragt
wird und nicht als »f«. Die Frage lautet dabei nicht »Welche Klasse?«,
sondern was im Profil dazu steht: **»Welche Ablautreihe?«** beim Verb,
**»Welche Deklinationsklasse?«** beim Substantiv.

Beide sind nicht voreingestellt — du schaltest sie in den
Sammlungseinstellungen ein, dann werden die Aufgaben für alles
nachgerechnet, was schon drinsteht.


### »Zählt nicht« neben neun von neun Wörtern

Zu merken war: eine Übersetzung, die mit der hinterlegten Fassung
Wort für Wort übereinstimmte, bekam »Richtig — 9 von 9 Wörtern« und
daneben die Marke **zählt nicht**; darunter musste man noch einmal
von Hand bestätigen, dass es richtig war. »Wie kommt das? Es ist doch
sogar wortgleich?«

Bei einem längeren Text schätzt die Lernende selbst ein, und das aus
gutem Grund: eine freie Übersetzung trifft die Referenz selten
wörtlich, ein Zeichenkettenvergleich wäre dort ein schlechter
Richter. Nur gilt die Begründung nicht mehr, wenn sie wörtlich
getroffen hat. Dann ist nichts mehr einzuschätzen.

Wortgleiches zählt jetzt also auch beim Text, ohne Nachfrage. Die Tür
geht nur in diese eine Richtung auf: eine Antwort, die **nicht**
wörtlich trifft, kann vollkommen richtig sein — dafür gibt es die
Selbsteinschätzung überhaupt —, und auch »fast« bleibt bei ihr. Im
Protokoll steht in diesem Fall »automatisch« statt
»Selbsteinschätzung«, denn gefragt wurde ja nicht; nachgerechnet wird
das am Server und nicht vom Browser geglaubt.

Ein Test hat genau das Gegenteil behauptet — mit einer wortgleichen
Antwort als Beispiel. Er hat den Fehler nicht gefunden, er hat ihn
festgeschrieben.

### Wort für Wort steht jetzt zwischen den Zeilen

Die Lesehilfe war eine Liste unter dem Absatz: »για für · μήνες der
Monat · των der«. Das ist eine Vokabelliste, und wer sie liest, sucht
danach im Satz die Stelle wieder, an der er war. Die unbekannten
Wörter kamen darin gar nicht vor — dabei sind genau die die Frage.

Jetzt steht die Bedeutung **über** dem Wort, an seinem Platz im Satz,
und jedes Wort bekommt seine Zeile darüber — auch das unbekannte,
dessen leere Oberzeile die eigentliche Auskunft ist. »Manche könnte
ich dann vielleicht auch erkennen aus dem Zusammenhang«: dafür muss
man sehen, wo die Lücke sitzt und was links und rechts davon bekannt
ist. Es ist dieselbe Darstellung, die ein Interlinearglossar seit
Jahrhunderten benutzt, und zwar aus demselben Grund.

Ausgeschaltet sieht der Absatz aus wie vorher; die Glosse kostet dann
keine Zeilenhöhe.

### Griechische Eigennamen gehören doch in den Wortschatz

Die Anweisung an den Chat sagte, Eigennamen seien auszulassen. Das
war für »AfD« richtig und für »Μπουτάκογλου« falsch: ein
griechischer Name ist für jemanden, der die Schrift erst lernt,
genauso unlesbar wie jedes andere Wort. »Die weiß ich ja auch
nicht.«

Jetzt gilt: Namen in der Schrift der Lernsprache werden angelegt, mit
der Umschrift und der Einordnung als Bedeutung (»Θεσσαλονίκη —
Thessaloniki, Stadt in Nordgriechenland«). Ausgelassen wird nur, was
ohnehin lateinisch dasteht.


### Einen ganzen Artikel auf einmal anfordern

Zu merken war: beim Einfügen eines Zeitungsartikels standen unter der
Deckungsanalyse hunderte Wörter, jedes mit einem eigenen Knopf. »Wenn
ich jetzt 260 mal klicke, macht das keinen Spaß.«

Gemessen am eingefügten Artikel: 1145 verschiedene Wörter, 840 davon
unbekannt, 27 % Deckung. Es gibt jetzt zwei Knöpfe in der
Deckungskarte — **Alle 840 unbekannten anfordern** und **Aus diesem
Text zurücknehmen**. Die Auswahl trifft der Server aus der Analyse,
die er ohnehin schon gerechnet hat; der Browser schickt nicht 840
Anfragen.

Dabei wird mitgezählt, wie oft jedes Wort im Text steht, und die
Liste ist danach geordnet. Bei 840 Einträgen ist die Reihenfolge das
Wichtigste: oben anfangen lohnt sich auch, wenn man nicht durchkommt.
Im Artikel kamen zuerst τη (22×), AfD (19×), στην (16×).

Was der Chat daraus liest, kommt jetzt in Häppchen von vierzig statt
in einem Block — achthundert Wörter in einer Antwort hieße, dass er
den Anfang vergessen hat, bevor er am Ende ist. Und zwei Fälle stehen
ihm ausdrücklich ins Werkzeug geschrieben, weil sie bei einem echten
Text die Mehrheit sind: eine **flektierte Form** eines Wortes, das
schon im Bestand steht, gehört an dieses Wort ergänzt und nicht als
zweites Lemma angelegt; **Eigennamen** wie »AfD« oder ein Nachname
gehören gar nicht in einen Wortschatz. Beides soll er abhaken und
sagen, warum.

Der Gegenknopf nimmt nur zurück, was noch offen ist. Was der Chat
schon eingetragen hat, bleibt stehen — es ist der Beleg dafür, woher
die Vokabel stammt.


### Akzentauswahl: nur noch eine, und sie beginnt beim Akzent

Zu merken war: beim Halten eines Vokals erschienen **zwei** Fenster
übereinander — das des Trainers und das von macOS. Das zweite bot
lateinische Akzente an (î, ï), die im Griechischen nichts zu suchen
haben, und beide hörten auf dieselben Zifferntasten, wobei das System
gewann.

Solange eine Taste mit Varianten gehalten wird, steht das Antwortfeld
jetzt auf »nur lesen«. In einem Feld, das man nicht beschreiben kann,
bietet macOS keine Buchstaben an — eingefügt wird ohnehin aus dem
Programm heraus. Die Sperre löst sich beim Loslassen und außerdem beim
Verlassen des Feldes oder Wegschalten der Seite; ein hängengebliebener
Schreibschutz wäre schlimmer als alles, wogegen er hilft.

Und die Auswahl beginnt beim Akzent: bei ι stehen ί, ϊ, ΐ auf 1, 2, 3.
Den unbetonten Buchstaben hat man ja schon getippt.

### Die Rundgänge überarbeitet: sechs statt vier, und nur noch Orientierung

Ein Rundgang sagt jetzt nur noch, **wo** etwas liegt. Das Warum steht
im Lehrgang, und jeder Rundgang endet mit dem Verweis auf sein
Kapitel. Vorher stand beides in den Sprechblasen — »fast richtig
kostet nichts«, »der Tipp macht die Aufgabe schwer« —, und eine Blase
ist dafür der falsche Ort: drei Sätze, vorbei, nichts zum
Nachschlagen.

Zwei kamen dazu, für die Orte, an denen man beim Pflegen wirklich
steht: **Ein Wort eintragen** und **Freigeben, was wartet**. Dazu neu
in den bestehenden: Sortieren und Einklappen, »Schluss für heute«,
»Fortschritt«, und die Farbe der Sammlung in der Kopfzeile.

Ein Rundgang, der eine Sammlung braucht, sucht sich jetzt eine
passende — die Freigabe eine mit wirklich Wartendem — und gibt die
vorherige am Ende zurück.

### Farbe, Sortieren, Einklappen — und Beispielsätze wie im Wörterbuch

Jede Sammlung hat jetzt eine Farbe. Sie steht als Kante an der Karte
und in der Kopfzeile, samt Punkt vor dem Namen: man sieht im
Augenwinkel, in welcher Sprache man gerade steckt. Wer keine wählt,
bekommt eine zugeteilt — ändern geht in den Einstellungen.

Auf der Übersicht lassen sich die Sammlungen sortieren (Name,
Fälliges, zuletzt gelernt) und einzeln einklappen. Beides bleibt im
Browser: eine Ansichtssache gehört zum Gerät, nicht zum Bestand.

Neu sind **Beispielsätze und Erklärungen** — wie im Wörterbuch. Zu
jeder Bedeutung kann ein Erklärsatz stehen, zu jedem Wort
Beispielsätze mit Übersetzung, und ein Satz lässt sich der Bedeutung
zuordnen, zu der er gehört: bei »to go« der Satz mit dem Auto zu
»fahren«, nicht zu »gehen«. Dein Chatprogramm kann beides schreiben.
Die Sätze werden nicht abgefragt und brauchen keine Freigabe — ein
Beispielsatz steht daneben und wird nicht gepaukt.

### Neu: der Lehrgang, mit Bildern und zum Mitmachen

Die vier Rundgänge waren zu kurz und zu oberflächlich — aber nicht,
weil sie schlecht gemacht wären. Eine Sprechblase trägt drei Sätze und
kann nur zeigen, was gerade auf dem Bildschirm steht. Was fehlte, ist
das Weltbild: Lexem, Bedeutungen, Formen, und dass Aufgaben **erzeugt**
werden. Ohne das sind Merkmale, Freigabe und die Rolle der KI nicht
erklärbar, weil die Wörter fehlen, in denen man es sagen könnte.

Darum jetzt beides. Die Rundgänge zeigen weiter, wo was liegt. Der
**Lehrgang** (in der Anleitung oder unter »Lehrgang«) erklärt, warum —
in zwei Spuren:

- **Ich will lernen** (drei Kapitel, acht Minuten): wie der Trainer
  fragt, Tippen und Antworten, was heute drankommt.
- **Ich pflege den Bestand** (sechs Kapitel, 45 Minuten): wie der
  Trainer die Vokabeln sieht, Merkmale und Formgruppen, Freigabe,
  Berichtigen und Löschen, die Rolle der KI, Ziele und Lehrwerk. Die
  ersten vier sind die Pflicht.

Ein Kapitel ist eine Seite, kein Ausklapper — wer eine Seite sieht,
liest sie zu Ende. Jedes endet mit einer Handlung im Übungskurs, und
fünf Kapitel haben ein Bildschirmfoto.

Der Übungskurs hat dafür drei **ungeprüfte** Einträge bekommen, einen
davon absichtlich falsch (»goed« statt »walked«). Vorher war er
durchgehend freigegeben — man konnte den wichtigsten Handgriff an ihm
also gar nicht üben.

### Berichtigt: die KI kann ihre Einträge doch freigeben

In der Anleitung stand »Freigeben kann es nicht. Alles, was es
einträgt, bleibt ungeprüft, bis ein Mensch es angesehen hat.« Das
stimmte nicht. Über `als_geprueft` kann ein Chatprogramm seine eigenen
Einträge sofort abfragbar machen, und bei Übungssätzen ging es
undokumentiert über ein Feld im Eintrag.

Die Abkürzung bleibt — sie ist bequem, wenn man den Eintrag ohnehin
beurteilen kann. Aber die Texte sagen das jetzt: normalerweise
ungeprüft, auf ausdrückliche Bitte gleich freigegeben, und mit dem
Hinweis, was das kostet. Bei Sprachen, die man selbst nicht beurteilen
kann, lieber nicht.

### Neu: Dein Fortschritt

Auf der Übersicht neben »Fehler wiederholen« ein Knopf **Fortschritt**.
Fünf Kacheln: was du getan hast (Antworten je Tag, nach Urteil
getrennt), was auf dich zukommt (Fälligkeiten der nächsten Wochen, mit
dem Überfälligen vorweg), wo dein Wortschatz steht, wie schnell du
antwortest — und darüber vier Zahlen, die man ohne Diagramm versteht.

Zugeschnitten auf **wenig** Daten. Beim Bauen standen 101 Antworten an
zwei Tagen im Protokoll, und genau damit muss jede Kachel etwas sagen;
eine Statistik, die erst nach einem halben Jahr aufwacht, sieht man
einmal an und nie wieder. Wo nichts auszusagen ist, steht ein Satz
statt eines leeren Gerüsts.

Die Zahlen stimmen mit denen der Übersicht überein — fremde
Sammlungen, die du nur mitpflegst, und Zeitformen hinter der
Lektionsschranke zählen hier wie dort nicht mit.

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
