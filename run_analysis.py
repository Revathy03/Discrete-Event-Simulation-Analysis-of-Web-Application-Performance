import os
import subprocess
import shutil
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

# --- CONFIGURATION TEMPLATE ---
BASE_CONFIG = """# Simulation Configuration
# Hardware
cores={cores}
threads_per_core={threads_per_core}
num_servers={num_servers}

# Timings (in seconds)
ctx_overhead={ctx_overhead}
sim_time=1000.0
warmup=100.0
mean_think={mean_think}
mean_service={mean_service}
timeout={timeout}
time_slice={time_slice}
max_queue_size={max_queue_size}

# Thermal/Load Balancing
load_balancer={load_balancer}
thermal_threshold={thermal_threshold}
throttle_factor={throttle_factor}

# Experiment Setup
num_runs=5
service_distribution=EXPONENTIAL
think_distribution=EXPONENTIAL
output_dir={output_dir}

# User counts for experiments
user_counts={user_counts}
"""

SCENARIOS = {
    "time_quantum": {
        "title": "Processor Sharing vs. Time Slicing Dynamics",
        "description": "Impact of context switching overhead on system response time.",
        "variants": {
            "quantum_0.002s": {"time_slice": 0.002},
            "quantum_0.010s": {"time_slice": 0.01},
            "quantum_0.050s": {"time_slice": 0.05},
            "quantum_0.200s": {"time_slice": 0.2},
            "quantum_0.500s": {"time_slice": 0.5},
            "quantum_1.0s": {"time_slice": 1.0}
        },
        "common": {"cores": 1, "threads_per_core": 1, "num_servers": 1, "ctx_overhead": 0.0012, "mean_think": 7.152, "mean_service": 0.048, "timeout": 10.0, "max_queue_size": -1, "load_balancer": "ROUND_ROBIN", "thermal_threshold": 100.0, "throttle_factor": 1.0, "user_counts": "10,50,100,200,300"},
        "technical_note": "Smaller quanta approach ideal Processor Sharing but increase overhead."
    },
    "buffer_limits": {
        "title": "Buffer Size Analysis",
        "description": "System behavior under finite queue capacity and load shedding.",
        "variants": {
            "buffer_10": {"max_queue_size": 10},
            "buffer_50": {"max_queue_size": 50},
            "buffer_inf": {"max_queue_size": -1}
        },
        "common": {"cores": 1, "threads_per_core": 1, "num_servers": 1, "ctx_overhead": 0.0012, "mean_think": 2.0, "mean_service": 0.048, "timeout": 10.0, "time_slice": 1.0, "load_balancer": "ROUND_ROBIN", "thermal_threshold": 100.0, "throttle_factor": 1.0, "user_counts": "10,50,100,200,300"},
        "technical_note": "Finite buffers stabilize response time at the cost of dropped requests."
    },
    "thermal_throttling": {
        "title": "Thermal-Induced Service Rate Degradation",
        "description": "Performance impact of CPU thermal protection and frequency scaling.",
        "variants": {
            "no_throttling": {"thermal_threshold": 100.0, "throttle_factor": 1.0},
            "heavy_throttle": {"thermal_threshold": 70.0, "throttle_factor": 0.5}
        },
        "common": {"cores": 1, "threads_per_core": 1, "num_servers": 1, "ctx_overhead": 0.0012, "mean_think": 7.152, "mean_service": 0.048, "timeout": 10.0, "time_slice": 1.0, "max_queue_size": -1, "load_balancer": "ROUND_ROBIN", "user_counts": "10,50,100,200,300"},
        "technical_note": "Throttling increases service time (D) to prevent overheating."
    },
    "thermal_load_balancing": {
        "title": "Thermal-Aware Dispatching Policy",
        "description": "Comparing Round-Robin vs. Thermal-Aware routing across 4 servers.",
        "variants": {
            "round_robin": {"load_balancer": "ROUND_ROBIN"},
            "thermal_aware": {"load_balancer": "THERMAL"}
        },
        "common": {"cores": 2, "threads_per_core": 1, "num_servers": 4, "ctx_overhead": 0.0012, "mean_think": 7.152, "mean_service": 0.048, "timeout": 10.0, "time_slice": 1.0, "max_queue_size": -1, "thermal_threshold": 75.0, "throttle_factor": 0.5, "user_counts": "10,50,100,200,400,600,800"},
        "technical_note": "Thermal routing balances load based on temperature, delaying the onset of throttling."
    },
    "thread_vs_cores": {
        "title": "Hardware Multithreading and Resource Scaling",
        "description": "Efficiency of SMT (Threads) vs. Physical Core scaling.",
        "variants": {
            "1_core_1_thread": {"cores": 1, "threads_per_core": 1},
            "1_core_2_threads": {"cores": 1, "threads_per_core": 2},
            "2_cores_1_thread": {"cores": 2, "threads_per_core": 1}
        },
        "common": {"num_servers": 1, "ctx_overhead": 0.0012, "mean_think": 7.152, "mean_service": 0.048, "timeout": 10.0, "time_slice": 1.0, "max_queue_size": -1, "load_balancer": "ROUND_ROBIN", "thermal_threshold": 100.0, "throttle_factor": 1.0, "user_counts": "10,50,100,200,300,400,500"},
        "technical_note": "Physical cores provide better scaling than logical SMT threads."
    },
    "think_time_impact": {
        "title": "Saturation Point Sensitivity to Arrival Intensity",
        "description": "How arrival rate (Think Time) affects the system saturation point (N*).",
        "variants": {
            "think_0.5s": {"mean_think": 0.5},
            "think_2.0s": {"mean_think": 2.0},
            "think_4.0s": {"mean_think": 4.0},
            "think_7.152s": {"mean_think": 7.152},
            "think_10.0s": {"mean_think": 10.0}
        },
        "common": {"cores": 1, "threads_per_core": 1, "num_servers": 1, "ctx_overhead": 0.0012, "mean_service": 0.048, "timeout": 10.0, "time_slice": 1.0, "max_queue_size": -1, "load_balancer": "ROUND_ROBIN", "thermal_threshold": 100.0, "throttle_factor": 1.0, "user_counts": "10,25,50,100,150,200,250,300"},
        "technical_note": "N* = (Z + D) / D. High think times defer saturation to higher user counts."
    },
    "sla_cliff": {
        "title": "SLA Violation and Verified Goodput Analysis",
        "description": "True Goodput vs Badput analysis at a fixed 0.5s SLA.",
        "variants": {
            "sla_fixed_0.5s": {"timeout": 0.5}
        },
        "common": {"cores": 1, "threads_per_core": 1, "num_servers": 1, "ctx_overhead": 0.0012, "mean_think": 7.152, "mean_service": 0.048, "time_slice": 1.0, "max_queue_size": -1, "load_balancer": "ROUND_ROBIN", "thermal_threshold": 100.0, "throttle_factor": 1.0, "user_counts": "10,50,100,150,180,200,220,250,300,350,400"},
        "technical_note": "Calculates True Goodput: P(RT < 0.5s) * Throughput. Shows the cliff where badput overtakes goodput."
    },
    "timeout_dynamics": {
        "title": "Client Timeout and Reneging Dynamics",
        "description": "Impact of client timeout on system throughput and goodput.",
        "variants": {
            "timeout_0.5s": {"timeout": 0.5},
            "timeout_2.0s": {"timeout": 2.0},
            "timeout_10.0s": {"timeout": 10.0}
        },
        "common": {"cores": 1, "threads_per_core": 1, "num_servers": 1, "ctx_overhead": 0.0012, "mean_think": 2.0, "mean_service": 0.048, "time_slice": 1.0, "max_queue_size": -1, "load_balancer": "ROUND_ROBIN", "thermal_threshold": 100.0, "throttle_factor": 1.0, "user_counts": "10,50,100,200,300"},
        "technical_note": "Aggressive timeouts can improve goodput by shedding long-running requests."
    },
    "thrashing_wall": {
        "title": "Context Switching Overhead & System Thrashing",
        "description": "Analysis of system behavior as context switching costs approach service time.",
        "variants": {
            "overhead_0.0012s": {"ctx_overhead": 0.0012},
            "overhead_0.005s": {"ctx_overhead": 0.005},
            "overhead_0.010s": {"ctx_overhead": 0.010},
            "overhead_0.020s": {"ctx_overhead": 0.020},
            "overhead_0.040s": {"ctx_overhead": 0.040}
        },
        "common": {"cores": 1, "threads_per_core": 1, "num_servers": 1, "mean_think": 7.152, "mean_service": 0.048, "timeout": 10.0, "time_slice": 1.0, "max_queue_size": -1, "load_balancer": "ROUND_ROBIN", "thermal_threshold": 100.0, "throttle_factor": 1.0, "user_counts": "10,50,100,150,200,250,300,400"},
        "technical_note": "High context overhead creates a performance wall where throughput collapses."
    },
    "flash_crowd": {
        "title": "Non-Stationary Flash Crowd Arrival Impact",
        "description": "Impact of sudden user spikes on response time stability.",
        "variants": {
            "gradual_load": {"mean_think": 7.152},
            "flash_crowd": {"mean_think": 1.0}
        },
        "common": {"cores": 1, "threads_per_core": 1, "num_servers": 1, "ctx_overhead": 0.0012, "mean_service": 0.048, "timeout": 10.0, "time_slice": 1.0, "max_queue_size": -1, "load_balancer": "ROUND_ROBIN", "thermal_threshold": 100.0, "throttle_factor": 1.0, "user_counts": "10,50,100,200,300"},
        "technical_note": "Flash crowds drastically shift the operating point towards saturation."
    },
    "core_efficiency": {
        "title": "Scale-Up (Super Core) vs. Scale-Out (Multi-Core)",
        "description": "Comparison of a single ultra-fast core vs. four standard cores with identical total throughput capacity.",
        "variants": {
            "super_core_0.012s": {"cores": 1, "mean_service": 0.012},
            "quad_standard_0.048s": {"cores": 4, "mean_service": 0.048}
        },
        "common": {"threads_per_core": 1, "num_servers": 1, "ctx_overhead": 0.0012, "mean_think": 7.152, "timeout": 10.0, "time_slice": 1.0, "max_queue_size": -1, "load_balancer": "ROUND_ROBIN", "thermal_threshold": 100.0, "throttle_factor": 1.0, "user_counts": "10,50,100,200,300,400,500"},
        "technical_note": "The Super Core wins at low load by finishing tasks 4x faster, while Multi-Cores catch up at high load via parallelism."
    }
}

