"""
Macro model for the Endogenous-Investment Keynesian ABM
(normalised-CES core + endogenous labour market — roadmap point 11 + brief 04).

Single-good, fixed-price (numeraire = 1), stock-flow-consistent circular flow of
income.  Production is a *normalised* CES with elasticity of substitution ``sigma``
(``sigma = 1`` is the Cobb-Douglas core; ``sigma -> 0`` is Leontief); firms hire
endogenously at a fixed wage ``w_bar``; the unemployed earn nothing, so employment
drives demand.

Period sequence (employment is set *before* households form demand, because
expected income depends on employment status) — UNCHANGED by brief 04:

    1. firms form expectations, compute desired employment; the labour market
       fires the excess and fills vacancies (random matching) -> employment
    2. households form consumption demand (income = wage if employed, else 0;
       plus dividends for capitalists)
    3. firms plan investment (profit flow, accelerator on last utilisation)
    4. firms register demand (consumption + investment)
    5. firms produce: Y = min(demand, Y*(K, L)); ration; set u
    6. firm accounting: wage_bill = w_bar*L, retained (= I_planned), residual dividends
    7. investment settlement: pay I_delivered; K(t+1) = (1-delta)K + I_delivered;
       buffer returns to zero
    8. household settlement (credit income, pay for delivered goods)

Conserved quantity (checked in ``tests/``): at a period boundary the buffer is
zero, so ``sum(household wealth + income) + sum(firm money_buffer)`` is constant.
The unemployed simply receive nothing, so money is still conserved.
"""

import mesa
import numpy as np

from agents import (
    Firm,
    Household,
    Capitalist,
    ces_capacity,
    ces_wage_share_profitmax,
    _Y0,
)


# ============================================================
# Normalisation anchor — a MODELLING CHOICE, measured once and frozen
# ============================================================
#
# The normalised CES needs a base point ``(K0, L0, Y0)`` that is the SAME for every
# sigma and every rho on the grid, otherwise the normalisation normalises nothing
# (Klump & Saam 2008).  These per-firm values were measured once on branch
# ``labour-market`` (the Cobb-Douglas core, i.e. sigma = 1) at:
#
#     retention_ratio = 0.40, seeds {0, 1, 2}, 2000 steps, mean of the last 50
#     observations, all other parameters at their defaults below
#     (initial_capital = 40.0, wage_rate = 0.9, c0 = 2.0, N = 100, 10 firms).
#
# Measured aggregates: K = 418.7356984217038, L = 73.95333333333333 over 10 firms.
#
# Anchoring at rho = 0.40 centres the experiment on the reference scenario of the
# labour-market branch.  The values are per firm; with constant returns to scale the
# normalised CES is homogeneous of degree 1 in (K, L), so scaling (K0, L0, Y0) by a
# common factor leaves the function identical — per-firm vs aggregate anchoring is
# immaterial, provided Y0 is derived from the same K0, L0.
#
# At sigma = 1 the anchor is irrelevant: the identity with Cobb-Douglas holds for any
# (K0, L0) as long as Y0 is *computed* (agents._Y0), never measured.  It matters only
# for sigma != 1, where it fixes the point through which every sigma-variant passes.
ANCHOR_K0 = 41.87356984217038
ANCHOR_L0 = 7.395333333333333


# ============================================================
# Metrics
# ============================================================

def _households(model):
    return [a for a in model.agents if isinstance(a, Household)]


def _firms(model):
    return [a for a in model.agents if isinstance(a, Firm)]


def compute_gini(values):
    """Gini coefficient of a list of non-negative values (0 = equality)."""
    x = np.sort(np.asarray(values, dtype=float))
    n = x.size
    total = x.sum()
    if n == 0 or total <= 0:
        return 0.0
    index = np.arange(1, n + 1)
    return (2.0 * np.sum(index * x) / (n * total)) - (n + 1.0) / n


def compute_income_gini(model):
    return compute_gini([h.income for h in _households(model)])


def compute_wealth_gini(model):
    net_worth = [
        h.net_worth() if isinstance(h, Capitalist) else h.wealth
        for h in _households(model)
    ]
    return compute_gini(net_worth)


def compute_output(model):
    return sum(f.production for f in _firms(model))


