/* Wortschatz: Liste, Einzelansicht mit Paradigma, und die Eingabemaske.
 *
 * Die Eingabemaske baut sich aus den Formgruppen der Sprache auf. Wer eine
 * Sammlung hat, in der nur Présent und Passé composé abgefragt werden,
 * bekommt genau diese Felder — und nicht alle fünfzehn Zeiten. */

import { api } from './api.js';
import { h, leeren, meldung, sprechen } from './hilfen.js';
import { stammdaten } from './stammdaten.js';
import { zustand, merken } from './zustand.js';

async function sammlungSichern() {
  if (zustand.sammlungId) return zustand.sammlungId;
  const alle = await api.sammlungen(zustand.benutzerId);
  if (!alle.length) return null;
  merken({ sammlungId: alle[0].id });
  return alle[0].id;
}

/* -------------------------------------------------------------- Liste */

export async function zeichnen(behaelter) {
  const sammlungId = await sammlungSichern();
  const el = leeren(behaelter);
  if (!sammlungId) {
    el.append(h('div', { class: 'leer' },
      h('p', { text: 'Noch keine Sammlung vorhanden.' }),
      h('button', { class: 'wichtig', onclick: () => { location.hash = '#/uebersicht'; } },
        'Sammlung anlegen')));
    return;
  }

  const kopf = h('div', { style: 'display:flex;gap:.5rem;align-items:center;flex-wrap:wrap' });
  const suche = h('input', {
    type: 'search', placeholder: 'Suchen in Wort und Bedeutung', style: 'flex:1 1 12rem',
  });
  kopf.append(suche, h('button', {
    class: 'wichtig', onclick: () => { location.hash = '#/neu'; },
  }, '+ Wort'));

  el.append(h('h1', { text: 'Wortschatz' }), kopf);
  const liste = h('div', { class: 'liste', style: 'margin-top:1rem' });
  el.append(liste);

  let uhr = null;
  let lauf = 0;
  const nachladen = async () => {
    // Laufende Nummer gegen überholende Antworten: ohne sie kann die
    // Trefferliste zu "ab" unter dem Suchwort "abc" stehenbleiben.
    const meine = ++lauf;
    const ergebnis = await api.lexeme(sammlungId, { suche: suche.value, anzahl: 200 });
    if (meine !== lauf) return;
    leeren(liste);
    if (!ergebnis.lexeme.length) {
      liste.append(h('div', { class: 'leer' },
        h('p', { text: suche.value ? 'Nichts gefunden.' : 'Noch keine Wörter eingetragen.' })));
      return;
    }
    liste.append(h('p', { class: 'leise', text: `${ergebnis.gesamt} Wörter` }));
    for (const l of ergebnis.lexeme) {
      liste.append(h('button', {
        class: 'eintrag', onclick: () => { location.hash = `#/wort/${l.id}`; },
      },
        h('span', { class: 'lemma', text: l.lemma }),
        h('span', { class: 'bedeutung', text: l.erste_bedeutung || '—' }),
        l.formen_anzahl ? h('span', { class: 'marke', text: `${l.formen_anzahl} Formen` }) : null,
        l.ungeprueft_anzahl
          ? h('span', { class: 'marke warnung', text: `${l.ungeprueft_anzahl} ungeprüft` })
          : null,
        h('span', { class: 'marke', text: `${l.aufgaben_anzahl} Aufgaben` })));
    }
  };
  suche.addEventListener('input', () => { clearTimeout(uhr); uhr = setTimeout(nachladen, 220); });
  // Beim Verlassen der Ansicht die wartende Suche abräumen.
  window.addEventListener('hashchange', () => clearTimeout(uhr), { once: true });
  await nachladen();
}

/* ------------------------------------------------------- Einzelansicht */

