/** Texte lesen und übersetzen.
 *
 * Drei Ansichten in einer Datei, weil sie dieselbe Sache in drei
 * Zuständen sind: die Liste der Texte, der Einwurf eines neuen, und die
 * Werkbank, auf der übersetzt wird.
 *
 * Die Werkbank zeigt links den Abschnitt, rechts das eigene Feld. Jedes
 * Wort im Original ist anklickbar: ein Klick schlägt nach, was im
 * eigenen Wortschatz dazu steht. Steht nichts da, bietet derselbe Klick
 * an, das Wort für die KI zu merken — der Weg vom »das kenne ich nicht«
 * bis zum Eintrag ist damit zwei Klicks lang und verlässt die Seite
 * nicht.
 *
 * Dass er die Seite nicht verlässt, ist hier gelernt: »Wenn ich ein
 * Wort ansehe, weil ich es nicht weiß, dann komme ich nicht wieder
 * zurück zur Abfrage.« Dieselbe Falle wäre hier noch teurer — eine
 * halbe Stunde Übersetzungsarbeit hinge daran.
 */

import { api } from './api.js';
import { h, leeren, meldung, tun } from './hilfen.js';
import { zustand, merken } from './zustand.js';

const FARBE = {
  sitzt: 'wort-sitzt',
  lernen: 'wort-lernen',
  neu: 'wort-neu',
  unbekannt: 'wort-unbekannt',
};


// ------------------------------------------------------------- Textliste

/* Kapitelfilter und Auswahl — wie im Wortschatz, und bewusst gleich.
 *
 * »Die Texte müssten wir noch zusammenfassbar machen, also Text –
 * Kapitel. So ist das schwer für jemand, der damit lernt.«
 *
 * Der Iwein liegt in 173 Stücken vor. Als flache Liste ist das keine
 * Bedienung, sondern ein Stapel. Die Spalte text.lektion_id gab es
 * längst — bei den griechischen Texten ist sie sogar gefüllt (390 von
 * 392), nur sah man sie nirgends. */
let textFilter = '';
let textAngehakt = new Set();
let textSammlung = null;
const OHNE_KAPITEL = 'ohne';

