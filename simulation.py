from market import MarketEnvironment
from agents import MarketMaker, Investor
import numpy as np

class DealerMarketSimulation:
    def __init__(self, num_market_makers=2, num_investors=10):
        self.market_env = MarketEnvironment()
        
        self.market_makers = [
            MarketMaker(
                agent_id=f"MM_{i}", 
                num_tiers=5, 
                alpha=0.5, 
                delta_tier=0.0001
            ) for i in range(num_market_makers)
        ]
        
        # Heterogeneous Investors (vary size and freq)
        self.investors = []
        for i in range(num_investors):
            # Vary mu_trade from 0.5 to 4.5 (log scale approx)
            mu = 0.5 + (i / num_investors) * 4.0 
            inv = Investor(
                agent_id=f"INV_{i}",
                mu_trade=mu, # Paper Table 1 ranges
                sigma_trade=0.2,
                p_trade=0.5 # 50% chance per step
            )
            self.investors.append(inv)
            
        # Metrics storage
        self.history = []

    def run(self):
        """Runs the simulation until completion."""
        print(f"Starting simulation with {len(self.market_makers)} MMs and {len(self.investors)} Investors.")
        
        while self.market_env.step():
            self._step_simulation()
            
        print("Simulation completed.")
        return self.history

    def _step_simulation(self):
        step_data = {
            "time": self.market_env.current_step,
            "mid_price": self.market_env.mid_price,
            "mm_positions": {},
            "investor_trades": [],
            "hedge_trades": []
        }
        
        # 1. Update MM Tiering (periodically or every step)
        all_inv_ids = [inv.agent_id for inv in self.investors]
        for mm in self.market_makers:
            mm.update_tiering(all_inv_ids)

        # 2. Investors generate trade requests
        for inv in self.investors:
            signed_size = inv.generate_trade_request()
            if signed_size is None or signed_size == 0:
                continue
                
            trade_size = abs(signed_size)
            trade_dir = 1 if signed_size > 0 else -1 # 1 for Buy, -1 for Sell (Investor persp)
            
            # Investor asks for quotes
            best_mm = None
            best_spread = float('inf')
            
            for mm in self.market_makers:
                # MM quotes spread s(v, u)
                spread = mm.get_price_curve(self.market_env, inv.agent_id, trade_size)
                # Ensure random tie-breaking if identical? Usually not identical due to tiering.
                if spread < best_spread:
                    best_spread = spread
                    best_mm = mm
            
            # Execute Trade
            # Investor buys -> MM Sells (-size) at Mid + Spread
            # Investor sells -> MM Buys (+size) at Mid - Spread
            
            # Exec Price relative to mid: Direction * Spread
            # Actual Price = Mid + Direction * Spread
            # If Inv Buys (1): Price = Mid + Spread (Matches MM Sell Ask)
            # If Inv Sells (-1): Price = Mid - Spread (Matches MM Buy Bid)
            
            # NOTE: Paper convention "Spread" s(v,u) is distance from Mid.
            # Ask = Mid + s, Bid = Mid - s.
            
            exec_price = self.market_env.mid_price + (trade_dir * best_spread)
            
            # Record at MM side
            # MM perspective: Counter to Investor.
            # Inv Buy -> MM Sell (-size)
            mm_signed_size = -signed_size
            best_mm.record_trade(inv.agent_id, mm_signed_size, exec_price, self.market_env.mid_price)
            
            # Update Revenue Tracking for Tiering (Yield)
            # Revenue = Spread * Volume
            inv_revenue = best_spread * trade_size
            curr_rev = best_mm.investor_revenue_yield.get(inv.agent_id, 0.0)
            # Simple accumulating average
            # Ideally exponential moving average
            best_mm.investor_revenue_yield[inv.agent_id] = curr_rev + inv_revenue # Tracking total revenue for simplified sorting

            step_data["investor_trades"].append({
                "investor": inv.agent_id,
                "mm": best_mm.agent_id,
                "size": signed_size,
                "price": exec_price
            })

        # 3. MMs Hedge
        # MM trades with other MMs
        for mm in self.market_makers:
            # Check hedging need
            hedge_size, direction = mm.hedging_strategy(self.market_env, self.market_makers)
            
            if hedge_size > 0.1: # Threshold to avoid tiny trades
                # Find best quote from OTHER MMs
                # MM acts as taker here
                best_counterparty = None
                best_hedge_spread = float('inf')
                
                for other in self.market_makers:
                    if other == mm:
                        continue
                    # Taking liquidity from other MM
                    # Other MM sees 'mm' as a participant.
                    # Currently MMs don't tier each other in my code (default tier).
                    hedge_spread = other.get_price_curve(self.market_env, mm.agent_id, hedge_size)
                    if hedge_spread < best_hedge_spread:
                        best_hedge_spread = hedge_spread
                        best_counterparty = other
                
                if best_counterparty:
                    # Execute Hedge
                    # MM wants to trade 'direction' * hedge_size
                    # Current MM is Taker. Counterparty is Maker.
                    
                    taker_signed_size = direction * hedge_size
                    maker_signed_size = -taker_signed_size
                    
                    price = self.market_env.mid_price + (direction * best_hedge_spread)
                    
                    mm.record_trade(best_counterparty.agent_id, taker_signed_size, price, self.market_env.mid_price)
                    best_counterparty.record_trade(mm.agent_id, maker_signed_size, price, self.market_env.mid_price)

                    step_data["hedge_trades"].append({
                        "taker": mm.agent_id,
                        "maker": best_counterparty.agent_id,
                        "size": taker_signed_size,
                        "price": price,
                        "mid_price": self.market_env.mid_price
                    })
        
        # Record State
        for mm in self.market_makers:
            step_data["mm_positions"][mm.agent_id] = mm.net_position
            
        self.history.append(step_data)

if __name__ == "__main__":
    sim = DealerMarketSimulation()
    sim.run()
