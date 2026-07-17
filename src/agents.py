"""
Agent definitions for the Endogenous-Investment Keynesian ABM
(normalised-CES core + endogenous labour market — roadmap point 11 + brief 04).

The model is *stock-flow consistent* (SFC).  With internal (retained-earnings)
financing the conserved money stock is

    sum(household wealth + income) + sum(firm money_buffer) = const

and the firm cash account is an intra-period pass-through (``money_buffer`` returns
to zero every period).

Behavioural core:

1. **Normalised CES production, elasticity of substitution ``sigma``.**

       Y* = Y0 * [ pi0*(K/K0)^r + (1-pi0)*(L/L0)^r ] ^ (1/r),   r = (sigma-1)/sigma

   The Cobb-Douglas core is the ``sigma = 1`` (``r = 0``) member of this family and
   Leontief the ``sigma -> 0`` member.  Capital is essential only for ``sigma <= 1``.
   See :func:`ces_capacity` for why the *normalised* form is mandatory here.

2. **Fixed wage ``w_bar`` (not residual).**  Distribution is set by the wage:
   ``wage_bill = w_bar * L`` and profit is the residual ``sales - w_bar*L``.  The
   wage share is a *measured outcome*, bounded above by the profit-max wage share
   :func:`ces_wage_share_profitmax` (which equals ``1-pi0`` only at ``sigma = 1``).
   Unemployed households earn no wage, so their consumption falls — this is what
   makes the Keynesian demand channel bite.

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

import math

import mesa


# ======================================================================
# Normalised CES technology
# ======================================================================
#
# WHY NORMALISED.  The textbook CES ``Y = A*[a*K^r + (1-a)*L^r]^(1/r)`` cannot be
# used to *sweep* sigma: varying ``r`` at fixed ``(A, a)`` also moves the implied
# factor shares and the efficiency level, so ``A`` and ``a`` are not comparable
# across sigma and any change of behaviour is unattributable.  The normalised form
# (Klump & de La Grandville 2000; Klump & Saam 2008; Klump, McAdam & Willman 2012)
# fixes a base point ``(K0, L0, Y0)`` and the base-point capital share ``pi0``, so
# every sigma-variant passes through the same point with the same factor shares and
# two economies differ *only* by sigma.
#
# CAVEAT, declared not hidden: Temple (2012) argues normalisation does not isolate
# "pure" effects of sigma and that sigma is not a deep parameter.  Normalisation is
# used here as a *comparison device* that makes sigma-variants commensurable at a
# base point — not as a claim of causal identification.
#
# The base point is a MODELLING CHOICE (see model.ANCHOR_* for how it was measured).

#: ``|r|`` below this uses the Cobb-Douglas (``r = 0``) branch, which is the exact
#: analytical limit.  ``1/r`` is singular at ``r = 0``; this is *the* classic CES
#: implementation bug.  1e-6 keeps the relative error of the CES branch at the
#: boundary near 1e-10 (checked in tests/test_model.py::test_ces_r_branch_is_continuous).
R_EPS = 1e-6

_INF = float("inf")


def ces_r(sigma):
    """Substitution parameter ``r = (sigma-1)/sigma``."""
    if sigma <= 0.0:
        raise ValueError("sigma must be > 0")
    return (sigma - 1.0) / sigma


def _Y0(A, K0, L0, pi0):
    """Base-point capacity.

    RULE (brief 04 §2.3): ``Y0`` is *computed* from the capacity function, never
    measured.  Measured output is ``min(demand, capacity)``, so anchoring on it
    would break the identity with Cobb-Douglas at sigma = 1.  With this ``Y0`` the
    ``r = 0`` branch is identically ``A*K^pi0*L^(1-pi0)`` for *every* ``(K, L)``,
    not merely at the base point.
    """
    return A * (K0 ** pi0) * (L0 ** (1.0 - pi0))


def ces_capacity(K, L, A, K0, L0, pi0, sigma):
    """Normalised CES capacity ``Y*(K, L)``.

    Limits: ``sigma -> 0`` gives ``Y0*min(K/K0, L/L0)`` (Leontief), ``sigma = 1``
    Cobb-Douglas, ``sigma -> inf`` the linear ``Y0*(pi0*K/K0 + (1-pi0)*L/L0)``.

    Capital is essential only for ``sigma <= 1``: for ``sigma > 1`` labour alone
    produces (``K = 0 => Y* > 0``), which is a property of the technology, not a bug.
    """
    if A <= 0.0:
        return 0.0
    r = ces_r(sigma)

    if abs(r) < R_EPS:
        # Cobb-Douglas branch.  Written in the *original* expression tree so that
        # sigma = 1 reproduces the labour-market branch bit-for-bit (brief §10.1).
        if K <= 0.0 or L <= 0.0:
            return 0.0
        return A * (K ** pi0) * (L ** (1.0 - pi0))

    Y0 = _Y0(A, K0, L0, pi0)

    # Degenerate factors: 0**r is +inf for r < 0, so handle before the arithmetic.
    if K <= 0.0 or L <= 0.0:
        if r < 0.0:
            return 0.0                       # both factors essential (sigma < 1)
        if K <= 0.0 and L <= 0.0:
            return 0.0
        if K <= 0.0:
            return Y0 * ((1.0 - pi0) ** (1.0 / r)) * (L / L0)
        return Y0 * (pi0 ** (1.0 / r)) * (K / K0)

    # log-sum-exp: (K/K0)**r overflows for strongly negative r (small sigma).
    a = math.log(pi0) + r * math.log(K / K0)
    b = math.log1p(-pi0) + r * math.log(L / L0)
    m = a if a > b else b
    lse = m + math.log(math.exp(a - m) + math.exp(b - m))
    return Y0 * math.exp(lse / r)


def ces_capital_ceiling(K, A, K0, L0, pi0, sigma):
    """``Y_max(K)``: the output ceiling as ``L -> inf``.  Finite only for sigma < 1.

    For ``sigma < 1`` capital caps output no matter how much labour is hired::

        L -> inf  =>  Y* -> Y0 * pi0**(1/r) * (K/K0)

    Demand above this ceiling cannot be met by *any* finite ``L`` — the
    "Leontief-like" regime where capital, not demand, is the binding constraint.
    """
    r = ces_r(sigma)
    if r >= -R_EPS:
        return _INF                          # no capital ceiling for sigma >= 1
    if A <= 0.0 or K <= 0.0:
        return 0.0
    return _Y0(A, K0, L0, pi0) * (pi0 ** (1.0 / r)) * (K / K0)


def ces_labour_for_demand(Ye, K, A, K0, L0, pi0, sigma):
    """Labour needed to produce expected demand ``Ye`` — the inverse of the CES.

        l~ = ( (y~^r - pi0*k~^r) / (1-pi0) ) ** (1/r)

    Returns ``+inf`` when no finite ``L`` reaches ``Ye`` (sigma < 1 and
    ``Ye > Y_max(K)``: capital is the binding constraint), and ``0.0`` when capital
    alone already covers demand (possible for sigma > 1).
    """
    if Ye <= 0.0:
        return 0.0
    if A <= 0.0:
        return _INF
    r = ces_r(sigma)

    if abs(r) < R_EPS:
        if K <= 0.0:
            return _INF                      # capital essential, demand unreachable
        AKa = A * (K ** pi0)                 # original expression tree (brief §10.1)
        return (Ye / AKa) ** (1.0 / (1.0 - pi0))

    Y0 = _Y0(A, K0, L0, pi0)
    log_yr = r * math.log(Ye / Y0)

    if K <= 0.0:
        if r < 0.0:
            return _INF                      # capital essential
        log_pk = -_INF                       # pi0 * 0**r = 0 for r > 0
    else:
        log_pk = math.log(pi0) + r * math.log(K / K0)

    # T = y~^r - pi0*k~^r;  sign(T) is decided on the logs (no overflow).
    if log_pk >= log_yr:
        # T <= 0.  For r < 0 that means Ye is above the capital ceiling (no finite
        # L); for r > 0 it means capital alone already covers demand.
        return _INF if r < 0.0 else 0.0

    d = log_pk - log_yr                      # < 0
    log_lr = log_yr + math.log1p(-math.exp(d)) - math.log1p(-pi0)
    return L0 * math.exp(log_lr / r)


def ces_labour_profitmax(K, A, w, K0, L0, pi0, sigma):
    """Labour where ``MPL = w`` (price = 1).  May be ``0.0`` or ``+inf``.

        q = ( w*L0 / ((1-pi0)*Y0) ) ** sigma
        l~ = k~ * ( pi0 / (q**r - (1-pi0)) ) ** (1/r)

    Existence requires ``D = q**r - (1-pi0) > 0``.  ``D <= 0`` means opposite things
    on the two sides of sigma = 1, so the branch is on the sign of ``r``:

    * ``sigma > 1``: MPL has a positive floor ``(1-pi0)**(1/r) * Y0/L0``; if ``w``
      is below it, hiring is always profitable => ``L_profitmax = +inf`` and the
      workforce ``N`` becomes the binding constraint.
    * ``sigma < 1``: MPL has a finite *maximum* ``(1-pi0)**(1/r) * Y0/L0`` at
      ``L -> 0``; if ``w`` exceeds it the firm never hires => ``L_profitmax = 0``.
    """
    if A <= 0.0:
        return 0.0
    if w <= 0.0:
        return _INF                          # free labour: hire without limit
    r = ces_r(sigma)

    if abs(r) < R_EPS:
        if K <= 0.0:
            return 0.0
        AKa = A * (K ** pi0)                 # original expression tree (brief §10.1)
        return ((1.0 - pi0) * AKa / w) ** (1.0 / pi0)

    Y0 = _Y0(A, K0, L0, pi0)

    if K <= 0.0:
        if r < 0.0:
            return 0.0                       # capital essential
        mpl_flat = ((1.0 - pi0) ** (1.0 / r)) * (Y0 / L0)
        return _INF if w < mpl_flat else 0.0

    # q**r == z**(sigma-1) with z = w*L0/((1-pi0)*Y0);  written in z to avoid a
    # needless round-trip through q.
    z = w * L0 / ((1.0 - pi0) * Y0)
    D = (z ** (sigma - 1.0)) - (1.0 - pi0)
    if D <= 0.0:
        return _INF if r > 0.0 else 0.0
    return L0 * (K / K0) * ((pi0 / D) ** (1.0 / r))


def ces_mpl(K, L, A, K0, L0, pi0, sigma):
    """Marginal product of labour ``(1-pi0)*(Y0/L0)*(y~/l~)**(1-r)``.

    Decreasing in ``L`` for ``K > 0`` (constant returns to scale).  Strictly so in
    exact arithmetic for any sigma > 0, but as sigma -> 0 the technology approaches
    the Leontief kink where MPL is flat below it: at sigma = 0.05 consecutive values
    are within 1 ulp and the monotonicity is only weak in floating point.
    """
    if L <= 0.0 or A <= 0.0:
        return _INF
    r = ces_r(sigma)
    Y0 = _Y0(A, K0, L0, pi0)
    Y = ces_capacity(K, L, A, K0, L0, pi0, sigma)
    if Y <= 0.0:
        return 0.0 if r >= 0.0 else _INF
    return (1.0 - pi0) * (Y0 / L0) * (((Y / Y0) / (L / L0)) ** (1.0 - r))


def ces_wage_share_profitmax(A, w, K0, L0, pi0, sigma):
    """Wage share *at the profit-max point*: ``(1-pi0) * z**(1-sigma)``.

    With constant returns this depends only on ``(w, sigma, anchor)`` — not on ``K``
    — because ``MPL = w`` pins the K/L ratio.  It equals ``1-pi0`` exactly at
    sigma = 1 (the old ``wage share <= 1-alpha`` bound) and is the sigma-dependent
    upper bound on the realised wage share, since ``w*L/Y`` rises with ``L`` and the
    firm never hires past the profit-max point.

    Returns NaN when no interior profit-max exists (``D <= 0``), where the bound has
    no referent.
    """
    if A <= 0.0 or w <= 0.0:
        return float("nan")
    Y0 = _Y0(A, K0, L0, pi0)
    z = w * L0 / ((1.0 - pi0) * Y0)
    r = ces_r(sigma)
    if abs(r) >= R_EPS:
        if (z ** (sigma - 1.0)) - (1.0 - pi0) <= 0.0:
            return float("nan")
    return (1.0 - pi0) * (z ** (1.0 - sigma))


class Firm(mesa.Agent):
    """A productive unit: normalised-CES technology, fixed wage, internal financing.

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
        self.L_profitmax = 0.0                    # labour where MPL = w_bar (may be inf)
        self.L_demand = 0.0                       # labour for expected demand (may be inf)
        self.binding_constraint = "demand"        # diagnostic: which limit bites
        self.labour_rationed = False              # diagnostic: unemployed pool ran dry

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
        """Desired headcount = floor(min(labour-for-demand, profit-max labour, N)).

        ``Y_e`` is last period's realised demand (static expectations).  ``floor``
        (not round) so a firm never overshoots the profit-max point.  The firm never
        hires where the marginal product of labour is below the wage, which keeps
        gross profit positive.

        Either limit can be ``+inf`` once sigma != 1 (see :func:`ces_labour_for_demand`
        and :func:`ces_labour_profitmax`), so the workforce ``N`` also caps the
        *desired* headcount — there are only ``N`` workers in the economy and
        ``int(inf)`` would raise.  At sigma = 1 both limits are finite and well below
        ``N``, so this cap never binds and the baseline is untouched.

        ``binding_constraint`` records which limit bites; ``"capital"`` is the
        sigma < 1 regime where demand exceeds ``Y_max(K)`` and *no* finite ``L``
        reaches it.
        """
        K = self.capital
        A = self.productivity
        m = self.model
        w = m.wage_rate

        if A <= 0.0:
            self.desired_employment = 0
            self.L_profitmax = 0.0
            self.L_demand = 0.0
            self.binding_constraint = "profitmax"
            return

        self.L_demand = ces_labour_for_demand(
            self.expected_demand, K, A, m.K0, m.L0, m.pi0, m.sigma
        )
        self.L_profitmax = ces_labour_profitmax(
            K, A, w, m.K0, m.L0, m.pi0, m.sigma
        )

        if self.L_demand == _INF:
            # sigma < 1 only: demand sits above Y_max(K), so *no* amount of hiring
            # reaches it — only capital does.  This takes priority over "profitmax":
            # the firm does stop at L_profitmax, but the distinguishing fact is that
            # even hiring past it (at a loss) could not meet demand.
            self.binding_constraint = "capital"
        elif self.L_demand <= self.L_profitmax:
            self.binding_constraint = "demand"
        else:
            self.binding_constraint = "profitmax"

        limit = min(self.L_demand, self.L_profitmax, float(m.num_households))
        self.desired_employment = max(0, int(limit))

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

        CONVENTION for ``L_profitmax = +inf`` (possible only for sigma > 1, where
        MPL never falls to ``w_bar``): the profit-max capacity is ``+inf`` and
        ``u = 0``.  This is the honest limit, not a fudge — as ``L_profitmax -> inf``
        the profit-max capacity diverges and ``Y / Y*_pm -> 0`` continuously, so the
        firm reads as maximally far below its profit-max scale.  The accelerator then
        sits at its floor ``1 + beta*(0 - target_utilization)``.
        """
        L = len(self.workers)
        A = self.productivity
        m = self.model
        K = self.capital

        self.capacity = ces_capacity(K, L, A, m.K0, m.L0, m.pi0, m.sigma)

        self.production = min(self.faced_demand, self.capacity)

        self.rationing = (
            self.production / self.faced_demand if self.faced_demand > 1e-12 else 1.0
        )

        if self.L_profitmax == _INF:
            self.profitmax_capacity = _INF
            self.utilization = 0.0
        else:
            self.profitmax_capacity = ces_capacity(
                K, self.L_profitmax, A, m.K0, m.L0, m.pi0, m.sigma
            )
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
