import os
import subprocess
import pandas as pd
import matplotlib.pyplot as plt

# Configuration
CONFIG_FILE = "config.txt"
SIM_BINARY = "../../web_sim"
RESULTS_BASE = "results"

# Range of total threads to test
TEST_RANGE = [1, 2, 3, 4, 6, 8]

def update_config(cores, threads, label):
    """Updates config.txt for a specific hardware setup"""
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
        f.write(f"output_dir={RESULTS_BASE}/{label}_total_{cores*threads}\n")

def run_sim():
    subprocess.run([SIM_BINARY, CONFIG_FILE], check=True, capture_output=True)

def collect_results(label, total_range, is_multi_core):
    data = []
    for val in total_range:
        path = f"{RESULTS_BASE}/{label}_total_{val}/think_time_EXPONENTIAL/service_time_EXPONENTIAL/des_results.csv"
        if os.path.exists(path):
            df = pd.read_csv(path)
            row = df.iloc[0].to_dict()
            row['TotalThreads'] = val
            row['Type'] = 'Multi-Core (Adding Cores)' if is_multi_core else 'Single-Core (Adding Threads)'
            data.append(row)
    return data

def main():
    if not os.path.exists(RESULTS_BASE): os.makedirs(RESULTS_BASE)
    
    print("Starting Threading vs. Core Efficiency Analysis...")
    
    # 1. Single Core Sweep (Increase threads on 1 core)
    for t in TEST_RANGE:
        print(f"Testing Single Core: 1 Core, {t} Threads...")
        update_config(1, t, "single_core")
        run_sim()

    # 2. Multi Core Sweep (Increase cores, 1 thread per core)
    # Note: We limit this to the number of physical cores available in the sim (usually 4 or 8)
    for c in [1, 2, 3, 4, 6, 8]:
        print(f"Testing Multi-Core: {c} Cores, 1 Thread/Core...")
        update_config(c, 1, "multi_core")
        run_sim()

    # Collect and Plot
    results = collect_results("single_core", TEST_RANGE, False) + \
              collect_results("multi_core", [1, 2, 3, 4, 6, 8], True)
    df = pd.DataFrame(results)
    
    plt.figure(figsize=(12, 7))
    for t in df['Type'].unique():
        subset = df[df['Type'] == t]
        plt.plot(subset['TotalThreads'], subset['Avg_RT'], 'o-', linewidth=2, label=t)

    plt.xlabel('Total Processing Units (Cores or Threads)', fontsize=12)
    plt.ylabel('Average Response Time (s)', fontsize=12)
    plt.title('Why Threads ≠ Cores: Single-Core Scaling vs. Multi-Core Scaling', fontsize=14)
    plt.legend()
    plt.grid(True, linestyle='--', alpha=0.6)
    
    # Label the starting point
    plt.annotate('Baseline (1 Core, 1 Thread)', xy=(1, df['Avg_RT'].max()), xytext=(2, df['Avg_RT'].max()),
                 arrowprops=dict(facecolor='black', shrink=0.05))

    plot_path = "cores_vs_threads_rt.png"
    plt.savefig(plot_path)
    print(f"\nAnalysis complete! Plot saved to: {plot_path}")

if __name__ == "__main__":
    main()
