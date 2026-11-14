/* Die Abfrage. Hier entscheidet sich, ob der Trainer taugt.
 *
 * Vier Dinge sind anders als üblich:
 *   - Die Formangabe ist die Frage, nicht das Kleingedruckte.
 *   - "Fast richtig" kostet nichts: noch einmal tippen, dann zählt es.
 *   - Jeder Bewertungsknopf sagt vorher, welchen Termin er ergibt.
 *   - "Warum jetzt?" legt die Rechnung offen.
 */

import { api } from './api.js';
import { anfuegen, h, leeren, meldung, prozent, zahl, zerlegungZeigen,
         silbenZeigen, sprechen, stimmeDa } from './hilfen.js';
import { stammdaten } from './stammdaten.js';
import { zeichenleiste } from './tastatur.js';
import { zustand } from './zustand.js';

const NOTEN = [
  { note: 1, name: 'Nochmal', hinweis: 'Saß nicht' },
  { note: 2, name: 'Schwer', hinweis: 'Mit Mühe' },
  { note: 3, name: 'Gut', hinweis: 'Saß' },
  { note: 4, name: 'Leicht', hinweis: 'Sofort da' },
];

export class Sitzung {
  constructor(behaelter, optionen = {}) {
    this.behaelter = behaelter;
    this.optionen = optionen;
    this.aufgabe = null;
    this.ergebnis = null;
    this.phase = 'frage';
    this.gezaehlt = { richtig: 0, fast: 0, falsch: 0, gesamt: 0 };
    this.begonnen = 0;
    this.denkzeitStart = 0;     // wann die Frage stand
    this.denkzeit = null;       // bis zum ERSTEN Tastendruck
    this.versuche = 1;
    this.wertungOffen = false;  // "anders werten" aufgeklappt?
    // Riegel gegen Doppelauslösung. Ohne ihn wertet eine gedrückt gehaltene
    // Eingabetaste dieselbe Aufgabe mehrfach: der Phasenwechsel kommt erst
    // nach dem await, bis dahin kommt jeder weitere Tastendruck durch. Das
    // schreibt Phantomwiederholungen ins Protokoll und bläht die Stabilität.
    this.laeuft = false;
    this.abgebrochen = false;
    this.aufgedeckt = false;
    this.eingabeWert = '';
    this.reihenWerte = {};
    this.merkmalsWahl = {};
    this.lg = {};
    this.tastatur = (e) => this.aufTaste(e);
  }

  async start() {
    document.addEventListener('keydown', this.tastatur);
    try {
      this.lg = await api.legasthenieLesen(zustand.benutzerId);
    } catch { this.lg = {}; }
    // Das Tagespensum einmal zu Beginn: daran misst der Balken, und
    // daran sieht man, ob die Abfrage in zehn Fragen zu Ende ist oder
    // in dreihundert.
    try {
      this.pensum = await api.stand(zustand.benutzerId,
                                    this.optionen.sammlungId || null);
    } catch { this.pensum = null; }
    await this.naechste();
  }

  beenden() {
    // Auch das Zeichnen stilllegen: sonst schreibt eine Sitzung, die noch
    // auf eine Antwort wartet, in den Inhaltsbereich der neuen Ansicht.
    this.abgebrochen = true;
    document.removeEventListener('keydown', this.tastatur);
  }

  /* ------------------------------------------------------------- Laden */

  async naechste() {
    this.ergebnis = null;
    this.eingabeWert = '';
    this.reihenWerte = {};
    this.merkmalsWahl = {};
    this.denkzeit = null;
    this.versuche = 1;
    this.wertungOffen = false;
    this.aufgedeckt = false;      // sonst wirkt "Weiß ich nicht" fort
    this.zeichneLade();
    let reihe;
    try {
      reihe = await api.naechste(this.optionen.lernzielId
        ? { benutzer_id: zustand.benutzerId,
            lernziel_id: this.optionen.lernzielId, anzahl: 1 }
        : { benutzer_id: zustand.benutzerId,
            sammlung_id: this.optionen.sammlungId ?? zustand.sammlungId,
            lektion_id: this.optionen.lektionId,
            nur: this.optionen.nur, anzahl: 1 });
    } catch (fehler) {
      this.zeichneFehler(fehler.message);
      return;
    }
    if (!reihe || !reihe.length) {
      this.zeichneFertig();
      return;
    }
    if (this.abgebrochen) return;
    this.aufgabe = reihe[0];
    this.begonnen = performance.now();
    this.denkzeitStart = this.begonnen;

    // Im Legastheniemodus beim ersten Zusammentreffen zuerst ansehen.
    // Ins Leere tippen erzeugt nur einen Fehler, den man sich mitmerkt.
    const istNeu = (this.aufgabe.lernstand?.zustand ?? 'neu') === 'neu';
    if (this.lg.aktiv && this.lg.erkennen_vor_schreiben && istNeu
        && this.aufgabe.eingabeart === 'text') {
      await this.zeichneEinpraegen();
    } else {
      this.phase = 'frage';
      this.zeichnen();
    }
  }

