/* Der Inhalt des Lehrgangs — getrennt von seiner Darstellung.
 *
 * Zwei Spuren, weil zwei Leute verschiedene Dinge brauchen: wer nur
 * lernt, muss nie wissen, was ein Merkmalsbündel ist; wer den Bestand
 * pflegt, kommt ohne nicht aus.
 *
 * Jedes Kapitel endet mit einer HANDLUNG im Übungskurs. Das ist die
 * wichtigste Regel dieser Datei: ein Kapitel, das nur gelesen wird,
 * ist nach einer Woche weg. »Tun« heißt hier nicht »lies weiter«,
 * sondern »mach das einmal, dann kommst du zurück«.
 *
 * Bausteine:
 *   ['absatz', text]      gewöhnlicher Text
 *   ['merke', text]       der eine Satz, der hängenbleiben soll
 *   ['liste', [...]]      Aufzählung
 *   ['bild', name, text]  Bildschirmfoto aus frontend/bilder/lehrgang
 *                         (erzeugt von werkzeuge/bilder-aufnehmen.py)
 *   ['tun', ziel, text]   die Handlung am Ende, als Verweis ins Werkzeug
 */

export const SPUREN = [
  {
    kennung: 'lernen',
    name: 'Ich will lernen',
    fuer: 'Für alle, die den Trainer benutzen.',
    dauer: 'drei Kapitel, zusammen acht Minuten',
    kapitel: [
      {
        titel: 'Wie der Trainer fragt',
        dauer: '3 Minuten',
        teile: [
          ['absatz', 'Der Trainer fragt nicht Vokabeln ab, sondern '
            + 'Aufgaben. Zu einem Wort gehören meist mehrere: die '
            + 'Bedeutung erkennen, das Wort bilden, eine Form bilden. '
            + 'Jede davon hat ihren eigenen Termin — du kannst »das Haus« '
            + 'sicher erkennen und trotzdem beim Bilden hängen.'],
          ['bild', 'abfrage',
            'Oben die Aufgabenart, in der Mitte das Gefragte, darunter '
            + 'das Antwortfeld.'],
          ['absatz', 'Tippen und Enter. Danach siehst du, ob es gestimmt '
            + 'hat und wann das Wort wiederkommt; noch einmal Enter '
            + 'bringt die nächste Frage.'],
          ['merke', 'Fast richtig kostet nichts. Liegt nur ein Zeichen '
            + 'daneben, darfst du noch einmal — erst der zweite Versuch '
            + 'zählt.'],
          ['absatz', '»Weiß ich nicht« ist kein Drücken vor der Antwort, '
            + 'sondern die ehrliche Auskunft: das Wort kommt dann bald '
            + 'wieder. Raten verfälscht den Plan, und der Plan arbeitet '
            + 'für dich.'],
          ['absatz', '»Tipp« deckt Stück für Stück auf und bleibt in der '
            + 'Abfrage. Er kostet etwas: eine Antwort mit Tipp gilt als '
            + '»schwer«, das Wort kommt also früher wieder. Das ist keine '
            + 'Strafe, sondern die Wahrheit über das, was du kannst.'],
          ['tun', '#/lernen', 'Fünf Fragen im Übungskurs beantworten'],
        ],
      },
      {
        titel: 'Tippen und antworten',
        dauer: '3 Minuten',
        teile: [
          ['absatz', 'Für Griechisch musst du nichts umschalten. Tippe '
            + 'lateinisch, und es erscheint griechisch: aus '
            + '»grafo« wird γραφο. Der Trainer bildet dieselben Tasten ab '
            + 'wie das griechische Systemlayout, du lernst also nichts '
            + 'Falsches.'],
          ['liste', [
            'Betonung: erst die Taste Ö, dann den Vokal — ά.',
            'Oder den Vokal gedrückt halten und die Ziffer wählen: '
              + 'ι wird zu ί, ϊ oder ΐ.',
            'Wortende-ς liegt auf W.',
            'Unter dem Antwortfeld kannst du die Belegung aufklappen, '
              + 'ohne die Abfrage zu verlassen.',
          ]],
          ['absatz', 'Wer sein Systemlayout wirklich umschaltet, kann das '
            + 'tun — dann merkt der Trainer es und hält sich heraus.'],
          ['merke', 'Den Artikel darfst du mitschreiben, musst aber '
            + 'nicht. Ein FALSCHER Artikel zählt als Fehler.'],
          ['absatz', 'Akzente sind ein Hinweis, kein Fehler: wer γραφω '
            + 'statt γράφω schreibt, bekommt »fast« und darf noch einmal. '
            + 'Bei Sätzen wird Wort für Wort verglichen, und du siehst '
            + 'genau, welches Wort anders war.'],
          ['tun', '#/lernen', 'Eine Runde tippen und die Belegung aufklappen'],
        ],
      },
      {
        titel: 'Was heute drankommt',
        dauer: '2 Minuten',
        teile: [
          ['bild', 'uebersicht',
            'Die Übersicht: oben was heute ansteht, darunter deine '
            + 'Sammlungen.'],
          ['liste', [
            '»Fällig« heißt: heute planmäßig dran.',
            '»Verlernt« ist danebengegangen und kommt bald wieder.',
            '»Neu« war noch nie dran — das ist dein Vorrat, keine '
              + 'offene Rechnung.',
            '»Sitzt« kannst du dauerhaft.',
          ]],
          ['merke', 'Das Tagespensum ist eine Zahl, keine Mauer. Steht '
            + 'daneben ein Rückstand, heißt das nur: so viel wäre '
            + 'außerdem fällig. Er wird kleiner, wenn du dranbleibst.'],
          ['absatz', 'Du bekommst nie dasselbe Wort zweimal hintereinander, '
            + 'auch wenn du es dreimal falsch hattest: erst sind die '
            + 'anderen dran. Und unter jeder Frage steht »Warum kommt das '
            + 'jetzt?« — dort erklärt der Trainer seine Rechnung. Nichts '
            + 'davon ist geheim.'],
          ['tun', '#/statistik', '»Fortschritt« ansehen'],
        ],
      },
    ],
  },
  {
    kennung: 'pflegen',
    name: 'Ich pflege den Bestand',
    fuer: 'Für die, die Vokabeln einträgt und freigibt.',
    dauer: 'sechs Kapitel, zusammen 45 Minuten — die ersten vier sind '
         + 'die Pflicht',
    kapitel: [
      {
        titel: 'Wie der Trainer die Vokabeln sieht',
        dauer: '8 Minuten',
        teile: [
          ['absatz', 'Das ist das Kapitel, ohne das die anderen nicht '
            + 'verständlich sind. Drei Ebenen:'],
          ['liste', [
            'Das LEXEM ist das Wort als Ganzes: »to go«, Verb.',
            'Die BEDEUTUNGEN hängen daran: gehen; fahren (mit Fahrzeug). '
              + 'Eine Bedeutung kann mehrere Übersetzungen haben, und '
              + 'alle gelten als richtig.',
            'Die FORMEN hängen ebenfalls daran: goes, went, gone. Jede '
              + 'Form trägt Merkmale — welche Zeit, welche Person.',
          ]],
          ['merke', 'Aufgaben trägst du nicht ein. Sie werden erzeugt: '
            + 'aus jeder Bedeutung und jeder geprüften Form entsteht, '
            + 'was abgefragt werden kann.'],
          ['absatz', 'Darum wächst die Zahl der Aufgaben schneller als '
            + 'die der Wörter. Der Übungskurs hat 20 Wörter und über 60 '
            + 'Aufgaben. Und darum zählen Übersicht und Fortschritt in '
            + 'Aufgaben, nicht in Wörtern: ein Verb bringt viel Arbeit '
            + 'mit, ein Adverb kaum.'],
          ['bild', 'wortschatz',
            'Der Wortschatz. Ein Klick auf ein Wort zeigt seine '
            + 'Formentafel.'],
          ['tun', '#/wortschatz', 'Im Übungskurs »to go« aufschlagen'],
        ],
      },
      {
        titel: 'Merkmale und Formgruppen',
        dauer: '10 Minuten',
        teile: [
          ['absatz', 'Eine Form wird nicht durch einen Spaltennamen '
            + 'beschrieben, sondern durch ein Bündel von Merkmalen: '
            + '{modus: indikativ, tempus: präsens, person: 3, numerus: '
            + 'sg}. Das klingt umständlich und ist der Grund, warum '
            + 'derselbe Trainer Griechisch, Französisch und '
            + 'Mittelhochdeutsch kann, ohne dass jemand Code ändert.'],
          ['merke', 'Eine FORMGRUPPE ist eine Tabelle: alle Personen '
            + 'einer Zeit, alle Fälle eines Hauptworts. Sie bestimmt, '
            + 'welche Felder dir beim Eintragen angeboten werden — und '
            + 'welche Zeiten überhaupt abgefragt werden.'],
          ['absatz', 'Welche Formgruppen eine Sammlung benutzt, stellst '
            + 'du unter »Einstellungen« ein. Das ist der wichtigste '
            + 'Schalter des ganzen Werkzeugs: ohne ihn entstünden pro '
            + 'französischem Verb an die zweihundert Aufgaben.'],
          ['absatz', 'Abgewählte Formgruppen werden abgeschaltet, nicht '
            + 'gelöscht. Wer das Plus-que-parfait später zuschaltet, '
            + 'findet seinen Lernstand vor.'],
          ['tun', '#/neu', '»to drink« von Hand eintragen, mit drei Formen'],
        ],
      },
      {
        titel: 'Freigabe',
        dauer: '7 Minuten',
        teile: [
          ['absatz', 'Was eine KI oder ein Import einträgt, ist zunächst '
            + 'ungeprüft — und Ungeprüftes wird NICHT abgefragt. Das ist '
            + 'die wichtigste Sicherung im Werkzeug: eine erfundene Form, '
            + 'die unbemerkt gepaukt wird, ist schlimmer als eine '
            + 'fehlende.'],
          ['bild', 'freigabe',
            'Die Prüfansicht, nach Lektionen geordnet.'],
          ['absatz', 'Im Übungskurs warten mit Absicht sechs Formen auf '
            + 'dich. Eine davon ist falsch: bei »to walk« steht als '
            + 'Vergangenheit »goed«. So etwas erfindet eine KI wirklich — '
            + 'sie überträgt die regelmäßige Endung auf ein Verb, das sie '
            + 'nicht hat. Finde sie, bevor du durchklickst.'],
          ['merke', 'Freigeben soll die KI nicht — sie KANN es aber, wenn '
            + 'du sie ausdrücklich darum bittest. Dann prüft niemand '
            + 'mehr nach. Bei Sprachen, die du selbst nicht beurteilen '
            + 'kannst, lieber nicht.'],
          ['absatz', 'Unter »Einstellungen« gibt es außerdem den Schalter '
            + '»Ungeprüfte Formen mitabfragen«. Er hebt die ganze '
            + 'Sicherung auf. Es gibt Lagen, in denen das richtig ist — '
            + 'aber man sollte wissen, dass man es getan hat.'],
          ['tun', '#/freigabe', 'Die sechs offenen Formen durchgehen'],
        ],
      },
      {
        titel: 'Berichtigen und löschen',
        dauer: '6 Minuten',
        teile: [
          ['absatz', 'Der Lernstand hängt an der Aufgabe, und die Aufgabe '
            + 'am Merkmalsbündel — nicht an der Zeilennummer. Darum '
            + 'überlebt er eine Berichtigung: wer eine Form richtigstellt, '
            + 'verliert nicht, was daran gelernt wurde.'],
          ['merke', 'Eine geänderte Form ist wieder ungeprüft. Sie '
            + 'verschwindet also aus der Abfrage, bis du sie erneut '
            + 'freigibst — das ist Absicht und keine Panne.'],
          ['absatz', 'Löschen verlangt den Namen des Wortes und sagt dir '
            + 'vorher, wie viel Lernstand dabei verlorengeht. Wenn du '
            + 'unsicher bist, setze die Aufgabe lieber aus: dann wird sie '
            + 'nicht mehr gefragt, bleibt aber erhalten.'],
          ['tun', '#/freigabe', '»goed« zu »walked« berichtigen'],
        ],
      },
      {
        titel: 'Die Rolle der KI',
        dauer: '8 Minuten',
        teile: [
          ['absatz', 'Der Trainer ruft nirgends nach außen an. Es gibt '
            + 'keinen Schlüssel, keine Netzverbindung zu einem '
            + 'KI-Anbieter, keine laufenden Kosten. Alles, was eine KI '
            + 'hier tut, tut DEIN Chatprogramm — es verbindet sich mit '
            + 'dem Trainer, nicht umgekehrt.'],
          ['merke', 'Es handelt in deinem Namen und sieht genau die '
            + 'Sammlungen, die dir gehören oder dir freigegeben sind. '
            + 'Fremde bleiben unsichtbar.'],
          ['absatz', 'Gut kann es: ganze Lektionen mit allen Formen '
            + 'eintragen, Formen ergänzen, Grammatikregeln schreiben, '
            + 'Übungssätze anlegen, die Lektionszuordnung der Zeitformen '
            + 'vorschlagen, Texte hinterlegen und übersetzen, und die '
            + 'Wörter abholen, die du beim Lesen angefordert hast.'],
          ['absatz', 'Was es NICHT kann: wissen, was du gerade im '
            + 'Unterricht hattest. Und es irrt — besonders bei '
            + 'unregelmäßigen Formen. Deshalb die Freigabe.'],
          ['liste', [
            'Sag ihm, welche Sammlung: »in meinem Griechisch«.',
            'Sag ihm die Lektion: »Lektion 12«.',
            'Lass es erst zeigen, dann eintragen: »zeig mir die zehn '
              + 'Wörter, bevor du sie einträgst«.',
            'Danach immer über die Freigabe sehen.',
          ]],
          ['tun', '#/hilfe', 'Den Abschnitt »Chatprogramm anschließen« lesen'],
        ],
      },
      {
        titel: 'Ziele und das Lehrwerk',
        dauer: '6 Minuten',
        teile: [
          ['absatz', 'Ein Lernziel ist ein Ausschnitt mit einem Ziel '
            + 'davor: »Lektion 3 bis Freitag«. Du bestimmst den Umfang — '
            + 'Lektionen, Wortarten, Zeiten, Abfragearten — und wenn du '
            + 'einen Termin einträgst, rechnet der Trainer aus, wie viel '
            + 'täglich nötig wäre.'],
          ['bild', 'lehrgang-einstellung',
            '»Wo stehst du im Lehrwerk?« in den Einstellungen einer '
            + 'Sammlung.'],
          ['absatz', 'Eine Vokabelsammlung bringt oft alle Zeitformen '
            + 'mit, auch die aus Kapiteln, die ihr noch nicht hattet. '
            + 'Hier trägst du ein, ab welcher Lektion das Buch welche '
            + 'Zeitform einführt — vorgeschlagen aus den Lektionsnamen — '
            + 'und bei welcher Lektion du stehst.'],
          ['merke', 'Ohne deine eigene Lektionsangabe ändert sich '
            + 'nichts. Ein Lernziel mit Lektionsauswahl hält sich auch '
            + 'ohne sie an seine Lektionen.'],
          ['absatz', 'Ausgeblendet heißt wartet, nicht gelöscht. Kommst '
            + 'du bei der Lektion an, ist die Zeitform von selbst wieder '
            + 'dabei.'],
          ['tun', '#/einstellungen/lehrgang',
            'Im Übungskurs »bei Lektion 3« eintragen und sehen, was wegfällt'],
        ],
      },
    ],
  },
];
