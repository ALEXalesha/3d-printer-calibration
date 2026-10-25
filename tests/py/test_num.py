"""num.py: the numbers that must be equal in both editions."""
import math

from hypothesis import given, strategies as st

from calib3d.core import num

coords = st.floats(min_value=-1000, max_value=1000, allow_nan=False, allow_infinity=False)


@given(coords, coords)
def test_hypot_equals_cpython(a, b):
    assert num.hypot(a, b) == math.hypot(a, b)


@given(st.floats(min_value=-1e-3, max_value=1e-3, allow_nan=False), coords)
def test_hypot_small_and_mixed(a, b):
    assert num.hypot(a, b) == math.hypot(a, b)


def test_hypot_edges():
    assert num.hypot(0.0, 0.0) == 0.0
    assert num.hypot(3.0, 4.0) == 5.0
    assert num.hypot(-0.0, 2.5) == 2.5


def test_tan_table_is_cpython():
    # The table was taken once with math.tan on Windows; another system's libm (Linux) may differ in the
    # last bit (GitHub review 25.10) - so 1 ulp of tolerance, not exact ==. The table itself does not change.
    for a in range(90):
        want = math.tan(math.radians(a))
        assert abs(num.tan_deg(a) - want) <= math.ulp(want), a


def test_trim():
    assert num.trim(0.4, 2) == "0.4"
    assert num.trim(1.0, 1) == "1"
    assert num.trim(12.0, 1) == "12"
    assert num.trim(0.0, 3) == "0"
    assert num.trim(2.85, 3) == "2.85"


def test_python_rounding_rules():
    assert num.fixed(0.125, 2) == "0.12"     # exact half - to even
    assert num.fixed(0.375, 2) == "0.38"
    assert num.py_round(2.5) == 2 and num.py_round(3.5) == 4
    assert num.py_repr(1.0) == "1.0" and num.py_repr(0.2) == "0.2"
