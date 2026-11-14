"""Unterstützung bei Legasthenie.

Vorweg, damit die Entscheidungen nachvollziehbar sind: zur Lesbarkeit ist die
Befundlage ungleich. **Gut belegt** ist, dass vergrößerter Zeichenabstand das
Lesen erleichtert (Zorzi u.a. 2012), ebenso größere Schrift, mehr Zeilenabstand,
kurze Zeilen, linksbündiger Flattersatz und gedämpfter Kontrast. **Schwach
belegt** sind die eigens für Legasthenie entworfenen Schriftarten; kontrollierte
Vergleiche finden gegenüber einer schlichten Grotesk meist keinen Vorteil.
Darum ist hier der Abstand voreingestellt und die Schriftart nur ein Angebot.

Beim Lernen selbst setzt dieses Modul auf drei Dinge:

1. **Fehler benennen statt bewerten.** "Du hast b und d vertauscht" ist eine
   brauchbare Auskunft, "falsch" ist keine. Die Fehlerarten unten sind
   genau die, die beim Abruf von Zeichenfolgen typisch sind.

2. **Zerlegen in Sinneinheiten.** Das Arbeitsgedächtnis hält drei bis vier
   Brocken, nicht zwölf Einzelbuchstaben. Und hier hat dieser Trainer einen
   Vorteil, den kein Kartenstapel hat: weil die Formen eines Wortes
   zusammenstehen, lässt sich der Stamm aus dem Paradigma ABLEITEN statt
   raten — "parl|ions" ist keine Silbentrennung, sondern die wirkliche Naht
   des Wortes.

3. **Stufenweises Aufdecken.** Erst erkennen, dann schreiben; und beim
   Schreiben nicht ins Leere, sondern gegen ein Gerüst.
"""

from __future__ import annotations

import unicodedata

# ----------------------------------------------------------- Verwechslungen

# Spiegelbildliche und drehbare Formen — die klassischen Verwechslungen.
GESTALT = [("b", "d"), ("b", "p"), ("d", "p"), ("p", "q"), ("q", "g"),
           ("u", "n"), ("m", "w"), ("a", "o"), ("h", "n"), ("f", "t")]

# Klanglich nahe Paare. Sie treten beim Schreiben nach Gehör auf.
KLANG = [("d", "t"), ("g", "k"), ("b", "p"), ("f", "v"), ("s", "z"),
         ("w", "v"), ("ä", "e"), ("i", "ü"), ("eu", "äu"), ("ei", "ai"),
         ("ch", "sch"), ("k", "ck"), ("z", "tz")]

# Reihenfolgefehler in festen Gruppen.
REIHENFOLGE = [("ei", "ie"), ("ie", "ei"), ("eu", "ue"), ("au", "ua")]

DOPPELBAR = "bdfgklmnprstz"
# Auch die griechischen — sonst zeigt die Maske auf Stufe 3 das ganze
# Wort, weil keiner ihrer Buchstaben als Vokal erkannt wird. Bei den
# Tipps wäre das die Lösung statt eines Hinweises, im Legastheniemodus
# stünde die Antwort in der Frage.
VOKALE = ("aeiouäöüyâêîôûæœ"
          "αειουηω"                      # griechische Vokale
          "άέίόύήώ"                      # mit Tonos
          "ϊϋΐΰ")                        # mit Trema


def _zeichen(text: str) -> str:
    return unicodedata.normalize("NFC", (text or "").strip().casefold())


def _paar_bekannt(a: str, b: str, liste) -> bool:
    return any({a, b} == {x, y} for x, y in liste)


# ------------------------------------------------------------ Fehleranalyse

def _schritte(a: str, b: str) -> list[tuple[str, int, str, str]]:
    """Levenshtein mit Rückverfolgung. Gibt die Einzelschritte zurück:
    ("ersetzt" | "ausgelassen" | "eingefuegt", Stelle, aus, nach)."""
    n, m = len(a), len(b)
    tafel = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n + 1):
        tafel[i][0] = i
    for j in range(m + 1):
        tafel[0][j] = j
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            tafel[i][j] = min(tafel[i - 1][j] + 1,
                              tafel[i][j - 1] + 1,
                              tafel[i - 1][j - 1] + (a[i - 1] != b[j - 1]))
    schritte, i, j = [], n, m
    while i > 0 or j > 0:
        if i > 0 and j > 0 and a[i - 1] == b[j - 1] and tafel[i][j] == tafel[i - 1][j - 1]:
            i, j = i - 1, j - 1
        elif i > 0 and j > 0 and tafel[i][j] == tafel[i - 1][j - 1] + 1:
            schritte.append(("ersetzt", j - 1, a[i - 1], b[j - 1]))
            i, j = i - 1, j - 1
        elif i > 0 and tafel[i][j] == tafel[i - 1][j] + 1:
            schritte.append(("eingefuegt", j, a[i - 1], ""))
            i -= 1
        else:
            schritte.append(("ausgelassen", j - 1, "", b[j - 1]))
            j -= 1
    return list(reversed(schritte))


