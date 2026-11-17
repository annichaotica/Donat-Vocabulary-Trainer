/* Tagesziel und Strähne in der Kopfzeile.
 *
 * Von allem, was zur Gamifikation gehört, ist dies das Billigste mit der
 * größten Wirkung: ein angefangener Ring will geschlossen werden. Die
 * Tagesdosis war längst eingestellt und stand nirgends — man sah erst am
 * Ende der Abfrage, dass man sie erreicht hatte.
 *
 * Darum oben und nicht in der Übersicht: während der Abfrage ist die
 * Übersicht nicht zu sehen, und gerade dann zählt der Ring hoch.
 *
 * ZWEI ZEICHEN, ZWEI BEDEUTUNGEN, und keines sagt zwei Dinge:
 *   der Ring  — wie weit das heutige Pensum aufgegangen ist
 *   die Zahl  — wie viele Tage in Folge es aufgegangen IST
 *
 * Ohne Tagesdosis (»ohne Grenze«) entfällt der Ring. Ein Ziel, das
 * jemand ausdrücklich abgewählt hat, zeichnet man nicht trotzdem hin.
 */

import { api } from './api.js';
import { svg } from './hilfen.js';

const UMFANG = 2 * Math.PI * 10;      // r = 10 im Bild unten

let stand = null;
// Gegen überholte Antworten: wer schnell zwischen Seiten wechselt, löst
// mehrere Abrufe aus, und der langsamere kam früher zuletzt an.
let lauf = 0;


export function letzterStand() { return stand; }


/** Holt den Stand, zeichnet und gibt ihn zurück.
 *
 * Wer die Zahlen BRAUCHT — der Abschluss der Abfrage —, wartet darauf.
 * Die Kopfzeile nicht, dafür gibt es `auffrischen` darunter.
 */
export async function holen(benutzerId) {
  if (!benutzerId) { stand = null; zeichnen(); return null; }
  const meiner = ++lauf;
  const neu = await api.spiel(benutzerId);
  // Eine überholte Antwort wird zurückgegeben, aber nicht gezeichnet:
  // wer sie angefordert hat, bekommt sie; der Ring gehört inzwischen
  // einem anderen Aufruf.
  if (meiner === lauf) { stand = neu; zeichnen(); }
  return neu;
}


/** Dasselbe, aber ohne Warten — die Kopfzeile soll nicht auf einen
 *  Zählvorgang über alle Aufgaben warten. Bis die Antwort da ist,
 *  bleibt der alte Ring stehen. */
export function auffrischen(benutzerId) {
  holen(benutzerId).catch(() => { /* dann bleibt der Ring, wie er war */ });
}


/** Eine Antwort weiter — ohne Rückfrage beim Server.
 *
 * Die Abfrage weiß selbst, dass sie gerade etwas gewertet hat. Ein
 * Abruf je Antwort wäre eine Anfrage für eine Zahl, die man schon hat;
 * bei zwanzig Fragen sind das zwanzig Zählläufe über alle Aufgaben.
 *
 * Die Strähne rührt das nicht an: sie kann sich innerhalb des Tages nur
 * EINMAL ändern, nämlich wenn das Ziel aufgeht. Genau dann wird sie
 * hochgezählt — mehr Fälle gibt es nicht.
 */
export function fortschreiben(erledigt) {
  if (!stand) return;
  const z = stand.tagesziel;
  const vorher = z.geschafft;
  z.erledigt = erledigt;
  if (!vorher && z.erledigt >= z.ziel) {
    z.geschafft = true;
    stand.straehne.laufend += 1;
    stand.straehne.laengste = Math.max(stand.straehne.laengste,
                                       stand.straehne.laufend);
    stand.straehne.heute_geschafft = true;
  }
  zeichnen();
}


export function zeichnen() {
  const knopf = document.getElementById('kopf-spiel');
  if (!knopf) return;
  while (knopf.firstChild) knopf.firstChild.remove();
  if (!stand) { knopf.hidden = true; return; }

  const z = stand.tagesziel;
  const f = stand.straehne;
  const mitRing = Boolean(z.dosis);
  // Ohne Ring und ohne Strähne gibt es nichts zu zeigen — dann soll da
  // auch kein leerer Knopf stehen, der sich anfassen lässt.
  if (!mitRing && !f.laufend) { knopf.hidden = true; return; }
  knopf.hidden = false;

  if (mitRing) knopf.append(ring(z));
  if (f.laufend) {
    knopf.append(flamme(), Object.assign(document.createElement('span'),
      { className: 'kopf-spiel-zahl', textContent: String(f.laufend) }));
  }
  knopf.classList.toggle('ist-geschafft', Boolean(z.geschafft));
  knopf.title = beschriftung(z, f);
  knopf.setAttribute('aria-label', knopf.title);
}


