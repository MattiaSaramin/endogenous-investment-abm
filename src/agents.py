"""
Agent definitions for the Endogenous-Investment Keynesian ABM.

The model is *stock-flow consistent* (SFC): within each period every unit of
money that leaves a household as spending is received by some firm as revenue
and paid straight back out as wages, dividends or fiscal transfers.  Nothing is
created or destroyed, so the aggregate money stock is conserved (see ``tests/``).

Four behavioural mechanisms drive the dynamics:

1. **Differential (class) saving.**  Workers consume a large share of their
   income; capitalists consume a small share of theirs.  Persistent capitalist
   saving is the demand *leakage* whose macroeconomic consequences the project
   studies.

2. **Wealth effect.**  Consumption also responds to accumulated money wealth
   (``lambda * W``).  This prevents the baseline economy from collapsing to zero
   and instead pins it at a low *stagnation* equilibrium.

3. **Endogenous investment.**  Capitalists channel a fraction ``theta`` of their
   accumulated savings hoard into productive capital.

4. **A labour market with unemployment.**  Firms employ only as many workers as
   they expect to need, subject to a Leontief capital constraint (``kappa`` units
   of capital equip one job).  The unemployed lose their wage, cut consumption,
   and that shortfall feeds back into aggregate demand.  Investment reduces
   unemployment through *two* channels: it recycles demand (more hiring) and it
   builds the capital that equips new jobs.
"""

import mesa


class Firm(mesa.Agent):
    """A productive unit that hires labour and owns capital.

    Output is Leontief: one employed worker produces ``A`` units of the good, and
    a job can only exist if it is backed by ``kappa`` units of capital, so the
    firm can employ at most ``K / kappa`` workers.  Employment is chosen to meet
    *expected* demand; the goods market rations when realised demand exceeds what
    the employed workforce can produce.
    """

    def __init__(self, model, initial_capital=5.0):
        super().__init__(model)

        # Network / labour links
        self.workers = []          # currently employed households
        self.customers = []
        self.owner = None

        # Real state
        self.capital = initial_capital
        self.pending_capital = 0.0

        # Expectations & employment
        self.expected_demand = 0.0
        self.desired_employment = 0

        # Flow variables
        self.consumption_demand = 0.0
        self.investment_demand = 0.0
        self.faced_demand = 0.0
        self.production = 0.0
        self.sales = 0.0
        self.rationing = 1.0
        self.labour_utilization = 0.0     # output / (A * employed)
        self.capital_utilization = 0.0    # employed / max jobs

        # Distribution
        self.wage_per_worker = 0.0
        self.wage_bill = 0.0
        self.dividend_pool = 0.0

    # ------------------------------------------------------------------
    def update_capital(self):
        """Depreciate, install last period's investment, and apply the floor.

        Run at the *start* of the period, before hiring, so employment is always
        bounded by the capital actually in place.  Installing the previous
        period's investment here preserves the one-period gestation lag.
        """
        self.capital *= (1.0 - self.model.delta)
        self.capital += self.pending_capital
        self.capital = max(self.capital, self.model.capital_floor)
        self.pending_capital = 0.0

    def max_jobs(self):
        """Number of jobs the current capital stock can equip (Leontief)."""
        return self.capital / self.model.capital_per_job

    def plan_employment(self):
        """Desired headcount = labour needed for expected demand, capped by capital.

        ``expected_demand`` is last period's realised demand (naive adaptive
        expectations), which introduces the one-period lag that drives the
        labour-market dynamics.
        """
        labour_for_demand = round(self.expected_demand / self.model.productivity)
        capital_ceiling = int(self.max_jobs())   # a job needs a whole unit of capital

        self.desired_employment = max(0, min(labour_for_demand, capital_ceiling))

    # ------------------------------------------------------------------
    def register_demand(self):
        """Aggregate consumption orders (via the network) plus investment orders."""
        self.consumption_demand = sum(
            h.desired_consumption / h.num_consumption_links
            for h in self.customers
        )
        self.investment_demand = (
            self.model.total_investment_demand / self.model.num_firms
        )
        self.faced_demand = self.consumption_demand + self.investment_demand

    def step_production(self):
        """Produce up to what the employed workforce can make; ration the rest."""
        capacity = self.model.productivity * len(self.workers)

        self.production = min(self.faced_demand, capacity)

        self.rationing = (
            self.production / self.faced_demand if self.faced_demand > 1e-12 else 1.0
        )
        self.labour_utilization = (
            self.production / capacity if capacity > 1e-12 else 0.0
        )
        jobs = self.max_jobs()
        self.capital_utilization = len(self.workers) / jobs if jobs > 1e-12 else 0.0

        # Adaptive expectation for next period.
        self.expected_demand = self.faced_demand

    # ------------------------------------------------------------------
    def step_accounting(self):
        """Distribute revenue as wages then dividends; depreciate/install capital.

        Revenue (price is the numeraire, so revenue = goods sold) is paid out
        first as wages, up to the going wage rate per employed worker, with the
        remainder distributed as dividends.  Capping wages at revenue keeps firms
        solvent and the model stock-flow consistent even when a demand shortfall
        leaves workers idle.
        """
        self.sales = self.production
        n = len(self.workers)

        if n > 0:
            self.wage_per_worker = min(self.model.wage_rate, self.sales / n)
        else:
            self.wage_per_worker = 0.0

        self.wage_bill = self.wage_per_worker * n
        self.dividend_pool = self.sales - self.wage_bill

        for worker in self.workers:
            worker.next_income += self.wage_per_worker
        if self.owner is not None:
            self.owner.next_income += self.dividend_pool


