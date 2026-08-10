import os
import subprocess
import pandas as pd
import matplotlib.pyplot as plt

# Configuration
CONFIG_FILE = "config.txt"
SIM_BINARY = "../../web_sim"
RESULTS_BASE = "results"
TIME_SLICES = [0.005, 0.01, 0.02, 0.05, 0.1, 0.2, 0.5, 1.0]

def update_config(quantum):
    with open(CONFIG_FILE, "r") as f:
        lines = f.readlines()
    with open(CONFIG_FILE, "w") as f:
        for line in lines:
            if line.startswith("time_slice="):
                f.write(f"time_slice={quantum}\n")
            elif line.startswith("output_dir="):
                continue # Skip existing output_dir to set it below
            else:
                f.write(line)
        f.write(f"output_dir={RESULTS_BASE}/slice_{str(quantum).replace('.','p')}\n")

def run_sim():
    subprocess.run([SIM_BINARY, CONFIG_FILE], check=True, capture_output=True)

def collect_results():
    all_data = []
    for q in TIME_SLICES:
        path = f"{RESULTS_BASE}/slice_{str(q).replace('.','p')}/think_time_EXPONENTIAL/service_time_EXPONENTIAL/des_results.csv"
        if os.path.exists(path):
            df = pd.read_csv(path)
            # We take the result for a high load (e.g., 200 users) to see the saturation clearly
            # Or average across all user counts if preferred. Let's take 150 users as a representative load.
            df_subset = df[df['Users'] == 150]
            if not df_subset.empty:
                row = df_subset.iloc[0].to_dict()
                row['Quantum'] = q
                all_data.append(row)
    return pd.DataFrame(all_data)

def main():
    if not os.path.exists(RESULTS_BASE): os.makedirs(RESULTS_BASE)
    
    print("Running simulations for different quantum values...")
    for q in TIME_SLICES:
        print(f"Testing Quantum: {q}s")
        update_config(q)
        run_sim()

    df = collect_results()
    print("\nSummary Results (at 150 users):")
    print(df[['Quantum', 'Goodput', 'Avg_RT']])

    # Plotting
    fig, ax1 = plt.subplots(figsize=(10, 6))

    color = 'tab:blue'
    ax1.set_xlabel('Quantum (Time Slice) [s]')
    ax1.set_ylabel('Goodput (req/s)', color=color)
    ax1.plot(df['Quantum'], df['Goodput'], 'o-', color=color, label='Goodput')
    ax1.tick_params(axis='y', labelcolor=color)

    ax2 = ax1.twinx()
    color = 'tab:red'
    ax2.set_ylabel('Avg Response Time [s]', color=color)
    ax2.plot(df['Quantum'], df['Avg_RT'], 's-', color=color, label='Avg RT')
    ax2.tick_params(axis='y', labelcolor=color)

    plt.title('Quantum Optimization: Goodput vs Latency Tradeoff\n(Fixed ctx=0.01s, service=0.15s, 150 Users)')
    plt.xscale('log') 
    from matplotlib.ticker import ScalarFormatter
    ax1.xaxis.set_major_formatter(ScalarFormatter())
    ax1.set_xticks(TIME_SLICES) # Ensure all our tested values are marked
    plt.grid(True, which="both", ls="-", alpha=0.5)
    
    plot_path = f"{RESULTS_BASE}/quantum_tradeoff.png"
    plt.savefig(plot_path)
    print(f"\nPlot saved to: {plot_path}")

if __name__ == "__main__":
    main()
