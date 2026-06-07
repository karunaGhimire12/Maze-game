# Maze Adventure

A first-level 3D hedge maze game made with Python and Ursina. The code is split into a scalable `game/` package.

## Game Rules

- Reach the simple 3D house before the timer ends.
- The shrub maze has confusing branches, dead ends, and quiz checkpoints.
- You start with 5 lives.
- Golden question coins ask simple math or GK questions and move after restart.
- Correct answers add time. Harder questions give more time.
- Wrong answers remove one life.
- If lives reach 0 or the timer reaches 0, the level is failed.
- First-person movement uses Ursina's `FirstPersonController`.

## Run

Install dependencies once inside your venv:

```powershell
python -m pip install -r requirements.txt
```

Then start the game with taskipy:

```powershell
.\venv\Scripts\Activate.ps1
task start
```

You can also use:

```powershell
task play
```

## Controls

- Move: arrow keys or WASD
- Move: WASD or arrow keys
- Look around: mouse
- Submit answer: Enter
- Restart after win/loss: R
- Unlock/lock mouse: Escape
