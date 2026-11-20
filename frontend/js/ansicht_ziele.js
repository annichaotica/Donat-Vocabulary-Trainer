/* Lernziele und dynamische Lernblöcke.
 *
 * Ein Lernziel ist ein Ausschnitt des Bestands mit einem Termin. Der
 * Ausschnitt ist ausdrücklich nicht an eine Lektion gebunden — "alle Verben
 * im Passé composé über alle Lektionen" ist ein genauso gültiges Ziel wie
 * "Lektion 3 bis Freitag".
 *
 * Der Block wird daraus errechnet und nicht gespeichert: Fälliges zuerst,
 * dann Wackliges, dann so viel Neues, wie der Termin verlangt — verschränkt
 * gemischt, damit nicht sechs Formen desselben Verbs hintereinander kommen.
 */

import { api } from './api.js';
import { h, leeren, meldung, anfuegen, tun } from './hilfen.js';
import { stammdaten } from './stammdaten.js';
import { zustand, merken } from './zustand.js';

export async function zeichnen(behaelter) {
  const el = leeren(behaelter);
  const ziele = await api.lernziele(zustand.benutzerId);

  el.append(h('h1', { text: 'Lernziele' }));
  if (!ziele.length) {
    el.append(h('p', { class: 'leise',
      text: 'Noch kein Ziel. Ein Ziel ist ein Ausschnitt des Bestands mit '
          + 'einem Termin — der Trainer rechnet daraus aus, wie viel täglich '
          + 'dran sein muss, und stellt die Blöcke entsprechend zusammen.' }));
  }

  for (const z of ziele) {
    el.append(zielkarte(behaelter, z));
  }
  el.append(await teilNeuesZiel(behaelter));
}

function zielkarte(behaelter, z) {
  const f = z.fortschritt || {};
  const anteil = Math.round((f.anteil || 0) * 100);
  const eng = f.neu_taeglich_noetig && !f.schaffbar;

  return h('div', { class: 'karte' },
    h('div', { style: 'display:flex;justify-content:space-between;gap:1rem;flex-wrap:wrap' },
      h('strong', { text: z.name }),
      z.termin ? h('span', { class: 'marke' + (eng ? ' warnung' : ''),
                             text: f.lage || z.termin }) : null),
    h('p', { class: 'leise', style: 'margin:.2rem 0 .5rem', text: f.umfang_text || '' }),

    // Ein Ziel, das nichts trifft, stand bisher mit »0 von 0« da und
    // sagte kein Wort dazu. Man rätselt dann an der falschen Stelle —
    // bei den Wörtern, obwohl es an der Aufgabenart hing.
    (f.warum_leer || []).length
      ? h('div', { class: 'befund hinweis', style: 'margin:.4rem 0 .6rem' },
          h('p', { style: 'margin:0 0 .3rem' },
            h('b', { text: 'Dieses Ziel trifft keine einzige Aufgabe.' })),
          h('ul', { style: 'margin:0;padding-left:1.2rem' },
            f.warum_leer.map((t) => h('li', { text: t }))))
      : null,

    h('div', { class: 'zielbalken', title: `${f.geschafft} von ${f.gesamt}` },
      h('i', { style: `width:${anteil}%` })),
    h('p', { class: 'leise', style: 'margin:.3rem 0 0',
             text: `${f.geschafft ?? 0} von ${f.gesamt ?? 0} geschafft (${anteil} %)` }),

    h('div', { class: 'zahlen' },
      zahl(f.faellig, 'fällig', 'faellig'),
      zahl(f.verlernt, 'verlernt', 'verlernt'),
      zahl(f.neu, 'noch nie dran', 'neu'),
      f.neu_taeglich_noetig
        ? zahl(f.neu_taeglich_noetig, 'täglich neu nötig')
        : null),

    // Nicht bloß »das wird eng«, sondern woran es liegt — in den
    // Einheiten, in denen die Einstellungen stehen. Vorher verglich die
    // Prüfung gegen eine fest eingebaute 40, die mit niemandes
    // Einstellung etwas zu tun hatte.
    eng
      ? h('div', { class: 'befund hinweis', style: 'margin-top:.6rem' },
          h('p', { style: 'margin:0 0 .3rem' },
            h('b', { text: 'So reicht die Zeit nicht:' })),
          h('ul', { style: 'margin:0 0 .5rem;padding-left:1.2rem' },
            (f.huerden || []).map((t) => h('li', { text: t }))),
          h('p', { class: 'leise', style: 'margin:0 0 .5rem' },
            'Entweder den Termin verschieben, den Umfang kleiner '
            + 'schneiden — oder mehr am Tag vornehmen.'),
          f.pensum_noetig
            ? h('button', {
                onclick: async () => {
                  // Die Einstellung still zu ändern wäre falsch. Erst
                  // sagen, was es bedeutet, dann auf Knopfdruck tun.
                  const frage = `Pensum auf ${f.pensum_noetig} Fragen und `
                    + `${f.woerter_taeglich_noetig} neue Wörter am Tag `
                    + 'setzen? Das gilt für alle Sammlungen, nicht nur für '
                    + 'dieses Ziel.';
                  if (!confirm(frage)) return;
                  try {
                    await api.benutzerAendern(zustand.benutzerId, {
                      fragen_je_tag: f.pensum_noetig,
                      neu_je_sitzung: f.woerter_taeglich_noetig,
                    });
                    meldung('Pensum angepasst.');
                    zeichnen(behaelter);
                  } catch (fehler) { meldung(fehler.message, 'fehler'); }
                },
              }, `Pensum auf ${f.pensum_noetig} Fragen am Tag setzen`)
            : null)
      : null,

    h('div', { class: 'frage-werkzeuge' },
      h('button', {
        class: 'wichtig',
        disabled: !(f.gesamt),
        onclick: () => { merken({ lernzielId: z.id }); location.hash = `#/lernen/ziel/${z.id}`; },
      }, 'Block starten'),
      h('button', {
        class: 'schlicht',
        onclick: () => zeigeBlock(behaelter, z),
      }, 'Was käme dran?'),
      h('button', {
        class: 'schlicht',
        onclick: () => bearbeiten(behaelter, z),
      }, 'Bearbeiten'),
      h('button', {
        class: 'schlicht gefahr',
        onclick: () => tun(async () => {
            if (!confirm(`Lernziel „${z.name}" löschen? Der Lernstand bleibt.`)) return;
            await api.lernzielLoeschen(z.id);
            zeichnen(behaelter);
        }),
      }, 'Löschen')));
}

