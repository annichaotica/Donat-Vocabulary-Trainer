/* Wortschatz: Liste, Einzelansicht mit Paradigma, und die Eingabemaske.
 *
 * Die Eingabemaske baut sich aus den Formgruppen der Sprache auf. Wer eine
 * Sammlung hat, in der nur Présent und Passé composé abgefragt werden,
 * bekommt genau diese Felder — und nicht alle fünfzehn Zeiten. */

import { api } from './api.js';
import { h, leeren, meldung, sprechen, tun } from './hilfen.js';
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

/* Welche Kapitel gerade gewählt sind, und was angehakt ist.
 *
 * Außerhalb der Zeichenfunktion, damit die Auswahl einen Sprung in ein
 * Wort und zurück übersteht — sonst verliert man dreißig Haken, weil
 * man eine Bedeutung nachsehen wollte. */
let filter = { lektion: '', wortart: '' };
let angehakt = new Set();
// Zu WELCHER Sammlung Filter und Haken gehören. Ohne das zeigte ein
// Wechsel der Sammlung eine leere Liste: die Kapitelkennung der alten
// Sammlung gibt es in der neuen nicht, und gefiltert wurde trotzdem
// danach. Die Haken wären obendrein fremde Wörter gewesen.
let gemerkteSammlung = null;

