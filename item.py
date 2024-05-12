"""
Quick comments from Skyler:
I think that we will actually want to be loading the items from a json, somewhat like rooms.
- So, each item in the json will have weight and sprite png (so you can use arcades sprite from png to make the actual sprite)

For value ranges, if a 0 is passed in, the value is 10-30, 1 is 30-60 and 2 is 60-100 (just use this to set the value of this sprite)
I would split up the json into two areas, being one handed and two handed, and then value range 
(i.e. "0" for 0 value items, see resources/items.json for this)
- for instance, if a 0 is passed in for value, and it isn't a two-handed item:
        assign self.value of randint(10, 30), and randomly choose something from
        Load the json (using json.load) and access the list of items of value 0 using following:
        data_from_json["one_handed"]["0"]     Then randomly pull from this for the weight and specific sprite

"""

import arcade
import json
import random
from arcade.experimental.lights import Light, LightLayer


class Item(arcade.Sprite):
    def __init__(self):
        """
        initialize value, size, type, is_two_handed
        """
        super().__init__()
        self.weight = None
        self.value = None
        self.texture = None
        self.texture_name = None
        self.texture_inventory = None
        self.texture_map = None
        self.type = None
        self.two_handed = None
        self.on_ground = None
        self.rotation = 0

    def setup(self, x_center, y_center, value, is_two_handed):
        """
        Update the variables based on these
        :param x_center:
        :param y_center:
        :param value:
        :param is_two_handed:
        """
        self.center_x = x_center
        self.center_y = y_center

        # Determine value range
        if value == 0:
            value_range = "0"
        elif value == 1:
            value_range = "1"
        else:
            value_range = "2"

        # Determine if one-handed or two-handed
        item_type = "one_handed" if not is_two_handed else "two_handed"

        # Load item data from JSON
        with open("resources/items.json", "r") as file:
            data_from_json = json.load(file)

        # Choose random item from the specified range and type
        items = data_from_json[item_type][value_range]
        item = random.choice(items)

        # Generate random value within the specified range
        value_lower, value_upper = item["value_range"]
        self.value = random.randint(value_lower, value_upper)

        # Assign weight and texture (for each of the two textures)
        self.weight = item["weight"]
        self.texture_map = arcade.Sprite(item["sprite_filename"])
        self.texture = arcade.load_texture(item["sprite_filename"])
        self.texture_name = item["sprite_filename"]
        self.texture_inventory = arcade.Sprite(item["sprite_inventory_filename"])
        self.on_ground = True
        self.two_handed = is_two_handed

        return self

    def set_inventory_texture(self):
        """
        Switch self.texture from map texture to inventory texture
        """
        # self.texture = arcade.load_texture(self.texture_inventory)
        self.on_ground = False

    def set_map_texture(self):
        """
        switch self.texture from inventory to map
        """
        # self.texture = arcade.load_texture(self.texture_map)
        self.on_ground = True

    def draw_self(self):
        if self.on_ground:
            self.texture_map.center_x = self.center_x
            self.texture_map.center_y = self.center_y
            self.texture_map.draw()
        else:
            self.texture_inventory.center_x = self.center_x
            self.texture_inventory.center_y = self.center_y
            self.texture_inventory.draw()

    def get_value(self):
        return self.value


# Different class for tools, as these have no value
class Tool(Item):
    def __init__(self):
        super().__init__()
        self.value = 0
        self.cost = None

    def setup_tool(self, x_center, y_center, id):
        """
        Update the variables based on these, for use in creating tools
        :param x_center:
        :param y_center:
        :param id: id of the item
        """
        self.center_x = x_center
        self.center_y = y_center

        # Load item data from JSON
        with open("resources/items.json", "r") as file:
            data_from_json = json.load(file)

        # Choose random item from the specified range and type
        tools = data_from_json["tools"]

        item = tools[0] # default buy first thing in list, if no others are found
        for tool in tools:
            if tool["terminal_phrase"] == id:
                # print(id, tool["terminal_phrase"])
                item = tool
                break

        # Get cost of the item
        self.cost = item["cost"]
        self.type = item["terminal_print"]

        # Assign weight and texture (for each of the two textures)
        self.weight = item["weight"]
        self.texture_map = arcade.Sprite(item["sprite_filename"])
        self.texture = arcade.load_texture(item["sprite_filename"])
        self.texture_name = item["sprite_filename"]
        self.texture_inventory = arcade.Sprite(item["sprite_inventory_filename"])
        self.on_ground = True
        self.two_handed = False

        return self

