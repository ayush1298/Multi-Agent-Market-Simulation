# run_all.py
from experiments.exp_sensitivity import run_sensitivity_experiment
from experiments.exp_internalization import run_internalization_experiment
from experiments.exp_hedging import run_hedging_experiment

if __name__ == "__main__":
    print("Starting All Experiments...")
    run_sensitivity_experiment()
    run_internalization_experiment()
    run_hedging_experiment()
    print("All Experiments Completed.")
