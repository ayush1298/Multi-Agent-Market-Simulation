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
        
    # Parameters
    gammas = [0.0, 0.05, 0.25, 0.5, 1.0, 100.0]
    gamma_labels = {100.0: "Inf"} # For legend
    
    volatilities = [
        ("Low Volatility", cfg.SIGMA_MKT_LOW),   # 0.1
        ("High Volatility", cfg.SIGMA_MKT_HIGH)  # 0.3
    ]
    
    steps = 500 # Match Figure 8/9
    num_sims = 20
    hedge_horizon = 20
    
    for vol_name, vol_val in volatilities:
        print(f"  Result {vol_name} (Sigma={vol_val})...")
        
        plt.figure(figsize=(10, 6))
        
        for g in gammas:
            label = gamma_labels.get(g, str(g))
            print(f"    Gamma {label}...")
            
            # Storage for cumulative trajectories
            traj_sum = np.zeros(steps)
            
            for _ in range(num_sims):
                sim = DealerMarketSimulation(num_mm=1, num_inv=10, sigma_mkt=vol_val) 
                target_mm = sim.market_makers[0]
                target_mm.gamma = g
                target_mm.ex_liquidation_horizon = hedge_horizon
                
                sim.run(steps=steps)
                
                rewards = sim.rewards[target_mm.agent_id]
                
                # Metric: Only Hedging + Risk Costs (Negative Rewards)
                # simulation.py stores 'c_hedge' as Negative and 'c_risk' as Negative.
                totals = [r["c_hedge"] + r["c_risk"] for r in rewards]
                
                if len(totals) < steps:
                    totals += [0.0] * (steps - len(totals))
                    
                traj = np.cumsum(totals)
                traj_sum += traj
                
            avg_traj = traj_sum / num_sims
            plt.plot(range(steps), avg_traj, label=f"RiskAversion: {label}")
            
        plt.title(f"Impact of Hedging Risk Aversion on MM Reward - {vol_name}")
        plt.xlabel("Time step")
        plt.ylabel("Reward")
        plt.legend()
        plt.grid(True)
        
        filename = f"{output_dir}/exp3_hedging_{vol_name.split()[0].lower()}.png"
        plt.savefig(filename)
        print(f"    Saved {filename}")

if __name__ == "__main__":
    run_hedging_experiment()
