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
    steps = 96
    num_sims = 20
    
    avg_results = {s: np.zeros(steps) for s in scenarios}
    
    for sc in scenarios:
        print(f"  Scenario {sc}...")
        
        for _ in range(num_sims):
            sim = DealerMarketSimulation(num_mm=2, num_inv=10)
            target_mm = sim.market_makers[1]
            comp_mm = sim.market_makers[0]
            
            # Disable Hedging (Ref paper: "metrics... purely due to internalization")
            # We set Gamma = 0 or overload hedging func
            target_mm.gamma = 0.0
            target_mm.calculate_hedge_quantity = lambda a, b: (0.0, 0)
            
            comp_mm.gamma = 0.0
            comp_mm.calculate_hedge_quantity = lambda a, b: (0.0, 0)
            
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

if __name__ == "__main__":
    run_internalization_experiment()