const OHNE_KAPITEL = 'ohne';

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

  if (gemerkteSammlung !== sammlungId) {
    gemerkteSammlung = sammlungId;
    filter = { lektion: '', wortart: '' };
    angehakt.clear();
  }

  const lektionen = await api.lektionen(sammlungId).catch(() => []);

  const kopf = h('div', { style: 'display:flex;gap:.5rem;align-items:center;flex-wrap:wrap' });
  const suche = h('input', {
    type: 'search', placeholder: 'Suchen in Wort und Bedeutung', style: 'flex:1 1 12rem',
  });
  kopf.append(suche, h('button', {
    class: 'wichtig', onclick: () => { location.hash = '#/neu'; },
  }, '+ Wort'), h('button', {
    onclick: () => { location.hash = '#/import'; },
  }, 'Datei einlesen'));

  // Das Kapitel ist der Hauptweg durch den Wortschatz, nicht ein
  // Nebenfilter: die Liste zeigt höchstens 200 Wörter, und im
  // griechischen Bestand stehen 1927. Ohne diese Auswahl sah man den
  // Anfang des Alphabets und sonst nichts.
  const lektionWahl = h('select', {},
    h('option', { value: '', text: 'alle Kapitel' }),
    lektionen.map((k) => h('option', {
      value: String(k.id),
      text: (k.nr !== null ? `${k.nr}. ` : '') + (k.name || 'ohne Namen')
          + ` (${k.lexeme})`,
    })),
    h('option', { value: OHNE_KAPITEL, text: 'ohne Kapitel' }));
  lektionWahl.value = filter.lektion;
  lektionWahl.addEventListener('change', () => {
    filter.lektion = lektionWahl.value;
    angehakt.clear();
    nachladen();
  });

  el.append(h('h1', { text: 'Wortschatz' }), kopf,
    h('div', { class: 'gezielt-filter', style: 'margin-top:.6rem' },
      lektionWahl));

  const stapel = h('div', {});
  const liste = h('div', { class: 'liste', style: 'margin-top:1rem' });
  el.append(stapel, liste);

  let uhr = null;
  let lauf = 0;

  const verschieben = (zielId, nr) => tun(async () => {
    const ids = [...angehakt];
    const daten = { lexem_ids: ids };
    if (zielId) daten.lektion_id = Number(zielId);
    else if (nr !== undefined) daten.lektion_nr = nr;
    const e = await api.lexemeVerschieben(sammlungId, daten);
    meldung(`${e.verschoben} ${e.verschoben === 1 ? 'Wort' : 'Wörter'} `
          + 'verschoben'
          + (e.aufgaben_geaendert
             ? ` — ${e.aufgaben_geaendert} Aufgaben haben sich dadurch `
               + 'geändert.' : '.'), 4000);
    angehakt.clear();
    zeichnen(behaelter);
  });

  /* Was mit der Auswahl geschehen soll. Erscheint erst, wenn etwas
   * angehakt ist — ein Kasten, der meistens leer dasteht, erzieht
   * dazu, ihn zu übersehen. */
  const stapelZeichnen = () => {
    leeren(stapel);
    if (!angehakt.size) return;
    const wohin = h('select', {},
      h('option', { value: '', text: 'Kapitel wählen …' }),
      lektionen.map((k) => h('option', {
        value: String(k.id),
        text: (k.nr !== null ? `${k.nr}. ` : '') + (k.name || 'ohne Namen'),
      })),
      h('option', { value: OHNE_KAPITEL, text: 'ohne Kapitel' }));
    const neueNr = h('input', { type: 'number', min: '0', max: '9999',
                                placeholder: 'neue Nr.',
                                style: 'width:7rem' });
    stapel.append(h('div', { class: 'karte gezielt-stapel' },
      h('b', { text: `${angehakt.size} ausgewählt` }),
      h('div', { class: 'frage-werkzeuge',
                 style: 'justify-content:flex-start;flex-wrap:wrap' },
        wohin,
        h('button', {
          class: 'wichtig',
          onclick: () => {
            if (!wohin.value) { meldung('Erst ein Kapitel wählen.'); return; }
            verschieben(wohin.value === OHNE_KAPITEL ? null : wohin.value,
                        wohin.value === OHNE_KAPITEL ? null : undefined);
          },
        }, 'Verschieben'),
        neueNr,
        h('button', {
          title: 'Legt das Kapitel an, falls es noch nicht da ist.',
          onclick: () => {
            if (neueNr.value === '') { meldung('Welche Nummer?'); return; }
            verschieben(null, Number(neueNr.value));
          },
        }, 'In neues Kapitel'),
        h('button', { class: 'schlicht',
                      onclick: () => { angehakt.clear(); stapelZeichnen();
                                       nachladen(); } },
          'Auswahl aufheben')),
      h('p', { class: 'leise', style: 'margin:.6rem 0 0',
               text: 'Das Kapitel entscheidet mit, wann ein Wort drankommt: '
                   + 'an ihm hängt die Lektionsschranke. Verschieben ist '
                   + 'darum keine Beschriftung, sondern ein Eingriff in '
                   + 'den Plan.' })));
  };

  const nachladen = async () => {
    // Laufende Nummer gegen überholende Antworten: ohne sie kann die
    // Trefferliste zu "ab" unter dem Suchwort "abc" stehenbleiben.
    const meine = ++lauf;
    const frage = { suche: suche.value, anzahl: 200 };
    if (filter.lektion === OHNE_KAPITEL) frage.ohne_lektion = true;
    else if (filter.lektion) frage.lektion_id = Number(filter.lektion);
    const ergebnis = await api.lexeme(sammlungId, frage);
    if (meine !== lauf) return;
    const woerter = ergebnis.lexeme;

    leeren(liste);
    if (!woerter.length) {
      liste.append(h('div', { class: 'leer' },
        h('p', { text: suche.value ? 'Nichts gefunden.'
                                   : 'Hier steht noch kein Wort.' })));
      return;
    }

    // Ehrlich sagen, dass die Liste abgeschnitten ist. Vorher stand da
    // »1927 Wörter« über 200 angezeigten, und man suchte den Rest.
    const abgeschnitten = ergebnis.gesamt > ergebnis.anzahl;
    liste.append(h('p', { class: 'leise' },
      abgeschnitten
        ? `${ergebnis.anzahl} von ${ergebnis.gesamt} Wörtern — nach Kapitel `
          + 'auswählen oder suchen, um den Rest zu sehen.'
        : `${woerter.length} ${woerter.length === 1 ? 'Wort' : 'Wörter'}`));

    let letztes;
    for (const l of woerter) {
      // Die Kapitelüberschrift zwischen den Wörtern: so liest sich die
      // Liste wie das Glossar des Lehrwerks, und man sieht auf einen
      // Blick, wo ein Wort hingehört.
      const kapitel = l.lektion_id === null ? OHNE_KAPITEL : l.lektion_id;
      if (kapitel !== letztes && !filter.lektion) {
        letztes = kapitel;
        liste.append(h('h2', { class: 'kapitelkopf',
          text: l.lektion_id === null
            ? 'Ohne Kapitel'
            : (l.lektion_nr !== null ? `${l.lektion_nr}. ` : '')
              + (l.lektion_name || 'ohne Namen') }));
      }

      const kasten = h('input', { type: 'checkbox', class: 'eintrag-haken',
                                  title: 'auswählen' });
      kasten.checked = angehakt.has(l.id);
      kasten.addEventListener('change', () => {
        if (kasten.checked) angehakt.add(l.id); else angehakt.delete(l.id);
        // Nur den Stapelkasten erneuern, nicht die Liste: beim
        // Durchhaken von dreißig Wörtern darf die Seite nicht unter
        // den Fingern wegspringen.
        stapelZeichnen();
      });

      liste.append(h('div', { class: 'eintrag-zeile' },
        kasten,
        h('button', {
          class: 'eintrag', style: 'flex:1 1 auto',
          onclick: () => { location.hash = `#/wort/${l.id}`; },
        },
          h('span', { class: 'lemma', text: l.lemma }),
          h('span', { class: 'bedeutung', text: l.erste_bedeutung || '—' }),
          l.formen_anzahl
            ? h('span', { class: 'marke', text: `${l.formen_anzahl} Formen` }) : null,
          l.ungeprueft_anzahl
            ? h('span', { class: 'marke warnung', text: `${l.ungeprueft_anzahl} ungeprüft` })
            : null,
          h('span', { class: 'marke', text: `${l.aufgaben_anzahl} Aufgaben` }))));
    }
    stapelZeichnen();
  };
  suche.addEventListener('input', () => { clearTimeout(uhr); uhr = setTimeout(nachladen, 220); });
  // Beim Verlassen der Ansicht die wartende Suche abräumen.
  window.addEventListener('hashchange', () => clearTimeout(uhr), { once: true });
  await nachladen();
}

