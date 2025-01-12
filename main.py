import pygame
import os
import matplotlib.pyplot as plt
import json
from math import sin, cos, pi
from kilobot import Kilobot, KILOBOT_RADIUS, draw_bots, update_bots, KilobotState, generate_kilobots, remove_bots_not_forming_shape, average_location_error

BACKGROUND_TILE_SIZE = 32
MS_PER_UPDATE = 100
TEST_NAME = "arrow_bad"
OUTPUT_FILE = f"info/output_info.json"
IMAGE_FILE = "shapes/arrow.png"

def save_graph_info_json(location_errors, timer, forming_shape_bots, average_error, test_name):
    if os.path.exists(OUTPUT_FILE):
        # Open OUTPUT_FILE and read the content as json
        with open(OUTPUT_FILE, "r") as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                data = {}
    else:
        data = {}

    # Update the data with the new test information
    data[test_name] = {"errors": location_errors, "time": timer, "bots": forming_shape_bots, "average_error": average_error}

    # Write the updated data back to the file
    with open(OUTPUT_FILE, "w") as f:
        json.dump(data, f, indent=4)
        
def main():
    display_desired_shape = True
    display_grid = True
    display_gradient = True
    display_bots = True
    enable_update = True
    location_errors = []
    number_of_last_forming_shape_bots = 0
    last_forming_shape_bots = []
    enable_trilateration = True
    
    # pygame setup
    pygame.init()
    screen = pygame.display.set_mode((1280, 720))
    clock = pygame.time.Clock()
    running = True
    font = pygame.font.SysFont(None, 24)
    timer = 0
    last_robot_join_time = 0
    
    # Load shape image
    shape = pygame.image.load(IMAGE_FILE)
    shape.set_colorkey ((255, 255, 255))
    shape.set_alpha(77)
    
    # Find red pixel
    shape_origin = None
    for x in range(shape.get_width()):
        for y in range(shape.get_height()):
            if shape.get_at((x, y)) == (255, 0, 0, 255):
                shape_origin = (x, y)
    
    # Generate bots
    if not shape_origin:
        print("Shape origin not found")
        return
    bots = generate_kilobots(shape_origin, 10, 20)
    
    # Convert to array
    shape_array = pygame.surfarray.array3d(shape)
    
    # Create error graph
    plt.ion()
    plt.figure()
    plt.title("Location error")
    plt.xlabel("Bots forming shape")
    plt.ylabel("Location error (px)")
    plt.grid()
    plt.show()

    while running:
        # poll for events
        # pygame.QUIT event means the user clicked X to close your window
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_1:
                    display_desired_shape = not display_desired_shape
                if event.key == pygame.K_2:
                    display_grid = not display_grid
                if event.key == pygame.K_3:
                    display_gradient = not display_gradient
                if event.key == pygame.K_4:
                    display_bots = not display_bots
                if event.key == pygame.K_SPACE:
                    enable_update = not enable_update
                if event.key == pygame.K_ESCAPE:
                    bots = remove_bots_not_forming_shape(bots)
                if event.key == pygame.K_s:
                    avg_error = average_location_error(forming_shape_bots)
                    save_graph_info_json(location_errors, last_robot_join_time, number_of_last_forming_shape_bots, avg_error, TEST_NAME)
                if event.key == pygame.K_t:
                    enable_trilateration = not enable_trilateration
            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    for bot in bots:
                        if bot._real_distance_to(event.pos) < KILOBOT_RADIUS:
                            bot.selected_bot = not bot.selected_bot

        
        # Update bots
        # dt = (clock.get_time() / 1000)
        dt = MS_PER_UPDATE / 1000
        
        if enable_update:
            timer += dt
            update_bots(bots, dt, shape_array, enable_trilateration=enable_trilateration)

        # Check robots forming shape
        forming_shape_bots = [bot for bot in bots if bot.state == KilobotState.JOINED_SHAPE]
        number_of_forming_shape_bots = len(forming_shape_bots)
        if number_of_forming_shape_bots != number_of_last_forming_shape_bots:
            # Find new bot
            new_bot = [bot for bot in forming_shape_bots if bot not in last_forming_shape_bots][0]
            
            location_errors.append(new_bot.location_error())
            number_of_last_forming_shape_bots = number_of_forming_shape_bots
            last_forming_shape_bots = forming_shape_bots
            # Update graph
            plt.plot(location_errors, 'b')
            plt.draw()
            plt.pause(0.001)
            last_robot_join_time = timer
            

        # Render game
        for x in range(0, 1280, BACKGROUND_TILE_SIZE):
            for y in range(0, 720, BACKGROUND_TILE_SIZE):
                pygame.draw.rect(screen, "#f1faee", (x, y, BACKGROUND_TILE_SIZE, BACKGROUND_TILE_SIZE), 0)
                if display_grid:
                    pygame.draw.rect(screen, (230,230,230), (x, y, BACKGROUND_TILE_SIZE, BACKGROUND_TILE_SIZE), 1)
                    
        if display_desired_shape:
            screen.blit(shape, (640 - shape.get_width()//2, 360 - shape.get_height()//2))
        
        if display_bots:
            draw_bots(screen, bots, display_gradient)
        
        
        # Show controls and info in bottom left
        texts = [
            "Controls: ",
            f"[1]: Display desired shape: {display_desired_shape}",
            f"[2]: Display grid: {display_grid}",
            f"[3]: Display gradient: {display_gradient}",
            f"[4]: Display bots: {display_bots}",
            f"[SPACE]: Enable update: {enable_update}",
            "[ESC]: Remove all bots not forming shape",
            "[S]: Save graph info to file",
            f"[T]: Toggle trilateration: {enable_trilateration}",
            f"Click on a bot for more info",
            "",
            f"Simulation time: {timer:.2f} seconds",
            f"FPS: {int(clock.get_fps())}",
            f"Total bots: {len(bots)} (Forming shape: {number_of_forming_shape_bots})"
        ]
        distance_between_lines = 20
        for i in range(len(texts)):
            line_i = len(texts) - i - 1
            text = font.render(texts[i], True, (0, 0, 0))
            screen.blit(text, (10, 720 - (line_i + 1) * distance_between_lines))
        

        # flip() the display to put your work on screen
        pygame.display.flip()

        clock.tick(60)  # limits FPS to 60

    pygame.quit()
    

main()