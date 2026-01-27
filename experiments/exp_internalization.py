# experiments/exp_internalization.py
import matplotlib.pyplot as plt
import numpy as np
import os
import core.config as cfg
from core.simulation import DealerMarketSimulation

def run_internalization_experiment(output_dir="plots"):
    print("Running Experiment 2: Internalization Effect...")
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    scenarios = ["50%", "100%"]
    steps = 300
    num_sims = 1000
    
    avg_results = {s: np.zeros(steps) for s in scenarios}
    
    for sc in scenarios:
        print(f"  Scenario {sc}...")
        
        for _ in range(num_sims):
            sim = DealerMarketSimulation(num_mm=2, num_inv=10)
            target_mm = sim.market_makers[1]
            comp_mm = sim.market_makers[0]
            
            # Disable Hedging (Ref paper: "metrics... purely due to internalization")
            target_mm.gamma = 0.0
            target_mm.calculate_hedge_quantity = lambda a, b: (0.0, 0)
            comp_mm.gamma = 0.0
            comp_mm.calculate_hedge_quantity = lambda a, b: (0.0, 0)
            
            # Disable Tiering (Simplified case: No Tiering)
            # Both MMs must have same pricing curve (except for shift)
            target_mm.investor_tiers = {i: 0 for i in sim.investors} # Force Tier 0? Or doesn't matter if delta=0
            comp_mm.investor_tiers = {i: 0 for i in sim.investors}
            
            # Important: Set delta_tier = 0 to effectively remove tiering penalty
            cfg.MM_DELTA_TIER = 0.0 # Hack global or set per agent? 
            # Agent class uses cfg.MM_DELTA_TIER. 
            # Let's patch the get_quote of agents or patch cfg.
            # But we run parallel? No, valid sequential.
            # Better: Modify get_quote inside loop? No, that's messy.
            # Let's overwrite agent method or attributes if we had them.
            # Agents read cfg module. 
            
            # Cleanest: Inject logic. agent.get_quote uses `penalty = cfg.MM_DELTA_TIER * tier`.
            # We can't easily change cfg per agent.
            # We will MonkeyPatch the agent instance's get_quote_spread?
            # Or just set their tiers to 0 always.
            target_mm.update_tiering = lambda x: None # Disable updates
            target_mm.investor_tiers = {f"INV_{k}": 0 for k in range(10)}
            
            comp_mm.update_tiering = lambda x: None
            comp_mm.investor_tiers = {f"INV_{k}": 0 for k in range(10)}

            # Pricing Setup
            if sc == "100%":
                 # Target MM has strictly better pricing -> 100% share
                 # Make Competitor infinite expensive
                 comp_mm.get_quote_spread = lambda a, b, c: 1e9
            else:
                 # 50% -> Identical (default)
                 pass
                 
            # Run
            sim.run(steps=steps)
            
            # Calculate Metric: |NetPos| / CumVolume
            cum_vol = 0.0
            metric_traj = []
            
            # Step by step replay from history
            # Actually history stores step logs.
            for step_log in sim.history:
                # Find Target MM trades this step
                step_vol = 0.0
                for trade in step_log["investor_trades"]:
                    if trade["mm"] == target_mm.agent_id:
                        step_vol += abs(trade["vol"])
                        
                cum_vol += step_vol
                # Net Pos at end of step
                net_pos = step_log["mm_positions"][target_mm.agent_id]
                
                if cum_vol > 1e-9:
                    val = abs(net_pos) / cum_vol
                else:
                    val = 1.0 # Or 0? Paper starts at 1 probably? No trades = no internalization.
                    # Paper Fig 7: Starts around 1.0. 
                    
                metric_traj.append(val)
                
            avg_results[sc] += np.array(metric_traj)
            
        avg_results[sc] /= num_sims

    # Plot
    plt.figure()
    for sc, data in avg_results.items():
        plt.plot(range(steps), data, label=f'{sc} Market Share')
        
    plt.title("Internalization Effect (Figure 7 Recreated)")
    plt.xlabel("Time Steps")
    plt.ylabel("|NetPos| / Cumulative Volume")
    plt.legend()
    plt.grid(True)
    plt.savefig(f"{output_dir}/exp2_internalization.png")
    print(f"Saved {output_dir}/exp2_internalization.png")
    
    # Restore Global Config (Critical for subsequent experiments)
    cfg.MM_DELTA_TIER = 4.0 # Default value
    print("Restored cfg.MM_DELTA_TIER to default.")

if __name__ == "__main__":
    run_internalization_experiment()
