"""
Macro model for the Endogenous-Investment Keynesian ABM
(core di offerta: Cobb-Douglas + finanziamento interno).

Single-good, fixed-price (numeraire = 1), stock-flow-consistent circular flow of
income.  Capital is essential (Cobb-Douglas), investment is financed by firms out
of *current* retained earnings (a within-period pass-through, not an accumulating
stock), and the wage share fixed by pricing is tied to the labour elasticity via
``markup = alpha/(1-alpha)``.

Period sequence:

    1. households form consumption demand
    2. firms plan investment I_planned (accelerator on last period's utilisation,
       from the flow of profit; capped by profit, no external credit)
    3. firms register demand (consumption + investment)
    4. firms produce: Y* = A*K^alpha*L^(1-alpha); Y = min(demand, Y*); ration; save u
    5. firm accounting: wages, retained (= I_planned) and residual dividends
    6. investment settlement: pay I_delivered from the retained earnings;
       K(t+1) = (1-delta)*K(t) + I_delivered; return any residual as dividends so
       the money buffer returns to zero (no sequestration)
    7. households settle (credit income, pay for delivered goods)

Conserved quantity (checked in ``tests/test_model.py``); at a period boundary the
buffer is zero, so this reduces to ``sum(household wealth + income)``:

    sum(household wealth + income + income accruing) + sum(firm money_buffer) = const
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
    """Inequality of net worth (money + owned firm's money & capital)."""
    net_worth = [
        h.net_worth() if isinstance(h, Capitalist) else h.wealth
        for h in _households(model)
    ]
    return compute_gini(net_worth)


def compute_output(model):
    return sum(f.production for f in _firms(model))


def compute_potential_output(model):
    return sum(f.capacity for f in _firms(model))


def compute_output_gap(model):
    potential = compute_potential_output(model)
    if potential <= 0:
        return 0.0
    return (potential - compute_output(model)) / potential


def compute_aggregate_capital(model):
    return sum(f.capital for f in _firms(model))


def compute_average_utilization(model):
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
    """Aggregate wage bill divided by aggregate sales (0 if no output)."""
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
    """Heterogeneous Keynesian economy: Cobb-Douglas core + internal financing.

    Parameters
    ----------
    alpha : float
        Capital elasticity in ``Y* = A*K^alpha*L^(1-alpha)`` (default 1/3;
        standard textbook value, **to be anchored** to a primary source).
        The markup is derived from it, not set independently.
    delta : float
        Capital depreciation rate (default 0.05; **to be anchored**).
    retention_ratio : float
        Share of gross profit retained to fund investment (default 0.40; **to be
        anchored** to corporate-finance evidence).
    beta : float
        Sensitivity of the investment accelerator to capacity utilisation.
    target_utilization : float
        Reference utilisation of the accelerator (~ expected steady-state u).
    investment_floor : float
        Minimum capex per firm (anti-collapse guardrail); also the minimum
        retention, so the buffer can fund it even at ``retention_ratio = 0``.
    initial_capital : float
        K(0) per firm; must be positive (capital is essential).
    c0, c1, capitalist_mpc, wealth_effect : float
        Consumption function terms.
    productivity : float
        Total factor productivity A.
    seed : int or None
        Seed for the model's random stream.

    Notes
    -----
    Distributive coherence: ``markup = alpha/(1-alpha)`` so that
    ``1/(1+markup) = 1-alpha`` (wage share = labour elasticity).  ``markup`` is a
    derived attribute, not a free parameter.
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
        initial_capital=5.0,

        # Internal financing / investment
        retention_ratio=0.40,
        beta=0.5,
        target_utilization=0.90,
        investment_floor=0.10,

        # Consumption
        c0=1.0,
        c1=0.9,
        capitalist_mpc=0.4,
        wealth_effect=0.08,

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

        # Distributive coherence: markup tied to alpha (NOT a free parameter).
        self.markup = alpha / (1.0 - alpha)
        assert abs(1.0 / (1.0 + self.markup) - (1.0 - alpha)) < 1e-12

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

        # --- build agents -----------------------------------------------
        firms = [
            Firm(self, productivity=productivity, initial_capital=initial_capital)
            for _ in range(num_firms)
        ]

        num_capitalists = int(num_households * pct_capitalists)

        for i in range(num_households):
            employer = firms[i % num_firms]

            if i < num_capitalists:
                owned = firms[i % num_firms]
                household = Capitalist(self, firm_employer=employer, firm_owned=owned)
                owned.owner = household
            else:
                household = Household(self, firm_employer=employer)

            employer.workers.append(household)

            num_links = max(1, num_firms // 2)
            linked = self.random.sample(firms, num_links)
            household.consumption_firms = linked
            household.num_consumption_links = len(linked)
            for firm in linked:
                firm.customers.append(household)

        # --- data collection --------------------------------------------
        self.datacollector = mesa.DataCollector(
            model_reporters={
                "Output": compute_output,
                "Potential_Output": compute_potential_output,
                "Output_Gap": compute_output_gap,
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
    def step(self):
        households = _households(self)
        firms = _firms(self)

        # 1. consumption demand
        for h in households:
            h.step_demand()

        # 2. firms plan investment (from the profit flow; accelerator on u_last)
        for f in firms:
            f.plan_investment()
        self.total_investment_demand = sum(f.desired_investment for f in firms)

        # 3. firms register demand (consumption + investment)
        for f in firms:
            f.register_demand()

        # 4. production + goods-market rationing
        for f in firms:
            f.step_production()
        self.investment_rationing = (
            sum(f.rationing for f in firms) / len(firms) if firms else 1.0
        )

        # 5. firm accounting: wages, retained (= I_planned), residual dividends
        for f in firms:
            f.step_accounting()

        # 6. investment settlement: pay I_delivered, update capital, return the
        #    residual as dividends so the buffer returns to zero (no sequestration)
        for f in firms:
            f.step_investment()
        self.total_investment_realised = sum(f.investment_delivered for f in firms)

        # 7. household settlement (credit income incl. this period's dividends)
        for h in households:
            h.step_settlement()

        self.datacollector.collect(self)
