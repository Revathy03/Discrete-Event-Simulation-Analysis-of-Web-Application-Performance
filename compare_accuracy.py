import pandas as pd
import os
import numpy as np

def calculate_error(results_dir, reference_type='measured', reference_csv=None):
    """
    Calculates accuracy metrics between DES results and a reference (Measured or MVA).
    reference_type: 'measured' or 'mva'
    """
    if reference_type == 'measured':
        df_ref_total = pd.read_csv(reference_csv)
        df_ref_total = df_ref_total[df_ref_total['Users'].notna()].copy()
        df_ref_total['Users'] = df_ref_total['Users'].astype(int)
        ref_rt_col = 'Response time'
        ref_tp_col = 'Throughput'
    
    comparisons = []
    
    for think_dir in os.listdir(results_dir):
        if think_dir.startswith("think_time_"):
            t_dist = think_dir.replace("think_time_", "")
            think_path = os.path.join(results_dir, think_dir)
            
            for service_dir in os.listdir(think_path):
                if service_dir.startswith("service_time_"):
                    s_dist = service_dir.replace("service_time_", "")
                    dist_dir = os.path.join(think_path, service_dir)
                    des_csv = os.path.join(dist_dir, "des_results.csv")
                    
                    if not os.path.exists(des_csv):
                        continue
                        
                    df_des = pd.read_csv(des_csv)
                    
                    if reference_type == 'mva':
                        mva_csv = os.path.join(dist_dir, "mva_results.csv")
                        if not os.path.exists(mva_csv):
                            continue
                        df_ref = pd.read_csv(mva_csv)
                        ref_rt_col = 'Response Time'
                        ref_tp_col = 'Throughput'
                    else:
                        df_ref = df_ref_total
                    
                    # Merge on Users to compare same data points
                    merged = pd.merge(df_des, df_ref, on='Users')
                    
                    if merged.empty:
                        continue
                    
                    # Handling column names from merge (Throughput_x, Throughput_y or Response Time)
                    # For DES: Avg_RT, Throughput (or Throughput_x if merged)
                    # For Reference: ref_rt_col, ref_tp_col (or ref_tp_col + '_y' if merged)
                    
                    tp_des_col = 'Throughput_x' if 'Throughput_x' in merged.columns else 'Throughput'
                    tp_ref_col = (ref_tp_col + '_y') if (ref_tp_col + '_y') in merged.columns else ref_tp_col
                    
                    # Calculate Normalized RMSE for Response Time
                    rt_diff = (merged['Avg_RT'] - merged[ref_rt_col])
                    rt_rmse = np.sqrt(np.mean(rt_diff**2))
                    rt_nrmse = rt_rmse / merged[ref_rt_col].mean()
                    
                    # Calculate Normalized RMSE for Throughput
                    tp_diff = (merged[tp_des_col] - merged[tp_ref_col])
                    tp_rmse = np.sqrt(np.mean(tp_diff**2))
                    tp_nrmse = tp_rmse / merged[tp_ref_col].mean()
                    
                    comparisons.append({
                        'Think': t_dist,
                        'Service': s_dist,
                        'RT_RMSE': rt_rmse,
                        'TP_RMSE': tp_rmse,
                        'RT_NRMSE': rt_nrmse,
                        'TP_NRMSE': tp_nrmse,
                        'Score': rt_nrmse + tp_nrmse # Normalized aggregate
                    })
    
    if not comparisons:
        return pd.DataFrame()
        
    return pd.DataFrame(comparisons).sort_values(by='Score')

def get_rankings(results_dir="results", measured_csv="closed_load_measurement.csv"):
    """Returns rankings against measured and MVA data."""
    rankings = {}
    
    if os.path.exists(measured_csv):
        ranking_measured = calculate_error(results_dir, reference_type='measured', reference_csv=measured_csv)
        if not ranking_measured.empty:
            rankings['measured'] = ranking_measured
            
    ranking_mva = calculate_error(results_dir, reference_type='mva')
    if not ranking_mva.empty:
        rankings['mva'] = ranking_mva
        
    return rankings

if __name__ == "__main__":
    results_dir = "results"
    measured_csv = "closed_load_measurement.csv"
    
    rankings = get_rankings(results_dir, measured_csv)
    
    if 'measured' in rankings:
        print("\n--- DES vs MEASURED Accuracy Ranking ---")
        print(rankings['measured'].to_string(index=False))
        
        print("\n--- Best Measured Combinations ---")
        for i in range(min(3, len(rankings['measured']))):
            best = rankings['measured'].iloc[i]
            print(f"Rank {i+1}: Think={best['Think']}, Service={best['Service']} (Score: {best['Score']:.4f})")
    
    if 'mva' in rankings:
        print("\n--- DES vs MVA Accuracy Ranking ---")
        print(rankings['mva'].to_string(index=False))
