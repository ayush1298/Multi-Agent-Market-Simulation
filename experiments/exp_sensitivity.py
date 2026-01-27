# experiments/exp_sensitivity.py
import matplotlib.pyplot as plt
import numpy as np
import os
import core.config as cfg
from core.simulation import DealerMarketSimulation

def run_sensitivity_experiment(output_dir="plots"):
    print("Running Experiment 1: Investor Price Sensitivity...")
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    # Parameters
    num_sims = 20
    steps = 96
    
    # Track Share per Investor ID (0 to 9)
    inv_ids = [f"INV_{k}" for k in range(10)]
    results = {inv: [] for inv in inv_ids} 
    
    print(f"  Simulations: {num_sims}, Steps: {steps}")
    
    for sim_idx in range(num_sims):
        if sim_idx % 5 == 0:
            print(f"  Sim {sim_idx}/{num_sims}...")
            
        sim = DealerMarketSimulation(num_mm=2, num_inv=10)
        
        target_mm = sim.market_makers[1] # Adaptive
        comp_mm = sim.market_makers[0] # Fixed Tier 2
        
        # Competitor: Fixed Tier 2
        comp_mm.update_tiering = lambda x: None
        comp_mm.investor_tiers = {inv: 2 for inv in inv_ids}
        
        # Target MM: Initializes at Tier 2 (Neutral) to ensure they win "some" trades (50%) initially
        # then adapts based on Yield.
        target_mm.investor_tiers = {inv: 2 for inv in inv_ids} 
        
        # Run
        for step in range(steps):
             # Force Comp to Tier 2 (redundant but safe)
             comp_mm.investor_tiers = {inv: 2 for inv in inv_ids}
             sim.step()
             
        # Collection
        trades_per_inv = {inv: {"target": 0, "total": 0} for inv in inv_ids}
        
        for step_log in sim.history:
            for trade in step_log["investor_trades"]:
                inv = trade["inv"]
                trades_per_inv[inv]["total"] += 1
                if trade["mm"] == target_mm.agent_id:
                    trades_per_inv[inv]["target"] += 1
                    
        # Calculate Share
        for inv in inv_ids:
            total = trades_per_inv[inv]["total"]
            target = trades_per_inv[inv]["target"]
            share = target / total if total > 0 else 0.5 
            results[inv].append(share)
            
    # Average Results
    avg_shares = []
    std_shares = []
    
    print("Results:")
    for inv in inv_ids:
        shares = results[inv]
        mean = np.mean(shares)
        std = np.std(shares)
        avg_shares.append(mean)
        std_shares.append(std)
        print(f"  {inv}: Share {mean:.2f} (+/- {std:.2f})")
        
    # Plot
    x_indices = range(len(inv_ids))
    
    plt.figure(figsize=(10, 6))
    plt.bar(x_indices, avg_shares, yerr=std_shares, alpha=0.7, capsize=5)
    plt.xticks(x_indices, inv_ids)
    plt.xlabel("Investor ID (Size Increases 0 -> 9)")
    plt.ylabel("Market Share of Adaptive MM")
    plt.title("Investor Price Sensitivity (Adaptive vs Fixed Tier 2)")
    plt.ylim(0, 1.0)
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    
    plt.savefig(f"{output_dir}/exp1_sensitivity.png")
    print(f"Saved {output_dir}/exp1_sensitivity.png")

if __name__ == "__main__":
    run_sensitivity_experiment()
