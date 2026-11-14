/* Freigabe: ganze Lektionen ansehen und bestätigen.
 *
 * Wenn ein Agent sechzehnhundert Wörter mit vollständigen Paradigmen
 * einträgt, entstehen mehrere tausend Formen — und ungeprüft wird nichts
 * abgefragt. Jede einzeln zu bestätigen ist nicht machbar.
 *
 * Darum hier das Paradigma als Tabelle, Zelle für Zelle nach den
 * Formgruppen der Sprache: eine leere oder doppelt besetzte Zelle sieht man
 * so auf einen Blick. Eine Liste in Eingabereihenfolge ließe sich nicht
 * prüfen.
 *
 * Abgewählt wird einzeln, freigegeben im Stapel. Die Reihenfolge ist
 * Absicht: es ist leichter, zwei Fehler abzuhaken, als dreißig richtige
 * Formen anzuklicken. */

import { api } from './api.js';
import { h, leeren, meldung } from './hilfen.js';
import { zustand, merken } from './zustand.js';

async function sammlungSichern() {
  if (zustand.sammlungId) return zustand.sammlungId;
  const alle = await api.sammlungen(zustand.benutzerId);
  if (!alle.length) return null;
  merken({ sammlungId: alle[0].id });
  return alle[0].id;
}

function ohneSammlung(el) {
  el.append(h('div', { class: 'leer' },
    h('p', { text: 'Noch keine Sammlung vorhanden.' }),
    h('button', {
      class: 'wichtig', onclick: () => { location.hash = '#/uebersicht'; },
    }, 'Zur Übersicht')));
}

/* ------------------------------------------------ Welche Lektionen? */

export async function zeichnen(behaelter) {
  const sammlungId = await sammlungSichern();
  const el = leeren(behaelter);
  if (!sammlungId) return ohneSammlung(el);

  el.append(h('h1', { text: 'Freigabe' }));
  const uebersicht = await api.freigabeLektionen(sammlungId);
  if (!uebersicht.offen_gesamt) {
    el.append(h('div', { class: 'leer' },
      h('p', { text: 'Alles freigegeben — es wartet nichts.' }),
      h('p', { class: 'leise', text: 'Hier erscheinen Formen, die über die '
        + 'Schnittstelle oder beim Import eingetragen wurden. Bis zur '
        + 'Freigabe werden sie nicht abgefragt.' })));
    return;
  }

  el.append(h('p', { class: 'leise', text:
    `${uebersicht.offen_gesamt} Formen warten auf Freigabe. Bis dahin `
    + 'werden sie nicht abgefragt.' }));

  const liste = h('div', { class: 'liste' });
  for (const k of uebersicht.lektionen) {
    // Lektionen, die beim Import entstanden sind, heißen schon "Lektion 5".
    // "Lektion 5 — Lektion 5" zu schreiben wäre albern.
    const nummer = k.nr !== null && k.nr !== undefined ? `Lektion ${k.nr}` : null;
    const name = nummer
      ? (k.name && k.name !== nummer ? `${nummer} — ${k.name}` : nummer)
      : 'Ohne Lektion';
    liste.append(h('button', {
      class: 'eintrag',
      onclick: () => { location.hash = `#/freigabe/${k.nr ?? 'ohne'}`; },
    },
      h('span', { class: 'lemma', text: name }),
      h('span', { class: 'bedeutung', text: `${k.woerter} Wörter` }),
      h('span', { class: 'marke warnung', text: `${k.offen} offen` })));
  }
  el.append(liste);
}

/* ------------------------------------------------------ Prüfansicht */

const JE_SEITE = 25;

