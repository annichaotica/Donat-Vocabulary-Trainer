/* Abtippen — sich mit den Wörtern vertraut machen.
 *
 * »Alle Vokabeln zeigen, deutsch französisch und abtippen, erfolgreich
 * abgetippt, dann nächste. Sie muss sich erst mal mit den Wörtern
 * vertraut machen.«
 *
 * Die Lösung steht die ganze Zeit da. Das ist nicht die abgeschwächte
 * Abfrage, es ist etwas anderes: die Hand über das Wort führen, bevor
 * man es abfragt. Darum hier auch keine Bewertung, keine Noten, keine
 * Termine — der Server schreibt bei dieser Betriebsart bewusst keinen
 * Lernstand.
 *
 * ZWEI ENTSCHEIDUNGEN, die den Ablauf bestimmen:
 *
 * Richtig abgetippt geht es VON SELBST weiter. Kein »Weiter«-Knopf.
 * Bei achtzig Wörtern ist jeder zusätzliche Klick achtzig Klicks, und
 * das war schon beim Markieren der unbekannten Wörter die Beschwerde.
 *
 * Falsch abgetippt passiert fast nichts: die Abweichung wird gezeigt,
 * das Feld bleibt stehen, man tippt weiter. Kein Fehlerzähler, keine
 * rote Bilanz. Wer eine Vorlage abschreibt, macht Vertipper, und die
 * sind hier keine Leistung, sondern Sand.
 */

import { api } from './api.js';
import { h, leeren, anfuegen, meldung, sprechen } from './hilfen.js';
import { stammdaten } from './stammdaten.js';
import { zustand } from './zustand.js';
import { zeichenleiste } from './tastatur.js';

const STAND = 'vokabeltrainer.abtippen';


/** Wo man stehengeblieben ist — je Sammlung.
 *
 * Im Browser und nicht auf dem Server: es ist ein Lesezeichen, kein
 * Lernstand. Auf einem anderen Gerät fängt man eben vorn an, und das
 * ist bei einer Liste, die man durchgeht, kein Verlust.
 */
function standLesen() {
  try { return JSON.parse(localStorage.getItem(STAND) || '{}'); }
  catch { return {}; }
}

function standMerken(sammlungId, stelle) {
  try {
    const alle = standLesen();
    alle[sammlungId] = stelle;
    localStorage.setItem(STAND, JSON.stringify(alle));
  } catch { /* privates Fenster — dann eben ohne Lesezeichen */ }
}


export async function zeichnen(behaelter) {
  const el = leeren(behaelter);
  el.append(h('h1', { text: 'Abtippen' }));

  if (!zustand.sammlungId) {
    el.append(h('p', { class: 'leise',
      text: 'Erst eine Sammlung wählen — oben in der Kopfzeile.' }));
    return;
  }

  let d;
  try {
    d = await api.abtippenReihe(zustand.sammlungId);
  } catch (fehler) {
    el.append(h('p', { class: 'leise', text: fehler.message }));
    return;
  }
  if (!d.karten.length) {
    el.append(h('p', { class: 'leise',
      text: d.ohne_uebersetzung
        ? `In »${d.sammlung}« hat noch kein Wort eine deutsche Seite. `
          + 'Ohne die gibt es nichts zum Abtippen.'
        : `In »${d.sammlung}« stehen noch keine Wörter.` }));
    return;
  }

  new Lauf(behaelter, d).start();
}


class Lauf {
  constructor(behaelter, d) {
    this.behaelter = behaelter;
    this.d = d;
    this.karten = d.karten;
    const gemerkt = standLesen()[d.sammlung_id] || 0;
    // Wer durch war, fängt wieder vorn an statt auf einer leeren Seite
    // zu landen.
    this.stelle = gemerkt < this.karten.length ? gemerkt : 0;
    this.geschafft = new Set();
    this.ergebnis = null;
    this.eingabe = '';
    // Wie oft bei DIESER Karte schon getippt wurde. Daran hängt, ob es
    // einen Weg daran vorbei gibt — siehe teilWerkzeuge.
    this.versuche = 0;
  }

  async start() {
    this.stimme = await stammdaten.stimme(this.d.sprache);
    this.sprachinfo = await stammdaten.sprache(this.d.sprache);
    this.zeichnen();
  }

  get karte() { return this.karten[this.stelle]; }

