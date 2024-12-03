from math import sin, cos, pi, inf
from enum import Enum
import pygame

KILOBOT_FORWARD_SPEED = 20
KILOBOT_ROTATION_SPEED = 5
KILOBOT_RADIUS = 10
DESIRED_DISTANCE = 23
BROADCAST_RADIUS = 50
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
            
            distance = ((self.pos[0] - other.pos[0])**2 + (self.pos[1] - other.pos[1])**2)**0.5
            if distance > BROADCAST_RADIUS:
                continue
            
            other.neighbours.append({"id": self.id, "distance": distance, "gradient": self.gradient, "state": self.state, "activation_index": self.activation_index})
    
    
    def form_gradient(self):
        if self.is_seed:
            self.gradient = 0
            return

        if not self.updates_gradient:
            return
        
        neighbours_within_gradient_distance = [neighbour for neighbour in self.neighbours if neighbour["distance"] < GRADIENT_DISTANCE]
        if len(neighbours_within_gradient_distance) == 0:
            self.gradient = inf
            return
        
        min_gradient = min([neighbour["gradient"] for neighbour in neighbours_within_gradient_distance])
        self.gradient = min_gradient + 1


    
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
                
            if position_inside_shape(self.pos, shape):
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
            if not position_inside_shape(self.pos, shape):
                self.state = KilobotState.JOINED_SHAPE
            closes_neighbour_distance = min([neighbour["distance"] for neighbour in self.neighbours])
            closest_neighbour = [neighbour for neighbour in self.neighbours if neighbour["distance"] == closes_neighbour_distance][0]
            if self.gradient <= closest_neighbour["gradient"]:
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
                
    def _fix_rotation(self):
        self.rotation %= 2 * pi
    


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
    
def update_neighbours(bots):
    for bot in bots:
        bot.neighbours = []
        
    for bot in bots:
        bot.broadcast(bots)
    
def update_bots(bots, dt, shape):
    update_neighbours(bots)
    
    for bot in bots:
        bot.form_gradient()
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