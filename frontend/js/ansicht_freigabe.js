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
  // Regeln hängen an keiner Lektion — sie gelten für die Sprache, nicht
  // für ein Kapitel. Darum stehen sie hier oben und nicht in der Liste.
  const offeneRegeln = await regelkasten(behaelter, sammlungId);
  if (offeneRegeln) el.append(offeneRegeln);
  if (!uebersicht.offen_gesamt && !uebersicht.uebungen_offen_gesamt) {
    if (offeneRegeln) return;
    el.append(h('div', { class: 'leer' },
      h('p', { text: 'Alles freigegeben — es wartet nichts.' }),
      h('p', { class: 'leise', text: 'Hier erscheinen Formen, die über die '
        + 'Schnittstelle oder beim Import eingetragen wurden. Bis zur '
        + 'Freigabe werden sie nicht abgefragt.' })));
    return;
  }

  const teile = [];
  if (uebersicht.offen_gesamt) teile.push(`${uebersicht.offen_gesamt} Formen`);
  if (uebersicht.uebungen_offen_gesamt) {
    teile.push(`${uebersicht.uebungen_offen_gesamt} Übungen`);
  }
  el.append(h('p', { class: 'leise', text:
    `${teile.join(' und ')} warten auf Freigabe. Bis dahin werden sie nicht `
    + 'abgefragt.' }));

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
      k.offen
        ? h('span', { class: 'marke warnung', text: `${k.offen} Formen` })
        : null,
      k.uebungen_offen
        ? h('span', { class: 'marke warnung',
                      text: `${k.uebungen_offen} Übungen` })
        : null));
  }
  el.append(liste);
}

/* --------------------------------------------- Regeln freigeben */

/* Das »Warum ist das so?«, bevor es jemand zu sehen bekommt.
 *
 * Eine falsche Grammatikerklärung ist schlimmer als gar keine: man
 * merkt sie sich, und sie klingt plausibel. Darum derselbe Weg wie bei
 * Formen und Übungen — eingetragen wird ungeprüft, gezeigt wird erst
 * nach einem Blick.
 */
async function regelkasten(behaelter, sammlungId) {
  let offen = [];
  try {
    offen = await api.regeln(sammlungId, true);
  } catch { return null; }
  if (!offen.length) return null;

  const kasten = h('div', { class: 'karte' },
    h('h2', { text: `${offen.length} ${offen.length === 1 ? 'Regel wartet'
                                                          : 'Regeln warten'}` }),
    h('p', { class: 'leise',
      text: 'Grammatikerklärungen, die beim Üben neben der Frage stehen '
          + 'sollen. Eine falsche Erklärung merkt man sich — darum erst '
          + 'lesen.' }));

  for (const r of offen) {
    const zeile = h('div', { class: 'regel-pruefung' });
    zeile.append(h('h3', { class: 'regel-titel', text: r.titel }));
    for (const absatz of String(r.text || '').split(/\n{2,}/)) {
      if (absatz.trim()) zeile.append(h('p', { text: absatz.trim() }));
    }
    if (r.beispiele?.length) {
      zeile.append(h('ul', { class: 'regel-beispiele' },
        r.beispiele.map((b) => h('li', {},
          h('b', { text: b.form || b.text || '' }),
          b.bedeutung ? h('span', { text: ` — ${b.bedeutung}` }) : null))));
    }
    zeile.append(h('p', { class: 'leise',
      text: 'Gilt für: ' + musterText(r.muster) }));
    zeile.append(h('div', { class: 'frage-werkzeuge' },
      h('button', {
        class: 'wichtig',
        onclick: async () => {
          try {
            await api.regelFreigeben(r.id);
            zeile.remove();
            meldung(`»${r.titel}« ist freigegeben.`);
          } catch (fehler) { meldung(fehler.message, 'fehler'); }
        },
      }, 'In Ordnung'),
      h('button', {
        onclick: async () => {
          try {
            await api.regelLoeschen(r.id);
            zeile.remove();
            meldung(`»${r.titel}« ist gelöscht.`);
          } catch (fehler) { meldung(fehler.message, 'fehler'); }
        },
      }, 'Löschen')));
    kasten.append(zeile);
  }
  return kasten;
}

