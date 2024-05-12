from item import Item, Shovel, Lantern
import arcade
import math

# Constant for how long the drop is present before leaving again
TIME_UNTIL_DROP = 1000# 25000
DROPSHIP_DROP_RADIUS = 96
ROTATION_PER_DROP = 90


class ItemDropShip(arcade.Sprite):
    def __init__(self):
        super().__init__()
        self.texture = arcade.load_texture("resources/tilemaps/dropship.png")
        self.time_until_drop = None
        self.time_before_leave = None

        self.items = None

    def setup(self):
        # Add to this as needed
        self.time_before_leave = -1
        self.time_until_drop = -1
        self.items = arcade.SpriteList()

    def change_position(self, tilemap):
        self.position = tilemap["dropship"][0].position

    def add_item(self, item):
        item.center_x = self.center_x
        item.center_y = self.center_y
        self.items.append(item)
        # Start the timer
        self.time_until_drop = TIME_UNTIL_DROP
        self.time_before_leave = -1

    def can_drop(self):
        if self.time_until_drop <= 0 and self.time_before_leave > 0:
            return True
        return False

    def drop_items(self):
        # Drop items around the dropship, by 90 degrees at a time, at a radius of 96 from the center
        rotation = 0
        item_list = arcade.SpriteList()
        for item in self.items:
            # Update position
            item.center_x = self.center_x + DROPSHIP_DROP_RADIUS * math.cos(math.radians(rotation))
            item.center_y = self.center_y + DROPSHIP_DROP_RADIUS * math.sin(math.radians(rotation))
            item_list.append(item)
            rotation += ROTATION_PER_DROP
        self.items = arcade.SpriteList()
        return item_list

    def draw_self(self):
        # print("drawing dropship", self.time_until_drop <= 0 and self.time_before_leave > 0, len(self.items), self.time_until_drop)
        if self.time_until_drop <= 0 and self.time_before_leave > 0:
            self.draw()

    def update_dropship(self):
        # The timers are only reset by add_items and after landing
        if self.time_until_drop > 0:
            self.time_until_drop -= 1
        elif self.time_before_leave <= 0 and self.time_until_drop == 0:
            self.time_before_leave = TIME_UNTIL_DROP
            self.time_until_drop = -1
        elif self.time_before_leave > 0:
            self.time_before_leave -= 1
        else:
            # Reset the dropship if all above are False
            self.setup()


