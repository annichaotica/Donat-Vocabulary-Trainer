/* Wegweiser. Adressen über das Raute-Zeichen, damit kein Server nötig ist,
 * der alle Pfade auf index.html umschreibt. */

import { api } from './api.js';
import { h, leeren, meldung, lesbareSchrift } from './hilfen.js';
import { zustand, merken, darstellungSetzen } from './zustand.js';
import * as marke from './marke.js';
import * as uebersicht from './ansicht_uebersicht.js';
import * as lernansicht from './ansicht_lernen.js';
import * as texte from './ansicht_texte.js';
import * as gezielt from './ansicht_gezielt.js';
import * as abtippen from './ansicht_abtippen.js';
import * as statistik from './ansicht_statistik.js';
import * as lehrgang from './ansicht_lehrgang.js';
import * as wortschatz from './ansicht_wortschatz.js';
import * as einstellungen from './ansicht_einstellungen.js';
import * as tastatur from './tastatur.js';
import * as spielzeichen from './spiel.js';
import * as zuspruch from './ansicht_zuspruch.js';
import * as ziele from './ansicht_ziele.js';
import * as freigabe from './ansicht_freigabe.js';
import * as einlesen from './ansicht_import.js';
import * as uebungen from './ansicht_uebungen.js';
import * as hilfe from './ansicht_hilfe.js';

// Zusätzliche Stildatei (Zeichenleiste, Tastaturhilfe) nachladen. Von hier
// aus, damit index.html unberührt bleibt.
document.head.append(Object.assign(document.createElement('link'),
  { rel: 'stylesheet', href: '/css/zusatz.css' }));

const kopf = document.getElementById('kopf');
let laufendeSitzung = null;

/** Ein FRISCHER Inhaltsbereich je Aufruf.
 *
 * Die Ansichten bauen sich stückweise auf und warten dazwischen auf die
 * Schnittstelle. Wechselt man in dieser Zeit die Seite, schrieb die alte
 * Ansicht danach weiter in denselben Bereich — und es standen zwei Seiten
 * untereinander. Das war über eine schnelle Leitung kaum zu sehen und über
 * eine langsame regelmäßig.
 *
 * Statt jede Ansicht einzeln prüfen zu lassen, ob sie noch die aktuelle
 * ist, bekommt jeder Aufruf seinen eigenen Bereich. Der alte wird aus der
 * Seite genommen; was dort noch ankommt, landet im Nirgendwo. Die Ansichten
 * selbst müssen davon nichts wissen.
 */
function frischerInhalt() {
  const alt = document.getElementById('inhalt');
  const neu = document.createElement('main');
  neu.id = 'inhalt';
  neu.className = 'inhalt';
  neu.tabIndex = -1;
  alt.replaceWith(neu);
  return neu;
}

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
  // Die Profilfarbe wählt jeder selbst; auf einem hellen Gelb ist
  // weiße Schrift nicht zu lesen.
  knopf.style.color = lesbareSchrift(person.farbe);
  knopf.title = `${person.name} — Profil wechseln`;

  let zusatz = '';
  let farbe = '';
  if (zustand.sammlungId) {
    try {
      const alle = await api.sammlungen(zustand.benutzerId);
      const s = alle.find((x) => x.id === zustand.sammlungId);
      if (s) { zusatz = s.name; farbe = s.farbe_wirksam || ''; }
      else merken({ sammlungId: null });
    } catch { /* nichts */ }
  }
  document.getElementById('kopf-zusatz').textContent = zusatz;
  // Die gewählte Sammlung nicht nur benennen, sondern zeigen: die
  // Kopfzeile bekommt ihre Farbe als Kante, und vor dem Namen steht
  // ein Punkt. Ein Name allein liest man nicht mehr, wenn er immer
  // dasteht — eine Farbe sieht man auch im Augenwinkel.
  // Nicht `kopf` nennen: so heißt in dieser Funktion schon etwas
  // anderes, und ein `const` desselben Namens legt die Zeile darüber
  // lahm, noch bevor es zugewiesen wird.
  const kopfleiste = document.getElementById('kopf');
  kopfleiste.style.setProperty('--sammlungsfarbe', farbe || 'transparent');
  kopfleiste.classList.toggle('hat-sammlung', Boolean(farbe));

  // Auf dem schmalen Gerät deckt die untere Leiste den Programmnamen ab —
  // dort ist der Name der Ansicht nützlicher.
  const weg = (location.hash || '#/').slice(1).split('/').filter(Boolean);
  document.getElementById('kopf-name').textContent = {
    uebersicht: 'Übersicht', wortschatz: 'Wortschatz', wort: 'Wort',
    neu: 'Neues Wort', lernen: 'Abfrage', ziele: 'Lernziele',
    freigabe: 'Freigabe', import: 'Datei einlesen', ueben: 'Sätze üben',
    hilfe: 'Anleitung', texte: 'Bücher und Texte',
    statistik: 'Fortschritt',
    zuspruch: 'Zuspruch',
    lehrgang: 'Lehrgang',
    einstellungen: 'Einstellungen',
    tastatur: 'Tastatur', profile: 'Profil wählen',
  }[weg[0]] || marke.NAME;

  // Den laufenden Reiter kennzeichnen.
  for (const knopf of document.querySelectorAll('.kopf-knoepfe button[data-ziel]')) {
    const aktiv = knopf.dataset.ziel === '#/' + (weg[0] || 'uebersicht');
    knopf.classList.toggle('aktiv', aktiv);
    if (aktiv) knopf.setAttribute('aria-current', 'page');
    else knopf.removeAttribute('aria-current');
  }

  const istStart = (location.hash || '#/').startsWith('#/uebersicht')
                 || location.hash === '#/' || !location.hash;
  document.getElementById('zurueck').hidden = istStart;

  // Tagesziel und Strähne. OHNE await: der Stand zählt über alle
  // Aufgaben, und die Kopfzeile darf darauf nicht warten. Bis die
  // Antwort da ist, bleibt der Ring stehen, wie er war.
  spielzeichen.auffrischen(zustand.benutzerId);
}

