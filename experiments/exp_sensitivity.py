# experiments/exp_sensitivity.py
import matplotlib.pyplot as plt
import numpy as np
import os
import core.config as cfg
from core.simulation import DealerMarketSimulation
from core.agents_investor import Investor

def run_sensitivity_experiment(output_dir="plots"):
    print("Running Experiment 1: Investor Price Sensitivity (Rigorous Isolation)...")
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    # Parameters
    num_sims = 5 # Reduced count (10 inv * 5 tiers * 5 sims = 250 runs)
    steps = 96
    tiers = range(cfg.NUM_TIERS) # 0 to 4
    
    # Investor Setup
    num_inv = 10
    mu_min, mu_max = 0.5, 7.0
    mus = np.linspace(mu_min, mu_max, num_inv)
    fixed_p_trade = 0.25 # Constant frequency
    
    # Results Container: results[inv_idx][tier] = [share1, share2, ...]
    results = {i: {k: [] for k in tiers} for i in range(num_inv)}
    
    print(f"  Investors: 10, Mu: 0.5-7.0, Freq p={fixed_p_trade}")
    print(f"  Simulations per point: {num_sims}")
    
    total_runs = num_inv * len(tiers) * num_sims
    current_run = 0
    
    # Loop over Investors (Isolate J)
    for i_idx in range(num_inv):
        i_mu = mus[i_idx]
        inv_id_target = f"INV_{i_idx}"
        
        print(f"  Inv {inv_id_target} (Mu={i_mu:.1f})...")
        
        for k in tiers:
            # Run Sims
            for _ in range(num_sims):
                sim = DealerMarketSimulation(num_mm=2, num_inv=num_inv)
                
                # Overwrite Investors
                sim.investors = []
                for j in range(num_inv):
                    # All have same freq, different mu
                    inv = Investor(f"INV_{j}", mu_trade=mus[j], p_trade=fixed_p_trade)
                    sim.investors.append(inv)
                    
                # Setup MMs
                comp_mm = sim.market_makers[0]
                target_mm = sim.market_makers[1]
                
                # Tune Skew (Sigma=0.0005)
                # Agg Z ~ 1000. Need Skew < 1e-4. 
                # 0.5 * sig^2 * 1000 = 1e-4 => sig^2 = 2e-7 => sig ~ 0.00045
                comp_mm.sigma_est = 0.0005
                target_mm.sigma_est = 0.0005
                
                # Configure Tiers
                # Competitor: Fixed Tier 2 for ALL
                comp_mm.update_tiering = lambda x: None
                comp_mm.investor_tiers = {inv.agent_id: 2 for inv in sim.investors}
                
                # Target: 
                # Investor J -> Tier K
                # Others -> Tier 2 (Neutral Baseline)
                target_mm.update_tiering = lambda x: None
                target_tiers = {inv.agent_id: 2 for inv in sim.investors}
                target_tiers[inv_id_target] = k
                target_mm.investor_tiers = target_tiers
                
                # Run
                sim.run(steps=steps)
                
                # Measure Share for Investor J
                target_trades = 0
                total_trades = 0
                
                for step_log in sim.history:
                    for trade in step_log["investor_trades"]:
                        if trade["inv"] == inv_id_target:
                            total_trades += 1
                            if trade["mm"] == target_mm.agent_id:
                                target_trades += 1
                                
                share = target_trades / total_trades if total_trades > 0 else 0.5
                results[i_idx][k].append(share)
                
                current_run += 1
                if current_run % 50 == 0:
                    print(f"    Progress: {current_run}/{total_runs}")

    # Process & Plot
    avg_results = {i: [] for i in range(num_inv)}
    std_results = {i: [] for i in range(num_inv)}
    
    for i in range(num_inv):
        for k in tiers:
            shares = results[i][k]
            avg_results[i].append(np.mean(shares))
            std_results[i].append(np.std(shares))
            
    # Plot
    # Select Small (0), Mid (4), Large (9)
    indices = [0, 4, 9]
    plt.figure(figsize=(10, 6))
    
    for i in indices:
        mu = mus[i]
        plt.plot(tiers, avg_results[i], marker='o', label=f'Inv Mu={mu:.1f}') # yerr=std_results[i] too messy?
        
    plt.title("Investor Price Sensitivity (Share vs Tier)")
    plt.xlabel("Target MM Tier (Competitor Fixed at Tier 2)")
    plt.ylabel("Market Share")
    plt.xticks(tiers)
    plt.legend()
    plt.grid(True)
    plt.ylim(0, 1.0)
    plt.axhline(0.5, color='gray', linestyle='--', alpha=0.5)
    plt.axvline(2, color='gray', linestyle='--', alpha=0.5)
    
    plt.savefig(f"{output_dir}/exp1_sensitivity.png")
    print(f"Saved {output_dir}/exp1_sensitivity.png")
    
    print("\nResults (Avg Share):")
    print("Tier | Small(0.5) | Mid(3.4) | Large(7.0)")
    for k_idx, k in enumerate(tiers):
        s0 = avg_results[0][k_idx]
        s4 = avg_results[4][k_idx]
        s9 = avg_results[9][k_idx]
        print(f"  {k}  |   {s0:.2f}     |   {s4:.2f}   |   {s9:.2f}")

if __name__ == "__main__":
    run_sensitivity_experiment()
