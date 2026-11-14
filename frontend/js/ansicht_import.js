/* Dateien einlesen.
 *
 * Es gibt zwei Arten von Dateien, und sie brauchen zwei Wege:
 *
 * **Merkmalsbündel (.json)** — das Format, in dem eine KI vollständige
 * Paradigmen liefert. Hier ist nichts zu raten, die Datei sagt alles selbst.
 *
 * **Tabellen (.csv, .tsv, Anki, Quizlet)** — Zeilen mit Spalten, und
 * niemand weiß vorher, welche Spalte was ist. Darum erst die Deutung
 * zeigen und berichtigen lassen.
 *
 * Beide Wege laufen IMMER zuerst als Probelauf. Ein Import, der ungefragt
 * tausend Zeilen in den Bestand kippt, ist schlimmer als keiner.
 *
 * Große Dateien werden in Päckchen geschickt. Ein einziger Aufruf mit
 * zehntausend Formen läuft in eine Zeitüberschreitung, und dann weiß
 * niemand, was angekommen ist. Der Import ist wiederholbar — ein zweiter
 * Lauf bessert nach, statt zu verdoppeln —, also ist das Stückeln
 * ungefährlich. */

import { api } from './api.js';
import { h, leeren, meldung } from './hilfen.js';
import { stammdaten } from './stammdaten.js';
import { zustand, merken } from './zustand.js';

/** Wie viele Einträge je Aufruf. Klein genug für die Zeitgrenze, groß
 *  genug, dass 1.300 Wörter nicht 1.300 Rundläufe brauchen. */
const PAECKCHEN = 100;

export async function zeichnen(behaelter) {
  const el = leeren(behaelter);
  const [sammlungen, sprachen] = await Promise.all([
    api.sammlungen(zustand.benutzerId), stammdaten.sprachen(),
  ]);
  el.append(h('h1', { text: 'Datei einlesen' }));
  if (!sammlungen.length) {
    el.append(h('div', { class: 'leer' },
      h('p', { text: 'Noch keine Sammlung vorhanden.' }),
      h('button', { class: 'wichtig', onclick: () => { location.hash = '#/uebersicht'; } },
        'Sammlung anlegen')));
    return;
  }

  const wahl = h('select', {},
    sammlungen.map((s) => {
      const sp = sprachen.find((x) => x.code === s.sprache);
      return h('option', {
        value: s.id, selected: s.id === zustand.sammlungId,
        text: `${s.name} (${sp ? sp.name : s.sprache})`,
      });
    }));
  const datei = h('input', {
    type: 'file', multiple: true,
    accept: '.json,.csv,.tsv,.txt,application/json,text/csv,text/plain',
  });

  el.append(h('div', { class: 'karte' },
    h('label', { class: 'feldname', text: 'In welche Sammlung?' }), wahl,
    h('label', { class: 'feldname', style: 'margin-top:.8rem',
                 text: 'Welche Dateien?' }), datei,
    h('p', { class: 'leise', style: 'margin:.6rem 0 0' },
      '.json mit Merkmalsbündeln (vollständige Paradigmen) oder .csv/.tsv ',
      'aus Anki, Quizlet oder einer Tabelle. Mehrere Dateien auf einmal ',
      'sind erlaubt — sie werden nacheinander gelesen.'),
    h('p', { class: 'leise', style: 'margin:.4rem 0 0' },
      h('strong', { text: 'Nichts wird sofort eingetragen.' }),
      ' Zuerst läuft ein Probelauf, und du siehst, was herauskäme.')));

  const bereich = h('div', {});
  el.append(bereich);

  datei.addEventListener('change', async () => {
    leeren(bereich);
    const dateien = [...datei.files];
    if (!dateien.length) return;
    for (const d of dateien) {
      try {
        await dateiBehandeln(bereich, Number(wahl.value), d);
      } catch (fehler) {
        bereich.append(h('div', { class: 'karte' },
          h('h2', { style: 'margin-top:0' }, d.name),
          h('p', { class: 'befund fehler', text: fehler.message || String(fehler) })));
      }
    }
  });
}

