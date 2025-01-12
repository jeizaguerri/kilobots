from math import sin, cos, pi, inf
from random import random, normalvariate
from enum import Enum
import pygame

KILOBOT_FORWARD_SPEED_MEAN = 10
KILOBOT_FORWARD_SPEED_STD = 1
KILOBOT_FORWARD_SPEED_ERROR = 0.01
KILOBOT_ROTATION_SPEED_MEAN = 3
KILOBOT_ROTATION_SPEED_STD = 0.5
KILOBOT_ROTATION_SPEED_ERROR = 0.01

DISTANCE_ERROR = 0.01

KILOBOT_RADIUS = 10
DESIRED_DISTANCE = 23
BROADCAST_RADIUS = 100
GRADIENT_DISTANCE = 30
STARTUP_TIME = 2
YIELD_DISTANCE = 35

DISABLE_MOVEMENT_ERROR = False
DISABLE_DISTANCE_ERROR = False

LOCALISE_TIME_AFTER_JOINING = 1

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
        self.percieved_pos = (0, 0) if not is_seed else pos
        self.selected_bot = False
        self.forwad_speed = normalvariate(KILOBOT_FORWARD_SPEED_MEAN, KILOBOT_FORWARD_SPEED_STD) if not DISABLE_MOVEMENT_ERROR else KILOBOT_FORWARD_SPEED_MEAN
        self.rotation_speed = normalvariate(KILOBOT_ROTATION_SPEED_MEAN, KILOBOT_ROTATION_SPEED_STD) if not DISABLE_MOVEMENT_ERROR else KILOBOT_ROTATION_SPEED_MEAN
        self.iterations_inside_shape = 0
        self.use_localise = True
        self.joined_shape_time = 0
        
    def __str__(self):
        return f"KiloBot {self.id} at {self.pos} facing {self.direction}"
    
    def move_straight(self, dt):
        movement_x = self.forwad_speed * cos(self.rotation) * dt
        movement_y = self.forwad_speed * sin(self.rotation) * dt
        error = random() * KILOBOT_FORWARD_SPEED_ERROR * 2 - KILOBOT_FORWARD_SPEED_ERROR
        error_x = error * movement_x
        error_y = error * movement_y
        if DISABLE_MOVEMENT_ERROR:
            error_x = 0
            error_y = 0
            
        new_position = (self.pos[0] + movement_x + error_x, self.pos[1] + movement_y + error_y)
        
        # Update position
        old_pos = self.pos
        self.pos = new_position
        
        # Fix position if colliding with other bots
        for bot in self.neighbours:
            if self._real_distance_to(bot["object"].pos) < 2 * KILOBOT_RADIUS:
                self.pos = old_pos
                break
        

        
    def rotate_left(self, dt):
        rotation = self.rotation_speed * dt
        error = random() * KILOBOT_ROTATION_SPEED_ERROR * 2 - KILOBOT_ROTATION_SPEED_ERROR
        rotation_error = error * rotation
        if DISABLE_MOVEMENT_ERROR: rotation_error = 0
        new_rotation = self.rotation - rotation + rotation_error
        
        self.rotation = new_rotation
        self._fix_rotation()
    
    def rotate_right(self, dt):
        rotation = self.rotation_speed * dt
        error = random() * KILOBOT_ROTATION_SPEED_ERROR * 2 - KILOBOT_ROTATION_SPEED_ERROR
        rotation_error = error * rotation
        if DISABLE_MOVEMENT_ERROR: rotation_error = 0
        new_rotation = self.rotation + rotation + rotation_error
        
        self.rotation = new_rotation
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
                self.move_straight(dt)
            else:
                self.move_straight(dt)
                self.rotate_left(dt)
        else:
            if self.prev_distance > current:
                self.move_straight(dt)
            else:
                self.move_straight(dt)
                self.rotate_right(dt)
                
        self.prev_distance = current
    
    
    def broadcast(self, bots):
        for other in bots: # Bot receiving the message
            if other.id == self.id:
                continue
            
            
            distance = self._real_distance_to(other.pos)
            error = random() * DISTANCE_ERROR * 2 - DISTANCE_ERROR
            distance_error = error * distance
            if DISABLE_DISTANCE_ERROR: distance_error = 0
            distance += distance_error
            
            if distance > BROADCAST_RADIUS:
                continue
            
            other.neighbours.append({"id": self.id, "distance": distance, "gradient": self.gradient, "state": self.state, "activation_index": self.activation_index, "pos": self.percieved_pos, "object": self})
    
    
    def form_gradient(self):
        if self.is_seed:
            self.gradient = 0
            return

        if not self.updates_gradient:
            return
        
        neighbours_within_gradient_distance = [neighbour for neighbour in self.neighbours if neighbour["distance"] < GRADIENT_DISTANCE]
        stationary_neighbours = [neighbour for neighbour in neighbours_within_gradient_distance if neighbour["state"] in (KilobotState.JOINED_SHAPE, KilobotState.WAIT_TO_MOVE)]
        
        if len(stationary_neighbours) == 0:
            self.gradient = inf
            self.prev_gradient = self.gradient
            return
        
        min_gradient = min([neighbour["gradient"] for neighbour in stationary_neighbours])
        self.gradient = min_gradient + 1


    def localise(self):
        if self.is_seed:
            return
        
        if self.state == KilobotState.JOINED_SHAPE and not self.use_localise:
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
    
    def perfect_localise(self):
        if self.state == KilobotState.JOINED_SHAPE:
            return
        
        self.percieved_pos = self.pos            
    
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
                self.iterations_inside_shape += 1
                if self.iterations_inside_shape > 10:
                    self.state = KilobotState.MOVE_WHILE_INSIDE
                    return
            else:
                self.iterations_inside_shape = 0
            
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
                self.joined_shape_time = 0
            closes_neighbour_distance = min([neighbour["distance"] for neighbour in self.neighbours])
            closest_neighbour = [neighbour for neighbour in self.neighbours if neighbour["distance"] == closes_neighbour_distance][0]
            if self.gradient == closest_neighbour["gradient"]: #and not self.going_down_gradient:
                self.state = KilobotState.JOINED_SHAPE
                self.joined_shape_time = 0
                
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
            if self.use_localise:
                self.joined_shape_time += dt
                if self.joined_shape_time > LOCALISE_TIME_AFTER_JOINING:
                    self.use_localise = False
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
    
    
    def location_error(self):
        return self._real_distance_to(self.percieved_pos)
    
                
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
    
