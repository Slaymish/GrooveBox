# Groovebox Engine AI Instructions

## Project Overview
This is a Python-based Groovebox application (drum machine/sequencer) built using `pygame` for both the graphical interface and audio playback. The core logic resides in `host/engine/groovebox/`.

## Architecture
The application follows a monolithic architecture with clear separation of concerns:

- **Entry Point**: `host/engine/groovebox/main.py` initializes the configuration and UI.
- **UI & Main Loop** (`ui_pygame.py`):
  - The `GrooveboxUI` class owns the application lifecycle.
  - Runs the main `while running:` loop.
  - Handles `pygame` events (keyboard input) and rendering.
  - Calls `sequencer.tick()` every frame to drive the audio engine.
- **Sequencer** (`sequencer.py`):
  - `Sequencer` class manages playback state (play/record, BPM, swing).
  - Uses `time.monotonic()` for precise musical timing, independent of the UI framerate.
  - Manages `Pattern`, `Track`, and `Step` data structures.
- **Audio** (`audio.py`):
  - `AudioEngine` wraps `pygame.mixer`.
  - Handles sample loading and playback.
  - **Pattern**: Decoupled from the UI; the sequencer triggers sounds via this engine.
- **Configuration** (`config.py`):
  - Loads settings from JSON files (e.g., `config/pad.json`).
  - Uses `dataclasses` for typed configuration objects.

## Development Workflow

### Running the Application
Run the application from the repository root to ensure relative paths (like config loading) work correctly:
```bash
python host/engine/groovebox/main.py
```
*Note: Ensure `pygame` is installed in your environment.*

### Key Dependencies
- **Pygame**: Used for window management, input handling, and audio mixing.
- **Dataclasses**: Extensively used for data modeling (`Step`, `Track`, `Pattern`).

## Coding Conventions & Patterns

### Type Hinting
- All functions and methods must have type hints.
- Use `list[Type]` instead of `List[Type]` (modern Python syntax).

### Data Structures
- Prefer `@dataclass` for state and configuration objects.
- Example:
  ```python
  @dataclass
  class Step:
      state: int = 0
  ```

### Timing & Audio
- **Do not** rely on `clock.tick()` for musical timing. The sequencer calculates delta time using `time.monotonic()`.
- Audio operations should be non-blocking.

### UI Implementation
- UI logic belongs in `ui_pygame.py`.
- Draw methods should be efficient as they run every frame.
- Input handling is centralized in `GrooveboxUI.run()` and delegated to handler methods.