class Household(mesa.Agent):
    """A worker household.

    Supplies labour, consumes ``C = c0 + mpc * income + lambda * wealth`` out of a
    money balance, and accumulates unspent income as wealth.  When unemployed it
    earns no wage (only a fiscal benefit, plus dividends if it is a capitalist),
    so its consumption falls — the demand feedback at the heart of the model.
    """

    is_capitalist = False

    def __init__(self, model):
        super().__init__(model)

        # Employment state (set by the labour market)
        self.employed = False
        self.employer = None

        # Stocks / flows
        self.wealth = 2.0
        self.income = 2.0
        self.next_income = 0.0

        self.desired_consumption = 0.0
        self.actual_consumption = 0.0
        self.savings = 0.0

        self.consumption_firms = []
        self.num_consumption_links = 1

    # ------------------------------------------------------------------
    def marginal_propensity(self):
        return self.model.c1

    def step_demand(self):
        target = (
            self.model.c0
            + self.marginal_propensity() * self.income
            + self.model.wealth_effect * self.wealth
        )
        affordable = self.wealth + self.income
        self.desired_consumption = min(max(target, 0.0), affordable)

    # ------------------------------------------------------------------
    def step_settlement(self):
        self.wealth += self.income

        self.actual_consumption = sum(
            (self.desired_consumption / self.num_consumption_links) * firm.rationing
            for firm in self.consumption_firms
        )

        self.wealth -= self.actual_consumption
        self.savings = self.income - self.actual_consumption

        self.income = self.next_income
        self.next_income = 0.0


class Capitalist(Household):
    """A household that also owns a firm and invests part of its saving hoard."""

    is_capitalist = True

    def __init__(self, model, firm_owned):
        super().__init__(model)

        self.owned_firm = firm_owned
        self.desired_investment = 0.0
        self.investment_injected = 0.0

    def marginal_propensity(self):
        return self.model.capitalist_mpc

    def net_worth(self):
        return self.wealth + self.owned_firm.capital

    # ------------------------------------------------------------------
    def plan_investment(self):
        """Deploy part of the accumulated savings hoard into productive capital.

        The accelerator responds to the owned firm's *capital* utilisation (jobs
        filled relative to jobs the capital can equip): when capital is fully
        staffed the firm wants more of it, so investment rises.
        """
        hoard = max(0.0, self.wealth - self.model.precautionary_buffer)

        utilisation_effect = 1.0 + self.model.investment_sensitivity * (
            self.owned_firm.capital_utilization - self.model.target_utilization
        )
        utilisation_effect = max(0.0, utilisation_effect)

        planned = self.model.theta * hoard * utilisation_effect
        budget = max(0.0, self.wealth + self.income - self.desired_consumption)
        self.desired_investment = min(planned, budget)

    def step_investment(self):
        self.investment_injected = max(
            0.0, self.desired_investment * self.model.investment_rationing
        )
        self.wealth -= self.investment_injected
        self.owned_firm.pending_capital += self.investment_injected
