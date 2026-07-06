import mesa
import random
from agents import Firm, Household, Capitalist

def compute_gini(model):
    agent_incomes = [a.income for a in model.agents if isinstance(a, Household)]
    x = sorted(agent_incomes)
    N = len(agent_incomes)
    if sum(x) == 0:
        return 0
    B = sum(xi * (N - i) for i, xi in enumerate(x)) / (N * sum(x))
    return 1 + (1 / N) - 2 * B

def compute_aggregate_capital(model):
    return sum([f.capital for f in model.agents if isinstance(f, Firm)])

def compute_output(model):
    return sum([f.production for f in model.agents if isinstance(f, Firm)])

class MacroModel(mesa.Model):
    def __init__(self, num_firms=10, num_households=100, pct_capitalists=0.10, 
                 markup=0.1, beta=1.0, extra=0.1, c0=0.01, c1=0.6, 
                 gamma=0.5, alpha=0.3, delta=0.05, theta=0.2):
        
        super().__init__()
        
        self.num_firms = num_firms
        self.num_households = num_households
        self.markup = markup
        self.beta = beta
        self.extra = extra
        self.c0 = c0
        self.c1 = c1
        
        self.gamma = gamma    
        self.alpha = alpha    
        self.delta = delta    
        self.theta = theta    
        self.total_investment = 0.0 
        
        # --- 1. Agent Initialization ---
        firms = []
        for i in range(self.num_firms):
            f = Firm(self)
            firms.append(f)
            
        num_capitalists = int(self.num_households * pct_capitalists)
        
        # --- 2. Topology Initialization ---
        for i in range(self.num_households):
            employer = firms[i % self.num_firms]
            if i < num_capitalists:
                owned_firm = firms[i % self.num_firms] 
                h = Capitalist(self, firm_employer=employer, firm_owned=owned_firm)
            else:
                h = Household(self, firm_employer=employer)
                
            employer.workers.append(h)
            
            num_initial_links = max(1, self.num_firms // 2)
            connected_firms = random.sample(firms, num_initial_links)
            for f in connected_firms:
                f.customers.append(h)
                
        # --- 3. Data Collection ---
        self.datacollector = mesa.DataCollector(
            model_reporters={
                "Output": compute_output,
                "Gini_Index": compute_gini,
                "Total_Capital": compute_aggregate_capital
            }
        )

    def step(self):
        """
        Explicit, foolproof Python loops to enforce strict macroeconomic stages.
        """
        # Stage 1: Demand
        for a in self.agents:
            if isinstance(a, Household):
                a.step_demand()
                
        # Stage 2: Production
        for f in self.agents:
            if isinstance(f, Firm):
                f.step_production()
                
        # Stage 3: Accounting (Firms calculate sales & distribute new income)
        for f in self.agents:
            if isinstance(f, Firm):
                f.step_accounting()
                
        # Stage 4: Accounting (Households update wealth based on old income)
        for a in self.agents:
            if isinstance(a, Household):
                a.step_accounting()
                
        # Stage 5: Investment
        for c in self.agents:
            if isinstance(c, Capitalist):
                c.step_investment()
                
        # Feed macro investment back into the next period
        capitalists = [a for a in self.agents if isinstance(a, Capitalist)]
        self.total_investment = sum([c.investment_injected for c in capitalists])
        
        self.datacollector.collect(self)