from concurrent.futures import ProcessPoolExecutor
import os
import subprocess
import shutil

distributions = ["CONSTANT", "UNIFORM", "EXPONENTIAL"]

def run_single_experiment(s_dist, t_dist):
    """Worker function for parallel simulation runs."""
    config_filename = f"tmp_config_{s_dist}_{t_dist}.txt"
    
    # Read base config and update distributions
    with open("config.txt", "r") as f:
        lines = f.readlines()
    
    with open(config_filename, "w") as f:
        for line in lines:
            if line.startswith("service_distribution="):
                f.write(f"service_distribution={s_dist}\n")
            elif line.startswith("think_distribution="):
                f.write(f"think_distribution={t_dist}\n")
            elif line.startswith("throttle_factor="):
                continue # We will set it explicitly below
            else:
                f.write(line)
        f.write("throttle_factor=1.0\n") # Disable throttling for main experiments
    
    print(f"   [START] Service={s_dist}, Think={t_dist}")
    try:
        # Run simulation
        subprocess.run(["./web_sim", config_filename], check=True, capture_output=True)
        # Run MVA
        subprocess.run(["python3", "mva_model.py", config_filename], check=True, capture_output=True)
    except Exception as e:
        print(f"   [ERROR] Service={s_dist}, Think={t_dist}: {e}")
        return False
    finally:
        if os.path.exists(config_filename):
            os.remove(config_filename)
    
    print(f"   [DONE]  Service={s_dist}, Think={t_dist}")
    return True

def run_single_experiment_wrapper(args):
    """Unpacks arguments for run_single_experiment."""
    return run_single_experiment(*args)

def main():
    print("Building web_sim...")
    subprocess.run(["make", "all"], check=True)

    print(f"\nRunning experiments across {len(distributions)**2} distribution combinations (Parallel)...")
    
    tasks = []
    for s_dist in distributions:
        for t_dist in distributions:
            tasks.append((s_dist, t_dist))

    # Using ProcessPoolExecutor for true parallelism
    with ProcessPoolExecutor() as executor:
        results = list(executor.map(run_single_experiment_wrapper, tasks))
    
    if all(results):
        print("\nAll simulations completed successfully.")
        
        # Integrate ranking and plotting
        print("\n--- Accuracy Ranking ---")
        import compare_accuracy
        import plot_results
        
        results_dir = "results"
        measured_csv = "closed_load_measurement.csv"
        
        rankings = compare_accuracy.get_rankings(results_dir, measured_csv)
        if 'measured' in rankings:
            print(rankings['measured'].to_string(index=False))
            print("\nGenerating consolidated plot...")
            plot_results.main()
    else:
        print("\nSome experiments failed.")

if __name__ == "__main__":
    main()
