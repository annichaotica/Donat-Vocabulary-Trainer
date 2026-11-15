/* Geführte Rundgänge durch den Trainer.
 *
 * »Kannst du für das erste Öffnen eine Tour durch das Tool bauen?
 * Quasi, diese Schaltfläche macht dies, diese Schaltfläche macht das,
 * hier erfährst du mehr? Eventuell wäre es dann sinnvoll, mehrere
 * Führungen zu machen?«
 *
 * Mehrere, ja. Eine Tour über fünfzehn Funktionen hat niemand zu Ende
 * gesehen.
 *
 * Nach dem ersten Durchlauf überarbeitet, mit einer klaren Aufteilung:
 * ein Rundgang sagt nur noch, WO etwas liegt. Das WARUM steht im
 * Lehrgang. Vorher stand beides in den Blasen — »fast richtig kostet
 * nichts«, »der Tipp macht die Aufgabe schwer« —, und eine Blase ist
 * dafür der falsche Ort: drei Sätze, vorbei, nichts zum Nachschlagen.
 * Jeder Rundgang endet darum mit dem Verweis auf sein Kapitel.
 *
 * Zwei Entscheidungen, die den Rest erklären:
 *
 * ÜBER SEITEN HINWEG. Ein Rundgang führt von der Übersicht in die
 * Abfrage; dabei zeichnet die Anwendung alles neu. Der Rundgang lebt
 * deshalb außerhalb des Inhalts, hängt an `hashchange` und sucht sein
 * Ziel nach jedem Wechsel neu.
 *
 * KEIN SCHRITT HÄLT DEN RUNDGANG AUF. Findet sich ein Ziel nicht —
 * weil die Sammlung leer ist, weil ein Knopf nur unter Bedingungen
 * erscheint —, wird der Text trotzdem gezeigt, nur ohne Hervorhebung.
 * Ein Rundgang, der an einem fehlenden Knopf hängenbleibt, ist
 * schlimmer als keiner: man kommt nicht mehr heraus.
 */

import { h } from './hilfen.js';
import { api } from './api.js';
// `merken` heißt hier schon etwas anderes (die Merkliste der
// gesehenen Rundgänge), darum unter anderem Namen.
import { zustand, merken as zustandMerken } from './zustand.js';

const GESEHEN = 'vokabeltrainer.fuehrungen';

// Wie oft nach einem noch fehlenden Ziel gesehen wird, je 250 ms.
const VERSUCHE = 8;

