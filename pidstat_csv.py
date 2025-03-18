import subprocess
import csv
import os

def capture_pidstat_data():
    pid = input("Enter the PID to monitor: ")

    try:
        pid = int(pid)
    except ValueError:
        print("Invalid PID. Please enter a valid integer for PID.")
        return

    check_pid_command = ["ps", "-p", str(pid)]
    result = subprocess.run(check_pid_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    if result.returncode != 0:
        print(f"Error: No process with PID {pid} found.")
        return

    interval = input("Enter the interval in seconds (default 1): ")
    count = input("Enter the number of times to repeat (default 5): ")

    interval = int(interval) if interval else 1
    count = int(count) if count else 5

    command = ["pidstat", "-t", "-p", str(pid), str(interval), str(count)]
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    pidstat_output = result.stdout

    output_dir = "pidstat_data"
    os.makedirs(output_dir, exist_ok=True)

    file_path = os.path.join(output_dir, f'pid_{pid}_info.csv')

    with open(file_path, 'w', newline='') as file:
        writer = csv.writer(file, delimiter=',')

        for line in pidstat_output.splitlines():
            if "Linux" in line:
                continue

            if line.startswith("Average:"):
                row = line.split()
                writer.writerow(row)
                continue

            if line:
                columns = line.split()
                timestamp = columns[0] + " " + columns[1]
                columns[0] = timestamp
                del columns[1]

                if "UID" in line and "Command" in line:
                    columns[0] = "Timestamp"
                    writer.writerow(columns)
                    continue

                command_index = next((i for i, val in enumerate(columns) if val.isalpha() or val.startswith("|__")), len(columns) - 1)
                normal_columns = columns[:command_index]
                command_column = " ".join(columns[command_index:]).replace(",", " ")
                writer.writerow(normal_columns + [command_column])

    print(f"Data successfully saved to {file_path}")

if __name__ == "__main__":
    capture_pidstat_data()


