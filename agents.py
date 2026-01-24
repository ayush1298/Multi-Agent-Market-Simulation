import numpy as np
from scipy.stats import norm

class Agent:
    def __init__(self, agent_id):
        self.agent_id = agent_id

class MarketMaker(Agent):
    def __init__(self, agent_id, num_tiers=5, alpha=0.5, delta_tier=0.0001, 
                 gamma=0.5, n_max=20, sigma_est=0.01):
        """
        Args:
            agent_id: Unique ID
            num_tiers: Number of price tiers (K)
            alpha: Pricing policy deformation parameter
            delta_tier: Constant tier penalty step
            gamma: Risk aversion parameter for hedging
            n_max: Max hedging horizon (steps)
            sigma_est: Estimated volatility for hedging calc
        """
        super().__init__(agent_id)
        
        # Parameters
        self.num_tiers = num_tiers
        self.alpha = alpha
        self.delta_tier = delta_tier
        self.gamma = gamma
        self.n_max = n_max
        self.sigma_est = sigma_est
        
        # State
        self.net_position = 0.0
        self.cash = 0.0
        self.trade_history = [] # list of dicts
        
        # Tiering State: map investor_id -> tier (0 is best)
        # Using a default tier for unknown investors
        self.investor_tiers = {} 
        self.default_tier = num_tiers - 1 # Worst tier by default
        
        # Metrics for tiering (Investor ID -> Metric)
        self.investor_revenue_yield = {}
        self.investor_volume = {}
        
    def get_tier(self, investor_id):
        return self.investor_tiers.get(investor_id, self.default_tier)
    
    def update_tiering(self, all_investor_ids):
        """
        Updates tiers based on historical revenue yield.
        Simple implementation: Sort investors by yield and assign quantiles.
        """
        if not self.investor_revenue_yield:
            return
            
        # Create list of (investor_id, yield)
        yields = []
        for iid in all_investor_ids:
            y = self.investor_revenue_yield.get(iid, 0.0)
            yields.append((iid, y))
            
        # Sort descending (Higher yield = Better, so assign to lower tier index)
        yields.sort(key=lambda x: x[1], reverse=True)
        
        # Assign tiers
        n = len(yields)
        for rank, (iid, _) in enumerate(yields):
            # Map rank to tier 0..K-1
            # Top fraction gets tier 0, next tier 1, etc.
            tier = int((rank / n) * self.num_tiers)
            tier = min(tier, self.num_tiers - 1)
            self.investor_tiers[iid] = tier

    def get_price_curve(self, market_env, investor_id, trade_size):
        """
        Returns the spread (price relative to mid) for a specific investor and size.
        s(v, u) = S_ref(0) * (S_ref(v)/S_ref(0))^alpha + s_tier(u)
        """
        tier = self.get_tier(investor_id)
        
        s_ref_v = market_env.get_reference_price_curve(trade_size)
        s_ref_0 = market_env.get_reference_price_curve(0) # Base spread
        
        # Pricing formula Eq 354
        base_term = s_ref_0 * ((s_ref_v / s_ref_0) ** self.alpha)
        tier_penalty = self.delta_tier * tier
        
        spread = base_term + tier_penalty
        return spread

    def hedging_strategy(self, market_env, other_mms):
        """
        Determines hedge trade size based on Almgren & Chriss logic (Section 3.2.3).
        Returns: (hedge_size, direction) or (0, 0)
        """
        if self.net_position == 0:
            return 0, 0
            
        z = self.net_position
        # We need to hedge to reduce position towards 0.
        # If z > 0 (Long), we Sell (-). If z < 0 (Short), we Buy (+).
        # Direction to trade: -sign(z)
        
        # Optimal schedule depends on:
        # Cost function c(v) (market impact)
        # Risk aversion gamma
        # Volatility sigma
        
        # Simplified linear cost approximation for derivation: c(v) = k * v 
        # Paper uses generic c(v) but then derives closed form for linear?
        # "Since c(v_hedge) is an increasing function..."
        # The Almgren-Chriss solution (classic) for linear cost and L2 risk is 
        # a specific trajectory sinh/cosh or geometric.
        # Paper heuristic: "first solves for schedule (xk)... then take v_hedge = z * x0"
        
        # Let's implement the specific logic for VaR minimization if possible, 
        # or use the standard Almgren-Chriss formula result which is:
        # x_k ~ sinh(kappa * (T - t_k)) / sinh(kappa * T) structure.
        
        # Let's assume a simplified linear cost c(v) = lambda * v for the internal model calculation.
        # The actual cost is min(other_mm_prices).
        
        # To make this robust without overly complex optimization loop at every step:
        # We define a "Hedge Rate" based on gamma.
        # Higher gamma -> Faster hedging (larger initial chunk).
        # Lower gamma -> Slower hedging.
        
        # If gamma ~ 0, hedge very little.
        # If gamma large, hedge almost all immediately.
        
        # Heuristic from paper Fig 4/text:
        # "Once gamma and Nmax chosen... solve for schedule."
        # Let's use a mapping: hedge_fraction = f(gamma, n_max)
        
        # Almgren Chriss standard solution for linear impact:
        # velocity = z * kappa * coth(kappa * T) ...
        # Resulting discrete trade fraction x0:
        # x0 = (1 - exp(-kappa * dt)) or similar.
        
        # Let's approximate x0:
        # Factor F depends on gamma.
        # If gamma is high, F -> 1.
        # If gamma is low, F -> 1/Nmax (uniform).
        
        # Let's use a sigmoid or bounded linear to map gamma to fraction [1/Nmax, 1].
        # Paper 3.2.3 doesn't give the explicit closed form used, likely numerical.
        # We will use this approximation:
        hedge_fraction = min(1.0, (1.0 / self.n_max) + (self.gamma * 0.1))
        # Wait, gamma scale in paper is 0 to >2.
        # Gamma=0 -> Time-Neutral -> TWAP? No, Eq 438 says min Expected Cost only?
        # Actually standard AC with gamma=0 is TWAP (constant rate). So x0 = 1/Nmax.
        # With gamma > 0, we front-load.
        
        if self.gamma < 1e-4:
             hedge_fraction = 1.0 / self.n_max
        else:
            # Simple acceleration
            hedge_fraction = (1.0 / self.n_max) * (1.0 + self.gamma * 2.0)
            
        hedge_fraction = min(hedge_fraction, 1.0)
        
        trade_size = abs(z) * hedge_fraction
        direction = -np.sign(z) # Opposite to position
        
        return trade_size, direction

    def record_trade(self, counterparty_id, size, price, current_mid_price):
        """
        Updates position and logging.
        size: signed size (+ Buy, - Sell) from MM perspective.
        """
        self.net_position += size
        self.cash -= (size * price) # If we buy, cash decreases
        
        self.trade_history.append({
            "counterparty": counterparty_id,
            "size": size,
            "price": price,
            "mid_price": current_mid_price
        })
        
        # Update metrics for tiering (if counterparty is investor)
        # Yield = Revenue / volume
        # We need to track this better.
        pass

class Investor(Agent):
    def __init__(self, agent_id, p_trade=0.5, mu_trade=1.0, sigma_trade=0.5, p_buy=0.5):
        super().__init__(agent_id)
        self.p_trade = p_trade
        self.mu_trade = mu_trade
        self.sigma_trade = sigma_trade
        self.p_buy = p_buy
        
    def generate_trade_request(self):
        """
        Returns trade size (signed) or None.
        """
        if np.random.random() > self.p_trade:
            return None
        
        # Log-normal size
        size = np.random.lognormal(self.mu_trade, self.sigma_trade)
        
        # Direction
        is_buy = np.random.random() < self.p_buy
        signed_size = size if is_buy else -size
        
        return signed_size
