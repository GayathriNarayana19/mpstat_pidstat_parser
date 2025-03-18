import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.backends.backend_pdf import PdfPages
import glob
import math
import numpy as np
import os
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

# Set seaborn style
sns.set_palette("Set2")  # Set2 color palette for distinct bar colors

# Function to get the path(s) from the user (either directory, single file, or multiple files)
def get_file_paths():
    user_input = input("Enter the path to the mpstat CSV files to be compared separated by commas (or) the directory path containing CSVs: (e.g., /home/ubuntu/data.csv,/home/ubuntu/data1.csv): ").strip()

    # Case 1: If user didn't enter anything, assume current directory
    if not user_input:
        user_input = "."
        print("No input provided. Using the current directory (PWD) by default.")

    # Option 1: If it's a directory
    if os.path.isdir(user_input):
        # Get all CSV files in the directory
        csv_files = glob.glob(os.path.join(user_input, '*.csv'))
        if not csv_files:
            print(f"No CSV files found in the directory: {user_input}")
        return csv_files

    # Option 2: If it's a single CSV file
    elif os.path.isfile(user_input) and user_input.lower().endswith('.csv'):
        return [user_input]

    # Option 3: If it's multiple CSV files (user enters them separated by commas)
    elif ',' in user_input:
        csv_files = [file.strip() for file in user_input.split(',')]
        # Check if each file exists and is a CSV file
        valid_files = [file for file in csv_files if os.path.isfile(file) and file.lower().endswith('.csv')]
        if not valid_files:
            print(f"No valid CSV files found in the input list.")
        return valid_files

    # If input doesn't match any of the above
    else:
        print("Invalid path. Please provide a valid directory or CSV file(s).")
        return []

# Function to load and extract CPU data
def load_and_extract_cpu_data(files, metric_column):
    #files = glob.glob(files_pattern)
    data_frames = []

    for file in files:
        try:
            df = pd.read_csv(file)
            df.columns = df.columns.str.strip()

            # Ensure 'Timestamp' column is handled correctly
            timestamp_col = next((col for col in df.columns if 'timestamp' in col.lower()), None)
            if not timestamp_col:
                print(f"Warning: No 'Timestamp' column found in {file}. Skipping...")
                continue

            # Filter rows where 'Timestamp' is 'Average'
            df_filtered = df[df[timestamp_col].astype(str).str.strip().str.lower() == 'average:']

            # Ensure 'CPU' column exists and clean it
            if 'CPU' not in df_filtered.columns:
                print(f"Warning: No 'CPU' column in {file}. Skipping...")
                continue

            df_filtered['CPU'] = df_filtered['CPU'].astype(str).str.strip()

            # Keep only rows where 'CPU' is a number or 'all'
            df_filtered = df_filtered[df_filtered['CPU'].apply(lambda x: x == 'all' or x.isdigit())]

            df_filtered['File'] = file.split('/')[-1]

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
    #print("Sample of filtered data:\n", result_df.head())  
    return result_df

# Function to round up to the nearest 10
def round_up_to_10(x):
    return math.ceil(x / 10) * 10 if x > 0 else 10