/* ------------------------------------------------- Datei einordnen */

async function dateiBehandeln(bereich, sammlungId, datei) {
  const text = await datei.text();
  const karte = h('div', { class: 'karte' },
    h('div', { class: 'freigabe-kopf' },
      h('h2', { style: 'margin:0', text: datei.name }),
      h('span', { class: 'marke', text: groesse(datei.size) })));
  bereich.append(karte);

  const gedeutet = deuten(text);
  if (gedeutet.art === 'fehler') {
    karte.append(h('p', { class: 'befund fehler', text: gedeutet.grund }));
    return;
  }
  if (gedeutet.art === 'tabelle') {
    karte.append(h('p', { class: 'leise',
      text: 'Als Tabelle gelesen — die Spaltendeutung steht unten und lässt '
          + 'sich berichtigen.' }));
    return tabelle(karte, sammlungId, text);
  }
  const teile = [];
  if (gedeutet.vokabeln.length) teile.push(`${gedeutet.vokabeln.length} Wörter`);
  if (gedeutet.uebungen.length) teile.push(`${gedeutet.uebungen.length} Übungen`);
  karte.append(h('p', { class: 'leise',
    text: `Merkmalsbündel erkannt: ${teile.join(', ') || 'nichts darin'}.` }));
  if (!teile.length) return;
  return buendel(karte, sammlungId, gedeutet);
}

function groesse(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} kB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

/** Was ist das für eine Datei?
 *
 *  Nicht an der Endung entschieden, sondern am Inhalt: eine .txt mit
 *  JSON darin ist JSON, und eine .json, die keine ist, soll das auch
 *  sagen und nicht an einer Spaltendeutung scheitern. */
export function deuten(text) {
  const anfang = text.trimStart()[0];
  if (anfang !== '[' && anfang !== '{') {
    return { art: 'tabelle' };
  }
  let daten;
  try {
    daten = JSON.parse(text);
  } catch (fehler) {
    return { art: 'fehler',
             grund: `Sieht nach JSON aus, lässt sich aber nicht lesen: ${fehler.message}` };
  }
  if (Array.isArray(daten)) {
    // Eine blanke Liste: Übungen erkennt man an "zielsprache", Wörter am
    // "lemma". Gemischt wäre mehrdeutig und kommt nicht vor.
    const uebung = daten.some((e) => e && (e.zielsprache || e.abschnitte));
    return uebung
      ? { art: 'buendel', vokabeln: [], uebungen: daten }
      : { art: 'buendel', vokabeln: daten, uebungen: [] };
  }
  const vokabeln = daten.vokabeln || daten.woerter || daten.eintraege || [];
  const uebungen = daten.uebungen || daten.saetze || daten.texte || [];
  if (!Array.isArray(vokabeln) || !Array.isArray(uebungen)) {
    return { art: 'fehler',
             grund: 'Erwartet wird eine Liste, oder ein Objekt mit den '
                  + 'Feldern "vokabeln" und/oder "uebungen".' };
  }
  return { art: 'buendel', vokabeln, uebungen };
}

/* --------------------------------------------- Merkmalsbündel (.json) */

