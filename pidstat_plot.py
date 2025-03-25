import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import seaborn as sns
import pandas as pd
import os
import re
import PyPDF2

def merge_pdfs(pdf_files, output_pdf):
    pdf_writer = PyPDF2.PdfWriter()
    for pdf_file in pdf_files:
        try:
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            for page in pdf_reader.pages:
                pdf_writer.add_page(page)
        except Exception as e:
            print(f"Error reading {pdf_file}: {e}")
    with open(output_pdf, 'wb') as out_file:
        pdf_writer.write(out_file)
    print(f"Merged PDF saved as {output_pdf}")

def load_and_extract_cpu_data(files):
    data_frames = []
    for file in files:
        try:
            columns = ['Timestamp', 'CPU', 'TID_1', 'TID_2', '%usr', '%system', '%guest', '%wait', '%CPU', 'Dash', 'Command']
            df = pd.read_csv(file, header=None, names=columns, on_bad_lines='skip')
            df.columns = df.columns.str.strip()
            df_filtered = df[df['Timestamp'].astype(str).str.strip().str.lower() == 'average:'].copy()

            def extract_tid(row):
                for col in ['TID_1', 'TID_2', 'CPU']:
                    if str(row[col]).isdigit():
                        return int(row[col])
                return None

            df_filtered['TID'] = df_filtered.apply(extract_tid, axis=1)
            df_filtered = df_filtered[df_filtered['TID'].notnull()]
            df_filtered['TID'] = df_filtered['TID'].astype(int)
            df_filtered['Command'] = df_filtered['Command'].astype(str).str.strip()
            df_filtered['File'] = os.path.basename(file)

            for col in ['%usr', '%system', '%guest', '%wait', '%CPU']:
                if col in df_filtered.columns:
                    df_filtered[col] = pd.to_numeric(df_filtered[col], errors='coerce')

            # Create a label like "TID 12345 (file.csv)"
            df_filtered['Label'] = df_filtered.apply(lambda row: f"TID {row['TID']} ({row['File']})", axis=1)

            data_frames.append(df_filtered)

        except Exception as e:
            print(f"Error processing {file}: {e}")

    if not data_frames:
        print("No valid data found in any files.")
        return pd.DataFrame()

    return pd.concat(data_frames, ignore_index=True)

def plot_metrics_by_command(df, output_dir):
    metrics = ['%usr', '%system', '%guest', '%wait', '%CPU']
    os.makedirs(output_dir, exist_ok=True)
    generated_pdfs = []

    for command, group in df.groupby('Command'):
        sns.set(style="whitegrid", palette="muted")
        fig, axes = plt.subplots(3, 2, figsize=(10, 12))
        axes = axes.flatten()
        fig.suptitle(f'Comparison of Metrics for Command: {command}', fontsize=16)

        unique_files = sorted(group['File'].unique())

        for idx, metric in enumerate(metrics):
            if idx >= len(axes):
                continue
            ax = axes[idx]
            data = group[['Label', metric, 'File']].dropna()

            sns.barplot(
                data=data,
                x='Label',
                y=metric,
                hue='File',
                ax=ax,
                dodge=False  # same label won't appear twice
            )

            # Rotate x labels for readability
            ax.set_xticklabels(ax.get_xticklabels(), rotation=45, ha='right')
            ax.set_title(f'{metric} Comparison', fontsize=14)
            ax.set_xlabel('TID (File)', fontsize=12)
            ax.set_ylabel(f'{metric} (%)', fontsize=12)

            for p in ax.patches:
                if not pd.isna(p.get_height()) and p.get_height() > 0:
                    ax.annotate(f'{p.get_height():.2f}',
                                (p.get_x() + p.get_width() / 2., p.get_height()),
                                ha='center', va='center',
                                fontsize=10, color='black',
                                xytext=(0, 5), textcoords='offset points')

            y_max = data[metric].max()
            ax.set_ylim(0, y_max * 1.2 if y_max > 0 else 1)

            if ax.get_legend():
                ax.get_legend().remove()

        # Hide unused plot
        if len(metrics) < len(axes):
            for j in range(len(metrics), len(axes)):
                axes[j].axis("off")

        # Add legend only once
        fig.legend(
            handles=[mpatches.Patch(label=f, color=sns.color_palette()[i])
                     for i, f in enumerate(unique_files)],
            labels=unique_files,
            loc='lower right',
            bbox_to_anchor=(0.95, 0.05),
            title="CSV files"
        )

        safe_command = re.sub(r'[^a-zA-Z0-9_\-]', '_', command)
        output_pdf = os.path.join(output_dir, f"{safe_command}_comparison.pdf")
        plt.tight_layout(rect=[0, 0.05, 1, 1])
        plt.savefig(output_pdf, format='pdf')
        plt.close()
        print(f"Generated: {output_pdf}")
        generated_pdfs.append(output_pdf)

    return generated_pdfs

def main():
    try:
        threshold = float(input("Enter CPU utilization threshold (default 10%): ").strip() or 10)
    except ValueError:
        print("Invalid input. Using default threshold of 10%.")
        threshold = 10.0

    file_paths_input = input("Enter CSV file paths (comma separated), or press Enter to use all in 'pidstat_data/': ").strip()
    if file_paths_input:
        file_paths = [p.strip() for p in file_paths_input.split(',')]
    else:
        data_dir = "pidstat_data"
        if not os.path.exists(data_dir):
            print(f"Directory '{data_dir}' not found.")
            return
        file_paths = [os.path.join(data_dir, f) for f in os.listdir(data_dir) if f.endswith(".csv")]

    if not file_paths:
        print("No files to process.")
        return

    df = load_and_extract_cpu_data(file_paths)
    if df.empty:
        print("No valid data found.")
        return

    df_filtered = df[df['%CPU'] >= threshold]
    if df_filtered.empty:
        print(f"No rows with %CPU >= {threshold}")
        return

    output_dir = "pidstat_command_plots"
    generated_pdfs = plot_metrics_by_command(df_filtered, output_dir)

    if generated_pdfs:
        merge_pdfs(generated_pdfs, os.path.join(output_dir, "merged_command_comparison.pdf"))
    else:
        print("No plots were generated.")

if __name__ == "__main__":
    main()
