# utils/math_utils.py
import numpy as np
from scipy.optimize import minimize

def solve_almgren_chriss(initial_position_z, 
                         n_steps, 
                         gamma, 
                         sigma, 
                         cost_function_callable):
    """
    Solves for the optimal hedging schedule X = [x0, x1, ..., x_{N-1}].
    Where x_k is the fraction of *initial_position* to trade at step k.
    
    Args:
        initial_position_z: Total size to liquidate (absolute value usually, or signed).
                            If signed, cost function must handle direction.
                            We assume input is |z| and we want to trade |z|.
                            The Caller handles direction.
        n_steps: N_max steps.
        gamma: Risk aversion parameter.
        sigma: Volatility (std dev of price change per step).
        cost_function_callable: Function c(v) returning marginal price impact/cost for volume v.
                                Cost = v * c(v).
    
    Returns:
        x0: The fraction to trade NOW (at step 0).
    """
    z = abs(initial_position_z)
    if z < 1e-9:
        return 0.0
        
    # Variables: x[0]...x[N-1]
    # Constraints: sum(x) = 1
    # Bounds: x >= 0 (no buying back)
    
    def objective(x):
        # x is array of fractions
        # E[C]
        # Trade at step k is of size: v_k = x[k] * z
        # Cost of trade k: v_k * cost_func(v_k)
        
        # Note: If cost_function_callable returns "Spread", then Cost = v * spread.
        # Yes.
        
        expected_cost = 0.0
        for val in x:
            vol = val * z
            expected_cost += vol * cost_function_callable(vol)
            
        # Var[C]
        # Var = sigma^2 * sum(y_k^2)
        # y_k is remaining position *after* trade k? 
        # Standard AC: y_k is position held during interval k (after trade k).
        # y_0 = 1 - x_0
        # y_1 = y_0 - x_1
        # ...
        # y_{N-1} = 0 (liquidated)
        
        variance = 0.0
        current_y_fraction = 1.0
        
        for val in x:
            current_y_fraction -= val
            variance += (current_y_fraction * z) ** 2
            
        variance *= (sigma ** 2)
        
        return expected_cost + gamma * variance

    # Initial Guess: Uniform
    x0_guess = np.ones(n_steps) / n_steps
    
    # Constraints
    cons = ({'type': 'eq', 'fun': lambda x: np.sum(x) - 1.0})
    bounds = [(0.0, 1.0) for _ in range(n_steps)]
    
    # Optimization
    # Tolerance loose to be fast
    res = minimize(objective, x0_guess, method='SLSQP', bounds=bounds, constraints=cons, options={'ftol': 1e-4, 'disp': False})
    
    if res.success:
        return res.x[0]
    else:
        # Fallback to uniform or simple initial hedge
        return 1.0 / n_steps
