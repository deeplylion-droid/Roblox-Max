#!/usr/bin/env python3
"""
Costruisce il place con Rojo e lo pubblica sull'esperienza tramite Open Cloud.
Uso: python3 tools/publish.py --universe 10769836705 --place 103319589301496 [--saved] [--rojo rojo]
Richiede una chiave API con lo scope universe-places:write (in questo ambiente la inietta il proxy).
"""
import argparse, json, os, subprocess, sys, urllib.request, urllib.error

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "build", "IlVivaioDelleNuvole.rbxlx")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--universe", required=True)
    ap.add_argument("--place", required=True)
    ap.add_argument("--saved", action="store_true", help="salva una versione senza pubblicarla")
    ap.add_argument("--rojo", default="rojo")
    ap.add_argument("--no-build", action="store_true")
    args = ap.parse_args()
    if not args.no_build:
        subprocess.run([args.rojo, "build", os.path.join(ROOT, "default.project.json"), "-o", OUT], check=True)
    with open(OUT, "rb") as f:
        body = f.read()
    kind = "Saved" if args.saved else "Published"
    url = f"https://apis.roblox.com/universes/v1/{args.universe}/places/{args.place}/versions?versionType={kind}"
    req = urllib.request.Request(url, data=body, method="POST")
    req.add_header("Content-Type", "application/xml")
    key = os.environ.get("ROBLOX_API_KEY")
    if key:
        req.add_header("x-api-key", key)
    try:
        with urllib.request.urlopen(req, timeout=180) as r:
            print(f"{kind}: versione {json.loads(r.read())['versionNumber']}")
    except urllib.error.HTTPError as e:
        print("Errore", e.code, e.read().decode("utf-8", "replace")[:400])
        sys.exit(1)


if __name__ == "__main__":
    main()
