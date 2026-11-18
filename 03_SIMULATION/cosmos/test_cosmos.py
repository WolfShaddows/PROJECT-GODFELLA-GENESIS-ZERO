import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from cosmos_engine import Cosmology, expansion_rate

def test_cosmology():

    model = Cosmology()

    assert abs(model.omega_k) < 1e-10

    h_today = expansion_rate(1.0, model)
    assert abs(h_today - model.H0) < 1e-8

    h_early = expansion_rate(0.001, model)
    assert h_early > h_today

    print("PASS: Flat universe consistency")
    print("PASS: Present expansion normalization")
    print("PASS: Early expansion rate")
    print("ALL TESTS PASSED")

if __name__ == "__main__":
    test_cosmology()
