"""
Macro model for the Endogenous-Investment Keynesian ABM.

The economy is a single-good, fixed-price, stock-flow-consistent circular flow
of income.  Each period unfolds in a fixed sequence so that spending, production,
income distribution and investment settle in a consistent order:

    1. households form consumption demand
    2. capitalists plan investment demand
    3. firms register the demand they face
    4. firms produce (subject to capacity) and the goods market rations
    5. firms distribute revenue (wages + dividends) and update capital
    6. households settle (credit income, pay for delivered goods)
    7. capitalists settle investment (pay for delivered capital goods)

Because firms distribute 100% of revenue and households only pay for goods that
are actually delivered, the quantity ``sum(wealth + income)`` is conserved every
period (verified in ``tests/test_model.py``).
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

    # index i runs 1..n; classic order-statistics formula
    index = np.arange(1, n + 1)
    return (2.0 * np.sum(index * x) / (n * total)) - (n + 1.0) / n


def compute_income_gini(model):
    return compute_gini([h.income for h in _households(model)])


def compute_wealth_gini(model):
    """Inequality of *net worth* (money balance + owned capital)."""
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
    """Relative gap between potential and actual output (0 = no slack)."""
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


def compute_total_wealth(model):
    return sum(h.wealth for h in _households(model))


# ============================================================
# Model
# ============================================================

class MacroModel(mesa.Model):
    """Heterogeneous Keynesian economy with endogenous investment.

    Parameters
    ----------
    num_firms, num_households : int
        Population sizes.
    pct_capitalists : float
        Share of households that also own a firm.
    markup : float
        Price markup; fixes the profit share ``markup / (1 + markup)``.
    alpha, gamma : float
        Capital-deepening exponent and weight in the capacity function
        ``A * L * (1 + gamma * (K/L) ** alpha)``.
    delta : float
        Capital depreciation rate per period.
    c0, c1, capitalist_mpc, wealth_effect : float
        Consumption: autonomous term, worker MPC, capitalist MPC and the
        propensity to consume out of wealth.  ``capitalist_mpc < c1`` creates the
        persistent saving leakage the project studies.
    theta : float
        Investment propensity out of capitalist saving (``theta = 0`` is the
        no-investment baseline).
    investment_sensitivity, target_utilization : float
        Accelerator: strength of, and reference point for, the response of
        investment to capacity utilisation.
    productivity : float
        Total-factor productivity ``A``.
    seed : int or None
        Seed for the model's random stream (workers, network, ordering).
    """

    def __init__(
        self,
        num_firms=10,
        num_households=100,
        pct_capitalists=0.10,

        # Firm / technology
        markup=0.2,
        alpha=0.5,
        gamma=0.5,
        delta=0.05,
        productivity=1.0,

        # Consumption
        c0=0.1,
        c1=0.9,
        capitalist_mpc=0.4,
        wealth_effect=0.02,

        # Investment
        theta=0.0,
        investment_sensitivity=1.0,
        target_utilization=0.8,
        precautionary_buffer=2.0,

        seed=None,
    ):
        super().__init__(seed=seed)

        # --- store parameters -------------------------------------------
        self.num_firms = num_firms
        self.num_households = num_households

        self.markup = markup
        self.alpha = alpha
        self.gamma = gamma
        self.delta = delta
        self.productivity = productivity

        self.c0 = c0
        self.c1 = c1
        self.capitalist_mpc = capitalist_mpc
        self.wealth_effect = wealth_effect

        self.theta = theta
        self.investment_sensitivity = investment_sensitivity
        self.target_utilization = target_utilization
        self.precautionary_buffer = precautionary_buffer

        # --- economy-wide flow variables --------------------------------
        self.total_investment_demand = 0.0     # planned investment orders
        self.total_investment_realised = 0.0   # investment actually installed
        self.investment_rationing = 1.0        # goods-market fill rate for I

        # --- build agents -----------------------------------------------
        firms = [Firm(self, productivity=productivity) for _ in range(num_firms)]

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

            # Consumption network: connect to a random subset of firms.
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
                "Consumption": compute_consumption,
                "Investment": compute_investment,
                "Total_Wealth": compute_total_wealth,
                "Income_Gini": compute_income_gini,
                "Wealth_Gini": compute_wealth_gini,
                "Average_Utilization": compute_average_utilization,
            }
        )

        # Record the initial state (t = 0) before any stepping.
        self.datacollector.collect(self)

    # ------------------------------------------------------------------
    def step(self):
        households = _households(model=self)
        firms = _firms(model=self)
        capitalists = [h for h in households if isinstance(h, Capitalist)]

        # 1. consumption demand
        for h in households:
            h.step_demand()

        # 2. investment plans -> economy-wide investment demand
        for c in capitalists:
            c.plan_investment()
        self.total_investment_demand = sum(c.desired_investment for c in capitalists)

        # 3. firms register the demand they face
        for f in firms:
            f.register_demand()

        # 4. production + goods-market rationing
        for f in firms:
            f.step_production()

        # Economy-wide investment fill rate = average firm rationing, since
        # investment orders are shared equally across firms.
        self.investment_rationing = (
            sum(f.rationing for f in firms) / len(firms) if firms else 1.0
        )

        # 5. firm accounting: distribute revenue, depreciate, install capital
        for f in firms:
            f.step_accounting()

        # 6. household settlement
        for h in households:
            h.step_settlement()

        # 7. capitalist investment settlement
        for c in capitalists:
            c.step_investment()
        self.total_investment_realised = sum(
            c.investment_injected for c in capitalists
        )

        # record
        self.datacollector.collect(self)
