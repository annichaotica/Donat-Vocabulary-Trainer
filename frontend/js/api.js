/* Zugriff auf die Schnittstelle. Ein Ort für alle Aufrufe. */

export class ApiFehler extends Error {
  constructor(text, status) { super(text); this.status = status; }
}

async function ruf(pfad, { methode = 'GET', daten = null, frage = null } = {}) {
  let adresse = '/api' + pfad;
  if (frage) {
    const teile = new URLSearchParams();
    for (const [name, wert] of Object.entries(frage)) {
      if (wert === null || wert === undefined || wert === '') continue;
      if (Array.isArray(wert)) wert.forEach((w) => teile.append(name, w));
      else teile.append(name, wert);
    }
    const text = teile.toString();
    if (text) adresse += '?' + text;
  }
  const antwort = await fetch(adresse, {
    method: methode,
    headers: daten ? { 'Content-Type': 'application/json' } : undefined,
    body: daten ? JSON.stringify(daten) : undefined,
  });
  if (antwort.status === 204) return null;
  const inhalt = await antwort.text();
  let geparst = null;
  try { geparst = inhalt ? JSON.parse(inhalt) : null; } catch { geparst = null; }
  if (!antwort.ok) {
    throw new ApiFehler(fehlertext(geparst) || `Fehler ${antwort.status}`, antwort.status);
  }
  return geparst;
}

function fehlertext(inhalt) {
  if (!inhalt) return null;
  const d = inhalt.detail;
  if (typeof d === 'string') return d;
  if (Array.isArray(d)) {
    // Pydantic nennt Feld und Grund — das soll man auch lesen können.
    return d.map((f) => {
      const ort = (f.loc || []).filter((t) => t !== 'body').join(' → ');
      return ort ? `${ort}: ${f.msg}` : f.msg;
    }).join('; ');
  }
  return null;
}

