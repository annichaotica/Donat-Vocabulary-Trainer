"""Sprachprofile.

Jede Sprache bringt mit:

* ihren Merkmalsraum — welche Formgruppen es gibt und aus welchen Zellen sie
  bestehen. Englisch braucht kein Genus, Griechisch braucht Kasus.
* ihre Namen für die Zeiten. Im Deutschunterricht heißt es "Passé composé",
  nicht "Perfekt", und "Αόριστος", nicht "Aorist". Darum trägt jede
  Formgruppe ihren eigenen Namen; er wird nicht aus Dimensionen zusammengesetzt.
* ihre Regeln für die Antwortprüfung — Akzente, Artikel, Schrift.

Eine neue Sprache ist ein neuer Eintrag hier, keine Änderung am Code.
"""

from __future__ import annotations

import merkmale as mk
from merkmale import (INVENTAR, WORTARTEN, MerkmalFehler, beschriften,
                      normieren, pruefen as pruefen_merkmale)

PERSONEN = (("1", "sg"), ("2", "sg"), ("3", "sg"),
            ("1", "pl"), ("2", "pl"), ("3", "pl"))


def _finit(kennung: str, name: str, merkmale: dict,
           personen=PERSONEN, kurz: str | None = None) -> dict:
    """Formgruppe mit Personenreihe, z.B. ein Präsens mit sechs Zellen."""
    return {
        "kennung": kennung,
        "name": name,
        "kurz": kurz or name,
        "merkmale": merkmale,
        "zellen": [{**merkmale, "person": p, "numerus": n} for p, n in personen],
    }


def _einzeln(kennung: str, name: str, merkmale: dict, kurz: str | None = None) -> dict:
    """Formgruppe mit genau einer Form, z.B. ein Partizip."""
    return {
        "kennung": kennung,
        "name": name,
        "kurz": kurz or name,
        "merkmale": merkmale,
        "zellen": [dict(merkmale)],
    }


def _kasusreihe(kennung: str, name: str, kasus: tuple[str, ...]) -> list[dict]:
    """Deklinationstabelle: Kasus × Numerus."""
    return [
        _einzeln(f"{kennung}_{k}_{n}",
                 f"{INVENTAR['kasus'][k][0]} {INVENTAR['numerus'][n][0]}",
                 {"kasus": k, "numerus": n},
                 kurz=f"{INVENTAR['kasus'][k][1]} {INVENTAR['numerus'][n][1]}")
        for n in ("sg", "pl") for k in kasus
    ]


# --------------------------------------------------------------- Französisch

_FR_ZEITEN = [
    _finit("praesens", "Présent", {"modus": "indikativ", "tempus": "praesens"}),
    _finit("imparfait", "Imparfait", {"modus": "indikativ", "tempus": "imperfekt"}),
    _finit("passe_compose", "Passé composé", {"modus": "indikativ", "tempus": "perfekt"}),
    _finit("plus_que_parfait", "Plus-que-parfait",
           {"modus": "indikativ", "tempus": "plusquamperfekt"}),
    _finit("passe_simple", "Passé simple", {"modus": "indikativ", "tempus": "praeteritum"}),
    _finit("futur_simple", "Futur simple", {"modus": "indikativ", "tempus": "futur"}),
    _finit("futur_anterieur", "Futur antérieur",
           {"modus": "indikativ", "tempus": "futur_perfekt"}),
    _finit("conditionnel", "Conditionnel présent",
           {"modus": "konditional", "tempus": "praesens"}),
    _finit("conditionnel_passe", "Conditionnel passé",
           {"modus": "konditional", "tempus": "perfekt"}),
    _finit("subjonctif", "Subjonctif présent",
           {"modus": "konjunktiv", "tempus": "praesens"}),
    _finit("subjonctif_passe", "Subjonctif passé",
           {"modus": "konjunktiv", "tempus": "perfekt"}),
    _finit("imperatif", "Impératif", {"modus": "imperativ"},
           personen=(("2", "sg"), ("1", "pl"), ("2", "pl"))),
    _einzeln("infinitif", "Infinitif", {"nonfinit": "infinitiv"}),
    _einzeln("participe_passe", "Participe passé", {"nonfinit": "partizip_perfekt"}),
    _einzeln("participe_present", "Participe présent", {"nonfinit": "partizip_praesens"}),
]

FRANZOESISCH = {
    # Was auf einer deutschen Tastatur mühsam ist. Die Leiste unter dem
    # Antwortfeld erspart in den meisten Fällen den Layoutwechsel.
    "sonderzeichen": ["é", "è", "ê", "ë", "à", "â", "ù", "û", "î", "ï",
                      "ô", "ç", "œ", "«", "»"],
    # Welche Formgruppen eine neue Sammlung von Anfang an abfragt. Alle 15
    # Zeiten gleichzeitig wären sinnlos; der Rest wird je Sammlung zugeschaltet.
    "formgruppen_standard": {
        "verb": ["praesens", "passe_compose", "imparfait", "futur_simple",
                 "participe_passe", "infinitif"],
        "substantiv": "alle",
        "adjektiv": "alle",
    },
    "code": "fr",
    "name": "Französisch",
    "schrift": "latein",
    "stimme": "fr-FR",
    "pruefung": {
        "gross_klein": "ignorieren",
        "diakritika": "hinweis",
        "satzzeichen": "ignorieren",
        "schriftregeln": [],
    },
    "artikel": {
        # Französisch beugt den Artikel nicht nach Fall, nur nach Zahl.
        "tabelle": {"m|sg": "le", "f|sg": "la", "m|pl": "les", "f|pl": "les"},
        "bestimmt": ["le", "la", "les", "l'"],
        "unbestimmt": ["un", "une", "des"],
        "regel": "optional_aber_richtig",
        "genus_artikel": {"m": "le", "f": "la"},
    },
    "formgruppen": {
        "verb": _FR_ZEITEN,
        "substantiv": [
            _einzeln("sg", "Singular", {"numerus": "sg"}),
            _einzeln("pl", "Plural", {"numerus": "pl"}),
        ],
        "adjektiv": [
            _einzeln("m_sg", "maskulin Singular", {"genus": "m", "numerus": "sg"}),
            _einzeln("f_sg", "feminin Singular", {"genus": "f", "numerus": "sg"}),
            _einzeln("m_pl", "maskulin Plural", {"genus": "m", "numerus": "pl"}),
            _einzeln("f_pl", "feminin Plural", {"genus": "f", "numerus": "pl"}),
        ],
    },
    "stammformen": ["infinitif", "participe_passe"],
    "lexemmerkmale": {
        "verb": {"hilfsverb": ["avoir", "être"], "klasse": ["er", "ir", "re", "unregelmäßig"]},
        # "mf": gemeinsames Geschlecht (un/une élève) — die Form ist
        # dieselbe, nur der Artikel richtet sich nach der Person.
        "substantiv": {"genus": ["m", "f", "mf"]},
    },
}

