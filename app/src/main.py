# main.py

import sys
import os
import pygame
import core.config as config

# Ensure src/ and data/ are on the path
_SRC = os.path.dirname(os.path.abspath(__file__))
_APP = os.path.dirname(_SRC)
sys.path.insert(0, _SRC)
sys.path.insert(0, _APP)


pygame.init()

info=pygame.display.Info()

config.SCREEN_WIDTH=int(info.current_w*0.6)
config.SCREEN_HEIGHT=int(info.current_h*0.85)
                         
from core.config import SCREEN_WIDTH, SCREEN_HEIGHT, MIN_SCREEN_WIDTH, MIN_SCREEN_HEIGHT, FPS
from core.engine import Engine
from core.game   import Game
from views.screens import MainMenuScreen


pygame.display.set_caption("Maze Quest")
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.RESIZABLE)
clock  = pygame.time.Clock()
engine = Engine()




def main():
    current_mode = None
    current_difficulty = None
    menu = MainMenuScreen()

    while engine.running:
        # ---- Main Menu Loop ----
        if current_mode is None:
            screen = pygame.display.get_surface()
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    engine.running = False
                    break
                selected = menu.handle_event(event)
                if selected:
                    current_mode, current_difficulty = selected
                if event.type == pygame.VIDEORESIZE:
                    w = max(MIN_SCREEN_WIDTH, event.w)
                    h = max(MIN_SCREEN_HEIGHT, event.h)
                    screen = pygame.display.set_mode((w, h), pygame.RESIZABLE)

            menu.draw(screen)
            pygame.display.flip()
            clock.tick(FPS)
            continue

        # ---- Game Loop ----
        game   = Game(current_mode, current_difficulty)
        result = engine.run(screen, game)

        if result == "menu":
            current_mode = None
            current_difficulty = None
        elif result == "retry":
            pass  # keep current_mode, restart
        else:
            # Window closed
            break

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
