# System Architecture

This document details the architectural design of the Multi-Agent Simulation. It describes the interplay between the exogenous market environment and the autonomous agents, the decision-making logic of the Market Makers, and the chronological execution flow of the simulation.

## 1. High-Level System Overview

The simulation operates as a closed-loop feedback system where the "Exogenous World" provides the boundary conditions (prices), and the "Agents" interact within those constraints to generate market data and rewards.

![High-Level System Overview](Architecture/High-Level%20System%20Overview.png)

### Component Breakdown

*   **Exogenous World**:
    *   **Market Environment**: The source of truth for the underlying asset's fundamental value. It evolves the Mid-Price using a Geometric Brownian Motion (GBM) stochastic process, independent of agent actions.
    *   **LOB Model**: A theoretical Limit Order Book model that provides the "Reference Price Curve" ($S_{ref}$), dictating the cost of immediate liquidity for any given volume. This serves as a benchmark for hedging costs.

*   **Simulation Engine**:
    *   Acts as the comprehensive orchestrator. It advances time ($t \rightarrow t+1$), triggers agent actions, resolves trade matching, and logs all events to the database.
    *   **Logging**: Captures high-frequency data (every trade) and state snapshots (positions, prices) for post-run analysis.

*   **Agents**:
    *   **Investors**: The "Demand Side". They generate trade requests based on internal preferences (frequency, size) and market conditions. They are the primary source of volume and revenue for Market Makers.
    *   **Market Makers (MM)**: The "Supply Side". They provide liquidity by quoting buy/sell prices. They also trade with each other (Competitor MMs) to manage risk via hedging.

*   **Reward System**:
    *   A critical feedback mechanism that calculates the utility for each Market Maker.
    *   **Net Position**: Tracks the inventory ($Z_t$) held by the MM. High inventory carries "Inventory Risk".
    *   **Revenue & Costs**: Aggregates Spread Revenue (profit from investors), Hedging Costs (inter-dealer spread paid), and Risk Costs (penalty for holding volatile inventory).

---

## 2. Market Maker Decision Engine

The Market Maker is the most complex agent in the system. Its behavior is governed by a sequential decision pipeline involved in every time step: **Tiering**, **Pricing**, and **Hedging**.

![Market Maker Decision Engine](Architecture/Market%20Maker%20Decision%20Engine%20Flowchart.png)

### Logic Flow

1.  **Client Tiering (Classification)**:
    *   *Input*: Historical trading data (Volume, Revenue) for each investor.
    *   *Process*: The MM calculates the **Weighted Yield** (Profitability) of each investor using an Exponential Moving Average. Investors are then ranked and segmented into discrete "Tiers" ($k=0, 1, ...$).
    *   *Output*: A Tier assignment for every investor, determining the baseline spread they will be quoted.

2.  **Pricing Logic (Quoting)**:
    *   *Trigger*: An Investor requests a quote for a specific volume and direction.
    *   *Base Spread*: Derived from the Investor's Tier. Better tiers get tighter spreads.
    *   *Inventory Skew*: The MM adjusts the price based on their current Net Position ($Z_t$) and Risk Aversion ($\gamma$).
        *   *Long Position*: Skews price down to encourage selling.
        *   *Short Position*: Skews price up to encourage buying.
    *   *Execution*: If the Investor accepts the quote, the trade is executed, and the MM's Net Position is updated immediately.

3.  **Hedging Logic (Risk Management)**:
    *   *Trigger*: Occurs after Client Trading is complete for the step.
    *   *Optimization*: The MM solves the **Almgren-Chriss** optimal execution problem. It balances the "Trading Cost" (impact of liquidating quickly) against the "Risk Cost" (volatility of holding inventory).
    *   *Decision*: The solver outputs an optimal trajectory. The MM executes the first chunk of this trajectory immediately.
    *   *Inter-Dealer Trade*: The hedge trade is executed against a Competitor Market Maker, acting as a Taker (paying the spread).

---

## 3. Detailed Interaction Flow

This sequence diagram illustrates the precise chronological order of operations within a single Simulation Step ($t$).

![Detailed Interaction Flow](Architecture/Detailed%20Interaction%20Flow.png)

### Step-by-Step Execution

1.  **Market Update (Start of Step)**:
    *   The Simulation Engine calls `env.step()`.
    *   The Mid-Price updates ($P_t \rightarrow P_{t+1}$). This new price is the anchor for all subsequent quoting.

2.  **Tiering Update**:
    *   Before any trading occurs, Market Makers update their internal classification of investors. This ensures that the day's quotes reflect the most recent yield performance.

3.  **Investor Trading Loop**:
    *   The simulation iterates through every Investor.
    *   **Request**: An investor may initiate a Buy or Sell request.
    *   **Quoting**: All Market Makers calculate their individualized quotes (Tier Spread + Inventory Skew) and send them to the Investor.
    *   **Selection**: The Investor selects the "Best Price" (Lowest Offer / Highest Bid).
    *   **Execution**: The trade is booked. The winning MM receives **Spread Revenue** and updates their **Net Position**.

4.  **Hedging Loop**:
    *   After servicing clients, Market Makers assess their risk.
    *   **Calculate**: They run the optimizer to determine if his inventory exceeds their risk tolerance.
    *   **Execute**: If a hedge is needed, they request quotes from *other* Market Makers. The best quote is taken, and the MM pays the **Hedging Cost**.

5.  **Rewards & Persistence (End of Step)**:
    *   **Delayed Revenue**: The system computes the "Position Revenue" (value change of inventory held over time).
    *   **Risk Cost**: The "Value at Risk" penalty is assessed based on the volatility of the portfolio functionality.
    *   **Logging**: All positions, trades, prices, and rewards are saved to the history log for this time step.