# ------------------------------------------------------------------ Spanisch

_ES_ZEITEN = [
    _finit("presente", "Presente", {"modus": "indikativ", "tempus": "praesens"}),
    _finit("imperfecto", "Pretérito imperfecto",
           {"modus": "indikativ", "tempus": "imperfekt"}, kurz="Imperfecto"),
    _finit("indefinido", "Pretérito indefinido",
           {"modus": "indikativ", "tempus": "praeteritum"}, kurz="Indefinido"),
    _finit("perfecto", "Pretérito perfecto",
           {"modus": "indikativ", "tempus": "perfekt"}, kurz="Perfecto"),
    _finit("pluscuamperfecto", "Pretérito pluscuamperfecto",
           {"modus": "indikativ", "tempus": "plusquamperfekt"}, kurz="Pluscuamperf."),
    _finit("futuro", "Futuro simple", {"modus": "indikativ", "tempus": "futur"}),
    _finit("condicional", "Condicional simple",
           {"modus": "konditional", "tempus": "praesens"}),
    _finit("subjuntivo", "Presente de subjuntivo",
           {"modus": "konjunktiv", "tempus": "praesens"}, kurz="Subj. presente"),
    _finit("subjuntivo_imperfecto", "Imperfecto de subjuntivo",
           {"modus": "konjunktiv", "tempus": "imperfekt"}, kurz="Subj. imperfecto"),
    _finit("imperativo", "Imperativo", {"modus": "imperativ"},
           personen=(("2", "sg"), ("3", "sg"), ("1", "pl"), ("2", "pl"), ("3", "pl"))),
    _einzeln("infinitivo", "Infinitivo", {"nonfinit": "infinitiv"}),
    _einzeln("participio", "Participio", {"nonfinit": "partizip_perfekt"}),
    _einzeln("gerundio", "Gerundio", {"nonfinit": "gerundium"}),
]

SPANISCH = {
    "sonderzeichen": ["á", "é", "í", "ó", "ú", "ü", "ñ", "¿", "¡"],
    "formgruppen_standard": {
        "verb": ["presente", "indefinido", "imperfecto", "futuro",
                 "participio", "infinitivo"],
        "substantiv": "alle",
        "adjektiv": "alle",
    },
    "code": "es",
    "name": "Spanisch",
    "schrift": "latein",
    "stimme": "es-ES",
    "pruefung": {
        "gross_klein": "ignorieren",
        "diakritika": "hinweis",
        "satzzeichen": "ignorieren",
        "schriftregeln": [],
    },
    "artikel": {
        "tabelle": {"m|sg": "el", "f|sg": "la", "m|pl": "los", "f|pl": "las"},
        "bestimmt": ["el", "la", "los", "las"],
        "unbestimmt": ["un", "una", "unos", "unas"],
        "regel": "optional_aber_richtig",
        "genus_artikel": {"m": "el", "f": "la"},
    },
    "formgruppen": {
        "verb": _ES_ZEITEN,
        "substantiv": [
            _einzeln("sg", "Singular", {"numerus": "sg"}),
            _einzeln("pl", "Plural", {"numerus": "pl"}),
        ],
        "adjektiv": [
            _einzeln("m_sg", "maskulin Singular", {"genus": "m", "numerus": "sg"}),
            _einzeln("f_sg", "feminin Singular", {"genus": "f", "numerus": "sg"}),
            _einzeln("m_pl", "maskulin Plural", {"genus": "m", "numerus": "pl"}),
            _einzeln("f_pl", "feminin Plural", {"genus": "f", "numerus": "pl"}),
        ],
    },
    "stammformen": ["infinitivo", "participio", "gerundio"],
    "lexemmerkmale": {
        "verb": {"klasse": ["ar", "er", "ir", "unregelmäßig"]},
        # "mf": gemeinsames Geschlecht (un/une élève) — die Form ist
        # dieselbe, nur der Artikel richtet sich nach der Person.
        "substantiv": {"genus": ["m", "f", "mf"]},
    },
}

# ------------------------------------------------------------------ Englisch

ENGLISCH = {
    "sonderzeichen": [],
    "formgruppen_standard": {"verb": "alle", "substantiv": "alle", "adjektiv": "alle"},
    "code": "en",
    "name": "Englisch",
    "schrift": "latein",
    "stimme": "en-GB",
    "pruefung": {
        "gross_klein": "ignorieren",
        "diakritika": "ignorieren",
        "satzzeichen": "ignorieren",
        "schriftregeln": [],
    },
    "artikel": {
        "bestimmt": ["the"],
        "unbestimmt": ["a", "an"],
        "regel": "ignorieren",
        "genus_artikel": {},
    },
    "formgruppen": {
        # Beim englischen Verb ist die Personenreihe uninteressant — gepaukt
        # werden die Stammformen und das -s der 3. Person.
        "verb": [
            _einzeln("infinitive", "Infinitiv", {"nonfinit": "infinitiv"}),
            _einzeln("present_3sg", "3. Person Singular Präsens",
                     {"modus": "indikativ", "tempus": "praesens",
                      "person": "3", "numerus": "sg"}, kurz="he/she/it"),
            _einzeln("past", "Simple past",
                     {"modus": "indikativ", "tempus": "praeteritum"}),
            _einzeln("past_participle", "Past participle",
                     {"nonfinit": "partizip_perfekt"}),
            _einzeln("present_participle", "Present participle (-ing)",
                     {"nonfinit": "partizip_praesens"}, kurz="-ing-Form"),
        ],
        "substantiv": [
            _einzeln("sg", "Singular", {"numerus": "sg"}),
            _einzeln("pl", "Plural", {"numerus": "pl"}),
        ],
        "adjektiv": [
            _einzeln("grund", "Grundstufe", {"stufe": "grund"}),
            _einzeln("komparativ", "Comparative", {"stufe": "komparativ"}),
            _einzeln("superlativ", "Superlative", {"stufe": "superlativ"}),
        ],
    },
    "stammformen": ["infinitive", "past", "past_participle"],
    "lexemmerkmale": {"verb": {"klasse": ["regelmäßig", "unregelmäßig"]}},
}

# ---------------------------------------------------------------- Griechisch