async function buendel(karte, sammlungId, daten) {
  const fortschritt = h('div', { class: 'fortschritt' }, h('i', {}));
  const stand = h('p', { class: 'leise' });
  const ausgabe = h('div', {});
  const knoepfe = h('div', { class: 'freigabe-knoepfe' });
  karte.append(knoepfe, fortschritt, stand, ausgabe);
  fortschritt.hidden = true;

  const lauf = async (nurPruefen) => {
    knoepfe.querySelectorAll('button').forEach((b) => { b.disabled = true; });
    fortschritt.hidden = false;
    leeren(ausgabe);
    const berichte = [];
    try {
      if (daten.vokabeln.length) {
        berichte.push(['Wörter', await paeckchenweise(
          daten.vokabeln, nurPruefen, fortschritt, stand, 'Wörter',
          (teil) => api.vokabelnImportieren(sammlungId,
            { eintraege: teil, nur_pruefen: nurPruefen }))]);
      }
      if (daten.uebungen.length) {
        berichte.push(['Übungen', await paeckchenweise(
          daten.uebungen, nurPruefen, fortschritt, stand, 'Übungen',
          (teil) => api.uebungenImportieren(sammlungId,
            { eintraege: teil, nur_pruefen: nurPruefen }))]);
      }
    } finally {
      fortschritt.hidden = true;
      knoepfe.querySelectorAll('button').forEach((b) => { b.disabled = false; });
    }
    stand.textContent = nurPruefen
      ? 'Probelauf fertig — geschrieben wurde nichts.'
      : 'Eingetragen.';
    for (const [was, bericht] of berichte) {
      ausgabe.append(berichtZeigen(was, bericht));
    }
    if (!nurPruefen) {
      echtKnopf.remove();
      // Einmal am Ende, nicht hinter jedem Teilbericht: es ist ein Weg,
      // keine zwei.
      ausgabe.append(h('div', { class: 'freigabe-knoepfe' },
        h('button', {
          class: 'wichtig',
          onclick: () => { merken({ sammlungId }); location.hash = '#/freigabe'; },
        }, 'Weiter zur Freigabe'),
        h('button', {
          onclick: () => { merken({ sammlungId }); location.hash = '#/wortschatz'; },
        }, 'Zum Wortschatz')));
    }
  };

  const probeKnopf = h('button', { onclick: () => lauf(true) }, 'Probelauf');
  const echtKnopf = h('button', {
    class: 'wichtig',
    onclick: () => {
      const anzahl = daten.vokabeln.length + daten.uebungen.length;
      if (!window.confirm(
        `${anzahl} Einträge wirklich eintragen?\n\n`
        + 'Schon freigegebene Formen werden dabei nicht überschrieben — '
        + 'Abweichungen werden gemeldet.')) return;
      lauf(false);
    },
  }, 'Eintragen');
  knoepfe.append(probeKnopf, echtKnopf);
  // Der Probelauf läuft von selbst an: niemand will erst einen Knopf
  // suchen, um zu erfahren, ob die Datei überhaupt taugt.
  await lauf(true);
}

/** Schickt die Liste in Päckchen und fasst die Berichte zusammen. */
async function paeckchenweise(liste, nurPruefen, fortschritt, stand, was, senden) {
  const gesamt = {
    eingereicht: 0, angelegt: 0, aktualisiert: 0, abgelehnt: 0,
    formen_neu: 0, formen_geaendert: 0, aufgaben: 0,
    lektionen_neu: [], eintraege: [],
  };
  for (let i = 0; i < liste.length; i += PAECKCHEN) {
    const teil = liste.slice(i, i + PAECKCHEN);
    stand.textContent = `${nurPruefen ? 'Probelauf' : 'Eintragen'}: `
      + `${was} ${i + 1}–${Math.min(i + PAECKCHEN, liste.length)} `
      + `von ${liste.length}`;
    fortschritt.firstChild.style.width =
      `${Math.round((i / liste.length) * 100)}%`;
    const bericht = await senden(teil);
    for (const feld of ['eingereicht', 'angelegt', 'aktualisiert', 'abgelehnt',
                        'formen_neu', 'formen_geaendert', 'aufgaben']) {
      gesamt[feld] += bericht[feld] || 0;
    }
    for (const nr of bericht.lektionen_neu || []) {
      if (!gesamt.lektionen_neu.includes(nr)) gesamt.lektionen_neu.push(nr);
    }
    // Die laufende Nummer ist je Päckchen neu — auf die Gesamtliste
    // umrechnen, sonst steht fünfmal "Eintrag 3".
    for (const e of bericht.eintraege || []) {
      gesamt.eintraege.push({ ...e, nr: (e.nr || 0) + i });
    }
  }
  fortschritt.firstChild.style.width = '100%';
  return gesamt;
}

