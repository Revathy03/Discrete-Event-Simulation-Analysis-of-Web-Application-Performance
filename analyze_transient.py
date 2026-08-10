import pandas as pd
import matplotlib.pyplot as plt
import os
import subprocess

def run_single_simulation(users, warmup_vals):
    results = []
    
    # Backup original config
    if os.path.exists('config.txt'):
        with open('config.txt', 'r') as f:
            original_config = f.read()
    else:
        original_config = None

    try:
        for w in warmup_vals:
            with open('config.txt', 'w') as f:
                f.write(f"cores=1\nthreads_per_core=1\nctx_overhead=0.0012\nsim_time={w + 500}\nwarmup={w}\nmean_think=7.152\nmean_service=0.048\ntimeout=10.0\nnum_runs=5\nservice_distribution=EXPONENTIAL\nthink_distribution=EXPONENTIAL\nuser_counts={users}\n")
            
            subprocess.run(['make'], check=True, capture_output=True)
            subprocess.run(['./web_sim'], check=True, capture_output=True)
            
            result_file = 'results/think_time_EXPONENTIAL/service_time_EXPONENTIAL/des_results.csv'
            if os.path.exists(result_file):
                df = pd.read_csv(result_file)
                if not df.empty:
                    rt = df.iloc[0]['Avg_RT']
                    results.append({'warmup': w, 'rt': rt})
                    print(f"Warmup: {w}, Avg RT: {rt:.4f}")

        df_res = pd.DataFrame(results)
        if not df_res.empty:
            plt.figure(figsize=(10, 6))
            plt.plot(df_res['warmup'], df_res['rt'], 'o-')
            plt.title(f'Avg Response Time vs Warmup period (Users={users})')
            plt.xlabel('Warmup Time (s)')
            plt.ylabel('Avg Response Time (s)')
            plt.grid(True)
            os.makedirs('plots', exist_ok=True)
            plt.savefig('plots/transient_analysis.png')
            print("Transient analysis plot saved to plots/transient_analysis.png")
    finally:
        # Restore original config
        if original_config:
            with open('config.txt', 'w') as f:
                f.write(original_config)

if __name__ == "__main__":
    # Run transient analysis at high load where it matters most
    run_single_simulation(users=200, warmup_vals=[0, 10, 20, 50, 100, 200, 500])
