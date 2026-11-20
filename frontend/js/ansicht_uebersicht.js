/* Profilwahl und Übersicht über die Sammlungen. */

import { api } from './api.js';
import { h, leeren, meldung, anfuegen, lesbareSchrift } from './hilfen.js';
import { stammdaten } from './stammdaten.js';
import { zustand, merken } from './zustand.js';
import * as fuehrung from './fuehrung.js';
import * as zuspruch from './ansicht_zuspruch.js';

export async function zeichnenProfile(behaelter, zurueckNach = null) {
  const leute = await api.benutzer();
  const el = leeren(behaelter);
  el.append(h('h1', { text: 'Wer lernt?' }));
  if (zurueckNach) {
    el.append(h('p', { class: 'leise',
      text: 'Auf diesem Gerät ist noch kein Profil gewählt. Danach geht es '
          + 'dorthin weiter, wo du hinwolltest.' }));
  }
  if (!leute.length) {
    el.append(h('p', { text: 'Noch kein Profil angelegt. Jeder bekommt eigene '
                           + 'Sammlungen und einen eigenen Lernstand.' }));
  }
  el.append(h('div', { class: 'karte-reihe' },
    leute.map((p) => h('button', {
      class: 'karte klickbar',
      onclick: () => {
        merken({ benutzerId: p.id, sammlungId: null });
        location.hash = zurueckNach || '#/uebersicht';
      },
    },
      h('div', { style: 'display:flex;align-items:center;gap:.75rem' },
        profilpunkt(p), h('strong', { text: p.name }))))));

  const name = h('input', { type: 'text', placeholder: 'Name', maxlength: '60' });
  const farbe = h('input', { type: 'color', value: '#6b7fd7', style: 'width:3rem;padding:.2rem' });
  el.append(h('div', { class: 'karte', style: 'margin-top:1.5rem' },
    h('h2', { style: 'margin-top:0', text: 'Neues Profil' }),
    h('div', { style: 'display:flex;gap:.5rem;align-items:center' }, name, farbe,
      h('button', {
        class: 'wichtig',
        onclick: async () => {
          if (!name.value.trim()) { meldung('Der Name fehlt.'); return; }
          try {
            const neu = await api.benutzerAnlegen({ name: name.value.trim(), farbe: farbe.value });
            merken({ benutzerId: neu.id, sammlungId: null });
            location.hash = zurueckNach || '#/uebersicht';
          } catch (fehler) { meldung(fehler.message); }
        },
      }, 'Anlegen'))));
}

/* Was in dieser Sammlung auf Freigabe wartet, als lesbare Teile.
 *
 * Alle drei Arten zählen: Formen, Übungen und Grammatikregeln. Hinge
 * der Knopf nur an den Formen, bliebe er unsichtbar, sobald allein eine
 * Regel wartet — und die läge dann unerreichbar in der Freigabe.
 */
function wartendes(s) {
  const teile = [];
  if (s.offene_formen) teile.push(`${s.offene_formen} Formen`);
  if (s.offene_uebungen) teile.push(`${s.offene_uebungen} Übungen`);
  if (s.offene_regeln) {
    teile.push(`${s.offene_regeln} ${s.offene_regeln === 1 ? 'Regel' : 'Regeln'}`);
  }
  return teile;
}

/* Der farbige Punkt mit dem Anfangsbuchstaben.
 *
 * Die Farbe geht über das CSSOM, nicht über ein style-ATTRIBUT. Im
 * Attribut stünde sie in einer ganzen Deklarationsliste, und ein
 * Semikolon darin genügte: »#fff;position:fixed;inset:0;…« legte eine
 * bildschirmfüllende Fläche über die Oberfläche und könnte obendrein
 * ein Bild von einer fremden Adresse nachladen. `.style.background`
 * nimmt dagegen nur eine gültige Farbe an und verwirft alles andere.
 * (Im Modell steht zusätzlich ein Muster — zwei Schlösser.)
 */
function profilpunkt(p) {
  const punkt = h('span', { class: 'profil-knopf',
                            text: (p.name || '?').slice(0, 1).toUpperCase() });
  punkt.style.background = p.farbe || '';
  punkt.style.color = lesbareSchrift(p.farbe);
  return punkt;
}

const SORTIERUNG = 'vokabeltrainer.sammlungen.sortierung';
const EINGEKLAPPT = 'vokabeltrainer.sammlungen.eingeklappt';

const ORDNUNGEN = [
  ['name', 'Name'],
  ['faellig', 'Fälliges zuerst'],
  ['zuletzt', 'zuletzt gelernt'],
];

function gelesen(schluessel, standard) {
  try { return JSON.parse(localStorage.getItem(schluessel)) ?? standard; }
  catch { return standard; }
}

function geschrieben(schluessel, wert) {
  try { localStorage.setItem(schluessel, JSON.stringify(wert)); }
  catch { /* privates Fenster */ }
}

const eingeklappt = () => gelesen(EINGEKLAPPT, []);

