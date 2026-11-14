# Festlegung für die KI-gestützte Befüllung

Stand 2026-11-14. Dieses Blatt richtet sich an eine KI, die Vokabeln samt
vollständigen Paradigmen für den Vokabeltrainer erzeugt — derzeit von Hand
hinübergetragen, später unmittelbar über den MCP-Server.

**Ja, vollständige Tabellen erzeugen** — alle Personen, alle verlangten Zeiten.
Der Trainer braucht sie vollständig, weil er daraus die Aufgaben ERZEUGT: jede
Form wird eine eigene Abfrage, und aus dem gemeinsamen Anfang aller Formen
leitet er den Wortstamm ab (für die Zerlegung "γράφ|ουμε"). Fehlende Zellen
bedeuten fehlende Aufgaben, und ein unvollständiges Paradigma verdirbt die
Stammerkennung.

## Das Format

Ein Wort ist **ein** Datensatz mit allem darin — Lemma, alle Formen, alle
Bedeutungen. Nicht vierzig Einzelsätze. Gesendet wird er an
`POST /api/lexeme`.

Jede Form besteht aus `text` und einem **Merkmalsbündel**. Das Bündel ist der
Kern des Ganzen: nicht `praesens_1sg` als Spaltenname, sondern
`{"modus": "indikativ", "tempus": "praesens", "person": "1", "numerus": "sg"}`.

### Verbindliche Regeln

1. `quelle` ist **`"ki"`** und `geprueft` ist **`false`**. Ungeprüfte Formen
   werden nicht abgefragt, bis ein Mensch sie bestätigt. Das ist Absicht:
   eine erfundene Form, die unbemerkt gepaukt wird, ist schlimmer als eine
   fehlende.
2. `person` ist eine **Zeichenkette**: `"1"`, nicht `1`.
3. Genau **eine** Form trägt `ist_grundform: true` — die Zitierform, unter der
   das Wort im Wörterbuch steht. Für sie entsteht keine eigene Formaufgabe.
4. Unbekannte Merkmale oder Werte werden **abgelehnt** (HTTP 422). Nur was
   unten steht, ist erlaubt. Eigene Zusätze gehen mit dem Vorsatz `x_`,
   etwa `"x_lehrbuchseite": "42"`.
5. Mehrere gültige Übersetzungen sind der **Normalfall** — bitte alle angeben,
   nicht die beste auswählen. Der Trainer nimmt jede davon als richtig an.
6. Verschiedene **Bedeutungen** sind etwas anderes als verschiedene
   Übersetzungen derselben Bedeutung. „Bank" als Geldinstitut und als Sitzbank
   sind zwei Einträge in `bedeutungen`, jeder mit `kontext`; „schreiben" und
   „aufschreiben" sind zwei `uebersetzungen` derselben Bedeutung.

## Vollständiges Beispiel

Griechisch, `γράφω` mit Präsens, Aorist und Futur — genau das, wonach gefragt
war. So sieht der fertige Datensatz aus:

