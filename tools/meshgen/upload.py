#!/usr/bin/env python3
"""
Carica le mesh GLB su Roblox tramite Open Cloud (Assets API) e scrive il manifest
`src/Shared/Catalog/MeshAssets.luau` con gli ID degli asset Model risultanti (l'importer accetta glTF binario; l'FBX scritto a mano veniva rifiutato).

Richiede: chiave API con scope asset:read + asset:write nell'header x-api-key
(in questo ambiente la inietta il proxy su apis.roblox.com) e l'ID utente creatore.

Uso: python3 tools/meshgen/upload.py --creator <userId> [--only nome ...] [--force]
Gli asset già caricati (assets/meshes/manifest.json, con hash del file invariato) vengono saltati.
"""
from __future__ import annotations
import argparse, hashlib, json, os, sys, time, urllib.request, urllib.error, uuid

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MESHES = os.path.join(ROOT, "assets", "meshes")
MANIFEST = os.path.join(MESHES, "manifest.json")
LUAU_OUT = os.path.join(ROOT, "src", "Shared", "Catalog", "MeshAssets.luau")
API = "https://apis.roblox.com/assets/v1"


def api_key():
    return os.environ.get("ROBLOX_API_KEY", "")


def request(method, url, body=None, headers=None):
    req = urllib.request.Request(url, data=body, method=method)
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    if api_key():
        req.add_header("x-api-key", api_key())
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, r.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")


def multipart(fields, file_field, filename, content, content_type):
    boundary = "----VivaioBoundary" + uuid.uuid4().hex
    parts = []
    for name, (value, ctype) in fields.items():
        parts.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"{name}\"\r\nContent-Type: {ctype}\r\n\r\n{value}\r\n".encode())
    parts.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"{file_field}\"; filename=\"{filename}\"\r\nContent-Type: {content_type}\r\n\r\n".encode() + content + b"\r\n")
    parts.append(f"--{boundary}--\r\n".encode())
    return b"".join(parts), f"multipart/form-data; boundary={boundary}"


def upload_mesh(path, name, creator):
    with open(path, "rb") as f:
        content = f.read()
    meta = {
        "assetType": "Model",
        "displayName": f"Vivaio · {name}",
        "description": "Mesh stilizzata generata proceduralmente per «Il Vivaio delle Nuvole».",
        "creationContext": {"creator": {"userId": str(creator)}},
    }
    body, ctype = multipart({"request": (json.dumps(meta), "application/json")}, "fileContent", f"{name}.glb", content, "model/gltf-binary")
    status, text = request("POST", f"{API}/assets", body, {"Content-Type": ctype})
    if status != 200:
        raise RuntimeError(f"upload {name}: HTTP {status} {text[:300]}")
    op = json.loads(text)
    op_id = op.get("operationId") or op.get("path", "").split("/")[-1]
    for attempt in range(40):
        time.sleep(1.5 if attempt < 5 else 3)
        status, text = request("GET", f"{API}/operations/{op_id}")
        if status != 200:
            continue
        data = json.loads(text)
        if data.get("done"):
            if "error" in data:
                raise RuntimeError(f"operation {name}: {data['error']}")
            return data["response"]
    raise RuntimeError(f"operation {name}: timeout")


def tri_count(path):
    """Numero di triangoli leggendo l'header JSON del GLB."""
    import struct as _s
    with open(path, "rb") as f:
        f.seek(12)
        ln, _ = _s.unpack("<II", f.read(8))
        js = json.loads(f.read(ln).decode())
    acc = js["accessors"][js["meshes"][0]["primitives"][0]["indices"]]
    return acc["count"] // 3


def file_hash(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()[:16]


def write_luau(manifest):
    lines = [
        "--!nonstrict",
        "-- GENERATO da tools/meshgen/upload.py — ID degli asset Model (glTF) caricati via Open Cloud.",
        "-- Il server li carica con InsertService:LoadAsset e li espone in ReplicatedStorage.MeshTemplates.",
        "return {",
    ]
    for name in sorted(manifest):
        e = manifest[name]
        lines.append(f'\t{name} = {{ AssetId = {e["assetId"]}, Tris = {e.get("tris", 0)} }},')
    lines.append("}")
    with open(LUAU_OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--creator", required=True)
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()
    manifest = {}
    if os.path.exists(MANIFEST):
        with open(MANIFEST) as f:
            manifest = json.load(f)
    files = sorted(f for f in os.listdir(MESHES) if f.endswith(".glb"))
    failures = []
    for fn in files:
        name = fn[:-4]
        if args.only and name not in args.only:
            continue
        path = os.path.join(MESHES, fn)
        h = file_hash(path)
        prev = manifest.get(name)
        if prev and prev.get("hash") == h and not args.force:
            print(f"{name:16s} invariato → asset {prev['assetId']}")
            continue
        try:
            resp = upload_mesh(path, name, args.creator)
            asset_id = int(resp["assetId"])
            manifest[name] = {"assetId": asset_id, "hash": h, "revisionId": resp.get("revisionId"), "state": resp.get("moderationResult", {}).get("moderationState"), "tris": tri_count(path)}
            print(f"{name:16s} caricato → asset {asset_id} ({manifest[name]['state']})")
        except Exception as e:  # noqa
            failures.append((name, str(e)))
            print(f"{name:16s} ERRORE: {e}")
        with open(MANIFEST, "w") as f:
            json.dump(manifest, f, indent=1, sort_keys=True)
        time.sleep(0.5)
    write_luau(manifest)
    print(f"\nManifest: {len(manifest)} asset → {LUAU_OUT}")
    if failures:
        print("Falliti:", failures)
        sys.exit(1)


if __name__ == "__main__":
    main()