export const RUNDGAENGE = [
  {
    kennung: 'wo-ist-was',
    name: 'Wo ist was',
    dauer: '2 Minuten',
    beschreibung: 'Der Rundgang für den ersten Tag.',
    kapitel: ['lernen', 0],
    schritte: [
      { seite: '#/uebersicht', ziel: '#kopf',
        titel: 'Oben steht, wo du bist',
        text: 'Links der Name der Ansicht, darunter die Sammlung, in der '
            + 'du gerade steckst — mit ihrer Farbe. Rechts die Reiter, '
            + 'ganz rechts dein Profil.' },
      { seite: '#/uebersicht', ziel: '.karte .zahlen',
        titel: 'Was heute ansteht',
        text: 'Fällig, verlernt, neu, sitzt. Darunter die Knöpfe, mit '
            + 'denen du loslegst — »Lernen« folgt dem Plan, »Frei üben« '
            + 'ignoriert ihn.' },
      { seite: '#/uebersicht', ziel: '.sammlungen > .karte',
        titel: 'Eine Sammlung',
        text: 'Ein Wortschatz, meist ein Lehrbuch. Alles, was dazugehört, '
            + 'hängt an dieser Karte: lernen, nachschlagen, Sätze, Texte, '
            + 'einlesen, einstellen.' },
      { seite: '#/uebersicht', ziel: '.sortierzeile',
        titel: 'Wenn es zu viele werden',
        text: 'Hier sortierst du die Sammlungen und klappst ein, was '
            + 'du gerade nicht brauchst.' },
      { seite: '#/uebersicht', ziel: () => knopfMit('Fortschritt')(),
        titel: 'Und wie läuft es?',
        text: '»Fortschritt« zeigt, was du getan hast und was in den '
            + 'nächsten Wochen auf dich zukommt.' },
    ],
  },
  {
    kennung: 'abfrage',
    name: 'In der Abfrage',
    dauer: '2 Minuten',
    beschreibung: 'Die Knöpfe unter der Frage.',
    sammlung: 'beliebig',
    kapitel: ['lernen', 0],
    schritte: [
      { seite: '#/lernen', ziel: '.frage',
        titel: 'Die Frage',
        text: 'Oben die Aufgabenart, darunter das Gefragte. Bei Formen '
            + 'steht die Formangabe dabei, mit einem deutschen Beispiel.' },
      { seite: '#/lernen', ziel: '.antwortfeld input, .antwortfeld textarea',
        titel: 'Hier tippst du',
        text: 'Enter prüft. Bei Griechisch tippst du lateinisch — es '
            + 'erscheint griechisch, ohne dass du etwas umschaltest.' },
      { seite: '#/lernen', ziel: '.frage-werkzeuge',
        titel: 'Wenn es klemmt',
        text: '»Tipp« deckt Stück für Stück auf. »Weiß ich nicht« sagt '
            + 'die Wahrheit. »Aussetzen« legt die Aufgabe beiseite. Und '
            + '»Schluss für heute« bringt dich zurück zur Übersicht.' },
      { seite: '#/lernen', ziel: 'details',
        titel: 'Warum kommt das jetzt?',
        text: 'Aufklappen, und der Trainer legt seine Rechnung offen.' },
    ],
  },
  {
    kennung: 'eintragen',
    name: 'Ein Wort eintragen',
    dauer: '2 Minuten',
    beschreibung: 'Die Maske für Vokabeln mit Formen.',
    sammlung: 'beliebig',
    kapitel: ['pflegen', 1],
    schritte: [
      { seite: '#/neu', ziel: '#inhalt input',
        titel: 'Die Grundform',
        text: 'Das Wort, wie es im Wörterbuch steht. Bei griechischen '
            + 'Substantiven mit Artikel: »το μήλο«.' },
      { seite: '#/neu', ziel: '#inhalt select',
        titel: 'Die Wortart entscheidet alles Weitere',
        text: 'Aus ihr ergibt sich, welche Formfelder du unten bekommst. '
            + 'Ein Verb bringt Zeiten mit, ein Substantiv Fälle.' },
      { seite: '#/neu', ziel: '#inhalt details',
        titel: 'Die Formen',
        text: 'Je Zeit oder Tabelle ein Block zum Aufklappen. Leer lassen '
            + 'ist erlaubt — nur was dasteht, wird abgefragt.' },
      { seite: '#/neu', ziel: () => knopfMit('Anlegen')(),
        titel: 'Anlegen',
        text: 'Danach entstehen die Aufgaben von selbst. Was du von Hand '
            + 'einträgst, ist sofort abfragbar; was die KI einträgt, '
            + 'wartet auf deine Freigabe.' },
    ],
  },
  {
    kennung: 'freigabe',
    name: 'Freigeben, was wartet',
    dauer: '2 Minuten',
    beschreibung: 'Die Prüfansicht für Einträge der KI.',
    sammlung: 'mit_offenem',
    kapitel: ['pflegen', 2],
    schritte: [
      { seite: '#/freigabe',
        titel: 'Was hier liegt, wird nicht abgefragt',
        text: 'Alles, was die KI oder ein Import eingetragen hat, wartet '
            + 'hier, bis ein Mensch es angesehen hat. Geordnet nach '
            + 'Lektionen.' },
      // Eine Liste, keine Kartenreihe: die Lektionsübersicht der
      // Freigabe benutzt .liste/.eintrag. Ich hatte .karte geraten,
      // und der Schritt zeigte ins Leere.
      { seite: '#/freigabe', ziel: '#inhalt .liste .eintrag',
        titel: 'Eine Lektion aufschlagen',
        text: 'Darin steht Wort für Wort, welche Formen warten — und '
            + 'woher sie stammen.' },
      { seite: '#/freigabe',
        titel: 'Einzeln oder im Ganzen',
        text: 'Je Wort gibt es »Alles in Ordnung«, »Später ansehen« und '
            + '»Bearbeiten«. Unten gibst du die ganze Lektion frei. Sieh '
            + 'vorher wirklich hin: die KI irrt besonders bei '
            + 'unregelmäßigen Formen.' },
    ],
  },
  {
    kennung: 'planen',
    name: 'Planen: Ziele und Lehrwerk',
    dauer: '2 Minuten',
    beschreibung: 'Ein Block bis Freitag — und nichts aus Kapiteln, die '
                + 'ihr noch nicht hattet.',
    sammlung: 'beliebig',
    kapitel: ['pflegen', 5],
    schritte: [
      { seite: '#/ziele',
        titel: 'Lernziele',
        text: 'Ein Ausschnitt mit einem Ziel davor: »Lektion 3 bis '
            + 'Freitag«. Hier legst du eines an oder änderst es.' },
      { seite: '#/ziele',
        ziel: () => knopfMit('Was käme dran')()
                 || document.querySelector('details.karte'),
        titel: 'Was käme dran?',
        text: 'Zeigt den nächsten Block, bevor du anfängst. Gefällt er '
            + 'dir nicht, würfelst du neu.' },
      { seite: '#/einstellungen/lehrgang',
        ziel: '#inhalt input[type=number]',
        titel: 'Wo stehst du im Lehrwerk?',
        text: 'Hier trägst du deine Lektion ein. Darunter steht, ab '
            + 'welcher Lektion das Buch welche Zeitform einführt.' },
    ],
  },
  {
    kennung: 'texte',
    name: 'Texte lesen und übersetzen',
    dauer: '2 Minuten',
    beschreibung: 'Einen Text einwerfen und sehen, ob du ihn könntest.',
    sammlung: 'beliebig',
    kapitel: ['lernen', 2],
    schritte: [
      { seite: '#/texte',
        titel: 'Deine Texte',
        text: 'Aus dem Buch, aus der Zeitung, was du willst. Leerzeilen '
            + 'trennen die Absätze, in denen du übersetzt.' },
      { seite: '#/texte', ziel: 'details',
        titel: 'Text einwerfen',
        text: 'Aufklappen, einfügen oder eine Datei wählen, speichern.' },
      { seite: '#/texte',
        titel: 'Und dann?',
        text: 'Über dem Text steht, ob du ihn schon übersetzen könntest. '
            + 'Jedes Wort ist anklickbar, rot unterlegte kennst du noch '
            + 'nicht — die kannst du für dein Chatprogramm merken.' },
    ],
  },
];

