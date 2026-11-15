/* Der eigene Lernfortschritt.
 *
 * »Und eine Statistik zu meinem Lernfortschritt, das braucht es
 * natürlich auch.«
 *
 * Die Diagramme sind von Hand gezeichnetes SVG, keine Bibliothek. Das
 * Frontend hat bewusst keinen Bauschritt, und eine Diagrammbibliothek
 * wäre das größte Paket im ganzen Werkzeug — für vier Balkenbilder.
 *
 * Zugeschnitten auf WENIG Daten: beim Bauen standen 101 Antworten an
 * zwei Tagen im Protokoll. Jede Kachel muss damit etwas sagen und darf
 * nicht erst nach einem halben Jahr aufwachen. Was ohne Daten nichts
 * aussagt, wird nicht als leeres Gerüst gezeigt, sondern durch einen
 * Satz ersetzt, der sagt, was fehlt.
 */

import { api } from './api.js';
import { h, leeren, anfuegen } from './hilfen.js';
import { zustand, merken } from './zustand.js';

const FARBE = {
  richtig: 'var(--richtig)',
  fast: 'var(--fast)',
  falsch: 'var(--falsch)',
  neu: 'var(--akzent)',
  lernen: 'var(--fast)',
  reif: 'var(--richtig)',
  verlernt: 'var(--falsch)',
};

const TYPNAME = {
  bedeutung_fremd_deutsch: 'Bedeutung erkennen',
  bedeutung_deutsch_fremd: 'Wort bilden',
  form_bilden: 'Form bilden',
  form_bestimmen: 'Form bestimmen',
  formenreihe: 'Ganze Reihe',
  stammformen: 'Stammformen',
  klasse: 'Klasse bestimmen',
  genus: 'Artikel',
};


export async function zeichnen(behaelter) {
  const el = leeren(behaelter);
  el.append(h('h1', { text: 'Dein Fortschritt' }));

  let d;
  let sammlungen = [];
  try {
    [d, sammlungen] = await Promise.all([
      api.statistik(zustand.benutzerId, zustand.statistikSammlung || null),
      api.sammlungen(zustand.benutzerId).catch(() => []),
    ]);
  } catch (fehler) {
    el.append(h('p', { class: 'leise', text: fehler.message }));
    return;
  }

  anfuegen(el, teilAuswahl(behaelter, sammlungen));

  if (!d.gesamt.antworten) {
    el.append(h('div', { class: 'karte' },
      h('p', { text: 'Noch keine Antwort in den letzten '
                   + `${d.gesamt.tage_betrachtet} Tagen. Sobald du lernst, `
                   + 'steht hier, wie es läuft.' })));
    anfuegen(el, teilWortschatz(d));
    return;
  }

  anfuegen(el, teilZahlen(d), teilTaetigkeit(d), teilVorschau(d),
           teilWortschatz(d), teilTempo(d));
}


function teilAuswahl(behaelter, sammlungen) {
  if (!sammlungen.length) return null;
  const wahl = h('select', {},
    h('option', { value: '', text: 'Alle Sammlungen, die du lernst' }),
    sammlungen.filter((s) => s.lerne_ich)
      .map((s) => h('option', { value: String(s.id), text: s.name })));
  wahl.value = zustand.statistikSammlung ? String(zustand.statistikSammlung) : '';
  wahl.addEventListener('change', () => {
    merken({ statistikSammlung: wahl.value ? Number(wahl.value) : null });
    zeichnen(behaelter);
  });
  return h('p', {}, wahl);
}


/** Die vier Zahlen, die man ohne Diagramm versteht. */
function teilZahlen(d) {
  const g = d.gesamt;
  return h('div', { class: 'karte' },
    h('div', { class: 'zahlen' },
      zahl(g.antworten, `Antworten in ${g.tage_betrachtet} Tagen`),
      zahl(g.quote === null ? '—' : `${g.quote} %`, 'auf Anhieb richtig'),
      zahl(g.aktive_tage, 'Tage gelernt'),
      zahl(g.straehne, g.straehne === 1 ? 'Tag am Stück' : 'Tage am Stück')),
    g.fast
      ? h('p', { class: 'leise', style: 'margin:.6rem 0 0',
                 text: `Dazu ${g.fast}× »fast« — ein Zeichen daneben, beim `
                     + 'zweiten Versuch richtig. Das zählt nicht als Fehler.' })
      : null);
}

