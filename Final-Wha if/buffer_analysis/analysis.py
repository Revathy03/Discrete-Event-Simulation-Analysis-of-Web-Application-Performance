import os
import subprocess
import pandas as pd
import matplotlib.pyplot as plt

# Configuration
CONFIG_FILE = "config.txt"
SIM_BINARY = "../../web_sim"
RESULTS_BASE = "results"

# We test two distinct load scenarios
USER_LOADS = [100, 250] 
# A more granular range to find the 'knee'
BUFFER_SIZES = [5, 10, 20, 40, 60, 80, 100, 150, 250] 

def update_config(size, users, timeout=1000.0):
    """Updates queue size, user count, and timeout in config.txt"""
    with open(CONFIG_FILE, "r") as f:
        lines = f.readlines()
    with open(CONFIG_FILE, "w") as f:
        for line in lines:
            if line.startswith("max_queue_size="):
                f.write(f"max_queue_size={size}\n")
            elif line.startswith("user_counts="):
                f.write(f"user_counts={users}\n")
            elif line.startswith("timeout="):
                f.write(f"timeout={timeout}\n")
            elif line.startswith("output_dir="):
                continue
            else:
                f.write(line)
        label = "infinite" if size == -1 else str(size)
        f.write(f"output_dir={RESULTS_BASE}/users_{users}_size_{label}\n")

def run_sim():
    subprocess.run([SIM_BINARY, CONFIG_FILE], check=True, capture_output=True)

def collect_results():
    all_data = []
    for u in USER_LOADS:
        for s in BUFFER_SIZES:
            label = "infinite" if s == -1 else str(s)
            path = f"{RESULTS_BASE}/users_{u}_size_{label}/think_time_EXPONENTIAL/service_time_EXPONENTIAL/des_results.csv"
            if os.path.exists(path):
                df = pd.read_csv(path)
                # Take the first (and only) row for this specific user count
                row = df.iloc[0].to_dict()
                row['BufferSize'] = s
                row['Users'] = u
                row['Label'] = "Inf" if s == -1 else str(s)
                all_data.append(row)
    return pd.DataFrame(all_data)

def main():
    if not os.path.exists(RESULTS_BASE): os.makedirs(RESULTS_BASE)
    
    print(f"Starting Optimal Buffer Analysis for loads: {USER_LOADS}")
    for u in USER_LOADS:
        for s in BUFFER_SIZES:
            lbl = "Infinite" if s == -1 else str(s)
            print(f"Testing Users: {u}, Buffer: {lbl}...")
            update_config(s, u)
            run_sim()

    df = collect_results()
    
    # Plotting
    fig, axes = plt.subplots(len(USER_LOADS), 1, figsize=(12, 6 * len(USER_LOADS)))
    if len(USER_LOADS) == 1: axes = [axes]

    for i, u in enumerate(USER_LOADS):
        ax1 = axes[i]
        subset = df[df['Users'] == u]
        indices = range(len(subset))
        
        # Goodput on Left Y-Axis
        color1 = 'tab:green'
        ax1.set_xlabel('Buffer Size')
        ax1.set_ylabel('Goodput (req/s)', color=color1, fontweight='bold')
        ax1.plot(indices, subset['Goodput'], 'o-', color=color1, linewidth=2, label='Goodput')
        ax1.tick_params(axis='y', labelcolor=color1)
        ax1.set_xticks(indices)
        ax1.set_xticklabels(subset['Label'])
        
        # Response Time on Right Y-Axis
        ax2 = ax1.twinx()
        color2 = 'tab:red'
        ax2.set_ylabel('Avg Response Time (s)', color=color2, fontweight='bold')
        ax2.plot(indices, subset['Avg_RT'], 's--', color=color2, linewidth=2, label='Avg RT')
        ax2.tick_params(axis='y', labelcolor=color2)
        
        ax1.set_title(f'Buffer Optimization (No Timeout): {u} Concurrent Users', fontsize=14, pad=15)
        ax1.grid(True, alpha=0.3)
        
        # In a no-timeout scenario, the 'right' buffer is the one that plateaus Goodput
        # No Gray shading needed as there is no timeout 'danger'
            
    plt.tight_layout()
    plot_path = "buffer_optimization_results.png"
    plt.savefig(plot_path)
    print(f"\nAnalysis complete! Plot saved to: {plot_path}")

if __name__ == "__main__":
    main()