function einklappen(id, zu) {
  const alle = new Set(eingeklappt());
  if (zu) alle.add(id); else alle.delete(id);
  geschrieben(EINGEKLAPPT, [...alle]);
}

/** Sortiert die Sammlungen nach der gemerkten Ordnung.
 *
 * Die Reihenfolge ist eine Ansichtssache und bleibt deshalb im
 * Browser — sie gehört zum Gerät, nicht zum Bestand. Wer am Telefon
 * nach Fälligem ordnet, will das am Rechner nicht unbedingt auch.
 */
function geordnet(sammlungen, staende) {
  const wie = gelesen(SORTIERUNG, 'name');
  const kopie = [...sammlungen];
  if (wie === 'faellig') {
    // Die Fälligkeiten stehen in den Ständen, die die Übersicht
    // ohnehin holt — nicht in der Sammlungsliste. Sie dort noch
    // einmal zu zählen hieße, dieselbe Zahl an zwei Orten zu rechnen.
    const faellig = (x) => staende[sammlungen.indexOf(x)]?.faellig || 0;
    // Stabil: bei gleich vielen Fälligen bleibt die Namensfolge.
    return kopie.sort((a, b) => faellig(b) - faellig(a)
                              || a.name.localeCompare(b.name, 'de'));
  }
  if (wie === 'zuletzt') {
    return kopie.sort((a, b) => String(b.zuletzt_gelernt || '')
                                  .localeCompare(String(a.zuletzt_gelernt || ''))
                              || a.name.localeCompare(b.name, 'de'));
  }
  return kopie.sort((a, b) => a.name.localeCompare(b.name, 'de'));
}

function teilSortierung(behaelter) {
  const wahl = h('select', {},
    ORDNUNGEN.map(([wert, text]) => h('option', { value: wert, text })));
  wahl.value = gelesen(SORTIERUNG, 'name');
  wahl.addEventListener('change', () => {
    geschrieben(SORTIERUNG, wahl.value);
    zeichnen(behaelter);
  });
  const zu = eingeklappt().length;
  return h('p', { class: 'leise sortierzeile' },
    'Sortiert nach ', wahl,
    zu
      ? h('button', {
          class: 'schlicht',
          onclick: () => { geschrieben(EINGEKLAPPT, []); zeichnen(behaelter); },
        }, `${zu} eingeklappt — alle zeigen`)
      : null);
}

/** Eine eingeklappte Sammlung: Name, Farbe, das Nötigste. */
function teilEingeklappt(behaelter, s, stand) {
  // EINE Zeile: Name, Zahl, zwei Knöpfe. Vorher standen Name und
  // Knöpfe untereinander, und im Raster wurde der Kasten auf die Höhe
  // der ausgeklappten Karte gestreckt — eingeklappt sah nach mehr aus
  // als ausgeklappt.
  return h('div', {
    class: 'karte sammlungskarte eingeklappt',
    style: `--sammlungsfarbe:${s.farbe_wirksam || 'var(--rand)'}`,
  },
    h('strong', { text: s.name }),
    h('span', { class: 'leise',
                text: `${stand?.faellig || 0} fällig · ${s.lexeme ?? 0} Wörter` }),
    h('span', { class: 'eingeklappt-knoepfe' },
      h('button', {
        onclick: () => { merken({ sammlungId: s.id, lektionId: null });
                         location.hash = '#/lernen'; },
      }, 'Lernen'),
      h('button', {
        onclick: () => { einklappen(s.id, false); zeichnen(behaelter); },
      }, 'Ausklappen')));
}


/** Die Karte für den Anfang: Rundgänge und der Übungskurs.
 *
 * Sie verschwindet, sobald alle Rundgänge einmal gesehen sind — ein
 * Hinweis, der nach dem zwanzigsten Mal noch dasteht, wird zu
 * Hintergrundrauschen, und dann liest man auch den nächsten nicht mehr.
 * Über die Anleitung bleiben die Rundgänge erreichbar.
 */
