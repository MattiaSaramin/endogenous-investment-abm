"""
Behavioural and accounting tests for the Cobb-Douglas core with internal
(retained-earnings) financing.

Run with ``pytest`` from the repository root (see ``tests/conftest.py`` which
puts ``src/`` on the path).  The suite pins down:

* **Stock-flow consistency** — money (incl. the infra-period firm buffer) is
  neither created nor destroyed, and the buffer returns to zero every period
  (the structural guarantee against money sequestration).
* **Distributive coherence** — markup tied to alpha; wage share = 1-alpha.
* **Essential capital** — Cobb-Douglas capacity is zero without capital.
* **The headline result** — a live supply channel: output and capital rise
  monotonically with the retention ratio, the extended economy runs
  capacity-constrained, and K/Y lands in the 2.5-3 band.
* **Long-run stability** for both the baseline and the extended economy.
"""

import pytest

from model import (
    MacroModel,
    compute_gini,
    _households,
    _firms,
)
from agents import Firm, Household, Capitalist


STEPS = 500
ALPHA = 1.0 / 3.0


def total_money(model):
    """Conserved quantity: household money + in-transit income + firm buffers."""
    hh = sum(h.wealth + h.income + h.next_income for h in _households(model))
    firm = sum(f.money_buffer for f in _firms(model))
    return hh + firm


def _steady(retention_ratio, seed=0, steps=STEPS, tail=50, **kw):
    m = MacroModel(retention_ratio=retention_ratio, seed=seed, **kw)
    for _ in range(steps):
        m.step()
    return m.datacollector.get_model_vars_dataframe().tail(tail).mean()


# ----------------------------------------------------------------------
# Stock-flow consistency + the anti-sequestration guarantee
# ----------------------------------------------------------------------

@pytest.mark.parametrize("rho", [0.0, 0.2, 0.4])
def test_money_is_conserved(rho):
    model = MacroModel(retention_ratio=rho, seed=7)
    initial = total_money(model)
    for _ in range(STEPS):
        model.step()
        assert total_money(model) == pytest.approx(initial, abs=1e-7)


@pytest.mark.parametrize("rho", [0.0, 0.4])
def test_buffer_returns_to_zero(rho):
    """Every firm's money buffer is zero at the end of every period."""
    model = MacroModel(retention_ratio=rho, seed=2)
    for _ in range(200):
        model.step()
        for f in _firms(model):
            assert f.money_buffer == pytest.approx(0.0, abs=1e-9)


def test_distribution_identity():
    """wage_bill + dividends + retained == sales for every firm, every period."""
    model = MacroModel(retention_ratio=0.4, seed=3)
    for _ in range(100):
        model.step()
        for f in _firms(model):
            assert f.wage_bill + f.dividend_pool + f.retained == pytest.approx(
                f.sales, abs=1e-9
            )


def test_dividends_non_negative():
    """The residual-payout rule never forces the owner to fund the firm."""
    model = MacroModel(retention_ratio=0.4, seed=5)
    for _ in range(STEPS):
        model.step()
        for f in _firms(model):
            assert f.dividend_pool >= -1e-9


# ----------------------------------------------------------------------
# Technology / distribution
# ----------------------------------------------------------------------

def test_markup_tied_to_alpha():
    m = MacroModel(alpha=ALPHA, seed=0)
    assert m.markup == pytest.approx(ALPHA / (1.0 - ALPHA))
    assert 1.0 / (1.0 + m.markup) == pytest.approx(1.0 - ALPHA)


def test_capital_is_essential():
    """Cobb-Douglas: with zero capital, capacity is exactly zero."""
    model = MacroModel(seed=0)
    firm = _firms(model)[0]
    firm.capital = 0.0
    firm.calculate_capacity()
    assert firm.capacity == 0.0


def test_factor_shares_match_alpha():
    s = _steady(retention_ratio=0.4)
    assert s["Wage_Share"] == pytest.approx(1.0 - ALPHA, abs=0.01)
    assert s["Profit_Share"] == pytest.approx(ALPHA, abs=0.01)


def test_output_never_exceeds_capacity():
    model = MacroModel(retention_ratio=0.4, seed=5)
    for _ in range(STEPS):
        model.step()
        for f in _firms(model):
            assert f.production <= f.capacity + 1e-9


# ----------------------------------------------------------------------
# Reproducibility
# ----------------------------------------------------------------------

def test_seed_is_deterministic():
    def final_output(seed):
        m = MacroModel(retention_ratio=0.4, seed=seed)
        for _ in range(200):
            m.step()
        return m.datacollector.get_model_vars_dataframe()["Output"].iloc[-1]

    assert final_output(42) == final_output(42)
    assert final_output(1) != final_output(2)


# ----------------------------------------------------------------------
# The Gini helper
# ----------------------------------------------------------------------

def test_gini_bounds():
    assert compute_gini([5, 5, 5, 5]) == pytest.approx(0.0)
    assert compute_gini([0, 0, 0, 100]) == pytest.approx(0.75)
    assert compute_gini([]) == 0.0
    assert compute_gini([1, 2, 3]) == pytest.approx(compute_gini([10, 20, 30]))


# ----------------------------------------------------------------------
# The headline economic result: a live supply channel
# ----------------------------------------------------------------------

def test_extended_is_capacity_constrained():
    """With high retention the economy runs at capacity (capital binds)."""
    s = _steady(retention_ratio=0.4)
    assert s["Average_Utilization"] > 0.90


def test_capital_to_output_in_band():
    """K/Y ~= rho*alpha/delta lands in the 2.5-3 band at rho = 0.4."""
    s = _steady(retention_ratio=0.4)
    ky = s["Total_Capital"] / s["Output"]
    assert 2.4 <= ky <= 3.0


def test_output_and_capital_increase_in_retention():
    rhos = (0.0, 0.1, 0.2, 0.4)
    outputs = [_steady(retention_ratio=r)["Output"] for r in rhos]
    capitals = [_steady(retention_ratio=r)["Total_Capital"] for r in rhos]
    assert all(b <= a + 1e-6 for b, a in zip(outputs, outputs[1:]))
    assert all(b <= a + 1e-6 for b, a in zip(capitals, capitals[1:]))


def test_no_collapse_extended():
    """Capital and output stay strictly positive (no death spiral)."""
    model = MacroModel(retention_ratio=0.4, seed=1)
    for _ in range(800):
        model.step()
        assert sum(f.capital for f in _firms(model)) > 1.0
        assert sum(f.production for f in _firms(model)) > 1.0


@pytest.mark.parametrize("rho", [0.0, 0.4])
def test_long_run_stability(rho):
    """No buffer creep, no drift: output at t=1000 matches t=2000."""
    model = MacroModel(retention_ratio=rho, seed=0)
    y1000 = y2000 = None
    for t in range(2000):
        model.step()
        if t == 999:
            y1000 = sum(f.production for f in _firms(model))
    y2000 = sum(f.production for f in _firms(model))
    assert y2000 == pytest.approx(y1000, rel=0.02)
    for f in _firms(model):
        assert f.money_buffer == pytest.approx(0.0, abs=1e-9)
