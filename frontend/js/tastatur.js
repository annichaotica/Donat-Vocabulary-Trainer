/* Zeichenleiste und Tastaturhilfe.
 *
 * Zwei verschiedene Probleme, zwei verschiedene Antworten:
 *
 *   Lateinische Schrift mit Akzenten (Französisch, Spanisch,
 *   Mittelhochdeutsch) — hier sind es EINZELNE Zeichen in sonst gewohnter
 *   Schreibung. Eine Leiste unter dem Feld erspart den Layoutwechsel.
 *
 *   Nichtlateinische Schrift (Griechisch) — hier tippt man ganze Wörter in
 *   der fremden Schrift. Eine Palette aus 36 Knöpfen ersetzt keine Tastatur,
 *   sie behindert nur. Also der Weg zum Layout, und die Anleitung dazu.
 */

import { h, meldung } from './hilfen.js';

/** Fügt ein Zeichen an der Einfügemarke ein und gibt den Fokus zurück. */
function einfuegen(feld, zeichen, beiAenderung) {
  if (!feld) return;
  const anfang = feld.selectionStart ?? feld.value.length;
  const ende = feld.selectionEnd ?? feld.value.length;
  feld.value = feld.value.slice(0, anfang) + zeichen + feld.value.slice(ende);
  const neu = anfang + zeichen.length;
  feld.focus();
  feld.setSelectionRange(neu, neu);
  if (beiAenderung) beiAenderung(feld.value);
}

/** Die Leiste unter dem Antwortfeld. Gibt null zurück, wenn sie nichts nützt. */
export function zeichenleiste(sprache, feldHolen, beiAenderung) {
  const zeichen = sprache?.sonderzeichen || [];
  if (!zeichen.length && !sprache?.tastatur_empfohlen) return null;

  const kasten = h('div', {});
  if (zeichen.length) {
    const leiste = h('div', { class: 'zeichenleiste' });
    for (const z of zeichen) {
      leiste.append(h('button', {
        class: 'zeichen', type: 'button', lang: sprache.code,
        title: `${z} einfügen`,
        // Kein Fokusverlust im Antwortfeld
        onmousedown: (e) => e.preventDefault(),
        onclick: () => einfuegen(feldHolen(), z, beiAenderung),
      }, z));
    }
    kasten.append(leiste);
  }
  if (sprache?.tastatur_empfohlen) {
    kasten.append(h('div', { class: 'tastaturhinweis' },
      h('span', { text: `Für ${sprache.name} lohnt ein eigenes Tastaturlayout — `
                      + 'die Leiste oben hilft nur bei den Betonungszeichen.' }),
      h('a', { href: '#/tastatur', text: 'Wie geht das?' })));
  }
  return kasten;
}

/* ------------------------------------------------------------- Hilfeseite */

function geraet() {
  const kennung = `${navigator.userAgent} ${navigator.platform || ''}`;
  if (/iPhone|iPad|iPod/.test(kennung)
      || (/Mac/.test(kennung) && navigator.maxTouchPoints > 1)) return 'ios';
  if (/Android/.test(kennung)) return 'android';
  if (/Mac/.test(kennung)) return 'mac';
  if (/Win/.test(kennung)) return 'windows';
  return 'mac';
}