def fehler_benennen(eingabe: str, ziel: str) -> dict | None:
    """Was für ein Fehler war das?

    Gibt Art und eine Erklärung in Klartext zurück, oder None, wenn die
    Abweichung zu groß ist, um sie sinnvoll zu benennen.
    """
    a, b = _zeichen(eingabe), _zeichen(ziel)
    if not a or not b or a == b:
        return None

    # Vertauschte Nachbarn: "frsit" für "frist". Die häufigste Form des
    # Reihenfolgefehlers und die, die als Tippfehler verschwinden würde.
    if len(a) == len(b):
        abweichend = [i for i in range(len(a)) if a[i] != b[i]]
        if len(abweichend) == 2:
            i, k = abweichend
            if k == i + 1 and a[i] == b[k] and a[k] == b[i]:
                return {"art": "umgestellt",
                        "text": f"Die Reihenfolge: {b[i]} kommt vor {b[k]}, "
                                f"nicht umgekehrt.",
                        "stellen": abweichend}

    # Umgestellte Buchstabengruppen: "ei" für "ie".
    for links, rechts in REIHENFOLGE:
        if links in a and rechts in b and a.replace(links, rechts) == b:
            return {"art": "umgestellt_gruppe",
                    "text": f"Hier steht {rechts}, nicht {links}.",
                    "stellen": []}

    schritte = _schritte(a, b)
    if len(schritte) > 2:
        return None

    # Doppelung: ein Zeichen zu viel oder zu wenig, und zwar genau neben
    # seinem Zwilling.
    if len(schritte) == 1:
        art, stelle, aus, nach = schritte[0]
        if art == "eingefuegt" and aus in DOPPELBAR and aus * 2 in a:
            return {"art": "doppelung_zuviel",
                    "text": f"Ein {aus} zu viel — hier wird es nicht verdoppelt.",
                    "stellen": [stelle]}
        if art == "ausgelassen" and nach in DOPPELBAR and nach * 2 in b:
            return {"art": "doppelung_zuwenig",
                    "text": f"Hier gehört {nach}{nach} hin, mit zwei.",
                    "stellen": [stelle]}
        if art == "ersetzt":
            if _paar_bekannt(aus, nach, GESTALT):
                return {"art": "gestalt_verwechselt",
                        "text": f"{aus} und {nach} sehen sich ähnlich — "
                                f"hier ist es {nach}.",
                        "stellen": [stelle]}
            if _paar_bekannt(aus, nach, KLANG):
                return {"art": "klang_verwechselt",
                        "text": f"Klingt wie {aus}, geschrieben wird {nach}.",
                        "stellen": [stelle]}
            if aus in VOKALE and nach in VOKALE:
                return {"art": "vokal",
                        "text": f"Der Selbstlaut: {nach}, nicht {aus}.",
                        "stellen": [stelle]}
            return {"art": "ersetzt",
                    "text": f"An dieser Stelle steht {nach}, nicht {aus}.",
                    "stellen": [stelle]}
        if art == "ausgelassen":
            return {"art": "ausgelassen",
                    "text": f"Ein {nach} fehlt.", "stellen": [stelle]}
        return {"art": "eingefuegt",
                "text": f"Das {aus} gehört nicht hinein.", "stellen": [stelle]}

    arten = {s[0] for s in schritte}
    if arten == {"ausgelassen"}:
        fehlt = "".join(s[3] for s in schritte)
        return {"art": "ausgelassen",
                "text": f"Es fehlen zwei Zeichen: {fehlt}.",
                "stellen": [s[1] for s in schritte]}
    return None


# ----------------------------------------------------------- Zerlegen

