/* Einstellungen: was die Sammlung abfragt, wie der Algorithmus terminiert,
 * und der Legastheniemodus. */

import { api } from './api.js';
import { datumText, h, leeren, meldung, zahl } from './hilfen.js';
import { stammdaten } from './stammdaten.js';
import { zustand, darstellungSetzen } from './zustand.js';

export async function zeichnen(behaelter) {
  const el = leeren(behaelter);
  el.append(h('h1', { text: 'Einstellungen' }));
  el.append(h('p', {},
    h('button', { onclick: () => { location.hash = '#/hilfe'; } },
      'Anleitung — Lernen und Chatprogramm anschließen')));

  if (zustand.sammlungId) {
    el.append(await teilSammlung(behaelter));
  } else {
    el.append(h('p', { class: 'leise',
      text: 'Keine Sammlung gewählt — die Einstellungen zu Formgruppen und '
          + 'Aufgabentypen gelten je Sammlung. Über die Übersicht eine auswählen.' }));
  }
  if (zustand.sammlungId) el.append(await teilZugriff(behaelter));
  el.append(await teilLernen(behaelter));
  el.append(await teilLegasthenie(behaelter));
  el.append(await teilZugaenge(behaelter));
  el.append(h('details', { class: 'karte' },
    h('summary', { text: 'Tastatur' }),
    h('ul', {},
      h('li', {}, h('kbd', { text: '1' }), '–', h('kbd', { text: '4' }), ' bewerten'),
      h('li', {}, h('kbd', { text: 'Enter' }), ' prüfen, dann vorgeschlagene Bewertung'),
      h('li', {}, h('kbd', { text: 'l' }), ' lernen, ',
        h('kbd', { text: 'w' }), ' Wortschatz, ', h('kbd', { text: 'u' }), ' Übersicht')),
    // Der Weg zur Belegung gehört hierher und nicht nur in den Hinweis
    // unter dem Antwortfeld: dort steht er erst, wenn man schon mitten
    // in der Abfrage sitzt und sucht.
    h('p', { style: 'margin-bottom:0' },
      h('button', {
        onclick: () => { location.hash = '#/tastatur'; },
      }, 'Fremde Schrift: wo liegt welcher Buchstabe?'))));
}

/* --------------------------------------------- Wer darf mitlernen */

const RECHTE = {
  lesen: 'mitlernen',
  schreiben: 'mitlernen und pflegen',
};

