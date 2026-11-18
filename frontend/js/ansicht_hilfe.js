/* Die Anleitung — geschrieben für die, die den Trainer benutzen, nicht
 * für die, die ihn gebaut haben.
 *
 * Zwei Teile, weil es zwei Fragen sind: wie lerne ich damit, und wie
 * schließe ich mein Chatprogramm an, damit es mir die Vokabeln einträgt.
 *
 * Die Adresse der Schnittstelle kommt vom Server und steht nicht im
 * Quelltext: sie gehört zur Anlage und nicht ins öffentliche Repo.
 */

import { api } from './api.js';
import { h, leeren, meldung } from './hilfen.js';
import { zustand } from './zustand.js';
import * as fuehrung from './fuehrung.js';

function abschnitt(titel, ...inhalt) {
  return h('details', { class: 'karte hilfe' },
    h('summary', {}, h('strong', { text: titel })),
    h('div', { class: 'hilfe-inhalt' }, ...inhalt));
}

function schritte(...zeilen) {
  return h('ol', { class: 'hilfe-schritte' },
    zeilen.map((z) => h('li', {}, ...(Array.isArray(z) ? z : [z]))));
}

export async function zeichnen(behaelter) {
  const el = leeren(behaelter);
  let stand = {};
  try { stand = await api.zustand(); } catch { /* nichts */ }
  const adresse = stand.mcp_url || null;
  const kopfzeile = stand.mcp_kopfzeile || 'x-account-key';

  el.append(h('h1', { text: 'Anleitung' }));
  el.append(h('p', { class: 'leise',
    text: 'Zwei Fragen, zwei Teile: wie du damit lernst, und wie du dein '
        + 'Chatprogramm anschließt, damit es dir die Vokabeln einträgt.' }));

  /* ---------------------------------------------------------- Lernen */

  el.append(h('h2', { text: 'Lehrgang' }));
  el.append(h('div', { class: 'karte' },
    h('p', { style: 'margin-top:0' },
      'Ausführlich und zum Mitmachen: zwei Spuren, neun Kapitel, jedes '
      + 'endet mit etwas, das du im Übungskurs ausprobierst. Hier steht '
      + 'auch, was die Rundgänge nicht erklären können — wie der Trainer '
      + 'die Vokabeln sieht, was Merkmale und Formgruppen sind, wozu die '
      + 'Freigabe da ist und was die KI darf.'),
    h('button', { class: 'wichtig',
                  onclick: () => { location.hash = '#/lehrgang'; } },
      'Zum Lehrgang')));

  el.append(h('h2', { text: 'Geführte Rundgänge' }));
  el.append(h('p', { class: 'leise',
    text: 'Kurz und einzeln. Jeder hört an einer Stelle auf, an der du '
        + 'etwas ausprobieren kannst — die Anwendung bleibt dabei '
        + 'bedienbar.' }));
  const rundgaenge = h('div', { class: 'karte' });
  for (const r of fuehrung.RUNDGAENGE) {
    rundgaenge.append(h('div', { class: 'lehrgangszeile' },
      h('button', { onclick: () => fuehrung.starten(r.kennung) },
        'Starten'),
      h('span', {}, h('b', { text: r.name }),
        h('span', { class: 'leise', text: ` · ${r.dauer}` })),
      h('span', { class: 'leise', text: r.beschreibung })));
  }
  rundgaenge.append(h('p', { class: 'leise', style: 'margin:.8rem 0 0' },
    'Auf der Übersicht steht dafür eine Karte, bis du sie ausblendest. ',
    h('button', {
      class: 'schlicht',
      onclick: () => {
        fuehrung.wiederZeigen();
        meldung('Die Karte erscheint wieder auf der Übersicht.');
      },
    }, 'Karte wieder einblenden')));
  el.append(rundgaenge);

  el.append(h('h2', { text: 'Lernen' }));

  el.append(abschnitt('Wie eine Abfrage abläuft',
    h('p', {}, 'Du bekommst eine Frage, tippst die Antwort und drückst ',
      h('kbd', { text: 'Enter' }), '. Danach siehst du, ob es gestimmt hat, '
      + 'und wann das Wort wiederkommt. Noch einmal ', h('kbd', { text: 'Enter' }),
      ' bringt die nächste Frage.'),
    h('p', {}, h('b', { text: 'Fast richtig kostet nichts. ' }),
      'Wenn nur ein Zeichen danebenliegt, darfst du es noch einmal tippen. '
      + 'Erst der zweite Versuch zählt.'),
    h('p', {}, h('b', { text: 'Du musst dich nicht selbst benoten. ' }),
      'Der Trainer bewertet aus deiner Antwort — ob sie stimmte, welche Art '
      + 'Fehler es war, wie oft du es versucht hast. Wenn du anderer Meinung '
      + 'bist, kannst du die Wertung ändern; das wird als Eingriff vermerkt.'),
    h('p', {}, h('b', { text: 'Weiß ich nicht' }), ' ist kein Drücken vor der '
      + 'Antwort, sondern die ehrliche Auskunft — das Wort kommt dann bald '
      + 'wieder. Raten verfälscht den Plan.')));

  el.append(abschnitt('Was abgefragt wird',
    h('dl', {},
      h('dt', { text: 'Bedeutung erkennen' }),
      h('dd', { text: 'Fremdes Wort, gesucht ist die Bedeutung. Eine von '
                    + 'mehreren hinterlegten genügt.' }),
      h('dt', { text: 'Wort bilden' }),
      h('dd', { text: 'Deutsche Bedeutung, gesucht ist das fremde Wort. '
                    + 'Gibt es mehrere mit derselben Bedeutung, gelten alle '
                    + '— außer die Frage nennt einen Zusammenhang.' }),
      h('dt', { text: 'Form bilden' }),
      h('dd', {}, 'Grundform und Formangabe gegeben, gesucht ist die Form. '
        + 'Unter der Formangabe steht ein Beispiel auf Deutsch, und daneben '
        + 'das Pronomen: ', h('b', { text: '(εσύ) 2. Person Singular' }), '.'),
      h('dt', { text: 'Ganze Reihe' }),
      h('dd', { text: 'Eine ganze Tabelle auf einmal — ich gehe, du gehst, '
                    + 'er geht. Enter springt ins nächste Feld, erst im '
                    + 'letzten wird geprüft.' }),
      h('dt', { text: 'Artikel' }),
      h('dd', { text: 'Welcher Artikel gehört zu dem Wort?' }))));

  el.append(abschnitt('Was als richtig gilt',
    h('p', {}, h('b', { text: 'Den Artikel darfst du mitschreiben. ' }),
      'τα καρότα ist richtig, καρότα auch — dann wird dir der Artikel '
      + 'aber gezeigt, denn mitzuschreiben ist die bessere Gewohnheit. '
      + 'Ein FALSCHER Artikel zählt als Fehler.'),
    h('p', {}, h('b', { text: 'Das Pronomen darfst du mitschreiben. ' }),
      'εγώ γράφω ist genauso richtig wie γράφω.'),
    h('p', {}, h('b', { text: 'Akzente sind ein Hinweis, kein Fehler. ' }),
      'Wer γραφω statt γράφω schreibt, bekommt „fast“ und darf es noch '
      + 'einmal tippen.'),
    h('p', {}, h('b', { text: 'Satzzeichen zählen nicht. ' }),
      'Bei Sätzen wird Wort für Wort verglichen, und du siehst genau, '
      + 'welches Wort anders war.')));

  el.append(abschnitt('Was heute drankommt',
    h('p', {}, 'Du suchst dir nicht aus, was abgefragt wird — der Trainer '
      + 'rechnet es aus. Jedes Wort bekommt einen Termin: was du sicher '
      + 'kannst, kommt in Wochen wieder, was wackelt, morgen. Oben in der '
      + 'Abfrage steht, wie weit du heute bist.'),
    h('p', {}, h('b', { text: 'Das Tagespensum ist eine Zahl, keine Mauer. ' }),
      'Steht daneben ein Rückstand, heißt das nur: so viel wäre außerdem '
      + 'fällig. Du musst ihn nicht aufholen — er wird kleiner, wenn du '
      + 'dranbleibst.'),
    h('p', {}, h('b', { text: 'Erst jedes Wort einmal, dann das zweite Mal. ' }),
      'Auch wenn du etwas dreimal hintereinander falsch hast, kommt es '
      + 'nicht dreimal hintereinander — erst sind die anderen dran.'),
    h('p', {}, h('b', { text: 'Der Ring oben ist dein Tagesziel. ' }),
      'Er füllt sich mit jeder Antwort und bekommt einen Haken, wenn das '
      + 'Pensum aufgegangen ist. Daneben steht deine Strähne: wie viele '
      + 'Tage in Folge du sie geschafft hast.'),
    h('p', {}, h('b', { text: 'Ziel und Grenze sind zweierlei. ' }),
      'Die Grenze sagt, wie viele Fragen der Trainer an einem Tag '
      + 'höchstens vorlegt — sie steht absichtlich hoch, und für ein '
      + 'Lernziel mit nahem Termin wird sie noch höher gesetzt. Das '
      + 'Tagesziel ist das, was du dir vornimmst. Beides stellst du '
      + 'unter Einstellungen ein.'),
    h('p', {}, h('b', { text: 'Ein kurzer Tag zählt auch. ' }),
      'War weniger fällig als dein Ziel, gilt der Tag als geschafft, '
      + 'sobald nichts mehr da ist — du sollst nicht gegen deinen eigenen '
      + 'Terminplan arbeiten, nur damit eine Zahl stehen bleibt. Und zwei '
      + 'Fehltage im Monat trägt die Strähne mit; der dritte reißt sie.'),
    h('p', { class: 'leise' }, 'Wie viele Fragen am Tag und wie viel Neues '
      + 'dazwischen, stellst du unter Einstellungen ein.')));

  el.append(abschnitt('Bücher und Texte',
    h('p', {}, 'Bücher und Texte gehören zu ', h('b', { text: 'dir' }),
      ' und nicht zu einer Sammlung. Du findest sie darum auf der '
      + 'Übersicht als eigene Karte — ein Regal, auch wenn du drei '
      + 'Sprachen lernst.'),
    h('p', {}, h('b', { text: 'Drei Ebenen: Buch, Kapitel, Text. ' }),
      'Ein Buch bündelt Texte; innerhalb des Buchs ordnen Kapitel sie. '
      + 'Das Kapitel ist einfach ein Name — gleiche Schreibweise heißt '
      + 'gleiches Kapitel.'),
    h('p', {}, h('b', { text: 'Wogegen gelesen wird. ' }),
      'Jedes Buch nennt einen Wortschatz. Daran rechnet der Trainer aus, '
      + 'ob du den Text schon lesen könntest — darum darf kein Text aus '
      + 'einem anderen Wortschatz hinein.'),
    h('p', { class: 'leise' }, 'Ein Buch aufzulösen löscht keine Texte. '
      + 'Es ist eine Klammer, kein Behälter — danach stehen sie unter '
      + '»Ohne Buch«.')));

  el.append(abschnitt('Texte lesen',
    h('p', {}, h('b', { text: 'Übersetzung daneben. ' }),
      'Über dem Text steht ein Schalter. Angeschaltet stehen Original '
      + 'und Übersetzung nebeneinander — so sind mittelhochdeutsche '
      + 'Ausgaben gedruckt, und so liest man sie auch. Ausgeschaltet '
      + 'bleibt die Übersetzung eingeklappt unter deinem eigenen Feld: '
      + 'zum Vergleichen, nachdem du selbst übersetzt hast.'),
    h('p', {}, h('b', { text: 'Kapitel. ' }),
      'Texte lassen sich zu Kapiteln zusammenfassen — ein Werk, ein '
      + 'Lehrbuchkapitel, was du willst. Die Liste gliedert sich danach, '
      + 'und über ihr wählst du ein einzelnes aus. Zum Umhängen die '
      + 'Kästchen anhaken, Kapitel wählen, umhängen; eine neue Nummer '
      + 'legt eines an. Anders als beim Wortschatz entscheidet das '
      + 'Kapitel hier über nichts — es ordnet nur.'),
    h('p', {}, h('b', { text: 'Wo nichts steht, steht das auch da. ' }),
      'Abschnitte ohne Übersetzung zeigen »noch nicht übersetzt«. Die '
      + 'Lücke ist die Auskunft — so siehst du, was noch fehlt.'),
    h('p', { class: 'leise' }, 'Die Übersetzungen trägt dein '
      + 'Chatprogramm ein. Deine eigene Fassung wird dabei nie '
      + 'angerührt: die Referenz gehört zum Text, dein Versuch gehört '
      + 'dir.')));

  el.append(abschnitt('Punkte, Stufen und Zuspruch',
    h('p', {}, h('b', { text: 'Punkte gibt es fürs Drankommen. ' }),
      'Je Aufgabe und Tag einmal — gleich, ob die Antwort stimmte. Das ist '
      + 'Absicht: hingen Punkte am »richtig«, lohnte es sich, sich selbst '
      + 'großzügig zu bewerten, und dann stimmt der Terminplan nicht mehr. '
      + 'Am meisten bringt, was dauerhaft sitzt, und dorthin führt kein '
      + 'Nachmittag, sondern nur Zeit.'),
    h('p', {}, h('b', { text: 'Dieselbe Karte fünfzigmal bringt nichts. ' }),
      'Gezählt wird je Aufgabe, nicht je Antwort. Wer mehr Punkte will, '
      + 'muss mehr verschiedene Wörter anfassen.'),
    h('p', {}, h('b', { text: 'Die Stufe fällt nie. ' }),
      'Sie hängt an der Summe aller Punkte, und die wird nur größer. Wie '
      + 'es wirklich steht, sagt der Wortschatz im Fortschritt — der geht '
      + 'in beide Richtungen.'),
    h('p', {}, h('b', { text: 'Zuspruch schicken. ' }),
      'An Leute, mit denen du eine Sammlung teilst, höchstens fünfmal am '
      + 'Tag an dieselbe Person. Vier Arten: eine Botschaft, die beim '
      + 'nächsten Öffnen dasteht; doppelte Punkte für einen Tag, den der '
      + 'andere sich aussucht; ein Joker, der einen Fehltag der Strähne '
      + 'trägt; und ein Versprechen.'),
    h('p', {}, h('b', { text: 'Das Versprechen ist das Stärkste. ' }),
      '»Lernziel bis Freitag → Kino.« Die App rechnet daran nichts aus '
      + 'und schenkt nichts — sie merkt sich den Satz und sagt, wenn er '
      + 'fällig ist. Abhaken kann nur, wer ihn gegeben hat.'),
    h('p', { class: 'leise' }, 'Alles außer dem Zuspruch wird aus deinem '
      + 'Protokoll gerechnet. Darum fängt niemand bei null an — wer schon '
      + 'gelernt hat, hat auch schon Punkte.')));

  el.append(abschnitt('Lernziele: ein Block mit Termin',
    h('p', {}, 'Ein Lernziel ist ein Ausschnitt mit einem Ziel davor: ',
      h('b', { text: 'Lektion 3 bis Freitag' }), '. Du sagst, was dazugehört '
      + '— Lektionen, Wortarten, Zeiten, Abfragearten —, und wenn du einen '
      + 'Termin einträgst, rechnet der Trainer aus, wie viel täglich nötig '
      + 'wäre. Reicht dein Pensum dafür nicht, sagt er es dir.'),
    h('p', {}, h('b', { text: 'Was käme dran? ' }),
      'zeigt den nächsten Block, bevor du anfängst, und begründet ihn: so '
      + 'viel Fälliges, so viel Wackliges, so viel Neues.'),
    h('p', {}, h('b', { text: 'Neu würfeln ' }),
      'stellt denselben Block aus anderen Wörtern zusammen. Wie viel '
      + 'fällig, wacklig und neu ist, bleibt gleich — das entscheidet der '
      + 'Termin, nicht der Würfel.'),
    h('p', { class: 'leise' }, 'Ein Lernziel lässt sich jederzeit ändern, '
      + 'auch nachträglich ein Datum setzen oder wieder entfernen.')));

  el.append(abschnitt('Gezielt üben',
    h('p', {}, 'Manchmal will man nicht den Plan, sondern ein Thema: nur '
      + 'Verben, nur Adjektive, nur den Aorist. Auf jeder Sammlungskarte '
      + 'steht dafür ', h('b', { text: 'Gezielt üben' }), '. Dahinter '
      + 'stehen alle Wortarten, die es in deiner Sammlung wirklich gibt, '
      + 'und jede Zeit einzeln — mit der Zahl daneben, damit du siehst, '
      + 'ob sich das lohnt.'),
    h('p', {}, h('b', { text: 'Ohne Tagespensum. ' }),
      'Hier wird geübt, solange du magst. Dein Lernstand zählt ganz normal '
      + 'mit; nur der Terminplan steuert nicht.'),
    h('p', { class: 'leise' }, 'Das gilt für diese Sitzung. Beim nächsten '
      + '»Lernen« bist du wieder im Plan — wer heute nur Verben übt, soll '
      + 'morgen nicht unbemerkt darin hängen.')));

  el.append(abschnitt('Nur das, was ihr schon hattet',
    h('p', {}, 'Eine Vokabelsammlung bringt oft alle Formen mit, auch die '
      + 'aus Kapiteln, die ihr noch gar nicht hattet. Dann fragt der '
      + 'Trainer nach dem Aorist, während ihr beim Präsens seid.'),
    h('p', {}, 'Unter ', h('b', { text: 'Einstellungen' }), ' steht darum ',
      h('b', { text: 'Wo stehst du im Lehrwerk?' }), '. Dort trägst du '
      + 'zweierlei ein: ab welcher Lektion eine Zeitform im Buch '
      + 'vorkommt — das schlägt der Trainer aus euren Lektionsnamen vor — '
      + 'und bei welcher Lektion du gerade bist.'),
    h('p', {}, 'Was später kommt, bleibt dann draußen. Kommst du dort an, '
      + 'ist es von selbst wieder dabei; du musst nichts umstellen.'),
    h('p', {}, h('b', { text: 'Nichts geht verloren. ' }),
      'Ausgeblendet heißt wartet, nicht gelöscht — auch dein Lernstand '
      + 'bleibt stehen.'),
    h('p', { class: 'leise' }, 'Trägst du keine Lektion ein, ändert sich '
      + 'gar nichts; dann kommt alles dran wie bisher. Bedeutungen sind '
      + 'nie betroffen — ein Wort kann man lernen, bevor man seine Zeiten '
      + 'kennt.')));

  el.append(abschnitt('Welche Sammlungen mitgelernt werden',
    h('p', {}, 'Wenn dir jemand eine Sammlung freigibt, heißt das erst '
      + 'einmal nur: du darfst hineinsehen und mithelfen. Gelernt wird sie '
      + 'nicht automatisch — sonst lägen fremde Vokabeln zwischen deinen.'),
    h('p', {}, 'Auf jeder Sammlungskarte steht dafür ein Häkchen. Eigene '
      + 'Sammlungen sind angehakt, freigegebene nicht. Wollt ihr dasselbe '
      + 'zusammen lernen, hakt es jeder für sich an.'),
    h('p', { class: 'leise' }, 'Das betrifft nur die allgemeine Abfrage. '
      + 'Über »Lernen« auf der Karte kommst du in jede Sammlung hinein, '
      + 'auch in eine nicht angehakte.')));

  el.append(abschnitt('Texte lesen und übersetzen',
    h('p', {}, 'Unter ', h('b', { text: 'Texte' }), ' auf der '
      + 'Sammlungskarte kannst du einen Text einfügen oder als Datei '
      + 'hochladen — ein Stück aus dem Buch, eine Zeitungsmeldung, was du '
      + 'willst. Leerzeilen trennen die Absätze; in diesen Abschnitten '
      + 'übersetzt du dann.'),
    h('p', {}, h('b', { text: 'Vorher sagt er dir, ob du das kannst. ' }),
      'Jedes Wort wird mit deinem Wortschatz verglichen — Grundformen und '
      + 'alle eingetragenen Formen. Darüber steht ein Satz wie ',
      h('i', { text: '»Fast — 2 Wörter fehlen dir noch«' }), '.'),
    h('p', {}, h('b', { text: 'Geraten wird dabei nicht. ' }),
      'Steht μικρός in deinem Wortschatz, aber die Form μικρό nicht, gilt '
      + 'μικρό als unbekannt. Lieber eine zu vorsichtige Auskunft als eine '
      + 'Zusage, vor der du dann sitzt.'),
    h('p', {}, h('b', { text: 'Jedes Wort ist anklickbar. ' }),
      'Ein Klick zeigt deinen eigenen Eintrag dazu, samt der Form, die im '
      + 'Text steht: bei ', h('b', { text: 'διαβάζει' }), ' also ',
      h('b', { text: 'διαβάζω' }), ' — lesen, 3. Person Singular Präsens. '
      + 'Keine Maschinenübersetzung, dein eigener Wortschatz.'),
    h('p', {}, 'Deine Übersetzung sichert sich beim Tippen. Es gibt kein '
      + 'Abschicken, und du kannst jederzeit aufhören.'),
    h('p', {}, h('b', { text: 'Was dir fehlt, kannst du anfordern. ' }),
      'Rot unterlegte Wörter kennst du noch nicht — antippen und ',
      h('i', { text: '»Für die KI merken«' }), '. Dein Chatprogramm liest '
      + 'diese Liste über die Schnittstelle, legt die Vokabeln an und hakt '
      + 'sie ab. Wie du es anschließt, steht weiter unten.')));

  el.append(abschnitt('Griechisch tippen',
    h('p', {}, h('b', { text: 'Du musst nichts umschalten. ' }),
      'Tippst du ', h('b', { text: 'grafo' }), ', steht im Feld ',
      h('b', { text: 'γραφο' }) , ' — der Trainer bildet dieselben Tasten '
      + 'auf griechische Buchstaben ab wie das griechische Systemlayout. '
      + 'Betonung wie dort: erst die Taste ', h('kbd', { text: 'Ö' }),
      ', dann den Vokal. Wortende-ς liegt auf ', h('kbd', { text: 'W' }), '.'),
    h('p', { class: 'leise' },
      'Wer sein Layout lieber wirklich umschaltet, kann das tun — dann '
      + 'merkt der Trainer es und hält sich heraus. Abschalten lässt sich '
      + 'die Umschrift unter Einstellungen.'),
    h('p', {}, 'Für Griechisch lohnt ein eigenes Tastaturlayout — man tippt '
      + 'ja ganze Wörter. Wie man es einschaltet und wo welcher Buchstabe '
      + 'liegt, steht hier: '),
    h('p', {}, h('button', {
      onclick: () => { location.hash = '#/tastatur/el'; },
    }, 'Zur Tastaturhilfe')),
    h('p', { class: 'leise' }, 'Während der Abfrage kannst du die Belegung '
      + 'unter dem Antwortfeld aufklappen, ohne die Abfrage zu verlassen.')));

  /* ------------------------------------------------- Chat anschließen */

  el.append(h('h2', { text: 'Dein Chatprogramm anschließen' }));
  el.append(h('p', {},
    'Claude oder ChatGPT können Vokabeln direkt in deinen Trainer '
    + 'eintragen — ganze Lektionen mit allen Formen. Das spart das '
    + 'Abtippen. Alles, was dabei entsteht, läuft ',
    h('b', { text: 'in deinem Namen' }), ' und bleibt ungeprüft, bis du '
    + 'es freigibst — es sei denn, du bittest ausdrücklich um das '
    + 'Gegenteil.'));

  if (!adresse) {
    el.append(h('div', { class: 'befund hinweis' },
      'Für diesen Trainer ist keine Adresse von außen eingerichtet. '
      + 'Solange das so ist, geht das Anschließen nur im Heimnetz — frag '
      + 'die Person, die den Server betreut.'));
  }

  el.append(abschnitt('Schritt 1: Zugang anlegen (im Trainer)',
    schritte(
      ['Oben rechts auf ', h('b', { text: 'Einstellungen' }), '.'],
      [h('b', { text: 'Zugang für Claude (MCP)' }), ' aufklappen.'],
      ['Einen Namen eintragen, an dem du ihn wiedererkennst — etwa '
       + '„ChatGPT auf meinem Rechner“ — und auf ',
       h('b', { text: 'Zugang anlegen' }), '.'],
      [h('b', { text: 'Den Wert sofort kopieren. ' }),
       'Er wird nur ein einziges Mal gezeigt. Verlierst du ihn, legst du '
       + 'einen neuen an und nimmst den alten zurück.']),
    h('p', { class: 'befund hinweis' },
      'Der Zugang gehört dir allein. Wer ihn hat, kann in deinem Namen '
      + 'eintragen — also nicht weitergeben und nicht in einen Chat '
      + 'kopieren, den andere lesen.'),
    h('p', {}, h('button', {
      class: 'wichtig',
      onclick: () => { location.hash = '#/einstellungen'; },
    }, 'Zu den Einstellungen'))));

  const adressfeld = h('input', {
    type: 'text', readonly: true, value: adresse || '(noch nicht eingerichtet)',
    style: 'font-family:ui-monospace,monospace;font-size:.9em',
    onclick: (e) => { e.target.select(); },
  });
  const kopffeld = h('input', {
    type: 'text', readonly: true, value: kopfzeile,
    style: 'font-family:ui-monospace,monospace;font-size:.9em;max-width:16rem',
    onclick: (e) => { e.target.select(); },
  });

  el.append(abschnitt('Schritt 2: Im Chatprogramm eintragen',
    h('p', { text: 'Beide Programme brauchen dasselbe — eine Adresse und '
                 + 'dein Zugangsmerkmal:' }),
    h('label', { class: 'feldname', text: 'Adresse' }), adressfeld,
    h('label', { class: 'feldname', style: 'margin-top:.6rem',
                 text: 'Name der Kopfzeile' }), kopffeld,
    h('p', { class: 'leise', style: 'margin-top:.3rem',
             text: 'Als Wert kommt dein Zugangsmerkmal aus Schritt 1 hinein.' }),
    h('p', { style: 'margin-top:.8rem' },
      'Wo der Knopf dafür sitzt, heißt je nach Programm ',
      h('b', { text: 'Connector' }), ', ', h('b', { text: 'MCP' }), ' oder ',
      h('b', { text: 'Integration' }), ' — und die Menüs ändern sich oft. '
      + 'Such in den Einstellungen danach; der Rest ist überall gleich.'),
    h('p', { class: 'befund hinweis' },
      h('strong', { text: 'Die Falle, in die alle tappen: ' }),
      'Der Name der Kopfzeile muss aus der angebotenen Liste ',
      h('b', { text: 'angeklickt' }), ' werden. Tippt man ihn selbst ein, '
      + 'wird er nicht mitgeschickt, und das Programm meldet nur, es könne '
      + 'den Trainer nicht erreichen — ohne zu sagen, warum.')));

  el.append(abschnitt('Schritt 3: Ausprobieren',
    h('p', { text: 'Schreib deinem Chatprogramm:' }),
    h('p', { class: 'loesung',
             text: '„Zeig mir meine Vokabelsammlungen.“' }),
    h('p', {}, 'Kommt eine Liste zurück, steht die Verbindung. Dann kannst '
      + 'du weitermachen, etwa:'),
    h('ul', {},
      h('li', { text: '„Trag die Vokabeln aus Lektion 5 ein, mit allen '
                    + 'Formen. Mach zuerst einen Probelauf.“' }),
      h('li', { text: '„Was in meinem Wortschatz sitzt noch nicht?“' }),
      h('li', { text: '„Schreib mir zehn Übungssätze mit den Wörtern bis '
                    + 'Lektion 12.“' })),
    h('p', { class: 'leise' },
      'Sag ihm ruhig „mach erst einen Probelauf“ — dann wird nichts '
      + 'geschrieben, und du siehst vorher, was herauskäme.')));

  el.append(abschnitt('Was es darf und was nicht',
    h('p', {}, 'Es sieht ', h('b', { text: 'nur deine' }), ' Sammlungen und '
      + 'die, die dir freigegeben sind. Fremde bleiben unsichtbar.'),
    h('p', {}, 'Es kann eintragen, berichtigen und löschen — Löschen aber '
      + 'nur, wenn es das Wort richtig benennt, und es sagt dir dabei, wie '
      + 'viel Lernstand dabei verlorengeht.'),
    h('p', {}, h('b', { text: 'Freigeben soll es nicht — es kann aber. ' }),
      'Normalerweise bleibt alles, was es einträgt, ungeprüft und wird '
      + 'nicht abgefragt, bis du es angesehen hast. Bittest du es '
      + 'ausdrücklich darum, darf es seine Einträge aber gleich '
      + 'freigeben.'),
    h('p', { class: 'leise' },
      'Diese Abkürzung ist bequem und sie hat einen Preis: dann prüft '
      + 'niemand mehr nach, und eine erfundene Form wird unbemerkt '
      + 'gepaukt. Wer sie nutzt, sollte hinterher über die Freigabe '
      + 'sehen, was entstanden ist. Für fremde Sprachen, die du selbst '
      + 'nicht beurteilen kannst, lieber gar nicht.'),
    h('p', {}, h('b', { text: 'Es sieht auch, was dir fehlt. ' }),
      'Die Wörter, die du beim Lesen angefordert hast, kann es abrufen — '
      + 'mit dem Satz, in dem sie standen, damit es die richtige Bedeutung '
      + 'erwischt. Es kann dir auch selbst einen Text hinlegen und vorher '
      + 'nachsehen, welche Wörter dir dafür noch fehlen. Sag ihm einfach: ',
      h('i', { text: '»Schau nach, welche Wörter ich angefordert habe, und '
                     + 'trag sie ein.«' })),
    h('p', {}, h('button', {
      onclick: () => { location.hash = '#/freigabe'; },
    }, 'Zur Freigabe'))));

  el.append(abschnitt('Wenn es nicht geht',
    h('dl', {},
      h('dt', { text: '„Konnte nicht erreicht werden“' }),
      h('dd', { text: 'Fast immer die Kopfzeile: aus der Liste anklicken, '
                    + 'nicht eintippen. Sonst kommt das Zugangsmerkmal gar '
                    + 'nicht an.' }),
      h('dt', { text: 'Es kennt die neuen Werkzeuge nicht' }),
      h('dd', { text: 'Die Liste der Werkzeuge wird beim Verbinden geholt. '
                    + 'Fang eine neue Unterhaltung an; hilft das nicht, '
                    + 'schalte den Connector aus und wieder ein.' }),
      h('dt', { text: 'Es trägt ein, aber nichts wird abgefragt' }),
      h('dd', { text: 'Das ist richtig so — es ist noch nicht freigegeben. '
                    + 'Unter Freigabe ansehen und bestätigen.' }))));

  el.append(h('p', { class: 'leise', style: 'margin-top:1.5rem' },
    'Steht hier etwas nicht drin, das du gebraucht hättest? Sag es weiter '
    + '— dann kommt es hinein.'));
}
