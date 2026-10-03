"""Numbers that must come out the same in Python and in JavaScript.

The JavaScript core (web/js/core/num.js) has a twin of every function here. Both editions
promise byte-for-byte equal G-code, so nothing that depends on the platform's maths
library is used for values that reach the file:

- hypot: math.hypot of CPython (vector_norm in Modules/mathmodule.c), written out with
  exact products (Dekker split). It equals math.hypot bit for bit (checked on 2 million
  pairs) and does not depend on the Python version.
- sq: x * x. The reference wrote (h / 2) ** 2, which goes through the C library pow();
  on Windows pow(x, 2) differs from x * x in about 1 of 2000 cases. For the reference
  profile both give the same G-code (the golden test proves it), and x * x is the same
  in every language.
- tan_deg: tangent of whole degrees from a table (profiles/tables.json) made once from
  math.tan(math.radians(a)), so JavaScript's Math.tan is never asked.
- fixed / py_round / py_repr: Python's formatting and rounding rules, which JavaScript
  imitates (toFixed rounds exact halves up, Python to even).
"""
import json
import math
from pathlib import Path

_SPLIT = 134217729.0  # 2**27 + 1, Veltkamp split of a double into two halves
_DBL_MIN = 2.2250738585072014e-308


def _two_prod(a, b):
    p = a * b
    t = _SPLIT * a
    ah = t - (t - a)
    al = a - ah
    t = _SPLIT * b
    bh = t - (t - b)
    bl = b - bh
    return p, ((ah * bh - p) + ah * bl + al * bh) + al * bl


def hypot(x, y):
    """math.hypot(x, y) of CPython 3.12+, bit for bit, for finite arguments."""
    x, y = abs(x), abs(y)
    mx = x if x > y else y
    if mx == 0.0:
        return 0.0
    _, e = math.frexp(mx)
    if e < -1023:  # subnormals: CPython rescales by DBL_MIN first
        return _DBL_MIN * hypot(x / _DBL_MIN, y / _DBL_MIN)
    scale = math.ldexp(1.0, -e)
    csum, frac1, frac2 = 1.0, 0.0, 0.0
    for v in (x, y):
        v *= scale
        hi, lo = _two_prod(v, v)
        s = csum + hi
        frac2 += (csum - s) + hi
        csum = s
        frac1 += lo
    h = math.sqrt(csum - 1.0 + (frac1 + frac2))
    hi, lo = _two_prod(-h, h)
    s = csum + hi
    frac2 += (csum - s) + hi
    csum = s
    frac1 += lo
    h += (csum - 1.0 + (frac1 + frac2)) / (2.0 * h)
    return h / scale


def sq(x):
    return x * x


def fixed(x, digits):
    """f"{x:.{digits}f}" - the one place where numbers become G-code text."""
    return f"{x:.{digits}f}"


def py_round(x, digits=None):
    """Python's round(): exact value, halves to even."""
    return round(x) if digits is None else round(x, digits)


def py_repr(x):
    """str(x) of a float as Python writes it."""
    return repr(float(x))


def trim(x, digits):
    """fixed() without trailing zeros: 0.40 -> "0.4", 1.00 -> "1"."""
    s = fixed(x, digits)
    if "." in s:
        s = s.rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


_TABLES = None


def tables():
    global _TABLES
    if _TABLES is None:
        from .profiles import profiles_dir
        _TABLES = json.loads((profiles_dir() / "tables.json").read_text(encoding="utf-8"))
    return _TABLES


def tan_deg(a):
    """Tangent of a whole number of degrees, 0..89."""
    a = int(a)
    if not 0 <= a <= 89:
        raise ValueError(f"angle {a} out of 0..89")
    return float.fromhex(tables()["tan_deg"][a])


def make_tan_table():
    """What profiles/tables.json holds: math.tan(math.radians(a)) as exact hex."""
    return [math.tan(math.radians(a)).hex() for a in range(90)]


__all__ = ["hypot", "sq", "fixed", "py_round", "py_repr", "trim", "tan_deg", "Path"]
