from math import sin, cos, pi, inf
from enum import Enum
import pygame

KILOBOT_FORWARD_SPEED = 15
KILOBOT_ROTATION_SPEED = 7
KILOBOT_RADIUS = 10
DESIRED_DISTANCE = 23
BROADCAST_RADIUS = 100
GRADIENT_DISTANCE = 30
STARTUP_TIME = 2
YIELD_DISTANCE = 35

class KilobotState(Enum):
    START = 0
    WAIT_TO_MOVE = 1
    MOVE_WHILE_OUTSIDE = 2
    MOVE_WHILE_INSIDE = 3
    JOINED_SHAPE = 4


class Kilobot:
    id = 0
    activation_index = 0
    def __init__(self, pos:tuple, rotation:float, color:str="red", is_seed:bool=False):
        self.id = Kilobot.id
        Kilobot.id += 1
        self.pos = pos
        self.rotation = rotation
        self.state = 0
        self.color = color
        self.neighbours = [] # Dict of (id, distance, gradient)
        self.prev_distance = inf
        self.gradient = inf if is_seed else inf
        self.is_seed = is_seed
        self.state =  KilobotState.START
        self.timer = 0
        self.updates_gradient = True
        self.activation_index = inf
        # self.going_down_gradient = False
        # self.prev_gradient = 0
        self.percieved_pos = (0, 0) if not is_seed else pos
        self.selected_bot = False
    
    def __str__(self):
        return f"KiloBot {self.id} at {self.pos} facing {self.direction}"
    
    def moveStraight(self, dt):
        movement_x = KILOBOT_FORWARD_SPEED * cos(self.rotation) * dt
        movement_y = KILOBOT_FORWARD_SPEED * sin(self.rotation) * dt
        self.pos = (self.pos[0] + movement_x, self.pos[1] + movement_y)

        
    def rotateLeft(self, dt):
        self.rotation -= KILOBOT_ROTATION_SPEED * dt
        self._fix_rotation()
    
    def rotateRight(self, dt):
        self.rotation += KILOBOT_ROTATION_SPEED * dt
        self._fix_rotation()
        
    def follow_edge(self, dt):
        # Store nearest neighbour in current
        current = inf
        not_moving_neighbours = [neighbour for neighbour in self.neighbours if neighbour["state"] not in [KilobotState.MOVE_WHILE_INSIDE, KilobotState.MOVE_WHILE_OUTSIDE]]
        for neighbour in not_moving_neighbours:
            if neighbour["distance"] < current:
                current = neighbour["distance"]
                
        if current < DESIRED_DISTANCE:
            if self.prev_distance < current:
                self.moveStraight(dt)
            else:
                self.moveStraight(dt)
                self.rotateLeft(dt)
        else:
            if self.prev_distance > current:
                self.moveStraight(dt)
            else:
                self.moveStraight(dt)
                self.rotateRight(dt)
                
        self.prev_distance = current
    
    
    def broadcast(self, bots):
        for other in bots: # Bot receiving the message
            if other.id == self.id:
                continue
            
            distance = self._real_distance_to(other.pos)
            if distance > BROADCAST_RADIUS:
                continue
            
            other.neighbours.append({"id": self.id, "distance": distance, "gradient": self.gradient, "state": self.state, "activation_index": self.activation_index, "pos": self.percieved_pos})
    
    
    def form_gradient(self):
        if self.is_seed:
            self.gradient = 0
            return

        if not self.updates_gradient:
            return
        
        neighbours_within_gradient_distance = [neighbour for neighbour in self.neighbours if neighbour["distance"] < GRADIENT_DISTANCE]
        # if self.state == KilobotState.JOINED_SHAPE:
        #     joined_neighbours_within_gradient_distance = [neighbour for neighbour in neighbours_within_gradient_distance if neighbour["state"] == KilobotState.JOINED_SHAPE]
        #     if len(joined_neighbours_within_gradient_distance) > 0:
        #         min_gradient = min([neighbour["gradient"] for neighbour in joined_neighbours_within_gradient_distance])
        #         self.gradient = min_gradient + 1
        #         gradient_changed = self.gradient != self.prev_gradient
        #         if gradient_changed:
        #             self.going_down_gradient = self.gradient < self.prev_gradient
        #             self.prev_gradient = self.gradient
        #     return
        
        if len(neighbours_within_gradient_distance) == 0:
            self.gradient = inf
            self.prev_gradient = self.gradient
            return
        
        min_gradient = min([neighbour["gradient"] for neighbour in neighbours_within_gradient_distance])
        self.gradient = min_gradient + 1


    def localise(self):
        if self.state == KilobotState.JOINED_SHAPE:
            return
        
        localised_stationary_neighbours = [neighbour for neighbour in self.neighbours if neighbour["state"] in [KilobotState.JOINED_SHAPE]]
        if len(localised_stationary_neighbours) < 3:
            return

        for neighbour in localised_stationary_neighbours:
            c = self._percieved_distance_to(neighbour["pos"])
            v = (self.percieved_pos[0] - neighbour["pos"][0], self.percieved_pos[1] - neighbour["pos"][1])
            v = (v[0] / c, v[1] / c)
            n = (neighbour["pos"][0] + neighbour["distance"] * v[0], neighbour["pos"][1] + neighbour["distance"] * v[1])
            self.percieved_pos = (self.percieved_pos[0] - (self.percieved_pos[0] - n[0]), self.percieved_pos[1] - (self.percieved_pos[1] - n[1]))
                
    
    def self_assembly(self, dt, shape):
        if self.state == KilobotState.START:
            if self.is_seed:
                self.state = KilobotState.JOINED_SHAPE
            else:
                self.form_gradient()
                self.timer += dt
                if self.timer > STARTUP_TIME:
                    self.state = KilobotState.WAIT_TO_MOVE
            return

        if self.state == KilobotState.WAIT_TO_MOVE:
            neighbour_states = [neighbour["state"] for neighbour in self.neighbours]
            if len(neighbour_states) == 0:
                    self.state = KilobotState.MOVE_WHILE_OUTSIDE
                    return
                
            moving_neighbour = KilobotState.MOVE_WHILE_INSIDE in neighbour_states or KilobotState.MOVE_WHILE_OUTSIDE in neighbour_states
            if not moving_neighbour:
                waiting_neighbours = [neighbour for neighbour in self.neighbours if neighbour["state"] == KilobotState.WAIT_TO_MOVE]
                if len(waiting_neighbours) == 0:
                    self.state = KilobotState.MOVE_WHILE_OUTSIDE
                    return
                highest_gradient = max([neighbour["gradient"] for neighbour in waiting_neighbours])
                highest_gradient_neighbours = [neighbour for neighbour in waiting_neighbours if neighbour["gradient"] == highest_gradient]
                if self.gradient > highest_gradient:
                    self.state = KilobotState.MOVE_WHILE_OUTSIDE
                elif self.gradient == highest_gradient and self.id > max([neighbour["id"] for neighbour in highest_gradient_neighbours]):
                    self.state = KilobotState.MOVE_WHILE_OUTSIDE
            return
        
        if self.state == KilobotState.MOVE_WHILE_OUTSIDE:
            if self.activation_index == inf:
                self.activation_index = Kilobot.activation_index
                Kilobot.activation_index += 1
                
            if position_inside_shape(self.percieved_pos, shape):
                self.state = KilobotState.MOVE_WHILE_INSIDE
                return
            
            moving_prior_neighbours = [neighbour for neighbour in self.neighbours if neighbour["state"] in [KilobotState.MOVE_WHILE_INSIDE, KilobotState.MOVE_WHILE_OUTSIDE] and neighbour["activation_index"] < self.activation_index]
            if len(moving_prior_neighbours) <= 0:
                self.follow_edge(dt)
            else:
                closest_edge_following_neighbour = min([neighbour["distance"] for neighbour in moving_prior_neighbours])
                if closest_edge_following_neighbour > YIELD_DISTANCE:
                    self.follow_edge(dt)
            return

        if self.state == KilobotState.MOVE_WHILE_INSIDE:
            if not position_inside_shape(self.percieved_pos, shape):
                self.state = KilobotState.JOINED_SHAPE
            closes_neighbour_distance = min([neighbour["distance"] for neighbour in self.neighbours])
            closest_neighbour = [neighbour for neighbour in self.neighbours if neighbour["distance"] == closes_neighbour_distance][0]
            if self.gradient == closest_neighbour["gradient"]: #and not self.going_down_gradient:
                self.state = KilobotState.JOINED_SHAPE
                
            moving_prior_neighbours = [neighbour for neighbour in self.neighbours if neighbour["state"] in [KilobotState.MOVE_WHILE_INSIDE, KilobotState.MOVE_WHILE_OUTSIDE] and neighbour["activation_index"] < self.activation_index]
            if len(moving_prior_neighbours) <= 0:
                self.follow_edge(dt)
            else:
                closest_edge_following_neighbour = min([neighbour["distance"] for neighbour in moving_prior_neighbours])
                if closest_edge_following_neighbour > YIELD_DISTANCE:
                    self.follow_edge(dt)
            return
        
        if self.state == KilobotState.JOINED_SHAPE:
            self.updates_gradient = False
            return

    colors_dict = {
            KilobotState.START: "#A8DADC",
            KilobotState.WAIT_TO_MOVE: "#e63946",
            KilobotState.MOVE_WHILE_OUTSIDE: "#a8dadc",
            KilobotState.MOVE_WHILE_INSIDE: "#457b9d",
            KilobotState.JOINED_SHAPE: "#1d3557",
        }
    def update_color(self):        
        color = self.colors_dict[self.state]
        self.color = color
        if self.is_seed:
            self.color = "#00848f"
    
    def draw_additional_info(self, screen):
        # Show percieved position
        pygame.draw.circle(screen, "blue", self.percieved_pos, 5)
        
        #Outline self
        pygame.draw.circle(screen, "black", self.pos, KILOBOT_RADIUS, 2)
        
        # Outline neighbours
        for neighbour in self.neighbours:
            pygame.draw.circle(screen, "green", neighbour["pos"], KILOBOT_RADIUS, 1)
            
                
    def _fix_rotation(self):
        self.rotation %= 2 * pi
    
    def _real_distance_to(self, pos):
        return ((self.pos[0] - pos[0])**2 + (self.pos[1] - pos[1])**2)**0.5
    
    def _percieved_distance_to(self, pos):
        return ((self.percieved_pos[0] - pos[0])**2 + (self.percieved_pos[1] - pos[1])**2)**0.5
    


