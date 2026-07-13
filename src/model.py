"""
Macro model for the Endogenous-Investment Keynesian ABM with a labour market.

The economy is a single-good, fixed-price, stock-flow-consistent circular flow
of income with **unemployment**.  Each period:

    0. firms update capital (install last period's investment, depreciate)
    1. firms plan desired employment from expected demand (capped by capital)
    2. the labour market fires excess workers and fills vacancies
    3. households form consumption demand
    4. capitalists plan investment demand
    5. firms register demand, produce (subject to employed labour) and ration
    6. firms distribute revenue (wages + dividends)
    7. the government runs a balanced-budget benefit (flat tax funds transfers)
    8. households settle (credit income, pay for delivered goods)
    9. capitalists settle investment (queue capital for next period)

Because firms distribute 100% of revenue, the fiscal step is a pure transfer,
and households only pay for delivered goods, ``sum(wealth + income)`` is conserved
every period (verified in ``tests/test_model.py``).
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


def compute_potential_output(model):
    """Full-employment output, capped by the jobs the capital stock can equip."""
    firms = _firms(model)
    capital_jobs = sum(f.max_jobs() for f in firms)
    full_employment = min(model.num_households, capital_jobs)
    return model.productivity * full_employment


def compute_output_gap(model):
    potential = compute_potential_output(model)
    if potential <= 0:
        return 0.0
    return (potential - compute_output(model)) / potential


def compute_unemployment(model):
    households = _households(model)
    if not households:
        return 0.0
    unemployed = sum(1 for h in households if not h.employed)
    return unemployed / len(households)


def compute_employment(model):
    return sum(1 for h in _households(model) if h.employed)


def compute_aggregate_capital(model):
    return sum(f.capital for f in _firms(model))


def compute_average_capital_utilization(model):
    firms = _firms(model)
    if not firms:
        return 0.0
    return sum(f.capital_utilization for f in firms) / len(firms)


def compute_consumption(model):
    return sum(h.actual_consumption for h in _households(model))


def compute_investment(model):
    return model.total_investment_realised


def compute_tax_rate(model):
    return model.tax_rate


# ============================================================
# Model
# ============================================================

class MacroModel(mesa.Model):
    """Heterogeneous Keynesian economy with endogenous investment and unemployment.

    Key parameters (see the module docstring for the period sequence)
    ----------------------------------------------------------------
    capital_per_job : float
        Units of capital that equip one job (Leontief).  ``max jobs = K / kappa``.
    capital_floor : float
        Minimum capital per firm (basic infrastructure never scrapped); sets a
        floor under employment so the baseline stagnates rather than collapses.
    benefit_replacement_rate : float
        Unemployment benefit as a fraction of the wage, funded by a flat income
        tax whose rate adjusts to balance the budget each period (a pure transfer).
    max_tax : float
        Cap on the balanced-budget tax rate; if benefits would need more, they are
        scaled down to what the cap raises.
    theta : float
        Investment propensity out of the accumulated savings hoard (``0`` = the
        no-investment baseline).
    """

    def __init__(
        self,
        num_firms=10,
        num_households=100,
        pct_capitalists=0.10,

        # Technology / firms
        markup=0.2,
        productivity=1.0,
        capital_per_job=0.5,
        capital_floor=3.5,
        delta=0.05,
        initial_capital=5.0,

        # Consumption
        c0=0.1,
        c1=0.9,
        capitalist_mpc=0.2,
        wealth_effect=0.02,

        # Investment
        theta=0.0,
        investment_sensitivity=1.0,
        target_utilization=0.9,
        precautionary_buffer=2.0,

        # Government
        benefit_replacement_rate=0.3,
        max_tax=0.6,

        seed=None,
    ):
        super().__init__(seed=seed)

        # --- parameters -------------------------------------------------
        self.num_firms = num_firms
        self.num_households = num_households

        self.markup = markup
        self.productivity = productivity
        self.capital_per_job = capital_per_job
        self.capital_floor = capital_floor
        self.delta = delta

        # Wage rate consistent with the markup: full-capacity revenue A splits
        # into a wage share 1/(1+markup) and a profit share markup/(1+markup).
        self.wage_rate = productivity / (1.0 + markup)

        self.c0 = c0
        self.c1 = c1
        self.capitalist_mpc = capitalist_mpc
        self.wealth_effect = wealth_effect

        self.theta = theta
        self.investment_sensitivity = investment_sensitivity
        self.target_utilization = target_utilization
        self.precautionary_buffer = precautionary_buffer

        self.benefit_replacement_rate = benefit_replacement_rate
        self.max_tax = max_tax

        # --- economy-wide flow variables --------------------------------
        self.total_investment_demand = 0.0
        self.total_investment_realised = 0.0
        self.investment_rationing = 1.0
        self.tax_rate = 0.0
        self.benefit = 0.0

        # --- build firms ------------------------------------------------
        firms = [Firm(self, initial_capital=initial_capital) for _ in range(num_firms)]

        # --- build households -------------------------------------------
        num_capitalists = int(num_households * pct_capitalists)
        households = []
        for i in range(num_households):
            if i < num_capitalists:
                owned = firms[i % num_firms]
                h = Capitalist(self, firm_owned=owned)
                owned.owner = h
            else:
                h = Household(self)
            households.append(h)

            num_links = max(1, num_firms // 2)
            linked = self.random.sample(firms, num_links)
            h.consumption_firms = linked
            h.num_consumption_links = len(linked)
            for firm in linked:
                firm.customers.append(h)

        # --- initial employment: fill each firm up to its capital ceiling
        pool = list(households)
        self.random.shuffle(pool)
        for firm in firms:
            capacity = int(firm.max_jobs())
            while capacity > 0 and pool:
                worker = pool.pop()
                worker.employed = True
                worker.employer = firm
                firm.workers.append(worker)
                capacity -= 1
            firm.expected_demand = self.productivity * len(firm.workers)

        # --- data collection --------------------------------------------
        self.datacollector = mesa.DataCollector(
            model_reporters={
                "Output": compute_output,
                "Potential_Output": compute_potential_output,
                "Output_Gap": compute_output_gap,
                "Unemployment_Rate": compute_unemployment,
                "Employment": compute_employment,
                "Total_Capital": compute_aggregate_capital,
                "Capital_Utilization": compute_average_capital_utilization,
                "Consumption": compute_consumption,
                "Investment": compute_investment,
                "Tax_Rate": compute_tax_rate,
                "Income_Gini": compute_income_gini,
                "Wealth_Gini": compute_wealth_gini,
            }
        )
        self.datacollector.collect(self)

    # ------------------------------------------------------------------
    def labour_market(self, firms, households):
        """Fire excess workers into an unemployed pool, then fill vacancies.

        Workers are mobile: an unemployed household can be hired by any firm with
        a vacancy (random matching).  Firms may leave vacancies unfilled when the
        pool is empty (full employment / labour shortage).
        """
        for f in firms:
            f.plan_employment()

        unemployed = [h for h in households if not h.employed]

        # release excess
        for f in firms:
            while len(f.workers) > f.desired_employment:
                worker = f.workers.pop()
                worker.employed = False
                worker.employer = None
                unemployed.append(worker)

        # fill vacancies from the shuffled pool
        self.random.shuffle(unemployed)
        for f in firms:
            vacancies = f.desired_employment - len(f.workers)
            while vacancies > 0 and unemployed:
                worker = unemployed.pop()
                worker.employed = True
                worker.employer = f
                f.workers.append(worker)
                vacancies -= 1

    def government(self, households):
        """Balanced-budget unemployment benefit: a flat tax funds the transfers.

        The tax is levied on this period's accrued income (``next_income``).  The
        rate adjusts so collections equal benefits paid, capped at ``max_tax`` (in
        which case benefits are scaled down).  Being a pure transfer, it conserves
        money.
        """
        unemployed = [h for h in households if not h.employed]
        n_unemployed = len(unemployed)

        base = sum(max(0.0, h.next_income) for h in households)
        desired = self.benefit_replacement_rate * self.wage_rate * n_unemployed

        if base > 0 and desired > 0:
            self.tax_rate = min(self.max_tax, desired / base)
        else:
            self.tax_rate = 0.0

        collected = self.tax_rate * base
        self.benefit = collected / n_unemployed if n_unemployed > 0 else 0.0

        for h in households:
            h.next_income *= (1.0 - self.tax_rate)
            if not h.employed:
                h.next_income += self.benefit

    # ------------------------------------------------------------------
    def step(self):
        households = _households(self)
        firms = _firms(self)
        capitalists = [h for h in households if isinstance(h, Capitalist)]

        # 0. capital law of motion (install last period's investment, depreciate)
        for f in firms:
            f.update_capital()

        # 1-2. labour market
        self.labour_market(firms, households)

        # 3. consumption demand
        for h in households:
            h.step_demand()

        # 4. investment plans
        for c in capitalists:
            c.plan_investment()
        self.total_investment_demand = sum(c.desired_investment for c in capitalists)

        # 5. production + rationing
        for f in firms:
            f.register_demand()
        for f in firms:
            f.step_production()
        self.investment_rationing = (
            sum(f.rationing for f in firms) / len(firms) if firms else 1.0
        )

        # 6. firm accounting
        for f in firms:
            f.step_accounting()

        # 7. government (balanced-budget benefit)
        self.government(households)

        # 8. household settlement
        for h in households:
            h.step_settlement()

        # 9. capitalist investment settlement
        for c in capitalists:
            c.step_investment()
        self.total_investment_realised = sum(c.investment_injected for c in capitalists)

        self.datacollector.collect(self)