/* Ein Lernziel nachträglich ändern.
 *
 * Vor allem den Termin: dass eine Probe ansteht, weiß man oft erst
 * später, und bis hierher ließ sich keiner nachtragen. Entfernen geht
 * auch — ein leeres Feld heißt »ohne Termin«, und das Ziel steht dann
 * nicht mehr unter Zeitdruck.
 */
async function bearbeiten(behaelter, z) {
  const name = h('input', { type: 'text', value: z.name || '' });
  const termin = h('input', { type: 'date', value: z.termin || '' });
  const ziel = h('select', {},
    h('option', { value: 'reif', text: 'sitzt dauerhaft' }),
    h('option', { value: 'einmal_richtig', text: 'einmal gekonnt' }));
  ziel.value = z.ziel || 'reif';
  const aktiv = h('input', { type: 'checkbox', checked: z.aktiv !== 0 });

  /* Der Umfang war bisher nur beim Anlegen einzustellen.
   *
   * »Bei den Lernzielen sollte man auch einstellen können, welche Tempi
   * und welche Abfragen dort erfolgen.« — Das Formular zum Anlegen
   * konnte das längst, das zum Bearbeiten nicht; wer sich beim Anlegen
   * vertat oder weiterkam, musste das Ziel wegwerfen und neu anlegen,
   * und damit den Lernstandsbezug des Blocks verlieren.
   *
   * Die Felder hängen an der Sammlung des Ziels: ohne sie gibt es keine
   * Lektionen und keine Formgruppen zu zeigen. Umgekehrt bleibt ein
   * Ziel über alle Sammlungen ohne diese Felder — dort wäre jede
   * Lektionsliste eine Lüge.
   */
  const umfang = z.umfang || {};
  const sammlungId = (umfang.sammlungen || [])[0] || null;
  const felder = {};
  const umfangFelder = h('div', {});
  if (sammlungId) {
    try {
      const [lektionen, einstellungen] = await Promise.all([
        api.lektionen(sammlungId), api.sammlungEinstellungen(sammlungId),
      ]);
      const [gruppen, typen, wortarten] = await Promise.all([
        api.formgruppen(einstellungen.sprache), stammdaten.aufgabentypen(),
        api.wortarten(sammlungId),
      ]);
      felder.lektionen = mehrfachwahl(
        'Lektionen', lektionen.map((l) => [String(l.id), l.name]),
        'Nichts gewählt heißt: alle.', umfang.lektionen || []);
      felder.formgruppen = mehrfachwahl(
        'Zeiten und Tabellen',
        Object.values(gruppen.wortarten).flat().map((g) => [g.kennung, g.name]),
        'Nichts gewählt heißt: alle, die in der Sammlung eingeschaltet sind.',
        umfang.formgruppen || []);
      felder.typen = mehrfachwahl(
        'Abfragearten',
        Object.entries(typen.typen).map(([k, t]) => [k, t.name]),
        'Nichts gewählt heißt: alle.', umfang.typen || []);
      // »Verben lernen, bestimmte Worttypen, k.A. Adjektive oder so« —
      // der Umfang konnte Wortarten längst, nur fragte kein Formular
      // danach. Für ein Ziel wie »Verben bis Freitag« braucht es das.
      felder.wortarten = mehrfachwahl(
        'Wortarten', wortarten.map((w) => [w.wortart, `${wortartName(w.wortart)} · ${w.aufgaben}`]),
        'Nichts gewählt heißt: alle.', umfang.wortarten || []);
      for (const f of Object.values(felder)) {
        if (f.element) umfangFelder.append(f.element);
      }
    } catch (fehler) {
      umfangFelder.append(h('p', { class: 'leise',
        text: `Der Umfang ließ sich nicht laden: ${fehler.message}` }));
    }
  }

  /** Der Umfang, wie er gespeichert werden soll.
   *
   * Die Sammlung wird mitgeschrieben, auch wenn sie hier nicht
   * änderbar ist — `umfang` wird als Ganzes ersetzt, ein Auslassen
   * würde sie löschen. */
  function umfangLesen() {
    const neu = {};
    if (umfang.sammlungen) neu.sammlungen = umfang.sammlungen;
    if (umfang.lexeme) neu.lexeme = umfang.lexeme;
    for (const [schluessel, feld] of Object.entries(felder)) {
      const wahl = feld.gewaehlt();
      if (!wahl.length) continue;
      neu[schluessel] = schluessel === 'lektionen' ? wahl.map(Number) : wahl;
    }
    return neu;
  }

  const kasten = h('div', { class: 'karte' },
    h('h2', { text: 'Lernziel bearbeiten' }),
    h('label', { class: 'feldname', text: 'Name' }), name,
    h('label', { class: 'feldname', style: 'margin-top:.6rem',
                 text: 'Termin' }), termin,
    h('p', { class: 'leise', style: 'margin:.2rem 0 .6rem',
             text: 'Leer heißt: ohne Termin. Mit Termin rechnet der '
                 + 'Trainer aus, wie viel täglich nötig wäre — und sagt '
                 + 'dir, wenn dein Pensum dafür nicht reicht.' }),
    h('label', { class: 'feldname', text: 'Geschafft ist es, wenn …' }), ziel,
    h('label', { class: 'schalter', style: 'margin-top:.6rem' }, aktiv,
      h('span', { class: 'schalter-text' }, h('b', { text: 'Aktiv' }))),
    umfangFelder,
    h('div', { class: 'frage-werkzeuge', style: 'margin-top:.8rem' },
      h('button', {
        class: 'wichtig',
        onclick: async () => {
          try {
            await api.lernzielAendern(z.id, {
              name: name.value.trim() || z.name,
              // Leerer String heißt ausdrücklich »entfernen«; null
              // hieße »nicht genannt« und ließe den Termin stehen.
              termin: termin.value || '',
              ziel: ziel.value,
              aktiv: aktiv.checked,
              umfang: umfangLesen(),
            });
            meldung('Gespeichert.');
            zeichnen(behaelter);
          } catch (fehler) { meldung(fehler.message, 'fehler'); }
        },
      }, 'Speichern'),
      h('button', { onclick: () => zeichnen(behaelter) }, 'Abbrechen')));
  leeren(behaelter).append(kasten);
}

