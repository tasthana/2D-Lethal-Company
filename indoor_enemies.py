import arcade
import json
from utility_functions import rotate_hit_box, is_clear_line_of_sight, is_within_facing_direction
import math
import random
import os
import time

# Tradeoff between grid size and how far the astar algorithm will search
# Also, much faster at higher grid sizes, wouldn't recommend below 32
SMALL_GRID_SIZE = 32
LARGE_GRID_SIZE = 64
MAX_PATH_LENGTH = 1024
PLAYING_FIELD_LEFT = 0
PLAYING_FIELD_BOTTOM = 0
MAP_SIZE = 5
SHOW_SLIME_PATHING = False
SLIME_TIMER = 3
SLIME_TIMER_DRAIN = 1

TEXTURE_CHANGE_COOLDOWN = 25


class Enemy(arcade.Sprite):
    # initialization function
    def __init__(self):
        super().__init__()

        # basic enemy attributes
        self.health = 0
        self.power_level = 0
        self.movement_speed = 0
        self.type = None
        self.wall_list = None
        self.barrier_list_large_grid = None
        self.barrier_list_small_grid = None
        self.path_find_timer = 0
        self.damage = 0
        self.damage_cooldown = 0
        self.temp_cooldown = 0

        # Need to update sprites with animations, directions, etc
        self.texture = None
        self.texture_name = None  # Needed for drawing hitboxes
        self.path = None
        self.physics_engine = None
        

        self.texture_folder = None
        self.texture_number = 0
        self.steps = 0
        self.texture_change_cooldown = TEXTURE_CHANGE_COOLDOWN

    # Assigns values to the correct attributes
    def setup(self, Type, wall_list, x_start, y_start, moon_name):
        self.type = Type
        self.wall_list = wall_list

        # Load item data from JSON
        with open("resources/monsters.json", "r") as file:
            data_from_json = json.load(file)

            # Assuming that type is the same as the identifiers for monsters.json
            self.power_level = data_from_json["indoors"][self.type]["power"]
            self.movement_speed = data_from_json["indoors"][self.type]["movement_speed"]
            # self.texture = arcade.load_texture(data_from_json["indoors"][self.type]["sprite"])
            self.texture_name = data_from_json["indoors"][self.type]["sprite"]
            self.health = data_from_json["indoors"][self.type]["health"]
            self.damage = data_from_json["indoors"][self.type]["damage"]
            self.damage_cooldown = data_from_json["indoors"][self.type]["damage_cooldown"]
            texture_folder = data_from_json["indoors"][self.type]["texture_folder"]
        file.close()

        # Load textures into texture list
        texture_files = load_files_from_directory(texture_folder)
        self.texture_folder = []
        for filename in texture_files:
            self.texture_folder.append(arcade.load_texture(filename))

        self.texture = random.choice(self.texture_folder)

        # Get the size of the map using the moon size * tile size
        with open("resources/moons.json", "r") as file:
            data_from_json = json.load(file)
            for moon in data_from_json:
                if moon.get("id") == moon_name:
                    map_size = int(float(moon.get("size")) * MAP_SIZE * TILE_SIZE)
                    break

        # Setup barrier list
        grid_size_large = LARGE_GRID_SIZE
        grid_size_small = SMALL_GRID_SIZE

        # Calculate the playing field size
        playing_field_left_boundary = PLAYING_FIELD_LEFT
        playing_field_right_boundary = map_size
        playing_field_top_boundary = map_size
        playing_field_bottom_boundary = PLAYING_FIELD_BOTTOM

        self.barrier_list_large_grid = arcade.AStarBarrierList(self,
                                                               self.wall_list,
                                                               grid_size_large,
                                                               playing_field_left_boundary,
                                                               playing_field_right_boundary,
                                                               playing_field_bottom_boundary,
                                                               playing_field_top_boundary)

        self.barrier_list_small_grid = arcade.AStarBarrierList(self,
                                                               self.wall_list,
                                                               grid_size_small,
                                                               playing_field_left_boundary,
                                                               playing_field_right_boundary,
                                                               playing_field_bottom_boundary,
                                                               playing_field_top_boundary)

        # Physics engine used to update monster position
        self.physics_engine = arcade.PhysicsEnginePlatformer(
            self, self.wall_list
        )
        self.physics_engine.gravity_constant = 0
        # position the monster at its starting location
        self.center_x = x_start
        self.center_y = y_start
        return self

    def add_walls(self, walls):
        # To change the wall list
        self.wall_list.extend(walls)
        self.physics_engine = arcade.PhysicsEnginePlatformer(
            self, self.wall_list
        )
        self.physics_engine.gravity_constant = 0

    def setup_outdoor_enemy(self, Type, moon_name, x_start, y_start):
        self.type = Type
        # Load item data from JSON
        with open("resources/monsters.json", "r") as file:
            data_from_json = json.load(file)
            # Assuming that type is the same as the identifiers for monsters.json
            self.power_level = data_from_json["outdoors"][self.type]["power"]
            self.movement_speed = data_from_json["outdoors"][self.type]["movement_speed"]
            self.texture = arcade.load_texture(data_from_json["outdoors"][self.type]["sprite"])
            self.texture_name = data_from_json["outdoors"][self.type]["sprite"]
            self.health = data_from_json["outdoors"][self.type]["health"]
            self.damage = data_from_json["outdoors"][self.type]["damage"]
            self.damage_cooldown = data_from_json["outdoors"][self.type]["damage_cooldown"]
            texture_folder = data_from_json["outdoors"][self.type]["texture_folder"]
        file.close()

        # Load textures into texture list
        texture_files = load_files_from_directory(texture_folder)
        self.texture_folder = []
        for filename in texture_files:
            self.texture_folder.append(arcade.load_texture(filename))

        # Load moon data from json
        with open("resources/moons.json", "r") as file:
            data_from_json = json.load(file)
            for moon in data_from_json:
                if moon.get("id") == moon_name:
                    tilemap_name = moon.get("outdoor_tilemap")
        tilemap = arcade.Scene.from_tilemap(arcade.load_tilemap(tilemap_name))
        self.wall_list = tilemap["walls"]

        # Physics engine used to update monster position
        self.physics_engine = arcade.PhysicsEnginePlatformer(
            self, self.wall_list
        )
        self.physics_engine.gravity_constant = 0
        # position the monster at its starting location
        self.center_x = x_start
        self.center_y = y_start
        return self

    # getters
    def get_health(self):
        return self.health

    def get_movement_speed(self):
        return self.movement_speed

    def get_power_level(self):
        return self.power_level

    def get_center_x(self):
        return self.center_x

    def get_center_y(self):
        return self.center_y

    # setters
    def set_health(self, health):
        self.health = health

    def set_movement_speed(self, movement_speed):
        self.movement_speed = movement_speed

    def set_power_level(self, power_level):
        self.power_level = power_level

    def set_center_x(self, new_center_x):
        self.center_x = new_center_x

    def set_center_y(self, new_center_y):
        self.center_y = new_center_y

    # basic A* Pathfinding
    # Other monsters will overload this method if they use a different Pathfinding system,
    # ie line of sight
    # Also moves the enemy along the path
    def pathfinding(self, PlayerCharacter):
        # Change path depending on: If path length is between
        if self.path is not None and path_length(self.path) < LARGE_GRID_SIZE * 2:
            temp_path = arcade.astar_calculate_path(self.position, PlayerCharacter.position,
                                                    self.barrier_list_small_grid,
                                                    diagonal_movement=True)
            if temp_path is not None:
                self.path = temp_path
        elif self.path_find_timer <= 0:

            temp_path = arcade.astar_calculate_path(self.position, PlayerCharacter.position,
                                                    self.barrier_list_large_grid,
                                                    diagonal_movement=True)
            if temp_path is not None:
                self.path_find_timer = SLIME_TIMER * (path_length(temp_path) // TILE_SIZE)
            else:
                self.path_find_timer = SLIME_TIMER

            if temp_path is not None:
                self.path = temp_path
        self.path_find_timer -= SLIME_TIMER_DRAIN


        # sees if the path is valid and if we have not reached the end of the path
        # then moves the enemy to the next point in the path
        if self.path and len(self.path) > 1:
            next_position = self.path[1]
            # Check if the enemy has reached the next position
            if (self.center_x, self.center_y) == next_position:
                # Pop the first point from the path list
                self.path.pop(0)
                next_position = self.path[1] if len(self.path) > 1 else None

            if next_position:
                if self.center_y < self.path[1][1]:
                    self.center_y += min(self.movement_speed, self.path[1][1] - self.center_y)
                elif self.center_y > self.path[1][1]:
                    self.center_y -= min(self.movement_speed, self.center_y - self.path[1][1])

                if self.center_x < self.path[1][0]:
                    self.center_x += min(self.movement_speed, self.path[1][0] - self.center_x)
                elif self.center_x > self.path[1][0]:
                    self.center_x -= min(self.movement_speed, self.center_x - self.path[1][0])

    # Draw method
    def draw_self(self):
        # self.texture.center_x = self.center_x
        # self.texture.center_y = self.center_y
        # self.texture.draw()
        self.draw()
        if self.path and SHOW_SLIME_PATHING:
            arcade.draw_line_strip(self.path, arcade.color.BLUE, 2)

    # Update method
    def update_monster(self, player):
        self.physics_engine.update()
        self.pathfinding(player)
        # Deal damage to player, over time
        if arcade.check_for_collision(self, player) and self.temp_cooldown <= 0:
            self.temp_cooldown = self.damage_cooldown
            player.decrease_health(self.damage)
        # Don't change this 1, the values temp_cooldown has stored is what to use for changing timings
        self.temp_cooldown -= 1

        if self.texture_change_cooldown <= 0:
            # Update the slime texture
            self.texture = self.texture_folder[self.texture_number]
            # Update texture number to length of list
            self.texture_number = (self.texture_number + 1) % len(self.texture_folder)
            self.texture_change_cooldown = TEXTURE_CHANGE_COOLDOWN
        self.texture_change_cooldown -= 1

    def decrease_health(self, amount):
        self.health -= amount


def distance(point1, point2):
    """Calculate the distance between two points."""
    x1, y1 = point1
    x2, y2 = point2
    return math.sqrt((x2 - x1)**2 + (y2 - y1)**2)


def path_length(path):
    """Calculate the length of a path."""
    total_length = 0
    for i in range(len(path) - 1):
        total_length += distance(path[i], path[i + 1])
    return total_length


def load_files_from_directory(directory):
    files = []
    for filename in sorted(os.listdir(directory)):
        if os.path.isfile(os.path.join(directory, filename)):
            files.append(os.path.join(directory, filename))
    return files


# Constants
THUMPER_ROTATION_RATE = 2
THUMPER_PASSIVE_FOV = 10
THUMPER_AGRO_FOV = 30
THUMPER_CHASE_FOV = 160  # Only can't see right behind them
# Thumper has 3 states: wandering the map, actively seeing the player and running at them,
# and just saw the player and is trying to find them for a short time
THUMPER_AGRO_STATES = {"wander": 1, "aggressive": 2, "search": 3}
AGRO_METER_MAX = 100
AGRO_DRAIN = 0.5

THUMPER_BASE_MOVEMENT_SPEED = 1
THUMPER_COLLISION_MS = 1 / 3
THUMPER_MOVEMENT_SPEED_INCREASE_RATE = 0.1
TILE_SIZE = 256  # Thumper search pattern based on room tiles
TILE_CENTER_CONST = 128
THUMPER_BASE_TURN_SIZE = 90

# Minimum distance to target node before finding new position
THUMPER_MIN_DISTANCE_BEFORE_TARGET = 32
THUMPER_MOVEMENT_DELAY = 10
THUMPER_MOVEMENT_DELAY_RATE = 0.01

THUMPER_TARGET_DISTANCE = 32
THUMPER_TARGET_DELAY_RATE = 1
THUMPER_TEXTURE_CHANGE_COOLDOWN = 30

class Thumper(Enemy):
    def __init__(self):
        super().__init__()
        self.rotation = 0
        self.agro_state = THUMPER_AGRO_STATES["wander"]
        self.agro_meter = AGRO_METER_MAX
        self.movement_delay = 0
        self.in_distance = False

        self.scale = 1.25

        # For use in
        self.target_position = None

        self.speed = THUMPER_BASE_MOVEMENT_SPEED

        # Use a set to keep track of areas the thumper has visited
        self.visited_areas = set()

        self.current_position = None

        # texture loading
        self.sprite_neutral = arcade.load_texture("resources/enemy_sprites/thumper/thumper_neutral.png")
        self.sprite_walk1 = arcade.load_texture("resources/enemy_sprites/thumper/thumper_1.png")
        self.sprite_walk2 = arcade.load_texture("resources/enemy_sprites/thumper/thumper_2.png")

        # anim cycle
        self.anim_cycle = [self.sprite_neutral, self.sprite_walk1, self.sprite_neutral, self.sprite_walk2]
        self.texture_change_cooldown = THUMPER_TEXTURE_CHANGE_COOLDOWN

    def setup(self, Type, wall_list, x_start, y_start, moon_name):
        super().setup(Type, wall_list, x_start, y_start, moon_name)
        current_area = (self.center_x // TILE_SIZE, self.center_y // TILE_SIZE)
        # Get the current position based on center of tile - possibly use this in future code based off bug testing
        self.current_position = (current_area[0] * TILE_SIZE + TILE_CENTER_CONST,
                                 current_area[1] * TILE_SIZE + TILE_CENTER_CONST)
        self.scale = 1.25

    def update_monster(self, player):
        """
        This works to try and detect the player if the thumper is wandering, otherwise it will patrol while wandering.
        If it sees the player it will charge in the general direction of the player, with reduced turning speed
        When switching states, movement speed is changed. For wandering (aggressive and non-aggressive) this is the base
        speed, but otherwise it is halved when seeing player and then incremented unless hitting a wall.
        :param player:
        :return:
        """
        if self.health <= 0:
            # Monster dead, no more movement or damage
            self.damage = 0
            return
        self.physics_engine.update()

        if self.agro_state == THUMPER_AGRO_STATES["wander"]:
            # If can see player, become aggressive
            if self.look_for_player(player, THUMPER_PASSIVE_FOV):
                self.agro_state = THUMPER_AGRO_STATES["aggressive"]
                self.speed = THUMPER_BASE_MOVEMENT_SPEED / 2  # half movement speed when seeing the player
                # This is steadily increased while chasing player
            # Roaming behavior - updates rotation and position
            self.roam()

        elif self.agro_state == THUMPER_AGRO_STATES["aggressive"]:
            # If can't see player, start searching for player
            dx = player.center_x - self.center_x
            dy = player.center_y - self.center_y
            target_distance = math.sqrt(dx ** 2 + dy ** 2)
            # If entering distance to player
            if (arcade.check_for_collision(self,
                                           player) or target_distance <= THUMPER_TARGET_DISTANCE) and not self.in_distance:
                self.movement_delay = THUMPER_MOVEMENT_DELAY
                self.in_distance = True
            else:
                self.in_distance = False
            if self.movement_delay > 0:
                # continue moving past player if in them
                if arcade.check_for_collision_with_list(self, self.wall_list):
                    self.update_rotation(dx, dy)
                    self.speed = 0
                else:
                    self.update_rotation(dx, dy)
                    self.center_x += self.speed * math.cos(math.radians(self.rotation))
                    self.center_y += self.speed * math.sin(math.radians(self.rotation))
                    if self.speed > 0 and not self.in_distance:
                        self.speed -= THUMPER_MOVEMENT_SPEED_INCREASE_RATE / THUMPER_COLLISION_MS
                self.movement_delay -= THUMPER_TARGET_DELAY_RATE
            # Aggressive search behavior
            elif not self.look_for_player(player, THUMPER_CHASE_FOV):
                self.agro_state = THUMPER_AGRO_STATES["search"]
                self.agro_meter = AGRO_METER_MAX
                self.visited_areas.clear()
                self.target_position = player.position
                if self.speed > THUMPER_BASE_MOVEMENT_SPEED:
                    self.speed -= THUMPER_MOVEMENT_DELAY_RATE
                else:
                    self.speed += THUMPER_MOVEMENT_DELAY_RATE
            else:
                # Aggressive behavior
                self.aggressive_behavior(player)
                self.target_position = player.position

        elif self.agro_state == THUMPER_AGRO_STATES["search"]:
            if self.look_for_player(player, THUMPER_AGRO_FOV):
                # If can see player, switch to agro again
                self.aggressive_behavior(player)
                self.agro_state = THUMPER_AGRO_STATES["aggressive"]
                self.speed = THUMPER_BASE_MOVEMENT_SPEED / 2
                # self.target_position = self.current_position
                self.visited_areas.clear()
                self.target_position = player.position

            elif self.agro_meter <= 0:
                # Ran out of agro, start roaming again
                self.roam()
                self.agro_state = THUMPER_AGRO_STATES["wander"]
                if self.speed > THUMPER_BASE_MOVEMENT_SPEED:
                    self.speed -= THUMPER_MOVEMENT_DELAY_RATE
                else:
                    self.speed += THUMPER_MOVEMENT_DELAY_RATE
            else:
                self.roam()
                self.agro_meter -= AGRO_DRAIN
                if self.speed > THUMPER_BASE_MOVEMENT_SPEED * 3 / 2:
                    self.speed -= THUMPER_MOVEMENT_DELAY_RATE
                else:
                    self.speed += THUMPER_MOVEMENT_DELAY_RATE

        # Deal damage to player if interacting with them - regardless of the state the thumper is in
        # Deal damage in cooldowns too, not constantly
        if arcade.check_for_collision(self, player) and self.temp_cooldown <= 0:
            self.temp_cooldown = self.damage_cooldown
            player.decrease_health(self.damage)
        else:
            self.temp_cooldown -= 1

        # TODO: Change the Thumper sprite

    def valid_move(self, next_x, next_y):
        # Create a temporary sprite to represent the Thumper at the next position
        temp_sprite = arcade.Sprite(self.texture_name)
        temp_sprite.center_x = next_x
        temp_sprite.center_y = next_y
        temp_sprite.width = self.width
        temp_sprite.height = self.height

        # Check for collision with the obstacle list
        if arcade.check_for_collision_with_list(temp_sprite, self.wall_list):
            return False
        else:
            return True

    def roam(self):
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
            if distance <= THUMPER_MIN_DISTANCE_BEFORE_TARGET:
                self.target_position = None
            else:
                # Update angle
                dx = self.target_position[0] - self.center_x
                dy = self.target_position[1] - self.center_y
                self.update_rotation(dx, dy)
                # Only move if starting to look in the correct direction - agro FOV will do
                if self.is_within_facing_direction(self.target_position, swath_degrees=THUMPER_PASSIVE_FOV):
                    self.center_x += self.speed * math.cos(math.radians(self.rotation))
                    self.center_y += self.speed * math.sin(math.radians(self.rotation))
                    return
                else:
                    self.center_x += self.speed * math.cos(math.radians(self.rotation)) * THUMPER_COLLISION_MS
                    self.center_y += self.speed * math.sin(math.radians(self.rotation)) * THUMPER_COLLISION_MS
                    return

        valid_neighbors = self.get_neighboring_tiles(current_area)
        # Handle no possible movement options: have thumper retrace steps by clearing list
        if len(valid_neighbors) == 0:
            self.visited_areas.clear()
            valid_neighbors = self.get_neighboring_tiles(current_area)
        targeted_position = random.choice(valid_neighbors)
        self.target_position = targeted_position
        self.visited_areas.add(targeted_position)

        # Perform movement
        # Update angle
        dx = self.target_position[0] - self.center_x
        dy = self.target_position[1] - self.center_y
        self.update_rotation(dx, dy)
        # Only move if starting to look in the correct direction - agro FOV will do
        if self.is_within_facing_direction(self.target_position, swath_degrees=THUMPER_PASSIVE_FOV):
            self.center_x += self.speed * math.cos(math.radians(self.rotation))
            self.center_y += self.speed * math.sin(math.radians(self.rotation))
        else:
            self.center_x += self.speed * math.cos(math.radians(self.rotation)) * THUMPER_COLLISION_MS
            self.center_y += self.speed * math.sin(math.radians(self.rotation)) * THUMPER_COLLISION_MS

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

    def aggressive_behavior(self, player):
        # Calculate the direction towards the player
        dx = player.center_x - self.center_x
        dy = player.center_y - self.center_y
        target_distance = math.sqrt(dx ** 2 + dy ** 2)
        target_direction = math.degrees(math.atan2(dy, dx))
        # Hitting a wall, turn and stop moving
        if arcade.check_for_collision_with_list(self, self.wall_list):
            self.update_rotation(dx, dy)
            self.speed = 0
        # elif target_distance <= THUMPER_TARGET_DISTANCE:
        #     self.center_x += math.cos(
        #         math.radians(target_direction)) * self.speed
        #     self.center_y += math.sin(
        #         math.radians(target_direction)) * self.speed
        # Move the Thumper in the direction of the player
        elif self.is_within_facing_direction((player.center_x, player.center_y), swath_degrees=THUMPER_AGRO_FOV * 2):
            # Rotate monster to be towards player
            self.update_rotation(dx, dy)
            self.center_x += math.cos(math.radians(target_direction)) * self.speed
            self.center_y += math.sin(math.radians(target_direction)) * self.speed
            # Only increase speed while looking at player
            self.speed += THUMPER_MOVEMENT_SPEED_INCREASE_RATE

        else:
            # No movement, reset velocity
            self.update_rotation(dx, dy)
            if self.speed > 0:
                self.speed -= THUMPER_MOVEMENT_DELAY_RATE
            else:
                self.speed = 0

            # self.movement_delay = THUMPER_MOVEMENT_DELAY

    def look_for_player(self, player, swath):
        # Determine if there is a clear possible line of sight to the player
        line_of_sight = is_clear_line_of_sight(player.center_x, player.center_y, self.center_x,
                                               self.center_y, self.wall_list)
        # If no possible clear line of sight, return
        if not line_of_sight:
            return False
        if self.is_within_facing_direction([player.center_x, player.center_y], swath_degrees=swath):
            # The thumper can see the player and has a clear line of sight
            return True
        return False

    def is_within_facing_direction(self, target_position, swath_degrees=30):
        """
        Check if the Thumper's rotation direction is looking at the player.
        """
        # Calculate the angle from the Thumper to the target in radians
        dx = target_position[0] - self.center_x
        dy = target_position[1] - self.center_y
        angle_to_target = math.atan2(dy, dx)

        # Calculate the difference between the Thumper's facing direction and the angle to the target
        angle_diff = math.degrees(angle_to_target) - self.rotation

        # Normalize the angle difference to be within the range of -180 and 180 degrees
        angle_diff = (angle_diff + 180) % 360 - 180

        # Check if the absolute angle difference is within the swath degrees
        return abs(angle_diff) <= swath_degrees

    def update_rotation(self, x_direction, y_direction):
        """
        This is needed for updating the monster's rotation (important for thumper) based on movement direction
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
        if min(diff_clockwise, diff_counterclockwise) < THUMPER_ROTATION_RATE:
            rotation_rate = THUMPER_ROTATION_RATE / 2
            # Decrease again if closer
            if min(diff_clockwise, diff_counterclockwise) < THUMPER_ROTATION_RATE / 2:
                rotation_rate = THUMPER_ROTATION_RATE / 4
        else:
            rotation_rate = THUMPER_ROTATION_RATE

        # Adjust rotation
        if current_rotation != target_direction:
            self.rotation += rotation_direction * rotation_rate
            # Only update hitbox if rotation has changed
            # Have to create a new sprite each time for the angle is only supplied during creation
            self.hit_box = rotate_hit_box(arcade.Sprite(self.texture_name).hit_box, self.rotation)

    def draw_self(self):
        # Draw the thumper rotated to its movement direction

        # increment the animation counter
        if self.movement_speed:
            self.steps += self.movement_speed


        if self.steps > self.texture_change_cooldown:
            self.texture_number = (self.texture_number + 1) % len(self.anim_cycle)
            self.steps = 0

        arcade.draw_texture_rectangle(self.center_x, self.center_y, self.texture.width * self.scale,
                                      self.texture.height * self.scale, self.anim_cycle[self.texture_number], self.rotation)

#
# # Constants
# SPIDER_ROTATION_RATE = 2
# SPIDER_PASSIVE_FOV = 10
# SPIDER_AGRO_FOV = 30
# SPIDER_CHASE_FOV = 160  # Only can't see right behind them
# # Spider has 4 states: wandering the map, actively seeing the player and running at them,
# # spinning webs, and freezing if it sees the player
# SPIDER_AGRO_STATES = {"wander": 1, "aggressive": 2, "brokenWeb": 3, "freeze": 4}
# AGRO_METER_MAX = 30  Might not be needed
# AGRO_DRAIN = 1
# SPIDER_MAX_WEBS = 7
#
# SPIDER_BASE_MOVEMENT_SPEED = 1
# SPIDER_COLLISION_MS = 1 / 3
# SPDIER_MOVEMENT_SPEED_INCREASE_RATE = 0.2
# TILE_SIZE = 256  # Spider search pattern based on room tiles
# TILE_CENTER_CONST = 128
# SPIDER_BASE_TURN_SIZE = 90
#
# # Minimum distance to target node before finding new position
# SPIDER_MIN_DISTANCE_BEFORE_TARGET = 20
# SPIDER_MOVEMENT_DELAY = 10
# SPIDER_MOVEMENT_DELAY_RATE = 0.01
#
# SPIDER_TARGET_DISTANCE = 20
# SPIDER_TARGET_DELAY_RATE = 1
#
# class Spider(Enemy):
#     def __init__(self):
#         super().__init__()
#         self.webs = []
#         self.state = SPIDER_AGRO_STATES["wander"]
#         self.has_line_of_sight = False
#
#     def setup(self, Type, wall_list, x_start, y_start, moon_name):
#         super().setup(Type, wall_list, x_start, y_start, moon_name)
#         current_area = (self.center_x // TILE_SIZE, self.center_y // TILE_SIZE)
#         # Get the current position based on center of tile - possibly use this in future code based off bug testing
#         self.current_position = (current_area[0] * TILE_SIZE + TILE_CENTER_CONST,
#                                  current_area[1] * TILE_SIZE + TILE_CENTER_CONST)
#
#     def update_monster(self, player):
#         if self.health <= 0:
#             Monster dead, no more movement or damage
#             self.damage = 0
#             return
#         self.physics_engine.update()
#
#         # Deal damage to player if interacting with them - regardless of the state the thumper is in
#         # Deal damage in cooldowns too, not constantly
#         if arcade.check_for_collision(self, player) and self.temp_cooldown <= 0:
#             self.temp_cooldown = self.damage_cooldown
#             player.decrease_health(self.damage)
#         else:
#             self.temp_cooldown -= 1
#
#         if len(self.webs) >= SPIDER_MAX_WEBS or 
#                                       math.sqrt((player.center_x - self.center_x) ** 2 + (player.center_y - self.center_y) ** 2) <= SPIDER_TARGET_DISTANCE:
#             self.state = SPIDER_AGRO_STATES["freeze"]
#             self.movement_speed = 0
#
#         if self.agro_state == SPIDER_AGRO_STATES["wander"] or self.agro_state == SPIDER_AGRO_STATES["freeze"]:
#            self.check_broken_webs()
#
#
#         if self.agro_state == SPIDER_AGRO_STATES["wander"]:
#            # If can see player, become aggressive
#            if self.has_line_of_sight(player, SPIDER_PASSIVE_FOV):
#                if math.sqrt((player.center_x - self.center_x) ** 2 + (player.center_y - self.center_y) ** 2) <= SPIDER_MIN_TARGET_DISTANCE:
#                  self.agro_state = SPIDER_AGRO_STATES["aggressive"]
#                  self.speed = SPIDER_BASE_MOVEMENT_SPEED / 2  # half movement speed when seeing the player
#                  # This is steadily increased while chasing player
#                #Freeze if spider can see the player, but the player is not close enough to aggro 
#                else:
#                   self.agro_state = SPIDER_AGRO_STATES["freeze"]
#                
#            # Roaming behavior - updates rotation and position
#            self.roam()
#
#           elif self.agro_state == SPIDER_AGRO_STATES["aggressive"]:
#            # If can't see player, start searching for player
#            dx = player.center_x - self.center_x
#            dy = player.center_y - self.center_y
#            target_distance = math.sqrt(dx ** 2 + dy ** 2)
#            # If entering distance to player
#            if (arcade.check_for_collision(self,
#                                           player) or target_distance <= SPIDER_TARGET_DISTANCE) and not self.in_distance:
#                self.movement_delay = SPIDER_MOVEMENT_DELAY
#                self.in_distance = True
#            else:
#                self.in_distance = False
#            if self.movement_delay > 0:
#                # continue moving past player if in them
#                if arcade.check_for_collision_with_list(self, self.wall_list):
#                    self.update_rotation(dx, dy)
#                    self.speed = 0
#                else:
#                    self.update_rotation(dx, dy)
#                    self.center_x += self.speed * math.cos(math.radians(self.rotation))
#                    self.center_y += self.speed * math.sin(math.radians(self.rotation))
#                    if self.speed > 0 and not self.in_distance:
#                        self.speed -= SPIDER_MOVEMENT_SPEED_INCREASE_RATE / SPIDER_COLLISION_MS
#                self.movement_delay -= SPIDER_TARGET_DELAY_RATE
#            # Aggressive search behavior
#            elif not self.has_line_of_sight(player, SPIDER_CHASE_FOV):
#                self.visited_areas.clear()
#               self.target_position = player.position
#                if self.speed > SPIDER_BASE_MOVEMENT_SPEED:
#                    self.speed -= SPIDER_MOVEMENT_DELAY_RATE
#                else:
#                    self.speed += SPIDER_MOVEMENT_DELAY_RATE
#           else:
#               self.agro_state = SPIDER_AGRO_STATES["wander"]
#
#     def roam(self):
#         # Check to set new areas
#         current_area = (self.center_x // TILE_SIZE, self.center_y // TILE_SIZE)
#         # Get the current position based on center of tile - possibly use this in future code based off bug testing
#         self.current_position = (current_area[0] * TILE_SIZE + TILE_CENTER_CONST,
#                                  current_area[1] * TILE_SIZE + TILE_CENTER_CONST)
#
#         # First check if there is a target position, and move towards it
#         if self.target_position is not None:
#             # Check to see if within a certain distance of target position
#             distance = math.sqrt((self.target_position[0] - self.center_x) ** 2 +
#                                  (self.target_position[1] - self.center_y) ** 2)
#             if distance <= SPIDER_MIN_DISTANCE_BEFORE_TARGET:
#                 self.target_position = None
#             else:
#                 # Update angle
#                 dx = self.target_position[0] - self.center_x
#                 dy = self.target_position[1] - self.center_y
#                 self.update_rotation(dx, dy)
#                 # Only move if starting to look in the correct direction - agro FOV will do
#                 if self.is_within_facing_direction(self.target_position, swath_degrees=SPIDER_PASSIVE_FOV):
#                     self.center_x += self.speed * math.cos(math.radians(self.rotation))
#                     self.center_y += self.speed * math.sin(math.radians(self.rotation))
#                     return
#                 else:
#                     self.center_x += self.speed * math.cos(math.radians(self.rotation)) * SPIDER_COLLISION_MS
#                     self.center_y += self.speed * math.sin(math.radians(self.rotation)) * SPIDER_COLLISION_MS
#                     return
#
#         valid_neighbors = self.get_neighboring_tiles(current_area)
#         # Handle no possible movement options: have Spider place a web and retrace steps by clearing list
#         if len(valid_neighbors) == 0:
#             if len(self.webs) < MAX_WEBS:
#                 self.place_web()
#             self.visited_areas.clear()
#             valid_neighbors = self.get_neighboring_tiles(current_area)
#         targeted_position = random.choice(valid_neighbors)
#         self.target_position = targeted_position
#         self.visited_areas.add(targeted_position)
#
#         # Perform movement
#         # Update angle
#         dx = self.target_position[0] - self.center_x
#         dy = self.target_position[1] - self.center_y
#         self.update_rotation(dx, dy)
#         # Only move if starting to look in the correct direction - agro FOV will do
#         if self.is_within_facing_direction(self.target_position, swath_degrees=SPIDER_PASSIVE_FOV):
#             self.center_x += self.speed * math.cos(math.radians(self.rotation))
#             self.center_y += self.speed * math.sin(math.radians(self.rotation))
#         else:
#             self.center_x += self.speed * math.cos(math.radians(self.rotation)) * SPIDER_COLLISION_MS
#             self.center_y += self.speed * math.sin(math.radians(self.rotation)) * SPIDER_COLLISION_MS
#
#     def get_neighboring_tiles(self, current_tile):
#         # Generate the positions of the four neighboring tiles
#         neighbors = [
#             (current_tile[0], current_tile[1] + 1),  # Above
#             (current_tile[0], current_tile[1] - 1),  # Below
#             (current_tile[0] - 1, current_tile[1]),  # Left
#             (current_tile[0] + 1, current_tile[1])  # Right
#         ]
#
#         scaled_current_tile = [current_tile[0] * TILE_SIZE + TILE_CENTER_CONST,
#                                current_tile[1] * TILE_SIZE + TILE_CENTER_CONST]
#         valid_neighbors = []
#         for area in neighbors:
#             if area not in self.visited_areas:
#                 # determine where the position of the next tile is and decide line of sight
#                 potentional_position = (area[0] * TILE_SIZE + TILE_CENTER_CONST,
#                                         area[1] * TILE_SIZE + TILE_CENTER_CONST)
#                 if is_clear_line_of_sight(scaled_current_tile[0], scaled_current_tile[1], potentional_position[0],
#                                           potentional_position[1], self.wall_list):
#                     valid_neighbors.append(potentional_position)
#         return valid_neighbors
#
#     #Checks to see if a web is broken
#     #Returns the first web that is broken
#     #Or returns none
#     def check_broken_webs(self):
#         for web in self.webs:
#             if web.is_broken_web():
#                 return web
#         return None
#
#      def has_line_of_sight(self, player, swath):
#         # Determine if there is a clear possible line of sight to the player
#         line_of_sight = is_clear_line_of_sight(player.center_x, player.center_y, self.center_x,
#                                                self.center_y, self.wall_list)
#         # If no possible clear line of sight, return false
#         if not line_of_sight:
#             return False
#         if self.is_within_facing_direction([player.center_x, player.center_y], swath_degrees=swath):
#             # The spider can see the player and has a clear line of sight
#             return True
#         return False
#
#     def is_within_facing_direction(self, target_position, swath_degrees=30):
#         """
#         Check if the spider's rotation direction is looking at the player.
#         """
#         # Calculate the angle from the Thumper to the target in radians
#         dx = target_position[0] - self.center_x
#         dy = target_position[1] - self.center_y
#         angle_to_target = math.atan2(dy, dx)
#
#         # Calculate the difference between the Thumper's facing direction and the angle to the target
#         angle_diff = math.degrees(angle_to_target) - self.rotation
#
#         # Normalize the angle difference to be within the range of -180 and 180 degrees
#         angle_diff = (angle_diff + 180) % 360 - 180
#
#         # Check if the absolute angle difference is within the swath degrees
#         return abs(angle_diff) <= swath_degrees
#
#
#
#    def update_rotation(self, x_direction, y_direction):
#        """
#        This is needed for updating the monster's rotation (important for Spider) based on movement direction
#        Called from update_monster method
#        """
#        # Calculate target direction using arctan
#        target_direction = math.degrees(math.atan2(y_direction, x_direction))
#
#        # Normalize target direction to be in the range [0, 360) (arctan is in range -180 to 180)
#        target_direction = (target_direction + 360) % 360
#        current_rotation = self.rotation % 360
#
#        # Calculate the absolute difference between target direction and current rotation
#        diff_clockwise = (target_direction - current_rotation) % 360
#        diff_counterclockwise = (current_rotation - target_direction) % 360
#
#        # Determine the direction (clockwise or counterclockwise) to rotate
#        if diff_clockwise <= diff_counterclockwise:
#            rotation_direction = 1  # Rotate clockwise
#        else:
#            rotation_direction = -1  # Rotate counterclockwise
#
#        # Adjust rotation rate if rotation is close to target (reduce stuttering
#        if min(diff_clockwise, diff_counterclockwise) < SPIDER_ROTATION_RATE:
#            rotation_rate = SPIDER_ROTATION_RATE / 2
#            # Decrease again if closer
#            if min(diff_clockwise, diff_counterclockwise) < SPIDER_ROTATION_RATE / 2:
#                rotation_rate = SPIDER_ROTATION_RATE / 4
#        else:
#            rotation_rate = SPIDER_ROTATION_RATE
#
#        # Adjust rotation
#        if current_rotation != target_direction:
#            self.rotation += rotation_direction * rotation_rate
#            # Only update hitbox if rotation has changed
#            # Have to create a new sprite each time for the angle is only supplied during creation
#            self.hit_box = rotate_hit_box(arcade.Sprite(self.texture_name).hit_box, self.rotation)
#
#       #Makes a web and adds it to the webs list
#       def make_web(self):
#           self.webs.append(new Web(self.center_x, self.center_y))
#
#
#       def draw_self(self):
#        # Draw the thumper rotated to its movement direction
#        arcade.draw_texture_rectangle(self.center_x, self.center_y, self.texture.width * self.scale,
#                                      self.texture.height * self.scale, self.texture, self.rotation)
#
#
#
# Class Web(sprite):
#   def __init__(self):
#       super.__init__():
#       self.center_x = 0
#       self.center_y = 0
#       self.texture = None
#       self.is_broken = False
#       self.payer_entered = False
#   def setup(self,  center_x, center_y):       
#       with open("resources/monsters.json", "r") as file:
#           data_from_json = json.load(file)
#               self.texture = data_from_json["indoors"]["Web"]["base_texture"]
#       file.close()
#   
#   def update(self):
#       self.is_broken_web()
#       if self.is_broken:
#           data_from_json = json.load(file)
#               self.texture = data_from_json["indoors"]["Web"]["broken_texture"]
#           file.close()
#       self.check_player_overlap(self, player)
#       if self.player_entered and not arcade.check_for_collision(self, player):
#           self.is_broken = True
#       
#   def check_player_overlap(self, player):
#       if arcade.check_for_collision(self, player):
#           self.player_entered = True
#           return True
#       return False
# 
#   def is_broken_web(self):
#       return self.is_broken 
#     
#   def on_draw(self):
#       arcade.draw(self.texture)  