function ring(z) {
  const anteil = z.ziel ? Math.min(1, z.erledigt / z.ziel) : 0;
  const bild = svg('svg', { viewBox: '0 0 26 26', class: 'kopf-ring',
                            'aria-hidden': 'true', focusable: 'false' });
  bild.append(svg('circle', {
    cx: 13, cy: 13, r: 10, fill: 'none', 'stroke-width': 3,
    stroke: 'currentColor', opacity: 0.2,
  }));
  if (z.geschafft) {
    // Geschafft ist voll, auch wenn die Dosis gar nicht nötig war, weil
    // nichts mehr fällig stand. Ein Ring, der bei drei von zwanzig
    // stehenbleibt, obwohl der Tag erledigt ist, sieht nach Rückstand
    // aus — und das ist das Gegenteil der Wahrheit.
    bild.append(svg('circle', {
      cx: 13, cy: 13, r: 10, fill: 'none', 'stroke-width': 3,
      stroke: 'currentColor', class: 'kopf-ring-voll',
    }));
    bild.append(svg('path', {
      d: 'M8.5 13.4l3 3 6-6.4', fill: 'none', stroke: 'currentColor',
      'stroke-width': 2.4, 'stroke-linecap': 'round',
      'stroke-linejoin': 'round', class: 'kopf-ring-haken',
    }));
  } else {
    bild.append(svg('circle', {
      cx: 13, cy: 13, r: 10, fill: 'none', 'stroke-width': 3,
      stroke: 'currentColor', 'stroke-linecap': 'round',
      'stroke-dasharray': `${(anteil * UMFANG).toFixed(2)} ${UMFANG.toFixed(2)}`,
      transform: 'rotate(-90 13 13)', class: 'kopf-ring-bogen',
    }));
  }
  return bild;
}


function flamme() {
  const bild = svg('svg', { viewBox: '0 0 24 24', class: 'kopf-flamme',
                            'aria-hidden': 'true', focusable: 'false' });
  // EIN gefüllter Umriss, keine Strichzeichnung und kein zweites Teil.
  // Bei 1,2 rem ist für beides kein Platz: die erste Fassung war
  // gestrichelt und sah aus wie ein Ausrufezeichen, die zweite hatte
  // ein helles Herz und sah aus wie ein Bäumchen. Eine Silhouette, die
  // man auf den ersten Blick erkennt, ist hier mehr wert als eine
  // Zeichnung, die aus der Nähe hübscher wäre.
  bild.append(svg('path', {
    d: 'M12 22.5c-3.8 0-6.8-2.9-6.8-6.6 0-2.5 1.2-4.5 2.6-6.1C9.3 8.1 10.8 6.3'
     + ' 11.1 2.7c0-.4.5-.6.8-.3 1.7 1.2 5.1 4.2 5.1 7.9 0 .7-.1 1.4-.3 2'
     + ' .6-.4 1.1-1.1 1.3-2.1.1-.4.6-.5.9-.2 1.2 1.3 1.9 3.3 1.9 5.9 0'
     + ' 3.7-3 6.6-6.8 6.6z',
    fill: 'currentColor', stroke: 'none',
  }));
  return bild;
}


/** Was im Hinweis steht. Hier stehen die GENAUEN Zahlen — der Ring
 *  zeigt nur die Richtung, und wer es wissen will, soll nicht rechnen. */
function beschriftung(z, f) {
  const teile = [];
  if (z.dosis) {
    if (z.nichts_mehr_faellig) {
      teile.push(`Tagesziel erreicht — es war nichts mehr fällig `
               + `(${z.erledigt} von ${z.ziel}).`);
    } else if (z.geschafft) {
      teile.push(`Tagesziel geschafft: ${z.erledigt} von ${z.ziel} Fragen.`);
    } else {
      teile.push(`${z.erledigt} von ${z.ziel} Fragen heute — noch `
               + `${z.ziel - z.erledigt}.`);
    }
  }
  if (f.laufend) {
    teile.push(`Strähne: ${f.laufend} ${f.laufend === 1 ? 'Tag' : 'Tage'} in Folge`
             + (f.laengste > f.laufend ? ` (am längsten: ${f.laengste}).`
                                       : '.'));
  }
  const joker = f.joker_benutzt?.length || 0;
  if (joker) {
    // Die überbrückten Tage werden GENANNT. Eine Strähne, die
    // stillschweigend über Fehltage hinwegzählt, behauptet etwas, das
    // nicht stimmt — und das merkt man genau dann, wenn man sich darauf
    // etwas einbildet.
    teile.push(joker === 1
      ? 'Ein Fehltag ist dabei überbrückt — zwei im Monat trägt die Strähne mit.'
      : `${joker} Fehltage sind dabei überbrückt — mehr trägt die Strähne nicht.`);
  }
  teile.push('Zum Lernen.');
  return teile.join(' ');
}