# Function to plot the metric with color and style adjustments
def plot_metric(df, metric_column, metric_name, pdf_path):
    if df.empty:
        print(f"No data available for {metric_name}. Skipping PDF generation.")
        return

    with PdfPages(pdf_path) as pdf:
        cpus = df['CPU'].unique()
        num_pages = math.ceil(len(cpus) / 6)

        # Get the Set2 color palette for CSV files
        colors = sns.color_palette("Set2", len(df['File'].unique()))  # Unique color for each CSV file

        for page_num in range(num_pages):
            # Check if there's only 1 plot to display
            if len(cpus) == 1:
                # Create a single subplot layout (1 row, 1 column)
                fig, axs = plt.subplots(1, 1, figsize=(8.5, 11))
                fig.suptitle(f'Comparison of Metrics - {metric_name}', fontsize=16)
                axs.set_facecolor('#f0f0f0')  # Set subplot background color
                axs.grid(axis='y', linestyle='--', color='white', linewidth=0.7)  # White horizontal grid lines

                cpu = cpus[0]
                cpu_data = df[df['CPU'] == cpu]

                # Get the unique CSV files and their corresponding color
                file_names = cpu_data['File'].unique()
                for j, file_name in enumerate(file_names):
                    file_data = cpu_data[cpu_data['File'] == file_name]
                    color = colors[j]

                    bars = axs.bar(file_data['File'], file_data[metric_column], color=color, label=f'{file_name}')

                    # Add annotations for all bars
                    for bar in bars:
                        height = bar.get_height()
                        if not np.isnan(height):
                            axs.text(bar.get_x() + bar.get_width() / 2, height + 1, f'{height:.2f}',
                                     ha='center', va='bottom', fontsize=8, fontweight='bold')

                axs.set_title(f'{metric_name} for CPU {cpu}')
                axs.set_xlabel('CSV File')
                axs.set_ylabel(metric_name)
                axs.tick_params(axis='x', rotation=45)

                max_value = cpu_data[metric_column].max()
                max_value_rounded = round_up_to_10(max_value)
                axs.set_ylim([0, max_value_rounded])

                plt.tight_layout()
                pdf.savefig(fig)
                plt.close(fig)
            else:
                # Create a 3x2 grid (fixed size) for 2 or more subplots
                fig, axs = plt.subplots(3, 2, figsize=(8.5, 11))
                fig.suptitle(f'Comparison of Metrics - {metric_name}', fontsize=16)
                axs = axs.flatten()  # Flatten the 3x2 grid into a 1D array for easier access

                # Set the background color for all subplots
                for ax in axs:
                    ax.set_facecolor('#f0f0f0')  # Set subplot background color
                    ax.grid(axis='y', linestyle='--', color='white', linewidth=0.7)  # White horizontal grid lines

                # Plot each CPU data in available subplots
                start_idx = page_num * 6
                end_idx = min(start_idx + 6, len(cpus))

                for i in range(start_idx, end_idx):
                    cpu = cpus[i]
                    cpu_data = df[df['CPU'] == cpu]

                    # Get the unique CSV files and their corresponding color
                    file_names = cpu_data['File'].unique()
                    for j, file_name in enumerate(file_names):
                        file_data = cpu_data[cpu_data['File'] == file_name]
                        color = colors[j]

                        bars = axs[i - start_idx].bar(file_data['File'], file_data[metric_column], color=color, label=f'{file_name}')

                        # Add annotations for all bars
                        for bar in bars:
                            height = bar.get_height()
                            if not np.isnan(height):
                                axs[i - start_idx].text(bar.get_x() + bar.get_width() / 2, height + 1, f'{height:.2f}',
                                                        ha='center', va='bottom', fontsize=8, fontweight='bold')

                    axs[i - start_idx].set_title(f'{metric_name} for CPU {cpu}')
                    axs[i - start_idx].set_xlabel('CSV File')
                    axs[i - start_idx].set_ylabel(metric_name)
                    axs[i - start_idx].tick_params(axis='x', rotation=45)

                    max_value = cpu_data[metric_column].max()
                    max_value_rounded = round_up_to_10(max_value)
                    axs[i - start_idx].set_ylim([0, max_value_rounded])

                # Remove empty subplots by not plotting anything on them
                for j in range(end_idx - start_idx, len(axs)):
                    fig.delaxes(axs[j])

                plt.tight_layout()
                pdf.savefig(fig)
                plt.close(fig)
# Main execution
if __name__ == "__main__":
    # Get the file paths (directory, single CSV, or multiple CSVs)
    csv_files = get_file_paths()
    generated_pdfs = []                
    if csv_files:
        # List of metrics you want to plot for 'CPU all' and each individual core
        metrics = ['%usr', '%sys', '%idle', '%iowait', '%irq', '%soft', '%steal', '%guest', '%gnice']

        output_dir = "mpstat_plots"
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            print(f"Directory '{output_dir}' created.")

        # For each metric, generate a PDF
        for metric in metrics:
            # Load and extract all CPU core data (including 'CPU all') from the CSV files
            df = load_and_extract_cpu_data(csv_files, metric)
                
            if not df.empty:
                # Define the full path for the output PDF
                pdf_path = os.path.join(output_dir, f'{metric}_comparison.pdf')
                plot_metric(df, metric, metric, pdf_path)
                generated_pdfs.append(pdf_path)
            print(f'{metric} comparison saved to {pdf_path}')
    
    merged_output_pdf = os.path.join(output_dir, "mpstat_comparison_merged.pdf")
    merge_pdfs(generated_pdfs, merged_output_pdf)
    print(f"Final merged PDF saved to {merged_output_pdf}")

