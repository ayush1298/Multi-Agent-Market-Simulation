# Implementation Details

This document provides a detailed step-by-step breakdown of the logic implemented in each core component of the system.

## 1. Market Environment (`core/market.py`)

The exogenous market environment simulates the underlying asset price and liquidity constraints.

*   **Mid-Price Evolution**: Modeled as a Geometric Brownian Motion (GBM).
    *   $P_{t} = P_{t-1} \cdot e^{(\mu - 0.5\sigma^2)\Delta t + \sigma \sqrt{\Delta t} Z}$
    *   $\sigma$ represents market volatility (configurable for experiments).
*   **Reference Price Curve ($S_{ref}$)**: Derived from a Limit Order Book (LOB) density function $\rho(x) = \Lambda / x^\Omega$.
    *   Calculates the market impact cost of transacting volume $v$ immediately.
    *   Used as the benchmark for "Competitor Cost" in the hedging module.
    *   Implements the formulas from *Appendix A.1* (Logarithmic cost for $\Omega=2$, Power Law for $\Omega \neq 2$).

## 2. Market Maker Agent (`core/agents_mm.py`)

The Market Maker (MM) is the central agent, optimizing quotes and managing inventory.

### A. Tiering Logic
*   **Goal**: Segment investors based on their profitability.
*   **Metric**: Weighted Yield = $\text{EMA}(\frac{\text{Revenue}}{\text{Volume}})$.
*   **Process**:
    *   Updates yield history after every trade.
    *   Sorts investors by yield.
    *   Assigns Tier $k \in \{0, ..., K-1\}$ (0 is best/cheapest).

### B. Pricing Logic
*   **Quote**: $P_{quote} = P_{mid} + S_{spread} + S_{skew}$.
*   **Spread ($S_{spread}$)**: Determined by the Investor's Tier.
    *   $S(v) = \alpha + \beta_{tier} \cdot v$
    *   Base spread $\alpha$ increases with Tier Index (Worse Tier = Higher Spread).
*   **Inventory Skew ($S_{skew}$)**: Adjusts price to encourage inventory mean-reversion.
    *   $S_{skew} = -\gamma \sigma^2 (Z_t)$
    *   If MM is Long ($Z>0$): Quotes lower to Sell.
    *   If MM is Short ($Z<0$): Quotes higher to Buy.

### C. Hedging Logic (Almgren-Chriss Optimization)
*   **Goal**: Determine optimal quantity $v_{hedge}$ to liquidate over horizon $T$ to minimize Trading Cost + Risk Cost.
*   **Solver** (`utils/math_utils.py`):
    *   Minimizes Objective: $E[\text{Cost}] + \gamma \cdot \text{Var}[\text{Cost}]$.
    *   Uses `scipy.optimize.minimize` to find the trading trajectory.
    *   The first step of the trajectory is executed as the hedge trade.

## 3. Investor Agent (`core/agents_investor.py`)

Investors represent diverse order flows.

*   **Heterogeneity**: Each investor has a different trade frequency ($p_{trade}$) and average trade size ($\mu_{size}$).
*   **Decision Loop**:
    1.  **Request**: Randomly decides to trade (Bernoulli process).
    2.  **Quote Request**: Asks all MMs for a quote (Buy/Sell).
    3.  **Selection**: Selects the MM with the **Best Price**.
    4.  **Execution**: Trades with the winner.

## 4. Simulation Engine (`core/simulation.py`)

Orchestrates the interactions over discrete time steps.

### Step-by-Step Cycle
1.  **Market Update**: Evolves $P_{mid}$.
2.  **Tiering Update**: MMs re-rank investors.
3.  **Investor Trading**:
    *   Investors request quotes.
    *   Trades are executed.
    *   MM positions are updated ($Z_{t} \leftarrow Z_{t-1} \pm v$).
    *   **Revenue Recording**: Immediate Spread Revenue captured.
4.  **Hedging**:
    *   MMs calculate hedge needs.
    *   Execute trades against *other* MMs (Inter-dealer market).
    *   Costs recorded.
5.  **Data Logging**:
    *   Positions logged *after* all trades to ensure accuracy.
    *   Transactions pushed to `trade_queue` for delayed analysis.

### Reward Calculation
*   **Reward** = Spread Revenue (Immediate) + Position Revenue (Delayed) - Hedging Cost - Risk Cost.
*   **Delayed Revenue**: Captures the value of holding inventory over time interval $T_m$.
*   **Risk Cost**: Penalizes volatility of returns over the interval.

## 5. Experiment Implementations

### Experiment 1: Investor Price Sensitivity
*   **Objective**: Show that investors prefer better tiers.
*   **Method**:
    *   Fixes one MM at "Tier 2" (Baseline).
    *   Varies Target MM's tier from 0 (Best) to 4 (Worst).
    *   Measures Market Share captured.
*   **Key Detail**: Uses **Inventory Skew** to create pricing dynamics even when spreads are static.

### Experiment 2: Internalization Effect
*   **Objective**: Show that higher market share reduces relative risk.
*   **Method**:
    *   Scenario A: 50% Share (Two identical MMs).
    *   Scenario B: 100% Share (Target MM wins all trades).
    *   Metric: $\frac{|NetPosition|}{CumulativeVolume}$.
*   **Key Detail**: Disables Hedging and Tiering to isolate the "Natural Internalization" effect.

### Experiment 3: Hedging Costs
*   **Objective**: Optimal Risk Aversion depends on Volatility.
*   **Method**:
    *   Low Volatility ($\sigma=0.1$) vs High Volatility ($\sigma=0.3$).
    *   Varies $\gamma$ (Risk Aversion).
    *   Metric: Cumulative (Hedging Cost + Risk Cost).
*   **Key Detail**: Defines Cost as negative Reward. Shows that in High Volatility, *some* hedging (moderate $\gamma$) is better than none.