# --- TOOLS ---

def load_csv(path):
    f = os.path.join(path, "think_time_EXPONENTIAL", "service_time_EXPONENTIAL", "des_results.csv")
    return pd.read_csv(f) if os.path.exists(f) else None

def get_label(metric):
    labels = {
        'Avg_RT': 'Avg Response Time (s)',
        'Throughput': 'Total Throughput (req/s)',
        'Goodput': 'Successful Goodput (req/s)',
        'DropRate': 'Request Drop Rate',
        'Users': 'Number of Users',
        'MaxTemp': 'Peak Temperature (°C)'
    }
    return labels.get(metric, metric)

def plot_with_annotations(q_id, q_dir, data):
    plt.style.use('seaborn-v0_8-muted')
    
    variants = sorted(data['variants'].keys())
    dfs = {v: load_csv(os.path.join(q_dir, "results", v.replace('=', '_').replace('.', 'p'))) for v in variants}
    if not any(df is not None for df in dfs.values()): return

    # Decide which metrics to plot based on scenario (Ensuring Side-by-Side consistency)
    metrics_to_plot = ['Avg_RT', 'Throughput']
    if q_id == "time_quantum":
        metrics_to_plot = ['Avg_RT', 'Throughput']
    elif q_id == "thermal_throttling":
        metrics_to_plot = ['Avg_RT', 'MaxTemp', 'Goodput']
    elif q_id == "thermal_load_balancing":
        metrics_to_plot = ['Avg_RT', 'MaxTemp']
    elif q_id == "buffer_limits":
        metrics_to_plot = ['Avg_RT', 'Goodput']
    elif q_id in ["sla_cliff", "timeout_dynamics"]:
        metrics_to_plot = ['TrueGoodput', 'TrueBadput']
    elif q_id == "think_time_impact":
        metrics_to_plot = ['Throughput', 'N_sat']
    elif q_id == "thrashing_wall":
        metrics_to_plot = ['Throughput', 'Avg_RT']
    elif q_id == "core_efficiency":
        metrics_to_plot = ['Avg_RT', 'Throughput']
        
    # Mapping for minimal, accurate titles
    var_map = {
        "time_quantum": "Time Quanta",
        "buffer_limits": "Buffer Sizes",
        "thermal_throttling": "Thermal Thresholds",
        "thermal_load_balancing": "Dispatching Policies",
        "thread_vs_cores": "Resource Types",
        "think_time_impact": "Think Times",
        "sla_cliff": "User Counts",
        "timeout_dynamics": "Client Timeouts",
        "thrashing_wall": "Context Switch Overheads",
        "flash_crowd": "Arrival Intensities",
        "core_efficiency": "Hardware Configurations"
    }
    var_name = var_map.get(q_id, "Parameters")

    fig, axes = plt.subplots(1, len(metrics_to_plot), figsize=(7*len(metrics_to_plot), 6))
    if len(metrics_to_plot) == 1: axes = [axes]
    
    for ax, metric in zip(axes, metrics_to_plot):
        display_metric = metric.replace('_', ' ').title()
        if metric == 'N_sat': display_metric = "Saturation Point (N*)"
        if metric == 'MaxTemp': display_metric = "Peak Temperature"
        
        ax.set_title(f"{display_metric} for varying {var_name}", fontweight='bold', fontsize=11)
        
        if metric == 'N_sat':
            # Specialized Plot: Saturation Point vs. Think Time
            z_vals = []
            n_sat_vals = []
            for v, df in dfs.items():
                if df is not None:
                    z = float(v.split('_')[1].replace('s', ''))
                    # Saturation where Utilization >= 0.95
                    sat_df = df[df['Utilization'] >= 0.95]
                    n_sat = sat_df.iloc[0]['Users'] if not sat_df.empty else df.iloc[-1]['Users']
                    z_vals.append(z)
                    n_sat_vals.append(n_sat)
            
            # Sort by Z
            sorted_indices = np.argsort(z_vals)
            z_vals = np.array(z_vals)[sorted_indices]
            n_sat_vals = np.array(n_sat_vals)[sorted_indices]
            
            ax.plot(z_vals, n_sat_vals, 's-', color='darkblue', linewidth=2, label='Simulated N*')
            D = data['common']['mean_service'] + data['common'].get('ctx_overhead', 0)
            z_range = np.linspace(min(z_vals), max(z_vals), 100)
            ax.plot(z_range, z_range/D + 1, 'r--', alpha=0.5, label=f'Theoretical (Z/{D:.3f} + 1)')
            ax.set_xlabel('Think Time (s)')
            ax.set_ylabel('N*')
            ax.grid(True, alpha=0.3)
            ax.legend()
        
        elif metric in ['TrueGoodput', 'TrueBadput']:
            # Specialized Calculation for SLA Cliff
            sla = 0.5
            for v, df in dfs.items():
                if df is not None:
                    # success_prob = 1 - e^(-SLA/Avg_RT)
                    success_prob = 1 - np.exp(-sla / df['Avg_RT'])
                    true_goodput = df['Throughput'] * success_prob
                    true_badput = df['Throughput'] - true_goodput
                    
                    if metric == 'TrueGoodput':
                        ax.plot(df['Users'], true_goodput, 'o-', color='green', linewidth=3, label='Verified Goodput (<0.5s)')
                    else:
                        ax.plot(df['Users'], true_badput, 's--', color='red', linewidth=2, label='Badput (>0.5s)')
                        # Mark crossover
                        crossover = df[true_badput > true_goodput]
                        if not crossover.empty:
                             x_val = crossover.iloc[0]['Users']
                             ax.axvline(x=x_val, color='black', linestyle='--', alpha=0.5)
                             ax.text(x_val + 5, true_badput.max()*0.5, f'Cliff: {x_val} Users', fontweight='bold', fontsize=9)
            
            ax.set_xlabel(get_label('Users'))
            ax.set_ylabel('Rate (req/s)')
            ax.grid(True, alpha=0.3)
            ax.legend()
            
        else:
            # Standard Line Plot
            # Use a diverse colormap to ensure distinct colors
            cmap = plt.cm.get_cmap('tab10')
            for i, (v, df) in enumerate(dfs.items()):
                if df is not None:
                    color = cmap(i % 10)
                    # Cleaner labels for the legend (Using Seconds)
                    lbl = v.replace('quantum_', 'Q=').replace('overhead_', 'O=').replace('_', ' ').title()
                    if 'Q=' in lbl or 'O=' in lbl: lbl = lbl.replace(' ', '')
                    ax.plot(df['Users'], df[metric], 'o-', color=color, markersize=4, linewidth=1.5, label=lbl)
            
            ax.set_xlabel(get_label('Users'))
            ax.set_ylabel(get_label(metric))
            ax.grid(True, alpha=0.3)
            ax.legend(fontsize=9)

    # Add important configuration in a small box at top (Dynamic, no N/A)
    common = data['common']
    priority_params = [
        ('mean_service', 'Mean Service'),
        ('ctx_overhead', 'Context Overhead'),
        ('mean_think', 'Mean Think'),
        ('time_slice', 'Time Slice'),
        ('timeout', 'Timeout'),
        ('max_queue_size', 'Buffer Limit'),
    ]
    
    config_items = []
    for key, label in priority_params:
        val = common.get(key)
        if val is not None:
            if key == 'max_queue_size' and val == -1:
                config_items.append(f"{label}: Infinite")
            elif val != -1:
                if isinstance(val, float):
                    config_items.append(f"{label}: {val:.3g}s")
                else:
                    config_items.append(f"{label}: {val}")
    
    # Add hardware
    config_items.append(f"Cores: {common.get('cores', 1)} | Servers: {common.get('num_servers', 1)}")
    
    config_str = "  |  ".join(config_items)
    fig.text(0.5, 0.95, config_str, ha='center', fontsize=9, fontweight='bold', 
             bbox=dict(boxstyle='round,pad=0.5', facecolor='white', alpha=0.9, edgecolor='lightgray'))

    plt.tight_layout(rect=[0, 0, 1, 0.93])
    plt.savefig(os.path.join(q_dir, "plot.png"), dpi=200)
    plt.close()

