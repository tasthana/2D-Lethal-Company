import arcade

class Spawner(arcade.Sprite):

    def __init__(self):
        """
        initialize spawner and variables
        """
        super().__init__()

        self.texture = arcade.load_texture("resources/hazard_sprites/vent.png")
        self.cooldown_max = 0
        self.cooldown_current = 0
        self.spawn_queue = []

    def setup(self, cooldowns, monsters):
        """
        populate the spawn queue
        """
        self.cooldown_queue = cooldowns
        self.spawn_queue = monsters
        self.queue_pos = 0
        self.cooldown_current = self.cooldown_queue[self.queue_pos]
        
    def update_spawner(self, time, avail_power):
        """
        increments the spawner cooldown
        if a spawn is successful, returns data in the following format:
        power increase, [monster id, x, y]
        """
        self.cooldown_current -= time

        # if cooldown is 0, the spawn queue has a monster, and the available power is greater than 0, spawn a monster
        if self.cooldown_current < 1 and len(self.spawn_queue) > 0 and avail_power > 0:
            
            # send data to game.py to spawn the monster, remove the monster, and reset the cooldown
            monster_data = self.spawn_queue[0]
            self.spawn_queue.pop(0)
            self.queue_pos += 1
            self.cooldown_current = self.cooldown_queue[self.queue_pos]

            return monster_data[1], [monster_data[0], self.center_x, self.center_y]

        return None

    def get_monsters(self):
        return self.spawn_queue
    
    def get_current_cooldown(self):
        return self.cooldown_current
    
    def get_max_cooldown(self):
        return self.cooldown_queue[self.queue_pos]

    def get_cooldown_queue(self):
        return self.cooldown_queue

    def set_monsters(self, monster_queue):
        self.spawn_queue = monster_queue

    def set_current_cooldown(self, cooldown):
        self.cooldown_current = cooldown

    def set_max_cooldown(self, cooldown):
        self.cooldown_queue[self.queue_pos] = cooldown

    def set_cooldown_queue(self, cooldown_queue):
        self.cooldown_queue = cooldown_queue


# While indoor spawner is updated in room, this is specifically for outdoors
class OutdoorSpawner(Spawner):
    def __init__(self):
        super().__init__()

    def setup_coords(self, x, y, cooldowns, monsters):
        super().setup(cooldowns, monsters)
        self.center_x = x
        self.center_y = y
    