def _EL_DREI_GENERA(praefix: str) -> list[dict]:
    """Die drei Geschlechter im Nominativ Singular.

    Dieselbe Reihe für Adjektiv, Pronomen, Artikel und Zahlwort — es ist
    dieselbe Beugung, und sie viermal auszuschreiben hieße, sie dreimal
    falsch nachziehen zu können.
    """
    return [_einzeln(f"{praefix}_{g}",
                     f"{INVENTAR['genus'][g][0]} Nominativ Singular",
                     {"genus": g, "kasus": "nom", "numerus": "sg"})
            for g in ("m", "f", "n")]


_EL_KASUS = ("nom", "gen", "akk", "vok")

GRIECHISCH = {
    # Hier hilft keine Zeichenleiste: wer Griechisch schreibt, tippt ganze
    # Wörter in griechischer Schrift. Eine Palette aus 36 Knöpfen ersetzt
    # keine Tastatur, sie behindert nur. Also der Hinweis auf den
    # Layoutwechsel — und nur die Zeichen, die auch auf einer griechischen
    # Tastatur umständlich sind.
    "tastatur_empfohlen": True,
    "sonderzeichen": ["ά", "έ", "ή", "ί", "ό", "ύ", "ώ", "ϊ", "ϋ", "ΐ", "ΰ", "ς"],
    # Vorangestellte Wörtchen, die nicht zum Stamm gehören. Ohne sie ergäbe
    # die Stammerkennung beim Futur "θα γράψ" statt "γράψ" — und die
    # Zerlegung in Stamm und Endung zeigte das θα als Teil des Wortstamms.
    "partikeln": ["θα", "να", "ας", "δεν", "μην"],
    "formgruppen_standard": {
        # Dieselben drei Stammformen, einmal aktiv und einmal passiv.
        "verb": ["enestotas", "aoristos", "mellontas_stigmiaios",
                 "enestotas_pass", "aoristos_pass", "mellontas_pass"],
        "substantiv": ["subst_nom_sg", "subst_gen_sg", "subst_akk_sg",
                       "subst_nom_pl", "subst_gen_pl", "subst_akk_pl"],
        "adjektiv": "alle",
        "pronomen": "alle",
        "artikel": "alle",
        "numerale": "alle",
    },
    "code": "el",
    "name": "Griechisch",
    "schrift": "griechisch",
    "stimme": "el-GR",
    "pruefung": {
        "gross_klein": "ignorieren",
        # Die Betonungszeichen gehören zur Rechtschreibung, ein Vertipper
        # darin soll aber nicht als Fehler zählen, sondern als Hinweis.
        "diakritika": "hinweis",
        "satzzeichen": "ignorieren",
        "schriftregeln": ["griechisch"],
    },
    "artikel": {
        # Vollständig, nicht nur der Nominativ: sonst gilt "του καρότου"
        # als artikellos und der Artikel darin als Tippfehler.
        "bestimmt": ["ο", "η", "το", "οι", "τα",
                     "του", "της", "των", "τον", "την", "τους", "τις"],
        "unbestimmt": ["ένας", "μία", "μια", "ένα", "ενός", "μιας", "έναν"],
        "regel": "optional_aber_richtig",
        "genus_artikel": {"m": "ο", "f": "η", "n": "το"},
        # Welcher Artikel zu welcher Zelle gehört. Damit lässt sich beim
        # Üben nicht nur dulden, dass jemand ihn mitschreibt, sondern auch
        # sagen, WELCHER es gewesen wäre.
        "tabelle": {
            "m|nom|sg": "ο",   "f|nom|sg": "η",   "n|nom|sg": "το",
            "m|gen|sg": "του", "f|gen|sg": "της", "n|gen|sg": "του",
            "m|akk|sg": "τον", "f|akk|sg": "την", "n|akk|sg": "το",
            "m|nom|pl": "οι",  "f|nom|pl": "οι",  "n|nom|pl": "τα",
            "m|gen|pl": "των", "f|gen|pl": "των", "n|gen|pl": "των",
            "m|akk|pl": "τους", "f|akk|pl": "τις", "n|akk|pl": "τα",
        },
    },
    "formgruppen": {
        "verb": [
            # Aktiv. Das genus_verbi steht ausdrücklich dabei, seit es auch
            # Passivgruppen gibt — sonst passte eine Passivform auch hierher.
            _finit("enestotas", "Ενεστώτας (Präsens)",
                   {"modus": "indikativ", "tempus": "praesens",
                    "genus_verbi": "aktiv"}, kurz="Ενεστώτας"),
            _finit("paratatikos", "Παρατατικός (Imperfekt)",
                   {"modus": "indikativ", "tempus": "imperfekt",
                    "genus_verbi": "aktiv"}, kurz="Παρατατικός"),
            _finit("aoristos", "Αόριστος (Aorist)",
                   {"modus": "indikativ", "tempus": "aorist",
                    "genus_verbi": "aktiv"}, kurz="Αόριστος"),
            # Das Futur unterscheidet den Aspekt, und das ist kein Feinsinn:
            # θα γράψω heißt "ich werde schreiben", θα γράφω "ich werde
            # schreibend sein". Zwei Formen, zwei Bedeutungen.
            _finit("mellontas_stigmiaios", "Μέλλοντας στιγμιαίος (Futur, punktuell)",
                   {"modus": "indikativ", "tempus": "futur",
                    "aspekt": "perfektiv", "genus_verbi": "aktiv"},
                   kurz="Μέλλ. στιγμ."),
            _finit("mellontas_exakolouthitikos",
                   "Μέλλοντας εξακολουθητικός (Futur, fortgesetzt)",
                   {"modus": "indikativ", "tempus": "futur",
                    "aspekt": "imperfektiv", "genus_verbi": "aktiv"},
                   kurz="Μέλλ. εξακ."),
            _finit("parakeimenos", "Παρακείμενος (Perfekt)",
                   {"modus": "indikativ", "tempus": "perfekt",
                    "genus_verbi": "aktiv"}, kurz="Παρακείμενος"),
            _finit("ypotaktiki", "Υποτακτική (Konjunktiv)",
                   {"modus": "konjunktiv", "tempus": "praesens",
                    "genus_verbi": "aktiv"}, kurz="Υποτακτική"),
            _finit("prostaktiki", "Προστακτική (Imperativ)",
                   {"modus": "imperativ", "genus_verbi": "aktiv"},
                   personen=(("2", "sg"), ("2", "pl")), kurz="Προστακτική"),

            # Passiv. Eigene Gruppen, nicht bloß ein Merkmal an den
            # Aktivformen: die Endungen sind andere, und bei Deponentien
            # gibt es das Aktiv überhaupt nicht.
            _finit("enestotas_pass", "Ενεστώτας Παθητικής (Präsens Passiv)",
                   {"modus": "indikativ", "tempus": "praesens",
                    "genus_verbi": "passiv"}, kurz="Ενεστ. Παθ."),
            _finit("aoristos_pass", "Αόριστος Παθητικής (Aorist Passiv)",
                   {"modus": "indikativ", "tempus": "aorist",
                    "genus_verbi": "passiv"}, kurz="Αόρ. Παθ."),
            _finit("paratatikos_pass", "Παρατατικός Παθητικής (Imperfekt Passiv)",
                   {"modus": "indikativ", "tempus": "imperfekt",
                    "genus_verbi": "passiv"}, kurz="Παρατ. Παθ."),
            _finit("mellontas_pass", "Μέλλοντας Παθητικής (Futur Passiv, punktuell)",
                   {"modus": "indikativ", "tempus": "futur",
                    "aspekt": "perfektiv", "genus_verbi": "passiv"},
                   kurz="Μέλλ. Παθ."),
            _finit("ypotaktiki_pass", "Υποτακτική Παθητικής (Konjunktiv Passiv)",
                   {"modus": "konjunktiv", "tempus": "praesens",
                    "genus_verbi": "passiv"}, kurz="Υποτ. Παθ."),

            # Nicht nach Person gebeugt
            _einzeln("metochi_pass", "Μετοχή παθητικού παρακειμένου "
                                     "(Partizip Perfekt Passiv)",
                     {"nonfinit": "partizip_perfekt", "genus_verbi": "passiv"},
                     kurz="Μετοχή Παθ."),
            _einzeln("gerundio", "Γερούνδιο (Gerundium, -οντας)",
                     {"nonfinit": "gerundium", "genus_verbi": "aktiv"},
                     kurz="Γερούνδιο"),
        ],
        "substantiv": _kasusreihe("subst", "Deklination", _EL_KASUS),
        "adjektiv": _EL_DREI_GENERA("adj") + [
            # καλός – καλύτερος – ο καλύτερος
            _einzeln("adj_komparativ", "Συγκριτικός (Komparativ)",
                     {"stufe": "komparativ"}, kurz="Συγκριτικός"),
            _einzeln("adj_superlativ", "Υπερθετικός (Superlativ)",
                     {"stufe": "superlativ"}, kurz="Υπερθετικός"),
        ],
        # Auch Pronomen, Artikel und Zahlwörter werden nach Geschlecht
        # gebeugt: αυτός/αυτή/αυτό, ο/η/το, ένας/μία/ένα, τρεις/τρία. Ohne
        # eigene Gruppen fielen diese Formen in keine Tabelle und ließen
        # sich weder zuschalten noch gemeinsam ansehen.
        "pronomen": _EL_DREI_GENERA("pron"),
        "artikel": _EL_DREI_GENERA("art"),
        "numerale": _EL_DREI_GENERA("num"),
    },
    "stammformen": ["enestotas", "aoristos", "mellontas_stigmiaios"],
    "lexemmerkmale": {
        "substantiv": {"genus": ["m", "f", "n", "mf"]},
        "verb": {
            "klasse": ["Α-Konjugation", "Β1", "Β2", "unregelmäßig",
                       # Passivtypen nach der Endung der 1. Person Singular
                       "-ομαι", "-άμαι", "-ούμαι", "-ιέμαι"],
            # Deponentien (θυμάμαι, έρχομαι, κοιμάμαι) haben nur Passivformen,
            # bedeuten aber nichts Passives. Ihre Aktivgruppen gelten darum
            # nicht als fehlend.
            "diathese": ["aktiv", "medial", "deponens"],
        },
    },
}

