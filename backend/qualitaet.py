"""Prüft Einträge auf das, was der Trainer braucht.

Ein Eintrag kann formal gültig und trotzdem nutzlos sein. Wenn der Stamm nicht
ableitbar ist, läuft die Zerlegung leer; wenn ein Paradigma Lücken hat, fehlen
Aufgaben; wenn keine Übersetzung in der Grundsprache steht, entsteht gar keine
Bedeutungsaufgabe. Das muss, wer einträgt, VORHER erfahren — vor allem ein
Agent am MCP, der nicht selbst nachsieht.

Jeder Befund trägt seine Schwere:

    fehler   der Eintrag taugt so nicht, es entsteht keine brauchbare Abfrage
    hinweis  es geht, aber eine Fähigkeit des Trainers bleibt ungenutzt
    notiz    nur zur Kenntnis
"""

from __future__ import annotations

import sqlite3

import aufgaben
import datenbank as dbm
import legasthenie
import merkmale as mk
import sprachen

SCHWEREN = ("fehler", "hinweis", "notiz")


def _befund(art: str, schwere: str, text: str, betrifft=None, rat: str | None = None):
    return {"art": art, "schwere": schwere, "text": text,
            "betrifft": betrifft or [], "rat": rat}


def pruefen(db: sqlite3.Connection, lexem_id: int) -> dict:
    """Prüft einen eingetragenen Eintrag."""
    lexem = dbm.zeile(db, "SELECT * FROM lexem WHERE id = ?", (lexem_id,))
    if lexem is None:
        raise KeyError(f"Lexem {lexem_id} gibt es nicht")
    e = aufgaben.sammlung_einstellungen(db, lexem["sammlung_id"])
    code, grund, wortart = e["sprache"], e["grundsprache"], lexem["wortart"]

    formen = dbm.zeilen(db, "SELECT * FROM form WHERE lexem_id = ?", (lexem_id,))
    for f in formen:
        f["merkmale"] = dbm.j_lesen(f["merkmale"])
    bedeutungen = dbm.zeilen(db, "SELECT * FROM bedeutung WHERE lexem_id = ?",
                             (lexem_id,))
    uebersetzungen = []
    for b in bedeutungen:
        uebersetzungen += dbm.zeilen(
            db, "SELECT * FROM uebersetzung WHERE bedeutung_id = ?", (b["id"],))
    aktive = dbm.zeilen(db, """SELECT * FROM aufgabe
                                WHERE lexem_id = ? AND aktiv = 1""", (lexem_id,))

    befunde: list[dict] = []
    befunde += _bedeutungen_pruefen(uebersetzungen, grund)
    befunde += _lemma_pruefen(db, lexem)
    befunde += _formen_pruefen(formen, code, wortart, e)
    befunde += _staemme_pruefen(formen, code, wortart)
    befunde += _aufgaben_pruefen(aktive, formen, uebersetzungen)

    schwer = [b for b in befunde if b["schwere"] == "fehler"]
    return {
        "lexem_id": lexem_id,
        "lemma": lexem["lemma"],
        "gut": not schwer,
        "befunde": sorted(befunde, key=lambda b: SCHWEREN.index(b["schwere"])),
        "aufgaben_aktiv": len(aktive),
        "formen": len(formen),
        "ungeprueft": sum(1 for f in formen if not f["geprueft"]),
    }


# ----------------------------------------------------------- Einzelprüfungen

def _bedeutungen_pruefen(uebersetzungen: list[dict], grund: str) -> list[dict]:
    passend = [u for u in uebersetzungen if u["sprache"] == grund]
    if not passend:
        return [_befund(
            "ohne_bedeutung", "fehler",
            f"Keine Übersetzung in der Grundsprache ({grund}) hinterlegt.",
            rat="Ohne sie entsteht keine einzige Bedeutungsaufgabe — weder in "
                "die eine noch in die andere Richtung.")]
    einzeln = [u for u in passend if u["text"].strip()]
    befunde = []
    if len(einzeln) == 1:
        befunde.append(_befund(
            "nur_eine_uebersetzung", "hinweis",
            "Nur eine Übersetzung hinterlegt.",
            rat="Der Trainer nimmt jede hinterlegte Übersetzung als richtig an. "
                "Wer nur eine einträgt, verschenkt das — und bekommt ein "
                "»falsch« für eine Antwort, die stimmt."))
    doppelt = [t for t in {u["text"] for u in einzeln}
               if sum(1 for u in einzeln if u["text"] == t) > 1]
    if doppelt:
        befunde.append(_befund("uebersetzung_doppelt", "notiz",
                               f"Doppelt eingetragen: {', '.join(doppelt)}.",
                               betrifft=doppelt))
    return befunde