// ------------------------------------------------------------ Gedächtnis

function gesehen() {
  try { return JSON.parse(localStorage.getItem(GESEHEN) || '[]'); }
  catch { return []; }
}

function merken(kennung) {
  try {
    const alle = new Set(gesehen());
    alle.add(kennung);
    localStorage.setItem(GESEHEN, JSON.stringify([...alle]));
  } catch { /* privates Fenster — dann eben ohne Gedächtnis */ }
}

export function schonGesehen(kennung) {
  return gesehen().includes(kennung);
}

/** »Die Tutorials soll man natürlich auch ausblenden können.«
 *
 * Kein eigener Schalter, sondern dieselbe Merkliste: alle als gesehen
 * eintragen. Dadurch gibt es nur EINEN Zustand und keine zweite
 * Einstellung, die dem ersten widersprechen könnte — und über die
 * Anleitung bleiben sie erreichbar.
 */
export function alleAusblenden() {
  for (const r of RUNDGAENGE) merken(r.kennung);
}


/** Die Merkliste leeren — für »von vorn«. */
export function wiederZeigen() {
  try { localStorage.removeItem(GESEHEN); } catch { /* egal */ }
}


export function alleGesehen() {
  return RUNDGAENGE.every((r) => schonGesehen(r.kennung));
}


// -------------------------------------------------------------- Der Lauf

let laeuft = null;