# -------------------------------------------------------- Mittelhochdeutsch

# Im Mittelhochdeutschen sind die vier STAMMFORMEN das eigentliche Lernziel:
#   nëmen – nam – nâmen – genomen
# Daraus leitet sich das ganze Paradigma ab, und nach der Ablautreihe sind die
# starken Verben in sieben Klassen geordnet. Deshalb sind die beiden
# Präteritalstämme hier eigene Formgruppen: sie sind spezifischer als die
# Präteritumsreihe und gewinnen darum bei der Beschriftung.

MITTELHOCHDEUTSCH = {
    # Die Längenzeichen und Ligaturen der Lachmannschen Normalschreibung.
    # Auf keiner Tastatur der Welt bequem erreichbar.
    "sonderzeichen": ["â", "ê", "î", "ô", "û", "æ", "œ", "ë", "ï", "ü",
                      "iu", "ʒ", "ſ"],
    "code": "gmh",
    "name": "Mittelhochdeutsch",
    "schrift": "latein",
    # Es gibt keine Sprachsynthese dafür. Deutsch zu nehmen wäre irreführend,
    # denn die Aussprache ist eine andere — also keine Stimme.
    "stimme": None,
    "pruefung": {
        "gross_klein": "ignorieren",
        # Die Längenzeichen (â ê î ô û) unterscheiden Formen — nam gegen nâmen
        # ist Singular gegen Plural. Sie sind also bedeutsam. Gleichzeitig
        # weichen die Ausgaben voneinander ab und auf einer normalen Tastatur
        # sind sie mühsam. Darum: Hinweis, keine Strafe.
        "diakritika": "hinweis",
        "satzzeichen": "ignorieren",
        "schriftregeln": ["mittelhochdeutsch"],
    },
    "artikel": {
        "bestimmt": ["der", "diu", "daz", "die", "des", "dem", "den",
                     "dër", "diz"],
        "unbestimmt": ["ein", "eines", "einem", "einen", "einer"],
        "regel": "optional_aber_richtig",
        "genus_artikel": {"m": "der", "f": "diu", "n": "daz"},
        "tabelle": {
            "m|nom|sg": "der", "f|nom|sg": "diu", "n|nom|sg": "daz",
            "m|gen|sg": "des", "f|gen|sg": "der", "n|gen|sg": "des",
            "m|dat|sg": "dem", "f|dat|sg": "der", "n|dat|sg": "dem",
            "m|akk|sg": "den", "f|akk|sg": "die", "n|akk|sg": "daz",
            "m|nom|pl": "die", "f|nom|pl": "die", "n|nom|pl": "diu",
            "m|gen|pl": "der", "f|gen|pl": "der", "n|gen|pl": "der",
            "m|dat|pl": "den", "f|dat|pl": "den", "n|dat|pl": "den",
            "m|akk|pl": "die", "f|akk|pl": "die", "n|akk|pl": "diu",
        },
    },
    "formgruppen": {
        "verb": [
            _einzeln("infinitiv", "Infinitiv", {"nonfinit": "infinitiv"}),
            # Die beiden Präteritalstämme — Stammform zwei und drei.
            _einzeln("stamm_praet_sg", "1./3. Singular Präteritum",
                     {"modus": "indikativ", "tempus": "praeteritum",
                      "person": "1", "numerus": "sg"}, kurz="Prät. Sg."),
            _einzeln("stamm_praet_pl", "1./3. Plural Präteritum",
                     {"modus": "indikativ", "tempus": "praeteritum",
                      "person": "1", "numerus": "pl"}, kurz="Prät. Pl."),
            _einzeln("partizip_praet", "Partizip Präteritum",
                     {"nonfinit": "partizip_perfekt"}, kurz="Part. Prät."),
            _finit("praesens", "Präsens Indikativ",
                   {"modus": "indikativ", "tempus": "praesens"}, kurz="Präsens"),
            _finit("praeteritum", "Präteritum Indikativ",
                   {"modus": "indikativ", "tempus": "praeteritum"}, kurz="Präteritum"),
            _finit("konj_praesens", "Konjunktiv Präsens",
                   {"modus": "konjunktiv", "tempus": "praesens"}, kurz="Konj. Präs."),
            _finit("konj_praeteritum", "Konjunktiv Präteritum",
                   {"modus": "konjunktiv", "tempus": "praeteritum"}, kurz="Konj. Prät."),
            _finit("imperativ", "Imperativ", {"modus": "imperativ"},
                   personen=(("2", "sg"), ("2", "pl"))),
            _einzeln("partizip_praes", "Partizip Präsens",
                     {"nonfinit": "partizip_praesens"}, kurz="Part. Präs."),
        ],
        "substantiv": _kasusreihe("subst", "Deklination", ("nom", "gen", "dat", "akk")),
        "adjektiv": [
            _einzeln("stark", "starke Flexion, Nominativ Singular",
                     {"flexion": "stark", "kasus": "nom", "numerus": "sg"},
                     kurz="stark"),
            _einzeln("schwach", "schwache Flexion, Nominativ Singular",
                     {"flexion": "schwach", "kasus": "nom", "numerus": "sg"},
                     kurz="schwach"),
            _einzeln("komparativ", "Komparativ", {"stufe": "komparativ"}),
            _einzeln("superlativ", "Superlativ", {"stufe": "superlativ"}),
        ],
    },
    "formgruppen_standard": {
        # Vorab nur die Stammformen — das ist der Kern des Pensums.
        "verb": ["infinitiv", "stamm_praet_sg", "stamm_praet_pl", "partizip_praet"],
        "substantiv": ["subst_nom_sg", "subst_gen_sg", "subst_dat_sg",
                       "subst_akk_sg", "subst_nom_pl", "subst_gen_pl"],
        "adjektiv": "alle",
    },
    "stammformen": ["infinitiv", "stamm_praet_sg", "stamm_praet_pl",
                    "partizip_praet"],
    "lexemmerkmale": {
        # Die Ablautreihe ist ein lernbares Merkmal des Verbs, kein Merkmal
        # einer einzelnen Form.
        "verb": {"klasse": ["stark I", "stark II", "stark III", "stark IV",
                            "stark V", "stark VI", "stark VII",
                            "schwach", "Präteritopräsens", "Wurzelverb"]},
        "substantiv": {"genus": ["m", "f", "n", "mf"],
                       "klasse": ["stark a", "stark i", "stark u",
                                  "schwach n", "Wurzelnomen"]},
    },
    # Wonach die Abfrage »Klasse bestimmen« hier fragt. Genau so steht
    # es in der Klausur.
    "lexemmerkmale_fragen": {
        "verb": {"klasse": "Welche Ablautreihe?"},
        "substantiv": {"klasse": "Welche Deklinationsklasse?"},
    },
}

