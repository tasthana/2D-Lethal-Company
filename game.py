"""
CS 3050 Team 5

"""
import sys

import arcade
from arcade.experimental.lights import Light, LightLayer

import math

import player
from room import Room
from map import Map, gen_outdoor_spawners
from player import PlayerCharacter, MAX_STAM, MAX_HEALTH
from item import Item, Shovel, Lantern
from utility_functions import euclidean_distance, calculate_direction_vector_negative, is_within_facing_direction
from game_loop_utilities import increase_quota
from ship import Ship, SHIP_INTERACTION_OPTIONS, GAMESTATE_OPTIONS
from indoor_enemies import Enemy, Thumper
from time import time
import random

import cProfile, pstats, io
from pstats import SortKey

import json

# Constants
SCREEN_WIDTH = 1000
SCREEN_HEIGHT = 650
BACKGROUND_SCROLL_SPEED = 1
BACKGROUND_SHIFT = 300

PLAYER_SHIP_SHIFT_X = 64
PLAYER_SHIP_SHIFT_Y = 128

SCREEN_TITLE = "2D Lethal Company"

# Starting location of the player, and movement constants
PLAYER_START_X = 500
PLAYER_START_Y = 500
STAM_DRAIN = 0.17  # set to match game
BASE_MOVEMENT_SPEED = 2
SPRINT_DELAY = 30

# delay for entering and leaving building
ENTER_EXIT_DELAY = 50

# Game loop variables
INITIAL_QUOTA = 130
MAX_DAYS = 3

TILE_SCALING = 0.5

# Time constants
MS_PER_SEC = 1000
SEC_PER_MIN = 60
MIN_PER_HOUR = 60
SEC_PER_HOUR = SEC_PER_MIN * MIN_PER_HOUR
# Time passes slightly faster in game than irl - one second is a bit more than a minute
# 1.6 means 16 hours in 10 minutes
TIME_RATE_INCREASE = 1.6
DAY_LENGTH = 10 * SEC_PER_MIN * MS_PER_SEC
AMBIENT_COLOR = (5, 5, 5)
DARK_AMBIENT_COLOR = (0, 0, 0)

# Screens
START_SCREEN = 0
GAME_SCREEN = 1
RESET_SCREEN = 2
DEATH_SCREEN = 3
# PAUSE_SCREEN = 4 
current_screen = START_SCREEN

PAUSE_CONTROL_X_SHIFT = 256
PAUSE_CONTROL_Y_SHIFT = -175


