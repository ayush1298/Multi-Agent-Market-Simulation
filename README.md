# Multi-Agent Simulation for Pricing and Hedging in a Dealer Market

A Python-based Agent-Based Simulation (ABS) reproducing the findings of the paper *A Multi-Agent Simulation for Pricing and Heding in a Dealer Market*.

**[Read Detailed Implementation Guide](IMPLEMENTATION_DETAILS.md)**

## Quick Start
1.  **Install Dependencies**:
    ```bash
    pip install numpy scipy matplotlib
    ```
2.  **Run All Experiments**:
    ```bash
    python3 run_all.py
    ```
    *Plots will be generated in `plots/`.*

## Project Structure
*   `core/`: Simulation engine and Agent definitions (*MarketMaker, Investor*).
*   `experiments/`: Scripts reproducing specific paper figures.
*   `utils/`: Mathematical solvers (Almgren-Chriss optimization).
*   `run_all.py`: Orchestrator script.

## Experiments Overview

| Experiment | Goal | Simulation | Output |
| :--- | :--- | :--- | :--- |
| **1. Price Sensitivity** | Verify investors trade less with pricier tiers. | `experiments/exp_sensitivity.py` | `plots/exp1_sensitivity.png` |
| **2. Internalization** | Show netting benefits of high market share. | `experiments/exp_internalization.py` | `plots/exp2_internalization.png` |
| **3. Hedging Costs** | Optimize risk aversion $\gamma$ vs. volatility. | `experiments/exp_hedging.py` | `plots/exp3_hedging_*.png` |

## Documentation
For a step-by-step explanation of the internal logic (Pricing, Tiering, Hedging, and Simulation Loop), please refer to **[IMPLEMENTATION_DETAILS.md](IMPLEMENTATION_DETAILS.md)**.

## References
*Ganesh, S., Vadori, N., Xu, M., Zheng, H., Reddy, P., & Veloso, M. (2019). Multi-Agent Simulation for Pricing and Hedging in a Dealer Market.*