function willkommen(behaelter, sammlungen) {
  if (fuehrung.alleGesehen() && sammlungen.length) return null;

  const karte = h('div', { class: 'karte' });
  karte.append(h('h2', { style: 'margin-top:0',
                         text: sammlungen.length
                           ? 'Noch nicht überall gewesen?'
                           : 'Willkommen' }));
  if (!sammlungen.length) {
    karte.append(h('p', {},
      'Du hast noch keine Sammlung. Du kannst eine anlegen — oder '
      + 'erst einmal einen kleinen englischen Übungskurs einrichten, '
      + 'an dem sich alles ausprobieren lässt: Vokabeln, Formen, '
      + 'Sätze, ein Lesetext und eine Grammatikregel.'));
    karte.append(h('button', {
      class: 'wichtig',
      onclick: async (e) => {
        e.target.disabled = true;
        try {
          const d = await api.beispielkursAnlegen(zustand.benutzerId);
          merken({ sammlungId: d.sammlung_id });
          meldung(d.neu ? `Übungskurs angelegt: ${d.aufgaben} Aufgaben.`
                        : 'Der Übungskurs war schon da.');
          zeichnen(behaelter);
        } catch (f) {
          meldung(f.message, 'fehler');
          e.target.disabled = false;
        }
      },
    }, 'Übungskurs einrichten'));
  }

  karte.append(h('p', { style: 'margin:.8rem 0 .4rem' },
    h('b', { text: 'Ausführlich: ' }),
    h('a', { href: '#/lehrgang' }, 'der Lehrgang'),
    ' — zwei Spuren, neun Kapitel, jedes zum Mitmachen.'));
  karte.append(h('p', { class: 'leise', style: 'margin:.4rem 0',
                        text: 'Oder kurze Rundgänge durch die Oberfläche:' }));
  const reihe = h('div', { class: 'gruppenwahl' });
  for (const r of fuehrung.RUNDGAENGE) {
    reihe.append(h('button', {
      type: 'button',
      class: fuehrung.schonGesehen(r.kennung) ? 'schlicht' : '',
      title: `${r.beschreibung} (${r.dauer})`,
      onclick: () => fuehrung.starten(r.kennung),
    }, fuehrung.schonGesehen(r.kennung) ? `${r.name} ✓` : r.name));
  }
  karte.append(reihe);
  karte.append(h('p', { style: 'margin:.7rem 0 0' },
    h('button', {
      class: 'schlicht',
      onclick: () => {
        fuehrung.alleAusblenden();
        meldung('Ausgeblendet. Unter Anleitung findest du die Rundgänge '
              + 'jederzeit wieder.', 4000);
        zeichnen(behaelter);
      },
    }, 'Diese Karte ausblenden')));
  return karte;
}


/** Wo stehe ich im Lehrwerk — als eine Zeile auf der Karte.
 *
 * »Jetzt muss ich fragen, wo ich eine Lektionsnummer eintragen soll.«
 * Die Einstellung lag zweieinhalb Bildschirme tief in den
 * Sammlungseinstellungen, hinter sechsundzwanzig Ankreuzfeldern. Eine
 * Einstellung, die man nicht findet, gibt es nicht — also steht hier,
 * was gilt, und ein Weg direkt dorthin.
 *
 * Nur eine Zeile, und nur wenn es Lektionen gibt: wo kein Lehrwerk
 * ist, gibt es auch keinen Stand darin.
 */
function lehrwerkZeile(s) {
  if (!s.lektionen) return null;
  const hin = (e) => {
    e.preventDefault();
    merken({ sammlungId: s.id });
    location.hash = '#/einstellungen/lehrgang';
  };
  return h('p', { class: 'leise', style: 'margin:.3rem 0 0' },
    s.bis_lektion
      ? `Lehrwerk: bei Lektion ${s.bis_lektion} von ${s.lektionen} · `
      : `Lehrwerk: ${s.lektionen} Lektionen, alle dabei · `,
    h('a', { href: '#/einstellungen/lehrgang', onclick: hin },
      s.bis_lektion ? 'ändern' : 'Lektion eintragen'));
}


/** »Gezielt üben« — Verben, Adjektive, eine einzelne Zeitform.
 *
 * »Dann brauchen wir noch ein paar mehr Lernmodi: Verben lernen, Zeiten
 * lernen, bestimmte Worttypen, k.A. Adjektive oder so.«
 *
 * Ein Modus ist KEIN eigener Mechanismus, sondern ein Ausschnitt —
 * dieselben Begriffe, die auch der Umfang eines Lernziels kennt, und
 * dieselben Spalten in der Abfrage. Ein zweiter Weg daneben liefe
 * früher oder später auseinander; genau das war bei den Übungen schon
 * einmal passiert.
 *
 * Er gilt für diese Sitzung und wird nicht gespeichert. Wer heute nur
 * Verben übt, soll morgen nicht unbemerkt darin hängen.
 */