async function teilZugriff(behaelter) {
  const [z, leute] = await Promise.all([
    api.zugriff(zustand.sammlungId), api.benutzer(),
  ]);
  const kasten = h('div', { class: 'karte' });
  kasten.append(h('h2', { style: 'margin-top:0', text: 'Wer darf mitlernen' }));
  kasten.append(h('p', { class: 'leise' },
    'Der Lernstand hängt an der Person, nicht an der Sammlung: wer '
    + 'mitlernt, fängt mit seinem eigenen Fortschritt an. ',
    h('b', { text: 'Pflegen' }), ' heißt zusätzlich, Wörter ändern und '
    + 'freigeben zu dürfen.'));

  const neu = async () => zeichnen(behaelter);

  kasten.append(h('p', { style: 'margin:.6rem 0 .2rem' },
    h('b', { text: z.besitzer.name }),
    h('span', { class: 'marke', text: 'gehört ihr' })));

  for (const m of z.mitlernende) {
    kasten.append(h('div', { class: 'zugriffszeile' },
      h('span', {}, m.name,
        h('span', { class: 'marke', text: RECHTE[m.recht] || m.recht })),
      h('div', { class: 'durchsicht-knoepfe' },
        h('button', {
          onclick: async () => {
            await api.zugriffSetzen(zustand.sammlungId, {
              benutzer_id: m.id,
              recht: m.recht === 'lesen' ? 'schreiben' : 'lesen',
            });
            meldung('Geändert.');
            neu();
          },
        }, m.recht === 'lesen' ? 'auch pflegen lassen' : 'nur mitlernen'),
        h('button', {
          class: 'schlicht gefahr',
          onclick: async () => {
            if (!confirm(`${m.name} den Zugriff entziehen?\n\n`
                       + 'Der Lernstand bleibt erhalten, falls du es dir '
                       + 'anders überlegst.')) return;
            await api.zugriffSetzen(zustand.sammlungId,
                                    { benutzer_id: m.id, recht: null });
            meldung('Zugriff entzogen.');
            neu();
          },
        }, 'entziehen'),
        h('button', {
          class: 'schlicht',
          onclick: async () => {
            if (!confirm(`Die Sammlung an ${m.name} übertragen?\n\n`
                       + `${m.name} wird Besitzerin. Du behältst `
                       + 'Schreibzugriff, kannst also weiter pflegen.')) return;
            await api.besitzUebertragen(zustand.sammlungId, {
              benutzer_id: m.id, bisherige_behaelt_zugriff: true });
            meldung('Übertragen.');
            neu();
          },
        }, 'Besitz übertragen'))));
  }

  const schon = new Set([z.besitzer.id, ...z.mitlernende.map((m) => m.id)]);
  const offen = leute.filter((p) => !schon.has(p.id));
  if (offen.length) {
    const wahl = h('select', {}, offen.map(
      (p) => h('option', { value: p.id, text: p.name })));
    const recht = h('select', {},
      h('option', { value: 'lesen', text: 'mitlernen' }),
      h('option', { value: 'schreiben', text: 'mitlernen und pflegen' }));
    kasten.append(h('div', { class: 'zugriffszeile', style: 'margin-top:.8rem' },
      wahl, recht,
      h('button', {
        onclick: async () => {
          await api.zugriffSetzen(zustand.sammlungId, {
            benutzer_id: Number(wahl.value), recht: recht.value });
          meldung('Freigegeben.');
          neu();
        },
      }, 'Dazunehmen')));
  } else if (!z.mitlernende.length) {
    kasten.append(h('p', { class: 'leise',
      text: 'Es gibt noch kein weiteres Profil. Über den Profilknopf oben '
          + 'rechts lässt sich eines anlegen.' }));
  }
  return kasten;
}


/* ------------------------------------------------- Sammlung: was abfragen */

