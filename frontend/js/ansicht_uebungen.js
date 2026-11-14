/* Sätze und Texte üben.
 *
 * Verwandt mit der Vokabelabfrage, aber an drei Stellen bewusst anders —
 * und jede davon hat einen Grund:
 *
 * **Ein Feld, in das mehrere Zeilen passen.** Ein Satz ist kein Wort. Ein
 * einzeiliges Feld, in dem der Anfang nach links wegrutscht, macht das
 * Nachlesen der eigenen Antwort unmöglich.
 *
 * **Die Rückmeldung nennt die Wörter.** "Falsch" ist bei einem Satz keine
 * Auskunft; "σπίτι statt θέατρο, στο fehlt" schon.
 *
 * **Bei langen Texten entscheidet der Mensch.** Der Vergleich läuft und
 * wird gezeigt, zählt aber nicht: eine freie Übersetzung eines Absatzes
 * stimmt selten wörtlich, und wer sie deshalb als falsch wertet, erzieht
 * zum Auswendiglernen der Musterlösung.
 */

import { api } from './api.js';
import { anfuegen, h, leeren, meldung, sprechen, stimmeDa } from './hilfen.js';
import { stammdaten } from './stammdaten.js';
import { zeichenleiste } from './tastatur.js';
import { zustand, merken } from './zustand.js';

const NOTEN = [
  { note: 1, name: 'Nochmal', hinweis: 'Saß nicht' },
  { note: 2, name: 'Schwer', hinweis: 'Mit Mühe' },
  { note: 3, name: 'Gut', hinweis: 'Saß' },
  { note: 4, name: 'Leicht', hinweis: 'Sofort da' },
];

const SELBST = [
  { urteil: 'richtig', name: 'Richtig', hinweis: 'Sinn getroffen' },
  { urteil: 'fast', name: 'Fast', hinweis: 'Kleinigkeiten daneben' },
  { urteil: 'falsch', name: 'Falsch', hinweis: 'Noch nicht' },
];

export class Uebungssitzung {
  constructor(behaelter, optionen = {}) {
    this.behaelter = behaelter;
    this.optionen = optionen;
    this.aufgabe = null;
    this.ergebnis = null;
    this.phase = 'frage';            // frage | rueckmeldung
    this.feld = null;
    this.eingabeWert = '';
    this.laeuft = false;
    this.abgebrochen = false;
    this.wertungOffen = false;
    this.gezaehlt = { richtig: 0, fast: 0, falsch: 0 };
    this.aufgedeckt = false;
    // Die Wertung der laufenden Aufgabe. MUSS bei jeder neuen Aufgabe
    // zurück auf null — siehe naechste().
    this.gewertet = null;
    this._taste = (e) => this.aufTaste(e);
    document.addEventListener('keydown', this._taste);
  }

  beenden() {
    this.abgebrochen = true;
    document.removeEventListener('keydown', this._taste);
  }

  async start() {
    this.zeichneLade();
    await this.naechste();
  }

  async naechste() {
    this.phase = 'frage';
    this.ergebnis = null;
    this.eingabeWert = '';
    this.wertungOffen = false;
    this.aufgedeckt = false;
    // Blieb stehen und wirkte in die nächste Aufgabe hinein: nach der
    // ersten Wertung zeigte jeder lange Text statt »Wie war es?« die
    // Wertung der VORIGEN Aufgabe, und »Weiter« übersprang ihn
    // ungewertet. Derselbe Fehlertyp wie der doppelte Tastenbehandler
    // und das überholte <main>.
    this.gewertet = null;
    let liste;
    try {
      liste = await api.uebungNaechste({
        benutzer_id: zustand.benutzerId,
        sammlung_id: this.optionen.sammlungId || null,
        lektion_nr: this.optionen.lektionNr ?? null,
        bis_lektion: this.optionen.bisLektion ?? null,
        richtung: this.optionen.richtung || null,
        nur: this.optionen.nur || null,
        anzahl: 1,
      });
    } catch (fehler) {
      this.zeichneFehler(fehler.message);
      return;
    }
    if (this.abgebrochen) return;
    if (!liste.length) { await this.zeichneFertig(); return; }
    this.aufgabe = liste[0];
    // Das echte Sprachprofil holen, nicht eines erfinden: ob eine
    // Zeichenleiste nützt und ob ein Layout lohnt, weiß nur das Profil.
    // Erfunden stand da "Für de lohnt ein eigenes Tastaturlayout".
    try {
      this.antwortsprache = await stammdaten.sprache(this.aufgabe.antwort_sprache);
    } catch { this.antwortsprache = null; }
    if (this.abgebrochen) return;
    this.zeichnen();
    this.fokussieren();
  }