function verdrahten() {
  for (const knopf of document.querySelectorAll('.kopf-knoepfe button[data-ziel]')) {
    knopf.addEventListener('click', () => { location.hash = knopf.dataset.ziel; });
  }
  // Der Ring zeigt den Tagesstand und die Strähne — und führte bisher
  // mitten in eine Abfrage.
  //
  // »Da wurde mir jetzt aber ein spanischer Begriff gezeigt. Macht es
  // denn überhaupt Sinn, über diesen Button zum allgemeinen Lernen zu
  // springen?« — Nein. Er sprang nach #/lernen OHNE die Sammlung zu
  // leeren, also in das, was zuletzt eingestellt war; und er ist eine
  // Anzeige, kein Startknopf. Wer auf eine Zahl tippt, will wissen,
  // was dahintersteckt.
  //
  // »Dein Fortschritt« ist genau die Seite dazu: Stufe, Punkte,
  // Strähne, überbrückte Fehltage. Gestartet wird von der Übersicht,
  // wo auch steht, WAS man lernt.
  document.getElementById('kopf-spiel').addEventListener('click', () => {
    location.hash = '#/statistik';
  });
  document.getElementById('knopf-profil').addEventListener('click', () => {
    // Von außen gibt es nichts zu wechseln.
    location.hash = identitaet?.gebunden ? '#/einstellungen' : '#/profile';
  });
  document.getElementById('zurueck').addEventListener('click', () => {
    if (history.length > 1) history.back(); else location.hash = '#/uebersicht';
  });
  window.addEventListener('hashchange', wegweisen);
}

/** Steht die Identität fest, weil die Anfrage durch Cloudflare Access kam?
 *  Dann entfällt der Profilwähler — von außen handelt jeder als er selbst. */
let identitaet = null;

async function identitaetKlaeren() {
  if (identitaet !== null) return identitaet;
  try {
    identitaet = await api.ich();
  } catch {
    identitaet = { gebunden: false, benutzer: null };
  }
  if (identitaet.gebunden && identitaet.benutzer) {
    if (zustand.benutzerId !== identitaet.benutzer.id) {
      merken({ benutzerId: identitaet.benutzer.id, sammlungId: null });
    }
  }
  return identitaet;
}

/** Welche Sprache lernt die gewählte Sammlung gerade? */
async function spracheDerSammlung() {
  if (!zustand.sammlungId || !zustand.benutzerId) return null;
  try {
    const alle = await api.sammlungen(zustand.benutzerId);
    return (alle.find((s) => s.id === zustand.sammlungId) || {}).sprache || null;
  } catch { return null; }
}


