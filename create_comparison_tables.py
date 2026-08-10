import os
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib as mpl

mpl.rcParams['mathtext.fontset'] = 'dejavusans'
mpl.rcParams['font.family'] = 'sans-serif'

def generate_table_image(df, title_str, output_path):
    fig = plt.figure(figsize=(14, 8))
    # Utilize space: left, bottom, width, height (leave more room at top for title)
    ax = fig.add_axes([0.05, 0.05, 0.9, 0.82])
    ax.axis('off')
    
    # Title centered at the top of the figure
    fig.text(0.5, 0.94, title_str, fontsize=24, ha='center', va='center')
    
    df_fmt = df.copy()
    for col in df_fmt.columns:
        if df_fmt[col].dtype == 'float64':
            df_fmt[col] = df_fmt[col].apply(lambda x: f"{x:.4f}" if pd.notnull(x) else "")
        else:
            df_fmt[col] = df_fmt[col].apply(lambda x: str(int(x)) if pd.notnull(x) and isinstance(x, (float, int)) else str(x))
            
    # Prepare header rows
    # Row 0: Category headers
    # Row 1: Method headers
    header0 = ['Users', 'Response Time', '', '', 'Throughput', '', '', 'Utilization', '', '']
    header1 = ['', 'Measured', 'MVA', 'DES', 'Measured', 'MVA', 'DES', 'Measured', 'MVA', 'DES']
    
    cell_text = [header1] + df_fmt.values.tolist()
    
    # Create table with header1 and data
    table = ax.table(cellText=cell_text, colLabels=header0, cellLoc='center', loc='center', bbox=[0, 0, 1, 1])
    table.auto_set_font_size(False)
    table.set_fontsize(11) # Reduced font size for better fit
    
    cells = table.get_celld()
    
    # Customize header cells
    for i in range(len(header0)):
        # Row 0 is colLabels (header0)
        cell = cells[(0, i)]
        cell.set_text_props(weight='bold', fontsize=13)
        cell.set_facecolor('#d3d3d3')
        
        # Row 1 of table is header1 (from cell_text[0])
        cell1 = cells[(1, i)]
        cell1.set_text_props(weight='bold', fontsize=11)
        # Consistent color for Users column, lighter for others
        if i == 0:
            cell1.set_facecolor('#d3d3d3')
        else:
            cell1.set_facecolor('#e3e3e3')

    # Response Time (1, 2, 3), Throughput (4, 5, 6), Utilization (7, 8, 9)
    merge_groups = [(1, 2, 3), (4, 5, 6), (7, 8, 9)]
    for group in merge_groups:
        main_col = group[0]
        for col_idx in group:
            cell = cells[(0, col_idx)]
            if col_idx != main_col:
                cell.get_text().set_text("")
            
            # Robust boundary setting to avoid overlapping borders
            if col_idx == main_col:
                cell.visible_edges = 'TBL' # Visible: Top, Bottom, Left
            elif col_idx == group[-1]:
                cell.visible_edges = 'TBR' # Visible: Top, Bottom, Right
            else:
                cell.visible_edges = 'TB'  # Visible: Top, Bottom
    
    # Merge 'Users' vertically between header0 and header1
    cells[(0, 0)].get_text().set_text("Users")
    cells[(0, 0)].visible_edges = 'LRT' # Left, Right, Top
    cells[(1, 0)].get_text().set_text("")
    cells[(1, 0)].visible_edges = 'LRB' # Left, Right, Bottom
    
    # Color coding for data rows
    for r in range(1, len(cell_text)): # Data starts at index 1 in cell_text, which is row r+1 in table
        for c in range(len(header0)):
            cell = cells[(r + 1, c)]
            col_tuple = df.columns[c]
            if len(col_tuple) > 1:
                method = col_tuple[1]
                if method == 'Measured':
                    cell.set_facecolor('#FFDAB9')
                elif method == 'MVA':
                    cell.set_facecolor('#ADD8E6')
                elif method == 'DES':
                    cell.set_facecolor('#90EE90')
                    
    plt.savefig(output_path, dpi=75)
    plt.close(fig)