async function teilSammlung(behaelter) {
  const [einstellungen, typen] = await Promise.all([
    api.sammlungEinstellungen(zustand.sammlungId),
    stammdaten.aufgabentypen(),
  ]);
  const gruppen = await api.formgruppen(einstellungen.sprache);
  const gewaehlteGruppen = new Set(einstellungen.formgruppen);
  const gewaehlteTypen = new Set(einstellungen.typen);

  const kasten = h('div', { class: 'karte' });
  kasten.append(h('h2', { style: 'margin-top:0', text: 'Was diese Sammlung abfragt' }));
  kasten.append(h('p', { class: 'leise',
    text: 'Abgewählte Formgruppen werden abgeschaltet, nicht gelöscht — wer das '
        + 'Plus-que-parfait später wieder zuschaltet, findet seinen Lernstand vor.' }));

  // Aufgabentypen
  kasten.append(h('h3', { text: 'Aufgabentypen' }));
  for (const [kennung, t] of Object.entries(typen.typen)) {
    const haken = h('input', {
      type: 'checkbox', checked: gewaehlteTypen.has(kennung),
      onchange: (e) => {
        if (e.target.checked) gewaehlteTypen.add(kennung);
        else gewaehlteTypen.delete(kennung);
      },
    });
    kasten.append(h('label', { class: 'schalter' }, haken,
      h('span', { class: 'schalter-text' },
        h('b', { text: t.name }), h('span', { text: t.beschreibung }),
        // Ein Beispiel sagt mehr als die Beschreibung. Wer "Form
        // bestimmen" liest, weiß noch nicht, was ihn erwartet.
        t.beispiel
          ? h('span', { class: 'beispielzeile', text: t.beispiel })
          : null)));
  }

  // Formgruppen nach Wortart
  kasten.append(h('h3', { text: 'Formgruppen' }));
  for (const [wortart, liste] of Object.entries(gruppen.wortarten)) {
    if (!liste.length) continue;
    const reihe = h('div', { class: 'gruppenwahl' });
    // Was diese Gruppe ist, in einer Zeile — als Mouseover UND unten zum
    // Aufklappen, denn auf dem Telefon gibt es kein Mouseover.
    const erklaert = (g) => [g.name,
                             g.erklaerung ? `— ${g.erklaerung}` : null,
                             g.beispiel ? `(${g.beispiel})` : null,
                             `· ${g.zellen} ${g.zellen === 1 ? 'Form' : 'Formen'}`]
      .filter(Boolean).join(' ');
    for (const g of liste) {
      const knopf = h('button', {
        class: gewaehlteGruppen.has(g.kennung) ? 'aktiv' : null,
        title: erklaert(g),
        onclick: () => {
          if (gewaehlteGruppen.has(g.kennung)) gewaehlteGruppen.delete(g.kennung);
          else gewaehlteGruppen.add(g.kennung);
          knopf.className = gewaehlteGruppen.has(g.kennung) ? 'aktiv' : '';
        },
      }, g.kurz);
      reihe.append(knopf);
    }
    kasten.append(h('div', { style: 'margin-bottom:.8rem' },
      h('p', { class: 'leise', style: 'margin:.4rem 0 .3rem',
               text: wortartName(wortart) }), reihe,
      h('details', { class: 'gruppenhilfe' },
        h('summary', { text: 'Was ist das jeweils?' }),
        h('dl', {}, liste.map((g) => [
          h('dt', {}, g.kurz,
            h('span', { class: 'leise',
                        text: ` · ${g.zellen} ${g.zellen === 1 ? 'Form' : 'Formen'}` })),
          h('dd', {},
            h('span', { text: g.name }),
            g.erklaerung
              ? h('span', { class: 'leise', text: ` — ${g.erklaerung}` })
              : null,
            g.beispiel
              ? h('span', { class: 'beispielzeile', text: g.beispiel })
              : null),
        ])))));
  }

  const ungeprueft = h('input', {
    type: 'checkbox', checked: einstellungen.ungeprueft_abfragen,
  });
  kasten.append(h('label', { class: 'schalter' }, ungeprueft,
    h('span', { class: 'schalter-text' },
      h('b', { text: 'Ungeprüfte Formen mitabfragen' }),
      h('span', { text: 'Normalerweise werden von der KI oder einem Muster erzeugte '
                      + 'Formen erst nach Bestätigung abgefragt. Eine erfundene Form, '
                      + 'die unbemerkt gepaukt wird, ist schlimmer als eine fehlende.' }))));

  kasten.append(h('button', {
    class: 'wichtig', style: 'margin-top:.8rem',
    onclick: async () => {
      try {
        const ergebnis = await api.sammlungEinstellungenSetzen(zustand.sammlungId, {
          formgruppen: [...gewaehlteGruppen],
          typen: [...gewaehlteTypen],
          ungeprueft_abfragen: ungeprueft.checked,
        });
        const b = ergebnis.aufgaben;
        meldung(`Gespeichert — ${b.angelegt} neu, ${b.reaktiviert} wieder dabei, `
              + `${b.abgeschaltet} abgeschaltet.`, 4000);
        zeichnen(behaelter);
      } catch (fehler) { meldung(fehler.message); }
    },
  }, 'Speichern und Aufgaben neu rechnen'));
  return kasten;
}

function wortartName(w) {
  return { verb: 'Verben', substantiv: 'Substantive', adjektiv: 'Adjektive' }[w] || w;
}

/* --------------------------------------------------------- Lernverhalten */

