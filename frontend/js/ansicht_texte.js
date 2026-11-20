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


// --------------------------------------------------------- Bücherregal

/* Bücher, Kapitel, Texte — und das Regal gehört dem Konto.
 *
 * »Tatsächlich würde ich behaupten, die Texte gehören dem Konto und
 * nicht der Sammlung, also können sie auch außerhalb der
 * Sammlungskarte dargestellt werden, als eigene Karte.«
 *
 * Sie hat recht. Der Iwein gehört nicht zu »Mittelhochdeutsch,
 * Stammformen« — er ist Literatur, die man MIT diesem Wortschatz
 * liest. Vorher musste man erst eine Sammlung wählen, und bei drei
 * Sammlungen stand der Knopf »Texte« dreimal auf der Übersicht, jedes
 * Mal mit einem anderen Ausschnitt dahinter.
 *
 * Die Sammlung steht trotzdem an jedem Buch: an ihr hängt die Deckung
 * (»kann ich das schon lesen?«). Sie ist eine Eigenschaft, kein
 * Eingang.
 */
let offeneBuecher = new Set();
let angehakt = new Set();

export async function zeichnen(behaelter) {
  const el = leeren(behaelter);
  el.append(h('h1', { text: 'Bücher und Texte' }));

  let buecher, texte, sammlungen;
  try {
    [buecher, texte, sammlungen] = await Promise.all([
      api.buecher(zustand.benutzerId),
      api.alleTexte(zustand.benutzerId),
      api.sammlungen(zustand.benutzerId),
    ]);
  } catch (fehler) {
    el.append(h('p', { class: 'leise', text: fehler.message }));
    return;
  }

  if (!texte.length && !buecher.length) {
    el.append(h('p', { class: 'leise',
      text: 'Noch nichts hier. Wirf einen Text ein — der Trainer sagt dir '
          + 'dann, ob du ihn schon lesen könntest.' }));
    el.append(teilEinwerfen(behaelter, sammlungen));
    return;
  }

  el.append(h('p', { class: 'leise',
    text: 'Was dir beim Lesen fehlt, kannst du im Text antippen und '
        + 'anfordern.' }));

  const stapel = h('div', {});
  el.append(stapel);
  const stapelZeichnen = () => {
    leeren(stapel);
    if (angehakt.size) {
      stapel.append(teilStapel(behaelter, buecher, texte, stapelZeichnen));
    }
  };

  for (const b of buecher) {
    el.append(teilBuch(behaelter, b, texte, stapelZeichnen));
  }

  const lose = texte.filter((t) => t.buch_id === null);
  if (lose.length) {
    el.append(h('h2', { class: 'kapitelkopf',
      text: buecher.length ? 'Ohne Buch' : 'Texte' }));
    // Hier MIT Sammlung: außerhalb eines Buchs sagt nichts anderes,
    // gegen welchen Wortschatz der Text gelesen wird.
    el.append(teilTexte(behaelter, lose, stapelZeichnen, true));
  }

  el.append(teilEinwerfen(behaelter, sammlungen));
  el.append(teilNeuesBuch(behaelter, sammlungen));
  stapelZeichnen();
}


/** Ein Buch als aufklappbare Karte.
 *
 * Zugeklappt, solange niemand es öffnet: bei fünf Büchern mit je 173
 * Stücken wäre die Seite sonst ein Band. Welche offen sind, überlebt
 * das Neuzeichnen — sonst klappt das Buch nach jeder Zuordnung zu.
 */
function teilBuch(behaelter, b, texte, stapelZeichnen) {
  const meine = texte.filter((t) => t.buch_id === b.id);
  const offen = offeneBuecher.has(b.id);

  const kopf = h('button', {
    class: 'buchkopf',
    onclick: () => {
      if (offen) offeneBuecher.delete(b.id); else offeneBuecher.add(b.id);
      zeichnen(behaelter);
    },
  },
    h('span', { class: 'buchpfeil', text: offen ? '▾' : '▸' }),
    h('span', {},
      h('strong', { text: b.titel }),
      b.verfasser ? h('span', { class: 'leise', text: ` · ${b.verfasser}` }) : null));

  const karte = h('div', { class: 'karte' }, kopf,
    h('p', { class: 'leise', style: 'margin:.2rem 0 0' },
      `${meine.length} ${meine.length === 1 ? 'Text' : 'Texte'}`,
      ` · ${b.sammlung}`,
      b.abschnitte
        ? (b.uebersetzt === b.abschnitte ? ' · ganz übersetzt'
           : b.uebersetzt ? ` · ${b.uebersetzt} von ${b.abschnitte} Abschnitten übersetzt`
             : ' · noch nicht übersetzt')
        : ''));

  if (!offen) return karte;

  // Nach Kapiteln, in der Reihenfolge ihres ersten Textes. Das Kapitel
  // ist ein Name am Text und keine eigene Zeile — es hat nichts außer
  // seinem Namen und seiner Stelle.
  const kapitel = [];
  const nach = new Map();
  for (const t of meine) {
    const name = t.kapitel || null;
    if (!nach.has(name)) { nach.set(name, []); kapitel.push(name); }
    nach.get(name).push(t);
  }
  for (const name of kapitel) {
    if (name !== null || kapitel.length > 1) {
      karte.append(h('h3', { class: 'kapitelkopf',
                             text: name || 'Ohne Kapitel' }));
    }
    karte.append(teilTexte(behaelter, nach.get(name), stapelZeichnen));
  }
  if (!meine.length) {
    karte.append(h('p', { class: 'leise',
      text: 'Noch kein Text in diesem Buch. Unten einen anhaken und '
          + 'zuordnen.' }));
  }
  karte.append(h('div', { class: 'frage-werkzeuge',
                          style: 'margin-top:.8rem' },
    h('button', { class: 'schlicht', onclick: () => buchUmbenennen(behaelter, b) },
      'Umbenennen'),
    h('button', { class: 'schlicht gefahr',
                  onclick: () => buchEntfernen(behaelter, b, meine.length) },
      'Buch auflösen')));
  return karte;
}