  /* ---------------------------------------------------------- Zeichnen */

  zeichneLade() {
    leeren(this.behaelter).append(h('p', { class: 'leer', text: 'Einen Moment …' }));
  }

  zeichneFehler(text) {
    leeren(this.behaelter).append(
      h('div', { class: 'karte' },
        h('h2', { text: 'Das ging schief' }),
        h('p', { text }),
        h('button', { class: 'wichtig', onclick: () => this.naechste() }, 'Nochmal versuchen')));
  }

  zeichneFertig() {
    const { richtig, fast, falsch, gesamt } = this.gezaehlt;
    leeren(this.behaelter).append(
      h('div', { class: 'karte' },
        h('h1', { text: gesamt ? 'Fertig für heute' : 'Nichts zu tun' }),
        gesamt
          ? h('div', {},
              h('p', { text: `${gesamt} ${gesamt === 1 ? 'Aufgabe' : 'Aufgaben'} bearbeitet.` }),
              h('div', { class: 'zahlen' },
                h('div', { class: 'zahl' }, h('b', { text: String(richtig) }), h('span', { text: 'richtig' })),
                h('div', { class: 'zahl' }, h('b', { text: String(fast) }), h('span', { text: 'fast richtig' })),
                h('div', { class: 'zahl' }, h('b', { text: String(falsch) }), h('span', { text: 'nicht gewusst' }))))
          : h('p', { text: 'Es ist gerade nichts fällig. Freies Üben geht trotzdem jederzeit.' }),
        h('div', { class: 'frage-werkzeuge' },
          h('button', { class: 'wichtig', onclick: () => { location.hash = '#/uebersicht'; } }, 'Zur Übersicht'),
          h('button', { onclick: () => { this.gezaehlt = { richtig: 0, fast: 0, falsch: 0, gesamt: 0 }; this.optionen.nur = 'frei'; this.naechste(); } }, 'Frei weiterüben'))));
  }

  async zeichneEinpraegen() {
    this.phase = 'einpraegen';
    let gezeigt = null;
    try {
      gezeigt = await api.aufdecken({
        benutzer_id: zustand.benutzerId, aufgabe_id: this.aufgabe.aufgabe_id,
      });
    } catch { /* dann eben ohne */ }
    if (!gezeigt || !gezeigt.erwartet?.length) {
      this.phase = 'frage'; this.zeichnen(); return;
    }
    const wort = gezeigt.erwartet[0];
    const stimme = await stammdaten.stimme(this.aufgabe.antwort_sprache
                                           || this.aufgabe.sprache);
    if (this.lg.vorlesen_zuerst && stimme) sprechen(wort, stimme, 0.8);

    const z = gezeigt.zerlegung || {};
    leeren(this.behaelter).append(
      h('div', { class: 'abfrage' },
        h('span', { class: 'aufgabentyp' }, h('i', { class: 'punkt' }), 'Neu — erst ansehen'),
        h('div', { class: 'frage' },
          h('p', { class: 'leise', text: this.frageZeile() }),
          h('p', { class: 'frage-wort' },
            z.silben?.length > 1 && this.lg.silben_faerben ? silbenZeigen(z.silben) : wort),
          z.teile?.length === 2 && this.lg.stamm_hervorheben
            ? h('div', { style: 'display:flex;justify-content:center' }, zerlegungZeigen(z))
            : null,
          h('div', { class: 'frage-werkzeuge' },
            stimme ? h('button', { onclick: () => sprechen(wort, stimme, 0.75) }, '🔊 Nochmal hören') : null)),
        h('p', { class: 'leise', text: 'Ansehen, hören, dann selbst schreiben.' }),
        h('button', {
          class: 'wichtig',
          onclick: () => {
            this.phase = 'frage';
            // Die Denkzeit zählt erst ab dem Moment, in dem wirklich
            // abgefragt wird — nicht ab dem Einprägen.
            this.denkzeitStart = performance.now();
            this.zeichnen();
          },
        }, 'Jetzt schreiben')));
  }

  frageZeile() {
    const a = this.aufgabe;
    if (a.typ === 'bedeutung_fremd_deutsch') return `${a.frage_text} heißt …`;
    if (a.typ === 'bedeutung_deutsch_fremd') return `„${a.frage_text}" heißt …`;
    if (a.typ === 'form_bilden') return `${a.frage_zusatz} von ${a.frage_text}`;
    return a.typ_name;
  }

