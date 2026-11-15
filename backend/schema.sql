-- Vokabeltrainer, Datenbankschema.
-- Grundgedanke: ein Lexem hat FORMEN (mit Merkmalen beschrieben) und
-- BEDEUTUNGEN (mit beliebig vielen gültigen Übersetzungen). Abgefragt und
-- terminiert wird nicht das Lexem, sondern jede einzelne AUFGABE darüber.

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS schema_stand (
    version INTEGER NOT NULL
);

-- ---------------------------------------------------------------- Sprachen

CREATE TABLE IF NOT EXISTS sprache (
    code         TEXT PRIMARY KEY,              -- 'fr', 'es', 'en', 'el', 'de'
    name         TEXT NOT NULL,
    schrift      TEXT NOT NULL DEFAULT 'latein',
    stimme       TEXT,                          -- BCP47 für Sprachsynthese
    profil       TEXT NOT NULL DEFAULT '{}'     -- JSON, siehe sprachen.py
);

-- --------------------------------------------------------------- Benutzer

CREATE TABLE IF NOT EXISTS benutzer (
    id             INTEGER PRIMARY KEY,
    name           TEXT NOT NULL UNIQUE,
    -- Von Cloudflare Access geprüfte Mailadresse. Nur gesetzt bei Profilen,
    -- die von außen hereinkommen; im Heimnetz bleibt sie leer und man wählt
    -- sein Profil wie bisher aus der Liste.
    email          TEXT UNIQUE,
    farbe          TEXT NOT NULL DEFAULT '#6b7fd7',
    einstellungen  TEXT NOT NULL DEFAULT '{}',
    -- Darf Sprachprofile ändern und neue Sprachen einrichten. Das wirkt auf
    -- den ganzen Bestand, auch auf fremde Sammlungen — ein eingeladener Gast
    -- soll das nicht können. Die erste angelegte Person bekommt es.
    verwalter      INTEGER NOT NULL DEFAULT 0,
    angelegt       TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Zugangsmerkmale für die MCP-Schnittstelle, je Person eines.
--
-- Ein gemeinsames Geheimnis wäre hier falsch: man könnte nicht sagen, wer
-- etwas eingetragen hat, und man könnte es niemandem einzeln entziehen.
-- Gespeichert wird nur der Streuwert — das Geheimnis selbst sieht der Server
-- nach der Ausgabe nie wieder.
CREATE TABLE IF NOT EXISTS mcp_token (
    id              INTEGER PRIMARY KEY,
    benutzer_id     INTEGER NOT NULL REFERENCES benutzer(id) ON DELETE CASCADE,
    name            TEXT NOT NULL,           -- wofür, z.B. "Claude-App iPad"
    streuwert       TEXT NOT NULL UNIQUE,    -- sha256 des Geheimnisses
    anfang          TEXT NOT NULL,           -- erste Zeichen, zum Wiedererkennen
    angelegt        TEXT NOT NULL DEFAULT (datetime('now')),
    zuletzt_benutzt TEXT,
    aktiv           INTEGER NOT NULL DEFAULT 1
);
CREATE INDEX IF NOT EXISTS idx_mcp_token_benutzer ON mcp_token(benutzer_id);

-- --------------------------------------------------------------- Sammlungen

CREATE TABLE IF NOT EXISTS sammlung (
    id            INTEGER PRIMARY KEY,
    besitzer_id   INTEGER NOT NULL REFERENCES benutzer(id) ON DELETE CASCADE,
    name          TEXT NOT NULL,
    sprache       TEXT NOT NULL REFERENCES sprache(code),
    grundsprache  TEXT NOT NULL DEFAULT 'de' REFERENCES sprache(code),
    beschreibung  TEXT,
    -- JSON. Wichtigster Eintrag: "formgruppen" — welche Zeiten und Tabellen
    -- überhaupt abgefragt werden. Ohne diese Auswahl entstünden pro
    -- französischem Verb an die zweihundert Aufgaben.
    einstellungen TEXT NOT NULL DEFAULT '{}',
    angelegt      TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_sammlung_besitzer ON sammlung(besitzer_id);

-- Freigabe einer Sammlung an ein anderes Profil. Der Lernstand bleibt
-- trotzdem persönlich: er hängt an (aufgabe, benutzer), nicht an der Sammlung.
CREATE TABLE IF NOT EXISTS freigabe (
    sammlung_id  INTEGER NOT NULL REFERENCES sammlung(id) ON DELETE CASCADE,
    benutzer_id  INTEGER NOT NULL REFERENCES benutzer(id) ON DELETE CASCADE,
    recht        TEXT NOT NULL CHECK (recht IN ('lesen', 'schreiben')),
    PRIMARY KEY (sammlung_id, benutzer_id)
);

-- Lerne ich diese Sammlung, oder sehe ich sie nur?
--
-- Das waren bisher dieselbe Sache, und das war falsch: eine Freigabe
-- heißt »du darfst hineinsehen und mitpflegen«, nicht »das lernst du«.
-- Wer ein fremdes Französisch berichtigt, bekam es in der
-- allgemeinen Abfrage zwischen die griechischen Wörter gemischt.
--
-- Hier stehen nur die ABWEICHUNGEN von der Vorgabe. Die Vorgabe
-- ergibt sich aus dem Besitz: die eigenen Sammlungen lernt man, die
-- fremden nicht. Eine Zeile hier dreht das für ein Profil um. Dadurch
-- braucht keine neue Sammlung und keine neue Freigabe einen
-- Begleiteintrag, und es gibt keinen Zustand, der nachlaufen kann.
CREATE TABLE IF NOT EXISTS lernwahl (
    benutzer_id  INTEGER NOT NULL REFERENCES benutzer(id) ON DELETE CASCADE,
    sammlung_id  INTEGER NOT NULL REFERENCES sammlung(id) ON DELETE CASCADE,
    lernen       INTEGER NOT NULL CHECK (lernen IN (0, 1)),
    PRIMARY KEY (benutzer_id, sammlung_id)
);

CREATE TABLE IF NOT EXISTS lektion (
    id           INTEGER PRIMARY KEY,
    sammlung_id  INTEGER NOT NULL REFERENCES sammlung(id) ON DELETE CASCADE,
    -- Die Nummer im Lehrwerk. Sie ist der Schlüssel, unter dem ein Import
    -- seine Lektion wiederfindet — der Name darf sich ändern, die Nummer
    -- nicht. Ohne sie ließe sich "bis Lektion 12" nicht abfragen.
    nr           INTEGER,
    name         TEXT NOT NULL,
    beschreibung TEXT,
    reihenfolge  INTEGER NOT NULL DEFAULT 0
);
-- Der Index auf nr steht in datenbank.py bei der Wanderung, nicht hier:
-- in einer bestehenden Datenbank ist CREATE TABLE IF NOT EXISTS wirkungslos,
-- die Spalte kommt erst durch ALTER TABLE — ein Index hier liefe zu früh.
CREATE INDEX IF NOT EXISTS idx_lektion_sammlung ON lektion(sammlung_id);

-- ------------------------------------------------------------------ Lexeme

CREATE TABLE IF NOT EXISTS lexem (
    id           INTEGER PRIMARY KEY,
    sammlung_id  INTEGER NOT NULL REFERENCES sammlung(id) ON DELETE CASCADE,
    lektion_id   INTEGER REFERENCES lektion(id) ON DELETE SET NULL,
    lemma        TEXT NOT NULL,
    wortart      TEXT NOT NULL,
    -- Lernreihenfolge innerhalb der Lektion. Neues wird in dieser Folge
    -- eingeführt, nicht nach Zufall oder Eingabedatum.
    reihenfolge  INTEGER NOT NULL DEFAULT 0,
    -- ERKLÄRTE LÜCKEN: Merkmalsmuster für Zellen, die es bei diesem Wort
    -- nicht gibt. Eine Zelle gilt als erklärt leer, wenn eines der Muster
    -- in ihr enthalten ist. Beispiele:
    --   unpersönlich (πρέπει, βρέχει): [{"person":"1"},{"person":"2"}]
    --   ohne Aorist (είμαι, ξέρω):     [{"tempus":"aorist"}]
    --   nur Plural (τα μεσάνυχτα):     [{"numerus":"sg"}]
    --   unveränderlich (το ταξί, μπλε): [{}]  — das leere Muster passt überall
    -- Erklärte Lücken gelten nicht als Mangel und stören die Stammerkennung
    -- nicht. Ohne sie meldete der Trainer bei jedem dritten griechischen
    -- Wort einen Fehler, den es nicht gibt.
    luecken      TEXT NOT NULL DEFAULT '[]',
    -- Stamm je Formgruppe, von Hand gesetzt. Überschreibt die Ableitung
    -- aus den Formen — nötig, wo die nicht trägt.
    staemme      TEXT NOT NULL DEFAULT '{}',
    -- Kennung aus der Quelle, falls es eine gibt. Sie entscheidet beim
    -- wiederholten Import, ob ein Eintrag derselbe ist. Ohne sie dient
    -- lemma + wortart als Schlüssel — was bei Gleichlautern (φορά "Mal"
    -- und "er trägt") nicht reicht, darum diese Ausweichmöglichkeit.
    kennung      TEXT,
    -- lexemfeste Merkmale, z.B. {"genus": "f"} beim Substantiv,
    -- {"klasse": "er", "hilfsverb": "etre"} beim französischen Verb
    merkmale     TEXT NOT NULL DEFAULT '{}',
    notiz        TEXT,
    angelegt     TEXT NOT NULL DEFAULT (datetime('now')),
    geaendert    TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_lexem_sammlung ON lexem(sammlung_id);
CREATE INDEX IF NOT EXISTS idx_lexem_lektion  ON lexem(lektion_id);
CREATE INDEX IF NOT EXISTS idx_lexem_lemma    ON lexem(sammlung_id, lemma);
-- idx_lexem_folge und idx_lexem_kennung ebenfalls in der Wanderung.

-- Eine Wortform mit ihrem Merkmalsbündel.
-- quelle/geprueft: generierte oder von der KI ergänzte Formen werden erst
-- abgefragt, wenn sie bestätigt sind.
CREATE TABLE IF NOT EXISTS form (
    id            INTEGER PRIMARY KEY,
    lexem_id      INTEGER NOT NULL REFERENCES lexem(id) ON DELETE CASCADE,
    text          TEXT NOT NULL,
    merkmale      TEXT NOT NULL DEFAULT '{}',
    ist_grundform INTEGER NOT NULL DEFAULT 0,
    -- Nebenform derselben Zelle: μιλάω neben μιλώ, είστε neben είσαστε.
    -- Beide gelten als richtig; gefragt und für die Stammerkennung benutzt
    -- wird die Hauptform.
    ist_variante  INTEGER NOT NULL DEFAULT 0,
    aussprache    TEXT,                       -- IPA
    audio         TEXT,                       -- Dateipfad eigener Aufnahme
    quelle        TEXT NOT NULL DEFAULT 'manuell'
                  CHECK (quelle IN ('manuell','generiert','wiktionary','ki','import')),
    geprueft      INTEGER NOT NULL DEFAULT 1,
    notiz         TEXT
);
CREATE INDEX IF NOT EXISTS idx_form_lexem ON form(lexem_id);

-- ------------------------------------------------------------- Bedeutungen

CREATE TABLE IF NOT EXISTS bedeutung (
    id           INTEGER PRIMARY KEY,
    lexem_id     INTEGER NOT NULL REFERENCES lexem(id) ON DELETE CASCADE,
    reihenfolge  INTEGER NOT NULL DEFAULT 0,
    kontext      TEXT,            -- Unterscheidung, z.B. "Geldinstitut"
    notiz        TEXT
);
CREATE INDEX IF NOT EXISTS idx_bedeutung_lexem ON bedeutung(lexem_id);

-- Mehrere gültige Übersetzungen je Bedeutung sind der Normalfall.
CREATE TABLE IF NOT EXISTS uebersetzung (
    id            INTEGER PRIMARY KEY,
    bedeutung_id  INTEGER NOT NULL REFERENCES bedeutung(id) ON DELETE CASCADE,
    sprache       TEXT NOT NULL,
    text          TEXT NOT NULL,
    ist_haupt     INTEGER NOT NULL DEFAULT 0,
    quelle        TEXT NOT NULL DEFAULT 'manuell',
    geprueft      INTEGER NOT NULL DEFAULT 1
);
CREATE INDEX IF NOT EXISTS idx_uebersetzung_bedeutung ON uebersetzung(bedeutung_id);

CREATE TABLE IF NOT EXISTS beispiel (
    id              INTEGER PRIMARY KEY,
    lexem_id        INTEGER NOT NULL REFERENCES lexem(id) ON DELETE CASCADE,
    bedeutung_id    INTEGER REFERENCES bedeutung(id) ON DELETE SET NULL,
    satz            TEXT NOT NULL,
    uebersetzung    TEXT,
    luecke_form_id  INTEGER REFERENCES form(id) ON DELETE SET NULL,
    quelle          TEXT NOT NULL DEFAULT 'manuell'
);
CREATE INDEX IF NOT EXISTS idx_beispiel_lexem ON beispiel(lexem_id);

-- ----------------------------------------------------------------- Aufgaben

-- Aufgaben werden aus den Daten ERZEUGT, nicht von Hand gepflegt.
-- schluessel ist deterministisch (typ:lexem:zielart:zielid) und verhindert
-- Doppelte bei erneutem Erzeugen.
CREATE TABLE IF NOT EXISTS aufgabe (
    id          INTEGER PRIMARY KEY,
    lexem_id    INTEGER NOT NULL REFERENCES lexem(id) ON DELETE CASCADE,
    typ         TEXT NOT NULL,
    ziel_art    TEXT,                   -- 'bedeutung' | 'form' | 'lexem'
    ziel_id     INTEGER,
    schluessel  TEXT NOT NULL UNIQUE,
    -- Zu welcher Formgruppe (Zeit, Fall-Tabelle) gehört diese Aufgabe?
    -- NULL bei allem, was keine Form abfragt: Bedeutung, Genus.
    --
    -- Steht hier MIT, obwohl sie sich aus Merkmalsbündel und
    -- Sprachprofil errechnen ließe — und genau deshalb: errechnen geht
    -- nur in Python, und dann müsste die Abfrage hinterher aussieben,
    -- was sie gerade erst in einem Fenster zusammengesucht hat. Das ist
    -- die Fehlerfamilie, die hier schon mehrfach zugeschlagen hat. Die
    -- Bedingung gehört in die Abfrage.
    formgruppe  TEXT,
    aktiv       INTEGER NOT NULL DEFAULT 1
);
CREATE INDEX IF NOT EXISTS idx_aufgabe_lexem ON aufgabe(lexem_id);
CREATE INDEX IF NOT EXISTS idx_aufgabe_typ   ON aufgabe(typ);

-- Ab welcher Lektion ist eine Formgruppe im Lehrwerk eingeführt?
--
-- »Bei den Anfängerkapiteln, die ich mir gerade ansehe, habe ich noch
-- gar nicht alle Zeitformen gelernt.« — Gemessen: von 6971
-- Formaufgaben im griechischen Bestand waren 832 Präsens und rund 2900
-- Aorist, Futur und Passiv. Alles lag im selben Topf, aus dem die
-- Tagesdosis zieht.
--
-- Die Lektionsnamen sagen es selbst — »39 Aorist I«, »40 Konjunktiv
-- und Futur«, »45 Passiv Präsens«. Damit lässt sich die Schranke an
-- den Lehrgang binden, statt sie von Hand nachzuziehen: wer bei
-- Lektion 20 steht, bekommt keinen Aorist, und wenn er bei 39 ankommt,
-- kommt der Aorist von selbst.
--
-- Je Sammlung, nicht je Person: wann das Buch etwas einführt, ist eine
-- Eigenschaft des Lehrwerks. Wo die einzelne Person steht, steht in
-- `buchstand`.
CREATE TABLE IF NOT EXISTS formgruppe_lektion (
    sammlung_id INTEGER NOT NULL REFERENCES sammlung(id) ON DELETE CASCADE,
    formgruppe  TEXT NOT NULL,
    ab_lektion  INTEGER NOT NULL,
    PRIMARY KEY (sammlung_id, formgruppe)
);

-- Wo stehe ich in diesem Lehrwerk?
--
-- Eine einzige Zahl, und sie gehört der Person: zwei Leute lernen
-- dasselbe Buch verschieden schnell. Ohne Eintrag gilt keine Schranke
-- — wer nichts einstellt, bekommt alles wie bisher. Das ist Absicht:
-- eine Schranke, die ungefragt zuschlägt, nimmt Stoff weg, den jemand
-- vielleicht gerade üben will.
CREATE TABLE IF NOT EXISTS buchstand (
    benutzer_id  INTEGER NOT NULL REFERENCES benutzer(id) ON DELETE CASCADE,
    sammlung_id  INTEGER NOT NULL REFERENCES sammlung(id) ON DELETE CASCADE,
    bis_lektion  INTEGER NOT NULL,
    PRIMARY KEY (benutzer_id, sammlung_id)
);

-- ---------------------------------------------------------------- Lernstand

CREATE TABLE IF NOT EXISTS lernzustand (
    aufgabe_id           INTEGER NOT NULL REFERENCES aufgabe(id) ON DELETE CASCADE,
    benutzer_id          INTEGER NOT NULL REFERENCES benutzer(id) ON DELETE CASCADE,
    zustand              TEXT NOT NULL DEFAULT 'neu'
                         CHECK (zustand IN ('neu','lernen','reif','verlernt','ausgesetzt')),
    stabilitaet          REAL,
    schwierigkeit        REAL,
    letzte_wiederholung  TEXT,
    faellig              TEXT,            -- Datum, ISO
    anzahl               INTEGER NOT NULL DEFAULT 0,
    anzahl_fehler        INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (aufgabe_id, benutzer_id)
);
CREATE INDEX IF NOT EXISTS idx_lernzustand_faellig
    ON lernzustand(benutzer_id, faellig);
CREATE INDEX IF NOT EXISTS idx_lernzustand_zustand
    ON lernzustand(benutzer_id, zustand);

-- Protokoll. Wird nie gelöscht: erlaubt spätere Optimierung der
-- FSRS-Parameter auf das eigene Lernverhalten.
CREATE TABLE IF NOT EXISTS wiederholung (
    id                 INTEGER PRIMARY KEY,
    aufgabe_id         INTEGER NOT NULL REFERENCES aufgabe(id) ON DELETE CASCADE,
    benutzer_id        INTEGER NOT NULL REFERENCES benutzer(id) ON DELETE CASCADE,
    zeitpunkt          TEXT NOT NULL,
    bewertung          INTEGER NOT NULL CHECK (bewertung BETWEEN 1 AND 4),
    antwort            TEXT,
    urteil             TEXT,           -- richtig | fast | falsch | aufgedeckt
    dauer_ms           INTEGER,        -- gesamt, inkl. Tippen
    -- Zeit bis zum ERSTEN Tastendruck. Das ist das Abrufmaß; die Gesamtzeit
    -- misst zu großen Teilen Tippgeschwindigkeit und Wortlänge mit.
    denkzeit_ms        INTEGER,
    versuche           INTEGER NOT NULL DEFAULT 1,
    -- Wie kam die Bewertung zustande: automatisch oder von Hand gesetzt?
    bewertung_quelle   TEXT NOT NULL DEFAULT 'automatisch',
    stabilitaet_vor    REAL,
    stabilitaet_nach   REAL,
    schwierigkeit_vor  REAL,
    schwierigkeit_nach REAL,
    intervall_tage     REAL,
    verstrichen_tage   REAL
);
CREATE INDEX IF NOT EXISTS idx_wiederholung_aufgabe
    ON wiederholung(benutzer_id, aufgabe_id, zeitpunkt);
CREATE INDEX IF NOT EXISTS idx_wiederholung_zeit
    ON wiederholung(benutzer_id, zeitpunkt);

-- ======================================================================
-- Textebene: echtes Textverständnis nach dem Pauken.
--
-- Vorbereitet, noch nicht in Betrieb (Stufe 4). Die Tabellen stehen jetzt
-- hier, damit später keine Datenbankwanderung nötig ist.
--
-- Der Gedanke: ein Text wird in Abschnitte zerlegt (meist Sätze) — das ist
-- die Einheit, an der gearbeitet wird. Jeder Abschnitt kann eine
-- Referenzübersetzung haben. Über text_lexem hängt der Text an den Vokabeln,
-- die in ihm vorkommen; damit lässt sich beides beantworten: "übe die
-- Vokabeln zu diesem Text" und "welchen Text kann ich mit meinem
-- Wortschatz schon lesen".
-- ======================================================================

-- Ein einzelner Übungssatz ist derselbe Gegenstand wie ein ganzer Text, nur
-- mit einem Abschnitt. Darum keine zweite Tabelle daneben: der Lernstand
-- soll nicht auf zwei Orte zerfallen, und text_lexem braucht auch der Satz.
--
-- typ           satz | text | dialog | brief | zeitungsstil
-- richtungen    JSON-Liste, z. B. ["el-de", "de-el"]: in welche Richtungen
--               geübt wird. Daraus entstehen die Textaufgaben.
-- quelle        WER es geschrieben hat.
-- verweis_*     WORAUF es sich stützt. Ein fremder Zeitungsartikel wird
--               verlinkt und nicht abgeschrieben; beides ist unabhängig,
--               ein KI-Text kann sich auf eine Quelle stützen.
-- geprueft      wie bei den Formen: bis ein Mensch freigibt, wird nicht
--               abgefragt.
-- kennung       Schlüssel des Lehrwerks, damit ein erneuter Import
--               aktualisiert statt zu verdoppeln.
CREATE TABLE IF NOT EXISTS text (
    id            INTEGER PRIMARY KEY,
    sammlung_id   INTEGER NOT NULL REFERENCES sammlung(id) ON DELETE CASCADE,
    lektion_id    INTEGER REFERENCES lektion(id) ON DELETE SET NULL,
    titel         TEXT NOT NULL,
    sprache       TEXT NOT NULL REFERENCES sprache(code),
    inhalt        TEXT NOT NULL,          -- der Text im Ganzen
    uebersetzung  TEXT,                   -- Referenzübersetzung im Ganzen
    niveau        TEXT,                   -- A1 … C2, frei
    quelle        TEXT NOT NULL DEFAULT 'manuell'
                  CHECK (quelle IN ('manuell','import','ki','wiktionary')),
    notiz         TEXT,
    angelegt      TEXT NOT NULL DEFAULT (datetime('now')),
    -- Die folgenden Spalten kamen später dazu. Sie stehen ZUSÄTZLICH in
    -- NACHRUESTEN (datenbank.py): dort für bestehende Bestände, hier
    -- damit eine frische Datenbank sie gleich mitbringt und wer das
    -- Schema liest die ganze Tabelle sieht. Vorher fehlte hier die
    -- halbe Tabelle, während der Kommentarblock darüber sie beschrieb.
    typ           TEXT NOT NULL DEFAULT 'satz',
    richtungen    TEXT,                   -- JSON: ["el-de","de-el"]
    verweis_titel TEXT,                   -- fremde Texte werden verlinkt,
    verweis_url   TEXT,                   -- nicht abgeschrieben
    geprueft      INTEGER NOT NULL DEFAULT 0,
    kennung       TEXT,                   -- stabil fürs Wiederfinden
    reihenfolge   INTEGER NOT NULL DEFAULT 0,
    geaendert     TEXT
);
CREATE INDEX IF NOT EXISTS idx_text_sammlung ON text(sammlung_id);

-- Die Arbeitseinheit: ein Satz oder ein Absatz.
-- varianten / referenz_varianten: weitere gültige Fassungen desselben
-- Abschnitts (Εχθές neben Χθες, "bin ich gegangen" neben "ging ich").
-- Jede zählt als richtig — sonst wäre eine richtige Übersetzung falsch,
-- nur weil sie nicht die aufgeschriebene ist.
CREATE TABLE IF NOT EXISTS textabschnitt (
    id            INTEGER PRIMARY KEY,
    text_id       INTEGER NOT NULL REFERENCES text(id) ON DELETE CASCADE,
    reihenfolge   INTEGER NOT NULL DEFAULT 0,
    original      TEXT NOT NULL,
    referenz      TEXT,                   -- Referenzübersetzung des Abschnitts
    notiz         TEXT,
    varianten          TEXT,              -- JSON-Liste
    referenz_varianten TEXT
);
CREATE INDEX IF NOT EXISTS idx_textabschnitt_text ON textabschnitt(text_id, reihenfolge);

-- Welche Vokabeln kommen in diesem Text vor? Wird beim Einpflegen ermittelt
-- (über den MCP-Server oder beim Import) und macht den Text mit dem
-- Wortschatz verrechenbar.
CREATE TABLE IF NOT EXISTS text_lexem (
    text_id     INTEGER NOT NULL REFERENCES text(id) ON DELETE CASCADE,
    lexem_id    INTEGER NOT NULL REFERENCES lexem(id) ON DELETE CASCADE,
    form_id     INTEGER REFERENCES form(id) ON DELETE SET NULL,
    abschnitt_id INTEGER REFERENCES textabschnitt(id) ON DELETE CASCADE,
    PRIMARY KEY (text_id, lexem_id, abschnitt_id)
);
CREATE INDEX IF NOT EXISTS idx_text_lexem_lexem ON text_lexem(lexem_id);

-- Mein eigener Übersetzungsversuch zu einem Abschnitt.
--
-- Getrennt von `textabschnitt.referenz`: das ist die Musterlösung und
-- gehört zum Text, das hier gehört zu mir. Zwei Leute können denselben
-- Text übersetzen, ohne sich zu überschreiben.
--
-- Es wird beim Tippen gesichert, nicht beim Abschicken — wer eine halbe
-- Stunde an einem Absatz sitzt und dann den Reiter schließt, soll nicht
-- von vorn anfangen.
CREATE TABLE IF NOT EXISTS uebersetzungsversuch (
    abschnitt_id INTEGER NOT NULL REFERENCES textabschnitt(id) ON DELETE CASCADE,
    benutzer_id  INTEGER NOT NULL REFERENCES benutzer(id) ON DELETE CASCADE,
    fassung      TEXT NOT NULL DEFAULT '',
    geaendert    TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (abschnitt_id, benutzer_id)
);

-- Wörter, die ich noch nicht kenne und eingetragen haben möchte.
--
-- Der Übergabepunkt an die angebundene KI: sie liest hier, was offen
-- ist, legt die Vokabeln an und hakt ab. Absichtlich NICHT an den Text
-- gebunden — ein Wort, das einem beim Lesen auffällt, ist dasselbe
-- Wort, das einem in der Zeitung auffällt. `text_id` und
-- `zusammenhang` sind Beigaben, damit die KI die Form im Satz sieht
-- und nicht raten muss, welche Bedeutung gemeint ist.
--
-- `wort` ist die SCHREIBWEISE aus dem Text, `vergleichsform` die
-- normierte Fassung. Nur letztere ist eindeutig — sonst stünde
-- dasselbe Wort zweimal in der Liste, einmal am Satzanfang groß.
CREATE TABLE IF NOT EXISTS wortwunsch (
    id            INTEGER PRIMARY KEY,
    benutzer_id   INTEGER NOT NULL REFERENCES benutzer(id) ON DELETE CASCADE,
    sammlung_id   INTEGER NOT NULL REFERENCES sammlung(id) ON DELETE CASCADE,
    wort          TEXT NOT NULL,
    vergleichsform TEXT NOT NULL,
    zusammenhang  TEXT,
    text_id       INTEGER REFERENCES text(id) ON DELETE SET NULL,
    erledigt      INTEGER NOT NULL DEFAULT 0,
    lexem_id      INTEGER REFERENCES lexem(id) ON DELETE SET NULL,
    angelegt      TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE (benutzer_id, sammlung_id, vergleichsform)
);
CREATE INDEX IF NOT EXISTS idx_wortwunsch_offen
    ON wortwunsch(sammlung_id, erledigt);

-- Aufgaben zum Text. Getrennt von `aufgabe` gehalten, weil hier nicht eine
-- einzelne Form geprüft wird, sondern freier Text.
--
-- typ:
--   uebersetzung_hin    Abschnitt in die Grundsprache übersetzen
--   uebersetzung_rueck  Abschnitt in die Lernsprache übersetzen
--   verstaendnis        Frage zum Inhalt
--   lueckentext         Lücke im Abschnitt füllen (Antwort prüfbar)
--
-- bewertung_art — der Kern des Problems: eine freie Übersetzung lässt sich
-- nicht per Zeichenkettenvergleich bewerten.
--   selbst    Referenzübersetzung aufdecken, selbst einschätzen
--   ki        Rückmeldung über den MCP-Server einholen
--   genau     prüfbare Antwort (Lückentext, Auswahlfrage)
CREATE TABLE IF NOT EXISTS textaufgabe (
    id             INTEGER PRIMARY KEY,
    text_id        INTEGER NOT NULL REFERENCES text(id) ON DELETE CASCADE,
    abschnitt_id   INTEGER REFERENCES textabschnitt(id) ON DELETE CASCADE,
    typ            TEXT NOT NULL,
    bewertung_art  TEXT NOT NULL DEFAULT 'selbst'
                   CHECK (bewertung_art IN ('selbst','ki','genau')),
    frage          TEXT,
    erwartet       TEXT NOT NULL DEFAULT '[]',   -- JSON-Liste gültiger Antworten
    schluessel     TEXT NOT NULL UNIQUE,
    aktiv          INTEGER NOT NULL DEFAULT 1
);
CREATE INDEX IF NOT EXISTS idx_textaufgabe_text ON textaufgabe(text_id);

-- Lernstand je Textaufgabe. Dieselbe Rechnung wie bei den Vokabeln (FSRS),
-- aber eine eigene Tabelle: lernzustand hängt mit einem Fremdschlüssel an
-- `aufgabe`, und eine Textaufgabe ist keine. Die Spalten sind absichtlich
-- deckungsgleich — so lässt sich fsrs.py unverändert benutzen, und was
-- für die Vokabeln gilt, gilt auch hier.
CREATE TABLE IF NOT EXISTS textlernzustand (
    textaufgabe_id       INTEGER NOT NULL REFERENCES textaufgabe(id) ON DELETE CASCADE,
    benutzer_id          INTEGER NOT NULL REFERENCES benutzer(id) ON DELETE CASCADE,
    zustand              TEXT NOT NULL DEFAULT 'neu'
                         CHECK (zustand IN ('neu','lernen','reif','verlernt','ausgesetzt')),
    stabilitaet          REAL,
    schwierigkeit        REAL,
    letzte_wiederholung  TEXT,
    faellig              TEXT,
    anzahl               INTEGER NOT NULL DEFAULT 0,
    anzahl_fehler        INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (textaufgabe_id, benutzer_id)
);
CREATE INDEX IF NOT EXISTS idx_textlernzustand_faellig
    ON textlernzustand(benutzer_id, faellig);

-- Bearbeitungen von Textaufgaben. Eigenes Protokoll, weil hier die Antwort
-- lang ist und die Rückmeldung der KI mitgeschrieben wird.
CREATE TABLE IF NOT EXISTS textbearbeitung (
    id             INTEGER PRIMARY KEY,
    textaufgabe_id INTEGER NOT NULL REFERENCES textaufgabe(id) ON DELETE CASCADE,
    benutzer_id    INTEGER NOT NULL REFERENCES benutzer(id) ON DELETE CASCADE,
    zeitpunkt      TEXT NOT NULL,
    antwort        TEXT,
    bewertung      INTEGER,          -- 1..4, wie bei den Vokabeln
    rueckmeldung   TEXT,             -- Text der KI oder eigene Notiz
    dauer_ms       INTEGER,
    -- Dieselben Felder wie in `wiederholung`: die beiden Protokolle
    -- sind absichtlich deckungsgleich, damit ein Lernkern beides kann
    -- (backend/lernkern.py).
    urteil             TEXT,
    denkzeit_ms        INTEGER,
    versuche           INTEGER NOT NULL DEFAULT 1,
    bewertung_quelle   TEXT,
    aufgedeckt         INTEGER NOT NULL DEFAULT 0,
    stabilitaet_vor    REAL,
    stabilitaet_nach   REAL,
    schwierigkeit_vor  REAL,
    schwierigkeit_nach REAL,
    intervall_tage     REAL,
    verstrichen_tage   REAL
);
CREATE INDEX IF NOT EXISTS idx_textbearbeitung
    ON textbearbeitung(benutzer_id, textaufgabe_id, zeitpunkt);

-- ======================================================================
-- Lernziele und Lernblöcke
--
-- Ein LERNZIEL ist ein Ausschnitt des Bestands mit einem Termin: "Lektion 3
-- bis Freitag", "alle Verben im Passé composé", "die Stammformen aus dem
-- Nibelungenlied". Der Ausschnitt ist ausdrücklich NICHT an eine Lektion
-- gebunden — er darf über Lektionen und sogar über Sammlungen greifen.
--
-- Ein LERNBLOCK wird daraus errechnet und nicht gespeichert: er ist immer
-- der aktuelle Zuschnitt aus Fälligem, Wackligem und Neuem, verschränkt
-- gemischt. Gespeichert wird nur das Ziel; der Block folgt daraus.
-- ======================================================================

CREATE TABLE IF NOT EXISTS lernziel (
    id            INTEGER PRIMARY KEY,
    benutzer_id   INTEGER NOT NULL REFERENCES benutzer(id) ON DELETE CASCADE,
    name          TEXT NOT NULL,
    -- JSON. Mögliche Einträge: sammlungen, lektionen, wortarten,
    -- formgruppen, typen, lexeme — alles Listen, alles freigestellt.
    -- Was fehlt, schränkt nicht ein.
    umfang        TEXT NOT NULL DEFAULT '{}',
    termin        TEXT,                    -- Datum, bis wann
    -- Was gilt als geschafft: 'reif' (sitzt dauerhaft) oder
    -- 'einmal_richtig' (wenigstens einmal gekonnt).
    ziel          TEXT NOT NULL DEFAULT 'reif'
                  CHECK (ziel IN ('reif', 'einmal_richtig')),
    aktiv         INTEGER NOT NULL DEFAULT 1,
    notiz         TEXT,
    -- »Neu würfeln« bei »Was käme dran?«. Der Zähler steht HIER und
    -- nicht in der Ansicht, weil Vorschau und Sitzung durch dieselbe
    -- Funktion gehen: ein Würfel, der nur die Vorschau änderte, zeigte
    -- einen Block, den die Abfrage danach nicht liefert.
    --
    -- 0 heißt: unverändert die beste Zusammenstellung. Jeder Wurf
    -- erhöht um eins und streut innerhalb der Gruppen neu — die
    -- Gruppen selbst (wie viel fällig, wacklig, neu) bleiben, sonst
    -- würfelte man den Terminplan weg.
    wurf          INTEGER NOT NULL DEFAULT 0,
    angelegt      TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_lernziel_benutzer ON lernziel(benutzer_id, aktiv);

-- ======================================================================
-- Grammatikregeln — das "Warum ist das so?" an der Frage.
--
-- Beim Üben steht die Regel zur Verfügung, die gerade greift: beim
-- griechischen Aorist die Regel zum Aorist, beim Genitiv die zum
-- Genitiv. Nicht als Grammatikbuch zum Durchlesen, sondern als Antwort
-- auf die eine Frage, die man in dem Moment hat.
--
-- Gefunden wird eine Regel über ihr MUSTER, nicht über eine feste
-- Zuordnung: {"wortart": "verb", "merkmale": {"tempus": "aorist"}}
-- greift bei jeder Aoristform jedes Verbs. Das ist dieselbe Mechanik
-- wie bei den erklärten Lücken (merkmale.passt_muster) und bei den
-- Formgruppen — eine Regel muss nicht wissen, welche Wörter es gibt.
--
-- Die Regeln hängen an der SAMMLUNG, nicht an der Sprache. Grammatik
-- ist zwar eine Eigenschaft der Sprache, aber die Sammlung ist überall
-- sonst die Einheit für Besitz, Freigabe und Zugriff; an der Sprache
-- hängend bräuchte es eine eigene Rechteregel, und die französischen
-- Erklärungen des einen gingen den anderen etwas an. Der Preis ist, dass zwei Sammlungen
-- derselben Sprache ihre Regeln doppelt pflegen.
--
-- `geprueft` wie überall: was ein Agent einträgt, wird nicht gezeigt,
-- bevor ein Mensch es angesehen hat.
CREATE TABLE IF NOT EXISTS regel (
    id           INTEGER PRIMARY KEY,
    sammlung_id  INTEGER NOT NULL REFERENCES sammlung(id) ON DELETE CASCADE,
    -- Stabile Kennung, damit ein Agent dieselbe Regel wiederfindet und
    -- berichtigt, statt eine zweite anzulegen.
    kennung      TEXT,
    titel        TEXT NOT NULL,
    text         TEXT NOT NULL,
    -- JSON-Liste: [{"form": "έγραψα", "bedeutung": "ich schrieb"}, …]
    beispiele    TEXT NOT NULL DEFAULT '[]',
    -- JSON: {"wortart": …, "formgruppe": …, "merkmale": {…}}
    -- Alles freigestellt. Das leere Muster greift überall — brauchbar
    -- für eine allgemeine Regel zur Sammlung.
    muster       TEXT NOT NULL DEFAULT '{}',
    reihenfolge  INTEGER NOT NULL DEFAULT 0,
    geprueft     INTEGER NOT NULL DEFAULT 0,
    quelle       TEXT,
    angelegt     TEXT NOT NULL DEFAULT (datetime('now')),
    geaendert    TEXT
);
CREATE INDEX IF NOT EXISTS idx_regel_sammlung
    ON regel(sammlung_id, geprueft);
CREATE UNIQUE INDEX IF NOT EXISTS idx_regel_kennung
    ON regel(sammlung_id, kennung) WHERE kennung IS NOT NULL;
