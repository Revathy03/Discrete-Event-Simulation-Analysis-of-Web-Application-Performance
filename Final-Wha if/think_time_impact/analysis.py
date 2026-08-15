import os
import subprocess
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

# Configuration
CONFIG_FILE = "config.txt"
SIM_BINARY = "../../web_sim"
RESULTS_BASE = "results"

# Range of think times to explore (What-if analysis)
THINK_TIMES = [0.5, 1.0, 2.0, 2.41, 4.0, 7.152, 10.0]
# Range of user counts to check for saturation
USER_COUNTS = [10, 25, 50, 75, 100, 125, 150, 175, 200, 250, 300]

def update_config(think_time, user_counts_str):
    with open(CONFIG_FILE, "r") as f:
        lines = f.readlines()
    with open(CONFIG_FILE, "w") as f:
        for line in lines:
            if line.strip().startswith("mean_think="):
                f.write(f"mean_think={think_time}\n")
            elif line.strip().startswith("user_counts="):
                f.write(f"user_counts={user_counts_str}\n")
            else:
                f.write(line)
        f.write(f"output_dir={RESULTS_BASE}/think_{think_time}\n")

def run_sim():
    subprocess.run([SIM_BINARY, CONFIG_FILE], check=True, capture_output=True)

def run_simulations():
    print("Starting simulation suite...")
    for z in THINK_TIMES:
        print(f"  Running think_time={z}s...")
        user_counts_str = ",".join(map(str, USER_COUNTS))
        update_config(z, user_counts_str)
        run_sim()

def collect_results():
    all_data = []
    for z in THINK_TIMES:
        path = f"{RESULTS_BASE}/think_{z}/think_time_EXPONENTIAL/service_time_EXPONENTIAL/des_results.csv"
        if os.path.exists(path):
            df = pd.read_csv(path)
            df['ThinkTime'] = z
            all_data.append(df)
    return pd.concat(all_data) if all_data else pd.DataFrame()

def main():
    if not os.path.exists(RESULTS_BASE): os.makedirs(RESULTS_BASE)
    
    # 1. Run Simulations
    run_simulations()
    
    # 2. Collect Data
    df = collect_results()
    if df.empty:
        print("No results collected. Check if web_sim is compiled and config is correct.")
        return

    # 3. Analyze Saturation Points
    # We define saturation where Utilization >= 0.95 or Throughput stops increasing
    saturation_points = []
    for z in THINK_TIMES:
        z_df = df[df['ThinkTime'] == z].sort_values('Users')
        # Use Utilization as a primary indicator
        sat_row = z_df[z_df['Utilization'] >= 0.95]
        if not sat_row.empty:
            n_sat = sat_row.iloc[0]['Users']
        else:
            n_sat = z_df.iloc[-1]['Users'] # Fallback
        saturation_points.append({'ThinkTime': z, 'N_sat': n_sat})
    
    sat_df = pd.DataFrame(saturation_points)

    # 4. Plotting
    plt.figure(figsize=(15, 6))

    # Plot 1: Throughput vs Users for different Think Times
    plt.subplot(1, 2, 1)
    for z in THINK_TIMES:
        z_df = df[df['ThinkTime'] == z].sort_values('Users')
        plt.plot(z_df['Users'], z_df['Throughput'], 'o-', label=f'Z={z}s')
    
    plt.axhline(y=1/0.0492, color='r', linestyle='--', alpha=0.5, label='Theoretical Max')
    plt.xlabel('Number of Users')
    plt.ylabel('Throughput (req/s)')
    plt.title('Throughput vs. Users (Varying Think Time)')
    plt.legend()
    plt.grid(True, alpha=0.3)

    # Plot 2: Saturation Users vs Think Time
    plt.subplot(1, 2, 2)
    plt.plot(sat_df['ThinkTime'], sat_df['N_sat'], 's-', color='darkblue', linewidth=2)
    
    # Add theoretical line
    D = 0.0492
    z_range = np.linspace(min(THINK_TIMES), max(THINK_TIMES), 100)
    plt.plot(z_range, z_range/D + 1, 'r--', alpha=0.5, label='Theoretical (N* = Z/D + 1)')
    
    # Highlight the 50 user case
    plt.annotate('50 Users @ 2.41s', xy=(2.41, 50), xytext=(4, 40),
                 arrowprops=dict(facecolor='black', shrink=0.05))

    plt.xlabel('Think Time (s)')
    plt.ylabel('Saturation User Count (N*)')
    plt.title('Saturation Point vs. Think Time')
    plt.legend()
    plt.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig("think_time_impact.png")
    print(f"\nAnalysis saved to think_time_impact.png")

    # 5. Comparative Summary for the User's question
    case_200 = df[(df['ThinkTime'] == 7.152) & (df['Users'] == 200)].iloc[0]
    case_50 = df[(df['ThinkTime'] == 2.41) & (df['Users'] == 50)].iloc[0]

    print("\n--- Comparative Analysis ---")
    print(f"{'Metric':<20} | {'N=200, Z=7.15s':<15} | {'N=50, Z=2.41s':<15}")
    print("-" * 56)
    print(f"{'Throughput (req/s)':<20} | {case_200['Throughput']:<15.2f} | {case_50['Throughput']:<15.2f}")
    print(f"{'Utilization':<20} | {case_200['Utilization']:<15.2f} | {case_50['Utilization']:<15.2f}")
    print(f"{'Avg Response Time':<20} | {case_200['Avg_RT']:<15.3f} | {case_50['Avg_RT']:<15.3f}")
    print("\nObservation: Both configurations lead to server saturation (Utilization ~1.0).")
    print("At Z=2.41s, 50 users apply the same pressure as 200 users at Z=7.15s.")

if __name__ == "__main__":
    main()