export async function zeichnen(behaelter) {
  leeren(behaelter);
  if (!zustand.sammlungId) {
    behaelter.append(h('p', { class: 'leise',
      text: 'Erst eine Sammlung wählen — ein Text gehört zu einer Sprache.' }));
    behaelter.append(h('button', {
      onclick: () => { location.hash = '#/uebersicht'; },
    }, 'Zur Übersicht'));
    return;
  }
  if (textSammlung !== zustand.sammlungId) {
    textSammlung = zustand.sammlungId;
    textFilter = '';
    textAngehakt.clear();
  }

  behaelter.append(h('h1', { text: 'Texte' }));
  behaelter.append(h('p', { class: 'leise',
    text: 'Einen Text einwerfen und sehen, ob du ihn schon übersetzen '
        + 'könntest. Was dir fehlt, kannst du beim Lesen anfordern.' }));

  const [texte, kapitel] = await Promise.all([
    api.texte(zustand.sammlungId),
    api.lektionen(zustand.sammlungId).catch(() => []),
  ]);

  if (!texte.length) {
    behaelter.append(h('p', { class: 'leise', text: 'Noch kein Text.' }),
                     teilEinwerfen(behaelter));
    return;
  }

  // Nur anbieten, wo es etwas zu ordnen gibt. Bei drei Texten ist ein
  // Kapitelfilter Beiwerk; bei 173 ist er der einzige Weg hinein.
  const mitKapitel = [...new Set(texte.map((t) => t.lektion_id))];
  if (texte.length > 5 || mitKapitel.length > 1) {
    behaelter.append(teilKapitelwahl(behaelter, texte, kapitel));
  }

  const stapel = h('div', {});
  const liste = h('div', { class: 'karte-reihe' });
  behaelter.append(stapel, liste, teilEinwerfen(behaelter));

  const stapelZeichnen = () => {
    leeren(stapel);
    if (textAngehakt.size) {
      stapel.append(teilStapel(behaelter, kapitel, stapelZeichnen));
    }
  };

  const gezeigt = texte.filter((t) => (
    textFilter === '' ? true
      : textFilter === OHNE_KAPITEL ? t.lektion_id === null
        : String(t.lektion_id) === textFilter));

  if (!gezeigt.length) {
    liste.append(h('p', { class: 'leise',
      text: 'In diesem Kapitel liegt noch kein Text.' }));
    return;
  }

  let letztes;
  for (const t of gezeigt) {
    const kennung = t.lektion_id === null ? OHNE_KAPITEL : t.lektion_id;
    if (kennung !== letztes && !textFilter) {
      letztes = kennung;
      liste.append(h('h2', { class: 'kapitelkopf',
        text: t.lektion_id === null
          ? 'Ohne Kapitel'
          : (t.lektion_nr !== null ? `${t.lektion_nr}. ` : '')
            + (t.lektion_name || 'ohne Namen') }));
    }
    const haken = h('input', { type: 'checkbox', class: 'eintrag-haken',
                               title: 'auswählen' });
    haken.checked = textAngehakt.has(t.id);
    haken.addEventListener('change', () => {
      if (haken.checked) textAngehakt.add(t.id);
      else textAngehakt.delete(t.id);
      stapelZeichnen();
    });
    liste.append(h('div', { class: 'karte' },
      h('div', { style: 'display:flex;align-items:center;gap:.6rem' },
        haken,
        h('strong', { text: t.titel })),
      h('p', { class: 'leise', style: 'margin:.2rem 0 .6rem',
               text: `${t.abschnitte} Abschnitte · ${t.zeichen} Zeichen`
                   + (t.niveau ? ` · ${t.niveau}` : '')
                   // Wie weit die Übersetzung ist. Nur wo sie überhaupt
                   // eine Rolle spielt: »0 übersetzt« an jedem Satz
                   // einer Anfängersammlung wäre Lärm.
                   + (t.abschnitte > 1
                      ? (t.uebersetzt === t.abschnitte
                         ? ' · ganz übersetzt'
                         : t.uebersetzt
                           ? ` · ${t.uebersetzt} von ${t.abschnitte} übersetzt`
                           : ' · noch nicht übersetzt')
                      : '') }),
      h('div', { class: 'frage-werkzeuge', style: 'justify-content:flex-start' },
        h('button', { class: 'wichtig',
          onclick: () => { location.hash = `#/texte/${t.id}`; },
        }, 'Öffnen'),
        h('button', { class: 'schlicht', onclick: () => entfernen(t, behaelter) },
          'Löschen'))));
  }
  stapelZeichnen();
}


function teilKapitelwahl(behaelter, texte, kapitel) {
  // Nur Kapitel, in denen auch ein Text liegt — die Vokabelkapitel
  // einer Sammlung sind oft viel mehr, und eine Auswahl mit fünfzig
  // leeren Einträgen hilft niemandem.
  const zaehler = new Map();
  for (const t of texte) {
    const k = t.lektion_id;
    zaehler.set(k, (zaehler.get(k) || 0) + 1);
  }
  const wahl = h('select', {},
    h('option', { value: '', text: `alle Kapitel (${texte.length})` }),
    kapitel.filter((k) => zaehler.has(k.id)).map((k) => h('option', {
      value: String(k.id),
      text: (k.nr !== null ? `${k.nr}. ` : '') + (k.name || 'ohne Namen')
          + ` (${zaehler.get(k.id)})`,
    })),
    zaehler.has(null)
      ? h('option', { value: OHNE_KAPITEL,
                      text: `ohne Kapitel (${zaehler.get(null)})` })
      : null);
  wahl.value = textFilter;
  wahl.addEventListener('change', () => {
    textFilter = wahl.value;
    textAngehakt.clear();
    zeichnen(behaelter);
  });
  return h('div', { class: 'gezielt-filter', style: 'margin:.6rem 0' }, wahl);
}