def _falten(text: str) -> str:
    """Vergleichsform ohne Betonungszeichen. Nötig, weil der Akzent wandert:
    griechisch έγρ-α-ψα gegen γρ-ά-ψαμε ist derselbe Stamm mit verschobener
    Betonung."""
    zerlegt = unicodedata.normalize("NFD", _zeichen(text))
    return unicodedata.normalize(
        "NFC", "".join(z for z in zerlegt if not unicodedata.combining(z)))


def _gemeinsamer_anfang(worte: list[str]) -> int:
    if not worte:
        return 0
    laenge = min(len(w) for w in worte)
    for i in range(laenge):
        if len({w[i] for w in worte}) > 1:
            return i
    return laenge


def ohne_partikel(wort: str, partikeln: list[str]) -> str:
    """Trennt ein vorangestelltes Wörtchen ab.

    Griechisch bildet das Futur mit θα davor: θα γράψω. Ohne Abtrennung
    ergäbe die Stammerkennung "θα γράψ" — und die Zerlegung zeigte das θα
    als Teil des Wortstamms, was es nicht ist.
    """
    text = (wort or "").strip()
    for p in sorted(partikeln or [], key=len, reverse=True):
        if text.casefold().startswith(p.casefold() + " "):
            return text[len(p):].strip()
    return text


def stamm(formen: list[str], partikeln: list[str] | None = None) -> str:
    """Der gemeinsame Stamm der Formen — aus dem Paradigma abgeleitet.

    Wer "parle, parles, parlons, parlez, parlent" beisammen hat, weiß ohne
    Wörterbuch, dass "parl" der Stamm ist. Genau deshalb kann dieser Trainer
    zerlegen, was ein Kartenstapel nicht kann.

    Zwei Dinge machen es schwieriger, als es klingt:

    * Der **Akzent wandert**. Darum wird ohne Betonungszeichen verglichen.
    * Ein **Augment** tritt vor den Stamm, aber nicht in allen Zellen:
      griechisch έγραψα, έγραψες, έγραψε — aber γράψαμε, γράψατε. Ein
      gemeinsamer Anfang über alle sechs Formen gibt es dann nicht, einen
      gemeinsamen Stamm aber sehr wohl. Darum wird jeder Form zugestanden,
      ein Zeichen davor zu haben.
    """
    sauber = [ohne_partikel(f, partikeln) for f in formen if f and f.strip()]
    sauber = [f for f in sauber if f]
    if len(sauber) < 2:
        return ""
    gefaltet = [_falten(f) for f in sauber]

    # Erster, einfacher Versuch: gemeinsamer Anfang aller Formen.
    laenge = _gemeinsamer_anfang(gefaltet)
    if laenge >= 2:
        return _laengster_treffer(sauber[0], gefaltet[0][:laenge])

    # Zweiter Versuch: jede Form darf ein Zeichen vorweg haben (Augment).
    moeglichkeiten = [{g, g[1:]} for g in gefaltet]
    kuerzeste = min(gefaltet, key=len)
    for ende in range(len(kuerzeste), 1, -1):
        for anfang in (0, 1):
            kandidat = kuerzeste[anfang:ende]
            if len(kandidat) < 2:
                continue
            if all(any(v.startswith(kandidat) for v in varianten)
                   for varianten in moeglichkeiten):
                return kandidat
    return ""


def _laengster_treffer(original: str, gefalteter_stamm: str) -> str:
    """Gibt den Stamm in der Schreibung des Originals zurück — mit Akzent,
    wenn er dort steht."""
    return original[:len(gefalteter_stamm)]


def teilen(wort: str, stamm_text: str,
           partikeln: list[str] | None = None) -> list[str]:
    """Zerlegt eine Form in Stamm und Endung.

    Vergleicht ohne Betonungszeichen und lässt ein Augment davor zu, damit
    έγραψα als έγραψ|α zerfällt und nicht unzerlegt bleibt.
    """
    if not wort or not stamm_text:
        return [wort] if wort else []
    # Ein vorangestelltes Wörtchen bleibt als eigenes Stück stehen: das θα
    # gehört zur Form, aber nicht zum Stamm.
    rumpf = ohne_partikel(wort, partikeln)
    vorsatz = wort[:len(wort) - len(rumpf)] if len(rumpf) < len(wort) else ""
    ziel = _falten(stamm_text)
    gefaltet = _falten(rumpf)
    for versatz in (0, 1):
        if gefaltet[versatz:].startswith(ziel):
            schnitt = versatz + len(ziel)
            rest = rumpf[schnitt:]
            teile = [rumpf[:schnitt]] + ([rest] if rest else [])
            return ([vorsatz.strip()] + teile) if vorsatz.strip() else teile
    return [wort]


