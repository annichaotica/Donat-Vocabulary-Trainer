/* Zuspruch — jemandem, der lernt, etwas schicken.
 *
 * »Auch möchte ich meiner Tochter Boosts schicken können zur
 * Motivation.«
 *
 * Zwei Orte, und das mit Absicht:
 *
 *   Die KARTE auf der Übersicht ist für den Empfänger. Sie steht ganz
 *   oben, vor allem anderen — ein Satz von der Mutter ist wichtiger
 *   als die Zahl der fälligen Aufgaben, und wer ihn erst nach dem
 *   Scrollen fände, fände ihn nicht.
 *
 *   Die SEITE ist für den Absender. Dort wird geschrieben,
 *   nachgesehen, abgehakt.
 *
 * Die stärkste der vier Arten ist das Versprechen, und es ist zugleich
 * die dümmste: die App rechnet daran nichts aus. Sie merkt sich einen
 * Satz und sagt hinterher, dass er fällig ist. Die Belohnung kommt
 * nicht aus der App — genau darum wirkt sie.
 */

import { api } from './api.js';
import { h, leeren, meldung, anfuegen, tun,
         lesbareSchrift } from './hilfen.js';
import { zustand } from './zustand.js';

const ARTEN = {
  botschaft: {
    name: 'Botschaft',
    was: 'Ein Satz, der beim nächsten Öffnen dasteht.',
  },
  verdoppler: {
    name: 'Doppelte Punkte',
    was: 'Für einen Tag, den sie sich selbst aussucht.',
  },
  joker: {
    name: 'Joker',
    was: 'Ein Fehltag mehr, den die Strähne diesen Monat mitträgt.',
  },
  versprechen: {
    name: 'Versprechen',
    was: 'Eine echte Belohnung an ein Lernziel geknüpft. Einlösen '
       + 'musst du selbst — die App ist nur Zeuge.',
  },
};


/** Wie ein Zuspruch sich liest. Ohne Knöpfe, ohne Rahmen.
 *
 * ZWEI Fassungen, und das ist kein Luxus: der erste Entwurf nahm
 * einfach `von_name || an_name`, und in der Liste des Absenders stand
 * dann »Kind: „Heute nur 15 Wörter“« — als hätte das Kind es gesagt.
 * Dieselbe Zeile liest sich von beiden Seiten verschieden.
 *
 * `ziele` sind die Lernziele des EMPFÄNGERS; damit lässt sich beim
 * Versprechen sagen, ob es schon fällig ist.
 */
function satz(z, ziele = [], empfangen = true) {
  const wer = empfangen ? z.von_name : null;
  if (z.art === 'botschaft') {
    return wer ? `${wer}: „${z.text}“` : `„${z.text}“`;
  }
  if (z.art === 'verdoppler') {
    if (z.eingeloest) return `Doppelte Punkte am ${datum(z.eingeloest)}.`;
    return wer ? `${wer} schenkt dir doppelte Punkte für einen Tag.`
               : 'Doppelte Punkte für einen Tag.';
  }
  if (z.art === 'joker') {
    const was = 'ein Fehltag mehr, den die Strähne diesen Monat mitträgt';
    return wer ? `${wer} schenkt dir einen Joker: ${was}.`
               : `Ein Joker: ${was}.`;
  }
  const woran = z.ziel_text ? `„${z.ziel_text}“` : 'das Lernziel';
  const ziel = ziele.find((x) => x.id === z.lernziel_id);
  const fertig = ziel && (ziel.fortschritt?.anteil ?? 0) >= 1;
  if (fertig) {
    return wer ? `Geschafft — ${wer} schuldet dir: ${z.belohnung}`
               : `Geschafft — fällig: ${z.belohnung}`;
  }
  const frist = z.gueltig_bis ? ` bis ${datum(z.gueltig_bis)}` : '';
  return `${woran} schaffen${frist} → ${z.belohnung}.`
       + (wer ? ` Versprochen von ${wer}.` : '');
}


function datum(iso) {
  if (!iso) return '';
  const [j, m, t] = iso.slice(0, 10).split('-');
  return `${Number(t)}.${Number(m)}.${j}`;
}


