"""
Behavioural and accounting tests for the Endogenous-Investment ABM.

Run with ``pytest`` from the repository root (see ``tests/conftest.py`` which
puts ``src/`` on the path).  The suite pins down:

* **Stock-flow consistency** — money (including the balanced-budget transfer) is
  neither created nor destroyed.
* **Labour-market accounting** — headcounts add up; output respects the
  employed workforce; the fiscal budget balances.
* **Reproducibility** — a fixed seed gives identical trajectories.
* **The headline economic result** — endogenous investment mitigates
  demand-constrained stagnation and unemployment.
"""

import pytest

from model import (
    MacroModel,
    compute_gini,
    _households,
    _firms,
)
from agents import Capitalist


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
        assert total_money(model) == pytest.approx(initial, abs=1e-7)


def test_firms_distribute_all_revenue():
    """Wages + dividends must exhaust sales every period (no retained money)."""
    model = MacroModel(theta=0.2, seed=3)
    for _ in range(50):
        model.step()
        for f in _firms(model):
            assert f.wage_bill + f.dividend_pool == pytest.approx(f.sales, abs=1e-9)


def test_no_negative_wealth():
    model = MacroModel(theta=0.3, seed=11)
    for _ in range(STEPS):
        model.step()
        for h in _households(model):
            assert h.wealth >= -1e-9


# ----------------------------------------------------------------------
# Labour market
# ----------------------------------------------------------------------

def test_headcount_adds_up():
    """Every household is either employed at exactly one firm or unemployed."""
    model = MacroModel(theta=0.15, seed=2)
    for _ in range(100):
        model.step()
        households = _households(model)
        employed = [h for h in households if h.employed]
        # employed workers appear in exactly their employer's roster
        roster = [w for f in _firms(model) for w in f.workers]
        assert len(roster) == len(employed)
        assert all(h.employer is not None for h in employed)
        assert all(not h.employed or h in h.employer.workers for h in households)


def test_output_respects_employed_labour():
    """A firm cannot produce more than its employed workers can make."""
    model = MacroModel(theta=0.3, seed=5)
    for _ in range(STEPS):
        model.step()
        for f in _firms(model):
            assert f.production <= model.productivity * len(f.workers) + 1e-9


def test_employment_capped_by_capital():
    """No firm employs more workers than its capital can equip (Leontief)."""
    model = MacroModel(theta=0.3, seed=8)
    for _ in range(STEPS):
        model.step()
        for f in _firms(model):
            assert len(f.workers) <= f.max_jobs() + 1e-9


def test_unemployment_in_bounds():
    model = MacroModel(theta=0.0, seed=1)
    for _ in range(STEPS):
        model.step()
        u = model.datacollector.get_model_vars_dataframe()["Unemployment_Rate"].iloc[-1]
        assert 0.0 <= u <= 1.0


def test_fiscal_budget_balances():
    """The tax rate stays within its cap; the transfer neither adds nor drains money."""
    model = MacroModel(theta=0.0, seed=4)  # baseline has high unemployment -> active fisc
    initial = total_money(model)
    for _ in range(200):
        model.step()
        assert 0.0 <= model.tax_rate <= model.max_tax + 1e-12
    assert total_money(model) == pytest.approx(initial, abs=1e-7)


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
# The Gini helper
# ----------------------------------------------------------------------

def test_gini_bounds():
    assert compute_gini([5, 5, 5, 5]) == pytest.approx(0.0)
    assert compute_gini([0, 0, 0, 100]) == pytest.approx(0.75)
    assert compute_gini([]) == 0.0
    assert compute_gini([0, 0]) == 0.0
    assert compute_gini([1, 2, 3]) == pytest.approx(compute_gini([10, 20, 30]))


# ----------------------------------------------------------------------
# The headline economic result
# ----------------------------------------------------------------------

def _steady(theta, seed=0, steps=STEPS, tail=50):
    m = MacroModel(theta=theta, seed=seed)
    for _ in range(steps):
        m.step()
    return m.datacollector.get_model_vars_dataframe().tail(tail).mean()


def test_baseline_is_demand_constrained():
    """No investment: high unemployment with spare capital (a demand gap, not scarcity)."""
    s = _steady(theta=0.0)
    assert s["Unemployment_Rate"] > 0.3          # deep, persistent unemployment
    assert s["Output_Gap"] > 0.15                # output well below potential
    assert s["Capital_Utilization"] < 0.95       # capital is NOT the binding constraint


def test_investment_mitigates_stagnation():
    """Investment raises output and employment and builds capital."""
    base = _steady(theta=0.0)
    inv = _steady(theta=0.15)
    assert inv["Unemployment_Rate"] < base["Unemployment_Rate"] - 0.15
    assert inv["Output"] > 1.5 * base["Output"]
    assert inv["Total_Capital"] > base["Total_Capital"]


def test_unemployment_falls_monotonically_in_theta():
    u = [_steady(theta=t)["Unemployment_Rate"] for t in (0.0, 0.05, 0.1, 0.2)]
    assert all(later <= earlier + 1e-6 for earlier, later in zip(u, u[1:]))
