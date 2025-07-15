/**
 * @file   Coordinate.cpp
 * @brief  Implementation of a simple 2D coordinate helper.
 * @author rickwgarcia@unm.edu
 * @date   2025-07-10
 */

#include "Coordinate.h"

/**
 * @brief  Construct a Coordinate with given X and Y.
 * @param  x  Initial x-coordinate.
 * @param  y  Initial y-coordinate.
 */
Coordinate::Coordinate(float x, float y)
  : x(x), y(y) { }

/**
 * @brief  Update the x-coordinate.
 * @param  new_x  New x value.
 */
void Coordinate::set_x(float new_x) {
    x = new_x;
}

/**
 * @brief  Update the y-coordinate.
 * @param  new_y  New y value.
 */
void Coordinate::set_y(float new_y) {
    y = new_y;
}

/**
 * @brief  Get the current x-coordinate.
 * @return Current x value.
 */
float Coordinate::get_x() const {
    return x;
}

/**
 * @brief  Get the current y-coordinate.
 * @return Current y value.
 */
float Coordinate::get_y() const {
    return y;
}
