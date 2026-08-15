import os
import subprocess
import pandas as pd
import matplotlib.pyplot as plt

# Configuration
CONFIG_FILE = "config.txt"
SIM_BINARY = "../../web_sim"
RESULTS_BASE = "results"

# Experiment Setup
CORE_CONFIGS = [1, 4]
BUFFER_SIZES = [5, 10, 20, 30, 50, 70, 100, 150]
TIMEOUT = 2.0 # 2-second user timeout

def update_config(cores, buffer_size):
    """Updates cores, max_queue_size, and timeout in config.txt"""
    with open(CONFIG_FILE, "r") as f:
        lines = f.readlines()
    with open(CONFIG_FILE, "w") as f:
        for line in lines:
            if line.startswith("cores="):
                f.write(f"cores={cores}\n")
            elif line.startswith("max_queue_size="):
                f.write(f"max_queue_size={buffer_size}\n")
            elif line.startswith("timeout="):
                f.write(f"timeout={TIMEOUT}\n")
            elif line.startswith("user_counts="):
                # Use a high load (250 users) to ensure the buffer is stressed
                f.write("user_counts=250\n")
            elif line.startswith("output_dir="):
                continue
            else:
                f.write(line)
        f.write(f"output_dir={RESULTS_BASE}/cores_{cores}_buffer_{buffer_size}\n")

def run_sim():
    subprocess.run([SIM_BINARY, CONFIG_FILE], check=True, capture_output=True)

def collect_results():
    all_data = []
    for c in CORE_CONFIGS:
        for b in BUFFER_SIZES:
            path = f"{RESULTS_BASE}/cores_{c}_buffer_{b}/think_time_EXPONENTIAL/service_time_EXPONENTIAL/des_results.csv"
            if os.path.exists(path):
                df = pd.read_csv(path)
                row = df.iloc[0].to_dict()
                row['Cores'] = c
                row['BufferSize'] = b
                all_data.append(row)
    return pd.DataFrame(all_data)

def main():
    if not os.path.exists(RESULTS_BASE): os.makedirs(RESULTS_BASE)
    
    print(f"Starting Multi-Core Buffer Analysis (Timeout={TIMEOUT}s)...")
    for c in CORE_CONFIGS:
        for b in BUFFER_SIZES:
            print(f"Testing Config: Cores={c}, Buffer={b}...")
            update_config(c, b)
            run_sim()

    df = collect_results()
    
    # Plotting
    plt.figure(figsize=(12, 8))
    
    for c in CORE_CONFIGS:
        subset = df[df['Cores'] == c]
        label = f'{c} Core(s)'
        plt.plot(subset['BufferSize'], subset['Goodput'], 'o-', linewidth=2, label=f'Goodput ({label})')

    plt.xlabel('Buffer Size (Max Queue Length)', fontsize=12)
    plt.ylabel('Goodput (req/s)', fontsize=12)
    plt.title('How Hardware Capacity Shifts the Buffer Paradox\n(Fixed 2.0s User Timeout, 250 Users)', fontsize=14)
    plt.grid(True, linestyle='--', alpha=0.6)
    plt.legend()
    
    # Add a visual explanation of why they differ
    plt.annotate('Bufferbloat starts early for 1 core', xy=(20, df[(df['Cores']==1) & (df['BufferSize']==20)]['Goodput'].values[0]), 
                 xytext=(40, 1), arrowprops=dict(facecolor='red', shrink=0.05))
    
    plt.annotate('4 cores clear the queue faster,\nallowing larger buffers', xy=(70, df[(df['Cores']==4) & (df['BufferSize']==70)]['Goodput'].values[0]), 
                 xytext=(80, 15), arrowprops=dict(facecolor='green', shrink=0.05))

    plot_path = "multicore_buffer_shift.png"
    plt.savefig(plot_path)
    print(f"\nAnalysis complete! Plot saved to: {plot_path}")

if __name__ == "__main__":
    main()