# --- MAIN EXECUTION ---

def main():
    output_base = "final_results/what_if_analysis"
    print(f"Starting Consolidated What-If Analysis (Results in {output_base})...")
    
    if os.path.exists(output_base): 
        shutil.rmtree(output_base)
    os.makedirs(output_base)

    for q_id, q_data in SCENARIOS.items():
        print(f" - Scenario: {q_data['title']}")
        q_dir = os.path.join(output_base, q_id)
        os.makedirs(q_dir, exist_ok=True)
        
        for v_name, v_params in q_data['variants'].items():
            v_dir = v_name.replace('=', '_').replace('.', 'p')
            out = os.path.join(q_dir, "results", v_dir)
            p = q_data['common'].copy()
            p.update(v_params)
            p['output_dir'] = out
            
            cfg_path = f"tmp_cfg_{q_id}_{v_dir}.txt"
            with open(cfg_path, "w") as f: f.write(BASE_CONFIG.format(**p))
            subprocess.run(["./web_sim", cfg_path], check=True, capture_output=True)
            if os.path.exists(cfg_path): os.remove(cfg_path)
        
        plot_with_annotations(q_id, q_dir, q_data)

    print(f"\nWhat-If Analysis complete. Results organized in {output_base}/")

if __name__ == "__main__":
    main()