  zeichnen() {
    if (this.abgebrochen) return;
    const a = this.aufgabe;
    const el = leeren(this.behaelter);
    el.append(h('div', { class: 'abfrage' },
      this.teilFortschritt(),
      this.teilFrage(),
      this.teilEingabe(),
      this.ergebnis ? this.teilRueckmeldung() : null,
      this.ergebnis && this.phase === 'rueckmeldung' ? this.teilWertung() : null,
      this.ergebnis && this.phase === 'rueckmeldung' ? this.teilSignale() : null,
      this.teilWarum(),
      this.teilEingriffe()));
    this.fokussieren();
    this.vielleichtVorlesen();
  }

  teilFortschritt() {
    const g = this.gezaehlt;
    // Am Tagespensum messen, nicht an einer erfundenen Marke. Vorher war
    // der Balken nach 25 Fragen voll, gleich ob noch dreißig oder
    // dreihundert kamen — und man wusste nie, ob eine Abfrage endet.
    const p = this.pensum;
    const anteil = p && p.heute_gesamt
      ? Math.round((p.heute_erledigt / p.heute_gesamt) * 100)
      : Math.min(100, g.gesamt * 4);
    const text = p && p.heute_gesamt
      ? `${p.heute_erledigt} von ${p.heute_gesamt} heute`
        + (g.gesamt ? ` · ${g.richtig} richtig` : '')
      : (g.gesamt ? `${g.gesamt} bearbeitet · ${g.richtig} richtig` : 'Los geht’s');
    return h('div', {},
      h('div', { class: 'fortschritt' }, h('i', { style: `width:${anteil}%` })),
      h('p', { class: 'leise', style: 'margin:.3rem 0 0', text }));
  }

  teilFrage() {
    const a = this.aufgabe;
    const kasten = h('div', { class: 'frage' });
    kasten.append(
      h('span', { class: 'aufgabentyp' }, h('i', { class: 'punkt' }), a.typ_name,
        a.herkunft ? h('span', { class: 'marke',
          text: { faellig: 'fällig', wacklig: 'wacklig',
                  neu: 'neu' }[a.herkunft] || a.herkunft }) : null),
      h('p', { class: 'frage-wort', lang: a.frage_sprache, text: a.frage_text }));
    if (a.frage_zusatz) {
      kasten.append(h('p', { class: 'frage-zusatz', text: a.frage_zusatz }));
    }
    // Ein Beispiel auf Deutsch. "wen oder was?" ist schon besser als
    // "Akkusativ", aber erst "ich sehe DEN Hund" macht es in einer
    // Sekunde klar — und zwar auch dem, der nie Latein hatte.
    if (a.frage_hilfe) {
      kasten.append(h('p', { class: 'frage-beispiel' },
        h('span', { class: 'leise', text: 'wie bei: ' }), a.frage_hilfe));
    }
    if (a.typ === 'bedeutung_fremd_deutsch' && a.anzahl_bedeutungen > 1) {
      kasten.append(h('p', { class: 'frage-hinweis',
        text: `${a.anzahl_bedeutungen} Bedeutungen hinterlegt — eine genügt.` }));
    }
    if (a.wortart_name && a.typ !== 'genus') {
      kasten.append(h('p', { class: 'frage-hinweis', text: a.wortart_name }));
    }
    // Vorlesen nur, wenn es für die Sprache eine Stimme gibt.
    const werkzeuge = h('div', { class: 'frage-werkzeuge' });
    if (a.vorlesen && this._stimme) {
      werkzeuge.append(h('button', {
        title: 'Vorlesen',
        onclick: () => sprechen(a.vorlesen, this._stimme),
      }, '🔊 Hören'));
    }
    if (werkzeuge.children.length) kasten.append(werkzeuge);
    return kasten;
  }

  teilEingabe() {
    const a = this.aufgabe;
    const fertig = this.phase === 'rueckmeldung';
    if (a.eingabeart === 'auswahl') return this.teilAuswahl(fertig);
    if (a.eingabeart === 'merkmale') return this.teilMerkmale(fertig);
    if (a.eingabeart === 'reihe') return this.teilReihe(fertig);

    const feld = h('input', {
      type: 'text', lang: a.antwort_sprache || a.sprache,
      autocapitalize: 'off', autocorrect: 'off', spellcheck: 'false',
      autocomplete: 'off', inputmode: 'text',
      placeholder: 'Antwort', value: this.eingabeWert,
      disabled: fertig,
      class: this.ergebnis ? this.ergebnis.urteil.urteil : null,
      oninput: (e) => {
        // Die Zeit bis zum ERSTEN Tastendruck ist das Abrufmaß. Die
        // Gesamtzeit misst zu großen Teilen Tippgeschwindigkeit mit.
        if (this.denkzeit === null && e.target.value) {
          this.denkzeit = Math.round(performance.now() - this.denkzeitStart);
        }
        this.eingabeWert = e.target.value;
      },
      onkeydown: (e) => {
        if (e.key === 'Enter') { e.preventDefault(); this.absenden(); }
      },
    });
    this.feld = feld;
    const kasten = h('div', {},
      h('div', { class: 'antwortfeld' },
        feld,
        fertig ? null : h('button', { class: 'wichtig', onclick: () => this.absenden() }, 'Prüfen')));
    // Gerüst statt leeres Feld: nur im Legastheniemodus und nur vor der Prüfung.
    // Das Gerüst kommt mit der Aufgabe vom Server — dort ist die erwartete
    // Antwort bekannt.
    if (this.lg.aktiv && !this.ergebnis && a.maske) {
      kasten.append(h('p', { class: 'maske', title: 'Gerüst zum Schreiben',
                             text: a.maske }));
    }
    // Zeichenleiste für Akzente und dergleichen — erspart den Layoutwechsel,
    // solange es um einzelne Zeichen in lateinischer Schrift geht.
    if (!fertig && this._antwortsprache) {
      const leiste = zeichenleiste(this._antwortsprache, () => this.feld,
                                   (wert) => { this.eingabeWert = wert; });
      if (leiste) kasten.append(leiste);
    }
    return kasten;
  }