async function teilLernen(behaelter) {
  const e = await api.benutzerEinstellungen(zustand.benutzerId);
  const kasten = h('div', { class: 'karte' });
  kasten.append(h('h2', { style: 'margin-top:0', text: 'Lernverhalten' }));

  const retention = h('input', {
    type: 'range', min: '0.80', max: '0.97', step: '0.01',
    value: String(e.wunschretention),
  });
  const retentionWert = h('output', { text: Math.round(e.wunschretention * 100) + ' %' });
  retention.addEventListener('input', () => {
    retentionWert.textContent = Math.round(Number(retention.value) * 100) + ' %';
  });

  const neu = h('input', { type: 'number', min: '0', max: '200', value: String(e.neu_je_sitzung) });

  kasten.append(h('div', { class: 'regler' },
    h('label', { text: 'Wie sicher soll etwas sitzen, wenn es wieder dran ist?' }),
    retentionWert, retention, h('span', {})));
  kasten.append(h('p', { class: 'leise',
    text: 'Höher heißt häufiger wiederholen und weniger vergessen, aber mehr '
        + 'Aufwand. 90 % ist der übliche Mittelweg; darunter wird es schnell lückig.' }));

  kasten.append(h('div', { class: 'regler' },
    h('label', { text: 'Neue Aufgaben je Tag' }), h('span', {}), neu, h('span', {})));

  const einstreuen = h('input', {
    type: 'checkbox', checked: Boolean(e.neues_einstreuen),
  });
  kasten.append(h('label', { class: 'schalter' }, einstreuen,
    h('span', { class: 'schalter-text' },
      h('b', { text: 'Neues durchgehend untermischen' }),
      h('span', { text: 'Normalerweise kommt erst alles Fällige dran und '
                      + 'danach Neues. Das ist für das Behalten das Beste, '
                      + 'macht eine lange Sitzung aber einseitig: man sieht '
                      + 'stundenlang dieselben Wörter.' }),
      h('span', { class: 'beispielzeile',
                  text: 'Eingeschaltet ist jede dritte Frage etwas Neues — '
                      + 'dafür rücken echte Wiederholungen etwas nach hinten.' }))));

  // Wie eine Form benannt wird. "Genitiv Singular" ist richtig und für
  // viele eine Mauer; wer daran scheitert, scheitert nicht an der Vokabel.
  const stil = h('select', {},
    h('option', { value: 'fach', text: 'Genitiv Singular' }),
    h('option', { value: 'beides', text: 'Genitiv Singular (wessen?, Einzahl)' }),
    h('option', { value: 'einfach', text: 'wessen?, Einzahl' }));
  stil.value = e.beschriftung || 'fach';
  kasten.append(h('div', { class: 'regler' },
    h('label', { text: 'Wie sollen die Formen benannt werden?' }),
    h('span', {}), stil, h('span', {})));
  kasten.append(h('p', { class: 'leise',
    text: 'Die Namen der Zeiten bleiben immer stehen — Αόριστος heißt im '
        + 'Lehrbuch so. Erklärt wird nur, welche Zelle darin gemeint ist.' }));

  // Im Legastheniemodus sind diese Werte ABGELEITET (0,95 statt 0,9 und
  // 8 statt 20). Würde man sie unverändert zurückschreiben, wären sie
  // fortan ausdrücklich gesetzt — und die Ableitung bliebe für immer
  // eingefroren, auch nach Abschalten des Modus. Darum wird nur gesendet,
  // was wirklich bewegt wurde.
  const ausgangswerte = { retention: e.wunschretention, neu: e.neu_je_sitzung,
                          stil: e.beschriftung || 'fach',
                          einstreuen: Boolean(e.neues_einstreuen) };
  if (e.legasthenie?.aktiv) {
    kasten.append(h('p', { class: 'leise',
      text: 'Diese Werte leitet der Legastheniemodus gerade ab. Wer sie hier '
          + 'bewegt, setzt sie fest — danach wirkt die Ableitung nicht mehr.' }));
  }

  kasten.append(h('button', {
    class: 'wichtig', style: 'margin-top:.6rem',
    onclick: async () => {
      const aenderungen = {};
      if (Number(retention.value) !== ausgangswerte.retention) {
        aenderungen.wunschretention = Number(retention.value);
      }
      if (Number(neu.value) !== ausgangswerte.neu) {
        aenderungen.neu_je_sitzung = Number(neu.value);
      }
      if (stil.value !== ausgangswerte.stil) {
        aenderungen.beschriftung = stil.value;
      }
      if (einstreuen.checked !== ausgangswerte.einstreuen) {
        aenderungen.neues_einstreuen = einstreuen.checked;
      }
      if (!Object.keys(aenderungen).length) {
        meldung('Nichts geändert.');
        return;
      }
      try {
        await api.benutzerAendern(zustand.benutzerId, aenderungen);
        meldung('Gespeichert.');
      } catch (fehler) { meldung(fehler.message); }
    },
  }, 'Speichern'));
  return kasten;
}

/* ------------------------------------------------------- Zugangsmerkmale */

