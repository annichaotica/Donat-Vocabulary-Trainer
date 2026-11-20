/* Gezieltes Lernen — Wort für Wort entscheiden, ob es abgefragt wird.
 *
 * »Wir brauchen einen Modus für gezieltes Lernen, dort soll Wort für
 * Wort auswählbar sein, was abgefragt wird.«
 *
 * Der Anlass: »meine Tochter, die genau die Vokabeln lernen muss,
 * die sie mir als Liste gegeben hat«. Eine Sammlung wächst mit der
 * Zeit; die Liste für die nächste Arbeit ist ein Ausschnitt daraus.
 * Ohne diese Ansicht bliebe nur, den Rest zu löschen oder eine zweite
 * Sammlung anzulegen — beides wirft weg, was schon gelernt ist.
 *
 * WARUM EINE EIGENE ANSICHT und nicht ein Schalter im Wortschatz:
 * dort sucht man EIN Wort. Hier bestimmt man eine Auswahl, und zwar
 * aus vielen. Das braucht Filter und die Möglichkeit, dreißig auf
 * einmal umzuschalten — ohne dreißig Klicks, denn das war schon
 * zweimal die Beschwerde.
 *
 * NICHT DIE GANZE SEITE. Das Kästchen zum Auswählen erneuerte von
 * jeher nur den Stapelkasten — »beim Durchhaken von fünfzig Wörtern
 * darf die Seite nicht unter den Fingern wegspringen«. Der ja/nein-
 * Schalter in derselben Zeile tat das Gegenteil: er rief `zeichnen`,
 * und das holte bis zu 200 Zeilen neu. Bei 1927 griechischen Wörtern
 * sprang die Seite bei jedem Umschalten nach oben.
 *
 * Jetzt kommt die geänderte Zeile vom Server zurück und wird an Ort
 * und Stelle ausgetauscht. Neu gezeichnet wird nur noch, wenn die
 * Zeile hier gar nicht mehr hingehört — unter »Nur ausgeschaltete«
 * verschwindet ein wieder eingeschaltetes Wort ja aus der Liste.
 *
 * STILLGELEGT IST NICHT GELÖSCHT. Die Aufgaben werden abgeschaltet,
 * der Lernstand bleibt stehen. Wer ein Wort später wieder dazunimmt,
 * fängt nicht von vorn an — dieselbe Zusage wie bei einer abgewählten
 * Zeitform.
 */

import { api } from './api.js';
import { h, leeren, anfuegen, meldung, tun } from './hilfen.js';
import { zustand } from './zustand.js';

let filter = { lektion_nr: null, wortart: '', nur_aus: false, suche: '' };
let ausgewaehlt = new Set();


export async function zeichnen(behaelter) {
  const el = leeren(behaelter);
  el.append(h('h1', { text: 'Gezielt lernen' }));

  if (!zustand.sammlungId) {
    el.append(h('p', { class: 'leise',
      text: 'Erst eine Sammlung wählen — oben in der Kopfzeile.' }));
    return;
  }

  let d;
  try {
    d = await api.abfrageUebersicht(zustand.sammlungId, filter);
  } catch (fehler) {
    el.append(h('p', { class: 'leise', text: fehler.message }));
    return;
  }

  el.append(h('p', { class: 'leise',
    text: 'Wörter, die hier ausgeschaltet sind, bleiben im Wortschatz und '
        + 'decken deine Lesetexte weiter ab — sie werden nur nicht mehr '
        + 'abgefragt. Der Lernstand bleibt dabei erhalten, falls du es dir '
        + 'anders überlegst.' }));

  el.append(teilFilter(behaelter, d));
  if (ausgewaehlt.size) el.append(teilStapel(behaelter, d));
  el.append(teilListe(behaelter, d));
}


function teilFilter(behaelter, d) {
  const neuZeichnen = () => { ausgewaehlt.clear(); zeichnen(behaelter); };

  const suche = h('input', { type: 'search', placeholder: 'Wort suchen',
                             value: filter.suche });
  let warten = null;
  suche.addEventListener('input', () => {
    clearTimeout(warten);
    warten = setTimeout(() => { filter.suche = suche.value.trim();
                                neuZeichnen(); }, 350);
  });

  const lektionen = [...new Set(d.woerter.map((w) => w.lektion_nr)
                                 .filter((n) => n !== null))].sort((a, b) => a - b);
  const lektion = h('select', {},
    h('option', { value: '', text: 'alle Lektionen' }),
    lektionen.map((n) => h('option', { value: String(n), text: `Lektion ${n}` })));
  lektion.value = filter.lektion_nr === null ? '' : String(filter.lektion_nr);
  lektion.addEventListener('change', () => {
    filter.lektion_nr = lektion.value ? Number(lektion.value) : null;
    neuZeichnen();
  });

  const wortarten = [...new Set(d.woerter.map((w) => w.wortart))].sort();
  const wortart = h('select', {},
    h('option', { value: '', text: 'alle Wortarten' }),
    wortarten.map((a) => h('option', { value: a, text: a })));
  wortart.value = filter.wortart;
  wortart.addEventListener('change', () => {
    filter.wortart = wortart.value; neuZeichnen();
  });

  const nurAus = h('button', {
    class: (filter.nur_aus ? 'aktiv' : 'schlicht') + ' gezielt-nuraus',
    onclick: () => { filter.nur_aus = !filter.nur_aus; neuZeichnen(); },
  }, `Nur ausgeschaltete (${d.stillgelegt})`);

  return h('div', { class: 'karte' },
    h('div', { class: 'gezielt-filter' }, suche, lektion, wortart, nurAus),
    h('p', { class: 'leise gezielt-zaehler', style: 'margin:.6rem 0 0',
             text: zaehlertext(d) }));
}