async function modusWaehlen(behaelter, s) {
  let gruppen = { wortarten: {} };
  let vorhanden = [];
  try {
    [gruppen, vorhanden] = await Promise.all([
      api.formgruppen(s.sprache), api.wortarten(s.id),
    ]);
  } catch (fehler) { meldung(fehler.message, 'fehler'); }

  const el = leeren(behaelter);
  el.append(h('h1', { text: 'Gezielt üben' }));
  el.append(h('p', { class: 'leise',
    text: `${s.name} — ein Ausschnitt statt des ganzen Plans, und ohne `
        + 'Tagesdosis: hier wird geübt, solange du magst. Der Lernstand '
        + 'zählt ganz normal mit. Beim nächsten »Lernen« gilt wieder '
        + 'der Plan.' }));

  // FREIES Üben, nicht der Plan.
  //
  // Mit dem Plan kam »Nichts zu tun«, sobald die Tagesdosis an neuen
  // Wörtern verbraucht war und zufällig nichts aus dem gewählten
  // Ausschnitt fällig stand — gemessen: 737 Adjektivaufgaben, und die
  // Abfrage lieferte null. Das ist rechnerisch richtig und als Angebot
  // unbrauchbar: wer ein Thema anklickt, will es üben. Der Lernstand
  // zählt dabei normal mit, nur der Terminplan steuert nicht.
  const starten = (modus, name) => {
    merken({ sammlungId: s.id, lektionId: null,
             lernmodus: { ...modus, nur: 'frei' } });
    meldung(`Gezielt üben: ${name}`);
    location.hash = '#/lernen';
  };

  const nachWortart = h('div', { class: 'karte' },
    h('h2', { style: 'margin-top:0', text: 'Nach Wortart' }),
    h('div', { class: 'gruppenwahl' },
      ...vorhanden.map((w) => h('button', {
        type: 'button',
        onclick: () => starten({ wortart: [w.wortart] },
                               wortartName(w.wortart)),
      }, `${wortartName(w.wortart)} · ${w.aufgaben}`))));

  // Jede Formgruppe einzeln — das ist das »Zeiten lernen«. Mit der
  // Wortart davor, weil »maskulin Nominativ Singular« bei Adjektiv,
  // Pronomen, Artikel und Zahlwort gleich heißt.
  const zeiten = h('div', { class: 'karte' },
    h('h2', { style: 'margin-top:0', text: 'Nach Zeit oder Tabelle' }));
  for (const [wortart, liste] of Object.entries(gruppen.wortarten || {})) {
    if (!liste.length) continue;
    zeiten.append(h('h3', { text: wortartName(wortart) }),
      h('div', { class: 'gruppenwahl' },
        ...liste.map((g) => h('button', {
          type: 'button',
          onclick: () => starten({ formgruppe: [g.kennung] }, g.name),
        }, g.name))));
  }

  el.append(nachWortart);
  if (vorhanden.length) el.append(zeiten);
  el.append(h('div', { class: 'frage-werkzeuge' },
    h('button', { onclick: () => { merken({ lernmodus: null });
                                   zeichnen(behaelter); } },
      'Zurück')));
}


/** Schalter »lerne ich diese Sammlung aktiv« — samt Erklärung daneben.
 *
 * Die Vorgabe steckt im Rücken: eigene Sammlungen ja, fremde nein. Hier
 * steht nur, was gerade gilt, und wie man es umdreht.
 */
function lernwahlZeile(s) {
  const schalter = h('input', { type: 'checkbox' });
  schalter.checked = Boolean(s.lerne_ich);
  const text = h('span', {});
  const beschriften = () => {
    text.textContent = schalter.checked
      ? 'Wird allgemein mitgelernt'
      : 'Nur ansehen und pflegen';
  };
  beschriften();
  schalter.addEventListener('change', async () => {
    schalter.disabled = true;
    const gewollt = schalter.checked;
    try {
      await api.lernwahlSetzen(s.id, zustand.benutzerId, gewollt);
      beschriften();
      meldung(gewollt
        ? `»${s.name}« wird jetzt mitgelernt.`
        : `»${s.name}« kommt in der allgemeinen Abfrage nicht mehr vor. `
          + 'Über den Knopf »Lernen« auf dieser Karte geht es weiterhin.');
      // Die Zahlen auf der Karte und oben zählen denselben Topf — sie
      // müssen mit. Sonst stünde dort gleich ein Wert, den die Abfrage
      // nicht einlöst.
      zeichnen(document.getElementById('inhalt'));
    } catch (fehler) {
      schalter.checked = !gewollt;
      beschriften();
      meldung(fehler.message, 'fehler');
    } finally {
      schalter.disabled = false;
    }
  });
  return h('label', {
    class: 'leise',
    style: 'display:flex;align-items:center;gap:.4rem;margin:.4rem 0 0;'
         + 'cursor:pointer',
  }, schalter, text);
}


/** Stufe, Punkte und der Weg zur nächsten — eine Zeile, kein Kasten.
 *
 * Die Punkte sind Beiwerk, und so sollen sie auch dastehen: unter den
 * Zahlen, die etwas über den Lernstand sagen, nicht über ihnen. Wer
 * eine Stufe aufsteigt, merkt es trotzdem.
 */
/** Die Ziele mit Termin — über allem Allgemeinen.
 *
 * »Die sind ja das, worauf der Fokus liegen sollte, wenn welche mit
 * Terminen da sind.« Und das stimmt doppelt: sie standen nicht nur
 * unter der Heute-Karte, sondern auch noch unter dem Bücherregal —
 * fünfter Block. In einem Profil stand dort »heute fällig, 60 offen«.
 *
 * ENTSCHEIDEND ist aber nicht die Reihenfolge, sondern der Knopf: der
 * große »Lernen« auf der Heute-Karte kennt die Lernziele NICHT. Er
 * startet die planmäßige Abfrage über den ganzen Bestand; ein Ziel
 * steuert die Abfrage nur über seinen eigenen Weg. Gemessen am echten
 * Stand lieferte »Lernen« Karotte, Minimarkt und Reis, während das
 * Ziel, das in zwei Tagen ablief, bei Lektion 2 und 3 stand.
 *
 * Darum ist die Zeile hier der Knopf, der genau dieses Ziel startet —
 * sonst zeigte sie einen Termin an und ließe einen damit allein.
 *
 * NUR MIT TERMIN. Ein Ziel ohne Termin ist ein Vorhaben und gehört
 * nach unten; hier oben steht, was eine Frist hat. Und nur drei: der
 * Streifen soll die Heute-Karte nicht unter die Falz schieben, sonst
 * wäre die Heilung schlimmer als die Krankheit.
 */