async function teilZugaenge(behaelter) {
  const kasten = h('details', { class: 'karte' },
    h('summary', {}, h('strong', { text: 'Zugang für Claude (MCP)' })));
  let liste = [];
  try {
    liste = await api.mcpToken(zustand.benutzerId);
  } catch (fehler) {
    kasten.append(h('p', { class: 'leise', text: fehler.message }));
    return kasten;
  }

  kasten.append(h('p', { class: 'leise',
    text: 'Damit kann Claude Vokabeln für dich eintragen — mit vollständigen '
        + 'Paradigmen, was von Hand niemand tippt. Jedes Merkmal gehört zu '
        + 'DEINEM Profil: alles, was darüber geschieht, geschieht in deinem '
        + 'Namen und nur auf deinem Bestand. Je Gerät eines anlegen, dann '
        + 'lässt sich einzeln zurücknehmen, was abhandenkommt.' }));

  if (liste.length) {
    const tafel = h('div', { class: 'liste' });
    for (const t of liste) {
      tafel.append(h('div', { class: 'eintrag' },
        h('span', { class: 'lemma', text: t.name }),
        h('span', { class: 'bedeutung',
                    text: `${t.anfang}… · ${t.zuletzt_benutzt
                      ? 'zuletzt ' + datumText(t.zuletzt_benutzt.slice(0, 10))
                      : 'noch nie benutzt'}` }),
        t.aktiv
          ? h('button', {
              class: 'schlicht gefahr',
              onclick: async () => {
                if (!confirm(`Zugang „${t.name}" zurücknehmen? Claude kann `
                           + 'damit sofort nichts mehr eintragen.')) return;
                await api.mcpTokenZuruecknehmen(t.id);
                zeichnen(behaelter);
              },
            }, 'Zurücknehmen')
          : h('span', { class: 'marke warnung', text: 'zurückgenommen' })));
    }
    kasten.append(tafel);
  }

  // Vorbelegt, damit der Knopf nicht ins Leere läuft. Vorher blieb bei
  // leerem Feld nur eine Kurzmeldung, die nach zwei Sekunden verschwand —
  // es sah aus, als täte der Knopf nichts.
  const vorschlag = `Claude, ${new Date().toLocaleDateString('de-DE',
    { day: 'numeric', month: 'long' })}`;
  const name = h('input', {
    type: 'text', value: vorschlag,
    placeholder: 'z.B. Claude-App auf dem iPad',
    oninput: () => { hinweis.hidden = true; name.classList.remove('falsch'); },
  });
  const hinweis = h('p', {
    class: 'leise', hidden: true, style: 'margin:0;color:var(--falsch)',
    text: 'Gib dem Zugang einen Namen — dann weißt du später, welches '
        + 'Gerät du zurücknimmst.',
  });
  const knopf = h('button', {
    class: 'wichtig',
    onclick: async () => {
      if (!name.value.trim()) {
        hinweis.hidden = false;
        name.classList.add('falsch');
        name.focus();
        return;
      }
      knopf.disabled = true;
      knopf.textContent = 'Wird angelegt …';
      try {
        const neu = await api.mcpTokenAnlegen(zustand.benutzerId,
                                              { name: name.value.trim() });
        zeigeToken(kasten, neu);
        name.value = '';
      } catch (fehler) {
        hinweis.hidden = false;
        hinweis.textContent = fehler.message;
      } finally {
        knopf.disabled = false;
        knopf.textContent = 'Zugang anlegen';
      }
    },
  }, 'Zugang anlegen');

  kasten.append(h('div', { style: 'display:grid;gap:.5rem;margin-top:.8rem' },
    h('label', { class: 'leise', for: 'zugangsname',
                 text: 'Wofür ist der Zugang?' }),
    name, hinweis, knopf));
  return kasten;
}

/** Das Geheimnis wird nur dieses eine Mal angezeigt — danach steht es
 *  nirgends mehr, nur sein Streuwert. */
function zeigeToken(kasten, neu) {
  const feld = h('input', {
    type: 'text', value: neu.token, readonly: true,
    onclick: (e) => e.target.select(),
    style: 'font-family:ui-monospace,monospace;font-size:.9em',
  });
  kasten.append(h('div', { class: 'rueckmeldung fast', style: 'margin-top:.8rem' },
    h('div', { class: 'rueckmeldung-kopf' },
      h('span', { text: '!' }), h('span', { text: 'Nur jetzt sichtbar' })),
    h('p', { text: 'Das Zugangsmerkmal wird nicht gespeichert, nur sein '
                 + 'Streuwert. Jetzt kopieren — nachher ist es weg.' }),
    feld,
    h('div', { class: 'frage-werkzeuge', style: 'justify-content:flex-start' },
      h('button', {
        onclick: async () => {
          try {
            await navigator.clipboard.writeText(neu.token);
            meldung('In die Zwischenablage gelegt.');
          } catch { feld.select(); meldung('Bitte von Hand kopieren.'); }
        },
      }, 'Kopieren'))));
  feld.scrollIntoView({ block: 'nearest' });
}