/* ------------------------------------------------------- Einzelansicht */

/** Die Wörter, die noch auf Freigabe warten — die Reihe, die man durchgeht.
 *
 *  Ohne sie heißt Prüfen: Wort anklicken, bestätigen, zurück zur Liste,
 *  scrollen, nächstes anklicken. Das nervt beim dritten Wort.
 */
/** Der zuletzt angemeldete Tastaturbehandler der Einzelansicht.
 *
 *  Sie zeichnet sich auch ohne Seitenwechsel neu — etwa nachdem eine
 *  einzelne Form bestätigt wurde. Dann bleibt der Inhaltsbereich
 *  derselbe, und ohne dieses Abmelden hinge ein zweiter Behandler daran:
 *  Enter löste doppelt aus.
 */
let tastenbehandler = null;


async function warteschlange(sammlungId) {
  try {
    const offen = await api.lexeme(sammlungId,
                                   { nur_ungepruefte: true, anzahl: 500 });
    return offen.lexeme.map((l) => l.id);
  } catch { return []; }
}


export async function zeichnenEinzeln(behaelter, lexemId) {
  const lexem = await api.lexem(lexemId);
  const sprache = await stammdaten.sprache(lexem.sprache);
  const el = leeren(behaelter);
  if (tastenbehandler) {
    document.removeEventListener('keydown', tastenbehandler);
    tastenbehandler = null;
  }
  const reihe = await warteschlange(lexem.sammlung_id);
  const stelle = reihe.indexOf(lexem.id);
  const naechstes = () => {
    // Nach dem Bestätigen ist dieses Wort aus der Reihe heraus — das
    // nächste rückt auf dieselbe Stelle. Darum nicht stelle+1.
    const rest = reihe.filter((id) => id !== lexem.id);
    if (!rest.length) return null;
    return rest[Math.min(Math.max(stelle, 0), rest.length - 1)];
  };
  const weiterZu = (id) => {
    if (id) location.hash = `#/wort/${id}`;
    else { meldung('Alle Wörter dieser Sammlung sind freigegeben.');
           location.hash = '#/wortschatz'; }
  };

  el.append(h('div', { class: 'wortkopf',
                       style: 'display:flex;justify-content:space-between;align-items:baseline;gap:1rem;flex-wrap:wrap' },
    h('div', {},
      h('h1', { style: 'margin:0', lang: lexem.sprache, text: lexem.lemma }),
      h('p', { class: 'leise', style: 'margin:.2rem 0 0',
               text: [lexem.wortart_name, sprache.name,
                      ...Object.entries(lexem.merkmale || {}).map(([d, w]) => `${d}: ${w}`)]
                     .filter(Boolean).join(' · ') })),
    h('div', { style: 'display:flex;gap:.4rem' },
      h('button', {
        onclick: () => kopfBearbeiten(behaelter, lexem),
      }, 'Bearbeiten'),
      sprache.stimme
        ? h('button', { onclick: () => sprechen(lexem.lemma, sprache.stimme) },
            '🔊 Hören')
        : null)));

  // Wo man in der Durchsicht steht, und wie man weiterkommt.
  if (stelle >= 0 && reihe.length > 1) {
    el.append(h('div', { class: 'durchsicht' },
      h('span', { class: 'leise',
                  text: `${stelle + 1} von ${reihe.length} noch ungeprüft` }),
      h('div', { class: 'durchsicht-knoepfe' },
        h('button', {
          disabled: stelle === 0,
          onclick: () => weiterZu(reihe[stelle - 1]),
        }, '‹ Vorheriges'),
        h('button', {
          disabled: stelle >= reihe.length - 1,
          onclick: () => weiterZu(reihe[stelle + 1]),
        }, 'Nächstes ›'))));
  }

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
        h('div', { style: 'white-space:nowrap' },
          h('button', {
            class: 'schlicht',
            onclick: (e) => {
              const karte = e.target.closest('.karte');
              if (karte.nextElementSibling?.classList.contains('bedeutungbearbeiten')) {
                return;
              }
              const kasten = bedeutungBearbeiten(behaelter, lexem, b);
              kasten.classList.add('bedeutungbearbeiten');
              karte.insertAdjacentElement('afterend', kasten);
            },
          }, 'Ändern'),
          h('button', {
            class: 'schlicht gefahr',
            onclick: () => tun(async () => {
                if (!confirm('Diese Bedeutung löschen?')) return;
                await api.bedeutungLoeschen(b.id);
                zeichnenEinzeln(behaelter, lexemId);
            }),
          }, 'Löschen')))));
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
          h('button', {
            class: 'schlicht',
            title: 'Schreibung oder Bestimmung berichtigen',
            onclick: (e) => formBearbeiten(behaelter, lexem, f,
                                           e.target.closest('tr')),
          }, 'Ändern'),
          f.geprueft ? null : h('button', {
            class: 'schlicht',
            title: 'Als geprüft markieren — erst dann wird sie abgefragt',
            onclick: () => tun(async () => {
              await api.formBestaetigen(f.id);
              zeichnenEinzeln(behaelter, lexemId);
            }),
          }, '✓ Bestätigen'),
          h('button', {
            class: 'schlicht gefahr',
            onclick: () => tun(async () => {
                if (!confirm(`Form „${f.text}" löschen?`)) return;
                await api.formLoeschen(f.id);
                zeichnenEinzeln(behaelter, lexemId);
            }),
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
        h('div', { class: 'freigabe-knoepfe' },
          h('button', {
            class: 'wichtig',
            onclick: () => bestaetigenUndWeiter(ungeprueft),
          }, reihe.length > 1 ? 'Bestätigen und weiter' : 'Alle bestätigen'),
          reihe.length > 1
            ? h('button', { onclick: () => weiterZu(naechstes()) },
                'Später — nächstes Wort')
            : null)));
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

  if (stelle >= 0 && reihe.length > 1) {
    el.append(h('p', { class: 'leise', style: 'margin-top:1rem' },
      h('kbd', { text: 'Enter' }), ' bestätigt und geht weiter, ',
      h('kbd', { text: '→' }), ' und ', h('kbd', { text: '←' }), ' blättern.'));
  }

  el.append(h('div', { class: 'frage-werkzeuge', style: 'justify-content:flex-start;margin-top:1.5rem' },
    h('button', { onclick: () => { location.hash = '#/wortschatz'; } }, 'Zurück zur Liste'),
    h('button', {
      class: 'schlicht gefahr',
      onclick: () => tun(async () => {
          if (!confirm(`„${lexem.lemma}" mit allen Formen und dem Lernstand löschen?`)) return;
          await api.lexemLoeschen(lexem.id);
          meldung('Gelöscht.');
          location.hash = '#/wortschatz';
      }),
    }, 'Wort löschen')));

  async function bestaetigenUndWeiter(ungeprueft) {
    const ziel = naechstes();
    for (const f of ungeprueft) await api.formBestaetigen(f.id);
    meldung(`${lexem.lemma}: ${ungeprueft.length} Formen bestätigt.`);
    if (reihe.length > 1) weiterZu(ziel);
    else zeichnenEinzeln(behaelter, lexemId);
  }

  // Tastatur. Beim Durchsehen von dreißig Wörtern zählt jeder Griff zur
  // Maus — und genau dafür ist diese Ansicht jetzt da.
  const aufTaste = (e) => {
    if (!el.isConnected) {
      document.removeEventListener('keydown', aufTaste);
      return;
    }
    if (e.metaKey || e.ctrlKey || e.altKey) return;
    if (['INPUT', 'TEXTAREA', 'SELECT'].includes(
        document.activeElement?.tagName)) return;
    if (e.key === 'Enter') {
      const offen = lexem.formen.filter((f) => !f.geprueft);
      e.preventDefault();
      if (offen.length) bestaetigenUndWeiter(offen);
      else weiterZu(naechstes());
    } else if (e.key === 'ArrowRight' && stelle >= 0
               && stelle < reihe.length - 1) {
      e.preventDefault(); weiterZu(reihe[stelle + 1]);
    } else if (e.key === 'ArrowLeft' && stelle > 0) {
      e.preventDefault(); weiterZu(reihe[stelle - 1]);
    }
  };
  tastenbehandler = aufTaste;
  document.addEventListener('keydown', aufTaste);
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