  /* ----------------------------------------------------------- Zeichnen */

  zeichneLade() {
    leeren(this.behaelter).append(h('p', { class: 'leise', text: 'Einen Moment…' }));
  }

  zeichneFehler(text) {
    leeren(this.behaelter).append(h('div', { class: 'karte' },
      h('h2', { style: 'margin-top:0', text: 'Das ging schief' }),
      h('p', { text }),
      h('button', { onclick: () => this.naechste() }, 'Nochmal')));
  }

  async zeichneFertig() {
    const el = leeren(this.behaelter);
    let stand = {};
    try {
      stand = await api.uebungStand(zustand.benutzerId, this.optionen.sammlungId);
    } catch { /* nichts */ }
    const nichts = !this.gezaehlt.richtig && !this.gezaehlt.fast
                 && !this.gezaehlt.falsch;
    el.append(h('div', { class: 'karte' },
      h('h2', { style: 'margin-top:0',
                text: nichts ? 'Hier wartet gerade nichts' : 'Geschafft' }),
      nichts && stand.ungeprueft
        ? h('p', {}, `${stand.ungeprueft} Übungsaufgaben sind noch nicht `
                   + 'freigegeben. Bis dahin werden sie nicht abgefragt.')
        : null,
      nichts && !stand.ungeprueft && !stand.gesamt
        ? h('p', { class: 'leise',
                   text: 'In dieser Sammlung gibt es noch keine Übungssätze.' })
        : null,
      !nichts
        ? h('div', { class: 'zahlen' },
            h('div', { class: 'zahl' },
              h('b', { text: String(this.gezaehlt.richtig) }),
              h('span', { text: 'richtig' })),
            h('div', { class: 'zahl' },
              h('b', { text: String(this.gezaehlt.fast) }),
              h('span', { text: 'fast' })),
            h('div', { class: 'zahl' },
              h('b', { text: String(this.gezaehlt.falsch) }),
              h('span', { text: 'falsch' })))
        : null,
      h('div', { class: 'frage-werkzeuge', style: 'justify-content:flex-start' },
        nichts && stand.ungeprueft
          ? h('button', {
              class: 'wichtig',
              onclick: () => { location.hash = '#/freigabe'; },
            }, 'Zur Freigabe')
          : null,
        h('button', { onclick: () => { location.hash = '#/uebersicht'; } },
          'Zur Übersicht'))));
  }

  zeichnen() {
    const a = this.aufgabe;
    const fertig = this.phase === 'rueckmeldung';
    const el = leeren(this.behaelter);
    const kasten = h('div', { class: 'abfrage' });

    kasten.append(h('div', { class: 'aufgabentyp' },
      h('span', { class: 'punkt' }),
      h('span', { text: a.aufgabe_text }),
      a.lektion_nr !== null && a.lektion_nr !== undefined
        ? h('span', { class: 'marke', text: `Lektion ${a.lektion_nr}` })
        : null,
      a.uebungstyp !== 'satz'
        ? h('span', { class: 'marke', text: a.uebungstyp })
        : null,
      a.abschnitte_gesamt > 1
        ? h('span', { class: 'marke',
                      text: `Teil ${a.abschnitt} von ${a.abschnitte_gesamt}` })
        : null));

    const frage = h('div', { class: 'frage' },
      h('p', { class: 'satzfrage', lang: a.frage_sprache, text: a.frage_text }));
    if (a.vorlesen && stimmeDa(a.frage_sprache)) {
      frage.append(h('div', { class: 'frage-werkzeuge' },
        h('button', {
          class: 'schlicht',
          onclick: () => sprechen(a.vorlesen, a.frage_sprache),
        }, '🔊 Hören')));
    }
    kasten.append(frage);
    kasten.append(this.teilEingabe(fertig));
    if (fertig) {
      kasten.append(this.teilRueckmeldung());
      anfuegen(kasten, this.teilWertung());
    }
    anfuegen(kasten, this.teilEingriffe(fertig));
    el.append(kasten);
  }

