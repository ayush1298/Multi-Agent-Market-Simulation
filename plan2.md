# 📘 IMPLEMENTATION SPECIFICATION

## Multi-Agent Simulation for Pricing and Hedging in a Dealer Market

> **Purpose**
> This document defines an **unambiguous, end-to-end specification** for implementing the dealer-market simulation described in *Ganesh et al. (2019)*.
> It is designed to be **directly consumable by an LLM** to generate correct code, reproduce experiments, and match plots/tables from the paper.

---

## 1. GLOBAL SIMULATION SETUP

### 1.1 Time and Horizon

* **Time step (`Δt`)**: 15 minutes
* **Steps per day**: 96
* **Typical run lengths**:

  * Price sensitivity experiments: 96 steps (1 day)
  * Internalization experiments: 250–300 steps
  * Hedging experiments: 500 steps

---

### 1.2 Agents

* **Market Makers (`M`)**: 2
* **Investors (`N`)**: 10
* **Tiers (`K`)**: typically 5 (indexed `0 … K−1`, where `0` is best)

---

### 1.3 Asset

* Single tradable asset
* All prices expressed **relative to mid-price `Pₜ`**

---

## 2. EXOGENOUS MARKET PROCESS

### 2.1 Mid-Price Dynamics

Mid-price follows **Geometric Brownian Motion**:

[
P_{t+1} = P_t \cdot \exp\left((\mu - \frac{1}{2}\sigma^2)\Delta t + \sigma \sqrt{\Delta t} Z_t\right)
]

* ( Z_t \sim \mathcal{N}(0,1) )
* **Volatility (`σ`)**:

  * Low-vol: 10% annualized
  * High-vol: 30% annualized
* Drift `μ = 0`

> ⚠️ **Important**
> Many mismatches happen if:
>
> * arithmetic Brownian motion is used instead
> * volatility is applied per step instead of annualized

---

### 2.2 Reference Exchange Spread (`s₀`)

At each time step:

* Sample:
  [
  s_0 \sim \mathcal{N}(0.015%, 0.005%)
  ]
* Clamp:
  [
  0.002% \le s_0 \le 0.05%
  ]

---

### 2.3 Reference Price Curve `S_ref(v)`

Let:

* ( v_{max} ): total exchange liquidity
* ( v_e = \frac{v}{v_{max}} \in [0,1) )
* ( \lambda = 1.6 )
* ( \omega = \frac{\lambda - 1}{\lambda - 2} )

Then:

[
S_{ref}(v) =
\frac{s_0}{2} \cdot \omega \cdot v_e \cdot \left(1 - (1 - v_e)^{1/\omega}\right)
]

* Used symmetrically for buy/sell
* Defined **relative to mid-price**

---

## 3. INVESTOR AGENTS

### 3.1 Trade Arrival

At each time step, investor `j` trades with probability:

[
\mathbb{P}(\text{trade}) = p^{trade}_j
]

---

### 3.2 Trade Size

Trade size is **log-normally distributed**:

[
v_j \sim \text{LogNormal}(\mu^{trade}_j, \sigma^{trade}_j)
]

---

### 3.3 Trade Direction

* Buy with probability `p_buy_j`
* Sell otherwise

---

### 3.4 Sophisticated Investors (Optional)

* Parameter: ( q_j \in [0.5, 1) )
* With probability `q_j`, investor sees sign of ( P_{t+t_m} - P_t )
* Adjusts buy/sell accordingly

---

### 3.5 Investor Action

* Observes prices from all market makers
* Chooses **minimum quoted price**
* Executes immediately

---

### 3.6 Investor Reward

[
R^{inv}*t = - s*{i,t}(v, u_{i,j,t}) \cdot v
]

---

## 4. MARKET MAKER AGENTS

### 4.1 State

Each market maker `i` observes:

* Trade history `{ṽ_{i,j,t'}}`
* Net position:
  [
  z_{i,t} = \sum_{t' < t} ṽ_{i,t'}
  ]
* Competitor prices
* `S_ref(v)`
* Mid-price `Pₜ`

---

## 5. TIERING POLICY

### 5.1 Trade Revenue

For a trade of size `v`:

