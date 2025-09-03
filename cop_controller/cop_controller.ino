/**
 * @file   cop_controller.ino
 * @brief  Four‑scale controller for HX711-based weight sensors.
 * @author rickwgarcia@unm.edu
 * @date   2025-07-10
 *
 * This sketch manages four HX711 scales, supports streaming readings,
 * calculating center of pressure (CoP), taring, and quick calibration.
 */

#include "HX711.h"
#include "scale.h"
#include "coordinate.h"
#include <EEPROM.h>

/// Available operating modes for the controller.
enum Mode {
  IDLE,            ///< No streaming; awaiting user input
  STREAM_READINGS, ///< Continuously output raw weights
  STREAM_COP       ///< Continuously output center of pressure
};

/// Current mode; defaults to IDLE.
static Mode mode = IDLE;

// EEPROM layout: three copies of Settings for redundancy
static constexpr int SETTINGS_SIZE   = sizeof(Settings);
static constexpr int EEPROM_ADDR_A   = 0;
static constexpr int EEPROM_ADDR_B   = EEPROM_ADDR_A + SETTINGS_SIZE;
static constexpr int EEPROM_ADDR_C   = EEPROM_ADDR_B + SETTINGS_SIZE;
static constexpr int EEPROM_ADDR_D   = EEPROM_ADDR_C + SETTINGS_SIZE;

// HX711 pins
#define CLK_PIN     6
#define DOUT_PIN_A  7
#define DOUT_PIN_B  8
#define DOUT_PIN_C  9
#define DOUT_PIN_D  10

// Four independent scale instances, each using its own EEPROM slot
Scale SCALE_A(EEPROM_ADDR_A);
Scale SCALE_B(EEPROM_ADDR_B);
Scale SCALE_C(EEPROM_ADDR_C);
Scale SCALE_D(EEPROM_ADDR_D);

/**
 * @brief  Compute calibration factor for one scale.
 * @param  scale   Pointer to the Scale object to calibrate.
 * @param  weight  Known weight placed on the scale (in the same units used by get_units()).
 * @return The computed calibration factor.
 */
float calc_calibration_val(Scale* scale, float weight) {
    float readings = scale->get_value(10);
    return readings / weight;
}

/**
 * @brief  Compute center of pressure (CoP) from four corner weights.
 * @param  wa  Weight from sensor A.
 * @param  wb  Weight from sensor B.
 * @param  wc  Weight from sensor C.
 * @param  wd  Weight from sensor D.
 * @return A Coordinate object with normalized X and Y CoP values in [-1,1].
 */
Coordinate calc_cop(float wa, float wb, float wc, float wd) {
    float total = wa + wb + wc + wd;
    if (total <= 0.0f) {
        return Coordinate(0.0f, 0.0f);
    }
    float x = ((wb + wc) - (wa + wd)) / total;
    float y = ((wa + wb) - (wc + wd)) / total;
    return Coordinate(x, y);
}

/**
 * @brief  Print the current CoP to Serial as “(X, Y)”.
 */
void print_cop() {
    float wa = SCALE_A.get_units();
    float wb = SCALE_B.get_units();
    float wc = SCALE_C.get_units();
    float wd = SCALE_D.get_units();

    Coordinate cop = calc_cop(wa, wb, wc, wd);
    Serial.print('(');
    Serial.print(cop.get_x(), 3);
    Serial.print(", ");
    Serial.print(cop.get_y(), 3);
    Serial.println(')');
}

/**
 * @brief  Display the available serial commands.
 */
void print_menu() {
    Serial.println(); 
    Serial.println(F("************************************"));
    Serial.println(F(" r - Stream weight readings"));
    Serial.println(F(" c - Stream Center of Pressure (CoP)"));
    Serial.println(F(" s - Stop the current stream"));
    Serial.println(F(" z - Tare all scales"));
    Serial.println(F(" k - Run quick calibration"));
    Serial.println(F(" h - Display this help menu"));
    Serial.println(F("************************************"));
}

/**
 * @brief  Print raw weight readings from all four scales, comma‑separated.
 */
void print_readings() {
    Serial.print(SCALE_A.get_units(), 1); Serial.print(',');
    Serial.print(SCALE_B.get_units(), 1); Serial.print(',');
    Serial.print(SCALE_C.get_units(), 1); Serial.print(',');
    Serial.println(SCALE_D.get_units(), 1);
}

/**
 * @brief  Tare (zero) all four scales.
 */
void tare_all() {
    Serial.println(F("Taring scales..."));
    SCALE_A.tare();
    SCALE_B.tare();
    SCALE_C.tare();
    SCALE_D.tare(); 
    
    Serial.println(F("Scaled tared."));
}

/**
 * @brief  Handles the user interface for the quick calibration routine.
 * @details Prompts the user to enter a known weight via the Serial Monitor,
 * parses the input, and then calls the core calibration logic.
 */