  /** Die ganze Tabelle auf einmal — ich gehe, du gehst, er/sie/es geht.
   *
   *  Ein Feld je Zeile, mit Beschriftung UND Beispiel daneben. Enter
   *  springt ins nächste Feld statt abzuschicken; abgeschickt wird erst
   *  im letzten oder über den Knopf. Sonst wäre die Reihe nach dem ersten
   *  Wort vorbei. */
  teilReihe(fertig) {
    const a = this.aufgabe;
    const zellen = a.zellen || [];
    if (!this.reihenWerte) this.reihenWerte = {};
    const ergebnisse = {};
    for (const z of (this.ergebnis?.aufloesung?.zellen || [])) {
      ergebnisse[z.zelle] = z;
    }
    const kasten = h('div', { class: 'reihe' });
    const felder = [];
    for (const [i, z] of zellen.entries()) {
      const r = ergebnisse[z.zelle];
      const feld = h('input', {
        type: 'text', lang: a.antwort_sprache || a.sprache,
        autocapitalize: 'off', autocorrect: 'off', spellcheck: 'false',
        autocomplete: 'off',
        value: this.reihenWerte[z.zelle] || '',
        disabled: fertig,
        class: r ? r.urteil : null,
        oninput: (e) => {
          if (this.denkzeit === null && e.target.value) {
            this.denkzeit = Math.round(performance.now() - this.denkzeitStart);
          }
          this.reihenWerte[z.zelle] = e.target.value;
        },
        onkeydown: (e) => {
          if (e.key !== 'Enter') return;
          e.preventDefault();
          const naechstes = felder[i + 1];
          if (naechstes && !naechstes.disabled) naechstes.focus();
          else this.absenden();
        },
      });
      felder.push(feld);
      kasten.append(h('div', { class: 'reihenzeile' + (r ? ' ' + r.urteil : '') },
        h('div', { class: 'reihenname' },
          h('span', { text: z.beschriftung }),
          z.beispiel
            ? h('span', { class: 'leise', text: z.beispiel })
            : null),
        feld,
        r && r.urteil !== 'richtig'
          ? h('div', { class: 'reihenloesung', lang: a.antwort_sprache },
              (r.erwartet || []).join(' / '))
          : h('div', {})));
    }
    this.feld = felder[0] || null;
    const unten = h('div', {});
    if (!fertig) {
      unten.append(h('div', { class: 'frage-werkzeuge',
                              style: 'justify-content:flex-start' },
        h('button', { class: 'wichtig', onclick: () => this.absenden() },
          'Prüfen')));
      if (this._antwortsprache) {
        const leiste = zeichenleiste(this._antwortsprache,
          () => document.activeElement && felder.includes(document.activeElement)
            ? document.activeElement : felder[0],
          () => { /* der Wert wird im oninput mitgeschrieben */ });
        if (leiste) unten.append(leiste);
      }
    }
    return h('div', {}, kasten, unten);
  }

  teilAuswahl(fertig) {
    const gewaehlt = this.eingabeWert;
    return h('div', { class: 'auswahlknoepfe' },
      (this.aufgabe.auswahl || []).map((w) => h('button', {
        disabled: fertig,
        class: gewaehlt === w.wert ? 'aktiv' : null,
        lang: this.aufgabe.sprache,
        onclick: () => {
          if (this.denkzeit === null) {
            this.denkzeit = Math.round(performance.now() - this.denkzeitStart);
          }
          this.eingabeWert = w.wert;
          this.absenden();
        },
      }, w.text)));
  }