function berichtZeigen(was, bericht) {
  const kasten = h('div', { style: 'margin-top:1rem' });
  kasten.append(h('h3', { style: 'margin:.2rem 0 .5rem', text: was }));
  const zahlen = h('div', { class: 'zahlen' },
    zahl(bericht.eingereicht, 'eingereicht'),
    zahl(bericht.angelegt, 'neu', 'neu'),
    zahl(bericht.aktualisiert, 'nachgebessert'),
    bericht.abgelehnt ? zahl(bericht.abgelehnt, 'abgelehnt', 'verlernt') : null,
    bericht.formen_neu ? zahl(bericht.formen_neu, 'Formen') : null,
    bericht.aufgaben ? zahl(bericht.aufgaben, 'Aufgaben') : null);
  kasten.append(zahlen);
  if (bericht.lektionen_neu.length) {
    kasten.append(h('p', { class: 'leise',
      text: `Neue Lektionen: ${bericht.lektionen_neu.join(', ')}` }));
  }

  const abgelehnt = bericht.eintraege.filter((e) => e.zustand === 'abgelehnt');
  const mitBefund = bericht.eintraege.filter((e) => e.zustand !== 'abgelehnt');
  if (abgelehnt.length) {
    kasten.append(h('h4', { style: 'margin:.8rem 0 .3rem',
      text: `Abgelehnt (${abgelehnt.length})` }));
    for (const e of abgelehnt.slice(0, 30)) {
      kasten.append(h('p', { class: 'befund fehler' },
        h('strong', { text: `${e.nr}. ${e.lemma || e.titel || ''} ` }),
        (e.fehler || []).join('; ')));
    }
    if (abgelehnt.length > 30) {
      kasten.append(h('p', { class: 'leise',
        text: `… und ${abgelehnt.length - 30} weitere.` }));
    }
  }
  if (mitBefund.length) {
    kasten.append(h('details', { style: 'margin-top:.6rem' },
      h('summary', { text: `${mitBefund.length} Einträge mit Anmerkungen` }),
      h('div', { style: 'margin-top:.5rem' },
        mitBefund.slice(0, 50).map((e) => h('p', { class: 'befund hinweis' },
          h('strong', { text: `${e.nr}. ${e.lemma || e.titel || ''} ` }),
          (e.befunde || []).map((b) => (typeof b === 'string' ? b : b.text))
            .join(' · '),
          (e.abweichungen || []).length
            ? h('span', { class: 'leise',
                text: ` — ${e.abweichungen.length} freigegebene Stellen `
                    + 'blieben unangetastet.' })
            : null)),
        mitBefund.length > 50
          ? h('p', { class: 'leise', text: `… und ${mitBefund.length - 50} weitere.` })
          : null)));
  }
  return kasten;
}

function zahl(wert, beschriftung, art) {
  return h('div', { class: 'zahl' + (art ? ' ' + art : '') },
    h('b', { text: String(wert ?? 0) }), h('span', { text: beschriftung }));
}

/* ------------------------------------------------ Tabellen (.csv/.tsv) */

const ROLLENNAMEN = {
  lemma: 'Wort', uebersetzung: 'Bedeutung', wortart: 'Wortart',
  lektion: 'Lektion', notiz: 'Notiz', ignorieren: '— übergehen —',
};

