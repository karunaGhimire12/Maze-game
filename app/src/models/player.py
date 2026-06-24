# models/player.py
# ─────────────────────────────────────────────────────────────────────────────
# Two player classes — one for rectangular grid mazes, one for circular mazes.
# Both share the same interface (lives, time_bonus, at_junction, lose_life).
#
# FIX #1 note:
#   CircularPlayer.move() simply forwards the direction string to
#   CircularMaze.can_move() which now contains the corrected logic.
#   No movement logic lives here — the maze is the single source of truth
#   for what moves are legal.
# ─────────────────────────────────────────────────────────────────────────────

import math

from core.config import PLAYER_LIVES, MOVE_SPEED_CELLS, CIRCULAR_MOVE_SPEED_CELLS


# ════════════════════════════════════════════════════════════════════════════
#  Rectangular player
# ════════════════════════════════════════════════════════════════════════════

class Player:
    """Player navigating a rectangular grid Maze."""

    def __init__(self, row: int, col: int):
        self.row  = row
        self.col  = col
        self.visual_row = float(row)
        self.visual_col = float(col)
        self._moving = False
        self.lives = PLAYER_LIVES
        self.time_bonus = 0            # accumulated bonus seconds (cosmetic)
        self.visited_junctions: set = set()

    # ── movement ──────────────────────────────────────────────────────────────

    def move(self, dr: int, dc: int, maze) -> bool:
        """
        Attempt to move by (dr, dc).  Returns True if the move was legal.
        The maze is the authority on walkability.
        """
        nr, nc = self.row + dr, self.col + dc
        if maze.is_walkable(nr, nc):
            self.row, self.col = nr, nc
            self._moving = True
            return True
        return False

    def update(self, dt: float) -> bool:
        """Animate toward the logical cell. Returns True on arrival this frame."""
        speed = MOVE_SPEED_CELLS * dt
        before = self._moving
        self.visual_row = _approach(self.visual_row, float(self.row), speed)
        self.visual_col = _approach(self.visual_col, float(self.col), speed)
        self._moving = (
            abs(self.visual_row - self.row) > 0.001 or
            abs(self.visual_col - self.col) > 0.001
        )
        return before and not self._moving

    def is_moving(self) -> bool:
        return self._moving

    def reset_to(self, row: int, col: int):
        self.row = row
        self.col = col
        self.visual_row = float(row)
        self.visual_col = float(col)
        self._moving = False
        self.visited_junctions.clear()

    # ── life management ───────────────────────────────────────────────────────

    def lose_life(self) -> bool:
        """Remove one life.  Returns True if the player is now dead (0 lives)."""
        self.lives = max(0, self.lives - 1)
        return self.lives <= 0

    # ── junction tracking ─────────────────────────────────────────────────────

    def at_junction(self, maze) -> bool:
        """
        Returns True once per junction cell — subsequent visits are ignored
        so the quiz popup is not re-triggered on the same cell.
        """
        pos = (self.row, self.col)
        if pos in self.visited_junctions:
            return False
        if maze.is_junction(self.row, self.col):
            self.visited_junctions.add(pos)
            return True
        return False

    # ── bonus ─────────────────────────────────────────────────────────────────

    def add_bonus(self, seconds: float):
        self.time_bonus += seconds


# ════════════════════════════════════════════════════════════════════════════
#  Circular player
# ════════════════════════════════════════════════════════════════════════════

class CircularPlayer:
    """
    Player navigating a CircularMaze.
    Position is (ring, sector).  Ring 0 = centre (goal), ring N-1 = outer start.

    FIX #1 — movement:
    Direction strings ('out', 'in', 'cw', 'ccw') are forwarded directly to
    CircularMaze.can_move() which now applies the corrected direction semantics.
    """

    def __init__(self, ring: int, sector: int):
        self.ring   = ring
        self.sector = sector
        self.visual_ring = float(ring)
        self.visual_sector = float(sector)
        self._moving = False
        self.lives  = PLAYER_LIVES
        self.time_bonus = 0
        self.visited_junctions: set = set()

    # ── movement ──────────────────────────────────────────────────────────────

    def move(self, direction: str, maze) -> bool:
        """
        Ask the maze whether movement in `direction` is possible.
        'out' / 'in' / 'cw' / 'ccw' — see CircularMaze.can_move() for details.
        Returns True if the move succeeded.
        """
        result = maze.can_move(self.ring, self.sector, direction)
        if result is not None:
            old_sector = self.sector
            self.ring, self.sector = result
            sector_count = maze.spr[self.ring]
            if direction == "cw" and self.sector == 0 and old_sector != 0:
                self.visual_sector = -1.0
            elif direction == "ccw" and self.sector == sector_count - 1 and old_sector == 0:
                self.visual_sector = float(sector_count)
            else:
                self.visual_sector = float(old_sector)
            self._moving = True
            return True
        return False

    def update(self, dt: float) -> bool:
        speed = CIRCULAR_MOVE_SPEED_CELLS * dt
        before = self._moving
        self.visual_ring = _approach(self.visual_ring, float(self.ring), speed)
        self.visual_sector = _approach(self.visual_sector, float(self.sector), speed)
        self._moving = (
            abs(self.visual_ring - self.ring) > 0.001 or
            abs(self.visual_sector - self.sector) > 0.001
        )
        return before and not self._moving

    def is_moving(self) -> bool:
        return self._moving

    def reset_to(self, ring: int, sector: int):
        self.ring = ring
        self.sector = sector
        self.visual_ring = float(ring)
        self.visual_sector = float(sector)
        self._moving = False
        self.visited_junctions.clear()

    # ── life management ───────────────────────────────────────────────────────

    def lose_life(self) -> bool:
        self.lives = max(0, self.lives - 1)
        return self.lives <= 0

    # ── junction tracking ─────────────────────────────────────────────────────

    def at_junction(self, maze) -> bool:
        pos = (self.ring, self.sector)
        if pos in self.visited_junctions:
            return False
        if maze.is_junction(self.ring, self.sector):
            self.visited_junctions.add(pos)
            return True
        return False

    # ── bonus ─────────────────────────────────────────────────────────────────

    def add_bonus(self, seconds: float):
        self.time_bonus += seconds


def _approach(value: float, target: float, step: float) -> float:
    if math.isclose(value, target, abs_tol=step):
        return target
    return value + step if value < target else value - step