/* ------------------------------------------------------- Berichtigen
 *
 * »Wir müssen die Datensätze natürlich auch mal überarbeiten können.
 * Dafür fehlt ein Knopf!«
 *
 * Es gab Löschen und Bestätigen, aber kein Ändern. Ein Tippfehler in
 * einer Form war damit nur zu beheben, indem man sie löscht und neu
 * anlegt — und dabei ist der Lernstand weg, denn er hängt an der Form.
 * Bei einem Bestand, den zum großen Teil eine KI gefüllt hat, ist das
 * die falsche Richtung: berichtigen wird häufiger gebraucht als
 * wegwerfen.
 *
 * Die Schnittstelle konnte das längst. Es fehlte nur der Knopf.
 */

/** Alle Zellen einer Wortart, quer durch die Formgruppen.
 *
 * Für die Berichtigung einer BESTIMMUNG: »zwei Genitiv Singular« ist
 * nicht unbedingt ein Tippfehler, sondern meist eine falsch
 * eingeordnete Form, und die gehört umgehängt statt gelöscht.
 */
async function zellenDerWortart(sprache, wortart) {
  const gruppen = await stammdaten.formgruppen(sprache);
  const liste = [];
  for (const g of (gruppen.wortarten[wortart] || [])) {
    for (const z of await zellenHolen(sprache, wortart, g.kennung)) {
      liste.push({ ...z, gruppe: g.name });
    }
  }
  return liste;
}


