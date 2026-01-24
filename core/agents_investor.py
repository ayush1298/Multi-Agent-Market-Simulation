# core/agents_investor.py
import numpy as np

class Investor:
    def __init__(self, agent_id, 
                 p_trade=0.5, 
                 mu_trade=1.0, 
                 sigma_trade=0.5, 
                 p_buy=0.5,
                 is_sophisticated=False,
                 sophisticated_prob=0.0):
        self.agent_id = agent_id
        
        # Params
        self.p_trade = p_trade
        self.mu_trade = mu_trade # LogNormal(mu, sigma)
        self.sigma_trade = sigma_trade
        
        self.p_buy = p_buy
        
        self.is_sophisticated = is_sophisticated
        self.sophisticated_prob = sophisticated_prob
        
    def generate_trade_request(self, future_price_delta=0.0):
        """
        Returns (volume, direction).
        volume > 0.
        direction: +1 (Buy), -1 (Sell).
        Returns None if no trade.
        """
        if np.random.random() > self.p_trade:
            return None
            
        # Size
        vol = np.random.lognormal(self.mu_trade, self.sigma_trade)
        
        # Direction
        if self.is_sophisticated and np.random.random() < self.sophisticated_prob:
            # Oracle logic:
            # If future price rises (delta > 0), Buy.
            # If future price falls (delta < 0), Sell.
            if future_price_delta > 0:
                direction = 1
            else:
                direction = -1
        else:
            # Standard logic
            if np.random.random() < self.p_buy:
                direction = 1
            else:
                direction = -1
                
        return vol, direction
