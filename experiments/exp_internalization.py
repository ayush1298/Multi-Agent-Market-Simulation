# experiments/exp_internalization.py
import matplotlib.pyplot as plt
import numpy as np
import os
import core.config as cfg
from core.simulation import DealerMarketSimulation
import pandas as pd

def run_internalization_experiment(output_dir="plots"):
    print("Running Experiment 2: Internalization Effect (Refined)...")
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    scenarios = ["50%", "100%"]
    steps = 300 # Match Figure 7 (300 steps)
    target_table_step = 96 # Table 2 is at 96 steps
    
    num_sims = 1000
    
    # Store all full trajectories to compute nanmean later
    all_trajectories = {s: [] for s in scenarios}
    
    for sc in scenarios:
        print(f"  Scenario {sc} Share (Simulating {num_sims} runs)...")
        
        for sim_idx in range(num_sims):
            if sim_idx % 100 == 0:
                print(f"    Sim {sim_idx}/{num_sims}...")
                
            sim = DealerMarketSimulation(num_mm=2, num_inv=10)
            target_mm = sim.market_makers[1]
            comp_mm = sim.market_makers[0]
            
            # OVERWRITE INVESTORS
            # Tuned p=0.1 to match Metric Magnitude
            mus = np.linspace(0.5, 7.0, 10)
            sim.investors = []
            for i, mu in enumerate(mus):
                from core.agents_investor import Investor
                inv = Investor(f"INV_{i}", mu_trade=mu, p_trade=0.1) 
                sim.investors.append(inv)
                
            # DISABLE HEDGING
            target_mm.calculate_hedge_quantity = lambda a, b: (0.0, 0)
            comp_mm.calculate_hedge_quantity = lambda a, b: (0.0, 0)
            
            # DISABLE TIERING
            target_mm.investor_tiers = {i.agent_id: 0 for i in sim.investors}
            target_mm.update_tiering = lambda x: None
            comp_mm.investor_tiers = {i.agent_id: 0 for i in sim.investors}
            comp_mm.update_tiering = lambda x: None
            
            # PRICING
            if sc == "100%":
                comp_mm.get_quoted_price = lambda env, inv, vol, direction: (
                    1e9 if direction == 1 else -1e9
                )
            else:
                 pass
                 
            # Run
            sim.run(steps=steps)
            
            # METRIC CALCULATION
            cum_vol = 0.0
            traj = []
            
            for step_log in sim.history:
                step_vol = 0.0
                for trade in step_log["investor_trades"]:
                    if trade["mm"] == target_mm.agent_id:
                        step_vol += abs(trade["vol"])
                
                cum_vol += step_vol
                net_pos = step_log["mm_positions"][target_mm.agent_id]
                
                if cum_vol > 1e-9:
                    val = abs(net_pos) / cum_vol
                else:
                    # Undefined. Using NaN to exclude from initial average
                    val = np.nan 
                    
                traj.append(val)
                
            all_trajectories[sc].append(np.array(traj))
            
    # Process Results
    results_mean = {}
    table_values = {s: [] for s in scenarios}
    
    for sc in scenarios:
        # Stack: (num_sims, steps)
        stack = np.vstack(all_trajectories[sc])
        
        # Compute NanMean (ignores NaNs at start)
        results_mean[sc] = np.nanmean(stack, axis=0)
        
        # Extract values for Table at specific index
        # We want the distribution of values at t=96 (index 95)
        # Handle cases where it might still be NaN? (Unlikely after 96 steps)
        # Replace NaN with 0 or exclude?
        # At step 96, if NaN, it means 0 trades in 96 steps. Very unlikely with p=0.1*10 = 1 trade/step avg.
        # But we filter.
        
        vals_at_96 = stack[:, target_table_step - 1]
        vals_clean = vals_at_96[~np.isnan(vals_at_96)]
        table_values[sc] = vals_clean

    # PLOT
    plt.figure(figsize=(10, 6))
    time_steps = range(1, steps + 1)
    
    for sc in scenarios:
        plt.plot(time_steps, results_mean[sc], label=f'{sc} Share')
        
    plt.title("Internalization Effect (Figure 7 Recreated)")
    plt.xlabel("Time Steps (15 min)")
    plt.ylabel("Internalization Metric |Z|/V")
    plt.legend()
    plt.grid(True)
    plt.ylim(0, 0.8) # Adjust Y-limit to zoom in relevant range
    
    plt.savefig(f"{output_dir}/exp2_internalization.png")
    print(f"\nSaved {output_dir}/exp2_internalization.png")
    
    # TABLE GENERATION
    print(f"\nTable 2. Internalization metric at {target_table_step} time steps (1 day)")
    print("-" * 40)
    print(f"{'METRIC':<20} {'50% SHARE':<10} {'100% SHARE':<10}")
    print("-" * 40)
    
    percentiles = [75, 50, 25]
    
    for p in percentiles:
        val_50 = np.percentile(table_values["50%"], p)
        val_100 = np.percentile(table_values["100%"], p)
        print(f"{p}TH PERCENTILE      {val_50:.2f}       {val_100:.2f}")
        
    print("-" * 40)
    
    # Restore Global Config
    cfg.MM_DELTA_TIER = 4.0 
    print("Restored cfg.MM_DELTA_TIER to default.")

if __name__ == "__main__":
    run_internalization_experiment()
