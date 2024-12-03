import pygame
from math import sin, cos, pi

from kilobot import Kilobot, KILOBOT_RADIUS, draw_bots, update_bots, KilobotState, generate_kilobot_grid

BACKGROUND_TILE_SIZE = 32
TIME_SCALE = 1

def main():
    display_desired_shape = True
    display_grid = True
    display_gradient = True
    display_bots = True
    
    # pygame setup
    pygame.init()
    screen = pygame.display.set_mode((1280, 720))
    clock = pygame.time.Clock()
    running = True
    
    # Create bots
    bots = []
    seed_bots = [
        Kilobot((768, 314), pi, is_seed=True),
    ]
    bots.extend(seed_bots)
    
    edge_bots = generate_kilobot_grid(10, 20, (768, 341))
    bots.extend(edge_bots)
    
    # Load shape image
    shape = pygame.image.load("donut.png")
    shape.set_colorkey ((255, 255, 255))
    shape.set_alpha(77)
    
    # Convert to array
    shape_array = pygame.surfarray.array3d(shape)
    
    

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
                
        
        # Update bots
        dt = (clock.get_time() / 1000) * TIME_SCALE
        update_bots(bots, dt, shape_array)

        # fill the screen with a color to wipe away anything from last frame
        # Gray tiles of size 10x10, black outline
        for x in range(0, 1280, BACKGROUND_TILE_SIZE):
            for y in range(0, 720, BACKGROUND_TILE_SIZE):
                pygame.draw.rect(screen, "#f1faee", (x, y, BACKGROUND_TILE_SIZE, BACKGROUND_TILE_SIZE), 0)
                if display_grid:
                    pygame.draw.rect(screen, (230,230,230), (x, y, BACKGROUND_TILE_SIZE, BACKGROUND_TILE_SIZE), 1)

        # RENDER YOUR GAME HERE
        if display_desired_shape:
            screen.blit(shape, (640 - shape.get_width()//2, 360 - shape.get_height()//2))
        
        if display_bots:
            draw_bots(screen, bots, display_gradient)

        # flip() the display to put your work on screen
        pygame.display.flip()

        clock.tick(60)  # limits FPS to 60

    pygame.quit()
    

main()