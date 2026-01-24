Comprehensive Implementation Plan: Multi-Agent Dealer Market Simulator

Reference Paper: "Multi-Agent Simulation for Pricing and Hedging in a Dealer Market" (Ganesh et al., 2019)

This document details the architecture, mathematical models, and algorithms required to replicate the dealer market simulation. It is designed to be a direct instruction manual for a coding agent.

1. Global Simulation Constants & Assumptions

Time & Scale

Time Step ($\Delta t$): 15 minutes.

Total Duration: 24 hours (96 steps) for standard experiments.

Asset: Single underlying asset.

Market Structure: $M$ Market Makers (MM), $N$ Investors.

Assumption: Dealer market activity does not impact the external Exchange prices.

Parameters to Config

N_investors: 10 (default)

M_market_makers: 2 (default)

K_tiers: 5 (default)

t_m: Time horizon for position revenue realization (e.g., 4 steps / 1 hour).

v_max: Total market liquidity parameter (e.g., 10,000).

2. Phase 1: Exogenous Market Environment (The Exchange)

The Environment acts as the source of truth for the "Reference Price" which drives MM pricing.

2.1 Reference Mid-Price ($P_t$)

Model: Geometric Brownian Motion (GBM).

Dynamics:


$$P_t = P_{t-1} \cdot \exp\left( (\mu - 0.5\sigma_{mkt}^2)\Delta t + \sigma_{mkt}\sqrt{\Delta t} Z \right)$$

Variables:

$Z \sim \mathcal{N}(0, 1)$ (Standard Normal).

$\mu$: Drift (assume $0$ for pure volatility tests).

$\sigma_{mkt}$: Annualized volatility.

Low Volatility exp: 10%

High Volatility exp: 30%

2.2 Reference Spread ($s_{0,t}$)

The spread between Best Bid and Best Ask on the external Limit Order Book (LOB).

Distribution: Sample $s_{0,t}$ at every step from a Normal Distribution.


$$s_{0,t} \sim \mathcal{N}(\mu_{spread}=1.5 \times 10^{-4}, \sigma_{spread}=0.5 \times 10^{-4})$$

Constraints: Clip $s_{0,t}$ to $[2 \times 10^{-5}, 5 \times 10^{-4}]$.

Note: This represents the "tightest" possible spread available in the market.

2.3 Reference Price Curve ($S_{ref,t}(v)$)

This function defines the cost of trading volume $v$ on the external exchange. It is derived from LOB assumptions in Appendix A.1.

Constants:

$\lambda = 1.6$ (LOB shape parameter).

$\omega = \frac{\lambda - 1}{\lambda - 2}$ (Derived parameter).

$v_{max}$: Maximum available liquidity (must be > max investor trade).

$\tilde{v} = v / v_{max}$ (Normalized volume).

Formula:
If $\lambda \neq 2$:


$$S_{ref}(v) = \frac{s_0}{2} \frac{\omega}{\tilde{v}} \left( 1 - (1 - \tilde{v})^{1/\omega} \right)$$


(Note: If $\lambda=2$, use logarithmic form: $-\frac{s_0}{2}\frac{1}{\tilde{v}}\ln(1-\tilde{v})$)

Usage: This curve serves as the baseline for MM pricing. MMs cannot price lower than $S_{ref}(v)$ without losing money against the exchange arbitrage.

3. Phase 2: Investor Agent Logic

Investors are price-takers. They generate trade requests and execute with the cheapest MM.

3.1 Trade Generation (Per Investor $j$)

At each time step $t$:

Arrival: Trade occurs if $rand() < p_j^{trade}$.

Size ($v_{trade}$): Sample from Log-Normal: $\ln(v) \sim \mathcal{N}(\mu_j^{size}, \sigma_j^{size})$.

Direction ($d$):

Standard Investor: $P(Buy) = 0.5$.

Sophisticated Investor (Oracle):

Has "skill" probability $q_j \in [0.5, 1.0)$.

Oracle looks ahead at $P_{t+t_m} - P_t$.

If $rand() < q_j$: Sets direction to profit from future move.

Else: Random direction.

3.2 Execution Logic

Solicit Quotes: Investor asks all $M$ MMs for a quote on size $v_{trade}$.

Quote from MM $i$: $price_{i} = s_{i,t}(v_{trade}, \text{tier}_{i,j})$.

Selection:


$$i^* = \arg\min_{i} \{ s_{i,t}(v_{trade}, \text{tier}_{i,j}) \}$$

Execute: Trade $v_{trade}$ with MM $i^*$.

4. Phase 3: Market Maker Agent Logic

The MM agent has three distinct sub-policies.

4.1 State Variables (Per MM $i$)

NetPosition ($z_{i,t}$): Current accumulated inventory.

Cash: Accumulated cash (optional, mostly for PnL tracking).

YieldHistory: Dictionary mapping Investor ID $\to$ List of past yields.

4.2 Tiering Policy (Client Classification)

Executed at the start of step $t$ before providing quotes.

Calculate Metric: For each investor $j$, calculate Average Yield ($\psi_{j,t}$).

Yield per trade: $Y_{trade} = \frac{\text{Revenue from trade}}{\text{Volume of trade}}$

Update: $\psi_{j,t} = \beta \cdot \psi_{j,t-1} + (1-\beta) \cdot Y_{trade}$ (Exponential Moving Average).

Alternative Metric: Revenue Rate = $\psi_{j,t} \times \text{AvgVolume}_j$.

Assign Tiers:

Sort all active investors by $\psi_{j,t}$ descending.