function zaehlertext(d) {
  return `${d.gesamt} Wörter in dieser Sammlung, davon `
       + `${d.stillgelegt} ausgeschaltet.`;
}


/** Die beiden Stellen, an denen »davon ausgeschaltet« steht.
 *
 * Sie standen bisher nur in `zeichnen` richtig, weil danach ohnehin
 * alles neu entstand. Wer eine Zeile austauscht, muss sie selbst
 * nachführen — sonst zeigt der Zähler den Stand von vorhin, und das
 * ist schlimmer als gar keiner. */
function zaehlerErneuern(behaelter, d, stillgelegt) {
  if (stillgelegt === null || stillgelegt === undefined) return;
  d.stillgelegt = stillgelegt;
  const text = behaelter.querySelector('.gezielt-zaehler');
  if (text) text.textContent = zaehlertext(d);
  const knopf = behaelter.querySelector('.gezielt-nuraus');
  if (knopf) knopf.textContent = `Nur ausgeschaltete (${d.stillgelegt})`;
}


/** Die geänderten Zeilen an Ort und Stelle austauschen.
 *
 * Gibt `false` zurück, wenn das nicht geht — dann hilft nur der
 * Neuaufbau. Das ist der Fall unter »Nur ausgeschaltete«: ein wieder
 * eingeschaltetes Wort gehört dort nicht mehr hin, und eine Zeile
 * stehen zu lassen, die der Filter ausschließt, wäre gelogen.
 */
function zeilenErneuern(behaelter, d, woerter) {
  if (filter.nur_aus) return false;
  for (const w of woerter) {
    const stelle = d.woerter.findIndex((x) => x.lexem_id === w.lexem_id);
    if (stelle < 0) return false;
    d.woerter[stelle] = w;
    const alt = behaelter.querySelector(
      `.gezielt-zeile[data-lexem="${w.lexem_id}"]`);
    if (!alt) return false;
    alt.replaceWith(zeileBauen(behaelter, d, w));
  }
  return true;
}


/** Was mit der Auswahl geschehen soll.
 *
 * Erscheint erst, wenn etwas ausgewählt ist — ein Kasten, der
 * meistens leer dasteht, erzieht dazu, ihn zu übersehen.
 */
function teilStapel(behaelter, d) {
  const setzen = (wert) => tun(async () => {
    const ids = [...ausgewaehlt];
    const r = await api.abfrageSetzen(ids, wert);
    meldung(`${ids.length} ${ids.length === 1 ? 'Wort' : 'Wörter'} `
          + (wert === false || wert === 'nachschlagen'
             ? 'ausgeschaltet.' : 'wieder dabei.'));
    ausgewaehlt.clear();
    zaehlerErneuern(behaelter, d, r.stillgelegt);
    if (zeilenErneuern(behaelter, d, r.woerter)) {
      haekchenGleichziehen(behaelter);
      stapelErneuern(behaelter, d);
    } else {
      zeichnen(behaelter);
    }
  });

  const vorlagen = Object.entries(d.vorlagen)
    .filter(([, v]) => v.an === false)
    .map(([name]) => name);

  return h('div', { class: 'karte gezielt-stapel' },
    h('b', { text: `${ausgewaehlt.size} ausgewählt` }),
    h('div', { class: 'frage-werkzeuge' },
      ...vorlagen.map((name) => h('button', {
        class: 'schlicht gefahr', onclick: () => setzen(name),
      }, `Ausschalten (${name})`)),
      h('button', { class: 'wichtig', onclick: () => setzen(true) },
        'Wieder abfragen'),
      h('button', { class: 'schlicht',
                    onclick: () => {
                      ausgewaehlt.clear();
                      haekchenGleichziehen(behaelter);
                      stapelErneuern(behaelter, d);
                    } },
        'Auswahl aufheben')));
}


