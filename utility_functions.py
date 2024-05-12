import math
import arcade


def euclidean_distance(point1, point2):
    """
    for use in several functions to calculate the pixel distance
    :param point1: (x, y) both integers
    :param point2: (x, y)
    :return: float distance between points
    """
    x1, y1 = point1
    x2, y2 = point2
    return math.sqrt((x2 - x1)**2 + (y2 - y1)**2)


def calculate_direction_vector_positive(facing_direction):
    # Calculate the angle in radians
    angle_radians = math.atan2(facing_direction[1], facing_direction[0])
    # Convert the angle to degrees
    angle_degrees = math.degrees(angle_radians)

    return angle_degrees


def calculate_direction_vector_negative(facing_direction):
    # Calculate the angle in radians
    angle_radians = math.atan2(facing_direction[1], facing_direction[0])
    # Convert the angle to degrees
    angle_degrees = math.degrees(angle_radians)

    return angle_degrees % 360


def is_within_facing_direction(self_position, self_facing_direction, target_position, swath_degrees=30):
    # Calculate the turret's direction in radians
    turret_direction_radians = math.radians(self_facing_direction)

    # Calculate the vector from the turret position to the target position
    dx = target_position[0] - self_position[0]
    dy = target_position[1] - self_position[1]

    # Calculate the angle between the turret's direction vector and the vector to the target
    angle_to_target = math.atan2(dy, dx)

    # Convert the angle to be between -π and π
    angle_diff = (angle_to_target - turret_direction_radians + math.pi) % (2 * math.pi) - math.pi

    # Convert the angle to degrees
    angle_diff_degrees = math.degrees(angle_diff)

    # Check if the absolute angle difference is within the swath degrees
    return abs(angle_diff_degrees) <= swath_degrees


def is_clear_line_of_sight(point1_x, point1_y, point2_x, point2_y, walls):
    """
    Check if there's a clear line of sight between a turret and a player, considering walls.
    """
    # Create a line segment between turret and player
    line = LineSegment(point1_x, point1_y, point2_x, point2_y)
    line_of_sight_collisions = arcade.check_for_collision_with_list(line, walls)

    # Line of sight is clear
    return not line_of_sight_collisions


def draw_line_until_collision(start_x, start_y, angle_degrees, max_length, walls, alpha=255, step=2):
    """
    Draw a line segment until it hits a wall
    """
    # Convert angle to radians
    angle_radians = math.radians(angle_degrees)

    # Initialize line segment with start point and angle
    line = LineSegment(start_x, start_y, start_x + math.cos(angle_radians) * max_length,
                       start_y + math.sin(angle_radians) * max_length, color=arcade.color.ORANGE, alpha=alpha)

    # Iterate until collision with wall or max_length reached
    while line.width < max_length:
        # Extend the line segment
        line.extend(step)

        # Check for collision with walls
        if len(arcade.check_for_collision_with_list(line, walls)) > 0:
            # If collision detected, return the current line segment
            return line

    # If no collision detected, return the line segment of max length
    return line


class LineSegment(arcade.Sprite):
    """
    Needed for calculating angle - easiest way to implement this
    """
    def __init__(self, point1_x, point1_y, point2_x, point2_y, color=arcade.color.WHITE, thickness=1, alpha=255):
        super().__init__()

        # Calculate the center of the line segment
        self.center_x = (point1_x + point2_x) / 2
        self.center_y = (point1_y + point2_y) / 2

        # Calculate the width and height of the line segment
        self.width = arcade.get_distance(point1_x, point1_y, point2_x, point2_y)
        self.height = thickness

        # Calculate the angle of the line segment using arctan2
        delta_x = point2_x - point1_x
        delta_y = point2_y - point1_y
        self.angle = math.degrees(math.atan2(delta_y, delta_x))

        # Set the color of the line segment
        self.color = color

    def extend(self, step):
        """
        Extend the line segment by a specified step.
        """
        self.width += step


def rotate_hit_box(hit_box_points, angle):
    """Rotate hit box points around a center point (cx, cy) by an angle."""
    new_points = []
    for x, y in hit_box_points:
        # Rotate points around center of player
        new_x = x * math.cos(math.radians(angle)) - y * math.sin(math.radians(angle))
        new_y = x * math.sin(math.radians(angle)) + y * math.cos(math.radians(angle))
        new_points.append((new_x, new_y))
    return new_points

def rotate_hit_box(hit_box_points, angle):
    """Rotate hit box points around a center point (cx, cy) by an angle."""
    new_points = []
    for x, y in hit_box_points:
        # Rotate points around center of player
        new_x = x * math.cos(math.radians(angle)) - y * math.sin(math.radians(angle))
        new_y = x * math.sin(math.radians(angle)) + y * math.cos(math.radians(angle))
        new_points.append((new_x, new_y))
    return new_points