function wortartName(w) {
  return { verb: 'Verben', substantiv: 'Substantive', adjektiv: 'Adjektive',
           adverb: 'Adverbien', pronomen: 'Pronomen', numerale: 'Zahlwörter',
           konjunktion: 'Konjunktionen', praeposition: 'Präpositionen',
           artikel: 'Artikel', wendung: 'Wendungen',
           sonstiges: 'Sonstiges' }[w] || w;
}

function zahl(wert, beschriftung, art) {
  if (wert === null || wert === undefined) return null;
  return h('div', { class: 'zahl' + (art ? ' ' + art : '') },
    h('b', { text: String(wert) }), h('span', { text: beschriftung }));
}

/** Zeigt den errechneten Block samt Begründung des Zuschnitts. */
async function zeigeBlock(behaelter, z, block = null) {
  if (!block) {
    try {
      block = await api.lernblock(z.id, zustand.benutzerId, 20);
    } catch (fehler) { meldung(fehler.message); return; }
  }

  const el = leeren(behaelter);
  el.append(h('h1', { text: z.name }));
  el.append(h('div', { class: 'karte' },
    h('p', { style: 'margin:0', text: block.begruendung }),
    block.wurf
      ? h('p', { class: 'leise', style: 'margin:.4rem 0 0',
                 text: `${block.wurf}× gewürfelt. Der Zuschnitt bleibt `
                     + 'derselbe — gewürfelt wird nur, welche Wörter es '
                     + 'innerhalb jeder Gruppe werden.' })
      : null));

  if (block.anzahl) {
    const liste = h('div', { class: 'liste' });
    for (const a of block.aufgaben) {
      liste.append(h('div', { class: 'eintrag' },
        h('span', { class: 'lemma', text: a.lemma }),
        h('span', { class: 'bedeutung', text: a.typ.replace(/_/g, ' ') }),
        h('span', { class: 'marke' + (a.herkunft === 'wacklig' ? ' warnung' : ''),
                    text: { faellig: 'fällig', wacklig: 'wacklig',
                            neu: 'neu' }[a.herkunft] })));
    }
    el.append(liste);
  }
  const wuerfel = h('button', {
    onclick: async () => {
      wuerfel.disabled = true;
      try {
        // Der Wurf wird AM ZIEL vermerkt; die Abfrage rechnet durch
        // dieselbe Funktion und liefert danach genau diesen Block.
        const neuer = await api.lernblockWuerfeln(z.id, zustand.benutzerId, 20);
        zeigeBlock(behaelter, z, neuer);
      } catch (fehler) {
        meldung(fehler.message, 'fehler');
        wuerfel.disabled = false;
      }
    },
  }, '🎲 Neu würfeln');

  el.append(h('div', { class: 'frage-werkzeuge' },
    block.anzahl ? h('button', {
      class: 'wichtig',
      onclick: () => { merken({ lernzielId: z.id }); location.hash = `#/lernen/ziel/${z.id}`; },
    }, 'Los') : null,
    block.anzahl ? wuerfel : null,
    // »Beim Block kann ich immer noch nichts ändern, also z.B. ein
    // Lernziel ohne Datum nicht mit Datum versehen.« — Bearbeiten gab
    // es, aber eine Ansicht weiter oben. Wer hier steht, will von
    // hier aus ändern und nicht erst zurückgehen und suchen.
    h('button', { class: 'schlicht', onclick: () => bearbeiten(behaelter, z) },
      'Bearbeiten'),
    h('button', { onclick: () => zeichnen(behaelter) }, 'Zurück')));
}

