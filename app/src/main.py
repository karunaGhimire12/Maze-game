# main.py

import sys
import os

# Ensure src/ and data/ are on the path
_SRC = os.path.dirname(os.path.abspath(__file__))
_APP = os.path.dirname(_SRC)
sys.path.insert(0, _SRC)
sys.path.insert(0, _APP)

import pygame

from core.config import SCREEN_WIDTH, SCREEN_HEIGHT, FPS
from core.engine import Engine
from core.game   import Game
from views.screens import MainMenuScreen


def main():
    pygame.init()
    pygame.display.set_caption("Maze Quest")

    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    clock  = pygame.time.Clock()
    engine = Engine()

    current_mode = None
    menu = MainMenuScreen()

    while engine.running:
        # ---- Main Menu Loop ----
        if current_mode is None:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    engine.running = False
                    break
                selected = menu.handle_event(event)
                if selected:
                    current_mode = selected

            menu.draw(screen)
            pygame.display.flip()
            clock.tick(FPS)
            continue

        # ---- Game Loop ----
        game   = Game(current_mode)
        result = engine.run(screen, game)

        if result == "menu":
            current_mode = None
        elif result == "retry":
            pass  # keep current_mode, restart
        else:
            # Window closed
            break

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()