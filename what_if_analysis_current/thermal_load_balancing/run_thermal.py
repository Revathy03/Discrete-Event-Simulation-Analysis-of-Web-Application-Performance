import os
import subprocess
import pandas as pd
import matplotlib.pyplot as plt

# Define configurations
base_config = """# Thermal Analysis Config
num_servers=4
cores=2
threads_per_core=1
ctx_overhead=0.0012
sim_time=500.0
warmup=100.0
mean_think=7.152
mean_service=0.048
timeout=10.0
time_slice=1.0
max_queue_size=-1
num_runs=5
service_distribution=EXPONENTIAL
think_distribution=EXPONENTIAL
user_counts=10,50,100,150,200,300,400,500,600,700,800
"""

def prepare_config(policy):
    out_dir = f"whatif_analysis/thermal_load_balancing/{policy}_results"
    cfg = base_config + f"\nload_balancer={policy}\noutput_dir={out_dir}\n"
    cfg_file = f"temp_config_{policy}.txt"
    with open(cfg_file, "w") as f:
        f.write(cfg)
    return cfg_file, out_dir

def run_experiment(policy):
    cfg_file, out_dir = prepare_config(policy)
    print(f"Running simulation for {policy}...")
    subprocess.run(["./web_sim", cfg_file], check=True)
    
    # Path to CSV
    csv_path = f"{out_dir}/think_time_EXPONENTIAL/service_time_EXPONENTIAL/des_results.csv"
    
    if os.path.exists(csv_path):
        return pd.read_csv(csv_path)
    else:
        print(f"Warning: Results not found at {csv_path}")
        return None

def plot_results(df_rr, df_thermal):
    plt.figure(figsize=(12, 5))
    
    # Plot Peak Temperature
    plt.subplot(1, 2, 1)
    plt.plot(df_rr['Users'], df_rr['MaxTemp'], marker='o', label='ROUND_ROBIN', linestyle='--')
    plt.plot(df_thermal['Users'], df_thermal['MaxTemp'], marker='s', label='THERMAL', linestyle='-')
    plt.title('Peak Output Temperature vs Users (4 Servers, 2 Cores/Server)')
    plt.xlabel('Concurrent Users')
    plt.ylabel('Peak Temperature (°C)')
    plt.grid(True)
    plt.legend()
    
    # Plot Response Time
    plt.subplot(1, 2, 2)
    plt.plot(df_rr['Users'], df_rr['Avg_RT'], marker='o', label='ROUND_ROBIN', linestyle='--')
    plt.plot(df_thermal['Users'], df_thermal['Avg_RT'], marker='s', label='THERMAL', linestyle='-')
    plt.title('Average Response Time vs Users')
    plt.xlabel('Concurrent Users')
    plt.ylabel('Response Time (s)')
    plt.grid(True)
    plt.legend()
    
    plt.tight_layout()
    import time
    timestamp = int(time.time())
    plot_file = f"whatif_analysis/thermal_load_balancing/thermal_effectiveness_{timestamp}.png"
    plt.savefig(plot_file)
    print(f"Plot saved to '{plot_file}'.")

def main():
    if not os.path.exists('web_sim'):
        print("Please compile 'web_sim' first using 'make'")
        return

    os.makedirs("whatif_analysis/thermal_load_balancing", exist_ok=True)
    
    df_rr = run_experiment("ROUND_ROBIN")
    df_thermal = run_experiment("THERMAL")
    
    if df_rr is not None and df_thermal is not None:
        plot_results(df_rr, df_thermal)
        
    # Cleanup config files
    for p in ["ROUND_ROBIN", "THERMAL"]:
        if os.path.exists(f"temp_config_{p}.txt"):
            os.remove(f"temp_config_{p}.txt")

if __name__ == "__main__":
    main()