export async function starten(kennung) {
  const rundgang = RUNDGAENGE.find((r) => r.kennung === kennung);
  if (!rundgang) return;
  beenden();
  // Manche Seiten gibt es nur MIT Sammlung — »Texte« sagt sonst nur
  // »erst eine Sammlung wählen«, und der Rundgang zeigt auf einen
  // Satz statt auf das, wovon er spricht. Also hier eine wählen und
  // am Ende zurückgeben: ein Rundgang soll nichts hinterlassen.
  let vorher;
  if (rundgang.sammlung) {
    vorher = zustand.sammlungId ?? null;
    const wahl = await sammlungFinden(rundgang.sammlung);
    if (wahl) zustandMerken({ sammlungId: wahl, lektionId: null });
  }
  laeuft = { rundgang, nr: 0, versuche: 0, teile: aufbauen(),
             sammlungZurueck: vorher };
  window.addEventListener('hashchange', neuAnsetzen);
  zeigen();
}

/** Eine Sammlung, an der sich der Rundgang vorführen lässt.
 *
 * »mit_offenem« für die Freigabe: eine Prüfansicht ohne Wartendes
 * zeigt nur den Satz »es wartet nichts« — der Rundgang zeigte dann
 * auf eine leere Seite statt auf das, wovon er spricht. Die Zahl der
 * offenen Formen steht schon in der Sammlungsliste.
 *
 * Die gerade gewählte Sammlung wird BEHALTEN, wenn sie passt: wer
 * schon in seinem Griechisch steht, soll den Rundgang dort sehen und
 * nicht in einem Beispielkurs.
 */
async function sammlungFinden(bedarf) {
  let alle = [];
  try { alle = await api.sammlungen(zustand.benutzerId); }
  catch { return null; }
  const taugt = (x) => (bedarf === 'mit_offenem'
    ? (x.offene_formen || 0) + (x.offene_uebungen || 0) > 0 : true);
  const jetzige = alle.find((x) => x.id === zustand.sammlungId);
  if (jetzige && taugt(jetzige)) return jetzige.id;
  const wahl = alle.find((x) => taugt(x) && x.name.includes('Übungskurs'))
            || alle.find((x) => taugt(x) && x.lerne_ich)
            || alle.find(taugt);
  return wahl ? wahl.id : (jetzige ? jetzige.id : (alle[0]?.id ?? null));
}


export function beenden() {
  if (!laeuft) return;
  window.removeEventListener('hashchange', neuAnsetzen);
  hervorhebungWeg();
  laeuft.teile.huelle.remove();
  // Die geliehene Sammlung zurückgeben. `undefined` heißt »nichts
  // geliehen«; `null` heißt »es war vorher keine gewählt«.
  if (laeuft.sammlungZurueck !== undefined) {
    zustandMerken({ sammlungId: laeuft.sammlungZurueck });
  }
  laeuft = null;
}

function aufbauen() {
  const titel = h('h2', { class: 'fuehrung-titel' });
  const text = h('p', { class: 'fuehrung-text' });
  const zaehler = h('span', { class: 'leise fuehrung-zaehler' });
  const zurueck = h('button', { onclick: () => springen(-1) }, 'Zurück');
  const weiter = h('button', { class: 'wichtig', onclick: () => springen(1) },
                   'Weiter');
  const schluss = h('button', { class: 'schlicht', onclick: abbrechen },
                    'Beenden');
  const weiterlesen = h('p', { class: 'leise fuehrung-mehr', hidden: true },
    h('a', {
      href: '#/lehrgang',
      onclick: (e) => {
        e.preventDefault();
        const [spur, kapitel] = laeuft?.rundgang.kapitel || [];
        abbrechen();
        if (spur !== undefined) location.hash = `#/lehrgang/${spur}/${kapitel}`;
      },
    }, 'Warum das so ist, steht im Lehrgang →'));
  const blase = h('div', { class: 'fuehrung-blase' }, titel, text, weiterlesen,
    h('div', { class: 'fuehrung-knoepfe' }, zaehler, zurueck, weiter, schluss));
  const huelle = h('div', { class: 'fuehrung' }, blase);
  document.body.append(huelle);
  return { huelle, blase, titel, text, zaehler, zurueck, weiter,
           weiterlesen };
}