# -------------------------------------------------------------------- Deutsch

DEUTSCH = {
    "sonderzeichen": ["ä", "ö", "ü", "ß", "„", "“"],
    "formgruppen_standard": {"verb": "alle", "substantiv": "alle", "adjektiv": "alle"},
    "code": "de",
    "name": "Deutsch",
    "schrift": "latein",
    "stimme": "de-DE",
    "pruefung": {
        "gross_klein": "ignorieren",
        "diakritika": "hinweis",
        "satzzeichen": "ignorieren",
        "schriftregeln": ["deutsch"],
    },
    "artikel": {
        "bestimmt": ["der", "die", "das"],
        "unbestimmt": ["ein", "eine"],
        "regel": "optional_aber_richtig",
        "genus_artikel": {"m": "der", "f": "die", "n": "das"},
    },
    "formgruppen": {
        "verb": [
            _finit("praesens", "Präsens", {"modus": "indikativ", "tempus": "praesens"}),
            _finit("praeteritum", "Präteritum",
                   {"modus": "indikativ", "tempus": "praeteritum"}),
            _einzeln("infinitiv", "Infinitiv", {"nonfinit": "infinitiv"}),
            _einzeln("partizip_ii", "Partizip II", {"nonfinit": "partizip_perfekt"}),
        ],
        "substantiv": [
            _einzeln("sg", "Singular", {"numerus": "sg"}),
            _einzeln("pl", "Plural", {"numerus": "pl"}),
        ],
        "adjektiv": [
            _einzeln("grund", "Grundstufe", {"stufe": "grund"}),
            _einzeln("komparativ", "Komparativ", {"stufe": "komparativ"}),
            _einzeln("superlativ", "Superlativ", {"stufe": "superlativ"}),
        ],
    },
    "stammformen": ["infinitiv", "praeteritum", "partizip_ii"],
    "lexemmerkmale": {"substantiv": {"genus": ["m", "f", "n", "mf"]}},
}

PROFILE: dict[str, dict] = {
    p["code"]: p for p in (DEUTSCH, ENGLISCH, FRANZOESISCH, SPANISCH, GRIECHISCH,
                           MITTELHOCHDEUTSCH)
}

# Ein Rückfallprofil, damit eine Sprache auch ohne eigenen Eintrag benutzbar
# ist: Bedeutungen abfragen geht immer, Formgruppen fehlen dann eben.
RUECKFALL = {
    "code": "??",
    "name": "Weitere Sprache",
    "schrift": "latein",
    "stimme": None,
    "pruefung": {"gross_klein": "ignorieren", "diakritika": "hinweis",
                 "satzzeichen": "ignorieren", "schriftregeln": []},
    "artikel": {"bestimmt": [], "unbestimmt": [], "regel": "ignorieren",
                "genus_artikel": {}},
    "sonderzeichen": [],
    "partikeln": [],
    "formgruppen": {},
    "formgruppen_standard": {},
    "stammformen": [],
    "lexemmerkmale": {},
}


# --------------------------------------------------- Profile aus der Datenbank

# Was hier steht, überschreibt die Profile im Code. Gefüllt wird es aus der
# Spalte sprache.profil — damit ein Agent am MCP eine Sprache einrichten oder
# eine bestehende nachjustieren kann, ohne dass jemand Code ändert.
UEBERSCHREIBUNGEN: dict[str, dict] = {}


