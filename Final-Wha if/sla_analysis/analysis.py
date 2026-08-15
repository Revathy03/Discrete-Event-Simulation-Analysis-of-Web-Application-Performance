import os
import subprocess
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

# Configuration
CONFIG_FILE = "config.txt"
SIM_BINARY = "../../web_sim"
RESULTS_BASE = "results"

# Experiment Setup
USER_COUNTS = [10, 30, 50, 70, 100, 130, 150, 180, 200, 250, 300]
TIMEOUT = 0.5        # Strict SLA
SERVICE_TIME = 0.048  # From user request
BUFFER_SIZE = -1     # Infinite queue

def update_config(users):
    """Updates config.txt with experimental parameters"""
    with open(CONFIG_FILE, "r") as f:
        lines = f.readlines()
    with open(CONFIG_FILE, "w") as f:
        for line in lines:
            if line.startswith("user_counts="):
                f.write(f"user_counts={users}\n")
            elif line.startswith("timeout="):
                f.write(f"timeout={TIMEOUT}\n")
            elif line.startswith("mean_service="):
                f.write(f"mean_service={SERVICE_TIME}\n")
            elif line.startswith("max_queue_size="):
                f.write(f"max_queue_size={BUFFER_SIZE}\n")
            elif line.startswith("cores="):
                f.write("cores=1\n")
            elif line.startswith("output_dir="):
                continue
            else:
                f.write(line)
        f.write(f"output_dir={RESULTS_BASE}/users_{users}\n")

def run_sim():
    subprocess.run([SIM_BINARY, CONFIG_FILE], check=True, capture_output=True)

def collect_results():
    all_data = []
    for u in USER_COUNTS:
        path = f"{RESULTS_BASE}/users_{u}/think_time_EXPONENTIAL/service_time_EXPONENTIAL/des_results.csv"
        if os.path.exists(path):
            df = pd.read_csv(path)
            row = df.iloc[0].to_dict()
            row['Users'] = u
            all_data.append(row)
    return pd.DataFrame(all_data)

def main():
    if not os.path.exists(RESULTS_BASE): os.makedirs(RESULTS_BASE)
    
    print(f"Starting SLA Cliff Analysis (Timeout={TIMEOUT}s, Service={SERVICE_TIME}s)...")
    for u in USER_COUNTS:
        print(f"Testing Users: {u}...")
        update_config(u)
        run_sim()

    df = collect_results()
    
    # Plotting
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 12))

    # Plot 1: Throughput Composition
    ax1.plot(df['Users'], df['Goodput'], 'o-', label='Goodput (Useful)', color='green', linewidth=3)
    ax1.plot(df['Users'], df['Badput'], 's--', label='Badput (Late)', color='orange')
    ax1.plot(df['Users'], df['DropRate'], 'x:', label='Drop Rate (Waiting)', color='red')
    
    # Find Crossover Point (DropRate > Goodput)
    crossover_users = df[df['DropRate'] > df['Goodput']]['Users'].min()
    if pd.notna(crossover_users):
        ax1.axvline(x=crossover_users, color='black', linestyle='--', alpha=0.5)
        ax1.text(crossover_users + 5, df['Goodput'].max()/2, f'Crossover: ~{crossover_users} Users', fontweight='bold')

    ax1.set_xlabel('Number of Users')
    ax1.set_ylabel('Rate (req/s)')
    ax1.set_title('The SLA Cliff: Goodput vs. Badput vs. Drops')
    ax1.legend()
    ax1.grid(True, alpha=0.3)

    # Plot 2: Latency vs SLA
    ax2.plot(df['Users'], df['Avg_RT'], 'd-', color='purple', label='Avg Response Time')
    ax2.axhline(y=TIMEOUT, color='red', linestyle='--', label=f'SLA Timeout ({TIMEOUT}s)')
    ax2.set_xlabel('Number of Users')
    ax2.set_ylabel('Time (s)')
    ax2.set_title('Response Time Bloat vs. SLA Limit')
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    
    # Add annotation for the Capacity Limit
    capacity = 1.0 / SERVICE_TIME
    ax1.axhline(y=capacity, color='blue', linestyle=':', alpha=0.4, label='Theoretical Max Capacity')

    plt.tight_layout()
    plot_path = "sla_cliff_analysis.png"
    plt.savefig(plot_path)
    print(f"\nAnalysis complete! Plot saved to: {plot_path}")
    
    # Summary of findings
    print("\n--- Key Findings ---")
    print(f"Theoretical System Capacity: {capacity:.2f} req/s")
    max_goodput = df['Goodput'].max()
    peak_users = df.loc[df['Goodput'].idxmax(), 'Users']
    print(f"Peak Goodput: {max_goodput:.2f} req/s at {peak_users} users")
    print(f"Crossover Point (Drops > Goodput): {crossover_users} users")

if __name__ == "__main__":
    main()