void quick_calibrate() {
    // Clear buffer
    while (Serial.available() > 0) {
        Serial.read();
    }
  
    Serial.println();
    Serial.println(F("Quick Calibration..."));
    Serial.println(F("Ensure scale has already been tared."));
    Serial.println(F("Place known weight in the center of the platform."));
    Serial.println(F("Enter the weight in lbs: "));
  
    // Block until user sends data
    while (Serial.available() == 0) {
        delay(50); 
    }
  
    // Read the floating-point number from the serial buffer
    float weight = Serial.parseFloat();
  
    // Clear any remaining characters from the buffer (like the newline)
    while(Serial.available() > 0) {
        Serial.read();
    }
  
    if (weight > 0.0) {
        calibrate_all(weight);
    } else {
        Serial.println(F("\nInvalid weight entered. Calibration cancelled."));
    }
}


/**
 * @brief  Calculates and applies a single, averaged calibration factor for all load cells.
 * @details This is the core calibration routine. It computes an individual calibration factor
 * for each of the four sensors based on an assumed equal weight distribution. It then
 * averages these four values to get a single factor, which is applied to all sensors
 * and saved to persistent memory (EEPROM). This method helps normalize the response
 * across all sensors.
 *
 * @param  weight The total known weight placed on the scale platform for calibration.
 *
 * @note   This function operates on two key assumptions:
 * 1. The scale has already been tared (zeroed). This function does not perform a tare.
 * 2. The `weight` is distributed perfectly evenly across all four sensors. For best
 * results, the calibration weight should be placed in the exact center of the scale.
 */
void calibrate_all(float weight) {
    Serial.println(F("Calibrating all..."));

    // Reset scale factor to 1.0 on all sensors to get raw readings for calibration.
    SCALE_A.set_scale(); 
    SCALE_B.set_scale(); 
    SCALE_C.set_scale(); 
    SCALE_D.set_scale(); 
     
    // Assume the total weight is distributed equally among the four scales.
    float perScale = weight / 4.0f;

    // Calculate the individual calibration factor for each scale.
    float ca = calc_calibration_val(&SCALE_A, perScale);
    float cb = calc_calibration_val(&SCALE_B, perScale);
    float cc = calc_calibration_val(&SCALE_C, perScale);
    float cd = calc_calibration_val(&SCALE_D, perScale);
    Serial.print("Scale A calibration factor: "); Serial.println(ca); 
    Serial.print("Scale B calibration factor: "); Serial.println(cb); 
    Serial.print("Scale C calibration factor: "); Serial.println(cc); 
    Serial.print("Scale D calibration factor: "); Serial.println(cd); 


    // Average the four factors to get a single, unified value.
    float avg = (ca + cb + cc + cd) / 4.0f;

    // Apply the averaged calibration factor to all scales.
    SCALE_A.set_scale(avg);
    SCALE_B.set_scale(avg);
    SCALE_C.set_scale(avg);
    SCALE_D.set_scale(avg);

    // Save the new calibration factor to EEPROM for each scale.
    SCALE_A.save();
    SCALE_B.save();
    SCALE_C.save();
    SCALE_D.save();

    Serial.print(F("New average calibration factor is: ")); 
    Serial.println(avg, 4); // Print with 4 decimal places for precision.
}


/**
 * @brief  Arduino setup: initialize serial, scales, load settings, then tare.
 */
void setup() {
    Serial.begin(115200);
    Serial.println(F("HX711 Four Scale Controller"));

    SCALE_A.begin(DOUT_PIN_A, CLK_PIN);
    SCALE_B.begin(DOUT_PIN_B, CLK_PIN);
    SCALE_C.begin(DOUT_PIN_C, CLK_PIN);
    SCALE_D.begin(DOUT_PIN_D, CLK_PIN);

    Serial.println(F("Loading settings from EEPROM..."));
    SCALE_A.load();
    SCALE_B.load();
    SCALE_C.load();
    SCALE_D.load();

    tare_all();
    Serial.println(F("System ready."));
    print_menu();
}

/**
 * @brief  Main loop: handle user commands and streaming modes.
 */
void loop() {
    // Non-blocking check for new command
    if (Serial.available()) {
        char cmd = Serial.read();
        switch (cmd) {
            case 'r': mode = STREAM_READINGS; break;
            case 'c': mode = STREAM_COP;  break;
            case 'z': mode = IDLE; tare_all();  break;
            case 'k': mode = IDLE; quick_calibrate(); print_menu(); break;
            case 'h': mode = IDLE; print_menu();  break;
            case 's': mode = IDLE;  break; 
        }
    }

    // Continuous streaming if in a streaming mode
    if (mode == STREAM_READINGS) {
        print_readings();
    } else if (mode == STREAM_COP) {
        print_cop();
    }
}
