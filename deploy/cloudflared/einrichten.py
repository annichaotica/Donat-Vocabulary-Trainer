#!/usr/bin/env python3
"""Richtet den Cloudflare-Tunnel samt Access ein.

    CF_TOKEN=...  CF_KONTO=<Kontokennung>  CF_ZONE=<deine-domain.de> \
      python3 einrichten.py --mailadressen du@example.com,kind@example.com

Mit --trocken zeigt es nur, was es täte.

Läuft in dieser Reihenfolge, und die Reihenfolge ist Absicht:

  1. Tunnel anlegen (oder den vorhandenen nehmen)
  2. Weiterleitungen eintragen
  3. **Access-Anwendungen und -Regeln** — der Schutz kommt VOR der
     Erreichbarkeit
  4. Erst danach die DNS-Einträge, die die Namen überhaupt auflösbar machen

Andersherum stünde der Vokabeltrainer, der keinerlei eigene Anmeldung hat,
für die Dauer der Einrichtung offen im Netz.

Das Skript ist mehrfach ausführbar: was es schon gibt, wird angepasst,
nicht verdoppelt.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request

# Nichts Persönliches fest eingebaut — das Projekt liegt öffentlich.
# Alle drei kommen aus der Umgebung oder von der Befehlszeile.
KONTO = os.environ.get("CF_KONTO", "").strip()
ZONE_NAME = os.environ.get("CF_ZONE", "").strip()
TUNNEL_NAME = os.environ.get("CF_TUNNEL", "familienserver").strip()

# Was von außen erreichbar wird. Alles andere bleibt im Heimnetz.
DIENSTE = [
    {"name": "vokabeln", "ziel": "http://127.0.0.1:8030",
     "titel": "Vokabeltrainer", "schutz": "personen"},
    {"name": "rezepte", "ziel": "http://127.0.0.1:9925",
     "titel": "Mealie (Rezepte)", "schutz": "personen"},
    # Immich bewusst OHNE Access: die Handy-App kann keine Anmeldeseite
    # bedienen, und der automatische Abgleich ist der halbe Nutzen. Es
    # schützt also allein Immichs eigene Anmeldung — ein Schloss statt
    # zwei. Das ist eine bewusste Abwägung, keine Nachlässigkeit.
    {"name": "fotos", "ziel": "http://127.0.0.1:2283",
     "titel": "Immich (Fotos)", "schutz": "ohne"},
    # Die MCP-Schnittstelle wird von der Claude-App gerufen, nicht von einem
    # Menschen — sie kann keine Anmeldeseite bedienen. Darum ein Diensttoken,
    # das Cloudflare schon am Rand prüft, dazu das eigene Geheimnis im Trainer.
    {"name": "mcp", "ziel": "http://127.0.0.1:8030",
     "titel": "Vokabeltrainer MCP", "schutz": "diensttoken"},
]

BASIS = "https://api.cloudflare.com/client/v4"


class CfFehler(Exception):
    pass


def ruf(pfad: str, methode: str = "GET", leib=None, token: str = ""):
    anfrage = urllib.request.Request(
        BASIS + pfad,
        data=json.dumps(leib).encode() if leib is not None else None,
        method=methode,
        headers={"Authorization": f"Bearer {token}",
                 "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(anfrage, timeout=30) as antwort:
            d = json.loads(antwort.read().decode())
    except urllib.error.HTTPError as fehler:
        try:
            d = json.loads(fehler.read().decode())
        except Exception:
            raise CfFehler(f"{methode} {pfad}: HTTP {fehler.code}") from fehler
        meldungen = "; ".join(f"{e.get('code')}: {e.get('message')}"
                              for e in d.get("errors", []))
        raise CfFehler(f"{methode} {pfad}: {meldungen or fehler.code}") from fehler
    if not d.get("success"):
        meldungen = "; ".join(f"{e.get('code')}: {e.get('message')}"
                              for e in d.get("errors", []))
        raise CfFehler(f"{methode} {pfad}: {meldungen}")
    return d.get("result")


def main() -> int:
    zerleger = argparse.ArgumentParser()
    zerleger.add_argument("--trocken", action="store_true",
                          help="nur zeigen, was geschähe")
    zerleger.add_argument("--mailadressen", default="",
                          help="Komma-getrennt, wer hereindarf")
    args = zerleger.parse_args()

    token = os.environ.get("CF_TOKEN", "").strip()
    if not token:
        print("CF_TOKEN fehlt.", file=sys.stderr)
        return 1
    if not KONTO or not ZONE_NAME:
        print("CF_KONTO und CF_ZONE müssen gesetzt sein. Die Kontokennung "
              "steht in der Adresszeile der Cloudflare-Verwaltung.",
              file=sys.stderr)
        return 1
    mailadressen = [m.strip() for m in args.mailadressen.split(",") if m.strip()]
    if not mailadressen and not args.trocken:
        print("--mailadressen fehlt: wer soll hereindürfen?", file=sys.stderr)
        return 1

    def sage(*teile):
        print(*teile, flush=True)

    # ---------------------------------------------------------- Zone
    zonen = ruf(f"/zones?name={ZONE_NAME}", token=token)
    if not zonen:
        raise CfFehler(f"Zone {ZONE_NAME} nicht gefunden")
    zone = zonen[0]["id"]
    sage(f"Zone {ZONE_NAME}: {zone}")

    if args.trocken:
        sage("\nTrockenlauf. Angelegt würde:")
        sage(f"  Tunnel »{TUNNEL_NAME}«")
        for d in DIENSTE:
            sage(f"  {d['name']}.{ZONE_NAME} -> {d['ziel']}  "
                 f"[{d['titel']}, Schutz: {d['schutz']}]")
        return 0

    # ---------------------------------------------------------- Tunnel
    vorhandene = ruf(f"/accounts/{KONTO}/cfd_tunnel?is_deleted=false", token=token)
    tunnel = next((t for t in vorhandene if t["name"] == TUNNEL_NAME), None)
    if tunnel:
        sage(f"Tunnel »{TUNNEL_NAME}« gibt es schon: {tunnel['id']}")
        geheimnis = ruf(f"/accounts/{KONTO}/cfd_tunnel/{tunnel['id']}/token",
                        token=token)
    else:
        tunnel = ruf(f"/accounts/{KONTO}/cfd_tunnel", "POST",
                     {"name": TUNNEL_NAME, "config_src": "cloudflare"},
                     token=token)
        geheimnis = tunnel.get("token") or ruf(
            f"/accounts/{KONTO}/cfd_tunnel/{tunnel['id']}/token", token=token)
        sage(f"Tunnel »{TUNNEL_NAME}« angelegt: {tunnel['id']}")
    tunnel_id = tunnel["id"]

    # ------------------------------------------------- Weiterleitungen
    eingang = [{"hostname": f"{d['name']}.{ZONE_NAME}", "service": d["ziel"]}
               for d in DIENSTE]
    eingang.append({"service": "http_status:404"})      # alles Übrige abweisen
    ruf(f"/accounts/{KONTO}/cfd_tunnel/{tunnel_id}/configurations", "PUT",
        {"config": {"ingress": eingang}}, token=token)
    sage(f"Weiterleitungen eingetragen: {len(DIENSTE)} Namen, Rest -> 404")

    # --------------------------------------------- Access VOR dem DNS
    diensttoken = None
    vorhandene_apps = ruf(f"/accounts/{KONTO}/access/apps", token=token) or []
    for d in DIENSTE:
        name = f"{d['name']}.{ZONE_NAME}"
        app = next((a for a in vorhandene_apps if a.get("domain") == name), None)

        if d["schutz"] == "ohne":
            # Kein Access davor. Eine etwaige frühere Anwendung wird entfernt,
            # sonst stünde sie weiter im Weg.
            if app:
                ruf(f"/accounts/{KONTO}/access/apps/{app['id']}", "DELETE",
                    token=token)
                sage(f"Access »{d['titel']}« entfernt (bewusst ohne Schutz)")
            else:
                sage(f"»{d['titel']}«: kein Access — es schützt die eigene "
                     f"Anmeldung des Dienstes")
            continue

        rumpf = {"name": d["titel"], "domain": name, "type": "self_hosted",
                 "session_duration": "24h",
                 "app_launcher_visible": d["schutz"] == "personen",
                 "auto_redirect_to_identity": False}
        if app:
            app = ruf(f"/accounts/{KONTO}/access/apps/{app['id']}", "PUT",
                      rumpf, token=token)
            sage(f"Access »{d['titel']}« angepasst")
        else:
            app = ruf(f"/accounts/{KONTO}/access/apps", "POST", rumpf, token=token)
            sage(f"Access »{d['titel']}« angelegt")

        regeln = ruf(f"/accounts/{KONTO}/access/apps/{app['id']}/policies",
                     token=token) or []
        for r in regeln:
            ruf(f"/accounts/{KONTO}/access/apps/{app['id']}/policies/{r['id']}",
                "DELETE", token=token)

        if d["schutz"] == "personen":
            ruf(f"/accounts/{KONTO}/access/apps/{app['id']}/policies", "POST",
                {"name": "Familie", "decision": "allow", "precedence": 1,
                 "include": [{"email": {"email": m}} for m in mailadressen]},
                token=token)
            sage(f"  Regel: {', '.join(mailadressen)} — Einmalcode per Mail")
        else:
            if diensttoken is None:
                alle = ruf(f"/accounts/{KONTO}/access/service_tokens",
                           token=token) or []
                alt = next((t for t in alle
                            if t["name"] == "claude-konnektor"), None)
                if alt:
                    ruf(f"/accounts/{KONTO}/access/service_tokens/{alt['id']}",
                        "DELETE", token=token)
                diensttoken = ruf(f"/accounts/{KONTO}/access/service_tokens",
                                  "POST",
                                  {"name": "claude-konnektor",
                                   "duration": "8760h"}, token=token)
                # SOFORT ausgeben, nicht erst am Ende: das Geheimnis gibt es
                # nur dieses eine Mal, und ein Abbruch danach machte es
                # unwiederbringlich.
                sage("")
                sage("  ── Diensttoken für den Claude-Konnektor ──")
                sage(f"  CF-Access-Client-Id:     {diensttoken['client_id']}")
                sage(f"  CF-Access-Client-Secret: {diensttoken['client_secret']}")
                sage("  (nur jetzt sichtbar)")
                sage("")
            ruf(f"/accounts/{KONTO}/access/apps/{app['id']}/policies", "POST",
                {"name": "Nur der Konnektor", "decision": "non_identity",
                 "precedence": 1,
                 # Die Regel verlangt die id des Diensttokens, NICHT die
                 # client_id — die beiden sehen ähnlich aus und sind es nicht.
                 "include": [{"service_token": {
                     "token_id": diensttoken["id"]}}]},
                token=token)
            sage("  Regel: nur das Diensttoken »claude-konnektor«")

    # ------------------------------------------------------------ DNS
    # Jetzt erst — vorher wären die Namen ungeschützt erreichbar gewesen.
    bestand = ruf(f"/zones/{zone}/dns_records?per_page=500", token=token)
    for d in DIENSTE:
        name = f"{d['name']}.{ZONE_NAME}"
        inhalt = f"{tunnel_id}.cfargotunnel.com"
        alt = next((r for r in bestand if r["name"] == name), None)
        rumpf = {"type": "CNAME", "name": d["name"], "content": inhalt,
                 "proxied": True, "ttl": 1,
                 "comment": f"Familienserver-Tunnel: {d['titel']}"}
        if alt:
            ruf(f"/zones/{zone}/dns_records/{alt['id']}", "PUT", rumpf, token=token)
            sage(f"DNS {name} angepasst")
        else:
            ruf(f"/zones/{zone}/dns_records", "POST", rumpf, token=token)
            sage(f"DNS {name} angelegt")

    ohne_schutz = [d["titel"] for d in DIENSTE if d["schutz"] == "ohne"]
    if ohne_schutz:
        sage("")
        sage("ACHTUNG: ohne Access, nur mit eigener Anmeldung erreichbar:")
        for t in ohne_schutz:
            sage(f"  {t}")
        sage("  Dort gilt: starkes Passwort, und die Anmeldeseite sollte eine")
        sage("  Ratenbegrenzung bekommen (Cloudflare: Sicherheit -> WAF ->")
        sage("  Ratenbegrenzungsregeln).")

    sage("\n" + "=" * 60)
    sage("TUNNELGEHEIMNIS — gehört nach /srv/cloudflared/.env:")
    sage(f"TUNNEL_TOKEN={geheimnis}")
    if diensttoken:
        sage("")
        sage("DIENSTTOKEN für den Claude-Konnektor — als Kopfzeilen eintragen:")
        sage(f"  CF-Access-Client-Id:     {diensttoken['client_id']}")
        sage(f"  CF-Access-Client-Secret: {diensttoken['client_secret']}")
        sage("  (Das Geheimnis wird nur dieses eine Mal angezeigt.)")
    sage("=" * 60)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except CfFehler as fehler:
        print(f"FEHLER: {fehler}", file=sys.stderr)
        sys.exit(2)
