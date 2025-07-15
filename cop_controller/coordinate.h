/**
 * @file   Coordinate.h
 * @brief  Declaration of a simple 2D coordinate helper.
 * @author rickwgarcia@unm.edu
 * @date   2025-07-10
 */

#ifndef COORDINATE_H
#define COORDINATE_H

/**
 * @class Coordinate
 * @brief Represents a point in 2D space with X and Y components.
 */
class Coordinate {
public:
    /**
     * @brief Construct a new Coordinate.
     * @param x Initial X value (defaults to 0.0).
     * @param y Initial Y value (defaults to 0.0).
     */
    Coordinate(float x = 0.0f, float y = 0.0f);

    /**
     * @brief Set the X component.
     * @param x New X value.
     */
    void set_x(float x);

    /**
     * @brief Set the Y component.
     * @param y New Y value.
     */
    void set_y(float y);

    /**
     * @brief Get the X component.
     * @return Current X value.
     */
    float get_x() const;

    /**
     * @brief Get the Y component.
     * @return Current Y value.
     */
    float get_y() const;

private:
    float x;  ///< X-coordinate value
    float y;  ///< Y-coordinate value
};

#endif // COORDINATE_H
