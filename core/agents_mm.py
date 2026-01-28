# core/agents_mm.py
import numpy as np
import core.config as cfg
from utils.math_utils import solve_almgren_chriss

class MarketMaker:
    def __init__(self, agent_id, 
                 alpha=cfg.MM_ALPHA_DEFAULT, 
                 gamma=0.5, 
                 n_max=20, 
                 sigma_est=0.01):
        self.agent_id = agent_id
        
        # Policy Params
        self.alpha = alpha
        self.gamma = gamma
        self.n_max = n_max
        self.sigma_est = sigma_est
        
        # State
        self.net_position = 0.0
        self.investor_tiers = {} # ID -> int
        self.investor_yield_ema = {} # ID -> float
        
        # Helper for optimization callback
        self._current_competitor_cost_func = None
        
    def update_tiering(self, trade_data_list):
        """
        Updates EMA of Yield for investors and re-assigns tiers.
        trade_data_list depends on Simulation calling convention.
        But actually, we update EMA incrementally as trades happen?
        Plan.md says: "Executed at start of step t... Update psi... Sort."
        """
        # Step 1: Update EMA is handled during trade execution (see record_trade).
        # Here we just Sort and Assign.
        
        if not self.investor_yield_ema:
            return
            
        # Sort
        sorted_investors = sorted(self.investor_yield_ema.items(), key=lambda x: x[1], reverse=True)
        # x is (id, yield)
        
        n = len(sorted_investors)
        for rank, (iid, _) in enumerate(sorted_investors):
            # Quantile classification
            # Tier 0 is best (top)
            # rank 0 -> tier 0
            # rank N -> tier K-1
            
            fraction = rank / n
            tier = int(fraction * cfg.NUM_TIERS)
            tier = min(tier, cfg.NUM_TIERS - 1)
            self.investor_tiers[iid] = tier

    def get_quote_spread(self, market_env, investor_id, volume):
        """
        Returns s(v, u).
        """
        tier = self.investor_tiers.get(investor_id, cfg.NUM_TIERS - 1)
        
        s_ref_v = market_env.get_reference_price_curve(volume)
        s_ref_0 = market_env.get_reference_price_curve(0)
        
        # Avoid div by zero
        if s_ref_0 < 1e-12:
            ratio = 1.0
        else:
            ratio = s_ref_v / s_ref_0
            
        # Formula
        base = s_ref_0 * (ratio ** self.alpha)
        penalty = cfg.MM_DELTA_TIER * tier
        
        return base + penalty

    def get_quoted_price(self, market_env, investor_id, volume, direction):
        """
        Returns the quoted price for an investor trade.
        Price = Mid + Direction * Spread / 2  (No, the formula returns Full Spread usually? Check paper. )
        Paper Eq 13: r^i(v) = R(v) ...
        Usually R(v) is "price impact" or "half-spread".
        Let's assume get_quote_spread returns the Half-Spread term relative to Mid.
        
        Plus Inventory Skew:
        Skew = - gamma * sigma^2 * NetPosition
        (Ho-Stoll logic: If Long, lower price to sell. Skew < 0.)
        
        Price = Mid + Skew + Direction * HalfSpread
        """
        half_spread = self.get_quote_spread(market_env, investor_id, volume)
        mid = market_env.mid_price
        
        # Calculate Skew
        # Using self.gamma (risk aversion) and self.sigma_est
        # Skew = - gamma * (sigma^2) * Position
        # Note: Position is signed.
        skew = - self.gamma * (self.sigma_est ** 2) * self.net_position
        
        price = mid + skew + direction * half_spread
        return price

    def calculate_hedge_quantity(self, market_env, competitor_cost_func):
        """
        Runs Almgren-Chriss optimization to determine immediate hedge size.
        competitor_cost_func: Callable(v) -> marginal cost (spread).
        """
        if abs(self.net_position) < 1e-6:
            return 0.0, 0
            
        # We need to solve for schedule x.
        # Initial position z.
        
        # Pass callback to utils
        x0 = solve_almgren_chriss(
            initial_position_z=abs(self.net_position),
            n_steps=self.n_max,
            gamma=self.gamma,
            sigma=self.sigma_est,
            cost_function_callable=competitor_cost_func
        )
        
        hedge_size = x0 * abs(self.net_position)
        
        # Direction: Reduce position.
        # If Long (pos > 0), Sell (-1).
        # If Short (pos < 0), Buy (+1).
        direction = -np.sign(self.net_position)
        
        return hedge_size, direction

    def update_investor_yield(self, investor_id, total_revenue, volume):
        """
        Updates Yield EMA.
        Psi_t = Beta * Psi_{t-1} + (1-Beta) * Yield_trade
        Yield = Total Revenue / Volume
        """
        if abs(volume) < 1e-9:
             return
             
        y_trade = total_revenue / abs(volume)
        beta = 0.9 # Weight decay factor
        
        prev = self.investor_yield_ema.get(investor_id, 0.0)
        # If first time, init with current
        if investor_id not in self.investor_yield_ema:
             self.investor_yield_ema[investor_id] = y_trade
        else:
             self.investor_yield_ema[investor_id] = beta * prev + (1 - beta) * y_trade