function zahl(wert, beschriftung) {
  return h('div', { class: 'zahl' },
    h('b', { text: String(wert) }), h('span', { text: beschriftung }));
}


/** Antworten je Tag, gestapelt nach Urteil. */
function teilTaetigkeit(d) {
  const tage = d.taetigkeit;
  const hoechst = Math.max(...tage.map((t) => t.gesamt), 1);
  const breite = 100 / tage.length;

  const balken = tage.map((t, i) => {
    const x = i * breite;
    let unten = 0;
    const stuecke = ['richtig', 'fast', 'falsch'].map((art) => {
      if (!t[art]) return null;
      const hoch = (t[art] / hoechst) * 100;
      const y = 100 - unten - hoch;
      unten += hoch;
      return svg('rect', { x: x + breite * 0.15, y,
                           width: breite * 0.7, height: hoch,
                           fill: FARBE[art] });
    }).filter(Boolean);
    // Auch leere Tage bekommen eine Fläche — sonst gäbe es nichts,
    // worauf der Hinweistext hängen könnte.
    const feld = svg('rect', { x, y: 0, width: breite, height: 100,
                               fill: 'transparent' });
    feld.append(svg('title', {}, `${t.tag}: ${t.gesamt} Antworten`));
    return [...stuecke, feld];
  }).flat();

  return h('div', { class: 'karte' },
    h('h2', { style: 'margin-top:0', text: 'Was du getan hast' }),
    h('p', { class: 'leise', style: 'margin:0 0 .6rem',
             text: `Antworten je Tag, letzte ${tage.length} Tage. `
                 + 'Grün richtig, gelb fast, rot daneben.' }),
    diagramm(balken),
    h('div', { class: 'diagramm-achse' },
      h('span', { text: tage[0].tag.slice(5) }),
      h('span', { text: 'heute' })));
}


/** Was in den nächsten Wochen fällig wird. */
function teilVorschau(d) {
  const reihe = d.vorschau;
  const hoechst = Math.max(...reihe.map((v) => v.n), 1);
  const breite = 100 / reihe.length;
  const summe = reihe.reduce((a, v) => a + v.n, 0);

  if (!summe) {
    return h('div', { class: 'karte' },
      h('h2', { style: 'margin-top:0', text: 'Was auf dich zukommt' }),
      h('p', { class: 'leise',
               text: 'Noch nichts terminiert — Termine entstehen, sobald du '
                   + 'ein Wort zum ersten Mal beantwortet hast.' }));
  }

  const balken = reihe.map((v, i) => {
    if (!v.n) return null;
    const hoch = (v.n / hoechst) * 100;
    const r = svg('rect', { x: i * breite + breite * 0.15, y: 100 - hoch,
                            width: breite * 0.7, height: hoch,
                            // Überfälliges ist Rückstand, nicht Zukunft.
                            fill: i === 0 ? 'var(--falsch)' : 'var(--akzent)' });
    r.append(svg('title', {}, `${v.beschriftung}: ${v.n}`));
    return r;
  }).filter(Boolean);

  return h('div', { class: 'karte' },
    h('h2', { style: 'margin-top:0', text: 'Was auf dich zukommt' }),
    h('p', { class: 'leise', style: 'margin:0 0 .6rem',
             text: 'Wann die Wörter wieder dran sind. Der rote Balken ganz '
                 + 'links ist überfällig — der kommt heute mit.' }),
    diagramm(balken),
    h('div', { class: 'diagramm-achse' },
      h('span', { text: 'überfällig · heute' }),
      h('span', { text: `in ${reihe.length - 2} Tagen` })));
}


/** Wo der Bestand steht.
 *
 * Das Band zeigt nur das ANGEFANGENE. Mit dem Vorrat zusammen wäre es
 * sinnlos: im echten Bestand stehen 10753 »noch nie dran« gegen 61
 * angefangene, und das Band war einfarbig. Gerade am Anfang ist aber
 * die kleine Zahl die interessante — sie ist der Fortschritt. Der
 * Vorrat steht als Satz daneben, wo er hingehört: als Zusammenhang,
 * nicht als Balken, der alles andere plattdrückt.
 */