export async function zeichnenEinzeln(behaelter, lexemId) {
  const lexem = await api.lexem(lexemId);
  const sprache = await stammdaten.sprache(lexem.sprache);
  const el = leeren(behaelter);

  el.append(h('div', { style: 'display:flex;justify-content:space-between;align-items:baseline;gap:1rem;flex-wrap:wrap' },
    h('div', {},
      h('h1', { style: 'margin:0', lang: lexem.sprache, text: lexem.lemma }),
      h('p', { class: 'leise', style: 'margin:.2rem 0 0',
               text: [lexem.wortart_name, sprache.name,
                      ...Object.entries(lexem.merkmale || {}).map(([d, w]) => `${d}: ${w}`)]
                     .filter(Boolean).join(' · ') })),
    sprache.stimme
      ? h('button', { onclick: () => sprechen(lexem.lemma, sprache.stimme) }, '🔊 Hören')
      : null));

  // Bedeutungen
  el.append(h('h2', { text: 'Bedeutungen' }));
  if (!lexem.bedeutungen.length) {
    el.append(h('p', { class: 'leise', text: 'Keine hinterlegt — ohne Bedeutung entsteht keine Abfrage.' }));
  }
  for (const b of lexem.bedeutungen) {
    el.append(h('div', { class: 'karte' },
      h('div', { style: 'display:flex;justify-content:space-between;gap:1rem' },
        h('div', {},
          h('strong', { text: b.uebersetzungen.map((u) => u.text).join(', ') }),
          b.kontext ? h('span', { class: 'leise', text: ` (${b.kontext})` }) : null,
          h('p', { class: 'leise', style: 'margin:.2rem 0 0',
                   text: `${b.uebersetzungen.length} gültige Übersetzung`
                       + (b.uebersetzungen.length === 1 ? '' : 'en') })),
        h('button', {
          class: 'schlicht gefahr',
          onclick: async () => {
            if (!confirm('Diese Bedeutung löschen?')) return;
            await api.bedeutungLoeschen(b.id);
            zeichnenEinzeln(behaelter, lexemId);
          },
        }, 'Löschen'))));
  }
  el.append(teilNeueBedeutung(behaelter, lexem));

  // Paradigma
  el.append(h('h2', { text: 'Formen' }));
  if (!lexem.formen.length) {
    el.append(h('p', { class: 'leise', text: 'Keine Formen eingetragen.' }));
  } else {
    const tafel = h('table', { class: 'paradigma' },
      h('thead', {}, h('tr', {},
        h('th', { text: 'Form' }), h('th', { text: 'Was ist das?' }),
        h('th', { text: 'Herkunft' }), h('th', { text: '' }))));
    const koerper = h('tbody', {});
    for (const f of lexem.formen) {
      koerper.append(h('tr', { class: f.geprueft ? null : 'ungeprueft' },
        h('td', { class: 'form', lang: lexem.sprache },
          f.text,
          f.ist_grundform ? h('span', { class: 'marke', text: 'Grundform' }) : null),
        h('td', { text: f.beschriftung }),
        h('td', {},
          h('span', { class: 'marke' + (f.geprueft ? '' : ' warnung'),
                      text: f.geprueft ? f.quelle : f.quelle + ', ungeprüft' })),
        h('td', { style: 'white-space:nowrap' },
          f.geprueft ? null : h('button', {
            class: 'schlicht',
            title: 'Als geprüft markieren — erst dann wird sie abgefragt',
            onclick: async () => { await api.formBestaetigen(f.id); zeichnenEinzeln(behaelter, lexemId); },
          }, '✓ Bestätigen'),
          h('button', {
            class: 'schlicht gefahr',
            onclick: async () => {
              if (!confirm(`Form „${f.text}" löschen?`)) return;
              await api.formLoeschen(f.id);
              zeichnenEinzeln(behaelter, lexemId);
            },
          }, 'Löschen'))));
    }
    tafel.append(koerper);
    el.append(h('div', { class: 'tabellenrahmen' }, tafel));
    const ungeprueft = lexem.formen.filter((f) => !f.geprueft);
    if (ungeprueft.length) {
      el.append(h('div', { class: 'karte' },
        h('p', { style: 'margin:0 0 .5rem',
                 text: `${ungeprueft.length} Formen sind noch ungeprüft und werden `
                     + 'darum nicht abgefragt. Eine erfundene Form, die unbemerkt '
                     + 'gepaukt wird, ist schlimmer als eine fehlende.' }),
        h('button', {
          onclick: async () => {
            for (const f of ungeprueft) await api.formBestaetigen(f.id);
            meldung(`${ungeprueft.length} Formen bestätigt.`);
            zeichnenEinzeln(behaelter, lexemId);
          },
        }, 'Alle bestätigen')));
    }
  }
  el.append(await teilNeueForm(behaelter, lexem));

  // Aufgaben
  const aktive = (lexem.aufgaben || []).filter((a) => a.aktiv);
  el.append(h('details', { class: 'karte', style: 'margin-top:1.5rem' },
    h('summary', { text: `${aktive.length} Aufgaben aus diesem Wort` }),
    h('p', { class: 'leise', text: 'Aufgaben werden aus den Daten erzeugt, nicht '
                                 + 'von Hand gepflegt. Welche entstehen, steuern die '
                                 + 'Einstellungen der Sammlung.' }),
    h('ul', {}, (lexem.aufgaben || []).map((a) => h('li', {
      class: a.aktiv ? null : 'leise',
    }, `${a.typ}${a.aktiv ? '' : ' — abgeschaltet'}`)))));

  el.append(h('div', { class: 'frage-werkzeuge', style: 'justify-content:flex-start;margin-top:1.5rem' },
    h('button', { onclick: () => { location.hash = '#/wortschatz'; } }, 'Zurück zur Liste'),
    h('button', {
      class: 'schlicht gefahr',
      onclick: async () => {
        if (!confirm(`„${lexem.lemma}" mit allen Formen und dem Lernstand löschen?`)) return;
        await api.lexemLoeschen(lexem.id);
        meldung('Gelöscht.');
        location.hash = '#/wortschatz';
      },
    }, 'Wort löschen')));
}