export const api = {
  zustand: () => ruf('/zustand'),
  sprachen: () => ruf('/sprachen'),
  formgruppen: (code) => ruf(`/sprachen/${code}/formgruppen`),
  merkmale: () => ruf('/merkmale'),
  aufgabentypen: () => ruf('/aufgabentypen'),

  ich: () => ruf('/ich'),
  benutzer: () => ruf('/benutzer'),
  benutzerLesen: (id) => ruf(`/benutzer/${id}`),
  mcpToken: (id) => ruf(`/benutzer/${id}/mcp-token`),
  mcpTokenAnlegen: (id, daten) =>
    ruf(`/benutzer/${id}/mcp-token`, { methode: 'POST', daten }),
  mcpTokenZuruecknehmen: (id) => ruf(`/mcp-token/${id}`, { methode: 'DELETE' }),
  benutzerAnlegen: (daten) => ruf('/benutzer', { methode: 'POST', daten }),
  benutzerAendern: (id, daten) => ruf(`/benutzer/${id}`, { methode: 'PATCH', daten }),
  benutzerEinstellungen: (id) => ruf(`/benutzer/${id}/einstellungen`),
  legasthenieLesen: (id) => ruf(`/benutzer/${id}/legasthenie`),
  legasthenieSetzen: (id, daten) => ruf(`/benutzer/${id}/legasthenie`, { methode: 'PUT', daten }),

  sammlungen: (benutzerId) => ruf('/sammlungen', { frage: { benutzer_id: benutzerId } }),
  sammlungAnlegen: (daten) => ruf('/sammlungen', { methode: 'POST', daten }),
  sammlungAendern: (id, daten) => ruf(`/sammlungen/${id}`, { methode: 'PATCH', daten }),
  sammlungLoeschen: (id) => ruf(`/sammlungen/${id}`, { methode: 'DELETE' }),
  zugriff: (id) => ruf(`/sammlungen/${id}/zugriff`),
  zugriffSetzen: (id, daten) => ruf(`/sammlungen/${id}/zugriff`, { methode: 'PUT', daten }),
  lernwahlSetzen: (id, benutzerId, lernen) => ruf(`/sammlungen/${id}/lernwahl`,
    { methode: 'PUT', daten: { benutzer_id: benutzerId, lernen } }),
  besitzUebertragen: (id, daten) =>
    ruf(`/sammlungen/${id}/besitz`, { methode: 'POST', daten }),

  sammlungEinstellungen: (id) => ruf(`/sammlungen/${id}/einstellungen`),
  sammlungEinstellungenSetzen: (id, daten) =>
    ruf(`/sammlungen/${id}/einstellungen`, { methode: 'PUT', daten }),
  lektionen: (id) => ruf(`/sammlungen/${id}/lektionen`),
  lektionAnlegen: (id, daten) => ruf(`/sammlungen/${id}/lektionen`, { methode: 'POST', daten }),

  lexeme: (sammlungId, frage) => ruf(`/sammlungen/${sammlungId}/lexeme`, { frage }),
  lexem: (id) => ruf(`/lexeme/${id}`),
  lexemAnlegen: (daten) => ruf('/lexeme', { methode: 'POST', daten }),
  lexemAendern: (id, daten) => ruf(`/lexeme/${id}`, { methode: 'PATCH', daten }),
  lexemLoeschen: (id) => ruf(`/lexeme/${id}`, { methode: 'DELETE' }),
  formAnlegen: (lexemId, daten) => ruf(`/lexeme/${lexemId}/formen`, { methode: 'POST', daten }),
  formAendern: (id, daten) => ruf(`/formen/${id}`, { methode: 'PATCH', daten }),
  formBestaetigen: (id) => ruf(`/formen/${id}/bestaetigen`, { methode: 'POST' }),
  formLoeschen: (id) => ruf(`/formen/${id}`, { methode: 'DELETE' }),
  bedeutungAnlegen: (lexemId, daten) =>
    ruf(`/lexeme/${lexemId}/bedeutungen`, { methode: 'POST', daten }),
  bedeutungLoeschen: (id) => ruf(`/bedeutungen/${id}`, { methode: 'DELETE' }),

  // Merkmalsbündel-Dateien (das Format, das die KI liefert)
  vokabelnImportieren: (sammlungId, daten) =>
    ruf(`/sammlungen/${sammlungId}/import/vokabeln`, { methode: 'POST', daten }),
  uebung: (id) => ruf(`/uebungen/${id}`),
  regeln: (sammlungId, nurUngepruefte = false) =>
    ruf(`/sammlungen/${sammlungId}/regeln`,
        { frage: { nur_ungepruefte: nurUngepruefte } }),
  regelFreigeben: (id, geprueft = true) =>
    ruf(`/regeln/${id}/freigabe`, { methode: 'POST', frage: { geprueft } }),
  regelAendern: (id, daten) =>
    ruf(`/regeln/${id}`, { methode: 'PATCH', daten }),
  regelLoeschen: (id) => ruf(`/regeln/${id}`, { methode: 'DELETE' }),
  uebungenImportieren: (sammlungId, daten) =>
    ruf(`/sammlungen/${sammlungId}/import/uebungen`, { methode: 'POST', daten }),
  // Tabellen (CSV, Anki, Quizlet)
  importVorschau: (sammlungId, daten) =>
    ruf(`/sammlungen/${sammlungId}/import/vorschau`, { methode: 'POST', daten }),
  importUebernehmen: (sammlungId, daten) =>
    ruf(`/sammlungen/${sammlungId}/import`, { methode: 'POST', daten }),

  uebungStand: (benutzerId, sammlungId) =>
    ruf('/uebungen/lernen/stand',
        { frage: { benutzer_id: benutzerId, sammlung_id: sammlungId } }),
  uebungNaechste: (frage) => ruf('/uebungen/lernen/naechste', { frage }),
  uebungPruefen: (daten) =>
    ruf('/uebungen/lernen/pruefen', { methode: 'POST', daten }),
  uebungAufdecken: (daten) =>
    ruf('/uebungen/lernen/aufdecken', { methode: 'POST', daten }),
  uebungBewerten: (daten) =>
    ruf('/uebungen/lernen/bewerten', { methode: 'POST', daten }),

  freigabeLektionen: (sammlungId) => ruf(`/sammlungen/${sammlungId}/freigabe/lektionen`),
  freigabe: (sammlungId, frage) => ruf(`/sammlungen/${sammlungId}/freigabe`, { frage }),
  freigabeSetzen: (sammlungId, daten) =>
    ruf(`/sammlungen/${sammlungId}/freigabe`, { methode: 'POST', daten }),

  lernziele: (benutzerId) => ruf('/lernziele', { frage: { benutzer_id: benutzerId } }),
  lernzielAnlegen: (daten) => ruf('/lernziele', { methode: 'POST', daten }),
  lernzielAendern: (id, daten) => ruf(`/lernziele/${id}`, { methode: 'PATCH', daten }),
  lernzielLoeschen: (id) => ruf(`/lernziele/${id}`, { methode: 'DELETE' }),
  lernzielFortschritt: (id, benutzerId) =>
    ruf(`/lernziele/${id}/fortschritt`, { frage: { benutzer_id: benutzerId } }),
  lernblock: (id, benutzerId, anzahl) =>
    ruf(`/lernziele/${id}/block`, { frage: { benutzer_id: benutzerId, anzahl } }),

  texte: (sammlungId) => ruf(`/sammlungen/${sammlungId}/texte`),
  textAnlegen: (sammlungId, daten) =>
    ruf(`/sammlungen/${sammlungId}/texte`, { methode: 'POST', daten }),
  text: (id, benutzerId) =>
    ruf(`/texte/${id}`, { frage: { benutzer_id: benutzerId } }),
  textLoeschen: (id) => ruf(`/texte/${id}`, { methode: 'DELETE' }),
  textDeckung: (id, benutzerId) =>
    ruf(`/texte/${id}/deckung`, { frage: { benutzer_id: benutzerId } }),
  textNachschlagen: (id, wort) =>
    ruf(`/texte/${id}/nachschlagen`, { frage: { wort } }),
  fassungSichern: (abschnittId, benutzerId, fassung) =>
    ruf(`/abschnitte/${abschnittId}/fassung`,
        { methode: 'PUT', daten: { benutzer_id: benutzerId, fassung } }),
  wortMerken: (textId, benutzerId, wort, zusammenhang) =>
    ruf(`/texte/${textId}/wortwunsch`,
        { methode: 'POST',
          daten: { benutzer_id: benutzerId, wort, zusammenhang } }),
  wortVergessen: (textId, benutzerId, wort) =>
    ruf(`/texte/${textId}/wortwunsch`,
        { methode: 'DELETE', frage: { benutzer_id: benutzerId, wort } }),
  wortwuensche: (benutzerId, sammlungId) =>
    ruf('/wortwuensche',
        { frage: { benutzer_id: benutzerId, sammlung_id: sammlungId } }),

  stand: (benutzerId, sammlungId) =>
    ruf('/lernen/stand', { frage: { benutzer_id: benutzerId, sammlung_id: sammlungId } }),
  naechste: (frage) => ruf('/lernen/naechste', { frage }),
  pruefen: (daten) => ruf('/lernen/pruefen', { methode: 'POST', daten }),
  tipp: (frage) => ruf('/lernen/tipp', { frage }),
  aufdecken: (daten) => ruf('/lernen/aufdecken', { methode: 'POST', daten }),
  bewerten: (daten) => ruf('/lernen/bewerten', { methode: 'POST', daten }),
  aussetzen: (daten) => ruf('/lernen/aussetzen', { methode: 'POST', daten }),
  fortsetzen: (daten) => ruf('/lernen/fortsetzen', { methode: 'POST', daten }),
  zuruecksetzen: (daten) => ruf('/lernen/zuruecksetzen', { methode: 'POST', daten }),
  termin: (daten) => ruf('/lernen/termin', { methode: 'POST', daten }),
  verlauf: (frage) => ruf('/lernen/verlauf', { frage }),
};
