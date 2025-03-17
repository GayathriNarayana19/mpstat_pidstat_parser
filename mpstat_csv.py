import subprocess
import csv
import re
import os

def parse_cpu_cores(cpu_cores):
    if not cpu_cores or cpu_cores.upper() == "ALL":
        return "ALL"
    if '-' in cpu_cores:
        try:
            start, end = map(int, cpu_cores.split('-'))
            return ",".join(str(i) for i in range(start, end + 1))
        except ValueError:
            print("Invalid range format. It should be like '0-2'.")
            return None
    return cpu_cores

def get_unique_filename(directory, filename):
    """Ensure the filename is unique within the given directory by appending a number if needed."""
    base, ext = os.path.splitext(filename)
    file_path = os.path.join(directory, filename)
    
    counter = 1
    while os.path.exists(file_path):
        filename = f"{base}{counter}{ext}"
        file_path = os.path.join(directory, filename)
        counter += 1

    return filename

def get_user_input():
    cpu_cores = input("Enter CPU cores to monitor (e.g., 'ALL', '0,1,4', '0-2') [Default: ALL]: ") or "ALL"
    interval = input("Enter interval in seconds [Default: 1]: ") or "1"
    count = input("Enter number of samples [Default: 20]: ") or "20"
    output_dir = input("Enter directory to save CSV files [Default: mpstat_data]: ") or "mpstat_data"
    output_file = input("Enter output CSV filename (without path) [Default: cpu_usage.csv]: ") or "cpu_usage.csv"

    try:
        interval = int(interval)
        count = int(count)
    except ValueError:
        print("Interval and count must be numeric values.")
        return None, None, None, None, None

    parsed_cpu_cores = parse_cpu_cores(cpu_cores)
    if parsed_cpu_cores is None:
        return None, None, None, None, None

    # Create the directory if it doesn't exist
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"Directory '{output_dir}' created.")

    # Ensure filename is unique
    output_file = get_unique_filename(output_dir, output_file)

    return parsed_cpu_cores, interval, count, output_dir, output_file

def run_mpstat(cpu_cores, interval, count):
    command = ["mpstat", "-P", cpu_cores, str(interval), str(count)]
    result = subprocess.run(command, capture_output=True, text=True)
    return result.stdout

def parse_mpstat_output(output):
    lines = output.strip().splitlines()
    data = []
    timestamp = None
    first_header_found = False  # Track first occurrence of the "CPU" header row

    for index, line in enumerate(lines):
        fields = line.split()
        if len(fields) < 12:
            continue  # Skip malformed lines

        # Match timestamp in format HH:MM:SS AM/PM
        if re.match(r"^\d{2}:\d{2}:\d{2} (AM|PM)", line):
            if fields[2] == "CPU":
                if not first_header_found:
                    first_header_found = True
                    timestamp = "Timestamp"  # Replace timestamp with "Timestamp"
                else:
                    timestamp = f"{fields[0]} {fields[1]}"  # Normal timestamp for others
            else:
                timestamp = f"{fields[0]} {fields[1]}"  # Normal timestamp
            cpu = fields[2]
            values = fields[3:]

        elif fields[0].lower() == "average:":  # Handle 'Average' row
            timestamp = "Average:"
            cpu = fields[1]
            values = fields[2:]

        else:
            continue  # Ignore unexpected lines

        data.append([timestamp, cpu] + values)

    return data

def write_to_csv(data, output_dir, filename):
    file_path = os.path.join(output_dir, filename)
    
    with open(file_path, mode='w', newline='') as file:  # Overwrite file instead of appending
        writer = csv.writer(file)
        writer.writerows(data)

    print(f"CPU usage data written to {file_path}")

def main():
    cpu_cores, interval, count, output_dir, output_file = get_user_input()
    if cpu_cores is None:
        print("Invalid input, exiting.")
        return

    output = run_mpstat(cpu_cores, interval, count)
    parsed_data = parse_mpstat_output(output)
    write_to_csv(parsed_data, output_dir, output_file)

if __name__ == "__main__":
    main()


