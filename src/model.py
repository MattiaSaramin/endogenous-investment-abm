import mesa
import random

from agents import Firm, Household, Capitalist


# ============================================================
# Inequality Metrics
# ============================================================

def compute_gini(values):

    x = sorted(values)
    N = len(x)

    if N == 0 or sum(x) == 0:
        return 0

    cumulative = sum(
        xi * (N - i)
        for i, xi in enumerate(x)
    )

    B = cumulative / (N * sum(x))

    return 1 + (1 / N) - 2 * B



def compute_income_gini(model):

    incomes = [
        a.income
        for a in model.agents
        if isinstance(a, Household)
    ]

    return compute_gini(incomes)



def compute_wealth_gini(model):

    wealth = [
        a.wealth
        for a in model.agents
        if isinstance(a, Household)
    ]

    return compute_gini(wealth)



# ============================================================
# Aggregate Variables
# ============================================================

def compute_aggregate_capital(model):

    return sum(
        f.capital
        for f in model.agents
        if isinstance(f, Firm)
    )



def compute_output(model):

    return sum(
        f.production
        for f in model.agents
        if isinstance(f, Firm)
    )



def compute_average_utilization(model):

    firms = [
        f
        for f in model.agents
        if isinstance(f, Firm)
    ]

    if len(firms) == 0:
        return 0

    return sum(
        f.utilization
        for f in firms
    ) / len(firms)



# ============================================================
# Main ABM
# ============================================================

class MacroModel(mesa.Model):

    def __init__(
        self,
        num_firms=10,
        num_households=100,
        pct_capitalists=0.10,

        # Firm parameters
        markup=0.2,
        beta=1.0,
        alpha=0.3,
        delta=0.02,

        # Consumption
        c0=0.01,
        c1=0.6,
        wealth_effect=0.1,

        # Investment
        theta=0.5,
        investment_sensitivity=1.0,
        target_utilization=0.8,

        # Productivity
        extra=0.1,

        # Reproducibility
        seed=None
    ):

        super().__init__()


        if seed is not None:
            random.seed(seed)



        # ----------------------------------------------------
        # Parameters
        # ----------------------------------------------------

        self.num_firms = num_firms
        self.num_households = num_households

        self.markup = markup

        # Production
        self.beta = beta
        self.alpha = alpha
        self.delta = delta
        self.extra = extra

        # Consumption
        self.c0 = c0
        self.c1 = c1
        self.wealth_effect = wealth_effect

        # Investment
        self.theta = theta
        self.investment_sensitivity = (
            investment_sensitivity
        )
        self.target_utilization = (
            target_utilization
        )

        # Aggregate investment
        self.total_investment = 0.0



        # ----------------------------------------------------
        # Create Firms
        # ----------------------------------------------------

        firms = []

        for _ in range(self.num_firms):

            firm = Firm(self)

            firms.append(firm)



        # ----------------------------------------------------
        # Create Households
        # ----------------------------------------------------

        num_capitalists = int(
            self.num_households *
            pct_capitalists
        )


        for i in range(self.num_households):

            employer = (
                firms[i % self.num_firms]
            )


            if i < num_capitalists:

                owned_firm = (
                    firms[i % self.num_firms]
                )

                household = Capitalist(
                    self,
                    firm_employer=employer,
                    firm_owned=owned_firm
                )

                owned_firm.owner = household

            else:

                household = Household(
                    self,
                    firm_employer=employer
                )



            # Labour market connection

            employer.workers.append(
                household
            )


            # Consumption network

            num_links = max(
                1,
                self.num_firms // 2
            )

            connected_firms = random.sample(
                firms,
                num_links
            )

            for firm in connected_firms:

                firm.customers.append(
                    household
                )



        # ----------------------------------------------------
        # Data Collection
        # ----------------------------------------------------

        self.datacollector = mesa.DataCollector(

            model_reporters={

                "Output":
                    compute_output,

                "Total_Capital":
                    compute_aggregate_capital,

                "Income_Gini":
                    compute_income_gini,

                "Wealth_Gini":
                    compute_wealth_gini,

                "Average_Utilization":
                    compute_average_utilization

            }
        )



    # ========================================================
    # Simulation Loop
    # ========================================================

    def step(self):


        # --------------------------------------------
        # 1. Household demand formation
        # --------------------------------------------

        for agent in self.agents:

            if isinstance(agent, Household):

                agent.step_demand()



        # --------------------------------------------
        # 2. Production
        # --------------------------------------------

        for agent in self.agents:

            if isinstance(agent, Firm):

                agent.step_production()



        # --------------------------------------------
        # 3. Firm accounting
        # --------------------------------------------

        for agent in self.agents:

            if isinstance(agent, Firm):

                agent.step_accounting()



        # --------------------------------------------
        # 4. Household accounting
        # --------------------------------------------

        for agent in self.agents:

            if isinstance(agent, Household):

                agent.step_accounting()



        # --------------------------------------------
        # 5. Capitalist investment
        # --------------------------------------------

        for agent in self.agents:

            if isinstance(agent, Capitalist):

                agent.step_investment()



        # Aggregate investment
        capitalists = [
            a
            for a in self.agents
            if isinstance(a, Capitalist)
        ]


        self.total_investment = sum(
            c.investment_injected
            for c in capitalists
        )



        # Store results

        self.datacollector.collect(self)