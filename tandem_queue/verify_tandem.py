import subprocess
import shutil
import csv
import os
import matplotlib.pyplot as plt

def run_mva(N, Z, D0, D1):
    """
    Mean Value Analysis for a closed system with:
    - N: Number of users
    - Z: Think time (delay center)
    - D0, D1: Service demands at server 0 and 1 (queueing centers)
    """
    Q0 = 0.0 # Initial queue length at server 0
    Q1 = 0.0 # Initial queue length at server 1
    
    for n in range(1, N + 1):
        # 1. Response times at each center for n users
        R0 = D0 * (1 + Q0)
        R1 = D1 * (1 + Q1)
        
        # 2. System Throughput
        lambda_val = n / (R0 + R1 + Z)
        
        # 3. New Queue Lengths for n users (using Little's Law)
        Q0 = lambda_val * R0
        Q1 = lambda_val * R1
        
    return lambda_val, (R0 + R1)

def calculate_open_rt(lambda_val, mu0, mu1):
    if lambda_val >= mu0 or lambda_val >= mu1:
        return float('inf')
    # E[N] = rho0/(1-rho0) + rho1/(1-rho1)
    # E[R] = E[N] / lambda = 1/(mu0-lambda) + 1/(mu1-lambda)
    return 1.0 / (mu0 - lambda_val) + 1.0 / (mu1 - lambda_val)

def run_simulation():
    print("Running tandem queue simulation...")
    # Ensure we run the tandem-specific web_sim
    binary = "./web_sim"
    if not os.path.exists(binary):
        print("Error: tandem_queue/web_sim not found. Build it first.")
        return
    subprocess.run([binary, "config.txt"], check=True, capture_output=True)

def verify():
    results_file = "results/think_time_EXPONENTIAL/service_time_EXPONENTIAL/des_results.csv"
    if not os.path.exists(results_file):
        print(f"Error: Results file {results_file} not found.")
        return

    mu0 = 1.0 / 0.05
    mu1 = 1.0 / 0.05
    D0 = 0.05
    D1 = 0.05
    Z = 100.0

    print("\nVerification Results (MVA Based):")
    print(f"{'Users':<6} | {'Thrpt(MVA)':<10} | {'Thrpt(Obs)':<10} | {'RT(Theo)':<10} | {'RT(Obs)':<10} | {'Error %':<8}")
    print("-" * 80)

    stats = []
    with open(results_file, mode='r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            N = int(row['Users'])
            avg_rt_obs = float(row['Avg_RT'])
            thrpt_obs = float(row['Throughput'])
            
            # 1. Get theoretical throughput from MVA
            thrpt_mva, rt_mva = run_mva(N, Z, D0, D1)
            
            # 2. Get theoretical RT using MVA throughput and Open Formula
            rt_theo = calculate_open_rt(thrpt_mva, mu0, mu1)
            
            error = abs(avg_rt_obs - rt_theo) / rt_theo * 100 if rt_theo != float('inf') else 0
            
            print(f"{N:<6} | {thrpt_mva:<10.4f} | {thrpt_obs:<10.4f} | {rt_theo:<10.4f} | {avg_rt_obs:<10.4f} | {error:<8.2f}%")
            stats.append({'Users': N, 'RT_Obs': avg_rt_obs, 'RT_Theo': rt_theo, 'TP_Obs': thrpt_obs, 'TP_Theo': thrpt_mva})

    # Generate Plots
    plt.figure(figsize=(14, 6), dpi=200)
    
    # 1. Throughput Plot
    plt.subplot(1, 2, 1)
    users = [s['Users'] for s in stats]
    plt.plot(users, [s['TP_Theo'] for s in stats], 'r--', label='MVA Theoretical')
    plt.plot(users, [s['TP_Obs'] for s in stats], 'bo-', label='DES Observed')
    plt.title('Tandem Queue: Throughput Comparison')
    plt.xlabel('Number of Users')
    plt.ylabel('Throughput (req/s)')
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.legend()

    # 2. Response Time Plot
    plt.subplot(1, 2, 2)
    plt.plot(users, [s['RT_Theo'] for s in stats], 'r--', label='Theoretical (Open Formula)')
    plt.plot(users, [s['RT_Obs'] for s in stats], 'go-', label='DES Observed')
    plt.title('Tandem Queue: Response Time Comparison')
    plt.xlabel('Number of Users')
    plt.ylabel('Avg Response Time (s)')
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.legend()

    plt.tight_layout()
    plt.savefig("results/tandem_comparison.png")
    plt.close()
    print("\nTandem comparison plots saved to results/tandem_comparison.png")

if __name__ == "__main__":
    run_simulation()
    verify()
    
    # Organize results
    dest = "../final_results/tandem_queue"
    if os.path.exists("results"):
        if os.path.exists(dest):
            shutil.rmtree(dest)
        shutil.copytree("results", dest)
        print(f"Tandem results organized in {dest}")