function teilStapel(behaelter, kapitel, stapelZeichnen) {
  const wohin = h('select', {},
    h('option', { value: '', text: 'Kapitel wählen …' }),
    kapitel.map((k) => h('option', {
      value: String(k.id),
      text: (k.nr !== null ? `${k.nr}. ` : '') + (k.name || 'ohne Namen'),
    })),
    h('option', { value: OHNE_KAPITEL, text: 'ohne Kapitel' }));
  const nr = h('input', { type: 'number', min: '0', max: '9999',
                          placeholder: 'neue Nr.', style: 'width:7rem' });
  const name = h('input', { type: 'text', placeholder: 'Name des Kapitels',
                            style: 'width:12rem' });

  const setzen = (daten) => tun(async () => {
    const e = await api.texteVerschieben(zustand.sammlungId,
                                         { text_ids: [...textAngehakt], ...daten });
    meldung(`${e.verschoben} ${e.verschoben === 1 ? 'Text' : 'Texte'} `
          + 'umgehängt.');
    textAngehakt.clear();
    zeichnen(behaelter);
  });

  return h('div', { class: 'karte gezielt-stapel' },
    h('b', { text: `${textAngehakt.size} ausgewählt` }),
    h('div', { class: 'frage-werkzeuge',
               style: 'justify-content:flex-start;flex-wrap:wrap' },
      wohin,
      h('button', {
        class: 'wichtig',
        onclick: () => {
          if (!wohin.value) { meldung('Erst ein Kapitel wählen.'); return; }
          setzen(wohin.value === OHNE_KAPITEL
            ? {} : { lektion_id: Number(wohin.value) });
        },
      }, 'Umhängen'),
      nr, name,
      h('button', {
        title: 'Legt das Kapitel an, falls es noch nicht da ist.',
        onclick: () => {
          if (nr.value === '') { meldung('Welche Nummer?'); return; }
          setzen({ lektion_nr: Number(nr.value),
                   lektion_name: name.value.trim() || null });
        },
      }, 'In neues Kapitel'),
      h('button', { class: 'schlicht',
                    onclick: () => { textAngehakt.clear(); zeichnen(behaelter); } },
        'Auswahl aufheben')));
}


function teilEinwerfen(behaelter) {
  const titel = h('input', { type: 'text', placeholder: 'Titel' });
  // Kein Pflichtfeld-Gehabe: Titel darf leer bleiben, dann heißt er so.
  const inhalt = h('textarea', {
    rows: '8', placeholder: 'Text hier einfügen …',
    style: 'width:100%;font-family:inherit',
  });
  const datei = h('input', { type: 'file', accept: '.txt,.md,text/plain' });
  datei.addEventListener('change', async () => {
    const f = datei.files?.[0];
    if (!f) return;
    // Nur Text — eine PDF hier zu entpacken wäre ein eigenes Vorhaben,
    // und ein halb entpacktes PDF ist schlimmer als keins.
    inhalt.value = await f.text();
    if (!titel.value.trim()) titel.value = f.name.replace(/\.[^.]+$/, '');
  });

  return h('details', { class: 'karte', style: 'margin-top:1rem' },
    h('summary', { text: 'Text einwerfen' }),
    h('p', { class: 'leise', style: 'margin:.4rem 0',
             text: 'Absätze durch Leerzeilen trennen — daran entstehen die '
                 + 'Abschnitte, in denen du übersetzt.' }),
    titel, inhalt,
    h('p', { class: 'leise', style: 'margin:.4rem 0' },
      'oder eine Datei: ', datei),
    h('button', {
      class: 'wichtig',
      onclick: async () => {
        if (!inhalt.value.trim()) { meldung('Der Text ist leer.'); return; }
        try {
          const t = await api.textAnlegen(zustand.sammlungId, {
            titel: titel.value, inhalt: inhalt.value });
          location.hash = `#/texte/${t.id}`;
        } catch (f) { meldung(f.message, 'fehler'); }
      },
    }, 'Speichern und öffnen'));
}