  zeichnen() {
    const el = leeren(this.behaelter);
    const k = this.karte;
    el.append(h('div', { class: 'abtippen-kopf' },
      h('span', { class: 'leise',
                  text: `${this.d.sammlung}${k.lektion
                    ? ' · ' + (k.lektion_nr ? `Lektion ${k.lektion_nr}` : k.lektion)
                    : ''}` }),
      h('span', { class: 'leise',
                  text: `${this.stelle + 1} von ${this.karten.length}` })));

    const balken = h('div', { class: 'abtippen-balken' },
      h('i', { style: `width:${((this.stelle) / this.karten.length) * 100}%` }));
    el.append(balken);

    // Hinweisen statt verstecken: beim Abschreiben prägt sich auch eine
    // falsche Schreibung ein, also soll man wissen, was noch niemand
    // angesehen hat. Weggelassen wird es nicht — der Trainer FRAGT
    // diese Wörter ja ab, und sie hier zu verschweigen wären zwei
    // Maßstäbe für dieselbe Vokabel.
    //
    // Nur auf der ersten Karte: er gilt für die ganze Runde, und über
    // achtzig Karten hinweg stünde er achtzigmal im Weg.
    if (this.d.ungeprueft && this.stelle === 0) {
      el.append(h('p', { class: 'hinweiskasten' },
        `${this.d.ungeprueft} von ${this.karten.length} Wörtern hat noch `
        + 'niemand durchgesehen. Sie kommen trotzdem dran — abgetippt wird '
        + 'aber, was dasteht, und eine falsche Schreibung prägt sich dabei '
        + 'genauso gut ein. Die betroffenen Karten sind gekennzeichnet. ',
        h('a', { href: '#/freigabe' }, 'Jetzt durchsehen')));
    }

    // Die Karte: oben die deutsche Seite, darunter — sichtbar — das
    // fremde Wort. Es ist eine Vorlage, kein Rätsel.
    const karte = h('div', { class: 'karte abtippkarte' },
      h('p', { class: 'abtipp-deutsch', lang: this.d.grundsprache,
               text: k.deutsch }),
      k.weitere.length > 1
        ? h('p', { class: 'leise', style: 'margin:.1rem 0 0',
                   text: 'auch: ' + k.weitere.slice(1).join(', ') })
        : null,
      h('p', { class: 'abtipp-fremd', lang: this.d.sprache, text: k.fremd }),
      k.ungeprueft
        ? h('p', { class: 'leise', style: 'margin:.4rem 0 0' },
            h('span', { class: 'marke warnung', text: 'ungeprüft' }),
            ' — diese Schreibung hat noch niemand bestätigt.')
        : null);
    if (this.stimme) {
      karte.append(h('div', { class: 'frage-werkzeuge' },
        h('button', { class: 'schlicht',
                      onclick: () => sprechen(k.fremd, this.stimme) },
          '🔊 Hören')));
    }
    el.append(karte);

    const feld = h('input', {
      type: 'text', class: 'abtippfeld', lang: this.d.sprache,
      placeholder: 'hier abtippen', autocomplete: 'off',
      autocapitalize: 'off', spellcheck: 'false',
      oninput: (e) => { this.eingabe = e.target.value; },
      // Die Eingabetaste ist bei einer Tippübung nicht die Abkürzung,
      // sondern der Weg: man tippt das Wort und drückt Enter, ohne die
      // Hände von der Tastatur zu nehmen. Ohne sie müsste man zwischen
      // jedem Wort zur Maus greifen — bei 36 Wörtern 36 mal.
      onkeydown: (e) => {
        if (e.key !== 'Enter') return;
        e.preventDefault();
        this.pruefen();
      },
    });
    feld.value = this.eingabe;
    this.feld = feld;
    el.append(feld);

    if (this.ergebnis && this.ergebnis.urteil !== 'richtig') {
      el.append(h('div', { class: 'rueckmeldung falsch' },
        h('div', { class: 'rueckmeldung-kopf' },
          h('span', { text: '✗' }),
          h('span', { text: 'Noch nicht gleich' })),
        h('p', { text: this.ergebnis.fehlertext || this.ergebnis.hinweis
                     || 'Schau noch einmal genau hin.' })));
    }

    // »Sie möchte gezwungen werden, die Wörter zu tippen, auch wenn sie
    // diese schon kennt.«
    //
    // Darum gibt es »Überspringen« nicht mehr von vornherein. Es
    // erscheint erst, wenn bei dieser Karte einmal getippt wurde und
    // es nicht gestimmt hat. Beides zusammen: wer die Vokabel kennt,
    // kommt nicht daran vorbei — wer an einem kaputten Eintrag
    // hängenbleibt, aber schon.
    //
    // Ein Ausweg muss bleiben. Eine Übung, aus der man nur durch
    // Schließen des Reiters herauskommt, ist keine Strenge, sondern
    // eine Falle; und es gibt Einträge mit Zeichen, die auf keiner
    // Tastatur liegen.
    el.append(h('div', { class: 'frage-werkzeuge' },
      h('button', { class: 'wichtig', onclick: () => this.pruefen() },
        'Prüfen'),
      this.versuche > 0
        ? h('button', { class: 'schlicht', onclick: () => this.springen(1) },
            'Überspringen')
        : null,
      this.stelle > 0
        ? h('button', { class: 'schlicht', onclick: () => this.springen(-1) },
            'Zurück')
        : null,
      h('button', { class: 'schlicht',
                    onclick: () => { location.hash = '#/uebersicht'; } },
        'Beenden')));

    // Die Zeichenleiste für Akzente — dieselbe wie in der Abfrage. Beim
    // Abtippen ist sie wichtiger als dort: hier soll ja gerade das
    // Zeichen genau stimmen.
    anfuegen(el, zeichenleiste(this.sprachinfo, () => this.feld,
                               (wert) => { this.eingabe = wert; }));

    el.append(h('p', { class: 'leise', style: 'margin-top:1rem',
      text: `${this.geschafft.size} in dieser Runde abgetippt. Das zählt `
          + 'nicht für die Abfrage — hier wird nichts bewertet und kein '
          + 'Termin gesetzt. Übersprungen wird nichts: jedes Wort will '
          + 'getippt werden, auch das, das du schon kennst.' }));

    feld.focus();
  }

