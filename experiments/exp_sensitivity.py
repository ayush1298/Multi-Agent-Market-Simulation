# experiments/exp_sensitivity.py
import matplotlib.pyplot as plt
import os
import core.config as cfg
from core.simulation import DealerMarketSimulation

def run_sensitivity_experiment(output_dir="plots"):
    print("Running Experiment 1: Investor Price Sensitivity...")
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    tiers_to_test = range(cfg.NUM_TIERS)
    # Pick a "Large" and "Small" investor from the heterogeneous set
    # Sim has 10 investors. 0=Small, 9=Large.
    inv_indices = [0, 9]
    
    results = {idx: [] for idx in inv_indices}
    
    # We run N sims per point
    num_sims = 30
    steps = 50
    
    for idx in inv_indices:
        inv_id = f"INV_{idx}"
        print(f"  Testing {inv_id}...")
        
        for k in tiers_to_test:
            share_accum = 0.0
            total_matches = 0
            
            for _ in range(num_sims):
                sim = DealerMarketSimulation(num_mm=2, num_inv=10)
                
                # Setup:
                # MM_0: Competitor. Standard/Fixed Tier.
                # MM_1: Target. FORCE Tier k for inv_id.
                
                # We need to hack the tiering update to prevent overwrite
                target_mm = sim.market_makers[1]
                target_mm.investor_tiers[inv_id] = k
                # Disable update_tiering for this MM
                target_mm.update_tiering = lambda x: None
                
                # Competitor: Tier 2 (Middle)
                comp_mm = sim.market_makers[0]
                comp_mm.investor_tiers[inv_id] = 2
                comp_mm.update_tiering = lambda x: None
                
                # Run
                sim.run(steps=steps)
                
                # Count Trades
                for step_log in sim.history:
                    for trade in step_log["investor_trades"]:
                        if trade["inv"] == inv_id:
                            total_matches += 1
                            if trade["mm"] == target_mm.agent_id:
                                share_accum += 1
                                
            avg_share = share_accum / max(1, total_matches)
            results[idx].append(avg_share)
            print(f"    Tier {k}: {avg_share:.2f}")

    # Plot
    plt.figure()
    for idx, shares in results.items():
        plt.plot(tiers_to_test, shares, marker='o', label=f'Investor {idx}')
    
    plt.title("Investor Price Sensitivity (Figure 5 Recreated)")
    plt.xlabel("Tier (Higher = More Expensive)")
    plt.ylabel("Market Share")
    plt.legend()
    plt.grid(True)
    plt.savefig(f"{output_dir}/exp1_sensitivity.png")
    print(f"Saved {output_dir}/exp1_sensitivity.png")

if __name__ == "__main__":
    run_sensitivity_experiment()
