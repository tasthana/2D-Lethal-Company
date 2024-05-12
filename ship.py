import arcade
import random
import json
from player import PlayerCharacter
from item import Item, Shovel, Lantern
from item_dropship import ItemDropShip
from arcade.experimental.lights import Light, LightLayer


MAX_DOOR_BATTERY = 100
DOOR_BATTERY_DRAIN = 0.2
DOOR_SPRITE_X = 64 + 16
DOOR_SPRITE_Y = 248 + 16
SHIP_LAYER_NAMES = ["walls", "background", "door_control", "lever", "terminal", "higher_background", "ship_ceiling"]
DELAY_INTERACTIONS = 5
DELAY_DRAIN = 0.1
GAMESTATE_OPTIONS = {"orbit": 0, "outdoors": 1, "indoors": 2, "company": 3}
SHIP_INTERACTION_OPTIONS = {"lever": 0, "door": 1, "terminal": 2}
SCREEN_HEIGHT = 650
SHIP_LIGHT_SIZE = 400


class Ship(arcade.Sprite):
    def __init__(self):
        """
        intialize the walls, background, textures
        To note, we will not be supporting moving things around the ship.
        """
        super().__init__()
        self.tilemap = None # Will also function as the walls of the ship

        # Interaction areas are handled in the tilemap

        self.in_orbit = True # Ship starts in orbit

        # Door movement (starts shut with no battery drain)
        self.door_closed = True
        self.door_sprite = None
        self.door_battery = MAX_DOOR_BATTERY
        self.door_battery_drain = 0
        self.interact_delay = 0
        # Need delay starting at max
        self.lever_delay = DELAY_INTERACTIONS

        self.ship_loot = None
        self.total_loot_value = 0

        # For terminal interaction
        self.player_interacting_with_terminal = False
        self.terminal_input = ""
        self.terminal_output = ""
        self.processed_output = ""
        self.short_output = ""
        self.money = 60 # Start with 60 moneys

        self.ship_light = Light(self.center_x, self.center_y, SHIP_LIGHT_SIZE, arcade.color.WHITE, 'soft')

        self.item_dropship = ItemDropShip()
        self.item_dropship.setup()

    def setup(self):
        # Load tilemap
        self.tilemap = arcade.Scene.from_tilemap(arcade.load_tilemap("resources/tilemaps/ship.tmx"))
        # The door sprite
        self.door_sprite = arcade.Sprite("resources/wall_sprites/closed_door.png")
        self.door_sprite.center_x += DOOR_SPRITE_X
        self.door_sprite.center_y += DOOR_SPRITE_Y
        # The loot present on the ship
        self.ship_loot = arcade.SpriteList()

        return self

    def change_outdoors(self, outdoors):
        # Setup item dropship
        self.item_dropship.change_position(outdoors)

    def update_position(self, delta_x, delta_y):
        # Update the position of the ship sprite
        self.center_x += delta_x
        self.center_y += delta_y

        # Update the position of each sprite within the tilemap
        for layer_name in SHIP_LAYER_NAMES:
            layer = self.tilemap[layer_name]
            for sprite in layer:
                sprite.center_x += delta_x
                sprite.center_y += delta_y

        self.door_sprite.center_x += delta_x
        self.door_sprite.center_y += delta_y

        for item in self.ship_loot:
            item.center_x += delta_x
            item.center_y += delta_y

        self.ship_light.position = (self.center_x + 64, self.center_y + 128)

    def get_pos(self):
        return self.center_x, self.center_y

    def draw_self(self, camera, gamestate, player, paused_bool):
        # Only draw the layers we want to have drawn - bounding boxes and interaction boxes aren't needed
        self.tilemap["background"].draw()
        self.tilemap["walls"].draw()
        self.tilemap["higher_background"].draw()
        # These will be removed later but here for debugging temporarily
        # self.tilemap["door_control"].draw()
        # self.tilemap["lever"].draw()
        # self.tilemap["terminal"].draw()
        # Draw the door if it is closed
        if self.door_closed:
            self.door_sprite.draw()

        # Draw ship loot
        for item in self.ship_loot:
            item.draw_self()

        # Update the item dropship
        self.item_dropship.draw_self()

        # Draw the amount of loot onto the hud if in orbit
        if (gamestate == GAMESTATE_OPTIONS["orbit"] or gamestate == GAMESTATE_OPTIONS["company"]) and \
                not self.player_interacting_with_terminal and not paused_bool:
            text_x = camera.position[0] + 20
            text_y = camera.position[1] + SCREEN_HEIGHT - 30
            arcade.draw_text(f"Total ship loot: {self.total_loot_value}", text_x, text_y - 210, arcade.csscolor.GREEN, 18)

        # Draw top of ship if player isn't in it
        if not arcade.check_for_collision_with_list(player, self.tilemap["background"]):
            self.tilemap["ship_ceiling"].draw()

    def reset(self):
        # Interaction areas are handled in the tilemap

        self.in_orbit = True  # Ship starts in orbit

        # Door movement (starts shut with no battery drain)
        self.door_closed = True
        self.door_battery = MAX_DOOR_BATTERY
        self.door_battery_drain = 0
        self.interact_delay = 0
        # Need delay starting at max
        self.lever_delay = DELAY_INTERACTIONS

        self.ship_loot = arcade.SpriteList()
        self.total_loot_value = 0

        # For terminal interaction
        self.player_interacting_with_terminal = False
        self.terminal_input = ""
        self.terminal_output = ""
        self.processed_output = ""
        self.short_output = ""
        # self.money = 60  # Start with 60 moneys - only have full money on init

        self.ship_light = Light(self.center_x, self.center_y, SHIP_LIGHT_SIZE, arcade.color.WHITE, 'soft')

        self.item_dropship = ItemDropShip()

    def add_item(self, item):
        self.ship_loot.append(item)
        self.total_loot_value += item.get_value()

    def remove_item(self, item):
        self.ship_loot.remove(item)
        self.total_loot_value -= item.get_value()
        if self.total_loot_value < 0:
            self.total_loot_value = 0

    def get_walls(self):
        # Create a SpriteList containing the walls
        wall_list = arcade.SpriteList()
        wall_list.extend(self.tilemap["walls"])
        # wall_list.extend(self.tilemap["higher_background"])

        # Append the door sprite when it is closed
        if self.door_closed:
            wall_list.append(self.door_sprite)

        return wall_list

    def get_walls_with_door(self):
        # Create a SpriteList containing the walls
        wall_list = arcade.SpriteList()
        wall_list.extend(self.tilemap["walls"])
        # wall_list.extend(self.tilemap["higher_background"])

        # Append the door sprite no matter what
        wall_list.append(self.door_sprite)

        return wall_list

    def get_background_hitbox(self):
        return self.tilemap["background"]

    def interact_ship(self, player):
        """
        This function has to do with interaction between the player and things on the ship.
        Having the delays in here makes it so that player interaction using the "e" key
        makes delays only happen when the player is interacting. In practice this is honestly fine.
        :param player: PlayerCharacter object
        :param camera: Camera object to draw onto hud
        :return: String, result of interaction
        """

        if arcade.check_for_collision_with_list(player, self.tilemap["door_control"]):
            if self.interact_delay <= 0:
                self.interact_delay = DELAY_INTERACTIONS
                # print("door controls manip")
                # reverse door state, if not in orbit
                if not self.in_orbit:
                    self.door_closed = not self.door_closed
                else:
                    self.door_closed = True
                return SHIP_INTERACTION_OPTIONS["door"]
            self.interact_delay -= DELAY_DRAIN
        elif arcade.check_for_collision_with_list(player, self.tilemap["lever"]):
            if self.lever_delay <= 0:
                # Lever is activated
                self.lever_delay = DELAY_INTERACTIONS
                # Clear item dropship if taking off
                if not self.in_orbit:
                    self.item_dropship.setup()
                return SHIP_INTERACTION_OPTIONS["lever"]
            self.lever_delay -= DELAY_DRAIN
        elif arcade.check_for_collision_with_list(player, self.tilemap["terminal"]):
            if self.interact_delay <= 0:
                # Set the player to be interacting with the terminal
                self.interact_delay = DELAY_INTERACTIONS
                # print("getting input")
                # Interact with keyboard / listen for input
                self.player_interacting_with_terminal = True

                return SHIP_INTERACTION_OPTIONS["terminal"]
            self.interact_delay -= DELAY_DRAIN

    def update_ship(self):
        # Logic for decreasing battery while door is closed and increasing when open
        if self.door_closed and self.door_battery > 0:
            self.door_battery -= self.door_battery_drain
            if self.door_battery <= 0:
                self.door_closed = False
        elif not self.door_closed and self.door_battery < 100:
            self.door_battery += self.door_battery_drain * 3 # door battery recovers faster

    def change_orbit(self):
        """
        Door battery drain needs to be zero when in orbit
        :return:
        """
        if self.in_orbit:
            self.in_orbit = False
            self.door_battery_drain = DOOR_BATTERY_DRAIN
            self.door_closed = False
        else:
            self.in_orbit = True
            self.door_battery_drain = 0
            self.door_closed = True

    def set_orbit(self):
        self.in_orbit = True
        self.door_battery_drain = 0
        self.door_closed = True
        # Clear the item dropship, the player left it
        self.item_dropship.setup()

    def set_landed(self):
        self.in_orbit = False
        self.door_battery_drain = DOOR_BATTERY_DRAIN
        self.door_closed = False

    def interact_terminal(self):
        """
        This will handle terminal interaction, which will require a different UI than normal. However, this can be drawn
        over the rest of the screen with some opacity. (like in game)
        This handles inputs from user for things like the moons, etc. This functions as a very simple parser
        :return:
        """
        return ""

    def get_door(self):
        return self.door_closed

    def get_loot(self):
        return self.ship_loot

    def set_loot(self, spritelist):
        self.ship_loot = spritelist

    def add_terminal_input(self, key):
        """
        Adds a single keypress to the input string
        """
        if key == arcade.key.ENTER:
            # Save terminal input into output(checked by process)
            self.terminal_output = self.terminal_input
            self.terminal_input = ""  # Reset input string after printing
        elif key == arcade.key.BACKSPACE:
            self.terminal_input = self.terminal_input[:-1]  # Remove last character
        elif key == arcade.key.ESCAPE:
            self.player_interacting_with_terminal = False
            self.processed_output = ""
            self.terminal_output = ""
            self.terminal_input = ""
            # Add input into output variable and reset input
        elif key in (arcade.key.LSHIFT, arcade.key.RSHIFT, arcade.key.NUMLOCK, arcade.key.CAPSLOCK,
                     arcade.key.LCTRL, arcade.key.RCTRL, arcade.key.LALT, arcade.key.RALT,
                     arcade.key.LMETA, arcade.key.RMETA):
            pass  # Ignore special keys
        else:
            # Add pressed character to input string
            self.terminal_input += chr(key)

    def check_terminal_input(self, gamestate):
        """
        Checks to see if there is any terminal output
        """
        if self.terminal_output != "":
            # output to user and reset terminal outpute
            self.short_output, self.processed_output = self.process_input(self.terminal_output, gamestate)
            self.terminal_output = ""

    def read_output(self):
        return self.short_output, self.processed_output

    def process_input(self, input_string, gamestate):
        """
        Processes string input, in basic form. Many of the inputs are hardcoded
        :param input_string: String
        """
        input_string = input_string.lower()

        with open('resources/items.json', 'r') as f:
            data = json.load(f)
        tools = data["tools"]

        # check if terminal phrase starts with a moon phrase
        tool = None
        for obj in tools:
            if input_string.startswith(obj['terminal_phrase']):
                tool = make_tool(obj['terminal_phrase'], self.item_dropship)
                break

        if tool is not None:
            # Ensure the drop pod is not full or already landed
            if tool.cost <= self.money and len(self.item_dropship.items) < 12 and self.item_dropship.time_before_leave <= 0:
                self.money -= tool.cost
                self.item_dropship.add_item(tool)
                if gamestate == GAMESTATE_OPTIONS["orbit"]:
                    return "bought", f"Successfully bought {tool.type}. \nDropship enroute to next planet."
                else:
                    return "bought", f"Successfully bought {tool.type}. \nDropship enroute to current planet."
            elif len(self.item_dropship.items) >= 12:
                return "full", "Dropship already full."
            elif self.item_dropship.time_before_leave >= 0:
                return "landed", "Dropship already landed, wait for it to depart before ordering more."
            else:
                return "insufficient", f"Insufficient funds."

        # For routing to company building
        if input_string.startswith("com"):
            # print("company")
            return "comp", "Routing to company building"
        elif input_string.startswith("moo"):
            # Load moon names
            rtn_string = "Available moons: "
            with open('resources/moons.json', 'r') as f:
                data = json.load(f)
            for moon in data:
                rtn_string += "\n" + moon["moon_name"]
            return "moons", rtn_string
        elif input_string.startswith("help"):
            return "help", "Moons: shows list of available moons\n\n" \
                           "Company building: route to company building\n\n" \
                           "Store: shows store items for purchase\n\n" \
                           "Exit terminal using escape key"
        elif input_string.startswith("sto"):
            with open('resources/items.json', 'r') as f:
                data = json.load(f)
            tools = data["tools"]
            # check if terminal phrase starts with a moon phrase
            output_string = "Store\n"
            for obj in tools:
                output_string += f"{obj['terminal_print']}\n"
            return "store", output_string
        else:
            # Only allow moon switching while in orbit
            if gamestate == GAMESTATE_OPTIONS["orbit"]:
                # Load moon data for terminal phrases - done after other inputs to not load every time
                with open('resources/moons.json', 'r') as f:
                    data = json.load(f)
                # check if terminal phrase starts with a moon phrase
                for obj in data:
                    if input_string.startswith(obj['terminal_phrase']):
                        return obj['terminal_phrase'], f"Routing to {obj['moon_name']}"
            else:
                return "", "Cannot change moon unless in orbit"
            return None, "Invalid input"


def make_tool(tool_name, dropship):
    if tool_name == "sho":
        shovel = Shovel()
        shovel.setup_tool(dropship.center_x, dropship.center_y, "sho")
        return shovel
    elif tool_name == "lan":
        lantern = Lantern()
        lantern.setup_tool(dropship.center_x, dropship.center_y, "lan")
        return lantern