  teilMerkmale(fertig) {
    const felder = h('div', { class: 'merkmalsfelder' });
    for (const d of this.aufgabe.dimensionen || []) {
      felder.append(h('div', { class: 'merkmalsfeld' },
        h('label', { for: 'm-' + d.dimension, text: d.name }),
        h('select', {
          id: 'm-' + d.dimension, disabled: fertig,
          onchange: (e) => {
            if (this.denkzeit === null) {
              this.denkzeit = Math.round(performance.now() - this.denkzeitStart);
            }
            this.merkmalsWahl[d.dimension] = e.target.value;
          },
        },
          h('option', { value: '', text: '–' }),
          d.werte.map((w) => h('option', {
            value: w.wert, selected: this.merkmalsWahl[d.dimension] === w.wert,
          }, w.text)))));
    }
    return h('div', {}, felder,
      fertig ? null : h('button', {
        class: 'wichtig', style: 'margin-top:.6rem',
        onclick: () => this.absenden(),
      }, 'Prüfen'));
  }

  teilRueckmeldung() {
    const u = this.ergebnis.urteil;
    const titel = { richtig: 'Richtig', fast: 'Fast richtig', falsch: 'Nicht richtig' }[u.urteil];
    const kasten = h('div', { class: 'rueckmeldung ' + u.urteil });
    kasten.append(h('div', { class: 'rueckmeldung-kopf' },
      h('span', { text: { richtig: '✓', fast: '≈', falsch: '✗' }[u.urteil] }),
      h('span', { text: titel }),
      u.urteil === 'fast' ? h('span', { class: 'leise', text: '— zählt nicht als Fehler' }) : null));

    if (u.hinweis) kasten.append(h('p', { text: u.hinweis }));

    // Die Fehlerart ist die nützlichste Zeile: "b und d sehen sich ähnlich"
    // statt bloß "falsch".
    if (u.fehlertext) {
      kasten.append(h('div', { class: 'fehlerart' },
        h('strong', { text: 'Was passiert ist: ' }), u.fehlertext));
    }

    // Bei der ganzen Reihe steht die Lösung schon neben jedem Feld. Ein
    // herausgegriffenes "Richtig ist: γράφω" wäre hier irreführend — es
    // ist ja nur eine von sechs.
    if (u.urteil !== 'richtig' && this.phase === 'rueckmeldung'
        && this.aufgabe.eingabeart !== 'reihe') {
      const loesung = this.loesungstext();
      if (loesung) {
        kasten.append(h('p', { class: 'leise', style: 'margin-top:.6rem', text: 'Richtig ist:' }),
                      h('p', { class: 'loesung', lang: this.aufgabe.antwort_sprache, text: loesung }));
      }
    }
    const zerlegt = zerlegungZeigen(this.ergebnis.zerlegung);
    if (zerlegt) kasten.append(zerlegt);

    if (this.aufgabe.eingabeart !== 'reihe') {
      anfuegen(kasten, this.teilAlternativen());
    }
    if (u.urteil === 'fast') {
      kasten.append(h('p', { class: 'leise', style: 'margin-top:.6rem',
        text: 'Noch einmal tippen — richtig geschrieben zählt es als gewusst.' }));
    }
    return kasten;
  }

  loesungstext() {
    const a = this.ergebnis.aufloesung || {};
    const u = this.ergebnis.urteil;
    if (u.treffer) return u.treffer;
    const erwartet = a.erwartet || [];
    return erwartet.length ? erwartet[0] : null;
  }

  teilAlternativen() {
    const a = this.ergebnis.aufloesung || {};
    // Bei "Bedeutung erkennen" alle Bedeutungen zeigen — auch die, die man
    // nicht genannt hat. Darum geht es ja.
    if (a.bedeutungen?.length) {
      const liste = h('ul', { class: 'alternativen' });
      for (const b of a.bedeutungen) {
        const texte = (b.uebersetzungen || []).map((u) => u.text).join(', ');
        liste.append(h('li', {},
          h('code', { text: texte }),
          b.kontext ? h('span', { class: 'leise', text: ` (${b.kontext})` }) : null));
      }
      return h('div', {}, h('p', { class: 'leise', style: 'margin-top:.6rem',
        text: a.bedeutungen.length > 1 ? 'Alle Bedeutungen:' : 'Hinterlegt:' }), liste);
    }
    // Was oben schon als Lösung steht, gehört nicht noch einmal hierher.
    const schon = this.loesungstext();
    const weitere = (a.erwartet || []).filter((t) => t !== schon);
    if (weitere.length) {
      return h('div', {}, h('p', { class: 'leise', style: 'margin-top:.6rem', text: 'Auch richtig:' }),
        h('ul', { class: 'alternativen' }, weitere.map((t) => h('li', {}, h('code', { text: t })))));
    }
    return null;
  }

