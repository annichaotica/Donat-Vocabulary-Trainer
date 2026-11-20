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
         silbenZeigen, sprechen, stimmeDa, tun } from './hilfen.js';
import { stammdaten } from './stammdaten.js';
import { zeichenleiste, umschriftAnhaengen,
         kannUmschreiben } from './tastatur.js';
import { zustand } from './zustand.js';
import * as spielzeichen from './spiel.js';

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
    this.zaehlerZuruecksetzen();
    // Was zuletzt ausgesetzt wurde, damit es sich zurücknehmen lässt.
    this.ausgesetzt = null;
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
    this.tipps = 0;
    this.tippText = null;
    this.eingabeWert = '';
    this.reihenWerte = {};
    this.merkmalsWahl = {};
    this.lg = {};
    // Nach »richtig« von selbst weiterspringen? Kommt aus den
    // Einstellungen; `sprung` ist die laufende Uhr, `sprungAus` das
    // »Hierbleiben« für GENAU diese Aufgabe.
    this.weiterspringen = false;
    this.sprung = null;
    this.sprungHalt = null;
    this.sprungAus = false;
    this.tastatur = (e) => this.aufTaste(e);
    /* Lag die Seite zwischendurch im Hintergrund?
     *
     * `performance.now()` läuft weiter, wenn man auf dem Handy die App
     * wechselt oder der Bildschirm zugeht. Die Zeit bis zum ersten
     * Tastendruck misst dann die Unterbrechung, nicht das Nachdenken —
     * und der Trainer wertet ein gekonntes Wort als »lange gesucht«
     * herunter. Darum wird die Messung in diesem Fall verworfen: lieber
     * keine Aussage als eine falsche.
     */
    this.warVersteckt = false;
    this.sichtbarkeit = () => {
      if (document.visibilityState === 'hidden') this.warVersteckt = true;
    };
    document.addEventListener('visibilitychange', this.sichtbarkeit);
  }

  async start() {
    document.addEventListener('keydown', this.tastatur);
    try {
      this.lg = await api.legasthenieLesen(zustand.benutzerId);
    } catch { this.lg = {}; }
    try {
      const e = await api.benutzerEinstellungen(zustand.benutzerId);
      this.umschrift = e.tastatur_umschrift !== false;
      this.weiterspringen = Boolean(e.weiterspringen);
    } catch { this.umschrift = true; }
    // Das Tagespensum einmal zu Beginn: daran misst der Balken, und
    // daran sieht man, ob die Abfrage in zehn Fragen zu Ende ist oder
    // in dreihundert.
    try {
      this.pensum = await api.stand(zustand.benutzerId,
                                    this.optionen.sammlungId || null);
    } catch { this.pensum = null; }
    this.pensumMarke = this.pensum ? this.pensum.heute_gesamt : 0;
    // Der Punktestand ZU BEGINN. Am Ende wird verglichen — das ist
    // genauer als jede Nachrechnung in der Oberfläche und hält die
    // Regel an einem Ort: im Server.
    try {
      this.spielVorher = await spielzeichen.holen(zustand.benutzerId);
    } catch { this.spielVorher = null; }
    await this.naechste();
  }

  /** Die Zähler einer Runde auf null.
   *
   * Stand dreimal als Literal in dieser Datei — und als der Wandel
   * dazukam (was dauerhaft sitzt, was neu angefangen ist), hätte man
   * ihn an drei Stellen nachtragen müssen. Die vierte Stelle hätte
   * gefehlt.
   */
  zaehlerZuruecksetzen() {
    this.gezaehlt = { richtig: 0, fast: 0, falsch: 0, gesamt: 0 };
    // Was sich am Lernstand GEÄNDERT hat, nicht wie viel getippt wurde.
    // Das ist der Unterschied zwischen »24 Aufgaben bearbeitet« und
    // »drei sitzen jetzt dauerhaft« — die zweite Zahl ist der Grund,
    // warum man es gemacht hat.
    this.wandel = { angefangen: 0, sitzt: 0, zurueck: 0 };
  }

  beenden() {
    // Auch das Zeichnen stilllegen: sonst schreibt eine Sitzung, die noch
    // auf eine Antwort wartet, in den Inhaltsbereich der neuen Ansicht.
    this.abgebrochen = true;
    this.sprungAbbrechen();
    document.removeEventListener('keydown', this.tastatur);
    document.removeEventListener('visibilitychange', this.sichtbarkeit);
    if (this._umschriftLoesen) this._umschriftLoesen();
    if (this._umschriftReihe) this._umschriftReihe.forEach((f) => f());
  }

  /* ------------------------------------------------------------- Laden */

  async naechste() {
    this.sprungAbbrechen();
    this.sprungAus = false;       // gilt immer nur für EINE Aufgabe
    this.ergebnis = null;
    this.eingabeWert = '';
    this.reihenWerte = {};
    this.merkmalsWahl = {};
    this.denkzeit = null;
    this.versuche = 1;
    this.wertungOffen = false;
    this.aufgedeckt = false;      // sonst wirkt "Weiß ich nicht" fort
    this.tipps = 0;               // ebenso die genommenen Tipps
    this.tippText = null;
    this.warVersteckt = false;    // und die Unterbrechung der vorigen Frage
    this.zeichneLade();
    let reihe;
    try {
      const grenze = this.ohneGrenze ? { ohne_grenze: true } : {};
      reihe = await api.naechste(this.optionen.lernzielId
        ? { benutzer_id: zustand.benutzerId,
            lernziel_id: this.optionen.lernzielId, anzahl: 1, ...grenze }
        : { benutzer_id: zustand.benutzerId,
            sammlung_id: this.optionen.sammlungId ?? zustand.sammlungId,
            lektion_id: this.optionen.lektionId,
            anzahl: 1,
            // Erst der Modus, dann der Weg: wer ausdrücklich
            // »Fehler wiederholen« aufruft, meint das auch, wenn
            // noch ein Ausschnitt eingestellt ist. Andersherum
            // überschriebe das »frei« des Modus die Absicht.
            ...(zustand.lernmodus || {}),
            ...(this.optionen.nur ? { nur: this.optionen.nur } : {}),
            ...grenze });
    } catch (fehler) {
      this.zeichneFehler(fehler.message);
      return;
    }
    if (!reihe || !reihe.length) {
      // Den Stand frisch holen: am Schluss zählt, was jetzt gilt, nicht
      // was zu Beginn der Sitzung galt.
      try {
        this.pensum = await api.stand(zustand.benutzerId,
                                      this.optionen.sammlungId || null);
        // Nur nach OBEN: ist zwischendurch wirklich mehr fällig
        // geworden, soll die Marke das zeigen. Zurückgehen darf sie
        // nicht.
        this.pensumMarke = Math.max(this.pensumMarke || 0,
                                    this.pensum.heute_gesamt);
      } catch { /* dann eben mit dem alten Stand */ }
      await this.zeichneFertig();
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

  /* Hängt die Umschrift an ein Antwortfeld — und meldet die vorige ab.
   *
   * Ohne das Abmelden bliebe bei jedem Neuzeichnen ein Behandler mehr
   * hängen; genau dieser Fehler ist hier schon zweimal passiert (der
   * doppelte Tastenbehandler, das überholte <main>).
   */
  umschriftSetzen(feld) {
    if (this._umschriftLoesen) { this._umschriftLoesen(); }
    this._umschriftLoesen = null;
    const code = this._antwortsprache?.code;
    if (!feld || !this.umschrift || !kannUmschreiben(code)) return;
    this._umschriftLoesen = umschriftAnhaengen(feld, code);
  }

  /* Ein Tipp — weniger als die Lösung, und die Abfrage läuft weiter.
   *
   * Dazwischen fehlte bisher alles: »Weiß ich nicht« deckt auf und
   * wertet als Nochmal, »Wort ansehen« führte aus der Abfrage heraus
   * und zurück kam man nicht. Wer nur einen Anstoß brauchte, hatte
   * keine Wahl.
   *
   * Ein genommener Tipp deckelt die Bewertung auf »Schwer« — die
   * Antwort kam selbst, aber nicht allein. Das steht auch in der
   * Begründung, damit niemand rätselt, warum es nicht »Gut« wurde.
   */
  async tippHolen() {
    if (this.tipps >= 3) return;
    try {
      const t = await api.tipp({
        benutzer_id: zustand.benutzerId,
        aufgabe_id: this.aufgabe.aufgabe_id,
        stufe: this.tipps + 1,
      });
      this.tipps = t.stufe || this.tipps + 1;
      this.tippText = t;
      this.zeichnen();
    } catch (fehler) {
      meldung(fehler.message, 'fehler');
    }
  }

  teilTipp() {
    const t = this.tippText;
    if (!t) return null;
    return h('div', { class: 'tipp' },
      h('p', { class: 'tipp-maske', lang: this.aufgabe.antwort_sprache,
               text: t.maske || '' }),
      h('p', { class: 'leise' },
        t.buchstaben
          ? `${t.buchstaben} Buchstaben`
            + (t.woerter > 1 ? ` in ${t.woerter} Wörtern` : '')
          : (t.hinweis || ''),
        t.stamm ? h('span', {}, ' · Stamm: ', h('b', { text: t.stamm })) : null,
        t.stufe >= t.hoechste_stufe
          ? h('span', { text: ' · mehr gibt es nicht' })
          : null));
  }

  /* Das Wort einblenden, ohne die Abfrage zu verlassen. */
  async wortZeigen() {
    let lexem;
    try {
      lexem = await api.lexem(this.aufgabe.lexem_id);
    } catch (fehler) { meldung(fehler.message, 'fehler'); return; }
    const kasten = h('div', { class: 'karte' },
      h('h2', { lang: lexem.sprache || this.aufgabe.sprache,
                text: lexem.lemma || '' }));
    for (const b of lexem.bedeutungen || []) {
      kasten.append(h('p', {},
        h('b', { text: (b.uebersetzungen || []).map((u) => u.text).join(', ') }),
        b.kontext ? h('span', { class: 'leise', text: ` (${b.kontext})` })
                  : null));
    }
    const formen = (lexem.formen || []).filter((f) => f.geprueft);
    if (formen.length) {
      kasten.append(h('p', { class: 'leise', style: 'margin-top:.6rem',
                             text: `${formen.length} Formen` }));
      kasten.append(h('ul', { class: 'regel-beispiele' },
        formen.slice(0, 20).map((f) => h('li', {},
          h('b', { text: f.text }),
          f.beschriftung ? h('span', { text: ` — ${f.beschriftung}` })
                         : null))));
    }
    kasten.append(h('div', { class: 'frage-werkzeuge' },
      h('button', { class: 'wichtig', onclick: () => this.zeichnen() },
        'Zurück zur Abfrage')));
    leeren(this.behaelter).append(kasten);
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

  /** Was am Ende einer Runde dasteht.
   *
   * Hier stand bisher, WIE VIEL getippt wurde: 24 Aufgaben, davon so
   * und so viele richtig. Das ist eine Leistungsmessung, kein Grund
   * weiterzumachen — und am nächsten Tag steht dieselbe Zahl da.
   *
   * Dazu kommt jetzt, was sich GEÄNDERT hat: was dauerhaft sitzt, was
   * neu angefangen ist, was aus dem Verlernten zurückgeholt wurde, und
   * wie die Strähne steht. Alles Sätze, die etwas benennen — »Super
   * gemacht!« glaubt beim dritten Mal niemand mehr, und ein Vierzehn-
   * jähriger beim ersten nicht.
   */
  async zeichneFertig() {
    const { richtig, fast, falsch, gesamt } = this.gezaehlt;
    const p = this.pensum || {};
    // Den Spielstand FRISCH holen, nicht den mitgezählten nehmen: ob der
    // Tag als geschafft gilt, hängt auch daran, ob überhaupt noch etwas
    // fällig war — und das weiß nur der Server. Mitgezählt wird während
    // der Runde, damit der Ring läuft; am Schluss zählt, was gilt.
    let sp = spielzeichen.letzterStand();
    try {
      sp = (await spielzeichen.holen(zustand.benutzerId)) || sp;
    } catch { /* dann mit dem mitgezählten Stand */ }
    if (this.abgebrochen) return;
    // Der Rückstand wird genannt, nicht verschwiegen — aber als Zahl, die
    // sinkt, nicht als Vorwurf. Verschwiegen wäre er schlimmer: dann
    // stünde morgen wieder dieselbe Zahl da und niemand wüsste, warum.
    const rueckstand = (!this.ohneGrenze && p.tagesdosis)
      ? (p.rueckstand || 0) : 0;
    // Auch wenn nichts im Rückstand ist: wer gerade erst angefangen hat
    // und auf die Tagesgrenze läuft, braucht den Weg vorbei.
    const geschafft = Boolean(p.tagesdosis)
      && p.heute_erledigt >= p.tagesdosis;
    // Der Fall, der ratlos macht: Pensum voll, aber in DIESER Sitzung
    // war noch nichts. Dann ist »Tagespensum geschafft« zwar wahr,
    // beantwortet aber die falsche Frage — man hat ja gerade erst
    // angefangen. Und »welches Tagespensum« ist berechtigt: die Dosis
    // zählt über alle Sammlungen zusammen, nicht je Lernziel.
    const fremdVoll = geschafft && !gesamt;
    leeren(this.behaelter).append(
      h('div', { class: 'karte' },
        h('h1', { text: fremdVoll ? 'Für heute ist Schluss'
                 : geschafft ? 'Tagespensum geschafft'
                 : (gesamt ? 'Fertig für heute' : 'Nichts zu tun') }),
        fremdVoll
          ? h('p', {},
              `Dein Tagespensum von ${p.tagesdosis} Fragen ist voll. `
              + 'Es zählt über alle Sammlungen und Lernziele zusammen — '
              + 'hier warst du heute zwar noch nicht dran, anderswo aber '
              + `schon ${p.heute_erledigt} Mal.`)
          : null,
        gesamt
          ? h('div', {},
              h('p', { text: `${gesamt} ${gesamt === 1 ? 'Aufgabe' : 'Aufgaben'} bearbeitet.` }),
              h('div', { class: 'zahlen' },
                h('div', { class: 'zahl' }, h('b', { text: String(richtig) }), h('span', { text: 'richtig' })),
                h('div', { class: 'zahl' }, h('b', { text: String(fast) }), h('span', { text: 'fast richtig' })),
                h('div', { class: 'zahl' }, h('b', { text: String(falsch) }), h('span', { text: 'nicht gewusst' }))))
          : (fremdVoll ? null
             : h('p', { text: 'Es ist gerade nichts fällig. Freies Üben geht '
                            + 'trotzdem jederzeit.' })),
        this.teilErfolg(),
        this.teilPunkte(sp),
        this.teilStraehne(sp),
        rueckstand
          ? h('p', { class: 'leise' },
              `Es warten noch ${rueckstand} `
              + `${rueckstand === 1 ? 'Frage' : 'Fragen'}. Die holst du nach `
              + 'und nach auf — jeder Tag, an dem du dein Pensum machst, '
              + 'macht die Zahl kleiner.')
          : null,
        h('div', { class: 'frage-werkzeuge' },
          h('button', { class: 'wichtig', onclick: () => { location.hash = '#/uebersicht'; } }, 'Zur Übersicht'),
          (rueckstand || fremdVoll)
            ? h('button', {
                onclick: () => {
                  // Die Grenze ist ein Vorschlag, kein Schloss.
                  this.ohneGrenze = true;
                  this.zaehlerZuruecksetzen();
                  this.naechste();
                },
              }, 'Trotzdem weitermachen')
            : null,
          h('button', { onclick: () => { this.zaehlerZuruecksetzen(); this.optionen.nur = 'frei'; this.naechste(); } }, 'Frei weiterüben'))));
  }

  /** Was sich am Lernstand geändert hat — und nur das.
   *
   * Nichts geschehen heißt: kein Satz. Eine Zeile, die auch »0 Aufgaben
   * sitzen jetzt dauerhaft« schreibt, erzieht dazu, die Stelle zu
   * überlesen, an der später etwas Gutes steht.
   */
  teilErfolg() {
    const w = this.wandel;
    const teile = [];
    if (w.sitzt) {
      teile.push(`${w.sitzt} ${w.sitzt === 1 ? 'Aufgabe sitzt' : 'Aufgaben sitzen'}`
               + ' jetzt dauerhaft');
    }
    if (w.zurueck) {
      teile.push(`${w.zurueck} ${w.zurueck === 1 ? 'Aufgabe' : 'Aufgaben'}`
               + ' aus dem Verlernten zurückgeholt');
    }
    if (w.angefangen) {
      teile.push(`${w.angefangen} neu angefangen`);
    }
    if (!teile.length) return null;
    // Gezählt wird in AUFGABEN und nicht in Wörtern, wie überall sonst
    // in diesem Trainer: ein Wort hat zwei Richtungen, und »drei
    // Wörter« wäre dann schlicht falsch.
    return h('p', { class: 'spiel-erfolg', text: teile.join(' · ') + '.' });
  }

  /** Was die Runde an Punkten gebracht hat — und ob eine Stufe fiel.
   *
   * Als Differenz zum Stand bei Sitzungsbeginn, nicht nachgerechnet.
   * Eine zweite Rechnung in der Oberfläche wäre eine zweite Wahrheit,
   * und sie würde beim ersten Mal abweichen, wenn jemand die Vergabe
   * im Server ändert.
   */
  teilPunkte(sp) {
    if (!sp || !this.spielVorher) return null;
    const dazu = sp.punkte.gesamt - this.spielVorher.punkte.gesamt;
    if (dazu <= 0) return null;
    const alt = this.spielVorher.punkte.stufe;
    const neu = sp.punkte.stufe;
    const aufgestiegen = neu.nummer > alt.nummer;
    return h('p', { class: aufgestiegen ? 'spiel-erfolg' : 'spiel-straehne' },
      `+${dazu} Punkte`,
      sp.punkte.heute_verdoppelt ? ' (heute zählt doppelt)' : '',
      aufgestiegen
        ? ` — Stufe ${neu.nummer} erreicht: ${neu.name}.`
        : '.');
  }

  /** Tagesziel und Strähne — und was noch fehlt.
   *
   * Der nützlichste Satz ist der letzte: »noch sechs Fragen, dann steht
   * die Strähne bei sechs Tagen«. Er nennt, was auf dem Spiel steht,
   * und zwar in einer Größe, die man noch heute abarbeiten kann.
   */
  teilStraehne(sp) {
    if (!sp) return null;
    const z = sp.tagesziel;
    const f = sp.straehne;
    const tage = (n) => `${n} ${n === 1 ? 'Tag' : 'Tage'}`;

    if (z.geschafft) {
      const teile = [z.nichts_mehr_faellig
        ? 'Tagesziel erreicht — es war nichts mehr fällig.'
        : 'Tagesziel geschafft.'];
      if (f.laufend) {
        teile.push(`Strähne: ${tage(f.laufend)} in Folge.`);
        if (f.laengste > f.laufend) {
          teile.push(`Am längsten waren es ${tage(f.laengste)}.`);
        }
      }
      return h('p', { class: 'spiel-straehne', text: teile.join(' ') });
    }
    const fehlt = Math.max(0, z.ziel - z.erledigt);
    return h('p', { class: 'spiel-straehne' },
      `Noch ${fehlt} ${fehlt === 1 ? 'Frage' : 'Fragen'} bis zum Tagesziel`,
      f.laufend
        ? ` — dann steht die Strähne bei ${tage(f.laufend + 1)}.`
        : '.');
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
      this.teilAusgesetzt(),
      this.teilFrage(),
      this.teilEingabe(),
      // Gleich unter dem Feld, nicht am Fuß der Seite — und HIER und
      // nicht in teilEingabe: die Auswahl- und Merkmalsaufgaben haben
      // ihren eigenen Zweig, sonst verlören gerade sie »Weiß ich
      // nicht«.
      this.teilHilfen(),
      this.teilTipp(),
      this.ergebnis ? this.teilRueckmeldung() : null,
      this.ergebnis && this.phase === 'rueckmeldung' ? this.teilWertung() : null,
      this.ergebnis && this.phase === 'rueckmeldung' ? this.teilSignale() : null,
      this.teilRegeln(),
      this.teilWarum(),
      this.teilEingriffe()));
    this.fokussieren();
    this.vielleichtVorlesen();
  }

  /** »Ausgesetzt — zurücknehmen?«
   *
   * Steht oben, über der nächsten Frage, und bleibt bis zur nächsten
   * Antwort stehen. Ein Knopf, der etwas dauerhaft aus der Abfrage
   * nimmt, braucht einen Rückweg in Reichweite — eine Meldung, die
   * nach drei Sekunden verschwindet, ist keiner.
   */
  teilAusgesetzt() {
    const a = this.ausgesetzt;
    if (!a) return null;
    return h('div', { class: 'karte hinweiskasten' },
      h('p', { style: 'margin:0' },
        h('b', { text: a.lemma || 'Die Aufgabe' }),
        ` ist ausgesetzt und kommt nicht mehr dran${a.typ ? ` (${a.typ})` : ''}.`),
      h('div', { class: 'frage-werkzeuge',
                 style: 'margin-top:.5rem' },
        h('button', {
          class: 'wichtig',
          onclick: () => tun(async () => {
            await api.fortsetzen(a.kennung);
            this.ausgesetzt = null;
            meldung('Wieder dabei.');
            this.zeichnen();
          }),
        }, 'Zurücknehmen'),
        h('button', {
          class: 'schlicht',
          onclick: () => { this.ausgesetzt = null; this.zeichnen(); },
        }, 'Passt so')));
  }

  teilFortschritt() {
    const g = this.gezaehlt;
    // Am Tagespensum messen, nicht an einer erfundenen Marke. Vorher war
    // der Balken nach 25 Fragen voll, gleich ob noch dreißig oder
    // dreihundert kamen — und man wusste nie, ob eine Abfrage endet.
    const p = this.pensum;
    // Die Marke steht fest, seit die Sitzung begann.
    //
    // Vorher wuchs bei »Nochmal« der NENNER: aus »12 von 40« wurde
    // »13 von 42«, der Balken stand oder ging zurück. Wer etwas nicht
    // wusste, sah einen Fortschritt, der nicht vorangeht — und zwar
    // genau der, der die Ermutigung am nötigsten hat.
    //
    // Eine Aufgabe, die am selben Tag noch einmal kommt, ist dieselbe
    // Aufgabe. Sie gehört nicht ein zweites Mal in das Pensum.
    const marke = p ? Math.max(this.pensumMarke || 0, p.heute_erledigt) : 0;
    const anteil = marke
      ? Math.round((p.heute_erledigt / marke) * 100)
      : Math.min(100, g.gesamt * 4);
    const text = marke
      ? `${p.heute_erledigt} von ${marke} heute`
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
    // Die deutsche Bedeutung — aber NUR bei den Reihen.
    //
    // »Das ist dort ok«: bei einer Bedeutungsaufgabe wäre sie die
    // Lösung, bei einer Reihe ist sie es nicht. Wer weiß, dass »aller«
    // gehen heißt, hat davon keine einzige der sechs Formen — er weiß
    // nur, wovon er redet. Der Server schickt sie darum auch nur für
    // diese beiden Aufgabenarten mit.
    if (a.bedeutung) {
      kasten.append(h('p', { class: 'frage-bedeutung', lang: 'de' },
        h('span', { class: 'leise', text: 'heißt: ' }), a.bedeutung));
    }
    // Ein Beispiel auf Deutsch. "wen oder was?" ist schon besser als
    // "Akkusativ", aber erst "ich sehe DEN Hund" macht es in einer
    // Sekunde klar — und zwar auch dem, der nie Latein hatte.
    if (a.frage_hilfe) {
      kasten.append(h('p', { class: 'frage-beispiel' },
        h('span', { class: 'leise', text: 'wie bei: ' }), a.frage_hilfe));
    }
    // Wer gemeint ist, in der Sprache selbst. In Klammern, wo das
    // Pronomen freiwillig ist — im Griechischen sagt die Endung es schon.
    if ((a.pronomen || []).length) {
      const text = a.pronomen.join(' / ');
      kasten.append(h('p', { class: 'frage-pronomen', lang: a.antwort_sprache },
        a.pronomen_pflicht ? text : `(${text})`,
        a.pronomen_pflicht
          ? null
          : h('span', { class: 'leise',
                        text: ' — darf mitgeschrieben werden' })));
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
    this.umschriftSetzen(fertig ? null : feld);
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

  /** »Tipp« und »Weiß ich nicht« — direkt unter dem Antwortfeld.
   *
   * »Kann die Tipp-Schaltfläche näher an das Eingabefenster heran.«
   *
   * Sie standen am Fuß der Seite, zwischen »Aussetzen« und »Schluss
   * für heute«. Das ist die falsche Nachbarschaft: die beiden gehören
   * zum ANTWORTEN und nicht zur Verwaltung der Aufgabe. Wer feststeckt,
   * sucht sie neben dem Feld, in dem er feststeckt.
   *
   * Der Tipp steht vor »Weiß ich nicht«: er ist das Kleinere, und wer
   * ihn zuerst sieht, greift nicht gleich zur Lösung.
   */
  teilHilfen() {
    if (this.phase === 'rueckmeldung') return null;
    return h('div', { class: 'hilfen' },
      h('button', {
        class: 'schlicht',
        title: 'Ein Anstoß, ohne die Lösung zu zeigen',
        disabled: this.tipps >= 3,
        onclick: () => this.tippHolen(),
      }, this.tipps ? 'Noch ein Tipp' : 'Tipp'),
      h('button', { class: 'schlicht', onclick: () => this.weissNicht() },
        'Weiß ich nicht'));
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
          h('span', {},
            (z.pronomen || []).length
              ? h('span', { class: 'zeilenpronomen', lang: a.antwort_sprache,
                            text: z.pronomen.join('/') + ' ' })
              : null,
            z.beschriftung),
          // »wie bei:« davor, seit die Bedeutung des Wortes oben steht.
          // Ohne das las sich »ich ging immer wieder« unter »heißt:
          // arbeiten« wie die Übersetzung dieser Zeile — dabei
          // erklärt das Beispiel die ZEITFORM und nimmt dafür immer
          // dasselbe Verb. Derselbe Vorsatz steht bei der einzelnen
          // Form schon.
          z.beispiel
            ? h('span', { class: 'leise' },
                h('span', { class: 'leiser', text: 'wie bei: ' }), z.beispiel)
            : null),
        feld,
        r && r.urteil !== 'richtig'
          ? h('div', { class: 'reihenloesung', lang: a.antwort_sprache },
              (r.erwartet || []).join(' / '))
          : h('div', {})));
    }
    this.feld = felder[0] || null;
    // Bei der ganzen Reihe hängt die Umschrift an jedem Feld.
    if (this._umschriftReihe) this._umschriftReihe.forEach((f) => f());
    this._umschriftReihe = [];
    if (!fertig && this.umschrift && kannUmschreiben(this._antwortsprache?.code)) {
      for (const f of felder) {
        this._umschriftReihe.push(
          umschriftAnhaengen(f, this._antwortsprache.code));
      }
    }
    const unten = h('div', {});
    if (!fertig) {
      unten.append(h('div', { class: 'frage-werkzeuge' },
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

    kasten.append(h('div', { class: 'frage-werkzeuge' },
      h('button', { class: 'wichtig', onclick: () => this.weiter() }, 'Weiter'),
      h('button', {
        class: 'schlicht',
        onclick: () => {
          // Wer von Hand werten will, will gerade nicht weiter.
          this.sprungAbbrechen();
          this.sprungAus = true;
          this.wertungOffen = !this.wertungOffen;
          this.zeichnen();
        },
      }, this.wertungOffen ? 'Doch automatisch' : 'Anders werten')));

    // Eine Seite, die sich von allein bewegt, braucht eine Bremse in
    // Reichweite — und sie muss zu SEHEN sein, bevor sie sich bewegt.
    // Der Balken ist die ehrlichste Anzeige: er sagt nicht nur DASS
    // gleich etwas passiert, sondern auch wie viel Zeit noch bleibt.
    if (this.springtGleich()) {
      kasten.append(h('div', { class: 'sprung' },
        h('div', { class: 'sprungbalken' },
          h('i', { style: `animation-duration:${this.sprungdauer()}ms` })),
        h('button', {
          class: 'schlicht',
          onclick: () => { this.sprungAbbrechen(); this.sprungAus = true;
                           this.zeichnen(); },
        }, 'Hierbleiben')));
    }

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

  /* Das »Warum ist das so?« — die Grammatikregel, die gerade greift.
   *
   * Steht ÜBER dem »Warum kommt das jetzt?«: das eine beantwortet eine
   * Frage, die man beim Lernen wirklich hat, das andere erklärt den
   * Terminplan. Und zugeklappt, denn in der Abfrage will man zuerst
   * antworten — wer nachsehen will, klappt auf.
   */
  /** Ein Blick auf die Lösung deckelt die Bewertung — wie ein Tipp.
   *
   * Der Tipp wurde mitgezählt und deckelte auf »Schwer«; die Regel
   * und »Wort ansehen« zeigten dasselbe Wissen umsonst. Damit war das
   * Tippsystem freiwillig: wer nachsah, bekam »Gut«, und der
   * Terminplan rechnete mit einem Wissen, das es nicht gibt.
   *
   * NICHT gesperrt, sondern gezählt. Die Regel beim Antworten
   * nachzulesen ist beim Mittelhochdeutschen durchaus erwünscht — nur
   * umsonst darf es nicht sein.
   */
  nachgesehen() {
    if (this.phase === 'rueckmeldung') return;
    if (this.tipps < 3) this.tipps = 3;
  }

  teilRegeln() {
    const regeln = this.aufgabe.regeln || [];
    if (!regeln.length) return null;
    const offen = this.phase !== 'rueckmeldung';
    const kasten = h('details', { class: 'warum regel' },
      h('summary', {
        // Beim Aufklappen VOR der Antwort gilt dasselbe wie beim
        // Tipp: die Regel zeigt bei einer Formaufgabe die Bildung,
        // und das ist die halbe Lösung.
        onclick: () => { if (offen) this.nachgesehen(); },
        title: offen
          ? 'Zählt wie ein Tipp — die Bewertung bleibt dann bei »Schwer«.'
          : null,
      }, regeln.length === 1
        ? 'Warum ist das so?'
        : `Warum ist das so? (${regeln.length})`));
    if (offen) {
      kasten.append(h('p', { class: 'leise', style: 'margin:.2rem 0 .6rem',
        text: 'Nachsehen ist in Ordnung — es zählt wie ein Tipp, die '
            + 'Bewertung bleibt dann bei »Schwer«.' }));
    }
    for (const r of regeln) {
      kasten.append(h('h3', { class: 'regel-titel', text: r.titel }));
      // Absätze getrennt: eine Regel in einem Block ist unlesbar.
      for (const absatz of String(r.text || '').split(/\n{2,}/)) {
        if (absatz.trim()) kasten.append(h('p', { text: absatz.trim() }));
      }
      if (r.beispiele?.length) {
        kasten.append(h('ul', { class: 'regel-beispiele' },
          r.beispiele.map((b) => h('li', {},
            h('b', { text: b.form || b.text || '' }),
            b.bedeutung ? h('span', { text: ` — ${b.bedeutung}` }) : null))));
      }
    }
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
    // »Tipp« und »Weiß ich nicht« stehen NICHT mehr hier, sondern
    // gleich unter dem Antwortfeld (teilHilfen). Sie gehören zum
    // Antworten; hier stehen die Dinge, die man mit der AUFGABE macht.
    const reihe = h('div', { class: 'frage-werkzeuge',
                             style: 'width:100%' });
    reihe.append(
      h('button', {
        class: 'schlicht', title: 'Diese Aufgabe nicht mehr abfragen',
        onclick: () => tun(async () => {
            // Was ausgesetzt wurde, MERKEN — und zwar mitsamt dem
            // Wort. Die Meldung sagte früher »in den Einstellungen
            // wieder einschaltbar«; das war unwahr, es gab im ganzen
            // Frontend keinen einzigen Aufrufer für `fortsetzen`. Wer
            // auf dem Handy danebentippte, verlor das Wort endgültig
            // und erfuhr nie, warum es nicht mehr kommt.
            this.ausgesetzt = { kennung, lemma: this.aufgabe.frage_text,
                                typ: this.aufgabe.typ_name };
            await api.aussetzen(kennung);
            meldung('Ausgesetzt — oben steht, wie du es zurücknimmst.');
            this.naechste();
        }),
      }, 'Aussetzen'),
      // Nicht mehr `location.hash` — das riss die Abfrage ab, und zurück
      // kam man nicht. Das Wort wird eingeblendet, danach geht es weiter.
      h('button', {
        class: 'schlicht',
        title: this.phase === 'rueckmeldung'
          ? 'Dieses Wort ansehen, ohne die Abfrage zu verlassen'
          : 'Zählt wie ein Tipp — die Bewertung bleibt dann bei »Schwer«.',
        onclick: () => { this.nachgesehen(); this.wortZeigen(); },
      }, 'Wort ansehen'),
      // »Ebenfalls ein Knopf, wenn man eine Abfragerunde beenden
      // möchte, dass man zur Hauptseite gehen kann, damit man nicht im
      // Menü suchen muss — das versteht nicht jeder.«
      //
      // Der Weg hinaus führte bisher über den Pfeil in der Kopfzeile
      // oder über »Übersicht« im Menü. Beides ist ein Umweg über etwas,
      // das nicht nach Ausgang aussieht. Nichts geht dabei verloren:
      // jede Antwort ist längst gespeichert.
      h('button', {
        class: 'schlicht',
        title: 'Abfrage beenden und zurück zur Übersicht',
        onclick: () => { location.hash = '#/uebersicht'; },
        // Nach rechts abgesetzt: »Aussetzen« nimmt ein Wort dauerhaft
        // aus der Abfrage, »Schluss für heute« beendet nur die Runde.
        // Beide sahen gleich aus und standen zwei Finger nebeneinander
        // — auf dem Handy ist das eine Falle.
        style: 'margin-left:auto',
      }, 'Schluss für heute'));
    return reihe;
  }

  /* ------------------------------------------------------------- Ablauf */

  /** Springt der Trainer nach dieser Antwort von selbst weiter?
   *
   * »Jede Aufgabe kostet auf dem Touchgerät einen zweiten Tipp.« Der
   * zweite ist »Weiter«, und nach einer sauber richtigen Antwort steht
   * in der Rückmeldung nichts mehr, was man lesen müsste.
   *
   * Die vier Ausschlüsse sind der ganze Punkt — ohne sie wäre das hier
   * ein »Rückmeldung überspringen«, und genau die will man sehen:
   *   fast richtig  → die richtige Schreibung steht da
   *   nicht richtig → die Lösung steht da
   *   Tipp genommen → die Wertung ist auf »Schwer« gedeckelt
   *   nachgesehen   → dasselbe, und das Wort steht da
   * Dazu »Anders werten«: wer das aufklappt, will gerade nicht weiter.
   */
  springtGleich() {
    return this.weiterspringen
        && !this.sprungAus
        && this.phase === 'rueckmeldung'
        && this.ergebnis?.urteil?.urteil === 'richtig'
        && !this.tipps
        && !this.aufgedeckt
        && !this.wertungOffen;
  }

  /** Wie lange die Rückmeldung stehen bleibt.
   *
   * Im Legastheniemodus länger: dort wächst die Schrift, und gelesen
   * wird langsamer — eine Zeitspanne, die für die einen flott ist, ist
   * für die anderen ein Wegschnappen.
   */
  sprungdauer() { return this.lg?.aktiv ? 2400 : 1400; }

  sprungStarten() {
    this.sprungAbbrechen();
    if (!this.springtGleich()) return;
    this.sprung = setTimeout(() => { this.sprung = null; this.weiter(); },
                             this.sprungdauer());

    // Wer in dieser Sekunde irgendwo hinfasst — »Warum kommt das
    // jetzt?« aufklappt, die Regel liest, zum Aussetzen greift —, der
    // will nicht weggeschoben werden. Das hält an.
    //
    // Und zwar OHNE neu zu zeichnen: pointerdown kommt vor click, ein
    // Neuaufbau nähme dem Finger den Knopf unter der Berührung weg und
    // der Klick ginge ins Leere. Stattdessen hält der Balken sichtbar
    // an — das ist die Rückmeldung.
    this.sprungHalt = () => {
      this.sprungAbbrechen();
      this.sprungAus = true;
      const balken = this.behaelter.querySelector('.sprungbalken i');
      if (balken) balken.style.animationPlayState = 'paused';
    };
    this.behaelter.addEventListener('pointerdown', this.sprungHalt);
  }

  /** Die Uhr anhalten. Muss von überall aufrufbar sein, wo die Sitzung
   *  weitergeht oder endet — eine Uhr, die nach dem Seitenwechsel noch
   *  feuert, bewertet die nächste Aufgabe. Ebenso der Horcher: ein
   *  übrig gebliebener würde die nächste Berührung als »Hierbleiben«
   *  für eine Aufgabe lesen, die noch gar nicht gestellt ist. */
  sprungAbbrechen() {
    if (this.sprung) { clearTimeout(this.sprung); this.sprung = null; }
    if (this.sprungHalt) {
      this.behaelter.removeEventListener('pointerdown', this.sprungHalt);
      this.sprungHalt = null;
    }
  }

  /** Die Wertung in den Blick holen.
   *
   * »Jede Aufgabe kostet auf dem Touchgerät einen zweiten Tipp.« Auf
   * einem 390er Gerät landet »Weiter« rechnerisch bei etwa 600 px in
   * einem nutzbaren Bereich von 636 — also auf der Kante. Im
   * Legastheniemodus wachsen Frage, Feld und Rückmeldung gleichzeitig,
   * und der Knopf liegt sicher darunter. In der ganzen Datei stand
   * kein einziges scrollIntoView.
   *
   * `block: 'nearest'` scrollt nur, wenn es nötig ist — wer die
   * Wertung ohnehin schon sieht, dem springt nichts weg.
   */
  wertungZeigen() {
    this.behaelter.querySelector('.wertung, .rueckmeldung')
      ?.scrollIntoView({ block: 'nearest' });
  }

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
        denkzeit_ms: this.warVersteckt ? null : this.denkzeit,
        versuche: this.versuche,
        // MITSCHICKEN. Der Server kennt das Feld seit jeher und
        // deckelt damit auf »Schwer« — nur schickte die Oberfläche es
        // nie. Der Satz im Kommentar bei `tippHolen` (»Ein genommener
        // Tipp deckelt die Bewertung«) stimmte deshalb nicht: das
        // ganze Tippsystem war umsonst zu haben.
        tipps: this.tipps,
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
    this.wertungZeigen();
    this.sprungStarten();
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
      this.wertungZeigen();
    } catch (fehler) {
      meldung(fehler.message);
    } finally {
      this.laeuft = false;
    }
  }

  /** Weiter zur nächsten Aufgabe. Ohne `note` gilt die automatische
   *  Bewertung; mit `note` ist es ein Eingriff von Hand. */
  async weiter(note = null) {
    // ZUERST die Uhr anhalten, nicht erst nach der Prüfung darunter:
    // sonst liefe sie weiter, wenn hier wegen `laeuft` abgebrochen
    // wird — und feuerte in die nächste Aufgabe hinein.
    this.sprungAbbrechen();
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
        denkzeit_ms: this.warVersteckt ? null : this.denkzeit,
        versuche: this.versuche,
        aufgedeckt: Boolean(this.aufgedeckt),
        tipps: this.tipps,
      });
      this.gezaehlt.gesamt += 1;
      // Die Rücknahmezeile gilt für die EINE Aufgabe danach. Wer
      // weiterlernt, hat sich entschieden.
      this.ausgesetzt = null;
      // Was sich am Lernstand geändert hat. Der Zustand VOR der Antwort
      // steht in der Aufgabe, der danach in der Antwort — beide liegen
      // hier vor, und keiner davon kostet eine weitere Anfrage.
      const vorher = this.aufgabe.lernstand?.zustand || 'neu';
      const nachher = ergebnis.zustand;
      if (vorher === 'neu' && nachher !== 'neu') this.wandel.angefangen += 1;
      if (vorher !== 'reif' && nachher === 'reif') this.wandel.sitzt += 1;
      if (vorher === 'verlernt' && nachher !== 'verlernt') {
        this.wandel.zurueck += 1;
      }
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
        // Der Ring in der Kopfzeile zählt mit — ohne Rückfrage beim
        // Server. Die Zahl liegt ja hier.
        spielzeichen.fortschreiben(this.pensum.heute_erledigt);
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
