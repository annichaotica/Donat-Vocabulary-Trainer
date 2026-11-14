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

/* ------------------------------------------------------ Tastaturbelegung
 *
 * »Ich such mich dumm und dämlich, wo die Buchstaben sind.« Die Anleitung
 * zum Umschalten löst das nicht — danach liegt zwar das Layout richtig,
 * aber man weiß immer noch nicht, dass ψ auf dem C liegt.
 *
 * Zwei Dinge sind dabei wichtig und leicht zu übersehen:
 *
 * **Die Beschriftung der eigenen Tastatur zählt, nicht die amerikanische.**
 * Auf einer deutschen Tastatur sind Y und Z vertauscht. υ liegt auf der
 * Taste, die mit Z beschriftet ist; ζ auf der mit Y. Eine Abbildung, die
 * die amerikanischen Namen zeigt, schickt einen genau zweimal an die
 * falsche Stelle.
 *
 * **Die Abbildung lernt mit.** Beim Tippen im Probefeld steht in
 * `event.code` die PHYSISCHE Taste und in `event.key` das Zeichen, das
 * wirklich herauskommt. Damit lässt sich die Belegung nicht nur anzeigen,
 * sondern nachmessen — und wenn ein Layout von der hinterlegten Annahme
 * abweicht, zeigt die Seite hinterher die Wahrheit statt der Annahme.
 */

/** Die physischen Tastenreihen, mit der Beschriftung einer DEUTSCHEN Tastatur. */
const REIHEN = [
  [['KeyQ', 'Q'], ['KeyW', 'W'], ['KeyE', 'E'], ['KeyR', 'R'], ['KeyT', 'T'],
   ['KeyY', 'Z'], ['KeyU', 'U'], ['KeyI', 'I'], ['KeyO', 'O'], ['KeyP', 'P'],
   ['BracketLeft', 'Ü'], ['BracketRight', '+']],
  [['KeyA', 'A'], ['KeyS', 'S'], ['KeyD', 'D'], ['KeyF', 'F'], ['KeyG', 'G'],
   ['KeyH', 'H'], ['KeyJ', 'J'], ['KeyK', 'K'], ['KeyL', 'L'],
   ['Semicolon', 'Ö'], ['Quote', 'Ä']],
  [['KeyZ', 'Y'], ['KeyX', 'X'], ['KeyC', 'C'], ['KeyV', 'V'], ['KeyB', 'B'],
   ['KeyN', 'N'], ['KeyM', 'M'], ['Comma', ','], ['Period', '.'],
   ['Slash', '-']],
];

const BELEGUNGEN = {
  el: {
    name: 'Griechisch',
    tasten: {
      KeyA: 'α', KeyB: 'β', KeyC: 'ψ', KeyD: 'δ', KeyE: 'ε', KeyF: 'φ',
      KeyG: 'γ', KeyH: 'η', KeyI: 'ι', KeyJ: 'ξ', KeyK: 'κ', KeyL: 'λ',
      KeyM: 'μ', KeyN: 'ν', KeyO: 'ο', KeyP: 'π', KeyR: 'ρ', KeyS: 'σ',
      KeyT: 'τ', KeyU: 'θ', KeyV: 'ω', KeyW: 'ς', KeyX: 'χ', KeyY: 'υ',
      KeyZ: 'ζ',
      KeyQ: ';', Semicolon: '΄', Quote: "'",
    },
    /** Woran man erkennt, dass das Layout WIRKLICH umgeschaltet ist.
     *  Ohne diese Prüfung lernte die Abbildung beim Tippen mit deutscher
     *  Tastatur lauter lateinische Buchstaben und machte sich selbst
     *  unbrauchbar. */
    schrift: /[\u0370-\u03FF\u1F00-\u1FFF]/,
    falschesLayout: 'Das sieht noch nach der deutschen Tastatur aus — '
                  + 'umgeschaltet wird mit ctrl + Leertaste.',
    /** Tasten, die allein nichts schreiben, sondern den nächsten Buchstaben
     *  verändern. */
    tot: { Semicolon: 'Betonungszeichen (Tonos)' },
    hinweise: [
      ['Betonung', 'Erst die Taste ', ['kbd', 'Ö'], ', dann den Vokal: ',
       ['b', 'ά έ ή ί ό ύ ώ'], '. Die Taste schreibt allein nichts — das ist '
       + 'richtig so.'],
      ['Trema', 'Erst ', ['kbd', 'Umschalt'], ' + ', ['kbd', 'Ö'],
       ', dann ι oder υ: ', ['b', 'ϊ ϋ'], '.'],
      ['Schluss-Sigma', 'σ und ς sind zwei Tasten: ', ['kbd', 'S'],
       ' mitten im Wort, ', ['kbd', 'W'], ' am Wortende — ',
       ['b', 'σπίτι'], ' gegen ', ['b', 'πώς'], '.'],
      ['Fragezeichen', 'Das griechische Fragezeichen sieht aus wie ein '
       + 'Strichpunkt und liegt auf ', ['kbd', 'Q'], ': ',
       ['b', 'Τι κάνεις;'], ' — kein Tippfehler.'],
      ['Y und Z', 'Auf einer deutschen Tastatur sind sie vertauscht. υ liegt '
       + 'auf der Taste mit dem aufgedruckten ', ['kbd', 'Z'], ', ζ auf der '
       + 'mit dem ', ['kbd', 'Y'], '.'],
    ],
  },
};