function teilListe(behaelter, d) {
  if (!d.woerter.length) {
    return h('p', { class: 'leise', text: 'Keine Wörter mit diesen Filtern.' });
  }

  const alleHier = d.woerter.map((w) => w.lexem_id);
  // Ein Kästchen und kein Knopf: es steht in derselben Spalte wie die
  // Kästchen darunter und meint dasselbe. »Alle« als Wort passte dort
  // nicht hinein und klebte an der Überschrift daneben.
  const alleKasten = h('input', { type: 'checkbox', title: 'alle auswählen' });
  alleKasten.checked = alleHier.length > 0
    && alleHier.every((i) => ausgewaehlt.has(i));
  alleKasten.addEventListener('change', () => {
    alleHier.forEach((i) => (alleKasten.checked ? ausgewaehlt.add(i)
                                                : ausgewaehlt.delete(i)));
    // Auch hier kein Neuaufbau: es ändert sich nichts an den Zeilen
    // außer ihrem Häkchen, und das lässt sich setzen.
    haekchenGleichziehen(behaelter);
    stapelErneuern(behaelter, d);
  });
  const kopf = h('div', { class: 'gezielt-zeile gezielt-kopf' },
    h('label', { class: 'hakenfeld', title: 'alle auswählen' }, alleKasten),
    h('span', { class: 'leise',
                text: `Wort (${d.woerter.length} angezeigt)` }),
    h('span', { class: 'leise', text: 'Aufgaben' }),
    h('span', { class: 'leise', text: 'wird abgefragt' }));

  const liste = h('div', { class: 'gezielt-liste' }, kopf);
  for (const w of d.woerter) liste.append(zeileBauen(behaelter, d, w));
  return liste;
}


/** EINE Zeile. Eigene Funktion, weil sie jetzt auch einzeln entsteht —
 *  nach dem Umschalten wird genau sie ausgetauscht. */
function zeileBauen(behaelter, d, w) {
  const kasten = h('input', { type: 'checkbox' });
  kasten.checked = ausgewaehlt.has(w.lexem_id);
  kasten.addEventListener('change', () => {
    if (kasten.checked) ausgewaehlt.add(w.lexem_id);
    else ausgewaehlt.delete(w.lexem_id);
    stapelErneuern(behaelter, d);
  });

  const schalter = h('button', {
    class: w.an ? 'aktiv' : 'schlicht gefahr',
    onclick: () => tun(async () => {
      const r = await api.abfrageSetzen([w.lexem_id], !w.an);
      zaehlerErneuern(behaelter, d, r.stillgelegt);
      // Der Rückweg ist kein Notnagel: unter »Nur ausgeschaltete«
      // gehört ein wieder eingeschaltetes Wort nicht mehr in die
      // Liste, und dann ist der Neuaufbau das Richtige.
      if (!zeilenErneuern(behaelter, d, r.woerter)) zeichnen(behaelter);
    }),
  }, w.an ? 'ja' : 'nein');

  return h('div', { class: 'gezielt-zeile' + (w.an ? '' : ' ist-aus'),
                    dataset: { lexem: String(w.lexem_id) } },
    h('label', { class: 'hakenfeld', title: 'auswählen' }, kasten),
    h('span', {},
      h('b', { lang: d.sprache, text: w.lemma }),
      w.bedeutung
        ? h('span', { class: 'leise', text: ` · ${w.bedeutung}` }) : null,
      w.vorlage
        ? h('span', { class: 'marke', text: w.vorlage }) : null),
    h('span', { class: 'leise', text: String(w.aufgaben) }),
    schalter);
}


/** Die Häkchen an das anpassen, was ausgewählt IST.
 *
 * Drei Stellen bewegen die Auswahl, ohne dass sich an den Zeilen sonst
 * etwas ändert: »alle auswählen«, »Auswahl aufheben« und der Stapel,
 * der nach getaner Arbeit leert. Keine davon braucht einen Neuaufbau —
 * aber alle drei müssen das Kästchen oben mitnehmen, sonst steht dort
 * ein Haken für eine Auswahl, die es nicht mehr gibt.
 */
function haekchenGleichziehen(behaelter) {
  for (const zeile of behaelter.querySelectorAll('.gezielt-zeile[data-lexem]')) {
    const k = zeile.querySelector('input[type=checkbox]');
    if (k) k.checked = ausgewaehlt.has(Number(zeile.dataset.lexem));
  }
  const kopf = behaelter.querySelector('.gezielt-kopf input[type=checkbox]');
  if (kopf) {
    const zeilen = [...behaelter.querySelectorAll('.gezielt-zeile[data-lexem]')];
    kopf.checked = zeilen.length > 0
      && zeilen.every((z) => ausgewaehlt.has(Number(z.dataset.lexem)));
  }
}


/** Nur den Stapelkasten erneuern, nicht die ganze Liste: beim
 *  Durchhaken von fünfzig Wörtern darf die Seite nicht unter den
 *  Fingern wegspringen. */
function stapelErneuern(behaelter, d) {
  const alt = behaelter.querySelector('.gezielt-stapel');
  if (alt) alt.remove();
  if (ausgewaehlt.size) {
    behaelter.querySelector('.gezielt-liste')
      .insertAdjacentElement('beforebegin', teilStapel(behaelter, d));
  }
}
