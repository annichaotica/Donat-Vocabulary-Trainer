# Vokabeltrainer — Copyright (C) 2026 Annuschka Brenner
#
# Freie Software unter der GNU Affero General Public License, Fassung 3
# oder später. Herausgegeben in der Hoffnung, dass sie nützt, aber OHNE
# JEDE GEWÄHRLEISTUNG. Siehe die Datei LICENSE.
"""FSRS-5 — der Lernalgorithmus, nachvollziehbar.

FSRS ist der Nachfolger von SM-2 und steckt heute in Anki. Der Unterschied zu
den üblichen Trainern liegt hier nicht in der Formel, sondern darin, dass
jede Zwischengröße abrufbar bleibt: Stabilität, Schwierigkeit,
Abrufwahrscheinlichkeit und die Termine, die sich aus jeder möglichen
Bewertung ergäben. Damit ist "Warum kommt diese Vokabel jetzt?" beantwortbar.

Die drei Größen:

* **Stabilität** S — die Zahl der Tage, nach denen die Erinnerung auf 90 %
  abgesunken ist. Sie ist damit unmittelbar der Abstand bis zur nächsten
  Wiederholung bei einer Wunschretention von 90 %.
* **Schwierigkeit** D von 1 bis 10 — wie zäh dieses Stück Wissen ist.
* **Abrufwahrscheinlichkeit** R — wie wahrscheinlich es heute noch sitzt.

Die Parameter `STANDARD` sind die allgemeinen FSRS-5-Vorgaben. Sie lassen
sich später aus dem eigenen Wiederholungsprotokoll nachrechnen; genau dafür
wird die Tabelle `wiederholung` nie geleert.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass

# Vergessenskurve: R(t) = (1 + FAKTOR * t/S) ^ ABFALL
ABFALL = -0.5
FAKTOR = 0.9 ** (1 / ABFALL) - 1          # = 19/81

STANDARD: tuple[float, ...] = (
    0.40255, 1.18385, 3.173, 15.69105,     # w0..w3  Anfangsstabilität je Bewertung
    7.1949, 0.5345,                        # w4,w5   Anfangsschwierigkeit
    1.4604, 0.0046,                        # w6,w7   Änderung und Rückzug der Schwierigkeit
    1.54575, 0.1192, 1.01925,              # w8..w10 Zuwachs bei Erfolg
    1.9395, 0.11, 0.29605, 2.2698,         # w11..w14 Stabilität nach Vergessen
    0.2315, 2.9898,                        # w15,w16 Abschlag "schwer", Zuschlag "leicht"
    0.51655, 0.6621,                       # w17,w18 Wiederholung am selben Tag
)

NOCHMAL, SCHWER, GUT, LEICHT = 1, 2, 3, 4
BEWERTUNGEN = {
    NOCHMAL: "Nochmal",
    SCHWER: "Schwer",
    GUT: "Gut",
    LEICHT: "Leicht",
}

S_MIN, S_MAX = 0.01, 36500.0
REIF_AB_TAGEN = 21.0


def _klemmen(wert: float, unten: float, oben: float) -> float:
    return max(unten, min(oben, wert))


def _zahl(wert: float, stellen: int = 1) -> str:
    """Deutsche Zahlschreibung. Nur die Zahl — ein .replace(".", ",") über
    einen ganzen Satz verwandelt auch die Satzpunkte in Kommata."""
    return f"{wert:.{stellen}f}".replace(".", ",")


@dataclass
class Zustand:
    """Der Gedächtniszustand einer Aufgabe bei einem Benutzer."""
    stabilitaet: float | None = None
    schwierigkeit: float | None = None

    @property
    def ist_neu(self) -> bool:
        return self.stabilitaet is None or self.schwierigkeit is None


# ------------------------------------------------------- Vergessen und Termin

def abrufwahrscheinlichkeit(verstrichen_tage: float, stabilitaet: float) -> float:
    """Wie wahrscheinlich sitzt es nach so vielen Tagen noch?"""
    if stabilitaet is None or stabilitaet <= 0:
        return 0.0
    return (1 + FAKTOR * max(0.0, verstrichen_tage) / stabilitaet) ** ABFALL


def intervall(stabilitaet: float, wunschretention: float = 0.9) -> float:
    """Abstand in Tagen, nach dem die Abrufwahrscheinlichkeit auf die
    Wunschretention gefallen ist. Bei 90 % ist das genau die Stabilität."""
    wunschretention = _klemmen(wunschretention, 0.70, 0.99)
    return (stabilitaet / FAKTOR) * (wunschretention ** (1 / ABFALL) - 1)


def streuen(tage: float, saat: int) -> float:
    """Streut den Termin leicht, damit nicht alles am selben Tag
    zusammenfällt. Pro Aufgabe immer gleich, also nicht bei jedem Blick
    ein anderer Termin."""
    if tage < 2.5:
        return tage
    spanne = max(1.0, tage * 0.05)
    wuerfel = random.Random(saat).uniform(-1.0, 1.0)
    return max(1.0, tage + spanne * wuerfel)


# --------------------------------------------------------------- Erstbewertung

def anfangsstabilitaet(bewertung: int, w=STANDARD) -> float:
    return _klemmen(w[bewertung - 1], S_MIN, S_MAX)


def anfangsschwierigkeit(bewertung: int, w=STANDARD) -> float:
    return _klemmen(w[4] - math.exp(w[5] * (bewertung - 1)) + 1, 1.0, 10.0)


# ------------------------------------------------------------- Fortschreibung

def neue_schwierigkeit(d: float, bewertung: int, w=STANDARD) -> float:
    """Schlechte Bewertungen erhöhen die Schwierigkeit, gute senken sie; dazu
    ein leichter Rückzug zur Mitte, damit ein einzelner Ausrutscher nicht
    dauerhaft nachwirkt."""
    delta = -w[6] * (bewertung - 3)
    d_neu = d + delta * (10 - d) / 9          # nach oben hin gedämpft
    d_neu = w[7] * anfangsschwierigkeit(LEICHT, w) + (1 - w[7]) * d_neu
    return _klemmen(d_neu, 1.0, 10.0)


def stabilitaet_nach_erfolg(s: float, d: float, r: float,
                            bewertung: int, w=STANDARD) -> float:
    """Der Zuwachs ist umso größer, je später wiederholt wurde (kleines R) —
    das ist der Kern des verteilten Lernens: zu früh wiederholen bringt wenig."""
    abschlag = w[15] if bewertung == SCHWER else 1.0
    zuschlag = w[16] if bewertung == LEICHT else 1.0
    zuwachs = (math.exp(w[8])
               * (11 - d)
               * (s ** -w[9])
               * (math.exp(w[10] * (1 - r)) - 1)
               * abschlag * zuschlag)
    return _klemmen(s * (1 + zuwachs), S_MIN, S_MAX)


def stabilitaet_nach_vergessen(s: float, d: float, r: float, w=STANDARD) -> float:
    """Nach einem Fehler fällt die Stabilität, aber nicht auf Null: was einmal
    gelernt war, kommt schneller zurück. Sie kann dabei nie steigen."""
    neu = (w[11]
           * (d ** -w[12])
           * ((s + 1) ** w[13] - 1)
           * math.exp(w[14] * (1 - r)))
    return _klemmen(min(neu, s), S_MIN, S_MAX)


def stabilitaet_am_selben_tag(s: float, bewertung: int, w=STANDARD) -> float:
    """Wiederholung am selben Tag. Sie bewegt die Stabilität nur wenig —
    mehrmals hintereinander dasselbe anzusehen ersetzt kein Ausschlafen."""
    return _klemmen(s * math.exp(w[17] * (bewertung - 3 + w[18])), S_MIN, S_MAX)


# ------------------------------------------------------------------- Ergebnis

@dataclass
class Ergebnis:
    stabilitaet: float
    schwierigkeit: float
    intervall_tage: float
    abrufwahrscheinlichkeit_vorher: float
    zustand: str
    bewertung: int


def bewerten(zustand: Zustand, bewertung: int, verstrichen_tage: float = 0.0,
             wunschretention: float = 0.9, w=STANDARD,
             saat: int | None = None,
             selber_tag: bool | None = None) -> Ergebnis:
    """Rechnet den neuen Gedächtniszustand und den nächsten Termin aus.

    `selber_tag` sagt, ob die vorige Antwort am selben KALENDERTAG kam.
    Ohne die Angabe wird wie bisher nach 24 Stunden entschieden — und
    genau das passte nicht zum Terminplan, der in Kalendertagen rechnet:
    wer abends um 20 Uhr lernt und morgens um 9 weitermacht, ist 13
    Stunden später einen Tag weiter, für die 24-Stunden-Regel aber noch
    am selben. Gemessen hat das Faktor drei ausgemacht (23,9 h → 1,41
    gegen 24,1 h → 4,03), und reife Karten blähte die Selber-Tag-Formel
    umgekehrt auf.
    """
    if bewertung not in BEWERTUNGEN:
        raise ValueError(f"Bewertung muss 1..4 sein, nicht {bewertung!r}")

    if zustand.ist_neu:
        s = anfangsstabilitaet(bewertung, w)
        d = anfangsschwierigkeit(bewertung, w)
        r_vorher = 0.0
    else:
        # Wie in der Referenzumsetzung: die ALTE Schwierigkeit geht in die
        # Stabilitätsformeln, und beide Werte werden vorher geklemmt. Ein von
        # Hand oder über den MCP verfälschter Lernzustand soll keinen
        # Serverfehler mitten in der Sitzung auslösen.
        s_alt = _klemmen(float(zustand.stabilitaet), S_MIN, S_MAX)
        d_alt = _klemmen(float(zustand.schwierigkeit), 1.0, 10.0)
        r_vorher = abrufwahrscheinlichkeit(verstrichen_tage, s_alt)
        d = neue_schwierigkeit(d_alt, bewertung, w)
        gleicher_tag = (verstrichen_tage < 1.0 if selber_tag is None
                        else selber_tag)
        if gleicher_tag:
            s = stabilitaet_am_selben_tag(s_alt, bewertung, w)
        elif bewertung == NOCHMAL:
            s = stabilitaet_nach_vergessen(s_alt, d_alt, r_vorher, w)
        else:
            s = stabilitaet_nach_erfolg(s_alt, d_alt, r_vorher, bewertung, w)

    tage = intervall(s, wunschretention)
    if bewertung == NOCHMAL:
        # Nicht in Tagen, sondern gleich wieder in dieser Sitzung.
        tage = 0.0
    else:
        tage = max(1.0, tage)
        if saat is not None:
            tage = streuen(tage, saat)

    if bewertung == NOCHMAL:
        neuer_zustand = "verlernt" if not zustand.ist_neu else "lernen"
    elif tage >= REIF_AB_TAGEN:
        neuer_zustand = "reif"
    else:
        neuer_zustand = "lernen"

    return Ergebnis(
        stabilitaet=round(s, 4),
        schwierigkeit=round(d, 4),
        intervall_tage=round(tage, 4),
        abrufwahrscheinlichkeit_vorher=round(r_vorher, 4),
        zustand=neuer_zustand,
        bewertung=bewertung,
    )


def vorschau(zustand: Zustand, verstrichen_tage: float = 0.0,
             wunschretention: float = 0.9, w=STANDARD,
             saat: int | None = None,
             selber_tag: bool | None = None) -> dict[int, float]:
    """Was würde jede der vier Bewertungen für einen Termin ergeben?

    Wird in der Oberfläche direkt auf den Knöpfen angezeigt — damit
    sichtbar ist, was die eigene Bewertung bewirkt.

    `saat` und `selber_tag` müssen dieselben sein wie beim späteren
    `bewerten`, sonst zeigt der Knopf etwas anderes an, als er tut: die
    Streuung um ±5 % lief nur in der Rechnung, nicht in der Vorschau.
    Der Knopf sagte »in 3,0 Monaten« und setzte 2,9.
    """
    return {
        b: bewerten(zustand, b, verstrichen_tage, wunschretention, w,
                    saat=saat, selber_tag=selber_tag).intervall_tage
        for b in BEWERTUNGEN
    }


def tage_in_text(tage: float) -> str:
    """Termin in lesbarer Form."""
    if tage <= 0:
        return "gleich noch einmal"
    if tage < 1:
        return "heute"
    if tage < 2:
        return "morgen"
    if tage < 31:
        return f"in {round(tage)} Tagen"
    if tage < 365:
        return f"in {_zahl(tage / 30.44)} Monaten"
    return f"in {_zahl(tage / 365.25)} Jahren"


def erklaeren(zustand: Zustand, verstrichen_tage: float,
              wunschretention: float = 0.9) -> dict:
    """Alles, was die Oberfläche braucht, um "Warum jetzt?" zu beantworten."""
    if zustand.ist_neu:
        return {
            "neu": True,
            "text": "Diese Aufgabe war noch nie dran.",
            "abrufwahrscheinlichkeit": None,
            "stabilitaet": None,
            "schwierigkeit": None,
        }
    r = abrufwahrscheinlichkeit(verstrichen_tage, zustand.stabilitaet)
    faellig_nach = intervall(zustand.stabilitaet, wunschretention)
    rest = faellig_nach - verstrichen_tage
    if rest <= 0:
        lage = f"fällig seit {_zahl(abs(rest))} Tagen"
    else:
        lage = f"planmäßig erst {tage_in_text(rest)}"
    return {
        "neu": False,
        "stabilitaet": round(zustand.stabilitaet, 2),
        "schwierigkeit": round(zustand.schwierigkeit, 2),
        "abrufwahrscheinlichkeit": round(r, 4),
        "verstrichen_tage": round(verstrichen_tage, 2),
        "intervall_tage": round(faellig_nach, 2),
        "text": (
            f"Zuletzt vor {_zahl(verstrichen_tage)} Tagen abgefragt. "
            f"Die Stabilität liegt bei {_zahl(zustand.stabilitaet)} Tagen, "
            f"die Erinnerung heute also bei etwa {r * 100:.0f} % — {lage}."
        ),
    }