/** Eine Formzeile zum Bearbeiten aufklappen — an Ort und Stelle.
 *
 * Nicht als eigene Seite und nicht als Fenster darüber: man berichtigt
 * eine Form, weil man die daneben gerade gesehen hat. Nimmt man ihr den
 * Zusammenhang weg, muss man ihn sich merken.
 */
async function formBearbeiten(behaelter, lexem, f, zeile) {
  if (!zeile || zeile.dataset.offen) return;
  zeile.dataset.offen = '1';
  const feld = h('input', { type: 'text', lang: lexem.sprache, value: f.text,
                            style: 'width:100%' });
  const wahl = h('select', { style: 'width:100%' },
    h('option', { value: '', text: f.beschriftung + ' (unverändert)' }));
  const bearbeiten = h('tr', { class: 'formbearbeiten' },
    h('td', { colspan: '4' },
      h('div', { class: 'feldzeile' },
        h('label', { class: 'leise', text: 'Schreibung' }), feld),
      h('div', { class: 'feldzeile' },
        h('label', { class: 'leise', text: 'Was ist das?' }), wahl),
      h('p', { class: 'leise', style: 'margin:.4rem 0 .6rem' },
        'Beides setzt die Form auf ',
        h('b', { text: 'ungeprüft' }),
        ' zurück — was geändert wurde, ist nicht mehr das, was jemand '
        + 'freigegeben hat. Eine berichtigte ',
        h('b', { text: 'Schreibung' }),
        ' behält den Lernstand. Eine andere ',
        h('b', { text: 'Bestimmung' }),
        ' nicht: der Lernstand hängt an der Zelle, nicht an der Form. '
        + 'Die Zelle, in die du sie hängst, fängt von vorn an — und die '
        + 'alte bleibt stehen, falls du es zurücknimmst.'),
      h('div', { class: 'frage-werkzeuge', style: 'justify-content:flex-start' },
        h('button', { class: 'wichtig', onclick: () => sichern() }, 'Speichern'),
        h('button', { class: 'schlicht', onclick: () => schliessen() },
          'Abbrechen'))));
  zeile.insertAdjacentElement('afterend', bearbeiten);
  feld.focus();
  feld.select();

  const schliessen = () => { delete zeile.dataset.offen; bearbeiten.remove(); };

  // Die Bestimmungen kommen nach: sie brauchen mehrere Abrufe, und das
  // Textfeld soll nicht darauf warten — der Tippfehler ist der häufigere
  // Fall und steht sofort bereit.
  for (const z of await zellenDerWortart(lexem.sprache, lexem.wortart)) {
    // Gruppenname nur davor, wenn er etwas HINZUFÜGT. Bei einer
    // einzelligen Gruppe heißt die Zelle wie die Gruppe, und
    // »Nominativ Singular · Nominativ Singular« ist keine Auskunft,
    // sondern ein Echo.
    const name = z.beschriftung.includes(z.gruppe) || z.gruppe === z.beschriftung
      ? z.beschriftung : `${z.gruppe} · ${z.beschriftung}`;
    wahl.append(h('option', { value: JSON.stringify(z.merkmale), text: name }));
  }

  const sichern = () => tun(async () => {
    const daten = {};
    const text = feld.value.trim();
    if (!text) { meldung('Ohne Schreibung geht es nicht.'); return; }
    if (text !== f.text) daten.text = text;
    if (wahl.value) daten.merkmale = JSON.parse(wahl.value);
    if (!Object.keys(daten).length) { schliessen(); return; }
    await api.formTeilAendern(f.id, daten);
    zeichnenEinzeln(behaelter, lexem.id);
  });
}


