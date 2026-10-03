"""Copy three.js (MIT) from node_modules into web/vendor/three.js as a plain script.

The page must work from file:// where ES modules are blocked, so the CommonJS build is
wrapped: the result sets window.THREE. Run after updating three in package.json.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "node_modules" / "three" / "build" / "three.cjs"
OUT = ROOT / "web" / "vendor" / "three.js"

if __name__ == "__main__":
    body = SRC.read_text(encoding="utf-8")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("// three.js (MIT, https://threejs.org), CommonJS build wrapped by tools/build_vendor.py\n"
                   "(function () {\nvar exports = {};\n" + body + "\nwindow.THREE = exports;\n})();\n",
                   encoding="utf-8", newline="\n")
    (OUT.parent / "three.LICENSE").write_text((ROOT / "node_modules" / "three" / "LICENSE").read_text(encoding="utf-8"),
                                              encoding="utf-8", newline="\n")
    print(OUT, OUT.stat().st_size)
