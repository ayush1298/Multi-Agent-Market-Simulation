# experiments/exp_hedging.py
import matplotlib.pyplot as plt
import numpy as np
import os
import core.config as cfg
from core.simulation import DealerMarketSimulation

def run_hedging_experiment(output_dir="plots"):
    print("Running Experiment 3: Hedging Costs vs Risk Aversion...")
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    gammas = [0.0, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0]
    results_cost = []
    
    num_sims = 5
    steps = 50
    
    # We test Low Volatility (default cfg)
    
    for g in gammas:
        print(f"  Gamma {g}...")
        total_cost_accum = 0.0
        
        for _ in range(num_sims):
            sim = DealerMarketSimulation(num_mm=2, num_inv=10)
            target_mm = sim.market_makers[0]
            target_mm.gamma = g
            
            sim.run(steps=steps)
            
            # Aggregate Rewards/Costs for Target MM
            # Reward = R_spread + R_pos - C_hedge + C_risk
            # We want "Total Cost" = -(Reward - Rev)?
            # Paper Fig 8: "Rewards shown are cumulative... only include hedging and risk costs".
            # So we sum (C_hedge (negative) + C_risk (negative)).
            # And then negate to show "Cost" (Positive).
            
            sim_hedging = 0.0
            sim_risk = 0.0
            
            for r_entry in sim.rewards[target_mm.agent_id]:
                sim_hedging += r_entry["c_hedge"] # This is negative (cost paid)
                sim_risk += r_entry["c_risk"] # Negative
                
            total_cost = -(sim_hedging + sim_risk)
            total_cost_accum += total_cost
            
        avg_cost = total_cost_accum / num_sims
        results_cost.append(avg_cost)
        print(f"    Avg Cost: {avg_cost:.4f}")

    # Plot
    plt.figure()
    plt.plot(gammas, results_cost, marker='o')
    plt.title("Total Cost vs Risk Aversion (Low Volatility)")
    plt.xlabel("Risk Aversion Gamma")
    plt.ylabel("Cumulative Cost (Hedging + Risk)")
    plt.grid(True)
    plt.savefig(f"{output_dir}/exp3_hedging.png")
    print(f"Saved {output_dir}/exp3_hedging.png")

if __name__ == "__main__":
    run_hedging_experiment()
