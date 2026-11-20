/* Der Name des Programms — in der Oberfläche an EINER Stelle.
 *
 * Er steht im Server (backend/marke.py) und kommt über
 * `GET /api/zustand` herüber. In index.html und im Webmanifest steht
 * er als Anfangswert, damit der Reitertitel nicht erst leer ist; sobald
 * die Anwendung geladen hat, gilt der Wert vom Server.
 *
 * Warum nicht einfach fest ins HTML: weil der Name sich ändern soll,
 * ohne dass man ihn an sieben Stellen suchen muss — und weil eine
 * eigene Fassung ihn über VOKABEL_NAME setzen kann, ohne den Quelltext
 * anzufassen.
 */

import { api } from './api.js';

/** Der Anfangswert aus dem HTML — gilt, bis der Server geantwortet hat. */
export let NAME = document.title || 'Donat';

export async function markeLaden() {
  try {
    const z = await api.zustand();
    if (z?.name) {
      NAME = z.name;
      document.title = NAME;
    }
  } catch { /* offline oder noch nicht da: der Anfangswert tut es */ }
  return NAME;
}
