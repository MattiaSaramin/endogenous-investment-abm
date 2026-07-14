"""
Agent definitions for the Endogenous-Investment Keynesian ABM
(core di offerta: Cobb-Douglas + finanziamento interno).

The model is *stock-flow consistent* (SFC).  With internal (retained-earnings)
financing the conserved money stock is

    sum(household wealth + household income) + sum(firm money_buffer) = const

Nothing is created or destroyed in settlement: retained profits stay as a money
balance on the firm's books (``money_buffer``) and re-enter the circuit when the
firm pays for delivered investment goods (see ``tests/``).

Behavioural core:

1. **Cobb-Douglas production with essential capital.**
   ``Y* = A * K^alpha * L^(1-alpha)`` — if ``K -> 0`` then ``Y* -> 0``.  Capital
   has a live intensive margin; this is what makes investment drive output *via
   capital* rather than only via the demand multiplier.

2. **Distributive coherence.**  The markup is tied to alpha (``markup =
   alpha/(1-alpha)``, set in the model) so the wage share fixed by pricing
   (``1/(1+markup)``) equals the labour elasticity (``1-alpha``).

3. **Internal financing via retained earnings.**  Firms retain a share of gross
   profit into a money buffer and fund investment from that accumulated buffer,
   not from the capitalist's personal savings.  With essential capital this
   breaks the collapse spiral that personal-savings financing would create.  An
   ``investment_floor`` is the anti-shutdown guardrail.

4. **Class saving + wealth effect** (unchanged): workers consume a large share of
   income, capitalists a small share; consumption also responds to money wealth.

Labour is simple in this task: ``L`` is fixed per firm (the workers assigned at
construction).  An explicit labour market is a later task.
"""

import mesa