pygame.font.init()
font = pygame.font.Font(None, 20)
def draw_bots(screen, bots, draw_gradient=True):
    for bot in bots:
        pygame.draw.circle(screen, bot.color, bot.pos, KILOBOT_RADIUS)
        end = (bot.pos[0] + 10 * cos(bot.rotation), bot.pos[1] + 10 * sin(bot.rotation))
        pygame.draw.line(screen, "#1D3557", bot.pos, end, 2)
        if draw_gradient:
            text = font.render(str(bot.gradient), True, "white")
            text_pos = (bot.pos[0] + 1 - text.get_width() / 2, bot.pos[1] + 1 - text.get_height() / 2)
            screen.blit(text, text_pos)

    for bot in bots:
        if bot.selected_bot:
            bot.draw_additional_info(screen)
    
def update_neighbours(bots):
    for bot in bots:
        bot.neighbours = []
        
    for bot in bots:
        bot.broadcast(bots)
    
def update_bots(bots, dt, shape):
    update_neighbours(bots)
    
    for bot in bots:
        bot.form_gradient()
        bot.localise()
        bot.self_assembly(dt, shape)
        bot.update_color()


def position_inside_shape(pos, shape):
    x, y = pos
    x, y = int(x), int(y)
    return (shape[x,y] == (0,0,0)).all()

def generate_kilobot_grid(rows, cols, start_pos):
    bots = []
    # diagonal grid
    for i in range(rows):
        offset = 0 if i % 2 == 0 else 1.25 * KILOBOT_RADIUS
        for j in range(cols):
            x = start_pos[0] - j * 2.5 * KILOBOT_RADIUS + offset
            y = start_pos[1] + i * 2.5 * KILOBOT_RADIUS
            bots.append(Kilobot((x, y), pi))
    
    return bots

def remove_bots_not_forming_shape(bots):
    bots_in_shape = [bot for bot in bots if bot.state == KilobotState.JOINED_SHAPE]
    bots = bots_in_shape
    return bots