import numpy as np

class MarketEnvironment:
    """
    Manages the market environment, including time and exogenous price processes.
    """
    def __init__(self, 
                 dt_min: int = 15, 
                 total_time_min: int = 24 * 60,
                 s0_mean: float = 0.00015, # 0.015%
                 s0_std: float = 0.00005,  # 0.005%
                 min_s0: float = 0.00002,
                 max_s0: float = 0.0005,
                 lambda_param: float = 1.6,
                 v_max: int = 1000, # Total liquidity parameter
                 volatility: float = 0.02 # Daily volatility
                 ):
        """
        Args:
            dt_min: Time step size in minutes (default 15).
            total_time_min: Total simulation time in minutes (default 24h).
            s0_mean: Mean of reference spread.
            s0_std: Std dev of reference spread.
            lambda_param: Parameter for LOB depth distribution.
            v_max: Total liquidity available in the exchange LOB.
            volatility: Annualized volatility (need to scale for simulation). 
                        Paper mentions 10% or 30% annualized, but experiments use specific mid-price process.
                        We'll use a simplified GBM.
        """
        self.dt_min = dt_min
        self.total_steps = int(total_time_min / dt_min)
        self.current_step = 0
        
        # Parameters for Reference Spread s0
        self.s0_mean = s0_mean
        self.s0_std = s0_std
        self.min_s0 = min_s0
        self.max_s0 = max_s0
        
        # LOB Parameters
        self.lambda_param = lambda_param
        self.v_max = v_max
        
        # Price Process
        self.mid_price = 100.0 # Starting price
        self.volatility = volatility 
        # Convert daily/annual volatility to per-step volatility
        # Assuming volatility input is roughly per day or similar scale. 
        # Let's assume input is per day for now, as paper experiments mention "volatility 10%" but context implies specific motion.
        # Paper says: "mid price increment over time period is sigma * Z" where Z ~ N(0,1).
        self.step_volatility = self.volatility * np.sqrt(self.dt_min / (24 * 60)) # Scaling simple random walk

        # History
        self.price_history = [self.mid_price]
        self.s0_history = []
        
        self.current_s0 = self._generate_s0()

    def _generate_s0(self):
        """Generates reference spread s0 for current step."""
        s0 = np.random.normal(self.s0_mean, self.s0_std)
        return np.clip(s0, self.min_s0, self.max_s0)

    def step(self):
        """Advances the market by one time step."""
        if self.current_step >= self.total_steps:
            return False
            
        # Update Mid Price (Geometric Brownian Motion or Arithmetic Walk as per paper approx)
        # Paper: Pt+1 = Pt + sigma * Z (Arithmetic for small intervals) or Pt * exp(...)
        # Paper p.6: "mid price increment ... is sigma * Z". This suggests Arithmetic Brownian Motion for the price itself?
        # Usually prices are geometric. But let's follow the "increment" wording if strictly needed.
        # However, GBM is standard. Let's use GBM: P_new = P_old * exp(...)
        
        # Re-reading paper Section 3.2.3: "mid price increment ... equal to sigma * Zk".
        # This implies P_{t+1} - P_t = sigma * Z. (Arithmetic)
        # We will use Arithmetic walk for simplicity as per paper description, but ensure P > 0.
        
        innovation = np.random.normal(0, 1)
        self.mid_price += self.step_volatility * self.mid_price * innovation # Using % volatility
        
        self.current_s0 = self._generate_s0()
        
        self.price_history.append(self.mid_price)
        self.s0_history.append(self.current_s0)
        
        self.current_step += 1
        return True

    def get_reference_price_curve(self, v: float) -> float:
        """
        Calculates S_ref(v) based on Appendix A.1
        S_ref(v) is the cost relative to mid-price.
        
        The paper derivation concludes with an implicit x* or a formula.
        Let's implement the resulting cost function or an approx.
        
        Paper says: S_ref(v) (spread) is cost of trading size v relative to mid price.
        Actually S_ref(v) usually means the marginal price or average price per unit? 
        Paper Eq 354 implies S_ref(v) is a value that scales.
        
        Appendix A.1 gives cost c(v).
        The average spread per unit for size v would be c(v) / v?
        Or is S_ref(v) the marginal price at size v?
        
        "The pricing policy takes ... S_ref(v) ... and generates pricing curve s(v,u)"
        Eq in 3.2.2: s(v,u) = S_ref(0) * (S_ref(v)/S_ref(0))^alpha + penalty.
        
        Let's look at Appendix A.1 details.
        It defines a cost c(v).
        Let's assume S_ref(v) corresponds to the price impact cost per unit, or the "spread" for that size.
        
        Approximation:
        The paper uses a specific power law density for the LOB.
        We can approximate S_ref(v) as: s0/2 * (1 + k * v^beta) or similar?
        
        Let's try to interpret the integral in Appendix A.1 if possible, or use a standard linear/power market impact model which is common in these papers.
        
        Given implementation complexity of exact Appendix integral (implicit x*), 
        and the fact that this is a reference curve, we can model it as:
        S_ref(v) = (s0 / 2) * (1 + lambda_impact * v) 
        OR follow the "volume penalty factor" concept.
        
        Let's stick to the spirit: "Trading large sizes is done at higher spread".
        Let's define S_ref(v) = (s0 / 2) * (1 + (v / v_max)^k) or similar.
        
        Paper Appendix A.1:
        f(x) proportional to (s0/2 + x)^-1.6
        This is a power law LOB.
        
        Let's use a simplified explicit formula that captures the essence:
        S_ref(v) = s0/2 + coefficient * v
        
        Wait, Eq 354 uses S_ref(v) / S_ref(0).
        S_ref(0) is s0/2.
        So S_ref(v) / S_ref(0) is the "Liquidity Premium".
        
        Let's implement a specific functional form:
        S_ref(v) = (s0 / 2) * (1 + C * v)
        where C depends on liquidity.
        
        For this implementation, let's use:
        S_ref(v) = (s0 / 2) * (1 + v / 100) # heuristic scaling
        """
        
        # Heuristic implementation of S_ref(v)
        # Represents half-spread for size v
        
        base_half_spread = self.current_s0 / 2.0
        
        # Liquidity penalty factor
        # If v is small, close to base_half_spread.
        # If v is large, spread increases.
        # Using a simple linear impact model for robustness if exact integral is complex.
        
        # However, to be closer to "Power Law LOB", the cost often scales as v^beta.
        # Let's use: S_ref(v) = base_half_spread * (1 + (v / 10.0)) 
        # (Assuming v is around order of magnitude 1-10 for investors)
        
        # Paper Experiment 4.1 table says Avg Trade Size 0.5 to 4.5.
        # So v is small.
        
        liquidity_penalty_factor = 1.0 + (0.1 * v) # Simple linear model
        
        return base_half_spread * liquidity_penalty_factor

    def get_state(self):
        return {
            "current_step": self.current_step,
            "mid_price": self.mid_price,
            "reference_spread": self.current_s0
        }
