import arcade
import random
import json
import math
import utility_functions

# half of turret sweep
ANGLE_FROM_DEFAULT = 89  # To handle an bug with turret rotation
DELAY_TIME_END_OF_SWEEP = 20
AGRO_DETECTION_ANGLE = 45
BASE_DETECTION_ANGLE = 30
BULLET_SPEED = 10
BULLETS_TO_FIRE = 100 # This modulus time between bullets is the amount fired
DELAY_BEFORE_FIRING = 50
FIRING_ANGLE = 10
TIME_BETWEEN_BULLETS = 5
BULLET_SPREAD = 3


class Mine(arcade.Sprite):
    def __init__(self):
        """
        Basic initialization
        # TODO: Add dropping weight sets off mine
        """

        # initialize seed
        super().__init__()

        self.weight = 0
        self.texture = None
        self.damage = 100
        self.armed = False
        self.exploded = False
        self.explosion_delay = 10
        self.explosion_distance = 100

    def setup(self, center_x, center_y):
        """
        Load texture and place onto map
        :return: self
        """
        # Load texture from mine file
        self.texture = arcade.load_texture("resources/hazard_sprites/mine.png")
        self.center_x = center_x
        self.center_y = center_y

        return self

    def get_weight(self):
        return self.weight

    def arm_mine(self):
        self.armed = True

    def explode_mine(self):
        self.exploded = True

    def get_armed(self):
        return self.armed

    def get_exploded(self):
        return self.exploded

    def get_damage(self):
        return self.damage

    def get_explosion_distance(self):
        return self.explosion_distance

    def decrease_delay(self):
        """
        Decrease the delay before explosion
        :return:
        """
        self.explosion_delay -= 1
        if self.explosion_delay == 0:
            self.exploded = True


