/* Sitzungszustand: wer lernt, welche Sammlung, welche Darstellung.
 *
 * Im Browser gemerkt, damit das iPad nicht bei jedem Öffnen nach dem Profil
 * fragt. Die Lerndaten selbst liegen ausschließlich auf dem Server. */

const SCHLUESSEL = 'vokabeltrainer.zustand';

const anfang = {
  benutzerId: null,
  sammlungId: null,
  lektionId: null,
};

function laden() {
  try {
    return { ...anfang, ...JSON.parse(localStorage.getItem(SCHLUESSEL) || '{}') };
  } catch {
    return { ...anfang };
  }
}

export const zustand = laden();

export function merken(aenderungen = {}) {
  Object.assign(zustand, aenderungen);
  try {
    localStorage.setItem(SCHLUESSEL, JSON.stringify({
      benutzerId: zustand.benutzerId,
      sammlungId: zustand.sammlungId,
      lektionId: zustand.lektionId,
    }));
  } catch { /* privates Fenster o.ä. — dann eben ohne Gedächtnis */ }
}

/* ------------------------------------------------- Darstellung einstellen */

/** Überträgt die Legasthenie-Einstellungen in die CSS-Variablen.
 *
 * Der Zeichenabstand ist die am besten belegte Maßnahme und darum der
 * Hauptschalter; die Schriftart ist nur ein Angebot. */
export function darstellungSetzen(lg) {
  const wurzel = document.documentElement;
  const aus = !lg || !lg.aktiv;
  if (aus) {
    for (const name of ['--mass', '--zeichenabstand', '--wortabstand',
                        '--zeilenhoehe', '--schrift-wort']) {
      wurzel.style.removeProperty(name);
    }
    wurzel.removeAttribute('data-grund');
    wurzel.removeAttribute('data-legasthenie');
    return;
  }
  wurzel.setAttribute('data-legasthenie', 'an');
  wurzel.style.setProperty('--mass', String(lg.schriftgroesse ?? 1.25));
  wurzel.style.setProperty('--zeichenabstand', `${lg.zeichenabstand ?? 0.12}em`);
  wurzel.style.setProperty('--wortabstand', `${lg.wortabstand ?? 0.16}em`);
  wurzel.style.setProperty('--zeilenhoehe', String(lg.zeilenhoehe ?? 1.9));
  if (lg.hintergrund) wurzel.setAttribute('data-grund', lg.hintergrund);
  else wurzel.removeAttribute('data-grund');

  const schriften = {
    grotesk: 'ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto, sans-serif',
    serifenlos: 'Verdana, Tahoma, "DejaVu Sans", sans-serif',
    opendyslexic: '"OpenDyslexic", "Open Dyslexic", Verdana, sans-serif',
  };
  wurzel.style.setProperty('--schrift-wort',
    schriften[lg.schriftart] || schriften.grotesk);
}
