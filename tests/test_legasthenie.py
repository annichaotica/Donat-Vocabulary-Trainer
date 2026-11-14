import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "backend"))

import legasthenie as lg


def art(eingabe, ziel):
    e = lg.fehler_benennen(eingabe, ziel)
    return e["art"] if e else None


# ------------------------------------------------------------ Fehler benennen

def test_vertauschte_nachbarn():
    e = lg.fehler_benennen("frsit", "frist")
    assert e["art"] == "umgestellt"
    assert "Reihenfolge" in e["text"]


def test_ei_statt_ie():
    # Greift schon die Nachbarvertauschung, ist das recht: sie benennt die
    # Buchstaben einzeln und ist damit die genauere Auskunft.
    e = lg.fehler_benennen("Freind", "Friend")
    assert e["art"] in ("umgestellt", "umgestellt_gruppe")
    assert "Reihenfolge" in e["text"] or "ie" in e["text"]


def test_umgestellte_gruppe_wenn_nicht_benachbart():
    e = lg.fehler_benennen("Liebe", "Leibe")
    assert e is not None
    assert "umgestellt" in e["art"]


def test_gestaltverwechslung_b_und_d():
    e = lg.fehler_benennen("bas", "das")
    assert e["art"] == "gestalt_verwechselt"
    assert "ähnlich" in e["text"]


def test_gestaltverwechslung_m_und_w():
    assert art("Masser", "Wasser") == "gestalt_verwechselt"


def test_klangverwechslung():
    e = lg.fehler_benennen("Tach", "Dach")
    assert e["art"] == "klang_verwechselt"
    assert "geschrieben" in e["text"]


def test_doppelung_fehlt():
    e = lg.fehler_benennen("komen", "kommen")
    assert e["art"] == "doppelung_zuwenig"
    assert "mm" in e["text"]


def test_doppelung_zuviel():
    e = lg.fehler_benennen("kammen", "kamen")
    assert e["art"] == "doppelung_zuviel"


def test_fehlender_buchstabe():
    assert art("Blme", "Blume") in ("ausgelassen", "vokal")


def test_vokalfehler():
    e = lg.fehler_benennen("Hond", "Hund")
    assert e["art"] == "vokal"
    assert "Selbstlaut" in e["text"]


def test_zu_grosse_abweichung_wird_nicht_benannt():
    assert lg.fehler_benennen("xyzabc", "Wasser") is None


def test_gleiche_eingabe_ist_kein_fehler():
    assert lg.fehler_benennen("Wasser", "Wasser") is None
    assert lg.fehler_benennen("wasser", "Wasser") is None


# --------------------------------------------------------------- Zerlegen

def test_stamm_aus_dem_paradigma():
    # Der eigentliche Gewinn: der Stamm wird abgeleitet, nicht geraten.
    assert lg.stamm(["parle", "parles", "parlons", "parlez", "parlent"]) == "parl"


def test_stamm_bei_unregelmaessigem_verb_leer():
    assert lg.stamm(["vais", "allons", "irai"]) == ""


def test_stamm_braucht_mindestens_zwei_formen():
    assert lg.stamm(["parle"]) == ""


def test_teilen_in_stamm_und_endung():
    assert lg.teilen("parlions", "parl") == ["parl", "ions"]
    assert lg.teilen("vais", "parl") == ["vais"]


def test_silben_deutsch():
    assert lg.silben("Wasser") == ["Was", "ser"]
    assert lg.silben("Blume") == ["Blu", "me"]
    assert lg.silben("sehen") == ["se", "hen"]


def test_silben_digraph_bleibt_zusammen():
    assert lg.silben("waschen") == ["wa", "schen"]


def test_silben_kurzes_wort_bleibt_ganz():
    assert lg.silben("und") == ["und"]
    assert lg.silben("") == []


def test_maske_stufenweise():
    assert lg.maske("parlons", 0) == "_ _ _ _ _ _ _"
    assert lg.maske("parlons", 1).startswith("p _")
    assert lg.maske("parlons", 2) == "p _ _ _ _ _ s"
    assert lg.maske("parlons", 3) == "p _ r l _ n s"


# ------------------------------------------- Stamm bei wanderndem Augment

def test_stamm_trotz_wanderndem_augment():
    """Im griechischen Aorist tritt das Augment nur in einigen Zellen vor den
    Stamm: έγραψα, aber γράψαμε. Einen gemeinsamen Anfang über alle sechs
    Formen gibt es darum nicht — einen gemeinsamen Stamm aber sehr wohl."""
    aorist = ["έγραψα", "έγραψες", "έγραψε", "γράψαμε", "γράψατε", "έγραψαν"]
    assert lg.stamm(aorist) == "γραψ"


def test_stamm_trotz_wanderndem_akzent():
    # γρά gegen γρα — derselbe Stamm, verschobene Betonung.
    assert lg.stamm(["γράφω", "γράφεις", "γράφουμε"]) == "γράφ"


def test_teilen_laesst_augment_zu():
    assert lg.teilen("γράψαμε", "γραψ") == ["γράψ", "αμε"]
    assert lg.teilen("έγραψα", "γραψ") == ["έγραψ", "α"]


def test_teilen_ohne_treffer_bleibt_ganz():
    assert lg.teilen("vais", "parl") == ["vais"]


def test_stamm_mit_partikel():
    futur = ["θα γράψω", "θα γράψεις", "θα γράψουμε"]
    assert lg.stamm(futur).startswith("θα γράψ")
