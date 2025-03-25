import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import seaborn as sns
import os
import re
import PyPDF2

def merge_pdfs(pdf_files, output_pdf):
    """Merge multiple PDFs into one."""
    pdf_writer = PyPDF2.PdfWriter()

    for pdf_file in pdf_files:
        try:
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            for page in range(len(pdf_reader.pages)):
                pdf_writer.add_page(pdf_reader.pages[page])
        except Exception as e:
            print(f"Error reading {pdf_file}: {e}")

    with open(output_pdf, 'wb') as out_file:
        pdf_writer.write(out_file)
    print(f"Merged PDF saved as {output_pdf}")

# Function to load and extract data from CSV files for the 'Average:' rows
def load_and_extract_cpu_data(files, metric_column):
    data_frames = []

    for file in files:
        try:
            # Read the CSV file
            df = pd.read_csv(file)
            df.columns = df.columns.str.strip()  # Clean column names

            # Ensure 'Timestamp' column is handled correctly
            timestamp_col = next((col for col in df.columns if 'timestamp' in col.lower()), None)
            if not timestamp_col:
                print(f"Warning: No 'Timestamp' column found in {file}. Skipping...")
                continue

            # Filter rows where 'Timestamp' is 'Average:'
            df_filtered = df[df[timestamp_col].astype(str).str.strip().str.lower() == 'average:']

            if df_filtered.empty:
                print(f"Warning: No 'Average:' rows found in {file}. Skipping...")
                continue

            # Add file name as a column for source identification
            df_filtered['File'] = file.split('/')[-1]

            # Ensure the metric column exists and handle it
            if metric_column in df_filtered.columns:
                df_filtered[metric_column] = pd.to_numeric(df_filtered[metric_column], errors='coerce')
            else:
                print(f"Warning: Column '{metric_column}' not found in {file}. Skipping...")
                continue

            data_frames.append(df_filtered)

        except Exception as e:
            print(f"Error processing {file}: {e}")

    if not data_frames:
        print("No valid data found in any files.")
        return pd.DataFrame()

    result_df = pd.concat(data_frames, ignore_index=True)
    return result_df

# Function to modify X-axis labels without altering the bar plot
def shorten_filenames(ax):
    """Modify X-axis labels to show only 'pid_<pid-num>'."""
    labels = [tick.get_text() for tick in ax.get_xticklabels()]
    new_labels = [re.search(r'pid_\d+', label).group(0) if re.search(r'pid_\d+', label) else label for label in labels]
    ax.set_xticklabels(new_labels, rotation=45)

# Function to plot all metrics for a single command or command+TID pair
def plot_all_metrics(df, command, tid, output_pdf):
    # List of all metrics to plot
    metrics = ['%usr', '%system', '%guest', '%wait', '%CPU']
    legend_handles = None

    sns.set(style="whitegrid", palette="muted")
    fig, axes = plt.subplots(3, 2, figsize=(9, 12), sharey=True)
    axes = axes.flatten()

    fig.suptitle(f'Comparison of Metrics for {command} (TID {tid})', fontsize=16)

    unique_files = df['File'].unique()
    num_files = len(unique_files)

    for idx, metric in enumerate(metrics):
        ax = axes[idx]
        ax.grid(True, axis='y', linestyle='-', color='white', linewidth=0.7)
        ax.set_facecolor('#f0f0f0')

        for spine in ax.spines.values():
            spine.set_edgecolor("black")
            spine.set_linewidth(1)

        df_filtered = df[df['Command'].str.strip().str.lower() == command.lower()]
        df_filtered = df_filtered[df_filtered['TID'] == tid]

        if df_filtered.empty:
            print(f"No data found for {command} (TID {tid}) - {metric}. Skipping plot.")
            continue

        sns.barplot(data=df_filtered, x='File', y=metric, hue='File', ax=ax)

        if not legend_handles:
            colors = sns.color_palette("tab10", num_files)
            legend_handles = [mpatches.Patch(color=colors[i], label=unique_files[i]) for i in range(num_files)]
        
        shorten_filenames(ax)
        ax.set_title(f'{metric} Comparison', fontsize=14)
        ax.set_xlabel('CSV Files', fontsize=12)
        ax.set_ylabel(f'{metric} (%)', fontsize=12)
        ax.tick_params(axis='x', rotation=45)

        for p in ax.patches:
            ax.annotate(f'{p.get_height():.2f}', 
                        (p.get_x() + p.get_width() / 2., p.get_height()), 
                        ha='center', va='center', 
                        fontsize=10, color='black', 
                        xytext=(0, 5), textcoords='offset points')

        ax.set_ylim(0, round(ax.get_ylim()[1], -1) + 10)

        if ax.get_legend() is not None:
            ax.get_legend().remove()

    axes[5].axis('off')

    if legend_handles:
        fig.legend(legend_handles, unique_files, loc='lower right', bbox_to_anchor=(0.9, 0.15), ncol=1, fontsize=12, title="CSV files")

    plt.tight_layout(rect=[0, 0.05, 1, 1])
    plt.savefig(output_pdf, format='pdf')
    plt.close(fig)

