/* Kleine Werkzeuge. Kein Rahmenwerk — ein Vokabeltrainer soll in fünf Jahren
 * noch starten, ohne dass sich ein Paketbaum von 2026 neu auflösen lässt. */

/** Element bauen. h('p', {class:'leise'}, 'Text') */
/* Baut ein Element. Es gibt BEWUSST keinen Weg, HTML einzusetzen.
 *
 * Hier stand einmal `html: wert -> el.innerHTML = wert`. Benutzt hat es
 * niemand — aber ein Teil der angezeigten Inhalte kommt von KI-Agenten
 * und aus eingelesenen Dateien, und ein einziges künftiges
 * `h('p', { html: lexem.lemma })` wäre gespeichertes XSS. Eine Tür, die
 * nicht gebraucht wird, baut man zu, statt sie zu bewachen.
 */
export function h(tag, eigenschaften = {}, ...kinder) {
  const el = document.createElement(tag);
  for (const [name, wert] of Object.entries(eigenschaften || {})) {
    if (wert === null || wert === undefined || wert === false) continue;
    if (name === 'class') el.className = wert;
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

/** Dasselbe für SVG. `h` kann es nicht: createElement legt im HTML-Raum
 *  an, und ein <circle> ohne Namensraum wird nie gezeichnet — es steht
 *  dann unsichtbar in der Seite, was beim Suchen eine Stunde kostet.
 *  Stand als lokale Hilfe in der Statistik; jetzt braucht sie auch die
 *  Kopfzeile, und zwei Fassungen desselben Werkzeugs laufen auseinander. */
export function svg(name, attribute = {}, text = null) {
  const e = document.createElementNS('http://www.w3.org/2000/svg', name);
  for (const [k, v] of Object.entries(attribute)) e.setAttribute(k, v);
  if (text !== null) e.textContent = text;
  return e;
}

let meldungsUhr = null;
/* Kurze Rückmeldung am Bildschirmrand.
 *
 * Der zweite Parameter darf eine Dauer in Millisekunden sein ODER das
 * Wort 'fehler'. Letzteres, weil vier Aufrufstellen es ohnehin so
 * geschrieben haben — in der Annahme, dort stünde die Art der Meldung.
 * Daraus wurde `setTimeout(fn, 'fehler')`, also NaN, geklemmt auf 0:
 * der Kasten verschwand im nächsten Tick. Ausgerechnet im Fehlerfall
 * war die Meldung damit unsichtbar.
 *
 * Statt vier Aufrufe zu berichtigen und auf den fünften zu hoffen,
 * versteht die Funktion jetzt beides. Ein Fehler bleibt länger stehen
 * als eine Bestätigung — er will gelesen werden.
 */
/* Hüllt einen Klickbehandler ein, der etwas am Server tut.
 *
 * `onclick: () => tun(async () => { … })`
 *
 * Ein `async`-Behandler, den niemand abwartet, verschluckt jeden
 * Fehler: die Zurückweisung läuft ins Leere, der Knopf sieht aus, als
 * hätte er gewirkt, und die Ansicht steht mit altem Inhalt da. Genau
 * das war an einem guten Dutzend Stellen so — Rechte ändern, Besitz
 * übertragen, Wörter und Formen löschen, Lernziele löschen.
 *
 * Statt jede Stelle einzeln einzupacken gibt es diese eine, damit auch
 * die nächste Stelle sie benutzt.
 */
export async function tun(arbeit, gelungen = null) {
  try {
    const wert = await arbeit();
    if (gelungen) meldung(gelungen);
    return wert;
  } catch (fehler) {
    meldung(fehler?.message || 'Das ging schief.', 'fehler');
    return undefined;
  }
}

export const MELDUNG_KURZ = 2600;
export const MELDUNG_FEHLER = 6000;

export function meldung(text, dauer = MELDUNG_KURZ) {
  const kasten = document.getElementById('meldung');
  kasten.textContent = text;
  kasten.hidden = false;
  kasten.classList.toggle('fehler', dauer === 'fehler');
  const ms = Number.isFinite(Number(dauer)) && Number(dauer) > 0
    ? Number(dauer)
    : (dauer === 'fehler' ? MELDUNG_FEHLER : MELDUNG_KURZ);
  clearTimeout(meldungsUhr);
  meldungsUhr = setTimeout(() => { kasten.hidden = true; }, ms);
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

// Der frühere `ESCAPE` ist ersatzlos weg: er maskierte nichts, sondern
// gab den Text unverändert zurück. In Verbindung mit einer HTML-Senke
// hätte `h('p', { html: ESCAPE(wert) })` sicher ausgesehen und wäre
// eine Lücke gewesen. Beides gibt es nicht mehr.