/* ----------------------------------------------------------- Neues Ziel */

async function teilNeuesZiel(behaelter) {
  const sammlungen = await api.sammlungen(zustand.benutzerId);
  const kasten = h('details', { class: 'karte', style: 'margin-top:1.5rem' },
    h('summary', { text: '+ Neues Lernziel' }));
  const koerper = h('div', { style: 'display:grid;gap:.7rem;margin-top:.8rem' });
  kasten.append(koerper);

  const name = h('input', { type: 'text', placeholder: 'z.B. Lektion 3 bis Freitag' });
  const termin = h('input', { type: 'date' });
  const ziel = h('select', {},
    h('option', { value: 'reif', text: 'sitzt dauerhaft (empfohlen)' }),
    h('option', { value: 'einmal_richtig', text: 'wenigstens einmal gekonnt' }));

  const sammlungWahl = h('select', {},
    h('option', { value: '', text: 'alle zugänglichen Sammlungen' }),
    sammlungen.map((s) => h('option', { value: String(s.id), text: s.name })));

  const umfangFelder = h('div', { style: 'display:grid;gap:.7rem' });

  const umfangBauen = async () => {
    leeren(umfangFelder);
    const sammlungId = sammlungWahl.value ? Number(sammlungWahl.value) : null;
    if (!sammlungId) {
      umfangFelder.append(h('p', { class: 'leise', style: 'margin:0',
        text: 'Ohne Sammlung umfasst das Ziel alles — auch das ist erlaubt, '
            + 'etwa für „alles, was fällig ist".' }));
      return;
    }
    const [lektionen, einstellungen] = await Promise.all([
      api.lektionen(sammlungId), api.sammlungEinstellungen(sammlungId),
    ]);
    const gruppen = await api.formgruppen(einstellungen.sprache);
    const typen = await stammdaten.aufgabentypen();

    umfangFelder._lektionen = mehrfachwahl(
      'Lektionen', lektionen.map((l) => [String(l.id), l.name]),
      'Mehrere wählbar — ein Ziel darf über Lektionen greifen.');
    const alleGruppen = Object.values(gruppen.wortarten).flat();
    umfangFelder._formgruppen = mehrfachwahl(
      'Formgruppen', alleGruppen.map((g) => [g.kennung, g.kurz]),
      'Nur Formaufgaben dieser Zeiten. Leer heißt: alle.');
    umfangFelder._wortarten = mehrfachwahl(
      'Wortarten',
      (await api.wortarten(sammlungId)).map(
        (w) => [w.wortart, `${wortartName(w.wortart)} · ${w.aufgaben}`]),
      'Nichts gewählt heißt: alle.');
    umfangFelder._typen = mehrfachwahl(
      'Aufgabentypen', Object.entries(typen.typen).map(([k, t]) => [k, t.name]),
      'Leer heißt: alle.');
    anfuegen(umfangFelder, umfangFelder._lektionen.element,
             umfangFelder._formgruppen.element, umfangFelder._wortarten.element,
             umfangFelder._typen.element);
  };
  sammlungWahl.addEventListener('change', umfangBauen);

  anfuegen(koerper,
    beschriftet('Name', name),
    beschriftet('Termin (freigestellt)', termin),
    beschriftet('Was gilt als geschafft', ziel),
    beschriftet('Sammlung', sammlungWahl),
    umfangFelder,
    h('button', {
      class: 'wichtig',
      onclick: async () => {
        if (!name.value.trim()) { meldung('Der Name fehlt.'); return; }
        const umfang = {};
        if (sammlungWahl.value) umfang.sammlungen = [Number(sammlungWahl.value)];
        for (const [feld, schluessel] of [['_lektionen', 'lektionen'],
                                          ['_formgruppen', 'formgruppen'],
                                          ['_wortarten', 'wortarten'],
                                          ['_typen', 'typen']]) {
          const wahl = umfangFelder[feld]?.gewaehlt();
          if (wahl?.length) {
            umfang[schluessel] = schluessel === 'lektionen'
              ? wahl.map(Number) : wahl;
          }
        }
        try {
          await api.lernzielAnlegen({
            benutzer_id: zustand.benutzerId,
            name: name.value.trim(),
            umfang,
            termin: termin.value || null,
            ziel: ziel.value,
          });
          meldung('Ziel angelegt.');
          zeichnen(behaelter);
        } catch (fehler) { meldung(fehler.message); }
      },
    }, 'Anlegen'));

  await umfangBauen();
  return kasten;
}

