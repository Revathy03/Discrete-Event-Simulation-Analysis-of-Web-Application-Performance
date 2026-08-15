import pandas as pd
import os
import numpy as np


def build_throughput_comparison(results_dir="results", measured_csv="closed_load_measurement.csv", output_csv="throughput_comparison.csv"):
    """Build a single CSV with measured, MVA, and DES throughput values and their errors."""
    if not os.path.exists(measured_csv):
        raise FileNotFoundError(f"Measured CSV not found: {measured_csv}")

    df_measured = pd.read_csv(measured_csv)
    df_measured = df_measured[df_measured['Users'].notna()].copy()
    df_measured['Users'] = df_measured['Users'].astype(int)
    df_measured = df_measured[['Users', 'Throughput']].rename(columns={'Throughput': 'Measured_Throughput'})

    all_rows = []

    for think_dir in sorted(os.listdir(results_dir)):
        if not think_dir.startswith("think_time_"):
            continue
        think_name = think_dir.replace("think_time_", "")
        think_path = os.path.join(results_dir, think_dir)

        for service_dir in sorted(os.listdir(think_path)):
            if not service_dir.startswith("service_time_"):
                continue
            service_name = service_dir.replace("service_time_", "")
            dist_dir = os.path.join(think_path, service_dir)
            des_csv = os.path.join(dist_dir, "des_results.csv")
            mva_csv = os.path.join(dist_dir, "mva_results.csv")

            if not os.path.exists(des_csv) or not os.path.exists(mva_csv):
                continue

            df_des = pd.read_csv(des_csv)[['Users', 'Throughput']].rename(columns={'Throughput': 'DES_Throughput'})
            df_mva = pd.read_csv(mva_csv)[['Users', 'Throughput']].rename(columns={'Throughput': 'MVA_Throughput'})

            merged = df_measured.merge(df_des, on='Users', how='inner').merge(df_mva, on='Users', how='inner')
            if merged.empty:
                continue

            for _, row in merged.iterrows():
                measured_tp = float(row['Measured_Throughput'])
                des_tp = float(row['DES_Throughput'])
                mva_tp = float(row['MVA_Throughput'])

                des_abs_err = abs(des_tp - measured_tp)
                mva_abs_err = abs(mva_tp - measured_tp)

                des_pct_err = (des_abs_err / measured_tp) * 100 if measured_tp else 0.0
                mva_pct_err = (mva_abs_err / measured_tp) * 100 if measured_tp else 0.0

                all_rows.append({
                    'Think Time Dist': think_name,
                    'Service Time Dist': service_name,
                    'Users': int(row['Users']),
                    'Measured Throughput': measured_tp,
                    'MVA Throughput': mva_tp,
                    'Simulator Throughput': des_tp,
                    'MVA Absolute Error': mva_abs_err,
                    'MVA % Error': mva_pct_err,
                    'Simulator Absolute Error': des_abs_err,
                    'Simulator % Error': des_pct_err,
                    'MVA Accuracy %': 100.0 - mva_pct_err,
                    'Simulator Accuracy %': 100.0 - des_pct_err,
                })

    if not all_rows:
        raise ValueError(f"No throughput comparison rows found in {results_dir}.")

    df_out = pd.DataFrame(all_rows)
    df_out.to_csv(output_csv, index=False)
    return df_out


def summarize_throughput_accuracy(df):
    """Return the average percentage error for MVA and the simulator against measured throughput."""
    if df.empty:
        return {'MVA Accuracy': None, 'Simulator Accuracy': None}

    mva_avg_err = df['MVA % Error'].mean()
    sim_avg_err = df['Simulator % Error'].mean()

    return {
        'MVA Avg % Error': mva_avg_err,
        'Simulator Avg % Error': sim_avg_err,
        'MVA Avg Accuracy %': 100.0 - mva_avg_err,
        'Simulator Avg Accuracy %': 100.0 - sim_avg_err,
    }


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
    output_csv = "throughput_comparison.csv"

    combined = build_throughput_comparison(results_dir, measured_csv, output_csv)
    summary = summarize_throughput_accuracy(combined)

    print(f"\n--- Combined throughput comparison written to {output_csv} ---")
    print(combined.head(10).to_string(index=False))
    print(f"\n--- Throughput Accuracy Summary ---")
    print(f"MVA average percent error: {summary['MVA Avg % Error']:.2f}%")
    print(f"Simulator average percent error: {summary['Simulator Avg % Error']:.2f}%")
    print(f"MVA average accuracy: {summary['MVA Avg Accuracy %']:.2f}%")
    print(f"Simulator average accuracy: {summary['Simulator Avg Accuracy %']:.2f}%")

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