/** Die Texte als flache Liste — im Buch wie außerhalb.
 *
 * Der erste Entwurf setzte die losen Texte als Karten; eine Karte in
 * der Karte, und der Haken stand neben einem Kasten im Kasten. Ein
 * Text sieht überall gleich aus, auch wenn er noch keinem Buch
 * zugeordnet ist — das ist ja gerade das, was man ändern will.
 */
function teilTexte(behaelter, liste, stapelZeichnen, mitSammlung = false) {
  const halter = h('div', { class: 'liste' });
  for (const t of liste) {
    const haken = h('input', { type: 'checkbox', class: 'eintrag-haken',
                               title: 'auswählen' });
    haken.checked = angehakt.has(t.id);
    haken.addEventListener('change', () => {
      if (haken.checked) angehakt.add(t.id); else angehakt.delete(t.id);
      stapelZeichnen();
    });
    const beschriftung = `${t.abschnitte} Abschnitte`
      + (t.abschnitte
         ? (t.uebersetzt === t.abschnitte ? ' · ganz übersetzt'
            : t.uebersetzt ? ` · ${t.uebersetzt} übersetzt` : '')
         : '');
    halter.append(h('div', { class: 'eintrag-zeile' },
      h('label', { class: 'hakenfeld', title: 'auswählen' }, haken),
      h('button', {
        class: 'eintrag', style: 'flex:1 1 auto',
        onclick: () => { location.hash = `#/texte/${t.id}`; },
      },
        h('span', { class: 'lemma', text: t.titel }),
        h('span', { class: 'bedeutung', text: beschriftung }),
        mitSammlung && t.sammlung
          ? h('span', { class: 'marke', text: t.sammlung }) : null)));
  }
  return halter;
}


/** Was mit den angehakten Texten geschehen soll. */
function teilStapel(behaelter, buecher, texte, stapelZeichnen) {
  const wohin = h('select', {},
    h('option', { value: '', text: 'Buch wählen …' }),
    buecher.map((b) => h('option', { value: String(b.id), text: b.titel })),
    h('option', { value: 'ohne', text: 'ohne Buch' }));
  // Vorhandene Kapitelnamen anbieten: Tippfehler machen sonst aus
  // einem Kapitel zwei.
  const bekannt = [...new Set(texte.map((t) => t.kapitel).filter(Boolean))];
  const kapitel = h('input', { type: 'text', list: 'kapitelnamen',
                               placeholder: 'Kapitel (freigestellt)',
                               style: 'width:14rem' });
  const liste = h('datalist', { id: 'kapitelnamen' },
    bekannt.map((n) => h('option', { value: n })));

  return h('div', { class: 'karte gezielt-stapel' },
    h('b', { text: `${angehakt.size} ausgewählt` }),
    h('div', { class: 'frage-werkzeuge',
               style: 'flex-wrap:wrap' },
      wohin, kapitel, liste,
      h('button', {
        class: 'wichtig',
        onclick: () => tun(async () => {
          if (!wohin.value) { meldung('Erst ein Buch wählen.'); return; }
          const e = await api.texteZuordnen({
            benutzer_id: zustand.benutzerId,
            text_ids: [...angehakt],
            buch_id: wohin.value === 'ohne' ? null : Number(wohin.value),
            kapitel: kapitel.value.trim() || null,
          });
          meldung(`${e.zugeordnet} ${e.zugeordnet === 1 ? 'Text' : 'Texte'} `
                + 'zugeordnet.');
          angehakt.clear();
          zeichnen(behaelter);
        }),
      }, 'Zuordnen'),
      h('button', { class: 'schlicht',
                    onclick: () => { angehakt.clear(); zeichnen(behaelter); } },
        'Auswahl aufheben'),
      // Beim Umbau auf das Regal war der Löschen-Knopf von den
      // Textkarten verschwunden. Hier ist er besser aufgehoben: wer
      // 173 Stücke eines Fehlimports loswerden will, klickt nicht 173
      // Mal. Die Rückfrage sagt, was mit verloren geht.
      h('button', {
        class: 'schlicht gefahr',
        onclick: () => tun(async () => {
          const ids = [...angehakt];
          if (!window.confirm(
            `${ids.length} ${ids.length === 1 ? 'Text' : 'Texte'} löschen? `
            + 'Die Übersetzungen dazu gehen mit verloren.')) return;
          for (const id of ids) await api.textLoeschen(id);
          meldung(`${ids.length} gelöscht.`);
          angehakt.clear();
          zeichnen(behaelter);
        }),
      }, 'Löschen')));
}