Partition into $K$ quantiles.

Tier 0 = Best (Highest Yield), Tier $K-1$ = Worst.

4.3 Pricing Policy (Quote Streaming)

Determines the spread $s(v, u)$ charged to an investor in tier $u$ for volume $v$.

Formula:


$$s(v, u) = S_{ref}(0) \left( \frac{S_{ref}(v)}{S_{ref}(0)} \right)^\alpha + \delta_{tier} \cdot u$$

Components:

$S_{ref}(0) = s_{0,t} / 2$: The "base" half-spread cost.

$\frac{S_{ref}(v)}{S_{ref}(0)}$: The exchange's volume penalty factor.

$\alpha$: MM's volume sensitivity parameter (e.g., 1.1 to 1.7). Higher $\alpha$ = steeper price increase for large trades.

$\delta_{tier}$: Fixed penalty per tier level (e.g., $1 \times 10^{-4}$).

4.4 Hedging Policy (Almgren-Chriss Optimization)

Executed after client trades are processed, if $z_{i,t} \neq 0$.

Objective: Minimize $VaR_p = E[C] + \gamma \sqrt{Var(C)}$.

Parameters:

$N_{max}$: Max time steps to liquidate (e.g., 5 hours = 20 steps).

$\gamma$: Risk aversion coefficient (0.0 to 10.0+).

$\sigma$: Estimated volatility of mid-price (per step).

Schedule Variables: Sequence $x_0, x_1, ..., x_{N-1}$ representing fraction of initial position $z_{i,t}$ to hedge at each step.

constraint: $\sum x_k = 1$.

Remaining position sequence $y_k$: $y_k = 1 - \sum_{j=0}^k x_j$.

Cost Functions:

$E[C] = \sum_{k=0}^{N_{max}-1} x_k \cdot c_{hedge}(z_{i,t} \cdot x_k)$

Where $c_{hedge}(v)$ is the best price available from competitor MMs.

$Var(C) = \sigma^2 \sum_{k=0}^{N_{max}-1} y_k^2$

Optimization Step:

Use scipy.optimize.minimize to find optimal vector $\vec{x}$.

Action: Execute immediate hedge trade of size $v_{hedge} = z_{i,t} \cdot x_0$.

Counterparty: Execute with the competitor MM offering lowest cost $c_{hedge}(v_{hedge})$.

5. Phase 4: Reward Engine

Rewards are calculated at the end of every step $t$.

Component 1: Spread Revenue ($R_{spread}$)
Immediate profit from charging a spread.


$$R_{spread} = \sum_{j \in \text{Clients}} v_{j,t} \cdot s_{i,t}(v_{j,t}, u_{i,j})$$

Component 2: Position Revenue ($R_{pos}$)
Profit/Loss due to price movement, realized after delay $t_m$.

Tracks a queue of trades made $t_m$ steps ago.


$$R_{pos} = \sum_{trade \in \text{Time } t-t_m} v_{trade} \cdot (P_{t} - P_{t-t_m})$$


(Note: Direction matters. If MM bought, profit if $P_t > P_{t-t_m}$.)

Component 3: Hedging Cost ($C_{hedge}$)
Cost paid to competitors to reduce inventory.


$$C_{hedge} = -1 \cdot (v_{hedge} \cdot \text{CompetitorSpread})$$

Component 4: Risk Cost ($C_{risk}$)
Penalty for holding inventory against adverse price moves.


$$C_{risk} = \min( z_{i,t} \cdot (P_t - P_{t-1}), 0 )$$


(Only penalizes losses; does not reward gains. Gains are captured in $R_{pos}$.)

Total Reward:


$$R_{total} = R_{spread} + R_{pos} + C_{hedge} + C_{risk}$$

6. Implementation Notes for Coding Agents

Modular Design:

Create class MarketEnvironment to encapsulate $P_t$ and $S_{ref}$ logic.

Create class MarketMaker with methods get_quote(v, investor_id), update_tiering(), and calculate_hedge().

Optimization Trick:

The Almgren-Chriss optimization runs every step. Since $c_{hedge}(v)$ (competitor pricing) might be complex/non-linear, numerical optimization is safer than analytic solutions.

For speed, assume $c_{hedge}(v)$ is linear locally or pre-calculate a lookup table.

Data Structures:

TradeLog: List of dicts {'time', 'investor_id', 'mm_id', 'volume', 'price', 'direction'}.

PositionQueue: For calculating delayed Position Revenue.

Verification:

Zero-Check: If $N_{investors}=0$, $P_t$ should still evolve as GBM.

Arbitrage-Check: Ensure $s_{MM}(v) \ge S_{ref}(v)$. If MM prices below exchange reference, they effectively lose money instantly (in real life) or fail to account for costs.

7. Validation Experiments to Run

Price Sensitivity:

Fix MM policies.

Manually force Investor X into Tier 0, then Tier 1, ... Tier K.

Record MM's market share of Investor X at each tier.

Internalization:

Run simulation with MM1 having standard pricing and MM2 having infinite pricing (MM1 gets 100% share).

Run with MM1 and MM2 identical (50% share).

Compare mean(abs(NetPosition) / TotalVolume) for MM1 in both cases.

Risk Aversion ($\gamma$) Sweep:

Run full simulations with $\gamma \in \{0.0, 0.1, 1.0, 10.0\}$.

Plot Total Reward vs $\gamma$.

Expectation: Intermediate $\gamma$ is optimal in high volatility; Low $\gamma$ optimal in low volatility.