function abbrechen() {
  if (!laeuft) return;
  merken(laeuft.rundgang.kennung);
  // Ein Rundgang endet oft in einer Ecke der Anwendung — in den
  // Einstellungen, in einer laufenden Abfrage. Wer dort stehen
  // bleibt, muss sich erst wieder zurechtfinden. Also immer zurück an
  // den Anfang, von dem aus alles erreichbar ist.
  //
  // Hier stand erst ein Vergleich mit der Startseite des Rundgangs —
  // der war verdreht: endete man dort, wo man angefangen hatte, blieb
  // man stehen. Es gibt nichts zu vergleichen, das Ziel ist immer
  // dasselbe.
  beenden();
  location.hash = '#/uebersicht';
}

function springen(richtung) {
  if (!laeuft) return;
  const nr = laeuft.nr + richtung;
  if (nr >= laeuft.rundgang.schritte.length) { abbrechen(); return; }
  laeuft.nr = Math.max(0, nr);
  laeuft.versuche = 0;
  zeigen();
}

/** Nach einem Seitenwechsel ist der Inhalt neu gezeichnet — das Ziel
 *  muss neu gesucht werden. Ein kurzer Aufschub, weil das Zeichnen
 *  Daten nachlädt; ohne ihn zeigt der Rundgang auf eine leere Seite. */
function neuAnsetzen() {
  if (laeuft) setTimeout(() => zeigen(true), 350);
}

function zeigen(nurAnsetzen = false) {
  if (!laeuft) return;
  const { rundgang, nr, teile } = laeuft;
  const schritt = rundgang.schritte[nr];

  // Auf der richtigen Seite? Sonst erst hin — der Rundgang setzt sich
  // nach dem hashchange von selbst fort.
  if (schritt.seite && !location.hash.startsWith(schritt.seite)) {
    if (!nurAnsetzen) { location.hash = schritt.seite; return; }
  }

  teile.titel.textContent = schritt.titel;
  teile.text.textContent = schritt.text;
  // Beim letzten Schritt der Verweis auf das Kapitel, das erklärt,
  // WARUM das alles so ist. Ein Rundgang sagt nur, wo etwas liegt;
  // alles Weitere gehört an einen Ort, den man wiederfindet.
  teile.weiterlesen.hidden = !(rundgang.kapitel
                               && nr === rundgang.schritte.length - 1);
  teile.zaehler.textContent = `${nr + 1} von ${rundgang.schritte.length}`;
  teile.zurueck.disabled = nr === 0;
  teile.weiter.textContent = nr === rundgang.schritte.length - 1
    ? 'Fertig' : 'Weiter';

  hervorhebungWeg();
  const ziel = finden(schritt.ziel);
  if (!ziel && schritt.ziel && laeuft.versuche < VERSUCHE) {
    // Noch nicht da — die Seite lädt ihre Daten nach. Ein fester
    // Aufschub wäre geraten: zu kurz, und der erste Schritt zeigt ins
    // Leere (genau das passierte beim Rundgang durch die Abfrage), zu
    // lang, und jeder Schritt ruckelt. Also nachsehen statt warten.
    laeuft.versuche += 1;
    setTimeout(() => zeigen(true), 250);
    return;
  }
  laeuft.versuche = 0;
  if (ziel) {
    ziel.classList.add('fuehrung-ziel');
    laeuft.hervorgehoben = ziel;
    // SOFORT rollen, nicht sanft. Beim sanften Rollen stand die Blase
    // an der Stelle, an der das Ziel VOR dem Rollen war — und lag
    // danach mitten darauf. Genau so war »Wo stehst du im Lehrwerk?«
    // zu sehen: das richtige Feld hervorgehoben, die Erklärung
    // darüber.
    ziel.scrollIntoView({ block: 'center', behavior: 'instant' });
    // Und erst im nächsten Bild messen: vorher steht weder die Höhe
    // der Blase noch die endgültige Lage des Ziels fest.
    requestAnimationFrame(() => {
      if (!laeuft || laeuft.hervorgehoben !== ziel) return;
      setzen(teile.blase, ziel);
      // Was draußen liegt, wird hereingezogen — eine Blase, deren
      // Knöpfe außerhalb des Bildschirms liegen, sperrt den Rundgang zu.
      hereinziehen(teile.blase);
    });
  } else {
    // Kein Ziel oder nicht gefunden: die Blase in die Mitte. Der Text
    // steht trotzdem, und der Rundgang läuft weiter.
    teile.blase.style.cssText = '';
    teile.blase.classList.add('fuehrung-mitte');
  }
}