async function wegweisen() {
  if (laufendeSitzung) { laufendeSitzung.beenden(); laufendeSitzung = null; }
  const inhalt = frischerInhalt();
  const weg = (location.hash || '#/').slice(1);
  const teile = weg.split('/').filter(Boolean);

  await identitaetKlaeren();
  await darstellungAnwenden();
  await kopfzeile();
  inhalt.focus({ preventScroll: true });

  // Von außen steht die Identität fest — der Profilwähler entfällt.
  if (identitaet?.gebunden && teile[0] === 'profile') {
    location.hash = '#/uebersicht';
    return;
  }
  // Ohne Profil geht nichts weiter. Aber nicht stillschweigend: merken,
  // wohin jemand eigentlich wollte, und nach der Wahl dorthin
  // zurückkehren. Sonst landet man unerklärt beim Profilwähler und
  // sucht die Seite, die man aufgerufen hatte.
  if (!zustand.benutzerId && teile[0] !== 'profile') {
    const ziel = location.hash || '#/uebersicht';
    return uebersicht.zeichnenProfile(inhalt, ziel !== '#/' ? ziel : null);
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
        {
          // Die Sitzung SYNCHRON anlegen und merken, bevor sie lädt. Sonst
          // bleibt beim Wegnavigieren während des Ladens eine verwaiste
          // Sitzung zurück, deren Tastaturbehandler weiterläuft.
          const optionen = (teile[1] === 'ziel' && teile[2])
            ? { lernzielId: Number(teile[2]) }
            : { nur: teile[1] || null, sammlungId: zustand.sammlungId,
                lektionId: zustand.lektionId };
          const sitzung = new lernansicht.Sitzung(inhalt, optionen);
          laufendeSitzung = sitzung;
          await sitzung.start();
          return;
        }
      case 'ziele':
        return await ziele.zeichnen(inhalt);
      case 'wortschatz':
        return await wortschatz.zeichnen(inhalt);
      case 'ueben':
        // #/ueben wählt aus, #/ueben/plan|frei|fehler übt, und
        // #/ueben/lektion/12 grenzt auf eine Lektion ein.
        {
          if (!teile[1]) return await uebungen.zeichnen(inhalt);
          const optionen = { sammlungId: zustand.sammlungId };
          if (teile[1] === 'lektion') optionen.lektionNr = Number(teile[2]);
          else if (teile[1] !== 'plan') optionen.nur = teile[1];
          const sitzung = new uebungen.Uebungssitzung(inhalt, optionen);
          laufendeSitzung = sitzung;
          await sitzung.start();
          return;
        }
      case 'lehrgang':
        // #/lehrgang listet, #/lehrgang/pflegen/2 öffnet ein Kapitel.
        return await lehrgang.zeichnen(
          inhalt, teile[1] || null,
          teile[2] !== undefined ? Number(teile[2]) : null);
      case 'abtippen':
        return await abtippen.zeichnen(inhalt);
      case 'gezielt':
        return await gezielt.zeichnen(inhalt);
      case 'statistik':
        return await statistik.zeichnen(inhalt);
      case 'zuspruch':
        return await zuspruch.zeichnen(inhalt);
      case 'texte':
        // #/texte listet, #/texte/7 öffnet die Werkbank.
        return teile[1]
          ? await texte.zeichnenText(inhalt, Number(teile[1]))
          : await texte.zeichnen(inhalt);
      case 'hilfe':
        return await hilfe.zeichnen(inhalt);
      case 'import':
        return await einlesen.zeichnen(inhalt);
      case 'freigabe':
        // #/freigabe listet die Lektionen, #/freigabe/12 prüft eine.
        return teile[1]
          ? await freigabe.zeichnenLektion(inhalt, teile[1])
          : await freigabe.zeichnen(inhalt);
      case 'wort':
        return await wortschatz.zeichnenEinzeln(inhalt, Number(teile[1]));
      case 'neu':
        return await wortschatz.zeichnenNeu(inhalt);
      case 'einstellungen':
        return await einstellungen.zeichnen(inhalt);
      case 'tastatur':
        // #/tastatur/el zeigt gleich die richtige Belegung; ohne Angabe
        // die der laufenden Sammlung.
        return tastatur.zeichnen(inhalt, teile[1] || await spracheDerSammlung());
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
// Den Namen holen, bevor der erste Titel gesetzt wird — sonst steht
// eine Sekunde lang der Anfangswert aus dem HTML da und springt dann um.
marke.markeLaden().then(() => wegweisen());

// Hilfe über die Tastatur — auf dem Mac der schnellste Weg.
document.addEventListener('keydown', (e) => {
  if (e.metaKey || e.ctrlKey || e.altKey) return;
  if (document.activeElement && ['INPUT', 'TEXTAREA', 'SELECT']
      .includes(document.activeElement.tagName)) return;
  if (e.key === 'l') location.hash = '#/lernen';
  else if (e.key === 'w') location.hash = '#/wortschatz';
  else if (e.key === 'u') location.hash = '#/uebersicht';
});
