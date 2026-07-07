"""
Behavioural and accounting tests for the Endogenous-Investment ABM.

Run with ``pytest`` from the repository root (see ``tests/conftest.py`` which
puts ``src/`` on the path).  The suite pins down three things:

* **Stock-flow consistency** — money is neither created nor destroyed.
* **Reproducibility** — a fixed seed gives identical trajectories.
* **The headline economic result** — endogenous investment mitigates
  demand-constrained stagnation.
"""

import numpy as np
import pytest

from model import (
    MacroModel,
    compute_gini,
    _households,
    _firms,
)
from agents import Firm, Household, Capitalist


STEPS = 400


def total_money(model):
    """Conserved quantity: money on hand plus income in transit."""
    return sum(h.wealth + h.income for h in _households(model))


# ----------------------------------------------------------------------
# Stock-flow consistency
# ----------------------------------------------------------------------

@pytest.mark.parametrize("theta", [0.0, 0.15, 0.4])
def test_money_is_conserved(theta):
    model = MacroModel(theta=theta, seed=7)
    initial = total_money(model)

    for _ in range(STEPS):
        model.step()
        assert total_money(model) == pytest.approx(initial, abs=1e-8)


def test_firms_distribute_all_revenue():
    """Wages + dividends must exhaust sales every period (no retained money)."""
    model = MacroModel(theta=0.2, seed=3)
    for _ in range(50):
        model.step()
        for f in _firms(model):
            assert f.wage_bill + f.dividend_pool == pytest.approx(f.sales, abs=1e-9)


def test_no_negative_wealth():
    """Households can never spend money they do not have."""
    model = MacroModel(theta=0.3, seed=11)
    for _ in range(STEPS):
        model.step()
        for h in _households(model):
            assert h.wealth >= -1e-9


# ----------------------------------------------------------------------
# Reproducibility
# ----------------------------------------------------------------------

def test_seed_is_deterministic():
    def final_output(seed):
        m = MacroModel(theta=0.15, seed=seed)
        for _ in range(200):
            m.step()
        return m.datacollector.get_model_vars_dataframe()["Output"].iloc[-1]

    assert final_output(42) == final_output(42)
    assert final_output(1) != final_output(2)


# ----------------------------------------------------------------------
# Accounting identities in the capacity / distribution rules
# ----------------------------------------------------------------------

def test_capacity_has_labour_floor():
    """With zero capital, capacity is exactly A * L (the labour-only floor)."""
    model = MacroModel(seed=0)
    firm = _firms(model)[0]
    firm.capital = 0.0
    firm.calculate_capacity()
    assert firm.capacity == pytest.approx(firm.productivity * len(firm.workers))


def test_output_never_exceeds_capacity():
    model = MacroModel(theta=0.3, seed=5)
    for _ in range(STEPS):
        model.step()
        for f in _firms(model):
            assert f.production <= f.capacity + 1e-9


# ----------------------------------------------------------------------
# The Gini helper
# ----------------------------------------------------------------------

def test_gini_bounds():
    assert compute_gini([5, 5, 5, 5]) == pytest.approx(0.0)          # equality
    assert compute_gini([0, 0, 0, 100]) == pytest.approx(0.75)       # n=4 max
    assert compute_gini([]) == 0.0
    assert compute_gini([0, 0]) == 0.0
    # scale invariance
    assert compute_gini([1, 2, 3]) == pytest.approx(compute_gini([10, 20, 30]))


# ----------------------------------------------------------------------
# The headline economic result
# ----------------------------------------------------------------------

def _steady(theta, seed=0, steps=STEPS, tail=50):
    m = MacroModel(theta=theta, seed=seed)
    for _ in range(steps):
        m.step()
    df = m.datacollector.get_model_vars_dataframe().tail(tail).mean()
    return df


def test_baseline_stagnates_below_capacity():
    """With no investment the economy is demand-constrained and holds no capital."""
    s = _steady(theta=0.0)
    assert s["Output_Gap"] > 0.2          # a large, persistent output gap
    assert s["Total_Capital"] < 1.0       # idle savings, capital depreciates away


def test_investment_mitigates_stagnation():
    """Positive investment raises output, builds capital and shrinks the gap."""
    base = _steady(theta=0.0)
    inv = _steady(theta=0.15)

    assert inv["Output"] > 1.5 * base["Output"]        # materially higher output
    assert inv["Output_Gap"] < base["Output_Gap"]      # smaller demand gap
    assert inv["Total_Capital"] > base["Total_Capital"]  # sustained capital


def test_output_increases_monotonically_in_theta():
    """More investment -> more steady-state output (over a sensible range)."""
    outputs = [_steady(theta=t)["Output"] for t in (0.0, 0.05, 0.1, 0.2)]
    assert all(b <= a + 1e-6 for b, a in zip(outputs, outputs[1:]))