def uebernehmen(eintraege: dict[str, dict]) -> None:
    """Setzt die Überschreibungen aus der Datenbank."""
    UEBERSCHREIBUNGEN.clear()
    UEBERSCHREIBUNGEN.update({k: v for k, v in eintraege.items() if v})


def _formgruppen_mischen(grund: dict, eigen: dict) -> dict:
    """Mischt Formgruppen je Wortart.

    Eine Gruppe mit derselben Kennung ersetzt die aus dem Code; neue kommen
    hinzu. So lässt sich dem Französischen eine Zeit anfügen, ohne alle
    fünfzehn noch einmal hinzuschreiben.
    """
    ergebnis = {wortart: list(gruppen) for wortart, gruppen in grund.items()}
    for wortart, gruppen in (eigen or {}).items():
        vorhanden = {g["kennung"]: i for i, g in enumerate(ergebnis.get(wortart, []))}
        ergebnis.setdefault(wortart, [])
        for g in gruppen:
            if g.get("kennung") in vorhanden:
                ergebnis[wortart][vorhanden[g["kennung"]]] = g
            else:
                ergebnis[wortart].append(g)
    return ergebnis


def profil(code: str) -> dict:
    if code in PROFILE:
        grund = dict(PROFILE[code])
    else:
        grund = dict(RUECKFALL)
        grund["code"] = code
        grund["name"] = code

    eigen = UEBERSCHREIBUNGEN.get(code)
    if not eigen:
        return grund

    for schluessel, wert in eigen.items():
        if schluessel == "formgruppen":
            grund["formgruppen"] = _formgruppen_mischen(
                grund.get("formgruppen", {}), wert)
        elif isinstance(wert, dict) and isinstance(grund.get(schluessel), dict):
            grund[schluessel] = {**grund[schluessel], **wert}
        else:
            grund[schluessel] = wert
    return grund


def formgruppen(code: str, wortart: str) -> list[dict]:
    return profil(code).get("formgruppen", {}).get(wortart, [])


def formgruppen_standard(code: str) -> list[str]:
    """Kennungen der Formgruppen, die eine neue Sammlung abfragt."""
    vorgabe = profil(code).get("formgruppen_standard", {})
    ergebnis: list[str] = []
    for wortart, auswahl in vorgabe.items():
        if auswahl == "alle":
            ergebnis += [g["kennung"] for g in formgruppen(code, wortart)]
        else:
            ergebnis += list(auswahl)
    return ergebnis


def formgruppe(code: str, kennung: str) -> dict | None:
    for gruppen in profil(code).get("formgruppen", {}).values():
        for g in gruppen:
            if g["kennung"] == kennung:
                return g
    return None


def _passt(gruppe: dict, merkmale: dict, wortart: str = "") -> bool:
    """Gehört die Form in diese Gruppe? Alle Gruppenmerkmale müssen stimmen.

    Verglichen wird über die Normalform: eine Verbform ohne Angabe zum
    Genus verbi gilt als aktiv. Ohne das passte eine Passivform auch auf
    die Aktivgruppe.
    """
    voll = normieren(merkmale, wortart) if wortart else merkmale
    return all(voll.get(d) == w for d, w in gruppe["merkmale"].items())


def _gleiche_worte(a: str, b: str) -> bool:
    """Dieselben Wörter, gleich in welcher Reihenfolge.

    "feminin Nominativ Singular" und "Nominativ Singular feminin" sind
    dasselbe; ohne diesen Vergleich gälte der Gruppenname als eigener Name
    und bliebe in der einfachen Beschriftung unübersetzt stehen.
    """
    teilen = lambda t: sorted(t.replace(",", " ").casefold().split())
    return teilen(a) == teilen(b)


def beschriften_form(code: str, wortart: str, merkmale: dict,
                     kurz: bool = False, stil: str = "fach") -> str:
    """Beschriftet eine Form mit dem Namen ihrer Formgruppe und, falls die
    Gruppe eine Personenreihe hat, der Person.

    {"modus":"konditional","tempus":"praesens","person":"1","numerus":"sg"}
    -> "Conditionnel présent, 1. Person Singular"

    Ohne Formgruppen fällt es auf die allgemeine Beschriftung zurück.
    """
    kandidaten = [g for g in formgruppen(code, wortart)
                  if _passt(g, merkmale, wortart)]
    if not kandidaten:
        return beschriften(merkmale, kurz=kurz, stil=stil)
    # Die spezifischste Gruppe gewinnt (die mit den meisten festen Merkmalen).
    gruppe = max(kandidaten, key=lambda g: len(g["merkmale"]))
    name = gruppe["kurz"] if kurz else gruppe["name"]
    rest = {d: w for d, w in merkmale.items() if d not in gruppe["merkmale"]}
    fach = f"{name}, {beschriften(rest, kurz=kurz)}" if rest else name
    if stil == "fach":
        return fach

    # Nur das erklären, was über den Gruppennamen hinausgeht. Die Gruppe
    # selbst erklären wir, wenn die Zelle IST die Gruppe (einzellige
    # Gruppen wie "Genitiv Singular" oder "Συγκριτικός").
    schlicht = mk._einfach(rest) if rest else mk._einfach(gruppe["merkmale"])
    if not schlicht or _gleiche_worte(schlicht, fach):
        return fach
    # Trägt die Gruppe einen eigenen Namen — "Αόριστος", "Passé composé" —,
    # bleibt er stehen: so heißt die Tabelle im Lehrbuch, das ist kein
    # Fachjargon zum Wegerklären. Heißt sie dagegen einfach so, wie ihre
    # Merkmale lauten ("Genitiv Singular"), dann IST der Name die
    # Fachbezeichnung und darf ersetzt werden.
    abgeleitet = _gleiche_worte(name, beschriften(gruppe["merkmale"], kurz=kurz))
    if stil == "einfach":
        if abgeleitet:
            return mk._einfach(merkmale)
        return f"{name}, {schlicht}"
    # Zwei Klammern hintereinander liest niemand gern.
    return (f"{fach} — {schlicht}" if fach.endswith(")")
            else f"{fach} ({schlicht})")


def klassenfrage(code: str, wortart: str, merkmal: str) -> str:
    """Wie die Frage nach einem Lexemmerkmal lautet.

    »Welche Klasse?« wäre überall richtig und nirgends gut: bei einem
    mittelhochdeutschen Verb heißt die Frage »Welche Ablautreihe?«, und
    wer das Wort nicht liest, sucht in der Auswahl nach etwas anderem.
    Steht nichts im Profil, bleibt die allgemeine Fassung.
    """
    eigen = (profil(code).get("lexemmerkmale_fragen", {})
             .get(wortart, {}).get(merkmal))
    return eigen or "Welche Klasse?"


