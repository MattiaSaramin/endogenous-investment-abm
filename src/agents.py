import mesa

class Firm(mesa.Agent):
    def __init__(self, model):
        super().__init__(model)
        self.workers = []       
        self.customers = []     
        self.inventory = 0.0    
        self.capital = 0.0      
        self.production = 0.0   
        self.sales = 0.0        
        self.faced_demand = 0.0
        self.dividend_pool = 0.0
        
    def step_production(self):
        # Divide demand evenly across the firms the consumer is linked to
        num_links = max(1, self.model.num_firms // 2)
        consumer_demand = sum([h.desired_consumption / num_links for h in self.customers])
        corporate_demand = self.model.total_investment / self.model.num_firms
        self.faced_demand = consumer_demand + corporate_demand
        
        max_capacity = self.model.beta * (1 + self.model.gamma * (self.capital ** self.model.alpha)) * (1 + self.model.extra) * len(self.workers)
        self.production = min(self.faced_demand, max_capacity)
        self.inventory += self.production

    def step_accounting(self):
        self.sales = min(self.faced_demand, self.inventory)
        self.inventory -= self.sales
        
        wage_pool = self.sales / (1 + self.model.markup)
        self.dividend_pool = (self.model.markup * self.sales) / (1 + self.model.markup)
        
        if len(self.workers) > 0:
            wage_per_worker = wage_pool / len(self.workers)
            for w in self.workers:
                w.next_income = wage_per_worker
                
        self.capital = (1 - self.model.delta) * self.capital


class Household(mesa.Agent):
    def __init__(self, model, firm_employer):
        super().__init__(model)
        self.employer = firm_employer
        self.wealth = 2.0               
        self.income = 2.0               
        self.next_income = 0.0
        self.desired_consumption = 0.0  
        self.actual_consumption = 0.0   
        
    def step_demand(self):
        # THE WEALTH EFFECT: Consumers spend out of income AND 10% of their hoarded wealth
        target = self.model.c0 + (self.model.c1 * self.income) + (0.1 * self.wealth)
        
        self.desired_consumption = min(target, self.wealth + self.income)
        self.actual_consumption = self.desired_consumption
        
    def step_accounting(self):
        self.wealth += (self.income - self.actual_consumption)
        self.income = self.next_income


class Capitalist(Household):
    def __init__(self, model, firm_employer, firm_owned):
        super().__init__(model, firm_employer)
        self.owned_firm = firm_owned
        self.investment_injected = 0.0
        
    def step_investment(self):
        self.income += self.owned_firm.dividend_pool
        
        excess_savings = max(0, self.income - self.actual_consumption)
        self.investment_injected = self.model.theta * excess_savings
        
        self.wealth -= self.investment_injected
        self.owned_firm.capital += self.investment_injected