async function entfernen(t, behaelter) {
  if (!window.confirm(`»${t.titel}« löschen? Deine Übersetzung dazu `
                      + 'geht mit verloren.')) return;
  await api.textLoeschen(t.id);
  zeichnen(behaelter);
}


// -------------------------------------------------------------- Werkbank

export async function zeichnenText(behaelter, textId) {
  leeren(behaelter);
  const [text, deckung] = await Promise.all([
    api.text(textId, zustand.benutzerId),
    api.textDeckung(textId, zustand.benutzerId),
  ]);
  merken({ sammlungId: text.sammlung_id });

  behaelter.append(h('h1', { text: text.titel }));
  behaelter.append(teilDeckung(deckung, textId, behaelter));
  behaelter.append(teilLesart(text, behaelter, textId));

  // Die Wortfarben je Abschnitt: die Deckung liefert die Wörter in der
  // Reihenfolge des ganzen Textes, die Abschnitte schneiden ihn in
  // Stücke. Statt die Stellen auszurechnen, wird je Abschnitt neu
  // zugeordnet — dieselbe Vergleichsform, derselbe Topf.
  const nachForm = new Map();
  for (const w of deckung.woerter) {
    if (!nachForm.has(w.vergleichsform)) nachForm.set(w.vergleichsform, w);
  }

  for (const a of text.abschnitte) {
    behaelter.append(teilAbschnitt(a, deckung, textId, behaelter));
  }

  behaelter.append(h('div', { class: 'frage-werkzeuge',
                              style: 'justify-content:flex-start' },
    h('button', { onclick: () => { location.hash = '#/texte'; } },
      'Zurück zu den Texten')));
}


/** Der Schalter für die Übersetzung daneben.
 *
 * »Für die Texte brauchen wir noch eine Option, Referenzübersetzungen
 * daneben zu stellen. Gerade bei den mittelhochdeutschen ist das
 * nämlich wichtig.«
 *
 * Und das stimmt: der Iwein steht vers für vers da, ein Abschnitt je
 * Vers. Genau so sind die Ausgaben gedruckt — links der Vers, rechts
 * die Übersetzung. Eingeklappt unter jedem Vers nützt sie beim Lesen
 * nichts; man will den Blick danebenlegen können, nicht achtundvierzig
 * Klappen öffnen.
 *
 * Steht hier oben und nicht in den Einstellungen: es ist eine
 * Entscheidung über DIESE Seite, und man trifft sie, während man sie
 * sieht.
 */
function teilLesart(text, behaelter, textId) {
  const mit = text.abschnitte.filter((a) => (a.referenz || '').trim()).length;
  const alle = text.abschnitte.length;
  const schalter = h('button', {
    class: zustand.textNebeneinander ? 'aktiv' : 'schlicht',
    onclick: () => {
      merken({ textNebeneinander: !zustand.textNebeneinander });
      zeichnenText(behaelter, textId);
    },
  }, 'Übersetzung daneben');

  return h('div', { class: 'frage-werkzeuge',
                    style: 'justify-content:flex-start;margin:.6rem 0' },
    schalter,
    // Ehrlich sagen, wie viel überhaupt da ist. Beim Iwein ist es
    // nichts — und dann soll nicht ein leerer Kasten den Eindruck
    // machen, die Anzeige sei kaputt.
    h('span', { class: 'leise' },
      mit === alle && alle
        ? `Alle ${alle} Abschnitte sind übersetzt.`
        : mit
          ? `${mit} von ${alle} Abschnitten sind übersetzt.`
          : 'Für diesen Text ist noch keine Übersetzung hinterlegt — '
            + 'dein Chatprogramm kann sie eintragen.'));
}


