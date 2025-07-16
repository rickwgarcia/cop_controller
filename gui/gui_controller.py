import tkinter as tk
from tkinter import ttk, scrolledtext
import serial
import serial.tools.list_ports
import threading
import queue
import re
# --- New Imports for Matplotlib Integration ---
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

class SerialThread(threading.Thread):
    """
    A separate thread to handle reading from the serial port non-blockingly.
    """
    def __init__(self, port, baudrate, data_queue, log_queue):
        super().__init__(daemon=True)
        self.port = port
        self.baudrate = baudrate
        self.data_queue = data_queue
        self.log_queue = log_queue
        self.serial_connection = None
        self.running = False
        self._calibration_weight = None
        self._is_calibrating = False

    def run(self):
        """Main loop for the thread."""
        try:
            self.serial_connection = serial.Serial(self.port, self.baudrate, timeout=1)
            self.running = True
            self.log_queue.put(f"Successfully connected to {self.port}.")
        except serial.SerialException as e:
            self.log_queue.put(f"Error: Failed to connect to {self.port}.\n{e}")
            return

        while self.running:
            try:
                line = self.serial_connection.readline().decode('utf-8').strip()
                if line:
                    # Check if the line contains calibration prompt
                    if "Enter the weight in lbs:" in line and self._is_calibrating:
                        self.send(f"{self._calibration_weight}\n")
                        self.log_queue.put(f"Sent calibration weight: {self._calibration_weight}")
                        self._is_calibrating = False # Reset calibration state

                    self.data_queue.put(line)

            except serial.SerialException:
                self.log_queue.put("Error: Serial device disconnected.")
                break
            except Exception as e:
                self.log_queue.put(f"An error occurred in serial thread: {e}")
                
        if self.serial_connection and self.serial_connection.is_open:
            self.serial_connection.close()
        self.log_queue.put("Serial connection closed.")

    def stop(self):
        """Stops the thread."""
        self.running = False

    def send(self, data):
        """Sends data to the serial port."""
        if self.serial_connection and self.serial_connection.is_open:
            self.serial_connection.write(data.encode('utf-8'))
            self.log_queue.put(f"Sent: {data.strip()}")

    def start_calibration(self, weight):
        """Initiates the calibration sequence."""
        self._calibration_weight = weight
        self._is_calibrating = True
        self.send('k')