/* ------------------------------------------------------------ Umschrift
 *
 * »Kannst du dem Programm nicht beibringen, das Tastaturlayout je nach
 * Antwort umzustellen?« — Eine Webseite kann das nicht, und sie darf es
 * auch nicht: eine Seite, die die Eingabe des Rechners umschaltet, wäre
 * ein Sicherheitsproblem. Auch mit Systemrechten käme der Trainer nicht
 * heran.
 *
 * Er kann aber dasselbe tun, was die griechische Systembelegung tut:
 * dieselben physischen Tasten auf griechische Buchstaben abbilden. Die
 * Abbildung steht ohnehin schon oben, für die Tastaturhilfe. Man tippt
 * `grafo` und im Feld steht `γραφο` — ohne Umschalten, auf jedem Gerät,
 * und wer doch umgeschaltet hat, merkt nichts davon: griechische Zeichen
 * gehen unangetastet durch.
 *
 * Gearbeitet wird mit `event.code`, also der PHYSISCHEN Taste. Darum ist
 * es gleichgültig, ob jemand eine deutsche oder eine amerikanische
 * Tastatur hat — auf beiden liegt α auf derselben Taste wie im
 * griechischen Layout.
 */

/** Der Tonos auf den Vokalen, und das Trema auf ι und υ. */
const BETONT = {
  α: 'ά', ε: 'έ', η: 'ή', ι: 'ί', ο: 'ό', υ: 'ύ', ω: 'ώ',
  Α: 'Ά', Ε: 'Έ', Η: 'Ή', Ι: 'Ί', Ο: 'Ό', Υ: 'Ύ', Ω: 'Ώ',
};
const TREMA = { ι: 'ϊ', υ: 'ϋ', Ι: 'Ϊ', Υ: 'Ϋ' };

/** Gibt es für diese Sprache überhaupt etwas umzuschreiben? */
export function kannUmschreiben(code) {
  return Boolean(code && Object.hasOwn(BELEGUNGEN, code)
                 && BELEGUNGEN[code].schrift);
}

/* Hängt die Umschrift an ein Eingabefeld.
 *
 * Gibt eine Funktion zurück, die sie wieder abmeldet — ohne die bliebe
 * bei jedem Neuzeichnen ein Behandler mehr hängen. Genau dieser Fehler
 * ist in diesem Projekt schon zweimal passiert.
 */