class Firm(mesa.Agent):
    """A productive unit with Cobb-Douglas technology and an internal money buffer.

    Holds capital and a money buffer fed by retained profits; faces consumption
    demand (from linked customers) plus economy-wide investment demand; funds its
    own investment out of the accumulated buffer.
    """

    def __init__(self, model, productivity=1.0, initial_capital=5.0):
        super().__init__(model)

        # Network links (populated by the model during construction)
        self.workers = []
        self.customers = []
        self.owner = None

        # Technology / real state
        self.productivity = productivity          # A
        self.capital = initial_capital            # K (essential: K=0 -> Y*=0)

        # Internal finance
        self.money_buffer = 0.0                   # M_f: retained profits held as money
        self.profit_last_period = 0.0             # drives next period's investment
        self.utilization_last_period = 0.0        # drives the accelerator

        # Investment plan / delivery
        self.desired_investment = 0.0
        self.investment_delivered = 0.0

        # Flow variables (recomputed every period)
        self.consumption_demand = 0.0
        self.investment_demand = 0.0
        self.faced_demand = 0.0
        self.capacity = 0.0
        self.production = 0.0
        self.sales = 0.0
        self.rationing = 1.0
        self.utilization = 0.0

        # Distribution
        self.wage_bill = 0.0
        self.gross_profit = 0.0
        self.retained = 0.0
        self.dividend_pool = 0.0

    # ------------------------------------------------------------------
    # Supply side
    # ------------------------------------------------------------------
    def calculate_capacity(self):
        """True Cobb-Douglas capacity: ``Y* = A * K^alpha * L^(1-alpha)``.

        Capital is **essential**: with ``K = 0`` (or no workers) capacity is zero.
        The collapse risk this creates is handled by ``investment_floor`` and a
        positive ``initial_capital``, not by a floor on capacity.
        """
        labour = len(self.workers)

        if labour == 0 or self.capital <= 0.0:
            self.capacity = 0.0
            return

        self.capacity = (
            self.productivity
            * (self.capital ** self.model.alpha)
            * (labour ** (1.0 - self.model.alpha))
        )

    def plan_investment(self):
        """Plan investment from the *flow* of profit (internal finance, no stock).

            util_effect = max(0, 1 + beta * (u_last - target_utilization))
            I_planned   = clip(retention_ratio * profit_last_period * util_effect,
                               investment_floor, profit_last_period)

        Investment is a real decision keyed to profit (a flow) and utilisation,
        not to an accumulated money stock.  The upper cap is the firm's own profit
        (no external credit; that arrives in a later task): in the relevant range
        ``I/Y = rho*alpha < alpha = profit/Y`` so the cap does not bind at steady
        state.  ``profit_last_period`` is used as the (known) basis so demand can
        be registered before this period's profit is realised; at steady state it
        equals current profit, so the firm retains exactly what it invests and the
        money buffer nets to zero every period (see ``step_investment``).
        """
        util_effect = 1.0 + self.model.beta * (
            self.utilization_last_period - self.model.target_utilization
        )
        util_effect = max(0.0, util_effect)

        desired = self.model.retention_ratio * self.profit_last_period * util_effect

        # At least the floor, never more than the firm's own profit (no credit).
        self.desired_investment = min(
            max(desired, self.model.investment_floor), self.profit_last_period
        )
        self.desired_investment = max(0.0, self.desired_investment)

    def register_demand(self):
        """Aggregate consumption orders (via the network) plus investment orders.

        A single-good economy: capital goods are the same good that is consumed,
        so economy-wide investment demand is shared equally across firms.
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
        """Produce up to capacity; record the rationing share and utilisation."""
        self.calculate_capacity()

        self.production = min(self.faced_demand, self.capacity)

        self.rationing = (
            self.production / self.faced_demand if self.faced_demand > 1e-12 else 1.0
        )
        self.utilization = (
            self.production / self.capacity if self.capacity > 1e-12 else 0.0
        )
        # Utilisation feeds next period's investment accelerator.
        self.utilization_last_period = self.utilization

    # ------------------------------------------------------------------
    # Accounting / distribution
    # ------------------------------------------------------------------
    def step_accounting(self):
        """Split revenue into wages, retained earnings and dividends.

        With a normalised price of one, revenue = goods sold.  The markup
        (tied to alpha in the model) fixes the wage share ``1/(1+markup) =
        1-alpha`` and the gross-profit share ``markup/(1+markup) = alpha``.

        The firm retains **exactly what it plans to invest** (a within-period
        pass-through, not an accumulating stock) and distributes all the rest of
        gross profit as dividends.  The distribution identity
        ``wage_bill + dividends + retained == sales`` holds exactly.
        """
        self.sales = self.production

        self.wage_bill = self.sales / (1.0 + self.model.markup)
        self.gross_profit = self.sales - self.wage_bill

        # Retain exactly the planned investment; distribute the residual.
        self.retained = self.desired_investment
        self.dividend_pool = self.gross_profit - self.retained
        self.money_buffer += self.retained

        if self.workers:
            wage = self.wage_bill / len(self.workers)
            for worker in self.workers:
                worker.next_income += wage

        if self.owner is not None:
            self.owner.next_income += self.dividend_pool

        # Remember gross profit for next period's investment plan.
        self.profit_last_period = self.gross_profit

    def step_investment(self):
        """Pay for delivered investment goods; return any residual as dividends.

        Investment demand is rationed by the goods market
        (``investment_rationing``); the delivered amount is paid out of the buffer
        (which holds exactly this period's retained earnings).  Whatever retention
        was not spent — because the goods market rationed the order — is paid to
        the owner as an extra dividend, so **the buffer returns to zero every
        period** (the structural guarantee against money sequestration).  Capital
        follows a one-period gestation lag: goods delivered in ``t`` are
        productive in ``t+1``.
        """
        self.investment_delivered = self.desired_investment * self.model.investment_rationing

        self.money_buffer -= self.investment_delivered
        self.capital = (1.0 - self.model.delta) * self.capital + self.investment_delivered

        # Return the un-invested residual (never sequestered) and zero the buffer.
        if self.owner is not None:
            self.owner.next_income += self.money_buffer
        self.money_buffer = 0.0


class Household(mesa.Agent):
    """A worker household.

    Consumes ``C = c0 + mpc * income + lambda * wealth`` out of a money balance,
    supplies labour, and accumulates any unspent income as wealth.
    """

    is_capitalist = False

    def __init__(self, model, firm_employer):
        super().__init__(model)

        self.employer = firm_employer

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
        """Form desired consumption, bounded by money actually available."""
        target = (
            self.model.c0
            + self.marginal_propensity() * self.income
            + self.model.wealth_effect * self.wealth
        )
        affordable = self.wealth + self.income
        self.desired_consumption = min(max(target, 0.0), affordable)

    # ------------------------------------------------------------------
    def step_settlement(self):
        """Credit income, pay for delivered (rationed) goods, roll income forward."""
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
    """A household that also owns a firm and receives its dividends.

    Investment is now a *firm* decision funded by retained earnings, so the
    capitalist no longer plans or finances investment personally; it consumes
    like any household (at a lower MPC) and collects dividends.  Its net worth
    includes the money and capital of the firm it owns.
    """

    is_capitalist = True

    def __init__(self, model, firm_employer, firm_owned):
        super().__init__(model, firm_employer)
        self.owned_firm = firm_owned

    def marginal_propensity(self):
        return self.model.capitalist_mpc

    def net_worth(self):
        """Money balance + the money and capital of the owned firm."""
        return self.wealth + self.owned_firm.capital + self.owned_firm.money_buffer
