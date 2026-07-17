"""
Behavioural and accounting tests for the Cobb-Douglas core with an endogenous
labour market (roadmap point 11).

Run with ``pytest`` from the repository root.  The suite pins down:

* **Stock-flow consistency** — money (incl. the infra-period buffer) is conserved
  even with unemployed households; the buffer returns to zero every period.
* **Distribution** — fixed wage; profit is the residual and stays positive; the
  wage share is a measured outcome bounded above by ``1 - alpha``.
* **Labour-market accounting** — headcounts add up, ``L_agg <= N`` (the cap that
  prevents the AK degeneration), no hiring beyond the profit-max point.
* **The demand channel bites** (the point of the task): a negative demand shock
  lowers employment and the wage bill.
* **Reproducibility and stability.**
"""

import pytest

from model import (
    MacroModel,
    compute_gini,
    _households,
    _firms,
)
from agents import Firm, Household, Capitalist


STEPS = 1500
ALPHA = 1.0 / 3.0
REF_RHO = 0.40          # a viable, demand-constrained reference scenario


def total_money(model):
    hh = sum(h.wealth + h.income + h.next_income for h in _households(model))
    return hh + sum(f.money_buffer for f in _firms(model))


def _steady(retention_ratio=REF_RHO, seed=0, steps=STEPS, tail=50, **kw):
    m = MacroModel(retention_ratio=retention_ratio, seed=seed, **kw)
    for _ in range(steps):
        m.step()
    return m.datacollector.get_model_vars_dataframe().tail(tail).mean()


# ----------------------------------------------------------------------
# Stock-flow consistency
# ----------------------------------------------------------------------

@pytest.mark.parametrize("rho", [0.35, 0.40])
def test_money_is_conserved(rho):
    model = MacroModel(retention_ratio=rho, seed=7)
    initial = total_money(model)
    for _ in range(600):
        model.step()
        assert total_money(model) == pytest.approx(initial, abs=1e-7)


@pytest.mark.parametrize("rho", [0.35, 0.40])
def test_buffer_returns_to_zero(rho):
    model = MacroModel(retention_ratio=rho, seed=2)
    for _ in range(300):
        model.step()
        for f in _firms(model):
            assert f.money_buffer == pytest.approx(0.0, abs=1e-9)


def test_distribution_identity():
    model = MacroModel(retention_ratio=REF_RHO, seed=3)
    for _ in range(300):
        model.step()
        for f in _firms(model):
            assert f.wage_bill + f.dividend_pool + f.retained == pytest.approx(
                f.sales, abs=1e-9
            )


def test_gross_profit_and_dividends_non_negative():
    """The firm never hires beyond MPL = w_bar, so profit stays >= 0; the residual
    payout is never negative (the owner never funds the firm)."""
    model = MacroModel(retention_ratio=REF_RHO, seed=5)
    for _ in range(600):
        model.step()
        for f in _firms(model):
            assert f.gross_profit >= -1e-9
            assert f.dividend_pool >= -1e-9


# ----------------------------------------------------------------------
# Labour-market accounting
# ----------------------------------------------------------------------

def test_employment_never_exceeds_workforce():
    """L_agg <= N by construction — the cap that restores decreasing returns."""
    model = MacroModel(retention_ratio=REF_RHO, seed=8)
    for _ in range(400):
        model.step()
        assert sum(len(f.workers) for f in _firms(model)) <= model.num_households


def test_headcount_adds_up():
    model = MacroModel(retention_ratio=REF_RHO, seed=2)
    for _ in range(200):
        model.step()
        households = _households(model)
        employed = [h for h in households if h.employed]
        roster = [w for f in _firms(model) for w in f.workers]
        assert len(roster) == len(employed)
        assert all(not h.employed or h in h.employer.workers for h in households)


def test_no_hiring_beyond_profit_max():
    model = MacroModel(retention_ratio=REF_RHO, seed=4)
    for _ in range(400):
        model.step()
        for f in _firms(model):
            assert len(f.workers) <= f.L_profitmax + 1.0   # +1 for integer floor


def test_wage_share_bounded_by_labour_elasticity():
    """Fixed wage + no hiring past MPL = w_bar => wage share <= 1 - alpha."""
    s = _steady()
    assert s["Wage_Share"] <= (1.0 - ALPHA) + 1e-6


def test_unemployment_in_bounds():
    model = MacroModel(retention_ratio=REF_RHO, seed=1)
    for _ in range(400):
        model.step()
        u = model.datacollector.get_model_vars_dataframe()["Unemployment_Rate"].iloc[-1]
        assert 0.0 <= u <= 1.0


# ----------------------------------------------------------------------
# Technology
# ----------------------------------------------------------------------

def test_capital_is_essential():
    """With zero capital, capacity and production are zero (Cobb-Douglas)."""
    model = MacroModel(seed=0)
    f = _firms(model)[0]
    f.capital = 0.0
    f.faced_demand = 10.0
    f.step_production()
    assert f.capacity == 0.0
    assert f.production == 0.0


# ----------------------------------------------------------------------
# The demand channel must bite (the point of the task)
# ----------------------------------------------------------------------

def test_demand_shock_lowers_employment_and_wage_bill():
    """A negative demand shock (lower c0) must reduce employment and the wage
    bill; otherwise the labour market is cosmetic."""
    strong = _steady(c0=2.0)
    weak = _steady(c0=1.2)

    assert weak["Employment"] < strong["Employment"] - 1.0
    strong_wage_bill = strong["Wage_Share"] * strong["Output"]
    weak_wage_bill = weak["Wage_Share"] * weak["Output"]
    assert weak_wage_bill < strong_wage_bill


# ----------------------------------------------------------------------
# Retention, capital, stability
# ----------------------------------------------------------------------

def test_capital_increases_in_retention():
    """More retention -> more capital (robust, regardless of the output sign)."""
    caps = [_steady(retention_ratio=r)["Total_Capital"] for r in (0.35, 0.40, 0.45)]
    assert all(b >= a - 1e-6 for a, b in zip(caps, caps[1:]))


def test_reference_is_viable_and_bounded():
    """The reference neither collapses (Y -> 0) nor diverges (AK growth): output
    stays in a bounded plausible band over a long run (mild oscillation is fine)."""
    model = MacroModel(retention_ratio=REF_RHO, seed=0)
    tail = []
    for t in range(2000):
        model.step()
        if t >= 1500:
            tail.append(sum(f.production for f in _firms(model)))
    assert min(tail) > 50.0        # no collapse
    assert max(tail) < 300.0       # no AK divergence
    assert max(tail) - min(tail) < 0.15 * (sum(tail) / len(tail))  # bounded fluctuation


def test_seed_is_deterministic():
    def final_output(seed):
        m = MacroModel(retention_ratio=REF_RHO, seed=seed)
        for _ in range(300):
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