class Turret(arcade.Sprite):
    def __init__(self):
        """
        Basic initialization
        """

        # initialize seed
        super().__init__()

        self.damage = 40
        self.base_direction = None
        self.facing_direction = None
        self.texture = None
        self.scale = 1.0  # Initial scale
        self.rotate_speed = 0.65
        self.rotate_direction = 1
        self.lower_end = None
        self.higher_end = None
        self.delay_at_edges = DELAY_TIME_END_OF_SWEEP
        self.delaying = False
        self.detection_angle = 30

        self.line_of_sight = False

        self.delay_after_firing = False
        self.firing = False
        self.delay_firing = DELAY_BEFORE_FIRING
        self.fire_duration = BULLETS_TO_FIRE # Number of bullets to fire upon update
        self.aiming = False
        self.bullets = None

        self.turret_laser = None

    def setup(self, center_x, center_y, view_direction):
        """
        Load texture and place onto map
        :return: self
        """
        # Load texture from mine file
        self.texture = arcade.load_texture("resources/hazard_sprites/turret.png")
        self.center_x = center_x
        self.center_y = center_y
        self.base_direction = utility_functions.calculate_direction_vector_negative(view_direction)
        # Initialize starting facing direction to be random direction within 90 degrees
        # from base position
        self.facing_direction = self.base_direction + random.randint(-ANGLE_FROM_DEFAULT, ANGLE_FROM_DEFAULT)
        self.lower_end = self.base_direction - ANGLE_FROM_DEFAULT
        self.higher_end = self.base_direction + ANGLE_FROM_DEFAULT

        self.bullets = arcade.SpriteList()

        return self

    def rotate(self, angle_degrees):
        """
        Rotate the turret's texture by the specified angle in degrees.
        """
        self.angle = angle_degrees

    def get_angle(self):
        return self.facing_direction

    def get_bullets(self):
        temp_bullets = self.bullets
        # Need to wipe the bullets from here so that an infinite number of bullets aren't passed to main
        self.bullets = arcade.SpriteList()
        return temp_bullets

    def update_status(self, player, wall_list):
        """
        Update turret rotation.
        """
        # previous direction, used for bugs with turret movement
        previous_direction = self.facing_direction

        # Calculate distance to player
        distance_to_player = utility_functions.euclidean_distance([player.center_x, player.center_y], [self.center_x,
                                                                                                       self.center_y])
        # Determine if there is a clear possible line of sight to the player
        self.line_of_sight = utility_functions.is_clear_line_of_sight(player.center_x, player.center_y, self.center_x,
                                                                      self.center_y, wall_list)

        # Determine turret laser
        self.turret_laser = utility_functions.draw_line_until_collision(self.center_x, self.center_y,
                                                                        self.facing_direction, 1000, wall_list,
                                                                        alpha=128, step=2)

        if self.line_of_sight and utility_functions.is_within_facing_direction([self.center_x, self.center_y], self.facing_direction,
                                                        [player.center_x, player.center_y],
                                                        swath_degrees=FIRING_ANGLE):
            # Check to see if the turret is currently firing, if not then decrease the timer before firing
            if self.delay_firing > 0 and not self.firing:
                self.delay_firing -= 1
                self.aiming = True
            else:
                self.firing = True
                self.delay_firing = DELAY_BEFORE_FIRING
        else:
            self.aiming = False
        # separate if statement so that if turret is looking at player it will continue to fire
        # (or if it has firing duration left)
        if self.firing and self.fire_duration > 0:
            # Create bullets and add to list if the firing counter is still greater than zero and mod the fire rate
            if (self.fire_duration - 1) % TIME_BETWEEN_BULLETS == 0:
                bullet_spread = self.facing_direction + random.uniform(-BULLET_SPREAD, BULLET_SPREAD)
                self.bullets.append(Bullet().setup(self.center_x, self.center_y, self.damage, bullet_spread))
                if self.aiming:
                    self.fire_duration = BULLETS_TO_FIRE
            # Otherwise, ignore and wait to fire until next bullet
            self.fire_duration -= 1
            # Delay current turret movement after player is lost by turret
            self.delaying = True
        # Done firing
        elif self.fire_duration <= 0:
            self.delay_firing = DELAY_BEFORE_FIRING
            self.firing = False
            self.fire_duration = BULLETS_TO_FIRE

            self.turret_laser = None
        elif not self.aiming:
            self.turret_laser = None


        # Move the turret
        # Calculate the angle between the turret's facing direction and the player, and move the turret
        if self.line_of_sight and utility_functions.is_within_facing_direction([self.center_x, self.center_y], self.facing_direction,
                                                        [player.center_x, player.center_y],
                                                        swath_degrees=self.detection_angle):

            # The following if statements handle if the turret passes from 360 to 0 degrees or 180 to -180 degrees
            # Otherwise, the turret jumps from where it was to higher or lower end.
            if self.lower_end > 0 or self.higher_end >= 360:
                player_vector = utility_functions.calculate_direction_vector_negative([player.center_x - self.center_x,
                                                                                       player.center_y - self.center_y])
            else:
                player_vector = utility_functions.calculate_direction_vector_positive([player.center_x - self.center_x,
                                                                                       player.center_y - self.center_y])
            if player_vector - previous_direction > 45:
                player_vector -= 360
            elif previous_direction - player_vector > 45:
                player_vector += 360
            if self.facing_direction < player_vector:
                self.facing_direction += self.rotate_speed * 200 / distance_to_player + self.rotate_speed * distance_to_player / 500
            elif self.facing_direction > player_vector:
                self.facing_direction -= self.rotate_speed * 200 / distance_to_player + self.rotate_speed * distance_to_player / 500

            if self.facing_direction >= self.higher_end:
                self.facing_direction = self.higher_end
                self.delaying = True
                self.rotate_direction = -1
            elif self.facing_direction <= self.lower_end:
                self.facing_direction = self.lower_end
                self.delaying = True
                self.rotate_direction = 1
            self.detection_angle = AGRO_DETECTION_ANGLE

        # Basic Turret movement
        elif not self.delaying:
            # Update the current facing direction based on direction and speed
            self.facing_direction += self.rotate_direction * self.rotate_speed
            # if angle is at end, spin
            if self.facing_direction <= self.lower_end or self.facing_direction >= self.higher_end:
                self.rotate_direction *= -1
                self.delaying = True
            self.detection_angle = BASE_DETECTION_ANGLE

        else:
            # Delaying the turret at the edges of sweep
            if self.delay_at_edges != 0:
                self.delay_at_edges -= 1
            else:
                self.delaying = False
                self.delay_at_edges = DELAY_TIME_END_OF_SWEEP
            self.detection_angle = BASE_DETECTION_ANGLE

    def get_turret_laser(self):
        return self.turret_laser

    def draw_scaled(self):
        """
        Draw the turret with scaled texture and rotation.
        """

        arcade.draw_texture_rectangle(self.center_x, self.center_y, self.texture.width * self.scale,
                                      self.texture.height * self.scale, self.texture, self.facing_direction)


class Bullet(arcade.Sprite):
    def __init__(self):
        """
        Basic initialization
        """

        # initialize seed
        super().__init__()

        self.damage = 0
        self.direction = None
        self.movement_speed = BULLET_SPEED
        self.texture = None
        # For drawing:
        self.scale = 1

    def setup(self, center_x, center_y, damage, direction):
        """
        Setup bullet using starting position, damage of bullet, and direction to fire
        :return: self
        """
        self.damage = damage
        self.center_x = center_x
        self.center_y = center_y
        self.direction = direction
        self.texture = arcade.load_texture("resources/hazard_sprites/bullet.png")

        return self

    def get_damage(self):
        return self.damage

    def update(self):
        """
        Update bullets movement
        """
        # Calculate the change in position using trigonometry
        self.change_x = math.cos(math.radians(self.direction)) * self.movement_speed
        self.change_y = math.sin(math.radians(self.direction)) * self.movement_speed

        # Update the bullet's position
        self.center_x += self.change_x
        self.center_y += self.change_y

    def draw_scaled(self):
        """
        Draw the turret with scaled texture and rotation.
        """

        arcade.draw_texture_rectangle(self.center_x, self.center_y, self.texture.width * self.scale,
                                      self.texture.height * self.scale, self.texture, self.direction)
