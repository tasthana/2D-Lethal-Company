import arcade
import json
from utility_functions import rotate_hit_box, is_clear_line_of_sight, is_within_facing_direction
import math
import random
from indoor_enemies import Enemy

# Giant class
GIANT_STATES = {"roam": 0, "agro": 1, "agro_search": 2}
GIANT_SEARCH_SWATH = 30
GIANT_TURN_SPEED = 1/5
GIANT_TARGET_DISTANCE = 24
TILE_SIZE = 256
TILE_CENTER_CONST = 128
GIANT_ROTATION_RATE = 4
GIANT_AGRO_METER = 25
GIANT_AGRO_METER_DRAIN = 1
GIANT_TEXTURE_CHANGE_COOLDOWN = 20

class Giant(Enemy):
    def __init__(self):
        super().__init__()
        self.state = GIANT_STATES["roam"]

        self.current_position = None
        self.target_position = None
        self.rotation = 0
        self.visited_areas = set()
        self.agro_meter = 0

        # texture loading
        self.sprite_neutral = arcade.load_texture("resources/enemy_sprites/giant/giant0.png")
        self.sprite_walk1 = arcade.load_texture("resources/enemy_sprites/giant/giant1.png")
        self.sprite_walk2 = arcade.load_texture("resources/enemy_sprites/giant/giant2.png")
        self.sprite_walk3 = arcade.load_texture("resources/enemy_sprites/giant/giant3.png")
        self.sprite_walk4 = arcade.load_texture("resources/enemy_sprites/giant/giant4.png")

        # anim cycle
        self.anim_cycle = [self.sprite_neutral, self.sprite_walk1, self.sprite_walk2, self.sprite_walk1, self.sprite_neutral, self.sprite_walk3, self.sprite_walk4, self.sprite_walk3]
        self.texture_change_cooldown = GIANT_TEXTURE_CHANGE_COOLDOWN

    def setup_outdoor_enemy(self, Type, moon_name, x_start, y_start):
        super().setup_outdoor_enemy(Type, moon_name, x_start, y_start)
        # Get the current area of the map the giant is in
        current_area = (self.center_x // TILE_SIZE, self.center_y // TILE_SIZE)
        self.current_position = (current_area[0] * TILE_SIZE + TILE_CENTER_CONST,
                                 current_area[1] * TILE_SIZE + TILE_CENTER_CONST)

    def update_monster(self, player):
        # Update the monster's state
        self.physics_engine.update()
        match self.state:
            case 0:
                if self.look_for_player(player, GIANT_SEARCH_SWATH):
                    self.state = GIANT_STATES["agro"]
                    self.movement_speed *= 2
                else:
                    self.roam()
            case 1:
                if self.look_for_player(player, GIANT_SEARCH_SWATH * 2):
                    # Make sure to update target position to players current position (set to center of tile in order to help with glitches
                    self.target_position = player.position
                    self.agro()
                else:
                    # Clear visited areas before anything else
                    self.visited_areas.clear()
                    self.state = GIANT_STATES["agro_search"]
                    self.agro_meter = GIANT_AGRO_METER

            case 2:
                # The difference between this and roam is that this has twice the movement speed
                if self.look_for_player(player, GIANT_SEARCH_SWATH):
                    self.state = GIANT_STATES["agro"]
                elif self.agro_meter <= 0:
                    self.movement_speed /= 2
                    self.state = GIANT_STATES["roam"]
                else:
                    self.roam()
                self.agro_meter -= GIANT_AGRO_METER_DRAIN

        # Deal damage to player if interacting with them - regardless of the state the thumper is in
        # Deal damage in cooldowns too, not constantly
        if arcade.check_for_collision(self, player) and self.temp_cooldown <= 0:
            self.temp_cooldown = self.damage_cooldown
            player.decrease_health(self.damage)
        else:
            self.temp_cooldown -= 1

    def look_for_player(self, player, swath):
        # Determine if there is a clear possible line of sight to the player
        line_of_sight = is_clear_line_of_sight(player.center_x, player.center_y, self.center_x,
                                               self.center_y, self.wall_list)
        # If no possible clear line of sight, return
        if not line_of_sight:
            return False
        if self.is_within_facing_direction([player.center_x, player.center_y], swath_degrees=swath):
            # The Giant can see the player and has a clear line of sight
            return True
        return False

    def is_within_facing_direction(self, target_position, swath_degrees=30):
        """
        Check if the Giant's rotation direction is looking at the player.
        """
        # Calculate the angle from the Giant to the target in radians
        dx = target_position[0] - self.center_x
        dy = target_position[1] - self.center_y
        angle_to_target = math.atan2(dy, dx)

        # Calculate the difference between the Giant's facing direction and the angle to the target
        angle_diff = math.degrees(angle_to_target) - self.rotation

        # Normalize the angle difference to be within the range of -180 and 180 degrees
        angle_diff = (angle_diff + 180) % 360 - 180

        # print(angle_diff)

        # Check if the absolute angle difference is within the swath degrees
        return abs(angle_diff) <= swath_degrees

    def roam(self):
        # print(self.target_position)
        # Check to set new areas
        current_area = (self.center_x // TILE_SIZE, self.center_y // TILE_SIZE)
        # Get the current position based on center of tile - possibly use this in future code based off bug testing
        self.current_position = (current_area[0] * TILE_SIZE + TILE_CENTER_CONST,
                                 current_area[1] * TILE_SIZE + TILE_CENTER_CONST)

        # First check if there is a target position, and move towards it
        if self.target_position is not None:
            # Check to see if within a certain distance of target position
            distance = math.sqrt((self.target_position[0] - self.center_x) ** 2 +
                                 (self.target_position[1] - self.center_y) ** 2)

            if distance <= GIANT_TARGET_DISTANCE:
                self.target_position = None
            else:
                # Update angle
                dx = self.target_position[0] - self.center_x
                dy = self.target_position[1] - self.center_y
                self.update_rotation(dx, dy)
                # Only move if starting to look in the correct direction - agro FOV will do
                if self.is_within_facing_direction(self.target_position, swath_degrees=GIANT_SEARCH_SWATH):
                    self.center_x += self.movement_speed * math.cos(math.radians(self.rotation))
                    self.center_y += self.movement_speed * math.sin(math.radians(self.rotation))
                    return
                else:
                    self.center_x += self.movement_speed * math.cos(math.radians(self.rotation)) * GIANT_TURN_SPEED
                    self.center_y += self.movement_speed * math.sin(math.radians(self.rotation)) * GIANT_TURN_SPEED
                    return
        # print("recalculating")
        valid_neighbors = self.get_neighboring_tiles(current_area)
        # Handle no possible movement options: have Giant retrace steps by clearing list
        if len(valid_neighbors) == 0:
            self.visited_areas.clear()
            valid_neighbors = self.get_neighboring_tiles(current_area)
        if len(valid_neighbors) == 0:
            return
        targeted_position = random.choice(valid_neighbors)
        self.target_position = targeted_position
        self.visited_areas.add(targeted_position)

        # Perform movement
        # Update angle
        dx = self.target_position[0] - self.center_x
        dy = self.target_position[1] - self.center_y
        self.update_rotation(dx, dy)
        # Only move if starting to look in the correct direction - agro FOV will do
        if self.is_within_facing_direction(self.target_position, swath_degrees=GIANT_SEARCH_SWATH):
            self.center_x += self.movement_speed * math.cos(math.radians(self.rotation))
            self.center_y += self.movement_speed * math.sin(math.radians(self.rotation))
            return
        else:
            self.center_x += self.movement_speed * math.cos(math.radians(self.rotation)) * GIANT_TURN_SPEED
            self.center_y += self.movement_speed * math.sin(math.radians(self.rotation)) * GIANT_TURN_SPEED
            return

    def get_neighboring_tiles(self, current_tile):
        # Generate the positions of the four neighboring tiles
        neighbors = [
            (current_tile[0], current_tile[1] + 1),  # Above
            (current_tile[0], current_tile[1] - 1),  # Below
            (current_tile[0] - 1, current_tile[1]),  # Left
            (current_tile[0] + 1, current_tile[1])  # Right
        ]

        scaled_current_tile = [current_tile[0] * TILE_SIZE + TILE_CENTER_CONST,
                               current_tile[1] * TILE_SIZE + TILE_CENTER_CONST]
        valid_neighbors = []
        for area in neighbors:
            if area not in self.visited_areas:
                # determine where the position of the next tile is and decide line of sight
                potentional_position = (area[0] * TILE_SIZE + TILE_CENTER_CONST,
                                        area[1] * TILE_SIZE + TILE_CENTER_CONST)
                if is_clear_line_of_sight(scaled_current_tile[0], scaled_current_tile[1], potentional_position[0],
                                          potentional_position[1], self.wall_list):
                    valid_neighbors.append(potentional_position)
        return valid_neighbors

    def agro(self):
        # Rotate towards player, at twice the normal rotation rate
        dx = self.target_position[0] - self.center_x
        dy = self.target_position[1] - self.center_y
        self.update_rotation(dx, dy, rate=2)

        # Walk towards player (IF can see and clear line of sight)
        if is_clear_line_of_sight(self.center_x, self.center_y, self.target_position[0],
                                  self.target_position[1], self.wall_list) and \
                self.is_within_facing_direction(self.target_position, swath_degrees=GIANT_SEARCH_SWATH):
            self.center_x += self.movement_speed * math.cos(math.radians(self.rotation))
            self.center_y += self.movement_speed * math.sin(math.radians(self.rotation))
        else:
            self.target_position = ((self.target_position[0] // TILE_SIZE) * TILE_SIZE + TILE_CENTER_CONST,
                                    (self.target_position[1] // TILE_SIZE) * TILE_SIZE + TILE_CENTER_CONST)

    def update_rotation(self, x_direction, y_direction, rate=1):
        """
        This is needed for updating the monster's rotation (important for Giant) based on movement direction
        Called from update_monster method
        """
        # Calculate target direction using arctan
        target_direction = math.degrees(math.atan2(y_direction, x_direction))

        # Normalize target direction to be in the range [0, 360) (arctan is in range -180 to 180)
        target_direction = (target_direction + 360) % 360
        current_rotation = self.rotation % 360

        # Calculate the absolute difference between target direction and current rotation
        diff_clockwise = (target_direction - current_rotation) % 360
        diff_counterclockwise = (current_rotation - target_direction) % 360

        # Determine the direction (clockwise or counterclockwise) to rotate
        if diff_clockwise <= diff_counterclockwise:
            rotation_direction = 1  # Rotate clockwise
        else:
            rotation_direction = -1  # Rotate counterclockwise

        # Adjust rotation rate if rotation is close to target (reduce stuttering
        if min(diff_clockwise, diff_counterclockwise) < GIANT_ROTATION_RATE * rate:
            rotation_rate = GIANT_ROTATION_RATE / 2
            # Decrease again if closer
            if min(diff_clockwise, diff_counterclockwise) < GIANT_ROTATION_RATE * rate / 2:
                rotation_rate = GIANT_ROTATION_RATE / 4
        else:
            rotation_rate = GIANT_ROTATION_RATE

        # Adjust rotation, if it has changed
        if current_rotation != target_direction:
            self.rotation += rotation_direction * rotation_rate * rate # rate is optional way to increase rotation speed
            # Only update hitbox if rotation has changed
            # Have to create a new sprite each time for the angle is only supplied during creation
            self.hit_box = rotate_hit_box(arcade.Sprite(self.texture_name).hit_box, self.rotation)

    def draw_self(self):

        # increment the animation counter
        if self.movement_speed:
            self.steps += self.movement_speed


        if self.steps > self.texture_change_cooldown:
            self.texture_number = (self.texture_number + 1) % len(self.anim_cycle)
            self.steps = 0

        # Draw the thumper rotated to its movement direction
        arcade.draw_texture_rectangle(self.center_x, self.center_y, self.texture.width * self.scale,
                                      self.texture.height * self.scale, self.anim_cycle[self.texture_number], self.rotation)
