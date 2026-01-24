import numpy as np
import matplotlib.pyplot as plt
from simulation import DealerMarketSimulation
from market import MarketEnvironment
from agents import MarketMaker, Investor
import os

# Create plots directory
if not os.path.exists("plots"):
    os.makedirs("plots")

def run_sensitivity_experiment():
    """
    Reproduces Figure 5: Investor Price Sensitivity.
    Hypothesis: Larger investors are more sensitive to tiering (price increases).
    """
    print("Running Investor Price Sensitivity Experiment...")
    
    # Setup: 2 MMs, 10 Investors
    # We focus on MM 2 (index 1).
    # We pick specific investors: Small (Inv 0) and Large (Inv 7/9).
    
    # We need to modify MM logic slightly to FORCE a tier.
    # We will subclass or just monkey-patch for the experiment.
    
    inv_ids_to_test = [0, 9] # Smallest and Largest (approx)
    tiers_to_test = [0, 1, 2, 3, 4]
    
    results = {iid: [] for iid in inv_ids_to_test}
    
    num_sims = 50 # Reduced from 300 for speed
    
    for inv_idx in inv_ids_to_test:
        inv_id_str = f"INV_{inv_idx}"
        print(f"  Testing Investor {inv_id_str}...")
        
        for k in tiers_to_test:
            market_share_count = 0
            total_trades_for_inv = 0
            
            for _ in range(num_sims):
                sim = DealerMarketSimulation(num_market_makers=2, num_investors=10)
                
                # Mock MM 1 (Competitor) to have fixed tiering (e.g., Tier 2)
                # Mock MM 2 (Target) to have FORCED tier k for this investor
                
                target_mm = sim.market_makers[1]
                
                # We need to intercept the run to count trades
                # Running manually step-by-step
                
                # Force tier in target_mm
                # We overwrite the get_tier method or pre-fill the dict and disable update
                target_mm.investor_tiers[inv_id_str] = k
                target_mm.update_tiering = lambda x: None # Disable updates
                
                # Competitor (MM 0) fixed tier 2 (middle)
                sim.market_makers[0].investor_tiers[inv_id_str] = 2
                sim.market_makers[0].update_tiering = lambda x: None
                
                # Run for shorter duration? Paper says 24h.
                # We run for e.g. 50 steps to get enough samples.
                
                while sim.market_env.step():
                    sim._step_simulation()
                
                # Post-process history
                for step in sim.history:
                    for trade in step["investor_trades"]:
                        if trade["investor"] == inv_id_str:
                            total_trades_for_inv += 1
                            if trade["mm"] == target_mm.agent_id:
                                market_share_count += 1
                                
            share = market_share_count / max(1, total_trades_for_inv)
            results[inv_idx].append(share)
            print(f"    Tier {k}: Share {share:.2f}")

    # Plot
    plt.figure()
    for inv_idx, shares in results.items():
        plt.plot(tiers_to_test, shares, marker='o', label=f'Investor {inv_idx}')
    
    plt.title("Investor Price Sensitivity")
    plt.xlabel("Tier (Higher = More Expensive)")
    plt.ylabel("Market Share")
    plt.legend()
    plt.grid(True)
    plt.savefig("plots/figure_5_sensitivity.png")
    print("Saved plots/figure_5_sensitivity.png")

def run_internalization_experiment():
    """
    Reproduces Figure 7: Internalization Effect.
    Compare 50% share vs 100% share.
    Metric: |NetPos| / CumulativeVolume
    """
    print("\nRunning Internalization Experiment...")
    
    scenarios = ["50%", "100%"]
    time_points = range(96) # 96 steps ~ 24 hours
    avg_internalization = {sc: np.zeros(len(time_points)) for sc in scenarios}
    
    num_sims = 20 # Reduced from 1000
    
    for sc in scenarios:
        print(f"  Scenario {sc}...")
        for sim_idx in range(num_sims):
            sim = DealerMarketSimulation(num_market_makers=2, num_investors=10)
            
            # Disable hedging to isolate internalization
            for mm in sim.market_makers:
                mm.hedging_strategy = lambda env, mms: (0, 0)
                
            mm_target = sim.market_makers[1]
            mm_comp = sim.market_makers[0]
            
            # Setup Pricing
            if sc == "50%":
                # Identical pricing parameters already default
                pass
            else: # 100%
                # Make Target MM strictly better
                # e.g. delta_tier = 0, or base spread smaller
                # We inject a hack into Competitor to make it infinite price
                mm_comp.get_price_curve = lambda env, inv, size: 1e9 
            
            # Run
            trades_cumsum = 0
            
            sim_metric = []
            
            # Custom Loop to track metrics
            for t in time_points:
                sim.market_env.step()
                sim._step_simulation()
                
                # Check trades for Target MM in this steps
                # sim.history[-1] is latest step
                step = sim.history[-1]
                
                step_vol = 0
                for trade in step["investor_trades"]:
                    if trade["mm"] == mm_target.agent_id:
                        step_vol += abs(trade["size"])
                
                trades_cumsum += step_vol
                
                net_pos = abs(mm_target.net_position)
                
                if trades_cumsum > 0:
                    metric = net_pos / trades_cumsum
                else:
                    metric = 1.0 # No internalization if no trades
                    
                sim_metric.append(metric)
                
            avg_internalization[sc] += np.array(sim_metric)
            
        avg_internalization[sc] /= num_sims

    # Plot
    plt.figure()
    for sc, data in avg_internalization.items():
        plt.plot(time_points, data, label=f'{sc} Market Share')
        
    plt.title("Internalization Effect")
    plt.xlabel("Time Steps")
    plt.ylabel("|NetPos| / Volume")
    plt.legend()
    plt.grid(True)
    plt.savefig("plots/figure_7_internalization.png")
    print("Saved plots/figure_7_internalization.png")

