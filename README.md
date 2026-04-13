# Festival Overlay Pro
A customizable, low-latency input overlay for rhythm games (optimized for Fortnite Festival).

## Features
- **GUI Configurator**: Easily change colors, FPS, and sound effects.
- **Input Recorder**: Assign keys or controller buttons by simply pressing them.
- **Special Layout**: Dedicated Overdrive (OD) lane with a visual gap for better visibility.
- **OBS Ready**: Custom chroma-key background support.

## Installation
1. Install [Python](https://www.python.org/).
2. Install Pygame:
   `pip install pygame`
3. Place a sound file named `click.wav` in the project directory.
4. Run the script:
   `python overlay.py`

## Note for Mac Users
Some Python versions (like 3.14) on macOS may have issues with the `pygame.mixer` module. If sound doesn't play, the overlay will still function perfectly as a visual aid.