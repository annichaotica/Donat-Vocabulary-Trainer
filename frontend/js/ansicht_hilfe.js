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
    + 'es freigibst.'));

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
    h('p', {}, h('b', { text: 'Freigeben kann es nicht. ' }),
      'Alles, was es einträgt, bleibt ungeprüft und wird nicht abgefragt, '
      + 'bis ein Mensch es angesehen hat. Das ist Absicht: ein Programm, '
      + 'das seine eigenen Einträge freigibt, hätte die Prüfung '
      + 'abgeschafft, nicht erledigt.'),
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