  teilEingabe(fertig) {
    const a = this.aufgabe;
    const kasten = h('div', {});
    // Mehrzeilig: ein Satz passt nicht in ein einzeiliges Feld, ohne dass
    // der Anfang nach links wegrutscht.
    const feld = h('textarea', {
      class: 'satzfeld' + (fertig && this.ergebnis
        ? ' ' + this.ergebnis.urteil.urteil : ''),
      lang: a.antwort_sprache,
      rows: a.uebungstyp === 'satz' ? '2' : '4',
      placeholder: 'Übersetzung',
      disabled: fertig,
      oninput: (e) => { this.eingabeWert = e.target.value; },
    });
    feld.value = this.eingabeWert;
    this.feld = feld;
    kasten.append(h('div', { class: 'satzeingabe' }, feld));
    if (!fertig) {
      kasten.append(h('div', { class: 'frage-werkzeuge',
                               style: 'justify-content:flex-start' },
        h('button', { class: 'wichtig', onclick: () => this.absenden() },
          'Prüfen')));
      if (this.antwortsprache) {
        const leiste = zeichenleiste(this.antwortsprache, () => this.feld,
                                     (wert) => { this.eingabeWert = wert; });
        if (leiste) kasten.append(leiste);
      }
    }
    return kasten;
  }

  teilRueckmeldung() {
    const e = this.ergebnis;
    const u = e.urteil;
    const titel = { richtig: 'Richtig', fast: 'Fast richtig',
                    falsch: 'Noch nicht' }[u.urteil];
    const kasten = h('div', { class: 'rueckmeldung ' + u.urteil });
    kasten.append(h('div', { class: 'rueckmeldung-kopf' },
      h('span', { text: { richtig: '✓', fast: '≈', falsch: '✗' }[u.urteil] }),
      h('span', { text: titel }),
      u.woerter_gesamt
        ? h('span', { class: 'leise',
                      text: `— ${u.woerter_richtig} von ${u.woerter_gesamt} Wörtern` })
        : null,
      !e.zaehlt ? h('span', { class: 'marke', text: 'zählt nicht' }) : null));

    // Wort für Wort: das ist bei einem Satz die eigentliche Auskunft.
    if (u.stellen && u.stellen.length) {
      const liste = h('ul', { class: 'stellen' });
      for (const s of u.stellen.slice(0, 12)) {
        if (s.art === 'anders') {
          liste.append(h('li', {},
            h('s', { lang: this.aufgabe.antwort_sprache, text: s.bekommen }),
            ' → ',
            h('b', { lang: this.aufgabe.antwort_sprache, text: s.erwartet })));
        } else if (s.art === 'fehlt') {
          liste.append(h('li', {}, 'fehlt: ',
            h('b', { lang: this.aufgabe.antwort_sprache, text: s.erwartet })));
        } else {
          liste.append(h('li', {}, 'zu viel: ',
            h('s', { lang: this.aufgabe.antwort_sprache, text: s.bekommen })));
        }
      }
      kasten.append(liste);
    } else if (u.hinweis) {
      kasten.append(h('p', { text: u.hinweis }));
    }

    const loesung = e.loesung || {};
    if (loesung.haupt) {
      kasten.append(h('p', { class: 'leise', style: 'margin-top:.6rem',
                             text: 'Gemeint war:' }));
      kasten.append(h('p', { class: 'loesung',
                             lang: this.aufgabe.antwort_sprache,
                             text: loesung.haupt }));
    }
    if ((loesung.weitere || []).length) {
      kasten.append(h('p', { class: 'leise',
        text: 'Ebenso richtig: ' + loesung.weitere.join(' · ') }));
    }
    // Die andere Seite dazu — wer die Lösung liest, will den Satz ganz
    // sehen und nicht nur die Hälfte, die er suchen sollte.
    if (loesung.gegenstueck) {
      kasten.append(h('p', { class: 'leise satzgegenstueck',
                             lang: this.aufgabe.frage_sprache,
                             text: loesung.gegenstueck }));
    }
    return kasten;
  }

