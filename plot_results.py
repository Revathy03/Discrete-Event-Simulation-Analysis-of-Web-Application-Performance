import pandas as pd
import matplotlib.pyplot as plt
import os
import numpy as np

def load_config(filename="config.txt"):
    config = {
        'mean_think': 7.152,
        'mean_service': 0.048,
        'ctx_overhead': 0.0012,
        'user_counts': []
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
            
            if name == 'mean_think':
                config['mean_think'] = float(value)
            elif name == 'mean_service':
                config['mean_service'] = float(value)
            elif name == 'ctx_overhead':
                config['ctx_overhead'] = float(value)
            elif name == 'service_distribution':
                config['service_distribution'] = value.strip()
            elif name == 'think_distribution':
                config['think_distribution'] = value.strip()
    return config

def plot_combined_accuracy(results_dir, ranking_df, measured_csv, output_path):
    """
    Plots all 9 distribution combinations.
    Best matching distribution is darkened/solid.
    Others are dotted.
    """
    plt.figure(figsize=(14, 10), dpi=200) # Higher resolution
    
    # 1. Plot Measured Data
    if os.path.exists(measured_csv):
        df_measured = pd.read_csv(measured_csv)
        df_measured = df_measured[df_measured['Users'].notna()].copy()
        plt.plot(df_measured['Users'], df_measured['Response time'], 'ks-', linewidth=3, markersize=10, label='Measured (Experimental)', zorder=10)
    
    # 2. Plot all 9 Distributions
    cm = plt.get_cmap('tab10')
    
    for i in range(len(ranking_df)):
        best = ranking_df.iloc[i]
        t_dist = best['Think']
        s_dist = best['Service']
        dist_dir = os.path.join(results_dir, f"think_time_{t_dist}", f"service_time_{s_dist}")
        des_csv = os.path.join(dist_dir, "des_results.csv")
        
        if os.path.exists(des_csv):
            df_des = pd.read_csv(des_csv)
            label = f"DES (T:{t_dist}, S:{s_dist})"
            
            if i == 0:
                # Rank 1: Darkened and Solid
                plt.plot(df_des['Users'], df_des['Avg_RT'], 'o-', color=cm(i % 10), linewidth=4, alpha=0.9, label=f"BEST: {label}", zorder=5)
                # Add confidence intervals only for the best one to avoid clutter
                plt.fill_between(df_des['Users'], df_des['Avg_RT'] - df_des['CI_Half'], df_des['Avg_RT'] + df_des['CI_Half'], color=cm(i % 10), alpha=0.2)
            else:
                # Others: Dotted
                plt.plot(df_des['Users'], df_des['Avg_RT'], '.:', color=cm(i % 10), linewidth=1, alpha=0.6, label=label)

    plt.xlabel('Number of Users', fontsize=14)
    plt.ylabel('Response Time (s)', fontsize=14)
    plt.title('Main Experiment: All Distribution Combinations vs Measured Data', fontsize=16, fontweight='bold')
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.legend(loc='upper left', fontsize=9, ncol=2)
    
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    plt.tight_layout()
    plt.savefig(output_path)
    plt.close()
    print(f"Consolidated 9-distribution plot saved to {output_path}")

def plot_distribution_results(s_dist, t_dist, results_dir, config, save_dir=None):
    if save_dir is None:
        save_dir = os.path.join(results_dir, f"think_time_{t_dist}", f"service_time_{s_dist}")
    
    dist_dir = os.path.join(results_dir, f"think_time_{t_dist}", f"service_time_{s_dist}")
    des_csv = os.path.join(dist_dir, "des_results.csv")
    mva_csv = os.path.join(dist_dir, "mva_results.csv")
    measured_csv = "closed_load_measurement.csv"

    if not os.path.exists(des_csv):
        print(f"Skipping Service: {s_dist}, Think: {t_dist} as {des_csv} does not exist.")
        return

    df_des = pd.read_csv(des_csv)
    df_mva = pd.read_csv(mva_csv) if os.path.exists(mva_csv) else None
    df_measured = pd.read_csv(measured_csv) if os.path.exists(measured_csv) else None

    # Theoretical constants (for reference/fallback)
    Z_theo = config['mean_think']
    D_theo = config['mean_service'] + config['ctx_overhead']
    m_star_theo = (Z_theo + D_theo) / D_theo

    # --- REFINED Graphical M* Derivation ---
    # 1. Low-load baseline: Use the FIRST data point (lowest user count) as the horizontal asymptote
    # This ensures the tangent passes through the very first point.
    R_low = df_des.iloc[0]['Avg_RT']

    # 2. High-load trend: Use only points where M >= 170 (deep saturation)
    # This ensures the tangent passes through the high-load points accurately.
    high_load_df = df_des[df_des['Users'] >= 170]
    dist_name = f"Think: {t_dist}, Service: {s_dist}"
    if len(high_load_df) >= 2:
        # Use numpy.polyfit for linear regression (degree 1)
        z = np.polyfit(high_load_df['Users'], high_load_df['Avg_RT'], 1)
        slope, intercept = z[0], z[1]
        
        # Intersection: R_low = slope * M + intercept => M = (R_low - intercept) / slope
        m_star_graphical = (R_low - intercept) / slope
        print(f"[{dist_name}] Refined Graphical M*: {m_star_graphical:.2f} (Theoretical: {m_star_theo:.2f})")
    else:
        print(f"[{dist_name}] Not enough specific high-load points (M>=170) to derive M*. Falling back to any points with Util > 90%.")
        high_load_fallback = df_des[df_des['Utilization'] > 0.90]
        if len(high_load_fallback) >= 2:
             z = np.polyfit(high_load_fallback['Users'], high_load_fallback['Avg_RT'], 1)
             slope, intercept = z[0], z[1]
             m_star_graphical = (R_low - intercept) / slope
        else:
            m_star_graphical = m_star_theo
            slope = D_theo
            intercept = -Z_theo

    # Standard bounds for consistency
    max_users = df_des['Users'].max()
    max_tp = df_des['Throughput'].max()
    max_rt = df_des['Avg_RT'].max()
    if df_measured is not None:
        max_users = max(max_users, df_measured['Users'].max())
        max_tp = max(max_tp, df_measured['Throughput'].max())
        max_rt = max(max_rt, df_measured['Response time'].max())

    def save_plot(name):
        plt.tight_layout()
        plt.savefig(os.path.join(save_dir, f"{name}.png"), dpi=200)
        plt.close()

    def add_dist_note():
        # Add distribution note on the right side of the header
        text = f"Think Time: {t_dist}\nService Time: {s_dist}"
        plt.title(text, loc='right', fontsize=8, color='gray', style='italic')

    # 1. Server CPU Utilization vs Throughput
    plt.figure(figsize=(12, 7))
    if df_measured is not None:
        df_measured_valid = df_measured.dropna(subset=['Throughput', 'Server CPU Utilizaiton %'])
        plt.plot(df_measured_valid['Throughput'], df_measured_valid['Server CPU Utilizaiton %'], 'k:.', linewidth=2, label='Measured (Experimental)', zorder=10)
    
    if df_mva is not None:
        plt.plot(df_mva['Throughput'], df_mva['Utilization'] * 100, 'gx--', linewidth=3, label='MVA Model', zorder=8)

    plt.plot(df_des['Throughput'], df_des['Utilization'] * 100, 'b-s', linewidth=2, label='DES Simulation', zorder=5)
    
    plt.xlabel('Throughput (req/s)')
    plt.ylabel('Server CPU Utilization (%)')
    plt.title('Server CPU Utilization vs Throughput (Comparison)', loc='left', fontweight='bold')
    add_dist_note()
    plt.xlim(0, max_tp * 1.1)
    plt.ylim(0, 105)
    plt.grid(True, linestyle='--', alpha=0.5)
    plt.legend()
    save_plot('util_vs_throughput')

    # 2. CPU Utilization % vs Number of Users
    plt.figure(figsize=(12, 7))
    if df_measured is not None:
        df_measured_valid = df_measured.dropna(subset=['Users', 'Server CPU Utilizaiton %'])
        plt.plot(df_measured_valid['Users'], df_measured_valid['Server CPU Utilizaiton %'], 'k:.', linewidth=2, label='Measured (Experimental)', zorder=10)
    
    if df_mva is not None:
        plt.plot(df_mva['Users'], df_mva['Utilization'] * 100, 'gx--', linewidth=3, label='MVA Model', zorder=8)

    plt.plot(df_des['Users'], df_des['Utilization'] * 100, 'b-s', linewidth=2, label='DES Simulation', zorder=5)
    
    plt.xlabel('Number of Users')
    plt.ylabel('Server CPU Utilization (%)')
    plt.title('Server CPU Utilization vs Number of Users (Comparison)', loc='left', fontweight='bold')
    add_dist_note()
    plt.xlim(0, max_users * 1.05)
    plt.ylim(0, 105)
    plt.grid(True, linestyle='--', alpha=0.5)
    plt.legend()
    save_plot('util_vs_users')

    # 3. Fraction of Requests dropped vs Number of Users
    plt.figure(figsize=(12, 7))
    if df_measured is not None:
        df_measured_valid = df_measured.dropna(subset=['Users', 'Drop Rate'])
        plt.plot(df_measured_valid['Users'], df_measured_valid['Drop Rate'], 'k:.', linewidth=2, label='Measured (Experimental)', zorder=10)
        
    plt.plot(df_des['Users'], df_des['DropRate'], 'r-s', linewidth=2, label='DES Simulation', zorder=5)
    
    plt.xlabel('Number of Users')
    plt.ylabel('Drop Rate')
    plt.title('Request Drop Rate vs Number of Users (Comparison)', loc='left', fontweight='bold')
    add_dist_note()
    plt.xlim(0, max_users * 1.05)
    plt.ylim(0, 0.05)
    plt.grid(True, linestyle='--', alpha=0.5)
    plt.legend()
    save_plot('drop_rate_vs_users')

    # 4. Response Time vs Users (with REFINED GRAPHICAL tangents and M*)
    plt.figure(figsize=(12, 7))
    plt.plot(df_des['Users'], df_des['Avg_RT'], 'b-s', linewidth=2, label='DES Simulation', zorder=5)
    
    users_range = np.linspace(0, max_users * 1.1, 200)
    
    # Plot Graphical Tangents
    plt.axhline(y=R_low, color='green', linestyle='--', label=f'Low Load (R_low={R_low:.4f}s)', alpha=0.6)
    
    high_load_line = slope * users_range + intercept
    # Only plot if it's reasonably high
    plt.plot(users_range[high_load_line > 0], high_load_line[high_load_line > 0], 
             color='orange', linestyle='--', label=f'High Load (slope={slope:.4f})', alpha=0.6)
    
    # Intersection Point
    plt.axvline(x=m_star_graphical, color='purple', linestyle=':', label=f'M* (Graphical) = {m_star_graphical:.2f}')
    
    # Annotate M* with an arrow
    plt.annotate(f'Derived M* = {m_star_graphical:.2f}', 
                 xy=(m_star_graphical, R_low), 
                 xytext=(m_star_graphical + 20, R_low + 0.5),
                 arrowprops=dict(facecolor='black', shrink=0.05, width=1, headwidth=8),
                 fontsize=10, fontweight='bold')
 
    plt.xlabel('Number of Users')
    plt.ylabel('Response Time (s)')
    plt.title('Response Time vs Number of Users (Graphical Analysis)', loc='left', fontweight='bold')
    add_dist_note()
    plt.ylim(0, max_rt * 1.5)
    plt.xlim(0, max_users * 1.05)
    plt.legend(loc='upper left')
    plt.grid(True, linestyle='--', alpha=0.5)
    save_plot('response_time_vs_users')

    # 5. Throughput, Goodput, Badput vs Number of Users
    plt.figure(figsize=(12, 7))
    if df_measured is not None:
        df_measured_valid = df_measured.dropna(subset=['Users', 'Throughput'])
        plt.plot(df_measured_valid['Users'], df_measured_valid['Throughput'], 'k:.', linewidth=2, label='Measured (Experimental)', zorder=10)
    
    if df_mva is not None:
        plt.plot(df_mva['Users'], df_mva['Throughput'], 'gx--', linewidth=3, label='MVA Model', zorder=8)

    plt.plot(df_des['Users'], df_des['Throughput'], 'b-s', linewidth=2, label='DES Throughput', zorder=5)
    plt.plot(df_des['Users'], df_des['Goodput'], 'c-^', linewidth=1.5, label='DES Goodput', alpha=0.7)
    plt.plot(df_des['Users'], df_des['Badput'], 'm-v', linewidth=1.5, label='DES Badput', alpha=0.7)
    
    plt.xlabel('Number of Users')
    plt.ylabel('Rate (req/s)')
    plt.title('Throughput Metrics: Multi-Model Comparison', loc='left', fontweight='bold')
    add_dist_note()
    plt.xlim(0, max_users * 1.05)
    plt.legend(loc='upper left', fontsize=9)
    plt.grid(True, linestyle='--', alpha=0.5)
    save_plot('throughput_metrics_vs_users')

    # 6. Comparison with measured and MVA (Response Time)
    plt.figure(figsize=(12, 7))
    if df_measured is not None:
        df_measured_valid = df_measured[df_measured['Users'].notna()]
        plt.plot(df_measured_valid['Users'], df_measured_valid['Response time'], 'k:.', linewidth=2, markersize=8, label='Measured (Experimental)', zorder=10)
    
    if df_mva is not None:
        plt.plot(df_mva['Users'], df_mva['Response Time'], 'gx--', linewidth=3, markersize=8, label='MVA Model', zorder=8)

    plt.plot(df_des['Users'], df_des['Avg_RT'], 'b-s', linewidth=2, label='DES Mean Response Time', zorder=5)
    
    plt.xlabel('Number of Users', fontsize=12)
    plt.ylabel('Response Time (s)', fontsize=12)
    plt.title('Response Time Comparison: DES vs MVA vs Measured', loc='left', fontweight='bold')
    add_dist_note()
    plt.xlim(0, max_users * 1.05)
    plt.ylim(0, max_rt * 1.2)
    plt.legend(loc='upper left')
    plt.grid(True, linestyle='--', alpha=0.5)
    save_plot('comparison_response_time')

    # 7. Comparison Throughput
    plt.figure(figsize=(12, 7))
    if df_measured is not None:
        df_measured_valid = df_measured[df_measured['Users'].notna()]
        plt.plot(df_measured_valid['Users'], df_measured_valid['Throughput'], 'k:.', linewidth=2, markersize=8, label='Measured (Experimental)', zorder=10)
    
    if df_mva is not None:
        plt.plot(df_mva['Users'], df_mva['Throughput'], 'gx--', linewidth=3, markersize=8, label='MVA Model', zorder=8)

    plt.plot(df_des['Users'], df_des['Throughput'], 'b-s', linewidth=2, label='DES Throughput', zorder=5)
    
    plt.xlabel('Number of Users', fontsize=12)
    plt.ylabel('Throughput (req/s)', fontsize=12)
    plt.title('Throughput Comparison: DES vs MVA vs Measured', loc='left', fontweight='bold')
    add_dist_note()
    plt.xlim(0, max_users * 1.05)
    plt.legend(loc='upper left')
    plt.grid(True, linestyle='--', alpha=0.5)
    save_plot('comparison_throughput')

    # 8. Comparison Utilization
    plt.figure(figsize=(12, 7))
    if df_measured is not None:
        df_measured_valid = df_measured[df_measured['Users'].notna()]
        plt.plot(df_measured_valid['Users'], df_measured_valid['Server CPU Utilizaiton %'], 'k:.', linewidth=2, markersize=8, label='Measured (Experimental)', zorder=10)
    
    if df_mva is not None:
        plt.plot(df_mva['Users'], df_mva['Utilization'] * 100, 'gx--', linewidth=3, markersize=8, label='MVA Model', zorder=8)

    plt.plot(df_des['Users'], df_des['Utilization'] * 100, 'b-s', linewidth=2, label='DES Utilization', zorder=5)
    
    plt.xlabel('Number of Users', fontsize=12)
    plt.ylabel('CPU Utilization (%)', fontsize=12)
    plt.title('Utilization Comparison: DES vs MVA vs Measured', loc='left', fontweight='bold')
    add_dist_note()
    plt.xlim(0, max_users * 1.05)
    plt.ylim(0, 105)
    plt.legend(loc='upper left')
    plt.grid(True, linestyle='--', alpha=0.5)
    save_plot('comparison_utilization')

    # 9. Comparison Drop Rate
    plt.figure(figsize=(12, 7))
    if df_measured is not None:
        df_measured_valid = df_measured[df_measured['Users'].notna()]
        plt.plot(df_measured_valid['Users'], df_measured_valid['Drop Rate'], 'k:.', linewidth=2, label='Measured (Experimental)', zorder=10)
        
    plt.plot(df_des['Users'], df_des['DropRate'], 'r-s', linewidth=2, label='DES Simulation', zorder=5)
    
    plt.xlabel('Number of Users', fontsize=12)
    plt.ylabel('Drop Rate')
    plt.title('Request Drop Rate Comparison: DES vs Measured', loc='left', fontweight='bold')
    add_dist_note()
    plt.xlim(0, max_users * 1.05)
    plt.ylim(0, 0.05)
    plt.legend(loc='upper left')
    plt.grid(True, linestyle='--', alpha=0.5)
    save_plot('comparison_droprate')

    # 10. Response Time vs Throughput (Comparison)
    plt.figure(figsize=(12, 7))
    if df_measured is not None:
        df_measured_valid = df_measured.dropna(subset=['Throughput', 'Response time'])
        plt.plot(df_measured_valid['Throughput'], df_measured_valid['Response time'], 'k:.', linewidth=2, label='Measured (Experimental)', zorder=10)
    
    if df_mva is not None:
        plt.plot(df_mva['Throughput'], df_mva['Response Time'], 'gx--', linewidth=3, label='MVA Model', zorder=8)

    plt.plot(df_des['Throughput'], df_des['Avg_RT'], 'b-s', linewidth=2, label='DES Simulation', zorder=5)
    
    plt.xlabel('Throughput (req/s)')
    plt.ylabel('Response Time (s)')
    plt.title('Response Time vs Throughput (Comparison)', loc='left', fontweight='bold')
    add_dist_note()
    plt.xlim(0, max_tp * 1.1)
    plt.ylim(0, max_rt * 1.2)
    plt.legend(loc='upper left')
    plt.grid(True, linestyle='--', alpha=0.5)
    save_plot('rt_vs_throughput')

    # 11. Response Time Comparison vs Throughput (DES, MVA, Measured)
    plt.figure(figsize=(12, 7))
    if df_measured is not None:
        df_measured_valid = df_measured.dropna(subset=['Throughput', 'Response time'])
        plt.plot(df_measured_valid['Throughput'], df_measured_valid['Response time'], 'k:.', linewidth=2, markersize=8, label='Measured (Experimental)', zorder=10)
    
    if df_mva is not None:
        plt.plot(df_mva['Throughput'], df_mva['Response Time'], 'gx--', linewidth=3, markersize=8, label='MVA Model', zorder=8)

    plt.plot(df_des['Throughput'], df_des['Avg_RT'], 'b-s', linewidth=2, label='DES Mean RT', zorder=5)
    
    plt.xlabel('Throughput (req/s)', fontsize=12)
    plt.ylabel('Response Time (s)', fontsize=12)
    plt.title('RT vs Throughput Comparison: DES vs MVA vs Measured', loc='left', fontweight='bold')
    add_dist_note()
    plt.xlim(0, max_tp * 1.1)
    plt.ylim(0, max_rt * 1.2)
    plt.legend(loc='upper left')
    plt.grid(True, linestyle='--', alpha=0.5)
    save_plot('comparison_rt_vs_throughput')

    # 12. Clean Response Time vs Users (DES with Shaded CI only)
    plt.figure(figsize=(12, 7))
    plt.plot(df_des['Users'], df_des['Avg_RT'], 'b-s', linewidth=2, label='DES Mean Response Time', zorder=5)
    plt.fill_between(df_des['Users'], 
                    df_des['Avg_RT'] - df_des['CI_Half'], 
                    df_des['Avg_RT'] + df_des['CI_Half'], 
                    color='blue', alpha=0.15, label='95% Confidence Interval', zorder=4)
    
    plt.xlabel('Number of Users', fontsize=12)
    plt.ylabel('Response Time (s)', fontsize=12)
    plt.title('DES Response Time with Confidence Interval', loc='left', fontweight='bold')
    add_dist_note()
    plt.xlim(0, max_users * 1.05)
    plt.ylim(0, max_rt * 1.2)
    plt.legend(loc='upper left')
    plt.grid(True, linestyle='--', alpha=0.5)
    save_plot('rt_vs_users_shaded_ci')

def main():
    import compare_accuracy
    results_dir = "results"
    measured_csv = "closed_load_measurement.csv"
    output_dir = "final_results/main_experiment"
    config = load_config()
    
    # Get rankings to find best distribution
    rankings = compare_accuracy.get_rankings(results_dir, measured_csv)
    
    if 'measured' in rankings:
        ranking_df = rankings['measured']
        print("Generating consolidated accuracy plot for 9 distributions...")
        plot_combined_accuracy(results_dir, ranking_df, measured_csv, 
                               os.path.join(output_dir, "all_distributions_comparison.png"))
        
        # Now generate ALL plots for the BEST distribution
        best = ranking_df.iloc[0]
        t_best = best['Think']
        s_best = best['Service']
        print(f"Generating detailed plots for the BEST distribution (T:{t_best}, S:{s_best})...")
        plot_distribution_results(s_best, t_best, results_dir, config, save_dir=output_dir)
    else:
        print("No measured data found for consolidated plot.")

if __name__ == "__main__":
    main()
