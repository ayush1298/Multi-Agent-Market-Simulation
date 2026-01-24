# core/config.py

# Simulation Constants
DT_MIN = 15
TOTAL_STEPS = 96 # 24 hours

# Market Parameters
LAMBDA_LOB = 1.6
V_MAX = 10000.0 # Total liquidity parameter

# GBM Parameters
MU_MKT = 0.0
SIGMA_MKT_LOW = 0.10 # Annualized? Paper says 10%
SIGMA_MKT_HIGH = 0.30

# Spread Parameters
S0_MEAN = 1.5e-4
S0_STD = 0.5e-4
S0_MIN = 2e-5
S0_MAX = 5e-4

# Agent Parameters
NUM_TIERS = 5
MM_ALPHA_DEFAULT = 1.5 # Sensitivity
MM_DELTA_TIER = 1e-4

# Time to realize Position Revenue (steps)
TM_DELAY = 4 # 1 hour