/** Lemma und Lexemmerkmale berichtigen.
 *
 * Die Ablautreihe steht hier und nicht an einer Form — sie beschreibt
 * das Wort. Falsch eingetragen macht sie die ganze Klassenabfrage
 * falsch, und zwar unbemerkt: die Frage sieht richtig aus.
 */
async function kopfBearbeiten(behaelter, lexem) {
  const gruppen = await stammdaten.formgruppen(lexem.sprache);
  const moeglich = (gruppen.lexemmerkmale || {})[lexem.wortart] || {};
  const fragen = (gruppen.lexemmerkmale_fragen || {})[lexem.wortart] || {};
  // »genus« und »klasse« sind die Namen im Datenbestand, nicht die der
  // Sache. Die Sprache sagt in ihrer Frage, wie sie heißt — »Welche
  // Ablautreihe?« wird hier zu »Ablautreihe«.
  const benennen = (name) => {
    const frage = fragen[name];
    if (frage) return frage.replace(/^Welche[rs]?\s+/, '').replace(/\?$/, '');
    return { genus: 'Geschlecht', klasse: 'Klasse' }[name]
           || name[0].toUpperCase() + name.slice(1);
  };
  const lemma = h('input', { type: 'text', lang: lexem.sprache,
                             value: lexem.lemma, style: 'width:100%' });
  const kasten = h('div', { class: 'karte' },
    h('div', { class: 'feldzeile' },
      h('label', { class: 'leise', text: 'Lemma' }), lemma));

  const felder = {};
  for (const [name, werte] of Object.entries(moeglich)) {
    const wahl = h('select', { style: 'width:100%' },
      h('option', { value: '', text: '— nichts eingetragen —' }),
      werte.map((w) => h('option', { value: w, text: w })));
    wahl.value = (lexem.merkmale || {})[name] || '';
    felder[name] = wahl;
    kasten.append(h('div', { class: 'feldzeile' },
      h('label', { class: 'leise', text: benennen(name) }), wahl));
  }
  if (!Object.keys(moeglich).length) {
    kasten.append(h('p', { class: 'leise',
      text: `Für ${lexem.wortart_name} sind in dieser Sprache keine `
          + 'Lexemmerkmale vorgesehen.' }));
  }

  kasten.append(h('div', { class: 'frage-werkzeuge',
                           style: 'justify-content:flex-start' },
    h('button', {
      class: 'wichtig',
      onclick: () => tun(async () => {
        const merkmale = {};
        for (const [name, wahl] of Object.entries(felder)) {
          if (wahl.value) merkmale[name] = wahl.value;
        }
        await api.lexemAendern(lexem.id,
                               { lemma: lemma.value.trim() || lexem.lemma,
                                 merkmale });
        zeichnenEinzeln(behaelter, lexem.id);
      }),
    }, 'Speichern'),
    h('button', { class: 'schlicht', onclick: () => kasten.remove() },
      'Abbrechen')));

  const kopf = behaelter.querySelector('.wortkopf');
  if (!kopf || kopf.nextElementSibling?.classList.contains('kopfbearbeiten')) return;
  kasten.classList.add('kopfbearbeiten');
  kopf.insertAdjacentElement('afterend', kasten);
  lemma.focus();
}


