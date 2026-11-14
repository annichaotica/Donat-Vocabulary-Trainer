/* Wegweiser. Adressen über das Raute-Zeichen, damit kein Server nötig ist,
 * der alle Pfade auf index.html umschreibt. */

import { api } from './api.js';
import { h, leeren, meldung } from './hilfen.js';
import { zustand, merken, darstellungSetzen } from './zustand.js';
import * as uebersicht from './ansicht_uebersicht.js';
import * as lernansicht from './ansicht_lernen.js';
import * as wortschatz from './ansicht_wortschatz.js';
import * as einstellungen from './ansicht_einstellungen.js';
import * as tastatur from './tastatur.js';
import * as ziele from './ansicht_ziele.js';

// Zusätzliche Stildatei (Zeichenleiste, Tastaturhilfe) nachladen. Von hier
// aus, damit index.html unberührt bleibt.
document.head.append(Object.assign(document.createElement('link'),
  { rel: 'stylesheet', href: '/css/zusatz.css' }));

const inhalt = document.getElementById('inhalt');
const kopf = document.getElementById('kopf');
let laufendeSitzung = null;

async function darstellungAnwenden() {
  if (!zustand.benutzerId) { darstellungSetzen(null); return; }
  try {
    darstellungSetzen(await api.legasthenieLesen(zustand.benutzerId));
  } catch { darstellungSetzen(null); }
}

async function kopfzeile() {
  if (!zustand.benutzerId) { kopf.hidden = true; return; }
  kopf.hidden = false;
  let person = null;
  try {
    person = (await api.benutzer()).find((p) => p.id === zustand.benutzerId) || null;
  } catch { /* nichts */ }
  if (!person) { merken({ benutzerId: null }); kopf.hidden = true; return; }

  const knopf = document.getElementById('knopf-profil');
  knopf.textContent = person.name.slice(0, 1).toUpperCase();
  knopf.style.background = person.farbe;
  knopf.title = `${person.name} — Profil wechseln`;

  let zusatz = '';
  if (zustand.sammlungId) {
    try {
      const alle = await api.sammlungen(zustand.benutzerId);
      const s = alle.find((x) => x.id === zustand.sammlungId);
      if (s) zusatz = s.name; else merken({ sammlungId: null });
    } catch { /* nichts */ }
  }
  document.getElementById('kopf-zusatz').textContent = zusatz;
  const istStart = (location.hash || '#/').startsWith('#/uebersicht')
                 || location.hash === '#/' || !location.hash;
  document.getElementById('zurueck').hidden = istStart;
}

function verdrahten() {
  for (const knopf of document.querySelectorAll('.kopf-knoepfe button[data-ziel]')) {
    knopf.addEventListener('click', () => { location.hash = knopf.dataset.ziel; });
  }
  document.getElementById('knopf-profil').addEventListener('click', () => {
    location.hash = '#/profile';
  });
  document.getElementById('zurueck').addEventListener('click', () => {
    if (history.length > 1) history.back(); else location.hash = '#/uebersicht';
  });
  window.addEventListener('hashchange', wegweisen);
}

async function wegweisen() {
  if (laufendeSitzung) { laufendeSitzung.beenden(); laufendeSitzung = null; }
  const weg = (location.hash || '#/').slice(1);
  const teile = weg.split('/').filter(Boolean);

  await darstellungAnwenden();
  await kopfzeile();
  inhalt.focus({ preventScroll: true });

  // Ohne Profil geht nichts weiter.
  if (!zustand.benutzerId && teile[0] !== 'profile') {
    return uebersicht.zeichnenProfile(inhalt);
  }

  try {
    switch (teile[0]) {
      case undefined:
      case 'uebersicht':
        return await uebersicht.zeichnen(inhalt);
      case 'profile':
        return await uebersicht.zeichnenProfile(inhalt);
      case 'lernen':
        // #/lernen/ziel/7 zieht aus einem Lernziel, #/lernen/frei übt frei.
        if (teile[1] === 'ziel' && teile[2]) {
          laufendeSitzung = await lernansicht.zeichnen(inhalt, {
            lernzielId: Number(teile[2]),
          });
          return;
        }
        laufendeSitzung = await lernansicht.zeichnen(inhalt, {
          nur: teile[1] || null,
          sammlungId: zustand.sammlungId,
          lektionId: zustand.lektionId,
        });
        return;
      case 'ziele':
        return await ziele.zeichnen(inhalt);
      case 'wortschatz':
        return await wortschatz.zeichnen(inhalt);
      case 'wort':
        return await wortschatz.zeichnenEinzeln(inhalt, Number(teile[1]));
      case 'neu':
        return await wortschatz.zeichnenNeu(inhalt);
      case 'einstellungen':
        return await einstellungen.zeichnen(inhalt);
      case 'tastatur':
        return tastatur.zeichnen(inhalt);
      default:
        leeren(inhalt).append(h('div', { class: 'leer' },
          h('p', { text: 'Diese Seite gibt es nicht.' }),
          h('button', { onclick: () => { location.hash = '#/uebersicht'; } }, 'Zur Übersicht')));
    }
  } catch (fehler) {
    console.error(fehler);
    leeren(inhalt).append(h('div', { class: 'karte' },
      h('h2', { text: 'Das ging schief' }),
      h('p', { text: fehler.message || String(fehler) }),
      h('button', { onclick: () => wegweisen() }, 'Nochmal')));
  }
}

verdrahten();
wegweisen();

// Hilfe über die Tastatur — auf dem Mac der schnellste Weg.
document.addEventListener('keydown', (e) => {
  if (e.metaKey || e.ctrlKey || e.altKey) return;
  if (document.activeElement && ['INPUT', 'TEXTAREA', 'SELECT']
      .includes(document.activeElement.tagName)) return;
  if (e.key === 'l') location.hash = '#/lernen';
  else if (e.key === 'w') location.hash = '#/wortschatz';
  else if (e.key === 'u') location.hash = '#/uebersicht';
});