def pruefen_lexemmerkmale(code: str, wortart: str, merkmale: dict) -> dict[str, str]:
    """Prüft die Merkmale eines LEXEMS — ein anderer Namensraum als die
    Merkmale einer Form.

    Das Geschlecht eines Substantivs steht im allgemeinen Inventar. Die
    Ablautreihe eines mittelhochdeutschen Verbs ("stark IV") oder das
    Hilfsverb eines französischen ("être") stehen dagegen nur im
    Sprachprofil — sie beschreiben das Wort, nicht eine seiner Formen.
    """
    if not isinstance(merkmale, dict):
        raise MerkmalFehler("Merkmale müssen ein Objekt sein")
    erlaubt = profil(code).get("lexemmerkmale", {}).get(wortart, {})
    sauber: dict[str, str] = {}
    for dimension, wert in merkmale.items():
        wert = str(wert)
        if dimension in erlaubt:
            if wert not in erlaubt[dimension]:
                moeglich = ", ".join(erlaubt[dimension])
                raise MerkmalFehler(
                    f"Unbekannter Wert {wert!r} für {dimension!r} "
                    f"bei {wortart}/{code}. Möglich: {moeglich}")
        elif dimension in INVENTAR:
            if wert not in INVENTAR[dimension]:
                moeglich = ", ".join(sorted(INVENTAR[dimension]))
                raise MerkmalFehler(
                    f"Unbekannter Wert {wert!r} für {dimension!r}. "
                    f"Möglich: {moeglich}")
        elif not dimension.startswith("x_"):
            bekannt = sorted(set(erlaubt) | {"genus", "x_<eigenes>"})
            raise MerkmalFehler(
                f"Unbekanntes Lexemmerkmal {dimension!r} für "
                f"{wortart} in {profil(code)['name']}. Bekannt: "
                f"{', '.join(bekannt)}")
        sauber[dimension] = wert
    return sauber


# ----------------------------------------------------------- Profil prüfen

ERLAUBTE_SCHLUESSEL = {"name", "schrift", "stimme", "pruefung", "artikel",
                       "formgruppen", "formgruppen_standard", "stammformen",
                       "lexemmerkmale", "lexemmerkmale_fragen",
                       "beschriftungen", "sonderzeichen",
                       "tastatur_empfohlen", "partikeln"}


# Personalpronomen je Person und Zahl.
#
# Zwei verschiedene Lagen, und beide müssen bedient werden:
#
# Im Deutschen, Englischen und Französischen GEHÖRT das Pronomen zur Form
# — "gehst" allein sagt man nicht. Wer konjugieren lernt, lernt "du gehst".
#
# Im Griechischen braucht es keines: die Endung sagt schon, wer gemeint
# ist. Dort ist es trotzdem nützlich zu SEHEN, wer gemeint ist — und wer
# es mitschreibt, hat nichts falsch gemacht.
#
# Darum überall: anzeigen, und beim Prüfen als freiwillig behandeln.
PERSONALPRONOMEN: dict[str, dict[str, list[str]]] = {
    "de": {"1sg": ["ich"], "2sg": ["du"], "3sg": ["er", "sie", "es"],
           "1pl": ["wir"], "2pl": ["ihr"], "3pl": ["sie"]},
    "en": {"1sg": ["I"], "2sg": ["you"], "3sg": ["he", "she", "it"],
           "1pl": ["we"], "2pl": ["you"], "3pl": ["they"]},
    "fr": {"1sg": ["je", "j'"], "2sg": ["tu"], "3sg": ["il", "elle", "on"],
           "1pl": ["nous"], "2pl": ["vous"], "3pl": ["ils", "elles"]},
    "es": {"1sg": ["yo"], "2sg": ["tú"], "3sg": ["él", "ella", "usted"],
           "1pl": ["nosotros", "nosotras"],
           "2pl": ["vosotros", "vosotras"],
           "3pl": ["ellos", "ellas", "ustedes"]},
    "el": {"1sg": ["εγώ"], "2sg": ["εσύ"], "3sg": ["αυτός", "αυτή", "αυτό"],
           "1pl": ["εμείς"], "2pl": ["εσείς"],
           "3pl": ["αυτοί", "αυτές", "αυτά"]},
    "gmh": {"1sg": ["ich"], "2sg": ["dû"], "3sg": ["er", "siu", "ez"],
            "1pl": ["wir"], "2pl": ["ir"], "3pl": ["sie"]},
}

# Wo das Pronomen zur Form gehört und wo es nur eine Lesehilfe ist.
# Im Griechischen steht es in Klammern — es wird nicht verlangt.
PRONOMEN_PFLICHT = {"de": True, "en": True, "fr": True, "es": False,
                    "el": False, "gmh": False}


def artikel_fuer(code: str, lexemmerkmale: dict, formmerkmale: dict) -> str | None:
    """Welcher Artikel gehört vor diese Form?

    Gebraucht, damit beim Üben nicht nur geduldet wird, dass jemand den
    Artikel mitschreibt, sondern auch gesagt werden kann, WELCHER es
    gewesen wäre — »τα καρότα«, nicht bloß »καρότα«. Den Artikel
    mitzuschreiben ist die bessere Gewohnheit; wer ihn weglässt, soll ihn
    wenigstens zu sehen bekommen.
    """
    a = profil(code).get("artikel", {}) or {}
    tabelle = a.get("tabelle") or {}
    genus = lexemmerkmale.get("genus")
    if not genus or not tabelle:
        return None
    if genus == "mf":
        genus = "m"            # ο/η γιατρός — einer muss gezeigt werden
    kasus = formmerkmale.get("kasus")
    numerus = formmerkmale.get("numerus", "sg")
    if kasus == "vok":
        # Ausdrücklich keiner — nicht »unbekannt«. Nur hier darf ein
        # mitgeschriebener Artikel als überflüssig gelten.
        import pruefung
        return pruefung.KEIN_ARTIKEL
    for schluessel in (f"{genus}|{kasus}|{numerus}", f"{genus}|{numerus}"):
        if schluessel in tabelle:
            return tabelle[schluessel]
    return None


def personalpronomen(code: str, merkmale: dict) -> list[str]:
    """Die möglichen Pronomen zu dieser Person und Zahl, in dieser Sprache."""
    person = merkmale.get("person")
    if not person or merkmale.get("nonfinit"):
        return []
    # Beim Imperativ steht kein Pronomen: "geh!", nicht "du geh!".
    if merkmale.get("modus") == "imperativ":
        return []
    schluessel = f"{person}{merkmale.get('numerus', 'sg')}"
    eigene = profil(code).get("personalpronomen")
    tabelle = eigene if eigene is not None else PERSONALPRONOMEN.get(code, {})
    return list(tabelle.get(schluessel, []))


