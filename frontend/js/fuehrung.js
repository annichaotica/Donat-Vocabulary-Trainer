/* Geführte Rundgänge durch den Trainer.
 *
 * »Kannst du für das erste Öffnen eine Tour durch das Tool bauen?
 * Quasi, diese Schaltfläche macht dies, diese Schaltfläche macht das,
 * hier erfährst du mehr? Eventuell wäre es dann sinnvoll, mehrere
 * Führungen zu machen?«
 *
 * Mehrere, ja. Eine Tour über fünfzehn Funktionen hat niemand zu Ende
 * gesehen. Vier kurze, die man einzeln nehmen kann, und jede hört an
 * einer Stelle auf, an der man etwas tun will.
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
    kennung: 'erste-schritte',
    name: 'Erste Schritte',
    dauer: '2 Minuten',
    beschreibung: 'Was wo steht und womit man anfängt.',
    schritte: [
      { seite: '#/uebersicht',
        titel: 'Das ist deine Übersicht',
        text: 'Oben steht, was heute ansteht: fällig, verlernt, neu. '
            + 'Darunter deine Sammlungen — eine Sammlung ist ein '
            + 'Wortschatz, meist ein Lehrbuch.' },
      { seite: '#/uebersicht', ziel: '.karte .zahlen',
        titel: 'Die vier Zahlen',
        text: '»Fällig« heißt: heute planmäßig dran. »Verlernt« ist '
            + 'danebengegangen und kommt bald wieder. »Neu« war noch '
            + 'nie dran. »Sitzt« kannst du dauerhaft.' },
      { seite: '#/uebersicht', ziel: 'button.wichtig',
        titel: 'Hier geht es los',
        text: '»Lernen« fragt nach dem Plan ab — der Trainer sucht aus, '
            + 'was dran ist. Daneben »Frei üben« ohne Plan und '
            + '»Fehler wiederholen« für das, was zuletzt schiefging.' },
      { seite: '#/uebersicht', ziel: '.sammlungen > .karte',
        titel: 'Eine Sammlungskarte',
        text: 'Jede Sammlung hat ihre eigenen Knöpfe: Lernen, '
            + 'Wortschatz ansehen, Sätze üben, Texte lesen, Vokabeln '
            + 'einlesen, gezielt üben. Alles, was zu dieser Sprache '
            + 'gehört, hängt an dieser Karte.' },
      { seite: '#/uebersicht', ziel: '.sammlungen input[type=checkbox]',
        titel: 'Lerne ich das mit?',
        text: 'Eigene Sammlungen sind angehakt. Was dir jemand nur zum '
            + 'Mitpflegen freigegeben hat, ist es nicht — sonst lägen '
            + 'fremde Vokabeln zwischen deinen.' },
    ],
  },
  {
    kennung: 'abfrage',
    name: 'Eine Abfrage von innen',
    dauer: '2 Minuten',
    beschreibung: 'Was passiert, wenn du antwortest.',
    schritte: [
      { seite: '#/lernen', ziel: '.frage',
        titel: 'Die Frage',
        text: 'Oben die Aufgabenart, darunter das Gefragte. Bei Formen '
            + 'steht die Formangabe dabei, mit einem deutschen '
            + 'Beispiel — damit klar ist, was gemeint ist.' },
      { seite: '#/lernen', ziel: '.antwortfeld input, .antwortfeld textarea',
        titel: 'Antworten',
        text: 'Tippen und Enter. Fast richtig kostet nichts: liegt nur '
            + 'ein Zeichen daneben, darfst du noch einmal. Bei '
            + 'Griechisch brauchst du nichts umzuschalten — tippe '
            + 'einfach lateinisch.' },
      { seite: '#/lernen', ziel: '.frage-werkzeuge',
        titel: 'Wenn du nicht weiterweißt',
        text: '»Tipp« deckt Stück für Stück auf und bleibt in der '
            + 'Abfrage. »Weiß ich nicht« ist die ehrliche Auskunft — '
            + 'das Wort kommt bald wieder. »Aussetzen« legt es ganz '
            + 'beiseite.' },
      { seite: '#/lernen', ziel: 'details',
        titel: 'Warum kommt das jetzt?',
        text: 'Aufklappen, und der Trainer sagt, warum gerade diese '
            + 'Frage dran ist und wann das Wort wiederkommt. Nichts '
            + 'davon ist geheim.' },
    ],
  },
  {
    kennung: 'planen',
    braucht_sammlung: true,
    name: 'Planen: Ziele und Lehrwerk',
    dauer: '3 Minuten',
    beschreibung: 'Einen Block bis Freitag, und nichts aus Kapiteln, '
                + 'die ihr noch nicht hattet.',
    schritte: [
      { seite: '#/ziele',
        titel: 'Lernziele',
        text: 'Ein Lernziel ist ein Ausschnitt mit einem Ziel davor: '
            + '»Lektion 3 bis Freitag«. Trägst du einen Termin ein, '
            + 'rechnet der Trainer aus, wie viel täglich nötig wäre.' },
      { seite: '#/ziele',
        // Mit Ziel der Knopf, ohne Ziel der Ausklapper zum Anlegen —
        // auf der Seite steht sonst nichts, worauf man zeigen könnte.
        ziel: () => knopfMit('Was käme dran')()
                 || document.querySelector('details.karte'),
        titel: 'Was käme dran?',
        text: 'Hast du ein Ziel, zeigt dieser Knopf den nächsten Block, '
            + 'bevor du anfängst, und begründet ihn. Gefällt er dir '
            + 'nicht, würfelst du neu — der Zuschnitt bleibt, nur die '
            + 'Wörter wechseln. Noch kein Ziel? Dann legst du hier '
            + 'eines an.' },
      // Das FELD, nicht die ganze Karte: die ist höher als der
      // Bildschirm, und ein Ziel, das nirgends hinpasst, drängt die
      // Blase an den Rand — im Betrieb waren ihre Knöpfe nicht mehr
      // zu sehen, und man kam aus dem Rundgang nicht heraus.
      { seite: '#/einstellungen/lehrgang',
        ziel: '#inhalt input[type=number]',
        titel: 'Wo stehst du im Lehrwerk?',
        text: 'Hier trägst du ein, bei welcher Lektion du bist. '
            + 'Darunter steht, ab welcher Lektion das Buch welche '
            + 'Zeitform einführt — vorgeschlagen aus den '
            + 'Lektionsnamen. Was später kommt, bleibt draußen, bis '
            + 'du dort ankommst. Nichts geht dabei verloren.' },
    ],
  },
  {
    kennung: 'texte',
    braucht_sammlung: true,
    name: 'Texte lesen und übersetzen',
    dauer: '2 Minuten',
    beschreibung: 'Einen Text einwerfen und sehen, ob du ihn schon '
                + 'könntest.',
    schritte: [
      { seite: '#/texte',
        titel: 'Deine Texte',
        text: 'Hier kannst du einen Text einfügen oder hochladen — aus '
            + 'dem Buch, aus der Zeitung, was du willst. Leerzeilen '
            + 'trennen die Absätze, in denen du übersetzt.' },
      { seite: '#/texte', ziel: 'details',
        titel: 'Text einwerfen',
        text: 'Aufklappen, einfügen, speichern. Im Übungskurs liegt '
            + 'schon einer bereit.' },
      { seite: '#/texte',
        titel: 'Was dich dort erwartet',
        text: 'Über dem Text steht, ob du ihn schon übersetzen '
            + 'könntest. Jedes Wort ist anklickbar und zeigt deinen '
            + 'eigenen Eintrag. Rot unterlegte kennst du noch nicht — '
            + 'die kannst du antippen und für dein Chatprogramm '
            + 'merken, das trägt sie dir dann ein.' },
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
  if (rundgang.braucht_sammlung && !zustand.sammlungId) {
    vorher = zustand.sammlungId ?? null;
    try {
      const alle = await api.sammlungen(zustand.benutzerId);
      // Den Übungskurs bevorzugen: an ihm ist alles vorführbar, und
      // er gehört niemandem im Ernst.
      const wahl = alle.find((x) => x.name.includes('Übungskurs'))
                || alle.find((x) => x.lerne_ich) || alle[0];
      if (wahl) zustandMerken({ sammlungId: wahl.id, lektionId: null });
    } catch { /* dann eben ohne — der Rundgang läuft trotzdem */ }
  }
  laeuft = { rundgang, nr: 0, versuche: 0, teile: aufbauen(),
             sammlungZurueck: vorher };
  window.addEventListener('hashchange', neuAnsetzen);
  zeigen();
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
  const blase = h('div', { class: 'fuehrung-blase' }, titel, text,
    h('div', { class: 'fuehrung-knoepfe' }, zaehler, zurueck, weiter, schluss));
  const huelle = h('div', { class: 'fuehrung' }, blase);
  document.body.append(huelle);
  return { huelle, blase, titel, text, zaehler, zurueck, weiter };
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
