import arcade
import math

import numpy as np

from utility_functions import rotate_hit_box
from arcade.experimental.lights import Light, LightLayer
from item import Item, Shovel, SHOVEL_DAMAGE, Lantern, LANTERN_LIGHT_SIZE

PLAYER_DELAY_PICKUP_DROP = 20
PLAYER_ROTATION_RATE = 10
MAX_HEALTH = 100
MAX_STAM = 100
INDOOR_LIGHT_SIZE = 150
OUTDOOR_LIGHT_SIZE = 1000
MS_PER_SEC = 1000
SEC_PER_MIN = 60
DAY_LENGTH = 10 * SEC_PER_MIN * MS_PER_SEC

SCAN_BASE_SIZE = 0
SCAN_MAX_SIZE = INDOOR_LIGHT_SIZE * 2
SCAN_MAX_TIMER = 25
SCAN_RADIUS_INCREASE = 10


class PlayerCharacter(arcade.Sprite):
    def __init__(self):
        """
        populate this with inventory items, holding_two handed boolean,
        current_item_slot_selected, health, and stamina

        """
        super().__init__()

        # Inventory attributes
        self.inventory = [None, None, None, None]  # Assuming 4 inventory slots
        self.holding_two_handed = False
        self.current_item_slot_selected = 1  # Default to first slot
        self.health = MAX_HEALTH
        self.stamina = MAX_STAM
        self.movement_speed = None
        self.moving = False
        self.walk_state = 0
        self.walk_time = 0
        self.total_weight = 0
        # Need to update sprites with animations, directions, etc
        self.texture = arcade.load_texture("resources/player_sprites/player_neutral.png")
        self.current_texture_name = "resources/player_sprites/player_neutral.png"

        # load all sprites
        self.sprite_neutral = arcade.load_texture("resources/player_sprites/player_neutral.png")
        self.sprite_walk1 = arcade.load_texture("resources/player_sprites/player_walk_left.png")
        self.sprite_walk2 = arcade.load_texture("resources/player_sprites/player_walk_right.png")
        self.sprite_neutral_carry = arcade.load_texture("resources/player_sprites/player_neutral_carry.png")
        self.sprite_walk1_carry = arcade.load_texture("resources/player_sprites/player_carry_left.png")
        self.sprite_walk2_carry = arcade.load_texture("resources/player_sprites/player_carry_right.png")

        self.rotation = 0

        # Block pickup if player is just dropped something or just picked something up
        self.pickup_drop_delay = 0

        self.player_indoor_light = Light(self.center_x, self.center_y, INDOOR_LIGHT_SIZE, arcade.color.WHITE, 'soft')
        self.player_outdoor_light = Light(self.center_x, self.center_y, OUTDOOR_LIGHT_SIZE, arcade.color.WHITE, 'soft')
        self.player_scan_light = Light(self.center_x, self.center_y, SCAN_BASE_SIZE, arcade.color.BLUE, "soft")

        self.player_swinging_shovel = False
        self.lantern_on = False
        self.lantern_interact_timer = 0

        self.scanning = False
        self.scan_max_delay = SCAN_MAX_TIMER

        """
        current item slot selected:
        when a player tries to pick up something, don't allow them to do this if they're holding something
        This will likely be done in the game class (as most things are), but we need to block the player from 
        picking something up if the current item slot 
        """

    def setup(self):
        """
        This may not be needed, add as wanted
        :return:
        """

    # get_health() - returns health value
    def get_health(self):
        return self.health

    # get_stam() - returns stamina value
    def get_stam(self):
        return self.stamina

    """
    get_inv(int) - returns the boolean value of the inputted inventory slot (true if something in it, false if not)
    - return false if player is holding a two-handed item (holding_two_handed is true), even if the other slot is full
    - this will be 1 indexed: first inventory slot is 1, second is 2, etc
    """

    def get_inv(self, inventory_slot):
        # Adjust for 1-indexed slots
        slot_index = inventory_slot - 1
        return self.inventory[slot_index] is not None

    def get_inv_specific(self):
        slot_index = self.current_item_slot_selected - 1
        return self.inventory[slot_index]

    def get_full_inv(self):
        return self.inventory

    # set_two_handed(bool) set two handed
    def set_two_handed(self, is_two_handed):
        self.holding_two_handed = is_two_handed

    """
    add_item(inventory_slot, item)
    - you don't need to handle for the inventory slot being open or closed
    - item will be an instance of the Item class, simply update the index of inventory_slot - 1 with this item
    """

    def add_item(self, inventory_slot, item):
        # Adjust for 1-indexed slots
        slot_index = inventory_slot - 1
        item.center_x = self.center_x
        item.center_y = self.center_y
        item.set_inventory_texture()
        self.inventory[slot_index] = item
        self.holding_two_handed = item.two_handed
        self.total_weight += item.weight

        # reset item drop/pickup delay
        self.reset_pd_delay()

    """
    remove_item(inventory_slot)
    - remove and return the object of the index of inventor_slot - 1, then set that index to be None (or whatever the 
      default empty value you decide for it) (the x and y coordinates of the item object need to be updated to the player's current location
      (This should be some sort of call to self.center_x and self.center_y to access the player Sprite's center
      """

    def remove_item(self, inventory_slot):
        # Adjust for 1-indexed slots
        slot_index = inventory_slot - 1
        removed_item = self.inventory[slot_index]
        self.inventory[slot_index] = None
        # Set holding_two_handed to be false if item was two handed
        if removed_item.two_handed:
            self.holding_two_handed = False
        self.total_weight -= removed_item.weight
        # Update items coordinates to the player's coordinates, and update items texture
        removed_item.set_map_texture()
        removed_item.center_x = self.center_x
        removed_item.center_y = self.center_y

        if removed_item is not None and type(removed_item) == Lantern:
            self.lantern_on = False

        # reset pickup drop delay
        self.reset_pd_delay()

        return removed_item

    def clear_inv(self):
        self.inventory = [None, None, None, None]

    def decrease_stam(self, amount):
        self.stamina -= amount
        if self.stamina < 0:
            self.stamina = 0

    def decrease_health(self, amount):
        self.health -= amount
        if self.health < 0:
            self.health = 0

    def add_stam(self, amount):

        self.stamina += amount
        if self.stamina > 100:  # Assuming max stamina is 100
            self.stamina = 100

    def add_health(self, amount):
        self.health += amount
        if self.health > 100:  # Assuming max health is 100
            self.health = 100

    def set_current_inv_slot(self, inventory_slot):
        """
        Set the currently selected inventory slot, unless there is a two-handed object being held.
        """
        if not self.holding_two_handed and not self.player_swinging_shovel:
            self.current_item_slot_selected = inventory_slot

    def reset(self):
        # Inventory attributes
        self.inventory = [None, None, None, None]  # Assuming 4 inventory slots
        self.holding_two_handed = False
        self.current_item_slot_selected = 1  # Default to first slot
        self.health = MAX_HEALTH
        self.stamina = MAX_STAM
        self.movement_speed = None
        self.moving = False
        self.walk_state = 0
        self.walk_time = 0
        self.total_weight = 0
        # Need to update sprites with animations, directions, etc
        # self.texture = arcade.load_texture("resources/player_sprites/player_neutral.png")
        # Need to update sprites with animations, directions, etc
        self.texture = arcade.load_texture("resources/player_sprites/player_neutral.png")
        self.current_texture_name = "resources/player_sprites/player_neutral.png"

        # load all sprites
        self.sprite_neutral = arcade.load_texture("resources/player_sprites/player_neutral.png")
        self.sprite_walk1 = arcade.load_texture("resources/player_sprites/player_walk_left.png")
        self.sprite_walk2 = arcade.load_texture("resources/player_sprites/player_walk_right.png")
        self.sprite_neutral_carry = arcade.load_texture("resources/player_sprites/player_neutral_carry.png")
        self.sprite_walk1_carry = arcade.load_texture("resources/player_sprites/player_carry_left.png")
        self.sprite_walk2_carry = arcade.load_texture("resources/player_sprites/player_carry_right.png")

        self.rotation = 0

        self.pickup_drop_delay = 0

        self.player_swinging_shovel = False

        # Reset lights
        self.player_indoor_light.radius = INDOOR_LIGHT_SIZE
        self.player_outdoor_light.radius = OUTDOOR_LIGHT_SIZE
        self.player_scan_light.radius = 0

    def get_current_inv_slot(self):
        """
        Getter for the currently selected inventory slot.
        """
        return self.current_item_slot_selected

    def set_movement_speed(self, speed):
        self.movement_speed = speed

    def get_movement_speed(self):
        return self.movement_speed

    def get_two_handed(self):
        return self.holding_two_handed

    def get_weight(self):
        return self.total_weight

    def get_pd_delay(self):
        return self.pickup_drop_delay

    def decrease_pd_delay(self):
        if self.pickup_drop_delay > 0:
            self.pickup_drop_delay -= 1

    def reset_pd_delay(self):
        self.pickup_drop_delay = PLAYER_DELAY_PICKUP_DROP

    def is_swinging_shovel(self):
        temp_item = self.inventory[self.current_item_slot_selected - 1]
        if temp_item is not None and type(temp_item) == Shovel and temp_item.is_swinging():
            return True
        return False

    def swing_shovel(self):
        temp_item = self.inventory[self.current_item_slot_selected - 1]
        if self.pickup_drop_delay <= 0 and temp_item is not None and \
                type(temp_item) == Shovel and not temp_item.is_swinging():
            temp_item.swing_shovel()
            return True
        return False

    def activate_lantern(self):
        temp_item = self.inventory[self.current_item_slot_selected - 1]
        if temp_item is not None and type(temp_item) == Lantern and self.lantern_interact_timer <= 0:
            self.lantern_on = not self.lantern_on
            self.lantern_interact_timer = PLAYER_DELAY_PICKUP_DROP * 2
            return True
        self.lantern_interact_timer -= 1
        return False

    def reset_light(self):
        # reset lantern being on or off: this is all it takes to change the light level
        self.lantern_on = False

    def update_player(self, indoor_monsters, outdoor_monsters):
        for item in self.inventory:
            if item is not None:
                item.center_x = self.center_x
                item.center_y = self.center_y

        temp_item = self.inventory[self.current_item_slot_selected - 1]

        if temp_item is not None and type(temp_item) == Shovel:
            # print(temp_item.start_swing, temp_item.swing_meter, temp_item.backwards_swing_meter, temp_item.angle)
            temp_item.update_shovel(self)

            if temp_item.is_swinging():
                if indoor_monsters is not None:
                    for monster in indoor_monsters:
                        # print(arcade.check_for_collision(temp_item, monster))
                        if arcade.check_for_collision(temp_item, monster):
                            temp_item.hit_monster(monster)
                if outdoor_monsters is not None:
                    for monster in outdoor_monsters:
                        # print(arcade.check_for_collision(temp_item, monster))
                        if arcade.check_for_collision(temp_item, monster):
                            temp_item.hit_monster(monster)

        if self.lantern_on:
            self.player_indoor_light.radius = LANTERN_LIGHT_SIZE
        else:
            self.player_indoor_light.radius = INDOOR_LIGHT_SIZE
        # print(self.player_scan_light.radius, self.player_scan_light.position)
        if self.scanning:
            if self.player_scan_light.radius <= SCAN_MAX_SIZE:
                self.player_scan_light.radius += SCAN_RADIUS_INCREASE
            # Wait for scan at max until delay runs out
            elif self.scan_max_delay > 0:
                self.scan_max_delay -= 1
            else:
                self.player_scan_light.radius = 0
                self.scanning = False

    def scan(self):
        if not self.scanning:
            self.scanning = True
            self.scan_max_delay = SCAN_MAX_TIMER

    def light_level(self, time_ms):
        # Set light level radius based on time of day, using logistic regression
        # Convert MS to a time of day in terms of the overall 10 minutes of the day
        portion_of_day = time_ms / DAY_LENGTH * 10
        decay_rate = -1
        # Midpoint in the logistic regression curve
        minute_in_day_center = 7
        target_light_level = OUTDOOR_LIGHT_SIZE / (1 + np.exp(-decay_rate * (portion_of_day - minute_in_day_center)))
        if not self.lantern_on:
            self.player_outdoor_light.radius = target_light_level
        else:
            self.player_outdoor_light.radius = max(target_light_level, LANTERN_LIGHT_SIZE)

    def update_rotation(self, x_direction, y_direction):
        """
        This is done by calculating the target direction for the player to turn, and then updating the players
        current direction by a step
        :param x_direction:
        :param y_direction:
        :return:
        """
        if self.player_swinging_shovel:
            return
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
        if min(diff_clockwise, diff_counterclockwise) < PLAYER_ROTATION_RATE:
            rotation_rate = PLAYER_ROTATION_RATE / 2
            # Decrease again if closer
            if min(diff_clockwise, diff_counterclockwise) < PLAYER_ROTATION_RATE / 2:
                rotation_rate = PLAYER_ROTATION_RATE / 4
        else:
            rotation_rate = PLAYER_ROTATION_RATE

        # Adjust rotation
        if current_rotation != target_direction:
            self.rotation += rotation_direction * rotation_rate
            # Only update hitbox if rotation has changed
            # Have to create a new sprite each time for the angle is only supplied during creation
            self.hit_box = rotate_hit_box(arcade.Sprite(self.current_texture_name).hit_box, self.rotation)

    def draw_self(self):
        """
        Draw the turret with scaled texture and rotation.
        """

        # reset states
        moving = False
        carrying = False

        # TODO: Render carried item in front of player

        # if the player is moving
        if self.change_x or self.change_y:
            moving = True

        # if the player is holding an item
        if self.inventory[self.current_item_slot_selected - 1] != None or self.holding_two_handed:
            carrying = True

        # every frame, increment the step counter, unless sprinting, then increase again!
        # when the step counter reaches 20, swap the walk state
        if self.movement_speed:
            self.walk_time += self.movement_speed

        # TODO: Add logic for interpolated sprites

        # logic for swapping states
        if self.walk_time > 30:
            match self.walk_state:
                case 0:
                    self.walk_state = 1
                case 1:
                    self.walk_state = 0

            self.walk_time = 0

        # TODO: move this out into the main body so that it can be referenced without re-initializing on each update
        sprite_matrix = [[[self.sprite_neutral, self.sprite_neutral], [self.sprite_walk1, self.sprite_walk2]],
                         [[self.sprite_neutral_carry, self.sprite_neutral_carry],
                          [self.sprite_walk1_carry, self.sprite_walk2_carry]]]

        sprite = sprite_matrix[carrying][moving][self.walk_state]

        arcade.draw_texture_rectangle(self.center_x, self.center_y, self.texture.width * self.scale,
                                      self.texture.height * self.scale, sprite, self.rotation)

        if carrying:
            held_item = self.inventory[self.current_item_slot_selected - 1]

            # some basic trig
            item_x = 20 * math.cos(math.radians(self.rotation))
            item_y = 20 * math.sin(math.radians(self.rotation))
            held_item.center_x = self.center_x + item_x
            held_item.center_y = self.center_y + item_y
            arcade.draw_texture_rectangle(self.center_x + item_x, self.center_y + item_y, held_item.width * self.scale,
                                          held_item.height * self.scale, held_item.texture, self.rotation + held_item.rotation - 90)
            # rotate hitbox of the item
            held_item.hit_box = rotate_hit_box(arcade.Sprite(held_item.texture_name).hit_box, self.rotation + held_item.rotation - 90)
            # held_item.draw_hit_box()