  teilWertung() {
    const e = this.ergebnis;
    const vorschau = this.aufgabe.vorschau || {};
    const kasten = h('div', { class: 'wertung' });

    // Beim langen Text schätzt der Mensch selbst ein: eine freie
    // Übersetzung stimmt selten wörtlich mit der Referenz überein.
    if (e.selbsteinschaetzung && !this.gewertet) {
      kasten.append(h('div', { class: 'wertung-kopf' },
        h('b', { text: 'Wie war es?' })));
      kasten.append(h('p', { class: 'wertung-grund',
        text: 'Bei längeren Texten passt ein wörtlicher Vergleich selten — '
            + 'darum entscheidest du. Der Vergleich oben ist nur Hilfe.' }));
      kasten.append(h('div', { class: 'bewertung' },
        SELBST.map(({ urteil, name, hinweis }) => h('button', {
          onclick: () => this.weiter({ urteil }),
        }, h('b', { text: name }), h('span', { text: hinweis })))));
      return kasten;
    }

    const w = this.gewertet;
    if (!w) {
      // Satz: der Vergleich zählt, es gibt aber noch keine Wertung —
      // weiter drücken schreibt sie fort.
      kasten.append(h('div', { class: 'frage-werkzeuge',
                               style: 'justify-content:flex-start' },
        h('button', { class: 'wichtig', onclick: () => this.weiter() },
          'Weiter')));
      return kasten;
    }
    const termin = vorschau[String(w.bewertung)]?.text || w.termin_text || '';
    kasten.append(h('div', { class: 'wertung-kopf' },
      h('span', { class: 'leise', text: 'Gewertet als' }),
      h('b', { text: NOTEN.find((n) => n.note === w.bewertung)?.name || '' }),
      termin ? h('span', { class: 'leise', text: `· wieder dran ${termin}` }) : null));
    kasten.append(h('div', { class: 'frage-werkzeuge',
                             style: 'justify-content:flex-start' },
      h('button', { class: 'wichtig', onclick: () => this.naechste() }, 'Weiter'),
      h('button', {
        class: 'schlicht',
        onclick: () => { this.wertungOffen = !this.wertungOffen; this.zeichnen(); },
      }, this.wertungOffen ? 'Doch so lassen' : 'Anders werten')));
    if (this.wertungOffen) {
      kasten.append(h('div', { class: 'bewertung' },
        NOTEN.map(({ note, name, hinweis }) => h('button', {
          class: note === w.bewertung ? 'aktiv' : null,
          onclick: () => this.umwerten(note),
        }, h('b', { text: name }),
           h('span', { text: vorschau[String(note)]?.text || hinweis })))));
    }
    return kasten;
  }

  teilEingriffe(fertig) {
    if (fertig) return null;
    return h('div', { class: 'frage-werkzeuge eingriffe' },
      h('button', { class: 'schlicht', onclick: () => this.weissNicht() },
        'Weiß ich nicht'),
      // Zeigt die ganze Übung, nicht nur den laufenden Abschnitt. Der
      // Knopf zeigte auf #/uebungen/<id> — eine Adresse, die der
      // Wegweiser nicht kennt; man landete auf »Diese Seite gibt es
      // nicht« und die Sitzung war dabei beendet.
      h('button', {
        class: 'schlicht',
        onclick: () => this.ganzeUebungZeigen(),
      }, 'Übung ansehen'));
  }