function teilNeuesBuch(behaelter, sammlungen) {
  const titel = h('input', { type: 'text', placeholder: 'Titel' });
  const verfasser = h('input', { type: 'text', placeholder: 'Verfasser (freigestellt)' });
  // Gegen welchen Wortschatz das Buch gelesen wird. Keine Spielerei:
  // ohne das gibt es die Auskunft »kannst du das schon lesen« nicht.
  const wortschatz = h('select', {},
    sammlungen.map((s) => h('option', { value: String(s.id),
                                        text: `${s.name} (${s.sprache})` })));

  return h('details', { class: 'karte', style: 'margin-top:1rem' },
    h('summary', { text: 'Neues Buch' }),
    h('p', { class: 'leise', style: 'margin:.4rem 0',
             text: 'Ein Buch bündelt Texte. Der Wortschatz dahinter '
                 + 'entscheidet, wogegen die Deckung gerechnet wird — '
                 + '»kannst du das schon lesen«.' }),
    h('div', { style: 'display:flex;gap:.5rem;flex-wrap:wrap' },
      titel, verfasser, wortschatz),
    h('button', {
      class: 'wichtig', style: 'margin-top:.6rem',
      onclick: () => tun(async () => {
        if (!titel.value.trim()) { meldung('Der Titel fehlt.'); return; }
        if (!wortschatz.value) { meldung('Erst eine Sammlung anlegen.'); return; }
        const b = await api.buchAnlegen({
          benutzer_id: zustand.benutzerId,
          sammlung_id: Number(wortschatz.value),
          titel: titel.value.trim(),
          verfasser: verfasser.value.trim() || null,
        });
        offeneBuecher.add(b.id);
        meldung('Buch angelegt.');
        zeichnen(behaelter);
      }),
    }, 'Anlegen'));
}


async function buchUmbenennen(behaelter, b) {
  const neu = window.prompt('Neuer Titel:', b.titel);
  if (neu === null || !neu.trim()) return;
  await api.buchAendern(b.id, { titel: neu.trim() });
  zeichnen(behaelter);
}


async function buchEntfernen(behaelter, b, anzahl) {
  // Ein Buch ist eine Klammer, kein Behälter — und das muss dastehen,
  // sonst traut sich niemand.
  if (!window.confirm(
    `»${b.titel}« auflösen? Die ${anzahl} Texte bleiben erhalten und `
    + 'stehen danach ohne Buch.')) return;
  await api.buchLoeschen(b.id);
  offeneBuecher.delete(b.id);
  zeichnen(behaelter);
}


function teilEinwerfen(behaelter, sammlungen) {
  const titel = h('input', { type: 'text', placeholder: 'Titel' });
  // Kein Pflichtfeld-Gehabe: Titel darf leer bleiben, dann heißt er so.
  const inhalt = h('textarea', {
    rows: '8', placeholder: 'Text hier einfügen …',
    style: 'width:100%;font-family:inherit',
  });
  const wortschatz = h('select', {},
    sammlungen.map((s) => h('option', { value: String(s.id),
                                        text: `${s.name} (${s.sprache})` })));
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
    h('div', { style: 'display:flex;gap:.5rem;align-items:center;margin:.4rem 0;flex-wrap:wrap' },
      h('span', { class: 'leise', text: 'Wortschatz:' }), wortschatz),
    h('p', { class: 'leise', style: 'margin:.4rem 0' },
      'oder eine Datei: ', datei),
    h('button', {
      class: 'wichtig',
      onclick: () => tun(async () => {
        if (!inhalt.value.trim()) { meldung('Der Text ist leer.'); return; }
        if (!wortschatz.value) { meldung('Erst eine Sammlung anlegen.'); return; }
        const t = await api.textAnlegen(Number(wortschatz.value), {
          titel: titel.value, inhalt: inhalt.value });
        location.hash = `#/texte/${t.id}`;
      }),
    }, 'Speichern und öffnen'));
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

  behaelter.append(h('div', { class: 'frage-werkzeuge' },
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
                    style: 'margin:.6rem 0' },
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
                   style: 'margin-top:.6rem' },
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
