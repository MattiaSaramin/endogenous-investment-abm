"""
Agent definitions for the Endogenous-Investment Keynesian ABM
(Cobb-Douglas core + endogenous labour market — roadmap point 11).

The model is *stock-flow consistent* (SFC).  With internal (retained-earnings)
financing the conserved money stock is

    sum(household wealth + income) + sum(firm money_buffer) = const

and the firm cash account is an intra-period pass-through (``money_buffer`` returns
to zero every period).

Behavioural core:

1. **Cobb-Douglas production with essential capital.**
   ``Y* = A * K^alpha * L^(1-alpha)`` — if ``K -> 0`` then ``Y* -> 0``.

2. **Fixed wage ``w_bar`` (not residual).**  Distribution is set by the wage:
   ``wage_bill = w_bar * L`` and profit is the residual ``sales - w_bar*L``.  The
   wage share therefore becomes a *measured outcome* (bounded above by ``1-alpha``),
   not an identity.  Unemployed households earn no wage, so their consumption falls
   — this is what makes the Keynesian demand channel bite.

3. **Endogenous employment.**  Each firm hires the minimum of three limits:
   labour needed for expected demand, the profit-maximising labour (where the
   marginal product equals ``w_bar``), and what the unemployed pool can supply.
   The economy-wide cap ``L <= N`` is what restores decreasing returns to capital
   (otherwise ``L_profitmax ∝ K`` gives an AK model with no steady state).

4. **Internal financing via retained earnings.**  Firms retain exactly what they
   invest and distribute the rest as dividends; investment is a profit-flow
   decision with a utilisation accelerator and a floor.

5. **Class saving + wealth effect.**  Workers consume a large share of income,
   capitalists a small share; consumption also responds to money wealth.
"""

import mesa