[
\text{Revenue} = s_{i,t}(v, u) \cdot v + (P_{t+t_m} - P_t) \cdot v
]

---

### 5.2 Yield

[
\text{Yield} = \frac{\text{Revenue}}{|v|}
]

---

### 5.3 Exponential Moving Average

[
\bar{y}*{j,t} = (1-\beta)\bar{y}*{j,t-1} + \beta \cdot \text{Yield}
]

---

### 5.4 Revenue Rate

[
\psi_{j,t} = \bar{y}_{j,t} \cdot \text{AvgVolume}_j
]

---

### 5.5 Tier Assignment

* Sort participants by `ψ`
* Assign quantiles → tiers
* Best quantile → tier 0

---

## 6. PRICING POLICY

For market maker `i`:

[
s_i(v, u) = S_{ref}(0) \cdot \left(\frac{S_{ref}(v)}{S_{ref}(0)}\right)^{\alpha_i} + \delta_{tier} \cdot u
]

* `α_i`: volume sensitivity
* `δ_tier`: linear tier penalty
* `S_ref(0) = s₀ / 2`

---

## 7. HEDGING POLICY (CORE SOURCE OF MISMATCHES)

### 7.1 Hedge Price

[
c(v) = \min_{j \ne i} s_{j,t}(v, u_{j,i,t})
]

---

### 7.2 Hedge Horizon

* `N_max`: number of steps (e.g., 5 hours = 20 steps)

---

### 7.3 Cost Function

Let:

* `x_k`: fraction hedged at step `k`
* `y_k`: remaining fraction

[
C = \sum_{k=0}^{N_{max}-1} x_k c(z_{i,t} x_k)

* \sigma \sum_{k=0}^{N_{max}-1} y_k Z_k
  ]

---

### 7.4 Value-at-Risk Objective

[
\text{VaR}_p = \mathbb{E}[C] + \gamma \sqrt{\text{Var}(C)}
]

* `γ`: **risk aversion**
* Larger `γ` → faster hedging

---

### 7.5 Optimal Policy

* Solve for `{x_k}` minimizing VaR
* Hedge immediately:
  [
  v^{hedge}*t = z*{i,t} \cdot x_0
  ]

---

## 8. MARKET MAKER REWARD

At time `t`:

### 8.1 Spread Revenue

[
R^{spread}_t = \sum s_i(v,u)\cdot v
]

---

### 8.2 Position Revenue (Delayed)

[
R^{pos}*{t+t_m} = (P*{t+t_m} - P_t)\cdot v
]

---

### 8.3 Hedging Cost

[
R^{hedge}_t = - c(v^{hedge}) \cdot v^{hedge}
]

---

### 8.4 Risk Cost

[
R^{risk}*t = \min(z*{i,t}(P_t - P_{t-1}), 0)
]

---

## 9. EXPERIMENTS TO REPRODUCE

---

### 9.1 Investor Price Sensitivity

* Fix tiers for one MM
* Vary tier of a single investor
* Measure:
  [
  \text{Market Share}_{i,j}
  ]

Plot:

* Market share vs tier
* 300 Monte Carlo runs

---

### 9.2 Internalization Effect

Metric:
[
\frac{|z_t|}{\sum_{t'=0}^{t} v_{t'}}
]

Compare:

* 50% market share
* 100% market share

---

### 9.3 Risk Aversion Study

* Fix `N_max = 5 hours`
* Sweep `γ ∈ {0, 0.05, 0.25, 0.5, 1, 5, ∞}`
* Plot cumulative:

  * hedging cost
  * risk cost

---

## 10. COMMON FAILURE POINTS (READ THIS)

⚠️ If your plots do not match:

1. Wrong `S_ref(v)` formula
2. Wrong GBM scaling
3. Hedging done greedily instead of VaR-optimal
4. Tier updates applied every trade instead of every step
5. Risk cost implemented as absolute instead of asymmetric
6. Using same RNG stream across agents

---

## 11. OUTPUT REQUIREMENTS

Your implementation **must produce**:

* Pricing curves (Figure 3)
* Net position vs time (Figure 4)
* Investor price sensitivity plots (Figure 5,6)
* Internalization curves (Figure 7)
* Risk aversion cost curves (Figure 8,9)

---