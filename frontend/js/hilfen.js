/* Kleine Werkzeuge. Kein Rahmenwerk — ein Vokabeltrainer soll in fünf Jahren
 * noch starten, ohne dass sich ein Paketbaum von 2026 neu auflösen lässt. */

/** Element bauen. h('p', {class:'leise'}, 'Text') */
export function h(tag, eigenschaften = {}, ...kinder) {
  const el = document.createElement(tag);
  for (const [name, wert] of Object.entries(eigenschaften || {})) {
    if (wert === null || wert === undefined || wert === false) continue;
    if (name === 'class') el.className = wert;
    else if (name === 'html') el.innerHTML = wert;
    else if (name === 'text') el.textContent = wert;
    else if (name.startsWith('on') && typeof wert === 'function') {
      el.addEventListener(name.slice(2), wert);
    } else if (name === 'dataset') {
      for (const [k, v] of Object.entries(wert)) el.dataset[k] = v;
    } else if (wert === true) el.setAttribute(name, '');
    else el.setAttribute(name, wert);
  }
  anhaengen(el, kinder);
  return el;
}

function anhaengen(el, kinder) {
  for (const kind of kinder.flat(4)) {
    if (kind === null || kind === undefined || kind === false) continue;
    el.append(kind instanceof Node ? kind : document.createTextNode(String(kind)));
  }
}

/** Hängt Kinder an und verwirft dabei null und undefined.
 *  element.append(null) fügt sonst die Zeichenkette "null" in die Seite ein —
 *  ein Fehler, der sich leicht einschleicht und hässlich aussieht. */
export function anfuegen(el, ...kinder) {
  for (const kind of kinder.flat(4)) {
    if (kind === null || kind === undefined || kind === false) continue;
    el.append(kind instanceof Node ? kind : document.createTextNode(String(kind)));
  }
  return el;
}

export function leeren(el) { while (el.firstChild) el.firstChild.remove(); return el; }

let meldungsUhr = null;
export function meldung(text, dauer = 2600) {
  const kasten = document.getElementById('meldung');
  kasten.textContent = text;
  kasten.hidden = false;
  clearTimeout(meldungsUhr);
  meldungsUhr = setTimeout(() => { kasten.hidden = true; }, dauer);
}

export function zahl(wert, stellen = 1) {
  if (wert === null || wert === undefined) return '–';
  return Number(wert).toLocaleString('de-DE', {
    minimumFractionDigits: stellen, maximumFractionDigits: stellen,
  });
}

export function prozent(anteil) {
  if (anteil === null || anteil === undefined) return '–';
  return Math.round(anteil * 100) + ' %';
}

export function datumText(iso) {
  if (!iso) return '–';
  const d = new Date(iso + (iso.length === 10 ? 'T12:00:00' : ''));
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleDateString('de-DE', { day: 'numeric', month: 'long', year: 'numeric' });
}

/* ------------------------------------------------------------ Vorlesen */

let stimmen = [];
function stimmenLaden() {
  if (!('speechSynthesis' in window)) return;
  stimmen = window.speechSynthesis.getVoices();
}
if ('speechSynthesis' in window) {
  stimmenLaden();
  window.speechSynthesis.addEventListener('voiceschanged', stimmenLaden);
}

/** Gibt es für diese Sprache überhaupt eine Stimme? */
export function stimmeDa(kennung) {
  if (!kennung || !('speechSynthesis' in window)) return false;
  if (!stimmen.length) stimmenLaden();
  const kurz = kennung.split('-')[0];
  return stimmen.some((s) => s.lang && s.lang.toLowerCase().startsWith(kurz));
}

export function sprechen(text, kennung, tempo = 0.9) {
  if (!text || !kennung || !('speechSynthesis' in window)) return false;
  if (!stimmen.length) stimmenLaden();
  const kurz = kennung.split('-')[0].toLowerCase();
  const stimme = stimmen.find((s) => s.lang && s.lang.toLowerCase() === kennung.toLowerCase())
              || stimmen.find((s) => s.lang && s.lang.toLowerCase().startsWith(kurz));
  if (!stimme) return false;
  window.speechSynthesis.cancel();
  const spruch = new SpeechSynthesisUtterance(text);
  spruch.voice = stimme;
  spruch.lang = stimme.lang;
  spruch.rate = tempo;
  window.speechSynthesis.speak(spruch);
  return true;
}

/* -------------------------------------------------------- Textbausteine */

/** Silben abwechselnd hinterlegen — Lesehilfe. */
export function silbenZeigen(silben) {
  return h('span', {}, (silben || []).map((s) => h('span', { class: 'silbe', text: s })));
}

/** Stamm und Endung getrennt zeigen. Der Stamm kommt aus dem Paradigma. */
export function zerlegungZeigen(zerlegung) {
  if (!zerlegung) return null;
  const kasten = h('div', { class: 'zerlegung' });
  const teile = zerlegung.teile || [];
  if (teile.length >= 2) {
    // Bei drei Teilen steht vorn ein eigenes Wörtchen: griechisch »θα«
    // bildet das Futur, gehört aber nicht zum Stamm.
    const hatVorsatz = teile.length === 3;
    if (hatVorsatz) {
      kasten.append(h('span', { class: 'teil vorsatz', text: teile[0],
                                title: 'eigenes Wörtchen' }));
    }
    kasten.append(
      h('span', { class: 'teil stamm', text: teile[hatVorsatz ? 1 : 0],
                  title: 'Stamm' }),
      h('span', { class: 'teil endung', text: teile[hatVorsatz ? 2 : 1],
                  title: 'Endung' }),
      h('span', { class: 'leise',
                  text: hatVorsatz ? 'Wörtchen, Stamm und Endung'
                                   : 'Stamm und Endung' }),
    );
  } else if (zerlegung.silben && zerlegung.silben.length > 1) {
    kasten.append(h('span', { class: 'teil' }, silbenZeigen(zerlegung.silben)),
                  h('span', { class: 'leise', text: 'Silben' }));
  } else {
    return null;
  }
  return kasten;
}

export const ESCAPE = (text) => String(text ?? '');