class App(tk.Tk):
    """
    The main GUI application window.
    """
    def __init__(self):
        super().__init__()
        self.title("CoP Controller")
        self.geometry("800x600")

        # Data storage
        self.serial_thread = None
        self.data_queue = queue.Queue()
        self.log_queue = queue.Queue()

        # Regex patterns for parsing data
        self.cop_pattern = re.compile(r"\(([-]?\d+\.\d+), ([-]?\d+\.\d+)\)")
        self.weight_pattern = re.compile(r"([-]?\d+\.\d+),([-]?\d+\.\d+),([-]?\d+\.\d+),([-]?\d+\.\d+)")
        
        # --- New: Data storage for the plot ---
        self.x_com_history = []
        self.y_com_history = []
        self.PLOT_HISTORY_LENGTH = 100 # How many historical points to show

        # UI Setup
        self.setup_ui()
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.process_queues()

    def setup_ui(self):
        """Creates and arranges all the widgets in the window."""
        main_frame = ttk.Frame(self, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        # --- Connection Frame ---
        conn_frame = ttk.LabelFrame(main_frame, text="Connection", padding="10")
        conn_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        conn_frame.columnconfigure(1, weight=1)

        ttk.Label(conn_frame, text="Port:").grid(row=0, column=0, sticky=tk.W, padx=5)
        self.port_var = tk.StringVar()
        self.port_menu = ttk.Combobox(conn_frame, textvariable=self.port_var, state="readonly")
        self.port_menu.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=5)
        self.refresh_ports()

        self.connect_button = ttk.Button(conn_frame, text="Connect", command=self.connect)
        self.connect_button.grid(row=0, column=2, padx=5)
        self.disconnect_button = ttk.Button(conn_frame, text="Disconnect", command=self.disconnect, state="disabled")
        self.disconnect_button.grid(row=0, column=3, padx=5)

        # --- Control Frame ---
        control_frame = ttk.LabelFrame(main_frame, text="Controls", padding="10")
        control_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N), pady=5)

        ttk.Button(control_frame, text="Stream Weights", command=lambda: self.send_command('r')).pack(fill=tk.X, pady=2)
        ttk.Button(control_frame, text="Stream CoP", command=lambda: self.send_command('c')).pack(fill=tk.X, pady=2)
        ttk.Button(control_frame, text="Stop Stream", command=lambda: self.send_command('s')).pack(fill=tk.X, pady=2)
        ttk.Button(control_frame, text="Tare Scales", command=lambda: self.send_command('z')).pack(fill=tk.X, pady=2)

        # --- Calibration Frame ---
        cal_frame = ttk.LabelFrame(main_frame, text="Quick Calibration", padding="10")
        cal_frame.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N), pady=5)
        
        ttk.Label(cal_frame, text="Place known weight on scale, enter the weight:").pack(padx=5, pady=2, anchor=tk.W)
        self.cal_weight_var = tk.StringVar(value="10.0")
        ttk.Entry(cal_frame, textvariable=self.cal_weight_var).pack(fill=tk.X, padx=5, pady=2)
        ttk.Button(cal_frame, text="Calibrate", command=self.start_calibration).pack(fill=tk.X, pady=5)

        # --- Data Display Frame ---
        data_frame = ttk.LabelFrame(main_frame, text="Live Data", padding="10")
        data_frame.grid(row=1, column=1, rowspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), padx=10)
        data_frame.columnconfigure(0, weight=1)
        data_frame.rowconfigure(1, weight=1)

        # Weight displays
        weights_grid = ttk.Frame(data_frame)
        weights_grid.grid(row=0, column=0, pady=10)
        self.weight_labels = []
        for i, name in enumerate(["Scale A", "Scale B", "Scale C", "Scale D"]):
            ttk.Label(weights_grid, text=f"{name}:").grid(row=i, column=0, sticky=tk.W, padx=5)
            label = ttk.Label(weights_grid, text="0.0", font=("Courier", 12), width=10)
            label.grid(row=i, column=1, sticky=tk.W, padx=5)
            self.weight_labels.append(label)
        
        # --- UPDATED: Matplotlib CoP Plot ---
        self.fig = Figure(figsize=(3, 3), dpi=100)
        self.ax = self.fig.add_subplot(111)
        
        self.trail_line, = self.ax.plot([], [], 'b-', alpha=0.5, label='History Trail')
        self.current_point_marker, = self.ax.plot([], [], 'ro', markersize=8, label='Current Position')

        self.ax.set_xlim(-1.5, 1.5)
        self.ax.set_ylim(-1.5, 1.5)
        self.ax.set_xlabel("X")
        self.ax.set_ylabel("Y")
        self.ax.set_title("Center of Pressure")
        self.ax.grid(True)
        self.ax.set_aspect('equal', adjustable='box')
        self.fig.tight_layout()

        self.canvas = FigureCanvasTkAgg(self.fig, master=data_frame)
        self.canvas.draw()
        self.canvas.get_tk_widget().grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # --- Log Console ---
        log_frame = ttk.LabelFrame(main_frame, text="Serial Log", padding="10")
        log_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        main_frame.rowconfigure(3, weight=1)

        self.log_text = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD, state="disabled", height=10)
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

    def refresh_ports(self):
        """Updates the list of available serial ports."""
        ports = [port.device for port in serial.tools.list_ports.comports()]
        self.port_menu['values'] = ports
        if ports:
            self.port_var.set(ports[0])

    def connect(self):
        """Starts the serial thread and connects to the selected port."""
        port = self.port_var.get()
        if not port:
            self.log_message("Please select a port first.")
            return

        self.serial_thread = SerialThread(port, 9600, self.data_queue, self.log_queue)
        self.serial_thread.start()
        
        self.connect_button.config(state="disabled")
        self.disconnect_button.config(state="normal")
        self.port_menu.config(state="disabled")

    def disconnect(self):
        """Stops the serial thread."""
        if self.serial_thread and self.serial_thread.is_alive():
            self.serial_thread.stop()
        
        self.connect_button.config(state="normal")
        self.disconnect_button.config(state="disabled")
        self.port_menu.config(state="normal")

    def send_command(self, cmd):
        """Sends a single character command to the Arduino."""
        if self.serial_thread and self.serial_thread.is_alive():
            self.serial_thread.send(cmd)
        else:
            self.log_message("Not connected.")

    def start_calibration(self):
        """Handles the calibration button click."""
        if not (self.serial_thread and self.serial_thread.is_alive()):
            self.log_message("Not connected.")
            return
        
        try:
            weight = float(self.cal_weight_var.get())
            self.serial_thread.start_calibration(weight)
        except ValueError:
            self.log_message("Error: Invalid calibration weight. Please enter a number.")
            
    def process_queues(self):
        """Periodically checks queues for new data and updates the GUI."""
        try:
            while not self.log_queue.empty():
                self.log_message(self.log_queue.get_nowait())
            
            while not self.data_queue.empty():
                line = self.data_queue.get_nowait()
                self.parse_and_update(line)

        except queue.Empty:
            pass
        finally:
            self.after(100, self.process_queues)

    def parse_and_update(self, line):
        """Parses a line of data and updates the appropriate UI element."""
        self.log_message(f"Received: {line}")

        # Check for weight data
        weight_match = self.weight_pattern.match(line)
        if weight_match:
            weights = weight_match.groups()
            for i in range(4):
                self.weight_labels[i].config(text=f"{float(weights[i]):.2f}")
            return

        # Check for CoP data
        cop_match = self.cop_pattern.match(line)
        if cop_match:
            x, y = map(float, cop_match.groups())
            self.update_cop_display(x, y)
            return

    def update_cop_display(self, x, y):
        """UPDATED: Updates the matplotlib plot with new CoP data."""
        # Append new data to the history
        self.x_com_history.append(x)
        self.y_com_history.append(y)

        # Trim the history to the desired length
        if len(self.x_com_history) > self.PLOT_HISTORY_LENGTH:
            self.x_com_history.pop(0)
            self.y_com_history.pop(0)

        # Update the trail line with the trimmed history
        self.trail_line.set_data(self.x_com_history, self.y_com_history)
        
        # Update the current point marker with only the latest data
        self.current_point_marker.set_data([x], [y])
        
        # Redraw the canvas efficiently
        self.canvas.draw_idle()

    def log_message(self, msg):
        """Appends a message to the log text area."""
        self.log_text.config(state="normal")
        self.log_text.insert(tk.END, msg + "\n")
        self.log_text.see(tk.END) # Auto-scroll
        self.log_text.config(state="disabled")

    def on_closing(self):
        """Handles window closing event."""
        self.disconnect()
        self.destroy()

if __name__ == "__main__":
    app = App()
    app.mainloop()