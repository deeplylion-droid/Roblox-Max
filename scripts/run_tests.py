#!/usr/bin/env python3
"""
Esegue i test e la simulazione economica fuori da Roblox con il CLI `luau`.
Copia i moduli condivisi "puri" (senza Instance) in una cartella temporanea, riscrive i
`require(script.Parent...)` in require relativi e inietta uno shim minimo di Vector3/Color3/Enum.

Uso:  python3 scripts/run_tests.py [--luau PATH]
"""
import argparse, os, re, shutil, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHARED = os.path.join(ROOT, "src", "Shared")
PURE = {
    "Config", "Strings", "Theme", "Types", "DefaultData", "LayoutValidator", "Remotes",
    "Util/Signal", "Util/TableUtil", "Util/Format", "Util/TimeUtil", "Util/GridUtil",
    "Catalog/Creatures", "Catalog/Defenses", "Catalog/Commissions", "Catalog/Cosmetics",
    "Catalog/Album", "Catalog/Decorations", "Catalog/Themes", "Catalog/SimulatedVivai",
}
SHIM = '''
local Vector3 = { new = function(x, y, z) return { X = x or 0, Y = y or 0, Z = z or 0 } end }
local Color3 = {
	fromRGB = function(r, g, b) return { R = r / 255, G = g / 255, B = b / 255, Lerp = function(self, o, t) return self end } end,
	new = function(r, g, b) return { R = r or 0, G = g or 0, B = b or 0, Lerp = function(self, o, t) return self end } end,
}
local UDim = { new = function(s, o) return { Scale = s, Offset = o } end }
local EnumMeta = { __index = function(t, k) local v = setmetatable({ Name = k }, { __index = function(_, k2) return { Name = k2 } end }) rawset(t, k, v) return v end }
local Enum = setmetatable({}, EnumMeta)
'''

def bundle(dst):
    for rel in PURE:
        src = os.path.join(SHARED, rel + ".luau")
        name = rel.split("/")[-1]
        with open(src, encoding="utf-8") as f:
            code = f.read()
        # require(script.Parent.X.Y) / require(game:GetService(...).Shared.X.Y) -> require("./Y")
        def repl(m):
            inner = m.group(1)
            last = re.split(r"[.\)]", inner.strip())[-1]
            return f'require("./{last}")'
        code = re.sub(r"require\(((?:script|game)[^)]*(?:\([^)]*\))?[^)]*)\)", repl, code)
        code = code.replace("--!nonstrict", "--!nonstrict\n" + SHIM, 1)
        with open(os.path.join(dst, name + ".luau"), "w", encoding="utf-8") as f:
            f.write(code)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--luau", default=shutil.which("luau") or "luau")
    args = ap.parse_args()
    tmp = tempfile.mkdtemp(prefix="vivaio_tests_")
    try:
        bundle(tmp)
        for script in ("tests.luau", "simulate_economy.luau"):
            shutil.copy(os.path.join(ROOT, "scripts", script), os.path.join(tmp, script))
            print(f"\n=== {script} ===")
            r = subprocess.run([args.luau, script], cwd=tmp, capture_output=True, text=True)
            print(r.stdout)
            if r.returncode != 0:
                print(r.stderr, file=sys.stderr)
                sys.exit(r.returncode)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

if __name__ == "__main__":
    main()
