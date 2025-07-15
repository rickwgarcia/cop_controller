/**
 * @file   Scale.h
 * @brief  Declaration of the Scale class extending HX711, with EEPROM persistence.
 * @author rickwgarcia@unm.edu
 * @date   2025-07-10
 */

#ifndef SCALE_H
#define SCALE_H

#include "HX711.h"
#include <EEPROM.h>

/**
 * @struct Settings
 * @brief  Stores calibration and offset factors for EEPROM.
 */
struct Settings {
    float calibration_factor; ///< Scale factor to apply to raw reading
    long zero_factor;         ///< Offset to apply for taring
};

/**
 * @class Scale
 * @brief Extends HX711 to add EEPROM-backed save/load of calibration settings.
 */
class Scale : public HX711 {
public:
    /**
     * @brief Construct a new Scale object.
     * @param address Starting EEPROM address for this scale’s Settings.
     */
    explicit Scale(int address);

    /**
     * @brief Save current calibration and zero factors to EEPROM.
     */
    void save();

    /**
     * @brief Load calibration and zero factors from EEPROM and apply them.
     */
    void load();

private:
    int eeprom_address; ///< EEPROM base address for this scale’s Settings
};

#endif // SCALE_H