function teilTermine(ziele) {
  const mitTermin = (ziele || [])
    .filter((z) => z.termin && z.aktiv && (z.fortschritt?.gesamt || 0) > 0)
    .sort((a, b) => a.termin.localeCompare(b.termin))
    .slice(0, 3);
  if (!mitTermin.length) return null;

  const streifen = h('div', { class: 'termine' });
  for (const z of mitTermin) {
    const f = z.fortschritt || {};
    const tage = f.tage_bis_termin;
    // Heute oder vorbei: das ist kein Hinweis mehr, das ist eine Lage.
    const dringend = typeof tage === 'number' && tage <= 0;
    streifen.append(h('button', {
      class: 'termin' + (dringend ? ' dringend' : ''),
      title: `»${z.name}« jetzt lernen`,
      onclick: () => {
        merken({ lernzielId: z.id });
        location.hash = `#/lernen/ziel/${z.id}`;
      },
    },
      h('span', { class: 'termin-kopf' },
        h('strong', { text: z.name }),
        h('span', { class: 'termin-lage', text: f.lage || '' })),
      h('span', { class: 'zielbalken' },
        h('i', { style: `width:${Math.round((f.anteil || 0) * 100)}%` })),
      h('span', { class: 'termin-fuss' },
        h('span', { class: 'leise',
                    text: `${f.geschafft ?? 0} von ${f.gesamt ?? 0}` }),
        h('span', { class: 'termin-los', text: 'Lernen \u203a' }))));
  }
  return streifen;
}


function stufenzeile(spielstand) {
  if (!spielstand) return null;
  const p = spielstand.punkte;
  const st = p.stufe;
  const teile = [h('b', { text: `Stufe ${st.nummer}: ${st.name}` }),
                 ` · ${p.gesamt.toLocaleString('de-DE')} Punkte`];
  if (st.naechste !== null) {
    teile.push(` · noch ${(st.naechste - p.gesamt).toLocaleString('de-DE')} `
             + `bis »${naechsterName(st)}«`);
  }
  if (p.heute) {
    teile.push(` · heute ${p.heute}`);
    if (p.heute_verdoppelt) teile.push(' (verdoppelt)');
  }
  return teile;
}


function naechsterName(st) {
  // Der Name der nächsten Stufe steht nicht in der Antwort — die Stufe
  // schon, und die Reihenfolge ist fest. Ihn mitzuschicken hieße, die
  // Leiter an zwei Orten zu führen.
  return STUFENNAMEN[st.nummer] || '…';
}

// Nur für die Beschriftung »noch so viel bis …«. Die Wahrheit steht im
// Server (spiel.STUFEN); hier liegt eine Abschrift der NAMEN, nicht der
// Schwellen — die kommen mit der Antwort.
const STUFENNAMEN = ['Buchstaben', 'Wörter', 'Sätze', 'Absätze', 'Seiten',
                     'Kapitel', 'Bücher', 'Regal', 'Bibliothek'];


