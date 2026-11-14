/* Einmal geladen, dann im Speicher: Sprachen, Merkmalsinventar, Aufgabentypen. */

import { api } from './api.js';

const halde = {};

async function einmal(name, holen) {
  if (!halde[name]) halde[name] = holen();
  return halde[name];
}

export const stammdaten = {
  sprachen: () => einmal('sprachen', () => api.sprachen()),
  merkmale: () => einmal('merkmale', () => api.merkmale()),
  aufgabentypen: () => einmal('aufgabentypen', () => api.aufgabentypen()),
  formgruppen: (code) => einmal('fg:' + code, () => api.formgruppen(code)),

  async sprache(code) {
    const alle = await this.sprachen();
    return alle.find((s) => s.code === code) || { code, name: code, stimme: null };
  },

  /** Welche Stimme nimmt die Sprachsynthese für diese Sprache?
   *  Für Mittelhochdeutsch gibt es keine — Deutsch zu nehmen wäre
   *  irreführend, die Aussprache ist eine andere. */
  async stimme(code) {
    return (await this.sprache(code)).stimme;
  },

  vergessen(name) { delete halde[name]; },
};
