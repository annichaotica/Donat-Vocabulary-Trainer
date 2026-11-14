# Vokabeltrainer — Copyright (C) 2026 Annuschka Brenner
#
# Freie Software unter der GNU Affero General Public License, Fassung 3
# oder später. Herausgegeben in der Hoffnung, dass sie nützt, aber OHNE
# JEDE GEWÄHRLEISTUNG. Siehe die Datei LICENSE.
"""Antwortprüfung in Schichten.

Keine Zeichenkettengleichheit. Von außen nach innen:

1. Normalisierung — Unicode, Leerraum, Satzzeichen, Groß/Klein.
2. Schriftregeln je Sprache — Schluss-Sigma im Griechischen, ß/ss im
   Deutschen, Akzente im Französischen und Spanischen.
3. Alternativen — mehrere gültige Übersetzungen, Klammerteile optional,
   Artikel je Sprache verlangt, freigestellt oder gleichgültig.
4. Verwechslungsprüfung — ist die Antwort eine ANDERE gültige Form desselben
   Wortes, wird genau das gesagt. Das darf kein Tippfehler sein: wer bei der
   1. Person "vas" schreibt, hat nicht sich vertippt, sondern die Person
   verwechselt.
5. Tippfehlertoleranz per Editierabstand. Ergebnis ist dann "fast richtig,
   bitte nochmal" — ohne Strafe für den Lernstand.
"""

from __future__ import annotations

import re
import unicodedata

import legasthenie
from dataclasses import dataclass, field, asdict

# Satzzeichen, die am Rand einer Antwort nichts bedeuten.
_RAND = " \t\n\r.,;:!?¡¿\"'»«“”„’…-–—"
# Typografische Apostrophe. iOS und macOS ersetzen den geraden Apostroph
# selbsttätig — ohne diese Gleichsetzung gilt »l’école« als falsch, und zwar
# ohne jeden Hinweis, weil es zeichengleich die richtige Antwort ist.
_APOSTROPHE = str.maketrans({"’": "'", "‘": "'", "ʼ": "'", "´": "'"})
_MEHRFACH_LEERRAUM = re.compile(r"\s+")
_KLAMMERTEIL = re.compile(r"\s*\(([^()]*)\)\s*")


@dataclass
class Urteil:
    urteil: str                              # richtig | fast | falsch
    treffer: str | None = None               # die getroffene erwartete Antwort
    hinweis: str | None = None               # Klartext für die Oberfläche
    abweichungen: list[str] = field(default_factory=list)
    distanz: int = 0
    # Welcher Art war der Fehler? Von legasthenie.fehler_benennen ergänzt.
    # "Du hast b und d vertauscht" ist eine brauchbare Auskunft,
    # "falsch" ist keine — und zwar für alle, nicht nur bei Legasthenie.
    fehlerart: str | None = None
    fehlertext: str | None = None

    @property
    def zaehlt_als_richtig(self) -> bool:
        return self.urteil == "richtig"

    def als_dict(self) -> dict:
        return asdict(self)


# ------------------------------------------------------------ Normalisierung

def _regeln(profil: dict) -> dict:
    return profil.get("pruefung", {}) if profil else {}


def normalisieren(text: str, profil: dict) -> str:
    """Vergleichsform: Unicode NFC, Ränder und Mehrfachleerraum weg,
    je nach Profil Groß/Klein eingezogen."""
    r = _regeln(profil)
    text = unicodedata.normalize("NFC", text or "")
    text = text.translate(_APOSTROPHE)
    text = _MEHRFACH_LEERRAUM.sub(" ", text).strip()
    if r.get("satzzeichen", "ignorieren") == "ignorieren":
        text = text.strip(_RAND)
    if r.get("gross_klein", "ignorieren") == "ignorieren":
        text = text.casefold()
    return text


def _schriftregeln(text: str, profil: dict) -> str:
    """Sprachspezifische Gleichsetzungen, die KEINE Diakritika sind."""
    for regel in _regeln(profil).get("schriftregeln", []):
        if regel == "griechisch":
            # Schluss-Sigma und Sigma sind derselbe Buchstabe. Wer mitten im
            # Wort ς schreibt, hat sich nicht geirrt, sondern nur die
            # Tastenkombination genommen, die sein Gerät anbietet.
            text = text.replace("ς", "σ")
        elif regel == "mittelhochdeutsch":
            # Die Ligaturen und das lange s lassen sich auf einer normalen
            # Tastatur nicht tippen, und die Ausgaben setzen sie verschieden.
            # Die Längenzeichen (â, ê …) fallen schon über die Diakritika weg.
            for alt, neu in (("æ", "ae"), ("œ", "oe"), ("ʒ", "z"),
                             ("ſ", "s"), ("ȥ", "z"), ("iu", "iu")):
                text = text.replace(alt, neu)
        elif regel == "deutsch":
            text = (text.replace("ß", "ss")
                        .replace("ä", "ae").replace("ö", "oe").replace("ü", "ue"))
    return text


