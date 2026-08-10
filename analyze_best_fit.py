import pandas as pd
import numpy as np
import os

def calculate_errors(measured_df, des_df):
    # Align by 'Users' count
    merged = pd.merge(measured_df[['Users', 'Response time']], 
                      des_df[['Users', 'Avg_RT']], 
                      on='Users')
    
    if merged.empty:
        return None
        
    mae = np.mean(np.abs(merged['Response time'] - merged['Avg_RT']))
    rmse = np.sqrt(np.mean((merged['Response time'] - merged['Avg_RT'])**2))
    mape = np.mean(np.abs((merged['Response time'] - merged['Avg_RT']) / merged['Response time'])) * 100
    
    return {'MAE': mae, 'RMSE': rmse, 'MAPE': mape}

def main():
    results_dir = "results"
    measured_csv = os.path.join(results_dir, "closed_load_measured.csv")
    
    if not os.path.exists(measured_csv):
        print(f"Measured data not found at {measured_csv}")
        return

    # Load measured data and clean up (remove empty rows/columns)
    df_measured = pd.read_csv(measured_csv)
    df_measured = df_measured[df_measured['Users'].notna()]
    df_measured['Users'] = df_measured['Users'].astype(int)

    analysis_results = []

    # Traverse nested directories
    for think_dir in os.listdir(results_dir):
        if think_dir.startswith("think_time_"):
            t_dist = think_dir.replace("think_time_", "")
            think_path = os.path.join(results_dir, think_dir)
            if not os.path.isdir(think_path):
                continue
                
            for service_dir in os.listdir(think_path):
                if service_dir.startswith("service_time_"):
                    s_dist = service_dir.replace("service_time_", "")
                    service_path = os.path.join(think_path, service_dir)
                    des_csv = os.path.join(service_path, "des_results.csv")
                    
                    if os.path.exists(des_csv):
                        df_des = pd.read_csv(des_csv)
                        errors = calculate_errors(df_measured, df_des)
                        if errors:
                            analysis_results.append({
                                'Think Dist': t_dist,
                                'Service Dist': s_dist,
                                **errors
                            })

    if not analysis_results:
        print("No simulation results found to analyze.")
        return

    results_df = pd.DataFrame(analysis_results)
    
    # Sort by RMSE (or MAE)
    results_df = results_df.sort_values(by='RMSE')

    print("\n--- Distribution Fit Analysis (Compared to Measured Data) ---")
    print(results_df.to_string(index=False))

    best_match = results_df.iloc[0]
    print(f"\nBest fitting combination: Think={best_match['Think Dist']}, Service={best_match['Service Dist']}")
    print(f"RMSE: {best_match['RMSE']:.4f}, MAE: {best_match['MAE']:.4f}, MAPE: {best_match['MAPE']:.2f}%")

if __name__ == "__main__":
    main()