function teilDeckung(d, textId, behaelter) {
  const z = d.zahlen;
  return h('div', { class: 'karte' },
    h('p', { style: 'margin:0 0 .6rem;font-weight:600', text: d.urteil }),
    h('div', { class: 'zahlen' },
      zahl(z.sitzt, 'sitzt'), zahl(z.lernen, 'am Lernen'),
      zahl(z.neu, 'neu'), zahl(z.unbekannt, 'kennst du nicht')),
    h('p', { class: 'leise', style: 'margin:.6rem 0 0',
             text: `${d.abdeckung} % der ${d.verschiedene_woerter} `
                 + 'verschiedenen Wörter stehen in deinem Wortschatz.' }),
    z.unbekannt
      ? h('p', { class: 'leise', style: 'margin:.4rem 0 0' },
          'Tippe ein rot unterlegtes Wort an, um es für die KI zu merken.')
      : null,
    // Bei einem Zeitungsartikel sind es schnell achthundert. Einzeln
    // anzutippen ist dann keine Bedienung mehr, sondern eine Strafe.
    z.unbekannt
      ? h('div', { class: 'frage-werkzeuge',
                   style: 'justify-content:flex-start;margin-top:.6rem' },
          h('button', {
            onclick: async (e) => {
              e.target.disabled = true;
              try {
                const r2 = await api.alleUnbekanntenMerken(
                  textId, zustand.benutzerId);
                meldung(`${r2.angefordert} Wörter stehen auf der Liste für `
                      + 'die KI — häufigste zuerst.', 5000);
                zeichnenText(behaelter, textId);
              } catch (f) {
                meldung(f.message, 'fehler'); e.target.disabled = false;
              }
            },
          }, `Alle ${z.unbekannt} unbekannten anfordern`),
          h('button', {
            class: 'schlicht',
            onclick: async () => {
              try {
                const r2 = await api.alleZurueck(textId, zustand.benutzerId);
                meldung(`${r2.entfernt} wieder von der Liste.`);
                zeichnenText(behaelter, textId);
              } catch (f) { meldung(f.message, 'fehler'); }
            },
          }, 'Aus diesem Text zurücknehmen'))
      : null);
}


function zahl(wert, beschriftung) {
  return h('div', { class: 'zahl' },
    h('b', { text: String(wert ?? 0) }), h('span', { text: beschriftung }));
}