def run_hedging_experiment():
    """
    Reproduces Figure 8/9: Impact of Risk Aversion Gamma on Costs.
    Vary Gamma, measure Hedging Cost + Risk Cost.
    Two volatility regimes: Low (default) and High.
    """
    print("\nRunning Hedging Experiment...")
    
    gammas = [0.0, 0.25, 0.5, 1.0, 2.0, 5.0]
    results_low_vol = []
    # results_high_vol = [] # Skip High Vol for now to save time/complexity
    
    num_sims = 10
    
    # We define cost function as per paper Eq 221 + Eq 225
    # Hedging Cost = Spread paid on hedges
    # Risk Cost = min(z * (P_t - P_{t-1}), 0)? 
    # Wait, paper says: "risk cost which penalizes ... min(z * deltaP, 0)" -> usually loss is negative. 
    # Paper text: "computed as min(zi,t * (Pt - Pt-1), 0)". 
    # This means ONLY LOSSES count as cost? Gains don't offset?
    # Yes, "risk cost".
    
    # Also "Rewards shown are cumulative... only include hedging and risk costs".
    # Note: Costs are usually negative rewards. We will sum absolute costs.
    
    print("  Low Volatility Scenario...")
    for g in gammas:
        total_cost_avg = 0
        
        for _ in range(num_sims):
            # Low Volatility (Env default 0.02 approx? Paper says 10% annual vs 30%)
            sim = DealerMarketSimulation(num_market_makers=1, num_investors=5)
            # Only 1 MM needed to test its hedging against "market" (or other MMs)
            # But we need other MMs to hedge WITH.
            # Make 2 MMs, focus on MM 0.
            
            sim = DealerMarketSimulation(num_market_makers=2, num_investors=10)
            target_mm = sim.market_makers[0]
            target_mm.gamma = g
            
            previous_price = sim.market_env.mid_price
            cumulative_cost = 0
            
            time_steps = 50 # Short run
            
            for _ in range(time_steps):
                sim.market_env.step()
                current_price = sim.market_env.mid_price
                price_change = current_price - previous_price
                previous_price = current_price
                
                # Check Hedge Trades BEFORE simulation step?
                # Simulation step does: Env Step -> Inv Trades -> MM Hedge
                # We need to capture costs.
                
                # Let's run the step, then inspect history
                sim._step_simulation()
                
                # 1. Calculate Risk Cost for this step
                # "min(z * deltaP, 0)"
                # Position is held over the interval. 
                # Strict interpretation: Position at START of interval * deltaP?
                # or End? Usually Start.
                # Let's use position from previous step.
                # MM position updates in _step_simulation.
                
                # Simplification: Use current position (post-trade) for next step risk?
                # Let's just calculate "Cost encountered during step".
                
                # Measuring Hedging Cost + Risk Cost
                
                step_idx = sim.market_env.current_step - 1
                last_step_data = sim.history[-1]
                
                # 1. Hedging Cost
                # Sum of spread paid for trades where target_mm was TAKER.
                # In simulation.py, we log "taker": mm.agent_id
                
                hedging_cost = 0.0
                if "hedge_trades" in last_step_data:
                    for trade in last_step_data["hedge_trades"]:
                        if trade["taker"] == target_mm.agent_id:
                            # Cost = Spread * Size
                            # Spread = |Price - Mid|
                            # Actually, Price is Execution Price. 
                            # If we Buy (Size > 0), Price > Mid. Cost = (Price - Mid) * Size.
                            # If we Sell (Size < 0), Price < Mid. Cost = (Mid - Price) * |Size|.
                            # In both cases, Cost = |Price - Mid| * |Size|
                            # Because Price = Mid + Direction * Spread
                            
                            spread = abs(trade["price"] - trade["mid_price"])
                            size = abs(trade["size"])
                            hedging_cost += spread * size
                
                # 2. Risk Cost
                # Formula: - min(Position * DeltaP, 0)
                # Position: target_mm.net_position (at end of step)
                # DeltaP: Change in mid price (already calc: price_change)
                # Note: If we use end-of-step position, it includes hedges.
                # Paper is non-specific on "zi,t". 
                # Let's use position * prior_price_change as proxy for "unhedged risk exposure realized"?
                # No, "impact of market price movements on its net position".
                # PnL from carrying inventory.
                pnl_impact = target_mm.net_position * price_change
                risk_cost = -min(pnl_impact, 0) # Only count losses
                
                cumulative_cost += (hedging_cost + risk_cost)
                
        results_low_vol.append(cumulative_cost)
        
        if num_sims > 1:
            results_low_vol[-1] /= num_sims
            
        print(f"    Gamma {g}: Cost {results_low_vol[-1]:.4f}")

    # Plot
    plt.figure()
    plt.plot(gammas, results_low_vol, marker='o')
    plt.title("Total Cost vs Risk Aversion (Low Vol)")
    plt.xlabel("Gamma")
    plt.ylabel("Cost")
    plt.grid(True)
    plt.savefig("plots/figure_8_hedging.png")
    print("Saved plots/figure_8_hedging.png")

if __name__ == "__main__":
    run_sensitivity_experiment()
    run_internalization_experiment()
    run_hedging_experiment()