def main():
    # Get CPU utilization threshold from user (default = 10)
    threshold_input = input("Enter CPU utilization threshold (default 10%): ").strip()
    threshold = float(threshold_input) if threshold_input else 10.0

    # Get CSV file paths from user (default to 'pidstat_data/' directory)
    file_paths_input = input("Enter the CSV file paths (comma separated) or press Enter to use all CSVs in 'pidstat_data/': ").strip()
    
    if file_paths_input:
        file_paths = [file.strip() for file in file_paths_input.split(',')]
    else:
        # Use all CSVs in 'pidstat_data/' directory
        data_dir = "pidstat_data"
        if not os.path.exists(data_dir):
            print(f"Error: Directory '{data_dir}' does not exist. Exiting.")
            return
        file_paths = [os.path.join(data_dir, f) for f in os.listdir(data_dir) if f.endswith('.csv')]

        if not file_paths:
            print(f"Error: No CSV files found in '{data_dir}'. Exiting.")
            return

    print(f"Using files: {file_paths}")

    # Load the data
    df = load_and_extract_cpu_data(file_paths, '%CPU')

    if df.empty:
        print("No valid data found for plotting. Exiting.")
        return

    # Filter processes where %CPU is greater than or equal to the threshold
    filtered_df = df[df['%CPU'] >= threshold]

    if filtered_df.empty:
        print(f"No processes found with CPU utilization >= {threshold}%. Exiting.")
        return

    # Define output directory
    output_dir = "pidstat_plots"
    os.makedirs(output_dir, exist_ok=True)

    generated_pdfs = []

    # Iterate through unique (Command, TID) pairs
    for (command, tid), group in filtered_df.groupby(['Command', 'TID']):
        output_pdf = os.path.join(output_dir, f"{command}_{tid}_comparison.pdf")
        plot_all_metrics(df, command, tid, output_pdf)
        generated_pdfs.append(output_pdf)
        print(f"Plot for {command} (TID {tid}) saved to {output_pdf}")

    # Merge all generated PDFs
    if generated_pdfs:
        merged_output_pdf = os.path.join(output_dir, "pidstat_comparison_merged.pdf")
        merge_pdfs(generated_pdfs, merged_output_pdf)
        print(f"Final merged PDF saved to {merged_output_pdf}")
    else:
        print("No plots were generated, so no merged PDF was created")

if __name__ == "__main__":
    main()
'''
# Main function to run the program
def main():
    # Get the CPU utilization threshold from the user
    try:
        threshold = float(input("Enter CPU utilization threshold (default = 10): ") or 10)
    except ValueError:
        print("Invalid input! Using default threshold of 10.")
        threshold = 10

    # Get CSV file paths from the user
    file_paths = input("Enter the CSV file paths (comma separated): ").split(',')
    file_paths = [file_path.strip() for file_path in file_paths]

    # Load data for CPU utilization
    df = load_and_extract_cpu_data(file_paths, '%CPU')

    if df.empty:
        print("No valid data found for plotting. Exiting.")
        return

    # Filter processes exceeding the threshold
    filtered_df = df[df['%CPU'] >= threshold]

    if filtered_df.empty:
        print(f"No processes exceeded {threshold}% CPU utilization. Exiting.")
        return

    # Get unique commands that exceeded the threshold
    commands_to_plot = filtered_df['Command'].str.strip().str.lower().unique()

    output_dir = "pidstat_plots"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    generated_pdfs = []

    for command in commands_to_plot:
        unique_tids = filtered_df[filtered_df['Command'].str.strip().str.lower() == command]['TID'].unique()
        for tid in unique_tids:
            output_pdf = os.path.join(output_dir, f"{command}_{tid}_comparison.pdf")
            plot_all_metrics(df, command, tid, output_pdf)
            generated_pdfs.append(output_pdf)
            print(f"Plot for {command} (TID {tid}) saved to {output_pdf}")

    merged_output_pdf = os.path.join(output_dir, "pidstat_comparison_merged.pdf")
    merge_pdfs(generated_pdfs, merged_output_pdf)
    print(f"Final merged PDF saved to {merged_output_pdf}")

if __name__ == "__main__":
    main()
'''