  /* Die ganze Übung ansehen, ohne die Sitzung zu verlassen.
   *
   * Beim Üben steht immer nur ein Abschnitt da. Wer den Zusammenhang
   * braucht — bei einem Dialog oder einem längeren Text —, bekommt ihn
   * hier eingeblendet und übt danach weiter.
   */
  async ganzeUebungZeigen() {
    const id = this.aufgabe?.uebung_id;
    if (!id) return;
    let u;
    try {
      u = await api.uebung(id);
    } catch (fehler) {
      meldung(fehler.message, 'fehler');
      return;
    }
    const abschnitte = u.abschnitte || [];
    const kasten = h('div', { class: 'karte' },
      h('h2', { text: u.titel || 'Die ganze Übung' }),
      u.lektion_nr !== null && u.lektion_nr !== undefined
        ? h('p', { class: 'leise', text: `Lektion ${u.lektion_nr}` })
        : null);
    for (const a of abschnitte) {
      kasten.append(h('p', { class: 'uebung-zeile' },
        h('b', { text: a.original || '' })));
      if (a.referenz) {
        kasten.append(h('p', { class: 'leise uebung-zeile',
                               text: a.referenz }));
      }
    }
    if (!abschnitte.length) {
      kasten.append(h('p', { class: 'leise', text: 'Keine Abschnitte.' }));
    }
    kasten.append(h('div', { class: 'frage-werkzeuge' },
      h('button', { class: 'wichtig', onclick: () => this.zeichnen() },
        'Zurück zur Aufgabe')));
    leeren(this.behaelter).append(kasten);
  }

  /* -------------------------------------------------------------- Tun */

  fokussieren() {
    if (this.feld) setTimeout(() => this.feld && this.feld.focus(), 30);
  }

  async absenden() {
    if (this.phase === 'rueckmeldung' || this.laeuft) return;
    if (!this.eingabeWert.trim()) {
      meldung('Noch keine Übersetzung eingegeben.');
      return;
    }
    this.laeuft = true;
    try {
      this.ergebnis = await api.uebungPruefen({
        benutzer_id: zustand.benutzerId,
        textaufgabe_id: this.aufgabe.textaufgabe_id,
        antwort: this.eingabeWert,
      });
    } catch (fehler) {
      meldung(fehler.message);
      return;
    } finally {
      this.laeuft = false;
    }
    if (this.abgebrochen) return;
    this.phase = 'rueckmeldung';
    const u = this.ergebnis.urteil.urteil;
    this.gezaehlt[u === 'richtig' ? 'richtig' : (u === 'fast' ? 'fast' : 'falsch')] += 1;
    // Beim Satz zählt das Urteil — dann gleich fortschreiben, damit nicht
    // zweimal gedrückt werden muss.
    if (this.ergebnis.zaehlt) {
      await this.werten({ urteil: u });
    }
    this.zeichnen();
  }

  async weissNicht() {
    if (this.laeuft) return;
    this.laeuft = true;
    try {
      const auf = await api.uebungAufdecken({
        benutzer_id: zustand.benutzerId,
        textaufgabe_id: this.aufgabe.textaufgabe_id,
      });
      this.ergebnis = {
        urteil: { urteil: 'falsch', stellen: [], hinweis: auf.hinweis,
                  woerter_gesamt: 0, woerter_richtig: 0 },
        loesung: auf.loesung, zaehlt: true, selbsteinschaetzung: false,
      };
    } catch (fehler) {
      meldung(fehler.message);
      return;
    } finally {
      this.laeuft = false;
    }
    this.aufgedeckt = true;
    this.phase = 'rueckmeldung';
    this.gezaehlt.falsch += 1;
    await this.werten({ urteil: 'falsch', aufgedeckt: true });
    this.zeichnen();
  }

  /** Schreibt den Lernstand fort und merkt sich die Wertung. */
  async werten(daten) {
    try {
      this.gewertet = await api.uebungBewerten({
        benutzer_id: zustand.benutzerId,
        textaufgabe_id: this.aufgabe.textaufgabe_id,
        antwort: this.eingabeWert || null,
        aufgedeckt: Boolean(daten.aufgedeckt || this.aufgedeckt),
        ...daten,
      });
    } catch (fehler) {
      meldung(fehler.message);
    }
  }

  async weiter(daten = null) {
    if (daten) {
      await this.werten(daten);
      this.zeichnen();
      return;
    }
    await this.naechste();
  }