def ohne_diakritika(text: str) -> str:
    """Zerlegt in Grundzeichen und wirft die Verbindungszeichen weg.
    Wirkt für Lateinisch (é -> e) und Griechisch (ά -> α) gleichermaßen."""
    zerlegt = unicodedata.normalize("NFD", text)
    return unicodedata.normalize(
        "NFC", "".join(z for z in zerlegt if not unicodedata.combining(z))
    )


def _genau(text: str, profil: dict) -> str:
    """Vergleichsform MIT Diakritika, aber mit angewandten Schriftregeln.

    Der Unterschied zu _kern ist der ganze Witz der Sache:
    Schriftregeln setzen gleichwertige SCHREIBUNGEN gleich — "schoene" für
    "schœne" ist keine Abweichung, sondern eine andere Ausgabenkonvention.
    Diakritika dagegen sind bedeutsam: "nam" und "nâmen" sind Singular und
    Plural. Darum werden sie nur hier unterschieden, nicht in _kern."""
    return _schriftregeln(normalisieren(text, profil), profil)


def _kern(text: str, profil: dict) -> str:
    """Vergleichsform ohne Diakritika und mit Schriftregeln."""
    return ohne_diakritika(_genau(text, profil))


# ----------------------------------------------------------------- Varianten

def varianten(text: str) -> list[str]:
    """Klammerteile sind optional: "(sich) waschen" gilt als "sich waschen"
    und als "waschen". Mehrere Klammern werden kombiniert."""
    ergebnis = {text}
    while True:
        neu = set()
        for v in ergebnis:
            treffer = _KLAMMERTEIL.search(v)
            if not treffer:
                continue
            mit = (v[:treffer.start()] + " " + treffer.group(1) + " "
                   + v[treffer.end():])
            ohne = v[:treffer.start()] + " " + v[treffer.end():]
            neu.add(_MEHRFACH_LEERRAUM.sub(" ", mit).strip())
            neu.add(_MEHRFACH_LEERRAUM.sub(" ", ohne).strip())
        if not neu - ergebnis:
            break
        ergebnis |= neu
    return [v for v in ergebnis if v]


def _artikel_trennen(text: str, profil: dict) -> tuple[str | None, str]:
    """Trennt einen führenden Artikel ab. Gibt (Artikel, Rest) zurück."""
    artikel = profil.get("artikel", {}) if profil else {}
    alle = [a.casefold() for a in
            list(artikel.get("bestimmt", [])) + list(artikel.get("unbestimmt", []))]
    if not alle:
        return None, text
    klein = text.casefold()
    for a in sorted(alle, key=len, reverse=True):
        if a.endswith("'"):                        # l'école
            if not klein.startswith(a):
                continue
            rest = text[len(a):].strip()
        elif klein.startswith(a + " "):
            rest = text[len(a) + 1:].strip()
        else:
            continue
        # Der Artikel selbst kann die gesuchte Vokabel sein. Dann bleibt er.
        if rest:
            return a, rest
    return None, text


# ------------------------------------------------------------ Editierabstand

def abstand(a: str, b: str, grenze: int = 4) -> int:
    """Levenshtein-Abstand, abgebrochen sobald die Grenze überschritten ist."""
    if a == b:
        return 0
    if abs(len(a) - len(b)) > grenze:
        return grenze + 1
    vorher = list(range(len(b) + 1))
    for i, za in enumerate(a, 1):
        jetzt = [i]
        for j, zb in enumerate(b, 1):
            jetzt.append(min(
                vorher[j] + 1,
                jetzt[j - 1] + 1,
                vorher[j - 1] + (za != zb),
            ))
        if min(jetzt) > grenze:
            return grenze + 1
        vorher = jetzt
    return vorher[-1]


def toleranz(laenge: int) -> int:
    """Wie viele Tippfehler gelten noch als "fast richtig"?

    Bei kurzen Wörtern keiner — "pan" und "pen" sind zwei Wörter. Und auch
    sonst knapp gehalten: die Rückmeldung nennt die richtige Lösung, großzügige
    Toleranz verschenkt also die Aufgabe."""
    if laenge < 4:
        return 0
    if laenge < 12:
        return 1
    return 2