/** Die Karte auf der Übersicht — für den, der ihn bekommt. */
export function karteFuerMich(behaelter, offene, ziele, neuZeichnen) {
  if (!offene.length) return null;
  const karte = h('div', { class: 'karte zuspruch-karte' },
    h('h2', { style: 'margin-top:0', text: 'Für dich' }));

  for (const z of offene) {
    const fertig = z.art === 'versprechen'
      && ziele.find((x) => x.id === z.lernziel_id
                        && (x.fortschritt?.anteil ?? 0) >= 1);
    const knoepfe = [];
    if (z.art === 'verdoppler' && !z.eingeloest) {
      knoepfe.push(h('button', {
        class: 'wichtig',
        title: 'Gilt für heute. Wer ihn für einen großen Tag aufhebt, '
             + 'hat mehr davon.',
        onclick: () => tun(async () => {
          await api.zuspruchEinloesen(z.id, zustand.benutzerId);
          meldung('Heute zählt doppelt.');
          neuZeichnen();
        }),
      }, 'Heute einlösen'));
    }
    if (z.art !== 'versprechen') {
      knoepfe.push(h('button', {
        class: 'schlicht',
        onclick: () => tun(async () => {
          await api.zuspruchGesehen(z.id, zustand.benutzerId);
          neuZeichnen();
        }),
      }, z.art === 'botschaft' ? 'Danke, gelesen' : 'Alles klar'));
    }

    karte.append(h('div', { class: 'zuspruch' + (fertig ? ' ist-faellig' : '') },
      h('span', { class: 'zuspruch-punkt',
                  style: `background:${z.von_farbe || '#6b7fd7'};`
                       + `color:${lesbareSchrift(z.von_farbe || '#6b7fd7')}`,
                  text: (z.von_name || '?').slice(0, 1).toUpperCase() }),
      h('div', { class: 'zuspruch-text' },
        h('p', { style: 'margin:0', text: satz(z, ziele) }),
        knoepfe.length
          ? h('div', { class: 'frage-werkzeuge',
                       style: 'margin-top:.4rem' },
              ...knoepfe)
          : null)));
  }
  return karte;
}


/* ------------------------------------------------------------- Seite */

export async function zeichnen(behaelter) {
  const el = leeren(behaelter);
  el.append(h('h1', { text: 'Zuspruch' }));

  let d;
  try {
    d = await api.zuspruch(zustand.benutzerId);
  } catch (fehler) {
    el.append(h('p', { class: 'leise', text: fehler.message }));
    return;
  }
  const ziele = await api.lernziele(zustand.benutzerId).catch(() => []);
  const neu = () => zeichnen(behaelter);

  anfuegen(el, karteFuerMich(behaelter, d.fuer_mich, ziele, neu));

  if (!d.empfaenger.length) {
    el.append(h('p', { class: 'leise',
      text: 'Du kannst gerade niemandem etwas schicken. Zuspruch geht an '
          + 'Leute, mit denen du eine Sammlung teilst — freigeben geht '
          + 'über »Freigabe« auf der Sammlungskarte.' }));
    return;
  }

  el.append(teilSchicken(behaelter, d, ziele, neu));
  anfuegen(el, teilVonMir(d, neu));
}