  async umwerten(note) {
    await this.werten({ bewertung: note });
    this.wertungOffen = false;
    this.zeichnen();
  }

  aufTaste(e) {
    if (e.metaKey || e.ctrlKey || e.altKey) return;
    const imFeld = document.activeElement === this.feld;
    // Im mehrzeiligen Feld schickt erst Umschalt+Enter ab — sonst käme man
    // nie zu einem Absatz.
    if (e.key === 'Enter' && (!imFeld || e.shiftKey)) {
      e.preventDefault();
      if (this.phase === 'frage') this.absenden();
      else if (this.gewertet || !this.ergebnis?.selbsteinschaetzung) this.naechste();
      return;
    }
    if (imFeld) return;
    if (this.phase === 'rueckmeldung' && /^[1-4]$/.test(e.key)) {
      e.preventDefault();
      if (this.ergebnis?.selbsteinschaetzung && !this.gewertet) {
        const zu = { 1: 'falsch', 2: 'fast', 3: 'richtig', 4: 'richtig' };
        this.weiter({ urteil: zu[e.key] });
      } else {
        this.umwerten(Number(e.key));
      }
    }
  }
}


/* --------------------------------------------------- Einstieg: was üben? */

export async function zeichnen(behaelter) {
  const el = leeren(behaelter);
  const sammlungId = zustand.sammlungId || null;
  let stand = {};
  try {
    stand = await api.uebungStand(zustand.benutzerId, sammlungId);
  } catch (fehler) {
    el.append(h('p', { class: 'befund fehler', text: fehler.message }));
    return;
  }
  el.append(h('h1', { text: 'Sätze üben' }));
  if (!stand.gesamt) {
    el.append(h('div', { class: 'leer' },
      h('p', { text: stand.ungeprueft
        ? `${stand.ungeprueft} Übungsaufgaben warten noch auf Freigabe.`
        : 'In dieser Sammlung gibt es noch keine Übungssätze.' }),
      stand.ungeprueft
        ? h('button', { class: 'wichtig',
                        onclick: () => { location.hash = '#/freigabe'; } },
            'Zur Freigabe')
        : null));
    return;
  }

  el.append(h('div', { class: 'karte' },
    h('div', { class: 'zahlen' },
      h('div', { class: 'zahl faellig' }, h('b', { text: String(stand.faellig) }),
        h('span', { text: 'fällig' })),
      h('div', { class: 'zahl verlernt' }, h('b', { text: String(stand.verlernt) }),
        h('span', { text: 'verlernt' })),
      h('div', { class: 'zahl neu' }, h('b', { text: String(stand.neu) }),
        h('span', { text: 'neu' })),
      h('div', { class: 'zahl' }, h('b', { text: String(stand.reif) }),
        h('span', { text: 'sitzt' })),
      h('div', { class: 'zahl' }, h('b', { text: String(stand.gesamt) }),
        h('span', { text: 'Aufgaben' }))),
    h('div', { class: 'frage-werkzeuge', style: 'justify-content:flex-start;margin-top:1rem' },
      h('button', {
        class: 'wichtig',
        disabled: !(stand.faellig + stand.verlernt + stand.neu),
        onclick: () => { location.hash = '#/ueben/plan'; },
      }, 'Üben'),
      h('button', { onclick: () => { location.hash = '#/ueben/frei'; } },
        'Frei üben'),
      h('button', { onclick: () => { location.hash = '#/ueben/fehler'; } },
        'Fehler wiederholen')),
    stand.ungeprueft
      ? h('p', { class: 'leise', style: 'margin-top:.6rem' },
          `${stand.ungeprueft} weitere warten auf Freigabe. `,
          h('a', { href: '#/freigabe', text: 'Ansehen' }))
      : null));

  el.append(h('p', { class: 'leise',
    text: 'Ein Satz wird Wort für Wort mit allen hinterlegten Fassungen '
        + 'verglichen und zählt. Bei längeren Texten läuft der Vergleich '
        + 'auch, aber die Einschätzung bleibt bei dir.' }));
}
