import tkinter as tk
from tkinter import ttk, scrolledtext
import serial
import serial.tools.list_ports
import threading
import queue
import re

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
                    if "Place known weight and enter its value:" in line and self._is_calibrating:
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
        
        ttk.Label(cal_frame, text="Known Weight:").pack(padx=5, pady=2, anchor=tk.W)
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
        
        # CoP Canvas
        self.cop_canvas = tk.Canvas(data_frame, bg="white", width=250, height=250)
        self.cop_canvas.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.cop_canvas.create_line(125, 0, 125, 250, fill="lightgrey")
        self.cop_canvas.create_line(0, 125, 250, 125, fill="lightgrey")
        self.cop_dot = self.cop_canvas.create_oval(120, 120, 130, 130, fill="red", outline="red")

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
        """Updates the position of the dot on the CoP canvas."""
        canvas_width = self.cop_canvas.winfo_width()
        canvas_height = self.cop_canvas.winfo_height()

        # Map normalized CoP coordinates [-1, 1] to canvas coordinates
        # Y is inverted because canvas (0,0) is top-left
        canvas_x = (x + 1) / 2 * canvas_width
        canvas_y = (1 - y) / 2 * canvas_height

        # Move the dot
        x0, y0, x1, y1 = self.cop_canvas.coords(self.cop_dot)
        dx = canvas_x - (x0 + x1) / 2
        dy = canvas_y - (y0 + y1) / 2
        self.cop_canvas.move(self.cop_dot, dx, dy)

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