/* ---------------------------------------------------------- Legasthenie */

async function teilLegasthenie(behaelter) {
  const lg = await api.legasthenieLesen(zustand.benutzerId);
  const kasten = h('details', { class: 'karte', open: lg.aktiv });
  kasten.append(h('summary', {}, h('strong', { text: 'Legastheniemodus' }),
    lg.aktiv ? h('span', { class: 'marke', text: 'an' }) : null));

  const stand = { ...lg };
  const uebernehmen = () => darstellungSetzen(stand);

  const probe = h('div', { class: 'probe' },
    h('p', { style: 'margin:0 0 .4rem', text: 'So sieht es aus:' }),
    h('p', { style: 'margin:0;font-family:var(--schrift-wort);font-size:1.3em;font-weight:600' },
      'nous travaillions'),
    h('p', { class: 'leise', style: 'margin:.2rem 0 0',
             text: 'Imparfait, 1. Person Plural' }));

  const anKnopf = h('input', {
    type: 'checkbox', checked: stand.aktiv,
    onchange: (e) => { stand.aktiv = e.target.checked; uebernehmen(); },
  });
  kasten.append(h('label', { class: 'schalter' }, anKnopf,
    h('span', { class: 'schalter-text' },
      h('b', { text: 'Legastheniemodus einschalten' }),
      h('span', { text: 'Ändert Darstellung und Lernablauf. Jeder Posten unten '
                      + 'einzeln abwählbar — Legasthenie sieht bei jedem anders aus.' }))));

  // ------------------------------- Darstellung
  kasten.append(h('h3', { text: 'Lesbarkeit' }));
  kasten.append(h('p', { class: 'leise',
    text: 'Zum Zeichenabstand ist die Befundlage gut: er erleichtert das Lesen '
        + 'messbar. Zu den eigens für Legasthenie entworfenen Schriftarten ist sie '
        + 'dünn — kontrollierte Vergleiche finden gegenüber einer schlichten '
        + 'Grotesk meist keinen Vorteil. Darum ist der Abstand hier der '
        + 'Hauptschalter und die Schrift nur ein Angebot. Am besten selbst '
        + 'ausprobieren, was sich leichter liest.' }));

  for (const [feld, beschriftung, min, max, schritt, einheit] of [
    ['zeichenabstand', 'Zeichenabstand', 0, 0.35, 0.01, 'em'],
    ['wortabstand', 'Wortabstand', 0, 0.6, 0.02, 'em'],
    ['zeilenhoehe', 'Zeilenabstand', 1.2, 2.6, 0.05, ''],
    ['schriftgroesse', 'Schriftgröße', 0.9, 2.0, 0.05, '×'],
  ]) {
    const regler = h('input', {
      type: 'range', min: String(min), max: String(max), step: String(schritt),
      value: String(stand[feld]),
    });
    const anzeige = h('output', { text: zahl(stand[feld], 2) + einheit });
    regler.addEventListener('input', () => {
      stand[feld] = Number(regler.value);
      anzeige.textContent = zahl(stand[feld], 2) + einheit;
      uebernehmen();
    });
    kasten.append(h('div', { class: 'regler' },
      h('label', { text: beschriftung }), anzeige, regler, h('span', {})));
  }

  const schriftWahl = h('select', {
    onchange: (e) => { stand.schriftart = e.target.value; uebernehmen(); },
  },
    h('option', { value: 'grotesk', text: 'Systemschrift (Grotesk)' }),
    h('option', { value: 'serifenlos', text: 'Verdana — breit laufend' }),
    h('option', { value: 'opendyslexic', text: 'OpenDyslexic (falls installiert)' }));
  schriftWahl.value = stand.schriftart;
  const grundWahl = h('select', {
    onchange: (e) => { stand.hintergrund = e.target.value; uebernehmen(); },
  },
    h('option', { value: 'creme', text: 'Creme — gedämpfter Kontrast' }),
    h('option', { value: 'hell', text: 'Weiß' }),
    h('option', { value: 'dunkel', text: 'Dunkel' }));
  grundWahl.value = stand.hintergrund;
  kasten.append(h('div', { class: 'regler' },
    h('label', { text: 'Schrift' }), h('span', {}), schriftWahl, h('span', {})));
  kasten.append(h('div', { class: 'regler' },
    h('label', { text: 'Hintergrund' }), h('span', {}), grundWahl, h('span', {})));
  kasten.append(probe);

  // ------------------------------- Lernablauf
  kasten.append(h('h3', { text: 'Lernablauf' }));
  for (const [feld, titel, erklaerung] of [
    ['silben_faerben', 'Silben abwechselnd hinterlegen',
     'Das Arbeitsgedächtnis hält drei bis vier Brocken, nicht zwölf Buchstaben.'],
    ['stamm_hervorheben', 'Stamm und Endung trennen',
     'Hier hat dieser Trainer einen Vorteil, den kein Kartenstapel hat: weil die '
     + 'Formen eines Wortes zusammenstehen, wird der Stamm abgeleitet statt geraten '
     + '— γράφ|ουμε ist die wirkliche Naht des Wortes, keine Silbentrennung.'],
    ['vorlesen_zuerst', 'Erst hören, dann sehen',
     'Mehrere Sinne gleichzeitig: sehen, hören, selbst schreiben. Wo es keine '
     + 'Stimme gibt — Mittelhochdeutsch —, entfällt es von selbst.'],
    ['erkennen_vor_schreiben', 'Beim ersten Mal erst ansehen',
     'Ins Leere tippen, was man noch nie gesehen hat, erzeugt nur einen Fehler, '
     + 'den man sich mitmerkt. Also zuerst ansehen und hören, dann schreiben.'],
    ['fehler_benennen', 'Fehlerart benennen',
     '„Du hast b und d vertauscht" ist eine brauchbare Auskunft, „falsch" ist keine.'],
    ['mehr_wiederholungen', 'Häufiger wiederholen',
     'Setzt die Zielsicherheit auf 95 % statt 90 % — kürzere Abstände, weniger '
     + 'Vergessen. Eine eigene Vorgabe oben hat Vorrang.'],
    ['weniger_neues', 'Weniger Neues auf einmal',
     'Acht neue Aufgaben je Tag statt zwanzig.'],
    ['keine_zeitmessung', 'Keine Zeitmessung',
     'Nichts wird mitgestoppt. Zeitdruck verschlechtert gerade hier das Ergebnis.'],
  ]) {
    const haken = h('input', {
      type: 'checkbox', checked: Boolean(stand[feld]),
      onchange: (e) => { stand[feld] = e.target.checked; },
    });
    kasten.append(h('label', { class: 'schalter' }, haken,
      h('span', { class: 'schalter-text' },
        h('b', { text: titel }), h('span', { text: erklaerung }))));
  }

  const maske = h('select', { onchange: (e) => { stand.maske_stufe = Number(e.target.value); } },
    h('option', { value: '0', text: 'Nichts vorgeben' }),
    h('option', { value: '1', text: 'Ersten Buchstaben zeigen' }),
    h('option', { value: '2', text: 'Ersten und letzten zeigen' }),
    h('option', { value: '3', text: 'Alle Mitlaute zeigen' }));
  maske.value = String(stand.maske_stufe ?? 2);
  kasten.append(h('div', { class: 'regler' },
    h('label', { text: 'Gerüst beim Schreiben' }), h('span', {}), maske, h('span', {})));

  kasten.append(h('div', { class: 'frage-werkzeuge', style: 'justify-content:flex-start' },
    h('button', {
      class: 'wichtig',
      onclick: async () => {
        try {
          const gespeichert = await api.legasthenieSetzen(zustand.benutzerId, stand);
          darstellungSetzen(gespeichert);
          meldung('Gespeichert.');
        } catch (fehler) { meldung(fehler.message); }
      },
    }, 'Speichern'),
    h('button', {
      onclick: async () => { darstellungSetzen(lg); zeichnen(behaelter); },
    }, 'Verwerfen')));
  return kasten;
}