  teilWertung() {
    const w = this.ergebnis.bewertung;
    if (!w) return null;
    const vorschau = this.aufgabe.vorschau || {};
    const termin = vorschau[w.bewertung]?.text || '';

    const kasten = h('div', { class: 'wertung' });
    kasten.append(h('div', { class: 'wertung-kopf' },
      h('span', { class: 'leise', text: 'Gewertet als' }),
      h('b', { text: w.name }),
      termin ? h('span', { class: 'leise', text: `· wieder dran ${termin}` }) : null));
    // Wer nicht selbst bewertet, muss sehen, wonach bewertet wurde.
    kasten.append(h('p', { class: 'wertung-grund', text: w.begruendung }));

    kasten.append(h('div', { class: 'frage-werkzeuge', style: 'justify-content:flex-start' },
      h('button', { class: 'wichtig', onclick: () => this.weiter() }, 'Weiter'),
      h('button', {
        class: 'schlicht',
        onclick: () => { this.wertungOffen = !this.wertungOffen; this.zeichnen(); },
      }, this.wertungOffen ? 'Doch automatisch' : 'Anders werten')));

    if (this.wertungOffen) {
      kasten.append(
        h('p', { class: 'leise', style: 'margin-top:.6rem',
                 text: 'Von Hand gewertet. Wird als Eingriff vermerkt, damit '
                     + 'später nachvollziehbar bleibt, worauf der Lernstand beruht.' }),
        h('div', { class: 'bewertung' },
          NOTEN.map(({ note, name, hinweis }) => h('button', {
            dataset: { note: String(note) },
            class: note === w.bewertung ? 'aktiv' : null,
            onclick: () => this.weiter(note),
          },
            h('b', { text: name }),
            h('span', { text: vorschau[note]?.text || hinweis }),
            h('kbd', { text: String(note) })))));
    }
    return kasten;
  }

  teilSignale() {
    const w = this.ergebnis?.bewertung;
    if (!w) return null;
    const s = w.signale || {};
    const kasten = h('details', { class: 'warum' },
      h('summary', { text: 'Wonach wurde gewertet?' }));
    const werte = h('div', { class: 'warum-werte' });
    werte.append(h('div', { class: 'warum-wert' },
      h('b', { text: { richtig: 'richtig', fast: 'fast richtig',
                       falsch: 'nicht richtig' }[s.urteil] || s.urteil }),
      h('span', { text: 'Antwort' })));
    if (s.versuche > 1) {
      werte.append(h('div', { class: 'warum-wert' },
        h('b', { text: String(s.versuche) }), h('span', { text: 'Versuche' })));
    }
    if (s.zeit_gewertet) {
      werte.append(
        h('div', { class: 'warum-wert' },
          h('b', { text: (s.denkzeit_ms / 1000).toFixed(1).replace('.', ',') + ' s' }),
          h('span', { text: 'bis zum ersten Tastendruck' })),
        h('div', { class: 'warum-wert' },
          h('b', { text: (s.bezugszeit_ms / 1000).toFixed(1).replace('.', ',') + ' s' }),
          h('span', { text: s.eigene_messwerte >= 6
            ? `deine übliche Zeit (aus ${s.eigene_messwerte} Messungen)`
            : 'Schätzwert, noch zu wenige eigene Messungen' })));
    }
    kasten.append(werte);
    kasten.append(h('p', { class: 'leise', style: 'margin-top:.5rem',
      text: s.zeit_gewertet
        ? 'Gemessen wird die Zeit bis zum ersten Tastendruck, nicht die ganze '
        + 'Eingabe — sonst würde Tippgeschwindigkeit mitgewertet. Und sie zählt '
        + 'nur im Verhältnis zu deiner eigenen üblichen Zeit.'
        : 'Die Zeit wird nicht gewertet. Bewertet wird allein, was herauskam.' }));
    return kasten;
  }

  teilWarum() {
    const w = this.aufgabe.warum || {};
    const l = this.aufgabe.lernstand || {};
    const kasten = h('details', { class: 'warum' },
      h('summary', { text: 'Warum kommt das jetzt?' }));
    kasten.append(h('p', { text: w.text || 'Noch keine Angaben.' }));
    if (!w.neu) {
      kasten.append(h('div', { class: 'warum-werte' },
        h('div', { class: 'warum-wert' },
          h('b', { text: zahl(w.stabilitaet) + ' Tage' }),
          h('span', { text: 'Stabilität' })),
        h('div', { class: 'warum-wert' },
          h('b', { text: zahl(w.schwierigkeit) + ' von 10' }),
          h('span', { text: 'Schwierigkeit' })),
        h('div', { class: 'warum-wert', style: 'min-width:8rem' },
          h('b', { text: prozent(w.abrufwahrscheinlichkeit) }),
          h('span', { text: 'sitzt heute noch' }),
          h('div', { class: 'balken' },
            h('i', { style: `width:${Math.round((w.abrufwahrscheinlichkeit || 0) * 100)}%` }))),
        h('div', { class: 'warum-wert' },
          h('b', { text: String(l.anzahl || 0) }),
          h('span', { text: 'mal abgefragt' })),
        h('div', { class: 'warum-wert' },
          h('b', { text: String(l.anzahl_fehler || 0) }),
          h('span', { text: 'davon daneben' }))));
      kasten.append(h('p', { class: 'leise', style: 'margin-top:.5rem',
        text: 'Die Stabilität ist die Zahl der Tage, nach der die Erinnerung '
            + 'auf 90 % gefallen ist. Sie wächst stärker, wenn man kurz vor '
            + 'dem Vergessen wiederholt — darum die langen Abstände.' }));
    }
    return kasten;
  }