def _lemma_pruefen(db: sqlite3.Connection, lexem: dict) -> list[dict]:
    gleich = dbm.zeilen(db, """SELECT id, lemma FROM lexem
                                WHERE sammlung_id = ? AND lemma = ? AND id != ?""",
                        (lexem["sammlung_id"], lexem["lemma"], lexem["id"]))
    if gleich:
        return [_befund(
            "lemma_doppelt", "hinweis",
            f"»{lexem['lemma']}« steht schon {len(gleich)}× in dieser Sammlung.",
            betrifft=[g["id"] for g in gleich],
            rat="Bei echten Gleichnamigkeiten in Ordnung. Sonst besser die "
                "Bedeutungen in EINEM Eintrag sammeln — dann gilt beim Abfragen "
                "jede davon.")]
    return []


def _formen_pruefen(formen: list[dict], code: str, wortart: str,
                    einstellungen: dict) -> list[dict]:
    befunde = []
    if not formen:
        # Nur melden, wo es überhaupt Formen geben KANN. Adverbien,
        # Präpositionen, Konjunktionen und Wendungen haben keine — ein
        # Mangel wäre das nur, wenn die Sprache für diese Wortart
        # Formgruppen kennt. Eine feste Ausnahmeliste wäre hier falsch:
        # was flektiert, entscheidet die Sprache, nicht eine Liste im Code.
        if not sprachen.formgruppen(code, wortart):
            return []
        return [_befund(
            "ohne_formen", "hinweis", "Keine Formen eingetragen.",
            rat=f"Für {mk.WORTARTEN.get(wortart, wortart)} in "
                f"{sprachen.profil(code)['name']} gibt es Formgruppen. Ohne "
                f"Formen bleibt es beim Bedeutungspauken — die Formabfrage, "
                f"der eigentliche Zweck, entfällt.")]

    grundformen = [f for f in formen if f["ist_grundform"]]
    if not grundformen:
        befunde.append(_befund(
            "grundform_fehlt", "hinweis", "Keine Form ist als Grundform markiert.",
            rat="Die Grundform ist die Zitierform. Sie wird nicht abgefragt — "
                "sonst stünde sie in der Frage und in der Antwort."))
    elif len(grundformen) > 1:
        befunde.append(_befund(
            "grundform_mehrfach", "fehler",
            f"{len(grundformen)} Formen sind als Grundform markiert.",
            betrifft=[f["text"] for f in grundformen],
            rat="Genau eine darf es sein."))

    ohne_merkmale = [f for f in formen
                     if not f["merkmale"] and not f["ist_grundform"]]
    if ohne_merkmale:
        befunde.append(_befund(
            "form_ohne_merkmale", "fehler",
            f"{len(ohne_merkmale)} Formen tragen keine Merkmale.",
            betrifft=[f["text"] for f in ohne_merkmale],
            rat="Eine Form ohne Merkmale ist nicht abfragbar — es ließe sich "
                "keine Frage danach stellen."))

    # Formen, die zu keiner Formgruppe gehören
    fremd = []
    for f in formen:
        if f["ist_grundform"] or not f["merkmale"]:
            continue
        if aufgaben._gruppe_der_form(code, wortart, f["merkmale"]) is None:
            fremd.append(f["text"])
    if fremd:
        befunde.append(_befund(
            "ausserhalb_der_formgruppen", "hinweis",
            f"{len(fremd)} Formen passen in keine Formgruppe der Sprache.",
            betrifft=fremd,
            rat="Sie werden zwar abgefragt, lassen sich aber nicht gemeinsam "
                "zu- oder abschalten und erscheinen in keiner Tabelle. Entweder "
                "die Merkmale anpassen oder dem Sprachprofil eine Formgruppe "
                "hinzufügen (PUT /api/sprachen/<code>/profil)."))

    # Lücken in den Formgruppen
    aktive_gruppen = set(einstellungen["formgruppen"])
    for gruppe in sprachen.formgruppen(code, wortart):
        if gruppe["kennung"] not in aktive_gruppen:
            continue
        belegt = 0
        fehlende = []
        for zelle in gruppe["zellen"]:
            if any(all(str(f["merkmale"].get(d)) == str(w) for d, w in zelle.items())
                   for f in formen):
                belegt += 1
            else:
                fehlende.append(sprachen.beschriften_form(code, wortart, zelle,
                                                          kurz=True))
        if belegt and fehlende:
            befunde.append(_befund(
                "paradigma_lueckig", "hinweis",
                f"{gruppe['name']}: {belegt} von {len(gruppe['zellen'])} Formen da.",
                betrifft=fehlende,
                rat=f"Es fehlen: {', '.join(fehlende)}. Fehlende Zellen bedeuten "
                    f"fehlende Aufgaben, und ein lückiges Paradigma verdirbt "
                    f"außerdem die Stammerkennung."))
    return befunde