# -------------------------------------------------------------------- Prüfung
_RANG = {"richtig": 0, "fast": 1, "falsch": 2}


def _anzeige(text: str) -> str:
    """Form für die Rückmeldung an den Menschen: nur Unicode und Leerraum
    geglättet. Niemals kleingeschrieben — die Kleinschreibung nach Unicode
    verwandelt das griechische Schluss-Sigma (ς -> σ), und dann steht in der
    Rückmeldung ein falsch geschriebenes Wort."""
    return _MEHRFACH_LEERRAUM.sub(
        " ", unicodedata.normalize("NFC", text or "").translate(_APOSTROPHE)).strip()


def _besser(neu: Urteil, alt: Urteil | None) -> bool:
    if alt is None:
        return True
    if _RANG[neu.urteil] != _RANG[alt.urteil]:
        return _RANG[neu.urteil] < _RANG[alt.urteil]
    # Gleiches Urteil: das mit Rückmeldung ist das nützlichere.
    return alt.hinweis is None and neu.hinweis is not None


def _vorsilbe_trennen(text: str, vorsilben: list[str]) -> str:
    """Trennt ein führendes Wort ab, wenn es eine der erlaubten Vorsilben ist.

    Gebraucht für Personalpronomen: wer bei γράφω »εγώ γράφω« schreibt,
    hat nichts falsch gemacht — im Griechischen ist das Pronomen
    freiwillig. Und wer es im Lehrbuch mit Pronomen gelernt hat, schreibt
    es eben mit.
    """
    if not vorsilben:
        return text
    klein = text.casefold().lstrip()
    for v in sorted((x.casefold() for x in vorsilben), key=len, reverse=True):
        if v.endswith("'"):                        # j'ai
            if klein.startswith(v):
                rest = text.lstrip()[len(v):].strip()
                if rest:
                    return rest
        elif klein.startswith(v + " "):
            rest = text.lstrip()[len(v) + 1:].strip()
            if rest:
                return rest
    return text