def compute_employment(model):
    return sum(len(f.workers) for f in _firms(model))


def compute_unemployment(model):
    n = model.num_households
    return 1.0 - compute_employment(model) / n if n > 0 else 0.0


def compute_potential_output(model):
    """Full-employment output benchmark: the CES capacity at ``(K_agg, N)``.

    Evaluated with the per-firm anchor, which is legitimate because the normalised
    CES has constant returns (see the ANCHOR_* note above).
    """
    k = compute_aggregate_capital(model)
    n = model.num_households
    if k <= 0 or n <= 0:
        return 0.0
    return ces_capacity(
        k, n, model.productivity, model.K0, model.L0, model.pi0, model.sigma
    )


def compute_output_gap(model):
    """Gap of output below full-employment potential (Teglio's output-gap concept)."""
    potential = compute_potential_output(model)
    if potential <= 0:
        return 0.0
    return (potential - compute_output(model)) / potential


def compute_aggregate_capital(model):
    return sum(f.capital for f in _firms(model))


def compute_average_utilization(model):
    """Mean firm utilisation Y / profit-max capacity (weak-demand signal)."""
    firms = _firms(model)
    if not firms:
        return 0.0
    return sum(f.utilization for f in firms) / len(firms)


def compute_consumption(model):
    return sum(h.actual_consumption for h in _households(model))


def compute_investment(model):
    return model.total_investment_realised


def compute_total_money_buffer(model):
    return sum(f.money_buffer for f in _firms(model))


def compute_wage_share(model):
    """Aggregate wage bill / sales — a *measured outcome*.

    Upper bound is :func:`compute_wage_share_profitmax`, which equals ``1 - pi0``
    only at sigma = 1.
    """
    firms = _firms(model)
    sales = sum(f.sales for f in firms)
    if sales <= 0:
        return 0.0
    return sum(f.wage_bill for f in firms) / sales


def compute_wage_share_profitmax(model):
    """Wage share the firm *would* post at its profit-max point (brief 04 §9.4).

    Independent of K under constant returns; the sigma-dependent ceiling on the
    realised wage share.  This is the second of the two channels through which sigma
    acts: sigma changes the profit-max K/L ratio at the given wage, hence the share
    of output going to labour, *in the opposite direction* to the employment loss.
    """
    return ces_wage_share_profitmax(
        model.productivity, model.wage_rate, model.K0, model.L0, model.pi0, model.sigma
    )


def compute_profit_share(model):
    firms = _firms(model)
    sales = sum(f.sales for f in firms)
    if sales <= 0:
        return 0.0
    return sum(f.gross_profit for f in firms) / sales


# --- regime diagnostics (brief 04 §9) -------------------------------------

def _binding(model, label):
    """Share of firms whose employment is held down by ``label`` this period.

    ``workforce`` overrides the planned limit: a firm that wanted more workers than
    the unemployed pool could supply is labour-constrained whatever it had planned.
    """
    firms = _firms(model)
    if not firms:
        return 0.0
    hit = sum(
        1
        for f in firms
        if (f.binding_constraint if not f.labour_rationed else "workforce") == label
    )
    return hit / len(firms)


def compute_bound_by_demand(model):
    return _binding(model, "demand")


def compute_bound_by_profitmax(model):
    return _binding(model, "profitmax")


def compute_bound_by_capital(model):
    """sigma < 1 only: demand above Y_max(K), unreachable at any finite L."""
    return _binding(model, "capital")


def compute_bound_by_workforce(model):
    return _binding(model, "workforce")


def compute_cash_constrained_frac(model):
    households = _households(model)
    if not households:
        return 0.0
    return sum(1 for h in households if h.cash_constrained) / len(households)


# ============================================================
# Model
# ============================================================