export async function zeichnenLektion(behaelter, lektion) {
  const sammlungId = await sammlungSichern();
  const el = leeren(behaelter);
  if (!sammlungId) return ohneSammlung(el);

  const nr = lektion === 'ohne' ? null : Number(lektion);
  /** Einzeln abgewählte Formen. Alles andere gilt als in Ordnung. */
  const abgewaehlt = new Set();

  const titel = h('h1', { text: nr === null ? 'Ohne Lektion' : `Lektion ${nr}` });
  const stand = h('p', { class: 'leise' });
  const liste = h('div', {
    class: 'freigabe-liste',
    style: 'display:flex;flex-direction:column;gap:1rem',
  });
  const fussleiste = h('div', { class: 'freigabe-leiste' });
  el.append(titel, stand, liste, fussleiste);

  let ab = 0;
  let offenGesamt = 0;
  let woerterGesamt = 0;

  const standSetzen = () => {
    const abgezogen = abgewaehlt.size;
    stand.textContent = `${woerterGesamt} Wörter, ${offenGesamt} Formen offen`
      + (abgezogen ? ` — ${abgezogen} abgewählt` : '');
  };

  const nachladen = async (anfuegen = false) => {
    const daten = await api.freigabe(sammlungId, {
      lektion_nr: nr === null ? null : nr, ab, anzahl: JE_SEITE,
    });
    offenGesamt = daten.offen_gesamt;
    woerterGesamt = daten.gesamt;
    if (!anfuegen) leeren(liste);
    if (!daten.woerter.length && !anfuegen) {
      liste.append(h('div', { class: 'leer' },
        h('p', { text: 'Hier ist alles freigegeben.' }),
        h('button', { onclick: () => { location.hash = '#/freigabe'; } },
          'Zurück zur Übersicht')));
      leeren(fussleiste);
      standSetzen();
      return;
    }
    for (const wort of daten.woerter) liste.append(wortkarte(wort));
    leeren(fussleiste);
    if (ab + daten.anzahl < daten.gesamt) {
      fussleiste.append(h('button', {
        onclick: async () => { ab += JE_SEITE; await nachladen(true); },
      }, `Weitere ${Math.min(JE_SEITE, daten.gesamt - ab - daten.anzahl)} laden`));
    }
    fussleiste.append(h('button', { class: 'wichtig', onclick: lektionFreigeben },
      nr === null ? 'Alles ohne Lektion freigeben' : `Lektion ${nr} freigeben`));
    standSetzen();
  };

  async function lektionFreigeben() {
    const abgezogen = abgewaehlt.size;
    const frage = abgezogen
      ? `Die ganze Lektion freigeben, ohne die ${abgezogen} abgewählten Formen?`
      : 'Die ganze Lektion freigeben?';
    if (!window.confirm(frage)) return;
    const ergebnis = await api.freigabeSetzen(sammlungId, {
      lektion_nr: nr === null ? null : nr,
      lexem_ids: nr === null ? ohneLektionIds() : null,
      ausser: [...abgewaehlt],
    });
    meldung(`${ergebnis.gesetzt} Formen freigegeben.`);
    abgewaehlt.clear();
    ab = 0;
    await nachladen();
  }

  /** Bei "ohne Lektion" lässt sich nicht über die Nummer eingrenzen —
   *  dann zählen die Wörter, die gerade sichtbar sind. */
  function ohneLektionIds() {
    return [...liste.querySelectorAll('[data-lexem]')]
      .map((el) => Number(el.dataset.lexem));
  }

  function wortkarte(wort) {
    const karte = h('div', { class: 'karte', dataset: { lexem: wort.lexem_id } });
    karte.append(h('div', { class: 'freigabe-kopf' },
      h('h2', { style: 'margin:0', lang: wort.sprache },
        wort.lemma,
        h('span', { class: 'marke', text: wort.wortart_name })),
      h('span', { class: 'marke warnung', text: `${wort.offen} offen` })));

    const bedeutungen = wort.bedeutungen
      .map((b) => (b.kontext ? `${b.uebersetzungen.join(', ')} (${b.kontext})`
        : b.uebersetzungen.join(', ')))
      .join(' · ');
    karte.append(h('p', { class: 'leise', style: 'margin:.2rem 0 .6rem',
      text: bedeutungen || 'Keine Bedeutung eingetragen' }));

    // Die Befunde VOR den Tabellen: wer weiß, dass das Paradigma lückig
    // ist, liest die Tabelle anders.
    for (const b of wort.befunde) {
      karte.append(h('p', {
        class: 'befund ' + (b.schwere === 'fehler' ? 'fehler' : 'hinweis'),
      },
        h('strong', { text: b.text }),
        b.rat ? h('span', { class: 'leise', text: ' ' + b.rat }) : null));
    }

    // Mehrzellige Gruppen bekommen je eine Tabelle mit Überschrift.
    // Einzellige wandern zusammen in EINE Tabelle, in der der Gruppenname
    // die Zeile beschriftet: καλός / καλή / καλύτερος gehören untereinander
    // gelesen, nicht in drei Tabellen mit je einer Zeile.
    const einzeln = [];
    for (const g of wort.gruppen) {
      if (g.zellen.length === 1) {
        einzeln.push({ ...g.zellen[0], beschriftung: g.name });
      } else {
        karte.append(gruppentafel(wort, g));
      }
    }
    if (einzeln.length) karte.append(formtafel(wort, einzeln));
    if (wort.ausserhalb.length) {
      karte.append(h('p', { class: 'leise', style: 'margin:.6rem 0 .2rem',
        text: 'Formen, die in keine Formgruppe passen:' }));
      karte.append(formtafel(wort, wort.ausserhalb.map((f) => ({
        beschriftung: '—', formen: [f],
      }))));
    }

    karte.append(h('div', { class: 'freigabe-knoepfe' },
      h('button', {
        class: 'wichtig',
        onclick: async () => {
          const ergebnis = await api.freigabeSetzen(sammlungId, {
            lexem_ids: [wort.lexem_id], ausser: [...abgewaehlt],
          });
          meldung(`${wort.lemma}: ${ergebnis.gesetzt} Formen freigegeben.`);
          karte.remove();
          // Was WIRKLICH gesetzt wurde, nicht was offen war: die
          // abgewählten Formen bleiben offen und müssen weiter zählen.
          offenGesamt -= ergebnis.gesetzt;
          standSetzen();
        },
      }, 'Alles in Ordnung'),
      h('button', { onclick: () => { location.hash = `#/wort/${wort.lexem_id}`; } },
        'Bearbeiten')));
    return karte;
  }

  function gruppentafel(wort, gruppe) {
    const kasten = h('div', {});
    kasten.append(h('h3', { style: 'margin:.8rem 0 .3rem;font-size:1em' },
      gruppe.name,
      gruppe.belegt < gruppe.von
        ? h('span', { class: 'marke warnung',
            text: `${gruppe.belegt} von ${gruppe.von}` })
        : null,
      gruppe.erklaert
        ? h('span', { class: 'marke',
            text: `${gruppe.erklaert} gibt es nicht` })
        : null));
    kasten.append(formtafel(wort, gruppe.zellen));
    return kasten;
  }

  function formtafel(wort, zellen) {
    const koerper = h('tbody', {});
    for (const zelle of zellen) {
      if (!zelle.formen.length) {
        // Leere Zelle sichtbar lassen: dass hier nichts steht, ist die
        // Auskunft. Eine erklärte Lücke ist dagegen kein Mangel.
        koerper.append(h('tr', { class: 'zelle-leer' },
          h('td', { class: 'form leise',
            text: zelle.erklaerte_luecke ? 'gibt es nicht' : '—' }),
          h('td', { text: zelle.beschriftung }),
          h('td', { colspan: 2 },
            zelle.erklaerte_luecke
              ? h('span', { class: 'marke', text: 'erklärte Lücke' })
              : h('span', { class: 'leise', text: 'fehlt' }))));
        continue;
      }
      for (const f of zelle.formen) koerper.append(formzeile(wort, zelle, f));
    }
    return h('div', { class: 'tabellenrahmen' },
      h('table', { class: 'paradigma' }, koerper));
  }

  function formzeile(wort, zelle, f) {
    const zeile = h('tr', { class: f.geprueft ? null : 'ungeprueft' });
    const kasten = f.geprueft ? null : h('input', {
      type: 'checkbox', checked: true,
      'aria-label': `${f.text} ist in Ordnung`,
      onchange: (e) => {
        if (e.target.checked) abgewaehlt.delete(f.form_id);
        else abgewaehlt.add(f.form_id);
        zeile.classList.toggle('abgewaehlt', !e.target.checked);
        standSetzen();
      },
    });
    zeile.append(
      h('td', { class: 'form', lang: wort.sprache },
        f.text,
        f.ist_grundform ? h('span', { class: 'marke', text: 'Grundform' }) : null,
        f.ist_variante ? h('span', { class: 'marke', text: 'Variante' }) : null),
      h('td', { text: zelle.beschriftung }),
      h('td', {}, f.geprueft
        ? h('span', { class: 'marke', text: 'freigegeben' })
        : h('span', { class: 'marke warnung', text: f.quelle || 'neu' })),
      h('td', {}, kasten));
    return zeile;
  }

  await nachladen();
}