function teilAbschnitt(a, deckung, textId, behaelter) {
  const original = h('div', { class: 'textabschnitt-original' });
  let mitBedeutung = 0;
  for (const stueck of woerterDesAbschnitts(a.original, deckung)) {
    if (stueck.lexem_id === undefined) {
      original.append(document.createTextNode(stueck.text));
      continue;
    }
    const knopf = h('button', {
      type: 'button',
      class: 'wortknopf ' + FARBE[stueck.art]
           + (stueck.gewuenscht ? ' wort-gewuenscht' : ''),
      onclick: (e) => wortZeigen(e.target, stueck, textId, a, behaelter),
    }, stueck.text);
    // Jedes Wort steht in einer Säule: Bedeutung oben, Wort unten.
    // Auch das unbekannte, und zwar MIT leerer Oberzeile — die Lücke
    // ist die Auskunft. »Manche könnte ich dann vielleicht auch
    // erkennen aus dem Zusammenhang«: dafür muss man sehen, wo sie
    // steht und was links und rechts davon bekannt ist.
    if (stueck.bedeutung) mitBedeutung += 1;
    original.append(h('span', { class: 'wortsaeule' },
      h('span', { class: 'glosse', lang: 'de', text: stueck.bedeutung || '' }),
      knopf));
  }

  const feld = h('textarea', {
    rows: '3', placeholder: 'Deine Übersetzung …',
    style: 'width:100%;font-family:inherit',
  });
  feld.value = a.meine_fassung || '';
  // Beim Tippen sichern, nicht beim Abschicken. Es gibt kein
  // Abschicken — wer eine halbe Stunde an einem Absatz sitzt, soll
  // nichts verlieren, wenn der Reiter zugeht.
  let warten = null;
  feld.addEventListener('input', () => {
    clearTimeout(warten);
    warten = setTimeout(() => {
      api.fassungSichern(a.id, zustand.benutzerId, feld.value)
        .catch((f) => meldung(f.message, 'fehler'));
    }, 800);
  });

  // Wort für Wort aus dem EIGENEN Wortschatz — keine Übersetzung,
  // und das steht auch so da. Eine echte Übersetzung kann der
  // Trainer nicht; er hat keine Übersetzungsmaschine und soll keine
  // erfinden. Was er hat, sind deine Einträge, und die reichen, um
  // beim Entziffern nicht an jedem zweiten Wort hängenzubleiben.
  const hilfe = wortFuerWort(original, mitBedeutung);

  if (zustand.textNebeneinander) {
    return h('div', { class: 'karte' },
      h('div', { class: 'abschnitt-paar' },
        h('div', {}, original, hilfe),
        // Die rechte Spalte bleibt stehen, auch wenn nichts da ist:
        // die Lücke ist die Auskunft. Beim Iwein sieht man damit auf
        // einen Blick, welche Verse noch keine Übersetzung haben.
        h('div', { class: 'abschnitt-referenz' },
          a.referenz
            ? h('p', { style: 'margin:0', text: a.referenz })
            : h('p', { class: 'leise', style: 'margin:0',
                       text: 'noch nicht übersetzt' }))),
      feld);
  }

  return h('div', { class: 'karte' },
    original,
    hilfe,
    feld,
    a.referenz
      ? h('details', { style: 'margin-top:.4rem' },
          h('summary', { class: 'leise',
                         text: 'Übersetzungsvorschlag vergleichen' }),
          h('p', { text: a.referenz }),
          h('p', { class: 'leise', style: 'margin:.3rem 0 0',
                   text: 'Von deinem Chatprogramm hinterlegt. Deine '
                       + 'eigene Fassung oben bleibt davon unberührt.' }))
      : null);
}


/** Den Abschnitt in Wörter und Zwischenräume zerlegen, mit Farbe.
 *
 * Die Deckung hat den ganzen Text zerlegt; hier wird dieselbe Zerlegung
 * auf einen Abschnitt angewandt, damit die Mehrwort-Einträge (»το
 * μήλο«) auch hier als EIN Knopf erscheinen und nicht als zwei.
 */