def pronomen_pflicht(code: str) -> bool:
    """Gehört das Pronomen zur Form, oder ist es nur eine Lesehilfe?"""
    p = profil(code)
    if "pronomen_pflicht" in p:
        return bool(p["pronomen_pflicht"])
    return PRONOMEN_PFLICHT.get(code, False)


def partikeln(code: str) -> list[str]:
    """Vorangestellte Wörtchen, die nicht zum Stamm gehören."""
    return list(profil(code).get("partikeln", []))


def tastatur_empfohlen(code: str) -> bool:
    """Lohnt für diese Sprache ein eigenes Tastaturlayout?

    Bei nichtlateinischer Schrift ja, immer: dort tippt man ganze Wörter in
    der fremden Schrift, und eine Zeichenleiste wäre nur im Weg. Bei
    lateinischer Schrift mit Akzenten reicht die Leiste — das sind einzelne
    Zeichen in sonst gewohnter Schreibung.
    """
    p = profil(code)
    if "tastatur_empfohlen" in p:
        return bool(p["tastatur_empfohlen"])
    return p.get("schrift", "latein") != "latein"


class ProfilFehler(ValueError):
    """Ein Sprachprofil ist nicht brauchbar."""


def pruefen_profil(daten: dict) -> dict:
    """Prüft ein Sprachprofil, bevor es gespeichert wird.

    Ein unbrauchbares Profil fällt sonst erst beim Lernen auf — und dann ist
    schon ein Bestand damit angelegt. Also hier, wo es noch folgenlos ist.
    """
    if not isinstance(daten, dict):
        raise ProfilFehler("Das Profil muss ein Objekt sein")
    unbekannt = set(daten) - ERLAUBTE_SCHLUESSEL
    if unbekannt:
        raise ProfilFehler(
            f"Unbekannte Einträge: {', '.join(sorted(unbekannt))}. "
            f"Erlaubt: {', '.join(sorted(ERLAUBTE_SCHLUESSEL))}")

    pr = daten.get("pruefung")
    if pr is not None:
        if not isinstance(pr, dict):
            raise ProfilFehler("pruefung muss ein Objekt sein")
        for feld, moeglich in (("gross_klein", {"ignorieren", "beachten"}),
                               ("diakritika", {"streng", "hinweis", "ignorieren"}),
                               ("satzzeichen", {"ignorieren", "beachten"})):
            if feld in pr and pr[feld] not in moeglich:
                raise ProfilFehler(
                    f"pruefung.{feld} muss eines sein von: "
                    f"{', '.join(sorted(moeglich))}")
        regeln = pr.get("schriftregeln", [])
        if not isinstance(regeln, list):
            raise ProfilFehler("pruefung.schriftregeln muss eine Liste sein")
        bekannt = {"griechisch", "deutsch", "mittelhochdeutsch"}
        for r in regeln:
            if r not in bekannt:
                raise ProfilFehler(
                    f"Unbekannte Schriftregel {r!r}. Bekannt: "
                    f"{', '.join(sorted(bekannt))}. Neue Regeln brauchen eine "
                    f"Ergänzung in pruefung.py — Zeichenersetzungen lassen sich "
                    f"nicht als Daten ausdrücken.")

    art = daten.get("artikel")
    if art is not None:
        if not isinstance(art, dict):
            raise ProfilFehler("artikel muss ein Objekt sein")
        if art.get("regel") not in (None, "optional_aber_richtig", "verlangt",
                                    "ignorieren"):
            raise ProfilFehler("artikel.regel muss optional_aber_richtig, "
                               "verlangt oder ignorieren sein")

    gruppen = daten.get("formgruppen")
    if gruppen is not None:
        if not isinstance(gruppen, dict):
            raise ProfilFehler("formgruppen muss nach Wortart gegliedert sein")
        for wortart, liste in gruppen.items():
            if wortart not in WORTARTEN:
                raise ProfilFehler(
                    f"Unbekannte Wortart {wortart!r}. Erlaubt: "
                    f"{', '.join(sorted(WORTARTEN))}")
            if not isinstance(liste, list):
                raise ProfilFehler(f"formgruppen.{wortart} muss eine Liste sein")
            kennungen = set()
            for g in liste:
                _pruefen_gruppe(wortart, g, kennungen)

    zeichen = daten.get("sonderzeichen")
    if zeichen is not None:
        if not isinstance(zeichen, list) or any(not isinstance(z, str) or len(z) > 4
                                                for z in zeichen):
            raise ProfilFehler("sonderzeichen muss eine Liste kurzer "
                               "Zeichenketten sein")

    standard = daten.get("formgruppen_standard")
    if standard is not None and not isinstance(standard, dict):
        raise ProfilFehler("formgruppen_standard muss nach Wortart gegliedert sein")

    return daten


def _pruefen_gruppe(wortart: str, g: dict, kennungen: set) -> None:
    if not isinstance(g, dict):
        raise ProfilFehler(f"Formgruppe in {wortart} ist kein Objekt")
    for feld in ("kennung", "name", "merkmale", "zellen"):
        if feld not in g:
            raise ProfilFehler(
                f"Formgruppe in {wortart}: {feld!r} fehlt. Eine Gruppe braucht "
                f"kennung, name, merkmale (was alle Zellen gemeinsam haben) "
                f"und zellen (die einzelnen Merkmalsbündel).")
    if g["kennung"] in kennungen:
        raise ProfilFehler(f"Kennung {g['kennung']!r} kommt in {wortart} doppelt vor")
    kennungen.add(g["kennung"])
    if not isinstance(g["zellen"], list) or not g["zellen"]:
        raise ProfilFehler(f"Formgruppe {g['kennung']!r}: zellen fehlen")
    try:
        pruefen_merkmale(g["merkmale"])
        for zelle in g["zellen"]:
            pruefen_merkmale(zelle)
    except MerkmalFehler as fehler:
        raise ProfilFehler(f"Formgruppe {g['kennung']!r}: {fehler}") from fehler
    # Jede Zelle muss die Gruppenmerkmale tragen — sonst findet die
    # Beschriftung ihre Gruppe nicht wieder.
    for zelle in g["zellen"]:
        for d, w in g["merkmale"].items():
            if str(zelle.get(d)) != str(w):
                raise ProfilFehler(
                    f"Formgruppe {g['kennung']!r}: die Zelle {zelle} trägt "
                    f"{d}={zelle.get(d)!r}, die Gruppe verlangt {w!r}. Jede "
                    f"Zelle muss die gemeinsamen Merkmale der Gruppe haben.")
