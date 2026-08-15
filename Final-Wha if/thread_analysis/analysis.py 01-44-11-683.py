import os
import subprocess
import pandas as pd
import matplotlib.pyplot as plt

# Configuration
CONFIG_FILE = "config.txt"
SIM_BINARY = "../../web_sim"
RESULTS_BASE = "results"

# Fixed Core counts
CORE_CONFIGS = [1, 4] 
# Increasing threads per core
THREAD_SWEEP = [1, 2, 4, 8, 16] 

def update_config(cores, threads):
    """Updates config.txt for a specific cores/threads combo"""
    with open(CONFIG_FILE, "r") as f:
        lines = f.readlines()
    with open(CONFIG_FILE, "w") as f:
        for line in lines:
            if line.startswith("cores="):
                f.write(f"cores={cores}\n")
            elif line.startswith("threads_per_core="):
                f.write(f"threads_per_core={threads}\n")
            elif line.startswith("output_dir="):
                continue
            elif line.startswith("user_counts="):
                f.write("user_counts=200\n")
            elif line.startswith("max_queue_size="):
                f.write("max_queue_size=100\n")
            elif line.startswith("timeout="):
                f.write("timeout=1000.0\n")
            else:
                f.write(line)
        f.write(f"output_dir={RESULTS_BASE}/cores_{cores}_tpc_{threads}\n")

def run_sim():
    subprocess.run([SIM_BINARY, CONFIG_FILE], check=True, capture_output=True)

def collect_results():
    data = []
    for c in CORE_CONFIGS:
        for t in THREAD_SWEEP:
            path = f"{RESULTS_BASE}/cores_{c}_tpc_{t}/think_time_EXPONENTIAL/service_time_EXPONENTIAL/des_results.csv"
            if os.path.exists(path):
                df = pd.read_csv(path)
                row = df.iloc[0].to_dict()
                row['Cores'] = f'{c} Core(s)'
                row['ThreadsPerCore'] = t
                data.append(row)
    return pd.DataFrame(data)

def main():
    if not os.path.exists(RESULTS_BASE): os.makedirs(RESULTS_BASE)
    
    print("Starting Threading Analysis (Fixed Cores, Variable Threads)...")
    for c in CORE_CONFIGS:
        for t in THREAD_SWEEP:
            print(f"Testing {c} Core(s) with {t} Threads per Core...")
            update_config(c, t)
            run_sim()

    df = collect_results()
    
    # Plotting
    plt.figure(figsize=(10, 6))
    for core_label in df['Cores'].unique():
        subset = df[df['Cores'] == core_label]
        plt.plot(subset['ThreadsPerCore'], subset['Avg_RT'], 'o-', linewidth=2, label=core_label)

    plt.xlabel('Threads per Core', fontsize=12)
    plt.ylabel('Average Response Time (s)', fontsize=12)
    plt.title('How Multi-threading Affects Response Time\n(Comparing 1 Core vs. 4 Cores)', fontsize=14)
    plt.legend()
    plt.grid(True, linestyle='--', alpha=0.6)
    
    plt.xticks(THREAD_SWEEP)
    
    plot_path = "thread_impact_fixed_cores.png"
    plt.savefig(plot_path)
    print(f"\nAnalysis complete! Plot saved to: {plot_path}")

if __name__ == "__main__":
    main()