class LethalGame(arcade.Window):
    """
    Main class for running the game
    """

    def __init__(self):
        """
        Initializer
        """
        # Call the parent class and set up the window
        super().__init__(SCREEN_WIDTH, SCREEN_HEIGHT, SCREEN_TITLE)

        arcade.enable_timings()

        # start screen button variables
        self.button_x = SCREEN_WIDTH // 3
        self.button_y = SCREEN_HEIGHT // 3
        self.button_width = 250
        self.button_height = 50
        self.mouse_x = SCREEN_WIDTH // 3
        self.mouse_y = SCREEN_WIDTH // 3
        self.current_screen = START_SCREEN
        self.show_reset_screen = False
        self.reset_screen_timer = None
        self.player_dead = False
        self.show_death_screen = False
        self.death_screen_timer = None
        self.pause_screen_visible = False

        # Initialize variables for spawning / map / other important variables
        self.gamestate = GAMESTATE_OPTIONS["orbit"]
        self.moon_name = "experimentation"
        self.indoor_map = None
        self.indoor_walls = None
        self.indoor_main_position = None
        self.indoor_main_bounding_box = None
        self.outdoor_starting_position = None
        self.outdoor_main_position = None

        self.ship = Ship().setup()

        self.orbit_background = arcade.Sprite("resources/tilemaps/orbit_background.png")
        self.orbit_background.center_x = self.ship.center_x
        self.orbit_background.center_y = self.ship.center_y - self.orbit_background.height // 2 + SCREEN_HEIGHT // 2 + BACKGROUND_SHIFT

        self.outdoor_map = None
        self.outdoor_walls = None
        self.outdoor_main_box = None

        self.player = PlayerCharacter()
        self.player.center_x = self.ship.center_x + PLAYER_SHIP_SHIFT_X
        self.player.center_y = self.ship.center_y + PLAYER_SHIP_SHIFT_Y
        self.inventory_hud = None

        self.indoor_enemy_entities = None
        self.outdoor_enemy_entities = None

        self.indoor_loot_items = None
        self.outdoor_loot_items = arcade.SpriteList()

        self.mines = None
        self.armed_mines = None
        self.turrets = None
        self.bullets = None

        self.indoor_spawners = None
        self.outdoor_spawners = None

        self.indoor_physics_engine = None
        self.outdoor_physics_engine = None
        self.ship_physics_engine = None

        # GUI variables
        # Set up the Camera
        self.camera = arcade.Camera(self.width, self.height)
        # Instead of using a scene, it may also be easier to just keep a sprite list
        # for each individual thing.
        # self.scene = None

        # Movement / inventory variables
        self.left_pressed = False
        self.right_pressed = False
        self.up_pressed = False
        self.down_pressed = False

        self.shift_pressed = False
        self.pressed_1 = False
        self.pressed_2 = False
        self.pressed_3 = False
        self.pressed_4 = False
        self.e_pressed = False
        self.g_pressed = False
        self.h_pressed = False
        self.q_pressed = False
        self.esc_pressed = False

        self.sprinting = False
        self.delaying_stam = False

        self.delay_main_enter_exit = ENTER_EXIT_DELAY

        # Inventory slots
        self.try_pickup_item = False
        self.drop_item = False

        # Set power levels - has to do with spawning mechanics
        self.indoor_power = None  # experimentation-40 levels
        self.outdoor_power = None

        # Game loop settings - some of these are off of the given ones from the wiki
        # https://lethal-company.fandom.com/wiki/Profit_Quota
        self.quota = INITIAL_QUOTA
        self.quotas_hit = 0
        self.days_left = MAX_DAYS
        self.quota_hud_sprite = arcade.Sprite("resources/player_sprites/quota_hud_box.png")
        self.day_hud_sprite = arcade.Sprite("resources/player_sprites/day_hud_box.png")
        self.zero_day_sprite = arcade.Sprite("resources/player_sprites/no_day_left.png")
        self.scrap_sold = 0
        self.sell_list = arcade.SpriteList()

        # Initialize time variables
        self.start_time = None
        self.delta_time = None
        self.time_hud_sprite = arcade.Sprite("resources/player_sprites/time_hud_box.png")

        self.last_terminal_output = None
        self.terminal_background = arcade.Sprite("resources/player_sprites/terminal_background.png")
        self.terminal_background.alpha = 128

        self.pause_background = arcade.Sprite("resources/screens/pause_background.png")
        self.pause_background.alpha = 128

        self.company_building = arcade.Scene.from_tilemap(arcade.load_tilemap("resources/tilemaps/company.tmx"))
        self.company_starting_position = (720, 640)
        self.company_physics_engine = arcade.PhysicsEnginePlatformer(
            self.player, self.company_building["walls"]
        )
        self.company_physics_engine.gravity_constant = 0

        # Layer for the lights on the map
        self.indoor_light_layer = LightLayer(SCREEN_WIDTH, SCREEN_HEIGHT)
        self.indoor_light_layer.set_background_color(arcade.color.BLACK)

        self.indoor_light_layer.add(self.player.player_indoor_light)
        self.indoor_light_layer.add(self.player.player_scan_light)

        self.outdoor_light_layer = LightLayer(SCREEN_WIDTH, SCREEN_HEIGHT)
        self.outdoor_light_layer.set_background_color(arcade.color.BLACK)

        self.outdoor_light_layer.add(self.player.player_outdoor_light)
        self.outdoor_light_layer.add(self.ship.ship_light)
        self.outdoor_light_layer.add(self.player.player_scan_light)

    def reset_game(self):
        """
        Reset the game, different than init
        """
        # start screen button variables
        self.button_x = SCREEN_WIDTH // 3  # X-coordinate of the button
        self.button_y = SCREEN_HEIGHT // 3  # Y-coordinate of the button
        self.button_width = 100  # Width of the button
        self.button_height = 50  # Height of the button
        self.mouse_x = SCREEN_WIDTH // 3  # Initial mouse X-coordinate
        self.mouse_y = SCREEN_WIDTH // 3  # Initial mouse Y-coordinate
        # self.current_screen = START_SCREEN

        # Initialize variables for spawning / map / other important variables
        self.gamestate = GAMESTATE_OPTIONS["orbit"]
        self.moon_name = "experimentation"
        self.indoor_map = None
        self.indoor_walls = None
        self.indoor_main_position = None
        self.indoor_main_bounding_box = None
        self.outdoor_starting_position = None
        self.outdoor_main_position = None

        self.ship = Ship().setup()

        self.orbit_background = arcade.Sprite("resources/tilemaps/orbit_background.png")
        self.orbit_background.center_x = self.ship.center_x
        self.orbit_background.center_y = self.ship.center_y - self.orbit_background.height // 2 + SCREEN_HEIGHT // 2 + BACKGROUND_SHIFT

        self.outdoor_map = None
        self.outdoor_walls = None
        self.outdoor_main_box = None

        self.player = PlayerCharacter()
        self.player.center_x = self.ship.center_x + PLAYER_SHIP_SHIFT_X
        self.player.center_y = self.ship.center_y + PLAYER_SHIP_SHIFT_Y
        self.inventory_hud = None

        self.indoor_enemy_entities = None

        self.indoor_loot_items = None
        self.outdoor_loot_items = arcade.SpriteList()

        self.mines = None
        self.armed_mines = None
        self.turrets = None
        self.bullets = None

        self.indoor_spawners = None
        self.outdoor_spawners = None

        self.indoor_physics_engine = None
        self.outdoor_physics_engine = None
        self.ship_physics_engine = None

        # GUI variables
        # Set up the Camera
        # self.camera = arcade.Camera(self.width, self.height)
        # Instead of using a scene, it may also be easier to just keep a sprite list
        # for each individual thing.
        # self.scene = None

        # Movement / inventory variables
        self.left_pressed = False
        self.right_pressed = False
        self.up_pressed = False
        self.down_pressed = False

        self.shift_pressed = False
        self.pressed_1 = False
        self.pressed_2 = False
        self.pressed_3 = False
        self.pressed_4 = False
        self.e_pressed = False
        self.g_pressed = False
        self.h_pressed = False
        self.q_pressed = False

        self.sprinting = False
        self.delaying_stam = False

        self.delay_main_enter_exit = ENTER_EXIT_DELAY

        # Inventory slots
        self.try_pickup_item = False
        self.drop_item = False

        # Set power levels - has to do with spawning mechanics
        self.indoor_power = None  # experimentation-40 levels
        self.outdoor_power = None

        # Game loop settings - some of these are off of the given ones from the wiki
        # https://lethal-company.fandom.com/wiki/Profit_Quota
        self.quota = INITIAL_QUOTA
        self.quotas_hit = 0
        self.days_left = MAX_DAYS
        self.quota_hud_sprite = arcade.Sprite("resources/player_sprites/quota_hud_box.png")
        self.day_hud_sprite = arcade.Sprite("resources/player_sprites/day_hud_box.png")
        self.zero_day_sprite = arcade.Sprite("resources/player_sprites/no_day_left.png")
        self.scrap_sold = 0
        self.sell_list = arcade.SpriteList()

        # Initialize time variables
        self.start_time = None
        self.delta_time = None
        self.time_hud_sprite = arcade.Sprite("resources/player_sprites/time_hud_box.png")

        self.last_terminal_output = None
        self.terminal_background = arcade.Sprite("resources/player_sprites/terminal_background.png")
        self.terminal_background.alpha = 128

        self.company_building = arcade.Scene.from_tilemap(arcade.load_tilemap("resources/tilemaps/company.tmx"))
        self.company_starting_position = (720, 640)
        self.company_physics_engine = arcade.PhysicsEnginePlatformer(
            self.player, self.company_building["walls"]
        )
        self.company_physics_engine.gravity_constant = 0

        # Layer for the lights on the map
        self.indoor_light_layer = LightLayer(SCREEN_WIDTH, SCREEN_HEIGHT)
        self.indoor_light_layer.set_background_color(arcade.color.BLACK)

        self.indoor_light_layer.add(self.player.player_indoor_light)
        self.indoor_light_layer.add(self.player.player_scan_light)

        self.outdoor_light_layer = LightLayer(SCREEN_WIDTH, SCREEN_HEIGHT)
        self.outdoor_light_layer.set_background_color(arcade.color.BLACK)

        self.outdoor_light_layer.add(self.player.player_outdoor_light)
        self.outdoor_light_layer.add(self.ship.ship_light)
        self.outdoor_light_layer.add(self.player.player_scan_light)

    def setup(self, moons_name):
        self.moon_name = moons_name
        # add players health on setup
        self.player.add_health(player.MAX_HEALTH)
        self.player.reset_light()
        # Set up the map, using procgen and the map class (passed in as parameters
        # Ideally this would work using some sort of arcade.load_tilemap(map_name)
        # if we use this we need to use layers for the physics engine, otherwise add
        # all walls to the walls list
        self.indoor_map = Map(self.moon_name)  # Will update later based on start screen inputs
        self.indoor_map.setup()

        # get the walls from the map
        self.indoor_walls = self.indoor_map.get_walls()
        self.indoor_loot_items = self.indoor_map.get_loot_list()
        self.mines = self.indoor_map.get_mines()
        self.armed_mines = arcade.SpriteList()
        self.turrets = self.indoor_map.get_turrets()
        self.bullets = arcade.SpriteList()

        # Again, update later to be from user input
        map_settings = self.indoor_map.get_map_data()
        self.outdoor_map = arcade.Scene.from_tilemap(arcade.load_tilemap(map_settings[0]))
        self.outdoor_starting_position = map_settings[1]
        self.indoor_power = map_settings[2]
        self.outdoor_power = map_settings[3]
        self.indoor_main_bounding_box = map_settings[4]
        self.outdoor_main_position = map_settings[5]

        self.ship.change_outdoors(self.outdoor_map)

        self.outdoor_light_layer.add(self.ship.ship_light)

        # Initialize player character
        self.indoor_main_position = self.indoor_map.get_player_start()
        # Add logic for starting location of player (from outdoors)
        self.player.center_x = self.outdoor_starting_position[0]
        self.player.center_y = self.outdoor_starting_position[1]
        # self.player.center_x = -20
        # self.player.center_y = -20
        self.player.set_movement_speed(BASE_MOVEMENT_SPEED)  # speed is pixels per frame

        # Just doesn't work to snap camera instantly
        self.center_camera_to_player(100)

        self.inventory_hud = arcade.SpriteList()
        # Add the four sprite items to the list
        for i in range(4):
            temp_sprite = arcade.Sprite("resources/item_sprites/inventory_box.png", scale=0.55)
            self.inventory_hud.append(temp_sprite)

        self.indoor_enemy_entities = []
        self.outdoor_enemy_entities = []

        # Set background color to be black
        arcade.set_background_color(arcade.color.DARK_GRAY)

        # Create indoor physics engine - we can use the platformer without gravity to get the intended effect
        self.indoor_physics_engine = arcade.PhysicsEnginePlatformer(
            self.player, walls=self.indoor_walls
        )
        self.indoor_physics_engine.gravity_constant = 0

        # Create outdoor physics engine - we can use the platformer without gravity to get the intended effect
        self.outdoor_physics_engine = arcade.PhysicsEnginePlatformer(
            self.player, self.outdoor_map["walls"]
        )
        self.outdoor_physics_engine.gravity_constant = 0

        # Separate physics engine for teh ship - can be used outdoors and in orbit
        self.ship_physics_engine = arcade.PhysicsEnginePlatformer(
            self.player, self.ship.get_walls()
        )
        self.ship_physics_engine.gravity_constant = 0

        # self.gamestate = GAMESTATE_OPTIONS["outdoors"] # Change once ship implemented

        # Ship update position uses delta_x and y
        ship_position = self.ship.get_pos()
        self.ship.update_position(self.outdoor_starting_position[0] - 64 - ship_position[0],
                                  self.outdoor_starting_position[1] - 128 - ship_position[1])

        self.indoor_light_layer = LightLayer(SCREEN_WIDTH, SCREEN_HEIGHT)
        self.indoor_light_layer.set_background_color(arcade.color.BLACK)

        self.indoor_light_layer.add(self.player.player_indoor_light)
        self.indoor_light_layer.add(self.player.player_scan_light)

        self.outdoor_light_layer = LightLayer(SCREEN_WIDTH, SCREEN_HEIGHT)
        self.outdoor_light_layer.set_background_color(arcade.color.BLACK)

        self.outdoor_light_layer.add(self.player.player_outdoor_light)
        self.outdoor_light_layer.add(self.ship.ship_light)
        self.outdoor_light_layer.add(self.player.player_scan_light)

        # Set starting time
        self.start_time = get_time()
        self.delta_time = get_time() - self.start_time  # clearly will start low, but is same way to update later

    def on_draw(self):
        """
        Render the screen
        """

        # Clear the screen
        self.clear()

        # print fps to console
        # print(arcade.get_fps(60))

        """
        FUTURE: May need to add another state for landing, to animate the ship
        """
        button_x = 100
        mouse_x = 50
        if self.current_screen == START_SCREEN:
            self.camera.move_to((0, 0), 1)
            self.draw_start_screen()

        elif self.current_screen == GAME_SCREEN:
            # Draw elements for other screens (e.g., game screen, indoor/outdoor screens)
            self.camera.use()
            # Draw orbit background
            if self.gamestate == GAMESTATE_OPTIONS["orbit"]:
                self.orbit_background.draw()
                if self.orbit_background.top > self.ship.center_y - SCREEN_HEIGHT // 2 - BACKGROUND_SHIFT + self.orbit_background.height // 2:
                    self.orbit_background.center_y = self.ship.center_y - self.orbit_background.height // 2 + SCREEN_HEIGHT // 2 + BACKGROUND_SHIFT
                self.orbit_background.center_y += 1
            # Draw the scene depending on indoors or outdoors
            if self.gamestate == GAMESTATE_OPTIONS["orbit"] or self.gamestate == GAMESTATE_OPTIONS["company"]:
                self.ship.draw_self(self.camera, self.gamestate, self.player, self.pause_screen_visible)
                if self.gamestate == GAMESTATE_OPTIONS["company"]:
                    self.company_building.draw()
                    self.ship.draw_self(self.camera, self.gamestate, self.player, self.pause_screen_visible)
                    for item in self.outdoor_loot_items:
                        item.draw_self()
                    for item in self.sell_list:
                        item.draw_self()

                if not self.ship.player_interacting_with_terminal and not self.pause_screen_visible:
                    # Draw correct days left (red if zero)
                    time_text_x = self.camera.position[0] + SCREEN_WIDTH / 2
                    time_text_y = self.camera.position[1] + SCREEN_HEIGHT - 32
                    if self.days_left > 0:
                        sprite = self.day_hud_sprite
                        sprite.center_x = time_text_x - 128
                        sprite.center_y = time_text_y
                        sprite.draw()
                        color = arcade.csscolor.GREEN
                        arcade.draw_text(f"{self.days_left} days left", sprite.center_x - 38, sprite.center_y - 6,
                                         color,
                                         12)
                    elif self.days_left < 0:
                        self.current_screen = RESET_SCREEN
                    else:
                        sprite = self.zero_day_sprite
                        sprite.center_x = time_text_x - 128
                        sprite.center_y = time_text_y
                        sprite.draw()

                        color = arcade.csscolor.RED
                        arcade.draw_text(f"{self.days_left} days left", sprite.center_x - 38, sprite.center_y - 6,
                                         color,
                                         12)

                    self.quota_hud_sprite.center_x = time_text_x
                    self.quota_hud_sprite.center_y = time_text_y
                    self.quota_hud_sprite.draw()

                    # Draw the days left
                    arcade.draw_text(f"Quota: {self.quota}", self.quota_hud_sprite.center_x - 42,
                                     self.quota_hud_sprite.center_y - 6, arcade.csscolor.GREEN,
                                     12)
                    self.quota_hud_sprite.center_x = time_text_x + 128
                    self.quota_hud_sprite.center_y = time_text_y
                    self.quota_hud_sprite.draw()
                    arcade.draw_text(f"Sold: {self.scrap_sold}", self.quota_hud_sprite.center_x - 42,
                                     self.quota_hud_sprite.center_y - 6, arcade.csscolor.GREEN,
                                     12)
                self.player.draw_self()

            elif self.gamestate == GAMESTATE_OPTIONS["outdoors"]:
                with self.outdoor_light_layer:
                    # Draw parts of outdoors before player
                    self.outdoor_map["background"].draw()
                    # self.outdoor_map["entrance"].draw() # Don't draw entrance layer
                    self.outdoor_map["walls"].draw()
                    self.ship.draw_self(self.camera, self.gamestate, self.player, self.pause_screen_visible)
                    for item in self.outdoor_loot_items:
                        item.draw_self()
                    self.player.draw_self()
                    for monster in self.outdoor_enemy_entities:
                        monster.draw_self()
                    self.outdoor_map["overhead"].draw()
                self.outdoor_light_layer.draw(ambient_color=AMBIENT_COLOR)

                # draw the time on hud, if the player isn't in the ship
                if not arcade.check_for_collision_with_list(self.player, self.ship.tilemap["background"]) and not self.pause_screen_visible:
                    time_text_x = self.camera.position[0] + SCREEN_WIDTH / 2
                    time_text_y = self.camera.position[1] + SCREEN_HEIGHT - 32
                    self.time_hud_sprite.center_x = time_text_x
                    self.time_hud_sprite.center_y = time_text_y
                    self.time_hud_sprite.draw()
                    # Draw the actual time
                    hours, minutes = ms_to_igt(self.delta_time)
                    arcade.draw_text(f"{hours:02d}:{minutes:02d}", time_text_x - 22, time_text_y - 6,
                                     arcade.csscolor.ORANGE, 12)

            else:  # self.gamestate == GAMESTATE_OPTIONS["indoors"] # equivalent expression

                # TODO: Only draw adjacent rooms
                # calculate adjacent rooms
                # doing this iteratively causes severe performance drops
                # for this to be efficient we'd need to do some GPU parallel processing chicanery
                with self.indoor_light_layer:
                    # Draw each room individually
                    # self.indoor_walls.draw()
                    self.indoor_map.draw_rooms(self.player)

                    for mine in self.mines:
                        if not mine.get_exploded():
                            mine.draw()

                    for armed_mine in self.armed_mines:
                        if armed_mine.get_exploded():
                            # see if the player is within the explosion distance
                            distance = euclidean_distance((self.player.center_x, self.player.center_y),
                                                          (armed_mine.center_x, armed_mine.center_y))
                            if distance <= armed_mine.get_explosion_distance():
                                self.player.decrease_health(armed_mine.get_damage())
                            self.armed_mines.remove(armed_mine)
                        else:
                            armed_mine.draw()

                    # Draw loot after mines but before turrets
                    # self.indoor_loot_items.draw()
                    for item in self.indoor_loot_items:
                        item.draw_self()

                    # draw bullets and turrets at correct angles
                    for bullet in self.bullets:
                        bullet.draw_scaled()
                    for turret in self.turrets:
                        if turret.get_turret_laser() != None:
                            turret.get_turret_laser().draw()
                        turret.draw_scaled()

                    # Draw monsters
                    for monster in self.indoor_enemy_entities:
                        monster.draw_self()

                self.indoor_light_layer.draw(ambient_color=DARK_AMBIENT_COLOR)
                self.player.draw_self()

            # Player needs to be drawn in each specific area (orbit, etc), due to lighting and other constraints
            # self.player.draw_self()

            # Draw the hud sprites
            temp_x = 300
            for slot in range(1, 5):
                if slot == self.player.get_current_inv_slot():
                    sprite = arcade.Sprite("resources/item_sprites/inventory_box.png", scale=0.55)
                else:
                    sprite = arcade.Sprite("resources/item_sprites/inventory_box_non_selected.png", scale=0.55)
                sprite.center_x = self.camera.position[0] + temp_x
                temp_x += 125
                sprite.center_y = self.camera.position[1] + 50
                sprite.alpha = 200
                sprite.draw()

            for idx, item in enumerate(self.player.get_full_inv()):
                if item != None:
                    temp_item = item
                    temp_item.center_x = self.camera.position[0] + 300 + idx * 125
                    temp_item.center_y = self.camera.position[1] + 50
                    # item.set_inventory_texture()
                    # print(item.center_x, item.center_y)
                    temp_item.draw_self()

            # Draw text for holding 2 handed item
            if self.player.get_two_handed():
                holding_text = arcade.Sprite("resources/player_sprites/full_hands.png", scale=0.67)
                holding_text.center_x = self.camera.position[0] + SCREEN_WIDTH // 2 - 12
                holding_text.center_y = self.camera.position[1] + 50
                holding_text.draw()

            # Draw text from ship
            if self.ship.player_interacting_with_terminal:
                self.terminal_background.center_x = self.camera.position[0] + SCREEN_WIDTH / 2
                self.terminal_background.center_y = self.camera.position[1] + SCREEN_HEIGHT / 2
                self.terminal_background.draw()
                arcade.draw_text(f"> {self.ship.terminal_input}", self.camera.position[0] + 50,
                                 self.camera.position[1] + 100, arcade.csscolor.GREEN, 24)
                arcade.draw_text(f"{self.ship.money}", self.camera.position[0] + SCREEN_WIDTH - 100,
                                 self.camera.position[1] + SCREEN_HEIGHT - 55, arcade.csscolor.GREEN, 24)
                base_output, processed_terminal_output = self.ship.read_output()
                if processed_terminal_output != "":
                    arcade.draw_text(processed_terminal_output, self.camera.position[0] + 50,
                                     self.camera.position[1] + SCREEN_HEIGHT - 100, arcade.csscolor.GREEN, 24,
                                     multiline=True, width=850)
            elif self.pause_screen_visible:
                # Draw the pause screen
                self.draw_pause_screen()
            else:
                # Draw the health and stamina on the camera view
                stamina_text = f"Stamina: {int(self.player.get_stam())}"
                weight_text = f"{int(self.player.get_weight())} lb"

                # Calculate the position for objects relative to the camera's position
                text_x = self.camera.position[0] + 20
                text_y = self.camera.position[1] + SCREEN_HEIGHT - 30

                # Draw the text at the calculated position
                # arcade.draw_text(health_text, text_x, text_y, arcade.csscolor.RED, 18)\
                health_sprite = arcade.Sprite(
                    f"resources/player_sprites/player_health_sprite_{int(self.player.get_health() // 25)}.png",
                    scale=0.75)
                health_sprite.center_x = self.camera.position[0] + 75
                health_sprite.center_y = self.camera.position[1] + SCREEN_HEIGHT - 80
                # health_sprite.alpha = 128 # use this to set opacity of objects
                health_sprite.draw()

                # Stamina representation
                arcade.draw_text(stamina_text, text_x, text_y - 150, arcade.csscolor.ORANGE, 18)
                arcade.draw_text(weight_text, text_x, text_y - 180, arcade.csscolor.ORANGE, 18)
        elif self.current_screen == DEATH_SCREEN:
            self.draw_death_screen()
        elif self.current_screen == RESET_SCREEN:
            self.draw_reset_screen()
        # Pause screen functions different than other screens: overlay on game screen
        # elif self.current_screen == PAUSE_SCREEN:
        #     self.draw_pause_screen()

    # TODO: this code needs to be massively simplified
    def process_keychange(self):
        """
        This function is used for changing the state of the player
        """
        # If player is interacting with the terminal, don't allow movement
        if self.ship.player_interacting_with_terminal:
            return

        # Update movement speed if shift is pressed - if sprinting, base movement speed should be doubled
        if not self.delaying_stam and self.shift_pressed and (
                self.up_pressed or self.down_pressed or self.right_pressed or self.left_pressed):
            self.sprinting = self.player.get_stam() > 0
        else:
            self.sprinting = False

        # Set movement speed
        if self.sprinting and not self.delaying_stam:
            self.player.set_movement_speed(BASE_MOVEMENT_SPEED * 2)  # Double speed when sprinting
        else:
            self.player.set_movement_speed(BASE_MOVEMENT_SPEED)

        # Delay stamina regeneration
        if self.delaying_stam:
            if self.player.get_stam() >= SPRINT_DELAY:
                self.delaying_stam = False
        # print(self.delaying_stam, self.sprinting)
        # Handle sprinting and stamina depletion
        if self.sprinting:
            if self.player.get_stam() < 1:
                self.delaying_stam = True
            else:
                # Decrease stamina based on players weight
                stam_drain_amount = STAM_DRAIN
                if self.player.get_weight() != 0:
                    stam_drain_amount *= 1 + 0.01 * self.player.get_weight()
                self.player.decrease_stam(stam_drain_amount)
        else:
            # Regenerate stamina if not sprinting
            if self.player.get_stam() < MAX_STAM:
                self.player.add_stam(STAM_DRAIN / 2)

        # Account for diagonal movement speed
        if self.up_pressed and self.right_pressed or self.down_pressed and self.right_pressed or \
                self.up_pressed and self.left_pressed or self.down_pressed and self.left_pressed:
            # Diagonal movement
            diagonal_speed = self.player.get_movement_speed() * (2 ** 0.5) / 2  # Movement speed for diagonal movement
            self.player.set_movement_speed(diagonal_speed)

        # Adjust speed for outdoors (since for some reason this is twice the speed of orbit and indoors
        if self.gamestate == GAMESTATE_OPTIONS["outdoors"] or self.gamestate == GAMESTATE_OPTIONS["company"]:
            self.player.set_movement_speed(self.player.get_movement_speed() / 2)

        # Account for weight
        if self.player.get_weight() != 0:
            # reverse exponential function to decrease weight
            self.player.set_movement_speed(self.player.get_movement_speed() *
                                           math.exp(-0.01 * self.player.get_weight()))

        # print(self.player.get_movement_speed())
        # Process up/down
        if self.up_pressed and not self.down_pressed:
            self.player.change_y = self.player.get_movement_speed()
        elif self.down_pressed and not self.up_pressed:
            self.player.change_y = -self.player.get_movement_speed()
        else:
            self.player.change_y = 0

        # Process left/right
        if self.right_pressed and not self.left_pressed:
            self.player.change_x = self.player.get_movement_speed()
        elif self.left_pressed and not self.right_pressed:
            self.player.change_x = -self.player.get_movement_speed()
        else:
            self.player.change_x = 0

        # determine the current inventory slot to pull from
        if self.pressed_1:
            self.player.set_current_inv_slot(1)
        elif self.pressed_2:
            self.player.set_current_inv_slot(2)
        elif self.pressed_3:
            self.player.set_current_inv_slot(3)
        elif self.pressed_4:
            self.player.set_current_inv_slot(4)

        # Handling if attempting to pick something up
        if self.e_pressed:
            self.try_pickup_item = True
        else:
            self.try_pickup_item = False

        # Handling if trying to drop something
        if self.g_pressed:
            self.drop_item = True
        else:
            self.drop_item = False

        # Handle player direction
        if self.left_pressed and self.right_pressed:
            # update upwards direction if both pressed
            self.player.update_rotation(0, 1)
        elif self.up_pressed and self.down_pressed:
            self.player.update_rotation(1, 0)
        elif self.up_pressed and self.right_pressed:
            self.player.update_rotation(1, 1)
        elif self.up_pressed and self.left_pressed:
            self.player.update_rotation(-1, 1)
        elif self.down_pressed and self.right_pressed:
            self.player.update_rotation(1, -1)
        elif self.down_pressed and self.left_pressed:
            self.player.update_rotation(-1, -1)
        elif self.left_pressed:
            self.player.update_rotation(-1, 0)
        elif self.right_pressed:
            self.player.update_rotation(1, 0)
        elif self.up_pressed:
            self.player.update_rotation(0, 1)
        elif self.down_pressed:
            self.player.update_rotation(0, -1)
        # Does have a default value, no need for else statement

        # Rotate player based on swinging their shovel - handled in player class
        if self.e_pressed:
            # Either of these will update the shovel to swinging or not swinging if player is holding shovel
            self.player.swing_shovel()

            self.player.activate_lantern()

        if self.h_pressed:
            self.player.scan()

    def on_key_press(self, key, modifiers):
        """
        Handling key presses
        :param key: the key object to be pressed
        :param modifiers:
        """
        if self.ship.player_interacting_with_terminal:
            self.ship.add_terminal_input(key)
        # In some examples, these are in if elif blocks, this is changed to if statements
        # to allow multiple directions to be pressed at once (only to allow up/down or right/left)
        if key == arcade.key.UP or key == arcade.key.W:
            self.up_pressed = True
        elif key == arcade.key.DOWN or key == arcade.key.S:
            self.down_pressed = True
        if key == arcade.key.LEFT or key == arcade.key.A:
            self.left_pressed = True
        elif key == arcade.key.RIGHT or key == arcade.key.D:
            self.right_pressed = True

        # Handle attempt_sprint
        if key == arcade.key.LSHIFT or key == arcade.key.RSHIFT:
            self.shift_pressed = True

        # for picking up and dropping items
        if key == arcade.key.E:
            self.e_pressed = True
        elif key == arcade.key.G:
            self.g_pressed = True
        elif key == arcade.key.H:
            self.h_pressed = True
        elif key == arcade.key.Q:
            self.q_pressed = True

        if not self.player.get_two_handed():
            # for changing selected inventory slots
            if key == arcade.key.KEY_1:
                self.pressed_1 = True
            elif key == arcade.key.KEY_2:
                self.pressed_2 = True
            elif key == arcade.key.KEY_3:
                self.pressed_3 = True
            elif key == arcade.key.KEY_4:
                self.pressed_4 = True

        # if key == arcade.key.P:
        #     self.p_pressed = True
        if key == arcade.key.TAB:
            self.pause_screen_visible = not self.pause_screen_visible

        # self.process_keychange() # since these are already in on_update I think this is fine to not be here

    def on_key_release(self, key, modifiers):
        """
        Handling the releases of keys
        :param key:
        :param modifiers:
        """
        # Deselect key presses
        if key == arcade.key.UP or key == arcade.key.W:
            self.up_pressed = False
        elif key == arcade.key.DOWN or key == arcade.key.S:
            self.down_pressed = False
        if key == arcade.key.LEFT or key == arcade.key.A:
            self.left_pressed = False
        elif key == arcade.key.RIGHT or key == arcade.key.D:
            self.right_pressed = False

        if key == arcade.key.LSHIFT or key == arcade.key.RSHIFT:
            self.shift_pressed = False

        if key == arcade.key.E:
            self.e_pressed = False
        elif key == arcade.key.G:
            self.g_pressed = False
        elif key == arcade.key.H:
            self.h_pressed = False
        elif key == arcade.key.Q:
            self.q_pressed = False
        # elif key == arcade.key.P:
        #     self.p_pressed = False 

        if not self.player.get_two_handed():
            if key == arcade.key.KEY_1:
                self.pressed_1 = False
            elif key == arcade.key.KEY_2:
                self.pressed_2 = False
            elif key == arcade.key.KEY_3:
                self.pressed_3 = False
            elif key == arcade.key.KEY_4:
                self.pressed_4 = False

        if key == arcade.key.ESCAPE:
            self.esc_pressed = False
        # self.process_keychange()

    def center_camera_to_player(self, speed):
        """
        Needed for centering the camera to the player on each game tick
        """
        screen_center_x = self.player.center_x - (self.camera.viewport_width / 2)
        screen_center_y = self.player.center_y - (self.camera.viewport_height / 2)

        player_centered = screen_center_x, screen_center_y

        self.camera.move_to(player_centered, speed)

    def snap_camera_to_player(self):
        """
        Needed for centering the camera to the player on each game tick
        """
        screen_center_x = self.player.center_x - (self.camera.viewport_width / 2)
        screen_center_y = self.player.center_y - (self.camera.viewport_height / 2)

        player_centered = screen_center_x, screen_center_y

        self.camera.move_to(player_centered, 1)

    def camera_reset_to_player(self):
        self.camera.move_to((self.player.position[0] - self.width / 2, self.player.position[1] - self.height / 2), 1)
        self.set_viewport(self.camera.position[0],
                          self.width + self.camera.position[0],
                          self.camera.position[1],
                          self.height + self.camera.position[1])

    def fix_camera(self):
        # Reset camera object
        self.camera = arcade.Camera(self.width, self.height)
        self.center_camera_to_player(1)

    def on_update(self,
                  delta_time=1/60): # 60 FPS works well and speeds up interactions to still a reasonable degree, without optimizations
        """Movement and game logic"""
        # If paused, allow no movements or other updates
        if self.pause_screen_visible:
            if self.q_pressed:
                # Quit the game
                sys.exit(0)
            # Account for time change while paused
            if self.gamestate == GAMESTATE_OPTIONS["outdoors"] or self.gamestate == GAMESTATE_OPTIONS["indoors"]:
                self.start_time += delta_time
            return
        # Process movement based on keys
        # print(self.player.health)
        self.process_keychange()

        self.player.update_player(self.indoor_enemy_entities, self.outdoor_enemy_entities)

        # Handle player interacting with terminal. If they are, handle accordingly
        if self.ship.player_interacting_with_terminal:
            self.ship.check_terminal_input(self.gamestate)
            # variable output is more useful, shorter more explanatory strings
            variable_output, terminal_string = self.ship.read_output()
            if variable_output != self.last_terminal_output and variable_output != None:
                # print(variable_output)
                self.last_terminal_output = variable_output

                # Check if it is a moon - only allow switching while in orbit (handled in ship class)
                # Load moon data for terminal phrases - done after other inputs to not load every time
                with open('resources/moons.json', 'r') as f:
                    data = json.load(f)
                # check if terminal phrase starts with a moon phrase
                for obj in data:
                    if self.last_terminal_output.startswith(obj['terminal_phrase']):
                        self.moon_name = obj["id"]
                    elif self.last_terminal_output.startswith("com"):
                        self.moon_name = "comp"
                # Add code for switching terminal output here

        else:
            self.last_terminal_output = None

        # Check time if landed
        if (self.gamestate == GAMESTATE_OPTIONS["outdoors"] or self.gamestate == GAMESTATE_OPTIONS["indoors"]) and \
                self.delta_time >= DAY_LENGTH:
            self.gamestate = GAMESTATE_OPTIONS["orbit"]
            self.recenter_orbit_background(self.ship.center_x, self.ship.center_y)
            self.snap_camera_to_player()
            # If player not on ship
            if len(arcade.check_for_collision_with_list(self.player, self.ship.get_background_hitbox())) == 0:
                self.player.reset()
                self.ship.reset()

            # Reset player location after checking location
            self.player.center_x = self.ship.center_x + 64
            self.player.center_y = self.ship.center_y + 128
            # self.ship.change_orbit()
            self.ship.set_orbit()

            # Remove a day left - after 3 days will be 0 - prevent landing/game over when done
            self.days_left -= 1
            self.current_screen = DEATH_SCREEN
            # You have to go to company to sell to do selling process - reset if taking back off after day 0 day
            if self.days_left < 0:
                self.current_screen = RESET_SCREEN
                self.reset_game()

        # Update item dropship
        if self.gamestate != GAMESTATE_OPTIONS["orbit"]:
            # Update the dropship
            self.ship.item_dropship.update_dropship()
            # Interact with the dropship
            if self.e_pressed and self.ship.item_dropship.can_drop() and \
                    arcade.check_for_collision(self.player, self.ship.item_dropship):
                self.outdoor_loot_items.extend(self.ship.item_dropship.drop_items())

        # Move the player with the physics engine
        if self.gamestate == GAMESTATE_OPTIONS["outdoors"]:
            # Update player light position
            self.player.player_outdoor_light.position = self.player.position
            self.player.player_scan_light.position = self.player.position

            self.outdoor_physics_engine.update()
            self.ship.update_ship()
            # This method will auto-update physics engine for if door is open or shut
            self.ship_physics_engine = arcade.PhysicsEnginePlatformer(
                self.player, self.ship.get_walls()
            )
            self.ship_physics_engine.gravity_constant = 0
            self.ship_physics_engine.update()

            # update spawners inside, and append new spawns to the spawn list
            spawned_monsters = self.indoor_map.update_spawners()
            if spawned_monsters is not None:
                self.indoor_enemy_entities.extend(spawned_monsters)

            # Update outdoor spawners
            # update spawners inside, and append new spawns to the spawn list
            spawned_monsters = self.indoor_map.update_outdoor_spawners()
            if spawned_monsters is not None:
                for monster in spawned_monsters:
                    monster.add_walls(self.ship.get_walls_with_door())
                self.outdoor_enemy_entities.extend(spawned_monsters)

            # Update the monsters
            for monster in self.outdoor_enemy_entities:
                monster.update_monster(self.player)

            # TODO: either change update method or don't update while outdoors, laggy
            # Update the monsters
            # for monster in self.indoor_enemy_entities:
            #     monster.update_monster(self.player)

            # Interact with the ship
            if self.e_pressed:
                ship_action = self.ship.interact_ship(self.player)
                # The following is changing from landing to orbit
                if ship_action == SHIP_INTERACTION_OPTIONS["lever"]:
                    self.gamestate = GAMESTATE_OPTIONS["orbit"]
                    self.recenter_orbit_background(self.ship.center_x, self.ship.center_y)
                    self.snap_camera_to_player()
                    # self.ship.change_orbit()
                    self.ship.set_orbit()
                    # Remove a day left - after 3 days will be 0 - prevent landing/game over when done
                    self.days_left -= 1
                    # You have to go to company to sell to do selling process - reset if taking back off after day 0 day
                    if self.days_left < 0:
                        self.current_screen = RESET_SCREEN
                        self.reset_game()

                elif ship_action == SHIP_INTERACTION_OPTIONS["terminal"]:
                    # This will handle inputs and drawing new stuff
                    self.ship.interact_terminal()
        elif self.gamestate == GAMESTATE_OPTIONS["company"]:
            self.company_physics_engine.update()
            self.ship.update_ship()
            # This method will auto-update physics engine for if door is open or shut
            self.ship_physics_engine = arcade.PhysicsEnginePlatformer(
                self.player, self.ship.get_walls()
            )
            self.ship_physics_engine.gravity_constant = 0
            self.ship_physics_engine.update()

            # Interact with the ship
            if self.e_pressed:
                ship_action = self.ship.interact_ship(self.player)
                # The following is changing from landing to orbit
                if ship_action == SHIP_INTERACTION_OPTIONS["lever"]:
                    self.gamestate = GAMESTATE_OPTIONS["orbit"]
                    self.recenter_orbit_background(self.ship.center_x, self.ship.center_y)
                    self.snap_camera_to_player()
                    # self.ship.change_orbit()
                    self.ship.set_orbit()
                    # Check days left
                    if self.days_left <= 0:
                        # if hit quota: reset days left and new quota
                        if self.scrap_sold >= self.quota:
                            self.days_left = 3
                            self.quotas_hit += 1
                            self.quota = increase_quota(self.quota, self.quotas_hit)
                            self.scrap_sold = 0
                        else:
                            # Tushar: Game end screen, after a short period restart the game (call init function)
                            self.current_screen = RESET_SCREEN
                            self.reset_game()
                elif ship_action == SHIP_INTERACTION_OPTIONS["terminal"]:
                    # This will handle inputs and drawing new stuff
                    self.ship.interact_terminal()
        elif self.gamestate == GAMESTATE_OPTIONS["indoors"]:
            self.indoor_physics_engine.update()

            # update spawners inside, and append new spawns to the spawn list
            spawned_monsters = self.indoor_map.update_spawners()
            if spawned_monsters is not None:
                self.indoor_enemy_entities.extend(spawned_monsters)

            # Update the monsters
            for monster in self.indoor_enemy_entities:
                monster.update_monster(self.player)

            # Update player light position
            self.player.player_indoor_light.position = self.player.position
            self.player.player_scan_light.position = self.player.position
        elif self.gamestate == GAMESTATE_OPTIONS["orbit"]:
            # This method will auto-update physics engine for if door is open or shut
            self.ship_physics_engine = arcade.PhysicsEnginePlatformer(
                self.player, self.ship.get_walls()
            )
            self.ship_physics_engine.gravity_constant = 0
            self.ship_physics_engine.update()
            if self.e_pressed:
                ship_action = self.ship.interact_ship(self.player)
                if ship_action == SHIP_INTERACTION_OPTIONS["lever"]:
                    self.gamestate = GAMESTATE_OPTIONS["outdoors"]
                    # self.ship.change_orbit()
                    self.ship.set_landed()
                    if self.moon_name != "comp":
                        # Setup and generate the new map (maybe show a loading screen before this and remove it after done)
                        # Like in game
                        self.snap_camera_to_player()
                        self.setup(self.moon_name)
                        self.ship.item_dropship.change_position(self.outdoor_map)
                    else:
                        self.gamestate = GAMESTATE_OPTIONS["company"]
                        # Setup the company building
                        # Ship update position uses delta_x and y
                        ship_position = self.ship.get_pos()
                        self.ship.update_position(self.company_starting_position[0] - 64 - ship_position[0],
                                                  self.company_starting_position[1] - 128 - ship_position[1])
                        self.player.center_x = self.company_starting_position[0]
                        self.player.center_y = self.company_starting_position[1]
                        self.snap_camera_to_player()
                        # Clear lists
                        self.outdoor_loot_items = arcade.SpriteList()
                        self.sell_list = arcade.SpriteList()
                        self.ship.item_dropship.change_position(self.company_building)

        # handle collisions - like this
        # item_hit_list = arcade.check_for_collision_with_list(
        #     self.player, self.loot_items # may need to change layer name
        # )
        self.player.decrease_pd_delay()

        # Handle checking if items are in hitbox and the player is attempting to pick something up
        # Add the item to inventory if the player's current slot is open
        if self.try_pickup_item and not self.player.get_inv(self.player.get_current_inv_slot()) and \
                self.player.get_pd_delay() == 0:
            # Since we can only populate the player's inventory slot with a single item,
            # we will only try with the first item
            # First, check to see if the player is in the ship (functions for orbit and outdoors)
            if arcade.check_for_collision_with_list(self.player, self.ship.get_background_hitbox()):
                # Check ship loot items
                item_hit_list = arcade.check_for_collision_with_list(self.player, self.ship.get_loot())
                if len(item_hit_list) > 0:
                    temp_item = item_hit_list[0]

                    self.player.add_item(self.player.get_current_inv_slot(), temp_item)
                    self.ship.remove_item(temp_item)
                    item_hit_list[0].remove_from_sprite_lists()  # remove from sprite list too

            else:
                if self.gamestate == GAMESTATE_OPTIONS["outdoors"] or self.gamestate == GAMESTATE_OPTIONS["company"]:
                    # Check outdoor loot items
                    self.outdoor_loot_items = self.check_player_list_collision(self.outdoor_loot_items)
                    # Also cannot pick items up from the sell list

                elif self.gamestate == GAMESTATE_OPTIONS["indoors"]:
                    # Check indoor loot items
                    self.indoor_loot_items = self.check_player_list_collision(self.indoor_loot_items)

        # Handle checking if the player wants to drop items
        if self.drop_item and self.player.get_inv(self.player.get_current_inv_slot()) and \
                self.player.get_pd_delay() == 0:
            temp_item = self.player.remove_item(self.player.get_current_inv_slot())
            if self.gamestate == GAMESTATE_OPTIONS["outdoors"] or self.gamestate == GAMESTATE_OPTIONS["company"]:
                # Only add to the ship list if the player is interacting with the ship
                if arcade.check_for_collision_with_list(self.player, self.ship.get_background_hitbox()):
                    self.ship.add_item(temp_item)
                elif arcade.check_for_collision_with_list(self.player, self.company_building["sell_areas"]):
                    self.sell_list.append(temp_item)
                else:
                    self.outdoor_loot_items.append(temp_item)
            elif self.gamestate == GAMESTATE_OPTIONS["orbit"]:
                self.ship.add_item(temp_item)
            else:
                self.indoor_loot_items.append(temp_item)

        # Check if a player is on a mine
        if self.gamestate == GAMESTATE_OPTIONS["indoors"]:
            mine_hit_list = arcade.check_for_collision_with_list(self.player, self.mines)
            if len(mine_hit_list) > 0:
                for mine in mine_hit_list:
                    mine.arm_mine()
                    self.mines.remove(mine)
                    self.armed_mines.append(mine)

            # Decrease delay for armed mines not touching the player
            for mine in self.armed_mines:
                if not arcade.check_for_collision(self.player, mine):
                    mine.decrease_delay()

            # Iterate through turrets and update
            for turret in self.turrets:
                turret.update_status(self.player, self.indoor_walls)
                # Need to set this as a temporary variable, as these are wiped from turrets memory by getter
                turret_bullets = turret.get_bullets()
                if len(turret_bullets) > 0:
                    self.bullets.extend(turret_bullets)

            # Will have to change bullets if implement shotguns - allows bullets outside
            # Check for bullet collisions with wall
            for bullet in self.bullets:
                bullet.update()
                bullet_wall_list = arcade.check_for_collision_with_list(
                    bullet, self.indoor_walls
                )
                if len(bullet_wall_list) > 0:
                    self.bullets.remove(bullet)

            # Check for bullet collisions with player, decrement health if hit
            bullet_hit_list = arcade.check_for_collision_with_list(
                self.player, self.bullets
            )
            for bullet in bullet_hit_list:
                # remove from bullets
                self.bullets.remove(bullet)
                self.player.decrease_health(bullet.get_damage())

        # Check for collision with entrances (enter indoors if outside)
        if self.gamestate == GAMESTATE_OPTIONS["outdoors"] and len(
                arcade.check_for_collision_with_list(self.player, self.outdoor_map["entrance"])) > 0:
            if self.e_pressed:
                if self.delay_main_enter_exit == 0:
                    self.gamestate = GAMESTATE_OPTIONS["indoors"]
                    self.delay_main_enter_exit = ENTER_EXIT_DELAY
                    # Move player to indoors starting position
                    self.player.center_x = self.indoor_main_position[0] - 64
                    self.player.center_y = self.indoor_main_position[1]
                    self.snap_camera_to_player()
                elif self.e_pressed:
                    self.delay_main_enter_exit -= 1
        # Exit if inside
        elif self.gamestate == GAMESTATE_OPTIONS["indoors"] and arcade.check_for_collision(self.player,
                                                                                           self.indoor_main_bounding_box):
            if self.e_pressed:
                if self.delay_main_enter_exit == 0:
                    # print("exitting")
                    self.gamestate = GAMESTATE_OPTIONS["outdoors"]
                    self.delay_main_enter_exit = ENTER_EXIT_DELAY
                    # set player to outdoor main position
                    self.player.center_x = self.outdoor_main_position[0]
                    self.player.center_y = self.outdoor_main_position[1]
                    self.snap_camera_to_player()
                else:
                    # print("delaying")
                    self.delay_main_enter_exit -= 1

        # Check for player interacting with bell
        if arcade.check_for_collision_with_list(self.player, self.company_building["bell"]) and self.e_pressed:
            for item in self.sell_list:
                # Include loss for number of days left
                value_loss = (MAX_DAYS - self.days_left) / MAX_DAYS

                self.scrap_sold += int(item.value * value_loss)
                self.ship.money += int(item.value * value_loss)
            self.sell_list = arcade.SpriteList()

        # Position the camera
        self.center_camera_to_player(0.075)

        # Check if the player is dead, reset screen and transfer to orbit otherwise
        if self.player.health <= 0 and self.gamestate != GAMESTATE_OPTIONS["orbit"]:
            self.current_screen = DEATH_SCREEN
            self.gamestate = GAMESTATE_OPTIONS["orbit"]
            self.player.reset()
            self.player.center_x = self.ship.center_x + 64
            self.player.center_y = self.ship.center_y + 128
            self.snap_camera_to_player()

            self.recenter_orbit_background(self.ship.center_x, self.ship.center_y)

            self.ship.reset()
            # self.ship.change_orbit()
            self.ship.set_orbit()
            # Remove a day left - after 3 days will be 0 - prevent landing/game over when done
            self.days_left -= 1
            # You have to go to company to sell to do selling process - reset if taking back off after day 0 day
            if self.days_left < 0:
                # TODO : Tushar: end game screen here
                self.current_screen = RESET_SCREEN
                self.reset_game()

        # Update the time if indoors or outdoors (i.e. this happens if it is during a day
        if self.gamestate == GAMESTATE_OPTIONS["outdoors"] or self.gamestate == GAMESTATE_OPTIONS["indoors"]:
            # Set player light level - can happen before update
            self.player.light_level(self.delta_time)
            self.delta_time = get_time() - self.start_time

    def check_player_list_collision(self, check_list):
        """
        :param check_list: List to check
        :return: the list
        """
        item_hit_list = arcade.check_for_collision_with_list(self.player, check_list)
        if len(item_hit_list) > 0:
            temp_item = item_hit_list[0]

            self.player.add_item(self.player.get_current_inv_slot(), temp_item)
            check_list.remove(
                item_hit_list[0])  # I'm not too sure how well this will work, have to try later
            item_hit_list[0].remove_from_sprite_lists()  # remove from sprite list too
        if check_list is None:
            return arcade.SpriteList()
        return check_list

    def draw_pause_screen(self):
        # arcade.draw_rectangle_filled(
        #     SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2,
        #     SCREEN_WIDTH, SCREEN_HEIGHT,
        #     arcade.color.WHITE + (0, 0, 0, 128)
        # )
        self.pause_background.center_x = self.camera.position[0] + SCREEN_WIDTH / 2
        self.pause_background.center_y = self.camera.position[1] + SCREEN_HEIGHT / 2
        self.pause_background.draw()
        # arcade.draw_text(
        #     "Paused", SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2,
        #     arcade.color.WHITE, font_size=50,
        #     anchor_x="center", anchor_y="center"
        # )
        # Draw controls, also at 50%
        corner_image = arcade.load_texture("resources/screens/controls.png")

        arcade.draw_texture_rectangle(
            self.pause_background.center_x + PAUSE_CONTROL_X_SHIFT, self.pause_background.center_y + PAUSE_CONTROL_Y_SHIFT,
            corner_image.width, corner_image.height,
            corner_image, alpha=128
        )

    def draw_death_screen(self):
        background_texture3 = arcade.load_texture("resources/screens/death.jpeg")

        if self.death_screen_timer is None:
            self.show_death_screen = True
            self.death_screen_timer = get_time()

        # Check if 5 seconds have elapsed and hide the reset screen
        if self.death_screen_timer is not None and get_time() - self.death_screen_timer >= 3000:
            self.death_screen_timer = None
            self.show_death_screen = False
            self.current_screen = GAME_SCREEN
            self.recenter_orbit_background(self.ship.center_x, self.ship.center_y)

        if self.draw_death_screen:
            arcade.draw_texture_rectangle(
                self.camera.position[0] + SCREEN_WIDTH // 2, self.camera.position[1] + SCREEN_HEIGHT // 2,
                SCREEN_WIDTH, SCREEN_HEIGHT,
                background_texture3
            )

            # arcade.draw_text(
            #     "GAME OVER", self.button_x - 15, SCREEN_HEIGHT // 3,
            #     arcade.color.WHITE, font_size=20
            # )

    def draw_reset_screen(self):
        background_texture2 = arcade.load_texture("resources/screens/reset.jpeg")

        # Set a timer for 5 seconds when the reset screen is shown
        if self.reset_screen_timer is None:
            self.show_reset_screen = True
            self.reset_screen_timer = get_time()

        # Check if 5 seconds have elapsed and hide the reset screen
        if self.reset_screen_timer is not None and get_time() - self.reset_screen_timer >= 5000:
            # print("drawing")
            self.reset_screen_timer = None
            self.show_reset_screen = False
            self.current_screen = GAME_SCREEN
            self.recenter_orbit_background(self.ship.center_x, self.ship.center_y)

        if self.draw_reset_screen:
            arcade.draw_texture_rectangle(
                self.camera.position[0] + SCREEN_WIDTH // 2, self.camera.position[1] + SCREEN_HEIGHT // 2,
                SCREEN_WIDTH, SCREEN_HEIGHT,
                background_texture2
            )
            arcade.draw_text(
                "-1 day", self.button_x - 15, SCREEN_HEIGHT // 3,
                arcade.color.WHITE, font_size=20
            )

    def draw_start_screen(self):
        background_texture = arcade.load_texture("resources/screens/Screen.jpeg")

        # Draw the background
        arcade.draw_texture_rectangle(
            SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2,
            SCREEN_WIDTH, SCREEN_HEIGHT,
            background_texture
        )

        if (self.button_x - self.button_width // 2 < self.mouse_x < self.button_x + self.button_width // 2 and
                self.button_y - self.button_height // 2 < self.mouse_y < self.button_y + self.button_height // 2):
            arcade.draw_rectangle_filled(
                self.button_x, self.button_y,
                self.button_width, self.button_height,
                arcade.color.GRAY
            )
        else:
            arcade.draw_rectangle_filled(
                self.button_x, self.button_y,
                self.button_width, self.button_height,
                arcade.color.RED
            )

        arcade.draw_text(
            "Start", self.button_x - 20, SCREEN_HEIGHT // 3,
            arcade.color.WHITE, font_size=20
        )
        corner_image = arcade.load_texture("resources/screens/controls.png")

        arcade.draw_texture_rectangle(
            SCREEN_WIDTH - corner_image.width // 2, corner_image.height // 2,
            corner_image.width, corner_image.height,
            corner_image
        )

    def on_mouse_press(self, x, y, button, modifiers):
        if self.current_screen == START_SCREEN:
            if (
                    self.button_x - self.button_width // 2 < x < self.button_x + self.button_width // 2 and
                    self.button_y - self.button_height // 2 < y < self.button_y + self.button_height // 2
            ):
                # Transition to the game screen
                self.current_screen = GAME_SCREEN

    def on_mouse_motion(self, x, y, dx, dy):
        self.mouse_x = x
        self.mouse_y = y

    def recenter_orbit_background(self, x, y):
        self.orbit_background.center_x = x
        self.orbit_background.center_y = y - self.orbit_background.height // 2 + SCREEN_HEIGHT // 2 + BACKGROUND_SHIFT


def get_time():
    # returns in second unit, multiple by 1000 for milliseconds
    timestamp = time() * 1000
    # round to nearest millisecond
    return int(timestamp)


def ms_to_igt(delta_time):
    # Convert the time difference in milliseconds to real-life seconds
    elapsed_seconds = (delta_time / MS_PER_SEC) * TIME_RATE_INCREASE

    # Convert real-life seconds to in-game hours (based on 8 am start)
    igt_hours = ((elapsed_seconds % SEC_PER_HOUR) // SEC_PER_MIN + 8) % 24

    igt_minutes = elapsed_seconds % SEC_PER_MIN

    return int(igt_hours), int(igt_minutes)


def main():
    """
    Main function
    """

    # Initialize game and begin runtime
    window = LethalGame()
    # window.setup("experimentation")
    arcade.run()


if __name__ == "__main__":
    pr = cProfile.Profile()
    pr.enable()
    main()
    pr.disable()

"""
Framework for game

from game startup:
- player chooses level (skip at start)
- procgen is called with map data (determines an array representation of the indoor map)
- map setup is called with procgens results as an argument
  - puts tile spaces together, creates room class objects (by passing spawn items)
- all these are done within game setup
-
- player entity is rendered


"""

"""
Current glitches:
- after picking up an item, dropping it, and picking it up again, the sprite in the inventory is not displayed
"""