function woerterDesAbschnitts(original, deckung) {
  const nach = new Map();
  for (const w of deckung.woerter) if (!nach.has(w.wort)) nach.set(w.wort, w);
  // Die längsten zuerst, sonst zerschneidet »το« das »το μήλο«.
  const muster = [...nach.keys()].sort((a, b) => b.length - a.length)
    .map((w) => w.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'));
  if (!muster.length) return [{ text: original }];

  const regel = new RegExp(`(${muster.join('|')})`, 'g');
  const stuecke = [];
  let zuletzt = 0;
  for (const treffer of original.matchAll(regel)) {
    if (treffer.index > zuletzt) {
      stuecke.push({ text: original.slice(zuletzt, treffer.index) });
    }
    stuecke.push({ ...nach.get(treffer[0]), text: treffer[0] });
    zuletzt = treffer.index + treffer[0].length;
  }
  if (zuletzt < original.length) stuecke.push({ text: original.slice(zuletzt) });
  return stuecke;
}


/** Wort für Wort — die Lesehilfe, die ohne KI auskommt.
 *
 * »Einen Übersetzungsvorschlag kann man sich vermutlich wieder nur von
 * der angeschlossenen KI holen?« — Für eine richtige Übersetzung ja.
 * Für das Entziffern nicht: die Bedeutungen stehen ja in deinem
 * Wortschatz. Das ist ausdrücklich KEINE Übersetzung, und die
 * Beschriftung sagt es, damit niemand sie dafür hält.
 *
 * ÜBER den Wörtern, nicht als Liste darunter. Die Liste war nach
 * Sprachen geordnet richtig und beim Lesen falsch: »για für · μήνες
 * der Monat · των der« ist eine Vokabelliste, und wer sie liest,
 * sucht danach im Satz die Stelle wieder, an der er war. Zwischen den
 * Zeilen steht die Bedeutung dort, wo das Wort steht — und die
 * unbekannten Wörter behalten ihren Platz in der Reihe, statt aus ihr
 * herauszufallen. Genau die sind ja die Frage.
 *
 * Es ist dieselbe Darstellung, die ein Interlinearglossar seit
 * Jahrhunderten benutzt, und zwar aus demselben Grund.
 */
function wortFuerWort(original, mitBedeutung) {
  if (!mitBedeutung) return null;
  const schalter = h('button', { type: 'button', class: 'schlicht' },
    `Wort für Wort einblenden (${mitBedeutung} aus deinem Wortschatz)`);
  let an = false;
  schalter.addEventListener('click', () => {
    an = !an;
    original.classList.toggle('mit-glosse', an);
    schalter.textContent = an
      ? 'Wort für Wort ausblenden'
      : `Wort für Wort einblenden (${mitBedeutung} aus deinem Wortschatz)`;
  });
  return h('div', { class: 'wfw' }, schalter);
}


/** Nachschlagen — und wenn nichts dasteht, anfordern. */
async function wortZeigen(knopf, stueck, textId, abschnitt, behaelter) {
  // Die Karte kommt UNTER den Abschnitt, nicht zwischen die Wörter.
  // Mitten hinein gesetzt schob sie den Rest des Satzes nach unten —
  // und beim Übersetzen ist der Satz das, worauf man schaut.
  const original = knopf.closest('.textabschnitt-original');
  const alt = original.parentElement.querySelector('.wortkarte');
  if (alt) alt.remove();
  for (const k of original.querySelectorAll('.wort-offen')) {
    k.classList.remove('wort-offen');
  }
  knopf.classList.add('wort-offen');

  const karte = h('div', { class: 'wortkarte karte' });
  original.insertAdjacentElement('afterend', karte);
  karte.append(h('p', { class: 'leise', text: 'einen Augenblick …' }));

  let d;
  try {
    d = await api.textNachschlagen(textId, stueck.text);
  } catch (f) { karte.textContent = f.message; return; }

  leeren(karte);
  karte.append(h('strong', { text: stueck.text }),
    h('button', { class: 'schlicht', style: 'float:right',
                  onclick: () => karte.remove() }, 'Schließen'));

  if (d.gefunden) {
    karte.append(h('p', { style: 'margin:.3rem 0' },
      h('b', { text: d.lemma }), ` · ${d.wortart}`));
    for (const b of d.bedeutungen) {
      karte.append(h('p', { style: 'margin:.2rem 0',
        text: b.uebersetzungen.join(', ')
            + (b.kontext ? ` (${b.kontext})` : '') }));
    }
    if (d.merkmale) {
      karte.append(h('p', { class: 'leise', style: 'margin:.2rem 0',
        text: Object.entries(d.merkmale).map(([k, v]) => `${k}: ${v}`)
          .join(' · ') }));
    }
    return;
  }

  karte.append(h('p', { style: 'margin:.3rem 0',
    text: 'Steht nicht in deinem Wortschatz.' }));
  const schon = stueck.gewuenscht;
  karte.append(h('button', {
    class: schon ? 'schlicht' : 'wichtig',
    onclick: async () => {
      try {
        if (schon) {
          await api.wortVergessen(textId, zustand.benutzerId, stueck.text);
          meldung(`»${stueck.text}« ist wieder von der Liste.`);
        } else {
          await api.wortMerken(textId, zustand.benutzerId, stueck.text,
                               abschnitt.original);
          meldung(`»${stueck.text}« steht auf der Liste für die KI.`);
        }
        zeichnenText(behaelter, textId);
      } catch (f) { meldung(f.message, 'fehler'); }
    },
  }, schon ? 'Doch nicht anfordern' : 'Für die KI merken'));
}
