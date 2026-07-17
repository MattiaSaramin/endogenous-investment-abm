"""
Macro model for the Endogenous-Investment Keynesian ABM
(Cobb-Douglas core + endogenous labour market — roadmap point 11).

Single-good, fixed-price (numeraire = 1), stock-flow-consistent circular flow of
income.  Capital is essential (Cobb-Douglas); firms hire endogenously at a fixed
wage ``w_bar``; the unemployed earn nothing, so employment drives demand.

Period sequence (employment is set *before* households form demand, because
expected income depends on employment status):

    1. firms form expectations, compute desired employment; the labour market
       fires the excess and fills vacancies (random matching) -> employment
    2. households form consumption demand (income = wage if employed, else 0;
       plus dividends for capitalists)
    3. firms plan investment (profit flow, accelerator on last utilisation)
    4. firms register demand (consumption + investment)
    5. firms produce: Y = min(demand, A*K^alpha*L^(1-alpha)); ration; set u
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

from agents import Firm, Household, Capitalist


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
    """Full-employment output benchmark: A * K_agg^alpha * N^(1-alpha)."""
    k = compute_aggregate_capital(model)
    n = model.num_households
    if k <= 0 or n <= 0:
        return 0.0
    return model.productivity * (k ** model.alpha) * (n ** (1.0 - model.alpha))


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
    """Aggregate wage bill / sales — now a *measured outcome* (<= 1 - alpha)."""
    firms = _firms(model)
    sales = sum(f.sales for f in firms)
    if sales <= 0:
        return 0.0
    return sum(f.wage_bill for f in firms) / sales


def compute_profit_share(model):
    firms = _firms(model)
    sales = sum(f.sales for f in firms)
    if sales <= 0:
        return 0.0
    return sum(f.gross_profit for f in firms) / sales


# ============================================================
# Model
# ============================================================

class MacroModel(mesa.Model):
    """Cobb-Douglas core with an endogenous labour market and a fixed wage.

    Parameters
    ----------
    alpha, delta, productivity, initial_capital : float
        Technology (``Y* = A*K^alpha*L^(1-alpha)``; alpha = 1/3), depreciation, A,
        and K(0) per firm.
    wage_rate : float
        The fixed wage ``w_bar`` per employed worker.  This is now the distributive
        parameter (replaces ``markup``): profit is the residual ``sales - w_bar*L``,
        so the wage share is a measured outcome, bounded above by ``1-alpha``.
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
        alpha=1.0 / 3.0,
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

        if not (0.0 < alpha < 1.0):
            raise ValueError("alpha must be in (0, 1)")

        # --- parameters -------------------------------------------------
        self.num_firms = num_firms
        self.num_households = num_households

        self.alpha = alpha
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
            L0 = len(f.workers)
            f.expected_demand = (
                productivity * (initial_capital ** alpha) * (L0 ** (1.0 - alpha))
                if L0 > 0 else 0.0
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
                "Profit_Share": compute_profit_share,
                "Income_Gini": compute_income_gini,
                "Wealth_Gini": compute_wealth_gini,
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