  async pruefen() {
    if (!this.eingabe.trim()) { this.feld.focus(); return; }
    try {
      this.ergebnis = await api.abtippenPruefen({
        lexem_id: this.karte.lexem_id, eingabe: this.eingabe });
    } catch (fehler) { meldung(fehler.message); return; }

    this.versuche += 1;
    if (this.ergebnis.urteil === 'richtig') {
      this.geschafft.add(this.karte.lexem_id);
      // Kurz stehenlassen, damit man das Grün sieht, dann von selbst
      // weiter. Ein »Weiter«-Knopf wären bei achtzig Wörtern achtzig
      // Klicks.
      this.feld.classList.add('richtig');
      this.feld.disabled = true;
      setTimeout(() => this.springen(1), 380);
      return;
    }
    this.zeichnen();
  }

  springen(um) {
    const ziel = this.stelle + um;
    this.ergebnis = null;
    this.eingabe = '';
    this.versuche = 0;
    if (ziel >= this.karten.length) { this.fertig(); return; }
    this.stelle = Math.max(0, ziel);
    standMerken(this.d.sammlung_id, this.stelle);
    this.zeichnen();
  }

  fertig() {
    standMerken(this.d.sammlung_id, 0);
    const el = leeren(this.behaelter);
    el.append(h('h1', { text: 'Durch!' }));
    el.append(h('div', { class: 'karte' },
      h('p', { text: `Alle ${this.karten.length} Wörter aus `
                   + `»${this.d.sammlung}« durchgetippt, `
                   + `${this.geschafft.size} davon richtig.` }),
      h('p', { class: 'leise',
        text: 'Jetzt kennst du die Wörter vom Sehen und vom Schreiben. '
            + 'Die Abfrage prüft, ob sie auch ohne Vorlage sitzen — dort '
            + 'zählt es dann.' }),
      h('div', { class: 'frage-werkzeuge' },
        h('button', { class: 'wichtig',
                      onclick: () => { this.stelle = 0;
                                       this.geschafft = new Set();
                                       this.zeichnen(); } },
          'Noch einmal von vorn'),
        h('button', { onclick: () => { location.hash = '#/lernen'; } },
          'Zur Abfrage'),
        h('button', { class: 'schlicht',
                      onclick: () => { location.hash = '#/uebersicht'; } },
          'Zur Übersicht'))));
  }
}