async function tabelle(karte, sammlungId, text) {
  const doppelte = h('select', {},
    h('option', { value: 'ueberspringen', text: 'Doppelte übergehen' }),
    h('option', { value: 'ergaenzen', text: 'Doppelte ergänzen' }),
    h('option', { value: 'trotzdem', text: 'Doppelte trotzdem anlegen' }));
  const ausgabe = h('div', {});
  karte.append(ausgabe);
  let zuordnung = null;
  let hatKopfzeile = null;

  const zeigen = async () => {
    leeren(ausgabe);
    const v = await api.importVorschau(sammlungId,
      { text, zuordnung, hat_kopfzeile: hatKopfzeile });
    if (v.fehler) {
      ausgabe.append(h('p', { class: 'befund fehler', text: v.fehler }));
      return;
    }
    zuordnung = v.zuordnung;
    hatKopfzeile = v.hat_kopfzeile;

    ausgabe.append(h('div', { class: 'zahlen' },
      zahl(v.zeilen, 'Zeilen'), zahl(v.brauchbar, 'brauchbar', 'neu'),
      v.doppelt ? zahl(v.doppelt, 'schon da') : null));
    ausgabe.append(h('p', { class: 'leise',
      text: `Trennzeichen: ${v.trenner}. `
          + (hatKopfzeile ? 'Erste Zeile als Kopfzeile gelesen.'
                          : 'Keine Kopfzeile erkannt.') }));

    // Die Spaltendeutung ist geraten — sie muss berichtigbar sein, sonst
    // ist der Import bei jeder ungewöhnlichen Datei verloren.
    const felder = h('div', { class: 'merkmalsfelder' });
    for (let i = 0; i < v.spalten; i += 1) {
      const auswahl = h('select', {
        onchange: (e) => {
          zuordnung = { ...zuordnung, [String(i)]: e.target.value };
          zeigen();
        },
      }, v.moegliche_rollen.map((r) => h('option', {
        value: r, selected: (zuordnung[String(i)] || 'ignorieren') === r,
        text: ROLLENNAMEN[r] || r,
      })));
      felder.append(h('div', { class: 'merkmalsfeld' },
        h('label', { text: `Spalte ${i + 1}` }), auswahl));
    }
    ausgabe.append(felder);
    ausgabe.append(h('label', { class: 'kaestchen' },
      h('input', {
        type: 'checkbox', checked: hatKopfzeile,
        onchange: (e) => { hatKopfzeile = e.target.checked; zeigen(); },
      }), ' Erste Zeile ist eine Kopfzeile'));

    if (v.beispiel.length) {
      const koerper = h('tbody', {});
      for (const e of v.beispiel) {
        koerper.append(h('tr', {},
          h('td', { class: 'form', text: e.lemma }),
          h('td', { text: (e.uebersetzungen || []).join(', ') }),
          h('td', {}, e.schon_vorhanden
            ? h('span', { class: 'marke warnung', text: 'schon da' })
            : h('span', { class: 'marke', text: e.wortart || '' }))));
      }
      ausgabe.append(h('div', { class: 'tabellenrahmen' },
        h('table', { class: 'paradigma' }, koerper)));
    }
    if (v.uebersprungen.length) {
      ausgabe.append(h('details', {},
        h('summary', { text: `${v.uebersprungen.length} Zeilen übergangen` }),
        h('pre', { class: 'leise',
          style: 'white-space:pre-wrap;font-size:.85em',
          text: v.uebersprungen.join('\n') })));
    }

    // Die Wahl gehört VOR den Knopf: was gleich geschieht, soll man
    // gelesen haben, bevor man drückt.
    ausgabe.append(h('label', { class: 'feldname', style: 'margin-top:.8rem',
                                text: 'Was mit schon vorhandenen Wörtern?' }),
                   doppelte);
    ausgabe.append(h('div', { class: 'freigabe-knoepfe' },
      h('button', {
        class: 'wichtig',
        onclick: async () => {
          if (!window.confirm(`${v.brauchbar} Zeilen wirklich eintragen?`)) return;
          const bericht = await api.importUebernehmen(sammlungId, {
            text, zuordnung, hat_kopfzeile: hatKopfzeile,
            doppelte: doppelte.value,
          });
          meldung(`${bericht.angelegt ?? bericht.eingetragen ?? 0} eingetragen.`);
          leeren(ausgabe).append(
            h('p', { text: 'Eingetragen.' }),
            h('button', {
              onclick: () => { merken({ sammlungId }); location.hash = '#/wortschatz'; },
            }, 'Zum Wortschatz'));
        },
      }, 'Eintragen')));
  };

  await zeigen();
}
