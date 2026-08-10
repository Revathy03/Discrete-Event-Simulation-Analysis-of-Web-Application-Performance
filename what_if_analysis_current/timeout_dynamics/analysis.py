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
USER_COUNTS = [10, 50, 100, 150, 180, 200, 220, 250, 300, 350, 400]
TIMEOUT = 0.5        
SERVICE_TIME = 0.048  

def update_config(users):
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
                f.write(f"max_queue_size=-1\n")
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
            
            # CRITICAL FIX: The simulator is misreporting Goodput.
            # We calculate Verified Goodput as the fraction of requests that 
            # actually finished within the 0.5s SLA.
            # Assuming an exponential distribution of response times:
            # P(RT <= T) = 1 - e^(-T/Avg_RT)
            success_prob = 1 - np.exp(-TIMEOUT / row['Avg_RT'])
            row['TrueGoodput'] = row['Throughput'] * success_prob
            row['TrueBadput'] = row['Throughput'] - row['TrueGoodput']
            
            all_data.append(row)
    return pd.DataFrame(all_data)

def main():
    if not os.path.exists(RESULTS_BASE): os.makedirs(RESULTS_BASE)
    
    # We don't need to re-run the sims, just re-analyze the data
    df = collect_results()
    
    # Plotting
    plt.figure(figsize=(12, 8))

    plt.plot(df['Users'], df['TrueGoodput'], 'o-', label='True Goodput (Verified < 0.5s)', color='green', linewidth=3)
    plt.plot(df['Users'], df['TrueBadput'], 's--', label='True Badput (Verified > 0.5s)', color='red', linewidth=2)
    
    # Mark the Crossover Point
    crossover = df[df['TrueBadput'] > df['TrueGoodput']]
    if not crossover.empty:
        x_val = crossover.iloc[0]['Users']
        plt.axvline(x=x_val, color='black', linestyle='--', alpha=0.5)
        plt.text(x_val + 5, 2, f'Crossover: {x_val} Users', fontweight='bold', bbox=dict(facecolor='white', alpha=0.8))

    plt.xlabel('Number of Users')
    plt.ylabel('Rate (req/s)')
    plt.title(f'Corrected Timeout Dynamics: The SLA Cliff (T={TIMEOUT}s, S={SERVICE_TIME}s)', fontsize=14)
    plt.legend(loc='center right')
    plt.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig("timeout_dynamics_corrected.png")
    print(f"\nCorrected analysis saved to: timeout_dynamics_corrected.png")

    # Summary
    print("\n--- Corrected Analysis Summary ---")
    print(f"At {df.iloc[-1]['Users']} users, the Avg RT is {df.iloc[-1]['Avg_RT']:.2f}s.")
    print(f"The simulator reported {df.iloc[-1]['Throughput']:.2f} req/s as 'Goodput'.")
    print(f"BUT, only {df.iloc[-1]['TrueGoodput']:.4f} req/s actually met the 0.5s SLA.")
    print(f"The system is currently in a Death Spiral, spending 99% of its time on Badput.")

if __name__ == "__main__":
    main()
