/* Profilwahl und Übersicht über die Sammlungen. */

import { api } from './api.js';
import { h, leeren, meldung } from './hilfen.js';
import { stammdaten } from './stammdaten.js';
import { zustand, merken } from './zustand.js';

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
  return punkt;
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


export async function zeichnen(behaelter) {
  const el = leeren(behaelter);
  const [sammlungen, sprachen] = await Promise.all([
    api.sammlungen(zustand.benutzerId), stammdaten.sprachen(),
  ]);
  const gesamt = await api.stand(zustand.benutzerId, null);

  el.append(h('h1', { text: 'Heute' }));
  el.append(h('div', { class: 'karte' },
    h('div', { class: 'zahlen' },
      zahlKasten(gesamt.faellig, 'fällig', 'faellig'),
      zahlKasten(gesamt.verlernt, 'verlernt', 'verlernt'),
      zahlKasten(gesamt.neu, 'neu', 'neu'),
      zahlKasten(gesamt.reif, 'sitzt'),
      zahlKasten(gesamt.gesamt, 'Aufgaben insgesamt')),
    h('div', { class: 'frage-werkzeuge', style: 'justify-content:flex-start;margin-top:1rem' },
      h('button', {
        class: 'wichtig',
        disabled: !(gesamt.faellig + gesamt.verlernt + gesamt.neu),
        onclick: () => { merken({ sammlungId: null }); location.hash = '#/lernen'; },
      }, 'Lernen'),
      h('button', { onclick: () => { merken({ sammlungId: null }); location.hash = '#/lernen/frei'; } },
        'Frei üben'),
      h('button', { onclick: () => { merken({ sammlungId: null }); location.hash = '#/lernen/fehler'; } },
        'Fehler wiederholen'))));

  // Lernziele: Ausschnitte des Bestands mit Termin, auch über Lektionen
  // und Sammlungen hinweg.
  const ziele = await api.lernziele(zustand.benutzerId).catch(() => []);
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
  el.append(h('div', { class: 'frage-werkzeuge', style: 'justify-content:flex-start' },
    h('button', { onclick: () => { location.hash = '#/ziele'; } },
      ziele.length ? 'Alle Lernziele' : 'Lernziel anlegen')));

  el.append(h('h2', { text: 'Sammlungen' }));
  if (!sammlungen.length) {
    el.append(h('p', { class: 'leise', text: 'Noch keine Sammlung. Unten anlegen.' }));
  }
  const reihe = h('div', { class: 'karte-reihe' });
  // Alle Zählungen auf einmal statt ein Rundlauf je Sammlung — das ist der
  // Startbildschirm, der soll nicht nach Sammlungszahl langsamer werden.
  const staende = await Promise.all(
    sammlungen.map((s) => api.stand(zustand.benutzerId, s.id).catch(() => ({}))));
  for (const [i, s] of sammlungen.entries()) {
    const stand = staende[i];
    const sprache = sprachen.find((x) => x.code === s.sprache);
    reihe.append(h('div', { class: 'karte' },
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
      h('div', { class: 'frage-werkzeuge', style: 'justify-content:flex-start;margin-top:.8rem' },
        h('button', {
          class: 'wichtig',
          onclick: () => { merken({ sammlungId: s.id, lektionId: null }); location.hash = '#/lernen'; },
        }, 'Lernen'),
        h('button', {
          onclick: () => { merken({ sammlungId: s.id }); location.hash = '#/wortschatz'; },
        }, 'Wortschatz'),
        h('button', {
          onclick: () => { merken({ sammlungId: s.id }); location.hash = '#/ueben'; },
        }, 'Sätze'),
        h('button', {
          onclick: () => { merken({ sammlungId: s.id }); location.hash = '#/texte'; },
        }, 'Texte'),
        h('button', {
          onclick: () => { merken({ sammlungId: s.id }); location.hash = '#/import'; },
        }, 'Einlesen'),
        wartendes(s).length
          ? h('button', {
              onclick: () => {
                merken({ sammlungId: s.id });
                location.hash = '#/freigabe';
              },
            }, 'Freigabe')
          : null,
        h('button', {
          class: 'schlicht',
          onclick: () => { merken({ sammlungId: s.id }); location.hash = '#/einstellungen'; },
        }, 'Einstellungen'))));
  }
  el.append(reihe);
  el.append(await teilNeueSammlung(behaelter, sprachen));
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