def main():
    base_dir = "results"
    output_dir = os.path.join(base_dir, "comparison_tables")
    os.makedirs(output_dir, exist_ok=True)
    
    measured_file = os.path.join(base_dir, "closed_load_measured.csv")
    if os.path.exists(measured_file):
        df_measured = pd.read_csv(measured_file)
        df_measured = df_measured.dropna(subset=['Users'])
        df_measured = df_measured[['Users', 'Response time', 'Throughput', 'Server CPU Utilizaiton %']].copy()
        df_measured.rename(columns={
            'Response time': 'Response Time', 
            'Server CPU Utilizaiton %': 'Utilization'
        }, inplace=True)
        df_measured['Utilization'] = df_measured['Utilization'] / 100.0
    else:
        df_measured = pd.DataFrame(columns=['Users', 'Response Time', 'Throughput', 'Utilization'])

    think_times = ["CONSTANT", "EXPONENTIAL", "UNIFORM"]
    service_times = ["CONSTANT", "EXPONENTIAL", "UNIFORM"]

    columns_order = [
         ('Users', ''),
         ('Response Time', 'Measured'), ('Response Time', 'MVA'), ('Response Time', 'DES'),
         ('Throughput', 'Measured'), ('Throughput', 'MVA'), ('Throughput', 'DES'),
         ('Utilization', 'Measured'), ('Utilization', 'MVA'), ('Utilization', 'DES')
    ]

    output_file = os.path.join(output_dir, "all_comparisons.xlsx")
    with pd.ExcelWriter(output_file, engine='xlsxwriter') as writer:
        workbook = writer.book
        format_measured = workbook.add_format({'bg_color': '#FFDAB9'})
        format_mva = workbook.add_format({'bg_color': '#ADD8E6'})
        format_des = workbook.add_format({'bg_color': '#90EE90'})

        for tt in think_times:
            for st in service_times:
                pair_dir = os.path.join(base_dir, f"think_time_{tt}", f"service_time_{st}")
                if not os.path.exists(pair_dir):
                    print(f"Directory not found: {pair_dir}")
                    continue

                mva_file = os.path.join(pair_dir, "mva_results.csv")
                des_file = os.path.join(pair_dir, "des_results.csv")
                
                df_mva = pd.DataFrame(columns=['Users', 'Response Time', 'Throughput', 'Utilization'])
                if os.path.exists(mva_file):
                    df_mva_raw = pd.read_csv(mva_file)
                    if 'Response Time' in df_mva_raw.columns:
                        df_mva = df_mva_raw[['Users', 'Response Time', 'Throughput', 'Utilization']]

                df_des = pd.DataFrame(columns=['Users', 'Avg_RT', 'Throughput', 'Utilization'])
                if os.path.exists(des_file):
                    df_des_raw = pd.read_csv(des_file)
                    if 'Avg_RT' in df_des_raw.columns:
                        df_des = df_des_raw[['Users', 'Avg_RT', 'Throughput', 'Utilization']].rename(columns={'Avg_RT': 'Response Time'})

                users = set()
                users.update(df_measured['Users'].dropna().astype(int).tolist())
                users.update(df_mva['Users'].dropna().astype(int).tolist())
                users.update(df_des['Users'].dropna().astype(int).tolist())
                
                if not users:
                    continue
                    
                merged_data = []
                for u in sorted(list(users)):
                    row = {'Users': u}
                    meas_row = df_measured[df_measured['Users'] == u]
                    row[('Response Time', 'Measured')] = meas_row['Response Time'].values[0] if not meas_row.empty else None
                    row[('Throughput', 'Measured')] = meas_row['Throughput'].values[0] if not meas_row.empty else None
                    row[('Utilization', 'Measured')] = meas_row['Utilization'].values[0] if not meas_row.empty else None
                    
                    mva_row = df_mva[df_mva['Users'] == u]
                    row[('Response Time', 'MVA')] = mva_row['Response Time'].values[0] if not mva_row.empty else None
                    row[('Throughput', 'MVA')] = mva_row['Throughput'].values[0] if not mva_row.empty else None
                    row[('Utilization', 'MVA')] = mva_row['Utilization'].values[0] if not mva_row.empty else None
                    
                    des_row = df_des[df_des['Users'] == u]
                    row[('Response Time', 'DES')] = des_row['Response Time'].values[0] if not des_row.empty else None
                    row[('Throughput', 'DES')] = des_row['Throughput'].values[0] if not des_row.empty else None
                    row[('Utilization', 'DES')] = des_row['Utilization'].values[0] if not des_row.empty else None
                    
                    merged_data.append(row)
                    
                df_final = pd.DataFrame(merged_data)
                df_final.rename(columns={'Users': ('Users', '')}, inplace=True)
                df_final.columns = pd.MultiIndex.from_tuples(df_final.columns)
                
                existing_cols = [col for col in columns_order if col in df_final.columns]
                df_final = df_final[existing_cols]
                
                sheet_name = f"{tt[:5]}_{st[:5]}"
                df_final.to_excel(writer, sheet_name=sheet_name)
                worksheet = writer.sheets[sheet_name]
                
                worksheet.set_column('A:A', 5)
                worksheet.set_column('B:B', 10)
                worksheet.set_column('C:C', 18, format_measured)
                worksheet.set_column('D:D', 18, format_mva)
                worksheet.set_column('E:E', 18, format_des)
                worksheet.set_column('F:F', 18, format_measured)
                worksheet.set_column('G:G', 18, format_mva)
                worksheet.set_column('H:H', 18, format_des)
                worksheet.set_column('I:I', 18, format_measured)
                worksheet.set_column('J:J', 18, format_mva)
                worksheet.set_column('K:K', 18, format_des)

                # Generate image
                title_str = f"$\\mathbf{{Think\\ Time:}}$ {tt.capitalize()}; $\\mathbf{{Service\\ Time:}}$ {st.capitalize()}"
                img_path = os.path.join(output_dir, f"table_{tt}_{st}.png")
                generate_table_image(df_final, title_str, img_path)

    print(f"Single Excel comparison file created at {output_file}")
    print("PNG images for tables also generated.")

if __name__ == "__main__":
    main()
