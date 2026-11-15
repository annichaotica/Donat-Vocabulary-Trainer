/* Der Lehrgang — ausführlicher als ein Rundgang, kürzer als ein Buch.
 *
 * »Mir sind diese vier Rundgänge zu kurz und zu oberflächlich.
 * Außerdem fehlt völlig etwas zur Rolle der KI, wie man Verben eingibt
 * und so weiter.«
 *
 * Die Rundgänge sind nicht zu kurz — sie sind die falsche Form für
 * diesen Inhalt. Eine Sprechblase trägt drei Sätze und kann nur
 * zeigen, was gerade auf dem Bildschirm steht. Was fehlte, ist das
 * Weltbild: Lexem, Bedeutungen, Formen, und dass Aufgaben ERZEUGT
 * werden. Ohne das sind Merkmale, Freigabe und die Rolle der KI nicht
 * erklärbar, weil die Wörter fehlen, in denen man es sagen könnte.
 *
 * Darum beides nebeneinander: die Rundgänge zeigen weiterhin, wo was
 * liegt. Der Lehrgang erklärt, warum.
 *
 * EIN KAPITEL IST EINE SEITE. Kein Ausklapper, keine lange Rolle.
 * Wer eine Seite sieht, liest sie zu Ende; wer eine Rolle sieht,
 * überfliegt sie. Und jedes Kapitel endet mit einer Handlung im
 * Übungskurs — gelesen ist nicht gekonnt.
 */

import { h, leeren, anfuegen } from './hilfen.js';
import { SPUREN } from './lehrgang_inhalt.js';

const GESCHAFFT = 'vokabeltrainer.lehrgang';


function geschafft() {
  try { return JSON.parse(localStorage.getItem(GESCHAFFT) || '[]'); }
  catch { return []; }
}

function merken(marke) {
  try {
    const alle = new Set(geschafft());
    alle.add(marke);
    localStorage.setItem(GESCHAFFT, JSON.stringify([...alle]));
  } catch { /* privates Fenster — dann eben ohne Gedächtnis */ }
}

const marke = (spur, nr) => `${spur}:${nr}`;


// ------------------------------------------------------------ Übersicht

export async function zeichnen(behaelter, spurKennung = null, nr = null) {
  if (spurKennung && nr !== null) return kapitel(behaelter, spurKennung, nr);

  const el = leeren(behaelter);
  el.append(h('h1', { text: 'Lehrgang' }));
  el.append(h('p', { class: 'leise',
    text: 'Zwei Spuren, weil zwei Leute Verschiedenes brauchen. Wer nur '
        + 'lernt, muss nie wissen, was ein Merkmalsbündel ist; wer den '
        + 'Bestand pflegt, kommt ohne nicht aus. Jedes Kapitel endet mit '
        + 'etwas, das du im Übungskurs ausprobierst.' }));

  const fertig = new Set(geschafft());
  for (const spur of SPUREN) {
    const karte = h('div', { class: 'karte' },
      h('h2', { style: 'margin-top:0', text: spur.name }),
      h('p', { class: 'leise', style: 'margin:0 0 .2rem', text: spur.fuer }),
      h('p', { class: 'leise', style: 'margin:0 0 .8rem', text: spur.dauer }));
    spur.kapitel.forEach((k, i) => {
      const fertigJa = fertig.has(marke(spur.kennung, i));
      karte.append(h('div', { class: 'lehrgangszeile' },
        h('button', {
          class: fertigJa ? 'schlicht' : '',
          onclick: () => { location.hash = `#/lehrgang/${spur.kennung}/${i}`; },
        }, fertigJa ? 'Noch einmal' : 'Lesen'),
        h('span', {}, h('b', { text: `${i + 1}. ${k.titel}` }),
          h('span', { class: 'leise', text: ` · ${k.dauer}` })),
        h('span', { class: 'leise',
                    text: fertigJa ? 'geschafft' : '' })));
    });
    el.append(karte);
  }

  el.append(h('p', { class: 'leise' },
    'Die kurzen Rundgänge durch die Oberfläche stehen in der ',
    h('a', { href: '#/hilfe' }, 'Anleitung'), '.'));
}


// --------------------------------------------------------- Ein Kapitel

function kapitel(behaelter, spurKennung, nr) {
  const spur = SPUREN.find((s) => s.kennung === spurKennung);
  const k = spur?.kapitel[nr];
  if (!k) { location.hash = '#/lehrgang'; return; }

  const el = leeren(behaelter);
  el.append(h('p', { class: 'leise' },
    h('a', { href: '#/lehrgang' }, spur.name),
    ` · Kapitel ${nr + 1} von ${spur.kapitel.length} · ${k.dauer}`));
  el.append(h('h1', { text: k.titel }));

  const kasten = h('div', { class: 'karte lehrgangstext' });
  for (const teil of k.teile) kasten.append(bauen(teil));
  el.append(kasten);

  // Weiterblättern. »Gelesen« wird beim Weitergehen vermerkt, nicht
  // beim Öffnen: wer eine Seite aufschlägt und sofort wegklickt, hat
  // sie nicht gelesen.
  const weiter = nr + 1 < spur.kapitel.length;
  el.append(h('div', { class: 'frage-werkzeuge',
                       style: 'justify-content:flex-start;margin-top:1rem' },
    nr > 0
      ? h('button', {
          onclick: () => { location.hash = `#/lehrgang/${spurKennung}/${nr - 1}`; },
        }, 'Zurück')
      : null,
    h('button', {
      class: 'wichtig',
      onclick: () => {
        merken(marke(spurKennung, nr));
        location.hash = weiter
          ? `#/lehrgang/${spurKennung}/${nr + 1}` : '#/lehrgang';
      },
    }, weiter ? 'Gelesen, weiter' : 'Gelesen — zur Übersicht'),
    h('button', { class: 'schlicht',
                  onclick: () => { location.hash = '#/lehrgang'; } },
      'Abbrechen')));
}


function bauen([art, a, b]) {
  if (art === 'absatz') return h('p', { text: a });
  if (art === 'merke') {
    return h('p', { class: 'hinweiskasten' }, h('b', { text: 'Merke: ' }), a);
  }
  if (art === 'liste') {
    return h('ul', {}, a.map((z) => h('li', { text: z })));
  }
  if (art === 'bild') {
    // `loading=lazy` und feste Maße: ohne sie springt der Text, während
    // das Bild nachlädt, und man verliert die Zeile, die man gerade
    // liest.
    return h('figure', { class: 'lehrgangsbild' },
      h('img', { src: `/bilder/lehrgang/${a}.png`, alt: b,
                 loading: 'lazy' }),
      h('figcaption', { class: 'leise', text: b }));
  }
  if (art === 'tun') {
    return h('p', { class: 'lehrgangstun' },
      h('b', { text: 'Jetzt du: ' }),
      h('a', { href: a }, b));
  }
  return h('p', { text: String(a) });
}
