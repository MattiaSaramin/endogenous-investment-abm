import mesa


class Firm(mesa.Agent):
    """
    Firm agents represent productive units.
    
    Each firm has:
    - workers
    - customers
    - capital stock
    - pending investment waiting for installation
    - production capacity
    """

    def __init__(self, model):
        super().__init__(model)

        self.workers = []
        self.customers = []

        # Production variables
        self.inventory = 0.0
        self.production = 0.0
        self.sales = 0.0
        self.faced_demand = 0.0

        # Capital variables
        self.capital = 1.0
        self.pending_capital = 0.0

        # Distribution variables
        self.dividend_pool = 0.0

        # Diagnostic variables
        self.capacity = 0.0
        self.utilization = 0.0


    def calculate_capacity(self):
        """
        Cobb-Douglas production function:

        Y = A * K^alpha * L^(1-alpha)

        Capital and labour jointly determine productive capacity.
        """

        labor = len(self.workers)

        if labor == 0:
            self.capacity = 0.0
            return

        self.capacity = (
            self.model.beta
            * (self.capital ** self.model.alpha)
            * (labor ** (1 - self.model.alpha))
            * (1 + self.model.extra)
        )


    def step_production(self):

        """
        Firms form demand expectations from:
        - household consumption
        - aggregate investment demand

        Production is constrained by capacity.
        """

        # Consumer demand distributed through network links
        num_links = max(1, self.model.num_firms // 2)

        consumer_demand = sum(
            h.desired_consumption / num_links
            for h in self.customers
        )

        # Investment expenditure enters aggregate demand
        investment_demand = (
            self.model.total_investment
            / self.model.num_firms
        )

        self.faced_demand = (
            consumer_demand
            + investment_demand
        )


        self.calculate_capacity()


        self.production = min(
            self.faced_demand,
            self.capacity
        )


        self.inventory += self.production


        if self.capacity > 0:
            self.utilization = (
                self.production /
                self.capacity
            )
        else:
            self.utilization = 0



    def step_accounting(self):

        """
        Firms distribute revenues between:
        - wages
        - dividends

        Capital depreciates.
        """

        self.sales = min(
            self.faced_demand,
            self.inventory
        )

        self.inventory -= self.sales


        # Revenue distribution
        wage_pool = (
            self.sales /
            (1 + self.model.markup)
        )

        self.dividend_pool = (
            self.sales -
            wage_pool
        )

        if isinstance(self.owner, Capitalist):
            self.owner.next_dividend = self.dividend_pool


        # Wage payments
        if len(self.workers) > 0:

            wage = (
                wage_pool /
                len(self.workers)
            )

            for worker in self.workers:
                worker.next_income = wage


        # Capital depreciation
        self.capital *= (
            1 -
            self.model.delta
        )


        # Installed investment becomes productive capital
        self.capital += self.pending_capital

        self.pending_capital = 0.0



class Household(mesa.Agent):
    """
    Household agents consume according to:

    C = c0 + c1Y + lambda W

    where wealth influences consumption.
    """

    def __init__(self, model, firm_employer):

        super().__init__(model)

        self.employer = firm_employer

        self.wealth = 2.0
        self.income = 2.0

        self.next_income = 0.0

        self.desired_consumption = 0.0
        self.actual_consumption = 0.0

        self.next_dividend = 0.0



    def step_demand(self):

        consumption_target = (
            self.model.c0
            +
            self.model.c1 * self.income
            +
            self.model.wealth_effect * self.wealth
        )


        self.desired_consumption = min(
            consumption_target,
            self.wealth + self.income
        )

        self.actual_consumption = (
            self.desired_consumption
        )



    def step_accounting(self):

        self.wealth += (
            self.income -
            self.actual_consumption
        )

        self.income = (
            self.next_income
        )



class Capitalist(Household):
    """
    Capitalists are households owning firms.

    They receive dividends and transform part
    of their surplus savings into investment.
    """

    def __init__(
        self,
        model,
        firm_employer,
        firm_owned
    ):

        super().__init__(
            model,
            firm_employer
        )

        self.owned_firm = firm_owned

        self.investment_injected = 0.0



    def step_investment(self):

        # Receive profits
        self.income += (
            self.owned_firm.dividend_pool
        )


        savings = max(
            0,
            self.income -
            self.actual_consumption
        )


        # Investment responds to utilization pressure

        utilization_effect = (
            1
            +
            self.model.investment_sensitivity *
            (
                self.owned_firm.utilization
                -
                self.model.target_utilization
            )
        )


        utilization_effect = max(
            0,
            utilization_effect
        )


        self.investment_injected = (
            self.model.theta
            *
            savings
            *
            utilization_effect
        )


        # Wealth finances investment
        self.wealth -= (
            self.investment_injected
        )


        # Investment is installed next period
        self.owned_firm.pending_capital += (
            self.investment_injected
        )