  teilEingriffe() {
    const kennung = { benutzer_id: zustand.benutzerId, aufgabe_id: this.aufgabe.aufgabe_id };
    const reihe = h('div', { class: 'frage-werkzeuge', style: 'justify-content:flex-start' });
    if (this.phase !== 'rueckmeldung') {
      reihe.append(h('button', { class: 'schlicht', onclick: () => this.weissNicht() },
        'Weiß ich nicht'));
    }
    reihe.append(
      h('button', {
        class: 'schlicht', title: 'Diese Aufgabe nicht mehr abfragen',
        onclick: async () => {
          await api.aussetzen(kennung);
          meldung('Ausgesetzt. In den Einstellungen wieder einschaltbar.');
          this.naechste();
        },
      }, 'Aussetzen'),
      h('button', {
        class: 'schlicht', title: 'Dieses Wort im Wortschatz ansehen',
        onclick: () => { location.hash = `#/wort/${this.aufgabe.lexem_id}`; },
      }, 'Wort ansehen'));
    return reihe;
  }

  /* ------------------------------------------------------------- Ablauf */

  async fokussieren() {
    if (this.feld && this.phase === 'frage') {
      this.feld.focus();
      this.feld.setSelectionRange(this.feld.value.length, this.feld.value.length);
    }
    // Sprachangaben nachladen (Stimme, Sonderzeichen) und nur dann neu
    // zeichnen, wenn sich dadurch etwas ändert.
    const code = this.aufgabe.antwort_sprache || this.aufgabe.sprache;
    const sprache = await stammdaten.sprache(code);
    const stimme = sprache.stimme && stimmeDa(sprache.stimme) ? sprache.stimme : null;
    // Nur neu zeichnen, wenn sich wirklich etwas geändert hat. Sonst ruft
    // zeichnen() wieder fokussieren() und das wieder zeichnen() — eine
    // Endlosschleife, die den Browser einfriert.
    const geaendert = this._stimme !== stimme
                   || this._antwortsprache?.code !== sprache.code;
    this._stimme = stimme;
    this._antwortsprache = sprache;
    if (geaendert && this.phase === 'frage' && !this.ergebnis) {
      this.zeichnen();
    }
  }

  vielleichtVorlesen() {
    // Nur bei Verständnisrichtung und nur wenn gewünscht: Hören zuerst.
    if (!this.lg.aktiv || !this.lg.vorlesen_zuerst) return;
    if (this.phase !== 'frage' || this.ergebnis) return;
    if (this._gelesen === this.aufgabe.aufgabe_id) return;
    if (this.aufgabe.vorlesen && this._stimme) {
      this._gelesen = this.aufgabe.aufgabe_id;
      sprechen(this.aufgabe.vorlesen, this._stimme, 0.85);
    }
  }

  antwortWert() {
    if (this.aufgabe.eingabeart === 'reihe') {
      return { ...(this.reihenWerte || {}) };
    }
    if (this.aufgabe.eingabeart === 'merkmale') {
      const sauber = {};
      for (const [d, w] of Object.entries(this.merkmalsWahl)) if (w) sauber[d] = w;
      return sauber;
    }
    return this.eingabeWert;
  }

  async absenden() {
    if (this.phase === 'rueckmeldung' || this.laeuft) return;
    const antwort = this.antwortWert();
    // Bei der Reihe zählt, ob IRGENDWO etwas steht — leere Felder sind
    // erlaubt und zählen als nicht gewusst, aber eine völlig leere
    // Tabelle ist keine Antwort.
    const leerEingabe = typeof antwort === 'string'
      ? !antwort.trim()
      : !Object.values(antwort).some((w) => String(w ?? '').trim());
    if (leerEingabe) { meldung('Noch keine Antwort eingegeben.'); return; }

    let ergebnis;
    this.laeuft = true;
    try {
      ergebnis = await api.pruefen({
        benutzer_id: zustand.benutzerId,
        aufgabe_id: this.aufgabe.aufgabe_id,
        antwort,
        denkzeit_ms: this.denkzeit,
        versuche: this.versuche,
      });
    } catch (fehler) {
      meldung(fehler.message);
      return;
    } finally {
      this.laeuft = false;
    }
    if (this.abgebrochen) return;

    this.ergebnis = ergebnis;
    if (ergebnis.nochmal_tippen && this.phase === 'frage') {
      // "Fast richtig": noch einmal tippen, ohne Strafe. Erst der zweite
      // Versuch entscheidet.
      this.phase = 'nochmal';
      this.versuche += 1;
      this.gezaehlt.fast += 1;
      this.zeichnen();
      if (this.feld) { this.feld.disabled = false; this.feld.focus(); this.feld.select(); }
      return;
    }
    this.phase = 'rueckmeldung';
    const u = ergebnis.urteil.urteil;
    if (u === 'richtig') this.gezaehlt.richtig += 1;
    else if (u === 'falsch') this.gezaehlt.falsch += 1;
    this.zeichnen();
  }

