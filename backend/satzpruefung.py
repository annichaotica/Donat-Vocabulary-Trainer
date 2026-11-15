"""Bewertung freier Übersetzungen.

Ein Satz ist kein Wort. `pruefung.pruefen` vergleicht eine Antwort als Ganzes
und ist dafür genau richtig — bei einem Satz aber führt dasselbe Verfahren zu
unbrauchbaren Auskünften: der Artikeltrenner nimmt "Der" aus "Der Mann geht"
heraus, die Tippfehlertoleranz von zwei Zeichen deckt bei sechzig Zeichen
einen ganzen Wortfehler, und "Du hast zwei Buchstaben vertauscht" ist über
einen Satz gesagt sinnlos.

Darum hier Wort für Wort, mit denselben Normalisierungsregeln der Sprache:

    richtig   jedes Wort sitzt (Satzzeichen und Groß/Klein nach Profil)
    fast      nur Akzente fehlen, oder bis zu zwei Wörter mit Tippfehler
    falsch    sonst — und dann mit der Angabe, WELCHE Wörter abweichen

Verglichen wird gegen alle angegebenen Fassungen; die am besten passende
gewinnt. Eine richtige Übersetzung darf nicht daran scheitern, dass sie
nicht die zuerst aufgeschriebene ist.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

import pruefung

# Satzzeichen am Wortrand. Innen bleiben sie stehen — "d'accord" und
# "σ' αγαπώ" sind ein Wort mit Apostroph, nicht zwei.
_RAND = " \t\n\r.,;:!?¡¿\"»«“”„…()[]"
_TRENNER = re.compile(r"\s+")

HOECHSTENS_TIPPFEHLER = 2


@dataclass
class Satzurteil:
    urteil: str                       # richtig | fast | falsch
    treffer: str | None = None        # die am besten passende Fassung
    hinweis: str | None = None
    abweichungen: list[str] = field(default_factory=list)
    # Wort für Wort, nur wenn es etwas zu zeigen gibt:
    # {"art": "anders"|"fehlt"|"ueberzaehlig", "erwartet":…, "bekommen":…}
    stellen: list[dict] = field(default_factory=list)
    woerter_gesamt: int = 0
    woerter_richtig: int = 0
    # Wort für Wort deckungsgleich mit einer hinterlegten Fassung —
    # nicht »gut genug«, sondern dasselbe. Daran hängt, ob die
    # Selbsteinschätzung überhaupt noch eine Frage ist; siehe
    # `uebung_lernen.pruefen`.
    wortgleich: bool = False

    @property
    def zaehlt_als_richtig(self) -> bool:
        return self.urteil == "richtig"

    def als_dict(self) -> dict:
        d = {"urteil": self.urteil, "treffer": self.treffer,
             "hinweis": self.hinweis, "abweichungen": self.abweichungen,
             "stellen": self.stellen, "woerter_gesamt": self.woerter_gesamt,
             "woerter_richtig": self.woerter_richtig,
             "wortgleich": self.wortgleich}
        return d


def woerter(text: str, profil: dict) -> list[str]:
    """Vergleichsform, in Wörter zerlegt."""
    roh = pruefung.normalisieren(text or "", profil)
    return [w for w in (t.strip(_RAND) for t in _TRENNER.split(roh)) if w]


def _anzeige_woerter(text: str) -> list[str]:
    """Dieselbe Zerlegung, aber in Schreibweise — für die Rückmeldung.
    Niemals kleingeschrieben: das griechische Schluss-Sigma würde sonst
    zu σ, und in der Rückmeldung stünde ein falsch geschriebenes Wort."""
    roh = pruefung._anzeige(text or "")
    return [w for w in (t.strip(_RAND) for t in _TRENNER.split(roh)) if w]


def _ausrichten(a: list[str], b: list[str]) -> list[tuple[int | None, int | None]]:
    """Längste gemeinsame Teilfolge, als Paarliste von Stellen.

    Ohne Ausrichtung wäre ein einziges eingefügtes Wort "alles ab hier
    falsch" — die Rückmeldung wäre wertlos.
    """
    n, m = len(a), len(b)
    tafel = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n - 1, -1, -1):
        for j in range(m - 1, -1, -1):
            tafel[i][j] = (tafel[i + 1][j + 1] + 1 if a[i] == b[j]
                           else max(tafel[i + 1][j], tafel[i][j + 1]))
    paare: list[tuple[int | None, int | None]] = []
    i = j = 0
    while i < n and j < m:
        if a[i] == b[j]:
            paare.append((i, j)); i += 1; j += 1
        elif tafel[i + 1][j] >= tafel[i][j + 1]:
            paare.append((i, None)); i += 1
        else:
            paare.append((None, j)); j += 1
    paare += [(k, None) for k in range(i, n)]
    paare += [(None, k) for k in range(j, m)]
    return paare


def _stellen(erwartet: list[str], e_anzeige: list[str],
             bekommen: list[str], b_anzeige: list[str]) -> list[dict]:
    """Benennt die Abweichungen. Ein Paar aus "fehlt" und "überzählig"
    direkt hintereinander ist ein ersetztes Wort und wird als solches
    gemeldet — zwei Meldungen wären für dieselbe Stelle eine zu viel."""
    roh = []
    for i, j in _ausrichten(erwartet, bekommen):
        if i is not None and j is not None:
            continue
        if i is not None:
            roh.append({"art": "fehlt", "erwartet": e_anzeige[i], "bekommen": None})
        else:
            roh.append({"art": "ueberzaehlig", "erwartet": None,
                        "bekommen": b_anzeige[j]})
    ergebnis: list[dict] = []
    k = 0
    while k < len(roh):
        if (k + 1 < len(roh) and roh[k]["art"] == "fehlt"
                and roh[k + 1]["art"] == "ueberzaehlig"):
            ergebnis.append({"art": "anders", "erwartet": roh[k]["erwartet"],
                             "bekommen": roh[k + 1]["bekommen"]})
            k += 2
        else:
            ergebnis.append(roh[k]); k += 1
    return ergebnis


def _tippfehler(erwartet: list[str], bekommen: list[str]) -> int | None:
    """Wie viele Wörter weichen nur um einen Tippfehler ab?

    None heißt: es ist kein Tippfehlerbild — die Wortzahl stimmt nicht,
    oder ein Wort ist ein anderes Wort.
    """
    if len(erwartet) != len(bekommen):
        return None
    anzahl = 0
    for e, b in zip(erwartet, bekommen):
        if e == b:
            continue
        grenze = pruefung.toleranz(len(e))
        if grenze and pruefung.abstand(e, b, grenze) <= grenze:
            anzahl += 1
        else:
            return None
    return anzahl


_RANG = {"richtig": 0, "fast": 1, "falsch": 2}


def pruefen(eingabe: str, erwartet: list[str], profil: dict) -> Satzurteil:
    """Prüft eine freie Übersetzung gegen alle gültigen Fassungen."""
    e_woerter = woerter(eingabe, profil)
    if not e_woerter:
        return Satzurteil("falsch", hinweis="Keine Antwort eingegeben.")
    fassungen = [f for f in (erwartet or []) if (f or "").strip()]
    if not fassungen:
        return Satzurteil("falsch",
                          hinweis="Zu dieser Aufgabe ist keine Lösung hinterlegt.")

    diakritika = (profil.get("pruefung", {}) or {}).get("diakritika", "hinweis")
    e_ohne = [pruefung.ohne_diakritika(w) for w in e_woerter]
    bestes: Satzurteil | None = None

    for fassung in fassungen:
        z_woerter = woerter(fassung, profil)
        z_ohne = [pruefung.ohne_diakritika(w) for w in z_woerter]
        treffer = pruefung._anzeige(fassung)

        if z_woerter == e_woerter:
            return Satzurteil("richtig", treffer=treffer,
                              woerter_gesamt=len(z_woerter),
                              woerter_richtig=len(z_woerter),
                              wortgleich=True)

        if z_ohne == e_ohne:
            # Jedes Wort sitzt, nur die Akzente nicht. Im Griechischen ist
            # das ein Hinweis und kein Fehler — der Akzent trägt dort
            # Bedeutung, aber nicht die des Satzes.
            urteil = Satzurteil(
                "fast" if diakritika != "streng" else "falsch",
                treffer=treffer, abweichungen=["diakritika"],
                hinweis="Richtig bis auf die Akzente.",
                woerter_gesamt=len(z_woerter), woerter_richtig=len(z_woerter))
            bestes = urteil if _besser(urteil, bestes) else bestes
            continue

        tippfehler = _tippfehler(z_ohne, e_ohne)
        if tippfehler is not None and tippfehler <= HOECHSTENS_TIPPFEHLER:
            urteil = Satzurteil(
                "fast", treffer=treffer, abweichungen=["tippfehler"],
                hinweis=f"{tippfehler} Wort mit Tippfehler."
                        if tippfehler == 1 else
                        f"{tippfehler} Wörter mit Tippfehlern.",
                stellen=_stellen(z_ohne, _anzeige_woerter(fassung),
                                 e_ohne, _anzeige_woerter(eingabe)),
                woerter_gesamt=len(z_woerter),
                woerter_richtig=len(z_woerter) - tippfehler)
            bestes = urteil if _besser(urteil, bestes) else bestes
            continue

        stellen = _stellen(z_ohne, _anzeige_woerter(fassung),
                           e_ohne, _anzeige_woerter(eingabe))
        getroffen = len(z_woerter) - sum(1 for s in stellen
                                         if s["art"] in ("fehlt", "anders"))
        getroffen = max(0, getroffen)
        urteil = Satzurteil(
            "falsch", treffer=treffer, stellen=stellen,
            # Stimmt überhaupt nichts, ist eine Wortliste keine Hilfe —
            # dann hat die Antwort mit dem Satz nichts zu tun.
            hinweis=("Das ist ein anderer Satz." if not getroffen
                     else _zusammenfassen(stellen)),
            woerter_gesamt=len(z_woerter), woerter_richtig=max(0, getroffen))
        bestes = urteil if _besser(urteil, bestes) else bestes

    return bestes or Satzurteil("falsch")


def _besser(neu: Satzurteil, alt: Satzurteil | None) -> bool:
    if alt is None:
        return True
    if _RANG[neu.urteil] != _RANG[alt.urteil]:
        return _RANG[neu.urteil] < _RANG[alt.urteil]
    # Gleiches Urteil: die Fassung mit weniger Abweichungen ist die gemeinte.
    return len(neu.stellen) < len(alt.stellen)


def _zusammenfassen(stellen: list[dict]) -> str:
    anders = [s for s in stellen if s["art"] == "anders"]
    fehlt = [s for s in stellen if s["art"] == "fehlt"]
    ueber = [s for s in stellen if s["art"] == "ueberzaehlig"]
    teile = []
    if anders:
        teile.append(", ".join(f"{s['bekommen']} → {s['erwartet']}"
                               for s in anders[:3]))
    if fehlt:
        teile.append("fehlt: " + ", ".join(s["erwartet"] for s in fehlt[:3]))
    if ueber:
        teile.append("zu viel: " + ", ".join(s["bekommen"] for s in ueber[:3]))
    return "; ".join(teile) or "Weicht ab."
