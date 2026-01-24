# core/market.py
import numpy as np
import core.config as cfg

class MarketEnvironment:
    """
    Simulates the exogenous exchange market.
    """
    def __init__(self):
        self.step_count = 0
        self.mid_price = 100.0
        
        # Calculate derived LOB parameter Omega
        # omega = (lambda - 1) / (lambda - 2)
        # Note: If lambda = 1.6, omega = 0.6 / -0.4 = -1.5
        # The paper formula (Eq 356/Appendix) might imply positive omega logic or specific handling.
        # Appendix A.1 text: f(x) ~ (s0/2 + x)^-lambda
        # Derivation involves integral.
        # Plan.md Formula: (s0/2) * (omega/v_tilde) * (1 - (1 - v_tilde)^(1/omega))
        # Let's trust plan.md formula directly.
        
        lam = cfg.LAMBDA_LOB
        if abs(lam - 2.0) < 1e-5:
             self.omega = None # Log case
        else:
             self.omega = (lam - 1) / (lam - 2)
             
        # Initial Spread
        self.current_s0 = self._generate_s0()
        
    def _generate_s0(self):
        s0 = np.random.normal(cfg.S0_MEAN, cfg.S0_STD)
        return np.clip(s0, cfg.S0_MIN, cfg.S0_MAX)
        
    def step(self, volatility=cfg.SIGMA_MKT_LOW):
        """
        Updates Mid Price using GBM components provided in strict formula.
        P_t = P_{t-1} * exp(...)
        """
        self.step_count += 1
        
        # Volatility per step (approx scaling)
        # Sigma_annual -> Sigma_step = Sigma * sqrt(dt_years)
        dt_years = (cfg.DT_MIN / (252 * 24 * 60)) # Approx fraction of trading year
        # Actually paper might mean "Volatility parameter" directly.
        # Plan.md: "Sigma_mkt: Annualized volatility... Low=10%"
        # GBM Formula in Plan: (mu - 0.5*sigma^2)*dt + sigma*sqrt(dt)*Z
        
        # Note: 24h market -> 252 days * 24h? Or 365? 
        # Crypto/FX is 24/7.
        # Let's use simple scaling: sigma_step = sigma_annual * sqrt(1/(365*96)) ??
        # 15 mins = 1/96 of day.
        # Day = 1/252 of year (Trading) or 1/365.
        # Let's assume 252 trading days equivalent.
        
        dt = 1.0 / (252 * 96) # Fraction of year
        sigma = volatility
        mu = cfg.MU_MKT
        
        z = np.random.normal(0, 1)
        drift = (mu - 0.5 * (sigma**2)) * dt
        diffusion = sigma * np.sqrt(dt) * z
        
        self.mid_price *= np.exp(drift + diffusion)
        self.current_s0 = self._generate_s0()
        
    def get_reference_price_curve(self, v):
        """
        Returns S_ref(v) based on the LOB formula in Plan.md.
        Represents the COST relative to mid-price (Half-Spread equivalent).
        """
        if v <= 1e-9:
            return self.current_s0 / 2.0
            
        v_tilde = v / cfg.V_MAX
        # Limit v_tilde to < 1.0 to avoid complex numbers/errors
        if v_tilde >= 0.999:
            v_tilde = 0.999
            
        base = self.current_s0 / 2.0
        
        if self.omega is None: # Lambda=2
            # logarithmic form: - (s0/2) * (1/v_tilde) * ln(1 - v_tilde)
            return -base * (1.0 / v_tilde) * np.log(1.0 - v_tilde)
        else:
            # Power law derived form
            # (s0/2) * (omega/v_tilde) * (1 - (1 - v_tilde)^(1/omega))
            
            term = (1.0 - v_tilde) ** (1.0 / self.omega)
            return base * (self.omega / v_tilde) * (1.0 - term)