```json
{
  "sammlung_id": 1,
  "lemma": "γράφω",
  "wortart": "verb",
  "merkmale": {"klasse": "Α-Konjugation"},
  "bedeutungen": [
    {"uebersetzungen": [{"text": "schreiben"}, {"text": "aufschreiben"}],
     "quelle": "ki"}
  ],
  "formen": [
    {"text": "γράφω",     "merkmale": {"modus": "indikativ", "tempus": "praesens", "person": "1", "numerus": "sg"},
     "ist_grundform": true, "quelle": "ki", "geprueft": false},
    {"text": "γράφεις", "merkmale": {"modus": "indikativ", "tempus": "praesens", "person": "2", "numerus": "sg"}, "quelle": "ki", "geprueft": false},
    {"text": "γράφει", "merkmale": {"modus": "indikativ", "tempus": "praesens", "person": "3", "numerus": "sg"}, "quelle": "ki", "geprueft": false},
    {"text": "γράφουμε", "merkmale": {"modus": "indikativ", "tempus": "praesens", "person": "1", "numerus": "pl"}, "quelle": "ki", "geprueft": false},
    {"text": "γράφετε", "merkmale": {"modus": "indikativ", "tempus": "praesens", "person": "2", "numerus": "pl"}, "quelle": "ki", "geprueft": false},
    {"text": "γράφουν", "merkmale": {"modus": "indikativ", "tempus": "praesens", "person": "3", "numerus": "pl"}, "quelle": "ki", "geprueft": false},
    {"text": "έγραψα", "merkmale": {"modus": "indikativ", "tempus": "aorist", "person": "1", "numerus": "sg"}, "quelle": "ki", "geprueft": false},
    {"text": "έγραψες", "merkmale": {"modus": "indikativ", "tempus": "aorist", "person": "2", "numerus": "sg"}, "quelle": "ki", "geprueft": false},
    {"text": "έγραψε", "merkmale": {"modus": "indikativ", "tempus": "aorist", "person": "3", "numerus": "sg"}, "quelle": "ki", "geprueft": false},
    {"text": "γράψαμε", "merkmale": {"modus": "indikativ", "tempus": "aorist", "person": "1", "numerus": "pl"}, "quelle": "ki", "geprueft": false},
    {"text": "γράψατε", "merkmale": {"modus": "indikativ", "tempus": "aorist", "person": "2", "numerus": "pl"}, "quelle": "ki", "geprueft": false},
    {"text": "έγραψαν", "merkmale": {"modus": "indikativ", "tempus": "aorist", "person": "3", "numerus": "pl"}, "quelle": "ki", "geprueft": false},
    {"text": "θα γράψω", "merkmale": {"modus": "indikativ", "tempus": "futur", "aspekt": "perfektiv", "person": "1", "numerus": "sg"}, "quelle": "ki", "geprueft": false},
    {"text": "θα γράψεις", "merkmale": {"modus": "indikativ", "tempus": "futur", "aspekt": "perfektiv", "person": "2", "numerus": "sg"}, "quelle": "ki", "geprueft": false},
    {"text": "θα γράψει", "merkmale": {"modus": "indikativ", "tempus": "futur", "aspekt": "perfektiv", "person": "3", "numerus": "sg"}, "quelle": "ki", "geprueft": false},
    {"text": "θα γράψουμε", "merkmale": {"modus": "indikativ", "tempus": "futur", "aspekt": "perfektiv", "person": "1", "numerus": "pl"}, "quelle": "ki", "geprueft": false},
    {"text": "θα γράψετε", "merkmale": {"modus": "indikativ", "tempus": "futur", "aspekt": "perfektiv", "person": "2", "numerus": "pl"}, "quelle": "ki", "geprueft": false},
    {"text": "θα γράψουν", "merkmale": {"modus": "indikativ", "tempus": "futur", "aspekt": "perfektiv", "person": "3", "numerus": "pl"}, "quelle": "ki", "geprueft": false}
  ]
}
```bash
curl -X POST http://<dein-server>:8030/api/lexeme \
     -H 'Content-Type: application/json' \
     -d @wort.json