function teilSchicken(behaelter, d, meineZiele, neu) {
  const karte = h('div', { class: 'karte' });
  karte.append(h('h2', { style: 'margin-top:0', text: 'Jemandem schicken' }));

  const wer = h('select', {}, d.empfaenger.map(
    (p) => h('option', { value: String(p.id), text: p.name })));
  const art = h('select', {}, Object.entries(ARTEN).map(
    ([schluessel, a]) => h('option', { value: schluessel, text: a.name })));
  const text = h('textarea', { rows: '2', maxlength: '400',
                               placeholder: 'Dein Satz' });
  const belohnung = h('input', { type: 'text', maxlength: '400',
                                 placeholder: 'z. B. Kino am Samstag' });
  const zielwahl = h('select', {}, h('option', { value: '', text: 'ohne Lernziel' }));
  const erklaerung = h('p', { class: 'leise', style: 'margin:.4rem 0 0' });

  // Die Lernziele des EMPFÄNGERS, nicht die eigenen. Ein Versprechen
  // auf das eigene Ziel wäre ein Vorsatz.
  const zieleLaden = async () => {
    const id = Number(wer.value);
    leeren(zielwahl).append(h('option', { value: '', text: 'ohne Lernziel' }));
    if (!id) return;
    const fremd = id === zustand.benutzerId
      ? meineZiele
      : await api.lernziele(id).catch(() => []);
    for (const z of fremd) {
      zielwahl.append(h('option', { value: String(z.id),
        text: z.name + (z.termin ? ` (bis ${datum(z.termin)})` : '') }));
    }
  };
  wer.addEventListener('change', zieleLaden);
  zieleLaden();

  const zeigen = () => {
    const a = art.value;
    erklaerung.textContent = ARTEN[a].was;
    text.parentElement.hidden = !(a === 'botschaft' || a === 'versprechen');
    belohnung.parentElement.hidden = a !== 'versprechen';
    zielwahl.parentElement.hidden = a !== 'versprechen';
    text.placeholder = a === 'versprechen'
      ? 'Dazu ein Satz (freigestellt)' : 'Dein Satz';
  };
  art.addEventListener('change', zeigen);

  karte.append(
    h('div', { class: 'regler' }, h('label', { text: 'An' }), h('span', {}),
      wer, h('span', {})),
    h('div', { class: 'regler' }, h('label', { text: 'Was' }), h('span', {}),
      art, h('span', {})),
    erklaerung,
    h('div', { style: 'margin-top:.6rem' },
      h('label', { class: 'leise', text: 'Lernziel' }), zielwahl),
    h('div', { style: 'margin-top:.6rem' }, belohnung),
    h('div', { style: 'margin-top:.6rem' }, text),
    h('div', { class: 'frage-werkzeuge',
               style: 'margin-top:.8rem' },
      h('button', {
        class: 'wichtig',
        onclick: () => tun(async () => {
          await api.zuspruchSchicken({
            von_id: zustand.benutzerId,
            an_id: Number(wer.value),
            art: art.value,
            text: text.value.trim() || null,
            belohnung: belohnung.value.trim() || null,
            lernziel_id: zielwahl.value ? Number(zielwahl.value) : null,
          });
          meldung('Abgeschickt.');
          neu();
        }),
      }, 'Abschicken')));
  zeigen();
  return karte;
}


function teilVonMir(d, neu) {
  if (!d.von_mir.length) return null;
  const karte = h('div', { class: 'karte' },
    h('h2', { style: 'margin-top:0', text: 'Von dir verschickt' }));
  for (const z of d.von_mir.slice(0, 15)) {
    const stand = z.erledigt ? 'erledigt'
                : z.gesehen ? 'gelesen' : 'noch ungelesen';
    karte.append(h('div', { class: 'zuspruch' },
      h('span', { class: 'zuspruch-punkt zuspruch-punkt-still',
                  text: (z.an_name || '?').slice(0, 1).toUpperCase() }),
      h('div', { class: 'zuspruch-text' },
        h('p', { style: 'margin:0', text: satz(z, [], false) }),
        h('p', { class: 'leise', style: 'margin:.1rem 0 0',
                 text: `an ${z.an_name} · ${stand}` }),
        h('div', { class: 'frage-werkzeuge',
                   style: 'margin-top:.3rem' },
          // Ein Versprechen hakt ab, wer es gegeben hat. Wer sich selbst
          // bescheinigen könnte, das Kino sei abgegolten, bräuchte keins.
          (z.art === 'versprechen' && !z.erledigt)
            ? h('button', {
                class: 'schlicht',
                onclick: () => tun(async () => {
                  await api.zuspruchErledigt(z.id, zustand.benutzerId);
                  meldung('Eingelöst.');
                  neu();
                }),
              }, 'Eingelöst')
            : null,
          (!z.gesehen && !z.erledigt)
            ? h('button', {
                class: 'schlicht gefahr',
                title: 'Geht nur, solange es noch niemand gelesen hat.',
                onclick: () => tun(async () => {
                  await api.zuspruchZurueck(z.id, zustand.benutzerId);
                  neu();
                }),
              }, 'Zurückziehen')
            : null))));
  }
  return karte;
}