export function umschriftAnhaengen(feld, code) {
  if (!feld || !kannUmschreiben(code)) return () => {};
  const b = BELEGUNGEN[code];
  const tasten = { ...b.tasten, ...gelernt(code) };
  let wartend = null;              // gedrückte tote Taste

  const einfuegen = (zeichen) => {
    const a = feld.selectionStart ?? feld.value.length;
    const e = feld.selectionEnd ?? a;
    feld.value = feld.value.slice(0, a) + zeichen + feld.value.slice(e);
    const neu = a + zeichen.length;
    feld.setSelectionRange(neu, neu);
    feld.dispatchEvent(new Event('input', { bubbles: true }));
  };

  const behandler = (e) => {
    if (e.ctrlKey || e.metaKey || e.altKey) return;
    // Schon in der Zielschrift? Dann ist das Layout umgeschaltet und
    // hier gibt es nichts zu tun.
    if (e.key.length === 1 && b.schrift.test(e.key)) { wartend = null; return; }
    // Die tote Taste: schreibt allein nichts, verändert das Nächste.
    if (b.tot && Object.hasOwn(b.tot, e.code)) {
      e.preventDefault();
      wartend = e.shiftKey ? 'trema' : 'tonos';
      return;
    }
    const zeichen = tasten[e.code];
    if (!zeichen || zeichen.length !== 1) { wartend = null; return; }
    // Nur lateinische Tasteneingaben ersetzen — was der Browser als
    // Steuertaste meldet (Enter, Pfeile), hat keine Länge 1.
    if (e.key.length !== 1) return;
    e.preventDefault();
    let aus = e.shiftKey ? zeichen.toUpperCase() : zeichen;
    // Schluss-Sigma kennt kein Großzeichen; Σ liegt auf derselben Taste.
    if (zeichen === 'ς' && e.shiftKey) aus = 'Σ';
    if (wartend === 'tonos' && BETONT[aus]) aus = BETONT[aus];
    else if (wartend === 'trema' && TREMA[aus]) aus = TREMA[aus];
    wartend = null;
    einfuegen(aus);
  };

  feld.addEventListener('keydown', behandler);
  return () => feld.removeEventListener('keydown', behandler);
}

const SPEICHER = 'vokabeltrainer.tastatur.';

function gelernt(code) {
  try {
    return JSON.parse(localStorage.getItem(SPEICHER + code) || '{}');
  } catch { return {}; }
}

function lernen(code, taste, zeichen) {
  try {
    const bisher = gelernt(code);
    if (bisher[taste] === zeichen) return false;
    bisher[taste] = zeichen;
    localStorage.setItem(SPEICHER + code, JSON.stringify(bisher));
    return true;
  } catch { return false; }
}

export function hatBelegung(code) {
  return Boolean(BELEGUNGEN[code]);
}

/** Nur die Tasten — Grundlage für die große Tafel und die kleine beim Tippen.
 *
 *  Gibt das Bild und die Tastenknöpfe zurück, damit der Aufrufer
 *  hervorheben kann, ohne die Baumstruktur zu kennen.
 */
function tastenbild(code, { klein = false, beiKlick = null } = {}) {
  const b = BELEGUNGEN[code];
  const gemessen = gelernt(code);
  const tasten = new Map();
  const bild = h('div', { class: 'tastaturbild' + (klein ? ' klein' : '') });
  for (const [i, reihe] of REIHEN.entries()) {
    const zeile = h('div', {
      class: 'tastenreihe',
      style: `padding-left:${i * (klein ? 0.7 : 1.1)}rem`,
    });
    for (const [taste, aufdruck] of reihe) {
      const zeichen = gemessen[taste] ?? b.tasten[taste] ?? '';
      const knopf = h('button', {
        class: 'taste' + (b.tot[taste] ? ' tot' : '') + (zeichen ? '' : ' leer'),
        type: 'button',
        title: b.tot[taste] ? b.tot[taste]
                            : (zeichen ? `${zeichen} auf ${aufdruck}` : aufdruck),
        // Kein Fokusverlust im Antwortfeld — sonst ist die Einfügemarke weg,
        // und genau da wollte man ja weiterschreiben.
        onmousedown: (e) => e.preventDefault(),
        onclick: () => beiKlick && beiKlick(zeichen, taste),
      },
        h('span', { class: 'taste-zeichen', lang: code, text: zeichen || '·' }),
        h('span', { class: 'taste-aufdruck', text: aufdruck }));
      tasten.set(taste, knopf);
      zeile.append(knopf);
    }
    bild.append(zeile);
  }
  return { bild, tasten, gemessen };
}


