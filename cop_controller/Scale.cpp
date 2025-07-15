/**
 * @file   Scale.cpp
 * @brief  Implementation of the Scale class methods for EEPROM persistence.  
 * @author rickwgarcia@unm.edu
 * @date   2025-07-10
 */


#include "Scale.h"

/**
 * @brief Constructor for the Scale class.
 * @param address The starting EEPROM address for storing scale settings.
 */
Scale::Scale(int address) {
  this->eeprom_address = address;
}

/**
 * @brief Saves the current scale settings (calibration factor and zero factor) to EEPROM.
 */
void Scale::save() {
  Settings settings;
  settings.calibration_factor = get_scale();
  settings.zero_factor = get_offset();

  EEPROM.put(this->eeprom_address, settings);
}

/**
 * @brief Loads the scale settings from EEPROM and applies them.
 */
void Scale::load() {
  Settings settings;
  EEPROM.get(this->eeprom_address, settings);

  set_scale(settings.calibration_factor);
  set_offset(settings.zero_factor);
}
