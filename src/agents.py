"""
Agent definitions for the Endogenous-Investment Keynesian ABM.

The model is *stock-flow consistent* (SFC): within each period every unit of
money that leaves a household as spending is received by some firm as revenue
and paid straight back out as wages or dividends.  Nothing is created or
destroyed, so the aggregate money stock is conserved (see ``tests/``).

Three behavioural mechanisms drive the dynamics:

1. **Differential (class) saving.**  Workers consume a large share of their
   income; capitalists consume a small share of theirs.  Persistent capitalist
   saving is the demand *leakage* whose macroeconomic consequences the project
   studies.

2. **Wealth effect.**  Consumption also responds to accumulated money wealth
   (``lambda * W``).  This prevents the baseline economy from collapsing to zero
   and instead pins it at a low *stagnation* equilibrium.

3. **Endogenous investment.**  Capitalists channel a fraction ``theta`` of their
   current saving into the capital stock of the firm they own.  Investment
   spending re-enters aggregate demand (recycling the leakage) and, with a
   one-period gestation lag, raises productive capacity.
"""

import mesa


class Firm(mesa.Agent):
    """A productive unit.

    Holds capital, employs workers, faces demand from a subset of households
    plus economy-wide investment demand, and distributes 100% of its sales
    revenue as wages (to workers) and dividends (to its owner).
    """

    def __init__(self, model, productivity=1.0, initial_capital=5.0):
        super().__init__(model)

        # Network links (populated by the model during construction)
        self.workers = []
        self.customers = []
        self.owner = None

        # Technology
        self.productivity = productivity          # A in the capacity function

        # Real state
        self.capital = initial_capital
        self.pending_capital = 0.0                # installed with a 1-period lag

        # Flow variables (reset / recomputed every period)
        self.consumption_demand = 0.0             # goods ordered for consumption
        self.investment_demand = 0.0              # goods ordered as investment
        self.faced_demand = 0.0
        self.capacity = 0.0
        self.production = 0.0
        self.sales = 0.0
        self.rationing = 1.0                      # share of demand actually served
        self.utilization = 0.0

        # Distribution
        self.wage_bill = 0.0
        self.dividend_pool = 0.0

    # ------------------------------------------------------------------
    # Supply side
    # ------------------------------------------------------------------
    def calculate_capacity(self):
        """Capital-augmented labour productivity (capital deepening).

            Y* = A * L * (1 + gamma * (K / L) ** alpha)

        Labour sets a positive floor (``A * L``) so the economy never loses the
        ability to produce, while capital *per worker* raises productivity with
        diminishing returns (``alpha < 1``).  This is deliberately **not** a
        textbook Cobb-Douglas ``A K^a L^(1-a)`` form, which would force capacity
        to zero as capital depreciates and would make a demand-constrained
        baseline impossible to study.
        """
        labour = len(self.workers)

        if labour == 0:
            self.capacity = 0.0
            return

        capital_per_worker = self.capital / labour

        self.capacity = (
            self.productivity
            * labour
            * (1.0 + self.model.gamma * (capital_per_worker ** self.model.alpha))
        )

    def register_demand(self):
        """Aggregate the orders this firm faces this period.

        Consumption demand is collected from linked customers (each household
        splits its desired consumption across the firms it is connected to).
        Investment demand is the economy-wide investment order flow shared
        equally across firms (a single-good economy: capital goods are the same
        good that is consumed).
        """
        self.consumption_demand = sum(
            h.desired_consumption / h.num_consumption_links
            for h in self.customers
        )

        self.investment_demand = (
            self.model.total_investment_demand / self.model.num_firms
        )

        self.faced_demand = self.consumption_demand + self.investment_demand

    def step_production(self):
        """Produce up to capacity; compute the rationing share and utilisation."""
        self.calculate_capacity()

        self.production = min(self.faced_demand, self.capacity)

        if self.faced_demand > 1e-12:
            self.rationing = self.production / self.faced_demand
        else:
            self.rationing = 1.0

        if self.capacity > 1e-12:
            self.utilization = self.production / self.capacity
        else:
            self.utilization = 0.0

    # ------------------------------------------------------------------
    # Accounting / distribution
    # ------------------------------------------------------------------
    def step_accounting(self):
        """Distribute revenue as wages and dividends, then depreciate/install.

        With a normalised price of one, revenue equals goods sold.  The markup
        fixes the functional income split: the wage share is ``1 / (1 + markup)``
        and the profit (dividend) share is ``markup / (1 + markup)``.  Revenue is
        fully distributed, which is what keeps the model stock-flow consistent.
        """
        self.sales = self.production

        self.wage_bill = self.sales / (1.0 + self.model.markup)
        self.dividend_pool = self.sales - self.wage_bill

        # Wages -> workers' income for next period
        if self.workers:
            wage = self.wage_bill / len(self.workers)
            for worker in self.workers:
                worker.next_income += wage

        # Dividends -> owner's income for next period
        if self.owner is not None:
            self.owner.next_income += self.dividend_pool

        # Capital: depreciate, then install last period's investment
        self.capital *= (1.0 - self.model.delta)
        self.capital += self.pending_capital
        self.pending_capital = 0.0