# Lantern Item the player can use
LANTERN_LIGHT_SIZE = 250


class Lantern(Tool):
    def __init__(self):
        super().__init__()
        # Only thing different is the light and if it is on or not
        self.light = None
        self.turned_on = None

    def setup_tool(self, x_center, y_center, identifier="lan"):
        super().setup_tool(x_center, y_center, identifier)
        # Initialize Light object to position
        self.light = LANTERN_LIGHT_SIZE # Light(self.center_x, self.center_y, LANTERN_LIGHT_SIZE, arcade.color.WHITE, 'soft')
        # Start turned off
        self.turned_on = False

    def turn_on(self):
        self.turned_on = True

    def turn_off(self):
        self.turned_on = False

    def get_value(self):
        return self.value


# Add shovel class
SHOVEL_SWING_TIME = 25
SHOVEL_SWING_TIME_DRAIN = 1
SHOVEL_ROTATION_PER_TICK = 5
SHOVEL_BASE_ROTATION = -45
SHOVEL_DAMAGE = 30


class Shovel(Tool):
    def __init__(self):
        super().__init__()
        # The difference here is a swinging animation, and a damage amount
        self.start_swing = False
        self.swing_meter = 0
        self.backwards_swing_meter = 0
        self.damage = 30
        self.rotation = SHOVEL_BASE_ROTATION # Update angle on pickup
        self.already_hit_target = False # For hitting targets, cannot hit more than one thing during shovel swing

    def setup_tool(self, x_center, y_center, identifier="sho"):
        super().setup_tool(x_center, y_center, identifier)
        # self.angle = player.angle - SHOVEL_BASE_ROTATION

    def draw_shovel(self):
        self.draw_self()

    def swing_shovel(self):
        if self.swing_meter <= 0 and self.backwards_swing_meter <= 0:
            self.start_swing = True
            self.already_hit_target = False # Set to false, nothing hit yet
        else:
            self.start_swing = False

    def update_shovel(self, player):
        if self.start_swing:
            player.player_swinging_shovel = True
            self.start_swing = False
            self.swing_meter = SHOVEL_SWING_TIME
            self.backwards_swing_meter = SHOVEL_SWING_TIME

        # This will rotate the shovel and the player
        self.rotate_shovel(player)
        # May need to update the hitbox of the player
        # self.update_hitbox()

    def rotate_shovel(self, player):
        # Turn shovel and player during duration
        if self.swing_meter > 0:
            # Rotate while swinging
            # self.rotation += SHOVEL_ROTATION_PER_TICK
            player.rotation += SHOVEL_ROTATION_PER_TICK
            self.swing_meter -= SHOVEL_SWING_TIME_DRAIN
        elif self.backwards_swing_meter > 0:
            # Rotate back to starting position
            # self.rotation -= SHOVEL_ROTATION_PER_TICK
            player.rotation -= SHOVEL_ROTATION_PER_TICK
            self.backwards_swing_meter -= SHOVEL_SWING_TIME_DRAIN
        else:
            player.player_swinging_shovel = False

    def get_value(self):
        return self.value

    def is_swinging(self):
        if self.swing_meter > 0:
            return True
        return False

    def hit_monster(self, monster):
        if not self.already_hit_target:
            print("Hitting monster")
            self.already_hit_target = True
            monster.decrease_health(SHOVEL_DAMAGE)