function teilNeueBedeutung(behaelter, lexem) {
  const texte = h('input', { type: 'text', placeholder: 'gehen, laufen, zu Fuß gehen' });
  const kontext = h('input', { type: 'text', placeholder: 'Unterscheidung, z.B. „mit Fahrzeug" (frei)' });
  return h('details', { class: 'karte' },
    h('summary', { text: '+ Bedeutung hinzufügen' }),
    h('div', { style: 'display:grid;gap:.5rem;margin-top:.8rem' },
      h('p', { class: 'leise', style: 'margin:0',
               text: 'Mehrere gültige Übersetzungen mit Komma trennen — der Trainer '
                   + 'nimmt jede davon an.' }),
      texte, kontext,
      h('button', {
        class: 'wichtig',
        onclick: async () => {
          const liste = texte.value.split(',').map((t) => t.trim()).filter(Boolean);
          if (!liste.length) { meldung('Keine Übersetzung eingegeben.'); return; }
          try {
            await api.bedeutungAnlegen(lexem.id, {
              uebersetzungen: liste.map((t, i) => ({ text: t, ist_haupt: i === 0 })),
              kontext: kontext.value.trim() || null,
              reihenfolge: lexem.bedeutungen.length,
            });
            zeichnenEinzeln(behaelter, lexem.id);
          } catch (fehler) { meldung(fehler.message); }
        },
      }, 'Hinzufügen')));
}

async function teilNeueForm(behaelter, lexem) {
  const [gruppen, einstellungen] = await Promise.all([
    stammdaten.formgruppen(lexem.sprache),
    api.sammlungEinstellungen(lexem.sammlung_id),
  ]);
  const fuerWortart = gruppen.wortarten[lexem.wortart] || [];
  if (!fuerWortart.length) {
    return h('p', { class: 'leise',
      text: `Für ${lexem.wortart_name} in ${gruppen.sprache} sind keine Formgruppen hinterlegt.` });
  }
  const aktiv = new Set(einstellungen.formgruppen);
  const wahl = h('select', {},
    fuerWortart.map((g) => h('option', {
      value: g.kennung,
      text: g.name + (aktiv.has(g.kennung) ? '' : ' — nicht abgefragt'),
    })));
  const felder = h('div', { style: 'display:grid;gap:.5rem;margin-top:.8rem' });

  const zellenBauen = async () => {
    leeren(felder);
    const gruppe = fuerWortart.find((g) => g.kennung === wahl.value);
    if (!gruppe) return;
    // Zellen aus der Schnittstelle: eine Zeile je Zelle, beschriftet.
    const zellen = await zellenHolen(lexem.sprache, lexem.wortart, gruppe.kennung);
    for (const z of zellen) {
      const vorhanden = lexem.formen.find(
        (f) => JSON.stringify(sortiert(f.merkmale)) === JSON.stringify(sortiert(z.merkmale)));
      const feld = h('input', {
        type: 'text', lang: lexem.sprache, value: vorhanden ? vorhanden.text : '',
        placeholder: z.beschriftung,
      });
      felder.append(h('div', { class: 'feldzeile' },
        h('label', { class: 'leise', text: z.beschriftung }), feld));
      z._feld = feld; z._vorhanden = vorhanden;
    }
    felder.append(h('button', {
      class: 'wichtig',
      onclick: async () => {
        let gezaehlt = 0;
        for (const z of zellen) {
          const text = z._feld.value.trim();
          if (!text) continue;
          if (z._vorhanden && z._vorhanden.text === text) continue;
          try {
            if (z._vorhanden) {
              await api.formAendern(z._vorhanden.id, {
                text, merkmale: z.merkmale, ist_grundform: false,
                quelle: 'manuell', geprueft: true,
              });
            } else {
              await api.formAnlegen(lexem.id, {
                text, merkmale: z.merkmale, quelle: 'manuell', geprueft: true,
              });
            }
            gezaehlt += 1;
          } catch (fehler) { meldung(fehler.message); return; }
        }
        meldung(gezaehlt ? `${gezaehlt} Formen gespeichert.` : 'Nichts geändert.');
        zeichnenEinzeln(behaelter, lexem.id);
      },
    }, 'Formen speichern'));
  };
  wahl.addEventListener('change', zellenBauen);
  const kasten = h('details', { class: 'karte' },
    h('summary', { text: '+ Formen eintragen' }),
    h('div', { style: 'margin-top:.8rem' },
      h('p', { class: 'leise', style: 'margin:0 0 .5rem',
               text: 'Zeit auswählen, dann die Zellen füllen. Leere Felder werden '
                   + 'übersprungen.' }),
      wahl, felder));
  kasten.addEventListener('toggle', () => { if (kasten.open && !felder.children.length) zellenBauen(); });
  return kasten;
}

