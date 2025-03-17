import subprocess
import csv

# Function to get user input and run the pidstat command
def capture_pidstat_data():
    # Get user input for PID
    pid = input("Enter the PID to monitor: ")

    # Validate the PID input
    try:
        pid = int(pid)
    except ValueError:
        print("Invalid PID. Please enter a valid integer for PID.")
        return

    # Check if the process with the given PID exists
    check_pid_command = ["ps", "-p", str(pid)]
    result = subprocess.run(check_pid_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    # If the process does not exist, return an error
    if result.returncode != 0:
        print(f"Error: No process with PID {pid} found.")
        return

    # Get user input for interval and count
    interval = input("Enter the interval in seconds (default 1): ")
    count = input("Enter the number of times to repeat (default 5): ")

    # Set default values if the user doesn't input anything
    if not interval:
        interval = 1
    else:
        interval = int(interval)

    if not count:
        count = 5
    else:
        count = int(count)

    # Validate the PID input
    try:
        pid = int(pid)
    except ValueError:
        print("Invalid PID. Please enter a valid integer for PID.")
        return

    # Run the pidstat command
    command = ["pidstat", "-t", "-p", str(pid), str(interval), str(count)]  # Run the pidstat command
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    # Get the output of the pidstat command
    pidstat_output = result.stdout

    # Prepare the CSV file name
    file_path = f'pid_{pid}_info.csv'

    # Open the file in write mode to overwrite if it exists
    with open(file_path, 'w', newline='') as file:
        writer = csv.writer(file)

        # Process each line from pidstat output
        for line in pidstat_output.splitlines():
            # Skip the line that contains the Linux information
            if "Linux" in line:
                continue

            # If the line contains average data, ensure it's added at the end
            if "Average:" in line:
                row = line.split()  # Split the pidstat output by spaces
                writer.writerow(row)

            # For regular lines, split by space and write them
            else:
                # Process the timestamp to ensure there's no comma before AM/PM
                if line:
                    columns = line.split()
                    # Merge the time part (columns[0] and columns[1]) into the first column
                    timestamp = columns[0] + " " + columns[1]  # Join the time part (AM/PM)
                    columns[0] = timestamp  # Replace the first column with formatted timestamp
                    # Remove the original timestamp column (index 1) since it's now merged
                    del columns[1]
                    if "UID" in line:
                        columns[0] = "Timestamp"
                    writer.writerow(columns)

    print(f"Data successfully saved to {file_path}")

# Run the function to capture data
if __name__ == "__main__":
    capture_pidstat_data()