function beschriftet(text, feld) {
  return h('div', {}, h('label', { class: 'leise', text }), feld);
}

/** Mehrfachauswahl als Knopfreihe — auf dem Handy brauchbarer als ein
 *  Mehrfach-Auswahlfeld, das man dort kaum bedienen kann. */
function mehrfachwahl(titel, eintraege, hinweis, vorgewaehlt = []) {
  // `vorgewaehlt` gibt es, seit sich ein Lernziel bearbeiten lässt: beim
  // Anlegen ist nichts gewählt, beim Bearbeiten muss dastehen, was gilt.
  // Ohne das sähe ein Ziel mit Umfang beim Öffnen aus wie eines ohne —
  // und Speichern hätte ihn stillschweigend gelöscht.
  const gewaehlt = new Set(vorgewaehlt.map(String));
  const reihe = h('div', { class: 'gruppenwahl' });
  for (const [wert, beschriftung] of eintraege) {
    const knopf = h('button', {
      type: 'button',
      class: gewaehlt.has(String(wert)) ? 'aktiv' : '',
      onclick: () => {
        if (gewaehlt.has(wert)) gewaehlt.delete(wert); else gewaehlt.add(wert);
        knopf.className = gewaehlt.has(wert) ? 'aktiv' : '';
      },
    }, beschriftung);
    reihe.append(knopf);
  }
  const element = eintraege.length
    ? h('div', {}, h('label', { class: 'leise', text: titel }), reihe,
        h('p', { class: 'leise', style: 'margin:.2rem 0 0;font-size:.85em',
                 text: hinweis }))
    : null;
  return { element, gewaehlt: () => [...gewaehlt] };
}