class MacroModel(mesa.Model):
    """Normalised-CES core with an endogenous labour market and a fixed wage.

    Parameters
    ----------
    sigma : float
        Elasticity of substitution between capital and labour.  ``1.0`` (default) is
        the Cobb-Douglas core and reproduces branch ``labour-market`` exactly;
        ``sigma -> 0`` approaches Leontief.  The empirical literature puts sigma
        below unity and rejects Cobb-Douglas — Chirinko (2008) 0.40–0.60, Chirinko &
        Mallick (2017) ~0.40, Knoblach, Roessler & Zwerschke (2020) meta-regression
        0.45–0.87; the Fed's SIGMA model uses 0.5.  Karabarbounis & Neiman (2014)
        dissent with sigma > 1.  Treated as a sweep, not a point estimate.
    pi0 : float
        Capital share at the base point (= the Cobb-Douglas capital elasticity, the
        old ``alpha``).  There is deliberately only one notion of the capital share
        in the code.
    K0, L0 : float
        Normalisation anchor, per firm.  A modelling choice, measured once and frozen
        — see the ANCHOR_* note at the top of this module.  ``Y0`` is *derived*
        (``A*K0^pi0*L0^(1-pi0)``), never measured.
    delta, productivity, initial_capital : float
        Depreciation, A, and K(0) per firm.  ``initial_capital`` is held fixed across
        any sigma/rho grid: the model has multiple equilibria and a viability
        threshold near rho = 0.30, so K(0) selects the basin.
    wage_rate : float
        The fixed wage ``w_bar`` per employed worker.  This is the distributive
        parameter (it replaced ``markup``): profit is the residual ``sales - w_bar*L``,
        so the wage share is a measured outcome, bounded above by the profit-max wage
        share (``1-pi0`` only at sigma = 1).
    retention_ratio, beta, target_utilization, investment_floor : float
        Internal-financing investment rule (unchanged from the core).
    c0, c1, capitalist_mpc, wealth_effect : float
        Consumption function terms.  ``c0`` and ``wealth_effect`` are demand levers
        (chosen values, not empirical estimates).
    seed : int or None
        Seed for the model's random stream (network, hiring/firing order).

    Notes
    -----
    The workforce cap ``L <= N`` (there are only ``num_households`` workers) is what
    restores decreasing returns to capital: with unlimited labour and a fixed wage,
    ``L_profitmax ∝ K`` gives ``Y* ∝ K`` (an AK model with no steady state).
    """

    def __init__(
        self,
        num_firms=10,
        num_households=100,
        pct_capitalists=0.10,

        # Technology
        sigma=1.0,
        pi0=1.0 / 3.0,
        K0=ANCHOR_K0,
        L0=ANCHOR_L0,
        delta=0.05,
        productivity=1.0,
        initial_capital=40.0,

        # Distribution
        wage_rate=0.9,

        # Internal financing / investment
        retention_ratio=0.40,
        beta=0.5,
        target_utilization=0.90,
        investment_floor=0.10,

        # Consumption
        c0=2.0,
        c1=0.9,
        capitalist_mpc=0.4,
        wealth_effect=0.05,

        seed=None,
    ):
        super().__init__(seed=seed)

        if not (0.0 < pi0 < 1.0):
            raise ValueError("pi0 must be in (0, 1)")
        if sigma <= 0.0:
            raise ValueError("sigma must be > 0")
        if K0 <= 0.0 or L0 <= 0.0:
            raise ValueError("the normalisation anchor (K0, L0) must be positive")

        # --- parameters -------------------------------------------------
        self.num_firms = num_firms
        self.num_households = num_households

        self.sigma = sigma
        self.pi0 = pi0
        self.K0 = K0
        self.L0 = L0
        #: Base-point capacity — derived, not a free parameter (brief 04 §2.3).
        self.Y0 = _Y0(productivity, K0, L0, pi0)
        self.delta = delta
        self.productivity = productivity
        self.wage_rate = wage_rate

        self.retention_ratio = retention_ratio
        self.beta = beta
        self.target_utilization = target_utilization
        self.investment_floor = investment_floor

        self.c0 = c0
        self.c1 = c1
        self.capitalist_mpc = capitalist_mpc
        self.wealth_effect = wealth_effect

        # --- economy-wide flow variables --------------------------------
        self.total_investment_demand = 0.0
        self.total_investment_realised = 0.0
        self.investment_rationing = 1.0

        # --- build firms ------------------------------------------------
        firms = [
            Firm(self, productivity=productivity, initial_capital=initial_capital)
            for _ in range(num_firms)
        ]

        # --- build households -------------------------------------------
        num_capitalists = int(num_households * pct_capitalists)
        for i in range(num_households):
            if i < num_capitalists:
                owned = firms[i % num_firms]
                household = Capitalist(self, firm_owned=owned)
                owned.owner = household
            else:
                household = Household(self)

            # Initial employment: assign round-robin (fully employed at t=0).
            employer = firms[i % num_firms]
            household.employed = True
            household.employer = employer
            employer.workers.append(household)

            num_links = max(1, num_firms // 2)
            linked = self.random.sample(firms, num_links)
            household.consumption_firms = linked
            household.num_consumption_links = len(linked)
            for firm in linked:
                firm.customers.append(household)

        # Initial expectations so the first-period labour market is not a shock.
        for f in firms:
            f.expected_demand = ces_capacity(
                initial_capital, len(f.workers), productivity, K0, L0, pi0, sigma
            )
            f.utilization_last_period = target_utilization

        # --- data collection --------------------------------------------
        self.datacollector = mesa.DataCollector(
            model_reporters={
                "Output": compute_output,
                "Potential_Output": compute_potential_output,
                "Output_Gap": compute_output_gap,
                "Unemployment_Rate": compute_unemployment,
                "Employment": compute_employment,
                "Total_Capital": compute_aggregate_capital,
                "Money_Buffer": compute_total_money_buffer,
                "Consumption": compute_consumption,
                "Investment": compute_investment,
                "Average_Utilization": compute_average_utilization,
                "Wage_Share": compute_wage_share,
                "Wage_Share_Profitmax": compute_wage_share_profitmax,
                "Profit_Share": compute_profit_share,
                "Income_Gini": compute_income_gini,
                "Wealth_Gini": compute_wealth_gini,
                # Which constraint bites (brief 04 §9.3)
                "Bound_Demand": compute_bound_by_demand,
                "Bound_Profitmax": compute_bound_by_profitmax,
                "Bound_Capital": compute_bound_by_capital,
                "Bound_Workforce": compute_bound_by_workforce,
                "Cash_Constrained": compute_cash_constrained_frac,
            }
        )
        self.datacollector.collect(self)

    # ------------------------------------------------------------------
    def labour_market(self, firms, households):
        """Fire the excess into an unemployed pool, then fill vacancies randomly.

        Workers are mobile: an unemployed household can be hired by any firm with a
        vacancy.  Firms may leave vacancies unfilled when the pool is empty (the
        ``L <= N`` cap), which is what caps aggregate employment at the workforce.
        """
        for f in firms:
            f.plan_employment()

        unemployed = [h for h in households if not h.employed]

        for f in firms:
            while len(f.workers) > f.desired_employment:
                worker = f.workers.pop()
                worker.employed = False
                worker.employer = None
                unemployed.append(worker)

        self.random.shuffle(unemployed)
        for f in firms:
            vacancies = f.desired_employment - len(f.workers)
            while vacancies > 0 and unemployed:
                worker = unemployed.pop()
                worker.employed = True
                worker.employer = f
                f.workers.append(worker)
                vacancies -= 1
            # Diagnostic: the pool ran dry, so the workforce is what bites here.
            f.labour_rationed = len(f.workers) < f.desired_employment

    # ------------------------------------------------------------------
    def step(self):
        households = _households(self)
        firms = _firms(self)

        # 1. labour market (employment set before demand)
        self.labour_market(firms, households)

        # 2. consumption demand
        for h in households:
            h.step_demand()

        # 3. firms plan investment
        for f in firms:
            f.plan_investment()
        self.total_investment_demand = sum(f.desired_investment for f in firms)

        # 4. firms register demand
        for f in firms:
            f.register_demand()

        # 5. production + goods-market rationing
        for f in firms:
            f.step_production()
        self.investment_rationing = (
            sum(f.rationing for f in firms) / len(firms) if firms else 1.0
        )

        # 6. firm accounting
        for f in firms:
            f.step_accounting()

        # 7. investment settlement (buffer -> 0)
        for f in firms:
            f.step_investment()
        self.total_investment_realised = sum(f.investment_delivered for f in firms)

        # 8. household settlement
        for h in households:
            h.step_settlement()

        self.datacollector.collect(self)
