# Multi-Agent Simulation for Pricing and Hedging in a Dealer Market

This repository implements an Agent-Based Simulation (ABS) of a Dealer Market, as described in the paper *"Multi-Agent Simulation for Pricing and Hedging in a Dealer Market" (Ganesh et al., 2019)*.

The simulation models the interactions between **Market Makers** (who quote prices and hedge risk) and **Investors** (who trade based on preferences) within an exogenous **Market Environment**.

## Project Structure

The project has been refactored into a modular architecture:

```
Multi-Agent-Market-Simulation/
├── core/                   # Core simulation logic
│   ├── config.py           # Global constants (Volatility, liquidity parameters)
│   ├── market.py           # Market Environment (GBM Price, LOB Reference)
│   ├── agents_mm.py        # Market Maker Agent (Tiering, Optimization)
│   ├── agents_investor.py  # Investor Agent (Trade generation)
│   └── simulation.py       # Main Simulation Loop & Reward Engine
├── utils/
│   └── math_utils.py       # Almgren-Chriss Optimization Solver (scipy)
├── experiments/            # Validation Experiments
│   ├── exp_sensitivity.py    # Figure 5: Investor Price Sensitivity
│   ├── exp_internalization.py# Figure 7: Internalization Effect
│   └── exp_hedging.py        # Figure 8/9: Hedging Costs vs Risk Aversion
├── plots/                  # Generated plots
├── run_all.py              # Master script to run all experiments
└── README.md
```

## Key Features

1.  **Exogenous Market Environment**:
    - Mid-Price evolves via Geometric Brownian Motion (GBM).
    - Reference Price Curve $S_{ref}(v)$ derived from a Limit Order Book (LOB) model.

2.  **Market Maker Agents**:
    - **Tiering**: Segments investors into tiers based on historical Yield (Revenue/Volume) using Exponential Moving Average.
    - **Pricing**: Quotes spreads $s(v,u)$ based on trade size and investor tier.
    - **Hedging**: Solves the **Almgren-Chriss** optimal execution problem to minimize Value-at-Risk ($VaR$) when liquidating inventory.

3.  **Reward Engine**:
    - Tracks **Spread Revenue** (Immediate), **Position Revenue** (Delayed), **Hedging Cost** (Spread paid), and **Risk Cost** (PnL volatility).

## Usage

### Prerequisites
- Python 3.x
- `numpy`, `scipy`, `matplotlib`

### Running Experiments
To run all verification experiments and generate plots:
```bash
python3 run_all.py
```

Results will be saved in the `plots/` directory.

## Experiments

### 1. Investor Price Sensitivity
Reproduces Figure 5 from the paper.
- **Goal**: Verify that rational investors trade less with Market Makers who assign them to worse (more expensive) pricing tiers.
- **Output**: `plots/exp1_sensitivity.png` showing Market Share vs Tier.

### 2. Internalization Effect
Reproduces Figure 7 from the paper.
- **Goal**: Demonstrate that Market Makers with higher market share (100% vs 50%) benefit from "Internalization" (organic netting of buy/sell flows), reducing their relative risk exposure.
- **Output**: `plots/exp2_internalization.png` showing $|NetPosition|/Volume$ over time.

### 3. Hedging Costs vs Risk Aversion
Reproduces Figure 8/9 from the paper.
- **Goal**: Analyze the trade-off between Hedging Costs (paying spread to liquidate) and Risk Costs (holding inventory).
- **Output**: `plots/exp3_hedging.png` showing Total Cost vs Gamma (Risk Aversion parameter).

## References
*Ganesh, S., Vadori, N., Xu, M., Zheng, H., Reddy, P., & Veloso, M. (2019). Multi-Agent Simulation for Pricing and Hedging in a Dealer Market.*