function musterText(muster) {
  const m = muster || {};
  const teile = [];
  if (m.wortart) teile.push(m.wortart);
  if (m.formgruppe) teile.push(m.formgruppe);
  for (const [d, w] of Object.entries(m.merkmale || {})) teile.push(`${d}: ${w}`);
  return teile.length ? teile.join(', ') : 'alles in dieser Sammlung';
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
  /** Abgewählte Übungen werden getrennt geführt: ihre Kennungen stammen
   *  aus einer anderen Tabelle und dürften sich sonst überschneiden. */
  const abgewaehlteUebungen = new Set();

  const titel = h('h1', { text: nr === null ? 'Ohne Lektion' : `Lektion ${nr}` });
  const stand = h('p', { class: 'leise' });
  const tastenhinweis = h('p', { class: 'leise', style: 'margin:.2rem 0 .8rem' },
    h('kbd', { text: 'Enter' }), ' gibt das markierte Wort frei, ',
    h('kbd', { text: '↓' }), ' und ', h('kbd', { text: '↑' }), ' gehen durch.');
  const liste = h('div', {
    class: 'freigabe-liste',
    style: 'display:flex;flex-direction:column;gap:1rem',
  });
  const fussleiste = h('div', { class: 'freigabe-leiste' });
  el.append(titel, stand, tastenhinweis, liste, fussleiste);

  let ab = 0;
  let offenGesamt = 0;
  let woerterGesamt = 0;
  // Außerhalb von nachladen(): die Kartenbauer unten brauchen sie, und
  // `daten` lebt nur innerhalb des Ladevorgangs.
  let sprache = null;

  let uebungenOffen = 0;
  /** Die Karte, die gerade dran ist. Beim Durchgehen zum Prüfen will man
   *  nicht scrollen, sondern weiterdrücken — also wird immer eine
   *  hervorgehoben, und nach dem Freigeben rückt die nächste nach. */
  let karten = [];
  let dran = 0;
  const standSetzen = () => {
    const abgezogen = abgewaehlt.size + abgewaehlteUebungen.size;
    stand.textContent = `${woerterGesamt} Wörter, ${offenGesamt} Formen offen`
      + (uebungenOffen ? `, ${uebungenOffen} Übungen` : '')
      + (abgezogen ? ` — ${abgezogen} abgewählt` : '');
  };

  const nachladen = async (anfuegen = false) => {
    const daten = await api.freigabe(sammlungId, {
      lektion_nr: nr === null ? null : nr, ab, anzahl: JE_SEITE,
    });
    offenGesamt = daten.offen_gesamt;
    woerterGesamt = daten.gesamt;
    uebungenOffen = daten.uebungen_gesamt || 0;
    sprache = daten.sprache;
    if (!anfuegen) { leeren(liste); karten = []; dran = 0; }
    if (!daten.woerter.length && !uebungenOffen && !anfuegen) {
      liste.append(h('div', { class: 'leer' },
        h('p', { text: 'Hier ist alles freigegeben.' }),
        h('button', { onclick: () => { location.hash = '#/freigabe'; } },
          'Zurück zur Übersicht')));
      leeren(fussleiste);
      standSetzen();
      return;
    }
    for (const wort of daten.woerter) {
      const karte = wortkarte(wort);
      karten.push(karte);
      liste.append(karte);
    }
    hervorheben(anfuegen ? dran : 0);
    if (!anfuegen && daten.uebungen && daten.uebungen.length) {
      liste.append(uebungskarte(daten.uebungen, daten.uebungen_gesamt));
    }
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
    const abgezogen = abgewaehlt.size + abgewaehlteUebungen.size;
    const frage = abgezogen
      ? `Die ganze Lektion freigeben — Formen und Übungssätze —, ohne die `
        + `${abgezogen} abgewählten?`
      : 'Die ganze Lektion freigeben, mit allen Übungssätzen?';
    if (!window.confirm(frage)) return;
    const ergebnis = await api.freigabeSetzen(sammlungId, {
      lektion_nr: nr === null ? null : nr,
      lexem_ids: nr === null ? ohneLektionIds() : null,
      ausser: [...abgewaehlt],
      ausser_uebungen: [...abgewaehlteUebungen],
    });
    meldung(`${ergebnis.gesetzt} Formen`
      + (ergebnis.uebungen ? ` und ${ergebnis.uebungen} Übungen` : '')
      + ' freigegeben.');
    abgewaehlt.clear();
    abgewaehlteUebungen.clear();
    ab = 0;
    await nachladen();
  }

  /** Bei "ohne Lektion" lässt sich nicht über die Nummer eingrenzen —
   *  dann zählen die Wörter, die gerade sichtbar sind. */
  function ohneLektionIds() {
    return [...liste.querySelectorAll('[data-lexem]')]
      .map((el) => Number(el.dataset.lexem));
  }

  /** Die Übungssätze der Lektion — in EINER Karte, nicht je Satz eine.
   *  Ein Satz ist in zwei Sekunden gelesen; vierzig Karten dafür wären
   *  vierzig Mal scrollen. */
  function uebungskarte(uebungen, gesamt) {
    const karte = h('div', { class: 'karte' });
    karte.append(h('div', { class: 'freigabe-kopf' },
      h('h2', { style: 'margin:0', text: 'Übungssätze' }),
      h('span', { class: 'marke warnung', text: `${gesamt} offen` })));
    karte.append(h('p', { class: 'leise', style: 'margin:.2rem 0 .6rem',
      text: 'Bis zur Freigabe werden sie nicht abgefragt. Einzelne lassen '
          + 'sich abwählen.' }));

    // Liste statt Tabelle: ein griechischer Satz ist lang, und in vier
    // Spalten rutschen Übersetzung und Kästchen seitlich aus dem Bild.
    // Untereinander bleibt beides lesbar, auch auf dem Telefon.
    const liste = h('div', { class: 'uebungsliste' });
    for (const u of uebungen) {
      const zeile = h('div', { class: 'uebungszeile' });
      const kasten = u.geprueft ? null : h('input', {
        type: 'checkbox', checked: true,
        'aria-label': `${u.inhalt} ist in Ordnung`,
        onchange: (e) => {
          if (e.target.checked) abgewaehlteUebungen.delete(u.uebung_id);
          else abgewaehlteUebungen.add(u.uebung_id);
          zeile.classList.toggle('abgewaehlt', !e.target.checked);
          standSetzen();
        },
      });
      zeile.append(
        h('div', { class: 'uebungskasten' },
          kasten || h('span', { class: 'marke', text: 'frei' })),
        h('div', { class: 'uebungstext' },
          h('p', { class: 'ziel', lang: sprache, text: u.inhalt }),
          h('p', { class: 'grund', text: u.uebersetzung || '—' }),
          h('p', { class: 'leise' },
            h('span', { class: 'marke', text: u.typ }),
            u.abschnitte > 1
              ? h('span', { class: 'marke', text: `${u.abschnitte} Abschnitte` })
              : null,
            h('span', { class: 'marke',
                        text: (u.richtungen || []).length === 2
                          ? 'beide Richtungen'
                          : ((u.richtungen || [])[0] === 'hin'
                             ? 'nur hin' : 'nur zurück') }))));
      liste.append(zeile);
    }
    karte.append(liste);
    if (gesamt > uebungen.length) {
      karte.append(h('p', { class: 'leise',
        text: `… und ${gesamt - uebungen.length} weitere. Der Knopf unten `
            + 'gibt alle frei.' }));
    }
    return karte;
  }

  /** Hebt eine Karte hervor und rollt sie in den Blick. */
  function hervorheben(i, rollen = false) {
    karten = karten.filter((k) => k.isConnected);
    if (!karten.length) { dran = 0; return; }
    dran = Math.max(0, Math.min(i, karten.length - 1));
    for (const [j, k] of karten.entries()) {
      k.classList.toggle('dran', j === dran);
    }
    if (rollen) {
      karten[dran].scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  }

  /** Nach dem Freigeben rückt die nächste Karte an dieselbe Stelle. */
  function weiter() {
    hervorheben(dran, true);
    standSetzen();
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

    karte.inOrdnung = async () => {
      const ergebnis = await api.freigabeSetzen(sammlungId, {
        lexem_ids: [wort.lexem_id], ausser: [...abgewaehlt],
      });
      meldung(`${wort.lemma}: ${ergebnis.gesetzt} Formen freigegeben.`);
      const stelle = karten.indexOf(karte);
      karte.remove();
      // Was WIRKLICH gesetzt wurde, nicht was offen war: die abgewählten
      // Formen bleiben offen und müssen weiter zählen.
      offenGesamt -= ergebnis.gesetzt;
      karten = karten.filter((k) => k.isConnected);
      // An dieselbe Stelle rückt die nächste Karte nach.
      hervorheben(Math.max(0, stelle), true);
      standSetzen();
      if (!karten.length) await nachladen();
    };
    karte.append(h('div', { class: 'freigabe-knoepfe' },
      h('button', { class: 'wichtig', onclick: () => karte.inOrdnung() },
        'Alles in Ordnung'),
      h('button', {
        onclick: () => hervorheben(karten.indexOf(karte) + 1, true),
      }, 'Später ansehen'),
      h('button', { class: 'schlicht',
                    onclick: () => { location.hash = `#/wort/${wort.lexem_id}`; } },
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

  // Tastatur: beim Durchgehen von dreißig Wörtern zählt jeder Griff zur
  // Maus. Enter gibt frei, Pfeile gehen durch.
  const aufTaste = (e) => {
    // Der Wegweiser tauscht bei jedem Seitenwechsel den Inhaltsbereich
    // aus. Ist unserer nicht mehr in der Seite, gehört der Behandler
    // auch nicht mehr dorthin.
    if (!el.isConnected) {
      document.removeEventListener('keydown', aufTaste);
      return;
    }
    if (e.metaKey || e.ctrlKey || e.altKey) return;
    if (['INPUT', 'TEXTAREA', 'SELECT'].includes(
        document.activeElement?.tagName)) return;
    const karte = karten[dran];
    if (!karte) return;
    if (e.key === 'Enter') { e.preventDefault(); karte.inOrdnung(); }
    else if (e.key === 'ArrowDown' || e.key === 'j') {
      e.preventDefault(); hervorheben(dran + 1, true);
    } else if (e.key === 'ArrowUp' || e.key === 'k') {
      e.preventDefault(); hervorheben(dran - 1, true);
    }
  };
  document.addEventListener('keydown', aufTaste);

  await nachladen();
}
