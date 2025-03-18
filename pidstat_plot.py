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

# Function to get the best matching command from the DataFrame
def get_matching_command(df, command):
    """
    If the exact command is not found, look for a prefixed version (e.g., '|__command')
    """
    # Convert all command names to lowercase for case-insensitive matching
    command_lower = command.lower()
    
    # Get the list of unique command names in lowercase
    available_commands = df['Command'].str.strip().str.lower().unique()

    # If exact match exists, return it
    if command_lower in available_commands:
        return command_lower

    # If prefixed version exists (e.g., '|__command'), return it
    prefixed_command = f"|__{command_lower}"
    if prefixed_command in available_commands:
        return prefixed_command

    # If nothing matches, return None
    return None

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

    # Set the Seaborn style for the plots
    sns.set(style="whitegrid", palette="muted")
    # Create a figure with 6 subplots (1 for each metric and one empty subplot)
    fig, axes = plt.subplots(3, 2, figsize=(9, 12), sharey=True)

    # Flatten axes for easy iteration
    axes = axes.flatten()

    fig.suptitle(f'Comparison of Metrics for {command} (TID {tid})', fontsize=16)

    unique_files = df['File'].unique()
    num_files = len(unique_files)

    # Loop through each metric and plot it in the 5 subplots (leave the 6th subplot empty)
    for idx, metric in enumerate(metrics):
        ax = axes[idx]
        # Set horizontal white gridlines and set facecolor
        ax.grid(True, axis='y', linestyle='-', color='white', linewidth=0.7)
        ax.set_facecolor('#f0f0f0')  # Set facecolor for each subplot

        for spine in ax.spines.values():
            spine.set_edgecolor("black")  # Set black outline
            spine.set_linewidth(1)  # Set outline thickness

        # Filter data for the given command and TID
        df_filtered = df[df['Command'].str.strip().str.lower() == command.lower()]
        df_filtered = df_filtered[df_filtered['TID'] == tid]

        if df_filtered.empty:
            print(f"No data found for command '{command}' with TID '{tid}' and metric '{metric}'. Skipping plot.")
            continue
        # Create a bar plot for the current metric
        sns.barplot(data=df_filtered, x='File', y=metric, hue='File', ax=ax)
        
        if not legend_handles:  # If no legend, create manually
            colors = sns.color_palette("tab10", num_files)
            legend_handles = [mpatches.Patch(color=colors[i], label=unique_files[i]) for i in range(num_files)]
        shorten_filenames(ax)
        # Set titles and labels for each subplot
        ax.set_title(f'{metric} Comparison', fontsize=14)
        ax.set_xlabel('CSV Files', fontsize=12)
        ax.set_ylabel(f'{metric} (%)', fontsize=12)  # Y-axis label for each subplot
        ax.tick_params(axis='x', rotation=45)

        # Annotate the bars with their values
        for p in ax.patches:
            ax.annotate(f'{p.get_height():.2f}', 
                        (p.get_x() + p.get_width() / 2., p.get_height()), 
                        ha='center', va='center', 
                        fontsize=10, color='black', 
                        xytext=(0, 5), textcoords='offset points')

        # Adjust Y-axis to start from 0 and set max Y to rounded value
        ax.set_ylim(0, round(ax.get_ylim()[1], -1) + 10)  # Set max Y to nearest 10
        #if legend_handles is None:
            #legend_handles, legend_labels = ax.get_legend_handles_labels()
            #print("Final Legend Handles:", legend_handles)
            #print("Final Legend Labels:", legend_labels)
        if ax.get_legend() is not None:
            ax.get_legend().remove()

    # Leave the last subplot empty (index 5) for clarity
    axes[5].axis('off')  # Turn off the 6th subplot (empty)
    if legend_handles:
        fig.legend(legend_handles, unique_files, loc='lower right', bbox_to_anchor=(0.9, 0.15), ncol=1, fontsize=12, title = "CSV files")

    plt.tight_layout(rect=[0, 0.05, 1, 1])
    # Adjust layout to avoid overlapping
    plt.tight_layout()

    # Save the plot to a PDF file
    plt.savefig(output_pdf, format='pdf')
    plt.close(fig)

# Main function to run the program
def main():
    # User input for commands to compare
    commands = input("Enter the process names to compare (comma separated): ").split(',')
    commands = [command.strip() for command in commands]

    # User input for CSV file paths
    file_paths = input("Enter the CSV file paths (comma separated): ").split(',')
    file_paths = [file_path.strip() for file_path in file_paths]

    # Load the data for the first metric to ensure the data exists
    df = load_and_extract_cpu_data(file_paths, '%usr')

    if df.empty:
        print("No valid data found for plotting. Exiting.")
        return

    # Define the output directory for saving PDFs
    output_dir = "pidstat_plots"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"Directory '{output_dir}' created.")

    generated_pdfs = []

    # For each command, plot all metrics (with differentiation for TID if necessary)
    for command in commands:

        matched_command = get_matching_command(df, command)
        
        if not matched_command:
            print(f"Warning: No match found for '{command}'. Skipping...")
            continue

        # Get unique TIDs for the current command
        #unique_tids = df[df['Command'].str.strip().str.lower() == command.lower()]['TID'].unique()
        unique_tids = df[df['Command'].str.strip().str.lower() == matched_command.lower()]['TID'].unique()
        if len(unique_tids) == 1:
            # If only one TID is found for this command, create one PDF with all metrics
            output_pdf = os.path.join(output_dir, f"{command}_comparison.pdf")
            plot_all_metrics(df, matched_command, unique_tids[0], output_pdf)
            generated_pdfs.append(output_pdf)
            print(f"Plot for {command} saved to {output_pdf}")
        else:
            # If there are multiple TIDs, create separate PDFs for each TID
            for tid in unique_tids:
                output_pdf = os.path.join(output_dir, f"{command}_{tid}_comparison.pdf")
                plot_all_metrics(df, matched_command, tid, output_pdf)
                generated_pdfs.append(output_pdf)
                print(f"Plot for {command} (TID {tid}) saved to {output_pdf}")

    merged_output_pdf = os.path.join(output_dir, "pidstat_comparison_merged.pdf")
    merge_pdfs(generated_pdfs, merged_output_pdf)
    print(f"Final merged PDF saved to {merged_output_pdf}")

if __name__ == "__main__":
    main()


