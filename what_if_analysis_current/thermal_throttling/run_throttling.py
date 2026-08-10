import os
import subprocess
import pandas as pd
import matplotlib.pyplot as plt
import time

# Define configurations for Single Server Throttling Analysis
base_config = """# Thermal Throttling Analysis Config
num_servers=1
cores=4
threads_per_core=1
ctx_overhead=0.0012
sim_time=500.0
warmup=100.0
mean_think=7.152
mean_service=0.1
timeout=10.0
time_slice=1.0
max_queue_size=-1
num_runs=5
service_distribution=EXPONENTIAL
think_distribution=EXPONENTIAL
user_counts=50,100,200,300,400,500,600,700,800
"""

def prepare_config(name, threshold, factor):
    out_dir = f"whatif_analysis/thermal_throttling/{name}_results"
    cfg = base_config + f"\noutput_dir={out_dir}\nthermal_threshold={threshold}\nthrottle_factor={factor}\n"
    cfg_file = f"temp_config_{name}.txt"
    with open(cfg_file, "w") as f:
        f.write(cfg)
    return cfg_file, out_dir

def run_experiment(name, threshold, factor):
    cfg_file, out_dir = prepare_config(name, threshold, factor)
    print(f"Running simulation for {name} (Threshold={threshold}, Factor={factor})...")
    subprocess.run(["./web_sim", cfg_file], check=True)
    
    # Path to CSV
    csv_path = f"{out_dir}/think_time_EXPONENTIAL/service_time_EXPONENTIAL/des_results.csv"
    
    if os.path.exists(csv_path):
        df = pd.read_csv(csv_path)
        return df
    else:
        print(f"Warning: Results not found at {csv_path}")
        return None

def plot_throttling_results(df_base, df_throttle):
    plt.figure(figsize=(15, 5))
    
    # Plot Peak Temperature
    plt.subplot(1, 3, 1)
    plt.plot(df_base['Users'], df_base['MaxTemp'], marker='o', label='No Throttling (Baseline)', linestyle='--')
    plt.plot(df_throttle['Users'], df_throttle['MaxTemp'], marker='s', label='With Throttling (70°C)', linestyle='-')
    plt.axhline(y=70, color='r', linestyle=':', label='Threshold (70°C)')
    plt.title('Peak Temperature vs Users')
    plt.xlabel('Concurrent Users')
    plt.ylabel('Peak Temperature (°C)')
    plt.grid(True)
    plt.legend()
    
    # Plot Response Time
    plt.subplot(1, 3, 2)
    plt.plot(df_base['Users'], df_base['Avg_RT'], marker='o', label='No Throttling', linestyle='--')
    plt.plot(df_throttle['Users'], df_throttle['Avg_RT'], marker='s', label='With Throttling', linestyle='-')
    plt.title('Average Response Time vs Users')
    plt.xlabel('Concurrent Users')
    plt.ylabel('Response Time (s)')
    plt.grid(True)
    plt.legend()

    # Plot Goodput
    plt.subplot(1, 3, 3)
    plt.plot(df_base['Users'], df_base['Goodput'], marker='o', label='No Throttling', linestyle='--')
    plt.plot(df_throttle['Users'], df_throttle['Goodput'], marker='s', label='With Throttling', linestyle='-')
    plt.title('Goodput vs Users')
    plt.xlabel('Concurrent Users')
    plt.ylabel('Goodput (req/s)')
    plt.grid(True)
    plt.legend()
    
    plt.tight_layout()
    timestamp = int(time.time())
    plot_file = f"whatif_analysis/thermal_throttling/throttling_analysis_{timestamp}.png"
    os.makedirs(os.path.dirname(plot_file), exist_ok=True)
    plt.savefig(plot_file)
    print(f"Plot saved to '{plot_file}'.")

def main():
    if not os.path.exists('web_sim'):
        print("Please compile 'web_sim' first.")
        return

    os.makedirs("whatif_analysis/thermal_throttling", exist_ok=True)
    
    # Baseline: High threshold so it never throttles
    df_base = run_experiment("Baseline", threshold=100.0, factor=1.0)
    
    # Throttling: Throttle at 70°C to 50% speed
    df_throttle = run_experiment("Throttling", threshold=70.0, factor=0.5)
    
    if df_base is not None and df_throttle is not None:
        plot_throttling_results(df_base, df_throttle)
        
    # Cleanup config files
    for p in ["Baseline", "Throttling"]:
        if os.path.exists(f"temp_config_{p}.txt"):
            os.remove(f"temp_config_{p}.txt")

if __name__ == "__main__":
    main()