def pruefen(eingabe: str, erwartet: list[str], profil: dict,
            verwechslungen: list[tuple[str, str]] | None = None,
            artikel_verlangt: str | None = None,
            fehler_benennen: bool = True,
            vorsilben: list[str] | None = None) -> Urteil:
    """Prüft eine Eingabe gegen alle gültigen Antworten.

    erwartet          alle zulässigen Antworten; eine zu treffen genügt
    verwechslungen    (Text, Beschriftung) anderer Formen desselben Wortes
    artikel_verlangt  der korrekte Artikel, wenn einer dazugehört
    fehler_benennen   die Art des Fehlers mitnennen (Reihenfolge, Doppelung,
                      verwechselte Buchstaben)

    Reihenfolge der Entscheidung:
      1. Treffer, ggf. bis auf Diakritika oder Artikel  -> gewinnt immer
      2. andere gültige Form desselben Wortes           -> klar falsch
      3. Tippfehler                                     -> "fast richtig"
    """
    if not (eingabe or "").strip() or not normalisieren(eingabe, profil):
        # Auch eine Antwort aus lauter Satzzeichen ist keine Antwort. Ohne
        # diese zweite Prüfung zählte ein versehentlich abgeschickter Punkt
        # als "nicht gewusst".
        return Urteil("falsch", hinweis="Keine Antwort eingegeben.")

    def abschluss(urteil: Urteil) -> Urteil:
        """Ergänzt die Fehlerart, bevor das Urteil hinausgeht."""
        if (not fehler_benennen or urteil.urteil == "richtig"
                or "verwechslung" in urteil.abweichungen):
            return urteil
        ziel = urteil.treffer
        if ziel is None:
            # Ohne Treffer die nächstliegende erwartete Antwort nehmen.
            kandidaten = [v for roh in erwartet for v in varianten(roh)]
            if not kandidaten:
                return urteil
            ziel = min(kandidaten,
                       key=lambda z: abstand(_kern(eingabe, profil),
                                             _kern(z, profil), grenze=99))
        art = legasthenie.fehler_benennen(eingabe, ziel)
        if art:
            urteil.fehlerart = art["art"]
            urteil.fehlertext = art["text"]
        return urteil

    # Ein freiwilliges Pronomen vorne weg — auf beiden Seiten, damit es
    # gleich ist, ob es in der Antwort oder in der hinterlegten Form steht.
    if vorsilben:
        eingabe = _vorsilbe_trennen(eingabe, vorsilben)
        erwartet = [_vorsilbe_trennen(e, vorsilben) for e in erwartet]

    regeln = _regeln(profil)
    diakritika = regeln.get("diakritika", "hinweis")
    artikelregel = (profil.get("artikel", {}) or {}).get("regel", "ignorieren")
    # Ein führender Artikel wird immer abgetrennt — "the table" und "table"
    # sind dieselbe Antwort. Die Regel entscheidet nur, ob er BEWERTET wird.
    artikel_pruefen = artikelregel != "ignorieren"

    e_norm = normalisieren(eingabe, profil)
    e_kern_voll = _kern(eingabe, profil)
    e_artikel, e_rest = _artikel_trennen(e_norm, profil)
    e_kern = _kern(e_rest, profil)
    e_genau = _genau(e_rest, profil)

    ziele = [(roh, v) for roh in erwartet for v in varianten(roh)]

    # ---- Schicht 1: Treffer, ggf. bis auf Diakritika oder Artikel
    bestes: Urteil | None = None
    for _roh, ziel in ziele:
        z_norm = normalisieren(ziel, profil)
        z_artikel, z_rest = _artikel_trennen(z_norm, profil)
        z_kern = _kern(z_rest, profil)
        z_genau = _genau(z_rest, profil)
        if not z_kern:
            continue

        gleich_genau = e_genau == z_genau
        gleich_kern = e_kern == z_kern
        if not gleich_kern:
            continue

        abw: list[str] = []
        hinweise: list[str] = []
        anzeige = _anzeige(ziel)

        if not gleich_genau:
            abw.append("diakritika")
            if diakritika == "streng":
                hinweise.append(f"Achte auf die Schreibung: {anzeige}")
            elif diakritika == "hinweis":
                hinweise.append(f"Fast — auf die Zeichen achten: {anzeige}")

        if artikel_pruefen:
            soll = artikel_verlangt or z_artikel
            if soll:
                if e_artikel is None:
                    if artikelregel == "verlangt":
                        abw.append("artikel_fehlt")
                        hinweise.append(f"Der Artikel fehlt: {_anzeige(soll)}")
                elif e_artikel.casefold() != soll.casefold():
                    abw.append("artikel_falsch")
                    hinweise.append(
                        f"Falscher Artikel: {_anzeige(soll)}, nicht {_anzeige(e_artikel)}")
            elif e_artikel is not None:
                abw.append("artikel_ueberfluessig")
                hinweise.append("Hier gehört kein Artikel davor.")

        if "diakritika" in abw and diakritika == "ignorieren":
            abw.remove("diakritika")
            hinweise = [h for h in hinweise if not h.startswith("Fast")]

        if not abw:
            return Urteil("richtig", anzeige)

        schwer = ("artikel_falsch" in abw
                  or ("diakritika" in abw and diakritika == "streng"))
        kandidat = Urteil("falsch" if schwer else "fast", anzeige,
                          " ".join(hinweise) or None, abw)
        if _besser(kandidat, bestes):
            bestes = kandidat

    if bestes is not None:
        return abschluss(bestes)

    # ---- Schicht 2: andere gültige Form desselben Wortes?
    # Muss VOR der Tippfehlertoleranz kommen. "vas" statt "vais" ist kein
    # Vertipper, sondern die verwechselte Person — und genau das soll dastehen.
    verwechselt = _verwechslung(e_kern_voll, verwechslungen or [], profil)
    if verwechselt:
        return Urteil("falsch",
                      hinweis=f"Das ist {verwechselt[1]} — gesucht war etwas anderes.",
                      abweichungen=["verwechslung"])

    # ---- Schicht 3: Tippfehler
    for _roh, ziel in ziele:
        z_norm = normalisieren(ziel, profil)
        _z_artikel, z_rest = _artikel_trennen(z_norm, profil)
        z_kern = _kern(z_rest, profil)
        if not z_kern:
            continue
        grenze = toleranz(len(z_kern))
        if grenze == 0:
            continue
        d = abstand(e_kern, z_kern, grenze=grenze)
        if 0 < d <= grenze:
            kandidat = Urteil("fast", _anzeige(ziel),
                              f"Tippfehler — richtig wäre: {_anzeige(ziel)}",
                              ["tippfehler"], d)
            if _besser(kandidat, bestes):
                bestes = kandidat

    return abschluss(bestes or Urteil("falsch"))


def _verwechslung(e_kern: str, verwechslungen: list[tuple[str, str]],
                  profil: dict) -> tuple[str, str] | None:
    for text, beschriftung in verwechslungen:
        if _kern(text, profil) == e_kern:
            return text, beschriftung
    return None