  async weissNicht() {
    if (this.laeuft || this.phase === 'rueckmeldung') return;
    this.laeuft = true;
    try {
      const gezeigt = await api.aufdecken({
        benutzer_id: zustand.benutzerId, aufgabe_id: this.aufgabe.aufgabe_id,
      });
      this.aufgedeckt = true;
      this.ergebnis = {
        urteil: { urteil: 'falsch', treffer: gezeigt.erwartet?.[0] || null,
                  hinweis: 'Aufgedeckt, ohne zu raten.', abweichungen: [],
                  fehlerart: null, fehlertext: null },
        aufloesung: gezeigt.aufloesung || { erwartet: gezeigt.erwartet },
        zerlegung: this.lg.aktiv ? gezeigt.zerlegung : null,
        bewertung: {
          bewertung: 1, name: 'Nochmal', automatisch: true,
          begruendung: 'Aufgedeckt statt geraten.',
          signale: { urteil: 'falsch', aufgedeckt: true, versuche: this.versuche,
                     zeit_gewertet: false },
        },
      };
      this.phase = 'rueckmeldung';
      this.gezaehlt.falsch += 1;
      this.zeichnen();
    } catch (fehler) {
      meldung(fehler.message);
    } finally {
      this.laeuft = false;
    }
  }

  /** Weiter zur nächsten Aufgabe. Ohne `note` gilt die automatische
   *  Bewertung; mit `note` ist es ein Eingriff von Hand. */
  async weiter(note = null) {
    if (this.phase !== 'rueckmeldung' || this.laeuft) return;
    const u = this.ergebnis?.urteil || {};
    this.laeuft = true;
    this.phase = 'wird_gewertet';      // gleich hier, nicht erst nach dem await
    try {
      const ergebnis = await api.bewerten({
        benutzer_id: zustand.benutzerId,
        aufgabe_id: this.aufgabe.aufgabe_id,
        bewertung: note,
        antwort: typeof this.eingabeWert === 'string' ? this.eingabeWert : null,
        urteil: u.urteil || null,
        fehlerart: u.fehlerart
          || (u.abweichungen || []).find((a) => a === 'diakritika'
                                             || a === 'verwechslung') || null,
        dauer_ms: Math.round(performance.now() - this.begonnen),
        denkzeit_ms: this.denkzeit,
        versuche: this.versuche,
        aufgedeckt: Boolean(this.aufgedeckt),
      });
      this.gezaehlt.gesamt += 1;
      if (this.pensum) {
        this.pensum.heute_erledigt += 1;
        // Eine erledigte Aufgabe, die gleich wiederkommt, bleibt offen.
        if (ergebnis.einschaetzung?.bewertung !== 1
            && this.pensum.heute_offen > 0) {
          this.pensum.heute_offen -= 1;
          this.pensum.heute_gesamt = this.pensum.heute_erledigt
                                   + this.pensum.heute_offen;
        } else {
          this.pensum.heute_gesamt += 1;
        }
      }
      // Länger als die üblichen Meldungen: hier steht die Auskunft, die
      // man wirklich lesen will — wie es gewertet wurde und wann es
      // wiederkommt. 1,8 Sekunden waren zu kurz, um beides zu erfassen.
      meldung(`${ergebnis.einschaetzung ? ergebnis.einschaetzung.name : 'Gewertet'}`
            + ` · wieder dran ${ergebnis.termin_text}.`, 3600);
    } catch (fehler) {
      meldung(fehler.message);
      this.phase = 'rueckmeldung';     // noch einmal versuchbar
      this.laeuft = false;
      return;
    }
    this.laeuft = false;
    this.aufgedeckt = false;
    await this.naechste();
  }

  aufTaste(e) {
    if (e.metaKey || e.ctrlKey || e.altKey) return;
    if (this.phase === 'einpraegen' && e.key === 'Enter') {
      e.preventDefault(); this.phase = 'frage'; this.zeichnen(); return;
    }
    if (this.phase !== 'rueckmeldung') return;
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault(); this.weiter(); return;         // automatische Wertung
    }
    if (e.key >= '1' && e.key <= '4') {
      e.preventDefault(); this.weiter(Number(e.key));    // Eingriff von Hand
    }
  }
}

export async function zeichnen(behaelter, optionen) {
  const sitzung = new Sitzung(behaelter, optionen);
  await sitzung.start();
  return sitzung;
}