```

`sammlung_id` erfragt man mit `GET /api/sammlungen?benutzer_id=1`.

## Das Merkmalsvokabular

Nur diese Dimensionen und Werte sind erlaubt.

- **nonfinit** — `infinitiv`, `partizip_praesens`, `partizip_perfekt`, `gerundium`, `supinum`
- **person** — `1`, `2`, `3`
- **kasus** — `nom`, `gen`, `dat`, `akk`, `vok`, `abl`
- **numerus** — `sg`, `pl`
- **genus** — `m`, `f`, `n`
- **stufe** — `grund`, `komparativ`, `superlativ`
- **tempus** — `praesens`, `imperfekt`, `praeteritum`, `aorist`, `perfekt`, `plusquamperfekt`, `futur`, `futur_perfekt`, `verlaufsform`
- **aspekt** — `perfektiv`, `imperfektiv`
- **modus** — `indikativ`, `konjunktiv`, `imperativ`, `konditional`
- **genus_verbi** — `aktiv`, `passiv`, `medium`
- **flexion** — `stark`, `schwach`

Dazu `genus` nur bei Substantiven und Adjektiven, `flexion` (stark/schwach)
im Deutschen und Mittelhochdeutschen, `aspekt` im Neugriechischen.

## Die Formgruppen je Sprache

Eine **Formgruppe** ist eine Tabelle, die gemeinsam gelernt wird — eine Zeit
mit ihren sechs Personen, oder eine einzelne Form wie das Partizip. Die Spalte
*Merkmale* nennt, was alle Zellen der Gruppe gemeinsam haben; bei mehrzelligen
Gruppen kommen `person` und `numerus` hinzu.

Die mit **(Standard)** bezeichneten Gruppen fragt eine neue Sammlung von
Anfang an ab. Die übrigen lassen sich jederzeit zuschalten — es ist also kein
Schaden, mehr zu liefern als voreingestellt ist.

### Griechisch (`el`)

Stammformen, das Kernpensum: **Ενεστώτας (Präsens) – Αόριστος (Aorist) – Μέλλοντας στιγμιαίος (Futur, punktuell)**

*Verb*

| Kennung | Name | Zellen | Merkmale |
|---|---|---|---|
| `enestotas` | Ενεστώτας (Präsens) (Standard) | 6 | `{"genus_verbi": "aktiv", "modus": "indikativ", "tempus": "praesens"}` |
| `paratatikos` | Παρατατικός (Imperfekt) | 6 | `{"genus_verbi": "aktiv", "modus": "indikativ", "tempus": "imperfekt"}` |
| `aoristos` | Αόριστος (Aorist) (Standard) | 6 | `{"genus_verbi": "aktiv", "modus": "indikativ", "tempus": "aorist"}` |
| `mellontas_stigmiaios` | Μέλλοντας στιγμιαίος (Futur, punktuell) (Standard) | 6 | `{"aspekt": "perfektiv", "genus_verbi": "aktiv", "modus": "indikativ", "tempus": "futur"}` |
| `mellontas_exakolouthitikos` | Μέλλοντας εξακολουθητικός (Futur, fortgesetzt) | 6 | `{"aspekt": "imperfektiv", "genus_verbi": "aktiv", "modus": "indikativ", "tempus": "futur"}` |
| `parakeimenos` | Παρακείμενος (Perfekt) | 6 | `{"genus_verbi": "aktiv", "modus": "indikativ", "tempus": "perfekt"}` |
| `ypotaktiki` | Υποτακτική (Konjunktiv) | 6 | `{"genus_verbi": "aktiv", "modus": "konjunktiv", "tempus": "praesens"}` |
| `prostaktiki` | Προστακτική (Imperativ) | 2 | `{"genus_verbi": "aktiv", "modus": "imperativ"}` |
| `enestotas_pass` | Ενεστώτας Παθητικής (Präsens Passiv) (Standard) | 6 | `{"genus_verbi": "passiv", "modus": "indikativ", "tempus": "praesens"}` |
| `aoristos_pass` | Αόριστος Παθητικής (Aorist Passiv) (Standard) | 6 | `{"genus_verbi": "passiv", "modus": "indikativ", "tempus": "aorist"}` |
| `paratatikos_pass` | Παρατατικός Παθητικής (Imperfekt Passiv) | 6 | `{"genus_verbi": "passiv", "modus": "indikativ", "tempus": "imperfekt"}` |
| `mellontas_pass` | Μέλλοντας Παθητικής (Futur Passiv, punktuell) | 6 | `{"aspekt": "perfektiv", "genus_verbi": "passiv", "modus": "indikativ", "tempus": "futur"}` |
| `ypotaktiki_pass` | Υποτακτική Παθητικής (Konjunktiv Passiv) | 6 | `{"genus_verbi": "passiv", "modus": "konjunktiv", "tempus": "praesens"}` |
| `metochi_pass` | Μετοχή παθητικού παρακειμένου (Partizip Perfekt Passiv) | 1 | `{"genus_verbi": "passiv", "nonfinit": "partizip_perfekt"}` |
| `gerundio` | Γερούνδιο (Gerundium, -οντας) | 1 | `{"genus_verbi": "aktiv", "nonfinit": "gerundium"}` |

*Substantiv*

| Kennung | Name | Zellen | Merkmale |
|---|---|---|---|
| `subst_nom_sg` | Nominativ Singular (Standard) | 1 | `{"kasus": "nom", "numerus": "sg"}` |
| `subst_gen_sg` | Genitiv Singular (Standard) | 1 | `{"kasus": "gen", "numerus": "sg"}` |
| `subst_akk_sg` | Akkusativ Singular (Standard) | 1 | `{"kasus": "akk", "numerus": "sg"}` |
| `subst_vok_sg` | Vokativ Singular | 1 | `{"kasus": "vok", "numerus": "sg"}` |
| `subst_nom_pl` | Nominativ Plural (Standard) | 1 | `{"kasus": "nom", "numerus": "pl"}` |
| `subst_gen_pl` | Genitiv Plural (Standard) | 1 | `{"kasus": "gen", "numerus": "pl"}` |
| `subst_akk_pl` | Akkusativ Plural (Standard) | 1 | `{"kasus": "akk", "numerus": "pl"}` |
| `subst_vok_pl` | Vokativ Plural | 1 | `{"kasus": "vok", "numerus": "pl"}` |

*Adjektiv*

| Kennung | Name | Zellen | Merkmale |
|---|---|---|---|
| `adj_m` | maskulin Nominativ Singular (Standard) | 1 | `{"genus": "m", "kasus": "nom", "numerus": "sg"}` |
| `adj_f` | feminin Nominativ Singular (Standard) | 1 | `{"genus": "f", "kasus": "nom", "numerus": "sg"}` |
| `adj_n` | neutrum Nominativ Singular (Standard) | 1 | `{"genus": "n", "kasus": "nom", "numerus": "sg"}` |
| `adj_komparativ` | Συγκριτικός (Komparativ) (Standard) | 1 | `{"stufe": "komparativ"}` |
| `adj_superlativ` | Υπερθετικός (Superlativ) (Standard) | 1 | `{"stufe": "superlativ"}` |

*Lexemmerkmale* — beschreiben das Wort, nicht eine Form:

- Substantiv, `genus`: `m`, `f`, `n`, `mf`
- Verb, `klasse`: `Α-Konjugation`, `Β1`, `Β2`, `unregelmäßig`, `-ομαι`, `-άμαι`, `-ούμαι`, `-ιέμαι`
- Verb, `diathese`: `aktiv`, `medial`, `deponens`

Das Griechische hat **eigene Passivgruppen**, nicht bloß ein Merkmal an den
Aktivformen: γράφομαι ist keine Variante von γράφω, die Endungen sind andere.
Darum trägt jede Aktivgruppe ausdrücklich `"genus_verbi": "aktiv"` — ohne das
passte eine Passivform in beide Tabellen.

**Deponentien** (θυμάμαι, έρχομαι, κοιμάμαι) haben *nur* Passivformen,
bedeuten damit aber nichts Passives. Sie brauchen das Lexemmerkmal
`{"diathese": "deponens"}`; dann gelten die Aktivgruppen, die es bei ihnen
gar nicht gibt, nicht als fehlend.


### Französisch (`fr`)

Stammformen, das Kernpensum: **Infinitif – Participe passé**

*Verb*

| Kennung | Name | Zellen | Merkmale |
|---|---|---|---|
| `praesens` | Présent (Standard) | 6 | `{"modus": "indikativ", "tempus": "praesens"}` |
| `imparfait` | Imparfait (Standard) | 6 | `{"modus": "indikativ", "tempus": "imperfekt"}` |
| `passe_compose` | Passé composé (Standard) | 6 | `{"modus": "indikativ", "tempus": "perfekt"}` |
| `plus_que_parfait` | Plus-que-parfait | 6 | `{"modus": "indikativ", "tempus": "plusquamperfekt"}` |
| `passe_simple` | Passé simple | 6 | `{"modus": "indikativ", "tempus": "praeteritum"}` |
| `futur_simple` | Futur simple (Standard) | 6 | `{"modus": "indikativ", "tempus": "futur"}` |
| `futur_anterieur` | Futur antérieur | 6 | `{"modus": "indikativ", "tempus": "futur_perfekt"}` |
| `conditionnel` | Conditionnel présent | 6 | `{"modus": "konditional", "tempus": "praesens"}` |
| `conditionnel_passe` | Conditionnel passé | 6 | `{"modus": "konditional", "tempus": "perfekt"}` |
| `subjonctif` | Subjonctif présent | 6 | `{"modus": "konjunktiv", "tempus": "praesens"}` |
| `subjonctif_passe` | Subjonctif passé | 6 | `{"modus": "konjunktiv", "tempus": "perfekt"}` |
| `imperatif` | Impératif | 3 | `{"modus": "imperativ"}` |
| `infinitif` | Infinitif (Standard) | 1 | `{"nonfinit": "infinitiv"}` |
| `participe_passe` | Participe passé (Standard) | 1 | `{"nonfinit": "partizip_perfekt"}` |
| `participe_present` | Participe présent | 1 | `{"nonfinit": "partizip_praesens"}` |

*Substantiv*

| Kennung | Name | Zellen | Merkmale |
|---|---|---|---|
| `sg` | Singular (Standard) | 1 | `{"numerus": "sg"}` |
| `pl` | Plural (Standard) | 1 | `{"numerus": "pl"}` |

*Adjektiv*

| Kennung | Name | Zellen | Merkmale |
|---|---|---|---|
| `m_sg` | maskulin Singular (Standard) | 1 | `{"genus": "m", "numerus": "sg"}` |
| `f_sg` | feminin Singular (Standard) | 1 | `{"genus": "f", "numerus": "sg"}` |
| `m_pl` | maskulin Plural (Standard) | 1 | `{"genus": "m", "numerus": "pl"}` |
| `f_pl` | feminin Plural (Standard) | 1 | `{"genus": "f", "numerus": "pl"}` |

*Lexemmerkmale* — beschreiben das Wort, nicht eine Form:

- Verb, `hilfsverb`: `avoir`, `être`
- Verb, `klasse`: `er`, `ir`, `re`, `unregelmäßig`
- Substantiv, `genus`: `m`, `f`


### Spanisch (`es`)

Stammformen, das Kernpensum: **Infinitivo – Participio – Gerundio**

*Verb*

| Kennung | Name | Zellen | Merkmale |
|---|---|---|---|
| `presente` | Presente (Standard) | 6 | `{"modus": "indikativ", "tempus": "praesens"}` |
| `imperfecto` | Pretérito imperfecto (Standard) | 6 | `{"modus": "indikativ", "tempus": "imperfekt"}` |
| `indefinido` | Pretérito indefinido (Standard) | 6 | `{"modus": "indikativ", "tempus": "praeteritum"}` |
| `perfecto` | Pretérito perfecto | 6 | `{"modus": "indikativ", "tempus": "perfekt"}` |
| `pluscuamperfecto` | Pretérito pluscuamperfecto | 6 | `{"modus": "indikativ", "tempus": "plusquamperfekt"}` |
| `futuro` | Futuro simple (Standard) | 6 | `{"modus": "indikativ", "tempus": "futur"}` |
| `condicional` | Condicional simple | 6 | `{"modus": "konditional", "tempus": "praesens"}` |
| `subjuntivo` | Presente de subjuntivo | 6 | `{"modus": "konjunktiv", "tempus": "praesens"}` |
| `subjuntivo_imperfecto` | Imperfecto de subjuntivo | 6 | `{"modus": "konjunktiv", "tempus": "imperfekt"}` |
| `imperativo` | Imperativo | 5 | `{"modus": "imperativ"}` |
| `infinitivo` | Infinitivo (Standard) | 1 | `{"nonfinit": "infinitiv"}` |
| `participio` | Participio (Standard) | 1 | `{"nonfinit": "partizip_perfekt"}` |
| `gerundio` | Gerundio | 1 | `{"nonfinit": "gerundium"}` |

*Substantiv*

| Kennung | Name | Zellen | Merkmale |
|---|---|---|---|
| `sg` | Singular (Standard) | 1 | `{"numerus": "sg"}` |
| `pl` | Plural (Standard) | 1 | `{"numerus": "pl"}` |

*Adjektiv*

| Kennung | Name | Zellen | Merkmale |
|---|---|---|---|
| `m_sg` | maskulin Singular (Standard) | 1 | `{"genus": "m", "numerus": "sg"}` |
| `f_sg` | feminin Singular (Standard) | 1 | `{"genus": "f", "numerus": "sg"}` |
| `m_pl` | maskulin Plural (Standard) | 1 | `{"genus": "m", "numerus": "pl"}` |
| `f_pl` | feminin Plural (Standard) | 1 | `{"genus": "f", "numerus": "pl"}` |

*Lexemmerkmale* — beschreiben das Wort, nicht eine Form:

- Verb, `klasse`: `ar`, `er`, `ir`, `unregelmäßig`
- Substantiv, `genus`: `m`, `f`


### Englisch (`en`)

Stammformen, das Kernpensum: **Infinitiv – Simple past – Past participle**

*Verb*

| Kennung | Name | Zellen | Merkmale |
|---|---|---|---|
| `infinitive` | Infinitiv (Standard) | 1 | `{"nonfinit": "infinitiv"}` |
| `present_3sg` | 3. Person Singular Präsens (Standard) | 1 | `{"modus": "indikativ", "numerus": "sg", "person": "3", "tempus": "praesens"}` |
| `past` | Simple past (Standard) | 1 | `{"modus": "indikativ", "tempus": "praeteritum"}` |
| `past_participle` | Past participle (Standard) | 1 | `{"nonfinit": "partizip_perfekt"}` |
| `present_participle` | Present participle (-ing) (Standard) | 1 | `{"nonfinit": "partizip_praesens"}` |

*Substantiv*

| Kennung | Name | Zellen | Merkmale |
|---|---|---|---|
| `sg` | Singular (Standard) | 1 | `{"numerus": "sg"}` |
| `pl` | Plural (Standard) | 1 | `{"numerus": "pl"}` |

*Adjektiv*

| Kennung | Name | Zellen | Merkmale |
|---|---|---|---|
| `grund` | Grundstufe (Standard) | 1 | `{"stufe": "grund"}` |
| `komparativ` | Comparative (Standard) | 1 | `{"stufe": "komparativ"}` |
| `superlativ` | Superlative (Standard) | 1 | `{"stufe": "superlativ"}` |

*Lexemmerkmale* — beschreiben das Wort, nicht eine Form:

- Verb, `klasse`: `regelmäßig`, `unregelmäßig`


### Mittelhochdeutsch (`gmh`)

Stammformen, das Kernpensum: **Infinitiv – 1./3. Singular Präteritum – 1./3. Plural Präteritum – Partizip Präteritum**

*Verb*

| Kennung | Name | Zellen | Merkmale |
|---|---|---|---|
| `infinitiv` | Infinitiv (Standard) | 1 | `{"nonfinit": "infinitiv"}` |
| `stamm_praet_sg` | 1./3. Singular Präteritum (Standard) | 1 | `{"modus": "indikativ", "numerus": "sg", "person": "1", "tempus": "praeteritum"}` |
| `stamm_praet_pl` | 1./3. Plural Präteritum (Standard) | 1 | `{"modus": "indikativ", "numerus": "pl", "person": "1", "tempus": "praeteritum"}` |
| `partizip_praet` | Partizip Präteritum (Standard) | 1 | `{"nonfinit": "partizip_perfekt"}` |
| `praesens` | Präsens Indikativ | 6 | `{"modus": "indikativ", "tempus": "praesens"}` |
| `praeteritum` | Präteritum Indikativ | 6 | `{"modus": "indikativ", "tempus": "praeteritum"}` |
| `konj_praesens` | Konjunktiv Präsens | 6 | `{"modus": "konjunktiv", "tempus": "praesens"}` |
| `konj_praeteritum` | Konjunktiv Präteritum | 6 | `{"modus": "konjunktiv", "tempus": "praeteritum"}` |
| `imperativ` | Imperativ | 2 | `{"modus": "imperativ"}` |
| `partizip_praes` | Partizip Präsens | 1 | `{"nonfinit": "partizip_praesens"}` |

*Substantiv*

| Kennung | Name | Zellen | Merkmale |
|---|---|---|---|
| `subst_nom_sg` | Nominativ Singular (Standard) | 1 | `{"kasus": "nom", "numerus": "sg"}` |
| `subst_gen_sg` | Genitiv Singular (Standard) | 1 | `{"kasus": "gen", "numerus": "sg"}` |
| `subst_dat_sg` | Dativ Singular (Standard) | 1 | `{"kasus": "dat", "numerus": "sg"}` |
| `subst_akk_sg` | Akkusativ Singular (Standard) | 1 | `{"kasus": "akk", "numerus": "sg"}` |
| `subst_nom_pl` | Nominativ Plural (Standard) | 1 | `{"kasus": "nom", "numerus": "pl"}` |
| `subst_gen_pl` | Genitiv Plural (Standard) | 1 | `{"kasus": "gen", "numerus": "pl"}` |
| `subst_dat_pl` | Dativ Plural | 1 | `{"kasus": "dat", "numerus": "pl"}` |
| `subst_akk_pl` | Akkusativ Plural | 1 | `{"kasus": "akk", "numerus": "pl"}` |

*Adjektiv*

| Kennung | Name | Zellen | Merkmale |
|---|---|---|---|
| `stark` | starke Flexion, Nominativ Singular (Standard) | 1 | `{"flexion": "stark", "kasus": "nom", "numerus": "sg"}` |
| `schwach` | schwache Flexion, Nominativ Singular (Standard) | 1 | `{"flexion": "schwach", "kasus": "nom", "numerus": "sg"}` |
| `komparativ` | Komparativ (Standard) | 1 | `{"stufe": "komparativ"}` |
| `superlativ` | Superlativ (Standard) | 1 | `{"stufe": "superlativ"}` |

*Lexemmerkmale* — beschreiben das Wort, nicht eine Form:

- Verb, `klasse`: `stark I`, `stark II`, `stark III`, `stark IV`, `stark V`, `stark VI`, `stark VII`, `schwach`, `Präteritopräsens`, `Wurzelverb`
- Substantiv, `genus`: `m`, `f`, `n`
- Substantiv, `klasse`: `stark a`, `stark i`, `stark u`, `schwach n`, `Wurzelnomen`


### Deutsch (`de`)

Stammformen, das Kernpensum: **Infinitiv – Präteritum – Partizip II**

*Verb*

| Kennung | Name | Zellen | Merkmale |
|---|---|---|---|
| `praesens` | Präsens (Standard) | 6 | `{"modus": "indikativ", "tempus": "praesens"}` |
| `praeteritum` | Präteritum (Standard) | 6 | `{"modus": "indikativ", "tempus": "praeteritum"}` |
| `infinitiv` | Infinitiv (Standard) | 1 | `{"nonfinit": "infinitiv"}` |
| `partizip_ii` | Partizip II (Standard) | 1 | `{"nonfinit": "partizip_perfekt"}` |

*Substantiv*

| Kennung | Name | Zellen | Merkmale |
|---|---|---|---|
| `sg` | Singular (Standard) | 1 | `{"numerus": "sg"}` |
| `pl` | Plural (Standard) | 1 | `{"numerus": "pl"}` |

*Adjektiv*

| Kennung | Name | Zellen | Merkmale |
|---|---|---|---|
| `grund` | Grundstufe (Standard) | 1 | `{"stufe": "grund"}` |
| `komparativ` | Komparativ (Standard) | 1 | `{"stufe": "komparativ"}` |
| `superlativ` | Superlativ (Standard) | 1 | `{"stufe": "superlativ"}` |

*Lexemmerkmale* — beschreiben das Wort, nicht eine Form:

- Substantiv, `genus`: `m`, `f`, `n`


## Übungssätze und Texte

Ein Übungssatz und ein ganzer Text sind derselbe Gegenstand mit
unterschiedlich vielen Abschnitten.

```json
{
  "typ": "satz",
  "lektion_nr": 39,
  "zielsprache": "Χθες πήγα στο θέατρο.",
  "grundsprache": "Gestern ging ich ins Theater.",
  "alternativen_zielsprache": ["Εχθές πήγα στο θέατρο."],
  "alternativen_grundsprache": ["Gestern bin ich ins Theater gegangen."],
  "richtungen": ["el-de", "de-el"],
  "quelle": {"art": "ki"}
}
```

- **`typ`** — `satz`, `text`, `dialog`, `brief` oder `zeitungsstil`.
- **`richtungen`** — in welche Richtungen geübt wird, als Sprachpaar
  (`el-de` heißt aus der Lernsprache in die Grundsprache) oder als
  `hin`/`rueck`. Daraus entstehen die Aufgaben; ohne Angabe beide.
- **`alternativen_*`** — weitere gültige Fassungen. **Großzügig angeben.**
  Eine richtige Übersetzung darf nicht daran scheitern, dass sie nicht die
  zuerst aufgeschriebene ist.
- **`quelle.art`** — `ki`, `eigen` oder `verweis`. Fremde Zeitungsartikel
  werden **verlinkt, nicht abgeschrieben**: bei `verweis` gehören `titel`
  und `url` dazu, und als Übung dient eine eigene Fassung.
- **`kennung`** — eigener Schlüssel, damit ein zweiter Lauf aktualisiert
  statt zu verdoppeln. Ohne sie dient der Zieltext selbst als Schlüssel.

Bei mehreren Sätzen ist eine ausdrückliche Liste `abschnitte` genauer:

```json
{
  "typ": "dialog",
  "titel": "Στο ταμείο",
  "abschnitte": [
    {"zielsprache": "Καλημέρα!", "grundsprache": "Guten Morgen!",
     "alternativen_grundsprache": ["Guten Tag!"]},
    {"zielsprache": "Τι θα πάρετε;", "grundsprache": "Was nehmen Sie?"}
  ],
  "richtungen": ["el-de"]
}
```

Ohne diese Liste wird nur dann in Sätze geteilt, wenn Zielsprache und
Grundsprache auf dieselbe Zahl kommen. Eine geratene Zuordnung wäre
schlimmer als ein ungeteilter Text — die Rückmeldung verglich dann mit dem
falschen Satz.

### Wie bewertet wird

Wort für Wort gegen alle angegebenen Fassungen, nach den Prüfregeln der
Sprache: Satzzeichen zählen nicht, Akzente sind ein Hinweis und kein
Fehler, bis zu zwei Wörter mit Tippfehler gelten als „fast". Bei `typ:
"satz"` zählt das Urteil. Bei allem Längeren bleibt die Einschätzung beim
Menschen und der Vergleich ist nur Hilfestellung — dort passt eine
wörtliche Übereinstimmung zu selten.

Die Rückmeldung nennt die abweichenden Wörter einzeln (`σπίτι → θέατρο`,
`fehlt: στο`). „Falsch" allein ist keine Auskunft.

### Vorher die Deckung prüfen

`text_pruefen(sammlung_id, text, bis_lektion)` sagt, welche Wörter eines
Textes im Bestand noch nicht vorkommen — nachgeschlagen über **alle
Formen**, nicht nur die Lemmata. Drei Listen kommen zurück: `bekannt`,
`zu_spaet` (steht da, kommt aber erst nach dieser Lektion) und `unbekannt`.
Partikeln der Sprache (`θα`, `να`, `δεν`) zählen nicht als unbekannt.

Das gehört **vor** das Schreiben eines Übungstextes. Ein Text mit dreißig
unbekannten Wörtern ist keine Übung, sondern eine Enttäuschung.

Wie Formen bleiben Übungen **ungeprüft**, bis ein Mensch sie freigibt.


## Berichtigen und Löschen

Ein Probelauf findet Fehler; danach müssen sie sich auch beheben lassen,
ohne dass ein Mensch alles von Hand nachzieht. Dafür gibt es
`vokabeln_auflisten`, `vokabel_aendern`, `form_aendern`, `form_loeschen`
und `vokabel_loeschen`.

Drei Regeln dabei:

- **Geänderter Inhalt fällt auf ungeprüft zurück.** Ändert sich der Text
  oder das Merkmalsbündel einer Form, gilt die Freigabe nicht mehr — was
  geändert wurde, ist nicht mehr das, was ein Mensch bestätigt hat. Die
  Freigabe selbst kann kein Werkzeug setzen.
- **Löschen verlangt eine Bestätigung.** `form_loeschen` braucht den
  vorhandenen Text, `vokabel_loeschen` das vorhandene Lemma. An jeder Form
  hängt ein Lernstand; eine verwechselte Kennung träfe sonst lautlos das
  Falsche. Die Antwort sagt, wie viele Wiederholungen verlorengehen —
  steht dort eine Zahl über null, vorher abstimmen.
- **Berichtigen ist besser als Löschen.** Eine falsch beschriftete Form
  lässt sich mit `form_aendern` richtigstellen; die Aufgaben hängen am
  Merkmalsbündel, nicht an der Zeile, und der Lernstand bleibt.

`bedeutungen` bei `vokabel_aendern` **ersetzt** alle Bedeutungen. Welche
einzelne Übersetzung sonst gemeint wäre, ließe sich nicht ausdrücken.


## Der MCP-Server

Der Server deckt inzwischen alles von diesem Blatt ab. Die Regeln bleiben
dieselben — er ist nur ein anderer Weg zur gleichen Schnittstelle und
prüft dieselben Merkmale. Der erste Aufruf in jeder Sitzung ist
`sammlungen_auflisten`, der zweite `formgruppen_zeigen` für die Sprache.