/** Die Abbildung samt Suche und Probefeld. */
export function belegung(code) {
  const b = BELEGUNGEN[code];
  if (!b) return null;
  const el = h('div', { class: 'karte' });
  let gemessen = gelernt(code);

  el.append(h('h2', { style: 'margin-top:0' },
    `Wo liegt was? (${b.name})`,
    h('span', { class: 'marke', text: 'deutsche Tastatur' })));
  el.append(h('p', { class: 'leise',
    text: 'Die großen Zeichen sind das, was herauskommt; klein darunter '
        + 'steht, was auf deiner Taste aufgedruckt ist.' }));

  const suche = h('input', {
    type: 'search', placeholder: 'Buchstaben suchen, z.B. ψ',
    lang: code, style: 'margin-bottom:.8rem',
    oninput: () => hervorheben(suche.value.trim()),
  });
  el.append(suche);

  const { bild, tasten } = tastenbild(code, {
    beiKlick: (zeichen) => { suche.value = zeichen; hervorheben(zeichen); },
  });
  el.append(bild);

  function hervorheben(gesucht) {
    const ziel = (gesucht || '').toLowerCase();
    for (const [taste, knopf] of tasten) {
      const zeichen = (gemessen[taste] ?? b.tasten[taste] ?? '').toLowerCase();
      knopf.classList.toggle('gesucht', Boolean(ziel) && zeichen === ziel);
    }
  }

  for (const [titel, ...rest] of b.hinweise) {
    el.append(h('p', { class: 'belegungshinweis' },
      h('strong', { text: titel + ': ' }), ...satz(rest)));
  }

  // Probefeld: hier wird gemessen statt geraten.
  const stand = h('p', { class: 'leise' });
  const warnung = h('p', { class: 'befund hinweis', hidden: true });
  const probe = h('input', {
    type: 'text', lang: code,
    placeholder: `Hier tippen — passt das Layout?`,
    onkeydown: (e) => {
      const knopf = tasten.get(e.code);
      if (!knopf) return;
      knopf.classList.add('gedrueckt');
      setTimeout(() => knopf.classList.remove('gedrueckt'), 220);
      // Ein einzelnes Zeichen ist das Ergebnis der Taste. "Dead" heißt:
      // tote Taste. Alles andere (Enter, Shift, …) sagt nichts aus.
      if (!e.key || e.key.length !== 1 || e.ctrlKey || e.metaKey || e.altKey) {
        return;
      }
      const zeichen = e.shiftKey ? e.key.toLowerCase() : e.key;
      // Nur lernen, was in der Schrift der Sprache steht. Sonst schriebe
      // ein Tippversuch mit deutscher Tastatur lauter lateinische
      // Buchstaben in die Abbildung — und die wäre hinterher falsch.
      if (b.schrift && !b.schrift.test(zeichen)) {
        warnung.textContent = b.falschesLayout || '';
        warnung.hidden = false;
        return;
      }
      warnung.hidden = true;
      if (lernen(code, e.code, zeichen)) {
        gemessen = gelernt(code);
        knopf.querySelector('.taste-zeichen').textContent = zeichen;
        knopf.classList.remove('leer');
      }
    },
  });
  el.append(h('div', { style: 'margin-top:1rem' },
    h('label', { class: 'feldname', text: 'Ausprobieren' }), probe,
    warnung, stand));
  stand.append('Die Abbildung lernt dabei mit: was deine Tastatur wirklich '
             + 'schreibt, steht gleich darüber. ');
  stand.append(h('button', {
    class: 'schlicht',
    onclick: () => {
      try { localStorage.removeItem(SPEICHER + code); } catch { /* egal */ }
      gemessen = {};
      for (const [taste, knopf] of tasten) {
        const z = b.tasten[taste] ?? '';
        knopf.querySelector('.taste-zeichen').textContent = z || '·';
        knopf.classList.toggle('leer', !z);
      }
      meldung('Gemessenes verworfen.');
    },
  }, 'Gemessenes verwerfen'));
  return el;
}

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

const MERKTAFEL_OFFEN = 'vokabeltrainer.merktafel';