function sortiert(objekt) {
  return Object.fromEntries(Object.entries(objekt || {}).sort());
}

/* Die Zellen einer Formgruppe samt Beschriftung. Die Schnittstelle gibt die
 * Gruppen zurück, die Zellen rechnen wir aus den Merkmalen aus — dieselbe
 * Reihenfolge wie im Sprachprofil. */
const zellenHalde = {};
async function zellenHolen(sprache, wortart, kennung) {
  const schluessel = `${sprache}/${wortart}/${kennung}`;
  if (zellenHalde[schluessel]) return zellenHalde[schluessel].map((z) => ({ ...z }));
  const antwort = await fetch(
    `/api/sprachen/${sprache}/formgruppen/${encodeURIComponent(kennung)}/zellen`);
  if (!antwort.ok) return [];
  const zellen = await antwort.json();
  zellenHalde[schluessel] = zellen;
  return zellen.map((z) => ({ ...z }));
}

/* ---------------------------------------------------------- Neues Wort */

export async function zeichnenNeu(behaelter) {
  const sammlungId = await sammlungSichern();
  const el = leeren(behaelter);
  if (!sammlungId) {
    el.append(h('div', { class: 'leer' },
      h('p', { text: 'Es gibt noch keine Sammlung, in die das Wort könnte.' }),
      h('button', { class: 'wichtig', onclick: () => { location.hash = '#/uebersicht'; } },
        'Sammlung anlegen')));
    return;
  }
  // Die Einstellungen nur EINMAL holen; die Sprache daraus.
  const einstellungen = await api.sammlungEinstellungen(sammlungId);
  const sprache = einstellungen.sprache;
  const [gruppen, merkmale] = await Promise.all([
    api.formgruppen(sprache), stammdaten.merkmale(),
  ]);
  el.append(h('h1', { text: 'Neues Wort' }),
            h('p', { class: 'leise', text: `${gruppen.sprache} · Bedeutungen und Formen `
                                         + 'in einem Zug — die Aufgaben entstehen daraus '
                                         + 'von selbst.' }));

  const lemma = h('input', { type: 'text', lang: sprache, placeholder: 'Wort in der Grundform' });
  const wortart = h('select', {},
    Object.entries(merkmale.wortarten).map(([w, n]) => h('option', { value: w, text: n })));
  wortart.value = 'verb';
  const uebersetzungen = h('input', { type: 'text', placeholder: 'gehen, laufen, zu Fuß gehen' });
  const lexemfelder = h('div', { style: 'display:grid;gap:.5rem' });
  const formfelder = h('div', {});

  const neuBauen = async () => {
    // Lexemmerkmale der gewählten Wortart (Geschlecht, Ablautreihe, Hilfsverb)
    leeren(lexemfelder);
    const moeglich = gruppen.lexemmerkmale[wortart.value] || {};
    for (const [dim, werte] of Object.entries(moeglich)) {
      const auswahl = h('select', { dataset: { dim } },
        h('option', { value: '', text: '– keine Angabe –' }),
        werte.map((w) => h('option', {
          value: w, text: merkmale.inventar[dim]?.[w]?.lang || w,
        })));
      lexemfelder.append(h('div', { class: 'feldzeile' },
        h('label', { class: 'leise', text: beschriftung(dim) }), auswahl));
    }
    // Formfelder aus den abgefragten Formgruppen
    leeren(formfelder);
    const aktiv = new Set(einstellungen.formgruppen);
    const fuer = (gruppen.wortarten[wortart.value] || []).filter((g) => aktiv.has(g.kennung));
    if (!fuer.length) {
      formfelder.append(h('p', { class: 'leise',
        text: 'Für diese Wortart fragt die Sammlung derzeit keine Formen ab. '
            + 'Das Wort lässt sich trotzdem anlegen; Formen kommen später dazu.' }));
      return;
    }
    for (const g of fuer) {
      const zellen = await zellenHolen(sprache, wortart.value, g.kennung);
      const raster = h('div', { style: 'display:grid;gap:.4rem' });
      for (const z of zellen) {
        const feld = h('input', { type: 'text', lang: sprache, placeholder: '—' });
        z._feld = feld;
        raster.append(h('div', { class: 'feldzeile' },
          h('label', { class: 'leise', text: z.beschriftung }), feld));
      }
      formfelder.append(h('details', { class: 'karte', open: g.kennung === fuer[0].kennung },
        h('summary', { text: g.name }), h('div', { style: 'margin-top:.6rem' }, raster)));
      g._zellen = zellen;
    }
    formfelder._gruppen = fuer;
  };
  wortart.addEventListener('change', neuBauen);

  el.append(h('div', { class: 'karte' },
    h('div', { style: 'display:grid;gap:.6rem' },
      h('div', {}, h('label', { class: 'leise', text: 'Wort' }), lemma),
      h('div', {}, h('label', { class: 'leise', text: 'Wortart' }), wortart),
      h('div', {}, h('label', { class: 'leise', text: 'Bedeutungen (mit Komma trennen)' }),
        uebersetzungen),
      lexemfelder)));
  el.append(h('h2', { text: 'Formen' }), formfelder);

  el.append(h('div', { class: 'frage-werkzeuge', style: 'justify-content:flex-start;margin-top:1rem' },
    h('button', {
      class: 'wichtig',
      onclick: async () => {
        if (!lemma.value.trim()) { meldung('Das Wort fehlt.'); return; }
        const lexemMerkmale = {};
        for (const auswahl of lexemfelder.querySelectorAll('select')) {
          if (auswahl.value) lexemMerkmale[auswahl.dataset.dim] = auswahl.value;
        }
        const formen = [];
        for (const g of formfelder._gruppen || []) {
          for (const z of g._zellen || []) {
            const text = z._feld.value.trim();
            if (text) formen.push({ text, merkmale: z.merkmale, geprueft: true });
          }
        }
        // Die Grundform ist das Lemma selbst, falls nicht schon dabei.
        const liste = uebersetzungen.value.split(',').map((t) => t.trim()).filter(Boolean);
        try {
          const neu = await api.lexemAnlegen({
            sammlung_id: sammlungId,
            lemma: lemma.value.trim(),
            wortart: wortart.value,
            merkmale: lexemMerkmale,
            formen,
            bedeutungen: liste.length
              ? [{ uebersetzungen: liste.map((t, i) => ({ text: t, ist_haupt: i === 0 })) }]
              : [],
          });
          meldung(`Angelegt — ${neu.aufgaben_bilanz.angelegt} Aufgaben entstanden.`);
          location.hash = `#/wort/${neu.id}`;
        } catch (fehler) { meldung(fehler.message); }
      },
    }, 'Anlegen'),
    h('button', { onclick: () => { location.hash = '#/wortschatz'; } }, 'Abbrechen')));

  await neuBauen();
}

function beschriftung(dim) {
  return { genus: 'Geschlecht', klasse: 'Klasse', hilfsverb: 'Hilfsverb',
           flexion: 'Flexion' }[dim] || dim;
}