_DIGRAPHEN = ("sch", "ch", "ck", "ph", "th", "sh", "qu", "ll", "rr", "gn")


def silben(wort: str) -> list[str]:
    """Näherungsweise Sprechsilben.

    Nach Vokalgruppen getrennt, Digraphen bleiben zusammen. Für Deutsch,
    Mittelhochdeutsch, Spanisch und Griechisch brauchbar, für Französisch und
    Englisch nur ein Anhalt — deren Schreibung gibt die Silbe nicht her.
    Als Lesehilfe reicht es; als Sprachwissenschaft nicht.
    """
    text = (wort or "").strip()
    if len(text) < 4:
        return [text] if text else []
    klein = text.casefold()

    # Vokalgruppen suchen
    gruppen: list[tuple[int, int]] = []
    i = 0
    while i < len(klein):
        if klein[i] in VOKALE:
            j = i
            while j + 1 < len(klein) and klein[j + 1] in VOKALE:
                j += 1
            gruppen.append((i, j))
            i = j + 1
        else:
            i += 1
    if len(gruppen) < 2:
        return [text]

    schnitte: list[int] = []
    for k in range(len(gruppen) - 1):
        ende_vokal = gruppen[k][1]
        anfang_naechster = gruppen[k + 1][0]
        zwischen = klein[ende_vokal + 1:anfang_naechster]
        if not zwischen:
            schnitt = anfang_naechster              # Hiatus: se-hen
        elif len(zwischen) == 1:
            schnitt = anfang_naechster - 1          # ein Konsonant wandert mit
        else:
            # Digraph am Ende der Gruppe bleibt beim folgenden Vokal
            rest = anfang_naechster - 1
            for d in _DIGRAPHEN:
                if zwischen.endswith(d):
                    rest = anfang_naechster - len(d)
                    break
            schnitt = max(ende_vokal + 1, rest)
        if schnitt > (schnitte[-1] if schnitte else 0):
            schnitte.append(schnitt)

    teile, vorher = [], 0
    for s in schnitte:
        if s > vorher:
            teile.append(text[vorher:s])
            vorher = s
    teile.append(text[vorher:])
    return [t for t in teile if t]


def maske(wort: str, stufe: int) -> str:
    """Gerüst statt leeres Feld.

    stufe 0  alles verdeckt       _ _ _ _ _ _
    stufe 1  erster Buchstabe     p _ _ _ _ _
    stufe 2  Anfang und Ende      p _ _ _ _ s
    stufe 3  Mitlaute sichtbar    p _ r l _ _
    """
    if not wort:
        return ""
    zeichen = list(wort)
    sichtbar = [False] * len(zeichen)
    if stufe >= 1:
        sichtbar[0] = True
    if stufe >= 2:
        sichtbar[-1] = True
    if stufe >= 3:
        for i, z in enumerate(zeichen):
            if z.casefold() not in VOKALE and z.isalpha():
                sichtbar[i] = True
    return " ".join(z if (s or not z.isalpha()) else "_"
                    for z, s in zip(zeichen, sichtbar))


# ------------------------------------------------------------ Voreinstellung

# Was der Modus einschaltet. Alles einzeln abwählbar — Legasthenie sieht bei
# jedem anders aus, und eine Voreinstellung, die man nicht ändern kann, ist
# keine Hilfe.
VOREINSTELLUNG = {
    "aktiv": False,
    # Darstellung
    "zeichenabstand": 0.12,          # em. Die am besten belegte Maßnahme.
    "wortabstand": 0.16,
    "zeilenhoehe": 1.9,
    "schriftgroesse": 1.25,          # Faktor
    "schriftart": "grotesk",         # grotesk | opendyslexic | serifenlos
    "hintergrund": "creme",          # creme | hell | dunkel
    "silben_faerben": True,
    "stamm_hervorheben": True,
    # Lernen
    "vorlesen_zuerst": True,         # hören, dann sehen
    "erkennen_vor_schreiben": True,  # erst auswählen, dann tippen
    "bausteine": True,               # Wort aus Bausteinen setzen statt tippen
    "maske_stufe": 2,                # Gerüst beim Schreiben
    "mehr_wiederholungen": True,     # häufiger, dafür kleinere Schritte
    "weniger_neues": True,
    "fehler_benennen": True,
    "keine_zeitmessung": True,
}
