# core/engine.py
# ─────────────────────────────────────────────────────────────────────────────
# Thin game-loop wrapper.  Drives one Game instance per call to run().
# Returns a routing token so main.py knows what to do next:
#   "menu"  → go back to mode-selection screen
#   "retry" → rebuild the same mode from scratch
#   None    → window was closed (quit)
# ─────────────────────────────────────────────────────────────────────────────

import pygame
from core.config import FPS


class Engine:

    def __init__(self):
        self.running = True
        self._clock  = pygame.time.Clock()

    def run(self, screen, game):
        """
        Run the game loop for a single Game instance until a routing
        signal is returned or the window is closed.
        """
        while self.running:
            # Delta-time in seconds — capped at 100 ms to avoid spiral of death
            dt = min(self._clock.tick(FPS) / 1000.0, 0.10)

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                    return None                   # caller should quit

                result = game.handle_event(event)
                if result in ("menu", "retry"):
                    return result

            game.update(dt)
            game.draw(screen)
            pygame.display.flip()

        return None