class Firm(mesa.Agent):
    """A productive unit: Cobb-Douglas technology, fixed wage, internal financing.

    Chooses employment from expected demand and the profit-max condition, produces
    with the workers it actually hires, pays a fixed wage ``w_bar`` per employed
    worker, and funds its own investment out of current retained earnings.
    """

    def __init__(self, model, productivity=1.0, initial_capital=5.0):
        super().__init__(model)

        # Network / labour links
        self.workers = []            # currently employed households
        self.customers = []
        self.owner = None

        # Technology / real state
        self.productivity = productivity          # A
        self.capital = initial_capital            # K (essential: K=0 -> Y*=0)

        # Internal finance
        self.money_buffer = 0.0
        self.profit_last_period = 0.0
        self.utilization_last_period = 0.0

        # Expectations / employment
        self.expected_demand = 0.0
        self.desired_employment = 0
        self.L_profitmax = 0.0                    # labour where MPL = w_bar

        # Investment plan / delivery
        self.desired_investment = 0.0
        self.investment_delivered = 0.0
        self.util_effect = 1.0                    # diagnostic: accelerator signal

        # Flow variables (recomputed every period)
        self.consumption_demand = 0.0
        self.investment_demand = 0.0
        self.faced_demand = 0.0
        self.capacity = 0.0              # A*K^a*L^(1-a) with L = employed
        self.profitmax_capacity = 0.0    # A*K^a*L_profitmax^(1-a)
        self.production = 0.0
        self.sales = 0.0
        self.rationing = 1.0
        self.utilization = 0.0           # Y / profitmax_capacity

        # Distribution
        self.wage_bill = 0.0
        self.gross_profit = 0.0
        self.retained = 0.0
        self.dividend_pool = 0.0

    # ------------------------------------------------------------------
    # Labour demand
    # ------------------------------------------------------------------
    def plan_employment(self):
        """Desired headcount = floor(min(labour-for-demand, profit-max labour)).

            L_demand    = (Y_e / (A*K^alpha)) ** (1/(1-alpha))    # invert Cobb-Douglas
            L_profitmax = ((1-alpha)*A*K^alpha / w_bar) ** (1/alpha)   # MPL = w_bar
            desired     = floor(min(L_demand, L_profitmax))

        ``Y_e`` is last period's realised demand (static expectations).  ``floor``
        (not round) so a firm never overshoots the profit-max point.  The firm never
        hires where the marginal product of labour is below the wage, which keeps
        gross profit positive.
        """
        K = self.capital
        A = self.productivity
        alpha = self.model.alpha
        w = self.model.wage_rate

        if K <= 0.0 or A <= 0.0:
            self.desired_employment = 0
            self.L_profitmax = 0.0
            return

        AKa = A * (K ** alpha)

        if self.expected_demand > 0.0:
            labour_for_demand = (self.expected_demand / AKa) ** (1.0 / (1.0 - alpha))
        else:
            labour_for_demand = 0.0

        if w > 0.0:
            self.L_profitmax = ((1.0 - alpha) * AKa / w) ** (1.0 / alpha)
        else:
            self.L_profitmax = float(self.model.num_households)

        self.desired_employment = max(0, int(min(labour_for_demand, self.L_profitmax)))

    # ------------------------------------------------------------------
    # Investment plan (unchanged in form; accelerator on last utilisation)
    # ------------------------------------------------------------------
    def plan_investment(self):
        """Plan investment from the flow of profit, capped by current profit."""
        util_effect = 1.0 + self.model.beta * (
            self.utilization_last_period - self.model.target_utilization
        )
        util_effect = max(0.0, util_effect)
        self.util_effect = util_effect          # diagnostic: accelerator signal

        desired = self.model.retention_ratio * self.profit_last_period * util_effect
        self.desired_investment = min(
            max(desired, self.model.investment_floor), self.profit_last_period
        )
        self.desired_investment = max(0.0, self.desired_investment)

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

    # ------------------------------------------------------------------
    # Supply side
    # ------------------------------------------------------------------
    def step_production(self):
        """Produce with the employed workforce; ration; set utilisation.

        Production capacity uses *employed* labour; utilisation is measured
        against the *profit-max* capacity, so ``u < 1`` signals a firm held below
        its profit-max scale by weak demand (the correct accelerator signal) and
        ``u = 1`` at the profit-max point.
        """
        L = len(self.workers)
        A = self.productivity
        alpha = self.model.alpha
        K = self.capital

        if K > 0.0 and L > 0:
            self.capacity = A * (K ** alpha) * (L ** (1.0 - alpha))
        else:
            self.capacity = 0.0

        self.production = min(self.faced_demand, self.capacity)

        self.rationing = (
            self.production / self.faced_demand if self.faced_demand > 1e-12 else 1.0
        )

        if K > 0.0 and self.L_profitmax > 0.0:
            self.profitmax_capacity = A * (K ** alpha) * (self.L_profitmax ** (1.0 - alpha))
        else:
            self.profitmax_capacity = 0.0

        self.utilization = (
            self.production / self.profitmax_capacity
            if self.profitmax_capacity > 1e-12 else 0.0
        )
        self.utilization_last_period = self.utilization

        # Static expectation for next period.
        self.expected_demand = self.faced_demand

    # ------------------------------------------------------------------
    # Accounting / distribution
    # ------------------------------------------------------------------
    def step_accounting(self):
        """Pay a fixed wage per employed worker; profit is the residual.

            wage_bill    = w_bar * L
            gross_profit = sales - wage_bill
            retained     = I_planned
            dividends    = gross_profit - retained

        Identity ``wage_bill + dividends + retained == sales`` holds exactly.
        Unemployed households are simply not paid, so the wage bill falls with
        employment — the demand channel.
        """
        self.sales = self.production
        L = len(self.workers)

        self.wage_bill = self.model.wage_rate * L
        self.gross_profit = self.sales - self.wage_bill

        self.retained = self.desired_investment
        self.dividend_pool = self.gross_profit - self.retained
        self.money_buffer += self.retained

        if L > 0:
            for worker in self.workers:
                worker.next_income += self.model.wage_rate

        if self.owner is not None:
            self.owner.next_income += self.dividend_pool

        self.profit_last_period = self.gross_profit

    def step_investment(self):
        """Pay for delivered investment goods; return the residual as dividends.

        The buffer holds exactly this period's retained earnings; after paying for
        delivered goods, any residual (from goods-market rationing) is paid to the
        owner, so **the buffer returns to zero every period**.  Capital follows a
        one-period gestation lag.
        """
        self.investment_delivered = self.desired_investment * self.model.investment_rationing

        self.money_buffer -= self.investment_delivered
        self.capital = (1.0 - self.model.delta) * self.capital + self.investment_delivered

        if self.owner is not None:
            self.owner.next_income += self.money_buffer
        self.money_buffer = 0.0


class Household(mesa.Agent):
    """A worker household.

    Supplies labour (employed or unemployed), consumes
    ``C = c0 + mpc * income + lambda * wealth`` out of a money balance, and
    accumulates unspent income as wealth.  Income is the wage received while
    employed (zero when unemployed), plus dividends for capitalists.
    """

    is_capitalist = False

    def __init__(self, model):
        super().__init__(model)

        # Employment state (set by the labour market)
        self.employed = False
        self.employer = None

        self.wealth = 2.0
        self.income = 2.0
        self.next_income = 0.0

        self.desired_consumption = 0.0
        self.actual_consumption = 0.0
        self.savings = 0.0
        self.cash_constrained = False      # diagnostic: liquidity cap binds

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
        # Diagnostic: the liquidity cap binds -> the household spends everything
        # it has (effective MPC ~ 1 at the margin).
        self.cash_constrained = target > affordable
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

    It supplies labour like any household (can be employed or unemployed) and, in
    addition, collects the dividends of the firm it owns.  Its net worth includes
    the money and capital of that firm.
    """

    is_capitalist = True

    def __init__(self, model, firm_owned):
        super().__init__(model)
        self.owned_firm = firm_owned

    def marginal_propensity(self):
        return self.model.capitalist_mpc

    def net_worth(self):
        """Money balance + the money and capital of the owned firm."""
        return self.wealth + self.owned_firm.capital + self.owned_firm.money_buffer