class Household(mesa.Agent):
    """A worker household.

    Consumes ``C = c0 + mpc * income + lambda * wealth`` out of a money balance,
    supplies labour, and accumulates any unspent income as wealth.  Money wealth
    is the household's only asset; net worth therefore equals ``wealth``.
    """

    #: marginal propensity to consume out of income (overridden for capitalists)
    is_capitalist = False

    def __init__(self, model, firm_employer):
        super().__init__(model)

        self.employer = firm_employer

        # Stocks / flows
        self.wealth = 2.0                 # money balance
        self.income = 2.0                 # disposable income this period
        self.next_income = 0.0            # accrues wages + dividends for t+1

        self.desired_consumption = 0.0
        self.actual_consumption = 0.0
        self.savings = 0.0

        # Consumption network (set by the model)
        self.consumption_firms = []
        self.num_consumption_links = 1

    # ------------------------------------------------------------------
    def marginal_propensity(self):
        return self.model.c1

    def step_demand(self):
        """Form desired consumption, bounded by money that is actually available."""
        target = (
            self.model.c0
            + self.marginal_propensity() * self.income
            + self.model.wealth_effect * self.wealth
        )

        # Cannot spend more than the money on hand (income is credited before
        # spending in ``step_settlement``), and never negative.
        affordable = self.wealth + self.income
        self.desired_consumption = min(max(target, 0.0), affordable)

    # ------------------------------------------------------------------
    def step_settlement(self):
        """Credit income, pay for delivered goods, roll income forward.

        ``actual_consumption`` reflects rationing at the firms this household
        buys from, so the household only ever pays for goods it actually
        receives — this is what makes the settlement money-conserving.
        """
        # 1. credit the income earned last period
        self.wealth += self.income

        # 2. compute what was actually delivered (demand x firm rationing share)
        self.actual_consumption = sum(
            (self.desired_consumption / self.num_consumption_links) * firm.rationing
            for firm in self.consumption_firms
        )

        # 3. pay for it
        self.wealth -= self.actual_consumption
        self.savings = self.income - self.actual_consumption

        # 4. roll accrued income forward
        self.income = self.next_income
        self.next_income = 0.0


class Capitalist(Household):
    """A household that also owns a firm and invests part of its saving.

    Investment demand is ``theta * saving * utilisation_effect``, financed out of
    the money balance.  The spending re-enters aggregate demand this period; the
    goods bought are installed as the owned firm's capital next period.
    """

    is_capitalist = True

    def __init__(self, model, firm_employer, firm_owned):
        super().__init__(model, firm_employer)

        self.owned_firm = firm_owned
        self.desired_investment = 0.0
        self.investment_injected = 0.0

    def marginal_propensity(self):
        return self.model.capitalist_mpc

    # ------------------------------------------------------------------
    def net_worth(self):
        """Total wealth = money balance + book value of owned capital."""
        return self.wealth + self.owned_firm.capital

    def plan_investment(self):
        """Deploy part of *accumulated savings* into productive capital.

        The research question concerns investment financed through **accumulated
        private savings** — i.e. the stock of money wealth a capitalist has piled
        up, not merely this period's saving flow.  Each period the capitalist
        converts a fraction ``theta`` of that idle money hoard into capital
        goods.  This is the portfolio decision at the heart of the model:

            desired_investment = theta * money_hoard * utilisation_effect

        where the money hoard is savings accumulated on top of a small
        precautionary buffer.  An accelerator term tilts investment towards
        firms running above their target utilisation and away from slack ones.
        Desired investment is capped by the money that will remain after paying
        for consumption, so settlement never claws spending back (which would
        break stock-flow consistency).
        """
        # Idle savings available to deploy (money wealth above a small buffer).
        hoard = max(0.0, self.wealth - self.model.precautionary_buffer)

        utilisation_effect = 1.0 + self.model.investment_sensitivity * (
            self.owned_firm.utilization - self.model.target_utilization
        )
        utilisation_effect = max(0.0, utilisation_effect)

        planned = self.model.theta * hoard * utilisation_effect

        # Money available for investment after consumption is paid for.
        budget = max(0.0, self.wealth + self.income - self.desired_consumption)
        self.desired_investment = min(planned, budget)

    def step_investment(self):
        """Pay for delivered investment goods and queue them as capital.

        Investment is rationed by the economy-wide goods-market fill rate (firms
        may be unable to supply every order).  Because ``plan_investment`` already
        capped desired investment to the available budget, the served amount is
        always affordable, so no money is created or destroyed here.
        """
        self.investment_injected = max(
            0.0, self.desired_investment * self.model.investment_rationing
        )

        self.wealth -= self.investment_injected
        self.owned_firm.pending_capital += self.investment_injected
