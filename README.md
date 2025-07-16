
# Arduino 4-Scale Center of Pressure (CoP) Controller

This project implements a versatile four-point weight sensing platform using an Arduino Nano, four load cells, and their corresponding HX711 amplifier modules. The system can stream individual weight readings or calculate the Center of Pressure (CoP) in real-time. It features a simple serial command interface for operation, including functions for taring and a quick calibration routine that saves settings to the Arduino's EEPROM for persistence between power cycles.

-----

## Features

  * **Four-Channel Weight Sensing**: Simultaneously measures weight from four independent load cells.
  * **Real-Time Center of Pressure (CoP) Calculation**: Computes the CoP based on the distribution of weight across the four sensors.
  * **Persistent Calibration**: Calibration and tare settings are saved to the Arduino's non-volatile EEPROM memory.
  * **Simple Serial Interface**: Control the unit and stream data using simple single-character commands via the Arduino Serial Monitor.
  * **Quick Calibration**: A streamlined process to calibrate all four scales at once using a single known weight.

-----

## Hardware Requirements

  * 1 x Arduino Nano (or compatible board)
  * 4 x Strain Gauge Load Cells (e.g., 50kg half-bridge or similar)
  * 4 x HX711 Load Cell Amplifier Modules
  * 1 x 5V DC Power Supply

-----

## Wiring Diagram

The hardware should be connected according to the diagram below. All four HX711 amplifier modules share a common clock pin (`SCK`), but each has a dedicated data pin (`DOUT`).
<img width="5556" height="5946" alt="weight_cop_full_wiring_bb" src="https://github.com/user-attachments/assets/5ba58f82-df31-49cd-aaae-2e01ae0fc0e9" />



### Pin Connections

| Arduino Pin | Connection                  |
| :---------- | :-------------------------- |
| `D6`        | `SCK` on **all four** HX711 modules |
| `D7`        | `DOUT` on HX711 for Scale A (Top-Left)   |
| `D8`        | `DOUT` on HX711 for Scale B (Top-Right)  |
| `D9`        | `DOUT` on HX711 for Scale C (Bottom-Right) |
| `D10`       | `DOUT` on HX711 for Scale D (Bottom-Left)  |
| `5V`        | `VCC` on all HX711 modules  |
| `GND`       | `GND` on all HX711 modules  |

-----

## Software Setup

### Dependencies

This project requires the `HX711` Arduino library. You can install it through the Arduino IDE's Library Manager. A common and recommended version is the one by **Bogdan Necula and Andreas Motl**.

### File Structure

Place all the provided files (`cop_controller.ino`, `Scale.h`, `Scale.cpp`, `Coordinate.h`, `Coordinate.cpp`) into the same sketch folder in your Arduino IDE.

1.  Open `cop_controller.ino` with the Arduino IDE.
2.  Ensure the other `.h` and `.cpp` files are open in tabs within the IDE.
3.  Select the correct board (e.g., Arduino Nano) and port.
4.  Upload the sketch to your Arduino.

-----

## How to Use

All interaction with the controller is done via the **Arduino Serial Monitor** set to a baud rate of **9600**. After uploading the sketch, open the Serial Monitor to begin.

### Initial Setup (Calibration)

On first use, or if you change the physical setup, you must calibrate the scales. The `quick_calibrate` function simplifies this process.

1.  With nothing on the scales, send the `k` command to start the calibration.
2.  The system will automatically tare itself.
3.  Place a **single weight of a known value** as close to the center of the platform as possible.
4.  Type the known weight's value into the Serial Monitor's input bar and press Enter.
5.  The controller will calculate an average calibration factor, apply it to all four scales, and save the settings to EEPROM. The system is now ready for use.

### Serial Commands

The following commands are available:

| Command | Action                               |
| :------ | :----------------------------------- |
| `r`     | **Stream Readings**: Continuously prints the weight from each of the four scales, comma-separated. |
| `c`     | **Stream CoP**: Continuously prints the calculated Center of Pressure as an (X, Y) coordinate. |
| `s`     | **Stop**: Halts any active data stream and returns the controller to an idle state. |
| `z`     | **Tare**: Zeros out all four scales. Use this to remove the weight of an object you don't want to measure. |
| `k`     | **Quick Calibrate**: Initiates the calibration routine described above. |
| `h`     | **Help**: Displays the menu of available commands. |

-----

## Center of Pressure (CoP) Calculation

The CoP is calculated based on the weight readings from the four corners, which are designated as follows:

```
(A) --[Y]-- (B)
 |           |
[X]         [X]
 |           |
(D) --[Y]-- (C)
```

The resulting CoP is given as a normalized coordinate pair $(X, Y)$, where both values range from -1.0 to 1.0.

  * **X-axis**: A value of -1.0 corresponds to the left edge (A-D), and +1.0 corresponds to the right edge (B-C).
  * **Y-axis**: A value of -1.0 corresponds to the top edge (A-B), and +1.0 corresponds to the bottom edge (D-C).

The formulas used are:

$$X_{CoP} = \frac{(W_B + W_C) - (W_A + W_D)}{W_A + W_B + W_C + W_D}$$

$$Y_{CoP} = \frac{(W_C + W_D) - (W_A + W_B)}{W_A + W_B + W_C + W_D}$$

Where $W\_A, W\_B, W\_C, W\_D$ are the weights measured at each respective corner.\

-----

## Python GUI Controller

For a more user-friendly experience, a Python-based graphical user interface (GUI) is available. This application provides a visual way to interact with the Arduino, display data, and run commands without needing to use the Serial Monitor directly. It features a real-time plot for the Center of Pressure, making it easy to visualize the data.

### GUI Features

  * **Easy Connection**: Automatically detects and lists available serial ports for a quick connection.
  * **Command Buttons**: Simple one-click buttons for all major functions: `Stream Weights`, `Stream CoP`, `Stop Stream`, and `Tare`.
  * **Visual CoP Plot**: Displays the Center of Pressure on a 2D graph in real-time. It shows the current CoP point and a historical "trail" of recent movements.
  * **Live Data Display**: Shows the current weight reading from each of the four individual scales.
  * **Simplified Calibration**: A dedicated section to input the known weight and initiate the quick calibration routine with a single button press.
  * **Serial Log**: A console window shows all data sent to and received from the Arduino, which is useful for debugging.

### Software Requirements

To run the GUI, you need Python 3 and a few additional libraries.

  * **Python 3.x**
  * **pyserial**: For handling the serial communication with the Arduino.
  * **matplotlib**: For creating the real-time 2D plot.

You can install the necessary libraries using pip:

```bash
pip install pyserial matplotlib
```

> **Note**: `Tkinter` is also required, but it is included with most standard Python installations on Windows, macOS, and Linux.

### How to Use the GUI

1.  Save the provided Python script to a file `gui_controller.py`.
2.  Make sure your Arduino is programmed with the `cop_controller.ino` sketch and connected to your computer via USB.
3.  Open a terminal or command prompt and run the script:
    ```bash
    python gui_controller.py
    ```
4.  The GUI window will appear.
      * **Connect**: Select the correct serial port for your Arduino from the dropdown menu and click the **Connect** button. The log should confirm a successful connection.
      * **Control**: Use the buttons in the "Controls" frame to start/stop data streams or tare the scales.
      * **View Data**: Watch the numerical weight values update in the "Live Data" section and observe the CoP movement on the graph.
      * **Calibrate**: To calibrate, enter your known weight value in the "Quick Calibration" box, place the weight on the platform, and click the **Calibrate** button. The GUI will handle sending the command and the weight value to the Arduino automatically.
