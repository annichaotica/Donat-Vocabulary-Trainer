# Zugang von außen

Der Familienserver ist von außen über einen **Cloudflare-Tunnel** erreichbar,
nicht über eine Portweiterleitung. Der Unterschied ist nicht Geschmackssache:

* Im Router bleibt **kein Port offen**. Die Verbindung baut der Server selbst
  nach außen auf.
* Es gibt **keine erreichbare Adresse des Hauses**. Wer den Namen nachschlägt,
  landet bei Cloudflare, nicht bei euch.
* Ein wechselnder Anschluss macht nichts aus — kein DynDNS nötig.

## Was erreichbar ist

Welche Namen das sind, steht in `einrichten.py` unter `DIENSTE` und wird
beim Einrichten über `CF_ZONE` mit der eigenen Domain verbunden:

| Name | Dienst | intern |
|---|---|---|
| `vokabeln.<deine-domain>` | Vokabeltrainer | `127.0.0.1:8030` |
| `rezepte.<deine-domain>` | Mealie | `127.0.0.1:9925` |
| `mcp.<deine-domain>` | MCP-Schnittstelle | `127.0.0.1:8030` |

Alles, was nicht in dieser Liste steht, beantwortet der Tunnel mit 404 — auch
wenn jemand den Namen errät.

## Davor steht Cloudflare Access

**Der Vokabeltrainer hat keinerlei Anmeldung.** Die Profile sind bloße Namen
ohne Passwort — im Heimnetz richtig so, im offenen Netz nicht. Deshalb fragt
Cloudflare Access *vor* dem Durchreichen nach einer Mailadresse und schickt
einen sechsstelligen Einmalcode. Nur hinterlegte Adressen kommen durch.

Wer hinterlegt ist, steht in der Zugriffsregel in der Cloudflare-Verwaltung
unter **Zero Trust → Access → Anwendungen**.

Die **MCP-Schnittstelle** ist anders geschützt: sie wird von einem Programm
gerufen, nicht von einem Menschen, und kann keine Anmeldeseite bedienen.
Davor steht ein **Access-Diensttoken** (zwei feste Kopfzeilen), dazu im
Trainer selbst noch ein eigenes Geheimnis. Zwei Schlösser, beide ohne
Mensch bedienbar.

## Wartung

```sh
cd /srv/cloudflared
docker compose logs -f          # läuft der Tunnel?
docker compose restart          # nach einer Konfigurationsänderung
docker compose pull && docker compose up -d   # Fassung aktualisieren
```

Der Tunnel ist **fassungsfest gebunden** (nicht `:latest`), damit er nicht
eines Nachts von selbst auf eine Fassung springt, die sich anders verhält.
Zum Aktualisieren die Nummer in `docker-compose.yml` ändern.

Die Weiterleitungen selbst stehen nicht hier, sondern bei Cloudflare in der
Tunnelkonfiguration — dieser Tunnel wird von dort aus verwaltet.

## Wenn etwas nicht geht

1. `docker compose logs --tail 50` — der Tunnel meldet jede abgelehnte
   Verbindung mit Grund.
2. Läuft der Dienst dahinter? `curl -s http://127.0.0.1:8030/api/zustand`
3. Zeigt der DNS-Eintrag noch auf den Tunnel? In der Cloudflare-Verwaltung
   muss ein CNAME auf `<Tunnelkennung>.cfargotunnel.com` stehen, orange Wolke.
