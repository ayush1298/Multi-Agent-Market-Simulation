# core/simulation.py
import numpy as np
import core.config as cfg
from core.market import MarketEnvironment
from core.agents_mm import MarketMaker
from core.agents_investor import Investor

class DealerMarketSimulation:
    def __init__(self, 
                 num_mm=2, 
                 num_inv=10, 
                 sigma_mkt=cfg.SIGMA_MKT_LOW):
        
        self.market_env = MarketEnvironment()
        self.sigma_mkt = sigma_mkt # Pass to env step if variable
        
        # Agents
        self.market_makers = [MarketMaker(f"MM_{i}") for i in range(num_mm)]
        
        # Investors (Heterogeneous)
        self.investors = []
        for i in range(num_inv):
            # Log scale distribution of sizes roughly as per paper Table 1
            mu = 0.5 + (i / num_inv) * 4.0
            self.investors.append(Investor(f"INV_{i}", mu_trade=mu))
            
        # Metrics & History
        self.history = []
        
        # Delayed Revenue Queue
        # List of lists: queue[t] contains list of trades made at time t
        # We process queue[t - T_delay] at time t
        self.trade_queue = [] # index = step
        
        # Reward tracking [mm_id][step_idx] -> Dict
        self.rewards = {mm.agent_id: [] for mm in self.market_makers}

    def run(self, steps=cfg.TOTAL_STEPS):
        for _ in range(steps):
            self.step()
            
    def step(self):
        # 0. Market Step
        self.market_env.step(volatility=self.sigma_mkt)
        current_mid = self.market_env.mid_price
        step_idx = self.market_env.step_count
        
        current_step_trades = [] # To be stored in queue
        
        step_log = {
            "time": step_idx,
            "mid_price": current_mid,
            "investor_trades": [],
            "hedge_trades": [],
            "mm_positions": {mm.agent_id: mm.net_position for mm in self.market_makers}
        }
        
        # 1. Update Tiering
        # Paper says: "At each time step... update tiering metric... sort"
        # We assume real-time update or start-of-step.
        for mm in self.market_makers:
            mm.update_tiering(None) # Data already inside MM
            
        # 2. Investor Trades
        for inv in self.investors:
            req = inv.generate_trade_request()
            if not req:
                continue
                
            vol, direction = req # vol > 0, direction +/- 1
            
            # Get Quotes
            best_mm = None
            best_spread = float('inf')
            
            for mm in self.market_makers:
                spread = mm.get_quote_spread(self.market_env, inv.agent_id, vol)
                if spread < best_spread:
                    best_spread = spread
                    best_mm = mm
            
            # Execute
            # Price = Mid + Direction * Spread
            exec_price = current_mid + direction * best_spread
            
            # MM Trade
            # Inv Buy (+1) -> MM Sell (-1)
            mm_signed_vol = -direction * vol
            
            best_mm.net_position += mm_signed_vol
            
            # Revenue Update (Spread Rev)
            spread_revenue = best_spread * vol
            best_mm.record_investor_trade_yield(inv.agent_id, spread_revenue, vol)
            
            # Record for Delayed Metrics
            trade_record = {
                "mm_id": best_mm.agent_id,
                "vol": mm_signed_vol, # Signed volume from MM perspective
                "price_at_trade": current_mid, # Ref price
                "step": step_idx
            }
            current_step_trades.append(trade_record)
            
            step_log["investor_trades"].append({
                "inv": inv.agent_id,
                "mm": best_mm.agent_id,
                "vol": mm_signed_vol,
                "price": exec_price
            })
            
            # Immediate Reward Logging (Spread)
            # We aggregate at end of step, but can track here too?
            # Let's aggregate later.
            
        # 3. Hedging
        for mm in self.market_makers:
            # Competitor Cost Function Wrapper
            def competitor_cost(vol_to_hedge):
                # We need best spread for this vol from OTHERS
                best_s = float('inf')
                for other in self.market_makers:
                    if other == mm: continue
                    # Assuming default/worst tier for inter-dealer?
                    # Or specific tier. Let's use default (last).
                    s = other.get_quote_spread(self.market_env, mm.agent_id, vol_to_hedge)
                    if s < best_s:
                        best_s = s
                return best_s
                
            hedge_vol, direction_h = mm.calculate_hedge_quantity(self.market_env, competitor_cost)
            
            if hedge_vol > 1e-4:
                # Execute Hedge
                # MM is Taker.
                # Find best Maker
                best_maker = None
                best_maker_spread = float('inf')
                
                for other in self.market_makers:
                    if other == mm: continue
                    s = other.get_quote_spread(self.market_env, mm.agent_id, hedge_vol)
                    if s < best_maker_spread:
                        best_maker_spread = s
                        best_maker = other
                
                if best_maker:
                    # Execute
                    # MM Taker trades 'direction_h * hedge_vol'
                    # Maker takes opposite
                    
                    taker_vol_signed = direction_h * hedge_vol
                    maker_vol_signed = -taker_vol_signed
                    
                    price_h = current_mid + direction_h * best_maker_spread
                    
                    mm.net_position += taker_vol_signed
                    best_maker.net_position += maker_vol_signed
                    
                    # Record Hedge Trade (Delayed Rev? Does Hedge count for Position Rev?)
                    # Yes, any change in position counts.
                    current_step_trades.append({
                        "mm_id": mm.agent_id,
                        "vol": taker_vol_signed,
                        "price_at_trade": current_mid,
                        "step": step_idx
                    })
                    current_step_trades.append({
                        "mm_id": best_maker.agent_id,
                        "vol": maker_vol_signed,
                        "price_at_trade": current_mid,
                        "step": step_idx
                    })
                    
                    step_log["hedge_trades"].append({
                        "taker": mm.agent_id,
                        "maker": best_maker.agent_id,
                        "vol": taker_vol_signed,
                        "spread_paid": best_maker_spread * hedge_vol
                    })

        self.trade_queue.append(current_step_trades)
        
        # 4. Calculate Rewards
        # Spread Rev: Included in Inv Trades (we can recap from step_log)
        # Hedging Cost: Included in Hedge Trades (spread_paid)
        # Position Rev: From queue[t - Tm]
        # Risk Cost: min(z * deltaP, 0)
        
        # Calculate P_change
        if step_idx > 1:
            p_prev = self.history[-1]["mid_price"]
        else:
            p_prev = current_mid # No risk cost on first step? or 0.
            
        p_delta = current_mid - p_prev
        
        # Delayed Rev
        delayed_idx = step_idx - cfg.TM_DELAY
        delayed_trades = []
        if delayed_idx >= 1: # 1-based indexing in queue storage approx?
             # trade_queue[0] is step 1.
             # if step_idx=5, delay=4. delayed_idx=1. trade_queue[0] matches?
             # We appended step 1 trades to index 0.
             # So delayed_idx should be index.
             # step_idx 5 (current). index 4.
             # target step 1. index 0.
             # index = (step_idx - 1) - delay
             queue_idx = (step_idx - 1) - cfg.TM_DELAY
             if queue_idx >= 0:
                 delayed_trades = self.trade_queue[queue_idx]
                 
        # Aggregation per MM
        for mm in self.market_makers:
            r_spread = 0.0
            c_hedge = 0.0
            r_pos = 0.0
            c_risk = 0.0
            
            # Spread Rev (from Investor trades this step where MM was Maker)
            for t in step_log["investor_trades"]:
                if t["mm"] == mm.agent_id:
                     # Price - Mid * Direction?
                     # Spread = |Price - Mid|
                     # Rev = Spread * Volume
                     spread = abs(t["price"] - current_mid)
                     r_spread += spread * abs(t["vol"])
                     
            # Hedging Cost (from Hedge trades this step where MM was Taker)
            for t in step_log["hedge_trades"]:
                if t["taker"] == mm.agent_id:
                    c_hedge += t["spread_paid"] # Already calc
                    
            # Need to negation? Reward formula says R_total = ... + C_hedge (negative?)
            # Plan md: C_hedge = -1 * (v * spread). (Eq 247)
            # So we subtract.
            
            # Position Rev
            for t in delayed_trades:
                if t["mm_id"] == mm.agent_id:
                    # v * (P_t - P_{t-Tm})
                    # Trade happened at P_{t-Tm}
                    p_old = t["price_at_trade"]
                    r_pos += t["vol"] * (current_mid - p_old)
                    
            # Risk Cost
            # min(z * deltaP, 0)
            # Use position at start? or end?
            # Plan.md: "z_{i,t} * (P_t - P_{t-1})"
            # Assuming z_{i,t} is position HELD during the interval.
            # Usually Start Position.
            # step_log["mm_positions"] is END position.
            # Start pos = End pos - NetFlow.
            # Or just use history[-1] pos.
            
            if self.history:
                z_start = self.history[-1]["mm_positions"][mm.agent_id]
            else:
                z_start = 0.0
                
            risk_val = z_start * p_delta
            c_risk = min(risk_val, 0.0) # Only penalty
            
            # Total
            total = r_spread + r_pos - c_hedge + c_risk
            
            self.rewards[mm.agent_id].append({
                "step": step_idx,
                "r_spread": r_spread,
                "r_pos": r_pos,
                "c_hedge": -c_hedge,
                "c_risk": c_risk,
                "total": total
            })
            
        self.history.append(step_log)