export async function zeichnen(behaelter) {
  const el = leeren(behaelter);
  const [sammlungen, sprachen] = await Promise.all([
    api.sammlungen(zustand.benutzerId), stammdaten.sprachen(),
  ]);
  const gesamt = await api.stand(zustand.benutzerId, null);
  // Beides zusammen, bevor gezeichnet wird: die Zuspruchkarte steht
  // GANZ OBEN, und was oben steht, darf nicht nachträglich
  // hineinspringen und den Rest nach unten schieben.
  const [spielstand, post] = await Promise.all([
    api.spiel(zustand.benutzerId).catch(() => null),
    api.zuspruch(zustand.benutzerId).catch(() => null),
  ]);

  // Der Einstieg ganz oben: Rundgänge und, solange nichts da ist, der
  // Übungskurs. Weiter unten zwischen den Sammlungen fände ihn niemand,
  // der zum ersten Mal hier ist — und für den ist er gemacht.
  // `anfuegen`, nicht `append`: die Karte ist null, sobald alle
  // Rundgänge gesehen sind, und `append(null)` schreibt das Wort
  // »null« in die Seite. Genau davor warnt der Kommentar bei
  // `anfuegen` — ich habe ihn überlesen und es stand oben auf
  // der Übersicht.
  // Vor allem anderen: ein Satz von der Mutter ist wichtiger als die
  // Zahl der fälligen Aufgaben. Wer ihn erst nach dem Scrollen fände,
  // fände ihn nicht.
  // Einmal geholt, zweimal gebraucht: oben für die Termine, unten für
  // den Abschnitt. Vorher stand derselbe Aufruf zweimal in dieser
  // Funktion.
  const ziele = await api.lernziele(zustand.benutzerId).catch(() => []);
  anfuegen(el, post && zuspruch.karteFuerMich(
    behaelter, post.fuer_mich, ziele, () => zeichnen(behaelter)));

  anfuegen(el, willkommen(behaelter, sammlungen));

  el.append(h('h1', { text: 'Heute' }));
  // Was einen Termin hat, steht VOR dem Allgemeinen — und ist der
  // Knopf, der genau das startet.
  anfuegen(el, teilTermine(ziele));
  el.append(h('div', { class: 'karte' },
    h('div', { class: 'zahlen' },
      zahlKasten(gesamt.faellig, 'fällig', 'faellig'),
      zahlKasten(gesamt.verlernt, 'verlernt', 'verlernt'),
      zahlKasten(gesamt.neu, 'neu', 'neu'),
      zahlKasten(gesamt.reif, 'sitzt'),
      zahlKasten(gesamt.gesamt, 'Aufgaben insgesamt')),
    h('div', { class: 'frage-werkzeuge', style: 'margin-top:1rem' },
      h('button', {
        class: 'wichtig',
        disabled: !(gesamt.faellig + gesamt.verlernt + gesamt.neu),
        onclick: () => { merken({ sammlungId: null }); location.hash = '#/lernen'; },
      }, 'Lernen'),
      // »Haben wir eigentlich auch eine Art Wiederholungsmodus?«
      //
      // Der Lernkern konnte es längst (nur=faellig), es führte nur
      // kein Knopf dorthin. Der Unterschied zu »Lernen« ist nicht
      // kosmetisch: planmäßig kommt NEUES dazu, sobald Platz ist.
      // Wer vor einer Arbeit steht oder wenig Zeit hat, will genau
      // das nicht — er will festigen, was schon angefangen ist.
      h('button', {
        disabled: !(gesamt.faellig + gesamt.verlernt),
        title: gesamt.faellig + gesamt.verlernt
          ? 'Nur Fälliges und Verlerntes — nichts Neues kommt dazu.'
          : 'Heute ist nichts fällig.',
        onclick: () => { merken({ sammlungId: null });
                         location.hash = '#/lernen/faellig'; },
      }, `Wiederholen (${gesamt.faellig + gesamt.verlernt})`),
      h('button', { onclick: () => { merken({ sammlungId: null }); location.hash = '#/lernen/frei'; } },
        'Frei üben'),
      h('button', { onclick: () => { merken({ sammlungId: null }); location.hash = '#/lernen/fehler'; } },
        'Fehler wiederholen'),
      // Ohne Rand sahen diese beiden in einer Reihe aus gerahmten
      // Knöpfen nach Text aus — sichtbar wurden sie erst beim
      // Überfahren, und auf dem Handy fährt niemand über etwas.
      h('button', { onclick: () => { location.hash = '#/statistik'; } },
        'Fortschritt'),
      // Erst zeigen, wenn es überhaupt jemanden gibt, dem man etwas
      // schicken darf. Ein Knopf, hinter dem »geht nicht« steht, ist
      // schlimmer als keiner.
      (post && post.empfaenger.length)
        ? h('button', { onclick: () => { location.hash = '#/zuspruch'; } },
            'Zuspruch schicken')
        : null),
    anfuegen(h('p', { class: 'leise', style: 'margin:.8rem 0 0' }),
             stufenzeile(spielstand))));

  // Lernziele: Ausschnitte des Bestands mit Termin, auch über Lektionen
  // und Sammlungen hinweg. Hier stehen ALLE — die mit Termin sind oben
  // schon einzeln zu sehen, die ohne nur hier.
  //
  // Vor den Büchern: ein Regal ist Stöbern, ein Ziel ist eine Zusage.
  el.append(h('h2', { text: 'Lernziele' }));
  if (ziele.length) {
    const reihe = h('div', { class: 'karte-reihe' });
    for (const z of ziele.slice(0, 4)) {
      const f = z.fortschritt || {};
      reihe.append(h('button', {
        class: 'karte klickbar',
        onclick: () => { location.hash = '#/ziele'; },
      },
        h('strong', { text: z.name }),
        h('p', { class: 'leise', style: 'margin:.2rem 0 .4rem',
                 text: f.lage || 'ohne Termin' }),
        h('div', { class: 'zielbalken' },
          h('i', { style: `width:${Math.round((f.anteil || 0) * 100)}%` })),
        h('p', { class: 'leise', style: 'margin:.3rem 0 0',
                 text: `${f.geschafft ?? 0} von ${f.gesamt ?? 0}` })));
    }
    el.append(reihe);
  } else {
    el.append(h('p', { class: 'leise',
      text: 'Noch keins. Ein Lernziel ist ein Ausschnitt des Bestands mit '
          + 'Termin — auch über Lektionen und Sammlungen hinweg. Der Trainer '
          + 'rechnet daraus aus, wie viel täglich dran sein muss.' }));
  }
  el.append(h('div', { class: 'frage-werkzeuge' },
    h('button', { onclick: () => { location.hash = '#/ziele'; } },
      ziele.length ? 'Alle Lernziele' : 'Lernziel anlegen')));

  // Bücher und Texte: eine eigene Karte, denn sie gehören dem Konto
  // und nicht einer Sammlung. Der Iwein gehört nicht zu
  // »Mittelhochdeutsch, Stammformen« — er ist Literatur, die man MIT
  // diesem Wortschatz liest.
  const buecher = await api.buecher(zustand.benutzerId).catch(() => []);
  const alleTexte = await api.alleTexte(zustand.benutzerId).catch(() => []);
  if (buecher.length || alleTexte.length) {
    const offeneAbschnitte = alleTexte.reduce(
      (summe, t) => summe + (t.abschnitte - t.uebersetzt), 0);
    el.append(h('h2', { text: 'Bücher und Texte' }));
    el.append(h('div', { class: 'karte' },
      h('div', { class: 'zahlen' },
        zahlKasten(buecher.length, buecher.length === 1 ? 'Buch' : 'Bücher'),
        zahlKasten(alleTexte.length, 'Texte'),
        zahlKasten(offeneAbschnitte, 'Abschnitte ohne Übersetzung')),
      h('div', { class: 'frage-werkzeuge',
                 style: 'margin-top:.8rem' },
        h('button', { class: 'wichtig',
                      onclick: () => { location.hash = '#/texte'; } },
          'Zum Regal'))));
  }

  el.append(h('h2', { text: 'Sammlungen' }));
  if (!sammlungen.length) {
    el.append(h('p', { class: 'leise', text: 'Noch keine Sammlung. Unten anlegen.' }));
  }
  // Die Reihe trägt einen eigenen Namen: `.karte-reihe` steht auf dieser
  // Seite dreimal — Profile, Lernziele, Sammlungen. Der Rundgang griff
  // damit die Lernzielkarte und erklärte dazu die Sammlungsknöpfe.
  anfuegen(el, sammlungen.length > 1 ? teilSortierung(behaelter) : null);
  const reihe = h('div', { class: 'karte-reihe sammlungen' });
  // Alle Zählungen auf einmal statt ein Rundlauf je Sammlung — das ist der
  // Startbildschirm, der soll nicht nach Sammlungszahl langsamer werden.
  const staende = await Promise.all(
    sammlungen.map((s) => api.stand(zustand.benutzerId, s.id).catch(() => ({}))));
  for (const [i, s] of geordnet(sammlungen, staende).entries()) {
    const stand = staende[sammlungen.indexOf(s)];
    const sprache = sprachen.find((x) => x.code === s.sprache);
    if (eingeklappt().includes(s.id)) {
      reihe.append(teilEingeklappt(behaelter, s, stand));
      continue;
    }
    reihe.append(h('div', {
      class: 'karte sammlungskarte',
      // Die Farbe als Kante, nicht als Fläche: sie soll zuordnen,
      // nicht schreien. Auf dunklem Grund trägt dieselbe Farbe.
      style: `--sammlungsfarbe:${s.farbe_wirksam || 'var(--rand)'}`,
    },
      h('div', { style: 'display:flex;justify-content:space-between;gap:.5rem' },
        h('strong', { text: s.name }),
        h('span', { class: 'marke', text: sprache ? sprache.name : s.sprache })),
      h('p', { class: 'leise', style: 'margin:.2rem 0 0',
               text: `${s.lexeme ?? 0} Wörter${s.eigen ? '' : ' · freigegeben'}` }),
      // Freigegeben heißt nicht gelernt. Wer ein fremdes Französisch
      // mitpflegt, bekam es bisher in der allgemeinen Abfrage zwischen
      // die griechischen Wörter gemischt, ohne eine Stelle, wo sich
      // das abstellen ließ. Der Schalter gehört hierher, zur Karte:
      // hier sieht man die fremden Sammlungen ja gerade.
      lernwahlZeile(s),
      lehrwerkZeile(s),
      // Ungeprüfte Formen werden nicht abgefragt. Wer das nicht weiß, sucht
      // vergeblich nach den Wörtern, die die KI gerade eingetragen hat —
      // darum steht es hier und nicht in einem Untermenü.
      // Was auf Freigabe wartet, in einer Zeile. Ungeprüftes wird nicht
      // abgefragt und nicht gezeigt — wer das nicht weiß, sucht
      // vergeblich nach dem, was die KI gerade eingetragen hat. Darum
      // steht es hier und nicht in einem Untermenü.
      wartendes(s).length
        ? h('p', { class: 'leise', style: 'margin:.3rem 0 0' },
            h('span', { class: 'marke warnung',
              text: wartendes(s).join(', ') + ' warten auf Freigabe' }))
        : null,
      h('div', { class: 'zahlen' },
        zahlKasten(stand.faellig, 'fällig', 'faellig'),
        zahlKasten(stand.neu, 'neu', 'neu'),
        zahlKasten(stand.verlernt, 'verlernt', 'verlernt')),
      h('div', { class: 'frage-werkzeuge', style: 'margin-top:.8rem' },
        h('button', {
          class: 'wichtig',
          onclick: () => { merken({ sammlungId: s.id, lektionId: null }); location.hash = '#/lernen'; },
        }, 'Lernen'),
        // Vor der Abfrage, nicht dahinter: wer eine Lektion neu
        // bekommt, macht sich erst vertraut und wird dann abgefragt.
        // In der Leiste steht es deshalb gleich neben »Lernen«.
        h('button', {
          onclick: () => { merken({ sammlungId: s.id, lektionId: null });
                           location.hash = '#/abtippen'; },
          title: 'Alle Wörter durchgehen und abtippen — die Lösung steht '
               + 'dabei. Zählt nicht für die Abfrage.',
        }, 'Abtippen'),
        h('button', {
          onclick: () => { merken({ sammlungId: s.id }); location.hash = '#/wortschatz'; },
        }, 'Wortschatz'),
        // »Texte« stand hier einmal — bei drei Sammlungen dreimal, jedes
        // Mal mit einem anderen Ausschnitt dahinter. Bücher und Texte
        // gehören dem Konto und haben jetzt ihre eigene Karte weiter
        // oben.
        //
        // Freigabe bleibt in der ersten Reihe, aber NUR solange etwas
        // wartet: das ist der eine Fall, der eine Handlung verlangt.
        wartendes(s).length
          ? h('button', {
              onclick: () => {
                merken({ sammlungId: s.id });
                location.hash = '#/freigabe';
              },
            }, 'Freigabe')
          : null),
      // Alles Weitere eine Klappe tiefer.
      //
      // Hier standen zehn gleich aussehende Knöpfe, davon neun ohne
      // Hervorhebung — bei drei Sammlungen über dreißig auf der
      // Startseite, bevor man überhaupt lernen kann. Was man täglich
      // braucht, sind drei; der Rest ist Einrichtung und wird im
      // Monat vielleicht einmal angefasst.
      h('details', { class: 'mehr-dazu' },
        h('summary', { text: 'Mehr mit dieser Sammlung' }),
        h('div', { class: 'frage-werkzeuge',
                   style: 'margin-top:.5rem' },
          h('button', {
            onclick: () => { merken({ sammlungId: s.id }); location.hash = '#/ueben'; },
          }, 'Sätze'),
          h('button', { onclick: () => modusWaehlen(behaelter, s) }, 'Gezielt üben'),
          h('button', {
            onclick: () => { merken({ sammlungId: s.id }); location.hash = '#/gezielt'; },
            title: 'Wort für Wort festlegen, was abgefragt wird — Eigennamen '
                 + 'und Abkürzungen stillegen, ohne sie zu löschen.',
          }, 'Auswahl'),
          h('button', {
            onclick: () => { merken({ sammlungId: s.id }); location.hash = '#/import'; },
          }, 'Einlesen'),
          h('button', {
            onclick: () => { merken({ sammlungId: s.id }); location.hash = '#/einstellungen'; },
          }, 'Einstellungen'),
          h('button', {
            title: 'Diese Karte einklappen',
            onclick: () => { einklappen(s.id, true); zeichnen(behaelter); },
          }, 'Einklappen')))));
  }
  el.append(reihe);
  el.append(await teilNeueSammlung(behaelter, sprachen));
}