/** Übersetzungen und Erklärsatz einer Bedeutung. */
function bedeutungBearbeiten(behaelter, lexem, b) {
  const kasten = h('div', { class: 'karte' });
  const liste = h('div', {});
  for (const u of b.uebersetzungen) {
    liste.append(h('div', { class: 'feldzeile' },
      h('span', {}, u.text,
        u.ist_haupt ? h('span', { class: 'marke', text: 'Haupt' }) : null),
      h('button', {
        class: 'schlicht gefahr',
        // Die letzte Übersetzung darf nicht weg: ohne sie gibt es keine
        // Abfrage mehr, und die Bedeutung stünde leer da.
        disabled: b.uebersetzungen.length < 2,
        title: b.uebersetzungen.length < 2
          ? 'Die letzte Übersetzung kann nicht weg — dann lieber die ganze '
            + 'Bedeutung löschen.' : '',
        onclick: () => tun(async () => {
          await api.uebersetzungLoeschen(u.id);
          zeichnenEinzeln(behaelter, lexem.id);
        }),
      }, 'Entfernen')));
  }
  const neuFeld = h('input', { type: 'text', style: 'width:100%',
                               placeholder: 'weitere Übersetzung' });
  const erklaerung = h('textarea', { rows: '2', style: 'width:100%',
                                     placeholder: 'Erklärsatz wie im Duden' });
  erklaerung.value = b.erklaerung || b.notiz || '';

  kasten.append(
    h('p', { class: 'leise', style: 'margin:0 0 .4rem', text: 'Übersetzungen' }),
    liste,
    h('div', { class: 'feldzeile' },
      h('label', { class: 'leise', text: 'Hinzufügen' }), neuFeld),
    h('div', { class: 'feldzeile' },
      h('label', { class: 'leise', text: 'Erklärung' }), erklaerung),
    h('div', { class: 'frage-werkzeuge', style: 'justify-content:flex-start' },
      h('button', {
        class: 'wichtig',
        onclick: () => tun(async () => {
          const text = neuFeld.value.trim();
          if (text) {
            await api.uebersetzungAnlegen(b.id, { text, quelle: 'manuell',
                                                  geprueft: true });
          }
          await api.erklaerungSetzen(b.id, erklaerung.value.trim());
          zeichnenEinzeln(behaelter, lexem.id);
        }),
      }, 'Speichern'),
      h('button', { class: 'schlicht', onclick: () => kasten.remove() },
        'Abbrechen')));
  return kasten;
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