def update_bots(bots, dt, shape, enable_trilateration=False):
    update_neighbours(bots)
    
    for bot in bots:
        bot.form_gradient()
        bot.localise() if enable_trilateration else bot.perfect_localise()
        bot.self_assembly(dt, shape)
        bot.update_color()


def position_inside_shape(pos, shape):
    x, y = pos
    x, y = int(x), int(y)
    return (shape[x,y] == (0,0,0)).all()

def generate_kilobots(shape_origin, rows, cols):
    bots = []
    
    # Generate seed
    bots.extend(generate_kilobot_seed(shape_origin))
    
    # Generate grid of kilobots
    grid_origin = (shape_origin[0] - KILOBOT_RADIUS * 2.5, shape_origin[1] + KILOBOT_RADIUS * 2.5)
    bots.extend(generate_kilobot_grid(rows, cols, grid_origin))
    
    return bots

def generate_kilobot_seed(start_pos):
    # 4 bots in + shape around start_pos
    bots = []
    bots.append(Kilobot((start_pos[0] - 1.5 * KILOBOT_RADIUS, start_pos[1]), 0, is_seed=True))
    bots.append(Kilobot((start_pos[0] + 1.5 * KILOBOT_RADIUS, start_pos[1]), pi, is_seed=True))
    bots.append(Kilobot((start_pos[0], start_pos[1] - 1.5 * KILOBOT_RADIUS), pi / 2, is_seed=True))
    bots.append(Kilobot((start_pos[0], start_pos[1] + 1.5 * KILOBOT_RADIUS), -pi / 2, is_seed=True))
    
    return bots
    

def generate_kilobot_grid(rows, cols, start_pos):
    bots = []
    # diagonal grid
    for i in range(rows):
        offset = 0 if i % 2 == 0 else 1.25 * KILOBOT_RADIUS
        for j in range(cols):
            x = start_pos[0] - j * 2.5 * KILOBOT_RADIUS + offset
            y = start_pos[1] + i * 2.5 * KILOBOT_RADIUS
            rotation =  random() * 2 * pi
            bots.append(Kilobot((x, y), rotation))
    
    return bots

def remove_bots_not_forming_shape(bots):
    bots_in_shape = [bot for bot in bots if bot.state == KilobotState.JOINED_SHAPE]
    bots = bots_in_shape
    return bots


def average_location_error(bots):
    location_errors = [bot.location_error() for bot in bots]
    return sum(location_errors) / len(location_errors)