function teilWortschatz(d) {
  const w = d.wortschatz;
  const angefangen = ['reif', 'lernen', 'verlernt'];
  const namen = { reif: 'sitzt', lernen: 'am Lernen', verlernt: 'verlernt' };
  const summe = angefangen.reduce((a, k) => a + (w[k] || 0), 0);
  const vorrat = w.neu || 0;

  if (!summe) {
    return h('div', { class: 'karte' },
      h('h2', { style: 'margin-top:0', text: 'Wo dein Wortschatz steht' }),
      h('p', { text: vorrat
        ? `${vorrat} Aufgaben warten, angefangen ist noch keine. Sobald du `
          + 'die ersten beantwortet hast, steht hier, wie sie sich verteilen.'
        : 'Noch nichts im Wortschatz.' }));
  }

  const band = h('div', { class: 'band' });
  for (const k of angefangen) {
    if (!w[k]) continue;
    band.append(h('i', {
      style: `width:${(w[k] / summe) * 100}%;background:${FARBE[k]}`,
      title: `${namen[k]}: ${w[k]}`,
    }));
  }

  return h('div', { class: 'karte' },
    h('h2', { style: 'margin-top:0', text: 'Wo dein Wortschatz steht' }),
    h('p', { class: 'leise', style: 'margin:0 0 .5rem',
             text: `${summe} Aufgaben hast du angefangen:` }),
    band,
    h('div', { class: 'bandlegende' },
      ...angefangen.filter((k) => w[k]).map((k) => h('span', {},
        h('i', { style: `background:${FARBE[k]}` }),
        `${namen[k]} ${w[k]}`))),
    h('p', { class: 'leise', style: 'margin:.6rem 0 0',
             text: vorrat
               ? `Dazu ${vorrat} Aufgaben, die noch nie dran waren — das ist `
                 + 'dein Vorrat, keine offene Rechnung. Gezählt in Aufgaben, '
                 + 'nicht in Wörtern: ein Verb bringt viele mit.'
               : 'Gezählt in Aufgaben, nicht in Wörtern — ein Verb bringt '
                 + 'viele mit.' }));
}


/** Wie lange bis zur Antwort, je Aufgabenart. */
function teilTempo(d) {
  if (!d.tempo.length) return null;
  const hoechst = Math.max(...d.tempo.map((t) => t.median_ms));
  const zeilen = d.tempo.map((t) => h('div', { class: 'tempozeile' },
    h('span', { text: TYPNAME[t.typ] || t.typ }),
    h('div', { class: 'tempobalken' },
      h('i', { style: `width:${(t.median_ms / hoechst) * 100}%` })),
    h('span', { class: 'leise',
                text: `${(t.median_ms / 1000).toFixed(1).replace('.', ',')} s`
                    + ` · ${t.anzahl}×` })));

  return h('div', { class: 'karte' },
    h('h2', { style: 'margin-top:0', text: 'Wie schnell du antwortest' }),
    h('p', { class: 'leise', style: 'margin:0 0 .6rem',
             text: 'Zeit bis zum ersten Tastendruck, Mittelwert der Mitte. '
                 + 'Nicht die Gesamtzeit — die misst vor allem, wie schnell '
                 + 'du tippst.' }),
    ...zeilen);
}


// ------------------------------------------------------------------ SVG

function svg(name, attribute = {}, text = null) {
  const e = document.createElementNS('http://www.w3.org/2000/svg', name);
  for (const [k, v] of Object.entries(attribute)) e.setAttribute(k, v);
  if (text !== null) e.textContent = text;
  return e;
}

/** Der Rahmen. `preserveAspectRatio=none` streckt die Balken auf die
 *  volle Breite — bei einem Balkenbild ist das richtig, die Form der
 *  einzelnen Säule sagt ja nichts aus. */
function diagramm(kinder) {
  const bild = svg('svg', {
    viewBox: '0 0 100 100', preserveAspectRatio: 'none',
    class: 'diagramm', role: 'img',
  });
  for (const k of kinder) bild.append(k);
  return bild;
}
