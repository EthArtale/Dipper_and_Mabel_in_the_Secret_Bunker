# Dipper and Mabel in the Secret Bunker

2D `pygame` game inspired by the atmosphere of Gravity Falls. The player guides Dipper through three connected stages: a forest escape, a bunker full of ciphers and traps, and a final boss fight against Bill's shadow.

The project is built as a single-file game in `main.py`, with external assets loaded from `assets/` when available and procedural fallbacks used when they are missing.

## Features

- 3 playable levels with different pacing and mechanics
- flashlight / diary reveal mechanic for hidden pages, clues, platforms, weak points, and destructible enemies
- menu and settings screens with replaceable UI assets
- parallax background support for level 1 and level 2
- boss fight with telegraphed attacks, teleportation, weak points, and multiple attack patterns
- procedural music and procedural sound effects as fallback audio
- support for custom sprites, backgrounds, logos, icons, and UI textures without changing the code

## Level Structure

### Level 1: Forest Run

- run near the Mystery Shack and collect pages
- dodge moving gnomes and static anomalies
- use the flashlight to reveal hidden pages
- forest background supports `forest_layer_1 ... forest_layer_12`

### Level 2: Secret Bunker

- larger platforming level with moving platforms, puzzles, traps, creatures, and hidden routes
- cipher interaction pauses gameplay and opens separate puzzle windows
- zero-gravity zones remove gravity instead of inverting it
- some spider-like enemies can be destroyed by sustained flashlight exposure
- bunker background supports `bunker_layer_1 ... bunker_layer_12`
- `bunker_layer_5` is rendered as a true foreground layer over the whole scene
- platforms and ceiling can use `bunker_tileset`

### Level 3: Boss Fight

- arena battle against Bill's shadow
- boss teleports between anchor points
- attacks include telegraphed dark-energy beams and rare ground bursts
- weak points are revealed and destroyed with the diary lens
- solving bunker ciphers grants boss-fight bonuses and unlocks the true ending when all 3 are solved

## Controls

- `A / D` or `Left / Right`: move
- `Space`, `W`, `Up`: jump
- `F` or left mouse button: use flashlight / reveal lens
- `E`: interact with ciphers and charge the portal
- `Esc`: pause, close puzzle window, or return from some screens
- `R`: restart after defeat or victory

## Run

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip setuptools wheel
.\.venv\Scripts\python.exe -m pip install -r .\requirements.txt
.\.venv\Scripts\python.exe .\main.py
```

If `pygame` tries to build from source and fails, force wheel-only install:

```powershell
.\.venv\Scripts\python.exe -m pip install --only-binary=:all: "pygame>=2.6.1,<2.7"
```

If your local Python still cannot get a wheel, recreate the environment with Python 3.12:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip setuptools wheel
.\.venv\Scripts\python.exe -m pip install -r .\requirements.txt
```

## Requirements

- Python 3.11+ recommended
- `pygame>=2.6.1,<2.7`

See `requirements.txt`.

## Project Structure

```text
GravityFalls/
|- main.py
|- requirements.txt
|- README.md
|- assets/
|  |- README.md
|  |- images/
|  |- fonts/
|  `- audio/
|- savegame.json
|- tmp_bunker_preview.png
|- .venv/
`- __pycache__/
```

Important notes:

- `main.py` contains the main loop, levels, UI, audio generation, and rendering helpers.
- `assets/README.md` documents replaceable asset filenames in detail.
- `savegame.json` is created automatically and stores progress.
- procedural audio may create temporary `.wav` files in the system temp directory.

## Replaceable Assets

The game supports external assets for:

- app window icon
- main menu logo
- main menu and settings backgrounds
- cipher puzzle background
- level backgrounds and parallax layers
- bunker tileset
- player, gnome, and boss sprites
- buttons, arrows, slider pieces, and settings UI parts
- custom background music

For the full supported filename list, see `assets/README.md`.

## Audio Notes

If no custom music is provided, the game generates background music procedurally. If no custom SFX are added, actions still have synthesized fallback sound effects.

Current procedural SFX cover:

- jump
- page pickup
- damage / hit
- opening a cipher puzzle
- solving a cipher
- burning spider-like enemies
- boss teleport
- boss attack
- portal activation
- menu clicks

## Save System

- progress is stored in `savegame.json`
- the file saves the current unlocked level index
- restarting the whole adventure can clear progress

## Git Notes

If you publish this project to Git, it is better not to commit generated or local-only files such as:

- `.venv/`
- `__pycache__/`
- `savegame.json`
- `tmp_bunker_preview.png`

Suggested `.gitignore` entries:

```gitignore
.venv/
__pycache__/
*.pyc
savegame.json
tmp_bunker_preview.png
```

Large custom binary assets can also be excluded or moved to Git LFS if the repository grows.

## Technical Notes

- The project uses a replaceable-asset-first approach: if an asset exists, it is loaded; otherwise a fallback is rendered or generated.
- The game mixes external raster art with procedural rendering to stay playable without a full asset pack.
- Several systems are intentionally data-like even inside a single-file structure: ciphers, pages, attack objects, telegraphs, weak points, and UI asset maps.

## Current State

This repository contains a playable prototype / vertical slice rather than a fully modularized production codebase. The game is feature-rich, but most logic currently lives in one file for iteration speed.

That makes the project easy to run and modify, but if it grows further, a future refactor into modules such as `levels`, `ui`, `audio`, and `assets` would be the natural next step.