/** Ein Ziel ist ein CSS-Wähler ODER eine Funktion.
 *
 * Die Funktion braucht es, wo CSS nicht hinreicht: »der Knopf mit der
 * Aufschrift ›Was käme dran?‹« lässt sich nicht als Wähler
 * ausdrücken, und derselbe Schritt soll auf »Lernziel anlegen«
 * zeigen, solange es noch kein Ziel gibt.
 */
function finden(ziel) {
  if (!ziel) return null;
  try {
    return typeof ziel === 'function' ? ziel() : document.querySelector(ziel);
  } catch { return null; }
}


/** Der erste Knopf, dessen Aufschrift einen der Texte enthält. */
export function knopfMit(...texte) {
  return () => [...document.querySelectorAll('button')]
    .find((b) => texte.some((t) => b.textContent.includes(t))) || null;
}


/** Zieht die Blase vollständig in den Bildschirm. */
function hereinziehen(blase) {
  const luft = 8;
  const r = blase.getBoundingClientRect();
  let { top, left } = r;
  top = Math.max(luft, Math.min(top, window.innerHeight - r.height - luft));
  left = Math.max(luft, Math.min(left, window.innerWidth - r.width - luft));
  if (Math.round(top) !== Math.round(r.top)
      || Math.round(left) !== Math.round(r.left)) {
    blase.style.top = `${top}px`;
    blase.style.left = `${left}px`;
  }
}


function hervorhebungWeg() {
  if (laeuft?.hervorgehoben) {
    laeuft.hervorgehoben.classList.remove('fuehrung-ziel');
    laeuft.hervorgehoben = null;
  }
}

/** Die Blase neben das Ziel — und niemals darüber.
 *
 * Erst unter das Ziel, dann darüber, und wenn beides nicht reicht,
 * daneben. Vorher wurde bei zu wenig Platz oben einfach `top - 190`
 * gesetzt: die Blase lag dann MITTEN auf dem Element, das sie
 * erklärt. Genau so war es bei einer hohen Lernzielkarte zu sehen.
 */
function setzen(blase, ziel) {
  blase.classList.remove('fuehrung-mitte');
  blase.style.cssText = '';
  const r = ziel.getBoundingClientRect();
  const hoehe = blase.offsetHeight || 190;
  const breite = blase.offsetWidth || 352;
  const luft = 12;

  let oben;
  if (window.innerHeight - r.bottom > hoehe + luft) {
    oben = r.bottom + luft;                       // darunter
  } else if (r.top > hoehe + luft) {
    oben = r.top - hoehe - luft;                  // darüber
  } else {
    oben = null;                                  // daneben
  }

  if (oben === null) {
    // Weder darüber noch darunter Platz — das Ziel ist größer als der
    // Bildschirm. Dann unten festhalten statt danebenquetschen: so
    // bleibt die Blase ganz sichtbar, und vor allem bleiben ihre
    // Knöpfe erreichbar. Ohne das stand sie halb außerhalb, und der
    // Rundgang ließ sich weder fortsetzen noch beenden.
    blase.style.cssText =
      `top:${window.innerHeight - hoehe - luft}px;`
      + `left:${Math.round((window.innerWidth - breite) / 2)}px;`;
    return;
  }
  const links = Math.max(luft,
    Math.min(r.left, window.innerWidth - breite - luft));
  blase.style.cssText = `top:${oben}px;left:${links}px;`;
}
