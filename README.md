# Dipper and Mabel in the Secret Bunker

2D Python game on `pygame` with three stages:

- Level 1: forest run around the Mystery Shack, dodging gnomes and anomalies while collecting diary pages.
- Level 2: secret bunker with ciphers, moving platforms, hidden ink, and gravity inversion zones.
- Level 3: boss fight against Bill Cipher's shadow, then portal activation with Stan's key.

The reveal mechanic is bound to `F`: Dipper uses the diary lens / flashlight to temporarily show hidden platforms, traps, weak points, and invisible-ink clues.

## Run

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip setuptools wheel
.\.venv\Scripts\python.exe -m pip install -r .\requirements.txt
.\.venv\Scripts\python.exe .\main.py
```

If `pip` tries to build `pygame` from source and fails, force wheel-only install:

```powershell
.\.venv\Scripts\python.exe -m pip install --only-binary=:all: "pygame>=2.6.1,<2.7"
```

If your local Python still cannot get a wheel, recreate the virtual environment with Python 3.12:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip setuptools wheel
.\.venv\Scripts\python.exe -m pip install -r .\requirements.txt
```

## Controls

- `A/D` or arrows: move
- `Space`, `W`, `Up`: jump
- `F`: reveal hidden ink / secret objects
- `E`: charge the portal on the final level
- `R`: restart after defeat or victory

## Music

Background music is generated procedurally on first launch as a looping `.wav` in the temp folder. It is designed to evoke mysterious indie-folk with acoustic-style harmonics, tape noise, and rising tension without needing external assets.