function wortartName(w) {
  return { verb: 'Verben', substantiv: 'Substantive', adjektiv: 'Adjektive',
           adverb: 'Adverbien', pronomen: 'Pronomen', numerale: 'Zahlwörter',
           konjunktion: 'Konjunktionen', praeposition: 'Präpositionen',
           artikel: 'Artikel', wendung: 'Wendungen',
           sonstiges: 'Sonstiges' }[w] || w;
}

function zahlKasten(wert, beschriftung, art) {
  return h('div', { class: 'zahl' + (art ? ' ' + art : '') },
    h('b', { text: String(wert ?? 0) }), h('span', { text: beschriftung }));
}

async function teilNeueSammlung(behaelter, sprachen) {
  const name = h('input', { type: 'text', placeholder: 'z.B. Französisch, Lektion 1–5' });
  const sprache = h('select', {},
    sprachen.filter((s) => s.code !== 'de')
      .map((s) => h('option', { value: s.code, text: s.name })),
    h('option', { value: 'de', text: 'Deutsch' }));
  return h('details', { class: 'karte', style: 'margin-top:1.5rem' },
    h('summary', { text: 'Neue Sammlung anlegen' }),
    h('div', { style: 'display:grid;gap:.6rem;margin-top:.8rem' },
      name, sprache,
      h('button', {
        class: 'wichtig',
        onclick: async () => {
          if (!name.value.trim()) { meldung('Der Name fehlt.'); return; }
          try {
            const neu = await api.sammlungAnlegen({
              besitzer_id: zustand.benutzerId,
              name: name.value.trim(), sprache: sprache.value,
            });
            merken({ sammlungId: neu.id });
            meldung('Angelegt. Jetzt Wörter eintragen.');
            location.hash = '#/wortschatz';
          } catch (fehler) { meldung(fehler.message); }
        },
      }, 'Anlegen')));
}