def _staemme_pruefen(formen: list[dict], code: str, wortart: str) -> list[dict]:
    """Lässt sich der Stamm je Formgruppe ableiten?

    Davon hängt die Zerlegung in Stamm und Endung ab — die Hilfe, die der
    Legastheniemodus anbietet und die kein Kartenstapel geben kann.
    """
    befunde = []
    for gruppe in sprachen.formgruppen(code, wortart):
        if len(gruppe["zellen"]) < 2:
            continue
        dazu = [f["text"] for f in formen
                if all(str(f["merkmale"].get(d)) == str(w)
                       for d, w in gruppe["merkmale"].items())]
        if len(dazu) < 2:
            continue
        if not legasthenie.stamm(dazu):
            befunde.append(_befund(
                "stamm_nicht_ableitbar", "hinweis",
                f"{gruppe['name']}: die Formen haben keinen gemeinsamen Stamm.",
                betrifft=dazu,
                rat="Bei wirklich unregelmäßigen Wörtern (aller: vais, allons) "
                    "ist das richtig so. Sonst ein Zeichen für einen Tippfehler "
                    "in einer der Formen. Ohne Stamm entfällt die Zerlegung in "
                    "Stamm und Endung."))
    return befunde


def _aufgaben_pruefen(aktive: list[dict], formen: list[dict],
                      uebersetzungen: list[dict]) -> list[dict]:
    if aktive:
        return []
    ungeprueft = [f for f in formen if not f["geprueft"]]
    if ungeprueft and not uebersetzungen:
        return [_befund(
            "keine_aufgaben", "hinweis",
            "Noch keine Aufgabe — alle Formen sind ungeprüft.",
            rat="Ungeprüfte Formen werden nicht abgefragt. Mit "
                "POST /api/formen/<id>/bestaetigen freigeben, nachdem ein "
                "Mensch sie angesehen hat.")]
    return [_befund(
        "keine_aufgaben", "fehler",
        "Aus diesem Eintrag entsteht keine einzige Aufgabe.",
        rat="Es fehlt entweder die Übersetzung oder es sind keine Formgruppen "
            "zugeschaltet, in die die Formen fallen.")]


# ----------------------------------------------------- Ganze Sammlung prüfen

def pruefen_sammlung(db: sqlite3.Connection, sammlung_id: int,
                     nur_mangelhafte: bool = True) -> dict:
    """Prüft alle Einträge einer Sammlung auf einmal."""
    berichte = []
    zaehler = {"fehler": 0, "hinweis": 0, "notiz": 0}
    for z in dbm.zeilen(db, "SELECT id FROM lexem WHERE sammlung_id = ? ORDER BY lemma",
                        (sammlung_id,)):
        bericht = pruefen(db, z["id"])
        for b in bericht["befunde"]:
            zaehler[b["schwere"]] += 1
        if bericht["befunde"] or not nur_mangelhafte:
            berichte.append(bericht)
    return {"sammlung_id": sammlung_id, "geprueft": len(berichte),
            "zaehler": zaehler, "eintraege": berichte}
