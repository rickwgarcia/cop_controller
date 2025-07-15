import serial
import datetime
import os
import matplotlib.pyplot as plt

def center_of_mass(weights):
    """Calculate X and Y values based on the weights of four sensors."""
    WA, WB, WC, WD = weights
    W_total = WA + WB + WC + WD
    if W_total == 0:
        return 0.0, 0.0

    x = ((WB + WC) - (WA + WD)) / W_total
    y = ((WC + WD) - (WA + WB)) / W_total
    return x, y

def read_weight(ser):
    """Read and parse weight data from the serial connection."""
    if ser.in_waiting > 0:
        line = ser.readline().decode('utf-8').strip()
        try:
            parsed_weights = [float(part) for part in line.split(',')]
            if len(parsed_weights) != 4:
                raise ValueError(f"Expected 4 values, got {len(parsed_weights)}")
            processed_weights = [max(0.0, w) for w in parsed_weights]
            return processed_weights
        except ValueError as e:
            print(f"Error parsing line '{line}': {e}")
    return None

if __name__ == '__main__':
    # --- Configuration ---
    serial_port = '/dev/ttyACM0'
    baud_rate = 9600
    # NEW: Configure how many historical points to show in the trail
    PLOT_HISTORY_LENGTH = 1000000000000000000000000000000000000000

    script_directory = os.path.dirname(os.path.abspath(__file__))
    script_start_time = datetime.datetime.now()
    base_filename = script_start_time.strftime("%Y-%m-%d_%H-%M-%S") + ".txt"
    output_filename = os.path.join(script_directory, base_filename)

    # --- Plotting Setup ---
    x_com_history, y_com_history = [], [] # Data lists for the plot history
    plt.ion()
    fig, ax = plt.subplots()

    # MODIFIED: Plot the historical trail as a semi-transparent blue line
    trail_line, = ax.plot(x_com_history, y_com_history, 'b-', alpha=0.5, label='History Trail')
    # NEW: Plot the current position as a large, distinct red marker
    current_point_marker, = ax.plot([], [], 'ro', markersize=10, label='Current Position')

    ax.set_xlim(-1.5, 1.5)
    ax.set_ylim(-1.5, 1.5)
    ax.set_xlabel("X")
    ax.set_ylabel("Y")
    ax.set_title("Real-Time Center of Mass (CoM)")
    ax.grid(True)
    ax.set_aspect('equal', adjustable='box')
    ax.legend() # NEW: Display the legend to identify the plots
    plt.show(block=False)
    plt.pause(0.1)

    ser = None
    try:
        ser = serial.Serial(serial_port, baud_rate, timeout=1)
        ser.flush()
        print(f"Serial connection established on {serial_port} at {baud_rate} baud.")
        print(f"Logging data to a new file: {output_filename}.")
        print("Plot window is active. Press Ctrl+C in the terminal to stop.")

        with open(output_filename, 'w') as data_file:
            data_file.write(f"# Data log started at: {script_start_time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            data_file.write(f"# Serial Port: {serial_port}, Baud Rate: {baud_rate}\n")
            data_file.write("# Format: Timestamp | [WA, WB, WC, WD] -> X: CoM_X, Y: CoM_Y\n")
            data_file.write("# -----\n")
            data_file.flush()

            while True:
                if not plt.fignum_exists(fig.number):
                    print("Plot window closed by user. Continuing data logging without plotting.")
                    # To stop everything if plot is closed, uncomment the line below:
                    # raise KeyboardInterrupt("Plot window closed by user.")

                weights = read_weight(ser)
                if weights:
                    x, y = center_of_mass(weights)
                    entry_timestamp_obj = datetime.datetime.now()
                    entry_timestamp_str = entry_timestamp_obj.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
                    
                    output_string = f"{entry_timestamp_str} | {weights} -> X: {x:.3f}, Y: {y:.3f}"
                    print(output_string)
                    
                    data_file.write(output_string + "\n")
                    data_file.flush()

                    # MODIFIED: Update plot data if the figure still exists
                    if plt.fignum_exists(fig.number):
                        # Append new data to the history
                        x_com_history.append(x)
                        y_com_history.append(y)

                        # Trim the history to the desired length
                        if len(x_com_history) > PLOT_HISTORY_LENGTH:
                            x_com_history.pop(0) # Remove the oldest X point
                            y_com_history.pop(0) # Remove the oldest Y point

                        # Update the trail line with the trimmed history
                        trail_line.set_data(x_com_history, y_com_history)
                        
                        # Update the current point marker with only the latest data
                        current_point_marker.set_data([x], [y])

                        plt.draw()

                plt.pause(0.001)

    except serial.SerialException as e:
        print(f"Serial communication error: {e}")
    except KeyboardInterrupt:
        print("\nLogging and plotting stopped by user (Ctrl+C).")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
    finally:
        if ser and ser.is_open:
            ser.close()
            print("Serial connection closed.")
        
        if 'output_filename' in locals():
            if os.path.exists(output_filename) and os.path.getsize(output_filename) > 0:
                 print(f"Data logging session finished. Data saved to: {output_filename}")
            elif os.path.exists(output_filename):
                 print(f"Data logging session ended. Log file may be empty: {output_filename}")
        else:
            print("Script terminated before logging filename was generated.")

        if 'fig' in locals() and plt.fignum_exists(fig.number):
            plt.close(fig)
            print("Plot window closed.")