const ANLEITUNGEN = {
  mac: {
    name: 'Mac',
    schritte: [
      ['Systemeinstellungen öffnen, dann ', ['b', 'Tastatur'], '.'],
      ['Bei ', ['b', 'Texteingabe'], ' neben ', ['b', 'Eingabequellen'],
       ' auf ', ['b', 'Bearbeiten…'], ' klicken.'],
      ['Unten links auf ', ['kbd', '+'], ', die Sprache suchen, ',
       ['b', 'Hinzufügen'], '.'],
      ['Im selben Fenster ', ['b', 'Eingabequellen in der Menüleiste anzeigen'],
       ' einschalten — sonst findet man den Wechsel nie wieder.'],
    ],
    wechsel: [['kbd', 'ctrl'], ' + ', ['kbd', 'Leertaste'],
              '. Auf neueren Geräten auch die ', ['kbd', '🌐'],
              '-Taste unten links. Oder oben rechts in der Menüleiste auf das '
              + 'Sprachkürzel klicken.'],
    dazu: ['Für einzelne Akzente braucht es oft gar keinen Wechsel: auf der '
           + 'deutschen Mac-Tastatur sind ', ['kbd', '´'], ' und ',
           ['kbd', '`'], ' (links neben der Löschtaste) sogenannte tote '
           + 'Tasten. Erst die Taste, dann den Vokal — ', ['kbd', '´'],
           ' dann ', ['kbd', 'e'], ' ergibt é.'],
  },
  windows: {
    name: 'Windows',
    schritte: [
      ['Einstellungen öffnen, dann ', ['b', 'Zeit und Sprache'], '.'],
      [['b', 'Sprache und Region'], ' wählen.'],
      ['Bei ', ['b', 'Bevorzugte Sprachen'], ' auf ', ['b', 'Sprache hinzufügen'],
       ', die Sprache suchen und hinzufügen.'],
      ['Windows lädt dabei auch die Rechtschreibhilfe mit — das darf man '
       + 'abwählen, die Tastatur kommt trotzdem.'],
    ],
    wechsel: [['kbd', 'Windows'], ' + ', ['kbd', 'Leertaste'],
              '. Älteres Kürzel: ', ['kbd', 'Alt'], ' + ', ['kbd', 'Umschalt'],
              '. Oder rechts unten in der Taskleiste auf das Sprachkürzel klicken.'],
    dazu: null,
  },
  ios: {
    name: 'iPhone und iPad',
    schritte: [
      ['Einstellungen öffnen, dann ', ['b', 'Allgemein'], '.'],
      [['b', 'Tastatur'], ' wählen, dann noch einmal ', ['b', 'Tastaturen'], '.'],
      [['b', 'Tastatur hinzufügen…'], ' antippen und die Sprache wählen.'],
    ],
    wechsel: ['Die ', ['kbd', '🌐'], '-Taste links unten auf der Tastatur '
              + 'antippen. Gedrückt halten zeigt alle Tastaturen auf einmal.'],
    dazu: ['Für einzelne Akzente genügt oft, den Buchstaben ',
           ['b', 'gedrückt zu halten'], ' — dann erscheinen é è ê ë zur Auswahl.'],
  },
  android: {
    name: 'Android',
    schritte: [
      ['Einstellungen öffnen, dann ', ['b', 'System'], ' und ',
       ['b', 'Sprachen und Eingabe'], '.'],
      [['b', 'Bildschirmtastatur'], ', dann die benutzte Tastatur (meist Gboard).'],
      [['b', 'Sprachen'], ' antippen, ', ['b', 'Tastatur hinzufügen'],
       ', die Sprache wählen.'],
    ],
    wechsel: ['Die ', ['kbd', '🌐'], '-Taste auf der Tastatur antippen, oder '
              + 'auf der Leertaste nach links und rechts wischen.'],
    dazu: ['Auch hier: den Buchstaben ', ['b', 'gedrückt halten'],
           ' zeigt die Varianten mit Akzent.'],
  },
};

function satz(teile) {
  return teile.map((t) => (Array.isArray(t) ? h(t[0], { text: t[1] }) : t));
}

export function zeichnen(behaelter) {
  const hier = geraet();
  const el = behaelter;
  el.append(h('h1', { text: 'Tastaturlayout wechseln' }));
  el.append(h('p', { text: 'Für Französisch, Spanisch und Mittelhochdeutsch '
                         + 'genügt meist die Zeichenleiste unter dem '
                         + 'Antwortfeld. Für Sprachen mit eigener Schrift — '
                         + 'Griechisch etwa — lohnt ein richtiges Layout, denn '
                         + 'dort tippt man ganze Wörter.' }));

  const kasten = h('div', { class: 'tastaturhilfe' });
  for (const [kennung, a] of Object.entries(ANLEITUNGEN)) {
    const ist = kennung === hier;
    const teil = h('details', {
      class: 'karte' + (ist ? ' dieses-geraet' : ''),
      open: ist,
    });
    teil.append(h('summary', {}, h('strong', { text: a.name })));
    teil.append(h('h3', { text: 'Sprache hinzufügen' }));
    teil.append(h('ol', {}, a.schritte.map((z) => h('li', {}, satz(z)))));
    teil.append(h('h3', { text: 'Umschalten' }));
    teil.append(h('p', {}, satz(a.wechsel)));
    if (a.dazu) {
      teil.append(h('h3', { text: 'Oft reicht weniger' }));
      teil.append(h('p', {}, satz(a.dazu)));
    }
    kasten.append(teil);
  }
  el.append(kasten);

  el.append(h('div', { class: 'karte' },
    h('h3', { style: 'margin-top:0', text: 'Zum Ausprobieren' }),
    h('p', { class: 'leise', text: 'Hier tippen und sehen, ob das Layout sitzt:' }),
    h('input', { type: 'text', placeholder: 'Probe…', lang: 'el' })));

  el.append(h('div', { class: 'frage-werkzeuge', style: 'justify-content:flex-start' },
    h('button', { onclick: () => history.back() }, 'Zurück')));
}
