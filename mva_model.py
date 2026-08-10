
import pandas as pd
import numpy as np
import os

def run_mva(user_counts, mean_think, mean_service, ctx_overhead):
    """
    Mean Value Analysis (MVA) for a Closed Jackson Network.
    M: number of users
    Z: mean think time
    D: total service demand (per visit service time * visits)
    In our case, we have 1 core (visits=1) and service time includes context switch overhead.
    """
    Z = mean_think
    D = mean_service + ctx_overhead
    
    results = []
    
    # Ni(0) = 0
    N_prev = 0
    
    # We iterate up to the maximum user count requested
    max_users = max(user_counts)
    
    # Store results for all M from 1 to max_users to maintain recursion
    mva_data = {}
    
    for M in range(1, max_users + 1):
        # 1. Response time at node: Ri(M) = (Ni(M-1) + 1) * D
        R = (N_prev + 1) * D
        
        # 2. System throughput: Lambda = M / (Z + R)
        throughput = M / (Z + R)
        
        # 3. Average number of users at node: Ni(M) = Lambda * R
        N = throughput * R
        
        mva_data[M] = {
            'Users': M,
            'Response Time': R,
            'Throughput': throughput,
            'Utilization': throughput * D
        }
        
        # Update N_prev for next iteration
        N_prev = N
        
    # Filter for the user counts we actually care about
    filtered_results = [mva_data[u] for u in user_counts if u in mva_data]
    return pd.DataFrame(filtered_results)

def load_config(filename):
    config = {
        'cores': 1,
        'ctx_overhead': 0.0012,
        'mean_think': 7.152,
        'mean_service': 0.048,
        'service_distribution': 'EXPONENTIAL',
        'think_distribution': 'EXPONENTIAL',
        'user_counts': [10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 110, 120, 130, 140, 150, 160, 170, 180, 190, 200, 210, 220, 230]
    }
    if not os.path.exists(filename):
        return config
    
    with open(filename, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if '=' not in line:
                continue
            name, value = line.split('=', 1)
            name = name.strip()
            value = value.strip()
            
            if name == 'cores':
                config['cores'] = int(value)
            elif name == 'ctx_overhead':
                config['ctx_overhead'] = float(value)
            elif name == 'mean_think':
                config['mean_think'] = float(value)
            elif name == 'mean_service':
                config['mean_service'] = float(value)
            elif name == 'service_distribution':
                config['service_distribution'] = value
            elif name == 'think_distribution':
                config['think_distribution'] = value
            elif name == 'user_counts':
                config['user_counts'] = [int(x) for x in value.split(',')]
    return config

if __name__ == "__main__":
    import sys
    config_file = "config.txt"
    if len(sys.argv) > 1:
        config_file = sys.argv[1]
    
    config = load_config(config_file)
    
    # In MVA, for 1 core, service demand includes context switch overhead.
    # If multiple cores, MVA for multiserver is different, but keeping it simple for 1 core.
    df_mva = run_mva(
        config['user_counts'], 
        config['mean_think'], 
        config['mean_service'], 
        config['ctx_overhead']
    )
    
    output_dir = f"results/think_time_{config['think_distribution']}/service_time_{config['service_distribution']}"
    os.makedirs(output_dir, exist_ok=True)
    output_path = f"{output_dir}/mva_results.csv"
    
    df_mva.to_csv(output_path, index=False)
    print(f"MVA results saved to {output_path}")
    print(df_mva.head())