function merktafelOffen() {
  try { return localStorage.getItem(MERKTAFEL_OFFEN) === 'ja'; } catch { return false; }
}

function merktafelMerken(offen) {
  try { localStorage.setItem(MERKTAFEL_OFFEN, offen ? 'ja' : 'nein'); } catch { /* egal */ }
}

/** Die Leiste unter dem Antwortfeld. Gibt null zurück, wenn sie nichts nützt. */
export function zeichenleiste(sprache, feldHolen, beiAenderung) {
  const zeichen = sprache?.sonderzeichen || [];
  const belegungDa = hatBelegung(sprache?.code);
  if (!zeichen.length && !sprache?.tastatur_empfohlen && !belegungDa) return null;

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
  // Die Merktafel beim Tippen: aufklappen, nachsehen, weiterschreiben.
  // Der Umweg über eine eigene Seite kostet die halbe Sitzung — man käme
  // mit der angefangenen Antwort nicht zurück.
  if (belegungDa) {
    const tafel = h('div', { hidden: !merktafelOffen() });
    const knopf = h('button', {
      type: 'button', class: 'schlicht merktafel-knopf',
      'aria-expanded': String(merktafelOffen()),
      // Ohne das verliert das Antwortfeld die Einfügemarke.
      onmousedown: (e) => e.preventDefault(),
      onclick: () => {
        const offen = tafel.hidden;
        tafel.hidden = !offen;
        knopf.setAttribute('aria-expanded', String(offen));
        knopf.textContent = offen ? 'Belegung ausblenden'
                                  : 'Wo liegt welcher Buchstabe?';
        merktafelMerken(offen);
        const feld = feldHolen();
        if (feld) feld.focus();
      },
    }, merktafelOffen() ? 'Belegung ausblenden'
                        : 'Wo liegt welcher Buchstabe?');

    // Ein Klick auf eine Taste schreibt das Zeichen. Gedacht ist die Tafel
    // zum Nachsehen — aber wenn man schon hinzeigt, soll sie auch tippen.
    const { bild } = tastenbild(sprache.code, {
      klein: true,
      beiKlick: (z) => {
        if (z && z !== '·') einfuegen(feldHolen(), z, beiAenderung);
      },
    });
    tafel.append(bild);
    tafel.append(h('p', { class: 'leise merktafel-fuss' },
      'Betonung: erst ', h('kbd', { text: 'Ö' }), ', dann den Vokal. ',
      'Wortende-ς liegt auf ', h('kbd', { text: 'W' }), '. ',
      h('a', { href: `#/tastatur/${sprache.code}`, text: 'Ganze Tafel' })));
    kasten.append(h('div', { class: 'merktafel' }, knopf, tafel));
  }

  if (sprache?.tastatur_empfohlen && !belegungDa) {
    kasten.append(h('div', { class: 'tastaturhinweis' },
      h('span', { text: `Für ${sprache.name} lohnt ein eigenes Tastaturlayout — `
                      + 'die Leiste oben hilft nur bei den Betonungszeichen.' }),
      h('a', { href: `#/tastatur/${sprache.code}`, text: 'Wie geht das?' })));
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

export function zeichnen(behaelter, sprache = null) {
  const hier = geraet();
  const el = behaelter;
  el.append(h('h1', { text: 'Tastatur' }));

  // Die Belegung zuerst: wer hierherkommt, hat das Layout meist schon und
  // sucht nur noch die Buchstaben.
  const bild = belegung(sprache);
  if (bild) el.append(bild);
  el.append(h('h2', { text: 'Layout hinzufügen und umschalten' }));
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

  if (!bild) {
    el.append(h('div', { class: 'karte' },
      h('h3', { style: 'margin-top:0', text: 'Zum Ausprobieren' }),
      h('p', { class: 'leise',
               text: 'Hier tippen und sehen, ob das Layout sitzt:' }),
      h('input', { type: 'text', placeholder: 'Probe…' })));
  }

  el.append(h('div', { class: 'frage-werkzeuge', style: 'justify-content:flex-start' },
    h('button', { onclick: () => history.back() }, 'Zurück')));
}
